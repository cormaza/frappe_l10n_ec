"""Monthly Form 103 collector: AUTHORIZED 07 voucher IR blocks to casilleros.

Pure Python, no frappe: Ring 1 tests inject synthetic voucher dicts shaped
like the bench fetch (``sri_number``/``voucher_state``/``sri_doc_code``/
``authorization_number``/``authorization_date``/``unsigned_xml``) and never
touch the database. The thin Script Report
(``ecuador_localization/report/sri_form_103``) fetches Authorized 07
vouchers on a bench site and shapes them for :func:`collect_103`.

Voucher shape::

    {
        "sri_number": "001-001-000000007",
        "voucher_state": "Authorized",
        "sri_doc_code": "07",
        "authorization_number": "1234567890",
        "authorization_date": "2026-03-25 10:00:00",  # bench Datetime, date, or DD/MM/YYYY
        "unsigned_xml": "<comprobanteRetencion ...>...</comprobanteRetencion>",
    }

Collection rules:

* Only ``Authorized`` ``07`` vouchers read; anything else (Rejected, other
  document codes, non-retencion bodies) is skipped, never fabricated.
* Only the requested month reads: ``authorization_date`` first, parsed body
  ``fiscal_period`` (``MM/YYYY``) as fallback. Vouchers with neither fail
  loud instead of landing in the wrong month.
* Every IR row (impuesto ``1``) resolves through the concepto table:
  unknown conceptos fail loud, and known conceptos without sighted
  casilleros fail loud (never guess a box). Base feeds the first
  casillero, the withheld value the second; single-box codes (309, 332,
  ...) record the base only.
* IVA rows (impuesto ``2``) are skipped: they belong to Form 104.
* Exterior rows (impuesto ``9``) collect into their regime boxes from
  the voucher's explicit ``sri_exterior_regime`` (``con``/``sin``/``paraiso``)
  through guide-sighted pairs only; a missing regime or an unsighted pair
  fails loud. Without exterior rows the section stays explicit-empty.
* Totals sum per casillero across the month's vouchers. Portal-level
  subtotals/totals (349/399, 499/500/501) are not computed here: the
  presentation subtotal (497/498) is informational only.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.voucher_data import parse_emitted_xml
from l10n_ec.sri.voucher_states import SriVoucherError
from l10n_ec.sri.withholding_concepts import NON_EMITTABLE_IMPUESTOS, casilleros_for, resolve_concepto

AUTHORIZED_STATE = "Authorized"
RETENCION_DOC_CODE = "07"


def collect_103(vouchers: list, year: int, month: int) -> dict:
	"""Aggregate one month of AUTHORIZED 07 IR blocks into casillero totals.

	Returns ``{casillero: value}`` sorted by casillero; a month with no
	Authorized 07 vouchers returns ``{}``. Portal subtotals travel with
	the data: 349/399 sum the residentes section, 497/498 the exterior
	section, and 499 = 399 + 498 (template formula, SRI RF ago-2026
	template). Boxes 500/501 need the external compensación input and
	stay portal-side, documented.
	"""
	_validate_period(year, month)
	totals: dict = {}
	for concepto, base, value, regime in _iter_ir_rows(vouchers, year, month):
		_accumulate_concepto(totals, concepto, base, value, regime)
	if not totals:
		return {}
	from l10n_ec.sri.withholding_concepts import CONCEPTS

	res_base: set = set()
	res_tax: set = set()
	for _impuesto, _description, _rate, _valid_from, casilleros in CONCEPTS.values():
		if _impuesto != "1" or not casilleros:
			continue
		res_base.add(int(casilleros[0]))
		if len(casilleros) > 1:
			res_tax.add(int(casilleros[1]))
	ext_base = {pair[0] for pair in EXTERIOR_BOXES.values()}
	ext_tax = {pair[1] for pair in EXTERIOR_BOXES.values()}
	totals[349] = round(sum(v for box, v in totals.items() if box in res_base), 2)
	totals[399] = round(sum(v for box, v in totals.items() if box in res_tax), 2)
	totals[497] = round(sum(v for box, v in totals.items() if box in ext_base), 2)
	totals[498] = round(sum(v for box, v in totals.items() if box in ext_tax), 2)
	totals[499] = round(totals[399] + totals[498], 2)
	return dict(sorted(totals.items()))


def _iter_ir_rows(vouchers: list, year: int, month: int):
	"""Yield ``(concepto, base, value, regime)`` IR rows of the month, validated.

	``regime`` comes from the voucher (``con``/``sin``/``paraiso``); resident
	rows carry ``None``.
	"""
	for voucher in vouchers or []:
		if voucher.get("voucher_state") != AUTHORIZED_STATE:
			continue
		if voucher.get("sri_doc_code", RETENCION_DOC_CODE) != RETENCION_DOC_CODE:
			continue
		xml = voucher.get("unsigned_xml") or ""
		if not xml:
			raise SriVoucherError(
				_("SRI voucher '{}' has no withholding XML to collect.").format(voucher.get("sri_number", ""))
			)
		body = parse_emitted_xml(xml)
		if body.get("kind") != "retencion":
			continue
		if _voucher_month(voucher, body) != (year, month):
			continue
		regime = voucher.get("sri_exterior_regime")
		for doc in body.get("docs", []):
			for row in doc.get("withholdings", []):
				yield (
					row.get("withholding_code", ""),
					round(float(row.get("base", 0.0)), 2),
					round(float(row.get("value", 0.0)), 2),
					regime,
				)


#: {(concepto, regime): (base_box, tax_box)} — guide-sighted pairs only.
#: Triplets in the concepto table read con/sin/paraiso; impuesto boxes do
#: NOT follow +50 universally (4050->4550), so every pair below was read
#: off the guide row, never arithmetized.
EXTERIOR_BOXES = {
	("501A", "con"): (410, 460),
	("501A", "sin"): (421, 471),
	("501A", "paraiso"): (431, 481),
	("501", "con"): (411, 461),
	("501", "sin"): (422, 472),
	("501", "paraiso"): (432, 482),
	("500", "con"): (411, 461),
	("500", "sin"): (422, 472),
	("500", "paraiso"): (432, 482),
}

#: Regime labels for presentation.
REGIME_LABELS = {"con": "con convenio", "sin": "sin convenio", "paraiso": "paraíso fiscal"}


def _accumulate_concepto(totals: dict, concepto: str, base: float, value: float, regime=None) -> None:
	"""Add one IR row to its concepto casilleros."""
	impuesto, _rate, _description = resolve_concepto(concepto)
	if impuesto in NON_EMITTABLE_IMPUESTOS:
		return _accumulate_exterior(totals, concepto, base, value, regime)
	if impuesto != "1":
		return
	boxes = casilleros_for(concepto)
	if not boxes:
		raise SriVoucherError(
			_("SRI withholding concepto '{}' has no Form 103 casilleros; cannot collect.").format(concepto)
		)
	totals[boxes[0]] = round(totals.get(boxes[0], 0.0) + base, 2)
	if len(boxes) > 1:
		totals[boxes[1]] = round(totals.get(boxes[1], 0.0) + value, 2)


def collect_103_by_concepto(vouchers: list, year: int, month: int) -> dict:
	"""Aggregate one month into ``{concepto_code: {base, value}}`` (pure).

	Companion to :func:`collect_103` for presentation: casillero totals
	cannot tell sibling conceptos apart when they share boxes (e.g. every
	``332*`` writes box 332), so rows render from fired conceptos, never
	from a blind box-to-concepto inversion.
	"""
	_validate_period(year, month)
	by_concepto: dict = {}
	for concepto, base, value, regime in _iter_ir_rows(vouchers, year, month):
		key = (concepto, regime) if regime else concepto
		entry = by_concepto.setdefault(key, {"base": 0.0, "value": 0.0, "regime": regime})
		entry["base"] = round(entry["base"] + base, 2)
		entry["value"] = round(entry["value"] + value, 2)
	return by_concepto


def _validate_period(year: int, month: int) -> None:
	"""Fail loud on an unusable fiscal period before reading any voucher."""
	if not isinstance(year, int) or year < 2000 or year > 9999:
		raise SriVoucherError(_("Form 103 collection year '{}' is out of range.").format(year))
	if not isinstance(month, int) or month < 1 or month > 12:
		raise SriVoucherError(_("Form 103 collection month '{}' is out of range.").format(month))


def _voucher_month(voucher: dict, body: dict) -> tuple:
	"""(year, month) of a voucher: authorization date, else fiscal period."""
	period = _authorization_month(voucher.get("authorization_date"))
	if period is None:
		period = _fiscal_month(body.get("fiscal_period") or "")
	if period is None:
		raise SriVoucherError(
			_("SRI voucher '{}' carries no usable authorization date or fiscal period.").format(
				voucher.get("sri_number", "")
			)
		)
	return period


def _authorization_month(value) -> tuple | None:
	"""(year, month) from a bench Datetime, date, or DD/MM/YYYY string."""
	if value is None or value == "":
		return None
	if isinstance(value, str):
		text = value.strip()
		try:
			if len(text) >= 10 and text[4] == "-" and text[7] == "-":
				return (int(text[0:4]), int(text[5:7]))
			parts = text.split("/")
			if len(parts) == 3 and len(parts[2]) == 4:
				return (int(parts[2]), int(parts[1]))
		except ValueError:
			return None
		return None
	year = getattr(value, "year", None)
	month = getattr(value, "month", None)
	if isinstance(year, int) and isinstance(month, int):
		return (year, month)
	return None


def _fiscal_month(fiscal_period: str) -> tuple | None:
	"""(year, month) from a parsed ``MM/YYYY`` fiscal period."""
	parts = (fiscal_period or "").strip().split("/")
	if len(parts) != 2:
		return None
	try:
		return (int(parts[1]), int(parts[0]))
	except ValueError:
		return None


def _accumulate_exterior(totals: dict, concepto: str, base: float, value: float, regime) -> None:
	"""Add one exterior row to its regime boxes (sourced pairs only)."""
	if regime not in ("con", "sin", "paraiso"):
		raise SriVoucherError(
			_(
				"Exterior concepto '{}' needs an explicit regime (con/sin/paraiso); refusing to place it."
			).format(concepto)
		)
	pair = EXTERIOR_BOXES.get((concepto, regime))
	if pair is None:
		raise SriVoucherError(
			_("Exterior pair ('{}', '{}') has no guide-sighted boxes; cannot collect.").format(
				concepto, regime
			)
		)
	totals[pair[0]] = round(totals.get(pair[0], 0.0) + base, 2)
	totals[pair[1]] = round(totals.get(pair[1], 0.0) + value, 2)


def _accumulate_row(totals: dict, row: dict) -> None:
	"""Add one parsed retencion row to its concepto casilleros."""
	_accumulate_concepto(
		totals,
		row.get("withholding_code", ""),
		round(float(row.get("base", 0.0)), 2),
		round(float(row.get("value", 0.0)), 2),
	)


def _append_exterior_row(rows: list, code: str, description: str, entry: dict, owned: set) -> None:
	"""Render one exterior concepto row from its declared regime (pure)."""
	regime = entry.get("regime") or ""
	pair = EXTERIOR_BOXES.get((code, regime))
	if pair is None:
		raise ValueError(
			_("Exterior pair ('{}', '{}') has no guide-sighted boxes; cannot present.").format(code, regime)
		)
	base = round(float(entry.get("base", 0.0)), 2)
	tax = round(float(entry.get("value", 0.0)), 2)
	owned.add(pair[0])
	owned.add(pair[1])
	rows.append(
		{
			"kind": "exterior",
			"concepto": f"{code} — {description} (exterior: {REGIME_LABELS.get(regime, regime)})",
			"cas_base": pair[0],
			"base": base,
			"cas_impuesto": pair[1],
			"impuesto": tax,
		}
	)


def build_103_rows(totals: dict, by_concepto: dict | None = None) -> list:
	"""Build per-concepto presentation rows from fired conceptos.

	``totals`` comes from :func:`collect_103`; ``by_concepto`` from
	:func:`collect_103_by_concepto`. Rows render from fired conceptos, never
	from a blind box-to-concepto inversion (sibling codes share boxes: every
	``332*`` writes box 332). Each row carries ``kind``
	(``concepto``/``total``/``note``), ``concepto`` (SRI code + official
	description), ``cas_base``, ``base``, ``cas_impuesto``, ``impuesto``.
	Only conceptos with movement render; the exterior section renders as an
	explicit-empty note (never guessed). A casillero no rendered concepto
	owns fails loud. Pure Python, no frappe.
	"""
	from l10n_ec.sri.withholding_concepts import CONCEPTS

	normalized = {int(box): round(float(value or 0.0), 2) for box, value in (totals or {}).items()}
	for box, value in normalized.items():
		if value < 0:
			raise ValueError(
				_("Form 103 casillero '{}' carries a negative value '{}'; retentions never subtract.").format(
					box, value
				)
			)
	if by_concepto is None:
		raise ValueError(
			_("Form 103 rows need per-concepto detail; totals alone cannot tell sibling conceptos apart.")
		)
	rows: list = []
	base_total = 0.0
	tax_total = 0.0
	owned: set = set()
	for key in sorted(by_concepto, key=str):
		entry = by_concepto[key] or {}
		code, entry_regime = key if isinstance(key, tuple) else (key, entry.get("regime"))
		if isinstance(key, tuple):
			entry = dict(entry, regime=entry_regime)
		base = round(float(entry.get("base", 0.0)), 2)
		tax = round(float(entry.get("value", 0.0)), 2)
		if not base and not tax:
			continue
		try:
			_impuesto, description, _rate, _valid_from, casilleros = CONCEPTS[code]
		except KeyError:
			raise ValueError(
				_("SRI withholding concepto '{}' is not a known concepto.").format(code)
			) from None
		if _impuesto == "9":
			_append_exterior_row(rows, code, description, entry, owned)
			continue
		if _impuesto != "1":
			continue
		if not casilleros:
			raise ValueError(
				_("SRI withholding concepto '{}' has no Form 103 casilleros; cannot present.").format(code)
			)
		base_box = int(casilleros[0])
		tax_box = int(casilleros[1]) if len(casilleros) > 1 else None
		owned.add(base_box)
		if tax_box:
			owned.add(tax_box)
		base_total = round(base_total + base, 2)
		tax_total = round(tax_total + tax, 2)
		rows.append(
			{
				"kind": "concepto",
				"concepto": f"{code} — {description}",
				"cas_base": base_box,
				"base": base,
				"cas_impuesto": tax_box,
				"impuesto": tax if tax_box else None,
			}
		)
	for box in normalized:
		if box in (349, 399, 497, 498, 499):
			continue  # computed portal boxes, rendered below from collected values
		if normalized[box] and box not in owned:
			raise ValueError(_("Form 103 casillero '{}' belongs to no rendered concepto.").format(box))
	ext_base = normalized.get(497, 0.0)
	ext_tax = normalized.get(498, 0.0)
	if ext_base or ext_tax:
		rows.append(
			{
				"kind": "subtotal",
				"concepto": "SUBTOTAL EXTERIOR (casilleros 497/498)",
				"cas_base": 497,
				"base": ext_base,
				"cas_impuesto": 498,
				"impuesto": ext_tax,
			}
		)
	else:
		rows.append(
			{
				"kind": "note",
				"concepto": "EXTERIOR: sin valores (se declara vacío)",
				"cas_base": None,
				"base": None,
				"cas_impuesto": None,
				"impuesto": None,
			}
		)
	rows.append(
		{
			"kind": "subtotal",
			"concepto": "SUBTOTAL RESIDENTES (casilleros 349/399)",
			"cas_base": 349,
			"base": normalized.get(349, 0.0),
			"cas_impuesto": 399,
			"impuesto": normalized.get(399, 0.0),
		}
	)
	rows.append(
		{
			"kind": "total",
			"concepto": "TOTAL RESIDENTES (presentación; el portal totaliza 349/399/499/500/501)",
			"cas_base": None,
			"base": base_total,
			"cas_impuesto": None,
			"impuesto": tax_total,
		}
	)
	rows.append(
		{
			"kind": "total",
			"concepto": "TOTAL IMPUESTO A PAGAR (399 + 498; casillero 499)",
			"cas_base": None,
			"base": None,
			"cas_impuesto": 499,
			"impuesto": normalized.get(499, 0.0),
		}
	)
	return rows

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
* Exterior rows (impuesto ``9``) fail loud as out of scope: the exterior
  section is recorded explicit-empty by the report, never guessed from
  resident rows.
* Totals sum per casillero across the month's vouchers. Portal-level
  subtotals/totals (349/399, 499/500/501) are not computed here: with the
  exterior section out of scope any such total would misstate the return.
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
	Authorized 07 vouchers returns ``{}``. The exterior section is always
	absent (explicit-empty, never guessed).
	"""
	_validate_period(year, month)
	totals: dict = {}
	for concepto, base, value in _iter_ir_rows(vouchers, year, month):
		_accumulate_concepto(totals, concepto, base, value)
	return dict(sorted(totals.items()))


def _iter_ir_rows(vouchers: list, year: int, month: int):
	"""Yield ``(concepto, base, value)`` IR rows of the month, validated."""
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
		for doc in body.get("docs", []):
			for row in doc.get("withholdings", []):
				yield (
					row.get("withholding_code", ""),
					round(float(row.get("base", 0.0)), 2),
					round(float(row.get("value", 0.0)), 2),
				)


def _accumulate_concepto(totals: dict, concepto: str, base: float, value: float) -> None:
	"""Add one IR row to its concepto casilleros."""
	impuesto, _rate, _description = resolve_concepto(concepto)
	if impuesto in NON_EMITTABLE_IMPUESTOS:
		raise SriVoucherError(
			_(
				"SRI withholding concepto '{}' is exterior scope and stays out of Form 103 residentes; the exterior section is recorded empty."
			).format(concepto)
		)
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
	for concepto, base, value in _iter_ir_rows(vouchers, year, month):
		entry = by_concepto.setdefault(concepto, {"base": 0.0, "value": 0.0})
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


def _accumulate_row(totals: dict, row: dict) -> None:
	"""Add one parsed retencion row to its concepto casilleros."""
	_accumulate_concepto(
		totals,
		row.get("withholding_code", ""),
		round(float(row.get("base", 0.0)), 2),
		round(float(row.get("value", 0.0)), 2),
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
	for code in sorted(by_concepto):
		entry = by_concepto[code] or {}
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
		if normalized[box] and box not in owned:
			raise ValueError(_("Form 103 casillero '{}' belongs to no rendered concepto.").format(box))
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
			"kind": "note",
			"concepto": "EXTERIOR: sin valores (fuera de alcance, se declara vacío)",
			"cas_base": None,
			"base": None,
			"cas_impuesto": None,
			"impuesto": None,
		}
	)
	return rows

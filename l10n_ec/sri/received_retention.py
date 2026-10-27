"""Map a received retencion XML into a SRI Received Withholding batch draft.

T4 scope: customer-issued withholdings (we are the sujeto retenido).
The parsed 07 carries everything: emisor (customer), number, clave
(doubles as authorization offline), date, fiscal period, and per-doc
withholdings. IR (impuesto 1) and IVA (impuesto 2) split per
sustento doc into allocation rows; unknown impuestos, rate mismatches
against the official table, and missing emisor fail loud.

Bench glue (supplier... customer lookup by emisor RUC, SI auto-match,
duplicate guard, batch insert) lives in the DocType layer, not here.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.withholding_concepts import resolve_concepto


def _to_iso(sri_date: str | None) -> str:
	"""`DD/MM/YYYY` to ISO; fail loud on anything else."""
	parts = (sri_date or "").strip().split("/")
	if len(parts) != 3 or not all(part.isdigit() for part in parts):
		raise ValueError(_("Received retencion date '{}' is not DD/MM/YYYY.").format(sri_date))
	day, month, year = (int(part) for part in parts)
	if not (1 <= month <= 12 and 1 <= day <= 31 and year >= 2000):
		raise ValueError(_("Received retencion date '{}' is not a real date.").format(sri_date))
	return f"{year:04d}-{month:02d}-{day:02d}"


def _split_withholding(entry: dict, doc_number: str) -> tuple:
	"""Split one withholding line into (ir_value, iva_value).

	Validates the concepto against the official table (unknown codes and
	rate mismatches fail loud naming the culprit). Impuesto 9
	(exterior-scope, e.g. 500-series) has no ATS/batch slot: fail loud
	instead of silently dropping someone else's withholding.
	"""
	concept = str(entry.get("withholding_code") or "")
	rate = float(entry.get("rate") or 0)
	value = round(float(entry.get("value") or 0), 2)
	try:
		impuesto, official_rate, _description = resolve_concepto(concept)
	except ValueError as exc:
		raise ValueError(
			_("Received withholding concepto '{}' on '{}' is unknown.").format(concept, doc_number)
		) from exc
	if official_rate is not None and round(float(official_rate), 2) != round(rate, 2):
		raise ValueError(
			_("Received withholding concepto '{}' carries rate '{}' but the official rate is '{}'.").format(
				concept, entry.get("rate"), official_rate
			)
		)
	if impuesto == "1":
		return value, 0.0
	if impuesto == "2":
		return 0.0, value
	raise ValueError(
		_("Received withholding concepto '{}' (impuesto '{}') has no batch slot.").format(concept, impuesto)
	)


def map_received_retencion(parsed: dict) -> dict:
	"""Build a SRI Received Withholding batch draft from parsed `comprobanteRetencion`.

	Returns plain data (customer identity, batch header, per-doc
	allocations with IR/IVA splits). The bench layer resolves the
	customer, matches sales invoices, and guards duplicates.
	"""
	parsed = parsed or {}
	if parsed.get("kind") != "retencion":
		raise ValueError(
			_("Received withholding mapper got '{}', not a retencion.").format(parsed.get("kind"))
		)
	emisor_ruc = (parsed.get("emisor_ruc") or "").strip()
	if not emisor_ruc:
		raise ValueError(_("Received withholding carries no emisor RUC."))
	clave = (parsed.get("clave_acceso") or "").strip()
	if not clave:
		raise ValueError(
			_("Received withholding carries no clave de acceso (offline doubles as authorization).")
		)
	allocations = []
	for doc in parsed.get("docs") or []:
		doc_number = (doc.get("doc_number") or "").strip()
		if not doc_number:
			raise ValueError(_("Received withholding has a sustento without document number."))
		ir_total = 0.0
		iva_total = 0.0
		for entry in doc.get("withholdings") or []:
			ir_value, iva_value = _split_withholding(entry, doc_number)
			ir_total = round(ir_total + ir_value, 2)
			iva_total = round(iva_total + iva_value, 2)
		allocations.append(
			{
				"doc_number": doc_number,
				"doc_date": _to_iso(doc.get("doc_issue_date")) if doc.get("doc_issue_date") else "",
				"ir_value": ir_total,
				"iva_value": iva_total,
			}
		)
	if not allocations:
		raise ValueError(_("Received withholding carries no sustento documents."))
	return {
		"kind": "retencion",
		"customer_tax_id": emisor_ruc,
		"customer_name": (parsed.get("emisor_name") or "").strip(),
		"retencion_number": (parsed.get("number") or "").strip(),
		"authorization": clave,
		"retencion_date": _to_iso(parsed.get("retencion_date")),
		"fiscal_period": (parsed.get("fiscal_period") or "").strip(),
		"allocations": allocations,
	}

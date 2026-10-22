"""Thin Frappe Script Report: SRI Form 103 (residentes IR casilleros).

Bench executes :func:`execute` over Authorized 07 vouchers of the filtered
company/month; the pure collector (``l10n_ec/sri/form103.py``) owns every
mapping rule. The exterior section is explicit-empty: this report renders
residentes rows only, never guessed exterior boxes. Ring-1 importable via
the ``frappe`` import guard (no database, empty data).
"""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.form103 import build_103_rows, collect_103


def execute(filters=None):
	"""Run the SRI Form 103 Script Report; one row per withholding concepto."""
	columns = [
		{"fieldname": "concepto", "label": _("Concept"), "fieldtype": "Data", "width": 380},
		{"fieldname": "cas_base", "label": _("Base box"), "fieldtype": "Int", "width": 100},
		{"fieldname": "base", "label": _("Base amount"), "fieldtype": "Float", "width": 150},
		{"fieldname": "cas_impuesto", "label": _("Withheld box"), "fieldtype": "Int", "width": 110},
		{"fieldname": "impuesto", "label": _("Withheld amount"), "fieldtype": "Float", "width": 150},
	]
	if frappe is None:  # Ring 1: importable, no database.
		return columns, []
	year = int(filters.get("year") or 0) if filters else 0
	month = int(filters.get("month") or 0) if filters else 0
	company = filters.get("company") if filters else None
	if not company or not year or not month:
		return columns, []
	totals = collect_103(_fetch_authorized_vouchers(company, year, month), year, month)
	data = build_103_rows(totals)
	total_row = next((r for r in data if r["kind"] == "total"), None)
	summary = [
		{"label": _("Total base"), "value": (total_row or {}).get("base") or 0.0, "indicator": "blue"},
		{
			"label": _("Total withheld"),
			"value": (total_row or {}).get("impuesto") or 0.0,
			"indicator": "orange",
		},
	]
	return columns, data, None, None, summary, True


def _fetch_authorized_vouchers(company: str, year: int, month: int) -> list:
	"""Authorized 07 vouchers of the month shaped for :func:`collect_103`."""
	from l10n_ec.ecuador_localization.voucher_flow import read_voucher_xml

	start = f"{year}-{month:02d}-01 00:00:00"
	end = f"{year}-{month:02d}-31 23:59:59"
	names = frappe.get_all(
		"SRI Electronic Voucher",
		filters={
			"company": company,
			"sri_doc_code": "07",
			"voucher_state": "Authorized",
			"authorization_date": ["between", [start, end]],
		},
		pluck="name",
	)
	vouchers = []
	for name in names:
		doc = frappe.get_doc("SRI Electronic Voucher", name)
		vouchers.append(
			{
				"sri_number": doc.get("sri_number"),
				"voucher_state": doc.get("voucher_state"),
				"sri_doc_code": doc.get("sri_doc_code"),
				"authorization_number": doc.get("authorization_number"),
				"authorization_date": doc.get("authorization_date"),
				"unsigned_xml": read_voucher_xml(doc, "unsigned_xml"),
			}
		)
	return vouchers

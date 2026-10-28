"""SRI ATS Script Report — month detail per document plus section subtotals.

The ATS XML/ZIP itself is built by `ats_reader.generate_ats_files` (pure +
XSD-validated); this report renders the same collected month as DIMM-style
grids so the user sees which documents feed each section before uploading.
"""

try:
	import frappe
	from frappe import _
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

	def _(message: str) -> str:  # type: ignore[no-redef]
		return message


from l10n_ec.sri.ats_layout import build_ats_rows


def execute(filters=None):
	"""Return columns, data for the SRI ATS month grids."""
	columns = [
		{"fieldname": "tercero", "label": _("Counterparty / Section"), "fieldtype": "Data", "width": 340},
		{"fieldname": "comprobante", "label": _("Voucher"), "fieldtype": "Data", "width": 210},
		{"fieldname": "base", "label": _("Taxable base"), "fieldtype": "Float", "width": 130},
		{"fieldname": "iva", "label": _("VAT"), "fieldtype": "Float", "width": 105},
		{"fieldname": "detalle", "label": _("Detail"), "fieldtype": "Data", "width": 255},
	]
	if frappe is None:
		return columns, []
	company = (filters or {}).get("company")
	year = int((filters or {}).get("year") or 0)
	month = int((filters or {}).get("month") or 0)
	if not company or not year or not month:
		return columns, []
	# Only Ecuadorian companies have ATS meaning; keep empty otherwise (contextual).
	company_country = frappe.db.get_value("Company", company, "country")
	country_code = frappe.db.get_value("Country", company_country, "code") if company_country else None
	if country_code and str(country_code).strip().upper() != "EC":
		return columns, []
	from l10n_ec.ecuador_localization.ats_reader import generate_ats_files, read_month
	from l10n_ec.sri.ats_collector import collect_month

	try:
		collected = collect_month(company, year, month, lambda c, y, m: read_month(c, y, m))
		data = build_ats_rows(collected)
	except Exception as exc:  # fail loud in report
		frappe.throw(str(exc))
	subtotals = [r for r in data if r["kind"] == "subtotal"]
	summary = [
		{
			"label": f"{r['seccion']} ({_('base')} / {_('VAT')})",
			"value": f"{r['base'] or 0.0:g} / {r['iva'] if r['iva'] is not None else '—'}",
		}
		for r in subtotals
	]
	return columns, data, None, None, summary, True


def _whitelist():
	"""``frappe.whitelist`` on bench, identity decorator for Ring-1 imports."""
	if frappe is None:  # pragma: no cover
		return lambda fn: fn
	return frappe.whitelist()


@_whitelist()
def download_ats(company: str, year: int, month: int) -> dict:
	"""Generate the ATS XML/ZIP of a month and return private File URLs.

	Desk entry point for the SRI ATS report button: the portal upload is
	the ZIP (it already embeds the XML); the XML URL stays for inspection.
	Files regenerate on every call so the download always matches the
	posted month. Fail loud on non-Ecuadorian companies and bad periods.
	"""
	from l10n_ec.ecuador_localization.ats_reader import generate_ats_files

	company_country = frappe.db.get_value("Company", company, "country")
	country_code = frappe.db.get_value("Country", company_country, "code") if company_country else None
	if country_code and str(country_code).strip().upper() != "EC":
		frappe.throw(_("ATS download needs an Ecuadorian company, found '{}'.").format(company))
	result = generate_ats_files(company, int(year), int(month))
	period = f"{int(month):02d}{int(year)}"
	urls = {}
	for kind, file_name, content in (
		("zip", f"AT{period}.zip", bytes(result["zip"])),
		("xml", f"AT{period}.xml", result["xml"].encode("utf-8")),
	):
		existing = frappe.db.get_value("File", {"file_name": file_name}, "name")
		if existing:
			frappe.delete_doc("File", existing, ignore_permissions=True, force=True)
		file_doc = frappe.get_doc(
			{"doctype": "File", "file_name": file_name, "content": content, "is_private": 1}
		).insert(ignore_permissions=True)
		urls[kind] = file_doc.file_url
	urls["counts"] = result["counts"]
	return urls

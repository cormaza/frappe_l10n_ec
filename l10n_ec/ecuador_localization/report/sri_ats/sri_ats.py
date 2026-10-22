"""SRI ATS Script Report — preview + download trigger (bench path is source of truth).

The ATS XML/ZIP itself is built by `ats_reader.generate_ats_files` (pure + XSD-validated);
this report only surfaces a month preview in Desk and offers the same builder via filters.
"""

try:
	import frappe
	from frappe import _
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

	def _(message: str) -> str:  # type: ignore[no-redef]
		return message

from l10n_ec.sri.ats_builder import build_ats_xml


def execute(filters=None):
	"""Return columns, data for SRI ATS preview; empty when filters incomplete."""
	columns = [
		{"fieldname": "seccion", "label": _("Section"), "fieldtype": "Data", "width": 140},
		{"fieldname": "detalle", "label": _("Detail"), "fieldtype": "Data", "width": 400},
		{"fieldname": "valor", "label": _("Value"), "fieldtype": "Currency", "width": 140},
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
	if company_country and frappe.db.get_value("Country", company_country, "code") != "EC":
		return columns, []
	from l10n_ec.ecuador_localization.ats_reader import generate_ats_files

	try:
		result = generate_ats_files(company, year, month)
	except Exception as exc:  # fail loud in report
		frappe.throw(str(exc))
	# Preview: counts + first XML snippet
	data = [
		{"seccion": "compras", "detalle": f"{result['counts']['compras']} detalleCompras", "valor": result["counts"]["compras"]},
		{"seccion": "ventas", "detalle": f"{result['counts']['ventas']} detalleVentas", "valor": result["counts"]["ventas"]},
		{"seccion": "exportaciones", "detalle": f"{result['counts']['exportaciones']} detalleExportaciones", "valor": result["counts"]["exportaciones"]},
		{"seccion": "anulados", "detalle": f"{result['counts']['anulados']} anulados", "valor": result["counts"]["anulados"]},
	]
	# Also validate XML so report fails loud if builder broke
	build_ats_xml({**result, "informante": {"IdInformante": "0000000000000", "razonSocial": "preview"}}, f"{month:02d}{year}")
	return columns, data

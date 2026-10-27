"""Bench glue for supplier XML reception (desk upload + fetch-by-clave share it).

Pure mapping lives in :mod:`l10n_ec.sri.received_invoice`; this module
only touches the database: resolve the supplier, build the template
catalog, guard duplicates, and insert the draft Purchase Invoice.
Everything user-facing fails loud with English messages; drafts never
post anything by themselves.
"""

try:
	import frappe
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:  # type: ignore[no-redef]
		return message

	frappe = None  # type: ignore[assignment]

from l10n_ec.sri.received_invoice import (
	assemble_purchase_invoice,
	map_received_factura,
	resolve_purchase_templates,
)
from l10n_ec.sri.soap_client import SriSoapClient, process_authorization_response
from l10n_ec.sri.voucher_data import parse_emitted_xml


def _collect_company_templates(company: str) -> list:
	"""Company Item Tax Templates as ``{title, rate, account_root_type}`` rows.

	Rate comes from the template's single tax row; multi-row templates
	are skipped (the matcher needs one rate per template). The root type
	lets the pure matcher keep debit-side (input VAT) templates only.
	"""
	templates = []
	for name in frappe.db.get_list("Item Tax Template", filters={"company": company}, pluck="name"):
		doc = frappe.get_doc("Item Tax Template", name)
		rows = doc.get("taxes") or []
		if len(rows) != 1:
			continue
		account = rows[0].get("tax_type")
		root_type = frappe.db.get_value("Account", account, "root_type") if account else None
		rate = rows[0].get("tax_rate")
		templates.append({"title": name, "rate": rate, "account_root_type": root_type})
	return templates


_IMPORTED_SUPPLIERS_GROUP = "Imported Suppliers"


def _ensure_imported_suppliers_group() -> str:
	"""Leaf group for auto-created suppliers; created once, clearly named."""
	if frappe.db.exists("Supplier Group", _IMPORTED_SUPPLIERS_GROUP):
		return _IMPORTED_SUPPLIERS_GROUP
	if not frappe.db.exists("Supplier Group", "All Supplier Groups"):
		raise ValueError(_("Cannot auto-create the supplier: no 'All Supplier Groups' root exists."))
	group = frappe.get_doc(
		{
			"doctype": "Supplier Group",
			"supplier_group_name": _IMPORTED_SUPPLIERS_GROUP,
			"is_group": 0,
			"parent_supplier_group": "All Supplier Groups",
		}
	)
	group.insert()
	return group.name


def _get_or_create_supplier(tax_id: str, supplier_name: str) -> str:
	"""Resolve the emisor by RUC, creating it on first sight.

	The invoice is going to be booked anyway, so refusing an unknown
	supplier only adds a manual round-trip. Creation is conservative:
	fail loud when the *name* already belongs to another RUC (never
	merge two taxpayers), and flag the new record for review.
	"""
	name = frappe.db.get_value("Supplier", {"tax_id": tax_id}, "name")
	if name:
		return name
	clash = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "tax_id")
	if clash not in (None, "", tax_id):
		raise ValueError(
			_("Supplier name '{}' already exists with a different RUC ({}): resolve it manually.").format(
				supplier_name, clash
			)
		)
	kind = "Company" if len(tax_id) == 13 and tax_id.isdigit() else "Individual"
	doc = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": supplier_name,
			"supplier_group": _ensure_imported_suppliers_group(),
			"supplier_type": kind,
			"tax_id": tax_id,
		}
	)
	doc.insert()
	frappe.msgprint(
		_("Supplier '{}' ({}) was created under '{}': please review its master data.").format(
			supplier_name, tax_id, _IMPORTED_SUPPLIERS_GROUP
		)
	)
	return doc.name


def _create_draft_from_xml(xml_text: str, company: str, item_code: str, sustento: str) -> str:
	"""Shared core: parsed XML (upload or SRI fetch) to draft Purchase Invoice."""
	try:
		parsed = parse_emitted_xml(xml_text)
	except ValueError as exc:
		frappe.throw(str(exc))
		raise
	if (parsed.get("kind") or "") != "factura":
		frappe.throw(
			_("Only supplier facturas can be imported as purchases (got '{}').").format(parsed.get("kind"))
		)
		raise ValueError("unreachable")
	templates = resolve_purchase_templates(_collect_company_templates(company))
	try:
		mapped = map_received_factura(parsed, item_code=item_code, sustento=sustento, templates=templates)
	except ValueError as exc:
		frappe.throw(str(exc))
		raise
	try:
		supplier = _get_or_create_supplier(mapped.pop("supplier_tax_id", ""), mapped.pop("supplier_name", ""))
	except ValueError as exc:
		frappe.throw(str(exc))
		raise
	duplicate = frappe.db.exists("Purchase Invoice", {"supplier": supplier, "bill_no": mapped.get("bill_no")})
	if duplicate:
		frappe.throw(
			_("Supplier invoice '{}' was already imported as {}.").format(mapped.get("bill_no"), duplicate)
		)
		raise ValueError("unreachable")
	doc = frappe.get_doc(assemble_purchase_invoice(mapped, supplier=supplier, company=company))
	doc.insert()
	return doc.name


@frappe.whitelist() if frappe else (lambda fn: fn)
def import_supplier_xml(xml_text: str, company: str, item_code: str, sustento: str) -> str:
	"""Create a draft Purchase Invoice from an uploaded supplier factura XML.

	Thin wrapper over the shared core; the file can be as old as the
	supplier's email allows (no SRI window involved).
	"""
	if frappe is None:  # pragma: no cover
		raise ValueError("Supplier XML import needs a Frappe Bench.")
	return _create_draft_from_xml(xml_text, company, item_code, sustento)


@frappe.whitelist() if frappe else (lambda fn: fn)
def fetch_supplier_xml(
	clave_acceso: str, company: str, item_code: str, sustento: str, environment: str = "production"
) -> str:
	"""Create a draft Purchase Invoice fetching the XML from SRI by clave.

	Same shared core as the upload path once the authorized XML arrives.
	The SRI web service answers recent authorizations only (about ten
	days in practice, no SLA): when it stays silent, upload the file
	instead.
	"""
	if frappe is None:  # pragma: no cover
		raise ValueError("SRI fetch needs a Frappe Bench.")
	key = (clave_acceso or "").strip()
	if not key.isdigit() or len(key) != 49:
		frappe.throw(_("A SRI access key is 49 digits (got '{}').").format(clave_acceso))
		raise ValueError("unreachable")
	client = SriSoapClient(environment=environment or "production")
	try:
		service = client.create_client("authorization")
		raw = SriSoapClient.request_authorization(service, key)
	except Exception as exc:
		frappe.throw(
			_("SRI did not answer the authorization query ({}). Upload the XML file instead.").format(exc)
		)
		raise ValueError("unreachable") from exc
	is_auth, messages, auth_values = process_authorization_response(raw, key)
	if not is_auth:
		detail = "; ".join(messages) if messages else _("not authorized or no longer available")
		frappe.throw(
			_("SRI has no authorized document for that key ({}). Upload the XML file instead.").format(detail)
		)
		raise ValueError("unreachable")
	xml_text = auth_values.get("l10n_ec_xml_comprobante") or ""
	if not xml_text.strip():
		frappe.throw(
			_("SRI confirmed the authorization but returned no document. Upload the XML file instead.")
		)
		raise ValueError("unreachable")
	return _create_draft_from_xml(xml_text, company, item_code, sustento)

"""Customer/Supplier `validate` hooks enforcing SRI tax identification (roadmap Phase 3)."""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.ecuador_localization.validation import (
	is_generic_final_consumer,
	validate_contact_tax_id,
)


def _resolve_country_code(doc) -> str | None:
	"""Resolve the party default address Country to its ISO code, if determinable."""
	if frappe is None:
		return None
	try:
		from frappe.contacts.doctype.address.address import get_default_address
	except ImportError:
		return None
	address_name = get_default_address(doc.doctype, getattr(doc, "name", None))
	if not address_name:
		return None
	country = frappe.db.get_value("Address", address_name, "country")
	if not country:
		return None
	return frappe.db.get_value("Country", country, "code")


def _reject_duplicate_final_consumer(doc) -> None:
	"""There is exactly one generic final consumer across Customers/Suppliers."""
	for doctype in ("Customer", "Supplier"):
		duplicate = frappe.db.exists(
			doctype,
			{"name": ("!=", doc.get("name")), "sri_identification_type": "07"},
		) or frappe.db.exists(
			doctype, {"name": ("!=", doc.get("name")), "tax_id": (doc.get("tax_id") or "").strip()}
		)
		if duplicate:
			frappe.throw(_("{} '{}' is already the generic final consumer.").format(doctype, duplicate))


def _reject_iva_withholding_assignment(doc) -> None:
	"""Parties must never carry uncomputable withholding categories (pure; raises ValueError)."""
	category = doc.get("tax_withholding_category") or ""
	if doc.get("doctype") == "Supplier" and category.startswith("Ecuador IVA "):
		raise ValueError(
			_(
				"IVA withholding categories cannot be assigned to suppliers: ERPNext cannot compute tax-on-tax withholdings. Purchase-side IVA is computed at emission; sales-side IVA settles via the received-withholding entry."
			)
		)
	if doc.get("doctype") == "Customer" and category.startswith("Ecuador "):
		raise ValueError(
			_(
				"Withholding categories cannot be assigned to customers: received withholdings settle via the payment-time entry (invoice stays gross, native rows inflate it and mis-side the liability). Leave the category empty and record the customer conceptos on the invoice."
			)
		)


def validate_sri_identification(doc, method=None) -> None:
	"""Validate the party tax ID for Ecuadorian contacts; skip when not applicable."""
	try:
		_reject_iva_withholding_assignment(doc)
	except ValueError as exc:
		if frappe:
			frappe.throw(str(exc))
		raise
	identification_type = doc.get("sri_identification_type")
	if not identification_type:
		return
	try:
		validate_contact_tax_id(
			_resolve_country_code(doc),
			identification_type,
			doc.get("tax_id"),
		)
	except ValueError as exc:
		if frappe:
			frappe.throw(str(exc))
		raise
	if frappe is not None and is_generic_final_consumer(identification_type, doc.get("tax_id")):
		_reject_duplicate_final_consumer(doc)

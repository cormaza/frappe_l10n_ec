"""Customer/Supplier `validate` hooks enforcing SRI tax identification (roadmap Phase 3)."""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

from l10n_ec.ecuador_localization.validation import validate_contact_tax_id


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


def validate_sri_identification(doc, method=None) -> None:
	"""Validate the party tax ID for Ecuadorian contacts; skip when not applicable."""
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
			frappe.throw(frappe._(str(exc)))
		raise

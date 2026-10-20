"""Sales Invoice `before_save` hooks for SRI invoicing rules (roadmap Phase 6D)."""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

from l10n_ec.ecuador_localization.validation import validate_final_consumer_amount


def validate_sri_invoice(doc, method=None) -> None:
	"""Enforce the Consumidor Final amount threshold on the invoice buyer."""
	if frappe is None:
		return
	customer = doc.get("customer")
	if not customer:
		return
	try:
		validate_final_consumer_amount(
			frappe.db.get_value("Customer", customer, "sri_identification_type"),
			frappe.db.get_value("Customer", customer, "tax_id"),
			doc.get("grand_total"),
		)
	except ValueError as exc:
		frappe.throw(str(exc))

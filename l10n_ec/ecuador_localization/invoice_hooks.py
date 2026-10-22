"""Sales Invoice `before_save` hooks for SRI invoicing rules (roadmap Phase 6D)."""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

from l10n_ec.ecuador_localization.validation import (
	company_country_code,
	is_ecuadorian_contact,
	is_generic_final_consumer,
	validate_final_consumer_amount,
	validate_pos_tickets,
)


def validate_sri_invoice(doc, method=None) -> None:
	"""Enforce the Consumidor Final amount threshold on the invoice buyer."""
	if frappe is None:
		return
	if not is_ecuadorian_contact(company_country_code(doc.get("company"))):
		return
	customer = doc.get("customer")
	if not customer:
		return
	identification_type = frappe.db.get_value("Customer", customer, "sri_identification_type")
	tax_id = frappe.db.get_value("Customer", customer, "tax_id")
	if doc.get("is_consolidated") and is_generic_final_consumer(identification_type, tax_id):
		_validate_consolidated_tickets(doc, identification_type, tax_id)
		return
	try:
		validate_final_consumer_amount(
			identification_type,
			tax_id,
			doc.get("grand_total"),
		)
	except ValueError as exc:
		frappe.throw(str(exc))


def _validate_consolidated_tickets(doc, identification_type, tax_id) -> None:
	"""Check each source POS ticket instead of the consolidated sum.

	The merge total is N valid sales, never one transaction: every ticket
	must clear the threshold on its own. Traceability comes from the
	`consolidated_invoice` backlink each merged ticket carries.
	"""
	try:
		tickets = frappe.get_all(
			"POS Invoice",
			filters={"consolidated_invoice": doc.get("name"), "docstatus": 1},
			pluck="grand_total",
		)
		validate_pos_tickets(identification_type, tax_id, tickets or [])
	except ValueError as exc:
		frappe.throw(str(exc))


def validate_pos_ticket(doc, method=None) -> None:
	"""Enforce the Consumidor Final threshold at POS ticket capture."""
	if frappe is None:
		return
	if not is_ecuadorian_contact(company_country_code(doc.get("company"))):
		return
	customer = doc.get("customer")
	if not customer:
		return
	try:
		validate_pos_tickets(
			frappe.db.get_value("Customer", customer, "sri_identification_type"),
			frappe.db.get_value("Customer", customer, "tax_id"),
			[doc.get("grand_total") or 0.0],
		)
	except ValueError as exc:
		frappe.throw(str(exc))

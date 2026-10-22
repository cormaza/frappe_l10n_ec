"""Sales Invoice `before_save` hooks for SRI invoicing rules (roadmap Phase 6D)."""

try:
	import frappe
	from frappe import _
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

	def _(message: str) -> str:  # type: ignore[no-redef]
		return message


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
	"""Enforce the Consumidor Final threshold at POS ticket capture.

	Also stamps the fiscal identity of the sale: the emission point comes
	from the POS Profile (one profile, one caja) and the session from the
	cashier's open POS Opening Entry. Both fail loud when missing on an
	Ecuadorian sale instead of drifting into the wrong sequence.
	"""
	if frappe is None:
		return
	if not is_ecuadorian_contact(company_country_code(doc.get("company"))):
		return
	_resolve_ticket_emission(doc)
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


def _resolve_ticket_emission(doc) -> None:
	"""Inherit the emission point from the profile; stamp the session."""
	profile = doc.get("pos_profile")
	if not profile:
		return
	point = frappe.db.get_value("POS Profile", profile, "sri_emission_point")
	if not point:
		frappe.throw(_("POS Profile '{}' needs an SRI Emission Point before selling.").format(profile))
	if not frappe.db.get_value("SRI Emission Point", point, "pos_only"):
		frappe.throw(
			_("Emission point '{}' is not POS-only; POS tickets need a locked POS point.").format(point)
		)
	ensure_ticket_point(doc.get("sri_emission_point"), point, doc.get("name") or _("(new ticket)"))
	doc.sri_emission_point = point
	opening = frappe.db.get_value(
		"POS Opening Entry",
		{"pos_profile": profile, "status": "Open", "docstatus": 1},
		"name",
	)
	if not opening:
		frappe.throw(
			_("No open POS Opening Entry for profile '{}'; open the cashier session before selling.").format(
				profile
			)
		)
	doc.pos_opening_entry = opening


def ensure_ticket_point(current: str | None, expected: str, ticket: str) -> None:
	"""Fail loud when a POS document points at another emission point (pure)."""
	if current and current != expected:
		raise ValueError(
			_("Document '{}' points at '{}', but its profile emits from '{}'.").format(
				ticket, current, expected
			)
		)


def inherit_pos_point_invoice(doc, method=None) -> None:
	"""Stamp counter sales (POS Sales Invoice mode) with the profile point.

	POS Invoice mode is covered at the ticket; this covers the sibling mode
	where each sale is a Sales Invoice carrying `pos_profile` (auto-resolved
	by the core). Desk invoices never carry a profile and skip silently.
	"""
	if frappe is None:
		return
	if not doc.get("is_pos") or doc.get("is_consolidated"):
		return
	if not is_ecuadorian_contact(company_country_code(doc.get("company"))):
		return
	profile = doc.get("pos_profile")
	if not profile:
		return
	point = frappe.db.get_value("POS Profile", profile, "sri_emission_point")
	if not point:
		frappe.throw(_("POS Profile '{}' needs an SRI Emission Point before selling.").format(profile))
	ensure_ticket_point(doc.get("sri_emission_point"), point, doc.get("name") or _("(new invoice)"))
	doc.sri_emission_point = point

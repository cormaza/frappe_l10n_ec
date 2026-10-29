"""Quotation/Sales Order hooks for e-commerce shop sales (roadmap Phase P2).

The shop is a logical caja: Webshop Settings carries one SRI Emission Point
and every cart document inherits it down the chain
(Quotation → Sales Order → Sales Invoice). Contact identity is enforced
before payment (order submit), not at invoicing time. Everything degrades
to a no-op when the Webshop app is not installed.
"""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:  # type: ignore[no-redef]
		return message


from l10n_ec.ecuador_localization.validation import (
	company_country_code,
	is_ecuadorian_contact,
	validate_final_consumer_amount,
)

#: Webshop cart marker (`shopping_cart/cart.py:_get_cart_quotation`).
SHOP_CART_ORDER_TYPE = "Shopping Cart"


def _shop_point(company: str | None) -> str | None:
	"""Emission point bound to the shop, or None when unresolvable."""
	if frappe is None or not company:
		return None
	if not frappe.db.exists("DocType", "Webshop Settings"):
		return None
	settings_company = frappe.db.get_single_value("Webshop Settings", "company")
	if settings_company and settings_company != company:
		raise ValueError(_("Shop belongs to '{}', cannot sell for '{}'.").format(settings_company, company))
	return frappe.db.get_single_value("Webshop Settings", "sri_emission_point")


def ensure_shop_point(current: str | None, expected: str, doc: str) -> None:
	"""Fail loud when a shop document points at another emission point (pure)."""
	if current and current != expected:
		raise ValueError(
			_("Document '{}' points at '{}', but the shop emits from '{}'.").format(doc, current, expected)
		)


def inherit_shop_point_quotation(doc, method=None) -> None:
	"""Stamp cart quotations (including quotation-only RFQ flow) with the shop point."""
	if frappe is None:
		return
	if doc.get("order_type") != SHOP_CART_ORDER_TYPE:
		return
	if not is_ecuadorian_contact(company_country_code(doc.get("company"))):
		return
	if not frappe.db.exists("DocType", "Webshop Settings"):
		return
	try:
		point = _shop_point(doc.get("company"))
	except ValueError as exc:
		frappe.throw(str(exc))
	if not point:
		frappe.throw(_("Webshop Settings needs an SRI Emission Point before selling."))
	try:
		ensure_shop_point(doc.get("sri_emission_point"), point, doc.get("name") or _("(new quotation)"))
	except ValueError as exc:
		frappe.throw(str(exc))
	doc.sri_emission_point = point


def _shop_customer(doc) -> tuple:
	"""(identification_type, tax_id) of the order buyer; Lead reads as generic CF."""
	if doc.get("quotation_to") == "Customer" or doc.get("customer"):
		customer = doc.get("customer") or doc.get("party_name")
		return (
			frappe.db.get_value("Customer", customer, "sri_identification_type"),
			frappe.db.get_value("Customer", customer, "tax_id"),
		)
	return ("07", "9999999999999")


def check_shop_contact(doc, method=None) -> None:
	"""Anticipate the CF ceiling before payment: unidentified buyers stop here."""
	if frappe is None:
		return
	if doc.get("order_type") != SHOP_CART_ORDER_TYPE and not doc.get("sri_emission_point"):
		return
	if not is_ecuadorian_contact(company_country_code(doc.get("company"))):
		return
	identification_type, tax_id = _shop_customer(doc)
	try:
		validate_final_consumer_amount(
			identification_type,
			tax_id,
			doc.get("base_grand_total")
			if doc.get("base_grand_total") is not None
			else doc.get("grand_total"),
		)
	except ValueError as exc:
		frappe.throw(str(exc))


def inherit_shop_point_order(doc, method=None) -> None:
	"""Stamp sales orders from their shop quotation; shop contact rule is separate."""
	if frappe is None:
		return
	source = None
	for item in doc.get("items") or []:
		if item.get("prevdoc_doctype") == "Quotation" and item.get("prevdoc_docname"):
			source = item.get("prevdoc_docname")
			break
	if not source:
		return
	point = frappe.db.get_value("Quotation", source, "sri_emission_point")
	if not point:
		return
	try:
		ensure_shop_point(doc.get("sri_emission_point"), point, doc.get("name") or _("(new order)"))
	except ValueError as exc:
		frappe.throw(str(exc))
	doc.sri_emission_point = point


def inherit_shop_point_invoice(doc, method=None) -> None:
	"""Stamp shop invoices from their sales order so emission finds the channel."""
	if frappe is None:
		return
	if doc.get("sri_emission_point"):
		return
	for item in doc.get("items") or []:
		order = item.get("sales_order")
		if not order:
			continue
		point = frappe.db.get_value("Sales Order", order, "sri_emission_point")
		if point:
			doc.sri_emission_point = point
			return

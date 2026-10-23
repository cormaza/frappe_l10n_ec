"""App lifecycle wiring for install, migrate, and uninstall (roadmap Phase 3)."""

from l10n_ec.ecuador_localization.custom_fields import (
	create_sri_custom_fields,
	delete_sri_custom_fields,
)

# (doctype, section-break fieldname) pairs whose taxes section collapses.
# The collapsible goes on the *labeled* parent (taxes_section): the grid
# lives in the unlabeled separator below it and follows the parent.
COLLAPSIBLE_TAX_SECTIONS = (
	("Sales Invoice", "taxes_section"),
	("Purchase Invoice", "taxes_section"),
)


def setup_collapsible_tax_sections() -> None:
	"""Make the core taxes grids collapsible (desk URLs stay untouched)."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		raise RuntimeError("frappe is required to set collapsible sections.")
	for doctype, fieldname in COLLAPSIBLE_TAX_SECTIONS:
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"fieldname": fieldname,
				"property": "collapsible",
				"value": 1,
				"property_type": "Check",
			}
		)


# (child table doctype, fieldname, grid width units) — the account head
# carries long ledger names, so it gets double room from charge/rate.
TAX_GRID_COLUMN_WIDTHS = (
	("Sales Taxes and Charges", "charge_type", 1),
	("Sales Taxes and Charges", "account_head", 4),
	("Sales Taxes and Charges", "rate", 1),
	("Sales Taxes and Charges", "tax_amount", 2),
	("Sales Taxes and Charges", "total", 2),
	("Sales Taxes and Charges", "net_amount", 2),
	("Purchase Taxes and Charges", "charge_type", 1),
	("Purchase Taxes and Charges", "account_head", 4),
	("Purchase Taxes and Charges", "rate", 1),
	("Purchase Taxes and Charges", "tax_amount", 2),
	("Purchase Taxes and Charges", "total", 2),
	("Purchase Taxes and Charges", "net_amount", 2),
)


def setup_tax_grid_widths() -> None:
	"""Give the ledger-name column room in the taxes grids."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		raise RuntimeError("frappe is required to set grid widths.")
	for doctype, fieldname, width in TAX_GRID_COLUMN_WIDTHS:
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"fieldname": fieldname,
				"property": "columns",
				"value": width,
				"property_type": "Int",
			}
		)


def remove_tax_grid_widths() -> None:
	"""Remove exactly the grid-width setters owned by this app."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		raise RuntimeError("frappe is required to remove grid widths.")
	for doctype, fieldname, _width in TAX_GRID_COLUMN_WIDTHS:
		frappe.db.delete(
			"Property Setter",
			{"doc_type": doctype, "field_name": fieldname, "property": "columns"},
		)


def after_install() -> None:
	create_sri_custom_fields()
	setup_collapsible_tax_sections()
	setup_tax_grid_widths()


def after_migrate() -> None:
	create_sri_custom_fields()
	setup_collapsible_tax_sections()
	setup_tax_grid_widths()


def before_uninstall() -> None:
	delete_sri_custom_fields()
	remove_collapsible_tax_sections()
	remove_tax_grid_widths()


def remove_collapsible_tax_sections() -> None:
	"""Remove exactly the property setters owned by this app."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		raise RuntimeError("frappe is required to remove collapsible sections.")
	for doctype, fieldname in COLLAPSIBLE_TAX_SECTIONS:
		frappe.db.delete(
			"Property Setter",
			{"doc_type": doctype, "field_name": fieldname},
		)

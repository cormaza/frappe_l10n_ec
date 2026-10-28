"""App lifecycle wiring for install, migrate, and uninstall (roadmap Phase 3)."""

from l10n_ec.ecuador_localization.custom_fields import (
	create_sri_custom_fields,
	delete_sri_custom_fields,
	prune_retired_sri_custom_fields,
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
	("Sales Taxes and Charges", "account_head", 3),
	("Sales Taxes and Charges", "description", 2),
	("Sales Taxes and Charges", "rate", 1),
	("Sales Taxes and Charges", "tax_amount", 2),
	("Sales Taxes and Charges", "total", 2),
	("Sales Taxes and Charges", "net_amount", 1),
	("Purchase Taxes and Charges", "charge_type", 1),
	("Purchase Taxes and Charges", "account_head", 3),
	("Purchase Taxes and Charges", "description", 2),
	("Purchase Taxes and Charges", "rate", 1),
	("Purchase Taxes and Charges", "tax_amount", 2),
	("Purchase Taxes and Charges", "total", 2),
	("Purchase Taxes and Charges", "net_amount", 1),
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


# Child-table fields shown in the taxes grids. `description` carries the short
# SRI labels (`Ret. IR 2%`, `IVA Pagado 15%`) that `sync_tax_row_descriptions`
# writes on every validate; without list-view it stays hidden and the operator
# only sees the truncated ledger names.
TAX_GRID_LIST_VIEW = (
	("Sales Taxes and Charges", "description"),
	("Purchase Taxes and Charges", "description"),
)


def setup_tax_grid_list_view() -> None:
	"""Show the short SRI description column in the taxes grids."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		raise RuntimeError("frappe is required to set grid list view.")
	for doctype, fieldname in TAX_GRID_LIST_VIEW:
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"fieldname": fieldname,
				"property": "in_list_view",
				"value": 1,
				"property_type": "Check",
			}
		)


def remove_tax_grid_list_view() -> None:
	"""Remove exactly the grid list-view setters owned by this app."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		raise RuntimeError("frappe is required to remove grid list view.")
	for doctype, fieldname in TAX_GRID_LIST_VIEW:
		frappe.db.delete(
			"Property Setter",
			{"doc_type": doctype, "field_name": fieldname, "property": "in_list_view"},
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
	setup_tax_grid_list_view()


def after_migrate() -> None:
	create_sri_custom_fields()
	prune_retired_sri_custom_fields()
	setup_collapsible_tax_sections()
	setup_tax_grid_widths()
	setup_tax_grid_list_view()
	_sync_existing_charts()


def _sync_existing_charts() -> None:
	"""Additive chart sync for pre-existing EC companies (bench only)."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		return
	from l10n_ec.ecuador_localization.chart_setup import sync_missing_chart_accounts

	for name in frappe.get_all("Company", pluck="name"):
		sync_missing_chart_accounts(name)


def before_uninstall() -> None:
	delete_sri_custom_fields()
	remove_collapsible_tax_sections()
	remove_tax_grid_widths()
	remove_tax_grid_list_view()


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

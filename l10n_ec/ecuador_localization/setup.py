"""App lifecycle wiring for install, migrate, and uninstall (roadmap Phase 3)."""

from l10n_ec.ecuador_localization.custom_fields import (
	create_sri_custom_fields,
	delete_sri_custom_fields,
)

# (doctype, section-break fieldname, grid label) triads. The taxes grid
# lives in the *unlabeled* separator break (headless sections can't show a
# chevron), so the label travels with the collapsible flag.
COLLAPSIBLE_TAX_SECTIONS = (
	("Sales Invoice", "section_break_40", "Tax details"),
	("Purchase Invoice", "section_break_51", "Tax details"),
)


def setup_collapsible_tax_sections() -> None:
	"""Make the core taxes grids collapsible (desk URLs stay untouched)."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		raise RuntimeError("frappe is required to set collapsible sections.")
	for doctype, fieldname, label in COLLAPSIBLE_TAX_SECTIONS:
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"fieldname": fieldname,
				"property": "collapsible",
				"value": 1,
				"property_type": "Check",
			}
		)
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"fieldname": fieldname,
				"property": "label",
				"value": label,
				"property_type": "Data",
			}
		)


def after_install() -> None:
	create_sri_custom_fields()
	setup_collapsible_tax_sections()


def after_migrate() -> None:
	create_sri_custom_fields()
	setup_collapsible_tax_sections()


def before_uninstall() -> None:
	delete_sri_custom_fields()
	remove_collapsible_tax_sections()


def remove_collapsible_tax_sections() -> None:
	"""Remove exactly the property setters owned by this app."""
	try:
		import frappe
	except ImportError:  # pragma: no cover
		raise RuntimeError("frappe is required to remove collapsible sections.")
	for doctype, fieldname, _label in COLLAPSIBLE_TAX_SECTIONS:
		frappe.db.delete(
			"Property Setter",
			{"doc_type": doctype, "field_name": fieldname},
		)

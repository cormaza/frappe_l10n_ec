"""Programmatic custom fields for Company, Customer, and Supplier (roadmap Phase 3)."""

try:
	import frappe
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	create_custom_fields = None  # type: ignore[assignment]

CUSTOM_FIELDS = {
	"Company": [
		{
			"depends_on": "eval:doc.country=='Ecuador'",
			"default": "Test",
			"fieldname": "sri_environment",
			"fieldtype": "Select",
			"insert_after": "country",
			"label": "SRI Environment",
			"options": "Test\nProduction",
		},
		{
			"depends_on": "eval:doc.country=='Ecuador'",
			"fieldname": "sri_signature",
			"fieldtype": "Link",
			"insert_after": "sri_environment",
			"label": "SRI Signature",
			"options": "SRI Signature",
		},
		{
			"depends_on": "eval:doc.country=='Ecuador'",
			"fieldname": "special_taxpayer_resolution",
			"fieldtype": "Data",
			"insert_after": "sri_signature",
			"label": "Special Taxpayer Resolution",
		},
		{
			"depends_on": "eval:doc.country=='Ecuador'",
			"fieldname": "withholding_agent_resolution",
			"fieldtype": "Data",
			"insert_after": "special_taxpayer_resolution",
			"label": "Withholding Agent Resolution",
		},
		{
			"depends_on": "eval:doc.country=='Ecuador'",
			"fieldname": "rimpe_regime",
			"fieldtype": "Select",
			"insert_after": "withholding_agent_resolution",
			"label": "RIMPE Regime",
			"options": "\nPopular Business\nEntrepreneur",
		},
		{
			"depends_on": "eval:doc.country=='Ecuador'",
			"default": "0",
			"fieldname": "accounting_required",
			"fieldtype": "Check",
			"insert_after": "rimpe_regime",
			"label": "Accounting Required",
		},
	],
	"Customer": [
		{
			"fieldname": "sri_identification_type",
			"fieldtype": "Link",
			"insert_after": "tax_id",
			"label": "SRI Identification Type",
			"options": "SRI Identification Type",
		},
		{
			"default": "0",
			"fieldname": "sri_related_party",
			"fieldtype": "Check",
			"insert_after": "sri_identification_type",
			"label": "Related Party",
		},
	],
	"Supplier": [
		{
			"fieldname": "sri_identification_type",
			"fieldtype": "Link",
			"insert_after": "tax_id",
			"label": "SRI Identification Type",
			"options": "SRI Identification Type",
		},
		{
			"default": "0",
			"fieldname": "sri_related_party",
			"fieldtype": "Check",
			"insert_after": "sri_identification_type",
			"label": "Related Party",
		},
	],
}


def create_sri_custom_fields() -> None:
	"""Create or update SRI custom fields idempotently (safe on re-migrate)."""
	if create_custom_fields is None:  # pragma: no cover
		raise RuntimeError("frappe is required to create custom fields.")
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)


def delete_sri_custom_fields() -> None:
	"""Remove exactly the custom fields owned by this app (uninstall path)."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to delete custom fields.")
	for doctype, fields in CUSTOM_FIELDS.items():
		frappe.db.delete(
			"Custom Field",
			{"dt": doctype, "fieldname": ("in", [f["fieldname"] for f in fields])},
		)

"""Programmatic custom fields for Company, Customer, Supplier, Mode of Payment, and Purchase Invoice."""

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
	"Sales Invoice": [
		{
			"fieldname": "sri_info_adicional",
			"fieldtype": "Table",
			"insert_after": "taxes_and_charges",
			"label": "SRI Additional Information",
			"options": "SRI Additional Information Entry",
			"description": "Per-document infoAdicional rows for the voucher (transactional rows win over central ones).",
		},
		{
			"fieldname": "sri_ir_concepto",
			"fieldtype": "Data",
			"insert_after": "taxes_and_charges",
			"label": "SRI IR Concepto",
			"description": "SRI IR withholding concepto withheld by the customer (e.g. 303, 312), validated against the concepto table; feeds the received-withholding settlement entry; leave empty when no IR withholding applies.",
		},
		{
			"fieldname": "sri_iva_concepto",
			"fieldtype": "Select",
			"insert_after": "taxes_and_charges",
			"label": "SRI IVA Concepto",
			"default": "",
			"options": "\n1\n2\n3\n7\n8\n9\n10\n11",
			"description": "SRI Tabla 23 IVA withholding concepto withheld by the customer; feeds the received-withholding settlement entry (1 bienes 30%, 2 servicios 70%, 3 honorarios 100%); leave empty when no IVA withholding applies.",
		},
		{
			"fieldname": "sri_received_retencion_number",
			"fieldtype": "Data",
			"insert_after": "sri_iva_concepto",
			"label": "Received Retencion Number",
			"description": "Number of the Comprobante de Retencion issued by the customer (e.g. 001-001-000000001); feeds ATS and Form 103 as tax credit.",
		},
		{
			"fieldname": "sri_received_retencion_auth",
			"fieldtype": "Data",
			"insert_after": "sri_received_retencion_number",
			"label": "Received Retencion Authorization",
			"description": "SRI authorization number of the customer-issued withholding voucher.",
		},
		{
			"fieldname": "sri_received_retencion_date",
			"fieldtype": "Date",
			"insert_after": "sri_received_retencion_auth",
			"label": "Received Retencion Date",
			"description": "Issue date of the customer-issued withholding voucher.",
		},
		{
			"fieldname": "sri_received_retencion_key",
			"fieldtype": "Data",
			"insert_after": "sri_received_retencion_date",
			"label": "Received Retencion Access Key",
			"description": "49-digit access key of the customer-issued withholding voucher.",
		},
	],
	"Quotation": [
		{
			"fieldname": "sri_info_adicional",
			"fieldtype": "Table",
			"insert_after": "taxes_and_charges",
			"label": "SRI Additional Information",
			"options": "SRI Additional Information Entry",
			"description": "Per-document infoAdicional rows; flow into order and invoice, then the voucher (transactional rows win over central ones).",
		},
	],
	"Sales Order": [
		{
			"fieldname": "sri_info_adicional",
			"fieldtype": "Table",
			"insert_after": "taxes_and_charges",
			"label": "SRI Additional Information",
			"options": "SRI Additional Information Entry",
			"description": "Per-document infoAdicional rows; flow into the invoice, then the voucher (transactional rows win over central ones).",
		},
	],
	"Purchase Invoice": [
		{
			"fieldname": "sri_is_liquidacion",
			"fieldtype": "Check",
			"insert_after": "bill_no",
			"label": "SRI Liquidacion",
			"description": "This purchase has no supplier invoice: we emit the Liquidacion de Compra (03). Drives voucher emission and ATS classification.",
		},
		{
			"fieldname": "sri_is_supplier_debit_note",
			"fieldtype": "Check",
			"insert_after": "sri_is_liquidacion",
			"label": "SRI Supplier Debit Note",
			"description": "This supplier document is a Nota de Debito (ATS classification only; their emission, no voucher from us).",
		},
		{
			"fieldname": "sri_supplier_auth_number",
			"fieldtype": "Data",
			"insert_after": "bill_no",
			"label": "Supplier Auth Number",
			"description": "SRI authorization number printed on the supplier invoice; feeds ATS compras.",
		},
		{
			"fieldname": "sri_iva_concepto",
			"fieldtype": "Select",
			"insert_after": "taxes_and_charges",
			"label": "SRI IVA Concepto",
			"default": "",
			"options": "\n1\n2\n3\n7\n8\n9\n10\n11",
			"description": "SRI Tabla 23 IVA withholding concepto driving the automatic deduction row and the voucher (1 bienes 30%, 2 servicios 70%, 3 honorarios 100%); leave empty when no IVA withholding applies.",
		},
	],
	"Mode of Payment": [
		{
			"default": "01",
			"fieldname": "sri_payment_code",
			"fieldtype": "Select",
			"insert_after": "mode_of_payment",
			"label": "SRI Payment Code",
			"options": "01\n15\n16\n17\n18\n19\n20\n21",
			"description": "SRI Tabla 24 payment code. Forward-placed mapping point POS and ATS readers will use in Phase 9A; vouchers still emit the default until wired.",
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

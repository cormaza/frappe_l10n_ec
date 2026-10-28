"""Programmatic custom fields for Company, Customer, Supplier, Mode of Payment, Purchase Invoice, POS Profile, and POS Invoice."""

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
		{
			"default": "0",
			"fieldname": "sri_skip_id_validation",
			"fieldtype": "Check",
			"insert_after": "sri_related_party",
			"label": "Skip SRI ID Validation",
			"description": "The SRI issues RUCs without check-digit validation; set this only with the number verified at the SRI portal, to unblock a real taxpayer the checksum rejects.",
		},
	],
	"Sales Invoice": [
		{
			"fieldname": "sri_section",
			"fieldtype": "Section Break",
			"insert_after": "sec_tax_breakup",
			"label": "SRI Invoicing",
			"collapsible": 1,
			"description": "Ecuadorian SRI data: withholdings, received slips and emission point.",
		},
		{
			"fieldname": "sri_section_2",
			"fieldtype": "Section Break",
			"insert_after": "sri_received_retencion_key",
		},
		{
			"fieldname": "sri_info_adicional",
			"fieldtype": "Table",
			"insert_after": "sri_section_2",
			"label": "SRI Additional Information",
			"options": "SRI Additional Information Entry",
			"description": "Per-document infoAdicional rows for the voucher (transactional rows win over central ones).",
		},
		{
			"fieldname": "sri_col_break_2",
			"fieldtype": "Column Break",
			"insert_after": "sri_received_retencion_date",
		},
		{
			"fieldname": "sri_ir_concepto",
			"fieldtype": "Data",
			"insert_after": "sri_section",
			"label": "SRI IR Concepto",
			"description": "SRI IR withholding concepto withheld by the customer (e.g. 303, 312), validated against the concepto table; feeds the received-withholding settlement entry; leave empty when no IR withholding applies.",
		},
		{
			"fieldname": "sri_iva_concepto",
			"fieldtype": "Select",
			"insert_after": "sri_col_break_2",
			"label": "SRI IVA Concepto",
			"default": "",
			"options": "\n1 - Bienes 30%\n2 - Servicios 70%\n3 - Honorarios 100%\n7 - Retención cero\n8 - No procede\n9 - Especial 10%\n10 - Especial 20%\n11 - Especial 50%",
			"description": "SRI Tabla 23 IVA withholding concepto withheld by the customer; feeds the received-withholding settlement entry (1 bienes 30%, 2 servicios 70%, 3 honorarios 100%); leave empty when no IVA withholding applies.",
		},
		{
			"fieldname": "sri_section_reimbursement",
			"fieldtype": "Section Break",
			"insert_after": "sri_iva_concepto",
			"label": "SRI Reimbursement",
		},
		{
			"fieldname": "sri_is_reimbursement",
			"fieldtype": "Check",
			"insert_after": "sri_section_reimbursement",
			"label": "SRI Is Reimbursement",
			"default": "0",
			"description": "Reimbursement voucher (41 received as mandante, 41 emitted as intermediary); drives sustento cross-check and ATS reembolsos.",
		},
		{
			"fieldname": "sri_reimbursement_details",
			"fieldtype": "Table",
			"insert_after": "sri_is_reimbursement",
			"label": "SRI Reimbursement Details",
			"options": "SRI Reimbursement Detail",
			"description": "Reimbursed vouchers behind this invoice; sums into totbasesImpReemb.",
		},
		{
			"fieldname": "sri_reimbursement_total",
			"fieldtype": "Currency",
			"insert_after": "sri_reimbursement_details",
			"label": "SRI Reimbursement Total",
			"read_only": 1,
			"description": "Calculated totbasesImpReemb from reimbursement details.",
		},
		{
			"fieldname": "sri_col_break_reimb_total",
			"fieldtype": "Column Break",
			"insert_after": "sri_reimbursement_total",
		},
		{
			"fieldname": "sri_allow_reimbursement_override",
			"fieldtype": "Check",
			"insert_after": "sri_col_break_reimb_total",
			"label": "Allow Reimbursement Override",
			"default": "0",
			"description": "Opt-in to force a manual reimbursement total instead of the calculated one.",
		},
		{
			"fieldname": "sri_reimbursement_override_value",
			"fieldtype": "Currency",
			"insert_after": "sri_allow_reimbursement_override",
			"label": "SRI Reimbursement Override",
			"description": "Manual totbasesImpReemb; needs the override opt-in.",
		},
		{
			"fieldname": "sri_received_retencion_number",
			"fieldtype": "Data",
			"insert_after": "sri_ir_concepto",
			"label": "Received Retencion Number",
			"description": "Number of the Comprobante de Retencion issued by the customer (e.g. 001-001-000000001); feeds ATS and Form 103 as tax credit.",
		},
		{
			"fieldname": "sri_received_retencion_auth",
			"fieldtype": "Data",
			"insert_after": "sri_iva_concepto",
			"label": "Received Retencion Authorization",
			"description": "SRI authorization number of the customer-issued withholding voucher.",
		},
		{
			"fieldname": "sri_received_retencion_date",
			"fieldtype": "Date",
			"insert_after": "sri_received_retencion_number",
			"label": "Received Retencion Date",
			"description": "Issue date of the customer-issued withholding voucher.",
		},
		{
			"fieldname": "sri_received_retencion_key",
			"fieldtype": "Data",
			"insert_after": "sri_received_retencion_auth",
			"label": "Received Retencion Access Key",
			"description": "49-digit access key of the customer-issued withholding voucher.",
		},
		{
			"fieldname": "sri_emission_point",
			"fieldtype": "Link",
			"insert_after": "pos_profile",
			"label": "SRI Emission Point",
			"options": "SRI Emission Point",
			"read_only": 1,
			"description": "Inherited from the POS Profile for counter sales; drives POS voucher emission.",
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
		{
			"fieldname": "sri_emission_point",
			"fieldtype": "Link",
			"insert_after": "company",
			"label": "SRI Emission Point",
			"options": "SRI Emission Point",
			"read_only": 1,
			"description": "Inherited from Webshop Settings for cart quotations (including quotation-only RFQ flow).",
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
		{
			"fieldname": "sri_emission_point",
			"fieldtype": "Link",
			"insert_after": "company",
			"label": "SRI Emission Point",
			"options": "SRI Emission Point",
			"read_only": 1,
			"description": "Inherited from the shop quotation; drives shop voucher emission.",
		},
	],
	"Purchase Invoice": [
		{
			"fieldname": "sri_sustento_code",
			"fieldtype": "Select",
			"insert_after": "bill_no",
			"label": "SRI Sustento Code",
			"default": "02 - Sin crédito tributario",
			"options": "01 - Con crédito tributario\n02 - Sin crédito tributario\n03 - Activos fijos con crédito\n04 - Activos fijos sin crédito\n05 - Gastos de viaje\n06 - Inventario con crédito\n07 - Inventario sin crédito\n08 - Reembolso (intermediario)\n09 - Gastos médicos\n10 - Dividendos\n11 - Débito bancario\n12 - Editores/combustibles\n13 - Sector público\n14 - Transporte (socios)\n15 - Servicios digitales",
			"description": "SRI Tabla 5 sustento for ATS (01 credit goods, 02 no-credit, 03/04 fixed assets, 06/07 inventory...); drives ATS classification.",
		},
		{
			"fieldname": "sri_is_liquidacion",
			"fieldtype": "Check",
			"insert_after": "sri_sustento_code",
			"label": "SRI Liquidacion",
			"description": "No supplier invoice: we emit the Liquidacion de Compra (03).",
		},
		{
			"fieldname": "sri_col_break_supplier",
			"fieldtype": "Column Break",
			"insert_after": "sri_is_liquidacion",
		},
		{
			"fieldname": "sri_supplier_auth_number",
			"fieldtype": "Data",
			"insert_after": "sri_col_break_supplier",
			"label": "Supplier Auth Number",
			"description": "SRI authorization number printed on the supplier invoice; feeds ATS compras.",
		},
		{
			"fieldname": "sri_is_supplier_debit_note",
			"fieldtype": "Check",
			"insert_after": "sri_supplier_auth_number",
			"label": "SRI Supplier Debit Note",
			"description": "Supplier Nota de Debito: ATS classification only, no voucher from us.",
		},
		{
			"fieldname": "sri_assumed_withholding",
			"fieldtype": "Check",
			"insert_after": "taxes_and_charges",
			"label": "SRI Assumed Withholding",
			"default": "0",
			"description": "The agent absorbs the withholding: payable intact, withheld total to non-deductible expense (520230).",
		},
		{
			"fieldname": "sri_col_break_taxes",
			"fieldtype": "Column Break",
			"insert_after": "sri_assumed_withholding",
		},
		{
			"fieldname": "sri_iva_concepto",
			"fieldtype": "Select",
			"insert_after": "sri_col_break_taxes",
			"label": "SRI IVA Concepto",
			"default": "",
			"options": "\n1 - Bienes 30%\n2 - Servicios 70%\n3 - Honorarios 100%\n7 - Retención cero\n8 - No procede\n9 - Especial 10%\n10 - Especial 20%\n11 - Especial 50%",
			"description": "SRI Tabla 23 IVA withholding concepto driving the automatic deduction row and the voucher (1 bienes 30%, 2 servicios 70%, 3 honorarios 100%); leave empty when no IVA withholding applies.",
		},
		{
			"fieldname": "sri_section_reimbursement",
			"fieldtype": "Section Break",
			"insert_after": "sri_iva_concepto",
			"label": "SRI Reimbursement",
		},
		{
			"fieldname": "sri_is_reimbursement",
			"fieldtype": "Check",
			"insert_after": "sri_section_reimbursement",
			"label": "SRI Is Reimbursement",
			"default": "0",
			"description": "Reimbursement purchase (41 received as mandante); drives sustento cross-check and ATS reembolsos.",
		},
		{
			"fieldname": "sri_reimbursement_details",
			"fieldtype": "Table",
			"insert_after": "sri_is_reimbursement",
			"label": "SRI Reimbursement Details",
			"options": "SRI Reimbursement Detail",
			"description": "Reimbursed vouchers behind this purchase; sums into totbasesImpReemb.",
		},
		{
			"fieldname": "sri_reimbursement_total",
			"fieldtype": "Currency",
			"insert_after": "sri_reimbursement_details",
			"label": "SRI Reimbursement Total",
			"read_only": 1,
			"description": "Calculated totbasesImpReemb from reimbursement details.",
		},
		{
			"fieldname": "sri_col_break_reimb_total",
			"fieldtype": "Column Break",
			"insert_after": "sri_reimbursement_total",
		},
		{
			"fieldname": "sri_allow_reimbursement_override",
			"fieldtype": "Check",
			"insert_after": "sri_col_break_reimb_total",
			"label": "Allow Reimbursement Override",
			"default": "0",
			"description": "Opt-in to force a manual reimbursement total instead of the calculated one.",
		},
		{
			"fieldname": "sri_reimbursement_override_value",
			"fieldtype": "Currency",
			"insert_after": "sri_allow_reimbursement_override",
			"label": "SRI Reimbursement Override",
			"description": "Manual totbasesImpReemb; needs the override opt-in.",
		},
	],
	"Payment Entry": [
		{
			"fieldname": "sri_received_withholding",
			"fieldtype": "Link",
			"insert_after": "reference_no",
			"label": "SRI Received Withholding",
			"options": "SRI Received Withholding",
			"description": "Customer-side batch: one slip covering many invoices. When linked, its allocations settle on submit instead of per-invoice fields.",
		},
	],
	"Mode of Payment": [
		{
			"default": "01 - Sin utilización del sistema financiero",
			"fieldname": "sri_payment_code",
			"fieldtype": "Select",
			"insert_after": "mode_of_payment",
			"label": "SRI Payment Code",
			"options": "01 - Sin utilización del sistema financiero\n15 - Compensación de deudas\n16 - Tarjeta de débito\n17 - Dinero electrónico\n18 - Tarjeta prepago\n19 - Tarjeta de crédito\n20 - Otros con utilización del sistema financiero\n21 - Endoso de títulos",
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
		{
			"default": "0",
			"fieldname": "sri_skip_id_validation",
			"fieldtype": "Check",
			"insert_after": "sri_related_party",
			"label": "Skip SRI ID Validation",
			"description": "The SRI issues RUCs without check-digit validation; set this only with the number verified at the SRI portal, to unblock a real taxpayer the checksum rejects.",
		},
	],
	"POS Profile": [
		{
			"fieldname": "sri_emission_point",
			"fieldtype": "Link",
			"insert_after": "warehouse",
			"label": "SRI Emission Point",
			"options": "SRI Emission Point",
			"description": "Caja fiscal: every ticket sold under this profile consumes sequential numbers from this point. One profile, one point.",
		},
	],
	"POS Invoice": [
		{
			"fieldname": "sri_emission_point",
			"fieldtype": "Link",
			"insert_after": "pos_profile",
			"label": "SRI Emission Point",
			"options": "SRI Emission Point",
			"read_only": 1,
			"description": "Inherited from the POS Profile at validate; drives per-ticket voucher emission.",
		},
		{
			"fieldname": "pos_opening_entry",
			"fieldtype": "Link",
			"insert_after": "sri_emission_point",
			"label": "POS Opening Entry",
			"options": "POS Opening Entry",
			"read_only": 1,
			"description": "Cashier session this ticket belongs to; stamped at validate for shift-level traceability.",
		},
	],
	"Webshop Settings": [
		{
			"fieldname": "sri_emission_point",
			"fieldtype": "Link",
			"insert_after": "company",
			"label": "SRI Emission Point",
			"options": "SRI Emission Point",
			"description": "Logical caja: every shop order emits from this point. One shop, one point.",
		},
	],
}


def create_sri_custom_fields() -> None:
	"""Create or update SRI custom fields idempotently (safe on re-migrate)."""
	if create_custom_fields is None:  # pragma: no cover
		raise RuntimeError("frappe is required to create custom fields.")
	present = {
		doctype: fields for doctype, fields in CUSTOM_FIELDS.items() if frappe.db.exists("DocType", doctype)
	}
	if present:
		create_custom_fields(present, ignore_validate=True, update=True)


# Custom fields this app used to own but no longer defines. Frappe's
# `create_custom_fields(update=True)` never deletes, so a removed layout
# break would linger as an orphan column on existing sites. Pruned on
# migrate; keep entries here (never silently drop the cleanup).
RETIRED_SRI_CUSTOM_FIELDS = (("Purchase Invoice", "sri_col_break_supplier_flags"),)


def prune_retired_sri_custom_fields() -> None:
	"""Delete exactly the retired custom fields listed above (migrate path)."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to prune custom fields.")
	for doctype, fieldname in RETIRED_SRI_CUSTOM_FIELDS:
		frappe.db.delete("Custom Field", {"dt": doctype, "fieldname": fieldname})


def pending_custom_fields() -> list:
	"""Doctypes skipped because their app is not installed (e.g. Webshop)."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to list custom fields.")
	return [doctype for doctype in CUSTOM_FIELDS if not frappe.db.exists("DocType", doctype)]


def delete_sri_custom_fields() -> None:
	"""Remove exactly the custom fields owned by this app (uninstall path)."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to delete custom fields.")
	for doctype, fields in CUSTOM_FIELDS.items():
		frappe.db.delete(
			"Custom Field",
			{"dt": doctype, "fieldname": ("in", [f["fieldname"] for f in fields])},
		)

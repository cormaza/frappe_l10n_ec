app_name = "l10n_ec"
app_title = "Ecuador Localization"
app_publisher = "Ecuador Localization Contributors"
app_description = "Ecuadorian Localization and SRI Electronic Invoicing (XAdES-BES) for Frappe / ERPNext v16"
app_email = "developers@example.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext"]

fixtures = [
	"SRI Identification Type",
	"SRI Document Type",
	"SRI Payment Method",
	"SRI Tax Support",
	{
		"dt": "Print Format",
		"filters": [["name", "in", ["SRI RIDE", "SRI RIDE Delivery Note", "SRI RIDE Withholding"]]],
	},
	{
		"dt": "Report",
		"filters": [["name", "in", ["SRI ATS", "SRI Form 103", "SRI Form 104"]]],
	},
	{
		"dt": "Workspace",
		"filters": [["name", "in", ["Ecuador Localization"]]],
	},
]

after_install = "l10n_ec.ecuador_localization.setup.after_install"
after_migrate = "l10n_ec.ecuador_localization.setup.after_migrate"
before_uninstall = "l10n_ec.ecuador_localization.setup.before_uninstall"

doctype_js = {
	"Purchase Invoice": "public/js/purchase_invoice_sustento.js",
}

jinja = {
	"methods": [
		"l10n_ec.ecuador_localization.jinja.sri_barcode",
		"l10n_ec.ecuador_localization.jinja.sri_authorized_voucher",
		"l10n_ec.ecuador_localization.jinja.sri_voucher_data",
		"l10n_ec.ecuador_localization.jinja.sri_emisor",
	],
}

doc_events = {
	"Customer": {
		"validate": "l10n_ec.ecuador_localization.party_hooks.validate_sri_identification",
	},
	"Supplier": {
		"validate": "l10n_ec.ecuador_localization.party_hooks.validate_sri_identification",
	},
	"Sales Invoice": {
		"before_save": "l10n_ec.ecuador_localization.invoice_hooks.validate_sri_invoice",
		"validate": [
			"l10n_ec.ecuador_localization.shop_hooks.inherit_shop_point_invoice",
			"l10n_ec.ecuador_localization.validation.sync_tax_row_descriptions",
		],
	},
	"Quotation": {
		"validate": "l10n_ec.ecuador_localization.shop_hooks.inherit_shop_point_quotation",
		"on_submit": "l10n_ec.ecuador_localization.shop_hooks.check_shop_contact",
	},
	"Sales Order": {
		"validate": "l10n_ec.ecuador_localization.shop_hooks.inherit_shop_point_order",
		"on_submit": "l10n_ec.ecuador_localization.shop_hooks.check_shop_contact",
	},
	"POS Invoice": {
		"validate": "l10n_ec.ecuador_localization.invoice_hooks.validate_pos_ticket",
	},
	"Purchase Invoice": {
		"validate": [
			"l10n_ec.ecuador_localization.validation.enforce_iva_deduction_row",
			"l10n_ec.ecuador_localization.validation.validate_sustento_code",
			"l10n_ec.ecuador_localization.validation.sync_tax_row_descriptions",
		],
		"before_save": "l10n_ec.ecuador_localization.validation.sync_tax_row_descriptions",
	},
	"Company": {
		"after_insert": "l10n_ec.ecuador_localization.chart_setup.setup_company_chart",
	},
	"Payment Entry": {
		"on_submit": "l10n_ec.ecuador_localization.received_settlement.settle_received_withholdings",
		"on_cancel": "l10n_ec.ecuador_localization.received_settlement.cancel_received_settlements",
	},
}

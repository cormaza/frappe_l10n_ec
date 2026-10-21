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
]

after_install = "l10n_ec.ecuador_localization.setup.after_install"
after_migrate = "l10n_ec.ecuador_localization.setup.after_migrate"
before_uninstall = "l10n_ec.ecuador_localization.setup.before_uninstall"

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
	},
	"Purchase Invoice": {
		"validate": "l10n_ec.ecuador_localization.validation.enforce_iva_deduction_row",
	},
	"Company": {
		"after_insert": "l10n_ec.ecuador_localization.chart_setup.setup_company_chart",
	},
}

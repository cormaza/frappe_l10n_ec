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
]

after_install = "l10n_ec.ecuador_localization.setup.after_install"
after_migrate = "l10n_ec.ecuador_localization.setup.after_migrate"
before_uninstall = "l10n_ec.ecuador_localization.setup.before_uninstall"

doc_events = {
	"Customer": {
		"validate": "l10n_ec.ecuador_localization.party_hooks.validate_sri_identification",
	},
	"Supplier": {
		"validate": "l10n_ec.ecuador_localization.party_hooks.validate_sri_identification",
	},
}

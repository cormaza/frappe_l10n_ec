"""Per-company Ecuadorian tax templates (roadmap Phase 4).

Item Tax Templates are company-scoped (they point at the company's own
accounts), so they are created by :func:`setup_ecuadorian_taxes` right
after the chart install. ICE/IRBPNR templates are account-bound shells:
their effective assessment happens at transaction level (Phase 6).
Withholding percentages below are rate data for Phase 7; ATS mapping
arrives with the withholding doctypes.
"""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

TAX_TEMPLATES = [
	{"title": "Ecuador VAT 15% - Sales", "account_number": "2010707", "rate": 15.0},
	{"title": "Ecuador VAT 5% - Sales", "account_number": "2010707", "rate": 5.0},
	{"title": "Ecuador VAT 0% - Sales", "account_number": "2010707", "rate": 0.0},
	{"title": "Ecuador VAT Exempt - Sales", "account_number": "2010707", "rate": 0.0},
	{"title": "Ecuador No VAT Object - Sales", "account_number": "2010707", "rate": 0.0},
	{"title": "Ecuador ICE - Sales", "account_number": "2010710", "rate": 0.0},
	{"title": "Ecuador IRBPNR - Sales", "account_number": "2010711", "rate": 0.0},
	{"title": "Ecuador VAT 15% - Purchases", "account_number": "1010504", "rate": 15.0},
	{"title": "Ecuador VAT 5% - Purchases", "account_number": "1010504", "rate": 5.0},
	{"title": "Ecuador VAT 0% - Purchases", "account_number": "1010504", "rate": 0.0},
	{"title": "Ecuador VAT Exempt - Purchases", "account_number": "1010504", "rate": 0.0},
	{"title": "Ecuador No VAT Object - Purchases", "account_number": "1010504", "rate": 0.0},
]

WITHHOLDING_RATES = {
	"income_tax": [1.0, 1.75, 2.0, 2.75, 8.0, 10.0],
	"vat": [30.0, 70.0, 100.0],
}


def setup_ecuadorian_taxes(company: str) -> None:
	"""Create the template catalog for a company; reruns skip existing titles."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to create tax templates.")
	abbr = frappe.db.get_value("Company", company, "abbr") or company
	for spec in TAX_TEMPLATES:
		title = f"{spec['title']} - {abbr}"
		if frappe.db.exists("Item Tax Template", {"title": title, "company": company}):
			continue
		account = frappe.db.get_value(
			"Account", {"company": company, "account_number": spec["account_number"]}, "name"
		)
		if not account:
			frappe.throw(
				frappe._("Missing account {} for tax template '{}'.").format(
					spec["account_number"], spec["title"]
				)
			)
		frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": title,
				"company": company,
				"taxes": [{"tax_type": account, "tax_rate": spec["rate"]}],
			}
		).insert(ignore_permissions=True)

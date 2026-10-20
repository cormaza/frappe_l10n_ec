"""Ecuadorian withholding category seeds (mirror of `WITHHOLDING_RATES`).

SRI concepto codes (301/303/...) intentionally live nowhere here: they need
the official SRI retenciones source first. Categories resolve their SRI
codes per call through an explicit map until then.
"""

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

EC_WITHHOLDING_CATEGORIES = [
	{"name": "Ecuador IR 1%", "tax_type": "IR", "rate": 1.0, "account_number": "2010709"},
	{"name": "Ecuador IR 1.75%", "tax_type": "IR", "rate": 1.75, "account_number": "2010709"},
	{"name": "Ecuador IR 2%", "tax_type": "IR", "rate": 2.0, "account_number": "2010709"},
	{"name": "Ecuador IR 2.75%", "tax_type": "IR", "rate": 2.75, "account_number": "2010709"},
	{"name": "Ecuador IR 8%", "tax_type": "IR", "rate": 8.0, "account_number": "2010709"},
	{"name": "Ecuador IR 10%", "tax_type": "IR", "rate": 10.0, "account_number": "2010709"},
	{"name": "Ecuador IVA 30%", "tax_type": "IVA", "rate": 30.0, "account_number": "2010708"},
	{"name": "Ecuador IVA 70%", "tax_type": "IVA", "rate": 70.0, "account_number": "2010708"},
	{"name": "Ecuador IVA 100%", "tax_type": "IVA", "rate": 100.0, "account_number": "2010708"},
]

WITHHOLDING_YEAR_START = "2026-01-01"
WITHHOLDING_YEAR_END = "2026-12-31"


def setup_ecuadorian_withholdings(company: str) -> None:
	"""Ensure EC withholding categories (+ this company's account rows)."""
	if frappe is None:  # pragma: no cover
		raise RuntimeError("frappe is required to seed withholding categories.")
	for spec in EC_WITHHOLDING_CATEGORIES:
		account = frappe.db.get_value(
			"Account", {"company": company, "account_number": spec["account_number"]}, "name"
		)
		if not account:
			raise ValueError(f"Missing account {spec['account_number']} for withholding setup.")
		if not frappe.db.exists("Tax Withholding Category", spec["name"]):
			frappe.get_doc(
				{
					"doctype": "Tax Withholding Category",
					"name": spec["name"],
					"category_name": spec["name"],
					"rates": [
						{
							"tax_withholding_rate": spec["rate"],
							"from_date": WITHHOLDING_YEAR_START,
							"to_date": WITHHOLDING_YEAR_END,
						}
					],
					"accounts": [{"company": company, "account": account}],
				}
			).insert(ignore_permissions=True)
			continue
		existing = frappe.db.get_value(
			"Tax Withholding Account", {"parent": spec["name"], "company": company}, "name"
		)
		if not existing:
			category = frappe.get_doc("Tax Withholding Category", spec["name"])
			category.append("accounts", {"company": company, "account": account})
			category.save(ignore_permissions=True)


def category_code_map():
	"""Map seeded category names to `(impuesto, None)`: SRI concepto codes pending."""
	return {
		spec["name"]: ("1" if spec["tax_type"] == "IR" else "2", None) for spec in EC_WITHHOLDING_CATEGORIES
	}

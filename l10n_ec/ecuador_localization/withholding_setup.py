"""Ecuadorian withholding category seeds (mirror of `WITHHOLDING_RATES`).

SRI concepto codes (301/303/...) intentionally live nowhere here: they need
the official SRI retenciones source first. Categories resolve their SRI
codes per call through an explicit map until then.
"""

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


def category_code_map():
	"""Map seeded category names to `(impuesto, None)`: SRI concepto codes pending."""
	return {spec["name"]: ("1" if spec["tax_type"] == "IR" else "2", None) for spec in EC_WITHHOLDING_CATEGORIES}

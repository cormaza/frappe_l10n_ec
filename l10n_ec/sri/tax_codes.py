"""Map ERPNext Item Tax Templates to SRI tax codes (pure Python, no frappe).

Rate codes follow the SRI Ficha Técnica (IVA `0`=0%, `2`=12%, `3`=14%,
`4`=15%, `6`=no-object, `7`=exempt, `8`=5% differentiated). Matching is by
template title because several titles share a 0.0 rate. ICE/IRBPNR rates
depend on the good itself and cannot map from a template: callers handle
those manually.
"""

TEMPLATE_TAX_CODES = {
	"Ecuador VAT 15% - Sales": ("2", "4"),
	"Ecuador VAT 5% - Sales": ("2", "8"),
	"Ecuador VAT 0% - Sales": ("2", "0"),
	"Ecuador VAT Exempt - Sales": ("2", "7"),
	"Ecuador No VAT Object - Sales": ("2", "6"),
	"Ecuador VAT 15% - Purchases": ("2", "4"),
	"Ecuador VAT 5% - Purchases": ("2", "8"),
	"Ecuador VAT 0% - Purchases": ("2", "0"),
	"Ecuador VAT Exempt - Purchases": ("2", "7"),
	"Ecuador No VAT Object - Purchases": ("2", "6"),
}


def tax_codes_for_template(title: str) -> tuple[str, str]:
	"""Return `(codigo, codigoPorcentaje)` for a template title.

	ERPNext template names append `" - {company abbr}"`; one suffix strip
	is retried before giving up.
	"""
	if title in TEMPLATE_TAX_CODES:
		return TEMPLATE_TAX_CODES[title]
	base = (title or "").rsplit(" - ", 1)[0]
	if base in TEMPLATE_TAX_CODES:
		return TEMPLATE_TAX_CODES[base]
	raise ValueError(
		f"Tax template '{title}' has no automatic SRI code mapping (ICE/IRBPNR need manual codes)."
	)

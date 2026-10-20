import unittest

from l10n_ec.sri.tax_codes import TEMPLATE_TAX_CODES, tax_codes_for_template

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestTaxCodes(UnitTestCase):
	"""Unit tests for the template-to-SRI-code mapping (pure Python)."""

	def test_vat_family_resolves(self) -> None:
		self.assertEqual(tax_codes_for_template("Ecuador VAT 15% - Sales"), ("2", "4"))
		self.assertEqual(tax_codes_for_template("Ecuador VAT 5% - Sales"), ("2", "8"))
		self.assertEqual(tax_codes_for_template("Ecuador VAT 0% - Sales"), ("2", "0"))
		self.assertEqual(tax_codes_for_template("Ecuador VAT Exempt - Sales"), ("2", "7"))
		self.assertEqual(tax_codes_for_template("Ecuador No VAT Object - Sales"), ("2", "6"))
		self.assertEqual(tax_codes_for_template("Ecuador VAT 15% - Purchases"), ("2", "4"))

	def test_catalog_covers_all_vat_templates(self) -> None:
		self.assertEqual(len(TEMPLATE_TAX_CODES), 10)

	def test_unmapped_template_raises_helpful_error(self) -> None:
		with self.assertRaisesRegex(ValueError, "no automatic SRI code mapping"):
			tax_codes_for_template("Ecuador ICE - Sales")
		with self.assertRaisesRegex(ValueError, "no automatic SRI code mapping"):
			tax_codes_for_template("Nonexistent Template")

	def test_company_suffix_is_stripped(self) -> None:
		self.assertEqual(tax_codes_for_template("Ecuador VAT 15% - Sales - DE"), ("2", "4"))

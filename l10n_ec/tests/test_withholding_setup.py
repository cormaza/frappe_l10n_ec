import unittest

from l10n_ec.ecuador_localization.withholding_setup import EC_WITHHOLDING_CATEGORIES, category_code_map

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestWithholdingSetup(UnitTestCase):
	"""Unit tests for the Ecuadorian withholding category seeds (pure Python)."""

	def test_six_ir_categories_cover_standard_rates(self) -> None:
		by_tax = {}
		for spec in EC_WITHHOLDING_CATEGORIES:
			by_tax.setdefault(spec["tax_type"], []).append(spec["rate"])
		self.assertEqual(sorted(by_tax["IR"]), [1.0, 1.75, 2.0, 2.75, 8.0, 10.0])
		self.assertNotIn("IVA", by_tax)

	def test_accounts_point_to_withholding_payables(self) -> None:
		for spec in EC_WITHHOLDING_CATEGORIES:
			self.assertEqual(spec["account_number"], "2010709")

	def test_code_map_marks_concepto_pending(self) -> None:
		mapping = category_code_map()
		self.assertEqual(mapping["Ecuador IR 2%"], ("1", None))
		self.assertNotIn("Ecuador IVA 30%", mapping)

	def test_no_iva_categories_seeded(self) -> None:
		# ERPNext cannot compute tax-on-tax withholdings: IVA categories must
		# never exist for assignment; IVA rows are synthesized at emission.
		for spec in EC_WITHHOLDING_CATEGORIES:
			self.assertFalse(spec["name"].startswith("Ecuador IVA "))

import unittest

from l10n_ec.ecuador_localization.chart_setup import find_account_path, get_ec_chart_tree
from l10n_ec.ecuador_localization.tax_templates import TAX_TEMPLATES, WITHHOLDING_RATES, template_title

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestEcuadorTaxTemplates(UnitTestCase):
	"""Unit tests for the tax template catalog (no database)."""

	def test_catalog_entries_are_well_formed(self) -> None:
		titles = set()
		for spec in TAX_TEMPLATES:
			self.assertTrue(spec["title"])
			self.assertNotIn(spec["title"], titles)
			titles.add(spec["title"])
			self.assertIsInstance(spec["rate"], float)
			self.assertGreaterEqual(spec["rate"], 0.0)

	def test_every_template_account_exists_in_chart(self) -> None:
		tree = get_ec_chart_tree()
		for spec in TAX_TEMPLATES:
			self.assertIsNotNone(
				find_account_path(tree, spec["account_number"]),
				f"Account {spec['account_number']} for '{spec['title']}' missing from chart",
			)

	def test_vat_rates_cover_sales_and_purchases(self) -> None:
		by_title = {spec["title"]: spec["rate"] for spec in TAX_TEMPLATES}
		for side in ("Sales", "Purchases"):
			for rate in (15.0, 8.0, 5.0, 0.0):
				self.assertIn(f"Ecuador VAT {rate:g}% - {side}", by_title)

	def test_template_title_expects_erpnext_suffix(self) -> None:
		# ERPNext appends " - {abbr}" to the stored name itself; passing a
		# pre-suffixed title would double it and break Link references.
		self.assertEqual(template_title("Ecuador VAT 15% - Sales", "DE"), "Ecuador VAT 15% - Sales - DE")

	def test_withholding_rate_sets(self) -> None:
		self.assertEqual(
			WITHHOLDING_RATES,
			{
				"income_tax": [1.0, 1.75, 2.0, 2.75, 8.0, 10.0],
				"vat": [30.0, 70.0, 100.0],
			},
		)

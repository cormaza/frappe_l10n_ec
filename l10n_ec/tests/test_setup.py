"""Unit tests for app lifecycle wiring constants (no database)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.setup import TAX_GRID_LIST_VIEW


class TestTaxGridListView(UnitTestCase):
	def test_short_description_shows_on_both_taxes_grids(self) -> None:
		self.assertIn(("Sales Taxes and Charges", "description"), TAX_GRID_LIST_VIEW)
		self.assertIn(("Purchase Taxes and Charges", "description"), TAX_GRID_LIST_VIEW)

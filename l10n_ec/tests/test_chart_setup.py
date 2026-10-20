import unittest

from l10n_ec.ecuador_localization.chart_setup import find_account_path, get_ec_chart_tree

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestChartSetup(UnitTestCase):
	"""Unit tests for chart loading and account lookup (no database)."""

	def test_tree_loads_with_all_roots(self) -> None:
		tree = get_ec_chart_tree()
		self.assertGreaterEqual(len(tree), 10)

	def test_find_account_path_resolves_operational_leaf(self) -> None:
		tree = get_ec_chart_tree()
		self.assertEqual(
			find_account_path(tree, "2010709"),
			("PASIVO", "PASIVO CORRIENTE", "OTRAS OBLIGACIONES CORRIENTES", "RETENCIÓN DE IR POR PAGAR"),
		)

	def test_find_account_path_returns_none_when_missing(self) -> None:
		self.assertIsNone(find_account_path(get_ec_chart_tree(), "9999999"))

import unittest

from l10n_ec.ecuador_localization.chart_setup import (
	EXPENSE_ACCOUNT_NUMBER,
	INCOME_ACCOUNT_NUMBER,
	INVENTORY_ACCOUNT_NUMBER,
	PAYABLE_ACCOUNT_NUMBER,
	RECEIVABLE_ACCOUNT_NUMBER,
	STOCK_RNB_ACCOUNT_NUMBER,
	find_account_path,
	get_ec_chart_tree,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestChartSetup(UnitTestCase):
	"""Unit tests for chart loading and account lookup (no database)."""

	def test_tree_loads_with_all_roots(self) -> None:
		tree = get_ec_chart_tree()
		self.assertEqual(len(tree), 7)

	def test_find_account_path_resolves_operational_leaf(self) -> None:
		tree = get_ec_chart_tree()
		self.assertEqual(
			find_account_path(tree, "2010709"),
			("PASIVO", "PASIVO CORRIENTE", "OTRAS OBLIGACIONES CORRIENTES", "RETENCIÓN DE IR POR PAGAR"),
		)

	def test_find_account_path_returns_none_when_missing(self) -> None:
		self.assertIsNone(find_account_path(get_ec_chart_tree(), "9999999"))

	def test_trade_control_accounts(self) -> None:
		self.assertEqual(RECEIVABLE_ACCOUNT_NUMBER, "101020503")
		self.assertEqual(PAYABLE_ACCOUNT_NUMBER, "2010301")
		self.assertEqual(INCOME_ACCOUNT_NUMBER, "4101")
		self.assertEqual(EXPENSE_ACCOUNT_NUMBER, "520128")
		self.assertEqual(INVENTORY_ACCOUNT_NUMBER, "1010306")
		self.assertEqual(STOCK_RNB_ACCOUNT_NUMBER, "2010303")
		tree = get_ec_chart_tree()
		for number in (RECEIVABLE_ACCOUNT_NUMBER, PAYABLE_ACCOUNT_NUMBER):
			self.assertIsNotNone(find_account_path(tree, number))


class TestFlattenChartAccounts(UnitTestCase):
	"""Additive chart sync plans from the template tree (pure)."""

	def test_flatten_lists_every_numbered_node_once(self) -> None:
		from l10n_ec.ecuador_localization.chart_setup import flatten_chart_accounts, get_ec_chart_tree

		flat = flatten_chart_accounts(get_ec_chart_tree())
		numbers = [number for number, _title, _parent in flat]
		self.assertIn("520230", numbers)
		self.assertIn("2010708", numbers)
		self.assertEqual(len(numbers), len(set(numbers)))

	def test_new_account_reports_parent_number(self) -> None:
		from l10n_ec.ecuador_localization.chart_setup import flatten_chart_accounts, get_ec_chart_tree

		parents = {number: parent for number, _title, parent in flatten_chart_accounts(get_ec_chart_tree())}
		self.assertEqual(parents["520230"], "5202")
		self.assertEqual(parents["520228"], "5202")

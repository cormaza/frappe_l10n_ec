"""Unit tests for assumed withholdings (pure JE math, no frappe)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.assumed_withholding import assumed_lines


def _row(account_number: str, amount: float, deduct: str = "Deduct"):
	return {"account_number": account_number, "tax_amount": amount, "add_deduct_tax": deduct}


class TestAssumedLines(UnitTestCase):
	def test_sums_withholding_rows_only(self) -> None:
		lines = assumed_lines(
			[_row("1010504", 15.0, "Add"), _row("2010709", 2.0), _row("2010708", 4.5)],
			{"expense": "520230 - X", "payable": "2010301 - Y", "cost_center": "Main - DE"},
			{"party_type": "Supplier", "party": "Demo Supplier RUC"},
		)
		self.assertIsNotNone(lines)
		debits = [line for line in lines if line.get("debit_in_account_currency")]
		credits = [line for line in lines if line.get("credit_in_account_currency")]
		self.assertEqual(len(debits), 1)
		self.assertEqual(debits[0]["debit_in_account_currency"], 6.5)
		self.assertEqual(debits[0]["account"], "520230 - X")
		self.assertEqual(len(credits), 1)
		self.assertEqual(credits[0]["credit_in_account_currency"], 6.5)
		self.assertEqual(credits[0]["account"], "2010301 - Y")

	def test_no_withholdings_returns_none(self) -> None:
		self.assertIsNone(
			assumed_lines(
				[_row("1010504", 15.0, "Add")],
				{"expense": "E", "payable": "P", "cost_center": "C"},
				{"party_type": "Supplier", "party": "S"},
			)
		)

	def test_add_rows_never_count(self) -> None:
		self.assertIsNone(
			assumed_lines(
				[_row("2010709", 2.0, "Add")],
				{"expense": "E", "payable": "P", "cost_center": "C"},
				{"party_type": "Supplier", "party": "S"},
			)
		)

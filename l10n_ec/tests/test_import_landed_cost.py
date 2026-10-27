"""Unit tests for SRI import landed cost (T4: LCV prefill mapping)."""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.sri.import_landed_cost import build_lcv_taxes, select_receipt_document


def _freight(**kwargs):
	leg = {
		"source": "ACC-PINV-2026-00002",
		"amount": 200.0,
		"expense_account": "Freight - DE",
		"account_currency": "USD",
		"exchange_rate": 1.0,
	}
	leg.update(kwargs)
	return leg


def _insurance(**kwargs):
	leg = {
		"source": "ACC-PINV-2026-00003",
		"amount": 50.0,
		"expense_account": "Insurance - DE",
		"account_currency": "USD",
		"exchange_rate": 1.0,
	}
	leg.update(kwargs)
	return leg


class TestSelectReceiptDocument(UnitTestCase):
	def test_purchase_receipt_wins(self) -> None:
		self.assertEqual(
			select_receipt_document("MAT-PR-2026-00001", "ACC-PINV-2026-00001", True),
			("Purchase Receipt", "MAT-PR-2026-00001"),
		)

	def test_invoice_with_update_stock_is_receipt(self) -> None:
		self.assertEqual(
			select_receipt_document(None, "ACC-PINV-2026-00001", True),
			("Purchase Invoice", "ACC-PINV-2026-00001"),
		)

	def test_invoice_without_update_stock_is_nothing(self) -> None:
		self.assertIsNone(select_receipt_document(None, "ACC-PINV-2026-00001", False))

	def test_order_only_is_nothing(self) -> None:
		self.assertIsNone(select_receipt_document(None, None, False))


class TestBuildLcvTaxes(UnitTestCase):
	def test_two_legs_map_to_tax_rows(self) -> None:
		rows = build_lcv_taxes(_freight(), _insurance())
		self.assertEqual(len(rows), 2)
		self.assertEqual(rows[0]["amount"], 200.0)
		self.assertEqual(rows[0]["expense_account"], "Freight - DE")
		self.assertIn("ACC-PINV-2026-00002", rows[0]["description"])
		self.assertEqual(rows[1]["amount"], 50.0)

	def test_zero_leg_is_skipped(self) -> None:
		rows = build_lcv_taxes(_freight(), _insurance(amount=0.0))
		self.assertEqual(len(rows), 1)

	def test_no_legs_fails(self) -> None:
		with self.assertRaises(ValueError):
			build_lcv_taxes(None, None)

	def test_all_zero_fails(self) -> None:
		with self.assertRaises(ValueError):
			build_lcv_taxes(_freight(amount=0.0), _insurance(amount=0.0))

	def test_missing_expense_account_fails(self) -> None:
		with self.assertRaises(ValueError):
			build_lcv_taxes(_freight(expense_account=""), _insurance())

	def test_negative_amount_fails(self) -> None:
		with self.assertRaises(ValueError):
			build_lcv_taxes(_freight(amount=-5.0), _insurance())

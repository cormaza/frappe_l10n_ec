"""Unit tests for the sales-side received-withholding settlement (pure parts)."""

import unittest
from unittest.mock import patch

from l10n_ec.ecuador_localization.received_settlement import build_settlement_for_si, settlement_lines

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

ACCOUNTS = {
	"ir_asset": "1010502 - IR",
	"iva_asset": "1010501 - IVA",
	"receivable": "131001 - REC",
	"cost_center": "Main",
}

PARTY = {"party_type": "Customer", "party": "Demo Customer RUC"}


class TestSettlementLines(UnitTestCase):
	def test_mixed_ir_and_iva_lines_balance(self) -> None:
		lines = settlement_lines(
			100.0, 150.0, ACCOUNTS, {"party_type": "Customer", "party": "Demo Customer RUC"}
		)
		self.assertEqual(len(lines), 3)
		self.assertEqual(lines[0]["debit_in_account_currency"], 100.0)
		self.assertEqual(lines[1]["debit_in_account_currency"], 150.0)
		self.assertEqual(lines[2]["credit_in_account_currency"], 250.0)
		self.assertEqual(lines[2]["account"], "131001 - REC")

	def test_empty_inputs_return_none(self) -> None:
		self.assertIsNone(
			settlement_lines(0.0, 0.0, ACCOUNTS, {"party_type": "Customer", "party": "Demo Customer RUC"})
		)
		self.assertIsNone(
			settlement_lines(0.0, 0.0, ACCOUNTS, {"party_type": "Customer", "party": "Demo Customer RUC"})
		)

	def test_ir_only_has_no_iva_line(self) -> None:
		lines = settlement_lines(2.0, 0.0, ACCOUNTS, {"party_type": "Customer", "party": "Demo Customer RUC"})
		self.assertEqual(len(lines), 2)
		self.assertEqual(lines[1]["credit_in_account_currency"], 2.0)


class FakeSIDoc(dict):
	"""Sales-Invoice double with list-style items/taxes/entries."""

	@property
	def items(self):
		# Shadows dict.items: base_lines() reads ref.items like frappe child tables.
		return self["items"]


class FakeItem:
	"""Item-row double with attribute access (mirrors frappe child docs)."""

	def __init__(self, values: dict) -> None:
		self.__dict__.update(values)

	def get(self, key, default=None):
		return self.__dict__.get(key, default)


class TestBuildSettlement(UnitTestCase):
	def _si(self, **overrides):
		base = {
			"company": "Demo Ecuador",
			"name": "ACC-SINV-0001",
			"posting_date": "2026-10-21",
			"debit_to": "131001 - REC",
			"sri_iva_concepto": "3",
			"sri_ir_concepto": "303",
			"net_total": 1000.0,
			"items": [
				FakeItem(
					{
						"item_code": "DEMO-WIDGET",
						"description": "Demo widget",
						"qty": 10.0,
						"rate": 100.0,
						"amount": 1000.0,
						"discount_amount": 0.0,
						"item_tax_template": "Ecuador VAT 15% - Sales",
						"taxes": [
							{
								"template": "Ecuador VAT 15% - Sales",
								"rate": 15.0,
								"base": 1000.0,
								"value": 150.0,
							}
						],
					}
				),
			],
		}
		base.update(overrides)
		return FakeSIDoc(base)

	def _resolvers(self):
		return {
			"resolve_asset": lambda company, number: {
				"1010502": "1010502 - IR",
				"1010501": "1010501 - IVA",
			}[number],
			"cost_center_resolver": lambda company: "Main",
		}

	@patch("l10n_ec.ecuador_localization.voucher_flow._template_rate", return_value=15.0)
	def test_full_settlement_matches_quipuy_example(self, _rate) -> None:
		settlement = build_settlement_for_si(self._si(), **self._resolvers())
		self.assertEqual(settlement["company"], "Demo Ecuador")
		debits = [line.get("debit_in_account_currency", 0) for line in settlement["accounts"]]
		self.assertEqual(sorted(debits), [0, 100.0, 150.0])
		credit = [
			line["credit_in_account_currency"]
			for line in settlement["accounts"]
			if "credit_in_account_currency" in line
		]
		self.assertEqual(credit, [250.0])
		self.assertIn("ACC-SINV-0001", settlement["user_remark"])

	@patch("l10n_ec.ecuador_localization.voucher_flow._template_rate", return_value=15.0)
	def test_ir_uses_base_net_total(self, _rate) -> None:
		doc = self._si(base_net_total=1080.0, net_total=1000.0)
		settlement = build_settlement_for_si(doc, **self._resolvers())
		debits = sorted(
			line.get("debit_in_account_currency", 0)
			for line in settlement["accounts"]
			if "debit_in_account_currency" in line
		)
		self.assertIn(round(1080.0 * 10 / 100, 2), debits)

	def test_no_withholdings_returns_none(self) -> None:
		doc = self._si(sri_iva_concepto="", sri_ir_concepto="")
		self.assertIsNone(build_settlement_for_si(doc, **self._resolvers()))

	@patch("l10n_ec.ecuador_localization.voucher_flow._template_rate", return_value=15.0)
	def test_missing_receivable_returns_none(self, _rate) -> None:
		doc = self._si(debit_to=None)
		self.assertIsNone(build_settlement_for_si(doc, **self._resolvers()))

	@patch("l10n_ec.ecuador_localization.voucher_flow._template_rate", return_value=15.0)
	def test_missing_asset_account_raises(self, _rate) -> None:
		with self.assertRaises(ValueError):
			build_settlement_for_si(
				self._si(),
				resolve_asset=lambda company, number: None,
				cost_center_resolver=lambda company: "Main",
			)


if __name__ == "__main__":
	unittest.main()

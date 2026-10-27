"""Unit tests for the Form 104 (IVA) collector (pure parts, no frappe)."""

import importlib.util
import unittest
from pathlib import Path

from l10n_ec.sri.form104 import FORM104_BOXES, collect_104
from l10n_ec.sri.voucher_states import SriVoucherError

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

REPORT_PY = (
	Path(__file__).resolve().parent.parent
	/ "ecuador_localization"
	/ "report"
	/ "sri_form_104"
	/ "sri_form_104.py"
)


def _ledger(**overrides):
	ledger = {
		"sales_taxes": [
			{"code": "2", "rate_code": "4", "base": 1000.0, "value": 150.0},
			{"code": "2", "rate_code": "4", "base": 500.0, "value": 75.0},
			{"code": "2", "rate_code": "0", "base": 200.0, "value": 0.0},
			{"code": "2", "rate_code": "7", "base": 100.0, "value": 0.0},
		],
		"purchase_taxes": [
			{"code": "2", "rate_code": "4", "base": 2000.0, "value": 300.0},
			{"code": "2", "rate_code": "6", "base": 50.0, "value": 0.0},
		],
		"iva_deduction_rows": [{"rate": 30.0, "amount": 90.0}],
		"settlements": [
			{"account_number": "1010501", "debit": 45.0},
			{"account_number": "1010502", "debit": 20.0},
		],
		"received_refs": [
			{
				"number": "001-002-000000009",
				"authorization": "0987654321",
				"date": "28/03/2026",
				"iva_value": 45.0,
				"renta_value": 20.0,
			}
		],
	}
	ledger.update(overrides)
	return ledger


def _load_report_module():
	spec = importlib.util.spec_from_file_location("sri_form_104_report_under_test", REPORT_PY)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class TestCollect104MonthMix(UnitTestCase):
	def test_month_mix_aggregates_all_sections(self) -> None:
		result = collect_104(_ledger(), 2026, 3)
		self.assertEqual(result["401"], 1500.0)
		self.assertEqual(result["411"], 1500.0)
		self.assertEqual(result["421"], 225.0)
		self.assertEqual(result["403"], 200.0)
		self.assertEqual(result["413"], 200.0)
		self.assertEqual(result["431"], 100.0)
		self.assertEqual(result["441"], 100.0)
		self.assertEqual(result["409"], 1700.0)
		self.assertEqual(result["419"], 1700.0)
		self.assertEqual(result["429"], 225.0)
		self.assertEqual(result["500"], 2000.0)
		self.assertEqual(result["510"], 2000.0)
		self.assertEqual(result["520"], 300.0)
		self.assertEqual(result["531"], 50.0)
		self.assertEqual(result["541"], 50.0)
		self.assertEqual(result["509"], 2000.0)
		self.assertEqual(result["519"], 2000.0)
		self.assertEqual(result["529"], 300.0)

	def test_deduction_and_settlement_credits(self) -> None:
		result = collect_104(_ledger(), 2026, 3)
		self.assertEqual(result["725"], 90.0)
		self.assertEqual(result["799"], 90.0)
		self.assertEqual(result["801"], 90.0)
		self.assertEqual(result["609"], 45.0)
		self.assertEqual(result["received_ir_credit"], 20.0)
		self.assertEqual(len(result["received_refs"]), 1)
		self.assertEqual(result["received_refs"][0]["number"], "001-002-000000009")
		self.assertEqual(result["received_refs"][0]["iva_value"], 45.0)
		self.assertEqual(result["received_refs"][0]["renta_value"], 20.0)

	def test_liquidation_follows_cash_default(self) -> None:
		result = collect_104(_ledger(), 2026, 3)
		self.assertEqual(result["480"], 1500.0)
		self.assertEqual(result["481"], 0.0)
		self.assertEqual(result["482"], 225.0)
		self.assertEqual(result["484"], 225.0)
		self.assertEqual(result["485"], 0.0)
		self.assertEqual(result["499"], 225.0)
		self.assertEqual(result["563"], 0.88)
		self.assertEqual(result["564"], 264.71)
		self.assertEqual(result["565"], 35.29)
		self.assertEqual(result["601"], 0.0)
		self.assertEqual(result["602"], 39.71)
		self.assertEqual(result["620"], -84.71)
		self.assertEqual(result["699"], -84.71)
		self.assertEqual(result["859"], 5.29)

	def test_differentiated_5pct_boxes(self) -> None:
		result = collect_104(
			_ledger(
				sales_taxes=[{"code": "2", "rate_code": "8", "tarifa": 5.0, "base": 400.0, "value": 20.0}],
				purchase_taxes=[{"code": "2", "rate_code": "8", "tarifa": 5.0, "base": 600.0, "value": 30.0}],
				iva_deduction_rows=[],
				settlements=[],
				received_refs=[],
			),
			2026,
			3,
		)
		self.assertEqual(result["425"], 400.0)
		self.assertEqual(result["435"], 400.0)
		self.assertEqual(result["445"], 20.0)
		self.assertEqual(result["429"], 20.0)
		self.assertEqual(result["540"], 600.0)
		self.assertEqual(result["550"], 600.0)
		self.assertEqual(result["560"], 30.0)
		self.assertEqual(result["529"], 30.0)
		# 563 counts 435 net: (411+412+420+435+415+416+417+418)/419 = 400/400
		self.assertEqual(result["563"], 1.0)
		self.assertEqual(result["564"], 30.0)

	def test_zero_amount_deduction_rows_are_skipped(self) -> None:
		result = collect_104(
			_ledger(iva_deduction_rows=[{"rate": 0.0, "amount": 0.0}]),
			2026,
			3,
		)
		self.assertEqual(result["799"], 0.0)

	def test_non_vat_impuestos_are_ignored(self) -> None:
		result = collect_104(
			_ledger(
				sales_taxes=[
					{"code": "3", "rate_code": "", "base": 50.0, "value": 5.0},
					{"code": "2", "rate_code": "4", "base": 100.0, "value": 15.0},
				],
				purchase_taxes=[],
				iva_deduction_rows=[],
				settlements=[],
				received_refs=[],
			),
			2026,
			3,
		)
		self.assertEqual(result["401"], 100.0)
		self.assertEqual(result["409"], 100.0)


class TestCollect104EmptyMonth(UnitTestCase):
	def test_empty_ledger_returns_all_zero_boxes(self) -> None:
		result = collect_104({}, 2026, 3)
		self.assertEqual(set(result) - {"received_refs", "received_ir_credit"}, FORM104_BOXES)
		for box in FORM104_BOXES:
			expected = 1.0 if box == "563" else 0.0
			self.assertEqual(result[box], expected, f"Box {box} is not {expected}")
		self.assertEqual(result["received_refs"], [])
		self.assertEqual(result["received_ir_credit"], 0.0)

	def test_explicit_empty_sections_match_empty_ledger(self) -> None:
		result = collect_104(
			{
				"sales_taxes": [],
				"purchase_taxes": [],
				"iva_deduction_rows": [],
				"settlements": [],
				"received_refs": [],
			},
			2026,
			3,
		)
		self.assertEqual(result["409"], 0.0)
		self.assertEqual(result["419"], 0.0)
		self.assertEqual(result["429"], 0.0)
		self.assertEqual(result["509"], 0.0)
		self.assertEqual(result["519"], 0.0)
		self.assertEqual(result["529"], 0.0)
		self.assertEqual(result["563"], 1.0)
		self.assertEqual(result["859"], 0.0)


class TestCollect104FailLoud(UnitTestCase):
	def test_bad_period_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_104(_ledger(), 1999, 3)
		with self.assertRaises(SriVoucherError):
			collect_104(_ledger(), 2026, 13)

	def test_unknown_vat_rate_code_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_104(
				_ledger(sales_taxes=[{"code": "2", "rate_code": "9", "base": 10.0, "value": 1.0}]),
				2026,
				3,
			)

	def test_unknown_tax_code_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_104(
				_ledger(sales_taxes=[{"code": "8", "rate_code": "4", "base": 10.0, "value": 1.0}]),
				2026,
				3,
			)

	def test_unknown_deduction_rate_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_104(
				_ledger(iva_deduction_rows=[{"rate": 15.0, "amount": 10.0}]),
				2026,
				3,
			)

	def test_unknown_settlement_account_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_104(
				_ledger(settlements=[{"account_number": "1010599", "debit": 10.0}]),
				2026,
				3,
			)

	def test_received_ref_without_number_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_104(
				_ledger(received_refs=[{"authorization": "123", "iva_value": 5.0}]),
				2026,
				3,
			)


class TestReportRing1Importable(UnitTestCase):
	def test_report_module_imports_without_frappe(self) -> None:
		module = _load_report_module()
		columns, data = module.execute(None)
		self.assertEqual(
			[column["fieldname"] for column in columns],
			["descripcion", "casilleros", "signo", "bruto", "neto", "impuesto"],
		)
		self.assertEqual(data, [])


if __name__ == "__main__":
	unittest.main()


class TestReturnsHitNetOnly(UnitTestCase):
	"""Credit notes reduce VALOR NETO (bruto - N/C), never VALOR BRUTO (DIMM)."""

	def test_sales_return_reduces_net_and_tax_only(self) -> None:
		ledger = _ledger(
			sales_taxes=[
				{"code": "2", "rate_code": "4", "base": 1000.0, "value": 150.0},
				{"code": "2", "rate_code": "4", "base": -200.0, "value": -30.0, "is_return": True},
			],
			purchase_taxes=[],
			iva_deduction_rows=[],
			settlements=[],
			received_refs=[],
		)
		result = collect_104(ledger, 2026, 3)
		self.assertEqual(result["401"], 1000.0)
		self.assertEqual(result["411"], 800.0)
		self.assertEqual(result["421"], 120.0)

	def test_purchase_return_reduces_net_and_tax_only(self) -> None:
		ledger = _ledger(
			sales_taxes=[],
			purchase_taxes=[
				{"code": "2", "rate_code": "4", "base": 2000.0, "value": 300.0},
				{"code": "2", "rate_code": "4", "base": -500.0, "value": -75.0, "is_return": True},
			],
			iva_deduction_rows=[],
			settlements=[],
			received_refs=[],
		)
		result = collect_104(ledger, 2026, 3)
		self.assertEqual(result["500"], 2000.0)
		self.assertEqual(result["510"], 1500.0)
		self.assertEqual(result["520"], 225.0)


class TestCollect104ReembolsoRegression(UnitTestCase):
	"""T3 (S2): collect_104 purchase_taxes exclude reembolso bases.

	Assumption: reembolso IVA stays out of the 500s/401s boxes; the ATS
	own bases (split_iva_bases) are the single source and T4 accounting
	owns the reimbursement IVA treatment.
	"""

	def test_split_iva_bases_ignores_reembolso_totals(self) -> None:
		from l10n_ec.sri.ats_collector import split_iva_bases

		own_taxes = [{"code": "2", "rate_code": "4", "base": 2000.0, "value": 300.0}]
		bases = split_iva_bases(own_taxes)
		self.assertEqual(bases["baseImpGrav"], 2000.0)
		self.assertEqual(bases["montoIva"], 300.0)

	def test_collect_104_excludes_reembolso_iva(self) -> None:
		result = collect_104(
			_ledger(
				purchase_taxes=[{"code": "2", "rate_code": "4", "base": 2000.0, "value": 300.0}],
			),
			2026,
			3,
		)
		# Own bases only: 50.0 taxed_base + 7.5 iva_amount from the reembolso
		# leg never reach the 500s boxes.
		self.assertEqual(result["500"], 2000.0)
		self.assertEqual(result["520"], 300.0)


class TestVariableRateBoxes(UnitTestCase):
	"""Tarifa-variable (decreed) rates route to 410/420/430 + 530/533/534."""

	def test_holiday_8pct_routes_variable(self) -> None:
		result = collect_104(
			_ledger(
				sales_taxes=[{"code": "2", "rate_code": "8", "tarifa": 8.0, "base": 100.0, "value": 8.0}],
				purchase_taxes=[],
				iva_deduction_rows=[],
				settlements=[],
				received_refs=[],
			),
			2026,
			3,
		)
		self.assertEqual(result["410"], 100.0)
		self.assertEqual(result["420"], 100.0)
		self.assertEqual(result["425"], 0.0)
		self.assertEqual(result["435"], 0.0)

	def test_variable_rate_without_tarifa_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_104(
				_ledger(sales_taxes=[{"code": "2", "rate_code": "8", "base": 100.0, "value": 8.0}]),
				2026,
				3,
			)

	def test_factor_563_counts_variable_and_5pct_net(self) -> None:
		result = collect_104(
			_ledger(
				sales_taxes=[
					{"code": "2", "rate_code": "4", "base": 1000.0, "value": 150.0},
					{"code": "2", "rate_code": "8", "tarifa": 5.0, "base": 200.0, "value": 10.0},
				],
				purchase_taxes=[],
				iva_deduction_rows=[],
				settlements=[],
				received_refs=[],
			),
			2026,
			3,
		)
		# (411 + 435) / 419 = (1000 + 200) / 1200
		self.assertEqual(result["563"], 1.0)
		self.assertEqual(result["419"], 1200.0)

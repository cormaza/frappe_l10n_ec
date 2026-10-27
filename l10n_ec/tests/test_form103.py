"""Unit tests for the Form 103 month collector (pure parts, no frappe)."""

import unittest

from l10n_ec.sri.form103 import collect_103
from l10n_ec.sri.voucher_states import SriVoucherError
from l10n_ec.sri.xml_builder import build_retencion_xml

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

CTX = {
	"environment": "1",
	"doc_code": "07",
	"ruc": "1790016919001",
	"legal_name": "PRUEBAS SERVICIO DE RENTAS INTERNAS",
	"head_office_address": "Av. Amazonas y Naciones Unidas",
	"establishment": "001",
	"emission_point": "001",
	"sequential": "000000007",
	"access_key": "1710202606112345678901234567890123456789012",
	"branch_address": "Av. Amazonas y Naciones Unidas",
	"special_taxpayer": "",
	"accounting_required": True,
}


def _row(concepto: str, base: float, rate: float, value: float, code: str = "1") -> dict:
	return {
		"code": code,
		"withholding_code": concepto,
		"base": base,
		"rate": rate,
		"value": value,
	}


def _retencion_xml(rows: list, fiscal_period: str = "03/2026") -> str:
	return build_retencion_xml(
		CTX,
		{
			"issue_date": "21/03/2026",
			"subject_id_type": "04",
			"related_party": "NO",
			"subject_name": "EMPRESA EJEMPLO SA",
			"subject_id": "1790016919001",
			"fiscal_period": fiscal_period,
			"docs": [
				{
					"sustento_code": "02",
					"doc_code": "01",
					"doc_number": "001-001-000000001",
					"issue_date": "20/03/2026",
					"auth_number": "1234567890",
					"subtotal": 1000.00,
					"total": 1150.00,
					"doc_taxes": [],
					"withholdings": rows,
					"payments": [{"method": "01", "amount": 1150.00}],
				}
			],
		},
	)


def _voucher(rows: list, **overrides) -> dict:
	voucher = {
		"sri_number": "001-001-000000007",
		"voucher_state": "Authorized",
		"sri_doc_code": "07",
		"authorization_number": "1234567890",
		"authorization_date": "2026-03-25 10:00:00",
		"unsigned_xml": _retencion_xml(rows),
	}
	voucher.update(overrides)
	return voucher


class TestCollect103(UnitTestCase):
	"""AUTHORIZED 07 IR blocks map concepto to exact casilleros."""

	def test_303_312_340_map_to_exact_casilleros(self) -> None:
		voucher = _voucher(
			[
				_row("303", 1000.0, 10.0, 100.0),
				_row("312", 500.0, 2.0, 10.0),
				_row("340", 2000.0, 3.0, 60.0),
			]
		)
		self.assertEqual(
			collect_103([voucher], 2026, 3),
			{
				303: 1000.0,
				312: 500.0,
				349: 3500.0,
				353: 100.0,
				362: 10.0,
				399: 170.0,
				497: 0.0,
				498: 0.0,
				499: 170.0,
				3400: 2000.0,
				3900: 60.0,
			},
		)

	def test_totals_sum_across_vouchers(self) -> None:
		vouchers = [
			_voucher([_row("303", 1000.0, 10.0, 100.0)], sri_number="001-001-000000007"),
			_voucher([_row("303", 400.0, 10.0, 40.0)], sri_number="001-001-000000008"),
		]
		self.assertEqual(
			collect_103(vouchers, 2026, 3),
			{303: 1400.0, 349: 1400.0, 353: 140.0, 399: 140.0, 497: 0.0, 498: 0.0, 499: 140.0},
		)

	def test_rejected_voucher_excluded(self) -> None:
		vouchers = [
			_voucher([_row("303", 1000.0, 10.0, 100.0)]),
			_voucher([_row("303", 500.0, 10.0, 50.0)], voucher_state="Rejected"),
		]
		self.assertEqual(
			collect_103(vouchers, 2026, 3),
			{303: 1000.0, 349: 1000.0, 353: 100.0, 399: 100.0, 497: 0.0, 498: 0.0, 499: 100.0},
		)

	def test_non_07_and_other_month_vouchers_excluded(self) -> None:
		vouchers = [
			_voucher([_row("303", 1000.0, 10.0, 100.0)]),
			_voucher([_row("303", 500.0, 10.0, 50.0)], sri_doc_code="01"),
			_voucher([_row("303", 700.0, 10.0, 70.0)], authorization_date="2026-02-20 10:00:00"),
		]
		self.assertEqual(
			collect_103(vouchers, 2026, 3),
			{303: 1000.0, 349: 1000.0, 353: 100.0, 399: 100.0, 497: 0.0, 498: 0.0, 499: 100.0},
		)

	def test_iva_rows_are_skipped(self) -> None:
		voucher = _voucher([_row("303", 1000.0, 10.0, 100.0), _row("2", 150.0, 70.0, 105.0, code="2")])
		self.assertEqual(
			collect_103([voucher], 2026, 3),
			{303: 1000.0, 349: 1000.0, 353: 100.0, 399: 100.0, 497: 0.0, 498: 0.0, 499: 100.0},
		)

	def test_single_box_concepto_records_base_only(self) -> None:
		voucher = _voucher([_row("309", 1000.0, 3.0, 30.0), _row("332", 500.0, 0.0, 0.0)])
		self.assertEqual(
			collect_103([voucher], 2026, 3),
			{309: 1000.0, 332: 500.0, 349: 1500.0, 399: 0.0, 497: 0.0, 498: 0.0, 499: 0.0},
		)

	def test_no_4xx_exterior_casillero_ever_emitted(self) -> None:
		voucher = _voucher([_row("303", 1000.0, 10.0, 100.0), _row("340", 2000.0, 3.0, 60.0)])
		for box in collect_103([voucher], 2026, 3):
			if box in (497, 498, 499):
				continue  # computed portal boxes, always present
			self.assertFalse(400 <= box <= 499, f"exterior box {box} must never be guessed")

	def test_unknown_concepto_raises(self) -> None:
		with self.assertRaises(SriVoucherError) as ctx:
			collect_103([_voucher([_row("999", 100.0, 1.0, 1.0)])], 2026, 3)
		self.assertIn("999", str(ctx.exception))

	def test_exterior_concepto_raises(self) -> None:
		with self.assertRaises(SriVoucherError) as ctx:
			collect_103([_voucher([_row("500", 100.0, 25.0, 25.0, code="9")])], 2026, 3)
		self.assertIn("exterior", str(ctx.exception).lower())

	def test_concepto_without_casilleros_raises(self) -> None:
		with self.assertRaises(SriVoucherError) as ctx:
			collect_103([_voucher([_row("325", 1000.0, 25.0, 250.0)])], 2026, 3)
		self.assertIn("325", str(ctx.exception))

	def test_empty_month_returns_empty(self) -> None:
		self.assertEqual(collect_103([], 2026, 3), {})

	def test_bad_period_fails_loud(self) -> None:
		for year, month in ((1999, 3), (2026, 0), (2026, 13)):
			with self.subTest(year=year, month=month):
				with self.assertRaises(SriVoucherError):
					collect_103([], year, month)

	def test_missing_xml_fails_loud(self) -> None:
		voucher = _voucher([_row("303", 1000.0, 10.0, 100.0)], unsigned_xml="")
		with self.assertRaises(SriVoucherError):
			collect_103([voucher], 2026, 3)

	def test_fiscal_period_fallback_attributes_month(self) -> None:
		voucher = _voucher(
			[_row("303", 1000.0, 10.0, 100.0)],
			authorization_date=None,
			unsigned_xml=_retencion_xml([_row("303", 1000.0, 10.0, 100.0)], fiscal_period="03/2026"),
		)
		self.assertEqual(
			collect_103([voucher], 2026, 3),
			{303: 1000.0, 349: 1000.0, 353: 100.0, 399: 100.0, 497: 0.0, 498: 0.0, 499: 100.0},
		)
		self.assertEqual(collect_103([voucher], 2026, 4), {})

	def test_voucher_without_any_date_raises(self) -> None:
		voucher = _voucher(
			[_row("303", 1000.0, 10.0, 100.0)],
			authorization_date=None,
			unsigned_xml=_retencion_xml([_row("303", 1000.0, 10.0, 100.0)], fiscal_period=""),
		)
		with self.assertRaises(SriVoucherError):
			collect_103([voucher], 2026, 3)


class TestForm103ReportRing1(UnitTestCase):
	"""The thin Script Report stays importable without frappe (Ring 1)."""

	def test_execute_without_frappe_returns_empty(self) -> None:
		try:
			import frappe
		except ImportError:
			frappe = None  # type: ignore[assignment]
		if frappe is not None:
			self.skipTest("Ring-1 only: bench executes the live fetch path.")
		from l10n_ec.ecuador_localization.report.sri_form_103.sri_form_103 import execute

		columns, data = execute({"company": "Demo Company", "year": 2026, "month": 3})
		self.assertEqual(
			[column["fieldname"] for column in columns],
			["concepto", "cas_base", "base", "cas_impuesto", "impuesto"],
		)
		self.assertEqual(data, [])


class TestCollect103Exterior(UnitTestCase):
	"""Exterior rows collect into their regime boxes (sourced, never guessed)."""

	def test_exterior_conVENio_collects(self) -> None:
		from l10n_ec.sri.form103 import collect_103

		voucher = _voucher([_row("501A", 1000.0, 10.0, 100.0, code="9")], sri_exterior_regime="con")
		self.assertEqual(
			collect_103([voucher], 2026, 3),
			{349: 0.0, 399: 0.0, 410: 1000.0, 460: 100.0, 497: 1000.0, 498: 100.0, 499: 100.0},
		)

	def test_exterior_sin_convenio_collects(self) -> None:
		from l10n_ec.sri.form103 import collect_103

		voucher = _voucher([_row("501", 2000.0, 25.0, 500.0, code="9")], sri_exterior_regime="sin")
		self.assertEqual(
			collect_103([voucher], 2026, 3),
			{349: 0.0, 399: 0.0, 422: 2000.0, 472: 500.0, 497: 2000.0, 498: 500.0, 499: 500.0},
		)

	def test_exterior_paraiso_collects(self) -> None:
		from l10n_ec.sri.form103 import collect_103

		voucher = _voucher([_row("501A", 500.0, 37.0, 185.0, code="9")], sri_exterior_regime="paraiso")
		self.assertEqual(
			collect_103([voucher], 2026, 3),
			{349: 0.0, 399: 0.0, 431: 500.0, 481: 185.0, 497: 500.0, 498: 185.0, 499: 185.0},
		)

	def test_exterior_without_regime_fails_loud(self) -> None:
		from l10n_ec.sri.form103 import collect_103

		with self.assertRaises(SriVoucherError) as ctx:
			collect_103([_voucher([_row("501A", 1000.0, 10.0, 100.0, code="9")])], 2026, 3)
		self.assertIn("regime", str(ctx.exception).lower())

	def test_exterior_unsighted_pair_fails_loud(self) -> None:
		from l10n_ec.sri.form103 import collect_103

		with self.assertRaises(SriVoucherError) as ctx:
			collect_103(
				[_voucher([_row("502", 1000.0, 25.0, 250.0, code="9")], sri_exterior_regime="sin")],
				2026,
				3,
			)
		self.assertIn("502", str(ctx.exception))


class TestCollect103ExteriorRegimes(UnitTestCase):
	"""Same concepto in two regimes renders two rows (never merged)."""

	def test_same_concepto_two_regimes(self) -> None:
		from l10n_ec.sri.form103 import build_103_rows, collect_103, collect_103_by_concepto

		vouchers = [
			_voucher([_row("501A", 1000.0, 10.0, 100.0, code="9")], sri_exterior_regime="con"),
			_voucher(
				[_row("501A", 500.0, 37.0, 185.0, code="9")],
				sri_number="001-001-000000008",
				sri_exterior_regime="paraiso",
			),
		]
		totals = collect_103(vouchers, 2026, 3)
		self.assertEqual(
			totals,
			{
				349: 0.0,
				399: 0.0,
				410: 1000.0,
				431: 500.0,
				460: 100.0,
				481: 185.0,
				497: 1500.0,
				498: 285.0,
				499: 285.0,
			},
		)
		rows = build_103_rows(totals, collect_103_by_concepto(vouchers, 2026, 3))
		conceptos = [r for r in rows if r["kind"] == "exterior"]
		self.assertEqual(len(conceptos), 2)
		self.assertEqual({(r["cas_base"], r["impuesto"]) for r in conceptos}, {(410, 100.0), (431, 185.0)})
		subtotal = next(r for r in rows if r["kind"] == "subtotal" and r["cas_base"] == 497)
		self.assertEqual((subtotal["base"], subtotal["impuesto"]), (1500.0, 285.0))


class TestCollect103ReembolsoRegression(UnitTestCase):
	"""T3 (S2): collect_103 flow unchanged by reimbursements.

	Assumption: reimbursement IVA stays out of Form 103; withholdings own
	the credit and T4 accounting owns the reimbursement IVA treatment.
	"""

	def test_reembolso_context_leaves_103_totals_unchanged(self) -> None:
		from l10n_ec.sri.form103 import collect_103

		voucher = _voucher(
			[
				_row("303", 1000.0, 10.0, 100.0),
				_row("312", 500.0, 2.0, 10.0),
			]
		)
		expected = {
			303: 1000.0,
			312: 500.0,
			349: 1500.0,
			353: 100.0,
			362: 10.0,
			399: 110.0,
			497: 0.0,
			498: 0.0,
			499: 110.0,
		}
		self.assertEqual(collect_103([voucher], 2026, 3), expected)


class TestCollect103Subtotals(UnitTestCase):
	"""Portal subtotals computed from collected boxes (template formula)."""

	def test_residentes_subtotals(self) -> None:
		from l10n_ec.sri.form103 import collect_103

		totals = collect_103(
			[_voucher([_row("303", 1000.0, 10.0, 100.0), _row("309", 500.0, 3.0, 30.0)])],
			2026,
			3,
		)
		self.assertEqual(totals[349], 1500.0)
		self.assertEqual(totals[399], 100.0)

	def test_total_499_sums_399_plus_498(self) -> None:
		from l10n_ec.sri.form103 import collect_103

		totals = collect_103(
			[
				_voucher([_row("303", 1000.0, 10.0, 100.0)]),
				_voucher(
					[_row("501A", 1000.0, 10.0, 100.0, code="9")],
					sri_number="001-001-000000008",
					sri_exterior_regime="con",
				),
			],
			2026,
			3,
		)
		self.assertEqual(totals[497], 1000.0)
		self.assertEqual(totals[498], 100.0)
		self.assertEqual(totals[499], 200.0)

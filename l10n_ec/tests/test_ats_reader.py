"""Unit tests for the ATS reader shaping helpers (pure Python)."""

import unittest

from l10n_ec.ecuador_localization.ats_reader import (
	is_reportable_purchase_number,
	is_sri_number,
	purchase_row,
	sale_row,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

TAXES = [{"code": "2", "rate_code": "4", "base": 100.0, "value": 15.0}]


class TestSriNumber(unittest.TestCase):
	def test_valid_numbers_pass(self) -> None:
		self.assertTrue(is_sri_number("001-001-000000001"))

	def test_invalid_numbers_fail(self) -> None:
		self.assertFalse(is_sri_number("DEMO-BILL-001"))
		self.assertFalse(is_sri_number(""))
		self.assertFalse(is_sri_number(None))


class TestPurchaseRow(unittest.TestCase):
	def _pi(self, **overrides):
		base = {
			"bill_no": "001-001-000000007",
			"bill_date": "20/10/2026",
			"posting_date": "21/10/2026",
			"grand_total": 115.0,
			"sri_supplier_auth_number": "1234567890",
			"taxes": TAXES,
		}
		base.update(overrides)
		return base

	def _supplier(self):
		return {
			"sri_identification_type": "04",
			"tax_id": "1790016919001",
			"supplier_name": "Demo Supplier",
		}

	def test_row_without_voucher_has_no_withholdings(self) -> None:
		row = purchase_row(self._pi(), self._supplier(), None)
		self.assertEqual(row["sri_number"], "001-001-000000007")
		self.assertEqual(row["auth_number"], "1234567890")
		self.assertNotIn("withholdings", row)
		self.assertNotIn("retencion", row)

	def test_authorized_voucher_adds_withholdings_and_retencion(self) -> None:
		voucher = {
			"voucher_state": "Authorized",
			"sri_number": "001-001-000000101",
			"authorization_number": "AUTH101",
			"authorization_date": "22/10/2026",
			"body": {
				"docs": [
					{"withholdings": [{"withholding_code": "312", "base": 100.0, "rate": 2.0, "value": 2.0}]}
				]
			},
		}
		row = purchase_row(self._pi(), self._supplier(), voucher)
		self.assertEqual(len(row["withholdings"]), 1)
		self.assertEqual(row["withholdings"][0]["concepto"], "312")
		self.assertEqual(row["retencion"]["number"], "001-001-000000101")

	def test_rejected_voucher_contributes_nothing(self) -> None:
		voucher = {"voucher_state": "Rejected", "body": {"docs": []}}
		row = purchase_row(self._pi(), self._supplier(), voucher)
		self.assertNotIn("withholdings", row)
		self.assertNotIn("retencion", row)


class TestSaleRow(unittest.TestCase):
	def test_row_without_settlement_has_no_received(self) -> None:
		row = sale_row({"posting_date": "21/10/2026", "grand_total": 1150.0, "taxes": TAXES}, {}, None, None)
		self.assertEqual(row["doc_code"], "01")
		self.assertNotIn("received", row)

	def test_settlement_adds_received_block(self) -> None:
		si = {
			"posting_date": "21/10/2026",
			"grand_total": 1150.0,
			"taxes": TAXES,
			"sri_received_retencion_number": "001-001-000000101",
			"sri_received_retencion_auth": "AUTH101",
			"sri_received_retencion_date": "22/10/2026",
			"sri_received_retencion_key": "1" * 49,
		}
		row = sale_row(
			si,
			{},
			{"sri_number": "001-001-000000050", "authorization_number": "AUTHP"},
			{"iva_value": 150.0, "renta_value": 100.0},
		)
		self.assertEqual(row["sri_number"], "001-001-000000050")
		self.assertEqual(row["received"]["iva_value"], 150.0)
		self.assertEqual(row["received"]["renta_value"], 100.0)


if __name__ == "__main__":
	unittest.main()


class TestGenerateAtsFiles(UnitTestCase):
	def test_pipeline_builds_valid_xml_and_zip(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import generate_ats_files

		def reader(company, year, month):
			return {
				"informante": {"IdInformante": "1760013210001", "razonSocial": "Demo Ecuador"},
				"purchases": [
					{
						"supplier_id_type": "04",
						"supplier_id": "1790016919001",
						"supplier_name": "Demo Supplier",
						"sustento_code": "02",
						"doc_code": "01",
						"sri_number": "001-001-000000007",
						"issue_date": "20/10/2026",
						"register_date": "21/10/2026",
						"auth_number": "1234567890",
						"taxes": [{"code": "2", "rate_code": "4", "base": 100.0, "value": 15.0}],
						"payments": [{"method": "01", "amount": 115.0}],
					}
				],
				"sales": [],
				"exports": [],
				"cancelled": [],
			}

		result = generate_ats_files("Demo Ecuador", 2026, 10, reader=reader)
		self.assertIn("<iva>", result["xml"])
		self.assertEqual(result["counts"]["compras"], 1)
		self.assertTrue(result["zip"].startswith(b"PK"))


class TestClassifyPurchase(UnitTestCase):
	def test_normal_invoice_is_01(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import classify_purchase

		self.assertEqual(classify_purchase(False, False, False), "01")

	def test_return_is_04(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import classify_purchase

		self.assertEqual(classify_purchase(True, False, False), "04")

	def test_supplier_debit_note_is_05(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import classify_purchase

		self.assertEqual(classify_purchase(False, False, True), "05")

	def test_liquidacion_is_03(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import classify_purchase

		self.assertEqual(classify_purchase(False, True, False), "03")

	def test_return_plus_liquidacion_raises(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import classify_purchase

		with self.assertRaises(ValueError):
			classify_purchase(True, True, False)


class TestPurchaseDocCode(UnitTestCase):
	def test_liquidacion_uses_voucher_numbers(self) -> None:
		voucher = {
			"voucher_state": "Authorized",
			"sri_number": "001-001-000000101",
			"authorization_number": "AUTH101",
			"authorization_date": "22/10/2026",
			"body": {"docs": []},
		}
		pi = {
			"bill_no": "",
			"bill_date": "20/10/2026",
			"posting_date": "21/10/2026",
			"grand_total": 100.0,
			"sri_supplier_auth_number": "",
			"taxes": [],
		}
		row = purchase_row(pi, {}, voucher, "03")
		self.assertEqual(row["doc_code"], "03")
		self.assertEqual(row["sri_number"], "001-001-000000101")
		self.assertEqual(row["auth_number"], "AUTH101")


class TestSustentoCode(unittest.TestCase):
	def test_explicit_sustento_flows_through(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import purchase_row

		row = purchase_row(
			{
				"bill_no": "001-001-000000007",
				"bill_date": "20/10/2026",
				"posting_date": "21/10/2026",
				"grand_total": 115.0,
				"sri_sustento_code": "06",
				"taxes": [],
			},
			{},
			None,
		)
		self.assertEqual(row["sustento_code"], "06")

	def test_missing_sustento_defaults_02(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import purchase_row

		row = purchase_row({"bill_no": "001-001-000000007", "taxes": []}, {}, None)
		self.assertEqual(row["sustento_code"], "02")


class TestReimbursementRow(unittest.TestCase):
	"""T3 (S3,S5): 41 classification plus reimbursement shaping."""

	def test_reimbursement_flag_returns_41(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import classify_purchase

		self.assertEqual(classify_purchase(False, False, False, True), "41")

	def test_reimbursement_conflicts_fail_loud(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import classify_purchase

		for flags in ((True, False, False, True), (False, True, False, True), (False, False, True, True)):
			with self.subTest(flags=flags):
				with self.assertRaises(ValueError):
					classify_purchase(*flags)

	def test_purchase_row_maps_reimbursement_details(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import purchase_row

		pi = {
			"bill_no": "001-001-000000041",
			"bill_date": "20/10/2026",
			"posting_date": "21/10/2026",
			"grand_total": 115.0,
			"sri_supplier_auth_number": "1234567890",
			"taxes": [],
			"sri_reimbursement_details": [
				{
					"doc_code": "01",
					"supplier_id_type": "04",
					"supplier_id": "1790016919001",
					"sri_number": "001-001-000000010",
					"issue_date": "2026-03-15",
					"auth_number": "1234567890",
					"base_amount": 100.0,
					"taxed_base": 50.0,
					"no_tax_base": 10.0,
					"exempt_base": 5.0,
					"ice_amount": 1.0,
					"iva_amount": 7.5,
				}
			],
			"sri_reimbursement_override_value": 10.0,
			"sri_allow_reimbursement_override": 1,
		}
		row = purchase_row(pi, {}, None, "41")
		self.assertEqual(len(row["reembolsos"]), 1)
		self.assertEqual(row["reembolsos"][0]["doc_code"], "01")
		self.assertEqual(row["reembolso_override"], 10.0)
		self.assertTrue(row["reembolso_allow_override"])


class TestIceAmount(unittest.TestCase):
	def test_ice_values_sum_into_monto(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import purchase_row, sale_row

		pi = {
			"bill_no": "001-001-000000015",
			"bill_date": "20/10/2026",
			"posting_date": "21/10/2026",
			"grand_total": 52.50,
			"taxes": [{"code": "3", "rate_code": "3072", "base": 50.0, "value": 2.50}],
		}
		self.assertEqual(purchase_row(pi, {}, None)["ice_amount"], 2.50)
		si = {"posting_date": "21/10/2026", "grand_total": 52.50, "taxes": pi["taxes"]}
		self.assertEqual(sale_row(si, {}, None, None)["ice_amount"], 2.50)

	def test_no_ice_taxes_yield_zero(self) -> None:
		from l10n_ec.ecuador_localization.ats_reader import purchase_row

		pi = {
			"bill_no": "001-001-000000011",
			"taxes": [{"code": "2", "rate_code": "4", "base": 100.0, "value": 15.0}],
		}
		self.assertEqual(purchase_row(pi, {}, None)["ice_amount"], 0.0)


class TestImportPurchaseRowPin(UnitTestCase):
	"""T5 (S3): settlement-linked imports classify exactly like plain 01s.

	The vendored ATS XSD carries no import marker (only codSustento /
	tpIdProv / tipoProv), so the reader intentionally applies no
	special-casing: an import-shaped PI keeps its sustento and supplier
	identity through the generic path.
	"""

	def test_import_shaped_pi_keeps_sustento_and_identity(self) -> None:
		pi = {
			"bill_no": "IMP-2026-000001",
			"bill_date": "20/10/2026",
			"posting_date": "21/10/2026",
			"grand_total": 1250.0,
			"sri_sustento_code": "06 - Inventario gravado",
			"sri_supplier_auth_number": "DAI-123",
			"taxes": [{"code": "2", "rate_code": "4", "base": 1000.0, "value": 150.0}],
		}
		supplier = {
			"sri_identification_type": "03",
			"tax_id": "990001000000001",
			"supplier_name": "Demo Spain Co",
		}
		row = purchase_row(pi, supplier, None, "01")
		self.assertEqual(row["doc_code"], "01")
		self.assertEqual(row["sustento_code"], "06")
		self.assertEqual(row["supplier_id"], "990001000000001")
		self.assertEqual(row["supplier_id_type"], "03")


class TestReportablePurchaseNumber(UnitTestCase):
	"""T5b: exterior 15-digit numbers report; local garbage still drops."""

	def test_sri_number_reports(self) -> None:
		self.assertTrue(is_reportable_purchase_number("001-001-000000001"))

	def test_exterior_run_reports(self) -> None:
		self.assertTrue(is_reportable_purchase_number("990001000000001"))

	def test_local_placeholder_still_drops(self) -> None:
		self.assertFalse(is_reportable_purchase_number("DEMO-BILL-001"))
		self.assertFalse(is_reportable_purchase_number(""))
		self.assertFalse(is_reportable_purchase_number(None))

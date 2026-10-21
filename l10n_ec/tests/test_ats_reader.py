"""Unit tests for the ATS reader shaping helpers (pure Python)."""

import unittest

from l10n_ec.ecuador_localization.ats_reader import is_sri_number, purchase_row, sale_row

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
		row = sale_row(si, {}, {"sri_number": "001-001-000000050", "authorization_number": "AUTHP"}, {"iva_value": 150.0, "renta_value": 100.0})
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

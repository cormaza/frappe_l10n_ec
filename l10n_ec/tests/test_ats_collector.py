"""Unit tests for the ATS month collector (pure parts, no frappe)."""

import unittest

from l10n_ec.sri.ats_collector import (
	collect_cancelled,
	collect_export,
	collect_month,
	collect_purchase,
	collect_sale,
	split_iva_bases,
	split_sri_number,
)
from l10n_ec.sri.voucher_states import SriVoucherError

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


def _purchase(**overrides):
	doc = {
		"docstatus": 1,
		"supplier_id_type": "04",
		"supplier_id": "1790016919001",
		"supplier_name": "Demo Supplier",
		"sustento_code": "02",
		"doc_code": "01",
		"sri_number": "001-001-000000123",
		"issue_date": "15/03/2026",
		"register_date": "20/03/2026",
		"auth_number": "1234567890",
		"taxes": [
			{"code": "2", "rate_code": "4", "base": 1000.0, "value": 150.0},
		],
		"ice_amount": 0.0,
		"payments": [{"method": "01", "amount": 1150.0}],
		"withholdings": [
			{"concepto": "303", "base": 1000.0, "rate": 10.0, "value": 100.0},
			{"concepto": "2", "base": 150.0, "rate": 70.0, "value": 105.0},
		],
		"retencion": {
			"number": "001-001-000000007",
			"authorization": "1234567890",
			"date": "25/03/2026",
		},
	}
	doc.update(overrides)
	return doc


def _sale(**overrides):
	doc = {
		"docstatus": 1,
		"customer_id_type": "04",
		"customer_id": "1790016919001",
		"customer_name": "Demo Customer",
		"doc_code": "01",
		"emission": "E",
		"sri_number": "001-001-000000321",
		"issue_date": "15/03/2026",
		"auth_number": "1234567890",
		"taxes": [
			{"code": "2", "rate_code": "4", "base": 1000.0, "value": 150.0},
		],
		"ice_amount": 0.0,
		"payments": [{"method": "19", "amount": 1150.0}],
		"received": {
			"retencion_number": "001-002-000000009",
			"authorization": "0987654321",
			"date": "28/03/2026",
			"access_key": "1" * 49,
			"iva_value": 105.0,
			"renta_value": 20.0,
		},
	}
	doc.update(overrides)
	return doc


def _reader(**sections):
	def _read(company, year, month):
		assert (company, year, month) == ("Demo Company", 2026, 3)
		return sections

	return _read


class TestCollectMonth(UnitTestCase):
	def test_month_mix_aggregates_all_sections(self) -> None:
		result = collect_month(
			"Demo Company",
			2026,
			3,
			_reader(
				purchases=[_purchase()],
				sales=[_sale()],
				exports=[
					{
						"exportacion_de": "01",
						"doc_code": "01",
						"sri_number": "001-001-000000400",
						"issue_date": "15/03/2026",
						"auth_number": "1234567890",
						"embarque_date": "16/03/2026",
						"fob_value": 5000.0,
						"voucher_fob_value": 5000.0,
					}
				],
				cancelled=[
					{"doc_code": "01", "sri_number": "001-001-000000124", "auth_number": "1234567890"}
				],
			),
		)
		self.assertEqual(set(result), {"compras", "ventas", "exportaciones", "anulados"})
		self.assertEqual(len(result["compras"]), 1)
		self.assertEqual(len(result["ventas"]), 1)
		self.assertEqual(len(result["exportaciones"]), 1)
		self.assertEqual(len(result["anulados"]), 1)

	def test_empty_month_returns_empty_lists(self) -> None:
		result = collect_month("Demo Company", 2026, 3, _reader())
		self.assertEqual(result, {"compras": [], "ventas": [], "exportaciones": [], "anulados": []})

	def test_draft_rows_are_skipped(self) -> None:
		result = collect_month(
			"Demo Company",
			2026,
			3,
			_reader(purchases=[_purchase(docstatus=0)], sales=[_sale(docstatus=0)]),
		)
		self.assertEqual(result["compras"], [])
		self.assertEqual(result["ventas"], [])

	def test_bad_period_fails_loud(self) -> None:
		for company, year, month in (("", 2026, 3), ("Demo Company", 1999, 3), ("Demo Company", 2026, 13)):
			with self.subTest(company=company, year=year, month=month):
				with self.assertRaises(SriVoucherError):
					collect_month(company, year, month, _reader())


class TestCollectPurchase(UnitTestCase):
	def test_ir_and_iva_withholdings_split(self) -> None:
		row = collect_purchase(_purchase())
		self.assertEqual(row["codSustento"], "02")
		self.assertEqual(row["idProv"], "1790016919001")
		self.assertEqual(row["establecimiento"], "001")
		self.assertEqual(row["puntoEmision"], "001")
		self.assertEqual(row["secuencial"], "000000123")
		self.assertEqual(row["baseImpGrav"], 1000.0)
		self.assertEqual(row["montoIva"], 150.0)
		self.assertEqual(row["montoIce"], 0.0)
		self.assertEqual(
			row["air"],
			[{"codRetAir": "303", "baseImpAir": 1000.0, "porcentajeAir": 10.0, "valRetAir": 100.0}],
		)
		self.assertEqual(row["valorRetServicios"], 105.0)
		self.assertEqual(row["valorRetBienes"], 0.0)
		self.assertEqual(row["formasDePago"], ["01"])
		self.assertEqual(row["estabRetencion1"], "001")
		self.assertEqual(row["secRetencion1"], "000000007")

	def test_template_taxes_resolve_and_ice_passes_through(self) -> None:
		row = collect_purchase(
			_purchase(
				taxes=[{"template": "Ecuador VAT 15% - Purchases", "base": 200.0, "value": 30.0}],
				ice_amount=12.5,
				withholdings=[],
				retencion={},
			)
		)
		self.assertEqual(row["baseImpGrav"], 200.0)
		self.assertEqual(row["montoIva"], 30.0)
		self.assertEqual(row["montoIce"], 12.5)
		self.assertEqual(row["air"], [])

	def test_missing_payments_default_to_01(self) -> None:
		row = collect_purchase(_purchase(payments=[]))
		self.assertEqual(row["formasDePago"], ["01"])

	def test_unknown_concepto_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_purchase(
				_purchase(withholdings=[{"concepto": "9999", "base": 1.0, "rate": 1.0, "value": 1.0}])
			)

	def test_exterior_scope_concepto_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_purchase(
				_purchase(withholdings=[{"concepto": "501", "base": 1.0, "rate": 1.0, "value": 1.0}])
			)

	def test_rate_mismatch_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_purchase(
				_purchase(withholdings=[{"concepto": "303", "base": 1000.0, "rate": 8.0, "value": 80.0}])
			)

	def test_unknown_payment_code_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_purchase(_purchase(payments=[{"method": "99", "amount": 1.0}]))

	def test_bad_sri_number_fails_loud(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_purchase(_purchase(sri_number="nope"))

	def test_non_iva_taxes_skip_bases(self) -> None:
		row = collect_purchase(
			_purchase(
				taxes=[{"code": "3", "rate_code": "", "base": 50.0, "value": 5.0}],
				withholdings=[],
				retencion={},
			)
		)
		self.assertEqual(row["baseImpGrav"], 0.0)
		self.assertEqual(row["montoIva"], 0.0)

	def test_zero_rate_iva_concepto_has_no_bucket(self) -> None:
		with self.assertRaises(SriVoucherError):
			collect_purchase(
				_purchase(withholdings=[{"concepto": "7", "base": 100.0, "rate": 0.0, "value": 0.0}])
			)


class TestCollectSale(UnitTestCase):
	def test_received_refs_feed_ventas_credit(self) -> None:
		row = collect_sale(_sale())
		self.assertEqual(row["idCliente"], "1790016919001")
		self.assertEqual(row["tipoEmision"], "E")
		self.assertEqual(row["numeroComprobantes"], 1)
		self.assertEqual(row["baseImpGrav"], 1000.0)
		self.assertEqual(row["montoIva"], 150.0)
		self.assertEqual(row["valorRetIva"], 105.0)
		self.assertEqual(row["valorRetRenta"], 20.0)
		self.assertEqual(row["formasDePago"], ["19"])
		self.assertEqual(row["received_number"], "001-002-000000009")
		self.assertEqual(row["received_access_key"], "1" * 49)

	def test_sale_without_received_settlement_zeroes_credit(self) -> None:
		row = collect_sale(_sale(received={}))
		self.assertEqual(row["valorRetIva"], 0.0)
		self.assertEqual(row["valorRetRenta"], 0.0)
		self.assertNotIn("received_number", row)


class TestExportsAndAnulados(UnitTestCase):
	def test_export_row_carries_fob_and_sri_numbers(self) -> None:
		row = collect_export(
			{
				"exportacion_de": "01",
				"doc_code": "01",
				"sri_number": "001-001-000000400",
				"issue_date": "15/03/2026",
				"auth_number": "1234567890",
				"embarque_date": "16/03/2026",
				"fob_value": 5000.0,
				"voucher_fob_value": 5000.0,
			}
		)
		self.assertEqual(row["exportacionDe"], "01")
		self.assertEqual(row["valorFOB"], 5000.0)
		self.assertEqual(row["secuencial"], "000000400")
		self.assertEqual(row["fechaEmbarque"], "16/03/2026")

	def test_cancelled_row_feeds_anulados_range(self) -> None:
		row = collect_cancelled(
			{"doc_code": "01", "sri_number": "001-001-000000124", "auth_number": "1234567890"}
		)
		self.assertEqual(row["tipoComprobante"], "01")
		self.assertEqual(row["establecimiento"], "001")
		self.assertEqual(row["puntoEmision"], "001")
		self.assertEqual(row["secuencialInicio"], "000000124")
		self.assertEqual(row["secuencialFin"], "000000124")
		self.assertEqual(row["autorizacion"], "1234567890")


class TestHelpers(UnitTestCase):
	def test_split_sri_number(self) -> None:
		self.assertEqual(split_sri_number("001-002-000000123"), ("001", "002", "000000123"))
		with self.assertRaises(SriVoucherError):
			split_sri_number("001-002")

	def test_split_iva_bases_by_rate_code(self) -> None:
		bases = split_iva_bases(
			[
				{"code": "2", "rate_code": "6", "base": 10.0, "value": 0.0},
				{"code": "2", "rate_code": "0", "base": 20.0, "value": 0.0},
				{"code": "2", "rate_code": "4", "base": 100.0, "value": 15.0},
				{"code": "2", "rate_code": "7", "base": 5.0, "value": 0.0},
			]
		)
		self.assertEqual(bases["baseNoGraIva"], 10.0)
		self.assertEqual(bases["baseImponible"], 20.0)
		self.assertEqual(bases["baseImpGrav"], 100.0)
		self.assertEqual(bases["baseImpExe"], 5.0)
		self.assertEqual(bases["montoIva"], 15.0)


if __name__ == "__main__":
	unittest.main()


class TestCreditNoteAbsValues(UnitTestCase):
	def test_04_amounts_report_positive(self) -> None:
		from l10n_ec.sri.ats_collector import collect_purchase

		row = collect_purchase(
			{
				"sri_number": "001-001-000000050",
				"doc_code": "04",
				"supplier_id_type": "04",
				"supplier_id": "1790016919001",
				"issue_date": "21/10/2026",
				"auth_number": "1234567890",
				"taxes": [{"code": "2", "rate_code": "4", "base": -20.0, "value": -3.0}],
			}
		)
		self.assertEqual(row["tipoComprobante"], "04")
		self.assertEqual(row["baseImpGrav"], 20.0)
		self.assertEqual(row["montoIva"], 3.0)

	def test_01_amounts_pass_through(self) -> None:
		from l10n_ec.sri.ats_collector import collect_purchase

		row = collect_purchase(
			{
				"sri_number": "001-001-000000007",
				"doc_code": "01",
				"supplier_id_type": "04",
				"supplier_id": "1790016919001",
				"issue_date": "20/10/2026",
				"auth_number": "1234567890",
				"taxes": [{"code": "2", "rate_code": "4", "base": 100.0, "value": 15.0}],
			}
		)
		self.assertEqual(row["baseImpGrav"], 100.0)

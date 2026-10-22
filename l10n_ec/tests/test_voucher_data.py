"""Round-trip tests: emitted SRI XML parses back to RIDE display data."""

import unittest

from l10n_ec.sri.voucher_data import parse_emitted_xml
from l10n_ec.sri.xml_builder import build_guia_xml, build_retencion_xml

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

CTX = {
	"environment": "1",
	"doc_code": "06",
	"ruc": "1790016919001",
	"legal_name": "PRUEBAS SERVICIO DE RENTAS INTERNAS",
	"head_office_address": "Av. Amazonas y Naciones Unidas",
	"establishment": "001",
	"emission_point": "001",
	"sequential": "000000001",
	"access_key": "1710202606112345678901234567890123456789012",
	"branch_address": "Av. Amazonas y Naciones Unidas",
	"special_taxpayer": "",
	"accounting_required": True,
}


class TestEmittedVoucherData(UnitTestCase):
	def test_guia_round_trip(self) -> None:
		data = {
			"issue_date": "21/10/2026",
			"origin_address": "Av. Amazonas y Naciones Unidas",
			"carrier_name": "TRANSPORTES EJEMPLO SA",
			"carrier_id_type": "04",
			"carrier_id": "1790016919001",
			"transport_start": "21/10/2026",
			"transport_end": "22/10/2026",
			"plate": "ABC1234",
			"recipients": [
				{
					"recipient_id": "1710034065",
					"recipient_name": "COMPRADOR EJEMPLO",
					"recipient_address": "Av. 6 de Diciembre",
					"transfer_reason": "Venta",
					"route": "Quito-Guayaquil",
					"doc_code": "01",
					"doc_number": "001-001-000012345",
					"auth_number": "1234567890",
					"doc_issue_date": "20/10/2026",
					"lines": [
						{
							"code": "DEMO-WIDGET",
							"aux_code": "WIDGET-AUX",
							"description": "Demo widget",
							"qty": 2.0,
						}
					],
				}
			],
		}
		parsed = parse_emitted_xml(build_guia_xml(CTX, data))
		self.assertEqual(parsed["kind"], "guia")
		self.assertEqual(parsed["plate"], "ABC1234")
		self.assertEqual(parsed["carrier_name"], "TRANSPORTES EJEMPLO SA")
		self.assertEqual(parsed["carrier_id"], "1790016919001")
		self.assertEqual(parsed["origin_address"], "Av. Amazonas y Naciones Unidas")
		self.assertEqual(len(parsed["recipients"]), 1)
		recipient = parsed["recipients"][0]
		self.assertEqual(recipient["recipient_name"], "COMPRADOR EJEMPLO")
		self.assertEqual(recipient["doc_number"], "001-001-000012345")
		self.assertEqual(recipient["lines"][0]["code"], "DEMO-WIDGET")

	def test_retencion_round_trip(self) -> None:
		data = {
			"issue_date": "21/10/2026",
			"subject_id_type": "04",
			"related_party": "NO",
			"subject_name": "EMPRESA EJEMPLO SA",
			"subject_id": "1790016919001",
			"fiscal_period": "10/2026",
			"docs": [
				{
					"sustento_code": "01",
					"doc_code": "01",
					"doc_number": "001-001-000000001",
					"issue_date": "20/10/2026",
					"auth_number": "1234567890",
					"local_payment": "01",
					"subtotal": 100.00,
					"total": 115.00,
					"doc_taxes": [
						{
							"tax_code": "2",
							"rate_code": "4",
							"base": 100.00,
							"rate": 15.0,
							"tax_value": 15.00,
						}
					],
					"withholdings": [
						{
							"code": "1",
							"withholding_code": "303",
							"base": 100.00,
							"rate": 1.0,
							"value": 1.00,
						}
					],
					"payments": [{"method": "01", "amount": 115.00}],
				}
			],
		}
		parsed = parse_emitted_xml(build_retencion_xml(CTX, data))
		self.assertEqual(parsed["kind"], "retencion")
		self.assertEqual(parsed["subject_name"], "EMPRESA EJEMPLO SA")
		self.assertEqual(parsed["subject_id"], "1790016919001")
		self.assertEqual(parsed["fiscal_period"], "10/2026")
		self.assertEqual(len(parsed["docs"]), 1)
		sustento = parsed["docs"][0]
		self.assertEqual(sustento["doc_number"], "001001000000001")
		withholding = sustento["withholdings"][0]
		self.assertEqual(withholding["withholding_code"], "303")
		self.assertAlmostEqual(withholding["value"], 1.00)


if __name__ == "__main__":
	unittest.main()


class TestFacturaRoundTrip(UnitTestCase):
	def test_factura_round_trip(self) -> None:
		from l10n_ec.sri.xml_builder import build_factura_xml

		ctx = dict(CTX)
		ctx["doc_code"] = "01"
		xml = build_factura_xml(
			ctx,
			{
				"issue_date": "20/10/2026",
				"buyer_id_type": "07",
				"buyer_name": "CONSUMIDOR FINAL",
				"buyer_id": "9999999999999",
				"buyer_address": "",
				"subtotal": 100.00,
				"discount": 0.0,
				"tax_totals": [{"code": "2", "rate_code": "4", "base": 100.00, "value": 15.00}],
				"tip": 0.0,
				"total": 115.00,
				"payments": [{"method": "01", "amount": 115.00}],
				"lines": [
					{
						"code": "DEMO-WIDGET",
						"description": "Demo widget",
						"qty": 1.0,
						"unit_price": 100.00,
						"discount": 0.0,
						"subtotal": 100.00,
						"total": 100.00,
						"taxes": [],
					}
				],
			},
		)
		parsed = parse_emitted_xml(xml)
		self.assertEqual(parsed["kind"], "factura")
		self.assertEqual(parsed["number"], "001-001-000000001")
		self.assertEqual(parsed["buyer_id"], "9999999999999")
		self.assertEqual(parsed["total"], 115.00)
		self.assertEqual(parsed["taxes"], [{"code": "2", "rate_code": "4", "base": 100.0, "value": 15.0}])

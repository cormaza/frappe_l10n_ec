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
		line = parsed["lines"][0]
		self.assertEqual(line["code"], "DEMO-WIDGET")
		self.assertEqual(line["qty"], 1.0)
		self.assertEqual(line["total"], 100.0)


class TestNotaCreditoDebitoRoundTrip(UnitTestCase):
	def test_nota_credito_round_trip(self) -> None:
		from l10n_ec.sri.xml_builder import build_nota_credito_xml

		ctx = dict(CTX)
		ctx["doc_code"] = "04"
		xml = build_nota_credito_xml(
			ctx,
			{
				"issue_date": "21/10/2026",
				"buyer_id_type": "04",
				"buyer_name": "EMPRESA EJEMPLO SA",
				"buyer_id": "1790016919001",
				"modified_doc_code": "01",
				"modified_doc_number": "001-001-000000001",
				"sustento_issue_date": "20/10/2026",
				"subtotal": 100.00,
				"adjustment_value": 115.00,
				"tax_totals": [{"code": "2", "rate_code": "4", "base": 100.00, "value": 15.00}],
				"reason": "Devolucion de mercaderia",
				"lines": [
					{
						"code": "PROD001",
						"aux_code": "",
						"description": "Servicio de consultoria",
						"qty": 1,
						"unit_price": 100.00,
						"discount": 0.0,
						"subtotal": 100.00,
						"taxes": [
							{"code": "2", "rate_code": "4", "rate": 15.0, "base": 100.00, "value": 15.00}
						],
					}
				],
			},
		)
		parsed = parse_emitted_xml(xml)
		self.assertEqual(parsed["kind"], "nota_credito")
		self.assertEqual(parsed["number"], "001-001-000000001")
		self.assertEqual(parsed["modified_doc_number"], "001-001-000000001")
		self.assertEqual(parsed["adjustment_value"], 115.00)
		self.assertEqual(parsed["lines"][0]["code"], "PROD001")

	def test_nota_debito_round_trip(self) -> None:
		from l10n_ec.sri.xml_builder import build_nota_debito_xml

		ctx = dict(CTX)
		ctx["doc_code"] = "05"
		xml = build_nota_debito_xml(
			ctx,
			{
				"issue_date": "21/10/2026",
				"buyer_id_type": "04",
				"buyer_name": "EMPRESA EJEMPLO SA",
				"buyer_id": "1790016919001",
				"modified_doc_code": "01",
				"modified_doc_number": "001-001-000000002",
				"sustento_issue_date": "20/10/2026",
				"subtotal": 100.00,
				"taxes": [{"code": "2", "rate_code": "4", "rate": 15.0, "base": 100.00, "value": 15.00}],
				"total_value": 115.00,
				"reasons": [{"reason": "Intereses", "value": 15.00}],
			},
		)
		parsed = parse_emitted_xml(xml)
		self.assertEqual(parsed["kind"], "nota_debito")
		self.assertEqual(parsed["number"], "001-001-000000001")
		self.assertEqual(parsed["total_value"], 115.00)
		self.assertEqual(parsed["reasons"][0]["reason"], "Intereses")


class TestReembolsoRoundTrip(UnitTestCase):
	def test_factura_reembolsos_round_trip(self) -> None:
		from l10n_ec.sri.xml_builder import build_factura_xml

		ctx = dict(CTX)
		ctx["doc_code"] = "01"
		reembolso = {
			"doc_code": "01",
			"supplier_id_type": "04",
			"supplier_id": "1790016919001",
			"supplier_country": "593",
			"sri_number": "001-001-000000001",
			"issue_date": "20/10/2026",
			"auth_number": "1234567890",
			"taxes": [
				{
					"codigo": "2",
					"codigoPorcentaje": "4",
					"tarifa": 15.0,
					"baseImponible": 100.00,
					"valor": 15.00,
				},
			],
		}
		xml = build_factura_xml(
			ctx,
			{
				"issue_date": "20/10/2026",
				"buyer_id_type": "04",
				"buyer_name": "INTERMEDIARIO EJEMPLO SA",
				"buyer_id": "1790016919001",
				"buyer_address": "",
				"subtotal": 200.00,
				"discount": 0.0,
				"tax_totals": [{"code": "2", "rate_code": "4", "base": 200.00, "value": 30.00}],
				"tip": 0.0,
				"total": 230.00,
				"payments": [{"method": "01", "amount": 230.00}],
				"lines": [
					{
						"code": "SERV-INT",
						"description": "Intermediation service",
						"qty": 1.0,
						"unit_price": 200.00,
						"discount": 0.0,
						"subtotal": 200.00,
						"total": 200.00,
						"taxes": [],
					}
				],
				"reembolsos": [reembolso],
			},
		)
		parsed = parse_emitted_xml(xml)
		self.assertEqual(parsed["kind"], "factura")
		self.assertIn("reembolsos", parsed)
		self.assertEqual(len(parsed["reembolsos"]), 1)
		entry = parsed["reembolsos"][0]
		self.assertEqual(entry["doc_code"], "01")
		self.assertEqual(entry["supplier_id_type"], "04")
		self.assertEqual(entry["supplier_id"], "1790016919001")
		self.assertEqual(entry["supplier_country"], "593")
		self.assertEqual(entry["sri_number"], "001-001-000000001")
		self.assertEqual(entry["issue_date"], "20/10/2026")
		self.assertEqual(entry["auth_number"], "1234567890")
		self.assertEqual(
			entry["taxes"],
			[{"codigo": "2", "codigoPorcentaje": "4", "tarifa": 15.0, "baseImponible": 100.0, "valor": 15.0}],
		)

	def test_factura_without_reembolsos_parses_without_key(self) -> None:
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
		self.assertNotIn("reembolsos", parsed)

	def test_liquidacion_reembolsos_round_trip(self) -> None:
		from l10n_ec.sri.xml_builder import build_liquidacion_compra_xml

		ctx = dict(CTX)
		ctx["doc_code"] = "03"
		reembolso = {
			"doc_code": "01",
			"supplier_id_type": "04",
			"supplier_id": "1790016919001",
			"sri_number": "001-001-000000001",
			"issue_date": "20/10/2026",
			"auth_number": "1234567890",
			"taxes": [
				{
					"codigo": "2",
					"codigoPorcentaje": "4",
					"tarifa": 15.0,
					"baseImponible": 100.00,
					"valor": 15.00,
				},
			],
		}
		xml = build_liquidacion_compra_xml(
			ctx,
			{
				"issue_date": "21/10/2026",
				"supplier_id_type": "05",
				"supplier_name": "JUAN PEREZ",
				"supplier_id": "1710034065",
				"supplier_address": "",
				"subtotal": 100.00,
				"discount": 0.0,
				"tax_totals": [{"code": "2", "rate_code": "4", "base": 100.00, "value": 15.00}],
				"total": 115.00,
				"payments": [{"method": "01", "amount": 115.00}],
				"lines": [
					{
						"code": "SERV-RURAL",
						"description": "Rural service",
						"qty": 1.0,
						"unit_price": 100.00,
						"discount": 0.0,
						"subtotal": 100.00,
						"total": 100.00,
						"taxes": [],
					}
				],
				"reembolsos": [reembolso],
			},
		)
		parsed = parse_emitted_xml(xml)
		self.assertEqual(parsed["kind"], "liquidacion_compra")
		self.assertEqual(parsed["number"], "001-001-000000001")
		self.assertEqual(parsed["supplier_name"], "JUAN PEREZ")
		self.assertEqual(parsed["total"], 115.00)
		self.assertEqual(len(parsed["reembolsos"]), 1)
		entry = parsed["reembolsos"][0]
		self.assertEqual(entry["doc_code"], "01")
		self.assertEqual(entry["sri_number"], "001-001-000000001")
		self.assertEqual(entry["taxes"][0]["baseImponible"], 100.0)
		self.assertEqual(entry["taxes"][0]["valor"], 15.0)

	def test_liquidacion_without_reembolsos_parses_without_key(self) -> None:
		from l10n_ec.sri.xml_builder import build_liquidacion_compra_xml

		ctx = dict(CTX)
		ctx["doc_code"] = "03"
		xml = build_liquidacion_compra_xml(
			ctx,
			{
				"issue_date": "21/10/2026",
				"supplier_id_type": "05",
				"supplier_name": "JUAN PEREZ",
				"supplier_id": "1710034065",
				"supplier_address": "",
				"subtotal": 100.00,
				"discount": 0.0,
				"tax_totals": [{"code": "2", "rate_code": "4", "base": 100.00, "value": 15.00}],
				"total": 115.00,
				"payments": [{"method": "01", "amount": 115.00}],
				"lines": [
					{
						"code": "SERV-RURAL",
						"description": "Rural service",
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
		self.assertEqual(parsed["kind"], "liquidacion_compra")
		self.assertNotIn("reembolsos", parsed)

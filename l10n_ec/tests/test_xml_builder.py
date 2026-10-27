import unittest
from datetime import date

from l10n_ec.sri.access_key import generate_access_key
from l10n_ec.sri.xml_builder import (
	SriXmlError,
	build_factura_xml,
	build_liquidacion_compra_xml,
	build_nota_credito_xml,
	build_nota_debito_xml,
	validate_against_xsd,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


def _context(cod_doc: str) -> dict:
	return {
		"environment": "1",
		"doc_code": cod_doc,
		"ruc": "1790016919001",
		"legal_name": "PRUEBAS SERVICIO DE RENTAS INTERNAS",
		"head_office_address": "Av. Amazonas y Naciones Unidas",
		"establishment": "001",
		"emission_point": "001",
		"sequential": "000000001",
		"access_key": generate_access_key(
			document_code_sri=cod_doc,
			complete_document_number="001-001-000000001",
			environment="1",
			date_document=date(2026, 10, 20),
			ruc="1790016919001",
			numeric_code="12345678",
		),
		"branch_address": "Av. Amazonas y Naciones Unidas",
		"special_taxpayer": "",
		"accounting_required": True,
	}


TAX_TOTAL = {"code": "2", "rate_code": "4", "base": 100.00, "value": 15.00}
LINE_TAX = {"code": "2", "rate_code": "4", "rate": 15.0, "base": 100.00, "value": 15.00}
LINE = {
	"code": "PROD001",
	"aux_code": "",
	"description": "Servicio de consultoria",
	"qty": 1,
	"unit_price": 100.00,
	"discount": 0.0,
	"subtotal": 100.00,
	"taxes": [LINE_TAX],
}

FACTURA_REEMBOLSO_TAXES = [
	{"codigo": "2", "codigoPorcentaje": "4", "tarifa": 15.0, "baseImponible": 100.00, "valor": 15.00},
]
FACTURA_REEMBOLSO = {
	"doc_code": "01",
	"supplier_id_type": "04",
	"supplier_id": "1790016919001",
	"sri_number": "001-001-000000001",
	"issue_date": "20/10/2026",
	"auth_number": "1234567890",
	"taxes": FACTURA_REEMBOLSO_TAXES,
}
LIQUIDACION_REEMBOLSO = {
	"doc_code": "01",
	"supplier_id_type": "04",
	"supplier_id": "1790016919001",
	"sri_number": "002-001-000000007",
	"issue_date": "20/10/2026",
	"auth_number": "1234567890",
	"taxes": [
		{"codigo": "2", "codigoPorcentaje": "4", "tarifa": 15.0, "baseImponible": 50.00, "valor": 7.50},
	],
}


class TestSriXmlBuilder(UnitTestCase):
	"""Unit tests for SRI XML generation and XSD validation (pure Python)."""

	def test_factura_validates_against_xsd(self) -> None:
		xml = build_factura_xml(
			_context("01"),
			{
				"issue_date": "20/10/2026",
				"buyer_id_type": "07",
				"buyer_name": "CONSUMIDOR FINAL",
				"buyer_id": "9999999999999",
				"buyer_address": "",
				"subtotal": 100.00,
				"discount": 0.0,
				"tax_totals": [TAX_TOTAL],
				"tip": 0.0,
				"total": 115.00,
				"payments": [{"method": "01", "amount": 115.00}],
				"lines": [LINE],
			},
		)
		self.assertTrue(validate_against_xsd(xml, "factura"))

	def test_nota_credito_validates_against_xsd(self) -> None:
		xml = build_nota_credito_xml(
			_context("04"),
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
				"tax_totals": [TAX_TOTAL],
				"reason": "Devolucion de mercaderia",
				"lines": [LINE],
			},
		)
		self.assertTrue(validate_against_xsd(xml, "nota_credito"))

	def test_nota_debito_validates_against_xsd(self) -> None:
		xml = build_nota_debito_xml(
			_context("05"),
			{
				"issue_date": "21/10/2026",
				"buyer_id_type": "04",
				"buyer_name": "EMPRESA EJEMPLO SA",
				"buyer_id": "1790016919001",
				"modified_doc_code": "01",
				"modified_doc_number": "001-001-000000001",
				"sustento_issue_date": "20/10/2026",
				"subtotal": 100.00,
				"taxes": [LINE_TAX],
				"total_value": 115.00,
				"reasons": [{"reason": "Interes por mora", "value": 15.00}],
			},
		)
		self.assertTrue(validate_against_xsd(xml, "nota_debito"))

	def test_liquidacion_compra_validates_against_xsd(self) -> None:
		xml = build_liquidacion_compra_xml(
			_context("03"),
			{
				"issue_date": "21/10/2026",
				"supplier_id_type": "05",
				"supplier_name": "JUAN PEREZ",
				"supplier_id": "1710034065",
				"supplier_address": "",
				"subtotal": 100.00,
				"discount": 0.0,
				"tax_totals": [TAX_TOTAL],
				"total": 115.00,
				"payments": [{"method": "01", "amount": 115.00}],
				"lines": [LINE],
			},
		)
		self.assertTrue(validate_against_xsd(xml, "liquidacion_compra"))

	def test_invalid_xml_raises_sri_xml_error(self) -> None:
		with self.assertRaises(SriXmlError):
			validate_against_xsd("<factura/>", "factura")


class TestFacturaReembolsos(UnitTestCase):
	"""Factura (01) emission with the SRI `<reembolsos>` block."""

	def _factura_data(self, reembolsos=None):
		data = {
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
					"aux_code": "",
					"description": "Intermediation service",
					"qty": 1,
					"unit_price": 200.00,
					"discount": 0.0,
					"subtotal": 200.00,
					"taxes": [{"code": "2", "rate_code": "4", "rate": 15.0, "base": 200.00, "value": 30.00}],
				}
			],
		}
		if reembolsos is not None:
			data["reembolsos"] = reembolsos
		return data

	def test_factura_with_reembolsos_validates_against_xsd(self) -> None:
		xml = build_factura_xml(_context("01"), self._factura_data([dict(FACTURA_REEMBOLSO)]))
		self.assertTrue(validate_against_xsd(xml, "factura"))

	def test_factura_reembolso_totals_render_in_schema_order(self) -> None:
		xml = build_factura_xml(
			_context("01"), self._factura_data([dict(FACTURA_REEMBOLSO), dict(FACTURA_REEMBOLSO)])
		)
		self.assertIn("<codDocReembolso>01</codDocReembolso>", xml)
		self.assertIn("<totalComprobantesReembolso>2.00</totalComprobantesReembolso>", xml)
		self.assertIn("<totalBaseImponibleReembolso>200.00</totalBaseImponibleReembolso>", xml)
		self.assertIn("<totalImpuestoReembolso>30.00</totalImpuestoReembolso>", xml)
		self.assertLess(xml.index("<totalDescuento>"), xml.index("<codDocReembolso>"))
		self.assertLess(xml.index("<totalImpuestoReembolso>"), xml.index("<totalConImpuestos>"))

	def test_factura_reembolso_detalle_follows_xsd_field_order(self) -> None:
		xml = build_factura_xml(_context("01"), self._factura_data([dict(FACTURA_REEMBOLSO)]))
		block = xml[xml.index("<reembolsos>") :]
		order = [
			"<tipoIdentificacionProveedorReembolso>",
			"<identificacionProveedorReembolso>",
			"<tipoProveedorReembolso>",
			"<codDocReembolso>",
			"<estabDocReembolso>",
			"<ptoEmiDocReembolso>",
			"<secuencialDocReembolso>",
			"<fechaEmisionDocReembolso>",
			"<numeroautorizacionDocReemb>",
			"<detalleImpuestos>",
			"<codigo>2</codigo>",
			"<codigoPorcentaje>4</codigoPorcentaje>",
			"<tarifa>15.00</tarifa>",
			"<baseImponibleReembolso>100.00</baseImponibleReembolso>",
			"<impuestoReembolso>15.00</impuestoReembolso>",
		]
		positions = [block.index(tag) for tag in order]
		self.assertEqual(positions, sorted(positions))
		self.assertIn("<reembolsos><reembolsoDetalle>", block)

	def test_factura_reembolso_country_renders_when_present(self) -> None:
		entry = dict(FACTURA_REEMBOLSO, supplier_country="593")
		xml = build_factura_xml(_context("01"), self._factura_data([entry]))
		self.assertIn("<codPaisPagoProveedorReembolso>593</codPaisPagoProveedorReembolso>", xml)
		self.assertTrue(validate_against_xsd(xml, "factura"))

	def test_factura_own_taxes_exclude_reembolso_bases(self) -> None:
		# Withholdings apply to the own base only, never to reembolso bases:
		# own totalConImpuestos keeps base 200 while reembolso totals carry 100.
		xml = build_factura_xml(_context("01"), self._factura_data([dict(FACTURA_REEMBOLSO)]))
		self.assertIn("<baseImponible>200.00</baseImponible>", xml)
		self.assertNotIn("<baseImponible>300.00</baseImponible>", xml)
		self.assertIn("<totalBaseImponibleReembolso>100.00</totalBaseImponibleReembolso>", xml)

	def test_factura_without_reembolsos_renders_no_block(self) -> None:
		xml = build_factura_xml(_context("01"), self._factura_data())
		self.assertNotIn("<reembolsos>", xml)
		self.assertNotIn("Reembolso", xml)
		self.assertTrue(validate_against_xsd(xml, "factura"))

	def test_factura_empty_reembolsos_renders_no_block(self) -> None:
		xml = build_factura_xml(_context("01"), self._factura_data([]))
		self.assertNotIn("<reembolsos>", xml)
		self.assertTrue(validate_against_xsd(xml, "factura"))

	def test_factura_reembolso_without_taxes_fails_loud(self) -> None:
		entry = dict(FACTURA_REEMBOLSO)
		del entry["taxes"]
		with self.assertRaises(SriXmlError):
			build_factura_xml(_context("01"), self._factura_data([entry]))

	def test_factura_reembolso_mixed_doc_codes_fail_loud(self) -> None:
		other = dict(FACTURA_REEMBOLSO, doc_code="03", sri_number="001-001-000000002")
		with self.assertRaises(SriXmlError):
			build_factura_xml(_context("01"), self._factura_data([dict(FACTURA_REEMBOLSO), other]))

	def test_factura_reembolso_bad_number_fails_loud(self) -> None:
		entry = dict(FACTURA_REEMBOLSO, sri_number="001001000000001")
		with self.assertRaises(SriXmlError):
			build_factura_xml(_context("01"), self._factura_data([entry]))


class TestLiquidacionReembolsos(UnitTestCase):
	"""Liquidacion de compra (03) emission with the SRI `<reembolsos>` block."""

	def _liquidacion_data(self, reembolsos=None):
		data = {
			"issue_date": "21/10/2026",
			"supplier_id_type": "05",
			"supplier_name": "JUAN PEREZ",
			"supplier_id": "1710034065",
			"supplier_address": "",
			"subtotal": 100.00,
			"discount": 0.0,
			"tax_totals": [TAX_TOTAL],
			"total": 115.00,
			"payments": [{"method": "01", "amount": 115.00}],
			"lines": [LINE],
		}
		if reembolsos is not None:
			data["reembolsos"] = reembolsos
		return data

	def test_liquidacion_with_reembolsos_validates_against_xsd(self) -> None:
		xml = build_liquidacion_compra_xml(
			_context("03"), self._liquidacion_data([dict(LIQUIDACION_REEMBOLSO)])
		)
		self.assertTrue(validate_against_xsd(xml, "liquidacion_compra"))

	def test_liquidacion_reembolso_totals_render_in_schema_order(self) -> None:
		xml = build_liquidacion_compra_xml(
			_context("03"), self._liquidacion_data([dict(LIQUIDACION_REEMBOLSO)])
		)
		self.assertIn("<codDocReembolso>01</codDocReembolso>", xml)
		self.assertIn("<totalComprobantesReembolso>1.00</totalComprobantesReembolso>", xml)
		self.assertIn("<totalBaseImponibleReembolso>50.00</totalBaseImponibleReembolso>", xml)
		self.assertIn("<totalImpuestoReembolso>7.50</totalImpuestoReembolso>", xml)
		self.assertLess(xml.index("<totalImpuestoReembolso>"), xml.index("<totalConImpuestos>"))
		self.assertIn("<reembolsos><reembolsoDetalle>", xml)

	def test_liquidacion_without_reembolsos_renders_no_block(self) -> None:
		xml = build_liquidacion_compra_xml(_context("03"), self._liquidacion_data())
		self.assertNotIn("<reembolsos>", xml)
		self.assertTrue(validate_against_xsd(xml, "liquidacion_compra"))

	def test_liquidacion_reembolso_without_taxes_fails_loud(self) -> None:
		entry = dict(LIQUIDACION_REEMBOLSO, taxes=[])
		with self.assertRaises(SriXmlError):
			build_liquidacion_compra_xml(_context("03"), self._liquidacion_data([entry]))


class TestInfoAdicional(unittest.TestCase):
	def test_merge_prefers_nearest_per_nombre(self) -> None:
		from l10n_ec.sri.xml_builder import merge_info_adicional

		merged = merge_info_adicional(
			[
				[{"nombre": "Email", "valor": "si@example.com"}],
				[{"nombre": "Email", "valor": "quote@example.com"}, {"nombre": "Web", "valor": "x.ec"}],
				[],
			]
		)
		self.assertEqual(
			merged,
			[{"nombre": "Email", "valor": "si@example.com"}, {"nombre": "Web", "valor": "x.ec"}],
		)

	def test_merge_caps_at_fifteen_rows(self) -> None:
		from l10n_ec.sri.xml_builder import SriXmlError, merge_info_adicional

		levels = [[{"nombre": f"K{i:02d}", "valor": "v"} for i in range(16)]]
		with self.assertRaises(SriXmlError):
			merge_info_adicional(levels)

	def test_factura_renders_info_adicional_block(self) -> None:
		from l10n_ec.sri.xml_builder import build_factura_xml, validate_against_xsd

		xml = build_factura_xml(
			_context("01"),
			{
				"issue_date": "20/10/2026",
				"buyer_id_type": "07",
				"buyer_name": "CONSUMIDOR FINAL",
				"buyer_id": "9999999999999",
				"buyer_address": "",
				"subtotal": 100.00,
				"discount": 0.0,
				"tax_totals": [TAX_TOTAL],
				"tip": 0.0,
				"total": 115.00,
				"payments": [{"method": "01", "amount": 115.00}],
				"lines": [LINE],
				"info_adicional": [{"nombre": "Email", "valor": "buyer@example.com"}],
			},
		)
		self.assertIn('<campoAdicional nombre="Email">buyer@example.com</campoAdicional>', xml)
		self.assertTrue(validate_against_xsd(xml, "factura"))


class TestTaxpayerStatusTags(unittest.TestCase):
	def test_agent_and_rimpe_tags_emit_in_tributaria(self) -> None:
		from l10n_ec.sri.xml_builder import _info_tributaria

		xml = _info_tributaria(
			{
				"environment": "1",
				"legal_name": "Test",
				"ruc": "1790016919001",
				"access_key": "1" * 49,
				"doc_code": "01",
				"establishment": "001",
				"emission_point": "001",
				"sequential": "000000001",
				"head_office_address": "Quito",
				"withholding_agent": True,
				"rimpe_regime": True,
			}
		)
		self.assertIn("<agenteRetencion>1</agenteRetencion>", xml)
		self.assertIn("<contribuyenteRimpe>CONTRIBUYENTE RÉGIMEN RIMPE</contribuyenteRimpe>", xml)
		self.assertLess(xml.index("<dirMatriz>"), xml.index("<agenteRetencion>"))
		self.assertLess(xml.index("<agenteRetencion>"), xml.index("<contribuyenteRimpe>"))

	def test_tags_absent_without_flags(self) -> None:
		from l10n_ec.sri.xml_builder import _info_tributaria

		xml = _info_tributaria(
			{
				"environment": "1",
				"legal_name": "Test",
				"ruc": "1790016919001",
				"access_key": "1" * 49,
				"doc_code": "01",
				"establishment": "001",
				"emission_point": "001",
				"sequential": "000000001",
				"head_office_address": "Quito",
			}
		)
		self.assertNotIn("agenteRetencion", xml)
		self.assertNotIn("contribuyenteRimpe", xml)

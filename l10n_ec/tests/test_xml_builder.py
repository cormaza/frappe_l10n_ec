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

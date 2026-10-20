import unittest
from datetime import date

from l10n_ec.sri.access_key import generate_access_key
from l10n_ec.sri.xml_builder import build_retencion_xml, validate_against_xsd

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


def _context() -> dict:
	return {
		"environment": "1",
		"doc_code": "07",
		"ruc": "1790016919001",
		"legal_name": "PRUEBAS SERVICIO DE RENTAS INTERNAS",
		"head_office_address": "Av. Amazonas y Naciones Unidas",
		"establishment": "001",
		"emission_point": "001",
		"sequential": "000000001",
		"access_key": generate_access_key(
			document_code_sri="07",
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


class TestSriRetencionBuilder(UnitTestCase):
	"""Unit tests for SRI withholding XML generation and XSD validation."""

	def test_retencion_validates_against_xsd(self) -> None:
		xml = build_retencion_xml(
			_context(),
			{
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
			},
		)
		self.assertTrue(validate_against_xsd(xml, "retencion"))

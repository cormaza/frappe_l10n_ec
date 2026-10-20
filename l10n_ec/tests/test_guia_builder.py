import unittest
from datetime import date

from l10n_ec.sri.access_key import generate_access_key
from l10n_ec.sri.xml_builder import build_guia_xml, validate_against_xsd

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


def _context() -> dict:
	return {
		"environment": "1",
		"doc_code": "06",
		"ruc": "1790016919001",
		"legal_name": "PRUEBAS SERVICIO DE RENTAS INTERNAS",
		"head_office_address": "Av. Amazonas y Naciones Unidas",
		"establishment": "001",
		"emission_point": "001",
		"sequential": "000000001",
		"access_key": generate_access_key(
			document_code_sri="06",
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


class TestSriGuiaBuilder(UnitTestCase):
	"""Unit tests for SRI delivery-note XML generation and XSD validation."""

	def test_guia_validates_against_xsd(self) -> None:
		xml = build_guia_xml(
			_context(),
			{
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
			},
		)
		self.assertIn('<guiaRemision id="comprobante" version="1.1.0">', xml)
		self.assertIn("<codDoc>06</codDoc>", xml)
		self.assertIn("<placa>ABC1234</placa>", xml)
		self.assertTrue(validate_against_xsd(xml, "guia"))


if __name__ == "__main__":
	unittest.main()

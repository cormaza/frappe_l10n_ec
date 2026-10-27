"""End-to-end reimbursement emission: flow payload, XSD emission, parse-back.

Covers S1/S3 emission of factura (01) and liquidacion de compra (03) carrying
the SRI `<reembolsos>` block. Withholdings apply to the own base only, never
to reembolso bases: own `totalConImpuestos` stays untouched while reembolso
taxes travel exclusively inside `reembolsos` plus the info-level totals.
"""

import unittest

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]

from l10n_ec.ecuador_localization.voucher_flow import build_voucher_payload
from l10n_ec.sri import xml_builder
from l10n_ec.sri.voucher_data import parse_emitted_xml

ACCESS_KEY = "2410202601179001691900110010010000000011234567815"

EMITTER = {
	"environment": "1",
	"ruc": "1790016919001",
	"legal_name": "PRUEBAS SERVICIO DE RENTAS INTERNAS",
	"trade_name": "",
	"head_office_address": "Av. Amazonas y Naciones Unidas",
	"establishment": "001",
	"emission_point": "001",
	"branch_address": "Av. Amazonas y Naciones Unidas",
	"special_taxpayer": "",
	"accounting_required": True,
}

SEQUENCE = {"sequential": "000000001", "access_key": ACCESS_KEY}

DETAIL = {
	"doc_code": "01",
	"supplier_id_type": "04",
	"supplier_id": "1790016919001",
	"sri_number": "001-001-000000001",
	"issue_date": "20/10/2026",
	"auth_number": "1234567890",
	"base_amount": 100.00,
	"taxed_base": 100.00,
	"no_tax_base": 0.0,
	"exempt_base": 0.0,
	"ice_amount": 0.0,
	"iva_amount": 15.00,
}

LINE = {
	"code": "SERV-INT",
	"aux_code": "",
	"description": "Intermediation service",
	"qty": 1,
	"unit_price": 200.00,
	"discount": 0.0,
	"subtotal": 200.00,
	"taxes": [{"template": "Ecuador VAT 15% - Sales", "rate": 15.0, "base": 200.00, "value": 30.00}],
}

TOTALS = [{"template": "Ecuador VAT 15% - Sales", "base": 200.00, "value": 30.00}]


def _factura_invoice() -> dict:
	return {
		"doctype": "Sales Invoice",
		"cod_doc": "01",
		"issue_date": "20/10/2026",
		"buyer_id_type": "04",
		"buyer_name": "INTERMEDIARIO EJEMPLO SA",
		"buyer_id": "1790016919001",
		"buyer_address": "",
		"subtotal": 200.00,
		"discount": 0.0,
		"tax_totals": TOTALS,
		"tip": 0.0,
		"total": 230.00,
		"payments": [{"method": "01", "amount": 230.00}],
		"lines": [LINE],
		"sri_reimbursement_details": [dict(DETAIL)],
	}


class TestReimbursementEmission(UnitTestCase):
	"""Flow payload renders XSD-valid XML whose parse-back matches the input."""

	def test_factura_end_to_end_round_trip(self) -> None:
		payload = build_voucher_payload(_factura_invoice(), EMITTER, SEQUENCE)
		builder = getattr(xml_builder, payload["builder"])
		xml = builder(payload["ctx"], payload["data"])
		self.assertTrue(xml_builder.validate_against_xsd(xml, payload["schema"]))
		parsed = parse_emitted_xml(xml)
		self.assertEqual(parsed["kind"], "factura")
		self.assertEqual(len(parsed["reembolsos"]), 1)
		entry = parsed["reembolsos"][0]
		self.assertEqual(entry["doc_code"], "01")
		self.assertEqual(entry["supplier_id"], "1790016919001")
		self.assertEqual(entry["sri_number"], "001-001-000000001")
		self.assertEqual(entry["issue_date"], "20/10/2026")
		self.assertEqual(
			entry["taxes"],
			[{"codigo": "2", "codigoPorcentaje": "4", "tarifa": 15.0, "baseImponible": 100.0, "valor": 15.0}],
		)
		# Own taxes exclude reembolso bases; reembolso taxes stay in their block.
		self.assertEqual(parsed["taxes"], [{"code": "2", "rate_code": "4", "base": 200.0, "value": 30.0}])

	def test_liquidacion_end_to_end_round_trip(self) -> None:
		invoice = {
			"doctype": "Purchase Invoice",
			"cod_doc": "03",
			"issue_date": "21/10/2026",
			"supplier_id_type": "05",
			"supplier_name": "JUAN PEREZ",
			"supplier_id": "1710034065",
			"supplier_address": "",
			"subtotal": 100.00,
			"discount": 0.0,
			"tax_totals": [{"template": "Ecuador VAT 15% - Purchases", "base": 100.00, "value": 15.00}],
			"total": 115.00,
			"payments": [{"method": "01", "amount": 115.00}],
			"lines": [
				{
					"code": "SERV-RURAL",
					"aux_code": "",
					"description": "Rural service",
					"qty": 1,
					"unit_price": 100.00,
					"discount": 0.0,
					"subtotal": 100.00,
					"taxes": [
						{
							"template": "Ecuador VAT 15% - Purchases",
							"rate": 15.0,
							"base": 100.00,
							"value": 15.00,
						}
					],
				}
			],
			"sri_reimbursement_details": [dict(DETAIL)],
		}
		payload = build_voucher_payload(invoice, EMITTER, SEQUENCE)
		builder = getattr(xml_builder, payload["builder"])
		xml = builder(payload["ctx"], payload["data"])
		self.assertTrue(xml_builder.validate_against_xsd(xml, payload["schema"]))
		parsed = parse_emitted_xml(xml)
		self.assertEqual(parsed["kind"], "liquidacion_compra")
		self.assertEqual(len(parsed["reembolsos"]), 1)
		self.assertEqual(parsed["reembolsos"][0]["taxes"][0]["valor"], 15.0)

	def test_emission_without_details_stays_unchanged(self) -> None:
		invoice = _factura_invoice()
		del invoice["sri_reimbursement_details"]
		payload = build_voucher_payload(invoice, EMITTER, SEQUENCE)
		self.assertNotIn("reembolsos", payload["data"])
		builder = getattr(xml_builder, payload["builder"])
		xml = builder(payload["ctx"], payload["data"])
		self.assertNotIn("<reembolsos>", xml)
		self.assertTrue(xml_builder.validate_against_xsd(xml, payload["schema"]))

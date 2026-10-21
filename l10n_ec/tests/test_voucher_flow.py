import unittest
from types import SimpleNamespace
from unittest.mock import create_autospec

from zeep import Client

try:
	import frappe
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]

from l10n_ec.ecuador_localization.doctype.sri_electronic_voucher.sri_electronic_voucher import (
	SRIElectronicVoucher,
)
from l10n_ec.ecuador_localization.voucher_flow import (
	aggregate_raw_totals,
	apply_transition,
	build_voucher_payload,
	generate_voucher_xml_doc,
	group_withholdings_by_sustento,
	map_line_taxes,
	map_tax_totals,
	poll_voucher_doc,
	sign_voucher_doc,
	submit_voucher_doc,
	sustento_entries,
	synthesize_iva_row,
)
from l10n_ec.sri.soap_client import SriSoapClient
from l10n_ec.sri.voucher_states import SriVoucherError
from l10n_ec.tests.test_helpers import generate_test_p12

try:
	import frappe
	from frappe.tests import UnitTestCase

	HAS_FRAPPE = True
except ImportError:  # pragma: no cover
	frappe = None  # type: ignore[assignment]
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]
	HAS_FRAPPE = False

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

LINE = {
	"code": "PROD001",
	"aux_code": "",
	"description": "Servicio de consultoria",
	"qty": 1,
	"unit_price": 100.00,
	"discount": 0.0,
	"subtotal": 100.00,
	"taxes": [{"template": "Ecuador VAT 15% - Sales", "rate": 15.0, "base": 100.00, "value": 15.00}],
}

TOTALS = [{"template": "Ecuador VAT 15% - Sales", "base": 100.00, "value": 15.00}]

INVOICE = {
	"doctype": "Sales Invoice",
	"cod_doc": "01",
	"issue_date": "20/10/2026",
	"buyer_id_type": "07",
	"buyer_name": "CONSUMIDOR FINAL",
	"buyer_id": "9999999999999",
	"buyer_address": "",
	"subtotal": 100.00,
	"discount": 0.0,
	"tax_totals": TOTALS,
	"tip": 0.0,
	"total": 115.00,
	"payments": [{"method": "01", "amount": 115.00}],
	"lines": [LINE],
}


def _factories():
	soap = SriSoapClient(environment="test", use_local_wsdl=True)
	reception = soap.create_client("reception").type_factory("ns0")
	authorization = soap.create_client("authorization").type_factory("ns0")
	return reception, authorization


def _reception_service(state, messages=()):
	reception, _ = _factories()
	response = reception.respuestaSolicitud(
		estado=state,
		comprobantes={
			"comprobante": [
				reception.comprobante(claveAcceso=ACCESS_KEY, mensajes={"mensaje": list(messages)})
			]
		},
	)
	service = create_autospec(Client).service
	service.validarComprobante.return_value = response
	return SimpleNamespace(service=service)


def _authorization_service(state):
	_, authorization = _factories()
	response = authorization.respuestaComprobante(
		claveAccesoConsultada=ACCESS_KEY,
		numeroComprobantes=1,
		autorizaciones={
			"autorizacion": [
				authorization.autorizacion(
					estado=state,
					numeroAutorizacion=ACCESS_KEY,
					fechaAutorizacion="20/10/2026 10:30:00",
					ambiente="PRUEBAS",
					comprobante="<factura/>",
					mensajes={"mensaje": []},
				)
			]
		},
	)
	service = create_autospec(Client).service
	service.autorizacionComprobante.return_value = response
	return SimpleNamespace(service=service)


def _voucher(**kwargs):
	values = {
		"access_key": ACCESS_KEY,
		"voucher_state": "Generated",
		"sri_doc_code": "01",
		"company": "Demo Ecuador",
		"reference_doctype": "Sales Invoice",
		"reference_name": "ACC-SINV-2026-00001",
		"unsigned_xml": "",
		"signed_xml": "",
		"authorization_number": "",
		"authorization_date": None,
		"last_message": "",
	}
	values.update(kwargs)
	if frappe is not None:
		return frappe.get_doc({"doctype": "SRI Electronic Voucher", **values})
	return SRIElectronicVoucher(**values)


def _key_material():
	return generate_test_p12(password=b"123456", expired=False), "123456"


class TestVoucherFlowMapping(UnitTestCase):
	"""Unit tests for invoice-to-payload mapping (pure Python)."""

	def test_map_line_taxes_resolves_templates(self) -> None:
		mapped = map_line_taxes(LINE)
		self.assertEqual(mapped["taxes"][0]["code"], "2")
		self.assertEqual(mapped["taxes"][0]["rate_code"], "4")
		self.assertEqual(mapped["taxes"][0]["value"], 15.00)
		self.assertEqual(mapped["code"], "PROD001")

	def test_map_unknown_template_raises(self) -> None:
		with self.assertRaisesRegex(ValueError, "no automatic SRI code mapping"):
			map_line_taxes({"taxes": [{"template": "Ecuador ICE - Sales", "rate": 0, "base": 1, "value": 0}]})
		with self.assertRaisesRegex(ValueError, "no automatic SRI code mapping"):
			map_tax_totals([{"template": "Nope", "base": 1, "value": 0}])

	def test_build_factura_payload(self) -> None:
		payload = build_voucher_payload(INVOICE, EMITTER, SEQUENCE)
		self.assertEqual(payload["builder"], "build_factura_xml")
		self.assertEqual(payload["ctx"]["access_key"], ACCESS_KEY)
		self.assertEqual(payload["ctx"]["doc_code"], "01")
		self.assertEqual(payload["data"]["buyer_id"], "9999999999999")
		self.assertEqual(payload["data"]["lines"][0]["taxes"][0]["rate_code"], "4")

	def test_build_credit_note_payload_carries_refs(self) -> None:
		invoice = dict(
			INVOICE,
			cod_doc="04",
			modified_doc_code="01",
			modified_doc_number="001-001-000000001",
			sustento_issue_date="20/10/2026",
			adjustment_value=115.00,
			reason="Devolucion",
		)
		payload = build_voucher_payload(invoice, EMITTER, SEQUENCE)
		self.assertEqual(payload["builder"], "build_nota_credito_xml")
		self.assertEqual(payload["data"]["modified_doc_number"], "001-001-000000001")
		self.assertEqual(payload["data"]["reason"], "Devolucion")

	def test_build_unsupported_code_raises(self) -> None:
		with self.assertRaises(SriVoucherError):
			build_voucher_payload(dict(INVOICE, cod_doc="99"), EMITTER, SEQUENCE)

	def test_build_retencion_payload_validates_end_to_end(self) -> None:
		from l10n_ec.sri.xml_builder import build_retencion_xml, validate_against_xsd

		payload = build_voucher_payload(
			{
				"cod_doc": "07",
				"issue_date": "21/10/2026",
				"subject_id_type": "04",
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
			EMITTER,
			SEQUENCE,
		)
		self.assertEqual(payload["builder"], "build_retencion_xml")
		xml = build_retencion_xml(payload["ctx"], payload["data"])
		self.assertTrue(validate_against_xsd(xml, payload["schema"]))

	def test_build_guia_payload_validates_end_to_end(self) -> None:
		from l10n_ec.sri.xml_builder import build_guia_xml, validate_against_xsd

		payload = build_voucher_payload(
			{
				"cod_doc": "06",
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
			EMITTER,
			SEQUENCE,
		)
		self.assertEqual(payload["builder"], "build_guia_xml")
		xml = build_guia_xml(payload["ctx"], payload["data"])
		self.assertTrue(validate_against_xsd(xml, payload["schema"]))


class TestVoucherFlowPipeline(UnitTestCase):
	"""Mocked end-to-end voucher pipeline (zeep factories, generic p12, no network)."""

	def _signed_doc(self):
		doc = _voucher()
		payload = build_voucher_payload(INVOICE, EMITTER, SEQUENCE)
		generate_voucher_xml_doc(doc, payload)
		sign_voucher_doc(doc, key_material=_key_material())
		return doc

	def test_generate_stores_xml_and_skips_when_not_generated(self) -> None:
		doc = _voucher()
		payload = build_voucher_payload(INVOICE, EMITTER, SEQUENCE)
		result = generate_voucher_xml_doc(doc, payload)
		self.assertTrue(result["ok"])
		self.assertIn("<factura", doc.unsigned_xml)
		apply_transition(doc, "sign")
		self.assertEqual(generate_voucher_xml_doc(doc, payload)["ok"], False)

	def test_sign_needs_generated_xml_first(self) -> None:
		doc = _voucher()
		result = sign_voucher_doc(doc, key_material=_key_material())
		self.assertFalse(result["ok"])
		self.assertIn("skipped", result)

	def test_submit_received_and_returned(self) -> None:
		received = self._signed_doc()
		result = submit_voucher_doc(received, client_ws=_reception_service("RECIBIDA"))
		self.assertTrue(result["ok"])
		self.assertEqual(received.voucher_state, "Received")

		returned = self._signed_doc()
		_, authorization = _factories()
		devuelta = _reception_service(
			"DEVUELTA",
			[
				authorization.mensaje(
					identificador="65",
					informacionAdicional="",
					mensaje="FECHA EMISION EXTEMPORANEA",
					tipo="ERROR",
				)
			],
		)
		result = submit_voucher_doc(returned, client_ws=devuelta)
		self.assertFalse(result["ok"])
		self.assertEqual(returned.voucher_state, "Returned")
		self.assertIn("ERROR [65]", returned.last_message)

	def test_double_submit_skips(self) -> None:
		doc = _voucher(voucher_state="Received")
		result = submit_voucher_doc(doc, client_ws=_reception_service("RECIBIDA"))
		self.assertFalse(result["ok"])
		self.assertIn("skipped", result)

	def test_poll_authorized_and_rejected(self) -> None:
		authorized = self._signed_doc()
		submit_voucher_doc(authorized, client_ws=_reception_service("RECIBIDA"))
		result = poll_voucher_doc(authorized, client_ws=_authorization_service("AUTORIZADO"))
		self.assertTrue(result["ok"])
		self.assertEqual(authorized.voucher_state, "Authorized")
		self.assertEqual(authorized.authorization_number, ACCESS_KEY)
		self.assertTrue(authorized.authorization_date)

		rejected = self._signed_doc()
		submit_voucher_doc(rejected, client_ws=_reception_service("RECIBIDA"))
		result = poll_voucher_doc(rejected, client_ws=_authorization_service("NO AUTORIZADO"), max_attempts=2)
		self.assertFalse(result["ok"])
		self.assertEqual(rejected.voucher_state, "Rejected")

	def test_full_mocked_pipeline_to_authorized(self) -> None:
		doc = _voucher()
		payload = build_voucher_payload(INVOICE, EMITTER, SEQUENCE)
		self.assertTrue(generate_voucher_xml_doc(doc, payload)["ok"])
		self.assertTrue(sign_voucher_doc(doc, key_material=_key_material())["ok"])
		self.assertTrue(submit_voucher_doc(doc, client_ws=_reception_service("RECIBIDA"))["ok"])
		result = poll_voucher_doc(doc, client_ws=_authorization_service("AUTORIZADO"))
		self.assertTrue(result["ok"])
		self.assertEqual(doc.voucher_state, "Authorized")

	def test_aggregate_raw_totals_groups_by_template(self) -> None:
		lines = [
			{"taxes": [{"template": "Ecuador VAT 15% - Sales", "base": 100.00, "value": 15.00}]},
			{"taxes": [{"template": "Ecuador VAT 15% - Sales", "base": 50.00, "value": 7.50}]},
		]
		totals = aggregate_raw_totals(lines)
		self.assertEqual(len(totals), 1)
		self.assertEqual(totals[0]["base"], 150.00)
		self.assertEqual(totals[0]["value"], 22.50)

	def test_group_withholdings_by_sustento(self) -> None:
		purchase_a = {
			"doc_code": "01",
			"number": "001-001-000000001",
			"issue_date": "20/10/2026",
			"auth_number": "1234567890",
			"subtotal": 100.00,
			"total": 115.00,
			"doc_taxes": [
				{"tax_code": "2", "rate_code": "4", "base": 100.00, "rate": 15.0, "tax_value": 15.00}
			],
			"payments": [{"method": "01", "amount": 115.00}],
		}
		purchase_b = dict(purchase_a, number="001-001-000000002")
		blocks = group_withholdings_by_sustento(
			[
				{
					"purchase": purchase_a,
					"tax_type": "IR",
					"withholding_code": "303",
					"rate": 1.0,
					"base": 100.00,
					"value": 1.00,
				},
				{
					"purchase": purchase_a,
					"tax_type": "IVA",
					"withholding_code": "9",
					"rate": 30.0,
					"base": 15.00,
					"value": 4.50,
				},
				{
					"purchase": purchase_b,
					"tax_type": "IR",
					"withholding_code": "303",
					"rate": 1.0,
					"base": 50.00,
					"value": 0.50,
				},
			],
			sustento_code="01",
		)
		self.assertEqual(len(blocks), 2)
		first = blocks[0]
		self.assertEqual(first["sustento_code"], "01")
		self.assertEqual(first["doc_number"], "001-001-000000001")
		codes = [(r["code"], r["withholding_code"]) for r in first["withholdings"]]
		self.assertEqual(codes, [("1", "303"), ("2", "9")])
		self.assertEqual(blocks[1]["doc_number"], "001-001-000000002")

	def test_sustento_entries_resolve_codes_explicitly(self) -> None:
		purchase = {"doc_code": "01", "number": "001-001-000000001"}
		entries = sustento_entries(
			[{"category": "Ecuador IR 2%", "rate": 2.0, "taxable": 100.00, "amount": 2.00}],
			purchase,
			{"Ecuador IR 2%": ("1", "303")},
		)
		self.assertEqual(len(entries), 1)
		self.assertEqual(entries[0]["tax_type"], "IR")
		self.assertEqual(entries[0]["withholding_code"], "303")
		with self.assertRaises(SriVoucherError):
			sustento_entries(
				[{"category": "Unknown", "rate": 1.0, "taxable": 1.0, "amount": 0.01}],
				purchase,
				{},
			)

	def test_apply_transition_guards_illegal_moves(self) -> None:
		doc = _voucher(voucher_state="Authorized")
		with self.assertRaises(SriVoucherError):
			apply_transition(doc, "sign")
		self.assertEqual(doc.voucher_state, "Authorized")

	def test_generate_validates_against_xsd(self) -> None:
		from l10n_ec.sri.xml_builder import SriXmlError

		doc = _voucher()
		payload = build_voucher_payload(INVOICE, EMITTER, SEQUENCE)
		self.assertTrue(generate_voucher_xml_doc(doc, payload)["ok"])
		bad = dict(payload, ctx=dict(payload["ctx"], environment="test"))
		with self.assertRaises(SriXmlError):
			generate_voucher_xml_doc(_voucher(), bad)

	@unittest.skipUnless(HAS_FRAPPE, "needs bench File API")
	def test_persist_roundtrip_keeps_xml_intact(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import persist_voucher_xml, read_voucher_xml

		doc = _voucher()
		doc.unsigned_xml = "<factura/>"
		url = persist_voucher_xml(doc, "unsigned_xml")
		self.assertTrue(url.endswith("-unsigned.xml"))
		self.assertEqual(read_voucher_xml(doc, "unsigned_xml"), "<factura/>")
		frappe.delete_doc("File", frappe.db.get_value("File", {"file_url": url}, "name"))


class TestSynthesizeIvaRow(UnitTestCase):
	"""IVA withholdings synthesize from IVA line taxes (ERPNext gap)."""

	def test_iva_lines_synthesize_rated_row(self) -> None:
		mapped = [map_line_taxes(LINE)]
		row = synthesize_iva_row(mapped, "1")
		self.assertEqual(row, {"category": "Ecuador IVA 30%", "rate": 30.0, "taxable": 15.0, "amount": 4.5})

	def test_non_iva_concepto_raises(self) -> None:
		with self.assertRaises(SriVoucherError):
			synthesize_iva_row([map_line_taxes(LINE)], "303")

	def test_unknown_concepto_raises(self) -> None:
		with self.assertRaises(SriVoucherError):
			synthesize_iva_row([map_line_taxes(LINE)], "9999")

	def test_zero_iva_base_emits_nothing(self) -> None:
		mapped = [{"taxes": [{"code": "3", "rate_code": "3001", "rate": 0.0, "base": 10.0, "value": 5.0}]}]
		self.assertIsNone(synthesize_iva_row(mapped, "1"))

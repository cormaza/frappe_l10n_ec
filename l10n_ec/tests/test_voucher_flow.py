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
	map_line_taxes,
	map_tax_totals,
	poll_voucher_doc,
	sign_voucher_doc,
	submit_voucher_doc,
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
			build_voucher_payload(dict(INVOICE, cod_doc="07"), EMITTER, SEQUENCE)


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
		result = poll_voucher_doc(
			rejected, client_ws=_authorization_service("NO AUTORIZADO"), max_attempts=2
		)
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

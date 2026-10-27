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
			{
				"taxes": [
					{"template": "Ecuador VAT 15% - Sales", "rate": 15.0, "base": 100.00, "value": 15.00}
				]
			},
			{"taxes": [{"template": "Ecuador VAT 15% - Sales", "rate": 15.0, "base": 50.00, "value": 7.50}]},
		]
		totals = aggregate_raw_totals(lines)
		self.assertEqual(len(totals), 1)
		self.assertEqual(totals[0]["rate"], 15.0)
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


class TestDeriveCodDoc(UnitTestCase):
	"""Unit tests for SRI document code derivation (mocked frappe)."""

	def test_liquidacion_purchase_derives_03(self) -> None:
		from unittest.mock import patch

		from l10n_ec.ecuador_localization.voucher_flow import _derive_cod_doc

		doc = SimpleNamespace(sri_is_liquidacion=1)
		with patch("l10n_ec.ecuador_localization.voucher_flow.frappe") as mock_frappe:
			mock_frappe.get_doc.return_value = doc
			self.assertEqual(_derive_cod_doc("Purchase Invoice", "PI-1"), "03")

	def test_supplier_invoice_refuses_emission(self) -> None:
		from unittest.mock import patch

		from l10n_ec.ecuador_localization.voucher_flow import _derive_cod_doc

		doc = SimpleNamespace(sri_is_liquidacion=0)
		with patch("l10n_ec.ecuador_localization.voucher_flow.frappe") as mock_frappe:
			mock_frappe.get_doc.return_value = doc
			with self.assertRaises(SriVoucherError):
				_derive_cod_doc("Purchase Invoice", "PI-1")

	def test_delivery_note_derives_06_without_frappe(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import _derive_cod_doc

		self.assertEqual(_derive_cod_doc("Delivery Note", "DN-1"), "06")


class FakeInfoDoc(dict):
	@property
	def items(self):
		return self["items"]


class TestResolveInfoAdicional(UnitTestCase):
	def test_si_rows_win_without_chain(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import resolve_info_adicional

		doc = FakeInfoDoc(
			{
				"company": "Demo No Central Co",
				"sri_info_adicional": [{"nombre": "Email", "valor": "si@example.com"}],
				"items": [],
			}
		)
		rows = resolve_info_adicional(doc)
		self.assertEqual(rows, [{"nombre": "Email", "valor": "si@example.com"}])

	def test_chain_merges_quote_order_invoice_central(self) -> None:
		from unittest.mock import patch

		from l10n_ec.ecuador_localization import voucher_flow

		quote = FakeInfoDoc(
			{
				"sri_info_adicional": [
					{"nombre": "Email", "valor": "quote@example.com"},
					{"nombre": "Web", "valor": "x.ec"},
				],
				"items": [],
			}
		)
		order = FakeInfoDoc(
			{
				"sri_info_adicional": [{"nombre": "Email", "valor": "order@example.com"}],
				"items": [{"prevdoc_doctype": "Quotation", "prevdoc_docname": "Q-1", "sales_order": ""}],
			}
		)
		si = FakeInfoDoc(
			{
				"company": "Demo Ecuador",
				"sri_info_adicional": [],
				"items": [{"prevdoc_doctype": "", "prevdoc_docname": "", "sales_order": "SO-1"}],
			}
		)
		fake_frappe = SimpleNamespace(
			get_doc=lambda doctype, name: {"SO-1": order, "Q-1": quote}[name],
			get_all=lambda *args, **kwargs: [],
		)
		with patch.object(voucher_flow, "frappe", fake_frappe):
			rows = voucher_flow.resolve_info_adicional(si)
		by_name = {row["nombre"]: row["valor"] for row in rows}
		self.assertEqual(by_name, {"Email": "order@example.com", "Web": "x.ec"})


class TestPayloadCtxCarriesTaxpayerFlags(UnitTestCase):
	def test_withholding_and_rimpe_flags_reach_ctx(self) -> None:
		emitter = dict(EMITTER, withholding_agent=True, rimpe_regime=True)
		payload = build_voucher_payload(INVOICE, emitter, SEQUENCE)
		self.assertTrue(payload["ctx"]["withholding_agent"])
		self.assertTrue(payload["ctx"]["rimpe_regime"])

	def test_flags_default_absent(self) -> None:
		payload = build_voucher_payload(INVOICE, EMITTER, SEQUENCE)
		self.assertFalse(payload["ctx"]["withholding_agent"])
		self.assertFalse(payload["ctx"]["rimpe_regime"])


class TestPointChannelLock(UnitTestCase):
	"""Emission points never serve both channels (pure rule)."""

	def test_pos_sale_needs_pos_point(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import validate_point_channel

		validate_point_channel(True, True, "001-002")
		with self.assertRaises(SriVoucherError):
			validate_point_channel(True, False, "001-001")

	def test_desk_sale_rejected_from_pos_point(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import validate_point_channel

		validate_point_channel(False, False, "001-001")
		with self.assertRaises(SriVoucherError):
			validate_point_channel(False, True, "001-002")


class TestShopChannelLock(UnitTestCase):
	"""Shop-only points serve e-commerce exclusively (pure rule)."""

	def test_shop_sale_needs_shop_point(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import validate_point_channel

		validate_point_channel(False, False, "001-004", "SO-1", is_shop_sale=True, shop_only=True)
		with self.assertRaises(SriVoucherError):
			validate_point_channel(False, False, "001-001", "SO-1", is_shop_sale=True, shop_only=False)

	def test_locked_points_reject_desk(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import validate_point_channel

		with self.assertRaises(SriVoucherError):
			validate_point_channel(False, False, "001-004", "SI-1", shop_only=True)
		with self.assertRaises(SriVoucherError):
			validate_point_channel(True, True, "X", "S", is_shop_sale=True, shop_only=True)


class TestTicketHelpers(UnitTestCase):
	"""Per-ticket payment code and merge identity uniformity (pure)."""

	def test_payment_code_default_and_passthrough(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import ticket_payment_code

		self.assertEqual(ticket_payment_code(None), "01")
		self.assertEqual(ticket_payment_code("01"), "01")
		self.assertEqual(ticket_payment_code("19"), "19")

	def test_payment_code_unknown_fails_loud(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import ticket_payment_code

		with self.assertRaises((ValueError, SriVoucherError)):
			ticket_payment_code("99")

	def test_merge_uniform_passes(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import check_merge_identity_uniform

		check_merge_identity_uniform([True, True], True, "M-1")
		check_merge_identity_uniform([False], False, "M-2")
		check_merge_identity_uniform([], True, "M-3")

	def test_merge_mixed_fails_loud(self) -> None:
		from l10n_ec.ecuador_localization.voucher_flow import check_merge_identity_uniform

		with self.assertRaises(SriVoucherError):
			check_merge_identity_uniform([True, False], True, "M-1")


class TestReimbursementPayload(UnitTestCase):
	"""Voucher payload carries `reembolsos` only when reimbursement lines exist."""

	def _detail(self):
		return {
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

	def _invoice(self, cod_doc, extra=None):
		base = dict(INVOICE, cod_doc=cod_doc)
		if cod_doc == "03":
			base.update(
				{
					"supplier_id_type": "05",
					"supplier_name": "JUAN PEREZ",
					"supplier_id": "1710034065",
					"supplier_address": "",
				}
			)
			for key in ("buyer_id_type", "buyer_name", "buyer_id", "buyer_address", "tip"):
				base.pop(key, None)
		if extra:
			base.update(extra)
		return base

	def test_factura_without_details_carries_no_reembolsos(self) -> None:
		payload = build_voucher_payload(self._invoice("01"), EMITTER, SEQUENCE)
		self.assertNotIn("reembolsos", payload["data"])

	def test_factura_with_details_carries_reembolsos(self) -> None:
		invoice = self._invoice("01", {"sri_reimbursement_details": [self._detail()]})
		payload = build_voucher_payload(invoice, EMITTER, SEQUENCE)
		reembolsos = payload["data"]["reembolsos"]
		self.assertEqual(len(reembolsos), 1)
		self.assertEqual(reembolsos[0]["doc_code"], "01")
		self.assertEqual(reembolsos[0]["sri_number"], "001-001-000000001")
		self.assertEqual(reembolsos[0]["taxes"][0]["codigoPorcentaje"], "4")
		self.assertAlmostEqual(reembolsos[0]["taxes"][0]["baseImponible"], 100.00)

	def test_factura_details_derive_tarifa_from_iva_amount(self) -> None:
		detail = dict(self._detail(), taxed_base=200.00, iva_amount=30.00, base_amount=200.00)
		invoice = self._invoice("01", {"sri_reimbursement_details": [detail]})
		payload = build_voucher_payload(invoice, EMITTER, SEQUENCE)
		tax = payload["data"]["reembolsos"][0]["taxes"][0]
		self.assertEqual(tax["codigo"], "2")
		self.assertEqual(tax["codigoPorcentaje"], "4")
		self.assertAlmostEqual(tax["tarifa"], 15.0)

	def test_factura_explicit_taxes_win_over_aggregates(self) -> None:
		taxes = [
			{"codigo": "2", "codigoPorcentaje": "4", "tarifa": 15.0, "baseImponible": 100.00, "valor": 15.00}
		]
		detail = dict(self._detail(), taxes=taxes)
		invoice = self._invoice("01", {"sri_reimbursement_details": [detail]})
		payload = build_voucher_payload(invoice, EMITTER, SEQUENCE)
		self.assertEqual(payload["data"]["reembolsos"][0]["taxes"], taxes)

	def test_liquidacion_with_details_carries_reembolsos(self) -> None:
		invoice = self._invoice("03", {"sri_reimbursement_details": [self._detail()]})
		payload = build_voucher_payload(invoice, EMITTER, SEQUENCE)
		self.assertEqual(len(payload["data"]["reembolsos"]), 1)
		self.assertEqual(payload["data"]["reembolsos"][0]["supplier_id"], "1790016919001")

	def test_liquidacion_without_details_carries_no_reembolsos(self) -> None:
		payload = build_voucher_payload(self._invoice("03"), EMITTER, SEQUENCE)
		self.assertNotIn("reembolsos", payload["data"])

	def test_partial_row_without_amounts_fails_loud(self) -> None:
		detail = dict(self._detail(), taxed_base=0.0, iva_amount=0.0, base_amount=0.0)
		invoice = self._invoice("01", {"sri_reimbursement_details": [detail]})
		with self.assertRaises((ValueError, SriVoucherError)):
			build_voucher_payload(invoice, EMITTER, SEQUENCE)

	def test_partial_row_without_number_fails_loud(self) -> None:
		detail = self._detail()
		del detail["sri_number"]
		invoice = self._invoice("01", {"sri_reimbursement_details": [detail]})
		with self.assertRaises((ValueError, SriVoucherError)):
			build_voucher_payload(invoice, EMITTER, SEQUENCE)

	def test_override_without_optin_fails_loud(self) -> None:
		invoice = self._invoice(
			"01",
			{
				"sri_reimbursement_details": [self._detail()],
				"sri_reimbursement_override_value": 10.00,
			},
		)
		with self.assertRaises((ValueError, SriVoucherError)):
			build_voucher_payload(invoice, EMITTER, SEQUENCE)

	def test_override_with_optin_passes(self) -> None:
		invoice = self._invoice(
			"01",
			{
				"sri_reimbursement_details": [self._detail()],
				"sri_reimbursement_override_value": 10.00,
				"sri_allow_reimbursement_override": True,
			},
		)
		payload = build_voucher_payload(invoice, EMITTER, SEQUENCE)
		self.assertEqual(len(payload["data"]["reembolsos"]), 1)

	def test_ice_without_explicit_taxes_fails_loud(self) -> None:
		detail = dict(self._detail(), ice_amount=5.00, taxed_base=0.0, iva_amount=0.0, base_amount=5.00)
		invoice = self._invoice("01", {"sri_reimbursement_details": [detail]})
		with self.assertRaises((ValueError, SriVoucherError)):
			build_voucher_payload(invoice, EMITTER, SEQUENCE)

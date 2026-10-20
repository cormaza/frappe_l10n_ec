import unittest
from datetime import datetime
from unittest.mock import create_autospec

import pytz
from zeep import Client

from l10n_ec.sri.soap_client import (
	PRODUCTION_URL,
	TEST_URL,
	SriSoapClient,
	process_authorization_response,
	process_reception_response,
)

try:
	from frappe.tests import UnitTestCase
except ImportError:  # pragma: no cover
	UnitTestCase = unittest.TestCase  # type: ignore[misc,assignment]


class TestSRISoapClient(UnitTestCase):
	"""Unit tests for offline SRI Zeep WSDL bindings and reception/authorization responses."""

	def test_sri_soap_wsdl_offline_loading_and_reception(self) -> None:
		soap = SriSoapClient(environment="test", use_local_wsdl=True)
		reception_client = soap.create_client("reception")
		factory = reception_client.type_factory("ns0")

		valid_response = factory.respuestaSolicitud(
			estado="RECIBIDA",
			comprobantes={
				"comprobante": [
					factory.comprobante(
						claveAcceso="2410202601179001691900110010010000000011234567815",
						mensajes={"mensaje": []},
					)
				]
			},
		)
		mock_ws = create_autospec(Client)
		mock_ws.service.validarComprobante.return_value = valid_response

		raw_resp = soap.send_xml_for_reception(mock_ws, "<factura/>")
		ok, messages = process_reception_response(raw_resp)
		self.assertTrue(ok)
		self.assertEqual(messages, [])

		# Test DEVUELTA with error message (ported from PR #102 sri_response.py)
		sri_message_date = factory.mensaje(
			identificador="65",
			informacionAdicional="Emission date out of tolerance range",
			mensaje="FECHA EMISION EXTEMPORANEA",
			tipo="ERROR",
		)
		returned_response = factory.respuestaSolicitud(
			estado="DEVUELTA",
			comprobantes={
				"comprobante": [
					factory.comprobante(
						claveAcceso="2410202601179001691900110010010000000011234567815",
						mensajes={"mensaje": [sri_message_date]},
					)
				]
			},
		)
		ok_returned, returned_messages = process_reception_response(returned_response)
		self.assertFalse(ok_returned)
		self.assertEqual(len(returned_messages), 1)
		self.assertIn("ERROR [65]", returned_messages[0])

	def test_sri_soap_authorization_response_processing(self) -> None:
		soap = SriSoapClient(environment="test", use_local_wsdl=True)
		auth_client = soap.create_client("authorization")
		factory = auth_client.type_factory("ns0")

		access_key = "2410202601179001691900110010010000000011234567815"
		guayaquil_tz = pytz.timezone("America/Guayaquil")
		auth_response = factory.respuestaComprobante(
			claveAccesoConsultada=access_key,
			numeroComprobantes=1,
			autorizaciones={
				"autorizacion": [
					factory.autorizacion(
						estado="AUTORIZADO",
						numeroAutorizacion=access_key,
						fechaAutorizacion=datetime(2026, 10, 24, 10, 30, 0, tzinfo=guayaquil_tz),
						ambiente="PRUEBAS",
						comprobante="<factura/>",
						mensajes={"mensaje": []},
					)
				]
			},
		)
		mock_ws = create_autospec(Client)
		mock_ws.service.autorizacionComprobante.return_value = auth_response

		raw_auth = soap.request_authorization(mock_ws, access_key)
		is_auth, messages, auth_values = process_authorization_response(raw_auth, access_key)
		self.assertTrue(is_auth)
		self.assertEqual(messages, [])
		self.assertEqual(auth_values["l10n_ec_xml_access_key"], access_key)
		self.assertIn("l10n_ec_authorization_date", auth_values)

	def test_sri_soap_urls_by_environment(self) -> None:
		test_client = SriSoapClient(environment="test", use_local_wsdl=False)
		prod_client = SriSoapClient(environment="production", use_local_wsdl=False)
		self.assertEqual(test_client.get_wsdl_url("reception"), TEST_URL["reception"])
		self.assertEqual(prod_client.get_wsdl_url("authorization"), PRODUCTION_URL["authorization"])

from datetime import datetime
from pathlib import Path
from typing import Any

import pytz
from zeep import Client
from zeep.helpers import serialize_object
from zeep.transports import Transport

TEST_URL = {
	"reception": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
	"authorization": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
}

PRODUCTION_URL = {
	"reception": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
	"authorization": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
}

WSDL_DIR = Path(__file__).resolve().parent / "wsdl"
LOCAL_WSDL = {
	"reception": str(WSDL_DIR / "RecepcionComprobantesOffline.wsdl"),
	"authorization": str(WSDL_DIR / "AutorizacionComprobantesOffline.wsdl"),
}

DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class SriSoapClient:
	"""SOAP client adapter for Ecuadorian SRI Offline Reception and Authorization web services.

	Ported from OCA/l10n-ecuador PR #102 (`account_edi_format.py` and `account_edi_document.py`).
	Supports loading local WSDL files for fast, deterministic offline unit testing.
	"""

	def __init__(
		self,
		environment: str = "test",
		timeout: int = 30,
		use_local_wsdl: bool = False,
	) -> None:
		self.environment = environment
		self.timeout = timeout
		self.use_local_wsdl = use_local_wsdl

	def get_wsdl_url(self, service_type: str) -> str:
		if service_type not in ("reception", "authorization"):
			raise ValueError(f"Unknown SRI service type: {service_type}")
		if self.use_local_wsdl:
			return LOCAL_WSDL[service_type]
		urls = PRODUCTION_URL if self.environment in ("production", "2") else TEST_URL
		return urls[service_type]

	def create_client(self, service_type: str) -> Client:
		transport = Transport(timeout=self.timeout)
		return Client(self.get_wsdl_url(service_type), transport=transport)

	@staticmethod
	def send_xml_for_reception(client_ws: Any, xml_string: str) -> Any:
		"""Submit signed XML to SRI `validarComprobante` endpoint."""
		return client_ws.service.validarComprobante(xml=xml_string.encode("utf-8"))

	@staticmethod
	def request_authorization(client_ws: Any, access_key: str) -> Any:
		"""Query SRI `autorizacionComprobante` endpoint by 49-digit access key."""
		return client_ws.service.autorizacionComprobante(claveAccesoComprobante=access_key)


def process_reception_response(response: Any) -> tuple[bool, list[str]]:
	"""Process SRI `validarComprobante` SOAP response.

	Ported from OCA/l10n-ecuador PR #102 (`account_edi_document.py::_l10n_ec_edi_process_response_send`).
	Returns `(ok, messages)`.
	"""
	msj_list: list[str] = []
	response_data = serialize_object(response, dict) if response else {}
	if not response_data:
		return False, msj_list

	ok = response_data.get("estado", "") == "RECIBIDA"
	if response_data.get("estado", "") == "DEVUELTA":
		ok = False

	comprobantes = (response_data.get("comprobantes") or {}).get("comprobante") or []
	for comprobante in comprobantes:
		mensajes = (comprobante.get("mensajes") or {}).get("mensaje") or []
		for msj in mensajes:
			if msj.get("tipo") == "ERROR":
				ok = False
			tipo = msj.get("tipo") or ""
			identificador = msj.get("identificador") or ""
			mensaje = msj.get("mensaje") or ""
			additional_info = msj.get("informacionAdicional") or ""
			msj_str = f"{tipo} [{identificador}] {mensaje} {additional_info}"
			msj_list.append(msj_str)

	return ok, msj_list


def process_authorization_response(
	response: Any,
	expected_access_key: str,
) -> tuple[bool, list[str], dict[str, str]]:
	"""Process SRI `autorizacionComprobante` SOAP response.

	Ported from OCA/l10n-ecuador PR #102 (`account_edi_document.py::_l10n_ec_edi_process_response_auth`).
	Returns `(is_authorized, messages, auth_values)`.
	"""
	is_auth = False
	msj_list: list[str] = []
	auth_values: dict[str, str] = {}
	response_data = serialize_object(response, dict) if response else {}
	if not response_data or not response_data.get("autorizaciones"):
		return is_auth, msj_list, auth_values

	autorizacion_list = response_data.get("autorizaciones").get("autorizacion")
	if not isinstance(autorizacion_list, list):
		autorizacion_list = [autorizacion_list]

	for doc in autorizacion_list:
		mensajes = (doc.get("mensajes") or {}).get("mensaje") or []
		for msj in mensajes:
			tipo = msj.get("tipo") or ""
			identificador = msj.get("identificador") or ""
			mensaje = msj.get("mensaje") or ""
			additional_info = msj.get("informacionAdicional") or ""
			msj_str = f"{tipo} [{identificador}] {mensaje} {additional_info}"
			msj_list.append(msj_str)

		estado = doc.get("estado")
		if estado != "AUTORIZADO":
			is_auth = False
			continue

		is_auth = True
		msj_list = []
		auth_date = doc.get("fechaAutorizacion")
		if not isinstance(auth_date, datetime):
			auth_date = datetime.now(pytz.UTC)
		elif auth_date.tzinfo:
			auth_date = auth_date.astimezone(pytz.UTC)

		auth_values["l10n_ec_authorization_date"] = auth_date.strftime(DEFAULT_DATETIME_FORMAT)
		numero_autorizacion = doc.get("numeroAutorizacion")
		if numero_autorizacion and numero_autorizacion != expected_access_key:
			auth_values["l10n_ec_xml_access_key"] = str(numero_autorizacion)
		else:
			auth_values["l10n_ec_xml_access_key"] = expected_access_key
		break

	return is_auth, msj_list, auth_values

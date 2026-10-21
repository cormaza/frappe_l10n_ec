"""Parse emitted SRI voucher XML back to RIDE display data (pure Python).

The RIDE must show what was actually emitted, so print formats read the
voucher's unsigned XML through :func:`parse_emitted_xml` instead of
re-deriving values from business documents.
"""

from lxml import etree


def parse_emitted_xml(xml_string: str | bytes) -> dict:
	"""Parse an unsigned `guiaRemision`/`comprobanteRetencion` into display data."""
	root = etree.fromstring(xml_string.encode("utf-8") if isinstance(xml_string, str) else xml_string)
	if root.tag == "guiaRemision":
		return _parse_guia(root)
	if root.tag == "comprobanteRetencion":
		return _parse_retencion(root)
	raise ValueError(f"Unsupported emitted voucher root '{root.tag}'.")


def _text(element: etree._Element | None) -> str:
	return element.text.strip() if element is not None and element.text else ""


def _parse_guia(root: etree._Element) -> dict:
	info = root.find("infoGuiaRemision")
	return {
		"kind": "guia",
		"origin_address": _text(info.find("dirPartida")),
		"carrier_name": _text(info.find("razonSocialTransportista")),
		"carrier_id_type": _text(info.find("tipoIdentificacionTransportista")),
		"carrier_id": _text(info.find("rucTransportista")),
		"transport_start": _text(info.find("fechaIniTransporte")),
		"transport_end": _text(info.find("fechaFinTransporte")),
		"plate": _text(info.find("placa")),
		"recipients": [_parse_recipient(item) for item in root.findall("destinatarios/destinatario")],
	}


def _parse_recipient(item: etree._Element) -> dict:
	return {
		"recipient_id": _text(item.find("identificacionDestinatario")),
		"recipient_name": _text(item.find("razonSocialDestinatario")),
		"recipient_address": _text(item.find("dirDestinatario")),
		"transfer_reason": _text(item.find("motivoTraslado")),
		"route": _text(item.find("ruta")),
		"doc_code": _text(item.find("codDocSustento")),
		"doc_number": _text(item.find("numDocSustento")),
		"auth_number": _text(item.find("numAutDocSustento")),
		"doc_issue_date": _text(item.find("fechaEmisionDocSustento")),
		"lines": [
			{
				"code": _text(line.find("codigoInterno")),
				"aux_code": _text(line.find("codigoAdicional")),
				"description": _text(line.find("descripcion")),
				"qty": float(_text(line.find("cantidad")) or 0),
			}
			for line in item.findall("detalles/detalle")
		],
	}


def _parse_retencion(root: etree._Element) -> dict:
	info = root.find("infoCompRetencion")
	return {
		"kind": "retencion",
		"subject_id_type": _text(info.find("tipoIdentificacionSujetoRetenido")),
		"subject_name": _text(info.find("razonSocialSujetoRetenido")),
		"subject_id": _text(info.find("identificacionSujetoRetenido")),
		"fiscal_period": _text(info.find("periodoFiscal")),
		"docs": [_parse_sustento(item) for item in root.findall("docsSustento/docSustento")],
	}


def _parse_sustento(item: etree._Element) -> dict:
	return {
		"doc_code": _text(item.find("codDocSustento")),
		"sustento_code": _text(item.find("codSustento")),
		"doc_number": _text(item.find("numDocSustento")),
		"doc_issue_date": _text(item.find("fechaEmisionDocSustento")),
		"auth_number": _text(item.find("numAutDocSustento")),
		"subtotal": float(_text(item.find("totalSinImpuestos")) or 0),
		"total": float(_text(item.find("importeTotal")) or 0),
		"withholdings": [
			{
				"tax_code": _text(row.find("codigo")),
				"withholding_code": _text(row.find("codigoRetencion")),
				"base": float(_text(row.find("baseImponible")) or 0),
				"rate": float(_text(row.find("porcentajeRetener")) or 0),
				"value": float(_text(row.find("valorRetenido")) or 0),
			}
			for row in item.findall("retenciones/retencion")
		],
	}

"""Parse emitted SRI voucher XML back to RIDE display data (pure Python).

The RIDE must show what was actually emitted, so print formats read the
voucher's unsigned XML through :func:`parse_emitted_xml` instead of
re-deriving values from business documents.
"""

from lxml import etree


def _unwrap_autorizacion(root):
	"""Unwrap an SRI <autorizacion> envelope into (document, auth data).

	Real-world files arrive as the authorized envelope: <comprobante>
	carries the signed document (usually CDATA), plus estado,
	numeroAutorizacion and fechaAutorizacion we keep for traceability.
	Fail loud when the envelope has no parseable document inside.
	"""
	auth = {
		"estado": _text(root.find("estado")),
		"numero_autorizacion": _text(root.find("numeroAutorizacion")),
		"fecha_autorizacion": _text(root.find("fechaAutorizacion")),
		"ambiente": _text(root.find("ambiente")),
	}
	comp = root.find("comprobante")
	if comp is None:
		raise ValueError("SRI autorizacion envelope carries no <comprobante>.")
	inner_xml = (comp.text or "").strip()
	if inner_xml.startswith("<"):
		return etree.fromstring(inner_xml.encode("utf-8")), auth
	children = [child for child in comp if isinstance(child.tag, str)]
	if len(children) != 1:
		raise ValueError("SRI autorizacion <comprobante> carries no single document.")
	return children[0], auth


def parse_emitted_xml(xml_string: str | bytes) -> dict:
	"""Parse an unsigned `guiaRemision`/`comprobanteRetencion` into display data."""
	root = etree.fromstring(xml_string.encode("utf-8") if isinstance(xml_string, str) else xml_string)
	auth = None
	if root.tag == "autorizacion":
		root, auth = _unwrap_autorizacion(root)
	if root.tag == "guiaRemision":
		parsed = _parse_guia(root)
	elif root.tag == "comprobanteRetencion":
		parsed = _parse_retencion(root)
	elif root.tag == "factura":
		parsed = _parse_factura(root)
	elif root.tag == "liquidacionCompra":
		parsed = _parse_liquidacion(root)
	elif root.tag == "notaCredito":
		parsed = _parse_nota_credito(root)
	elif root.tag == "notaDebito":
		parsed = _parse_nota_debito(root)
	else:
		raise ValueError(f"Unsupported emitted voucher root '{root.tag}'.")
	if auth:
		parsed["autorizacion"] = auth
	return parsed


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


def _parse_factura(root: etree._Element) -> dict:
	trib = root.find("infoTributaria")
	info = root.find("infoFactura")
	number = "-".join(
		[
			_text(trib.find("estab")),
			_text(trib.find("ptoEmi")),
			_text(trib.find("secuencial")),
		]
	)
	taxes = [
		{
			"code": _text(row.find("codigo")),
			"rate_code": _text(row.find("codigoPorcentaje")),
			"base": float(_text(row.find("baseImponible")) or 0),
			"value": float(_text(row.find("valor")) or 0),
		}
		for row in info.findall("totalConImpuestos/totalImpuesto")
	]
	result = {
		"kind": "factura",
		"number": number,
		"emisor_ruc": _text(trib.find("ruc")),
		"emisor_name": _text(trib.find("razonSocial")),
		"clave_acceso": _text(trib.find("claveAcceso")),
		"issue_date": _text(info.find("fechaEmision")),
		"buyer_id_type": _text(info.find("tipoIdentificacionComprador")),
		"buyer_name": _text(info.find("razonSocialComprador")),
		"buyer_id": _text(info.find("identificacionComprador")),
		"total": float(_text(info.find("importeTotal")) or 0),
		"currency": _text(info.find("moneda")),
		"taxes": taxes,
		"lines": [
			{
				"code": _text(line.find("codigoPrincipal")),
				"description": _text(line.find("descripcion")),
				"qty": float(_text(line.find("cantidad")) or 0),
				"unit_price": float(_text(line.find("precioUnitario")) or 0),
				"discount": float(_text(line.find("descuento")) or 0),
				"total": float(_text(line.find("precioTotalSinImpuesto")) or 0),
				"taxes": [
					{
						"code": _text(tax.find("codigo")),
						"rate_code": _text(tax.find("codigoPorcentaje")),
						"rate": float(_text(tax.find("tarifa")) or 0),
						"base": float(_text(tax.find("baseImponible")) or 0),
						"value": float(_text(tax.find("valor")) or 0),
					}
					for tax in line.findall("impuestos/impuesto")
				],
			}
			for line in root.findall("detalles/detalle")
		],
		"info_adicional": [
			{"nombre": field.get("nombre", ""), "valor": (field.text or "").strip()}
			for field in root.findall("infoAdicional/campoAdicional")
		],
	}
	reembolsos = _parse_reembolsos(root)
	if reembolsos is not None:
		result["reembolsos"] = reembolsos
		result["reembolso_totals"] = _parse_reembolso_totals(info)
	return result


def _parse_reembolso_tax(item: etree._Element) -> dict:
	"""Parse one emitted `detalleImpuesto` back to the emission dict shape."""
	return {
		"codigo": _text(item.find("codigo")),
		"codigoPorcentaje": _text(item.find("codigoPorcentaje")),
		"tarifa": float(_text(item.find("tarifa")) or 0),
		"baseImponible": float(_text(item.find("baseImponibleReembolso")) or 0),
		"valor": float(_text(item.find("impuestoReembolso")) or 0),
	}


def _parse_reembolso(item: etree._Element) -> dict:
	"""Parse one emitted `reembolsoDetalle` back to the emission dict shape."""
	number = "-".join(
		[
			_text(item.find("estabDocReembolso")),
			_text(item.find("ptoEmiDocReembolso")),
			_text(item.find("secuencialDocReembolso")),
		]
	)
	return {
		"doc_code": _text(item.find("codDocReembolso")),
		"supplier_id_type": _text(item.find("tipoIdentificacionProveedorReembolso")),
		"supplier_id": _text(item.find("identificacionProveedorReembolso")),
		"supplier_country": _text(item.find("codPaisPagoProveedorReembolso")),
		"supplier_type": _text(item.find("tipoProveedorReembolso")),
		"sri_number": number,
		"issue_date": _text(item.find("fechaEmisionDocReembolso")),
		"auth_number": _text(item.find("numeroautorizacionDocReemb")),
		"taxes": [_parse_reembolso_tax(tax) for tax in item.findall("detalleImpuestos/detalleImpuesto")],
	}


def _parse_reembolsos(root: etree._Element) -> list | None:
	"""Parse the emitted `reembolsos` block, or None when the voucher carries none."""
	items = root.findall("reembolsos/reembolsoDetalle")
	if not items:
		return None
	return [_parse_reembolso(item) for item in items]


def _parse_reembolso_totals(info: etree._Element) -> dict:
	"""Parse the info-level reimbursement totals of an emitted voucher."""
	return {
		"doc_code": _text(info.find("codDocReembolso")),
		"total_comprobantes": float(_text(info.find("totalComprobantesReembolso")) or 0),
		"total_base": float(_text(info.find("totalBaseImponibleReembolso")) or 0),
		"total_impuesto": float(_text(info.find("totalImpuestoReembolso")) or 0),
	}


def _parse_liquidacion(root: etree._Element) -> dict:
	"""Parse an emitted `liquidacionCompra` back to RIDE display data."""
	info = root.find("infoLiquidacionCompra")
	result: dict = {
		"kind": "liquidacion_compra",
		"number": _trib_number(root.find("infoTributaria")),
		"issue_date": _text(info.find("fechaEmision")),
		"supplier_id_type": _text(info.find("tipoIdentificacionProveedor")),
		"supplier_name": _text(info.find("razonSocialProveedor")),
		"supplier_id": _text(info.find("identificacionProveedor")),
		"subtotal": float(_text(info.find("totalSinImpuestos")) or 0),
		"discount": float(_text(info.find("totalDescuento")) or 0),
		"total": float(_text(info.find("importeTotal")) or 0),
		"taxes": [
			{
				"code": _text(row.find("codigo")),
				"rate_code": _text(row.find("codigoPorcentaje")),
				"base": float(_text(row.find("baseImponible")) or 0),
				"value": float(_text(row.find("valor")) or 0),
			}
			for row in info.findall("totalConImpuestos/totalImpuesto")
		],
		"lines": [
			{
				"code": _text(line.find("codigoPrincipal")),
				"description": _text(line.find("descripcion")),
				"qty": float(_text(line.find("cantidad")) or 0),
				"unit_price": float(_text(line.find("precioUnitario")) or 0),
				"discount": float(_text(line.find("descuento")) or 0),
				"total": float(_text(line.find("precioTotalSinImpuesto")) or 0),
			}
			for line in root.findall("detalles/detalle")
		],
	}
	reembolsos = _parse_reembolsos(root)
	if reembolsos is not None:
		result["reembolsos"] = reembolsos
		result["reembolso_totals"] = _parse_reembolso_totals(info)
	return result


def _trib_number(trib) -> str:
	return "-".join([_text(trib.find("estab")), _text(trib.find("ptoEmi")), _text(trib.find("secuencial"))])


def _parse_buyer(info) -> dict:
	return {
		"buyer_id_type": _text(info.find("tipoIdentificacionComprador")),
		"buyer_name": _text(info.find("razonSocialComprador")),
		"buyer_id": _text(info.find("identificacionComprador")),
	}


def _parse_nota_credito(root: etree._Element) -> dict:
	info = root.find("infoNotaCredito")
	return {
		"kind": "nota_credito",
		"number": _trib_number(root.find("infoTributaria")),
		"issue_date": _text(info.find("fechaEmision")),
		**_parse_buyer(info),
		"modified_doc_code": _text(info.find("codDocModificado")),
		"modified_doc_number": _text(info.find("numDocModificado")),
		"sustento_issue_date": _text(info.find("fechaEmisionDocSustento")),
		"subtotal": float(_text(info.find("totalSinImpuestos")) or 0),
		"adjustment_value": float(_text(info.find("valorModificacion")) or 0),
		"reason": _text(info.find("motivo")),
		"taxes": [
			{
				"code": _text(row.find("codigo")),
				"rate_code": _text(row.find("codigoPorcentaje")),
				"base": float(_text(row.find("baseImponible")) or 0),
				"value": float(_text(row.find("valor")) or 0),
			}
			for row in info.findall("totalConImpuestos/totalImpuesto")
		],
		"lines": [
			{
				"code": _text(line.find("codigoInterno")),
				"description": _text(line.find("descripcion")),
				"qty": float(_text(line.find("cantidad")) or 0),
				"unit_price": float(_text(line.find("precioUnitario")) or 0),
				"discount": float(_text(line.find("descuento")) or 0),
				"total": float(_text(line.find("precioTotalSinImpuesto")) or 0),
			}
			for line in root.findall("detalles/detalle")
		],
	}


def _parse_nota_debito(root: etree._Element) -> dict:
	info = root.find("infoNotaDebito")
	return {
		"kind": "nota_debito",
		"number": _trib_number(root.find("infoTributaria")),
		"issue_date": _text(info.find("fechaEmision")),
		**_parse_buyer(info),
		"modified_doc_code": _text(info.find("codDocModificado")),
		"modified_doc_number": _text(info.find("numDocModificado")),
		"sustento_issue_date": _text(info.find("fechaEmisionDocSustento")),
		"subtotal": float(_text(info.find("totalSinImpuestos")) or 0),
		"total_value": float(_text(info.find("valorTotal")) or 0),
		"taxes": [
			{
				"code": _text(row.find("codigo")),
				"rate_code": _text(row.find("codigoPorcentaje")),
				"base": float(_text(row.find("baseImponible")) or 0),
				"value": float(_text(row.find("valor")) or 0),
			}
			for row in info.findall("impuestos/impuesto")
		],
		"reasons": [
			{"reason": _text(row.find("razon")), "value": float(_text(row.find("valor")) or 0)}
			for row in root.findall("motivos/motivo")
		],
	}


def _parse_retencion(root: etree._Element) -> dict:
	info = root.find("infoCompRetencion")
	trib = root.find("infoTributaria")
	number_parts = [
		_text(trib.find("estab")) if trib is not None else "",
		_text(trib.find("ptoEmi")) if trib is not None else "",
		_text(trib.find("secuencial")) if trib is not None else "",
	]
	return {
		"kind": "retencion",
		"emisor_ruc": _text(trib.find("ruc")) if trib is not None else "",
		"emisor_name": _text(trib.find("razonSocial")) if trib is not None else "",
		"clave_acceso": _text(trib.find("claveAcceso")) if trib is not None else "",
		"number": "-".join(number_parts),
		"retencion_date": _text(info.find("fechaEmision")),
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

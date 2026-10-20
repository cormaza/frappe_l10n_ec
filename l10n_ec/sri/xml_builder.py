"""SRI electronic voucher XML builders with XSD validation (pure Python).

Ported from the field order proven against SRI pruebas by
`cuymo/facturacion-electronica-ec` (MIT), validated here against the
official XSD schemas bundled in `l10n_ec/sri/xsd/`.
"""

from pathlib import Path

from lxml import etree

XSD_DIR = Path(__file__).resolve().parent / "xsd"

SCHEMAS = {
	"factura": ("factura_V1.1.0.xsd", "1.1.0", "factura"),
	"nota_credito": ("NotaCredito_V1.1.0.xsd", "1.1.0", "notaCredito"),
	"nota_debito": ("NotaDebito_V1.0.0.xsd", "1.0.0", "notaDebito"),
	"liquidacion_compra": ("LiquidacionCompra_V1.1.0.xsd", "1.1.0", "liquidacionCompra"),
	"retencion": ("ComprobanteRetencion_V2.0.0.xsd", "2.0.0", "comprobanteRetencion"),
	"guia": ("GuiaRemision_V1.1.0.xsd", "1.1.0", "guiaRemision"),
}


class SriXmlError(ValueError):
	"""Raised when generated XML fails official XSD validation."""


def build_factura_xml(ctx: dict, data: dict) -> str:
	"""Build an unsigned `factura` (codDoc 01) XML string."""
	totals = "".join(_total_tax(t) for t in data["tax_totals"])
	payments = "".join(_payment(p) for p in data["payments"])
	lines = "".join(_factura_line(item) for item in data["lines"])
	buyer_address = (
		f"<direccionComprador>{escape_xml(data['buyer_address'])}</direccionComprador>"
		if data.get("buyer_address")
		else ""
	)
	return (
		'<?xml version="1.0" encoding="UTF-8"?>\n'
		f'<factura id="comprobante" version="{SCHEMAS["factura"][1]}">'
		f"{_info_tributaria(ctx)}"
		"<infoFactura>"
		f"<fechaEmision>{data['issue_date']}</fechaEmision>"
		f"{_branch_address_tag(ctx)}"
		f"{_special_taxpayer_tag(ctx)}"
		f"{_accounting_required_tag(ctx)}"
		f"<tipoIdentificacionComprador>{data['buyer_id_type']}</tipoIdentificacionComprador>"
		f"<razonSocialComprador>{escape_xml(data['buyer_name'])}</razonSocialComprador>"
		f"<identificacionComprador>{escape_xml(data['buyer_id'])}</identificacionComprador>"
		f"{buyer_address}"
		f"<totalSinImpuestos>{format_2(data['subtotal'])}</totalSinImpuestos>"
		f"<totalDescuento>{format_2(data['discount'])}</totalDescuento>"
		f"<totalConImpuestos>{totals}</totalConImpuestos>"
		f"<propina>{format_2(data['tip'])}</propina>"
		f"<importeTotal>{format_2(data['total'])}</importeTotal>"
		"<moneda>DOLAR</moneda>"
		f"<pagos>{payments}</pagos>"
		"</infoFactura>"
		f"<detalles>{lines}</detalles>"
		"</factura>"
	)


def build_nota_credito_xml(ctx: dict, data: dict) -> str:
	"""Build an unsigned `notaCredito` (codDoc 04) XML string."""
	totals = "".join(_total_tax(t) for t in data["tax_totals"])
	lines = "".join(_nota_credito_line(item) for item in data["lines"])
	return (
		'<?xml version="1.0" encoding="UTF-8"?>\n'
		f'<notaCredito id="comprobante" version="{SCHEMAS["nota_credito"][1]}">'
		f"{_info_tributaria(ctx)}"
		"<infoNotaCredito>"
		f"<fechaEmision>{data['issue_date']}</fechaEmision>"
		f"{_branch_address_tag(ctx)}"
		f"<tipoIdentificacionComprador>{data['buyer_id_type']}</tipoIdentificacionComprador>"
		f"<razonSocialComprador>{escape_xml(data['buyer_name'])}</razonSocialComprador>"
		f"<identificacionComprador>{escape_xml(data['buyer_id'])}</identificacionComprador>"
		f"{_special_taxpayer_tag(ctx)}"
		f"{_accounting_required_tag(ctx)}"
		f"<codDocModificado>{data['modified_doc_code']}</codDocModificado>"
		f"<numDocModificado>{escape_xml(data['modified_doc_number'])}</numDocModificado>"
		f"<fechaEmisionDocSustento>{escape_xml(data['sustento_issue_date'])}</fechaEmisionDocSustento>"
		f"<totalSinImpuestos>{format_2(data['subtotal'])}</totalSinImpuestos>"
		f"<valorModificacion>{format_2(data['adjustment_value'])}</valorModificacion>"
		"<moneda>DOLAR</moneda>"
		f"<totalConImpuestos>{totals}</totalConImpuestos>"
		f"<motivo>{escape_xml(data['reason'])}</motivo>"
		"</infoNotaCredito>"
		f"<detalles>{lines}</detalles>"
		"</notaCredito>"
	)


def build_nota_debito_xml(ctx: dict, data: dict) -> str:
	"""Build an unsigned `notaDebito` (codDoc 05) XML string."""
	taxes = "".join(_flat_tax(t) for t in data["taxes"])
	reasons = "".join(_debit_reason(m) for m in data["reasons"])
	return (
		'<?xml version="1.0" encoding="UTF-8"?>\n'
		f'<notaDebito id="comprobante" version="{SCHEMAS["nota_debito"][1]}">'
		f"{_info_tributaria(ctx)}"
		"<infoNotaDebito>"
		f"<fechaEmision>{data['issue_date']}</fechaEmision>"
		f"{_branch_address_tag(ctx)}"
		f"<tipoIdentificacionComprador>{data['buyer_id_type']}</tipoIdentificacionComprador>"
		f"<razonSocialComprador>{escape_xml(data['buyer_name'])}</razonSocialComprador>"
		f"<identificacionComprador>{escape_xml(data['buyer_id'])}</identificacionComprador>"
		f"{_special_taxpayer_tag(ctx)}"
		f"{_accounting_required_tag(ctx)}"
		f"<codDocModificado>{data['modified_doc_code']}</codDocModificado>"
		f"<numDocModificado>{escape_xml(data['modified_doc_number'])}</numDocModificado>"
		f"<fechaEmisionDocSustento>{escape_xml(data['sustento_issue_date'])}</fechaEmisionDocSustento>"
		f"<totalSinImpuestos>{format_2(data['subtotal'])}</totalSinImpuestos>"
		f"<impuestos>{taxes}</impuestos>"
		f"<valorTotal>{format_2(data['total_value'])}</valorTotal>"
		"</infoNotaDebito>"
		f"<motivos>{reasons}</motivos>"
		"</notaDebito>"
	)


def build_retencion_xml(ctx: dict, data: dict) -> str:
	"""Build an unsigned `comprobanteRetencion` (codDoc 07) XML string."""
	docs = "".join(_sustento_doc(item) for item in data["docs"])
	return (
		'<?xml version="1.0" encoding="UTF-8"?>\n'
		f'<comprobanteRetencion id="comprobante" version="{SCHEMAS["retencion"][1]}">'
		f"{_info_tributaria(ctx)}"
		"<infoCompRetencion>"
		f"<fechaEmision>{data['issue_date']}</fechaEmision>"
		f"{_branch_address_tag(ctx)}"
		f"{_special_taxpayer_tag(ctx)}"
		f"{_accounting_required_tag(ctx)}"
		f"<tipoIdentificacionSujetoRetenido>{data['subject_id_type']}</tipoIdentificacionSujetoRetenido>"
		f"<parteRel>{data.get('related_party', 'NO')}</parteRel>"
		f"<razonSocialSujetoRetenido>{escape_xml(data['subject_name'])}</razonSocialSujetoRetenido>"
		f"<identificacionSujetoRetenido>{escape_xml(data['subject_id'])}</identificacionSujetoRetenido>"
		f"<periodoFiscal>{data['fiscal_period']}</periodoFiscal>"
		"</infoCompRetencion>"
		f"<docsSustento>{docs}</docsSustento>"
		"</comprobanteRetencion>"
	)


def _sustento_doc(doc: dict) -> str:
	"""Build one `docSustento` block (sustento + taxes + withholdings + payments)."""
	doc_taxes = "".join(
		"<impuestoDocSustento>"
		f"<codImpuestoDocSustento>{tax['tax_code']}</codImpuestoDocSustento>"
		f"<codigoPorcentaje>{tax['rate_code']}</codigoPorcentaje>"
		f"<baseImponible>{format_2(tax['base'])}</baseImponible>"
		f"<tarifa>{format_2(tax['rate'])}</tarifa>"
		f"<valorImpuesto>{format_2(tax['tax_value'])}</valorImpuesto>"
		"</impuestoDocSustento>"
		for tax in doc.get("doc_taxes", [])
	)
	withholdings = "".join(
		"<retencion>"
		f"<codigo>{item['code']}</codigo>"
		f"<codigoRetencion>{item['withholding_code']}</codigoRetencion>"
		f"<baseImponible>{format_2(item['base'])}</baseImponible>"
		f"<porcentajeRetener>{format_2(item['rate'])}</porcentajeRetener>"
		f"<valorRetenido>{format_2(item['value'])}</valorRetenido>"
		"</retencion>"
		for item in doc.get("withholdings", [])
	)
	payments = "".join(_payment(item) for item in doc.get("payments", []))
	accounting_date = (
		f"<fechaRegistroContable>{escape_xml(doc['accounting_date'])}</fechaRegistroContable>"
		if doc.get("accounting_date")
		else ""
	)
	return (
		"<docSustento>"
		f"<codSustento>{doc['sustento_code']}</codSustento>"
		f"<codDocSustento>{doc['doc_code']}</codDocSustento>"
		f"<numDocSustento>{escape_xml(doc['doc_number'].replace('-', ''))}</numDocSustento>"
		f"<fechaEmisionDocSustento>{escape_xml(doc['issue_date'])}</fechaEmisionDocSustento>"
		f"{accounting_date}"
		f"<numAutDocSustento>{escape_xml(doc['auth_number'])}</numAutDocSustento>"
		f"<pagoLocExt>{doc.get('local_payment', '01')}</pagoLocExt>"
		f"<totalSinImpuestos>{format_2(doc['subtotal'])}</totalSinImpuestos>"
		f"<importeTotal>{format_2(doc['total'])}</importeTotal>"
		f"<impuestosDocSustento>{doc_taxes}</impuestosDocSustento>"
		f"<retenciones>{withholdings}</retenciones>"
		f"<pagos>{payments}</pagos>"
		"</docSustento>"
	)


def build_liquidacion_compra_xml(ctx: dict, data: dict) -> str:
	"""Build an unsigned `liquidacionCompra` (codDoc 03) XML string."""
	totals = "".join(_total_tax(t) for t in data["tax_totals"])
	payments = "".join(_payment(p) for p in data["payments"])
	lines = "".join(_factura_line(item) for item in data["lines"])
	supplier_address = (
		f"<direccionProveedor>{escape_xml(data['supplier_address'])}</direccionProveedor>"
		if data.get("supplier_address")
		else ""
	)
	return (
		'<?xml version="1.0" encoding="UTF-8"?>\n'
		f'<liquidacionCompra id="comprobante" version="{SCHEMAS["liquidacion_compra"][1]}">'
		f"{_info_tributaria(ctx)}"
		"<infoLiquidacionCompra>"
		f"<fechaEmision>{data['issue_date']}</fechaEmision>"
		f"{_branch_address_tag(ctx)}"
		f"{_special_taxpayer_tag(ctx)}"
		f"{_accounting_required_tag(ctx)}"
		f"<tipoIdentificacionProveedor>{data['supplier_id_type']}</tipoIdentificacionProveedor>"
		f"<razonSocialProveedor>{escape_xml(data['supplier_name'])}</razonSocialProveedor>"
		f"<identificacionProveedor>{escape_xml(data['supplier_id'])}</identificacionProveedor>"
		f"{supplier_address}"
		f"<totalSinImpuestos>{format_2(data['subtotal'])}</totalSinImpuestos>"
		f"<totalDescuento>{format_2(data['discount'])}</totalDescuento>"
		f"<totalConImpuestos>{totals}</totalConImpuestos>"
		f"<importeTotal>{format_2(data['total'])}</importeTotal>"
		"<moneda>DOLAR</moneda>"
		f"<pagos>{payments}</pagos>"
		"</infoLiquidacionCompra>"
		f"<detalles>{lines}</detalles>"
		"</liquidacionCompra>"
	)


def build_guia_xml(ctx: dict, data: dict) -> str:
	"""Build an unsigned `guiaRemision` (codDoc 06) XML string."""
	recipients = "".join(_guia_recipient(item) for item in data["recipients"])
	return (
		'<?xml version="1.0" encoding="UTF-8"?>\n'
		f'<guiaRemision id="comprobante" version="{SCHEMAS["guia"][1]}">'
		f"{_info_tributaria(ctx)}"
		"<infoGuiaRemision>"
		f"{_branch_address_tag(ctx)}"
		f"<dirPartida>{escape_xml(data['origin_address'])}</dirPartida>"
		f"<razonSocialTransportista>{escape_xml(data['carrier_name'])}</razonSocialTransportista>"
		f"<tipoIdentificacionTransportista>{data['carrier_id_type']}</tipoIdentificacionTransportista>"
		f"<rucTransportista>{escape_xml(data['carrier_id'])}</rucTransportista>"
		f"{_accounting_required_tag(ctx)}"
		f"{_special_taxpayer_tag(ctx)}"
		f"<fechaIniTransporte>{data['transport_start']}</fechaIniTransporte>"
		f"<fechaFinTransporte>{data['transport_end']}</fechaFinTransporte>"
		f"<placa>{escape_xml(data['plate'])}</placa>"
		"</infoGuiaRemision>"
		f"<destinatarios>{recipients}</destinatarios>"
		"</guiaRemision>"
	)


def _guia_recipient(item: dict) -> str:
	"""Build one `destinatario` block with its support document and lines."""
	route = f"<ruta>{escape_xml(item['route'])}</ruta>" if item.get("route") else ""
	auth = (
		f"<numAutDocSustento>{escape_xml(item['auth_number'])}</numAutDocSustento>"
		if item.get("auth_number")
		else ""
	)
	sustento_date = (
		f"<fechaEmisionDocSustento>{item['doc_issue_date']}</fechaEmisionDocSustento>"
		if item.get("doc_issue_date")
		else ""
	)
	sustento = (
		f"<codDocSustento>{item['doc_code']}</codDocSustento>"
		f"<numDocSustento>{escape_xml(item['doc_number'])}</numDocSustento>"
		f"{auth}"
		f"{sustento_date}"
		if item.get("doc_code") and item.get("doc_number")
		else ""
	)
	lines = "".join(_guia_line(line) for line in item["lines"])
	return (
		"<destinatario>"
		f"<identificacionDestinatario>{escape_xml(item['recipient_id'])}</identificacionDestinatario>"
		f"<razonSocialDestinatario>{escape_xml(item['recipient_name'])}</razonSocialDestinatario>"
		f"<dirDestinatario>{escape_xml(item['recipient_address'])}</dirDestinatario>"
		f"<motivoTraslado>{escape_xml(item['transfer_reason'])}</motivoTraslado>"
		f"{route}"
		f"{sustento}"
		f"<detalles>{lines}</detalles>"
		"</destinatario>"
	)


def _guia_line(line: dict) -> str:
	"""Build one recipient `detalle` (quantity-only, no taxes)."""
	aux = f"<codigoAdicional>{escape_xml(line['aux_code'])}</codigoAdicional>" if line.get("aux_code") else ""
	return (
		"<detalle>"
		f"<codigoInterno>{escape_xml(line['code'])}</codigoInterno>"
		f"{aux}"
		f"<descripcion>{escape_xml(line['description'])}</descripcion>"
		f"<cantidad>{format_6(line['qty'])}</cantidad>"
		"</detalle>"
	)


def validate_against_xsd(xml_string: str | bytes, schema_name: str) -> bool:
	"""Validate an XML voucher against its official XSD; raise `SriXmlError` if invalid."""
	filename = SCHEMAS[schema_name][0]
	schema = etree.XMLSchema(etree.parse(str(XSD_DIR / filename)))
	document = etree.fromstring(xml_string.encode("utf-8") if isinstance(xml_string, str) else xml_string)
	if not schema.validate(document):
		details = "; ".join(str(error) for error in schema.error_log)
		raise SriXmlError(f"XML does not validate against {filename}: {details}")
	return True


def escape_xml(text: str) -> str:
	"""Escape free-text values for SRI XML content."""
	return (
		(text or "")
		.replace("&", "&amp;")
		.replace("<", "&lt;")
		.replace(">", "&gt;")
		.replace('"', "&quot;")
		.replace("'", "&apos;")
	)


def format_2(number: float) -> str:
	"""Format monetary values with two decimals as SRI requires."""
	return f"{number:.2f}"


def format_6(number: float) -> str:
	"""Format quantities and unit prices with six decimals as SRI requires."""
	return f"{number:.6f}"


def _info_tributaria(ctx: dict) -> str:
	trade_name = (
		f"<nombreComercial>{escape_xml(ctx['trade_name'])}</nombreComercial>" if ctx.get("trade_name") else ""
	)
	return (
		"<infoTributaria>"
		f"<ambiente>{ctx['environment']}</ambiente>"
		"<tipoEmision>1</tipoEmision>"
		f"<razonSocial>{escape_xml(ctx['legal_name'])}</razonSocial>"
		f"{trade_name}"
		f"<ruc>{ctx['ruc']}</ruc>"
		f"<claveAcceso>{ctx['access_key']}</claveAcceso>"
		f"<codDoc>{ctx['doc_code']}</codDoc>"
		f"<estab>{ctx['establishment']}</estab>"
		f"<ptoEmi>{ctx['emission_point']}</ptoEmi>"
		f"<secuencial>{ctx['sequential']}</secuencial>"
		f"<dirMatriz>{escape_xml(ctx['head_office_address'])}</dirMatriz>"
		"</infoTributaria>"
	)


def _special_taxpayer_tag(ctx: dict) -> str:
	if not ctx.get("special_taxpayer"):
		return ""
	return f"<contribuyenteEspecial>{escape_xml(ctx['special_taxpayer'])}</contribuyenteEspecial>"


def _accounting_required_tag(ctx: dict) -> str:
	return f"<obligadoContabilidad>{'SI' if ctx.get('accounting_required') else 'NO'}</obligadoContabilidad>"


def _branch_address_tag(ctx: dict) -> str:
	return f"<dirEstablecimiento>{escape_xml(ctx['branch_address'])}</dirEstablecimiento>"


def _total_tax(tax: dict) -> str:
	return (
		"<totalImpuesto>"
		f"<codigo>{tax['code']}</codigo>"
		f"<codigoPorcentaje>{tax['rate_code']}</codigoPorcentaje>"
		f"<baseImponible>{format_2(tax['base'])}</baseImponible>"
		f"<valor>{format_2(tax['value'])}</valor>"
		"</totalImpuesto>"
	)


def _payment(payment: dict) -> str:
	term = ""
	if payment.get("term") is not None:
		term = (
			f"<plazo>{payment['term']}</plazo>"
			f"<unidadTiempo>{escape_xml(payment.get('time_unit') or 'dias')}</unidadTiempo>"
		)
	return (
		"<pago>"
		f"<formaPago>{payment['method']}</formaPago>"
		f"<total>{format_2(payment['amount'])}</total>"
		f"{term}"
		"</pago>"
	)


def _line_taxes(taxes: list) -> str:
	return "".join(
		"<impuesto>"
		f"<codigo>{tax['code']}</codigo>"
		f"<codigoPorcentaje>{tax['rate_code']}</codigoPorcentaje>"
		f"<tarifa>{format_2(tax['rate'])}</tarifa>"
		f"<baseImponible>{format_2(tax['base'])}</baseImponible>"
		f"<valor>{format_2(tax['value'])}</valor>"
		"</impuesto>"
		for tax in taxes
	)


def _factura_line(line: dict) -> str:
	aux_code = (
		f"<codigoAuxiliar>{escape_xml(line['aux_code'])}</codigoAuxiliar>" if line.get("aux_code") else ""
	)
	return (
		"<detalle>"
		f"<codigoPrincipal>{escape_xml(line['code'])}</codigoPrincipal>"
		f"{aux_code}"
		f"<descripcion>{escape_xml(line['description'])}</descripcion>"
		f"<cantidad>{format_6(line['qty'])}</cantidad>"
		f"<precioUnitario>{format_6(line['unit_price'])}</precioUnitario>"
		f"<descuento>{format_2(line['discount'])}</descuento>"
		f"<precioTotalSinImpuesto>{format_2(line['subtotal'])}</precioTotalSinImpuesto>"
		f"<impuestos>{_line_taxes(line['taxes'])}</impuestos>"
		"</detalle>"
	)


def _nota_credito_line(line: dict) -> str:
	aux_code = (
		f"<codigoAdicional>{escape_xml(line['aux_code'])}</codigoAdicional>" if line.get("aux_code") else ""
	)
	return (
		"<detalle>"
		f"<codigoInterno>{escape_xml(line['code'])}</codigoInterno>"
		f"{aux_code}"
		f"<descripcion>{escape_xml(line['description'])}</descripcion>"
		f"<cantidad>{format_6(line['qty'])}</cantidad>"
		f"<precioUnitario>{format_6(line['unit_price'])}</precioUnitario>"
		f"<descuento>{format_2(line['discount'])}</descuento>"
		f"<precioTotalSinImpuesto>{format_2(line['subtotal'])}</precioTotalSinImpuesto>"
		f"<impuestos>{_line_taxes(line['taxes'])}</impuestos>"
		"</detalle>"
	)


def _flat_tax(tax: dict) -> str:
	return (
		"<impuesto>"
		f"<codigo>{tax['code']}</codigo>"
		f"<codigoPorcentaje>{tax['rate_code']}</codigoPorcentaje>"
		f"<tarifa>{format_2(tax['rate'])}</tarifa>"
		f"<baseImponible>{format_2(tax['base'])}</baseImponible>"
		f"<valor>{format_2(tax['value'])}</valor>"
		"</impuesto>"
	)


def _debit_reason(reason: dict) -> str:
	return (
		"<motivo>"
		f"<razon>{escape_xml(reason['reason'])}</razon>"
		f"<valor>{format_2(reason['value'])}</valor>"
		"</motivo>"
	)

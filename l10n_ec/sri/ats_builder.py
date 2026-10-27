"""ATS XML renderer and monthly zip (pure Python, no frappe).

Renders the plain dicts aggregated by ``l10n_ec.sri.ats_collector`` into the
SRI ``AT{mmaaaa}.xml`` document, validated offline against the vendored
``l10n_ec/sri/xsd/ats.xsd``, plus the single-file month zip for the portal.

Element order follows ``ats.xsd`` exactly (every ``xsd:sequence`` is
order-sensitive); tag names are the SRI literals. Empty sections are omitted
(the section wrappers are ``minOccurs="0"``), never placeholder rows.

``montoIce`` is mandatory on every ``compras`` row and optional on ``ventas``
rows, mirroring the schema. Anything the builder cannot represent honestly
is refused with ``SriXmlError``, never repaired with defaults.
"""

import io
import re
import zipfile

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.xml_builder import (
	SriXmlError,
	escape_xml,
	format_2,
	validate_against_xsd,
)

#: Collector keys kept for downstream filings but never rendered into ATS XML.
IGNORED_VENTAS_KEYS = frozenset(
	{
		"received_number",
		"received_authorization",
		"received_date",
		"received_access_key",
	}
)

#: ``compras`` elements that must always be present (``minOccurs="1"`` in ats.xsd).
COMPRAS_REQUIRED = (
	"codSustento",
	"tpIdProv",
	"idProv",
	"tipoComprobante",
	"fechaRegistro",
	"establecimiento",
	"puntoEmision",
	"secuencial",
	"fechaEmision",
	"autorizacion",
	"baseNoGraIva",
	"baseImponible",
	"baseImpGrav",
	"baseImpExe",
	"montoIce",
	"montoIva",
	"valorRetBienes",
	"valorRetServicios",
	"valRetServ100",
)

#: Optional ``compras`` scalars, in schema order.
COMPRAS_OPTIONAL = (
	"denoProv",
	"parteRel",
	"valRetBien10",
	"valRetServ20",
	"valRetServ50",
)

#: ``ventas`` elements that must always be present.
VENTAS_REQUIRED = (
	"tpIdCliente",
	"idCliente",
	"tipoComprobante",
	"tipoEmision",
	"numeroComprobantes",
	"baseNoGraIva",
	"baseImponible",
	"baseImpGrav",
	"montoIva",
	"valorRetIva",
	"valorRetRenta",
)

#: ``exportaciones`` elements that must always be present.
EXPORTACIONES_REQUIRED = (
	"exportacionDe",
	"tipoComprobante",
	"fechaEmbarque",
	"valorFOB",
	"valorFOBComprobante",
	"establecimiento",
	"puntoEmision",
	"secuencial",
	"autorizacion",
	"fechaEmision",
)

#: ``anulados`` elements, all mandatory and in schema order.
ANULADOS_FIELDS = (
	"tipoComprobante",
	"establecimiento",
	"puntoEmision",
	"secuencialInicio",
	"secuencialFin",
	"autorizacion",
)

#: ``air`` detail row, in schema order.
AIR_FIELDS = ("codRetAir", "baseImpAir", "porcentajeAir", "valRetAir")

#: ``reembolso`` detail row, in ats.xsd schema order.
REEMBOLSO_FIELDS = (
	"tipoComprobanteReemb",
	"tpIdProvReemb",
	"idProvReemb",
	"establecimientoReemb",
	"puntoEmisionReemb",
	"secuencialReemb",
	"fechaEmisionReemb",
	"autorizacionReemb",
	"baseImponibleReemb",
	"baseImpGravReemb",
	"baseNoGraIvaReemb",
	"baseImpExeReemb",
	"montoIceRemb",
	"montoIvaRemb",
)

#: Retencion reference group: all five travel together or not at all.
RETENCION_FIELDS = (
	"estabRetencion1",
	"ptoEmiRetencion1",
	"secRetencion1",
	"autRetencion1",
	"fechaEmiRet1",
)


def _parse_period(period: str) -> tuple:
	"""Split a fiscal period into ``(month, year)`` zero-padded strings.

	Accepts ``MMYYYY``, ``MM/YYYY``, ``MM-YYYY``, ``YYYY-MM`` and ``YYYY/MM``.
	Anything else fails loud instead of guessing the filing month.
	"""
	text = (period or "").strip()
	match = re.fullmatch(r"(\d{4})[-/](\d{2})", text)
	if match:
		year, month = match.group(1), match.group(2)
	else:
		match = re.fullmatch(r"(\d{2})[-/](\d{4})", text)
		if match:
			month, year = match.group(1), match.group(2)
		elif re.fullmatch(r"\d{6}", text):
			if text.startswith(("19", "20")):
				year, month = text[:4], text[4:]
			else:
				month, year = text[:2], text[2:]
		else:
			raise SriXmlError(_("ATS period '{}' is not a fiscal month (MMYYYY).").format(period))
	if not ("01" <= month <= "12"):
		raise SriXmlError(_("ATS period month '{}' is out of range.").format(period))
	if not ("2000" <= year <= "9999"):
		raise SriXmlError(_("ATS period year '{}' is out of range.").format(period))
	return (month, year)


def _informante(collected: dict) -> dict:
	"""Return the informante header carried by the collected payload.

	Reads ``collected["informante"]`` (or the ``"header"`` alias). ``RUC`` and
	company name are mandatory; the single-value enumerations default to the
	only values the schema admits.
	"""
	header = collected.get("informante", collected.get("header", {})) or {}
	if not isinstance(header, dict):
		raise SriXmlError(_("ATS informante must be a dict of header fields."))
	informante = {
		"TipoIDInformante": header.get("TipoIDInformante", "R"),
		"IdInformante": header.get("IdInformante", ""),
		"razonSocial": header.get("razonSocial", ""),
		"codigoOperativo": header.get("codigoOperativo", "IVA"),
	}
	for key in ("regimenMicroempresa", "numEstabRuc", "totalVentas"):
		if header.get(key) not in (None, "", False):
			informante[key] = header[key]
	if not informante["IdInformante"]:
		raise SriXmlError(_("ATS informante needs 'IdInformante' (RUC)."))
	if not informante["razonSocial"]:
		raise SriXmlError(_("ATS informante needs 'razonSocial'."))
	if informante["TipoIDInformante"] != "R":
		raise SriXmlError(_("ATS 'TipoIDInformante' '{}' is not 'R'.").format(header.get("TipoIDInformante")))
	if informante["codigoOperativo"] != "IVA":
		raise SriXmlError(_("ATS 'codigoOperativo' '{}' is not 'IVA'.").format(header.get("codigoOperativo")))
	return informante


def _check_keys(row: dict, known: frozenset, where: str) -> None:
	"""Refuse row keys that are neither schema elements nor documented extras."""
	for key in row:
		if key not in known:
			raise SriXmlError(_("ATS {} row carries unknown field '{}'.").format(where, key))


def _require(row: dict, fields: tuple, where: str) -> None:
	"""Fail loud on missing mandatory elements instead of inventing values."""
	for field in fields:
		if row.get(field) in (None, ""):
			raise SriXmlError(_("ATS {} row needs '{}'.").format(where, field))


def _money(value: float) -> str:
	return format_2(float(value or 0.0))


def _air_block(entries: list) -> str:
	"""Render one ``air`` wrapper from withholding detail rows."""
	details = ""
	for entry in entries or []:
		_check_keys(entry, frozenset(AIR_FIELDS), "air")
		_require(entry, AIR_FIELDS, "air")
		details += (
			"<detalleAir>"
			f"<codRetAir>{escape_xml(str(entry['codRetAir']))}</codRetAir>"
			f"<baseImpAir>{_money(entry['baseImpAir'])}</baseImpAir>"
			f"<porcentajeAir>{_money(entry['porcentajeAir'])}</porcentajeAir>"
			f"<valRetAir>{_money(entry['valRetAir'])}</valRetAir>"
			"</detalleAir>"
		)
	return f"<air>{details}</air>" if details else ""


def _formas_de_pago_block(methods: list) -> str:
	"""Render one ``formasDePago`` wrapper; empty lists produce no element."""
	codes = "".join(f"<formaPago>{escape_xml(str(code))}</formaPago>" for code in methods or [])
	return f"<formasDePago>{codes}</formasDePago>" if codes else ""


def _reembolsos_block(row: dict) -> str:
	"""Render the ``reembolsos`` wrapper; reembolsos require ``totbasesImpReemb``."""
	entries = row.get("reembolsos")
	if not entries:
		return ""
	if row.get("totbasesImpReemb") in (None, ""):
		raise SriXmlError(_("ATS compras row carries reembolsos without 'totbasesImpReemb'."))
	if not isinstance(entries, (list, tuple)):
		raise SriXmlError(_("ATS compras 'reembolsos' must be a list of rows."))
	details = ""
	for entry in entries:
		if not isinstance(entry, dict):
			raise SriXmlError(_("ATS reembolso row must be a dict of voucher fields."))
		_check_keys(entry, frozenset(REEMBOLSO_FIELDS), "reembolso")
		_require(entry, REEMBOLSO_FIELDS, "reembolso")
		details += (
			"<reembolso>"
			f"<tipoComprobanteReemb>{escape_xml(str(entry['tipoComprobanteReemb']))}</tipoComprobanteReemb>"
			f"<tpIdProvReemb>{escape_xml(str(entry['tpIdProvReemb']))}</tpIdProvReemb>"
			f"<idProvReemb>{escape_xml(str(entry['idProvReemb']))}</idProvReemb>"
			f"<establecimientoReemb>{escape_xml(str(entry['establecimientoReemb']))}</establecimientoReemb>"
			f"<puntoEmisionReemb>{escape_xml(str(entry['puntoEmisionReemb']))}</puntoEmisionReemb>"
			f"<secuencialReemb>{escape_xml(str(entry['secuencialReemb']))}</secuencialReemb>"
			f"<fechaEmisionReemb>{escape_xml(str(entry['fechaEmisionReemb']))}</fechaEmisionReemb>"
			f"<autorizacionReemb>{escape_xml(str(entry['autorizacionReemb']))}</autorizacionReemb>"
			f"<baseImponibleReemb>{_money(entry['baseImponibleReemb'])}</baseImponibleReemb>"
			f"<baseImpGravReemb>{_money(entry['baseImpGravReemb'])}</baseImpGravReemb>"
			f"<baseNoGraIvaReemb>{_money(entry['baseNoGraIvaReemb'])}</baseNoGraIvaReemb>"
			f"<baseImpExeReemb>{_money(entry['baseImpExeReemb'])}</baseImpExeReemb>"
			f"<montoIceRemb>{_money(entry['montoIceRemb'])}</montoIceRemb>"
			f"<montoIvaRemb>{_money(entry['montoIvaRemb'])}</montoIvaRemb>"
			"</reembolso>"
		)
	return f"<reembolsos>{details}</reembolsos>"


def _retencion_block(row: dict) -> str:
	"""Render the withholding reference group, all five fields or none."""
	present = [field for field in RETENCION_FIELDS if row.get(field) not in (None, "")]
	if not present:
		return ""
	if len(present) != len(RETENCION_FIELDS):
		raise SriXmlError(
			_("ATS compras row carries a partial withholding reference ({}).").format(", ".join(present))
		)
	return (
		f"<estabRetencion1>{escape_xml(str(row['estabRetencion1']))}</estabRetencion1>"
		f"<ptoEmiRetencion1>{escape_xml(str(row['ptoEmiRetencion1']))}</ptoEmiRetencion1>"
		f"<secRetencion1>{escape_xml(str(row['secRetencion1']))}</secRetencion1>"
		f"<autRetencion1>{escape_xml(str(row['autRetencion1']))}</autRetencion1>"
		f"<fechaEmiRet1>{escape_xml(str(row['fechaEmiRet1']))}</fechaEmiRet1>"
	)


def _optional_scalar(row: dict, field: str, money: bool = False) -> str:
	"""Render an optional scalar only when the row carries a nonzero value."""
	if row.get(field) in (None, "", 0, 0.0):
		return ""
	if money:
		return f"<{field}>{_money(row[field])}</{field}>"
	return f"<{field}>{escape_xml(str(row[field]))}</{field}>"


def _render_compra(row: dict) -> str:
	"""Render one ``detalleCompras`` in ats.xsd element order."""
	known = frozenset(
		COMPRAS_REQUIRED
		+ COMPRAS_OPTIONAL
		+ ("totbasesImpReemb", "formasDePago", "air", "reembolsos")
		+ RETENCION_FIELDS
	)
	_check_keys(row, known, "compras")
	_require(row, COMPRAS_REQUIRED, "compras")
	optional_head = "".join(_optional_scalar(row, field) for field in ("denoProv", "parteRel"))
	optional_low = "".join(
		_optional_scalar(row, field, money=True) for field in ("valRetBien10", "valRetServ20")
	)
	return (
		"<detalleCompras>"
		f"<codSustento>{escape_xml(str(row['codSustento']))}</codSustento>"
		f"<tpIdProv>{escape_xml(str(row['tpIdProv']))}</tpIdProv>"
		f"<idProv>{escape_xml(str(row['idProv']))}</idProv>"
		f"<tipoComprobante>{escape_xml(str(row['tipoComprobante']))}</tipoComprobante>"
		f"{optional_head}"
		f"<fechaRegistro>{escape_xml(str(row['fechaRegistro']))}</fechaRegistro>"
		f"<establecimiento>{escape_xml(str(row['establecimiento']))}</establecimiento>"
		f"<puntoEmision>{escape_xml(str(row['puntoEmision']))}</puntoEmision>"
		f"<secuencial>{escape_xml(str(row['secuencial']))}</secuencial>"
		f"<fechaEmision>{escape_xml(str(row['fechaEmision']))}</fechaEmision>"
		f"<autorizacion>{escape_xml(str(row['autorizacion']))}</autorizacion>"
		f"<baseNoGraIva>{_money(row['baseNoGraIva'])}</baseNoGraIva>"
		f"<baseImponible>{_money(row['baseImponible'])}</baseImponible>"
		f"<baseImpGrav>{_money(row['baseImpGrav'])}</baseImpGrav>"
		f"<baseImpExe>{_money(row['baseImpExe'])}</baseImpExe>"
		f"<montoIce>{_money(row['montoIce'])}</montoIce>"
		f"<montoIva>{_money(row['montoIva'])}</montoIva>"
		f"{optional_low}"
		f"<valorRetBienes>{_money(row['valorRetBienes'])}</valorRetBienes>"
		f"{_optional_scalar(row, 'valRetServ50', money=True)}"
		f"<valorRetServicios>{_money(row['valorRetServicios'])}</valorRetServicios>"
		f"<valRetServ100>{_money(row['valRetServ100'])}</valRetServ100>"
		f"{_optional_scalar(row, 'totbasesImpReemb', money=True)}"
		f"{_formas_de_pago_block(row.get('formasDePago'))}"
		f"{_air_block(row.get('air'))}"
		f"{_retencion_block(row)}"
		f"{_reembolsos_block(row)}"
		"</detalleCompras>"
	)


def _render_venta(row: dict) -> str:
	"""Render one ``detalleVentas`` in ats.xsd element order."""
	known = frozenset((*VENTAS_REQUIRED, "denoCli", "montoIce", "formasDePago")) | IGNORED_VENTAS_KEYS
	_check_keys(row, known, "ventas")
	_require(row, VENTAS_REQUIRED, "ventas")
	return (
		"<detalleVentas>"
		f"<tpIdCliente>{escape_xml(str(row['tpIdCliente']))}</tpIdCliente>"
		f"<idCliente>{escape_xml(str(row['idCliente']))}</idCliente>"
		f"{_optional_scalar(row, 'denoCli')}"
		f"<tipoComprobante>{escape_xml(str(row['tipoComprobante']))}</tipoComprobante>"
		f"<tipoEmision>{escape_xml(str(row['tipoEmision']))}</tipoEmision>"
		f"<numeroComprobantes>{int(row['numeroComprobantes'])}</numeroComprobantes>"
		f"<baseNoGraIva>{_money(row['baseNoGraIva'])}</baseNoGraIva>"
		f"<baseImponible>{_money(row['baseImponible'])}</baseImponible>"
		f"<baseImpGrav>{_money(row['baseImpGrav'])}</baseImpGrav>"
		f"<montoIva>{_money(row['montoIva'])}</montoIva>"
		f"{_optional_scalar(row, 'montoIce', money=True)}"
		f"<valorRetIva>{_money(row['valorRetIva'])}</valorRetIva>"
		f"<valorRetRenta>{_money(row['valorRetRenta'])}</valorRetRenta>"
		f"{_formas_de_pago_block(row.get('formasDePago'))}"
		"</detalleVentas>"
	)


def _render_exportacion(row: dict) -> str:
	"""Render one ``detalleExportaciones`` in ats.xsd element order."""
	known = frozenset(EXPORTACIONES_REQUIRED)
	_check_keys(row, known, "exportaciones")
	_require(row, EXPORTACIONES_REQUIRED, "exportaciones")
	return (
		"<detalleExportaciones>"
		f"<exportacionDe>{escape_xml(str(row['exportacionDe']))}</exportacionDe>"
		f"<tipoComprobante>{escape_xml(str(row['tipoComprobante']))}</tipoComprobante>"
		f"<fechaEmbarque>{escape_xml(str(row['fechaEmbarque']))}</fechaEmbarque>"
		f"<valorFOB>{_money(row['valorFOB'])}</valorFOB>"
		f"<valorFOBComprobante>{_money(row['valorFOBComprobante'])}</valorFOBComprobante>"
		f"<establecimiento>{escape_xml(str(row['establecimiento']))}</establecimiento>"
		f"<puntoEmision>{escape_xml(str(row['puntoEmision']))}</puntoEmision>"
		f"<secuencial>{escape_xml(str(row['secuencial']))}</secuencial>"
		f"<autorizacion>{escape_xml(str(row['autorizacion']))}</autorizacion>"
		f"<fechaEmision>{escape_xml(str(row['fechaEmision']))}</fechaEmision>"
		"</detalleExportaciones>"
	)


def _render_anulado(row: dict) -> str:
	"""Render one ``detalleAnulados`` in ats.xsd element order."""
	known = frozenset(ANULADOS_FIELDS)
	_check_keys(row, known, "anulados")
	_require(row, ANULADOS_FIELDS, "anulados")
	return (
		"<detalleAnulados>"
		f"<tipoComprobante>{escape_xml(str(row['tipoComprobante']))}</tipoComprobante>"
		f"<establecimiento>{escape_xml(str(row['establecimiento']))}</establecimiento>"
		f"<puntoEmision>{escape_xml(str(row['puntoEmision']))}</puntoEmision>"
		f"<secuencialInicio>{escape_xml(str(row['secuencialInicio']))}</secuencialInicio>"
		f"<secuencialFin>{escape_xml(str(row['secuencialFin']))}</secuencialFin>"
		f"<autorizacion>{escape_xml(str(row['autorizacion']))}</autorizacion>"
		"</detalleAnulados>"
	)


def _section(name: str, rows: list, render) -> str:
	"""Render one ATS section; empty sections produce no element."""
	if not rows:
		return ""
	if not isinstance(rows, (list, tuple)):
		raise SriXmlError(_("ATS section '{}' must be a list of rows.").format(name))
	return f"<{name}>{''.join(render(row) for row in rows)}</{name}>"


def build_ats_xml(collected: dict, period: str) -> str:
	"""Render collected ATS sections into the validated ``AT{mmaaaa}.xml`` string.

	:param collected: ``ats_collector.collect_month`` output (``compras``,
		``ventas``, ``exportaciones``, ``anulados``) plus an ``informante``
		(or ``header``) dict with ``IdInformante`` and ``razonSocial``.
	:param period: fiscal month (``MMYYYY``, ``MM/YYYY``, ``MM-YYYY``,
		``YYYY-MM`` or ``YYYY/MM``).
	:raises SriXmlError: for anything the schema would refuse, with the
		schema error log attached.
	"""
	if not isinstance(collected, dict):
		raise SriXmlError(_("ATS collected payload must be a dict of sections."))
	month, year = _parse_period(period)
	informante = _informante(collected)
	known_sections = {"compras", "ventas", "exportaciones", "anulados", "informante", "header"}
	for key in collected:
		if key not in known_sections:
			raise SriXmlError(_("ATS payload carries unknown section '{}'.").format(key))
	optional_header = ""
	if informante.get("regimenMicroempresa") not in (None, ""):
		optional_header += (
			f"<regimenMicroempresa>{escape_xml(str(informante['regimenMicroempresa']))}</regimenMicroempresa>"
		)
	if informante.get("numEstabRuc") not in (None, ""):
		optional_header += f"<numEstabRuc>{escape_xml(str(informante['numEstabRuc']))}</numEstabRuc>"
	if informante.get("totalVentas") not in (None, ""):
		optional_header += f"<totalVentas>{_money(informante['totalVentas'])}</totalVentas>"
	compras_xml = _section("compras", collected.get("compras") or [], _render_compra)
	ventas_xml = _section("ventas", collected.get("ventas") or [], _render_venta)
	exportaciones_xml = _section("exportaciones", collected.get("exportaciones") or [], _render_exportacion)
	anulados_xml = _section("anulados", collected.get("anulados") or [], _render_anulado)
	xml = (
		'<?xml version="1.0" encoding="UTF-8"?>\n'
		"<iva>"
		f"<TipoIDInformante>{informante['TipoIDInformante']}</TipoIDInformante>"
		f"<IdInformante>{escape_xml(str(informante['IdInformante']))}</IdInformante>"
		f"<razonSocial>{escape_xml(str(informante['razonSocial']))}</razonSocial>"
		f"<Anio>{year}</Anio>"
		f"<Mes>{month}</Mes>"
		f"{optional_header}"
		f"<codigoOperativo>{informante['codigoOperativo']}</codigoOperativo>"
		f"{compras_xml}"
		f"{ventas_xml}"
		f"{exportaciones_xml}"
		f"{anulados_xml}"
		"</iva>"
	)
	validate_against_xsd(xml, "ats")
	return xml


def ats_filename(period: str) -> str:
	"""Return the SRI month filename ``AT{mmaaaa}.xml`` for a fiscal period."""
	month, year = _parse_period(period)
	return f"AT{month}{year}.xml"


def build_ats_zip(xml_string: str, period: str) -> bytes:
	"""Pack one built ATS XML into the single-file month zip for the portal."""
	if not xml_string:
		raise SriXmlError(_("ATS zip needs the built XML string."))
	validate_against_xsd(xml_string, "ats")
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(ats_filename(period), xml_string.encode("utf-8"))
	return buffer.getvalue()

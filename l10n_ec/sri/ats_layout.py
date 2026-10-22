"""ATS presentation rows: per-document detail plus section subtotals.

Mirrors the SRI ATS grids (compras / ventas / exportaciones / anulados):
one row per collected document with its SRI number, counterparty, taxable
base and tax, then a subtotal row per section. Pure Python, no frappe:
Ring 1 tests inject plain ``collect_month`` output dicts.
"""

try:
	from frappe import _
except ImportError:  # pragma: ignore[no-redef]  # pragma: no cover

	def _(message: str) -> str:  # type: ignore[no-redef]
		return message


#: Section titles in SRI ATS order.
SECTION_TITLES = {
	"compras": "COMPRAS (detalleCompras)",
	"ventas": "VENTAS (detalleVentas)",
	"exportaciones": "EXPORTACIONES (detalleExportaciones)",
	"anulados": "ANULADOS",
}


def _sri_number(row: dict) -> str:
	parts = [row.get("establecimiento") or "", row.get("puntoEmision") or "", row.get("secuencial") or ""]
	if any(parts):
		return "-".join(parts)
	return ""


def build_ats_rows(collected: dict) -> list:
	"""Build presentation rows from ``collect_month`` sections.

	Row dicts carry ``kind`` (``section``/``detail``/``subtotal``),
	``seccion``, ``comprobante``, ``tercero``, ``base``, ``iva``,
	``detalle``. Unknown sections fail loud instead of rendering guessed
	columns.
	"""
	collected = collected or {}
	unknown = set(collected) - set(SECTION_TITLES)
	if unknown:
		raise ValueError(_("ATS sections '{}' have no presentation layout.").format(sorted(unknown)))
	rows: list = []
	for section in ("compras", "ventas", "exportaciones", "anulados"):
		docs = collected.get(section) or []
		rows.append(
			{
				"kind": "section",
				"seccion": section,
				"comprobante": "",
				"tercero": SECTION_TITLES[section],
				"base": None,
				"iva": None,
				"detalle": f"{len(docs)} documento(s)",
			}
		)
		base_total = 0.0
		iva_total = 0.0
		for doc in docs:
			comprobante, tercero, base, iva, detalle = _detail_row(section, doc)
			base_total = round(base_total + (base or 0.0), 2)
			iva_total = round(iva_total + (iva or 0.0), 2)
			rows.append(
				{
					"kind": "detail",
					"seccion": section,
					"comprobante": comprobante,
					"tercero": tercero,
					"base": base,
					"iva": iva,
					"detalle": detalle,
				}
			)
		rows.append(
			{
				"kind": "subtotal",
				"seccion": section,
				"comprobante": "",
				"tercero": f"SUBTOTAL {SECTION_TITLES[section]}",
				"base": base_total,
				"iva": iva_total,
				"detalle": "",
			}
		)
	return rows


def _detail_row(section: str, doc: dict) -> tuple:
	"""(comprobante, tercero, base, iva, detalle) for one collected doc."""
	if section == "compras":
		number = "-".join(
			[
				doc.get("establecimiento") or "",
				doc.get("puntoEmision") or "",
				doc.get("secuencial") or "",
			]
		)
		return (
			f"{doc.get('tipoComprobante', '')} {number}".strip(),
			f"{doc.get('denoProv', '')} ({doc.get('tpIdProv', '')}{doc.get('idProv', '')})".strip(),
			round(float(doc.get("baseImpGrav") or 0.0), 2),
			round(float(doc.get("montoIva") or 0.0), 2),
			f"sustento {doc.get('codSustento', '')} · aut. {doc.get('autorizacion', '')}".strip(),
		)
	if section == "ventas":
		return (
			f"{doc.get('tipoComprobante', '')}".strip(),
			f"{doc.get('denoCli', '')} ({doc.get('tpIdCliente', '')}{doc.get('idCliente', '')})".strip(),
			round(float(doc.get("baseImpGrav") or 0.0), 2),
			round(float(doc.get("montoIva") or 0.0), 2),
			f"ret. IVA {doc.get('valorRetIva') or 0.0} · ret. renta {doc.get('valorRetRenta') or 0.0}",
		)
	if section == "exportaciones":
		return (
			f"{doc.get('tipoComprobante', '')} {_sri_number(doc)}".strip(),
			f"{doc.get('exportacionDe', '')}".strip(),
			round(float(doc.get("valorFOB") or 0.0), 2),
			None,
			f"embarque {doc.get('fechaEmbarque', '')}".strip(),
		)
	number = _sri_number(doc)
	return (
		f"{doc.get('tipoComprobante', '')} {number}".strip(),
		"",
		None,
		None,
		f"aut. {doc.get('autorizacion', '')}".strip(),
	)

"""SRI Sustento Tributario catalog (Tabla 5 ATS) — pure Python, no frappe."""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


# Tabla 5 SRI — 01..15 (00 historical, not offered). Descriptions from Ficha ATS.
SUSTENTOS = {
	"01": "Servicios o bienes distintos de inventarios y activos fijos, gravados, con derecho a crédito tributario",
	"02": "Servicios o bienes gravados distintos de inventarios y activos fijos sin crédito tributario; IVA a costo/gasto",
	"03": "Activos fijos gravados con derecho a crédito tributario",
	"04": "Activos fijos sin crédito tributario; IVA a costo/gasto",
	"05": "Gastos de viaje, hospedaje y alimentación a nombre de funcionarios",
	"06": "Inventario gravado con derecho a crédito tributario",
	"07": "Inventario sin crédito tributario; IVA a costo/gasto",
	"08": "Bienes/servicios gravados pagados para solicitar reembolso (intermediario)",
	"09": "Gastos médicos / medicina prepagada vía reembolso",
	"10": "Dividendos y utilidades distribuidas",
	"11": "Pagos por convenio de débito/recaudación instituciones financieras",
	"12": "Editores / retención presuntiva periódicos; combustibles; pronósticos deportivos",
	"13": "Valores reconocidos por el sector público a sujetos pasivos",
	"14": "Valores facturados por socios a operadoras de transporte",
	"15": "Pagos por consumos propios y de terceros de servicios digitales",
}

# Permissive guard — SRI does restrict sustentos by tipoComprobante/tpIdProv,
# but the official cross-table is not yet vendored. For now validate existence
# and let the selector be guided by UX defaults; tighten when catalog 06-08-2026 is parsed.
ALLOWED_SUSTENTOS = set(SUSTENTOS)


def validate_sustento(sustento_code: str, doc_code: str = "01", tp_id_prov: str = "04") -> None:
	"""Fail loud if sustento is outside Tabla 5 or not offered."""
	from l10n_ec.sri.codes import sri_code

	code = sri_code(sustento_code)
	if code not in ALLOWED_SUSTENTOS:
		raise ValueError(_("SRI sustento code '{}' is not in Tabla 5 (01-15).").format(code))
	# Future: check (doc_code, tp_id_prov, code) against vendored cross-table.

"""SRI reimbursement detail helpers (pure Python, no frappe).

T1 scope: independent reimbursement lines, sustento x tipoComprobante
cross-table (Tabla 5), and `totbasesImpReemb` resolution (calculated by
default, manual override only with explicit opt-in).
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.codes import sri_code
from l10n_ec.sri.sustentos import ALLOWED_SUSTENTOS

#: Allowed tipoComprobante per sustento (Ficha ATS Tabla 5 + SRI catalog).
#: Doc codes are bare SRI codes ("01", "03", "41", ...).
SUSTENTO_BY_DOC: dict[str, frozenset] = {
	"01": frozenset({"01", "03", "04", "05", "11", "12", "21", "41", "43", "47", "48", "294", "344"}),
	"02": frozenset(
		{
			"01",
			"02",
			"03",
			"04",
			"05",
			"09",
			"11",
			"12",
			"15",
			"19",
			"20",
			"21",
			"41",
			"43",
			"47",
			"48",
			"294",
			"344",
			"364",
		}
	),
	"03": frozenset({"01", "03", "04", "05", "41", "47", "48", "294", "344"}),
	"04": frozenset({"01", "02", "03", "04", "05", "15", "41", "47", "48", "294", "344"}),
	"05": frozenset({"01", "02", "03", "04", "05", "11", "15", "41", "294", "344"}),
	"06": frozenset({"01", "03", "04", "05", "41", "43", "47", "48", "294", "344"}),
	"07": frozenset({"01", "02", "03", "04", "05", "15", "41", "43", "47", "48", "294", "344", "364"}),
	"08": frozenset({"01", "02", "03", "04", "05", "21", "294", "344"}),
	"09": frozenset({"01", "04", "05", "45"}),
	"10": frozenset({"19"}),
	"11": frozenset({"12"}),
	"12": frozenset({"42"}),
	"13": frozenset({"19"}),
	"14": frozenset({"01", "02", "03", "04", "05"}),
	"15": frozenset({"01", "02", "03", "04", "05", "12", "15"}),
}


def validate_sustento_for_doc(sustento_code: str, doc_code: str, tp_id_prov: str = "04") -> None:
	"""Fail loud when a sustento cannot travel on a tipoComprobante.

	`tp_id_prov` is accepted for the future cross-table (tipo proveedor x
	sustento) and intentionally unchecked in T1.
	"""
	_tp_unused = tp_id_prov
	sustento = sri_code(sustento_code)
	doc = sri_code(doc_code)
	if sustento not in ALLOWED_SUSTENTOS:
		raise ValueError(_("SRI sustento code '{}' is not in Tabla 5 (01-15).").format(sustento))
	if not doc:
		raise ValueError(_("SRI document code is required for sustento '{}'.").format(sustento))
	allowed = SUSTENTO_BY_DOC.get(sustento)
	if allowed is not None and doc not in allowed:
		raise ValueError(_("SRI sustento '{}' cannot be used with document '{}'.").format(sustento, doc))


def calc_reimbursement_total(lines: list | tuple | None) -> float:
	"""Sum `base_amount` lines into `totbasesImpReemb` (rounded 2)."""
	total = 0.0
	for line in lines or []:
		if isinstance(line, dict):
			base = line.get("base_amount", 0.0)
		else:
			base = getattr(line, "base_amount", 0.0)
		total = round(total + float(base or 0.0), 2)
	return total


def resolve_reimbursement_total(
	lines: list | tuple | None,
	override_value: float | None,
	allow_override: bool = False,
) -> float:
	"""Return the ATS `totbasesImpReemb` for reimbursement lines.

	Calculated by default; a nonzero manual value wins only with explicit
	opt-in. A zero override is the untouched Currency default and reads as
	no override. A nonzero forced value without opt-in fails loud instead
	of silently diverging.
	"""
	calculated = calc_reimbursement_total(lines)
	if override_value in (None, "", 0, 0.0):
		return calculated
	forced = round(float(override_value), 2)
	if not allow_override:
		raise ValueError(_("Reimbursement total override needs explicit opt-in (got '{}').").format(forced))
	if forced < 0:
		raise ValueError(_("Reimbursement total override '{}' cannot be negative.").format(forced))
	return forced

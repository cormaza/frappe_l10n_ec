"""Official SRI withholding concepto table (XML `codigoRetencion` values).

Source: SRI Resolution NAC-DGERCGC26-00000009, vigencia 2026-03-01.
IR conceptos follow SRI Tabla 20; IVA conceptos follow SRI Tabla 23.
Descriptions are the official SRI Spanish wording (protocol exception);
everything else in this module is English. Pure Python, no frappe.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.voucher_states import SriVoucherError

WITHHOLDING_CONCEPTS_VALID_FROM = "2026-03-01"

# {codigoRetencion: (impuesto, description, rate, valid_from)}.
# impuesto '1' is IR (renta), impuesto '2' is IVA. Code suffixes
# ('303A', '3440', ...) stay verbatim as the SRI spells them.
CONCEPTS = {
	# IR (impuesto '1').
	"303": ("1", "Honorarios profesionales", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"303A": ("1", "Servicios profesionales sociedades", 5.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"304": ("1", "Intelecto sin título", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"304A": ("1", "Comisiones intelecto", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"304C": ("1", "Deportistas", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"304D": ("1", "Artistas", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"307": ("1", "Mano de obra", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"308": ("1", "Imagen y renombre", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"309": ("1", "Publicidad", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"310": ("1", "Transporte", 1.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"311": ("1", "Liquidación compra", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"312": ("1", "Bienes muebles", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"319": ("1", "Leasing", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"320": ("1", "Arriendo inmuebles", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"322": ("1", "Seguros", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"323": ("1", "Rendimientos financieros", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"332": ("1", "No sujeto", 0.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"343": ("1", "Otras 1%", 1.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"343A": ("1", "Energía eléctrica", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"343B": ("1", "Construcción", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"343C": ("1", "Botellas PET", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"344A": ("1", "Tarjetas", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"344B": ("1", "Minerales", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"3440": ("1", "Otras 3%", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"3482": ("1", "Comisiones sociedades", 5.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	# IVA (impuesto '2').
	"1": ("2", "Bienes", 30.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"2": ("2", "Servicios", 70.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"3": ("2", "Honorarios", 100.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"7": ("2", "Retención cero", 0.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"8": ("2", "No procede", 0.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"9": ("2", "Especial 10%", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"10": ("2", "Especial 20%", 20.0, WITHHOLDING_CONCEPTS_VALID_FROM),
	"11": ("2", "Especial 50%", 50.0, WITHHOLDING_CONCEPTS_VALID_FROM),
}


def resolve_concepto(code: str) -> tuple:
	"""Return `(impuesto, rate, description)` for an SRI `codigoRetencion`.

	Raises `SriVoucherError` for unknown codes instead of guessing.
	"""
	try:
		impuesto, description, rate, _valid_from = CONCEPTS[code]
	except KeyError:
		raise SriVoucherError(_("Unknown SRI withholding concepto code '{}'.").format(code)) from None
	return (impuesto, rate, description)


def validate_concepto_map(code_map: dict) -> None:
	"""Fail loud on pending (`None`) or unknown concepto codes in a per-call map.

	`code_map` resolves category names to `(impuesto, codigoRetencion)`.
	Also rejects pairs whose impuesto disagrees with the official table.
	"""
	for category, pair in code_map.items():
		impuesto, codigo = pair
		if codigo is None:
			raise SriVoucherError(_("Withholding category '{}' has no SRI code mapping.").format(category))
		expected, _rate, _description = resolve_concepto(codigo)
		if impuesto != expected:
			raise SriVoucherError(
				_("Withholding category '{}' maps impuesto '{}' but concepto '{}' is impuesto '{}'.").format(
					category, impuesto, codigo, expected
				)
			)

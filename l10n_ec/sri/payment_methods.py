"""Official SRI payment method table (XML `formaPago` values).

Source: SRI ficha tecnica Tabla 24 / ATS catalog (corroborated by deley.ec).
Descriptions are the official SRI Spanish wording (protocol exception);
everything else in this module is English. Pure Python, no frappe.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


from l10n_ec.sri.voucher_states import SriVoucherError

# {formaPago code: official Spanish description}.
TABLA_24 = {
	"01": "Sin utilización del sistema financiero",
	"15": "Compensación de deudas",
	"16": "Tarjeta de débito",
	"17": "Dinero electrónico",
	"18": "Tarjeta prepago",
	"19": "Tarjeta de crédito",
	"20": "Otros con utilización del sistema financiero",
	"21": "Endoso de títulos",
}


def resolve_payment_method(code: str) -> str:
	"""Return the official description for an SRI Tabla 24 `formaPago` code.

	Raises `SriVoucherError` for unknown codes instead of guessing.
	"""
	try:
		return TABLA_24[code]
	except KeyError:
		raise SriVoucherError(_("Unknown SRI payment method code '{}'.").format(code)) from None

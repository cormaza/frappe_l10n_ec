"""Gettext extraction markers for custom field labels and options.

`create_custom_fields` stores these strings in English in the database and
Frappe translates them at display time, so the definitions in
`custom_fields.py` intentionally stay raw. The bench pot scanner only
collects `_()` call literals, which is why every string below is repeated
here: this module exists for extraction and is never imported at runtime.
"""


def _(message: str) -> str:
	return message


CUSTOM_FIELD_STRINGS = [
	_("SRI Environment"),
	_("Test"),
	_("Production"),
	_("SRI Signature"),
	_("Special Taxpayer Resolution"),
	_("Withholding Agent Resolution"),
	_("RIMPE Regime"),
	_("Popular Business"),
	_("Entrepreneur"),
	_("Accounting Required"),
	_("SRI Identification Type"),
	_("Related Party"),
]

WITHHOLDING_CONCEPTO_STRINGS = [
	# Official SRI withholding concepto descriptions (Res. NAC-DGERCGC26-00000009,
	# vigencia 2026-03-01). Spanish is the source wording here (protocol
	# exception); entries exist so the translation catalog carries the official
	# vocabulary. CONCEPTS codes stay verbatim and are never translated.
	_("Honorarios profesionales"),
	_("Servicios profesionales sociedades"),
	_("Intelecto sin título"),
	_("Comisiones intelecto"),
	_("Deportistas"),
	_("Artistas"),
	_("Mano de obra"),
	_("Imagen y renombre"),
	_("Publicidad"),
	_("Transporte"),
	_("Liquidación compra"),
	_("Bienes muebles"),
	_("Leasing"),
	_("Arriendo inmuebles"),
	_("Seguros"),
	_("Rendimientos financieros"),
	_("No sujeto"),
	_("Otras 1%"),
	_("Energía eléctrica"),
	_("Construcción"),
	_("Botellas PET"),
	_("Tarjetas"),
	_("Minerales"),
	_("Otras 3%"),
	_("Comisiones sociedades"),
	_("Bienes"),
	_("Servicios"),
	_("Honorarios"),
	_("Retención cero"),
	_("No procede"),
	_("Especial 10%"),
	_("Especial 20%"),
	_("Especial 50%"),
]

RIDE_PRINT_FORMAT_STRINGS = [
	_("RIDE — Delivery Note"),
	_("RIDE — Withholding"),
	_("Issuer:"),
	_("Access Key:"),
	_("SRI Authorization:"),
	_("DOCUMENT IN PROCESS"),
	_("pending SRI authorization."),
	_("Recipient"),
	_("Name:"),
	_("Address:"),
	_("Origin Address:"),
	_("Carrier:"),
	_("Transport Dates:"),
	_("Plate:"),
	_("Transfer Reason:"),
	_("Support Document:"),
	_("Code"),
	_("Description"),
	_("Quantity"),
	_("Subject:"),
	_("Fiscal Period:"),
	_("Sustento:"),
	_("Totals:"),
	_("Tax"),
	_("Withholding Code"),
	_("Base"),
	_("Rate %"),
	_("Value"),
	_("Total Withheld:"),
]

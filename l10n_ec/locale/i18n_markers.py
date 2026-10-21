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
	_("SRI Payment Code"),
	_("SRI IR Concepto"),
	_(
		"SRI IR withholding concepto withheld by the customer (e.g. 303, 312), validated against the concepto table; feeds the received-withholding settlement entry; leave empty when no IR withholding applies."
	),
	_("SRI IVA Concepto"),
	_("Received Retencion Number"),
	_(
		"Number of the Comprobante de Retencion issued by the customer (e.g. 001-001-000000001); feeds ATS and Form 103 as tax credit."
	),
	_("Received Retencion Authorization"),
	_("SRI authorization number of the customer-issued withholding voucher."),
	_("Received Retencion Date"),
	_("Issue date of the customer-issued withholding voucher."),
	_("Received Retencion Access Key"),
	_("49-digit access key of the customer-issued withholding voucher."),
	_(
		"SRI Tabla 23 IVA withholding concepto driving the automatic deduction row and the voucher (1 bienes 30%, 2 servicios 70%, 3 honorarios 100%); leave empty when no IVA withholding applies."
	),
]

PAYMENT_METHOD_STRINGS = [
	# Official SRI Tabla 24 descriptions. Spanish is the source wording here
	# (protocol exception); entries exist so the translation catalog carries
	# the official vocabulary. TABLA_24 codes stay verbatim and are never
	# translated.
	_("Sin utilización del sistema financiero"),
	_("Compensación de deudas"),
	_("Tarjeta de débito"),
	_("Dinero electrónico"),
	_("Tarjeta prepago"),
	_("Tarjeta de crédito"),
	_("Otros con utilización del sistema financiero"),
	_("Endoso de títulos"),
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
	_("Ingresos del trabajo en relación de dependencia"),
	_(
		"Pagos a notarios y registradores de la propiedad y mercantil por sus actividades ejercidas como tales"
	),
	_("Honorarios y demás pagos por servicios de docencia"),
	_("COMPRAS AL PRODUCTOR: de bienes de origen bioacuático, forestal y los descritos  el art.27.1 de LRTI"),
	_("Impuesto a la Renta único para la actividad de producción y cultivo de palma aceitera"),
	_(
		"COMPRAS AL COMERCIALIZADOR: de bienes de origen bioacuático, forestal y los descritos  el art.27.1 de LRTI"
	),
	_(
		"Regalías por concepto de franquicias de acuerdo al Código INGENIOS (COESCCI) - pago a personas naturales"
	),
	_(
		"Cánones, derechos de autor,  marcas, patentes y similares de acuerdo  al Código INGENIOS (COESCCI) – pago a personas naturales"  # noqa: RUF001 (sourced OCA spelling)
	),
	_("Regalías por concepto de franquicias de acuerdo al Código INGENIOS (COESCCI) - pago a sociades"),
	_("Cánones, derechos de autor,  marcas, patentes y similares de acuerdo  al Código INGENIOS (COESCCI)"),
	_("Rendimientos financieros depósitos Cta. Corriente"),
	_("Rendimientos financieros  depósitos Cta. Ahorros Sociedades"),
	_("Por RF:  depósitos Cta. Ahorros Persona Natural"),
	_("Por rendimientos financieros:  depósitos en cuentas exentas"),
	_("Por rendimientos financieros: compra, cancelación o redención de mini bem´s y bem´s"),  # noqa: RUF001 (sourced OCA spelling)
	_("Rendimientos financieros depósito a plazo fijo  gravados"),
	_("Rendimientos financieros depósito a plazo fijo exentos"),
	_("Rendimientos financieros operaciones de reporto - repos"),
	_("Inversiones (captaciones) rendimientos distintos de aquellos pagados a IFIs"),
	_("Rendimientos financieros  obligaciones"),
	_("Rendimientos financieros  bonos convertible en acciones"),
	_("Por RF: bonos de organismos y gobiernos extranjeros"),
	_(
		"Por RF: Intereses en operaciones de crédito entre instituciones del sistema financiero y entidades economía popular y solidaria."
	),
	_(
		"Por RF: Por inversiones entre instituciones del sistema financiero y entidades economía popular y solidaria."
	),
	_("Rendimientos financieros : Inversiones en títulos valores en renta fija gravados"),
	_("Rendimientos financieros  Inversiones en títulos valores en renta fija exentos"),
	_(
		"Intereses y demás rendimientos financieros pagados a bancos y otras entidades sometidas al control de la Superintendencia de Bancos y de la Economía Popular y Solidaria"
	),
	_("Intereses pagados por entidades del sector público a favor de sujetos pasivos"),
	_("Otros intereses y rendimientos financieros gravados"),
	_("Otros intereses y rendimientos financieros exentos"),
	_(
		"Pagos y créditos en cuenta efectuados por el BCE y los depósitos centralizados de valores, en calidad de intermediarios, a instituciones del sistema financiero por cuenta de otras personas naturales y sociedades"
	),
	_("Rendimientos financieros originados en la deuda pública ecuatoriana"),
	_(
		"Rendimientos financieros originados en títulos valores de obligaciones de 360 días o más para el financiamiento de proyectos públicos en asociación público-privada"
	),
	_(
		"Intereses en operaciones de crédito entre instituciones del sistema financiero y entidades economía popular y solidaria."
	),
	_("Inversiones entre instituciones del sistema financiero y entidades economía popular y solidaria"),
	_(
		"Pagos y créditos en cuenta efectuados por el BCE y los depósitos centralizados de valores, en calidad de intermediarios, a instituciones del sistema financiero por cuenta de otras instituciones del sistema financiero"
	),
	_("Anticipo dividendos"),
	_("Dividendos exentos (por no llegar a franja exenta o beneficio de otras leyes)"),
	_("Préstamos accionistas, beneficiarios o partícipes residentes o establecidos en el Ecuador"),
	_(
		"Dividendos distribuidos que correspondan al impuesto a la renta único establecido en el art. 27 de la LRTI"
	),
	_("Dividendos distribuidos a personas naturales residentes"),
	_("Dividendos distribuidos a sociedades residentes"),
	_("Dividendos distribuidos a fideicomisos residentes"),
	_(
		"Dividendos gravados distribuidos en acciones (reinversión de utilidades sin derecho a reducción tarifa IR)"
	),
	_("Dividendos en acciones (capitalización de utilidades)"),
	_("Por la enajenación ocasional de acciones o participaciones y títulos valores"),
	_("Compra de bienes inmuebles"),
	_("Transporte público de pasajeros"),
	_(
		"Pagos en el país por transporte de pasajeros o transporte internacional de carga, a compañías nacionales o extranjeras de aviación o marítimas"
	),
	_("Valores entregados por las cooperativas de transporte a sus socios"),
	_("Compraventa de divisas distintas al dólar de los Estados Unidos de América"),
	_("Pagos con tarjeta de crédito"),
	_("Pago al exterior tarjeta de crédito reportada por la Emisora de tarjeta de crédito, solo recap"),
	_("Pago a través de convenio de debito (Clientes IFI`s)"),
	_(
		"Ganancia en la enajenación de derechos representativos de capital u otros derechos que permitan la exploración, explotación, concesión o similares de sociedades, que se coticen en bolsa de valores del Ecuador"
	),
	_(
		"Contraprestación producida por la enajenación de derechos representativos de capital u otros derechos que permitan la exploración, explotación, concesión o similares de sociedades, no cotizados en bolsa de valores del Ecuador"
	),
	_("Loterías, rifas, pronósticos deportivos, apuestas y similares"),
	_("Venta de combustibles a comercializadoras"),
	_("Venta de combustibles a distribuidores"),
	_("Producción y venta local de banano producido o no por el mismo sujeto pasivo"),
	_("Liquidación impuesto único a la venta local de banano de producción propia"),
	_("Impuesto único a la exportación de banano"),
	_("Por energía eléctrica"),
	_(
		"Por actividades de construcción de obra material inmueble, urbanización, lotización o actividades similares"
	),
	_("Impuesto único a la exportación de banano de producción propia - componente 2"),
	_("Impuesto único a la exportación de banano producido por terceros"),
	_(
		"Impuesto único a la exportación de banano producido por terceros de Asociaciones de micro y pequeños productores hasta 1000 cajas por semana por cada socio."
	),
	_(
		"Impuesto único a la exportación de banano producido por terceros de Asociaciones de micro, pequeños y medianos productores"
	),
	_("Otras retenciones aplicables el 2%"),
	_("Otras retenciones aplicables el 8%"),
	_("Dividendos exentos a sociedades, nacionales o extranjeras, domiciliadas en el Ecuador"),
	_(
		"Dividendos exentos distribuidos en acciones (reinversión de utilidades con derecho a reducción tarifa IR)"
	),
	_("Otras retenciones aplicables a otros porcentajes"),
	_("Otras ganancias de capital distintas de enajenación de derechos representativos de capital"),
	_("Donaciones en dinero -Impuesto a las donaciones"),
	_(
		"Retención a cargo del propio sujeto pasivo por la producción y/o comercialización de minerales y otros bienes"
	),
	_("Retención a cargo del propio sujeto pasivo por la comercialización de productos forestales"),
	_("Donaciones en dinero -Impuesto a la donaciones"),
	_("Dividendos anticipados préstamos accionistas, beneficiarios o partícipes"),
	_(
		"Impuesto único a ingresos provenientes de actividades agropecuarias en etapa de producción / comercialización local o exportación"
	),
	_("Impuesto a la renta único sobre los ingresos percibidos por los operadores de pronósticos deportivos"),
	_("Autorretenciones Sociedades Grandes Contribuyentes"),
	_("Otras autorretenciones (inciso 1 y 2 Art.92.1 RLRTI)"),
	_("Régimen Microempresarial"),
	_("Pago a no residentes - Rentas Inmobiliarias"),
	_("Pago a no residentes - Beneficios/Servicios  Empresariales"),
	_("Pago a no residentes - Servicios técnicos, administrativos o de consultoría y regalías"),
	_("Pago al exterior - Servicios Empresariales"),
	_("Pago a no residentes- Navegación Marítima y/o aérea"),
	_(
		"Pago a no residentes- Dividendos distribuidos a personas naturales (domiciliados o no en paraíso fiscal) o a sociedades sin beneficiario efectivo persona natural residente en Ecuador"
	),
	_("Dividendos a sociedades con beneficiario efectivo persona natural residente en el Ecuador"),
	_("Dividendos a no residentes incumpliendo el deber de informar la composición societaria"),
	_(
		"Dividendos a residentes o establecidos en paraísos fiscales o regímenes de menor imposición (con beneficiario Persona Natural residente en Ecuador)"
	),
	_(
		"Dividendos a fideicomisos o establecidos en paraísos fiscales o regímenes de menor imposición (con beneficiario Persona Natural residente en Ecuador)"
	),
	_(
		"Pago a no residentes - Anticipo dividendos (no domiciliada en paraísos fiscales o regímenes de menor imposición)"
	),
	_(
		"Pago a no residentes - Anticipo dividendos (domiciliadas en paraísos fiscales o regímenes de menor imposición)"
	),
	_(
		"Pago a no residentes - Préstamos accionistas, beneficiarios o partícipes (no domiciliadas en paraísos fiscales o regímenes de menor imposición)"
	),
	_(
		"Pago a no residentes - Préstamos accionistas, beneficiarios o partícipes (domiciliadas en paraísos fiscales o regímenes de menor imposición)"
	),
	_(
		"Pago a no residentes - Préstamos no comerciales a partes relacionadas  (no domiciliadas en paraísos fiscales o regímenes de menor imposición)"
	),
	_(
		"Pago a no residentes - Préstamos no comerciales a partes relacionadas  (domiciliadas en paraísos fiscales o regímenes de menor imposición)"
	),
	_("Pago a no residentes - Rendimientos financieros"),
	_("Pago a no residentes – Intereses de créditos de Instituciones Financieras del exterior"),  # noqa: RUF001 (sourced OCA spelling)
	_("Pago a no residentes – Intereses de créditos de gobierno a gobierno"),  # noqa: RUF001 (sourced OCA spelling)
	_("Pago a no residentes – Intereses de créditos de organismos multilaterales"),  # noqa: RUF001 (sourced OCA spelling)
	_("Pago a no residentes - Intereses por financiamiento de proveedores externos"),
	_("Pago a no residentes - Intereses de otros créditos externos"),
	_("Pago a no residentes - Otros Intereses y Rendimientos Financieros"),
	_("Pago al exterior - Intereses por Financiamiento de proveedores externos"),
	_("Pago al exterior - Intereses de créditos externos"),
	_("Pago al exterior - Créditos de IFI's organismos y gobierno a gobierno"),
	_("Pago a no residentes- Cánones, derechos de autor,  marcas, patentes y similares"),
	_("Pago a no residentes - Regalías por concepto de franquicias"),
	_(
		"Pago a no residentes - Otras ganancias de capital distintas de enajenación de derechos representativos de capital"
	),
	_("Pago a no residentes - Servicios profesionales independientes"),
	_("Pago a no residentes - Servicios profesionales dependientes"),
	_("Pago a no residentes- Artistas"),
	_("Pago a no residentes - Deportistas"),
	_("Pago a no residentes - Participación de consejeros"),
	_(
		"Pago a no residentes- Artistas y relacionados a  organización, producción y espectáculos artísticos y culturales en Ecuador"
	),
	_("Pago a no residentes - Pensiones"),
	_("Pago a no residentes- Reembolso de Gastos"),
	_("Pago a no residentes- Funciones Públicas"),
	_("Pago a no residentes - Estudiantes"),
	_("Pago al exterior - Otros conceptos de ingresos gravados"),
	_("Pago a no residentes - Pago a proveedores de servicios hoteleros y turísticos en el exterior"),
	_("Pago a no residentes - Arrendamientos mercantil internacional"),
	_("Pago al exterior - Seguros, cesiones y reaseguros"),
	_("Pago a no residentes - Comisiones por exportaciones y por promoción de turismo receptivo"),
	_(
		"Pago a no residentes - Por las empresas de transporte marítimo o aéreo y por empresas pesqueras de alta mar, por su actividad."
	),
	_("Pago a no residentes - Por las agencias internacionales de prensa"),
	_(
		"Pago a no residentes - Contratos de fletamento de naves para empresas de transporte aéreo o marítimo internacional"
	),
	_(
		"Pago a no residentes - Enajenación de derechos representativos de capital u otros derechos que permitan la exploración, explotación, concesión o similares de sociedades"
	),
	_(
		"Pago al exterior - Servicios técnicos, administrativos o de consultoría y regalías con convenio de doble tributación"
	),
	_(
		"Pago al exterior - Servicios técnicos, administrativos o de consultoría y regalías sin convenio de doble tributación"
	),
	_(
		"Pago al exterior - Servicios técnicos, administrativos o de consultoría y regalías en paraísos fiscales"
	),
	_("Pago a no residentes - Seguros y reaseguros (primas y cesiones)"),
	_("Pago al exterior - Seguros y reaseguros (primas y cesiones) sin convenio de doble tributación"),
	_("Pago al exterior - Seguros y reaseguros (primas y cesiones) en paraísos fiscales"),
	_("Pago al exterior - Otros pagos al exterior no sujetos a retención"),
	_("Pago a no residentes- Donaciones en dinero -Impuesto a las donaciones"),
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

ATS_COLLECTOR_STRINGS = [
	# User-facing ATS collector errors (l10n_ec/sri/ats_collector.py).
	# Extraction markers only; this module is never imported at runtime.
	_("ATS collection needs a company for '{}-{:02d}'."),
	_("ATS collection year '{}' is out of range."),
	_("ATS collection month '{}' is out of range."),
	_("ATS document number '{}' is not a SRI number."),
	_("SRI withholding concepto '{}' is ATS scope and has no XML retention row."),
	_("SRI withholding concepto '{}' carries rate '{}' but the official rate is '{}'."),
	_("SRI IVA withholding concepto '{}' has no ATS bucket for rate '{}'."),
]

ATS_BUILDER_STRINGS = [
	# User-facing ATS renderer errors (l10n_ec/sri/ats_builder.py).
	# Extraction markers only; this module is never imported at runtime.
	_("ATS period '{}' is not a fiscal month (MMYYYY)."),
	_("ATS period month '{}' is out of range."),
	_("ATS period year '{}' is out of range."),
	_("ATS informante must be a dict of header fields."),
	_("ATS informante needs 'IdInformante' (RUC)."),
	_("ATS informante needs 'razonSocial'."),
	_("ATS 'TipoIDInformante' '{}' is not 'R'."),
	_("ATS 'codigoOperativo' '{}' is not 'IVA'."),
	_("ATS {} row carries unknown field '{}'."),
	_("ATS {} row needs '{}'."),
	_("ATS compras row carries a partial withholding reference ({})."),
	_("ATS section '{}' must be a list of rows."),
	_("ATS collected payload must be a dict of sections."),
	_("ATS payload carries unknown section '{}'."),
	_("ATS zip needs the built XML string."),
]

"""Official SRI withholding concepto table (XML `codigoRetencion` values).

Source: SRI Resolution NAC-DGERCGC26-00000009, vigencia 2026-03-01.
IR conceptos follow SRI Tabla 20; IVA conceptos follow SRI Tabla 23.
Rates take only the OCA ATS catalog 2026-03-01 era (which matches the
Quipuy marzo-2026 resolution values on every overlapping code); codes with
no single 2026-03-01 percentage stay `None` (known but unrated, fail loud
on use) instead of borrowing another era. Casillero pairs come only from
headers explicitly printed in the 103 guide (`guia103.txt`); the C/C+50
pattern is observed, never inferred. Exterior 400s and otros 500s live
under impuesto '9': ATS scope, never an XML `codigoRetencion`.
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

# Impuestos that are never valid as XML `codigoRetencion`. '1' is IR
# (renta), '2' is IVA, '9' marks exterior/otros ATS scope (never XML).
NON_EMITTABLE_IMPUESTOS = frozenset({"9"})

# {codigoRetencion: (impuesto, description, rate, valid_from, casilleros)}.
# Code suffixes ('303A', '3440', ...) stay verbatim as the SRI spells them.
# `rate` is a percent (10.0 = 10%) or None when no single official rate
# applies at vigencia. `casilleros` holds the 103 guide casilleros sighted
# for the code, or None when the guide names none.
CONCEPTS = {
	# IR (impuesto '1').
	"303": ("1", "Honorarios profesionales", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM, (303, 353)),
	"303A": ("1", "Servicios profesionales sociedades", 5.0, WITHHOLDING_CONCEPTS_VALID_FROM, (3030, 3530)),
	"304": ("1", "Intelecto sin título", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM, (304, 354)),
	"304A": ("1", "Comisiones intelecto", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM, (304, 354)),
	"304C": ("1", "Deportistas", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM, (304, 354)),
	"304D": ("1", "Artistas", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM, (304, 354)),
	"307": ("1", "Mano de obra", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM, (307, 357)),
	"308": ("1", "Imagen y renombre", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM, (308, 358)),
	"309": ("1", "Publicidad", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM, (309,)),
	"310": ("1", "Transporte", 1.0, WITHHOLDING_CONCEPTS_VALID_FROM, (310,)),
	"311": ("1", "Liquidación compra", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM, (311, 361)),
	"312": ("1", "Bienes muebles", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM, (312, 362)),
	"319": ("1", "Leasing", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM, (319, 369)),
	"320": ("1", "Arriendo inmuebles", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM, (320, 370)),
	"322": ("1", "Seguros", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM, (322, 372)),
	"323": ("1", "Rendimientos financieros", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM, (323, 373)),
	"332": ("1", "No sujeto", 0.0, WITHHOLDING_CONCEPTS_VALID_FROM, (332,)),
	"343": ("1", "Otras 1%", 1.0, WITHHOLDING_CONCEPTS_VALID_FROM, (343, 393)),
	"343A": ("1", "Energía eléctrica", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM, (343, 393)),
	"343B": ("1", "Construcción", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM, (3430, 3450)),
	"343C": ("1", "Botellas PET", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"344A": ("1", "Tarjetas", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM, (344, 394)),
	"344B": ("1", "Minerales", 2.0, WITHHOLDING_CONCEPTS_VALID_FROM, (344, 394)),
	"3440": ("1", "Otras 3%", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM, (3440, 3940)),
	"3482": ("1", "Comisiones sociedades", 5.0, WITHHOLDING_CONCEPTS_VALID_FROM, (3140, 3640)),
	# IR residentes extension, current rates (OCA 2026-03-01 single percent).
	"302": (
		"1",
		"Ingresos del trabajo en relación de dependencia",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(302, 352),
	),
	"304B": (
		"1",
		"Pagos a notarios y registradores de la propiedad y mercantil por sus actividades ejercidas como tales",
		10.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(304, 354),
	),
	"304E": (
		"1",
		"Honorarios y demás pagos por servicios de docencia",
		10.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(304, 354),
	),
	"312A": (
		"1",
		"COMPRAS AL PRODUCTOR: de bienes de origen bioacuático, forestal y los descritos  el art.27.1 de LRTI",
		1.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3120, 3620),
	),
	"312C": (
		"1",
		"COMPRAS AL COMERCIALIZADOR: de bienes de origen bioacuático, forestal y los descritos  el art.27.1 de LRTI",
		1.75,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3121, 3621),
	),
	"314A": (
		"1",
		"Regalías por concepto de franquicias de acuerdo al Código INGENIOS (COESCCI) - pago a personas naturales",
		10.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(314, 364),
	),
	"314B": (
		"1",
		"Cánones, derechos de autor,  marcas, patentes y similares de acuerdo  al Código INGENIOS (COESCCI) – pago a personas naturales",  # noqa: RUF001 (sourced OCA spelling)
		10.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(314, 364),
	),
	"314C": (
		"1",
		"Regalías por concepto de franquicias de acuerdo al Código INGENIOS (COESCCI) - pago a sociades",
		10.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(314, 364),
	),
	"314D": (
		"1",
		"Cánones, derechos de autor,  marcas, patentes y similares de acuerdo  al Código INGENIOS (COESCCI)",
		10.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(314, 364),
	),
	"323A": (
		"1",
		"Rendimientos financieros depósitos Cta. Corriente",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323B1": (
		"1",
		"Rendimientos financieros  depósitos Cta. Ahorros Sociedades",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323E": (
		"1",
		"Rendimientos financieros depósito a plazo fijo  gravados",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323E2": (
		"1",
		"Rendimientos financieros depósito a plazo fijo exentos",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3230,),
	),
	"323F": (
		"1",
		"Rendimientos financieros operaciones de reporto - repos",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323G": (
		"1",
		"Inversiones (captaciones) rendimientos distintos de aquellos pagados a IFIs",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323H": ("1", "Rendimientos financieros  obligaciones", 3.0, WITHHOLDING_CONCEPTS_VALID_FROM, (323, 373)),
	"323I": (
		"1",
		"Rendimientos financieros  bonos convertible en acciones",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323M": (
		"1",
		"Rendimientos financieros : Inversiones en títulos valores en renta fija gravados",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323N": (
		"1",
		"Rendimientos financieros  Inversiones en títulos valores en renta fija exentos",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3230,),
	),
	"323O": (
		"1",
		"Intereses y demás rendimientos financieros pagados a bancos y otras entidades sometidas al control de la Superintendencia de Bancos y de la Economía Popular y Solidaria",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3230,),
	),
	"323P": (
		"1",
		"Intereses pagados por entidades del sector público a favor de sujetos pasivos",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323Q": (
		"1",
		"Otros intereses y rendimientos financieros gravados",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323R": (
		"1",
		"Otros intereses y rendimientos financieros exentos",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3230,),
	),
	"323S": (
		"1",
		"Pagos y créditos en cuenta efectuados por el BCE y los depósitos centralizados de valores, en calidad de intermediarios, a instituciones del sistema financiero por cuenta de otras personas naturales y sociedades",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(323, 373),
	),
	"323T": (
		"1",
		"Rendimientos financieros originados en la deuda pública ecuatoriana",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3230,),
	),
	"323U": (
		"1",
		"Rendimientos financieros originados en títulos valores de obligaciones de 360 días o más para el financiamiento de proyectos públicos en asociación público-privada",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3230,),
	),
	"324A": (
		"1",
		"Intereses en operaciones de crédito entre instituciones del sistema financiero y entidades economía popular y solidaria.",
		2.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(324, 374),
	),
	"324B": (
		"1",
		"Inversiones entre instituciones del sistema financiero y entidades economía popular y solidaria",
		2.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(324, 374),
	),
	"324C": (
		"1",
		"Pagos y créditos en cuenta efectuados por el BCE y los depósitos centralizados de valores, en calidad de intermediarios, a instituciones del sistema financiero por cuenta de otras instituciones del sistema financiero",
		2.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(324, 374),
	),
	"325": ("1", "Anticipo dividendos", 25.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"3250": (
		"1",
		"Dividendos exentos (por no llegar a franja exenta o beneficio de otras leyes)",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"325A": (
		"1",
		"Préstamos accionistas, beneficiarios o partícipes residentes o establecidos en el Ecuador",
		25.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"328": (
		"1",
		"Dividendos distribuidos a sociedades residentes",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"329": (
		"1",
		"Dividendos distribuidos a fideicomisos residentes",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"331": (
		"1",
		"Dividendos en acciones (capitalización de utilidades)",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"332B": ("1", "Compra de bienes inmuebles", 0.0, WITHHOLDING_CONCEPTS_VALID_FROM, (332,)),
	"332C": ("1", "Transporte público de pasajeros", 0.0, WITHHOLDING_CONCEPTS_VALID_FROM, (332,)),
	"332D": (
		"1",
		"Pagos en el país por transporte de pasajeros o transporte internacional de carga, a compañías nacionales o extranjeras de aviación o marítimas",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(332,),
	),
	"332E": (
		"1",
		"Valores entregados por las cooperativas de transporte a sus socios",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(310,),
	),
	"332F": (
		"1",
		"Compraventa de divisas distintas al dólar de los Estados Unidos de América",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3230,),
	),
	"332G": ("1", "Pagos con tarjeta de crédito", 0.0, WITHHOLDING_CONCEPTS_VALID_FROM, (332,)),
	"332H": (
		"1",
		"Pago al exterior tarjeta de crédito reportada por la Emisora de tarjeta de crédito, solo recap",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(332,),
	),
	"332I": (
		"1",
		"Pago a través de convenio de debito (Clientes IFI`s)",
		0.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(332,),
	),
	"333": (
		"1",
		"Ganancia en la enajenación de derechos representativos de capital u otros derechos que permitan la exploración, explotación, concesión o similares de sociedades, que se coticen en bolsa de valores del Ecuador",
		10.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(333,),
	),
	"334": (
		"1",
		"Contraprestación producida por la enajenación de derechos representativos de capital u otros derechos que permitan la exploración, explotación, concesión o similares de sociedades, no cotizados en bolsa de valores del Ecuador",
		2.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(334,),
	),
	"335": (
		"1",
		"Loterías, rifas, pronósticos deportivos, apuestas y similares",
		15.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(335,),
	),
	"340": (
		"1",
		"Impuesto único a la exportación de banano",
		3.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3400, 3900),
	),
	"3480": (
		"1",
		"Impuesto a la renta único sobre los ingresos percibidos por los operadores de pronósticos deportivos",
		15.0,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3480, 3980),
	),
	# IR residentes extension, known but unrated (no single 2026-03-01 rate).
	"312B": (
		"1",
		"Impuesto a la Renta único para la actividad de producción y cultivo de palma aceitera",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"323B2": (
		"1",
		"Por RF:  depósitos Cta. Ahorros Persona Natural",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"323C": (
		"1",
		"Por rendimientos financieros:  depósitos en cuentas exentas",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"323D": (
		"1",
		"Por rendimientos financieros: compra, cancelación o redención de mini bem´s y bem´s",  # noqa: RUF001 (sourced OCA spelling)
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"323J": (
		"1",
		"Por RF: bonos de organismos y gobiernos extranjeros",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"323K": (
		"1",
		"Por RF: Intereses en operaciones de crédito entre instituciones del sistema financiero y entidades economía popular y solidaria.",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"323L": (
		"1",
		"Por RF: Por inversiones entre instituciones del sistema financiero y entidades economía popular y solidaria.",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"326": (
		"1",
		"Dividendos distribuidos que correspondan al impuesto a la renta único establecido en el art. 27 de la LRTI",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"327": (
		"1",
		"Dividendos distribuidos a personas naturales residentes",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"330": (
		"1",
		"Dividendos gravados distribuidos en acciones (reinversión de utilidades sin derecho a reducción tarifa IR)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"332A": (
		"1",
		"Por la enajenación ocasional de acciones o participaciones y títulos valores",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"335A": (
		"1",
		"Pago al exterior tarjeta de crédito reportada por la Emisora de tarjeta de crédito, solo recap",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"336": (
		"1",
		"Venta de combustibles a comercializadoras",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(336, 386),
	),
	"337": ("1", "Venta de combustibles a distribuidores", None, WITHHOLDING_CONCEPTS_VALID_FROM, (337, 387)),
	"338": (
		"1",
		"Producción y venta local de banano producido o no por el mismo sujeto pasivo",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3380, 3880),
	),
	"339": (
		"1",
		"Liquidación impuesto único a la venta local de banano de producción propia",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"340A": ("1", "Por energía eléctrica", None, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"340B": (
		"1",
		"Por actividades de construcción de obra material inmueble, urbanización, lotización o actividades similares",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"341": (
		"1",
		"Impuesto único a la exportación de banano de producción propia - componente 2",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"342": (
		"1",
		"Impuesto único a la exportación de banano producido por terceros",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"342A": (
		"1",
		"Impuesto único a la exportación de banano producido por terceros de Asociaciones de micro y pequeños productores hasta 1000 cajas por semana por cada socio.",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"342B": (
		"1",
		"Impuesto único a la exportación de banano producido por terceros de Asociaciones de micro, pequeños y medianos productores",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"344": ("1", "Otras retenciones aplicables el 2%", None, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"345": ("1", "Otras retenciones aplicables el 8%", None, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"345A": (
		"1",
		"Dividendos gravados distribuidos en acciones (reinversión de utilidades sin derecho a reducción tarifa IR)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"345B": (
		"1",
		"Dividendos exentos a sociedades, nacionales o extranjeras, domiciliadas en el Ecuador",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"345C": (
		"1",
		"Dividendos exentos distribuidos en acciones (reinversión de utilidades con derecho a reducción tarifa IR)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"346": (
		"1",
		"Otras retenciones aplicables a otros porcentajes",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"346A": (
		"1",
		"Otras ganancias de capital distintas de enajenación de derechos representativos de capital",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"346B": (
		"1",
		"Donaciones en dinero -Impuesto a las donaciones",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(346, 396),
	),
	"346C": (
		"1",
		"Retención a cargo del propio sujeto pasivo por la producción y/o comercialización de minerales y otros bienes",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"346D": (
		"1",
		"Retención a cargo del propio sujeto pasivo por la comercialización de productos forestales",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3370, 3870),
	),
	"347": (
		"1",
		"Donaciones en dinero -Impuesto a la donaciones",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"347A": (
		"1",
		"Dividendos anticipados préstamos accionistas, beneficiarios o partícipes",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"348": (
		"1",
		"Impuesto único a ingresos provenientes de actividades agropecuarias en etapa de producción / comercialización local o exportación",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"3481": (
		"1",
		"Autorretenciones Sociedades Grandes Contribuyentes",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(3481,),
	),
	"349": (
		"1",
		"Retención a cargo del propio sujeto pasivo por la comercialización de productos forestales",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"350": (
		"1",
		"Otras autorretenciones (inciso 1 y 2 Art.92.1 RLRTI)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(350, 400),
	),
	"351": ("1", "Régimen Microempresarial", None, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	# IVA (impuesto '2').
	"1": ("2", "Bienes", 30.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"2": ("2", "Servicios", 70.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"3": ("2", "Honorarios", 100.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"7": ("2", "Retención cero", 0.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"8": ("2", "No procede", 0.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"9": ("2", "Especial 10%", 10.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"10": ("2", "Especial 20%", 20.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"11": ("2", "Especial 50%", 50.0, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	# Exterior / otros (impuesto '9'): ATS scope, never XML `codigoRetencion`.
	"500": (
		"9",
		"Pago a no residentes - Rentas Inmobiliarias",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"501": (
		"9",
		"Pago a no residentes - Beneficios/Servicios  Empresariales",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"501A": (
		"9",
		"Pago a no residentes - Servicios técnicos, administrativos o de consultoría y regalías",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(410, 421, 431),
	),
	"502": ("9", "Pago al exterior - Servicios Empresariales", None, WITHHOLDING_CONCEPTS_VALID_FROM, None),
	"503": (
		"9",
		"Pago a no residentes- Navegación Marítima y/o aérea",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"504": (
		"9",
		"Pago a no residentes- Dividendos distribuidos a personas naturales (domiciliados o no en paraíso fiscal) o a sociedades sin beneficiario efectivo persona natural residente en Ecuador",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(4050, 4160, 4260),
	),
	"504A": (
		"9",
		"Dividendos a sociedades con beneficiario efectivo persona natural residente en el Ecuador",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(4060, 4170, 4270),
	),
	"504B": (
		"9",
		"Dividendos a no residentes incumpliendo el deber de informar la composición societaria",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(4070, 4180, 4280),
	),
	"504C": (
		"9",
		"Dividendos a residentes o establecidos en paraísos fiscales o regímenes de menor imposición (con beneficiario Persona Natural residente en Ecuador)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(4060, 4170, 4270),
	),
	"504D": (
		"9",
		"Dividendos a fideicomisos o establecidos en paraísos fiscales o regímenes de menor imposición (con beneficiario Persona Natural residente en Ecuador)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(4060, 4170, 4270),
	),
	"504E": (
		"9",
		"Pago a no residentes - Anticipo dividendos (no domiciliada en paraísos fiscales o regímenes de menor imposición)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(404, 415, 425),
	),
	"504F": (
		"9",
		"Pago a no residentes - Anticipo dividendos (domiciliadas en paraísos fiscales o regímenes de menor imposición)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(404, 415, 425),
	),
	"504G": (
		"9",
		"Pago a no residentes - Préstamos accionistas, beneficiarios o partícipes (no domiciliadas en paraísos fiscales o regímenes de menor imposición)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(404, 415, 425),
	),
	"504H": (
		"9",
		"Pago a no residentes - Préstamos accionistas, beneficiarios o partícipes (domiciliadas en paraísos fiscales o regímenes de menor imposición)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(404, 415, 425),
	),
	"504I": (
		"9",
		"Pago a no residentes - Préstamos no comerciales a partes relacionadas  (no domiciliadas en paraísos fiscales o regímenes de menor imposición)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(404, 415, 425),
	),
	"504J": (
		"9",
		"Pago a no residentes - Préstamos no comerciales a partes relacionadas  (domiciliadas en paraísos fiscales o regímenes de menor imposición)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(404, 415, 425),
	),
	"505": (
		"9",
		"Pago a no residentes - Rendimientos financieros",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"505A": (
		"9",
		"Pago a no residentes – Intereses de créditos de Instituciones Financieras del exterior",  # noqa: RUF001 (sourced OCA spelling)
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(403, 414, 424),
	),
	"505B": (
		"9",
		"Pago a no residentes – Intereses de créditos de gobierno a gobierno",  # noqa: RUF001 (sourced OCA spelling)
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(403, 414, 424),
	),
	"505C": (
		"9",
		"Pago a no residentes – Intereses de créditos de organismos multilaterales",  # noqa: RUF001 (sourced OCA spelling)
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(403, 414, 424),
	),
	"505D": (
		"9",
		"Pago a no residentes - Intereses por financiamiento de proveedores externos",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(402, 413),
	),
	"505E": (
		"9",
		"Pago a no residentes - Intereses de otros créditos externos",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"505F": (
		"9",
		"Pago a no residentes - Otros Intereses y Rendimientos Financieros",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"506": (
		"9",
		"Pago al exterior - Intereses por Financiamiento de proveedores externos",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"507": (
		"9",
		"Pago al exterior - Intereses de créditos externos",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"508": (
		"9",
		"Pago al exterior - Créditos de IFI's organismos y gobierno a gobierno",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"509": (
		"9",
		"Pago a no residentes- Cánones, derechos de autor,  marcas, patentes y similares",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"509A": (
		"9",
		"Pago a no residentes - Regalías por concepto de franquicias",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"510": (
		"9",
		"Pago a no residentes - Otras ganancias de capital distintas de enajenación de derechos representativos de capital",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"511": (
		"9",
		"Pago a no residentes - Servicios profesionales independientes",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"512": (
		"9",
		"Pago a no residentes - Servicios profesionales dependientes",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"513": ("9", "Pago a no residentes- Artistas", None, WITHHOLDING_CONCEPTS_VALID_FROM, (411, 422, 432)),
	"513A": (
		"9",
		"Pago a no residentes - Deportistas",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"514": (
		"9",
		"Pago a no residentes - Participación de consejeros",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"515": (
		"9",
		"Pago a no residentes- Artistas y relacionados a  organización, producción y espectáculos artísticos y culturales en Ecuador",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"516": ("9", "Pago a no residentes - Pensiones", None, WITHHOLDING_CONCEPTS_VALID_FROM, (411, 422, 432)),
	"517": (
		"9",
		"Pago a no residentes- Reembolso de Gastos",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"518": (
		"9",
		"Pago a no residentes- Funciones Públicas",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"519": (
		"9",
		"Pago a no residentes - Estudiantes",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"520": (
		"9",
		"Pago al exterior - Otros conceptos de ingresos gravados",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"520A": (
		"9",
		"Pago a no residentes - Pago a proveedores de servicios hoteleros y turísticos en el exterior",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"520B": (
		"9",
		"Pago a no residentes - Arrendamientos mercantil internacional",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"520C": (
		"9",
		"Pago al exterior - Seguros, cesiones y reaseguros",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"520D": (
		"9",
		"Pago a no residentes - Comisiones por exportaciones y por promoción de turismo receptivo",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"520E": (
		"9",
		"Pago a no residentes - Por las empresas de transporte marítimo o aéreo y por empresas pesqueras de alta mar, por su actividad.",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"520F": (
		"9",
		"Pago a no residentes - Por las agencias internacionales de prensa",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"520G": (
		"9",
		"Pago a no residentes - Contratos de fletamento de naves para empresas de transporte aéreo o marítimo internacional",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
	"521": (
		"9",
		"Pago a no residentes - Enajenación de derechos representativos de capital u otros derechos que permitan la exploración, explotación, concesión o similares de sociedades",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(408, 419, 429),
	),
	"522A": (
		"9",
		"Pago al exterior - Servicios técnicos, administrativos o de consultoría y regalías con convenio de doble tributación",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"522B": (
		"9",
		"Pago al exterior - Servicios técnicos, administrativos o de consultoría y regalías sin convenio de doble tributación",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"522C": (
		"9",
		"Pago al exterior - Servicios técnicos, administrativos o de consultoría y regalías en paraísos fiscales",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"523A": (
		"9",
		"Pago a no residentes - Seguros y reaseguros (primas y cesiones)",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(409, 420, 430),
	),
	"523B": (
		"9",
		"Pago al exterior - Seguros y reaseguros (primas y cesiones) sin convenio de doble tributación",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"523C": (
		"9",
		"Pago al exterior - Seguros y reaseguros (primas y cesiones) en paraísos fiscales",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"524": (
		"9",
		"Pago al exterior - Otros pagos al exterior no sujetos a retención",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		None,
	),
	"525": (
		"9",
		"Pago a no residentes- Donaciones en dinero -Impuesto a las donaciones",
		None,
		WITHHOLDING_CONCEPTS_VALID_FROM,
		(411, 422, 432),
	),
}

# Per-row provenance. Every row traces to the Quipuy marzo-2026 resolution
# values, the OCA ATS catalog 2026-03-01 era, or an explicit 103 guide
# header; rows the sources leave unrated carry the reason instead of a guess.
SOURCES = {
	"303": "Quipuy marzo-2026 10%; OCA 2026-03-01 corroborates; guide header 303 y 353.",
	"303A": "Quipuy marzo-2026 5%; OCA 2026-03-01 corroborates; guide header 3030 y 3530.",
	"304": "Quipuy marzo-2026 10%; OCA 2026-03-01 corroborates; guide header 304 y 354.",
	"304A": "Quipuy marzo-2026 10%; OCA 2026-03-01 corroborates; guide header 304 y 354.",
	"304C": "Quipuy marzo-2026 10%; OCA 2026-03-01 corroborates; guide header 304 y 354.",
	"304D": "Quipuy marzo-2026 10%; OCA 2026-03-01 corroborates; guide header 304 y 354.",
	"307": "Quipuy marzo-2026 3%; OCA 2026-03-01 corroborates; guide header 307 y 357.",
	"308": "Quipuy marzo-2026 10%; OCA 2026-03-01 corroborates; guide header 308 y 358.",
	"309": "Quipuy marzo-2026 3%; OCA 2026-03-01 corroborates; guide header 309 (single, no pair).",
	"310": "Quipuy marzo-2026 1%; OCA 2026-03-01 corroborates; guide header 310 (single, shared with 332E).",
	"311": "Quipuy marzo-2026 3%; OCA 2026-03-01 corroborates; guide header 311 y 361.",
	"312": "Quipuy marzo-2026 2%; OCA 2026-03-01 corroborates; guide header 312 y 362.",
	"319": "Quipuy marzo-2026 2%; OCA 2026-03-01 corroborates; guide header 319 y 369.",
	"320": "Quipuy marzo-2026 10%; OCA 2026-03-01 corroborates; guide header 320 y 370.",
	"322": "Quipuy marzo-2026 2%; OCA 2026-03-01 corroborates; guide header 322 y 372.",
	"323": "Quipuy marzo-2026 3%; OCA 2026-03-01 corroborates; guide header 323 y 373.",
	"332": "Quipuy marzo-2026 0% (no sujeto); OCA 2026-03-01 corroborates; guide header 332 (single).",
	"343": "Quipuy marzo-2026 1%; OCA 2026-03-01 corroborates; guide header 343 y 393.",
	"343A": "Quipuy marzo-2026 2%; OCA 2026-03-01 corroborates; guide header 343 y 393.",
	"343B": "Quipuy marzo-2026 2%; OCA 2026-03-01 corroborates; guide header 3430 y 3450 as printed.",
	"343C": "Quipuy marzo-2026 2%; OCA 2026-03-01 corroborates; no explicit header (guide 344/394 group cites 344C, absent from OCA).",
	"344A": "Quipuy marzo-2026 2%; OCA 2026-03-01 corroborates; guide header 344 y 394.",
	"344B": "Quipuy marzo-2026 2%; OCA 2026-03-01 corroborates; guide header 344 y 394.",
	"3440": "Quipuy marzo-2026 3%; OCA 2026-03-01 corroborates; guide header 3440 y 3940 (prints code 340, OCA wording identifies 3440).",
	"3482": "Quipuy marzo-2026 5%; OCA 2026-03-01 corroborates; guide header 3140 y 3640.",
	"302": "OCA single era 2024-04-01 unresolved (Abierto); guide header 302 y 352; progressive table, no single rate.",
	"304B": "OCA 2026-03-01 rate 10%; guide header 304 y 354.",
	"304E": "OCA 2026-03-01 rate 10%; guide header 304 y 354.",
	"312A": "OCA 2026-03-01 rate 1%; guide header 3120 y 3620.",
	"312B": "No 2026-03-01 row (latest OCA era 2020-09-01, 1%); no guide sighting; known but unrated.",
	"312C": "OCA 2026-03-01 rate 1.75%; guide header 3121 y 3621.",
	"314A": "OCA 2026-03-01 rate 10%; guide header 314 y 364.",
	"314B": "OCA 2026-03-01 rate 10%; guide header 314 y 364.",
	"314C": "OCA 2026-03-01 rate 10%; guide header 314 y 364.",
	"314D": "OCA 2026-03-01 rate 10%; guide header 314 y 364.",
	"323A": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323B1": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323B2": "No 2026-03-01 row (latest OCA era 2013-01-01, unresolved); no guide sighting; known but unrated.",
	"323C": "No 2026-03-01 row (latest OCA era 2013-01-01, unresolved); no guide sighting; known but unrated.",
	"323D": "No 2026-03-01 row (latest OCA era 2014-10-01, unresolved); no guide sighting; known but unrated.",
	"323E": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323E2": "OCA 2026-03-01 rate 0%; guide header 3230 (single).",
	"323F": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323G": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323H": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323I": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323J": "No 2026-03-01 row (latest OCA era 2013-01-01, 2%); no guide sighting; known but unrated.",
	"323K": "No 2026-03-01 row (latest OCA era 2014-10-01, 1%); no guide sighting; known but unrated.",
	"323L": "No 2026-03-01 row (latest OCA era 2014-10-01, 1%); no guide sighting; known but unrated.",
	"323M": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323N": "OCA 2026-03-01 rate 0%; guide header 3230 (single).",
	"323O": "OCA 2026-03-01 rate 0%; guide header 3230 (single).",
	"323P": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323Q": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323R": "OCA 2026-03-01 rate 0%; guide header 3230 (single).",
	"323S": "OCA 2026-03-01 rate 3%; guide header 323 y 373.",
	"323T": "OCA 2026-03-01 rate 0%; guide header 3230 (single).",
	"323U": "OCA 2026-03-01 rate 0%; guide header 3230 (single).",
	"324A": "OCA 2026-03-01 rate 2%; guide header 324 y 374.",
	"324B": "OCA 2026-03-01 rate 2%; guide header 324 y 374.",
	"324C": "OCA 2026-03-01 rate 2%; guide header 324 y 374.",
	"325": "OCA 2026-03-01 rate 25%; guide 325 al 331 group names no casilleros.",
	"3250": "OCA 2026-03-01 rate 0%; not cited in the guide; no casilleros sighted.",
	"325A": "OCA 2026-03-01 rate 25%; guide 325 al 331 group names no casilleros.",
	"326": "OCA 2026-03-01 unresolved (12 o 14); guide 325 al 331 group; known but unrated.",
	"327": "OCA 2026-03-01 unresolved (12 o 14); guide 325 al 331 group; known but unrated.",
	"328": "OCA 2026-03-01 rate 0%; guide 325 al 331 group names no casilleros.",
	"329": "OCA 2026-03-01 rate 0%; guide 325 al 331 group names no casilleros.",
	"330": "No 2026-03-01 row (latest OCA era 2020-01-01, 0%); guide 325 al 331 group; known but unrated.",
	"331": "OCA 2026-03-01 rate 0%; guide 325 al 331 group names no casilleros.",
	"332A": "No 2026-03-01 row (latest OCA era 2016-05-01, 0%); no guide sighting; known but unrated.",
	"332B": "OCA 2026-03-01 rate 0% (no sujeto); guide header 332 (single).",
	"332C": "OCA 2026-03-01 rate 0% (no sujeto); guide header 332 (single).",
	"332D": "OCA 2026-03-01 rate 0% (no sujeto); guide header 332 (single).",
	"332E": "OCA 2026-03-01 rate 0%; listed under guide header 310, not under 332.",
	"332F": "OCA 2026-03-01 rate 0%; guide header 3230 (single).",
	"332G": "OCA 2026-03-01 rate 0% (no sujeto); guide header 332 (single).",
	"332H": "OCA 2026-03-01 rate 0% (no sujeto, residente family); guide header 332 (single).",
	"332I": "OCA 2026-03-01 rate 0% (no sujeto); guide header 332 (single).",
	"333": "OCA 2026-03-01 rate 10%; guide header 333 (single).",
	"334": "OCA 2026-03-01 rate 2%; guide header 334 (single, no explicit code citation).",
	"335": "OCA 2026-03-01 rate 15% (guide states impuesto único del 15%); guide header 335 (single).",
	"335A": "No 2026-03-01 row (latest OCA era 2014-10-01, unresolved, wording duplicates 332H); no guide sighting.",
	"336": "OCA 2026-03-01 unresolved (2/mil, per-mil not percent); guide header 336 y 386; known but unrated.",
	"337": "OCA 2026-03-01 unresolved (3/mil, per-mil not percent); guide header 337 y 387; known but unrated.",
	"338": "OCA 2026-03-01 unresolved (1 a 2 range); guide header 3380 y 3880; known but unrated.",
	"339": "No 2026-03-01 row (latest OCA era 2019-11-01, unresolved); no guide sighting; known but unrated.",
	"340": "OCA 2026-03-01 rate 3%; guide header 3400 y 3900.",
	"340A": "No 2026-03-01 row (latest OCA era 2014-10-01, 1%); no guide sighting; known but unrated.",
	"340B": "No 2026-03-01 row (latest OCA era 2014-10-01, 1%); no guide sighting; known but unrated.",
	"341": "No 2026-03-01 row (latest OCA era 2019-11-01, unresolved); no guide sighting; known but unrated.",
	"342": "No 2026-03-01 row (latest OCA era 2019-11-01, unresolved); no guide sighting; known but unrated.",
	"342A": "No 2026-03-01 row (latest OCA era 2016-05-01, unresolved); no guide sighting; known but unrated.",
	"342B": "No 2026-03-01 row (latest OCA era 2016-05-01, unresolved); no guide sighting; known but unrated.",
	"344": "No 2026-03-01 row (latest OCA era 2020-01-01, 2%); guide 344/394 group cites only 344A/B/C; known but unrated.",
	"345": "No 2026-03-01 row (latest OCA era 2024-01-01, 8%); no guide sighting; known but unrated.",
	"345A": "No 2026-03-01 row (latest OCA era 2014-10-01, unresolved); no guide sighting; known but unrated.",
	"345B": "No 2026-03-01 row (latest OCA era 2014-10-01, 0%); no guide sighting; known but unrated.",
	"345C": "No 2026-03-01 row (latest OCA era 2014-10-01, 0%); no guide sighting; known but unrated.",
	"346": "OCA 2026-03-01 unresolved (varios porcentajes); guide 346/396 names only 346B; known but unrated.",
	"346A": "OCA 2026-03-01 unresolved (varios porcentajes); no guide sighting; known but unrated.",
	"346B": "OCA 2026-03-01 unresolved (donations, Art 36 LRTI); guide header 346 y 396; known but unrated.",
	"346C": "OCA 2026-03-01 unresolved (0 a 10, minerals); no guide sighting; known but unrated.",
	"346D": "OCA 2026-03-01 unresolved (0 o 10, forestal); guide header 3370 y 3870; known but unrated.",
	"347": "No 2026-03-01 row (latest OCA era 2016-05-01, unresolved); no guide sighting; known but unrated.",
	"347A": "No 2026-03-01 row (latest OCA era 2014-10-01, 22%); no guide sighting; known but unrated.",
	"348": "No 2026-03-01 row (latest OCA era 2024-01-01, 1%); no guide sighting; known but unrated.",
	"3480": "OCA 2026-03-01 rate 15%; guide header 3480 y 3980.",
	"3481": "OCA 2026-03-01 unresolved; guide notes validity until June 2021; expired, known but unrated.",
	"349": "No 2026-03-01 row (latest OCA era 2016-05-01, unresolved); no guide sighting; known but unrated.",
	"350": "OCA 2026-03-01 unresolved (1,50 o 1,75); guide header 350 y 400; known but unrated.",
	"351": "No 2026-03-01 row (latest OCA era 2020-09-01, 1.75%); no guide sighting; known but unrated.",
	"1": "SRI Tabla 23 rate 30%; no 103 casilleros (form 104 scope).",
	"2": "SRI Tabla 23 rate 70%; no 103 casilleros (form 104 scope).",
	"3": "SRI Tabla 23 rate 100%; no 103 casilleros (form 104 scope).",
	"7": "SRI Tabla 23 rate 0%; no 103 casilleros (form 104 scope).",
	"8": "SRI Tabla 23 rate 0%; no 103 casilleros (form 104 scope).",
	"9": "SRI Tabla 23 rate 10%; no 103 casilleros (form 104 scope).",
	"10": "SRI Tabla 23 rate 20%; no 103 casilleros (form 104 scope).",
	"11": "SRI Tabla 23 rate 50%; no 103 casilleros (form 104 scope).",
	"500": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"501": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"501A": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 410, 421 y 431.",
	"502": "Latest OCA era 2016-05-01, unrated (ATS scope); no guide sighting.",
	"503": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"504": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 4050, 4160 y 4260.",
	"504A": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 4060, 4170 y 4270.",
	"504B": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 4070, 4180 y 4280.",
	"504C": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 4060, 4170 y 4270.",
	"504D": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 4060, 4170 y 4270.",
	"504E": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 404, 415 y 425.",
	"504F": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 404, 415 y 425.",
	"504G": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 404, 415 y 425.",
	"504H": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 404, 415 y 425.",
	"504I": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 404, 415 y 425.",
	"504J": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 404, 415 y 425.",
	"505": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"505A": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 403, 414 y 424.",
	"505B": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 403, 414 y 424.",
	"505C": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 403, 414 y 424.",
	"505D": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 402 y 413.",
	"505E": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"505F": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"506": "Latest OCA era 2013-01-01, unrated (ATS scope); no guide sighting.",
	"507": "Latest OCA era 2013-01-01, unrated (ATS scope); no guide sighting.",
	"508": "Latest OCA era 2013-01-01, unrated (ATS scope); no guide sighting.",
	"509": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"509A": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"510": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"511": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"512": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"513": "Latest OCA era 2024-03-01, unrated (ATS scope); guide header 411, 422 y 432.",
	"513A": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"514": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"515": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"516": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"517": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"518": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"519": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"520": "Latest OCA era 2016-05-01, unrated (ATS scope); no guide sighting.",
	"520A": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"520B": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"520C": "Latest OCA era 2014-10-01, unrated (ATS scope); no guide sighting.",
	"520D": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"520E": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"520F": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"520G": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
	"521": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 408, 419 y 429.",
	"522A": "Latest OCA era 2016-05-01, unrated (ATS scope); no guide sighting.",
	"522B": "Latest OCA era 2015-03-01, unrated (ATS scope); no guide sighting.",
	"522C": "Latest OCA era 2015-03-01, unrated (ATS scope); no guide sighting.",
	"523A": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 409, 420 y 430.",
	"523B": "Latest OCA era 2015-03-01, unrated (ATS scope); no guide sighting.",
	"523C": "Latest OCA era 2015-03-01, unrated (ATS scope); no guide sighting.",
	"524": "Latest OCA era 2016-05-01, unrated (ATS scope); no guide sighting.",
	"525": "OCA 2026-03-01 no_residente, unrated (ATS scope); guide header 411, 422 y 432.",
}

# Codes the sources name but this table cannot carry. 344C is cited by the
# 103 guide yet absent from the OCA catalog in every era: no description or
# rate source exists, so it stays out instead of being guessed.
UNMAPPED_CONCEPTS = {
	"344C": "103 guide 344/394 group cites 344A, 344B y 344C; OCA catalog has no 344C in any era (343C carries the PET wording); unsourceable.",
}

# Pre-2013 exterior/CDI matrix (latest OCA era 2012-01-01, no 103 guide
# sighting): ATS/9A scope, never XML `codigoRetencion`. Listed explicitly so
# no code falls silent: bare 401, the full 401+group+suffix matrix, and the
# five superseded 4xx headers.
UNMAPPED_PRE2013_EXTERIOR = frozenset({"401", "403", "405", "421", "427", "427A"}) | {
	f"401{group}{suffix}" for group in "ABCDEFGHIJKLMNOP" for suffix in "ABCDEFGHIJKLMNO"
}


def resolve_concepto(code: str) -> tuple:
	"""Return `(impuesto, rate, description)` for an SRI `codigoRetencion`.

	Raises `SriVoucherError` for unknown codes instead of guessing.
	"""
	from l10n_ec.sri.codes import sri_code

	code = sri_code(code)
	try:
		impuesto, description, rate, _valid_from, _casilleros = CONCEPTS[code]
	except KeyError:
		raise SriVoucherError(_("Unknown SRI withholding concepto code '{}'.").format(code)) from None
	return (impuesto, rate, description)


def casilleros_for(code: str) -> tuple | None:
	"""Return the 103 guide casilleros sighted for a concepto code.

	Returns None when the guide names no casilleros for the code.
	Raises `SriVoucherError` for unknown codes instead of guessing.
	"""
	try:
		_casilleros = CONCEPTS[code][4]
	except KeyError:
		raise SriVoucherError(_("Unknown SRI withholding concepto code '{}'.").format(code)) from None
	return _casilleros


def concepto_rate(code: str) -> float:
	"""Return the official percent rate for a concepto code.

	Raises `SriVoucherError` for unknown codes and for known-but-unrated
	codes (rate None): use-paths that need a rate must fail loud.
	"""
	_impuesto, rate, _description = resolve_concepto(code)
	if rate is None:
		raise SriVoucherError(
			_("SRI withholding concepto '{}' has no official rate for the current vigencia.").format(code)
		)
	return rate


def validate_concepto_map(code_map: dict) -> None:
	"""Fail loud on pending (`None`) or unknown concepto codes in a per-call map.

	`code_map` resolves category names to `(impuesto, codigoRetencion)`.
	Also rejects pairs whose impuesto disagrees with the official table and
	codes outside XML scope (impuesto '9': ATS only, never `codigoRetencion`).
	"""
	for category, pair in code_map.items():
		impuesto, codigo = pair
		if codigo is None:
			raise SriVoucherError(_("Withholding category '{}' has no SRI code mapping.").format(category))
		expected, _rate, _description = resolve_concepto(codigo)
		if expected in NON_EMITTABLE_IMPUESTOS:
			raise SriVoucherError(
				_(
					"SRI withholding concepto '{}' is ATS scope and cannot be used as an XML codigoRetencion."
				).format(codigo)
			)
		if impuesto != expected:
			raise SriVoucherError(
				_("Withholding category '{}' maps impuesto '{}' but concepto '{}' is impuesto '{}'.").format(
					category, impuesto, codigo, expected
				)
			)

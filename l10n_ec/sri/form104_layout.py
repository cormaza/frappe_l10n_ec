"""DIMM Form 104 presentation layout: official labels, blocks, report rows.

Source for labels: the SRI DIMM printout (Resolución NAC-DGERCGC17-00000324,
columns VALOR BRUTO / VALOR NETO / IMPUESTO GENERADO). Labels below quote that
printout verbatim; everything else in this module is English. Pure Python, no
frappe: Ring 1 tests inject plain ``totals`` dicts.

Two label groups postdate the printout and follow its triplet pattern instead:
``425/435/445`` + ``540/550/560`` (tarifa diferenciada, SRI rate code ``8``;
see ``docs/IVA_8_HOLIDAY.md``) and the ``565`` informational child (our own
``collect_104`` formula, never a portal box). Boxes the collector can never
write (``410/420/430/486/487/492/530/533/534/623/624/625``) fail loud when
nonzero instead of rendering with an invented label.
"""

try:
	from frappe import _
except ImportError:  # pragma: no cover

	def _(message: str) -> str:
		return message


#: Official DIMM labels per box (Spanish protocol exception).
LABELS = {
	"401": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA DIFERENTE DE CERO",
	"402": "VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA DIFERENTE DE CERO",
	"403": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA 0% QUE NO DAN DERECHO A CRÉDITO TRIBUTARIO",
	"404": "VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA 0% QUE NO DAN DERECHO A CRÉDITO TRIBUTARIO",
	"405": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA 0% QUE DAN DERECHO A CRÉDITO TRIBUTARIO",
	"406": "VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA 0% QUE DAN DERECHO A CRÉDITO TRIBUTARIO",
	"407": "EXPORTACIONES DE BIENES",
	"408": "EXPORTACIONES DE SERVICIOS Y/O DERECHOS",
	"409": "TOTAL VENTAS Y OTRAS OPERACIONES",
	"411": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA DIFERENTE DE CERO",
	"412": "VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA DIFERENTE DE CERO",
	"413": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA 0% QUE NO DAN DERECHO A CRÉDITO TRIBUTARIO",
	"414": "VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA 0% QUE NO DAN DERECHO A CRÉDITO TRIBUTARIO",
	"415": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA 0% QUE DAN DERECHO A CRÉDITO TRIBUTARIO",
	"416": "VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA 0% QUE DAN DERECHO A CRÉDITO TRIBUTARIO",
	"417": "EXPORTACIONES DE BIENES",
	"418": "EXPORTACIONES DE SERVICIOS Y/O DERECHOS",
	"419": "TOTAL VENTAS Y OTRAS OPERACIONES",
	"421": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA DIFERENTE DE CERO",
	"422": "VENTAS DE ACTIVOS FIJOS GRAVADAS TARIFA DIFERENTE DE CERO",
	"423": "IVA GENERADO EN LA DIFERENCIA ENTRE VENTAS Y NOTAS DE CRÉDITO CON DISTINTA TARIFA (AJUSTE A PAGAR)",
	"424": "IVA GENERADO EN LA DIFERENCIA ENTRE VENTAS Y NOTAS DE CRÉDITO CON DISTINTA TARIFA (AJUSTE A FAVOR)",
	"425": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA DIFERENCIADA",
	"429": "TOTAL VENTAS Y OTRAS OPERACIONES",
	"431": "TRANSFERENCIAS NO OBJETO O EXENTAS DE IVA",
	"434": "INGRESOS POR REEMBOLSO COMO INTERMEDIARIO / VALORES FACTURADOS POR OPERADORAS DE TRANSPORTE (INFORMATIVO)",
	"435": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA DIFERENCIADA",
	"441": "TRANSFERENCIAS NO OBJETO O EXENTAS DE IVA",
	"442": "NOTAS DE CRÉDITO TARIFA 0% POR COMPENSAR PRÓXIMO MES",
	"443": "NOTAS DE CRÉDITO TARIFA DIFERENTE DE CERO POR COMPENSAR PRÓXIMO MES",
	"444": "INGRESOS POR REEMBOLSO COMO INTERMEDIARIO / VALORES FACTURADOS POR OPERADORAS DE TRANSPORTE (INFORMATIVO)",
	"445": "VENTAS LOCALES (EXCLUYE ACTIVOS FIJOS) GRAVADAS TARIFA DIFERENCIADA",
	"453": "NOTAS DE CRÉDITO TARIFA DIFERENTE DE CERO POR COMPENSAR PRÓXIMO MES",
	"454": "INGRESOS POR REEMBOLSO COMO INTERMEDIARIO / VALORES FACTURADOS POR OPERADORAS DE TRANSPORTE (INFORMATIVO)",
	"480": "TOTAL TRANSFERENCIAS GRAVADAS TARIFA DIFERENTE DE CERO A CONTADO ESTE MES",
	"481": "TOTAL TRANSFERENCIAS GRAVADAS TARIFA DIFERENTE DE CERO A CRÉDITO ESTE MES",
	"482": "TOTAL IMPUESTO GENERADO (TRASLÁDESE CAMPO 429)",
	"483": "IMPUESTO A LIQUIDAR DEL MES ANTERIOR (TRASLÁDESE EL CAMPO 485 DE LA DECLARACIÓN DEL PERÍODO ANTERIOR)",
	"484": "IMPUESTO A LIQUIDAR EN ESTE MES",
	"485": "IMPUESTO A LIQUIDAR EN EL PRÓXIMO MES (482 - 484)",
	"499": "TOTAL IMPUESTO A LIQUIDAR EN ESTE MES (483 + 484)",
	"500": "ADQUISICIONES Y PAGOS (EXCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA DIFERENTE DE CERO (CON DERECHO A CRÉDITO TRIBUTARIO)",
	"501": "ADQUISICIONES LOCALES DE ACTIVOS FIJOS GRAVADOS TARIFA DIFERENTE DE CERO (CON DERECHO A CRÉDITO TRIBUTARIO)",
	"502": "OTRAS ADQUISICIONES Y PAGOS GRAVADOS TARIFA DIFERENTE DE CERO (SIN DERECHO A CRÉDITO TRIBUTARIO)",
	"503": "IMPORTACIONES DE SERVICIOS Y/O DERECHOS GRAVADOS TARIFA DIFERENTE DE CERO",
	"504": "IMPORTACIONES DE BIENES (EXCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA DIFERENTE DE CERO",
	"505": "IMPORTACIONES DE SERVICIOS Y/O DERECHOS GRAVADOS TARIFA DIFERENTE DE CERO",
	"506": "IMPORTACIONES DE BIENES (INCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA 0%",
	"507": "ADQUISICIONES Y PAGOS (INCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA 0%",
	"508": "ADQUISICIONES REALIZADAS A CONTRIBUYENTES RISE",
	"509": "TOTAL ADQUISICIONES Y PAGOS",
	"510": "ADQUISICIONES Y PAGOS (EXCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA DIFERENTE DE CERO (CON DERECHO A CRÉDITO TRIBUTARIO)",
	"511": "ADQUISICIONES LOCALES DE ACTIVOS FIJOS GRAVADOS TARIFA DIFERENTE DE CERO (CON DERECHO A CRÉDITO TRIBUTARIO)",
	"512": "OTRAS ADQUISICIONES Y PAGOS GRAVADOS TARIFA DIFERENTE DE CERO (SIN DERECHO A CRÉDITO TRIBUTARIO)",
	"513": "IMPORTACIONES DE SERVICIOS Y/O DERECHOS GRAVADOS TARIFA DIFERENTE DE CERO",
	"514": "IMPORTACIONES DE BIENES (EXCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA DIFERENTE DE CERO",
	"515": "IMPORTACIONES DE SERVICIOS Y/O DERECHOS GRAVADOS TARIFA DIFERENTE DE CERO",
	"516": "IMPORTACIONES DE BIENES (INCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA 0%",
	"517": "ADQUISICIONES Y PAGOS (INCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA 0%",
	"518": "ADQUISICIONES REALIZADAS A CONTRIBUYENTES RISE",
	"519": "TOTAL ADQUISICIONES Y PAGOS",
	"520": "ADQUISICIONES Y PAGOS (EXCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA DIFERENTE DE CERO (CON DERECHO A CRÉDITO TRIBUTARIO)",
	"521": "ADQUISICIONES LOCALES DE ACTIVOS FIJOS GRAVADOS TARIFA DIFERENTE DE CERO (CON DERECHO A CRÉDITO TRIBUTARIO)",
	"522": "OTRAS ADQUISICIONES Y PAGOS GRAVADOS TARIFA DIFERENTE DE CERO (SIN DERECHO A CRÉDITO TRIBUTARIO)",
	"523": "IMPORTACIONES DE SERVICIOS Y/O DERECHOS GRAVADOS TARIFA DIFERENTE DE CERO",
	"524": "IMPORTACIONES DE BIENES (EXCLUYE ACTIVOS FIJOS) GRAVADOS TARIFA DIFERENTE DE CERO",
	"525": "IMPORTACIONES DE SERVICIOS Y/O DERECHOS GRAVADOS TARIFA DIFERENTE DE CERO",
	"526": "IVA GENERADO EN LA DIFERENCIA ENTRE ADQUISICIONES Y NOTAS DE CRÉDITO CON DISTINTA TARIFA (AJUSTE EN POSITIVO AL CRÉDITO TRIBUTARIO)",
	"527": "IVA GENERADO EN LA DIFERENCIA ENTRE ADQUISICIONES Y NOTAS DE CRÉDITO CON DISTINTA TARIFA (AJUSTE EN NEGATIVO AL CRÉDITO TRIBUTARIO)",
	"529": "TOTAL ADQUISICIONES Y PAGOS",
	"531": "ADQUISICIONES NO OBJETO DE IVA",
	"532": "ADQUISICIONES EXENTAS DEL PAGO DE IVA",
	"535": "PAGOS NETOS POR REEMBOLSO COMO INTERMEDIARIO / VALORES FACTURADOS POR SOCIOS A OPERADORAS DE TRANSPORTE (INFORMATIVO)",
	"540": "ADQUISICIONES Y PAGOS GRAVADOS TARIFA DIFERENCIADA (CON DERECHO A CRÉDITO TRIBUTARIO)",
	"541": "ADQUISICIONES NO OBJETO DE IVA",
	"542": "ADQUISICIONES EXENTAS DEL PAGO DE IVA",
	"543": "NOTAS DE CRÉDITO TARIFA 0% POR COMPENSAR PRÓXIMO MES",
	"544": "NOTAS DE CRÉDITO TARIFA DIFERENTE DE CERO POR COMPENSAR PRÓXIMO MES",
	"545": "PAGOS NETOS POR REEMBOLSO COMO INTERMEDIARIO / VALORES FACTURADOS POR SOCIOS A OPERADORAS DE TRANSPORTE (INFORMATIVO)",
	"550": "ADQUISICIONES Y PAGOS GRAVADOS TARIFA DIFERENCIADA (CON DERECHO A CRÉDITO TRIBUTARIO)",
	"554": "NOTAS DE CRÉDITO TARIFA DIFERENTE DE CERO POR COMPENSAR PRÓXIMO MES",
	"555": "PAGOS NETOS POR REEMBOLSO COMO INTERMEDIARIO / VALORES FACTURADOS POR SOCIOS A OPERADORAS DE TRANSPORTE (INFORMATIVO)",
	"560": "ADQUISICIONES Y PAGOS GRAVADOS TARIFA DIFERENCIADA (CON DERECHO A CRÉDITO TRIBUTARIO)",
	"563": "FACTOR DE PROPORCIONALIDAD PARA CRÉDITO TRIBUTARIO (411+412+415+416+417+418) / 419",
	"564": "CRÉDITO TRIBUTARIO APLICABLE EN ESTE PERÍODO",
	"601": "IMPUESTO CAUSADO (SI DIFERENCIA CAMPO 499-564 ES MAYOR QUE CERO)",
	"602": "CRÉDITO TRIBUTARIO APLICABLE EN ESTE PERÍODO (SI DIFERENCIA CAMPO 499-564 ES MENOR QUE CERO)",
	"603": "(-) COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS CON MEDIO ELECTRÓNICO",
	"604": "(-) COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS EN ZONAS AFECTADAS LEY DE SOLIDARIDAD",
	"605": "(-) SALDO CRÉDITO TRIBUTARIO DEL MES ANTERIOR POR ADQUISICIONES E IMPORTACIONES",
	"606": "(-) SALDO CRÉDITO TRIBUTARIO DEL MES ANTERIOR POR RETENCIONES EN LA FUENTE DE IVA QUE LE HAN SIDO EFECTUADAS",
	"607": "(-) SALDO CRÉDITO TRIBUTARIO DEL MES ANTERIOR POR COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS CON MEDIO ELECTRÓNICO",
	"608": "(-) SALDO CRÉDITO TRIBUTARIO DEL MES ANTERIOR POR COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS EN ZONAS AFECTADAS LEY DE SOLIDARIDAD",
	"609": "(-) RETENCIONES EN LA FUENTE DE IVA QUE LE HAN SIDO EFECTUADAS EN ESTE PERÍODO",
	"610": "(+) AJUSTE POR IVA DEVUELTO O DESCONTADO POR ADQUISICIONES EFECTUADAS CON MEDIO ELECTRÓNICO",
	"611": "(+) AJUSTE POR IVA DEVUELTO O DESCONTADO EN ADQUISICIONES EFECTUADAS EN ZONAS AFECTADAS - LEY DE SOLIDARIDAD",
	"612": "(+) AJUSTE POR IVA DEVUELTO E IVA RECHAZADO IMPUTABLE AL CRÉDITO TRIBUTARIO EN EL MES (DEVOLUCIONES DE IVA)",
	"613": "(+) AJUSTE POR IVA DEVUELTO E IVA RECHAZADO IMPUTABLE AL CRÉDITO TRIBUTARIO EN EL MES (RETENCIONES EN LA FUENTE DE IVA)",
	"614": "(+) AJUSTE POR IVA DEVUELTO POR OTRAS INSTITUCIONES DEL SECTOR PÚBLICO IMPUTABLE AL CRÉDITO TRIBUTARIO EN EL MES",
	"615": "SALDO CRÉDITO TRIBUTARIO PARA EL PRÓXIMO MES POR ADQUISICIONES E IMPORTACIONES",
	"617": "SALDO CRÉDITO TRIBUTARIO PARA EL PRÓXIMO MES POR RETENCIONES EN LA FUENTE DE IVA QUE LE HAN SIDO EFECTUADAS",
	"618": "SALDO CRÉDITO TRIBUTARIO PARA EL PRÓXIMO MES POR COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS CON MEDIO ELECTRÓNICO",
	"619": "SALDO CRÉDITO TRIBUTARIO PARA EL PRÓXIMO MES POR COMPENSACIÓN DE IVA POR VENTAS EFECTUADAS EN ZONAS AFECTADAS LEY DE SOLIDARIDAD",
	"620": "SUBTOTAL A PAGAR (601-602-603-604-605-606-607-608-609+610+611+612+613+614)",
	"621": "IVA PRESUNTIVO DE SALAS DE JUEGO (BINGO MECÁNICOS) Y OTROS JUEGOS DE AZAR",
	"699": "TOTAL IMPUESTO A PAGAR POR PERCEPCIÓN (620 + 621)",
	"721": "RETENCIÓN DEL 10%",
	"723": "RETENCIÓN DEL 20%",
	"725": "RETENCIÓN DEL 30%",
	"727": "RETENCIÓN DEL 50%",
	"729": "RETENCIÓN DEL 70%",
	"731": "RETENCIÓN DEL 100%",
	"799": "TOTAL IMPUESTO RETENIDO (721+723+725+727+729+731)",
	"801": "TOTAL IMPUESTO A PAGAR POR RETENCIÓN (799 - 800)",
	"859": "TOTAL CONSOLIDADO DE IMPUESTO AL VALOR AGREGADO (699 + 801)",
}

#: Block titles in DIMM form order.
BLOCK_TITLES = (
	"RESUMEN DE VENTAS Y OTRAS OPERACIONES DEL PERÍODO QUE DECLARA",
	"LIQUIDACIÓN DEL IVA EN EL MES",
	"RESUMEN DE ADQUISICIONES Y PAGOS DEL PERÍODO QUE DECLARA",
	"RESUMEN IMPOSITIVO: AGENTE DE PERCEPCIÓN DEL IMPUESTO AL VALOR AGREGADO",
	"AGENTE DE RETENCIÓN DEL IMPUESTO AL VALOR AGREGADO",
	"TOTAL CONSOLIDADO DE IMPUESTO AL VALOR AGREGADO",
)

#: (kind, boxes) rows per block: triplet = (bruto, neto, impuesto) in one row.
_BLOCKS: tuple = (
	(
		"RESUMEN DE VENTAS Y OTRAS OPERACIONES DEL PERÍODO QUE DECLARA",
		(
			("triplet", ("401", "411", "421")),
			("triplet", ("402", "412", "422")),
			("single-impuesto", ("423",)),
			("single-impuesto", ("424",)),
			("triplet", ("403", "413", None)),
			("triplet", ("404", "414", None)),
			("triplet", ("405", "415", None)),
			("triplet", ("406", "416", None)),
			("triplet", ("407", "417", None)),
			("triplet", ("408", "418", None)),
			("triplet", ("425", "435", "445")),
			("total", ("409", "419", "429")),
			("duo", ("431", "441")),
			("single-neto", ("442",)),
			("duo-impuesto", ("443", "453")),
			("triplet", ("434", "444", "454")),
		),
	),
	(
		"LIQUIDACIÓN DEL IVA EN EL MES",
		(
			("single-bruto", ("480",)),
			("single-bruto", ("481",)),
			("single-bruto", ("482",)),
			("single-bruto", ("483",)),
			("single-bruto", ("484",)),
			("single-bruto", ("485",)),
			("single-bruto", ("499",)),
		),
	),
	(
		"RESUMEN DE ADQUISICIONES Y PAGOS DEL PERÍODO QUE DECLARA",
		(
			("triplet", ("500", "510", "520")),
			("triplet", ("501", "511", "521")),
			("triplet", ("502", "512", "522")),
			("triplet", ("503", "513", "523")),
			("triplet", ("504", "514", "524")),
			("triplet", ("505", "515", "525")),
			("single-impuesto", ("526",)),
			("single-impuesto", ("527",)),
			("duo", ("506", "516")),
			("duo", ("507", "517")),
			("duo", ("508", "518")),
			("triplet", ("540", "550", "560")),
			("total", ("509", "519", "529")),
			("duo", ("531", "541")),
			("duo", ("532", "542")),
			("single-neto", ("543",)),
			("duo-impuesto", ("544", "554")),
			("triplet", ("535", "545", "555")),
			("single-neto", ("563",)),
			("single-neto", ("564",)),
			("child-565", ("565",)),
		),
	),
	(
		"RESUMEN IMPOSITIVO: AGENTE DE PERCEPCIÓN DEL IMPUESTO AL VALOR AGREGADO",
		(
			("single-neto", ("601",)),
			("single-neto", ("602",)),
			("single-neto", ("603",)),
			("single-neto", ("604",)),
			("single-neto", ("605",)),
			("single-neto", ("606",)),
			("single-neto", ("607",)),
			("single-neto", ("608",)),
			("single-neto", ("609",)),
			("single-neto", ("610",)),
			("single-neto", ("611",)),
			("single-neto", ("612",)),
			("single-neto", ("613",)),
			("single-neto", ("614",)),
			("single-neto", ("615",)),
			("single-neto", ("617",)),
			("single-neto", ("618",)),
			("single-neto", ("619",)),
			("single-neto", ("620",)),
			("single-neto", ("621",)),
			("single-neto", ("699",)),
		),
	),
	(
		"AGENTE DE RETENCIÓN DEL IMPUESTO AL VALOR AGREGADO",
		(
			("single-neto", ("721",)),
			("single-neto", ("723",)),
			("single-neto", ("725",)),
			("single-neto", ("727",)),
			("single-neto", ("729",)),
			("single-neto", ("731",)),
			("single-neto", ("799",)),
			("single-neto", ("801",)),
		),
	),
	(
		"TOTAL CONSOLIDADO DE IMPUESTO AL VALOR AGREGADO",
		(("single-neto", ("859",)),),
	),
)

#: Boxes the collector never writes; nonzero here is a layout bug, fail loud.
_UNWRITABLE = frozenset({"410", "420", "430", "486", "487", "492", "530", "533", "534", "623", "624", "625"})


def label_for(box: str) -> str:
	"""Official DIMM label for a box; fail loud on unknown boxes."""
	try:
		return LABELS[box]
	except KeyError:
		raise ValueError(_("Form 104 box '{}' has no SRI label.").format(box)) from None


def build_104_rows(totals: dict) -> list:
	"""Build DIMM-ordered presentation rows from ``collect_104`` totals.

	Row dicts carry ``kind`` (``section``/``triplet``/``total``/``duo``/
	``duo-impuesto``/``single-bruto``/``single-neto``/``single-impuesto``/
	``child-565``), ``casilleros``, ``descripcion``, ``bruto``, ``neto``,
	``impuesto``. Keys of ``totals`` may be ``str`` or ``int``.
	"""
	normalized = {str(box): round(float(value or 0.0), 2) for box, value in (totals or {}).items()}
	for box in _UNWRITABLE:
		if normalized.get(box):
			raise ValueError(_("Form 104 box '{}' is not writable by the collector.").format(box))
	rows: list = []
	for title, lines in _BLOCKS:
		rows.append(
			{
				"kind": "section",
				"casilleros": "",
				"descripcion": title,
				"bruto": None,
				"neto": None,
				"impuesto": None,
			}
		)
		for kind, boxes in lines:
			if kind == "triplet":
				bruto, neto, impuesto = boxes
				rows.append(
					{
						"kind": "total"
						if boxes == ("409", "419", "429") or boxes == ("509", "519", "529")
						else "triplet",
						"casilleros": " · ".join(b for b in boxes if b),
						"descripcion": label_for(bruto),
						"bruto": normalized.get(bruto, 0.0),
						"neto": normalized.get(neto, 0.0) if neto else None,
						"impuesto": normalized.get(impuesto, 0.0) if impuesto else None,
					}
				)
			elif kind == "total":
				bruto, neto, impuesto = boxes
				rows.append(
					{
						"kind": "total",
						"casilleros": " · ".join(boxes),
						"descripcion": "TOTAL — " + label_for(bruto),
						"bruto": normalized.get(bruto, 0.0),
						"neto": normalized.get(neto, 0.0),
						"impuesto": normalized.get(impuesto, 0.0),
					}
				)
			elif kind == "duo":
				bruto, neto = boxes
				rows.append(
					{
						"kind": "duo",
						"casilleros": f"{bruto} · {neto}",
						"descripcion": label_for(bruto),
						"bruto": normalized.get(bruto, 0.0),
						"neto": normalized.get(neto, 0.0),
						"impuesto": None,
					}
				)
			elif kind == "duo-impuesto":
				neto, impuesto = boxes
				rows.append(
					{
						"kind": "duo",
						"casilleros": f"{neto} · {impuesto}",
						"descripcion": label_for(neto),
						"bruto": None,
						"neto": normalized.get(neto, 0.0),
						"impuesto": normalized.get(impuesto, 0.0),
					}
				)
			elif kind == "single-bruto":
				(box,) = boxes
				rows.append(
					{
						"kind": "single",
						"casilleros": box,
						"descripcion": label_for(box),
						"bruto": normalized.get(box, 0.0),
						"neto": None,
						"impuesto": None,
					}
				)
			elif kind == "single-neto":
				(box,) = boxes
				rows.append(
					{
						"kind": "total" if box in ("699", "801", "859", "620") else "single",
						"casilleros": box,
						"descripcion": label_for(box),
						"bruto": None,
						"neto": normalized.get(box, 0.0),
						"impuesto": None,
					}
				)
			elif kind == "single-impuesto":
				(box,) = boxes
				rows.append(
					{
						"kind": "single",
						"casilleros": box,
						"descripcion": label_for(box),
						"bruto": None,
						"neto": None,
						"impuesto": normalized.get(box, 0.0),
					}
				)
			elif kind == "child-565":
				rows.append(
					{
						"kind": "child",
						"casilleros": "565",
						"descripcion": "└ diferencia no aplicable en el período (informativo, base - 564)",
						"bruto": None,
						"neto": normalized.get("565", 0.0),
						"impuesto": None,
					}
				)
	return rows

# Dónde encontrar ATS, Formulario 103 y Formulario 104

Guía rápida para el demo (`demo`) y para producción. Todo está en español en el desk cuando `System Settings.language = es`.

## Presentación (estilo planilla SRI)

Los 3 reportes replican la grilla DIMM: bloques en orden del formulario,
casilleros con su descripción oficial, columnas Valor bruto / Valor neto /
Impuesto y subtotales por bloque (el total automático de Frappe está
desactivado porque sumar casilleros no tiene sentido). 103 muestra una fila
por concepto de retención (código + descripción oficial + casillero base e
impuesto); ATS muestra un renglón por documento con contraparte, base e IVA
más subtotal por sección. Etiquetas fuente: printout DIMM Res.
NAC-DGERCGC17-00000324 (`l10n_ec/sri/form104_layout.py`), Tabla 20/23 SRI
(`withholding_concepts.py`).

## 1) ATS — Anexo Transaccional Simplificado

**Qué genera:** `AT{MMAAAA}.xml` + `AT{MMAAAA}.zip` validados contra `l10n_ec/sri/xsd/ats.xsd` (compras, ventas, exportaciones, anulados). Solo entra lo **autorizado** (compras con número SRI + auth, ventas con voucher `01` autorizado, anulados autorizados-luego-void).

**Dónde generarlo:**

- **Desk (recomendado):** abrí el reporte **SRI ATS**, fijá Company/Año/Mes y apretá
  **Descargar ATS ZIP** — baja `AT{MMAAAA}.zip` (el que pide el portal SRI) y muestra
  cuántos documentos entraron por sección. El XML viaja dentro del ZIP.
- **Bench (alternativa):**
  ```bash
  bench --site demo execute "frappe.get_attr('l10n_ec.ecuador_localization.report.sri_ats.sri_ats.download_ats')('Demo Ecuador',2026,10)"
  # deja /private/files/AT102026.zip y .xml en el sitio
  ```

**Validación DIMM sin salir del desk:** el reporte muestra un indicador de estado
del validador (`Validador ats.plugin.1.19.0` en verde = al día; rojo = desactualizado
con el motivo; gris = no disponible). El botón **Validar en DIMM** corre el XML del
mes por el motor oficial del SRI (sidecar `docker_ats_validator`) y devuelve el
veredicto (`valid`/`observed`/`unavailable`), la lista de errores/advertencias y el
talón resumen como archivo. Requiere el sidecar corriendo y, opcionalmente en
`site_config.json`: `ats_validator_url` (default `http://127.0.0.1:8080`) y
`ats_validator_token`. Sin sidecar el reporte dice "no validado" — jamás verde
implícito.
  El mes demo de referencia es **10/2026** (octubre): trae 8 compras con `codSustento` mixtos (`02`/`06`), `tpIdProv 04/05`, `montoIce 2.50` en `001-001-000000015`, y tipos `01/04/05`.

- **Código:** `l10n_ec/sri/ats_collector.py` (agrega) + `l10n_ec/sri/ats_builder.py` (render + XSD) + `l10n_ec/ecuador_localization/ats_reader.py` (lee mes posteado).

**Verificación rápida del XML:** `montoIva`, `baseImpGrav` etc. deben sumar con `Form 104` (ver triangulación abajo).

## 2) Formulario 103 — Retenciones en la Fuente

**Qué hace:** agrega voucher `07` **autorizados** IR por casillero (`303/353`, `312/362`, `340/3900`...) en bloques residentes, más sección exterior por régimen (`con`/`sin`/`paraíso`) con subtotal `497/498` y total `499 = 399 + 498`. Sin filas exterior, la sección declara vacío explícito.

**Dónde abrirlo:** Desk → **Contabilidad** → **Informes** → busca **SRI Form 103** (tipo *Script Report*, `ref` Purchase Invoice).

**Filtros:** `Company` (ej. `Demo Ecuador`), `Year` (2026), `Month` (10).

**Bench (mismo resultado):**
```bash
bench --site demo execute "frappe.get_attr('l10n_ec.ecuador_localization.report.sri_form_103.sri_form_103.execute')({'company':'Demo Ecuador','year':2026,'month':10})"
```

**Demo:** el voucher `07` de `001-001-000000011` (`312` IR 2% sobre 100 → `2.00`) cae en `312/362`; está en `Rejected` demo (techo autofirmado) — para verlo en 103, ponlo transitoriamente en `Authorized` (ver triangulación).

## 2b) Retenciones: emitidas vs recibidas (no mezclar)

- **Emitidas (lado proveedor, nosotros retenemos):** vouchers `07` que
  emitimos sobre compras. Alimentan el 103 de arriba. Flujo en
  `voucher_flow.py`; nada de esta sección los lee.
- **Recibidas (lado cliente, nos retienen):** el cliente nos paga neto y
  nos entrega UN comprobante que cubre MUCHAS facturas nuestras.
  DocType `SRI Received Withholding` (cabecera del slip + tabla de
  asignaciones por factura con topes por base) enlazado al Payment Entry:
  al cobrar se valida (sin duplicidad, topes IR/IVA, mismo cliente) y se
  contabiliza un JE por factura; al cancelar el cobro se reversa. Demo:
  slip `001-002-000000201` sobre `ACC-SINV-2026-00005` (IR 20 + IVA 16)
  y `ACC-SINV-2026-00004` (IR 8). Sus JEs alimentan `609` y `received_refs`
  del 104; al ATS no entra sección de retenciones (el ATS informa
  compras/ventas, no slips).

## 3) Formulario 104 — Declaración de IVA

**Qué hace:** 128 casilleros (`401` ventas, `500` compras, `601` crédito, `609` IVA recibido, `620 = 601-602-609` etc.) con patrón **cajas vacías = 0**. Lee mayor posteado + filas de deducción IVA + JEs de liquidación (`1010501/1010502`) + `sri_received_*`.

**Dónde abrirlo:** Desk → **Contabilidad** → **Informes** → **SRI Form 104** (Script Report, `ref` Sales Invoice).

**Filtros:** `Company` / `Year` / `Month` (igual que 103).

**Bench:**
```bash
bench --site demo execute "frappe.get_attr('l10n_ec.ecuador_localization.report.sri_form_104.sri_form_104.execute')({'company':'Demo Ecuador','year':2026,'month':10})"
```

**Demo octubre:** `401=1060`, `500=330`, `609=150` (IVA recibido del JE `250`), `620` negativo es literal OCA cuando `609 > 601`.

## 4) Triangulación (evidencia de completitud, demo octubre 2026)

**Mismo mes, tres fuentes deben cerrar con granularidad entendida:**

- Ventas `401`: bruto `1075.00`, neto `1060.00`, impuesto `159.00` — la
  diferencia bruto/neto es la NC del mes (las devoluciones restan solo
  neto e impuesto, nunca bruto). Total `409`: `1675.00/1660.00/199.00`.
  Tarifa variable `410`: `400.00/400.00/32.00` (turismo 8% por decreto);
  tarifa fija 5% `425`: `160.00/160.00/8.00` (cemento). Un 5% decretado
  sería indistinguible del fijo: cae en 425 (documentado).
- Compras `500`: `350.00/330.00/49.50`; total `509`: `650.00/630.00/59.50`.
- Liquidación: factor `563 = 0.98` (fórmula literal de la plantilla:
  411+412+420+435+415+416+417+418 sobre 419), crédito `564 = 58.07`,
  causado `601 = 140.93`, retenciones recibidas `609 = 150.00` (del JE
  de liquidación), subtotal `620 = -9.07` → percepción `699 = -9.07`;
  retención `799/801 = 4.50` (fórmula `801 = 799-800-802`; 800/802 sin
  insumo, en cero); consolidado `859 = -4.57` (posición a favor, válida).
- `ATS`: 8 compras, 0 ventas, 0 exportaciones, 0 anulados (solo lo
  autorizado alimenta el ATS; las ventas demo viajan en `Rejected` por
  el techo autofirmado).
- `103` residentes: tres 07 stageados — `031`: 312/100 + 362/2.00;
  `032`: 303/1000 + 353/100.00 y 307/500 + 357/15.00; `033`: 3400/2000 +
  3900/60.00 y 332/500 (base sola). Subtotal `349/4100.00` + `399/177.00`.
- `103` exterior (tasas fundadas, régimen declarado): `034` España
  regalías 501A 10% con convenio → 410/1000 + 460/100.00; `035` USA
  servicios 501 25% sin convenio → 422/2000 + 472/500.00; `036` Panamá
  regalías 501A 37% paraíso → 431/500 + 481/185.00. Subtotal exterior
  497/3500.00 + 498/785.00; total impuesto `499 = 399 + 498 = 962.00`
  (fórmula impresa en la plantilla oficial). El exterior vive solo en
  el 103 + GL: sin sección ATS y sin tocar el 104 (las compras EXT no
  tienen plantilla IVA y sus bill_no no-SRI se excluyen del ATS).

NC `04` reporta en positivo (tipo lleva el signo), `03` solo si está autorizado, `02`/`06` sustentos ya vienen del campo `SRI Sustento Code`.

## 5) Campos que alimentan los informes

- **Compra:** `Bill No` (SRI `001-001-...`), `SRI Supplier Auth Number`, `SRI Sustento Code` (01-15, default 02), `SRI Liquidación` / `Is Return` / `SRI Supplier Debit Note` para `03/04/05`, `Item Tax Template` (15%/5%/8%/0% etc.).
- **Venta:** `SRI IR Concepto` (`303` etc.), `SRI IVA Concepto` (`1` bienes 30% / `2` servicios 70% / `3` honorarios 100%), más `Received Retención Number/Auth/Date/Key` + cobro `900` → JE.
- **Liquidación de reporte:** Desk → `SRI Form 103/104` → `Descargar` / `Imprimir`; ATS → `generate_ats_files` → `.zip`.

¿No ves el informe? `dev/demo.sh sync && bench --site demo migrate && bench --site demo clear-cache`, refresca el desk (`Ctrl+Shift+R`).

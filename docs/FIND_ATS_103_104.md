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

**Qué hace:** agrega voucher `07` **autorizados** IR por casillero (`303/353`, `312/362`, `340/3900`...). Exterior con `impuesto 9` queda **vacío explícito** (no se inventa).

**Dónde abrirlo:** Desk → **Contabilidad** → **Informes** → busca **SRI Form 103** (tipo *Script Report*, `ref` Purchase Invoice).

**Filtros:** `Company` (ej. `Demo Ecuador`), `Year` (2026), `Month` (10).

**Bench (mismo resultado):**
```bash
bench --site demo execute "frappe.get_attr('l10n_ec.ecuador_localization.report.sri_form_103.sri_form_103.execute')({'company':'Demo Ecuador','year':2026,'month':10})"
```

**Demo:** el voucher `07` de `001-001-000000011` (`312` IR 2% sobre 100 → `2.00`) cae en `312/362`; está en `Rejected` demo (techo autofirmado) — para verlo en 103, ponlo transitoriamente en `Authorized` (ver triangulación).

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

- Ventas `401`: bruto `1235.00`, neto `1220.00`, impuesto `183.00` — la
  diferencia bruto/neto es la NC del mes (las devoluciones restan solo
  neto e impuesto, nunca bruto). Total `409`: `1535.00/1520.00/203.00`.
- Compras `500`: `350.00/330.00/49.50`; total `509`: `650.00/630.00/59.50`.
- Liquidación: crédito aplicable `564 = 47.76`, causado `601 = 155.24`,
  retenciones recibidas `609 = 150.00` (del JE de liquidación),
  subtotal `620` + presuntivo → percepción `699 = 5.24`; retención
  `799/801 = 4.50`; consolidado `859 = 9.74`.
- `ATS`: 8 compras, 0 ventas, 0 exportaciones, 0 anulados (solo lo
  autorizado alimenta el ATS; las ventas demo viajan en `Rejected` por
  el techo autofirmado).
- `103`: tres 07 stageados como demo-data — `031`: 312/100 + 362/2.00;
  `032`: 303/1000 + 353/100.00 y 307/500 + 357/15.00; `033`: 3400/2000 +
  3900/60.00 y 332/500 (base sola). Total residentes: base `4100.00`,
  retenido `177.00`; exterior explícitamente vacío.

NC `04` reporta en positivo (tipo lleva el signo), `03` solo si está autorizado, `02`/`06` sustentos ya vienen del campo `SRI Sustento Code`.

## 5) Campos que alimentan los informes

- **Compra:** `Bill No` (SRI `001-001-...`), `SRI Supplier Auth Number`, `SRI Sustento Code` (01-15, default 02), `SRI Liquidación` / `Is Return` / `SRI Supplier Debit Note` para `03/04/05`, `Item Tax Template` (15%/5%/8%/0% etc.).
- **Venta:** `SRI IR Concepto` (`303` etc.), `SRI IVA Concepto` (`1` bienes 30% / `2` servicios 70% / `3` honorarios 100%), más `Received Retención Number/Auth/Date/Key` + cobro `900` → JE.
- **Liquidación de reporte:** Desk → `SRI Form 103/104` → `Descargar` / `Imprimir`; ATS → `generate_ats_files` → `.zip`.

¿No ves el informe? `dev/demo.sh sync && bench --site demo migrate && bench --site demo clear-cache`, refresca el desk (`Ctrl+Shift+R`).

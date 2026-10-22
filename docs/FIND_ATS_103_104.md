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

- **Bench (recomendado para demo):**
  ```bash
  bench --site demo execute "frappe.get_attr('l10n_ec.ecuador_localization.ats_reader.generate_ats_files')('Demo Ecuador', 2026, 10)"
  # guarda en /tmp/AT102026.xml y .zip — cópialo donde lo entrega el portal SRI
  ```
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

## 4) Triangulación (evidencia de completitud)

**Mismo mes, tres fuentes deben cerrar con granularidad entendida:**

- `ATS montoIva` (ej. `43.00`) ↔ `Form 104` bases/montos + `GL 1010504`
- `JE 250 (1010501 150 + 1010502 100)` ↔ `104 casillero 609` + `GL`
- `Voucher 07 (100/2.00)` ↔ `103 casillero 312/362`

NC `04` reporta en positivo (tipo lleva el signo), `03` solo si está autorizado, `02`/`06` sustentos ya vienen del campo `SRI Sustento Code`.

## 5) Campos que alimentan los informes

- **Compra:** `Bill No` (SRI `001-001-...`), `SRI Supplier Auth Number`, `SRI Sustento Code` (01-15, default 02), `SRI Liquidación` / `Is Return` / `SRI Supplier Debit Note` para `03/04/05`, `Item Tax Template` (15%/5%/8%/0% etc.).
- **Venta:** `SRI IR Concepto` (`303` etc.), `SRI IVA Concepto` (`1` bienes 30% / `2` servicios 70% / `3` honorarios 100%), más `Received Retención Number/Auth/Date/Key` + cobro `900` → JE.
- **Liquidación de reporte:** Desk → `SRI Form 103/104` → `Descargar` / `Imprimir`; ATS → `generate_ats_files` → `.zip`.

¿No ves el informe? `dev/demo.sh sync && bench --site demo migrate && bench --site demo clear-cache`, refresca el desk (`Ctrl+Shift+R`).

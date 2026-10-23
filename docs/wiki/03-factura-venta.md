# 3. Factura de venta — sección Facturación SRI

La factura de venta (`ACC-SINV-…`) colapsa lo tributario en la sección
**Facturación SRI**: conceptos de retención, comprobante de retención
recibido del cliente y punto de emisión.

![Sección Facturación SRI expandida](img/04-si-facturacion-sri.png)

## Campos

- **Concepto IR SRI** (`303`, `307`, `312`…) — concepto de retención de
  Renta que nos aplica el cliente; validado contra la tabla de 176
  conceptos. Alimenta el asiento de liquidación de retenciones recibidas.
- **Concepto IVA SRI** (`1` bienes 30%, `2` servicios 70%, `3` honorarios
  100%…) — Tabla 23 de retenciones de IVA.
- **Número / Autorización / Clave de acceso de retención recibida** —
  el comprobante de retención (06/07) que emite el cliente: número
  `001-001-…`, autorización del SRI y clave de 49 dígitos. Alimenta ATS
  (crédito) y Formulario 103.
- **Fecha de retención recibida** — fecha de emisión del comprobante
  del cliente.

En la captura, el cliente retuvo IR concepto `303` e IVA concepto `3`
(honorarios 100%) con comprobante `001-001-000000101`.

## Dónde sigue

- El XML que generamos nosotros por esta venta: [página 4](04-comprobantes.md).
- Dónde aparece el crédito de esta retención: [página 5](05-reportes.md).

# Wiki `l10n_ec` — Localización Ecuatoriana para ERPNext v16

Documentación funcional con capturas del sitio demo (`Demo Ecuador`).
Cada página explica una funcionalidad: dónde está en el Desk, qué datos
pide el SRI y cómo se ve en la demo.

## Índice

1. [Espacio de trabajo Ecuador](01-workspace.md) — sidebar, catálogos y reportes.
2. [Factura de compra](02-factura-compra.md) — sustento Tabla 5, liquidación / nota de débito del proveedor, grilla de impuestos, retenciones asumidas, importación XML / por clave.
3. [Factura de venta](03-factura-venta.md) — sección Facturación SRI, conceptos IR/IVA, retención recibida del cliente (manual + importación XML).
4. [Comprobantes electrónicos](04-comprobantes.md) — lista, factura 01 generada, retención 07 autorizada (régimen exterior).
5. [Reportes SRI: ATS, 103 y 104](05-reportes.md) — Anexo Transaccional, retenciones en la fuente e IVA mensual (incl. importaciones).
6. [Importaciones: del exterior al recosteo](06-importaciones.md) — factura `990…` sin IVA + settlement DAI + LCV nativo.
7. [Reembolsos: liquidación de compras por reembolso](07-reembolsos.md) — mandante e intermediario, bloque `<reembolsos>` y ATS.

## Cómo reproducir estas capturas

```bash
dev/demo.sh up      # infra (MariaDB + Redis en Docker)
dev/demo.sh reset   # sitio `demo` idempotente con datos de ejemplo
dev/demo.sh serve   # http://demo:8000 (usuario Administrator)
```

Ver [LOCAL_DEMO.md](../LOCAL_DEMO.md) para el detalle.

## Honestidad de la demo

- La firma usa un certificado `.p12` de prueba autofirmado: el SRI real
  respondería `FIRMA INVALIDA`. Los comprobantes quedan en `Generado` /
  `Rechazado`; los `Autorizado` visibles son estados representados
  (documentado también en [STATUS.md](../STATUS.md)).
- Autorizaciones de proveedor `1234567890` y números `001-001-…` son
  marcadores de ejemplo, no documentos reales.
- Ventas en ATS sale en `0` porque la demo no tiene comprobantes de venta
  autorizados (techo autofirmado); el 104 sí consolida las ventas.

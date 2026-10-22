# Roadmap independiente: POS y E-commerce (facturación electrónica)

Evaluación contra ERPNext v16 real (`~/frappe-bench-v16/apps/erpnext`) y los
hooks actuales de `l10n_ec`. Este roadmap es independiente del core de
facturación: nada aquí cambia GL, ATS ni 103/104; propone dos módulos
activables por separado.

## 1. Punto de partida (lo que ya cubre el core)

| Flujo | Qué se ejecuta hoy | Efecto SRI |
|---|---|---|
| Sales Invoice `before_save` | `validate_sri_invoice` → tope consumidor final USD 50 (`validation.validate_final_consumer_amount`) | Factura a CF > 50 exige identificación |
| Sales Invoice `validate` | `sync_tax_row_descriptions` | Solo presentación |
| Customer/Supplier `validate` | `validate_sri_identification` (solo si el doc trae `sri_identification_type`; exige `tax_id` válido + bloquea CF duplicado) | Contactos identificados quedan validados los cree quien los cree |
| Payment Entry `on_submit` | liquidación de retenciones recibidas | Cobra lo retenido |

## 2. POS (siempre presente con ERPNext: `point_of_sale` + `POS Invoice`)

### Cómo fluye en el core (verificado en fuentes)

1. Cada ticket es un `POS Invoice` individual (perfil `POS Profile`, cliente
   habitualmente genérico).
2. Al cierre (`POS Closing Entry`) los tickets se fusionan en **una** Sales
   Invoice consolidada por cliente (`POS Invoice Merge Log`, exige mismo
   `customer`; el doc lleva `is_pos=1, is_consolidated=1`).

### Brechas contra reglas SRI

- **G1 — el tope CF 50 se evalúa en el lugar equivocado.** Nuestros hooks
  corren sobre la Sales Invoice **consolidada** (suma de N tickets): un
  cierre con 10 tickets CF de 30 bloquea como si fuera una venta de 300,
  y ningún ticket individual se valida jamás.
- **G2 — emisión sin modelo definido.** ¿Un comprobante por ticket o uno
  por consolidado? El SRI factura por transacción; el consolidado es un
  artefacto contable de ERPNext. Sin decisión, no hay emisión correcta.
- **G3 — medio de pago.** El consolidado mezcla pagos de N tickets; la
  Tabla 24 (`formaPago`) del XML debe salir del ticket, no del consolidado.

### Módulo propuesto: `POS electrónico` (flag independiente)

- Hooks propios sobre `POS Invoice` (`validate`/`before_submit`): tope CF
  50 **por ticket** + arrastre de `sri_*` (identificación cuando la hay).
- Guardia en `POS Invoice Merge Log`: bloquea fusionar tickets que
  mezclen CF genérico con identificado, y tickets sin validación POS.
- Emisión: por defecto **un voucher por Sales Invoice consolidada solo si
  todos sus tickets comparten identificación**; caso contrario, decantado
  en decisión abierta abajo. Nunca emitir por ticket sin que el usuario lo
  pida: multiplica folios y confunde el ATS.
- Todo tras `sri_pos_enabled` (nuevo settings, default apagado).

## 3. E-commerce (app **opcional** `frappe/webshop`, no existe en el core v16)

Verificado: `erpnext/shopping_cart` es un stub y `modules.txt` no lista
tienda. La tienda real es app aparte que puede no estar instalada.

### Brechas

- **G4 — contacto invitado.** El checkout crea Customer/Contacto web sin
  `sri_identification_type`: nuestros `party_hooks` lo dejan pasar (solo
  actúan si el tipo viene seteado) y el pedido nace sin identidad fiscal.
- **G5 — el pedido no es factura.** Webshop emite Sales Order primero;
  nuestros hooks viven en Sales Invoice. La validación llega tarde (al
  facturar, con el cliente ya creado mal).
- **G6 — dependencia opcional.** Nada de `l10n_ec` puede importar `webshop`
  a nivel módulo: si no está instalada, el sitio no debe romperse.

### Módulo propuesto: `E-commerce electrónico` (flag independiente)

- Validación de contacto **en el checkout** (o en `Customer.validate` vía
  hook ya existente, extendido a exigir identificación EC cuando la
  compañía del carrito es ecuatoriana y el monto supera el tope CF):
  cédula/RUC/pasaporte con dígito verificador antes de pagar.
- Hooks sobre Sales Order (guardados: solo si el doctype existe) que
  anticipan el tope CF para fallar antes del pago, no en la factura.
- Todo tras `sri_ecommerce_enabled` (default apagado) + guards
  `frappe.db.exists("DocType", ...)` en cada hook.

## 4. Modelo de activación (no existe `auto_install` en Frappe)

A diferencia de Odoo, Frappe no tiene auto-instalación por dependencia.
El patrón es:

1. Un `SRI Settings` (o campos en Company) con un checkbox por módulo,
   default apagado: `sri_pos_enabled`, `sri_ecommerce_enabled`.
2. Cada hook nuevo empieza con early-return si su flag está apagado o su
   doctype/app no existe. El core actual no se toca.
3. La emisión de vouchers reutiliza `voucher_flow` tal cual (mismo
   pipeline, mismos estados, mismo ATS): los módulos solo aportan
   validación previa y datos, jamás otro motor de emisión.

## 5. Fases

- **Fase P0 — Settings + guards** (base de ambos): settings con flags,
  util `sri_module_enabled(name)`, tests Ring-1 de guards.
- **Fase P1 — POS**: ✅ implementado (R1+R2). Tope por ticket en
  `POS Invoice.validate` + excepción de consolidado en
  `validate_sri_invoice` (verifica cada ticket vía `consolidated_invoice`,
  no la suma). Probado en vivo: ticket CF 51 bloquea, cierre 2×40 CF
  consolida en 80.00 sin bloquear. Pendiente de P1: G3 (formaPago del
  ticket) y guardia explícita de mezcla en el merge.
- **Fase P2 — E-commerce**: G4+G5 (contacto validado pre-pago, tope
  anticipado en Sales Order). Criterio: checkout invitado > 50 sin
  cédula válida no llega a pagar; con cédula válida fluye hasta SI.
- **Fase P3 — Emisión POS**: solo tras decidir P0-abajo; reutiliza
  `create_and_process` sin cambios.

## 6. Decisiones que te pido antes de implementar

- **D1 (bloqueante P3): ¿un voucher por ticket o por consolidado?**
  Recomiendo consolidado-homogéneo (sección 2); por ticket solo si tu
  contador lo exige.
- **D2: ¿el tope CF en e-commerce bloquea el pago o solo advierte?**
  Recomiendo bloquear (un pedido impagable después es peor).
- **D3: ¿Webshop se instala en el demo?** Sin la app no hay cómo probar
  P2 en bench; propongo sumarla al `dev/demo.sh reset` solo cuando
  arranquemos P2.

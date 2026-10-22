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

## 3. E-commerce (app **opcional** `frappe/webshop`, no instalada en bench)

Verificado contra `frappe/webshop` (clon 2026-10-22): `erpnext/shopping_cart`
es un stub; la tienda vive en la app aparte.

### Respuesta multi-shop: un shop por site

`Webshop Settings` es **Single** con una sola `company`: no hay
multi-shop nativo. Multi-tienda real = multi-site (cada site, su settings
y su punto) o customización fuera de este roadmap. Diseño para un shop:

### Flujo verificado (`shopping_cart/cart.py`)

Carrito (`Quotation` tipo Shopping Cart, compañía del settings) →
`place_order()` → Quotation enviada + `Sales Order` enviada automáticamente.
`update_party` crea el Customer con solo nombre (persona/empresa): **sin
cédula, sin validación** — ese es el hueco fiscal exacto.

### Brechas

- **G4 — contacto invitado.** Sin `sri_identification_type`, nuestros
  `party_hooks` lo dejan pasar y el pedido nace sin identidad fiscal.
- **G5 — el pedido no es factura.** La validación en Sales Invoice llega
  tarde (al facturar, con el cliente ya creado mal y el pago hecho).
- **G6 — dependencia opcional.** Nada de `l10n_ec` puede importar `webshop`
  a nivel módulo: si no está instalada, el sitio no debe romperse.

### Diseño: el shop es una caja lógica (mismo modelo que POS-A)

- **Mapeo**: Custom Field `sri_emission_point` (Link) en `Webshop
  Settings` —creación guardada (solo si el doctype existe)—. Un shop, un
  punto, igual que un perfil, un punto. El dato vive en el portal porque
  el settings es lo que el theme ya lee (compañía, precios, checkout).
- **Herencia**: `Quotation` (carrito) → `Sales Order` → `Sales Invoice`
  arrastran `sri_emission_point` (custom fields en doctypes core, siempre
  seguros). El hook de Sales Order lo resuelve del settings cuando el
  origen es tienda; la factura lo hereda y el voucher emite desde ahí.
- **Canal**: nuevo check `shop_only` en el punto (mismo patrón que
  `pos_only`, sin migrar nada): venta tienda exige punto shop-only,
  escritorio y POS lo rechazan. Streams separados por canal, como cajas.
- **Contacto pre-pago**: hook en Sales Order con marca de origen tienda
  (a confirmar en implementación: el marcador exacto que deja `place_order`)
  exige identificación EC válida si el total supera el tope CF — falla
  antes del pago, no en la factura. Más API whitelisted
  `validate_shopper_id` para que el theme del checkout valide en vivo
  (el campo en el template lo pone webshop; nosotros exponemos la regla).
- **Theme**: confirmación de pedido muestra identidad fiscal del shop
  (RUC + sucursal de Company + punto) con campos existentes; sin
  sobreescribir templates de webshop desde nuestra app.
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

- **D1 (resuelto): híbrido.** Consolidada identificada o CF ≤ 50 → un
  voucher único. Consolidada CF > 50 → un voucher 01 por ticket
  (`create_and_process_consolidated`), todos referenciados a la SI para
  que ATS agregue cada cuerpo y el 104 siga leyendo el mayor. Regla de
  origen: un solo voucher CF > 50 falla fuerte en creación (el SRI lo
  rechazaría igual). Secuenciales: uno por ticket del punto de su caja,
  en orden; suma de XMLs = neto de la SI o falla.
- **D2: ¿el tope CF en e-commerce bloquea el pago o solo advierte?**
  Recomiendo bloquear (un pedido impagable después es peor).
- **D3: ¿Webshop se instala en el demo?** Sin la app no hay cómo probar
  P2 en bench; propongo sumarla al `dev/demo.sh reset` solo cuando
  arranquemos P2.

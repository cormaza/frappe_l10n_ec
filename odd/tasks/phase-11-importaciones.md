# Phase 11 — Liquidación de importación + recosteo (plan UX acordado)

Ecuadorian import flow: exterior purchase → cost accumulation (FOB/freight/
insurance) → tax settlement (AD VALOREM, FODINFA, IVA per LRTI Art. 59) →
fiscal reports + landed-cost revaluation via native ERPNext LCV.
Decisions: DAI file import primary, manual entry fallback; phase 1 covers
settlement + recosteo together.

## Specs

- S1: "este proceso es una compra al exterior, que necesita liquidarse para
  pagar los impuestos que corresponden, fodinfa, iva, ad valorem".
- S2: "ir recopilando gastos/costos que tiene que ver con el flete, el
  seguro, el fob, de tal manera que esto se acumule para aplicar la
  liquidacion".
- S3: "esta liquidacion que computa iva para ser integrado en los reportes
  fiscales, los valores de compras se van a los casilleros correspondientes,
  asi como el iva pagado".
- S4: "hacer un documento de liquidacion, para asociar documentos (ordenes
  de compras), recepciones de inventario, facturas etc".
- S5: "diseñemos un plan de ux que permita llegar a la liquidacion de
  impuestos, y tambien el recosteo (landed cost se llama en odoo)".
- S6: DAI input dual — file import (ECUAPASS XML/CSV) primary, manual entry
  fallback. Rates (AD VALOREM %, FODINFA %) are inputs from the DAI/tariff,
  never hardcoded; the app recomputes arithmetic fail-loud.
- S7: Recosteo via native ERPNext v16 Landed Cost Voucher (no custom
  proration): settlement prefills LCV against the goods receipt; LCV
  reposts valuation (SLE/GLE). Early-known charges may use purchase-tax
  Valuation / Total-and-Valuation categories instead.
- S8: Gate: seeded month must stay DIMM `valid` with unchanged compras
  count (CI `validate_month` gate, `.github/workflows/ci.yml`).

## Tasks

- T1 (S1, pure `l10n_ec/sri/`, Ring-1): CIF + tribute arithmetic
  (CIF→AD VALOREM→FODINFA→IVA Art. 59), fail-loud. Route: unit. Commit: fdeb4b9
- T2 (S2/S4, DocType layer): `SRI Import Settlement` DocType + links to
  PO/PR/PI sources. Route: doctype+controller. Commit: cf90182
- T3 (S6, settlement): DAI file import primary + manual fallback with
  arithmetic cross-check. Route: controller. Commit: b97b906
- T4 (S7, settlement→LCV): prefill + submit native LCV from settlement.
  Route: integration. Commit: 80d5e02
- T5 (S3, reports): dedicated 104 import boxes + ATS import marking.
  Route: reports. Commit: c670ad1
- T5b (S3, reports): exterior purchases report in ATS (no distinct
  sustento; 15-digit split; 103-only withholdings). DIMM-proven.
  Route: collector+reader. Commit: 598f9ca
- T6 (S8, demo/CI): seed import case + keep DIMM gate green. Route: demo.
  Commit: 282c41b
- T6b (S3 review catch): forbid local VAT on exterior purchases (guard +
  hook + seed fix + wiki). Route: validation. Commit: 0964d48

## Log

- L1 (original request, verbatim): "bien con el tema de importaciones, este
  tema lo explico pero necesito que lo valides con documentacion oficial,
  este proceso es una compra al exterior, que necesita liquidarse para pagar
  los impuestos que corresponden, fodinfa, iva, ad valorem, la idea es ir
  recopilando gastos/costos que tiene que ver con el flete, el seguro, el
  fob, de tal manera que esto se acumule para aplicar la liquidacion, esta
  liquidacion que computa iva para ser integrado en los reportes fiscales,
  los valores de compras se van a los casilleros correspondientes, asi como
  el iva pagado, creo que valdra la pena hacer un documento de liquidacion,
  para asociar documentos(ordenes de compras), recepciones de inventario,
  facturas etc, diseñemos un plan de ux que permita llegar a la liquidacion
  de impuestos, y tambien el recosteo (landed cost se llama en odoo),
  quisiera ver que opciones tenemos en erpnext para este recosteo si tiene
  algo integrado".
- L2 (validation): LRTI Art. 59 base = valor en aduana + impuestos/aranceles/
  tasas/derechos/recargos (vigente.ec + sri.gob.ec/IVA); COPCI import-consumo
  regime + DAI (SENAE); 104 guide 605/615 incl. importaciones. FODINFA 0.5 %
  numeric rate NOT confirmed from official source → S6 (rates are inputs).
  Gap: 104 dedicated import boxes stay zero today (form104.py) — T5.
- L3 (ERPNext v16, bench sources): native Landed Cost Voucher against
  PR / PI-with-update-stock, distribute Qty/Amount/Manual, vendor-invoice
  link, submit reposts SLE/GLE (`landed_cost_voucher.py`); early charges via
  purchase-tax Valuation categories (docs.frappe.io). → S7.
- L4 (decisions): DAI "2 como primario y 1 como capacidad manual"; scope
  "Liquidación + recosteo juntos" (phase 1 = T1–T6).
- L5 (T5b evidence): no distinct SRI sustento for imports (Tabla 5 is
  nature-based, verified vs Ficha Técnica Tabla 5 + XSD); XSD compras has
  no import marker except optional tipoProv (omitted, DIMM-valid without
  it). Sidecar probe 4/4 valid incl. plain exterior 01. Seeded month
  validates `valid` with 14 compras (11+3 exterior). Fresh seed without a
  worker piles ~650 jobs → QueueOverloaded; CI now drains first.
- L6 (user review catch): exterior invoices must not carry local VAT -
  the import credit is born by the DAI settlement, never by the foreign
  supplier invoice. Blindaje: `validate_no_local_vat` (pure) + Purchase
  Invoice validate hook (bench), fail-loud naming the template; seed
  import case fixed accordingly (no template on the exterior goods PI).
  104 import boxes read 0 until the DAI tax document exists (T7).
- L7 (arancel catalog evaluation, 2026-10-27): NO national catalog
  vendored. DAI stays the authority; rates always travel in with the
  declaration. Reopen only with versioned demand (see closing message).

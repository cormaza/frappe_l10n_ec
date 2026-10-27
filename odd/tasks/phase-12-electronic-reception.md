# Phase 12 — Electronic reception (XML upload / fetch by clave)

Receive supplier e-invoices as XML (file upload, primary) or fetched from
SRI by access key (secondary, time-boxed), parsed into draft Purchase
Invoices for review. Evaluation only; implementation not yet authorized.

## Specs

- S1: "poder importar los archivos xml de la facturación electronica".
- S2: "con un # de clave de acceso poder en el endpoint del SRI obtener
  el xml (esto se permite por una ventana de tiempo que habria que
  validar, segun mi entender es 30 dias, pero las guias que he visto
  indican menos tiempo)".
- S3: "evaluemos cual es el mejor approach para este tema".
- S4 (customer mirror): importar comprobantes de retención de clientes
  (XML 07 donde somos sujeto retenido), no solo facturas de proveedores.

## Tasks

- T1 (S1, pure `l10n_ec/sri/`, Ring-1): XML→draft-PI mapper core
  (emisor + per-line taxes parse, template-by-rate resolution,
  fail-loud mapping). Route: unit. Commit: -
- T2 (S1, desk): bench glue + upload button (whitelisted file intake,
  supplier resolve-or-fail, duplicate guard, template match by rate on
  debit-side accounts, draft PI). Route: integration. Commit: 997d132
- T3 (S2, desk+SOAP): fetch by clave through the SRI endpoint reusing
  the T1 core (extract `comprobante`, ~10-day practical window as UX
  note, never promised). Route: integration. Commit: d37c221
- T4 (S4, desk): customer withholding import (07 XML where we are the
  subject). Reuses A1 patterns + B fetch; target is the existing
  `SRI Received Withholding` batch + auto-allocation. Route:
  integration. Commit: 77a684f

## Findings (verified, with sources)

- F1: SRI SOAP `autorizacionComprobante({claveAccesoComprobante})`
  exists; our `soap_client.py` already wraps it
  (`request_authorization`) and our offline WSDL is vendored.
  The response `autorizacion` carries the full authorized XML in the
  `comprobante` string field (WSDL line 40); Ficha Técnica Esquema
  Offline §5.11 confirms "el WEB Service de autorización devuelve el
  XML autorizado". Gap: `process_authorization_response` extracts
  estado/numeroAutorizacion/fecha but NOT the `comprobante` XML yet.
- F2: No official availability window. Field evidence (trescloud,
  Ecuadorian e-invoicing practitioner, 2024-02): the webservice answers
  for ~10 days after authorization, sometimes less; no SRI communiqué,
  no SLA. The 30-day assumption is optimistic: design for ~10 days,
  never promise more.
- F3: Offline scheme rule: the emitter must send the XML to SRI within
  24h, and offline clave == numeroAutorizacion (Ficha §5.9).
- F4: Authenticated "consulta de comprobantes recibidos" is a WEB
  portal procedure (gob.ec SRI-014-06-01, RUC + password). No API.
  Scraping it means credentials in our code: out.
- F5: Our `voucher_data.py` already parses factura / liquidacion /
  nota crédito / nota débito / retención / guía + reembolsos — the same
  XSDs received docs use. Our XSDs: factura V1.1.0, retencion V2.0.0,
  etc. Parsers are tag-based (lxml), likely version-tolerant, to be
  pinned against real samples at implementation.
- F6: Mapping crux (same for both paths): supplier = emisor RUC +
  razon social (lookup, else create as draft data); bill_no =
  estab-punto-secuencial; auth number/date; tax lines -> ERPNext Item
  Tax Templates are company-named (map by rate, fail loud when absent);
  sustento is NOT in the XML (user sets it, fail loud if missing);
  XML line descriptions are not Item Codes (needs a default service
  item or per-line mapping decision).

## Options

- A. Manual XML upload → parse (F5) → draft PI for review/post.
  Always available (email XMLs never expire), zero SRI dependency,
  no window. Covers any age.
- B. Fetch by clave (SOAP, existing client + extract `comprobante`).
  Same draft PI + authenticity proof. Bounded by ~10-day practical
  window (F2), no SLA; SRI downtime risk.
- C. Shared core first: XML→draft-PI mapper (mapping table, T6b-style
  blindajes), with A and B as thin front-ends.
- D. Batch (ZIP / mailbox ingestion): later, same core.
- E. Portal scraping: OUT (fragile, credentials).

## Recommendation

A first (upload + parse + draft), B second (fetch reusing A's core +
the existing SOAP call). Shared mapper owns: supplier resolve/create
as draft data, SRI number split (reuse T5b helpers), tax-rate to
template mapping (fail loud), mandatory sustento, exterior XMLs stay
out (foreign suppliers issue no SRI XML; current manual path stands).
The clave window is a UX note ("SRI usually answers ~10 days"),
never a promise.

## Log

- L1 (original request, verbatim): "bien, cerremos este tema, ahora hay
  otro tema grande que quisiera poder implementar, es poder importar los
  archivos xml de la facturación electronica, o con un # de clave de
  acceso poder en el endpoint del SRI permitir obtener el xml(esto se
  permite por una ventana de tiempo que habria que validar, segun mi
  entender es 30 dias, pero las guias que he visto indican menos tiempo),
  evaluemos cual es el mejor approach para este tema".
- L2 (evaluation 2026-10-28): F1–F6 above. Recommendation: A then B
  over shared core C. Reopen E never (house rule on scraping +
  credentials).
- L3 (customer mirror, user question): retenciones de clientes (07 donde
  somos sujeto retenido) were NOT in the first scope; evaluated now.
  Parser `_parse_retencion`+`_parse_sustento` already exist (subject,
  fiscal period, per-doc numbers/auths, concepto base/rate/value); missing
  only emisor+clave (same additive extension as facturas). Target is the
  EXISTING `SRI Received Withholding` batch + allocations + stamp +
  settlement JE flow (nothing new downstream): mapper resolves customer
  by emisor RUC (fail loud: create first), auto-links SIs on exact
  (customer, number) match else leaves manual allocation, splits IR/IVA
  per impuesto with official-rate validation, rejects duplicates by
  (customer, number+auth). No template problem (07s carry conceptos,
  not templates), no sustento validation our-side (informational).
  Offline auth number = clave; online-scheme auth dates come from the B
  path. Added as T4 (after B, reuses both).
- L4 (user refinement, reception): unknown supplier is auto-created
  (clearly-named 'Imported Suppliers' group, type from ID length,
  name-clash guard, review note) instead of forcing a manual
  round-trip; the no-template error now lists available company
  templates with rates. Live proof on fresh seeded site for both.

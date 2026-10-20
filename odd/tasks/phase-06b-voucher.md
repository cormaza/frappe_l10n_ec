# Phase 6B: SRI Electronic Voucher DocType & Background Worker (Ring 2)

Implements roadmap Phase 6B on `version-16` with direct commits (no PR).

## Specs

- S1: Roadmap Phase 6B scope, quoted verbatim: "`SRI Electronic Voucher` DocType tracking the state machine (`Generated` → `Signed` → `Received` → `Authorized` / `Returned` / `Rejected`) for ERPNext `Sales Invoice` (regular, return/credit note, debit note) and `Purchase Invoice` (when `SRI Document Type == 03` Purchase Liquidation).", "Asynchronous submission and authorization polling via `frappe.enqueue(..., enqueue_after_commit=True)`."
- S2: Exit criteria (mock-first, OCA pattern): full pipeline end-to-end with mocked SRI responses green in both rings (Authorized, Returned, and Rejected paths); re-runs and double submits idempotent. A live SRI-pruebas run is an optional follow-up requiring an SRI-issued test certificate.
- S3: Locked readings: manual trigger via whitelisted methods (no auto-submit on invoice `on_submit`); worker functions importable and runnable synchronously for testing, with thin `frappe.enqueue` wiring for production; sequences allocated from `SRI Emission Point` records; tax mapping by template title — VAT `15%`→(`2`,`4`), `5%`→(`2`,`8`), `0%`→(`2`,`0`), Exempt→(`2`,`7`), No-object→(`2`,`6`) (per SRI Ficha Técnica v2.28 via versioned catalogs); ICE/IRBPNR auto-mapping explicitly out of scope (clear error, manual handling); `Authorized` proof requires an SRI-issued test certificate (self-signed only proves up to SRI response).
- S4: User decision (mock-first, OCA pattern): generic self-signed p12 (`test_helpers.generate_test_p12`) plus mocked SRI SOAP responses built with real zeep factories from the bundled WSDLs (established `test_sri_soap.py` pattern) — deterministic, no network, valid in both rings. No credential needed.
- S4: XML builders (6A), signer, access keys, SOAP client, catalogs, emission points, and Company signature fields are reused as-is.

## Tasks

- T1 (S1): `SRI Electronic Voucher` DocType + state machine + transition guards + Ring-1 tests. Route: inline. Commit: c5ee48d
- T2 (S1): Submit/poll pipeline + `tax_codes` mapping + enqueue wiring + mocked end-to-end tests (both rings). Route: inline. Commit: c5ee48d
- T3 (S2): Live proof against SRI pruebas + commit and push to `version-16`. Route: inline. Commit: -
- T3 (S2): Live proof against SRI pruebas + commit and push to `version-16`. Route: inline. Commit: -

## Log

- L1: "bien vamos con 6b"
- L2: Live proof (demo site, SRI pruebas, self-signed cert): full pipeline works — generate (XSD-gated) → sign → RECIBIDA → NO AUTORIZADO/Rejected with `FIRMA INVALIDA` (untrusted chain, as predicted). Bugs found live and fixed: raw XML in DocType fields gets bleach-sanitized on save (XML now lives in File attachments); XML `<ambiente>` needs `1`/`2` (endpoint selector is separate); access-key date must equal invoice posting_date (ERPNext normalizes posting dates to today unless `set_posting_time` is set); Item Tax Template names gain one company suffix at insert (pass base titles).

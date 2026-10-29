# Multi-Currency Reporting Hardening (base_ normalization)

## Specs
- S1: "no me interesa quitar su capacidad al erp de ser multi-moneda, lo que quiero es validar que la data que llega e los flujos de reportes sobre todo sean en la moneda correctamente"
- S2: Preserve ERP multi-currency (transaction currency untouched); every SRI fiscal boundary (emission XML, ATS, Form 104, Form 103 via XML, settlements, import CIF) aggregates in company currency (`base_` fields) which for EC companies is USD/DOLAR.
- S3: Fail loud when `base_` inputs are missing or `conversion_rate` is unusable instead of silently reporting transaction amounts as USD.
- S4: Original user intent: "quiero que evalues si hay hardening de multi-moneda para esta localizacion en sus flujos implementados, se que hay multi-compañía, pero quiero dejarlo blindado" + "adelante".

## Tasks
- T1 (S1,S2,S3): ATS reader + `base_lines` normalize to `base_` (company currency) with currency audit; Ring-1 tests. Route: inline.
- T2 (S1,S2,S3): Form 104 ledger normalize to `base_` (invoice taxes, IVA deduction rows, settlements). Route: inline.
- T3 (S1,S2,S3): Emission (`_invoice_dict`, withholding docs, `synthesize_iva_row`) emits `base_` as DOLAR. Route: inline.
- T4 (S1,S2,S3): Received settlement + thresholds use `base_` (SI `base_net_total`/`base_grand_total`). Route: inline.
- T5 (S1,S2,S3): Import settlement `CIF` sums `base_net_total` per leg (multi-currency legs convert, no single-transaction-currency gate). Route: inline.
- T6 (S1,S2): Docs + locale markers for new user-facing strings; full Ring-1 suite + pre-commit green. Route: inline.

## Log
- L1: "quiero que evalues si hay hardening de multi-moneda para esta localizacion en sus flujos implementados, se que hay multi-compañía, pero quiero dejarlo blindado"
- L2: "no me interesa quitar su capacidad al erp de ser multi-moneda, lo que quiero es validar que la data que llega e los flujos de reportes sobre todo sean en la moneda correctamente"
- L3: "adelante"

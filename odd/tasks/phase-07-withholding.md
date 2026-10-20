# Phase 7: Electronic Withholdings (`Comprobante de Retención` v2.0.0)

Implements roadmap Phase 7 on `version-16` with direct commits (no PR).

## Specs

- S1: Roadmap Phase 7 scope, quoted verbatim: "`SRI Withholding` DocType (or extension on `Purchase Invoice` / `Payment Entry`) generating `ComprobanteRetencion_V2.0.0.xsd` (`codDoc=07`).", "Supports multi-tax-support (`docsSustento` / `codSustento`) grouping for Income Tax (`impuesto codigo=1`) and VAT (`impuesto codigo=2`) withholdings on purchase invoices and credit card settlements (`Liquidación de Tarjeta de Crédito`).", "Automatic GL entry posting against withholding payable/receivable accounts."
- S2: Exit criteria (derived): one withholding voucher reaches SRI Received or better from the demo site with correct sustento grouping; native calculation untouched.
- S3: Locked readings: native `Tax Withholding Category`/`PaymentTaxWithholding` own ALL calculation, thresholds, GL posting, and reversal (proven by spike — card settlements included); this phase builds only the SRI mapping (`docsSustento` grouping), the `retencion` XML builder + XSD, `codDoc=07` voucher integration (6B flow reuse), EC category seeds from `WITHHOLDING_RATES`, and RIDE/email reuse (6C); no new state machine, no custom accounting.

## Tasks

- T1 (S1): Retención XSD + XML builder + Ring-1 tests. Route: inline. Commit: 0b7dcc8
- T2 (S1): Native-entry→SRI mapping (sustento grouping) + tests. Route: inline. Commit: 0b7dcc8
- T3 (S1): Voucher `07` integration + EC category seeds + live proof. Route: inline. Commit: -
- T4 (S2): Verify, commit and push to `version-16`. Route: inline. Commit: -

## Log

- L1: "dale, vamos con fase 7"

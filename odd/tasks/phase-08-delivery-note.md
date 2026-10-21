# Phase 8 — Electronic Delivery Note (`Guía de Remisión`, `codDoc=06`)

## Specs
- S1: EDI on ERPNext `Delivery Note` (`GuiaRemision_V1.1.0.xsd`): `build_guia_xml` with carrier (`Transportista`) RUC/identification, license plate (`placa`), transport start/end dates, origin/destination addresses, and linked `Sales Invoice` / `Stock Entry` support documents (`destinatarios`).
- S2: Verify, commit, and push to `version-16` with dual-ring tests and live SRI proof.

## Tasks
- T1 (S1): Guía XSD + `build_guia_xml` + tests. Route: inline. Commit: 237378c
- T2 (S1): Destinatarios mapping + voucher `06` integration + tests. Route: inline. Commit: 237378c
- T3 (S2): Live proof, verify, commit and push to `version-16`. Route: inline. Commit: 49083ad
- T4 (S1): RIDE print formats + email for 06/07 from the emitted XML (worker mvhymgzq-1-4jc5 + parent defect fix: `sri_voucher_data` resolver reading unsigned_xml). Route: worker. Commit: 05a7773

## Log
- L1: "bien avancemos con fase 8"
- L2: Contacts are company-global by ERPNext design (no company field on Customer/Supplier); fiscal nationality resolves per transaction context. Chained live proof (SRI pruebas, self-signed): SI voucher 01 (001-001-000000002, RECIBIDA then FIRMA INVALIDA) then DN voucher 06 (001-001-000000001, RECIBIDA then FIRMA INVALIDA, sustento without auth number accepted) — full factura-to-guia path proven; Authorized needs an SRI-issued cert.

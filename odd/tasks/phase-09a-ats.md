# Phase 9A — ATS Engine (Anexo Transaccional Simplificado)

## Specs
- S1: Monthly `AT{mmaaaa}.xml` + `.zip` (compras, ventas, exportaciones, anulados) validated offline against vendored `l10n_ec/sri/xsd/ats.xsd`, aggregating posted ledger (incl. IVA deduction rows + settlement JEs), voucher XML/RIDE data, SI received refs, Tabla 24 payment codes, concepto/casillero table.
- S2: Verify, commit, and push to `version-16` with dual-ring tests and a demo-month proof.

## Tasks
- T1 (S1): ATS collector (posted-month aggregation into SRI sections) + tests. Route: worker. Commit: -
- T2 (S1): XML builder + XSD validation + zip + tests. Route: worker. Commit: -
- T3 (S2): Demo-month proof, verify, commit and push to `version-16`. Route: parent. Commit: -

## Log
- L1: "adelante con 9a"

# Phase 9A — ATS Engine (Anexo Transaccional Simplificado)

## Specs
- S1: Monthly `AT{mmaaaa}.xml` + `.zip` (compras, ventas, exportaciones, anulados) validated offline against vendored `l10n_ec/sri/xsd/ats.xsd`, aggregating posted ledger (incl. IVA deduction rows + settlement JEs), voucher XML/RIDE data, SI received refs, Tabla 24 payment codes, concepto/casillero table.
- S2: Verify, commit, and push to `version-16` with dual-ring tests and a demo-month proof.

## Tasks
- T1 (S1): ATS collector (posted-month aggregation into SRI sections) + tests. Route: worker. Commit: ceec68a
- T2 (S1): XML builder + XSD validation + zip + tests. Route: worker. Commit: ceec68a
- T3 (S2): Demo-month proof, verify, commit and push to `version-16`. Route: parent. Commit: ceec68a

## Log
- L1: "adelante con 9a"
- L2: Live October proof (demo): 3 compras blocks from posted SRI PIs (supplier auths backfilled as demo placeholders), XSD-valid XML + AT102026.zip; ventas/exports/anulados honestly empty (no authorized emissions/cancels on demo — self-signed ceiling). Fiscal-existence rule: only Authorized emissions feed ATS. New production surface: generate_ats_files entry point + bench reader (incl. sri_supplier_auth_number field).

# Phase 9B — Forms 103 & 104 (Script Reports)

## Specs
- S1 (103): IR withholdings collector (authorized 07 voucher IR blocks → concepto→casillero pairs incl. residentes totals; exterior section explicit-empty) + Script Report. Live proof via staged-Authorized pattern (self-signed ceiling).
- S2 (104): VAT collector (SI/PI taxes rows, IVA deduction rows, settlement JEs, SI refs, TDS credits 1010501/1010502, empty-boxes pattern) + Script Report. Live proof on real posted ledger.
- S3: Verify, commit, and push to `version-16` with dual-ring tests and es translations.

## Tasks
- T1 (S1): 103 collector + report + tests. Route: worker. Commit: -
- T2 (S2): 104 collector + report + tests. Route: worker. Commit: -
- T3 (S3): Live proofs (staged 103 + ledger 104), verify, commit and push. Route: parent. Commit: -

## Log
- L1: "bien continuemos con fase 9b"
- L2: Split 9B1/9B2 (independent sources, disjoint files, parallel workers). OCA collectors (/tmp/oca-ref/oca_103_collector.py: residentes/exterior/totals; oca_104_collector.py: ventas/compras/liquidacion/empty-boxes) as design reference. Delivery = pure collector + thin Script Report (no wizard).

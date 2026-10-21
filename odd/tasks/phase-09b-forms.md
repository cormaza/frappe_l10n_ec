# Phase 9B — Forms 103 & 104 (Script Reports)

## Specs
- S1 (103): IR withholdings collector (authorized 07 voucher IR blocks → concepto→casillero pairs incl. residentes totals; exterior section explicit-empty) + Script Report. Live proof via staged-Authorized pattern (self-signed ceiling).
- S2 (104): VAT collector (SI/PI taxes rows, IVA deduction rows, settlement JEs, SI refs, TDS credits 1010501/1010502, empty-boxes pattern) + Script Report. Live proof on real posted ledger.
- S3: Verify, commit, and push to `version-16` with dual-ring tests and es translations.

## Tasks
- T1 (S1): 103 collector + report + tests. Route: worker. Commit: f9807d0
- T2 (S2): 104 collector + report + tests. Route: worker. Commit: f9807d0
- T3 (S3): Live proofs (staged 103 + ledger 104), verify, commit and push. Route: parent. Commit: f9807d0

## Log
- L1: "bien continuemos con fase 9b"
- L2: Split 9B1/9B2 (independent sources, disjoint files, parallel workers). OCA collectors (/tmp/oca-ref/oca_103_collector.py: residentes/exterior/totals; oca_104_collector.py: ventas/compras/liquidacion/empty-boxes) as design reference. Delivery = pure collector + thin Script Report (no wizard).
- L3: Live proofs — 103 staged-Authorized (312:100 + 362:2.00, IVA skipped, restored); 104 on posted October ledger (128 boxes, 401/411/421 + 500s + 609/801/859 reconcile arithmetically; negative 620 is OCA-literal when 609>601). Parent fixes: received_refs wired from SI fields (worker left []), settlement_values deduped into received_settlement, empty-filters guard on both reports, fixture-name invariant test (Report JSONs lacked name → migrate KeyError).

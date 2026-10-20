# Phase 4: Ecuador NIIF Chart of Accounts & Tax Templates

Implements roadmap Phase 4 on `version-16` with direct commits (no PR).
Full official SCVS transcription plus operational leaves, ERPNext loader,
and per-company tax template routine.

## Specs

- S1: Roadmap Phase 4 scope, quoted verbatim: "Verified NIIF Chart of Accounts (`Superintendencia de Compañías`) with correct `root_type` assignments and NIIF account numbers.", "Tax templates: VAT 15%, VAT 5% (construction), VAT 0%, VAT Exempt, No Object of VAT, ICE, IRBPNR, Income & VAT Withholding rates."
- S2: Roadmap Phase 4 exit criteria, quoted verbatim: "chart installs on a new Ecuadorian company; trial balance roots balance; every template posts to its intended account in a smoke test."
- S3: Depth decision. User chose "Completo + extensión operativa" after reviewing `odd/tasks/phase-04-chart-analysis.md`: full official transcription (~336 lines) plus ~30-40 operational leaves (banks, VAT in/out, withholding splits, ICE/IRBPNR, control details).
- S4: Locked readings: ERPNext chart picker is closed to external apps, so the app ships `chart_of_accounts/ec_niif_chart_template.json` (`name`/`country_code`/`tree` format) and installs it via ERPNext's `create_charts(company, custom_chart=...)`, auto-firing on Company creation only for Ecuadorian companies with zero accounts, plus a whitelisted reinstall guarded by no-GL-entries; computed/cash-flow groups (`42, 60-91, 95-99`) and `ELIMINADO` lines are excluded; official T→group / D→leaf (extended leaves become documented groups); account names stay in official Spanish (filing semantics; translating them would corrupt the Super Cías mapping); tax templates cover the VAT family sales+purchase plus ICE/IRBPNR account-bound templates, with the withholding-rate table delivered as data for Phase 7.

## Tasks

- T1 (S1): Transcribe official chart to JSON (mechanical transpose, reviewed) + operational leaves + Ring-1 structure tests. Route: inline. Commit: b1dd707
- T2 (S2): Chart loader (`chart_setup.py`, auto-install-if-empty + whitelisted reinstall) + hooks wiring. Route: inline. Commit: a8040c6
- T3 (S1): Tax template catalog + per-company creator routine + Ring-1 tests. Route: inline. Commit: a8040c6
- T4 (S2): Verify (`pytest -W error`, `pre-commit`), commit and push to `version-16`. Route: inline. Commit: a8040c6

## Log

- L1: "adelante fase 4"
- L2: Analysis input at `odd/tasks/phase-04-chart-analysis.md`; official source `PLAN DE CUENTAS.pdf` (SCVS) measured at 336 account lines, presentation-oriented, missing operational leaves (banks detail, VAT in/out, withholding splits).
- L3: Ring-2 checks (`migrate`, install on test company, template posting smoke test) pending: no bench in this environment; user tests on `version-16` directly.
- L4: T1 committed as b1dd707 (chart JSON, 324 nodes); T2-T4 as a8040c6. Transpose reconciled 315/315 official nodes; genuine source duplications disambiguated (5201/5202, 61/74, 63/76).
- L5: Demo run proved childless top-level lines cannot install (`The root account ... must be a group`); `61/63/65/72/74/76` nested under `52`, `66/71` under `43` (codes/names verbatim, 7 roots). Pinned by `test_roots_are_exactly_the_seven_postable_groups` and `test_orphan_result_lines_nest_under_result_groups`.
- L6: Invoice account resolution needs typed trade controls plus Company defaults: `101020503` (new operational leaf, Receivable), `2010301` (Payable), set via `_set_company_default_accounts` on every chart install. Reinstall order matters: clear Company links first, then templates, then accounts deepest-first (`lft desc`), else `LinkExistsError`/`NestedSetChildExistsError`. Live-verified: `debit_to` resolves to the NIIF control account.

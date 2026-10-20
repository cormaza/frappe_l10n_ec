# Phase 2: SRI Master Catalog DocTypes & Seed Data

Implements roadmap Phase 2 on `version-16` with direct commits (no PR).
Five catalog DocTypes plus one `istable` child, seed fixtures, and the
Phase 3 hook contract as a pure Ring-1-testable helper.

## Specs

- S1: Roadmap Phase 2 scope, quoted verbatim: "`SRI Identification Type` (`04`–`08`)", "`SRI Document Type` (`01` Invoice, `03` Purchase Liquidation, `04` Credit Note, `05` Debit Note, `06` Delivery Note, `07` Withholding, `41` Reimbursement)", "`SRI Payment Method` (`01` Without Financial System, `15` Compensation, `16` Debit Card, `17` Electronic Money, `18` Prepaid Card, `19` Credit Card, `20` Other with Financial System, `21` Endorsement of Titles)", "`SRI Tax Support` (`Sustento Tributario` codes `01`–`15` for purchases and ATS)", "`SRI Emission Point` (`Establecimiento` 3-digit + `Punto de Emisión` 3-digit + per-document-type 9-digit sequences)", "Seed data via fixtures matching official SRI codes."
- S2: Roadmap Phase 2 exit criteria, quoted verbatim: "all five DocTypes install cleanly on a test site; stored codes match the SRI specification exactly; controllers delegate format checks to `l10n_ec/sri/identification.py` (Phase 1)."
- S3: Hook contract proposal, quoted verbatim: "en la Fase 2 puedo ya dejar el contrato del hook definido (qué función del controlador llama a validate_identification y con qué gating de país), así la Fase 3 es solo cableado." Approved by user with "adelante, vamos fase 2".
- S4: Design readings locked during implementation: catalog codes enforced at schema level via `Select` options (no controller logic needed for closed sets); the S2 delegation clause is satisfied by the T3 hook-contract helper calling `validate_identification`; `SRI Emission Sequence` (`istable` child of Emission Point) carries the per-document-type 9-digit sequences; Emission Point records are per-company setup data (no fixtures); fixtures cover the four closed catalogs and are wired via `hooks.fixtures`.

## Tasks

- T1 (S1): Five catalog DocTypes + `SRI Emission Sequence` child (JSON, controllers, `__init__.py`, co-located tests). Route: inline. Commit: cba622b
- T2 (S1): Seed fixtures for the four closed catalogs + `hooks.fixtures` wiring. Route: inline. Commit: -
- T3 (S3): Hook-contract helper (`is_ecuadorian_contact`, `validate_contact_tax_id`) in `ecuador_localization/validation.py`, test-first, Ring 1. Route: inline. Commit: -
- T4 (S2): Verify (`pytest -W error`, `pre-commit`), commit and push to `version-16`. Route: inline. Commit: -

## Log

- L1: "adelante, vamos fase 2"
- L2: Sustento Tributario names 01-15 verified against SRI Tabla 5 (ATS technical sheet) via public catalog mirror; fixture titles use English functional names per repo i18n contract, Spanish arrives in Phase 5 (`es.po`).
- L3: T1 committed as cba622b (23 files, 787 insertions, mostly JSON schemas). Ring-2 install check (`migrate` on test site) pending: no bench available in this environment.

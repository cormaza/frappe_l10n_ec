# Phase 3: ERPNext Custom Fields & Install Wiring

Implements roadmap Phase 3 on `version-16` with direct commits (no PR).
Custom fields on Company/Customer/Supplier, install/migrate/uninstall
wiring, and `validate` hooks gating on the Country ISO code.

## Specs

- S1: Roadmap Phase 3 scope, quoted verbatim: "Wire `after_install` / `after_migrate` in `hooks.py` to idempotent `create_custom_fields`", "`Company`: `sri_environment` (`Test` / `Production`), `sri_signature` (`Link: SRI Signature`), `special_taxpayer_resolution`, `withholding_agent_resolution`, `rimpe_regime`, `accounting_required`.", "`Customer` & `Supplier`: `sri_identification_type`, `sri_related_party` (`Parte Relacionada`)."
- S2: Roadmap Phase 3 exit criteria, quoted verbatim: "fresh install and re-migrate both apply fields without duplicates or errors; uninstall path removes the customizations."
- S3: ISO gating decision. Proposal, quoted verbatim: "lo más robusto es matchear por código ISO `EC` del registro Country, que no depende de idioma ni de que alguien renombre el registro." Approved by user with "adelante toma la fase 3, teniendo encuenta lo del codigo ISO".
- S4: Locked readings: `validation.py` switches to ISO-code gating (`EC`, case-insensitive); the Country name-to-code lookup lives in the Phase 3 hook (frappe side), keeping `validation.py` frappe-free; unresolvable country (no default address) skips validation instead of blocking the save; validation only runs when `sri_identification_type` is set (no new mandatory-field rules — out of scope until Phase 6); `rimpe_regime` options are blank/`Popular Business`/`Entrepreneur`; `accounting_required` defaults to unchecked.

## Tasks

- T1 (S3, S4): Refine `validation.py` + Ring-1 tests to ISO-code gating. Route: inline. Commit: 03a8702
- T2 (S1): `custom_fields.py` (field defs, create, delete) + Ring-1 structure tests. Route: inline. Commit: 726bff2
- T3 (S1, S2): `hooks.py` wiring (`after_install`, `after_migrate`, `before_uninstall`, `doc_events` for Customer/Supplier). Route: inline. Commit: 726bff2
- T4 (S3, S4): `party_hooks.validate_sri_identification` (resolve Country code via default address, delegate, `frappe.throw`). Route: inline. Commit: 726bff2
- T5 (S2): Verify (`pytest -W error`, `pre-commit`), commit and push to `version-16`. Route: inline. Commit: 726bff2

## Log

- L1: "adelante toma la fase 3, teniendo encuenta lo del codigo ISO"
- L2: Ring-2 checks (`migrate`, fixture import, hook firing on a test site) pending: no bench in this environment; user tests on `version-16` directly.
- L3: T1 committed as 03a8702; T2-T4 committed as 726bff2 (11 files). Pre-commit reformatted four Phase 2 test files (whitespace only); they rode along in 726bff2.

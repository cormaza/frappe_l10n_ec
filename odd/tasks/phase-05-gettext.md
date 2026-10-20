# Phase 5: Spanish Gettext Catalog (`es`)

Implements roadmap Phase 5 on `version-16` with direct commits (no PR).
Bench-only steps (`generate-pot-file`, `update-po-files`,
`compile-po-to-mo`, UI spot-check) cannot run here; this phase ships
everything that makes them succeed: wrapped Python strings, a curated
`locale/es.po`, `locale/main.pot`, and local `msgfmt` validation.

## Specs

- S1: Roadmap Phase 5 scope, quoted verbatim: "Ensure every user-facing Python string is wrapped in `frappe._(\"...\")` and every JS string in `__(\"...\")` (English source) for all DocTypes delivered in Phases 0–4.", "Generate `l10n_ec/locale/main.pot`, translate `l10n_ec/locale/es.po`, and compile to `.mo` via `bench generate-pot-file`, `bench update-po-files --locale es`, `bench compile-po-to-mo --locale es`."
- S2: Roadmap Phase 5 exit criteria, quoted verbatim: "pot/po/mo pipeline runs clean inside bench; Spanish UI spot-check passes on the delivered DocTypes."
- S3: Locked readings: no JS files exist in the repo, so there is nothing to wrap in `__()`; pure-domain modules (`l10n_ec/sri/`, `validation.py`) keep raw English literals (Ring-1 import constraint) and are covered via `.po` msgids; parametrized f-string messages are rewritten to static `{0}`-style literals with identical runtime text (suite pins the text); `frappe._()` wrapping happens only inside `if frappe:` branches; fixture titles are user data, not translated; catalog `code` options are identifiers, not translated; `*.mo` is a build artifact (gitignored), `.pot`/`.po` are committed.

## Tasks

- T1 (S1): Rewrite parametrized messages to static `{}` literals + `frappe._()` at boundaries. Route: inline. Commit: e5029ca
- T2 (S1): Write `locale/main.pot` + `locale/es.po`, validate/compile with `msgfmt`. Route: inline. Commit: 28fb603
- T3 (S2): Verify (`pytest -W error`, `pre-commit`, `msgfmt --check`), commit and push to `version-16`. Route: inline. Commit: 28fb603

## Log

- L1: "hagamos la fase 5"
- L2: Bench steps and UI spot-check pending: no bench in this environment; user runs them on `version-16`.
- L3: Ruff UP030 forbids `{0}` and UP032 forbids `.format()`; kept `{}` implicit style plus a one-line UP032 ignore with rationale (ecosystem Gettext convention).

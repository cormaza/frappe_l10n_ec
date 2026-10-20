# Phase 5: Spanish Gettext Catalog (`es`)

Implements roadmap Phase 5 on `version-16` with direct commits (no PR).
Bench-only steps (`generate-pot-file`, `update-po-files`,
`compile-po-to-mo`, UI spot-check) cannot run here; this phase ships
everything that makes them succeed: wrapped Python strings, a curated
`locale/es.po`, `locale/main.pot`, and local `msgfmt` validation.

## Specs

- S1: Roadmap Phase 5 scope, quoted verbatim: "Ensure every user-facing Python string is wrapped in `frappe._(\"...\")` and every JS string in `__(\"...\")` (English source) for all DocTypes delivered in Phases 0–4.", "Generate `l10n_ec/locale/main.pot`, translate `l10n_ec/locale/es.po`, and compile to `.mo` via `bench generate-pot-file`, `bench update-po-files --locale es`, `bench compile-po-to-mo --locale es`."
- S2: Roadmap Phase 5 exit criteria, quoted verbatim: "pot/po/mo pipeline runs clean inside bench; Spanish UI spot-check passes on the delivered DocTypes."
- S3: Locked readings: no JS files exist in the repo, so there is nothing to wrap in `__()`; user-facing literals use the `from frappe import _` pattern with an identity fallback (Ring-1 safe) so the bench pot scanner extracts them; custom-field labels stay raw English in `custom_fields.py` (stored in DB, translated at display) with extraction markers in `l10n_ec/locale/i18n_markers.py`; parametrized messages use static `{}` literals with identical runtime text (suite pins the text); core-owned role names (`Accounts Manager`, `System Manager`) are intentionally left untranslated; `*.mo` is a build artifact (gitignored), `.pot`/`.po` are committed.

## Tasks

- T1 (S1): Rewrite parametrized messages to static `{}` literals + `frappe._()` at boundaries. Route: inline. Commit: e5029ca
- T2 (S1): Write `locale/main.pot` + `locale/es.po`, validate/compile with `msgfmt`. Route: inline. Commit: 28fb603
- T3 (S2): Verify (`pytest -W error`, `pre-commit`, `msgfmt --check`), commit and push to `version-16`. Route: inline. Commit: 28fb603

## Log

- L1: "hagamos la fase 5"
- L2: Bench steps done in local bench (`frappe-bench-v16`, MariaDB 11.8 + Redis in docker): `generate-pot-file`, `update-po-files --locale es`, `compile-po-to-mo --locale es` all clean; 65/65 integration tests green on `test_site`. Only the desk UI spot-check remains user-side.
- L3: Ruff UP030 forbids `{0}` and UP032 forbids `.format()`; kept `{}` implicit style plus UP032/UP030/UP031/UP037/UP040 ignores mirroring frappe core's own config (each annotated `(translations)` upstream), so the config cannot drift from a future core integration.
- L4: Ring 2 caught three real bugs: fixtures need explicit `name` (`import_doc` reads it), controller tests must use `frappe.get_doc` under real frappe, and error expectations must be dual-ring `(ValueError, frappe.ValidationError)`. Bench `update-po-files` prunes msgids its scanner cannot see (kept only via real `_()` calls or the markers file) and requires full `YYYY-MM-DD HH:MM` in `PO-Revision-Date`.

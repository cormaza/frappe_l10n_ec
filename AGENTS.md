# Agent Instructions (`l10n_ec` — Frappe v16 Ecuadorian Localization)

This repository is a standalone **Frappe Framework v16 / ERPNext v16** application (`l10n_ec`, version `16.0.0`, branch `version-16`) targeting **Python 3.14**, providing Ecuadorian localization and SRI Offline Electronic Invoicing (`Comprobantes Electrónicos Offline`, XAdES-BES).

---

## 1. Repository Layout & Execution Context

Unlike a multi-app `frappe-bench` workspace (`apps/`, `sites/`, `env/`), this repository is the **standalone `l10n_ec` app root**:

- **Ring 1 (Fast Local TDD & Static Analysis — Default Local Loop, `< 2s`)**:
  - Uses `.venv` (Python 3.14 managed via `uv`).
  - Run `pre-commit` hooks (Ruff import sorter, Ruff linter, Ruff formatter, JSON/TOML/YAML/AST checks):
    ```bash
    .venv/bin/pre-commit run --all-files --show-diff-on-failure
    ```
  - Run unit and cryptographic XAdES-BES signing test suite:
    ```bash
    .venv/bin/pytest -v --cov=l10n_ec/sri --cov-report=term-missing -W error
    ```
  - Run the GitHub Actions `workflow_dispatch` job locally via `act`:
    ```bash
    act workflow_dispatch -W .github/workflows/ci.yml -j fast-tdd-unit
    ```
- **Ring 2 (Full Frappe v16 + MariaDB 11.8 Bench Integration)**:
  - Note that `.agents/skills/frappe-app-dev/` supports both Standalone App Repository Mode and Full `frappe-bench` Mode.
  - Use **Frappe-Manager (`fm`)**, **`frappe_docker`**, or the `frappe-v16-integration` job in `.github/workflows/ci.yml` when executing full database-backed `bench` commands (`bench --site test_site migrate`, `bench --site test_site run-tests --app l10n_ec`).
  - For interactive development against a seeded demo site, use `dev/demo.sh` (see `docs/LOCAL_DEMO.md`): `up`, `reset` (idempotent drop/create/seed of site `demo`), `seed`, `serve`, `status`, `down`.
  - Local no-sudo bench (`~/frappe-bench-v16`, site `test_site`): MariaDB 11.8 and Redis run in Docker (bench v16 expects Redis on `11001`/`13001`, not the classic `11000`/`12000`/`13000` — always confirm against `sites/common_site_config.json`); a `redis-server --version` shim in `~/.local/bin` satisfies `bench init` config generation (the real servers are the containers); `yarn` comes from user-owned mise node (`npm install -g yarn`, no sudo); no `/etc/hosts` entry is needed for CLI-only `run-tests`.

---

## 2. Architectural & Domain Layering Rules

1. **Pure Python SRI Domain Layer (`l10n_ec/sri/`)**:
   - Contains `signer.py` (PKCS#12 decoding, certificate chain selection, XAdES-BES RSA-SHA1 enveloped signing via `xmlsig` + `xades==0.2.4`), `access_key.py` (Modulo 11 49-digit `claveAcceso`), and `soap_client.py` (offline/online `zeep` WSDL client).
   - **MUST NOT** have top-level `import frappe` dependencies so that Ring 1 tests execute in `< 2s` without a running MariaDB or Redis service.
   - **NEVER** call `ctx.load_pkcs12()` on `xmlsig` / `xades` contexts (`pyOpenSSL >= 24` removed `OpenSSL.crypto.PKCS12`). Always assign `ctx.x509`, `ctx.public_key`, and `ctx.private_key` directly as implemented in `l10n_ec/sri/signer.py`.

2. **Frappe v16 Module & DocType Layer (`l10n_ec/ecuador_localization/`)**:
   - Contains Frappe v16 DocType JSON definitions, controllers (`Document` subclasses with `TYPE_CHECKING` `DF` annotations), programmatic custom field definitions (`create_custom_fields`), and co-located `test_<doctype>.py` modules.
   - Controllers delegate cryptographic and SRI protocol operations to `l10n_ec/sri/`.

3. **Frappe v16 Test Runner Discovery Rule (Mandatory)**:
   - Frappe's `bench run-tests` uses `unittest.TestLoader().loadTestsFromModule(module)`, which **only** discovers methods on `unittest.TestCase` (`UnitTestCase` / `IntegrationTestCase`) subclasses and **silently ignores** bare top-level `def test_...()` functions.
   - Every test in any `test_*.py` file **MUST** be a method inside a `UnitTestCase` or `IntegrationTestCase` class (`from frappe.tests import IntegrationTestCase, UnitTestCase`, with `unittest.TestCase` fallback for standalone `pytest`).
   - `TestAppInstallability::test_frappe_test_runner_discovery_compliance` in `l10n_ec/tests/test_app_installability.py` enforces this invariant automatically.

4. **Ring 2 Hard Lessons (Mandatory)**:
   - Fixture records in `l10n_ec/fixtures/*.json` MUST include an explicit `"name"` key: bench's `import_doc` reads `doc["name"]` before insert (`KeyError: 'name'` otherwise), even for DocTypes with `autoname: field:<field>`.
   - Controller and hook tests MUST follow the dual-ring contract: build documents via `frappe.get_doc({...})` when frappe is present (direct `MyDoc(field=...)` instantiation has no DocType context under real Frappe and fails with `DocType None not found`), expect `(ValueError, frappe.ValidationError)` for validation errors (Ring 1 raises `ValueError`, bench converts `frappe.throw`), and bind the name with an explicit `import frappe` (`from frappe.tests import X` does NOT bind it, so a module-level `frappe.ValidationError` reference raises `NameError` at discovery). See `.agents/skills/frappe-app-dev/references/testing.md`.
   - The Ruff ignore list in `pyproject.toml` mirrors frappe core upstream (`UP030`/`UP031`/`UP032`/`UP037`/`UP040`, each annotated `(translations)` in core). Do NOT remove entries to satisfy the linter; adjust code instead — these translation ignores exist upstream and keep future core integration clean.

5. **Verify Against Core Sources Before Assuming (Mandatory)**:
   - When implementation depends on framework behavior, read the installed core sources (`~/frappe-bench-v16/apps/frappe`, `~/frappe-bench-v16/apps/erpnext`, pinned to the target branches) instead of assuming from docs or memory. See `.agents/skills/frappe-app-dev/references/existing-app.md`.
   - Past assumptions that cost cycles: setup completion is `Installed Application.is_setup_complete` per app (not `System Settings`); the chart picker reads only ERPNext's own template folders (external apps install via `create_charts(custom_chart=...)`); bench v16 Redis ports come from `sites/common_site_config.json` (`11001`/`13001`), not the classic `11000`/`12000`/`13000`.

---

## 3. Language Domain & Frappe v16 Gettext Translation (`i18n`) Contract

Following official Frappe v16 internationalization (`frappe/gettext/translate.py`) and regional localization apps (such as `resilient-tech/india-compliance` and `alyf-de/erpnext_germany`):

1. **100% English Source Code & Metadata**:
   - All Python/JS identifiers, module names, class names, comments, docstrings, commit messages, and markdown documentation **MUST** be in clean professional English.
   - All Frappe DocType names (`SRI Signature`, `SRI Payment Method`, `SRI Tax Support`, `SRI Emission Point`), `fieldname`s, `label`s, `description`s, Select `options`, Workspace titles, and Report labels **MUST** be defined in English in `.json` and `.py` files.
   - All user-facing strings in Python must be wrapped in `frappe._("...")` (in English), and all user-facing strings in JavaScript must be wrapped in `__("...")` (in English).

2. **Official SRI Protocol Exception**:
   - Only literal XML element/attribute names (`infoTributaria`, `claveAcceso`, `codDoc`, `razonSocialComprador`), XAdES object descriptions (`contenido comprobante`), and SOAP/WSDL/XSD identifiers (`RecepcionComprobantesOffline`, `validarComprobante`, `RECIBIDA`, `DEVUELTA`, `AUTORIZADO`) mandated by the Ecuadorian SRI technical specification remain in Spanish.

3. **Frappe v16 Gettext `locale/` Workflow (`es.po`)**:
   - Do **not** use legacy `translations/*.csv` files.
   - Spanish (`es`) UI translations for Ecuadorian users live in `l10n_ec/locale/main.pot` and `l10n_ec/locale/es.po` (the exact Frappe v16 counterpart to OCA's `i18n/es.po`).
   - Extract, update, and compile translations using Frappe's Gettext CLI inside a bench environment:
     ```bash
     bench generate-pot-file --app l10n_ec
     bench update-po-files --app l10n_ec --locale es
     bench compile-po-to-mo --app l10n_ec --locale es
     ```
   - User-facing literals in pure Python modules (no top-level `import frappe` allowed) use `from frappe import _` with an identity fallback (`def _(message: str) -> str: return message`), which keeps Ring 1 green while giving the bench pot scanner real `_()` call literals to extract.
   - `create_custom_fields` labels and Select options stay raw English (they are stored in the database and translated at display time); their translations are collected via extraction markers in `l10n_ec/locale/i18n_markers.py`, which MUST never be imported at runtime.
   - `bench update-po-files` PRUNES msgids its scanner cannot see: every shipped msgid needs a real `_()` call or a marker entry. After the bench cycle, adopt the regenerated `main.pot`/`es.po` (headers, `#:` refs) as canonical.
   - `PO-Revision-Date` MUST use the full `YYYY-MM-DD HH:MM` format; a bare date breaks `bench build --app` translation compilation.
   - Core-owned strings (e.g. the `Accounts Manager` / `System Manager` roles) stay untranslated in our catalog; core ships their translations.

---

## 4. Workspace Skills (`.agents/skills/`)

The following skills from [`frappe/skills`](https://github.com/frappe/skills) are installed in `.agents/skills/` for automatic and on-demand invocation:

- [`.agents/skills/frappe-app-dev/SKILL.md`](.agents/skills/frappe-app-dev/SKILL.md): Reference patterns for Frappe v16 DocTypes, controllers, hooks, permissions, background jobs, and testing (aligned for both Standalone App Repository Mode and Full `frappe-bench` Mode).
- [`.agents/skills/frappe-code-review/SKILL.md`](.agents/skills/frappe-code-review/SKILL.md): Structured checklist for reviewing Frappe pull requests and controller/database changes.
- [`.agents/skills/deep-app-audit/SKILL.md`](.agents/skills/deep-app-audit/SKILL.md): Comprehensive security (`S01`–`S42`) and correctness/customization (`A`/`B`/`C`/`D`) audit rules for Frappe applications.
- [`.agents/skills/code-style/SKILL.md`](.agents/skills/code-style/SKILL.md): Python/JS formatting, naming, early returns, and readability standards across the Frappe ecosystem.

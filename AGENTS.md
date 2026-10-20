# Agent Instructions (`l10n_ec` — Frappe v16 Ecuadorian Localization)

This repository is a standalone **Frappe Framework v16 / ERPNext v16** application (`l10n_ec`) targeting **Python 3.14**, providing Ecuadorian localization and SRI Offline Electronic Invoicing (`Comprobantes Electrónicos Offline`, XAdES-BES).

---

## 1. Repository Layout & Execution Context

Unlike a multi-app `frappe-bench` workspace (`apps/`, `sites/`, `env/`), this repository is the **standalone `l10n_ec` app root**:

- **Ring 1 (Fast Local TDD & Static Analysis — Default Local Loop, `< 2s`)**:
  - Uses `.venv` (Python 3.14 managed via `uv`).
  - Run linter and formatter:
    ```bash
    .venv/bin/ruff check .
    .venv/bin/ruff format --check .
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
  - Note that `.agents/skills/frappe-app-dev/` assumes commands like `bench --site <site> migrate` or `bench --site <site> run-tests` are executed from a `frappe-bench` directory where `l10n_ec` is installed under `apps/l10n_ec`.
  - Use **Frappe-Manager (`fm`)**, **`frappe_docker`**, or the `frappe-v16-integration` job in `.github/workflows/ci.yml` when executing full database-backed `bench` commands.

---

## 2. Architectural & Domain Layering Rules

1. **Pure Python SRI Domain Layer (`l10n_ec/sri/`)**:
   - Contains `signer.py` (PKCS#12 decoding, certificate chain selection, XAdES-BES RSA-SHA1 enveloped signing via `xmlsig` + `xades==0.2.4`), `access_key.py` (Modulo 11 49-digit `claveAcceso`), and `soap_client.py` (offline/online `zeep` WSDL client).
   - **MUST NOT** have top-level `import frappe` dependencies so that Ring 1 tests execute in `< 2s` without a running MariaDB or Redis service.
   - **NEVER** call `ctx.load_pkcs12()` on `xmlsig` / `xades` contexts (`pyOpenSSL >= 24` removed `OpenSSL.crypto.PKCS12`). Always assign `ctx.x509`, `ctx.public_key`, and `ctx.private_key` directly as implemented in `l10n_ec/sri/signer.py`.

2. **Frappe v16 Module & DocType Layer (`l10n_ec/ecuador_localization/`)**:
   - Contains Frappe v16 DocType JSON definitions, controllers (`Document` subclasses with `TYPE_CHECKING` `DF` annotations), and co-located `test_<doctype>.py` modules.
   - Controllers delegate cryptographic and SRI protocol operations to `l10n_ec/sri/`.

3. **Frappe v16 Test Runner Discovery Rule (Mandatory)**:
   - Frappe's `bench run-tests` uses `unittest.TestLoader().loadTestsFromModule(module)`, which **only** discovers methods on `unittest.TestCase` (`UnitTestCase` / `IntegrationTestCase`) subclasses and **silently ignores** bare top-level `def test_...()` functions.
   - Every test in any `test_*.py` file **MUST** be a method inside a `UnitTestCase` or `IntegrationTestCase` class (`from frappe.tests import IntegrationTestCase, UnitTestCase`, with `unittest.TestCase` fallback for standalone `pytest`).
   - `TestAppInstallability::test_frappe_test_runner_discovery_compliance` in `l10n_ec/tests/test_app_installability.py` enforces this invariant automatically.

4. **Language Domain Contract**:
   - All code, identifiers, comments, docstrings, DocType JSON labels, commit messages, and documentation files must be written in clean professional English (except official Ecuadorian SRI XML tag names and XAdES/WSDL constants mandated by the SRI technical specification).

---

## 3. Workspace Skills (`.agents/skills/`)

The following skills from [`frappe/skills`](https://github.com/frappe/skills) are installed in `.agents/skills/` for automatic and on-demand invocation:

- [`.agents/skills/frappe-app-dev/SKILL.md`](.agents/skills/frappe-app-dev/SKILL.md): Reference patterns for Frappe v16 DocTypes, controllers, hooks, permissions, background jobs, and testing.
- [`.agents/skills/frappe-code-review/SKILL.md`](.agents/skills/frappe-code-review/SKILL.md): Structured checklist for reviewing Frappe pull requests and controller/database changes.
- [`.agents/skills/deep-app-audit/SKILL.md`](.agents/skills/deep-app-audit/SKILL.md): Comprehensive security (`S01`–`S42`) and correctness/customization (`A`/`B`/`C`/`D`) audit rules for Frappe applications.
- [`.agents/skills/code-style/SKILL.md`](.agents/skills/code-style/SKILL.md): Python/JS formatting, naming, early returns, and readability standards across the Frappe ecosystem.

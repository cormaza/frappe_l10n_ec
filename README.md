# Ecuador Localization for Frappe / ERPNext v16 (`l10n_ec`)

Ecuadorian Localization and SRI Offline Electronic Invoicing (`Comprobantes Electrónicos Offline`, XAdES-BES) for **Frappe Framework v16** and **ERPNext v16** on **Python 3.14**.

This repository ports the verified cryptographic XAdES-BES signing, PKCS#12 certificate chain selection, Modulo 11 access key (`claveAcceso`) generation, and offline Zeep SOAP web-service patterns from [`OCA/l10n-ecuador` PR #102](https://github.com/OCA/l10n-ecuador/pull/102) into a native Frappe v16 application with a two-ring Test-Driven Development (TDD) architecture.

---

## Architecture Overview

1. **Pure SRI Cryptographic & Domain Core ([`l10n_ec/sri/`](l10n_ec/sri/))**:
   - [`l10n_ec/sri/signer.py`](l10n_ec/sri/signer.py): Decodes `.p12` / PKCS#12 bundles via `cryptography >= 42`, selects the certificate with `KeyUsage.digital_signature=True` across multi-certificate chains (Banco Central del Ecuador, Security Data, ANF, Uanataca), extracts UTC-aware validity dates (`not_valid_before_utc` / `not_valid_after_utc`), and signs XML vouchers with `xmlsig` + `xades==0.2.4` (`XAdES-BES` RSA-SHA1 Enveloped). Includes the `pyOpenSSL >= 24` compatibility bypass (`ctx.x509`, `ctx.public_key`, `ctx.private_key` direct assignment instead of `ctx.load_pkcs12()`).
   - [`l10n_ec/sri/access_key.py`](l10n_ec/sri/access_key.py): Generates and validates 49-digit SRI access keys (`claveAcceso`) with Modulo 11 check digits (`compute_mod11_check_digit`, `generate_access_key`) and sanitizes XML strings per SRI Technical Sheet Table 1.
   - [`l10n_ec/sri/soap_client.py`](l10n_ec/sri/soap_client.py) & [`l10n_ec/sri/wsdl/`](l10n_ec/sri/wsdl/): Wraps `zeep` for SRI `RecepcionComprobantesOffline` and `AutorizacionComprobantesOffline` endpoints, bundling offline `.wsdl` definitions for zero-network unit testing.

2. **Frappe v16 DocType Layer ([`l10n_ec/ecuador_localization/doctype/sri_signature/`](l10n_ec/ecuador_localization/doctype/sri_signature/))**:
   - [`sri_signature.json`](l10n_ec/ecuador_localization/doctype/sri_signature/sri_signature.json) & [`sri_signature.py`](l10n_ec/ecuador_localization/doctype/sri_signature/sri_signature.py): Frappe v16 equivalent of OCA's `sri.key.type`, storing `.p12` credentials, certificate metadata, and exposing `action_validate_and_load()` and `sign_xml()`.

3. **Two-Ring TDD & Static Analysis Guardrails**:
   - **Ring 1 (Fast Inner Loop, `< 1s`, No DB required)**: Runs via `pytest` and `ruff` directly on Python 3.14 using dynamic PKCS#12 certificate generation ([`l10n_ec/tests/test_helpers.py`](l10n_ec/tests/test_helpers.py)) and offline Zeep WSDL bindings.
   - **Ring 2 (Full Frappe v16 + MariaDB 11.8 Integration)**: Runs `bench --site test_site run-tests --app l10n_ec` via `frappe.tests.UnitTestCase` and `frappe.tests.IntegrationTestCase`.
   - **Pre-commit & Semgrep ([`.pre-commit-config.yaml`](.pre-commit-config.yaml))**: Enforces Frappe v16 Ruff formatting/linting and `frappe-semgrep-rules` (Frappe's equivalent to OCA's `pylint-odoo`).

---

## Quick Start: Fast Local TDD Loop (< 1 second)

You can run the entire cryptographic XAdES-BES signing, PKCS#12 chain resolution, Modulo 11, and SOAP WSDL test suite locally on Python 3.14 without starting MariaDB or Redis:

```bash
# 1. Create an isolated Python 3.14 virtual environment using uv
uv venv --python 3.14

# 2. Install l10n_ec in editable mode with test/linter dependencies
uv pip install -e ".[dev]"

# 3. Run Ruff linter and formatter checks
uv run ruff check .
uv run ruff format --check .

# 4. Run the fast unit & XAdES-BES test suite with coverage
uv run pytest -v --cov=l10n_ec/sri --cov-report=term-missing
```

---

## Full Frappe v16 Containerized Development & Manual CI

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for complete instructions on:
1. Spinning up a containerized Frappe v16 + ERPNext v16 stack using **Frappe-Manager (`fm`)** or **`frappe_docker` Devcontainer** (the Frappe equivalent of Doodba).
2. Running the manual GitHub Actions CI dispatcher ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) via `gh workflow run ci.yml` or locally with `act`.

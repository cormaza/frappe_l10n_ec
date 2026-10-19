# Development & Testing Guide (`l10n_ec` for Frappe v16)

This guide explains how to develop, lint, and test `l10n_ec` using:
1. **Ring 1**: The sub-second local Python 3.14 TDD loop (`uv` + `pytest` + `ruff`).
2. **Ring 2**: A containerized Frappe v16 + MariaDB 11.8 environment (**Frappe-Manager (`fm`)** or **`frappe_docker` Devcontainer**).
3. **Manual CI Dispatcher**: Triggering `.github/workflows/ci.yml` on demand via GitHub CLI (`gh`) or `act`.

---

## 1. Ring 1: Fast Local TDD Loop (`uv` + `pytest` + `ruff`)

All SRI cryptographic signing (`xmlsig` + `xades==0.2.4`), PKCS#12 certificate chain selection (`cryptography >= 42`), Modulo 11 access key (`claveAcceso`) generation, and Zeep SOAP WSDL bindings reside in [`l10n_ec/sri/`](../l10n_ec/sri/) with zero hard runtime dependency on a live MariaDB instance.

### Setup & Execution

```bash
# Create Python 3.14 virtualenv
uv venv --python 3.14

# Install package and dev tools
uv pip install -e ".[dev]"

# Run static analysis (Ruff linter + formatter)
uv run ruff check .
uv run ruff format --check .

# Run unit tests with coverage
uv run pytest -v --cov=l10n_ec/sri --cov-report=term-missing
```

### Installing Pre-Commit Guardrails (`ruff` + `frappe-semgrep-rules`)

```bash
uv tool install pre-commit
pre-commit install
pre-commit run --all-files
```

---

## 2. Ring 2: Full Frappe v16 Containerized Environment (Doodba Equivalent)

In the Frappe v16 ecosystem, **Frappe-Manager (`fm`)** and **`frappe_docker` Devcontainers** serve the same role that Doodba serves in OCA: providing an isolated, reproducible MariaDB 11.8 + Redis + Python 3.14 + Node 24 bench.

### Option A: Using Frappe-Manager (`fm`)

```bash
# 1. Install Frappe-Manager
uv tool install frappe-manager

# 2. Create a Frappe v16 + ERPNext v16 development site
fm create l10n-ec.localhost \
  --apps erpnext:version-16 \
  --frappe-branch version-16 \
  --environment dev

# 3. Shell into the bench container and link/install l10n_ec
fm shell l10n-ec.localhost
cd /workspace/frappe-bench
bench get-app l10n_ec /path/to/l10n_ec --resolve-deps
bench --site l10n-ec.localhost install-app l10n_ec
bench --site l10n-ec.localhost set-config allow_tests true

# 4. Run Frappe v16 UnitTestCase & IntegrationTestCase suites
bench --site l10n-ec.localhost run-tests --app l10n_ec
```

### Option B: Direct `frappe-bench` Setup on Linux / WSL2 / Container

```bash
# Initialize a Frappe v16 bench with Python 3.14
bench init --skip-assets --frappe-branch version-16 --python python3.14 frappe-bench
cd frappe-bench

# Fetch ERPNext v16 and link this repository
bench get-app erpnext --branch version-16 --resolve-deps
bench get-app l10n_ec /home/christopher/Documents/frappe --resolve-deps

# Create test site and install apps
bench new-site test_site --admin-password admin --mariadb-root-password root
bench --site test_site install-app erpnext
bench --site test_site install-app l10n_ec
bench --site test_site set-config allow_tests true

# Run all tests or a specific DocType test module
bench --site test_site run-tests --app l10n_ec
bench --site test_site run-tests --module l10n_ec.ecuador_localization.doctype.sri_signature.test_sri_signature
```

---

## 3. Manual CI Execution (`.github/workflows/ci.yml`)

To avoid burning GitHub Actions minutes on every intermediate commit, [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) is configured exclusively with `on: workflow_dispatch:`.

### Triggering on GitHub via `gh` CLI

```bash
# Run only the fast Python 3.14 TDD + Ruff job (~15 seconds)
gh workflow run ci.yml -f run_bench_integration=false

# Run both the fast TDD job AND the full Frappe v16 + MariaDB 11.8 integration job
gh workflow run ci.yml -f run_bench_integration=true

# Run a single module inside the Frappe v16 integration job
gh workflow run ci.yml \
  -f run_bench_integration=true \
  -f test_module="l10n_ec.ecuador_localization.doctype.sri_signature.test_sri_signature"
```

### Running the Workflow Locally with `act`

```bash
act workflow_dispatch -j fast-tdd-unit
```

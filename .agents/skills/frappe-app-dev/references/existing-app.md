# Existing App Workflow

Use this flow when extending, modifying, or fixing an existing Frappe app.

## Step 1: Detect workspace mode (Standalone App Repo vs Full Bench)

Check whether the workspace is a standalone app repository (like `l10n_ec`) or a full `frappe-bench` directory:

- **Standalone App Repository (`pyproject.toml` and `<app-name>/hooks.py` at workspace root, no `sites/` directory)**:
  - App package root is `<app-name>/` (e.g. `l10n_ec/`).
  - Pure domain modules live in `<app-name>/sri/` (`l10n_ec/sri/`).
  - Frappe modules and DocTypes live in `<app-name>/<module-name>/doctype/<doctype>/` (e.g. `l10n_ec/ecuador_localization/doctype/sri_signature/`).
- **Full `frappe-bench` Root (`apps/`, `sites/`, and `Procfile` exist)**:
  - App package root is `apps/<app-name>/<app-name>/`.
  - Frappe modules and DocTypes live in `apps/<app-name>/<app-name>/<module-name>/doctype/<doctype>/`.

Do NOT create a second app. Do NOT run `bench new-app`.

## Step 2: Read existing app structure

Key files to inspect first:
- `pyproject.toml` — dependencies, Ruff configuration, and `[tool.bench.frappe-dependencies]`
- `<app-name>/hooks.py` (or `apps/<app-name>/<app-name>/hooks.py`) — app metadata and registered hooks
- `<app-name>/modules.txt` — declared Frappe modules
- `<app-name>/<module-name>/` — existing DocTypes and controllers

## Step 3: Build / modify features

Read the app's existing code to understand patterns before making changes. Load only the relevant feature references from the main `SKILL.md` table.

## Step 4: Verify changes

### In Standalone App Repository Mode (Ring 1 Fast Loop)

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -v -W error
```

### In Full `frappe-bench` Mode / Containerized Ring 2

```bash
bench --site <site> migrate
bench --site <site> run-tests --app <app-name>
```

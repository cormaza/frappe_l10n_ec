---
name: frappe-app-dev
description: >-
  Builds full-stack Frappe Framework applications end-to-end. Use this skill any
  time the user mentions: creating or modifying a DocType, writing a controller
  or lifecycle hook, adding a whitelisted API, setting up a new Frappe app or
  bench site, building a desk form or list view, creating portal pages, writing
  background jobs or scheduled tasks, managing permissions or roles, writing
  Frappe tests, or working with frappe.db / frappe.qb. Also applies when the
  user says things like "how do I hook into save", "add a field to a DocType",
  "create a REST endpoint in Frappe", "run bench migrate", or "install an app on
  a site" — even if they don't explicitly say "Frappe".
---

# Frappe Full-Stack App Builder

## Global Rules (Workspace Mode Detection)

Determine which repository mode the workspace is in before running commands:

1. **Standalone App Repository Mode (Default in this repo: `pyproject.toml` and `<app_name>/hooks.py` are at the workspace root, and `sites/` does not exist)**:
   - All app file paths are relative to the repository root: `<app_name>/<module>/doctype/<doctype>/` (e.g., `l10n_ec/ecuador_localization/doctype/sri_signature/`), **not** `apps/<app_name>/<app_name>/...`.
   - You **may** create and edit DocType directories (`<app_name>/<module>/doctype/<doctype>/<doctype>.json`, `<doctype>.py`, `test_<doctype>.py`, `__init__.py`) directly.
   - Validate DocType schemas, `field_order`, controller imports, and unit tests immediately via the Ring 1 fast local loop:
     ```bash
     .venv/bin/ruff check .
     .venv/bin/ruff format --check .
     .venv/bin/pytest -v -W error
     ```
   - Do **not** run bare `bench` commands directly on the host when `sites/` does not exist. Use `act workflow_dispatch -W .github/workflows/ci.yml -j fast-tdd-unit` for local CI verification, and run `bench` commands inside **Frappe-Manager (`fm`)**, **`frappe_docker`**, or the `frappe-v16-integration` CI job.

2. **Full `frappe-bench` Mode (When `apps/`, `sites/`, and `Procfile` exist in the workspace or parent directory)**:
   - Paths are under `apps/<app_name>/<app_name>/<module>/...`.
   - Use bare `bench` (not `./env/bin/bench`), and always pass `--site <site>` explicitly (`bench --site <site> migrate`, `bench --site <site> run-tests --app <app_name>`).
   - Run `bench start` in a background process only after checking it is not already running.

## Flow Selection

Determine which flow applies, then read ONLY the relevant file:

### Working on an existing app

Read [existing-app.md](./references/existing-app.md) — covers standalone app repository mode vs full bench mode, module layout, and verification.

### Creating a brand new app

Read [new-app.md](./references/new-app.md) — covers bench setup, app scaffolding, site creation, and installation.

## Feature References

Load ONLY the references needed for the current task:

| Topic            | When to load                                 | File                                                    |
| ---------------- | -------------------------------------------- | ------------------------------------------------------- |
| Site management  | Finding/creating/managing sites              | [site-management.md](./references/site-management.md)   |
| DocTypes         | Creating/modifying DocTypes, fields, naming  | [doctypes.md](./references/doctypes.md)                 |
| Controllers      | Document lifecycle, server logic             | [controllers.md](./references/controllers.md)           |
| Whitelisted APIs | REST endpoints, `@frappe.whitelist()`        | [api.md](./references/api.md)                           |
| Database & ORM   | `frappe.db`, queries, raw SQL                | [database.md](./references/database.md)                 |
| Caching          | Redis, `frappe.cache`                        | [caching.md](./references/caching.md)                   |
| Realtime         | WebSocket, `publish_realtime`                | [realtime.md](./references/realtime.md)                 |
| Background jobs  | `frappe.enqueue`, scheduled jobs             | [background-jobs.md](./references/background-jobs.md)   |
| Hooks            | `hooks.py` patterns                          | [hooks.md](./references/hooks.md)                       |
| Permissions      | Roles, DocType permissions, `has_permission` | [permissions.md](./references/permissions.md)           |
| Testing          | Writing & running tests                      | [testing.md](./references/testing.md)                   |
| Frontend & UI    | Desk UI, Vue SPA, portal pages               | [frontend.md](./references/frontend.md) (router → 3 sub-files) |
| Bench CLI        | All bench commands reference                 | [bench-operations.md](./references/bench-operations.md) |

# Local Demo Environment (`dev/demo.sh`)

Spin up a demo site with Ecuadorian seed data to exercise validation, the
NIIF chart of accounts, and tax templates before moving to Phase 6.

## Prerequisites

- Docker + Compose plugin, and a bench with `frappe`, `erpnext`
  (`version-16`) and this app installed (see `AGENTS.md` Ring 2).
- Free ports `3306`, `11001`, `13001` — or a healthy stack already
  listening there (`demo.sh up` reuses it and says so).

## Quickstart

```bash
dev/demo.sh up      # start MariaDB + Redis (or reuse a healthy stack)
dev/demo.sh reset   # drop/create site `demo`, install apps, migrate, seed
dev/demo.sh serve   # serve desk on http://127.0.0.1:8000 (see hosts note)
dev/demo.sh seed    # re-run the seed only
dev/demo.sh status  # containers + sites overview
dev/demo.sh down    # stop containers (volumes keep the data)
dev/demo.sh assets  # recompile frontend bundles (un styled pages = missing build; if bench build only refreshes translations, run `yarn run build --apps frappe --run-build-command` inside apps/frappe)
```

`reset` is idempotent: it always drops `demo` first, so re-running it
restores the exact default database.

## What Gets Seeded

`l10n_ec/ecuador_localization/demo_seed.py` creates (skipping what exists):

- Company **Demo Ecuador** (Ecuador, USD) — its creation fires the chart
  auto-install hook, so this also proves Phase 4 end to end.
- Customers **Demo Customer RUC** (`04` valid RUC), **Demo Final
  Consumer** (`07`), Supplier **Demo Supplier RUC** (`04`), each with a
  primary Billing address in Ecuador.
- A negative case: a throwaway customer with an invalid RUC is saved and
  must be **blocked** by the Phase 3 hook (`negative_blocked: true` in the
  report), then removed again.

`seed` prints a report: company, parties, `negative_blocked`, account
counts by root type, and the Item Tax Template titles for the company.

## Verification Checklist

1. `negative_blocked: true` in the seed report (validation hook fires).
2. Desk → Chart of Accounts for Demo Ecuador shows the NIIF tree with
   account numbers (Phase 4 installed, not Standard).
3. Desk → Item Tax Template list shows the twelve `Ecuador ...` templates.
4. Desk → edit Demo Customer RUC tax ID to garbage → save is rejected.

## Desk Access

`bench serve` binds `127.0.0.1:8000`; Frappe routes by Host header, so add
`127.0.0.1 demo` to `/etc/hosts` (needs sudo, one-time) and open
`http://demo:8000` (user `Administrator`, password `admin`). Without the
hosts entry, only CLI (`run-tests`, `execute`, `migrate`) works.

`bench start` (full Procfile) is intentionally not used here: it launches
its own `redis-server` processes, which requires a real server binary.
`bench serve` is enough to browse and validate forms.

## Troubleshooting

- `up` reports ports in use: another stack (e.g. the `test_site` bench
  containers) already serves them. Either reuse it (healthy check passes)
  or stop it first.
- Full database nuke: `docker compose -f dev/docker-compose.yml down -v`
  (destroys volumes), then `dev/demo.sh reset`.
- `BENCH_DIR` env overrides the default `~/frappe-bench-v16`.

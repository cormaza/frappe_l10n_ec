#!/bin/bash
# Local demo control for l10n_ec development. See docs/LOCAL_DEMO.md.
# Commands: up | reset | seed | serve | status | down | assets | sync | worker
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH_DIR="${BENCH_DIR:-$HOME/frappe-bench-v16}"
SITE="${DEMO_SITE:-demo}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-root}"
DB_PORT="${DB_PORT:-3306}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

need_bench() {
	if [ ! -d "$BENCH_DIR/apps/frappe" ] || [ ! -d "$BENCH_DIR/apps/erpnext" ]; then
		echo "error: bench with frappe+erpnext not found at $BENCH_DIR" >&2
		exit 1
	fi
}

ports_healthy() {
	python3 -c "
import socket, sys
for port in (11001, 13001, $DB_PORT):
    try:
        socket.create_connection(('127.0.0.1', port), timeout=3).close()
    except OSError:
        sys.exit(1)
" 2>/dev/null
}

cmd_up() {
	if (cd "$REPO_ROOT" && docker compose -f dev/docker-compose.yml up -d --wait 2>/dev/null); then
		echo "demo infra up (docker compose)"
	elif ports_healthy; then
		echo "ports busy but healthy: reusing the existing stack"
	else
		echo "error: could not start infra and ports are not healthy" >&2
		exit 1
	fi
}

cmd_reset() {
	need_bench
	cmd_sync
	cmd_up
	cd "$BENCH_DIR"
	if [ -d "sites/$SITE" ]; then
		bench drop-site "$SITE" --force --no-backup --mariadb-root-password "$DB_ROOT_PASSWORD"
	fi
	bench new-site "$SITE" \
		--db-host 127.0.0.1 \
		--db-port "$DB_PORT" \
		--mariadb-root-password "$DB_ROOT_PASSWORD" \
		--admin-password "$ADMIN_PASSWORD" \
		--no-mariadb-socket
	bench --site "$SITE" list-apps | grep -q "^erpnext$" || bench --site "$SITE" install-app erpnext
	bench --site "$SITE" list-apps | grep -q "^l10n_ec$" || bench --site "$SITE" install-app l10n_ec
	bench --site "$SITE" migrate
	bench --site "$SITE" set-config allow_tests true
	bench --site "$SITE" execute "frappe.db.set_single_value('System Settings', 'time_zone', 'America/Guayaquil')"
	bench --site "$SITE" execute "frappe.db.set_single_value('System Settings', 'language', 'es')"
	bench --site "$SITE" execute "[frappe.db.set_value('Installed Application', {'app_name': a}, 'is_setup_complete', 1) for a in ('frappe', 'erpnext', 'l10n_ec')]"
	cmd_seed
}

cmd_seed() {
	need_bench
	cd "$BENCH_DIR"
	bench --site "$SITE" clear-cache >/dev/null
	bench --site "$SITE" execute "frappe.get_attr('l10n_ec.ecuador_localization.demo_seed.seed_demo')()"
}

cmd_serve() {
	need_bench
	cd "$BENCH_DIR"
	echo "Serving desk on http://127.0.0.1:8000 (add '127.0.0.1 $SITE' to /etc/hosts, open http://$SITE:8000)"
	bench serve --port 8000
}

cmd_assets() {
	need_bench
	cd "$BENCH_DIR"
	bench build
}

cmd_sync() {
	need_bench
	if [ ! -d "$BENCH_DIR/apps/l10n_ec" ]; then
		echo "error: l10n_ec is not installed in $BENCH_DIR" >&2
		exit 1
	fi
	cd "$REPO_ROOT"
	find l10n_ec -type f \( -name "*.py" -o -name "*.js" -o -name "*.json" -o -name "*.xsd" \) -not -path "*/__pycache__/*" | while read -r f; do
		mkdir -p "$BENCH_DIR/apps/l10n_ec/$(dirname "$f")"
		cp "$f" "$BENCH_DIR/apps/l10n_ec/$f"
	done
	echo "synced working tree into bench (locale .po/.pot excluded: they flow bench -> repo)"
}

cmd_worker() {
	need_bench
	cd "$BENCH_DIR"
	echo "Starting RQ worker (all queues). Without it, enqueued jobs pile up and new submits fail with QueueOverloaded."
	bench worker --quiet
}

cmd_status() {	need_bench
	docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep -E "l10nec|demo" || echo "no demo containers running"
	cd "$BENCH_DIR"
	bench --site "$SITE" list-apps 2>/dev/null || echo "site $SITE does not exist yet (run: dev/demo.sh reset)"
}

cmd_validator() {
	# Opt-in SRI ATS validator sidecar (built from the sibling repo).
	# Bench reaches it at http://127.0.0.1:8080 (the app default); the SRI ATS
	# report shows its staleness indicator and Validar en DIMM button.
	VALIDATOR_CTX="${ATS_VALIDATOR_CONTEXT:-$REPO_ROOT/../docker_ats_validator}"
	if [ ! -f "$VALIDATOR_CTX/Dockerfile" ]; then
		echo "error: ats validator repo not found at $VALIDATOR_CTX" >&2
		echo "hint: clone cormaza/docker_ats_validator next to this repo, or set ATS_VALIDATOR_CONTEXT" >&2
		exit 1
	fi
	if ! ls "$VALIDATOR_CTX/target/"*.jar >/dev/null 2>&1; then
		SERVICE_DIR="${ATS_VALIDATOR_SERVICE:-$REPO_ROOT/../ats_validator_rest}"
		if [ ! -x "$SERVICE_DIR/gradlew" ]; then
			echo "error: no service jar in $VALIDATOR_CTX/target and no gradle project at $SERVICE_DIR" >&2
			exit 1
		fi
		echo "building validator jar (one-time, needs network)..."
		(cd "$SERVICE_DIR" && ./gradlew bootJar -q)
		cp "$SERVICE_DIR"/build/libs/*.jar "$VALIDATOR_CTX/target/"
	fi
	cd "$REPO_ROOT"
	ATS_VALIDATOR_CONTEXT="$VALIDATOR_CTX" docker compose -f dev/docker-compose.yml up -d --wait ats-validator
	curl -s --max-time 5 http://127.0.0.1:8080/version | head -c 200; echo
}

cmd_down() {
	cd "$REPO_ROOT"
	docker compose -f dev/docker-compose.yml down
}

case "${1:-status}" in
	up) cmd_up ;;
	reset) cmd_reset ;;
	seed) cmd_seed ;;
	serve) cmd_serve ;;
	assets) cmd_assets ;;
	sync) cmd_sync ;;
	worker) cmd_worker ;;
	status) cmd_status ;;
	down) cmd_down ;;
	validator) cmd_validator ;;
	*) echo "usage: dev/demo.sh {up|reset|seed|serve|status|down|assets|sync|validator|worker}" >&2; exit 1 ;;
esac

#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${FRAPPE_BENCH_ROOT:-/home/frappe/frappe-bench}"
SITES_DIR="${SITES_DIR:-${BENCH_DIR}/sites}"
SITE_NAME="${FRAPPE_SITE:?FRAPPE_SITE is required}"
DB_HOST="${DB_HOST:?DB_HOST is required}"
DB_PORT="${DB_PORT:-3306}"
REDIS_CACHE_URL="${REDIS_CACHE_URL:?REDIS_CACHE_URL is required}"
REDIS_QUEUE_URL="${REDIS_QUEUE_URL:?REDIS_QUEUE_URL is required}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

wait_for_tcp() {
	local name="$1"
	local host="$2"
	local port="$3"
	local timeout="${4:-120}"
	python - "$name" "$host" "$port" "$timeout" <<'PY'
import socket
import sys
import time

name, host, port, timeout = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
deadline = time.time() + timeout
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"{name} is reachable at {host}:{port}")
            sys.exit(0)
    except OSError:
        time.sleep(2)
print(f"Timed out waiting for {name} at {host}:{port}", file=sys.stderr)
sys.exit(1)
PY
}

wait_for_redis_url() {
	local name="$1"
	local url="$2"
	python - "$name" "$url" <<'PY'
from urllib.parse import urlparse
import socket
import sys
import time

name, url = sys.argv[1], sys.argv[2]
parsed = urlparse(url)
host = parsed.hostname
port = parsed.port or 6379
deadline = time.time() + 120
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"{name} is reachable at {host}:{port}")
            sys.exit(0)
    except OSError:
        time.sleep(2)
print(f"Timed out waiting for {name} at {host}:{port}", file=sys.stderr)
sys.exit(1)
PY
}

cd "${BENCH_DIR}"

wait_for_tcp "MariaDB" "${DB_HOST}" "${DB_PORT}" 180
wait_for_redis_url "Redis cache" "${REDIS_CACHE_URL}"
wait_for_redis_url "Redis queue" "${REDIS_QUEUE_URL}"

if [ -f "${SITES_DIR}/${SITE_NAME}/site_config.json" ]; then
	echo "Site ${SITE_NAME} already exists. Skipping site creation."
else
	if [ -z "${ADMIN_PASSWORD}" ]; then
		echo "ADMIN_PASSWORD is required for first site creation." >&2
		exit 1
	fi

	new_site_args=(
		"${SITE_NAME}"
		--db-type mariadb
		--db-host "${DB_HOST}"
		--db-port "${DB_PORT}"
		--admin-password "${ADMIN_PASSWORD}"
		--install-app erpnext
		--install-app transport_management
		--set-default
	)

	if [ -n "${DB_NAME:-}" ]; then
		new_site_args+=(--db-name "${DB_NAME}")
	fi
	if [ -n "${DB_USER:-}" ]; then
		new_site_args+=(--db-user "${DB_USER}")
	fi
	if [ -n "${DB_PASSWORD:-}" ]; then
		new_site_args+=(--db-password "${DB_PASSWORD}")
	fi
	if [ "${SETUP_DB:-1}" = "0" ]; then
		new_site_args+=(--no-setup-db)
	else
		new_site_args+=(--db-root-username "${DB_ROOT_USER:-root}")
		if [ -n "${DB_ROOT_PASSWORD:-}" ]; then
			new_site_args+=(--db-root-password "${DB_ROOT_PASSWORD}")
		fi
		new_site_args+=(--mariadb-user-host-login-scope "%")
	fi

	bench new-site "${new_site_args[@]}"
fi

bench --site "${SITE_NAME}" set-config db_host "${DB_HOST}"
bench --site "${SITE_NAME}" set-config db_port "${DB_PORT}"
bench --site "${SITE_NAME}" set-config redis_cache "${REDIS_CACHE_URL}"
bench --site "${SITE_NAME}" set-config redis_queue "${REDIS_QUEUE_URL}"
bench --site "${SITE_NAME}" set-config redis_socketio "${REDIS_SOCKETIO_URL:-${REDIS_QUEUE_URL}}"

bench --site "${SITE_NAME}" execute transport_management.setup.after_migrate
bench --site "${SITE_NAME}" clear-cache

echo "Bootstrap completed for ${SITE_NAME}."

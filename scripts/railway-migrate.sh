#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${FRAPPE_BENCH_ROOT:-/home/frappe/frappe-bench}"
SITE_NAME="${FRAPPE_SITE:?FRAPPE_SITE is required}"
MIGRATE_TIMEOUT="${RAILWAY_MIGRATE_TIMEOUT_SECONDS:-900}"

cd "${BENCH_DIR}"

echo "Running bench migrate for ${SITE_NAME} with ${MIGRATE_TIMEOUT}s timeout."
if ! timeout "${MIGRATE_TIMEOUT}" bench --site "${SITE_NAME}" migrate; then
	cat >&2 <<MSG
bench migrate failed or timed out.

Known development risk: migration may stall around:
  Removing orphan doctypes...
  Command: Sleep

Do not keep a production deploy blocked indefinitely. Inspect the Railway logs,
increase RAILWAY_MIGRATE_TIMEOUT_SECONDS only if progress is visible, or run
targeted reload/setup helpers manually after confirming schema state.
MSG
	exit 1
fi

bench --site "${SITE_NAME}" execute transport_management.setup.after_migrate
bench --site "${SITE_NAME}" clear-cache

echo "Migration completed for ${SITE_NAME}."

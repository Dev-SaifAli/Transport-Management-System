#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${FRAPPE_BENCH_ROOT:-/home/frappe/frappe-bench}"
SITES_DIR="${SITES_DIR:-${BENCH_DIR}/sites}"
SITE_NAME="${FRAPPE_SITE:-tms.localhost}"
START_MODE="${RAILWAY_START_MODE:-web}"
ENABLE_BACKGROUND="${RAILWAY_ENABLE_BACKGROUND_PROCESSES:-0}"

export PATH="/home/frappe/.local/bin:${PATH}"
export FRAPPE_BENCH_ROOT="${BENCH_DIR}"
export SITES_DIR
export SITES_PATH="${SITES_PATH:-${SITES_DIR}}"
export FRAPPE_SITE="${SITE_NAME}"

if ! command -v bench >/dev/null 2>&1; then
	echo "bench command is not available on PATH" >&2
	exit 127
fi

mkdir -p "${BENCH_DIR}/logs" "${SITES_DIR}"
cd "${BENCH_DIR}"

pids=()
shutting_down=0

start_process() {
	local name="$1"
	shift

	echo "Starting ${name}..."
	(
		exec "$@"
	) > >(sed -u "s/^/[${name}] /") 2> >(sed -u "s/^/[${name}] /" >&2) &

	pids+=("$!")
}

shutdown() {
	local status="${1:-0}"

	if [[ "${shutting_down}" -eq 1 ]]; then
		exit "${status}"
	fi

	shutting_down=1
	echo "Stopping Railway Frappe processes..."

	if [[ "${#pids[@]}" -gt 0 ]]; then
		kill -TERM "${pids[@]}" 2>/dev/null || true

		local deadline=$((SECONDS + ${RAILWAY_SHUTDOWN_TIMEOUT_SECONDS:-30}))
		while [[ "${SECONDS}" -lt "${deadline}" ]]; do
			local alive=0
			for pid in "${pids[@]}"; do
				if kill -0 "${pid}" 2>/dev/null; then
					alive=1
					break
				fi
			done

			[[ "${alive}" -eq 0 ]] && break
			sleep 1
		done

		kill -KILL "${pids[@]}" 2>/dev/null || true
	fi

	exit "${status}"
}

trap 'shutdown 0' TERM INT

start_process "web" \
	"${BENCH_DIR}/env/bin/gunicorn" \
	--chdir "${SITES_DIR}" \
	--bind "0.0.0.0:${PORT:-8000}" \
	--workers "${GUNICORN_WORKERS:-2}" \
	--threads "${GUNICORN_THREADS:-4}" \
	--timeout "${GUNICORN_TIMEOUT:-120}" \
	transport_management.railway_wsgi:application \
	--preload

if [[ "${START_MODE}" == "all" || "${ENABLE_BACKGROUND}" == "1" ]]; then
	start_process "scheduler" bench schedule
	start_process "worker-short" bench worker --queue short
	start_process "worker-default" bench worker --queue default
	start_process "worker-long" bench worker --queue long
else
	echo "Background processes disabled; running web only."
	echo "Set RAILWAY_START_MODE=all or RAILWAY_ENABLE_BACKGROUND_PROCESSES=1 after restore/migration approval."
fi

set +e
wait -n
exit_status=$?

if [[ "${shutting_down}" -eq 0 ]]; then
	echo "A Railway Frappe process exited with status ${exit_status}; stopping remaining processes." >&2
	shutdown "${exit_status}"
fi

exit "${exit_status}"

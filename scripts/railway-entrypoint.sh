#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${FRAPPE_BENCH_ROOT:-/home/frappe/frappe-bench}"
SITES_DIR="${SITES_DIR:-${BENCH_DIR}/sites}"
SITES_PATH="${SITES_PATH:-${SITES_DIR}}"
SITE_NAME="${FRAPPE_SITE:-tms.localhost}"
SITES_TEMPLATE_DIR="${SITES_TEMPLATE_DIR:-/opt/frappe/sites-template}"

mkdir -p "${SITES_DIR}"

if [ ! -f "${SITES_DIR}/apps.txt" ] && [ -d "${SITES_TEMPLATE_DIR}" ]; then
	cp -a "${SITES_TEMPLATE_DIR}/." "${SITES_DIR}/"
fi

# Synchronize Bench apps from the Docker image with the persistent volume.
TEMPLATE_APPS="${SITES_TEMPLATE_DIR}/apps.txt"
PERSISTENT_APPS="${SITES_DIR}/apps.txt"

if [[ -f "${TEMPLATE_APPS}" && -f "${PERSISTENT_APPS}" ]]; then
        (
                flock -x 9

                TEMP_APPS="$(mktemp "${SITES_DIR}/.apps-sync.XXXXXX")"
                trap 'rm -f "${TEMP_APPS}"' EXIT

                cp "${PERSISTENT_APPS}" "${TEMP_APPS}"

                while IFS= read -r app || [[ -n "${app}" ]]; do
                        [[ -z "${app}" ]] && continue

                        if ! grep -Fxq -- "${app}" "${TEMP_APPS}"; then
                                # Add a newline if the last existing line has none.
                                if [[ -s "${TEMP_APPS}" ]] &&
                                   [[ "$(tail -c 1 "${TEMP_APPS}" | wc -l)" -eq 0 ]]; then
                                        printf '\n' >> "${TEMP_APPS}"
                                fi

                                printf '%s\n' "${app}" >> "${TEMP_APPS}"
                                echo "Registered Bench app: ${app}"
                        fi
                done < "${TEMPLATE_APPS}"

                if ! cmp -s "${PERSISTENT_APPS}" "${TEMP_APPS}"; then
        chmod --reference="${PERSISTENT_APPS}" "${TEMP_APPS}"
        chown --reference="${PERSISTENT_APPS}" "${TEMP_APPS}"
        mv -f "${TEMP_APPS}" "${PERSISTENT_APPS}"
fi
        ) 9>"${SITES_DIR}/.apps-sync.lock"
fi

if [ -d "${SITES_TEMPLATE_DIR}/assets" ]; then
	rm -rf "${SITES_DIR}/assets"
	cp -a "${SITES_TEMPLATE_DIR}/assets" "${SITES_DIR}/assets"
	chown -hR frappe:frappe "${SITES_DIR}/assets" 2>/dev/null || true
fi

python - <<'PY'
import json
import os
from pathlib import Path

bench_dir = Path(os.environ.get("FRAPPE_BENCH_ROOT", "/home/frappe/frappe-bench"))
sites_dir = Path(os.environ.get("SITES_DIR", str(bench_dir / "sites")))
site_name = os.environ.get("FRAPPE_SITE", "tms.localhost")

config_path = sites_dir / "common_site_config.json"
if config_path.exists():
    config = json.loads(config_path.read_text() or "{}")
else:
    config = {}

def set_if_env(key, env_name, cast=str):
    value = os.environ.get(env_name)
    if value not in (None, ""):
        config[key] = cast(value)

set_if_env("db_host", "DB_HOST")
set_if_env("db_port", "DB_PORT", int)
set_if_env("redis_cache", "REDIS_CACHE_URL")
set_if_env("redis_queue", "REDIS_QUEUE_URL")
config["redis_socketio"] = os.environ.get(
    "REDIS_SOCKETIO_URL",
    os.environ.get("REDIS_QUEUE_URL", config.get("redis_socketio", "redis://redis-queue:6379")),
)
config["socketio_port"] = int(os.environ.get("FRAPPE_SOCKETIO_PORT", os.environ.get("SOCKETIO_PORT", config.get("socketio_port", 9000))))
config["serve_default_site"] = True
config["default_site"] = site_name
config["frappe_user"] = os.environ.get("FRAPPE_USER", "frappe")
config.pop("developer_mode", None)
config.pop("live_reload", None)
config.pop("file_watcher_port", None)

sites_dir.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(config, indent=1, sort_keys=True) + "\n")
PY

if [[ " $* " == *"gunicorn"* ]]; then
	if [ "$(id -u)" = "0" ] && id frappe >/dev/null 2>&1 && command -v runuser >/dev/null 2>&1; then
		runuser -u frappe -- env \
			FRAPPE_SITE="${SITE_NAME}" \
			SITES_PATH="${SITES_PATH}" \
			FRAPPE_BENCH_ROOT="${BENCH_DIR}" \
			"${BENCH_DIR}/env/bin/python" "${BENCH_DIR}/railway-clear-asset-cache.py"
	else
		FRAPPE_SITE="${SITE_NAME}" \
			SITES_PATH="${SITES_PATH}" \
			FRAPPE_BENCH_ROOT="${BENCH_DIR}" \
			"${BENCH_DIR}/env/bin/python" "${BENCH_DIR}/railway-clear-asset-cache.py"
	fi
fi
# Optional HRMS installation for an explicitly authorized deployment.
if [[ "${RAILWAY_INSTALL_HRMS:-0}" == "1" ]]; then
        if [[ " $* " == *"gunicorn"* ]]; then
                echo "HRMS installation enabled for ${SITE_NAME}."

                FRAPPE_SITE="${SITE_NAME}" \
                FRAPPE_BENCH_ROOT="${BENCH_DIR}" \
                SITES_DIR="${SITES_DIR}" \
                bash "${BENCH_DIR}/railway-install-hrms.sh"
        fi
fi

exec "$@"

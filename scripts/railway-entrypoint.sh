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

exec "$@"

#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${FRAPPE_BENCH_ROOT:-/home/frappe/frappe-bench}"
SITES_DIR="${SITES_DIR:-${BENCH_DIR}/sites}"
SITES_PATH="${SITES_PATH:-${SITES_DIR}}"
SITE_NAME="${FRAPPE_SITE:-tms.localhost}"
SITES_TEMPLATE_DIR="${SITES_TEMPLATE_DIR:-/opt/frappe/sites-template}"

mkdir -p "${SITES_DIR}"

if [[ -L "${SITES_DIR}" ]]; then
	echo "Refusing to prepare symlinked sites directory: ${SITES_DIR}" >&2
	exit 1
fi

BENCH_DIR_REAL="$(realpath -e -- "${BENCH_DIR}")"
SITES_DIR_REAL="$(realpath -e -- "${SITES_DIR}")"
if [[ "${SITES_DIR_REAL}" != "${BENCH_DIR_REAL}/sites" ]]; then
	echo "Refusing to prepare unexpected sites directory: ${SITES_DIR_REAL}" >&2
	exit 1
fi

if [[ "$(id -u)" == "0" ]]; then
	if ! id frappe >/dev/null 2>&1 || ! command -v runuser >/dev/null 2>&1; then
		echo "Root startup requires the frappe user and runuser to prepare the volume safely." >&2
		exit 1
	fi

	FRAPPE_UID="$(id -u frappe)"
	FRAPPE_GID="$(id -g frappe)"
	OWNERSHIP_MARKER="${SITES_DIR_REAL}/.railway-volume-owner-v1"

	if [[ ! -f "${OWNERSHIP_MARKER}" || -L "${OWNERSHIP_MARKER}" ]] ||
		[[ "$(stat -c '%u:%g' "${OWNERSHIP_MARKER}" 2>/dev/null || true)" != "${FRAPPE_UID}:${FRAPPE_GID}" ]]; then
		echo "Preparing sites volume ownership for frappe (${FRAPPE_UID}:${FRAPPE_GID})..."
		# Limit repair to this mount, without following symlinks or crossing filesystems.
		find "${SITES_DIR_REAL}" -xdev \( -type d -o -type f \) \
			\( ! -uid "${FRAPPE_UID}" -o ! -gid "${FRAPPE_GID}" \) \
			-exec chown -h "${FRAPPE_UID}:${FRAPPE_GID}" {} +
		find "${SITES_DIR_REAL}" -xdev \( -type d -o -type f \) \
			-exec chmod u+rwX {} +
		install -o "${FRAPPE_UID}" -g "${FRAPPE_GID}" -m 600 /dev/null "${OWNERSHIP_MARKER}"
	fi
elif [[ "$(id -u)" != "$(id -u frappe)" ]]; then
	echo "Runtime must start as root for volume preparation or as the frappe user." >&2
	exit 1
elif [[ ! -w "${SITES_DIR}" ]]; then
	echo "Sites directory is not writable by frappe: ${SITES_DIR}" >&2
	exit 1
fi

if [ ! -f "${SITES_DIR}/apps.txt" ] && [ -d "${SITES_TEMPLATE_DIR}" ]; then
	cp -a -n "${SITES_TEMPLATE_DIR}/." "${SITES_DIR}/"
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
	mkdir -p "${SITES_DIR}/assets"
	if [[ "$(id -u)" == "0" ]]; then
		chown "${FRAPPE_UID}:${FRAPPE_GID}" "${SITES_DIR}/assets"
	fi
	cp -a "${SITES_TEMPLATE_DIR}/assets/." "${SITES_DIR}/assets/"
fi

"${BENCH_DIR}/env/bin/python" - <<'PY'
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

if [[ " $* " == *"gunicorn"* || " $* " == *"railway-start-all.sh"* ]]; then
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

# Run application processes as frappe, never root.
if [[ "$(id -u)" == "0" ]]; then
    echo "Preparing Frappe runtime permissions..."

    # Fix only root-owned files in the Bench logs directory.
    if [[ -d "${BENCH_DIR}/logs" ]]; then
        find "${BENCH_DIR}/logs" \
            -maxdepth 1 -type f -user root \
            -exec chown frappe:frappe {} +
    fi

    # Fix only root-owned files in site logs directories.
    if [[ -d "${SITES_DIR}" ]]; then
        while IFS= read -r -d '' log_dir; do
            find "$log_dir" -maxdepth 1 -type f -user root \
                -exec chown frappe:frappe {} +
        done < <(
            find "${SITES_DIR}" \
                -mindepth 2 -maxdepth 2 -type d -name "logs" \
                -print0
        )
    fi

    # Entrypoint may have written this configuration as root.
    if [[ -f "${SITES_DIR}/common_site_config.json" ]]; then
        chown frappe:frappe "${SITES_DIR}/common_site_config.json"
    fi

    # Perform installation as the frappe user.
    if [[ "${RAILWAY_INSTALL_HRMS:-0}" == "1" ]] &&
       [[ " $* " == *"gunicorn"* ]]; then
        echo "Starting guarded HRMS installation as frappe..."

        runuser -u frappe -- env \
            HOME=/home/frappe \
            PATH="/home/frappe/.local/bin:${PATH}" \
            FRAPPE_SITE="${SITE_NAME}" \
            FRAPPE_BENCH_ROOT="${BENCH_DIR}" \
            SITES_DIR="${SITES_DIR}" \
            bash "${BENCH_DIR}/railway-install-hrms.sh"
    fi

    echo "Starting application as frappe..."
    exec runuser -u frappe -- "$@"
fi

# Also support Docker environments already running as frappe.
if [[ "${RAILWAY_INSTALL_HRMS:-0}" == "1" ]] &&
   [[ " $* " == *"gunicorn"* ]]; then
    FRAPPE_SITE="${SITE_NAME}" \
    FRAPPE_BENCH_ROOT="${BENCH_DIR}" \
    SITES_DIR="${SITES_DIR}" \
    bash "${BENCH_DIR}/railway-install-hrms.sh"
fi

exec "$@"

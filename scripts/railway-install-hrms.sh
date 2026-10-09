#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${FRAPPE_BENCH_ROOT:-/home/frappe/frappe-bench}"
SITES_DIR="${SITES_DIR:-${BENCH_DIR}/sites}"
SITE_NAME="${FRAPPE_SITE:?FRAPPE_SITE is required}"

cd "${BENCH_DIR}"

SITE_CONFIG="${SITES_DIR}/${SITE_NAME}/site_config.json"

# Never create or recreate a site.
if [[ ! -f "${SITE_CONFIG}" ]]; then
    echo "ERROR: Existing site configuration not found: ${SITE_CONFIG}" >&2
    exit 1
fi

# HRMS must already be included in the Docker image.
if [[ ! -d "${BENCH_DIR}/apps/hrms" ]]; then
    echo "ERROR: HRMS is missing from the Docker image." >&2
    exit 1
fi

# Store the lock on the persistent sites volume.
LOCK_FILE="${SITES_DIR}/.hrms-install.lock"
exec 9>"${LOCK_FILE}"

# Prevent simultaneous installation attempts.
flock -w 300 9 || {
    echo "ERROR: Could not acquire HRMS installation lock." >&2
    exit 1
}

if ! INSTALLED_APPS="$(bench --site "${SITE_NAME}" list-apps)"; then
    echo "ERROR: Could not read installed apps for ${SITE_NAME}." >&2
    exit 1
fi

if printf '%s\n' "${INSTALLED_APPS}" | awk '{print $1}' | grep -qx 'hrms'; then
    echo "HRMS is already installed on ${SITE_NAME}. Skipping."
    exit 0
fi

echo "HRMS is missing from ${SITE_NAME}. Installing..."

INSTALL_TIMEOUT="${HRMS_INSTALL_TIMEOUT_SECONDS:-900}"

echo "Installing HRMS with ${INSTALL_TIMEOUT}s timeout..."

if ! timeout "${INSTALL_TIMEOUT}" bench --site "${SITE_NAME}" install-app hrms; then
    echo "ERROR: HRMS installation failed or timed out." >&2
    echo "Inspect installation logs and database state before retrying." >&2
    exit 1
fi

echo "HRMS installation command completed successfully."

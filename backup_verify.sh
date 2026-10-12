#!/bin/bash
set -euo pipefail

BACKUP_DIR="/home/frappe/backups/al-rana-20261012"
DATE=$(date +%Y%m%d-%H%M%S)

echo "=== PRE-DEPLOY BACKUP WITH VERIFICATION ==="

# 1. Fresh DB backup with verification
DB_BACKUP="${BACKUP_DIR}/pre-deploy-db-backup-$(date +%Y%m%d-%H%M%S).sql.gz"
echo "Creating DB backup: ${DB_BACKUP}"
mariadb-dump --skip-ssl --single-transaction --quick --routines --triggers \
  -h mariadb.railway.internal -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" \
  | gzip > "${DB_BACKUP}"

if [ ! -s "${DB_BACKUP}" ]; then
    echo "ERROR: DB backup empty or failed"
    exit 1
fi

DB_SHA=$(sha256sum "${DB_BACKUP}" | awk '{print $1}')
echo "DB backup SHA256: ${DB_SHA}"

# 2. Fresh files backup with verification
FILES_BACKUP="${BACKUP_DIR}/pre-deploy-files-$(date +%Y%m%d-%H%M%S).tar.gz"
echo "Creating files backup: ${FILES_BACKUP}"
tar -czf "${FILES_BACKUP}" -C /home/frappe/frappe-bench/sites/tms-staging public private

if [ ! -s "${FILES_BACKUP}" ]; then
    echo "ERROR: Files backup empty or failed"
    exit 1
fi

FILES_SHA=$(sha256sum "${FILES_BACKUP}" | awk '{print $1}')
echo "Files backup SHA256: ${FILES_SHA}"

# 4. Copy to offsite location
OFFSITE_DIR="/home/frappe/offsite-backups/al-rana-20261012"
mkdir -p "${OFFSITE_DIR}"
cp "${DB_BACKUP}" "${OFFSITE_DIR}/"
cp "${FILES_BACKUP}" "${OFFSITE_DIR}/"

# 5. Verify offsite copies
OFFSITE_DB_SHA=$(sha256sum "${OFFSITE_DIR}/$(basename ${DB_BACKUP})" | awk '{print $1}')
OFFSITE_FILES_SHA=$(sha256sum "${OFFSITE_DIR}/$(basename ${FILES_BACKUP})" | awk '{print $1}')

if [ "${DB_SHA}" != "${OFFSITE_DB_SHA}" ]; then
    echo "ERROR: Offsite DB backup checksum mismatch"
    exit 1
fi
if [ "${FILES_SHA}" != "${OFFSITE_FILES_SHA}" ]; then
    echo "ERROR: Offsite files backup checksum mismatch"
    exit 1
fi

echo "=== BACKUP COMPLETE ==="
echo "DB backup: ${DB_BACKUP} (SHA: ${DB_SHA})"
echo "Files backup: ${FILES_BACKUP} (SHA: ${FILES_SHA})"
echo "Offsite copies verified"

# Save manifest
cat > "${BACKUP_DIR}/pre-deploy-manifest-$(date +%Y%m%d-%H%M%S).txt" << EOF
DB_BACKUP=${DB_BACKUP}
DB_SHA256=${DB_SHA}
FILES_BACKUP=${FILES_BACKUP}
FILES_SHA256=${FILES_SHA}
TIMESTAMP=$(date -Iseconds)
EOF

echo "Manifest saved"

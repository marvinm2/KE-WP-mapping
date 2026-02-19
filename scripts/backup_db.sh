#!/bin/bash
# /app/scripts/backup_db.sh
# SQLite backup using Online Backup API (safe during active writes).
# Schedule: daily at 02:00 container time. Retention: 7 days.
# Source: https://sqlite.org/backup.html
set -euo pipefail

DB_PATH="/app/data/ke_wp_mapping.db"
BACKUP_DIR="/app/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/ke_wp_mapping_${TIMESTAMP}.db"
RETENTION_DAYS=7

mkdir -p "${BACKUP_DIR}"

# .backup uses the Online Backup API: checkpoints WAL, then copies atomically.
# DO NOT back up just the .db file without the -wal and -shm files;
# always use this script to get a consistent snapshot.
sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"

# Integrity check — remove backup if corrupted
RESULT=$(sqlite3 "${BACKUP_FILE}" "PRAGMA integrity_check;")
if [ "${RESULT}" != "ok" ]; then
    echo "[BACKUP ERROR] Integrity check failed for ${BACKUP_FILE}: ${RESULT}" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

echo "[BACKUP OK] ${BACKUP_FILE}"

# Prune backups older than retention period
find "${BACKUP_DIR}" -name "ke_wp_mapping_*.db" -mtime "+${RETENTION_DAYS}" -delete

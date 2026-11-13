#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="${BACKUP_DIR}/turnos_${STAMP}.dump"

mkdir -p "${BACKUP_DIR}"

docker compose exec -T db pg_dump \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${POSTGRES_DB:-turnos}" \
  --format=custom \
  --no-owner \
  --no-acl \
  > "${FILE}"

find "${BACKUP_DIR}" -name 'turnos_*.dump' -type f -mtime "+${RETENTION_DAYS}" -delete

echo "Backup creado: ${FILE}"

#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Uso: $0 <archivo.dump>" >&2
  exit 1
fi

FILE="$1"
if [[ ! -f "${FILE}" ]]; then
  echo "No existe el archivo: ${FILE}" >&2
  exit 1
fi

docker compose exec -T db pg_restore \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${POSTGRES_DB:-turnos}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  < "${FILE}"

echo "Restore completado desde: ${FILE}"

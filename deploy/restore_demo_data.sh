#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DB_NAME="${ODOO_DB_NAME:-odoo19}"
DB_DUMP_PATH="${DB_DUMP_PATH:-$ROOT_DIR/deploy/exports/${DB_NAME}.dump}"
FILESTORE_TGZ_PATH="${FILESTORE_TGZ_PATH:-$ROOT_DIR/deploy/exports/${DB_NAME}-filestore.tgz}"

if [[ ! -f "$DB_DUMP_PATH" ]]; then
  echo "Missing DB dump: $DB_DUMP_PATH" >&2
  exit 1
fi

echo "Restoring PostgreSQL dump into database service..."
docker compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE ${DB_NAME} OWNER odoo;"
docker compose exec -T db pg_restore -U odoo -d postgres --clean --if-exists --create < "$DB_DUMP_PATH"

if [[ -f "$FILESTORE_TGZ_PATH" ]]; then
  echo "Restoring filestore tarball..."
  docker compose exec -T web mkdir -p "/var/lib/odoo/filestore/${DB_NAME}"
  docker compose exec -T web rm -rf "/var/lib/odoo/filestore/${DB_NAME}"
  docker compose exec -T web mkdir -p /var/lib/odoo/filestore
  docker compose exec -T web tar -C /var/lib/odoo -xzf - < "$FILESTORE_TGZ_PATH"
else
  echo "No filestore tarball found at $FILESTORE_TGZ_PATH; skipping filestore restore."
fi

echo "Restore complete."

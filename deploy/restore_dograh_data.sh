#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DOGRAH_DB_DUMP_PATH="${DOGRAH_DB_DUMP_PATH:-$ROOT_DIR/deploy/exports/dograh-postgres.dump}"
DOGRAH_MINIO_TGZ_PATH="${DOGRAH_MINIO_TGZ_PATH:-$ROOT_DIR/deploy/exports/dograh-minio-data.tgz}"

if [[ ! -f "$DOGRAH_DB_DUMP_PATH" ]]; then
  echo "Missing Dograh DB dump: $DOGRAH_DB_DUMP_PATH" >&2
  exit 1
fi

echo "Restoring Dograh PostgreSQL dump..."
docker compose exec -T dograh-postgres psql -U postgres -d postgres -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
docker compose exec -T dograh-postgres pg_restore -U postgres -d postgres --clean --if-exists --no-owner --no-privileges < "$DOGRAH_DB_DUMP_PATH"

if [[ -f "$DOGRAH_MINIO_TGZ_PATH" ]]; then
  echo "Restoring Dograh MinIO data..."
  docker compose stop dograh-minio
  TMP_DIR="/private/tmp/dojong-dograh-minio-restore"
  rm -rf "$TMP_DIR"
  mkdir -p "$TMP_DIR"
  tar -C "$TMP_DIR" -xzf "$DOGRAH_MINIO_TGZ_PATH"
  docker cp "$TMP_DIR/dograh-minio-data/." dojong-odoo19-dograh-minio-1:/data
  rm -rf "$TMP_DIR"
  docker compose start dograh-minio
else
  echo "No Dograh MinIO tarball found at $DOGRAH_MINIO_TGZ_PATH; skipping MinIO restore."
fi

echo "Dograh restore complete."

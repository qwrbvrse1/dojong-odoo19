#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-/private/tmp/dojong-demo-bundle-$(date +%Y%m%d-%H%M%S)}"
ARCHIVE_NAME="${2:-dojong-odoo19-demo-bundle.tgz}"

mkdir -p "$OUT_DIR"

STAGE_DIR="$OUT_DIR/dojong-odoo19"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

rsync -a \
  --exclude '.git' \
  --exclude '.DS_Store' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.codex' \
  --exclude '.claude' \
  --exclude 'odoo-web-data' \
  --exclude 'node_modules' \
  "$ROOT_DIR/" "$STAGE_DIR/"

cat > "$STAGE_DIR/deploy/DEPLOY_README.md" <<'EOF'
# Demo Deploy Notes

## Required files

Place these in `deploy/exports/` before bootstrap:

- `odoo19.dump`
- `odoo19-filestore.tgz`
- `dograh-postgres.dump`
- `dograh-minio-data.tgz`

## 1. Build images

```bash
./deploy/build_images.sh
```

## 2. Start services

```bash
./deploy/server_up.sh
```

## 3. Restore DB + filestore

```bash
./deploy/restore_demo_data.sh
```

## 4. Apply demo config

Set env vars as needed:

- `PUBLIC_DOMAIN`
- `PORTALOPS_GOOGLE_MAPS_GROUNDING_API_KEY`
- `PORTALOPS_GOOGLE_MAPS_BROWSER_API_KEY`
- `PORTALOPS_DOGRAH_API_KEY`
- `PORTALOPS_DOGRAH_API_BASE_URL`
- `PORTALOPS_DOGRAH_UI_BASE_URL`
- `PORTALOPS_DOGRAH_START_URL`
- `PORTALOPS_DOGRAH_AUTH_EMAIL`
- `PORTALOPS_DOGRAH_AUTH_PASSWORD`
- `PORTALOPS_DOGRAH_WEBHOOK_SECRET`
- `PORTALOPS_DOGRAH_FLOW_ID`
- `PORTALOPS_DOGRAH_LOW_VISION_FLOW_ID`
- `PORTALOPS_DOGRAH_EMBED_TOKEN`

Then run:

```bash
./deploy/apply_demo_config.sh
```

## 5. Restore Dograh data

```bash
./deploy/restore_dograh_data.sh
```

## 6. Upgrade module

```bash
docker compose exec -T web /bin/bash -lc "python3 /opt/odoo/odoo-bin -c /etc/odoo/odoo.conf -d odoo19 -u portalops_demo --stop-after-init --no-http"
docker compose restart web
```

## 7. Reverse proxy with Caddy

If Caddy is already running on the server:

```bash
sudo caddy reload --config /etc/caddy/Caddyfile
```

## 8. One-shot path

```bash
./deploy/bootstrap_demo_server.sh
```

## 9. Public routes

- `/` and `/p/atl-midtown` -> Odoo on `127.0.0.1:8070`
- `/api/v1/*` -> Dograh API on `127.0.0.1:8000`
- `/dograh*`, `/auth*`, `/workflow*` -> Dograh UI on `127.0.0.1:3010`
EOF

(
  cd "$OUT_DIR"
  tar -czf "$ARCHIVE_NAME" "dojong-odoo19"
)

echo "Bundle created:"
echo "$OUT_DIR/$ARCHIVE_NAME"

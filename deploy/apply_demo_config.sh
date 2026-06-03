#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DB_NAME="${ODOO_DB_NAME:-odoo19}"

export PORTALOPS_GOOGLE_MAPS_GROUNDING_API_KEY="${PORTALOPS_GOOGLE_MAPS_GROUNDING_API_KEY:-}"
export PORTALOPS_GOOGLE_MAPS_BROWSER_API_KEY="${PORTALOPS_GOOGLE_MAPS_BROWSER_API_KEY:-}"
export PORTALOPS_DOGRAH_API_KEY="${PORTALOPS_DOGRAH_API_KEY:-}"
export PORTALOPS_DOGRAH_API_BASE_URL="${PORTALOPS_DOGRAH_API_BASE_URL:-http://127.0.0.1:8000}"
export PORTALOPS_DOGRAH_UI_BASE_URL="${PORTALOPS_DOGRAH_UI_BASE_URL:-https://${PUBLIC_DOMAIN:-qwrbql-demo.prdops.dev}/dograh}"
export PORTALOPS_DOGRAH_START_URL="${PORTALOPS_DOGRAH_START_URL:-http://127.0.0.1:8000}"
export PORTALOPS_DOGRAH_AUTH_EMAIL="${PORTALOPS_DOGRAH_AUTH_EMAIL:-}"
export PORTALOPS_DOGRAH_AUTH_PASSWORD="${PORTALOPS_DOGRAH_AUTH_PASSWORD:-}"
export PORTALOPS_DOGRAH_WEBHOOK_SECRET="${PORTALOPS_DOGRAH_WEBHOOK_SECRET:-}"
export PORTALOPS_DOGRAH_FLOW_ID="${PORTALOPS_DOGRAH_FLOW_ID:-}"
export PORTALOPS_DOGRAH_LOW_VISION_FLOW_ID="${PORTALOPS_DOGRAH_LOW_VISION_FLOW_ID:-}"
export PORTALOPS_DOGRAH_EMBED_TOKEN="${PORTALOPS_DOGRAH_EMBED_TOKEN:-}"

docker compose exec -T web /bin/bash -lc "python3 /opt/odoo/odoo-bin shell -c /etc/odoo/odoo.conf -d ${DB_NAME} --no-http <<'PY'
import os
env['ir.config_parameter'].sudo().set_param('portalops_demo.google_maps_grounding_api_key', os.environ.get('PORTALOPS_GOOGLE_MAPS_GROUNDING_API_KEY', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.google_maps_browser_api_key', os.environ.get('PORTALOPS_GOOGLE_MAPS_BROWSER_API_KEY', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_api_key', os.environ.get('PORTALOPS_DOGRAH_API_KEY', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_api_base_url', os.environ.get('PORTALOPS_DOGRAH_API_BASE_URL', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_ui_base_url', os.environ.get('PORTALOPS_DOGRAH_UI_BASE_URL', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_start_url', os.environ.get('PORTALOPS_DOGRAH_START_URL', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_auth_email', os.environ.get('PORTALOPS_DOGRAH_AUTH_EMAIL', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_auth_password', os.environ.get('PORTALOPS_DOGRAH_AUTH_PASSWORD', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_webhook_secret', os.environ.get('PORTALOPS_DOGRAH_WEBHOOK_SECRET', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_flow_id', os.environ.get('PORTALOPS_DOGRAH_FLOW_ID', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_low_vision_flow_id', os.environ.get('PORTALOPS_DOGRAH_LOW_VISION_FLOW_ID', ''))
env['ir.config_parameter'].sudo().set_param('portalops_demo.dograh_embed_token', os.environ.get('PORTALOPS_DOGRAH_EMBED_TOKEN', ''))
print('PortalOps demo config applied.')
PY"


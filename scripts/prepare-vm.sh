#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CORE_MODULES=(
  dojo_core
  subscription_oca
  dojo_subscriptions
  dojo_onboarding
  bi_all_digital_sign
  dojo_sign
)

join_by_comma() {
  local IFS=","
  echo "$*"
}

MODULE_LIST="$(join_by_comma "${CORE_MODULES[@]}")"

echo "==> Bootstrapping local Odoo source and config"
./scripts/bootstrap_worktree_odoo.sh

echo "==> Building Docker images"
docker compose build

echo "==> Starting Docker services"
docker compose up -d

echo "==> Waiting for Odoo web endpoint"
for _ in $(seq 1 30); do
  if curl -fsSI http://127.0.0.1:8070/web/login >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsSI http://127.0.0.1:8070/web/login >/dev/null 2>&1; then
  echo "Odoo web endpoint did not become ready on http://127.0.0.1:8070/web/login" >&2
  docker compose ps
  docker compose logs --tail=200 web || true
  exit 1
fi

echo "==> Installing core Dojo modules into database odoo19"
docker compose stop web
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf \
  -d odoo19 \
  --workers=0 \
  --max-cron-threads=0 \
  --no-http \
  -i "$MODULE_LIST" \
  --stop-after-init

echo "==> Restarting web after module installation"
docker compose up -d web

echo "==> Verifying module install states"
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web shell -c /etc/odoo/odoo.conf -d odoo19 <<'PY'
names = [
    'dojo_core',
    'subscription_oca',
    'dojo_subscriptions',
    'dojo_onboarding',
    'bi_all_digital_sign',
    'dojo_sign',
]
states = {}
for name in names:
    mod = env['ir.module.module'].search([('name', '=', name)], limit=1)
    states[name] = mod.state if mod else 'MISSING'
    print(name, states[name])

bad = {k: v for k, v in states.items() if v != 'installed'}
if bad:
    raise SystemExit(f"Module verification failed: {bad}")
PY

echo "==> Verifying core model availability"
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web shell -c /etc/odoo/odoo.conf -d odoo19 <<'PY'
print("dojo.member", env['dojo.member'].search_count([]))
print("dojo.class.session", env['dojo.class.session'].search_count([]))
print("dojo.class.enrollment", env['dojo.class.enrollment'].search_count([]))
print("dojo.onboarding.record", env['dojo.onboarding.record'].search_count([]))
print("sale.subscription", env['sale.subscription'].search_count([]))
PY

echo "==> Final container status"
docker compose ps

echo
echo "VM preparation complete."
echo "Core Dojo modules are installed and verified against database odoo19."

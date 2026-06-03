#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d odoo ]; then
  echo "Cloning Odoo saas-19.2 into ./odoo ..."
  git clone --depth=1 --branch saas-19.2 https://github.com/odoo/odoo ./odoo
else
  echo "./odoo already exists"
fi

mkdir -p enterprise

if [ ! -f config/odoo.conf ]; then
  echo "Creating config/odoo.conf from example ..."
  cp config/odoo.conf.example config/odoo.conf
else
  echo "config/odoo.conf already exists"
fi

echo "Bootstrap complete."
echo "Next steps:"
echo "  docker compose build"
echo "  docker compose up -d"
echo "  docker compose run --rm web --config=/etc/odoo/odoo.conf -d odoo19 -i dojo_core,subscription_oca,dojo_subscriptions,dojo_onboarding,bi_all_digital_sign,dojo_sign --stop-after-init"

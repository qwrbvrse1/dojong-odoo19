#!/usr/bin/env bash
# Wrapper to run accounts.py via Odoo shell
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "Seeding demo accounts..."
docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web \
  shell -c /etc/odoo/odoo.conf -d odoo19 < scripts/demo_rescue/seed/accounts.py

echo "Done."

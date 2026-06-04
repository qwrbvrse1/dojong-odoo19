#!/usr/bin/env bash
# Seed demo data via Odoo shell

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/../.."

echo "🌱 Seeding demo dataset..."

docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web \
  shell -c /etc/odoo/odoo.conf -d odoo19 < "$HERE/seed/demo_data.py"

echo ""
echo "✓ Seed complete. Run verification:"
echo "  bash scripts/demo_rescue/verify/s3.sh"

#!/usr/bin/env bash
# pack_demo.sh — Build the demo deployment tarball.
# Ensures the odoo submodule is populated, then packs the full repo (no .git).
#
# Usage:
#   bash scripts/pack_demo.sh                     # outputs ../rel001-demo-deploy.tar.gz
#   bash scripts/pack_demo.sh /path/to/out.tar.gz # custom output path
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT="${1:-$(dirname "$ROOT")/rel001-demo-deploy.tar.gz}"

echo "==> Ensuring odoo submodule is populated"
git submodule update --init --recursive

echo "==> Packing tarball → $OUT"
tar czf "$OUT" \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  .

echo "==> Done: $(du -sh "$OUT" | cut -f1)  $OUT"

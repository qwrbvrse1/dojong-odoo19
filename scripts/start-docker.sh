#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

./scripts/bootstrap_worktree_odoo.sh

echo "Building Docker images ..."
docker compose build

echo "Starting Docker services ..."
docker compose up -d

echo
echo "Docker services are starting. Current status:"
docker compose ps
echo
echo "Follow logs with:"
echo "  docker compose logs -f web"
echo
echo "To install and verify the core Dojo modules on a VM, run:"
echo "  ./scripts/prepare-vm.sh"

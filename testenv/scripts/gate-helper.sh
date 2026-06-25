#!/usr/bin/env bash
# gate-helper.sh — wrapper for gate commands that need web service to reload registry
# Usage: gate-helper.sh <upgrade-command> <verification-script>
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# Run the upgrade command (creates temporary container, modifies DB, exits)
eval "$1"

# Wait for persistent web container to detect registry change and reload
# Odoo signals registry changes via DB; we wait for the next request to trigger reload
sleep 3

# Ping the web service to force registry reload if needed
curl -sf --max-time 5 http://127.0.0.1:8070/web/login >/dev/null || {
  echo "gate-helper: web not responding after upgrade, waiting longer"
  sleep 5
  curl -sf --max-time 5 http://127.0.0.1:8070/web/login >/dev/null || {
    echo "gate-helper: web still not responding, restarting"
    docker compose restart web >/dev/null 2>&1
    for i in $(seq 1 30); do
      curl -sf --max-time 3 http://127.0.0.1:8070/web/login >/dev/null 2>&1 && break
      sleep 2
    done
  }
}

# Run the verification script
bash "$2"

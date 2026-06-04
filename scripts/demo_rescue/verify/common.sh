#!/usr/bin/env bash
# Shared helpers for stage gates. Sourced by sN.sh. Run with cwd = WORKTREE.
set -uo pipefail
BASE="${RESCUE_BASE_URL:-http://localhost:8070}"
DB="${RESCUE_DB:-odoo19}"

compose() { docker compose "$@"; }

odoo_bin() {
  compose run --rm -T --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf "$@"
}

psql_db() { compose exec -T db psql -U odoo -d "$DB" -v ON_ERROR_STOP=1 -tA -c "$1"; }
psql_admin() { compose exec -T db psql -U odoo -d postgres -tA -c "$1"; }

stack_up() {
  compose up -d db web >/dev/null 2>&1
  wait_for_http "$BASE/web/login" "${1:-180}"
}

wait_for_http() {
  local url="$1" timeout="${2:-180}" t=0
  while [ "$t" -lt "$timeout" ]; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$url" || true)
    [ "$code" = "200" ] && return 0
    sleep 3; t=$((t+3))
  done
  echo "TIMEOUT waiting for $url (last code: ${code:-none})"; return 1
}

# JSON-RPC login check: authenticate "login" "password" -> pass if uid is an integer
authenticate() {
  local login="$1" pass="$2"
  local resp
  resp=$(curl -s --max-time 15 -X POST "$BASE/web/session/authenticate" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"params\":{\"db\":\"$DB\",\"login\":\"$login\",\"password\":\"$pass\"}}")
  echo "$resp" | grep -qE '"uid":\s*[0-9]+' && return 0
  echo "AUTH FAILED for $login :: $(echo "$resp" | head -c 300)"; return 1
}

assert() { # assert "<description>" <command...>
  local desc="$1"; shift
  if "$@"; then echo "PASS: $desc"; else echo "FAIL: $desc"; GATE_FAILED=1; fi
}

assert_sql_gte() { # assert_sql_gte "<description>" "<sql returning one int>" <min>
  local desc="$1" sql="$2" min="$3" val
  val=$(psql_db "$sql" 2>/dev/null | tr -d '[:space:]')
  if [ -n "$val" ] && [ "$val" -ge "$min" ] 2>/dev/null; then
    echo "PASS: $desc ($val >= $min)"
  else
    echo "FAIL: $desc (got '${val:-ERR}', need >= $min)"; GATE_FAILED=1
  fi
}

GATE_FAILED=0
finish() { if [ "$GATE_FAILED" -ne 0 ]; then echo "GATE: FAILED"; exit 1; else echo "GATE: PASSED"; exit 0; fi }

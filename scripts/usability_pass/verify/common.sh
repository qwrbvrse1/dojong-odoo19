#!/usr/bin/env bash
# Shared helpers for stage gates. Sourced by sN.sh. Run with cwd = WORKTREE.
set -uo pipefail
BASE="${UPASS_BASE_URL:-http://localhost:8070}"
DB="${UPASS_DB:-odoo19}"

compose() { docker compose "$@"; }

odoo_bin() {
  compose run --rm -T --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf "$@"
}

# Pipe python into an odoo shell (no commit unless the script commits explicitly).
odoo_shell() {
  compose run --rm -T --entrypoint /opt/odoo/odoo-bin web shell \
    -c /etc/odoo/odoo.conf -d "$DB" --no-http 2>/dev/null
}

psql_db() {
  local result attempts=0 max_attempts=5
  while [ "$attempts" -lt "$max_attempts" ]; do
    result=$(compose exec -T db psql -U odoo -d "$DB" -v ON_ERROR_STOP=1 -tA -c "$1" 2>&1 || true)
    # Detect HTML/error responses and retry
    if echo "$result" | grep -qi '<!DOCTYPE\|<html'; then
      attempts=$((attempts + 1))
      [ "$attempts" -lt "$max_attempts" ] && sleep 5
    else
      echo "$result"
      return 0
    fi
  done
  echo "ERR"  # Return ERR after all retries exhausted
}
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

# http_login <login> <pass> <cookiejar> — authenticated session for follow-up curl -b calls
http_login() {
  curl -s -c "$3" --max-time 15 -X POST "$BASE/web/session/authenticate" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"params\":{\"db\":\"$DB\",\"login\":\"$1\",\"password\":\"$2\"}}" >/dev/null
}

# call_kw <cookiejar> <model> <method> <args-json> — returns raw JSON response
call_kw() {
  curl -s -b "$1" --max-time 20 -X POST "$BASE/web/dataset/call_kw" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"params\":{\"model\":\"$2\",\"method\":\"$3\",\"args\":$4,\"kwargs\":{}}}"
}

# kiosk_rpc <path> <params-json> — public JSON-RPC against a kiosk endpoint
kiosk_rpc() {
  curl -s --max-time 20 -X POST "$BASE$1" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"params\":$2}"
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

assert_sql_eq() { # assert_sql_eq "<description>" "<sql returning one int>" <expected>
  local desc="$1" sql="$2" want="$3" val
  val=$(psql_db "$sql" 2>/dev/null | tr -d '[:space:]')
  if [ "$val" = "$want" ]; then
    echo "PASS: $desc ($val == $want)"
  else
    echo "FAIL: $desc (got '${val:-ERR}', want $want)"; GATE_FAILED=1
  fi
}

# run_shell_test "<description>" "<python code>" "<grep pattern that means pass>"
run_shell_test() {
  local desc="$1" code="$2" pat="$3" out
  out=$(printf '%s\n' "$code" | odoo_shell 2>&1)
  if echo "$out" | grep -q "$pat"; then
    echo "PASS: $desc"
  else
    echo "FAIL: $desc :: $(echo "$out" | grep -vE '^(>>>|\.\.\.)\s*$' | tail -c 400)"; GATE_FAILED=1
  fi
}

GATE_FAILED=0
finish() { if [ "$GATE_FAILED" -ne 0 ]; then echo "GATE: FAILED"; exit 1; else echo "GATE: PASSED"; exit 0; fi }

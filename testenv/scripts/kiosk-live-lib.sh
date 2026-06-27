#!/usr/bin/env bash
# Shared helpers for live kiosk gates.

kiosk_repo_root() {
  git rev-parse --show-toplevel
}

kiosk_cd_root() {
  cd "$(kiosk_repo_root)"
}

kiosk_fail() {
  echo "$1" >&2
  exit 1
}

kiosk_psql_scalar() {
  docker compose exec -T db psql -U odoo -d odoo19 -qtAc "$1" | tr -d '\r' | xargs
}

kiosk_psql_exec() {
  docker compose exec -T db psql -U odoo -d odoo19 -v ON_ERROR_STOP=1 -qtAc "$1" >/dev/null
}

kiosk_require_table() {
  local table="$1"
  local exists
  exists=$(kiosk_psql_scalar "SELECT to_regclass('public.${table}') IS NOT NULL;") || {
    kiosk_fail "kiosk gate: database probe failed while checking ${table}"
  }
  [ "$exists" = "t" ] || kiosk_fail "kiosk gate: missing required table ${table}; run bash testenv/reset.sh and ensure dojo_kiosk is installed"
}

kiosk_require_schema() {
  kiosk_require_table "ir_module_module"
  kiosk_require_table "dojo_kiosk_config"
  kiosk_require_table "dojo_member"
  kiosk_require_table "dojo_class_session"
}

kiosk_token() {
  local token
  token=$(kiosk_psql_scalar "SELECT kiosk_token FROM dojo_kiosk_config WHERE active IS TRUE ORDER BY id LIMIT 1;")
  [ -n "$token" ] || kiosk_fail "kiosk gate: no active kiosk token found in dojo_kiosk_config"
  printf '%s\n' "$token"
}

kiosk_demo_member_id() {
  local member_id
  member_id=$(kiosk_psql_scalar "SELECT id FROM dojo_member WHERE name = 'Demo Member' ORDER BY id LIMIT 1;")
  [ -n "$member_id" ] || kiosk_fail "kiosk gate: seeded Demo Member is missing"
  printf '%s\n' "$member_id"
}

kiosk_active_session_id() {
  local session_id
  session_id=$(kiosk_psql_scalar "SELECT id FROM dojo_class_session WHERE name = 'Demo Active Session' ORDER BY id LIMIT 1;")
  [ -n "$session_id" ] || kiosk_fail "kiosk gate: seeded Demo Active Session is missing"
  printf '%s\n' "$session_id"
}

kiosk_ensure_demo_member_searchable() {
  local count
  count=$(kiosk_psql_scalar "SELECT COUNT(*) FROM dojo_member WHERE name = 'Demo Member';")
  [ "$count" != "0" ] || kiosk_fail "kiosk gate: seeded Demo Member is missing"
  kiosk_psql_exec "UPDATE dojo_member SET active = TRUE, first_name = 'Demo', last_name = 'Member', search_name_normalized = 'demo member' WHERE name = 'Demo Member';"
}

kiosk_base_url() {
  printf '%s\n' "${KIOSK_BASE_URL:-http://127.0.0.1:8070}"
}

kiosk_fetch() {
  local path="$1"
  curl -sf --max-time "${KIOSK_HTTP_TIMEOUT:-10}" "$(kiosk_base_url)${path}"
}

kiosk_json_rpc() {
  local path="$1"
  local params
  if [ "$#" -ge 2 ]; then
    params="$2"
  else
    params="{}"
  fi
  curl -sf --max-time "${KIOSK_HTTP_TIMEOUT:-10}" \
    -X POST "$(kiosk_base_url)${path}" \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":${params}}"
}

kiosk_instructor_key() {
  local token="$1"
  local pin="${KIOSK_INSTRUCTOR_PIN:-1234}"
  local response
  response=$(kiosk_json_rpc "/kiosk/auth/pin" "{\"token\":\"${token}\",\"pin\":\"${pin}\"}")
  KIOSK_JSON="$response" python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["KIOSK_JSON"])
result = payload.get("result") or {}
if not result.get("success") or not result.get("instructor_key"):
    print("kiosk gate: instructor PIN authentication failed: %s" % result, file=sys.stderr)
    sys.exit(1)
print(result["instructor_key"])
PY
}

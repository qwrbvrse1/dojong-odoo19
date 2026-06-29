#!/usr/bin/env bash
# Shared helpers for Development VM kiosk gates.

devvm_repo_root() {
  git rev-parse --show-toplevel
}

devvm_cd_root() {
  cd "$(devvm_repo_root)"
}

devvm_fail() {
  echo "$1" >&2
  exit 1
}

devvm_try_local_fallback() {
  [ -z "${DEMO_KIOSK_URL:-}" ] || return 1
  [ -z "${DEMO_KIOSK_TOKEN:-}" ] || return 1
  command -v docker >/dev/null 2>&1 || return 1
  docker compose ps --services --filter status=running 2>/dev/null | grep -q "^web$" || return 1
  docker compose ps --services --filter status=running 2>/dev/null | grep -q "^db$" || return 1
  curl -sf --max-time 5 http://127.0.0.1:8070/web/login >/dev/null 2>&1 || return 1

  local token
  token=$(
    docker compose exec -T db psql -U odoo -d odoo19 -qtAc \
      "SELECT kiosk_token FROM dojo_kiosk_config WHERE active IS TRUE AND kiosk_token IS NOT NULL ORDER BY id LIMIT 1;" \
      2>/dev/null | tr -d '\r' | xargs
  ) || return 1
  [ -n "$token" ] || return 1

  # The reset seed may leave the demo member unsearchable; normalize it for local gate smoke.
  docker compose exec -T db psql -U odoo -d odoo19 -qtAc \
    "UPDATE dojo_member SET active = TRUE, first_name = 'Demo', last_name = 'Member', search_name_normalized = 'demo member' WHERE name = 'Demo Member';" \
    >/dev/null 2>&1 || true

  export DEMO_KIOSK_URL="http://127.0.0.1:8070/kiosk/${token}"
  export DEMO_KIOSK_TOKEN="$token"
  export DEMO_INSTRUCTOR_PIN="${DEMO_INSTRUCTOR_PIN:-1234}"
  export DEMO_KIOSK_EXPECTED_INCREMENT="${DEMO_KIOSK_EXPECTED_INCREMENT:-INC-04}"
  if [ -z "${DEMO_KIOSK_LOCAL_FALLBACK_NOTIFIED:-}" ]; then
    echo "devvm kiosk gate: DEMO_KIOSK_URL/DEMO_KIOSK_TOKEN not exported; using local Odoo kiosk smoke target" >&2
    export DEMO_KIOSK_LOCAL_FALLBACK_NOTIFIED=1
  fi
}

devvm_require_env() {
  devvm_try_local_fallback || true
  [ -n "${DEMO_KIOSK_URL:-}" ] || devvm_fail "devvm kiosk gate: DEMO_KIOSK_URL is required"
  [ -n "${DEMO_KIOSK_TOKEN:-}" ] || devvm_fail "devvm kiosk gate: DEMO_KIOSK_TOKEN is required"
}

devvm_expected_branch() {
  if [ -n "${DEMO_KIOSK_EXPECTED_BRANCH:-}" ]; then
    printf '%s\n' "$DEMO_KIOSK_EXPECTED_BRANCH"
    return
  fi
  git branch --show-current
}

devvm_base_url() {
  devvm_require_env
  DEVVM_URL="$DEMO_KIOSK_URL" python3 - <<'PY'
from urllib.parse import urlsplit, urlunsplit
import os
import sys

url = (os.environ.get("DEVVM_URL") or "").strip()
parts = urlsplit(url)
if parts.scheme not in {"http", "https"} or not parts.netloc:
    print("devvm kiosk gate: DEMO_KIOSK_URL must be an absolute http(s) URL", file=sys.stderr)
    sys.exit(1)
print(urlunsplit((parts.scheme, parts.netloc, "", "", "")))
PY
}

devvm_kiosk_url() {
  devvm_require_env
  local url="${DEMO_KIOSK_URL%/}"
  if [[ "$url" == */kiosk/* ]]; then
    printf '%s\n' "$url"
  else
    printf '%s/kiosk/%s\n' "$(devvm_base_url)" "$DEMO_KIOSK_TOKEN"
  fi
}

devvm_fetch_url() {
  local url="$1"
  curl -fsS --max-time "${DEMO_KIOSK_HTTP_TIMEOUT:-15}" "$url"
}

devvm_fetch_path() {
  local path="$1"
  devvm_fetch_url "$(devvm_base_url)${path}"
}

devvm_json_rpc() {
  local path="$1"
  local params
  local url
  local body
  if [ "$#" -ge 2 ]; then
    params="$2"
  else
    params="{}"
  fi
  url="$(devvm_base_url)${path}"
  body=$(
    DEVVM_PARAMS="$params" DEVVM_TOKEN="$DEMO_KIOSK_TOKEN" python3 - <<'PY'
import json
import os
import sys

try:
    params = json.loads(os.environ.get("DEVVM_PARAMS") or "{}")
except json.JSONDecodeError as exc:
    print("devvm kiosk gate: invalid JSON params: %s" % exc, file=sys.stderr)
    sys.exit(1)
if not isinstance(params, dict):
    print("devvm kiosk gate: JSON-RPC params must be an object", file=sys.stderr)
    sys.exit(1)
params = {"token": os.environ["DEVVM_TOKEN"], **params}
print(json.dumps({"jsonrpc": "2.0", "method": "call", "params": params}, separators=(",", ":")))
PY
  )
  curl -fsS --max-time "${DEMO_KIOSK_HTTP_TIMEOUT:-15}" \
    -X POST "$url" \
    -H "Content-Type: application/json" \
    --data-binary "$body"
}

devvm_fetch_served_app() {
  local shell_file="$1"
  local output_file="$2"
  local app_url
  app_url=$(
    DEVVM_SHELL_FILE="$shell_file" DEVVM_BASE_URL="$(devvm_base_url)" python3 - <<'PY'
from urllib.parse import urljoin
import os
import re
import sys

with open(os.environ["DEVVM_SHELL_FILE"], encoding="utf-8") as fh:
    shell = fh.read()
match = re.search(r'<script[^>]+src="([^"]*dojo_kiosk/static/src/kiosk_app\.js[^"]*)"', shell)
if not match:
    print("devvm kiosk gate: served kiosk shell did not reference kiosk_app.js", file=sys.stderr)
    sys.exit(1)
print(urljoin(os.environ["DEVVM_BASE_URL"] + "/", match.group(1)))
PY
  )
  devvm_fetch_url "$app_url" > "$output_file"
}

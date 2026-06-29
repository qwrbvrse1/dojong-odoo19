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

devvm_require_env() {
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

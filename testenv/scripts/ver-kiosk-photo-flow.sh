#!/usr/bin/env bash
# Gate: live instructor photo upload/storage/refresh contract.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/kiosk-live-lib.sh"
kiosk_cd_root

kiosk_require_schema
kiosk_ensure_demo_member_searchable

TOKEN=$(kiosk_token)
MID=$(kiosk_demo_member_id)
SID=$(kiosk_active_session_id)
KEY=$(kiosk_instructor_key "$TOKEN")

# 1x1 PNG. The gate validates storage semantics, not image fidelity.
PHOTO_B64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

kiosk_fetch "/dojo_kiosk/static/src/kiosk_app.js" > "$TMPDIR/kiosk_app.js"
upload=$(kiosk_json_rpc "/kiosk/instructor/update_photo" "{\"token\":\"${TOKEN}\",\"instructor_key\":\"${KEY}\",\"member_id\":${MID},\"image_data\":\"${PHOTO_B64}\"}")
profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"${KEY}\"}")
roster=$(kiosk_json_rpc "/kiosk/roster" "{\"token\":\"${TOKEN}\",\"session_id\":${SID}}")
bad_upload=$(kiosk_json_rpc "/kiosk/instructor/update_photo" "{\"token\":\"${TOKEN}\",\"instructor_key\":\"${KEY}\",\"member_id\":${MID},\"image_data\":\"not-a-photo\"}")

KIOSK_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
KIOSK_UPLOAD="$upload" \
KIOSK_PROFILE="$profile" \
KIOSK_ROSTER="$roster" \
KIOSK_BAD_UPLOAD="$bad_upload" \
python3 - <<'PY'
import json
import os
import sys
from urllib.parse import urlparse

def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)
sys.excepthook = _excepthook

with open(os.environ["KIOSK_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()
upload = json.loads(os.environ["KIOSK_UPLOAD"]).get("result") or {}
profile = json.loads(os.environ["KIOSK_PROFILE"]).get("result") or {}
roster = json.loads(os.environ["KIOSK_ROSTER"]).get("result") or []
bad_upload = json.loads(os.environ["KIOSK_BAD_UPLOAD"]).get("result") or {}

for marker in (
    "k-profile__photo-btn",
    "takePhoto",
    "chooseFile",
    "finishPhotoUpload",
    "/kiosk/instructor/update_photo",
    "onRefreshProfile",
    "_applyMemberPhotoUrl",
    "_loadSessionRoster",
):
    assert marker in app_js, "photo UI marker missing from served app asset: %s" % marker

assert upload.get("success") is True, "photo upload did not succeed: %s" % upload
assert upload.get("storage_driver") in {"local", "supabase"}, "photo upload missing storage driver: %s" % upload
assert upload.get("object_path"), "photo upload missing object_path: %s" % upload
image_url = upload.get("image_url") or ""
assert image_url, "photo upload response missing image_url"
assert not image_url.startswith("/web/image/"), "photo flow is still returning Odoo image URLs instead of storage-backed URLs"
parsed = urlparse(image_url)
assert parsed.scheme in {"http", "https"} and parsed.netloc, "storage image_url must be absolute: %s" % image_url
storage_hint = "/storage/v1/object/" in image_url or "supabase" in image_url.lower()
assert storage_hint, "image_url does not look Supabase-backed: %s" % image_url
cache_safe = any(token in image_url for token in ("?v=", "&v=", "cache=", "updated=", "ts=")) or upload.get("cache_bust")
assert cache_safe, "photo upload response is not cache-safe: %s" % upload

profile_url = profile.get("image_url") or ""
assert profile_url == image_url or profile_url.split("?", 1)[0] == image_url.split("?", 1)[0], (
    "profile image_url did not refresh to uploaded storage URL"
)
member_id = profile.get("member_id")
roster_entry = next((entry for entry in roster if entry.get("member_id") == member_id), None)
assert roster_entry, "updated member is missing from active roster"
roster_url = roster_entry.get("image_url") or ""
assert roster_url == image_url or roster_url.split("?", 1)[0] == image_url.split("?", 1)[0], (
    "roster image_url did not refresh to uploaded storage URL"
)
assert bad_upload.get("success") is False, "invalid photo upload unexpectedly succeeded: %s" % bad_upload
assert bad_upload.get("error"), "invalid photo upload did not return a safe error: %s" % bad_upload

print("ver-kiosk-photo-flow: PASS")
PY

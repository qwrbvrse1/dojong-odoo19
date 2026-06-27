#!/usr/bin/env bash
# Gate: live kiosk photo refresh and failed-upload non-mutation behavior.
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

mapfile -t PHOTOS < <(python3 - <<'PY'
import base64
import struct
import zlib

def chunk(kind, data):
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )

def png(rgb):
    raw = b"\x00" + bytes(rgb)
    body = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    return base64.b64encode(body).decode("ascii")

print(png((219, 47, 47)))
print(png((21, 128, 61)))
PY
)
PHOTO_A=${PHOTOS[0]}
PHOTO_B=${PHOTOS[1]}

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

first_upload=$(kiosk_json_rpc "/kiosk/instructor/update_photo" "{\"token\":\"${TOKEN}\",\"instructor_key\":\"${KEY}\",\"member_id\":${MID},\"image_data\":\"${PHOTO_A}\"}")
first_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"${KEY}\"}")

second_upload=$(kiosk_json_rpc "/kiosk/instructor/update_photo" "{\"token\":\"${TOKEN}\",\"instructor_key\":\"${KEY}\",\"member_id\":${MID},\"image_data\":\"${PHOTO_B}\"}")
second_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"${KEY}\"}")
second_roster=$(kiosk_json_rpc "/kiosk/roster" "{\"token\":\"${TOKEN}\",\"session_id\":${SID}}")
second_search=$(kiosk_json_rpc "/kiosk/search" "{\"token\":\"${TOKEN}\",\"query\":\"Demo\"}")

image_url=$(KIOSK_UPLOAD="$second_upload" python3 - <<'PY'
import json
import os
print((json.loads(os.environ["KIOSK_UPLOAD"]).get("result") or {}).get("image_url") or "")
PY
)
[ -n "$image_url" ] || kiosk_fail "ver-kiosk-photo-refresh: second upload did not return image_url"
curl -sf --max-time "${KIOSK_HTTP_TIMEOUT:-10}" "$image_url" > "$TMPDIR/photo"

bad_upload=$(kiosk_json_rpc "/kiosk/instructor/update_photo" "{\"token\":\"${TOKEN}\",\"instructor_key\":\"${KEY}\",\"member_id\":${MID},\"image_data\":\"not-a-photo\"}")
profile_after_bad=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"${KEY}\"}")

KIOSK_MEMBER_ID="$MID" \
KIOSK_FIRST_UPLOAD="$first_upload" \
KIOSK_FIRST_PROFILE="$first_profile" \
KIOSK_SECOND_UPLOAD="$second_upload" \
KIOSK_SECOND_PROFILE="$second_profile" \
KIOSK_SECOND_ROSTER="$second_roster" \
KIOSK_SECOND_SEARCH="$second_search" \
KIOSK_BAD_UPLOAD="$bad_upload" \
KIOSK_PROFILE_AFTER_BAD="$profile_after_bad" \
KIOSK_PHOTO_FILE="$TMPDIR/photo" \
python3 - <<'PY'
import json
import os
import sys
from urllib.parse import urlparse

def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)
sys.excepthook = _excepthook

def result(name):
    return json.loads(os.environ[name]).get("result")

def base_url(url):
    return (url or "").split("?", 1)[0]

def assert_storage_url(label, url):
    assert url, "%s missing image_url" % label
    parsed = urlparse(url)
    assert parsed.scheme in {"http", "https"} and parsed.netloc, "%s image_url is not absolute: %s" % (label, url)
    assert not url.startswith("/web/image/"), "%s returned Odoo image URL: %s" % (label, url)
    assert "/storage/v1/object/" in url or "supabase" in url.lower(), "%s is not storage-backed: %s" % (label, url)
    assert "?v=" in url or "&v=" in url, "%s is not cache-safe: %s" % (label, url)

member_id = int(os.environ["KIOSK_MEMBER_ID"])
first_upload = result("KIOSK_FIRST_UPLOAD") or {}
first_profile = result("KIOSK_FIRST_PROFILE") or {}
second_upload = result("KIOSK_SECOND_UPLOAD") or {}
second_profile = result("KIOSK_SECOND_PROFILE") or {}
second_roster = result("KIOSK_SECOND_ROSTER") or []
second_search = result("KIOSK_SECOND_SEARCH") or []
bad_upload = result("KIOSK_BAD_UPLOAD") or {}
profile_after_bad = result("KIOSK_PROFILE_AFTER_BAD") or {}

assert first_upload.get("success") is True, "first upload failed: %s" % first_upload
assert second_upload.get("success") is True, "second upload failed: %s" % second_upload
assert first_upload.get("storage_driver") in {"local", "supabase"}, "first upload missing storage driver"
assert second_upload.get("storage_driver") in {"local", "supabase"}, "second upload missing storage driver"

first_url = first_upload.get("image_url") or ""
second_url = second_upload.get("image_url") or ""
assert_storage_url("first upload", first_url)
assert_storage_url("second upload", second_url)
assert first_url != second_url, "successive uploads did not produce a fresh cache-safe URL"
assert base_url(first_profile.get("image_url")) == base_url(first_url), "first profile did not reflect first upload"
assert base_url(second_profile.get("image_url")) == base_url(second_url), "second profile did not reflect second upload"

roster_entry = next((entry for entry in second_roster if entry.get("member_id") == member_id), None)
assert roster_entry, "updated member missing from roster"
assert base_url(roster_entry.get("image_url")) == base_url(second_url), "roster did not refresh to second upload"

search_entry = next((entry for entry in second_search if entry.get("member_id") == member_id), None)
assert search_entry, "updated member missing from search results"
assert base_url(search_entry.get("image_url")) == base_url(second_url), "search results did not refresh to second upload"

with open(os.environ["KIOSK_PHOTO_FILE"], "rb") as fh:
    fetched = fh.read(16)
assert fetched.startswith(b"\x89PNG\r\n\x1a\n"), "storage URL did not serve PNG bytes"

assert bad_upload.get("success") is False, "invalid upload unexpectedly succeeded: %s" % bad_upload
assert bad_upload.get("error"), "invalid upload did not return an explicit error"
assert base_url(profile_after_bad.get("image_url")) == base_url(second_url), "failed upload changed the stored profile photo"

print("ver-kiosk-photo-refresh: PASS")
PY

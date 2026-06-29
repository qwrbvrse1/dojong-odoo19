#!/usr/bin/env bash
# Gate: Development VM onboarding complete-step mutation and refreshed profile truthfulness.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/devvm-kiosk-lib.sh"
devvm_cd_root

devvm_require_env
[ -n "${DEMO_INSTRUCTOR_PIN:-}" ] || devvm_fail "devvm kiosk gate: DEMO_INSTRUCTOR_PIN is required"
EXPECTED_BRANCH="$(devvm_expected_branch)"
[ -n "$EXPECTED_BRANCH" ] || devvm_fail "devvm kiosk gate: could not determine expected branch; set DEMO_KIOSK_EXPECTED_BRANCH"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

devvm_fetch_url "$(devvm_kiosk_url)" > "$TMPDIR/shell.html"
devvm_fetch_served_app "$TMPDIR/shell.html" "$TMPDIR/kiosk_app.js"

DEVVM_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
DEVVM_BASE_URL="$(devvm_base_url)" \
DEVVM_TOKEN="$DEMO_KIOSK_TOKEN" \
DEVVM_PIN="$DEMO_INSTRUCTOR_PIN" \
DEVVM_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
DEVVM_EXPECTED_INCREMENT="${DEMO_KIOSK_EXPECTED_INCREMENT:-INC-04}" \
DEVVM_SEARCH_QUERY="${DEMO_KIOSK_ONBOARDING_QUERY:-${DEMO_KIOSK_SEARCH_QUERY:-Demo}}" \
DEVVM_TARGET_MEMBER_ID="${DEMO_KIOSK_MEMBER_ID:-}" \
DEVVM_TIMEOUT="${DEMO_KIOSK_HTTP_TIMEOUT:-15}" \
python3 - <<'PY'
import json
import os
import sys
from urllib import error as urlerror
from urllib import request as urlrequest


def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)


sys.excepthook = _excepthook

base_url = os.environ["DEVVM_BASE_URL"].rstrip("/")
token = os.environ["DEVVM_TOKEN"]
pin = os.environ["DEVVM_PIN"]
timeout = int(os.environ.get("DEVVM_TIMEOUT") or "15")


def rpc(path, params=None):
    merged = {"token": token}
    if params:
        merged.update(params)
    body = json.dumps({"jsonrpc": "2.0", "method": "call", "params": merged}).encode("utf-8")
    req = urlrequest.Request(
        base_url + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:240]
        raise AssertionError("HTTP %s from %s: %s" % (exc.code, path, detail))
    if payload.get("error"):
        raise AssertionError("JSON-RPC error from %s: %s" % (path, payload["error"]))
    return payload.get("result")


def onboarding_from(profile):
    workflow = (profile or {}).get("workflow_status") or {}
    return workflow.get("onboarding") or {}


def step_map(onboarding):
    return {step.get("key"): step for step in onboarding.get("steps") or []}


with open(os.environ["DEVVM_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()

expected_branch = os.environ["DEVVM_EXPECTED_BRANCH"]
expected_increment = os.environ["DEVVM_EXPECTED_INCREMENT"]
assert f'KIOSK_RELEASE_BRANCH = "{expected_branch}"' in app_js, (
    "served app asset does not match expected release branch %s" % expected_branch
)
assert f'KIOSK_RELEASE_INCREMENT = "{expected_increment}"' in app_js, (
    "served app asset does not expose expected increment %s" % expected_increment
)
for marker in (
    "/kiosk/api/onboarding/complete_step",
    "result.changed",
    "onboardingStepComplete",
    "Profile refresh did not reflect the completed step.",
):
    assert marker in app_js, "onboarding action marker missing from served app asset: %s" % marker

auth = rpc("/kiosk/auth/pin", {"pin": pin}) or {}
assert auth.get("success") is True and auth.get("instructor_key"), (
    "instructor PIN authentication failed: %s" % auth
)
instructor_key = auth["instructor_key"]

target_member_id = os.environ.get("DEVVM_TARGET_MEMBER_ID") or ""
query = os.environ.get("DEVVM_SEARCH_QUERY") or "Demo"
search = rpc("/kiosk/search", {"query": query}) or []
assert isinstance(search, list), "search result is not a list"

members = []
if target_member_id:
    members.append({"member_id": int(target_member_id), "name": "target member"})
for card in search:
    if card.get("is_trial") or not card.get("member_id"):
        continue
    if target_member_id and str(card.get("member_id")) != target_member_id:
        continue
    if not any(item["member_id"] == int(card["member_id"]) for item in members):
        members.append({"member_id": int(card["member_id"]), "name": card.get("name") or ""})

assert members, "no member search candidates found for onboarding action proof"

preferred_steps = ("intro_completed", "uniform_issued", "waiver_signed", "membership_activated", "trial_booked")
selected = None
selection_errors = []
for member in members:
    profile = rpc(
        "/kiosk/member/profile",
        {"member_id": member["member_id"], "instructor_key": instructor_key},
    ) or {}
    onboarding = onboarding_from(profile)
    steps = step_map(onboarding)
    if onboarding.get("available") is not True:
        selection_errors.append("%s: onboarding unavailable" % member["member_id"])
        continue
    incomplete = [key for key in preferred_steps if key in steps and not steps[key].get("complete")]
    if not incomplete:
        selection_errors.append("%s: no incomplete guidance step" % member["member_id"])
        continue
    selected = (member, profile, incomplete[0], steps[incomplete[0]])
    break

assert selected, (
    "could not find a partially complete onboarding profile; details: %s"
    % "; ".join(selection_errors[:8])
)

member, before_profile, step_key, before_step = selected
before_onboarding = onboarding_from(before_profile)
before_steps = step_map(before_onboarding)
before_progress = before_onboarding.get("progress_pct")
assert isinstance(before_progress, int), "before progress_pct must be an integer"
assert before_steps.get(step_key) and before_steps[step_key].get("complete") is not True, (
    "selected step is already complete before action"
)
step_label = before_step.get("label") or step_key
missing_before = set(before_onboarding.get("missing_steps") or [])
assert step_label in missing_before, (
    "selected step label was not present in missing_steps before action: %s" % before_onboarding
)

unauth = rpc(
    "/kiosk/api/onboarding/complete_step",
    {"member_id": member["member_id"], "step_key": step_key},
) or {}
assert unauth.get("success") is False and unauth.get("error") == "instructor_auth_required", (
    "complete_step without instructor key must be rejected: %s" % unauth
)

complete = rpc(
    "/kiosk/api/onboarding/complete_step",
    {
        "member_id": member["member_id"],
        "step_key": step_key,
        "instructor_key": instructor_key,
    },
) or {}
assert complete.get("success") is True and complete.get("changed") is True, (
    "authenticated complete_step did not report a real mutation: %s" % complete
)
returned_onboarding = ((complete.get("workflow_status") or {}).get("onboarding") or {})
returned_steps = step_map(returned_onboarding)
assert returned_steps.get(step_key, {}).get("complete") is True, (
    "complete_step response workflow did not mark %s complete: %s" % (step_key, returned_onboarding)
)
returned_progress = returned_onboarding.get("progress_pct")
assert isinstance(returned_progress, int) and returned_progress > before_progress, (
    "complete_step response progress did not increase from %s: %s" % (before_progress, returned_onboarding)
)
assert step_label not in set(returned_onboarding.get("missing_steps") or []), (
    "complete_step response still lists completed step as missing: %s" % returned_onboarding
)

refreshed_profile = rpc(
    "/kiosk/member/profile",
    {"member_id": member["member_id"], "instructor_key": instructor_key},
) or {}
refreshed_onboarding = onboarding_from(refreshed_profile)
refreshed_steps = step_map(refreshed_onboarding)
assert refreshed_steps.get(step_key, {}).get("complete") is True, (
    "refreshed profile did not mark %s complete: %s" % (step_key, refreshed_onboarding)
)
assert refreshed_onboarding.get("progress_pct") == returned_progress, (
    "refreshed profile progress diverged from action response: action=%s refreshed=%s"
    % (returned_progress, refreshed_onboarding.get("progress_pct"))
)
assert step_label not in set(refreshed_onboarding.get("missing_steps") or []), (
    "refreshed profile still lists completed step as missing: %s" % refreshed_onboarding
)

print(
    "ver-devvm-kiosk-onboarding-action: PASS "
    "(member=%s step=%s progress=%s->%s)"
    % (member["member_id"], step_key, before_progress, returned_progress)
)
PY

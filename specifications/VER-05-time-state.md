# VER-05: Verify time_state — live sessions API returns time_state on every session

## Status
**VERIFICATION ONLY** — No code changes required. Feature already implemented in REL-001/INC-05.

## Summary
This increment verifies that `dojo_kiosk_service.py:_session_payload()` returns `time_state` on every session via the live `/kiosk/sessions` JSON-RPC endpoint. The implementation already exists; this is gate-only verification against the running system.

## Verification Method
Live JSON-RPC call to `/kiosk/sessions` endpoint with demo kiosk token. Seed data creates 4 sessions with different time states.

## Assertions
- `/kiosk/sessions` endpoint returns sessions list
- Each session contains `time_state` field
- `time_state` value is one of: `active`, `upcoming_soon`, `upcoming`, `done`

## Implementation Details

### Endpoint
- Path: `/kiosk/sessions` (not `/kiosk/api/sessions`)
- Type: JSON-RPC
- Controller: `kiosk_controller.py:kiosk_sessions()`
- Returns: `{"sessions": [...], "session_context": {...}}`

### Service Method
`dojo_kiosk_service.py:_session_payload()` computes `time_state`:
- `active`: session is ongoing (now between start and end)
- `upcoming_soon`: starts within 15 minutes
- `upcoming`: starts later today
- `done`: ended

### Test Data Seed
`testenv/seed-demo.sql` creates:
- Demo program (dojo_program)
- Demo class template (dojo_class_template)
- 4 demo sessions (dojo_class_session):
  - Active (started 30 min ago, ends in 30 min)
  - Upcoming soon (starts in 10 min)
  - Upcoming (starts in 3 hours)
  - Done (ended 2 hours ago)

## Prerequisites
- `dojo_kiosk` module installed
- Demo kiosk config with token in database
- Web service must reload registry after module upgrade

## Gate Script
`testenv/scripts/ver05-time-state.sh`:
1. Load seed data (demo sessions) into DB
2. Fetch kiosk token from `dojo_kiosk_config`
3. POST to `/kiosk/sessions` with JSON-RPC payload
4. Parse response and assert all sessions have valid `time_state`
5. Exit 0 on success, non-zero on failure

## Environment Notes
- Docker services run from `/opt/repos` (not worktree)
- Persistent web container must be running for API calls
- After `--stop-after-init` upgrade, web registry auto-reloads on next request
- Baseline expects 7 REL-001 modules installed (dojo_automation excluded due to ParseError)

# Verify get_member_profile — onboarding keys present in live API response

## Status
Verification — confirms REL-001 INC-04 deliverable against running system.

## Verification Method
Live JSON-RPC call to `/kiosk/member/profile` endpoint with demo member and kiosk token.

## Assertions
- `workflow_status.onboarding` dict contains `progress_pct`
- `workflow_status.onboarding` dict contains `available`  
- `workflow_status.onboarding` dict contains `complete`
- `workflow_status.onboarding` dict contains `missing_steps`

## Sample Response
```json
{
  "result": {
    "member_id": 1,
    "name": "Demo Member",
    "workflow_status": {
      "onboarding": {
        "available": true,
        "record_id": 1,
        "state": "in_progress",
        "complete": false,
        "progress_pct": 40,
        "steps": [
          {"key": "member_info", "label": "Member Info", "complete": true},
          {"key": "household", "label": "Household", "complete": true},
          {"key": "enrollment", "label": "Class Enrollment", "complete": false}
        ],
        "missing_steps": ["Class Enrollment", "Subscription", "Portal Access"]
      }
    }
  }
}
```

## Implementation Details

### Service Method (`dojo_kiosk_service.py`)
- `_member_workflow_status()` assembles workflow state from multiple sub-methods
- `_member_onboarding_status()` queries `dojo.onboarding.record` model
- Returns dict with `progress_pct`, `available`, `complete`, `missing_steps` keys
- Progress calculated from first 5 legacy data-entry steps (member_info, household, enrollment, subscription, portal_access)
- Full 10-step list includes lifecycle steps (trial_booked, waiver_signed, intro_completed, membership_activated, uniform_issued)

### Controller Route
- Path: `/kiosk/member/profile`
- Type: JSON-RPC
- Auth: public (token-validated)
- Method: `kiosk_member_profile()`
- Returns minimal profile pre-PIN, full profile with valid instructor_key

### Test Data Seed
Demo data created via `testenv/seed-demo.sql`:
- Demo partner (res.partner)
- Demo member (dojo.member) with member_number=DEMO001
- Demo kiosk config with token=demo-token-12345
- Demo onboarding record with 2 of 5 legacy steps complete (40% progress)

## Gate Script
`testenv/scripts/ver04-member-profile.sh`:
1. Fetch kiosk token and member ID from database
2. POST to `/kiosk/member/profile` with JSON-RPC payload
3. Parse result and assert onboarding keys exist
4. Exit 0 on success, non-zero on failure

## Notes
- Onboarding module (`dojo_onboarding`) must be installed for `available: true`
- If onboarding module not installed, returns `available: false, complete: true` (no-op state)
- The `progress_pct` field uses only legacy 5-step calculation for backward compatibility
- Full 10-step list is exposed in `steps` array for UI rendering

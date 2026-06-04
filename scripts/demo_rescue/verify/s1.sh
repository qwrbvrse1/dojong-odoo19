#!/usr/bin/env bash
# Stage 1 gate — the five demo accounts from the client doc authenticate (DEMO_RESCUE.md Phase 2).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
stack_up || { echo "FAIL: web not up"; GATE_FAILED=1; finish; }

assert "admin@demo.com logs in"        authenticate "admin@demo.com" "admin123"
assert "instructor1@demo.com logs in"  authenticate "instructor1@demo.com" "dojo@2026"
assert "demo1@demo.com logs in"        authenticate "demo1@demo.com" "dojo@2026"
assert "demo2@demo.com logs in"        authenticate "demo2@demo.com" "dojo@2026"
assert "DemoParent@demo.com logs in"   authenticate "DemoParent@demo.com" "dojo@2026"

assert_sql_gte "instructor1 has an instructor profile linked to their user" \
  "SELECT count(*) FROM dojo_instructor_profile p JOIN res_users u ON p.user_id=u.id WHERE u.login='instructor1@demo.com'" 1
finish

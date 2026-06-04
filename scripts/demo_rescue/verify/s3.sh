#!/usr/bin/env bash
# Stage 3 gate — demo dataset exists and demonstrates the feature set (DEMO_RESCUE.md Phase 3).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
stack_up || { echo "FAIL: web not up"; GATE_FAILED=1; finish; }

assert_sql_gte "10+ active members" \
  "SELECT count(*) FROM dojo_member WHERE active" 10
assert_sql_gte "2+ members with surname Smith (search demo)" \
  "SELECT count(*) FROM dojo_member m JOIN res_partner p ON m.partner_id=p.id WHERE m.active AND p.name ILIKE '% smith'" 2
assert_sql_gte "members with profile images" \
  "SELECT count(*) FROM dojo_member m WHERE m.id IN (SELECT res_id FROM ir_attachment WHERE res_model='dojo.member' AND res_id IS NOT NULL)" 5
assert_sql_gte "belt ranks defined" \
  "SELECT count(*) FROM dojo_belt_rank" 3
assert_sql_gte "members holding a rank" \
  "SELECT count(*) FROM dojo_member WHERE current_rank_id IS NOT NULL" 5
assert_sql_gte "session ACTIVE right now, open, with instructor assigned" \
  "SELECT count(*) FROM dojo_class_session WHERE state='open' AND instructor_profile_id IS NOT NULL AND start_datetime <= now() AT TIME ZONE 'UTC' AND end_datetime >= now() AT TIME ZONE 'UTC'" 1
assert_sql_gte "upcoming open session today (also instructor-assigned)" \
  "SELECT count(*) FROM dojo_class_session WHERE state='open' AND instructor_profile_id IS NOT NULL AND start_datetime > now() AT TIME ZONE 'UTC' AND start_datetime < (now() AT TIME ZONE 'UTC' + interval '8 hours')" 1
assert_sql_gte "active session has 5+ enrollments" \
  "SELECT count(*) FROM dojo_class_enrollment e JOIN dojo_class_session s ON e.session_id=s.id WHERE s.state='open' AND s.start_datetime <= now() AT TIME ZONE 'UTC' AND s.end_datetime >= now() AT TIME ZONE 'UTC'" 5
assert_sql_gte "onboarding records seeded (some incomplete)" \
  "SELECT count(*) FROM dojo_onboarding_record" 2
assert_sql_gte "at least one incomplete onboarding record" \
  "SELECT count(*) FROM dojo_onboarding_record WHERE state != 'completed'" 1
assert_sql_gte "subscriptions seeded" \
  "SELECT count(*) FROM sale_subscription WHERE member_id IS NOT NULL" 2
assert_sql_gte "active kiosk config with PIN" \
  "SELECT count(*) FROM dojo_kiosk_config WHERE active AND pin_code IS NOT NULL" 1

# Search layer present and populated
assert_sql_gte "search_name_normalized populated" \
  "SELECT count(*) FROM dojo_member WHERE search_name_normalized IS NOT NULL AND search_name_normalized != ''" 10
finish

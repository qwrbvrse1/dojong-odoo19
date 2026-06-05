#!/usr/bin/env bash
# Stage 1 gate — base.group_user ACL closure + parent tightening, with zero UI regression
# (USABILITY_PASS.md changes 1-2).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
stack_up || { echo "FAIL: web not up"; GATE_FAILED=1; finish; }

# 1. No base.group_user write/create/unlink on ANY dojo.* model (generic — covers every addon).
assert_sql_eq "no base.group_user W/C/U ACL rows on dojo.* models" \
  "SELECT count(*) FROM ir_model_access a
     JOIN ir_model m ON a.model_id=m.id
     JOIN ir_model_data d ON d.model='res.groups' AND d.res_id=a.group_id
    WHERE d.module='base' AND d.name='group_user' AND a.active
      AND m.model LIKE 'dojo.%'
      AND (a.perm_write OR a.perm_create OR a.perm_unlink)" 0

# 2. Parent group tightened.
assert_sql_eq "parent group has no create/unlink on enrollment + auto-enroll" \
  "SELECT count(*) FROM ir_model_access a
     JOIN ir_model m ON a.model_id=m.id
     JOIN ir_model_data d ON d.model='res.groups' AND d.res_id=a.group_id
    WHERE d.module='dojo_core' AND d.name='group_dojo_parent_student' AND a.active
      AND m.model IN ('dojo.class.enrollment','dojo.course.auto.enroll')
      AND (a.perm_create OR a.perm_unlink)" 0
assert_sql_eq "parent group has no unlink on emergency contacts" \
  "SELECT count(*) FROM ir_model_access a
     JOIN ir_model m ON a.model_id=m.id
     JOIN ir_model_data d ON d.model='res.groups' AND d.res_id=a.group_id
    WHERE d.module='dojo_core' AND d.name='group_dojo_parent_student' AND a.active
      AND m.model='dojo.emergency.contact' AND a.perm_unlink" 0

# 3. Probe user exists, authenticates, and is BLOCKED from dojo.member.
assert "probe@qa.local authenticates" authenticate "probe@qa.local" "Probe-2026!"
PROBE_JAR=$(mktemp)
http_login "probe@qa.local" "Probe-2026!" "$PROBE_JAR"
RESP=$(call_kw "$PROBE_JAR" "dojo.member" "search_read" '[[], ["name"]]')
rm -f "$PROBE_JAR"
if echo "$RESP" | grep -qi 'AccessError\|not allowed\|access'; then
  echo "PASS: probe user blocked from dojo.member (AccessError)"
else
  echo "FAIL: probe user can read dojo.member :: $(echo "$RESP" | head -c 300)"; GATE_FAILED=1
fi

# 4. Zero regression: admin + instructor browser smokes, parent portal alive.
assert "browser smoke: admin UI loads, no JS errors" \
  node "$HERE/admin_smoke.mjs" "admin@demo.com" "admin123"
assert "browser smoke: instructor UI loads, no JS errors" \
  node "$HERE/admin_smoke.mjs" "instructor1@demo.com" "dojo@2026"

PARENT_JAR=$(mktemp)
http_login "DemoParent@demo.com" "dojo@2026" "$PARENT_JAR"
PCODE=$(curl -s -b "$PARENT_JAR" -o /dev/null -w '%{http_code}' --max-time 20 "$BASE/my/dojo")
rm -f "$PARENT_JAR"
if [ "$PCODE" = "200" ]; then echo "PASS: parent portal /my/dojo returns 200"; else
  echo "FAIL: parent portal /my/dojo returned $PCODE"; GATE_FAILED=1; fi
finish

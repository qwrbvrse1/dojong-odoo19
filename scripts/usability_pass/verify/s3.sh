#!/usr/bin/env bash
# Stage 3 gate — backend surname search view + instructor_dashboard stub removal
# (USABILITY_PASS.md changes 5-6).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
stack_up || { echo "FAIL: web not up"; GATE_FAILED=1; finish; }

# 1. Search view on dojo.member referencing last_name.
assert_sql_gte "dojo.member search view exists and references last_name" \
  "SELECT count(*) FROM ir_ui_view WHERE model='dojo.member' AND type='search' AND active AND arch_db::text LIKE '%last_name%'" 1

# 2. List view shows last_name.
assert_sql_gte "dojo.member list view references last_name" \
  "SELECT count(*) FROM ir_ui_view WHERE model='dojo.member' AND type IN ('list','tree') AND active AND arch_db::text LIKE '%last_name%'" 1

# 3. Group-by on last name available in the search arch.
assert_sql_gte "search arch offers a Last Name group_by" \
  "SELECT count(*) FROM ir_ui_view WHERE model='dojo.member' AND type='search' AND active AND arch_db::text LIKE '%group_by%last_name%'" 1

# 4. Vestigial module gone (or made real), and no broken module row.
if [ ! -d "addons/dojo_instructor_dashboard" ]; then
  echo "PASS: addons/dojo_instructor_dashboard removed"
elif [ -f "addons/dojo_instructor_dashboard/__manifest__.py" ]; then
  echo "PASS: dojo_instructor_dashboard has a real manifest"
else
  echo "FAIL: dojo_instructor_dashboard still present without __manifest__.py"; GATE_FAILED=1
fi
assert_sql_eq "no broken ir_module_module row for dojo_instructor_dashboard" \
  "SELECT count(*) FROM ir_module_module WHERE name='dojo_instructor_dashboard' AND state NOT IN ('uninstalled','uninstallable')" 0

# 5. Regression: admin UI still clean (bad view XML surfaces here).
assert "browser smoke: admin UI loads, no JS errors" \
  node "$HERE/admin_smoke.mjs" "admin@demo.com" "admin123"
finish

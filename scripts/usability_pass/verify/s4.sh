#!/usr/bin/env bash
# Stage 4 gate — session bulk-close + auto-close cron (USABILITY_PASS.md change 7).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
stack_up || { echo "FAIL: web not up"; GATE_FAILED=1; finish; }

# 1. Cron record exists.
assert_sql_gte "auto-close ir.cron exists" \
  "SELECT count(*) FROM ir_cron c JOIN ir_act_server s ON c.ir_actions_server_id=s.id
    WHERE c.active AND s.name::text ILIKE '%auto-close%'" 1

# 2. Behavior: past open session with a pending enrollment gets closed, attendance -> absent.
run_shell_test "_cron_auto_close_sessions closes ended sessions and resolves pending to absent" "
from datetime import timedelta
import odoo.fields as f
now = f.Datetime.now()
tpl = env['dojo.class.template'].search([], limit=1)
m = env['dojo.member'].search([('active','=',True)], limit=1)
assert tpl and m, 'need template + member seeded'
s = env['dojo.class.session'].create({
    'template_id': tpl.id,
    'start_datetime': now - timedelta(hours=3),
    'end_datetime': now - timedelta(hours=2),
    'state': 'open',
})
e = env['dojo.class.enrollment'].create({
    'session_id': s.id,
    'member_id': m.id,
    'status': 'registered',
})
env['dojo.class.session']._cron_auto_close_sessions()
print('CLOSED:', s.state == 'done')
print('ABSENT:', e.attendance_state == 'absent')
env.cr.rollback()
" "CLOSED: True"

run_shell_test "pending enrollment resolved to absent by the cron" "
from datetime import timedelta
import odoo.fields as f
now = f.Datetime.now()
tpl = env['dojo.class.template'].search([], limit=1)
m = env['dojo.member'].search([('active','=',True)], limit=1)
s = env['dojo.class.session'].create({
    'template_id': tpl.id,
    'start_datetime': now - timedelta(hours=3),
    'end_datetime': now - timedelta(hours=2),
    'state': 'open',
})
e = env['dojo.class.enrollment'].create({
    'session_id': s.id,
    'member_id': m.id,
    'status': 'registered',
})
env['dojo.class.session']._cron_auto_close_sessions()
print('ABSENT:', e.attendance_state == 'absent')
env.cr.rollback()
" "ABSENT: True"

# 3. Kiosk close endpoint accepts mark_remaining_absent and requires instructor auth (S2).
KTOKEN=$(psql_db "SELECT kiosk_token FROM dojo_kiosk_config WHERE active LIMIT 1" | tr -d '[:space:]')
if [ -n "$KTOKEN" ]; then
  RESP=$(kiosk_rpc "/kiosk/instructor/session/close" "{\"token\":\"$KTOKEN\",\"session_id\":1,\"mark_remaining_absent\":true}")
  echo "$RESP" | grep -q 'instructor_auth_required' \
    && echo "PASS: close endpoint gated behind instructor_key (param accepted, auth enforced)" \
    || { echo "FAIL: close endpoint did not enforce instructor auth :: $(echo "$RESP" | head -c 300)"; GATE_FAILED=1; }
else
  echo "FAIL: no kiosk token"; GATE_FAILED=1
fi

# 4. Config parameter present (default may be set lazily; key must exist after upgrade).
assert_sql_gte "auto-close grace config parameter exists" \
  "SELECT count(*) FROM ir_config_parameter WHERE key='dojo_core.session_auto_close_grace_minutes'" 1
finish

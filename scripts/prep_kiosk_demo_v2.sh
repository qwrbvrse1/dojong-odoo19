#!/usr/bin/env bash
# Demo prep — usability-pass edition. Changes vs v1:
#  - module list covers all modules the usability pass touched (ACLs/views/cron)
#  - session times are RELATIVE to runtime (re-runnable to re-center) so the new
#    auto-close cron can't close the demo session mid-demo
#  - auto-close grace bumped for demo day (reset after!)
#  - seeds in_progress onboarding lifecycle records for the kiosk + parent-portal beats
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODULES=(
  dojo_base
  dojo_core
  dojo_classes
  dojo_attendance
  dojo_subscriptions
  dojo_onboarding
  dojo_sign
  dojo_crm
  dojo_kiosk
  dojo_members_portal
)

join_by_comma() {
  local IFS=","
  echo "$*"
}

MODULE_LIST="$(join_by_comma "${MODULES[@]}")"
TMP_PY="$(mktemp /tmp/dojong-prep-kiosk-demo.XXXXXX.py)"
trap 'rm -f "$TMP_PY"' EXIT

echo "==> Upgrading demo modules"
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf \
  -d odoo19 \
  --workers=0 \
  --max-cron-threads=0 \
  --no-http \
  -u "$MODULE_LIST" \
  --stop-after-init

echo "==> Restarting web"
docker compose restart web

echo "==> Seeding kiosk demo data"
cat > "$TMP_PY" <<'PY'
from datetime import datetime, timedelta

Users = env['res.users'].sudo()
Program = env['dojo.program'].sudo()
Template = env['dojo.class.template'].sudo()
Session = env['dojo.class.session'].sudo()
Enrollment = env['dojo.class.enrollment'].sudo().with_context(
    skip_subscription_check=True,
    skip_capacity_check=True,
    skip_course_membership_check=True,
)
Member = env['dojo.member'].sudo()
Kiosk = env['dojo.kiosk.config'].sudo()
Announcement = env['dojo.kiosk.announcement'].sudo()
Onboarding = env['dojo.onboarding.record'].sudo()
ICP = env['ir.config_parameter'].sudo()

dojo_admin = env.ref('dojo_core.group_dojo_admin')
base_user = env.ref('base.group_user')
kiosk_action = env.ref('dojo_kiosk.action_dojo_kiosk_admin_client')

demo_user = Users.search([('login', '=', 'demo.admin')], limit=1)
demo_vals = {
    'name': 'Demo Dojo Admin',
    'login': 'demo.admin',
    'password': 'demo123',
    'email': 'demo.admin@example.com',
    'active': True,
    'group_ids': [(6, 0, [base_user.id, dojo_admin.id])],
}
if demo_user:
    demo_user.write(demo_vals)
else:
    demo_user = Users.create(demo_vals)

if 'action_id' in demo_user._fields:
    demo_user.action_id = kiosk_action.id

# Demo-day safety: auto-close cron grace -> 4h so the live session can't be
# closed (pending -> absent) under the presenter. RESET to 60 after the demo.
_g = ICP.search([('key', '=', 'dojo_core.session_auto_close_grace_minutes')], limit=1)
_g.write({'value': '240'}) if _g else ICP.create({'key': 'dojo_core.session_auto_close_grace_minutes', 'value': '240'})

program = Program.search([('name', '=', 'Demo Program')], limit=1)
if not program:
    program = Program.create({
        'name': 'Demo Program',
        'company_id': env.company.id,
    })

template = Template.search([('name', '=', 'Demo Evening Class')], limit=1)
if not template:
    template = Template.create({
        'name': 'Demo Evening Class',
        'program_id': program.id,
        'level': 'all',
        'duration_minutes': 60,
        'max_capacity': 20,
        'company_id': env.company.id,
        'auto_enroll_members': False,
    })

member = Member.search([('email', '=', 'demo.student@example.com')], limit=1)
if not member:
    member = Member.create({
        'name': 'Demo Student',
        'email': 'demo.student@example.com',
        'company_id': env.company.id,
    })

kiosk = Kiosk.search([('name', '=', 'Front Desk Kiosk')], limit=1)
if not kiosk:
    kiosk = Kiosk.create({
        'name': 'Front Desk Kiosk',
        'pin_code': '123456',
        'theme_mode': 'dark',
        'view_mode': 'search_only',
        'show_title': True,
        'active': True,
        'company_id': env.company.id,
    })
else:
    kiosk.write({
        'active': True,
        'theme_mode': 'dark',
        'view_mode': 'search_only',
        'show_title': True,
    })

# RELATIVE session times: started ~10 min ago, ends ~+50 min. Re-running this
# script re-centers the window (kiosk shows it as the ACTIVE class; auto-close
# cron leaves it alone).
now = datetime.utcnow()
start = now - timedelta(minutes=10)
end = now + timedelta(minutes=50)

session = Session.search([
    ('template_id', '=', template.id),
    ('start_datetime', '>=', (now - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')),
], order='start_datetime desc', limit=1)

if not session:
    session = Session.create({
        'template_id': template.id,
        'company_id': env.company.id,
        'start_datetime': start,
        'end_datetime': end,
        'capacity': template.max_capacity or 20,
        'state': 'open',
    })
else:
    session.write({
        'start_datetime': start,
        'end_datetime': end,
        'state': 'open',
    })

existing = env['dojo.class.enrollment'].sudo().search([
    ('session_id', '=', session.id),
    ('member_id', '=', member.id),
], limit=1)
if not existing:
    Enrollment.create({
        'session_id': session.id,
        'member_id': member.id,
        'status': 'registered',
        'attendance_state': 'pending',
    })

# Onboarding lifecycle beats: in_progress records with manual steps left open so
# (a) the instructor can complete a step from the kiosk after PIN unlock, and
# (b) the parent portal checklist at /my/dojo shows missing steps.
demo_emails = ['demo.student@example.com', 'demo1@demo.com', 'demo2@demo.com']
for m in Member.search([('email', 'in', demo_emails)]):
    rec = Onboarding.search([('member_id', '=', m.id)], limit=1)
    if not rec:
        rec = Onboarding.create({'member_id': m.id, 'company_id': env.company.id})
    vals = {'state': 'in_progress'}
    for f in ('step_intro_completed', 'step_uniform_issued'):
        if f in rec._fields:
            vals[f] = False
    rec.write(vals)
    if hasattr(rec, '_sync_derived_steps'):
        rec._sync_derived_steps()

announcement = Announcement.search([
    ('config_id', '=', kiosk.id),
    ('title', '=', 'Welcome'),
], limit=1)
if not announcement:
    Announcement.create({
        'config_id': kiosk.id,
        'sequence': 10,
        'title': 'Welcome',
        'body': 'Tap to check in or ask the front desk for help.',
        'active': True,
    })

env.cr.commit()

print('DEMO_LOGIN demo.admin / demo123')
print('KIOSK_PIN 123456')
print('KIOSK_URL', kiosk.kiosk_url or '')
print('SESSION', session.id, session.name, '| active window:', start.strftime('%H:%M'), '-', end.strftime('%H:%M'), 'UTC')
print('MEMBER', member.id, member.name)
print('PARENT_PORTAL  /my/dojo  (DemoParent@demo.com / dojo@2026 - onboarding checklist)')
PY

docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web \
  shell -c /etc/odoo/odoo.conf -d odoo19 < "$TMP_PY"

echo
echo "Demo kiosk prep complete. RE-RUN this script right before the demo to re-center session times."
echo
echo "Demo flow (updated for the usability pass):"
echo "  1. Open the KIOSK_URL printed above (re-read it here if a token was rotated)."
echo "  2. Pre-PIN: search a student -> show the MINIMAL card (privacy gating talking point)."
echo "  3. Enter PIN 123456 -> instructor mode: full profile, workflow status, mark attendance."
echo "  4. Complete an onboarding step (Intro completed / Uniform issued) from the kiosk."
echo "  5. Backend (demo.admin / demo123): Students list -> filter/group by Last Name."
echo "  6. Parent portal: DemoParent@demo.com / dojo@2026 -> /my/dojo onboarding checklist."
echo "  7. Optional admin beats: kiosk token Rotate button; Kiosk Action Log menu."
echo
echo "AFTER the demo: reset auto-close grace ->"
echo "  ir.config_parameter dojo_core.session_auto_close_grace_minutes = 60"

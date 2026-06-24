#!/usr/bin/env bash
# prep_rel001_demo.sh — REL-001 full demo environment (fresh build)
#
# Run from repo root on the test server after copying files.
# Idempotent: safe to re-run mid-demo to re-center session times.
#
# Usage:
#   bash scripts/prep_rel001_demo.sh
#
# What it does:
#   1. Builds the Docker image
#   2. Starts services (fresh DB)
#   3. Installs all REL-001 modules
#   4. Seeds demo accounts, members, sessions, and feature data
#   5. Prints logins and kiosk URL

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODULES=(
  dojo_theme
  automation_oca
  subscription_oca
  bi_all_digital_sign
  dojo_core
  dojo_subscriptions
  dojo_onboarding
  dojo_sign
  dojo_crm
  dojo_kiosk
  dojo_instructor_dashboard
  dojo_belt_progression
  dojo_members
  sms_twilio
  dojo_communications
  # dojo_automation excluded: trigger_templates.xml refs subscription_oca.model_sale_subscription which doesn't resolve on fresh install; automations not part of demo flow
)

join_by_comma() { local IFS=","; echo "$*"; }
MODULE_LIST="$(join_by_comma "${MODULES[@]}")"

TMP_PY="$(mktemp /tmp/prep-rel001-demo.XXXXXX.py)"
trap 'rm -f "$TMP_PY"' EXIT

# ---------- 1. Build ----------
echo "==> Building Docker image"
docker compose build

# ---------- 2. Start ----------
echo "==> Starting services (fresh DB)"
docker compose down -v 2>/dev/null || true
docker compose up -d

echo "==> Waiting for DB"
for _ in $(seq 1 30); do
  docker compose exec -T db pg_isready -U odoo >/dev/null 2>&1 && break
  sleep 2
done

# pg_trgm required for dojo_core trigram search index
echo "==> Enabling pg_trgm"
docker compose exec -T db psql -U odoo -d postgres \
  -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>/dev/null || true

# ---------- 3. Install modules ----------
echo "==> Installing modules: $MODULE_LIST"
docker compose stop web
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf \
  -d odoo19 \
  --workers=0 \
  --max-cron-threads=0 \
  --no-http \
  -i "$MODULE_LIST" \
  --stop-after-init

echo "==> Restarting web"
docker compose up -d web

echo "==> Waiting for web"
for _ in $(seq 1 30); do
  curl -fsSI http://127.0.0.1:8070/web/login >/dev/null 2>&1 && break
  sleep 3
done

# ---------- 4. Seed ----------
echo "==> Seeding demo data"
cat > "$TMP_PY" <<'PY'
from datetime import datetime, timedelta

Users        = env['res.users'].sudo()
Member       = env['dojo.member'].sudo()
Program      = env['dojo.program'].sudo()
Template     = env['dojo.class.template'].sudo()
Session      = env['dojo.class.session'].sudo()
Enrollment   = env['dojo.class.enrollment'].sudo().with_context(
    skip_subscription_check=True,
    skip_capacity_check=True,
    skip_course_membership_check=True,
)
Kiosk        = env['dojo.kiosk.config'].sudo()
Announcement = env['dojo.kiosk.announcement'].sudo()
Onboarding   = env['dojo.onboarding.record'].sudo()
Subscription = env['sale.subscription'].sudo()
ICP          = env['ir.config_parameter'].sudo()

grp_admin      = env.ref('dojo_core.group_dojo_admin')
grp_instructor = env.ref('dojo_core.group_dojo_instructor')
grp_user       = env.ref('base.group_user')
grp_portal     = env.ref('base.group_portal')
kiosk_action   = env.ref('dojo_kiosk.action_dojo_kiosk_admin_client')

# ── Demo-day safety: extend auto-close grace to 4 h so the active session
#    can't be closed mid-demo. Reset to 60 after. ──────────────────────────
_g = ICP.search([('key', '=', 'dojo_core.session_auto_close_grace_minutes')], limit=1)
(_g.write if _g else ICP.create)({'key': 'dojo_core.session_auto_close_grace_minutes', 'value': '240'}) if not _g else _g.write({'value': '240'})

# ── Required demo accounts ────────────────────────────────────────────────
def upsert_user(login, name, password, groups, action=None):
    u = Users.search([('login', '=', login)], limit=1)
    vals = {
        'name': name, 'login': login, 'password': password,
        'email': login, 'active': True,
        'group_ids': [(6, 0, [g.id for g in groups])],
    }
    if u:
        u.write(vals)
    else:
        u = Users.create(vals)
    if action and 'action_id' in u._fields:
        u.action_id = action.id
    return u

admin_user      = upsert_user('admin@demo.com',       'Demo Admin',      'admin123',  [grp_user, grp_admin], kiosk_action)
instructor_user = upsert_user('instructor1@demo.com',  'Alex Instructor', 'dojo@2026', [grp_user, grp_instructor])
student1_user   = upsert_user('demo1@demo.com',        'Jordan Smith',    'dojo@2026', [grp_portal])
student2_user   = upsert_user('demo2@demo.com',        'Casey Doe',       'dojo@2026', [grp_portal])
parent_user     = upsert_user('DemoParent@demo.com',   'Demo Parent',     'dojo@2026', [grp_portal])

# ── Members ───────────────────────────────────────────────────────────────
BELT_RANKS = ['white', 'yellow', 'orange', 'green', 'blue', 'purple', 'red', 'brown', 'black']

def upsert_member(email, name, belt=None, phone=None):
    m = Member.search([('email', '=', email)], limit=1)
    vals = {'name': name, 'email': email, 'company_id': env.company.id}
    if belt and 'belt_rank' in Member._fields:
        vals['belt_rank'] = belt
    if phone:
        vals['phone'] = phone
    if m:
        m.write(vals)
    else:
        m = Member.create(vals)
    return m

members = [
    upsert_member('demo1@demo.com',         'Jordan Smith',        'blue',   '555-0101'),
    upsert_member('demo2@demo.com',         'Casey Doe',           'green',  '555-0102'),
    upsert_member('john.smith@demo.com',    'John Smith',          'brown',  '555-0103'),
    upsert_member('jane.smith@demo.com',    'Jane Smith',          'purple', '555-0104'),
    upsert_member('bob.smithson@demo.com',  'Bob Smithson',        'yellow', '555-0105'),
    upsert_member('alice.doe@demo.com',     'Alice Doe',           'orange', '555-0106'),
    upsert_member('maria.santos@demo.com',  'Maria Santos',        'green',  '555-0107'),
    upsert_member('kim.park@demo.com',      'Kim Park',            'blue',   '555-0108'),
    upsert_member('tyler.nguyen@demo.com',  'Tyler Nguyen',        'white',  '555-0109'),
    upsert_member('sam.oconnor@demo.com',   "Sam O'Connor",        'red',    '555-0110'),
    upsert_member('pat.smith@demo.com',     'Pat Smith',           'yellow', '555-0111'),
    upsert_member('robin.lee@demo.com',     'Robin Lee',           'black',  '555-0112'),
]

# ── Instructor profile ────────────────────────────────────────────────────
InstructorProfile = None
for model in ('dojo.instructor.profile', 'dojo.instructor'):
    if model in env.registry:
        InstructorProfile = env[model].sudo()
        break

instructor_profile = None
if InstructorProfile is not None:
    instructor_profile = InstructorProfile.search([('user_id', '=', instructor_user.id)], limit=1)
    if not instructor_profile:
        instructor_profile = InstructorProfile.create({
            'user_id': instructor_user.id,
            'partner_id': instructor_user.partner_id.id,
            'name': instructor_user.name,
            'company_id': env.company.id,
        })

# ── Program and class template ─────────────────────────────────────────────
program = Program.search([('name', '=', 'REL-001 Demo Program')], limit=1)
if not program:
    program = Program.create({'name': 'REL-001 Demo Program', 'company_id': env.company.id})

tmpl_vals = {
    'name': 'Evening Fundamentals',
    'program_id': program.id,
    'level': 'all',
    'duration_minutes': 60,
    'max_capacity': 20,
    'company_id': env.company.id,
    'auto_enroll_members': False,
}
if instructor_profile and 'instructor_id' in Template._fields:
    tmpl_vals['instructor_id'] = instructor_profile.id
elif instructor_profile and 'instructor_ids' in Template._fields:
    tmpl_vals['instructor_ids'] = [(4, instructor_profile.id)]

template = Template.search([('name', '=', 'Evening Fundamentals')], limit=1)
if template:
    template.write(tmpl_vals)
else:
    template = Template.create(tmpl_vals)

# ── Sessions: active | upcoming_soon | upcoming | done ────────────────────
now = datetime.utcnow()

SESSIONS = [
    ('active',        now - timedelta(minutes=10), now + timedelta(minutes=50), 'open'),
    ('upcoming_soon', now + timedelta(minutes=8),  now + timedelta(minutes=68), 'open'),
    ('upcoming',      now + timedelta(minutes=90), now + timedelta(minutes=150), 'open'),
    ('done',          now - timedelta(hours=3),    now - timedelta(hours=2),    'done'),
]

session_records = {}
for label, t_start, t_end, state in SESSIONS:
    existing = Session.search([
        ('template_id', '=', template.id),
        ('start_datetime', '>=', (now - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')),
        ('start_datetime', '<=', (now + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')),
        ('state', '=', state),
    ], limit=1) if label != 'done' else Session.search([
        ('template_id', '=', template.id),
        ('start_datetime', '<', now.strftime('%Y-%m-%d %H:%M:%S')),
        ('state', '=', 'done'),
    ], limit=1)

    sess_vals = {
        'template_id': template.id,
        'company_id': env.company.id,
        'start_datetime': t_start,
        'end_datetime': t_end,
        'capacity': 20,
        'state': state,
    }
    if instructor_profile and 'instructor_id' in Session._fields:
        sess_vals['instructor_id'] = instructor_profile.id

    if existing:
        existing.write(sess_vals)
        session_records[label] = existing
    else:
        session_records[label] = Session.create(sess_vals)

# ── Enroll all members in the active session ──────────────────────────────
active_session = session_records['active']
for m in members:
    existing_enroll = env['dojo.class.enrollment'].sudo().search([
        ('session_id', '=', active_session.id),
        ('member_id', '=', m.id),
    ], limit=1)
    if not existing_enroll:
        Enrollment.create({
            'session_id': active_session.id,
            'member_id': m.id,
            'status': 'registered',
            'attendance_state': 'pending',
        })

# Mark a few as present in the done session for dashboard check-in count
done_session = session_records['done']
for m in members[:5]:
    existing = env['dojo.class.enrollment'].sudo().search([
        ('session_id', '=', done_session.id),
        ('member_id', '=', m.id),
    ], limit=1)
    if not existing:
        Enrollment.create({
            'session_id': done_session.id,
            'member_id': m.id,
            'status': 'registered',
            'attendance_state': 'present',
        })

# ── Kiosk config ──────────────────────────────────────────────────────────
kiosk = Kiosk.search([('name', '=', 'Front Desk Kiosk')], limit=1)
kiosk_vals = {
    'name': 'Front Desk Kiosk',
    'pin_code': '123456',
    'theme_mode': 'dark',
    'view_mode': 'search_only',
    'show_title': True,
    'active': True,
    'company_id': env.company.id,
}
if kiosk:
    kiosk.write(kiosk_vals)
else:
    kiosk = Kiosk.create(kiosk_vals)

ann = Announcement.search([('config_id', '=', kiosk.id), ('title', '=', 'Welcome')], limit=1)
if not ann:
    Announcement.create({
        'config_id': kiosk.id,
        'sequence': 10,
        'title': 'Welcome',
        'body': 'Tap your name to check in, or ask the front desk for help.',
        'active': True,
    })

# ── Onboarding records: varied completion states ──────────────────────────
ONBOARDING_STATES = [
    # (email, step_intro, step_uniform)
    ('demo1@demo.com',        False, False),   # ~0% — open tasks for kiosk demo
    ('demo2@demo.com',        True,  False),   # ~50%
    ('john.smith@demo.com',   True,  True),    # complete
    ('jane.smith@demo.com',   False, False),   # 0%
    ('bob.smithson@demo.com', True,  False),   # 50%
    ('alice.doe@demo.com',    True,  True),    # complete
]

for email, intro, uniform in ONBOARDING_STATES:
    m = Member.search([('email', '=', email)], limit=1)
    if not m:
        continue
    rec = Onboarding.search([('member_id', '=', m.id)], limit=1)
    o_vals = {'member_id': m.id, 'company_id': env.company.id, 'state': 'in_progress'}
    for field, val in [('step_intro_completed', intro), ('step_uniform_issued', uniform)]:
        if field in Onboarding._fields:
            o_vals[field] = val
    if rec:
        rec.write(o_vals)
    else:
        rec = Onboarding.create(o_vals)
    if hasattr(rec, '_sync_derived_steps'):
        rec._sync_derived_steps()

# ── Belt test record (dojo_belt_progression) ──────────────────────────────
if 'dojo.belt.test' in env.registry:
    BeltTest = env['dojo.belt.test'].sudo()
    bt = BeltTest.search([('name', 'like', 'REL-001 Demo')], limit=1)
    bt_vals = {
        'name': 'REL-001 Demo Belt Test',
        'company_id': env.company.id,
    }
    if 'test_date' in BeltTest._fields:
        bt_vals['test_date'] = (now + timedelta(days=7)).date()
    if not bt:
        BeltTest.create(bt_vals)

# ── Promotion history (dojo_belt_progression) ─────────────────────────────
if 'dojo.promotion.history' in env.registry:
    PromHist = env['dojo.promotion.history'].sudo()
    m_robin = Member.search([('email', '=', 'robin.lee@demo.com')], limit=1)
    if m_robin and not PromHist.search([('member_id', '=', m_robin.id)], limit=1):
        ph_vals = {
            'member_id': m_robin.id,
            'company_id': env.company.id,
            'promoted_by': instructor_user.id if 'promoted_by' in PromHist._fields else None,
        }
        for f in ('from_rank', 'rank_from'):
            if f in PromHist._fields:
                ph_vals[f] = 'red'
                break
        for f in ('to_rank', 'rank_to'):
            if f in PromHist._fields:
                ph_vals[f] = 'black'
                break
        if 'promotion_date' in PromHist._fields:
            ph_vals['promotion_date'] = (now - timedelta(days=30)).date()
        ph_vals = {k: v for k, v in ph_vals.items() if v is not None}
        PromHist.create(ph_vals)

env.cr.commit()

# ── Print access info ─────────────────────────────────────────────────────
kiosk_url = kiosk.kiosk_url if hasattr(kiosk, 'kiosk_url') and kiosk.kiosk_url else 'http://localhost:8070/kiosk'
session_window = f"{(now - timedelta(minutes=10)).strftime('%H:%M')} – {(now + timedelta(minutes=50)).strftime('%H:%M')} UTC"

print()
print("=" * 60)
print("REL-001 DEMO ENVIRONMENT READY")
print("=" * 60)
print(f"Web:           http://localhost:8070/web/login")
print(f"Kiosk URL:     {kiosk_url}")
print(f"Kiosk PIN:     123456")
print(f"Active session window: {session_window}")
print()
print("Logins:")
print("  admin@demo.com        / admin123   (admin)")
print("  instructor1@demo.com  / dojo@2026  (instructor)")
print("  demo1@demo.com        / dojo@2026  (student, Jordan Smith)")
print("  demo2@demo.com        / dojo@2026  (student, Casey Doe)")
print("  DemoParent@demo.com   / dojo@2026  (parent)")
print()
print("Search demo members:")
print("  'Smi'     -> Jordan Smith, John Smith, Jane Smith, Bob Smithson, Pat Smith")
print("  'Smith J' -> Jordan Smith, Jane Smith (flexible order)")
print("  'Doe'     -> Casey Doe, Alice Doe")
print()
print("After the demo: reset auto-close grace ->")
print("  ir.config_parameter  dojo_core.session_auto_close_grace_minutes = 60")
print("=" * 60)
PY

docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web \
  shell -c /etc/odoo/odoo.conf -d odoo19 < "$TMP_PY"

echo
echo "Re-run this script right before the demo to re-center session times."

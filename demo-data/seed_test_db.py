"""
Test DB demo seeds — full schema.

Creates:
  • Martial-art styles + standard TKD/BJJ belt ranks
  • Programs (linked to styles + belt ranks)
  • An instructor profile
  • Class templates with weekly recurrence ENABLED, then generates sessions
  • Subscription plans (program- and course-based)
  • Dojo members (kids, teens, adults), some assigned to subscription plans
  • Member ranks (current_rank_id) for active members
  • A scheduled belt test with registrations
  • CRM leads spread across pipeline stages

Run:
  sudo systemctl stop odoo19-test.service
  sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/python3 /opt/odoo19/odoo19/odoo-bin shell \
      -c /etc/odoo19-test.conf -d test --no-http \
      < /opt/odoo19/odoo19/custom-addons-test/demo-data/seed_test_db.py
  sudo systemctl start odoo19-test.service

Idempotent: re-runs clean previous seeded records (by tag / @seed.test email / SEED marker).
"""
from datetime import date, datetime, timedelta
import random

random.seed(42)

SEED_TAG = "demo_seed_test"
SEED_PREFIX = "SEED · "
PASSWORD_DOMAIN = "@seed.test"

today = date.today()


# ---------------------------------------------------------------------------
# 0. Cleanup
# ---------------------------------------------------------------------------
print("=" * 60)
print("CLEANUP previous seed data")
print("=" * 60)

Tag = env["crm.tag"]
seed_tag = Tag.search([("name", "=", SEED_TAG)], limit=1) or Tag.create({"name": SEED_TAG})

old_leads = env["crm.lead"].search([("tag_ids", "in", seed_tag.id)])
print(f"  leads → unlink {len(old_leads)}")
old_leads.unlink()

# Class enrollments → sessions → templates
old_enrolls = env["dojo.class.enrollment"].search(
    [("session_id.template_id.name", "=like", f"{SEED_PREFIX}%")]
)
if old_enrolls:
    print(f"  dojo.class.enrollment → unlink {len(old_enrolls)}")
    old_enrolls.unlink()
old_sessions = env["dojo.class.session"].search([("template_id.name", "=like", f"{SEED_PREFIX}%")])
if old_sessions:
    print(f"  dojo.class.session → unlink {len(old_sessions)}")
    old_sessions.unlink()
old_templates = env["dojo.class.template"].search([("name", "=like", f"{SEED_PREFIX}%")])
if old_templates:
    print(f"  dojo.class.template → unlink {len(old_templates)}")
    old_templates.unlink()

# Belt-test registrations → tests
old_btr = env["dojo.belt.test.registration"].search(
    [("test_id.name", "=like", f"{SEED_PREFIX}%")]
)
if old_btr:
    print(f"  dojo.belt.test.registration → unlink {len(old_btr)}")
    old_btr.unlink()
old_tests = env["dojo.belt.test"].search([("name", "=like", f"{SEED_PREFIX}%")])
if old_tests:
    print(f"  dojo.belt.test → unlink {len(old_tests)}")
    old_tests.unlink()

# Member ranks (notes contains SEED)
old_mranks = env["dojo.member.rank"].search([("notes", "=like", "%SEED%")])
if old_mranks:
    print(f"  dojo.member.rank → unlink {len(old_mranks)}")
    old_mranks.unlink()

# Subscriptions for seed plans
old_subs = env["sale.subscription"].search([("plan_id.name", "=like", f"{SEED_PREFIX}%")])
if old_subs:
    print(f"  sale.subscription → unlink {len(old_subs)}")
    try:
        old_subs.unlink()
    except Exception as e:
        print(f"    skip subs: {e}")

# Subscription plans
old_plans = env["dojo.subscription.plan"].search([("name", "=like", f"{SEED_PREFIX}%")])
if old_plans:
    print(f"  dojo.subscription.plan → unlink {len(old_plans)}")
    try:
        old_plans.unlink()
    except Exception as e:
        print(f"    skip plans: {e}")

# Members + partners
old_members = env["dojo.member"].search([("partner_id.email", "=ilike", f"%{PASSWORD_DOMAIN}")])
old_partners = old_members.mapped("partner_id")
print(f"  dojo.member → unlink {len(old_members)}")
old_members.unlink()
old_partners.unlink()
stray = env["res.partner"].search([
    ("email", "=ilike", f"%{PASSWORD_DOMAIN}"),
    ("user_ids", "=", False),
])
if stray:
    print(f"  res.partner stragglers → unlink {len(stray)}")
    try:
        stray.unlink()
    except Exception as e:
        env.cr.rollback()
        print(f"    skip stragglers: {e}")

env.cr.commit()


# ---------------------------------------------------------------------------
# 1. Martial-art styles + Belt ranks
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STYLES & BELT RANKS")
print("=" * 60)

Style = env["dojo.martial.art.style"]
BeltRank = env["dojo.belt.rank"]

def get_or_create_style(name, code, desc):
    s = Style.search([("code", "=", code)], limit=1)
    if not s:
        s = Style.create({"name": name, "code": code, "description": desc})
        print(f"  + style {name}")
    return s

tkd = get_or_create_style("Taekwondo", "TKD", "Korean martial art (kicks, striking).")
bjj = get_or_create_style("Brazilian Jiu-Jitsu", "BJJ", "Ground grappling and submissions.")

TKD_BELTS = [
    # name, sequence, color, attendance_threshold, max_stripes, is_dan, dan_level
    ("White Belt",          10, "#ffffff",   0, 0, False, 0),
    ("Yellow Belt",         20, "#f9c800",  15, 3, False, 0),
    ("Green Belt",          30, "#2e7d32",  25, 3, False, 0),
    ("Blue Belt",           40, "#1565c0",  35, 3, False, 0),
    ("Red Belt",            50, "#c62828",  50, 3, False, 0),
    ("Black Belt 1st Dan",  60, "#212121", 100, 0, True,  1),
]
BJJ_BELTS = [
    ("White Belt (BJJ)",  10, "#ffffff",   0, 4, False, 0),
    ("Blue Belt (BJJ)",   20, "#1565c0",  60, 4, False, 0),
    ("Purple Belt (BJJ)", 30, "#6a1b9a", 100, 4, False, 0),
    ("Brown Belt (BJJ)",  40, "#5d4037", 150, 4, False, 0),
    ("Black Belt (BJJ)",  50, "#212121", 200, 6, True,  1),
]

def upsert_rank(style, spec):
    name, seq, color, thr, stripes, is_dan, dan_level = spec
    r = BeltRank.search([("name", "=", name), ("style_id", "=", style.id)], limit=1)
    if r:
        return r
    return BeltRank.create({
        "name": name, "sequence": seq, "color": color, "style_id": style.id,
        "attendance_threshold": thr, "max_stripes": stripes,
        "is_dan": is_dan, "dan_level": dan_level,
    })

tkd_ranks = [upsert_rank(tkd, b) for b in TKD_BELTS]
bjj_ranks = [upsert_rank(bjj, b) for b in BJJ_BELTS]
print(f"  TKD ranks: {len(tkd_ranks)}  BJJ ranks: {len(bjj_ranks)}")


# ---------------------------------------------------------------------------
# 2. Instructor profile
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("INSTRUCTOR PROFILE")
print("=" * 60)

Instructor = env["dojo.instructor.profile"]
Users = env["res.users"]
inst_user = Users.search([("login", "=", "instructor.kim@seed.test")], limit=1)
if not inst_user:
    inst_user = Users.create({
        "name": "Master Kim",
        "login": "instructor.kim@seed.test",
        "email": "instructor.kim@seed.test",
    })
    inst_user.partner_id.write({"phone": "+1-555-0001"})
inst_partner = inst_user.partner_id
inst = Instructor.search([("user_id", "=", inst_user.id)], limit=1)
if not inst:
    vals = {
        "name": "Master Kim",
        "user_id": inst_user.id,
        "partner_id": inst_partner.id,
    }
    inst = Instructor.create(vals)
print(f"  instructor: {inst_partner.name} (id={inst.id})")


# ---------------------------------------------------------------------------
# 3. Programs (linked to styles + belt ranks)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("PROGRAMS")
print("=" * 60)

Program = env["dojo.program"]
program_specs = [
    ("Preschool Taekwondo",    "TKD-PRE",  tkd, tkd_ranks, False),
    ("Kids Taekwondo",         "TKD-KID",  tkd, tkd_ranks, False),
    ("Teen & Adult Taekwondo", "TKD-ADT",  tkd, tkd_ranks, False),
    ("Adult BJJ",              "BJJ-ADT",  bjj, bjj_ranks, False),
    ("Free Trial Class",       "TRIAL",    tkd, [],        True),
]
programs = {}
for name, code, style, ranks, is_trial in program_specs:
    p = Program.search([("name", "=", name)], limit=1)
    vals = {
        "name": name, "code": code,
        "style_id": style.id,
        "is_trial": is_trial,
        "manager_instructor_id": inst.id,
    }
    if ranks:
        vals["belt_rank_ids"] = [(6, 0, [r.id for r in ranks])]
    if p:
        p.write(vals)
    else:
        p = Program.create(vals)
        print(f"  + {name}")
    programs[name] = p


# ---------------------------------------------------------------------------
# 4. Class templates with weekly recurrence
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("CLASS TEMPLATES (with recurrence)")
print("=" * 60)

Template = env["dojo.class.template"]

def time_to_float(h, m=0):
    return h + m / 60.0

template_specs = [
    # (name, program, level, duration, capacity, days_dict, time_h, time_m)
    (f"{SEED_PREFIX}Tiny Tigers TKD",       "Preschool Taekwondo",    "beginner",     30, 12, dict(rec_mon=True, rec_wed=True),               16, 0),
    (f"{SEED_PREFIX}Kids TKD Beginners",    "Kids Taekwondo",         "beginner",     45, 20, dict(rec_mon=True, rec_wed=True, rec_fri=True), 17, 0),
    (f"{SEED_PREFIX}Kids TKD Intermediate", "Kids Taekwondo",         "intermediate", 45, 20, dict(rec_tue=True, rec_thu=True),               18, 0),
    (f"{SEED_PREFIX}Teen/Adult TKD",        "Teen & Adult Taekwondo", "all",          60, 25, dict(rec_mon=True, rec_wed=True, rec_fri=True), 19, 0),
    (f"{SEED_PREFIX}TKD Sparring",          "Teen & Adult Taekwondo", "advanced",     60, 15, dict(rec_sat=True),                             10, 0),
    (f"{SEED_PREFIX}BJJ Fundamentals",      "Adult BJJ",              "beginner",     60, 20, dict(rec_tue=True, rec_thu=True),               19, 30),
    (f"{SEED_PREFIX}BJJ Open Mat",          "Adult BJJ",              "all",          90, 30, dict(rec_sat=True),                             11, 0),
    (f"{SEED_PREFIX}Free Trial",            "Free Trial Class",       "beginner",     45,  6, dict(rec_sat=True),                              9, 0),
]

level_field = Template._fields.get("level")
allowed_levels = set()
if level_field and getattr(level_field, "selection", None):
    allowed_levels = {k for k, _ in level_field.selection}

templates = []
for name, prog_name, level, dur, cap, days, h, m in template_specs:
    if allowed_levels and level not in allowed_levels:
        level = next(iter(allowed_levels))
    vals = {
        "name": name,
        "program_id": programs[prog_name].id,
        "duration_minutes": dur,
        "max_capacity": cap,
        "instructor_profile_ids": [(6, 0, [inst.id])],
        "recurrence_active": True,
        "recurrence_time": time_to_float(h, m),
        "recurrence_start_date": today,
        "recurrence_end_date": today + timedelta(days=120),
        "recurrence_instructor_id": inst.id,
    }
    if level_field:
        vals["level"] = level
    vals.update(days)
    t = Template.create(vals)
    templates.append(t)
    days_str = ",".join(k.replace("rec_", "") for k, v in days.items() if v)
    print(f"  + {name}  [{days_str} @ {h:02d}:{m:02d}]")

env.cr.commit()


# ---------------------------------------------------------------------------
# 5. Generate sessions for the next 60 days
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("GENERATING SESSIONS")
print("=" * 60)

sessions_before = env["dojo.class.session"].search_count([])
for t in templates:
    try:
        t.action_generate_sessions()
    except Exception as e:
        print(f"  ! {t.name}: {e}")
sessions_after = env["dojo.class.session"].search_count([])
print(f"  sessions created: {sessions_after - sessions_before}")


# ---------------------------------------------------------------------------
# 6. Subscription plans
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("SUBSCRIPTION PLANS")
print("=" * 60)

Plan = env["dojo.subscription.plan"]

plan_specs = [
    {
        "name": f"{SEED_PREFIX}Kids TKD Unlimited",
        "code": "SEED-KID-UNL",
        "price": 149.0, "initial_fee": 50.0,
        "billing_period": "monthly", "duration": 0,
        "plan_type": "program",
        "program_ids": [programs["Kids Taekwondo"].id, programs["Preschool Taekwondo"].id],
        "description": "Unlimited Taekwondo classes for kids age 4-12.",
    },
    {
        "name": f"{SEED_PREFIX}Adult TKD Standard",
        "code": "SEED-ADT-STD",
        "price": 169.0, "initial_fee": 0.0,
        "billing_period": "monthly", "duration": 0,
        "plan_type": "program",
        "program_ids": [programs["Teen & Adult Taekwondo"].id],
        "description": "Standard adult/teen TKD membership.",
    },
    {
        "name": f"{SEED_PREFIX}BJJ Unlimited",
        "code": "SEED-BJJ-UNL",
        "price": 189.0, "initial_fee": 75.0,
        "billing_period": "monthly", "duration": 0,
        "plan_type": "program",
        "program_ids": [programs["Adult BJJ"].id],
        "description": "Unlimited BJJ classes.",
    },
    {
        "name": f"{SEED_PREFIX}Family — Multi-Program",
        "code": "SEED-FAMILY",
        "price": 249.0, "initial_fee": 50.0,
        "billing_period": "monthly", "duration": 12,
        "plan_type": "program",
        "program_ids": [programs[n].id for n in ("Kids Taekwondo", "Teen & Adult Taekwondo", "Adult BJJ")],
        "description": "12-month family plan covering Kids TKD, Adult TKD and BJJ.",
    },
    {
        "name": f"{SEED_PREFIX}Sparring Course (8-week)",
        "code": "SEED-SPAR",
        "price": 240.0, "initial_fee": 0.0,
        "billing_period": "monthly", "duration": 2,
        "plan_type": "course",
        "allowed_template_ids": [t.id for t in templates if "Sparring" in t.name],
        "description": "8-week sparring course (course-based).",
    },
]

plans_by_code = {}
for spec in plan_specs:
    code = spec["code"]
    p = Plan.search([("code", "=", code)], limit=1)
    vals = dict(spec)
    if vals.get("program_ids"):
        vals["program_ids"] = [(6, 0, vals["program_ids"])]
    if vals.get("allowed_template_ids"):
        vals["allowed_template_ids"] = [(6, 0, vals["allowed_template_ids"])]
    if p:
        p.write(vals)
    else:
        p = Plan.create(vals)
    plans_by_code[code] = p
    print(f"  + plan {p.name} (${p.price})")

env.cr.commit()


# ---------------------------------------------------------------------------
# 7. Members
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("MEMBERS")
print("=" * 60)

Partner = env["res.partner"]
Member = env["dojo.member"]

member_specs = [
    # (first, last, email, phone, dob, state, program, gender, plan_code)
    ("Mason",   "Carter",   "mason.carter@seed.test",   "+1-555-0101", date(2015, 3, 12),  "active",    "Kids Taekwondo",         "male",   "SEED-KID-UNL"),
    ("Olivia",  "Nguyen",   "olivia.nguyen@seed.test",  "+1-555-0102", date(2014, 7, 22),  "active",    "Kids Taekwondo",         "female", "SEED-KID-UNL"),
    ("Liam",    "Garcia",   "liam.garcia@seed.test",    "+1-555-0103", date(2016, 11, 5),  "active",    "Preschool Taekwondo",    "male",   "SEED-KID-UNL"),
    ("Sofia",   "Patel",    "sofia.patel@seed.test",    "+1-555-0104", date(2013, 1, 30),  "active",    "Kids Taekwondo",         "female", "SEED-KID-UNL"),
    ("Ethan",   "Kim",      "ethan.kim@seed.test",      "+1-555-0105", date(2010, 9, 17),  "active",    "Teen & Adult Taekwondo", "male",   "SEED-ADT-STD"),
    ("Ava",     "Brown",    "ava.brown@seed.test",      "+1-555-0106", date(1989, 4, 2),   "active",    "Teen & Adult Taekwondo", "female", "SEED-ADT-STD"),
    ("Noah",    "Wilson",   "noah.wilson@seed.test",    "+1-555-0107", date(1992, 12, 19), "trial",     "Adult BJJ",              "male",   None),
    ("Mia",     "Davis",    "mia.davis@seed.test",      "+1-555-0108", date(2017, 6, 8),   "trial",     "Preschool Taekwondo",    "female", None),
    ("Lucas",   "Martinez", "lucas.martinez@seed.test", "+1-555-0109", date(1985, 2, 14),  "paused",    "Adult BJJ",              "male",   "SEED-BJJ-UNL"),
    ("Isabella","Lopez",    "isabella.lopez@seed.test", "+1-555-0110", date(2012, 10, 27), "active",    "Kids Taekwondo",         "female", "SEED-FAMILY"),
    ("James",   "Anderson", "james.anderson@seed.test", "+1-555-0111", date(1978, 8, 3),   "active",    "Adult BJJ",              "male",   "SEED-BJJ-UNL"),
    ("Emma",    "Taylor",   "emma.taylor@seed.test",    "+1-555-0112", date(2018, 5, 21),  "trial",     "Preschool Taekwondo",    "female", None),
    ("Daniel",  "Walker",   "daniel.walker@seed.test",  "+1-555-0113", date(1995, 6, 14),  "active",    "Teen & Adult Taekwondo", "male",   "SEED-ADT-STD"),
    ("Chloe",   "Roberts",  "chloe.roberts@seed.test",  "+1-555-0114", date(2011, 3, 9),   "active",    "Kids Taekwondo",         "female", "SEED-KID-UNL"),
    ("Henry",   "Scott",    "henry.scott@seed.test",    "+1-555-0115", date(1980, 11, 30), "cancelled", "Adult BJJ",              "male",   None),
]

members_info = []
gender_field = Member._fields.get("gender")
allowed_genders = set()
if gender_field and getattr(gender_field, "selection", None):
    allowed_genders = {k for k, _ in gender_field.selection}

for first, last, email, phone, dob, state, prog_name, gender, plan_code in member_specs:
    partner = Partner.create({
        "name": f"{first} {last}",
        "email": email,
        "phone": phone,
        "is_company": False,
    })
    vals = {
        "partner_id": partner.id,
        "date_of_birth": dob,
        "membership_state": state,
    }
    if gender_field and gender in allowed_genders:
        vals["gender"] = gender
    member = Member.create(vals)
    members_info.append((member, prog_name, plan_code))

print(f"  members created: {len(members_info)}")

env.cr.commit()


# ---------------------------------------------------------------------------
# 8. Member ranks
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("MEMBER RANKS")
print("=" * 60)

MemberRank = env["dojo.member.rank"]

program_ranks = {
    "Preschool Taekwondo":    tkd_ranks,
    "Kids Taekwondo":         tkd_ranks,
    "Teen & Adult Taekwondo": tkd_ranks,
    "Adult BJJ":              bjj_ranks,
}

ranks_assigned = 0
for member, prog_name, _plan in members_info:
    if member.membership_state not in ("active", "paused"):
        continue
    pool = program_ranks.get(prog_name) or []
    if not pool:
        continue
    rank = random.choice(pool[: max(1, len(pool) - 1)])
    program = programs[prog_name]
    MemberRank.create({
        "member_id": member.id,
        "rank_id": rank.id,
        "program_id": program.id,
        "date_awarded": today - timedelta(days=random.randint(30, 365)),
        "stripe_count": random.randint(0, max(0, rank.max_stripes)),
        "notes": "SEED initial rank",
    })
    if "current_rank_id" in member._fields:
        member.current_rank_id = rank.id
    ranks_assigned += 1
print(f"  member ranks assigned: {ranks_assigned}")

env.cr.commit()


# ---------------------------------------------------------------------------
# 9. Subscriptions
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("MEMBER SUBSCRIPTIONS")
print("=" * 60)

Sub = env["sale.subscription"]
default_pricelist = env["product.pricelist"].search([], limit=1)
if not default_pricelist:
    default_pricelist = env["product.pricelist"].create({"name": "SEED · Default", "currency_id": env.company.currency_id.id})
sub_count = 0
for member, prog_name, plan_code in members_info:
    if not plan_code:
        continue
    plan = plans_by_code.get(plan_code)
    if not plan:
        continue
    vals = {
        "partner_id": member.partner_id.id,
        "member_id": member.id,
        "plan_id": plan.id,
    }
    if default_pricelist:
        vals["pricelist_id"] = default_pricelist.id
    if plan.template_id:
        vals["template_id"] = plan.template_id.id
    if plan.program_ids:
        vals["program_ids"] = [(6, 0, plan.program_ids.ids)]
    try:
        Sub.create(vals)
        sub_count += 1
    except Exception as e:
        env.cr.rollback()
        print(f"  ! sub for {member.partner_id.email}: {e}")
print(f"  subscriptions created: {sub_count}")

env.cr.commit()


# ---------------------------------------------------------------------------
# 10. Belt tests + registrations
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("BELT TESTS")
print("=" * 60)

BeltTest = env["dojo.belt.test"]
BTR = env["dojo.belt.test.registration"]

upcoming = BeltTest.create({
    "name": f"{SEED_PREFIX}Spring TKD Belt Test",
    "test_date": today + timedelta(days=21),
    "location": "Main Dojo Floor",
    "instructor_profile_id": inst.id,
    "program_id": programs["Kids Taekwondo"].id,
    "max_participants": 20,
    "state": "scheduled",
})
print(f"  + {upcoming.name}  ({upcoming.test_date})")

past = BeltTest.create({
    "name": f"{SEED_PREFIX}Winter TKD Belt Test",
    "test_date": today - timedelta(days=45),
    "location": "Main Dojo Floor",
    "instructor_profile_id": inst.id,
    "program_id": programs["Teen & Adult Taekwondo"].id,
    "max_participants": 20,
    "state": "completed",
})
print(f"  + {past.name}  (completed)")

upcoming_regs = past_regs = 0
for member, prog_name, _plan in members_info:
    if "Taekwondo" not in prog_name or not member.current_rank_id:
        continue
    if member.membership_state != "active":
        continue
    next_rank = next((r for r in tkd_ranks if r.sequence > member.current_rank_id.sequence), None)
    if not next_rank:
        continue
    BTR.create({
        "test_id": upcoming.id,
        "member_id": member.id,
        "target_rank_id": next_rank.id,
        "program_id": programs[prog_name].id,
        "result": "pending",
    })
    upcoming_regs += 1

for idx, (member, prog_name, _plan) in enumerate(members_info):
    if "Taekwondo" not in prog_name or not member.current_rank_id:
        continue
    if past_regs >= 4:
        break
    next_rank = next((r for r in tkd_ranks if r.sequence > member.current_rank_id.sequence), None)
    if not next_rank:
        continue
    BTR.create({
        "test_id": past.id,
        "member_id": member.id,
        "target_rank_id": next_rank.id,
        "program_id": programs[prog_name].id,
        "result": "pass" if idx % 3 != 0 else "fail",
    })
    past_regs += 1

print(f"  upcoming registrations: {upcoming_regs}")
print(f"  past registrations:     {past_regs}")

env.cr.commit()


# ---------------------------------------------------------------------------
# 11. CRM Leads (full pipeline)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("CRM LEADS")
print("=" * 60)

Lead = env["crm.lead"]
Stage = env["crm.stage"]

stages_by_name = {}
for s in Stage.search([("sequence", ">=", 10)]):
    stages_by_name[s.name] = s

def stage(name):
    return stages_by_name.get(name) or Stage.search([("name", "=", name)], limit=1)

def tag(name):
    return Tag.search([("name", "=", name)], limit=1)

team = env["crm.team"].search([], limit=1)

lead_specs = [
    ("Free trial — Aiden Walsh",       "Aiden Walsh",     "aiden.walsh@seed.test",     "+1-555-0201", "New",               "Online",   "Kids Taekwondo",         "Child", 1),
    ("Walk-in — Bella Hughes",         "Bella Hughes",    "bella.hughes@seed.test",    "+1-555-0202", "New",               "Walk-In",  "Teen & Adult Taekwondo", "Teen",  2),
    ("Referral — Caleb Stone",         "Caleb Stone",     "caleb.stone@seed.test",     "+1-555-0203", "Qualified",         "Referral", "Adult BJJ",              "Adult", 3),
    ("Website inquiry — Daria Volkov", "Daria Volkov",    "daria.volkov@seed.test",    "+1-555-0204", "Qualified",         "Online",   "Teen & Adult Taekwondo", "Adult", 5),
    ("Trial booked — Ezra Lin",        "Ezra Lin",        "ezra.lin@seed.test",        "+1-555-0205", "Trial Booked",      "Online",   "Kids Taekwondo",         "Child", 6),
    ("Trial booked — Fatima Hassan",   "Fatima Hassan",   "fatima.hassan@seed.test",   "+1-555-0206", "Trial Booked",      "Event",    "Adult BJJ",              "Adult", 7),
    ("Trial running — Grayson Reed",   "Grayson Reed",    "grayson.reed@seed.test",    "+1-555-0207", "Trial-in-progress", "Walk-In",  "Teen & Adult Taekwondo", "Teen",  10),
    ("Trial running — Harper Quinn",   "Harper Quinn",    "harper.quinn@seed.test",    "+1-555-0208", "Trial-in-progress", "Referral", "Kids Taekwondo",         "Child", 11),
    ("Evaluating plan — Ivan Petrov",  "Ivan Petrov",     "ivan.petrov@seed.test",     "+1-555-0209", "Evaluation",        "Online",   "Adult BJJ",              "Adult", 14),
    ("Pricing requested — Jade Kim",   "Jade Kim",        "jade.kim@seed.test",        "+1-555-0210", "Evaluation",        "Online",   "Teen & Adult Taekwondo", "Teen",  15),
    ("Signed up — Kai Bennett",        "Kai Bennett",     "kai.bennett@seed.test",     "+1-555-0211", "Won",               "Referral", "Kids Taekwondo",         "Child", 21),
    ("Signed up — Luna Rivera",        "Luna Rivera",     "luna.rivera@seed.test",     "+1-555-0212", "Won",               "Walk-In",  "Adult BJJ",              "Adult", 25),
    ("Cold inquiry — Marcus Cole",     "Marcus Cole",     "marcus.cole@seed.test",     "+1-555-0213", "New",               "Online",   "Teen & Adult Taekwondo", "Adult", 0),
    ("Birthday party — Nina Park",     "Nina Park",       "nina.park@seed.test",       "+1-555-0214", "New",               "Event",    "Kids Taekwondo",         "Child", 0),
    ("Family of 3 — Owen Brooks",      "Owen Brooks",     "owen.brooks@seed.test",     "+1-555-0215", "Qualified",         "Referral", "Kids Taekwondo",         "Child", 4),
]

leads_count = 0
for name, contact, email, phone, stage_name, src, prog, age, days_ago in lead_specs:
    s = stage(stage_name)
    tag_ids = [t.id for t in (tag(src), tag(prog), tag(age), seed_tag) if t]
    lead = Lead.create({
        "name": name,
        "contact_name": contact,
        "email_from": email,
        "phone": phone,
        "stage_id": s.id if s else False,
        "tag_ids": [(6, 0, tag_ids)],
        "type": "lead",
        "team_id": team.id if team else False,
        "description": "Demo seed lead.",
    })
    create_dt = today - timedelta(days=days_ago)
    env.cr.execute(
        "UPDATE crm_lead SET create_date=%s, write_date=%s WHERE id=%s",
        (create_dt, create_dt, lead.id),
    )
    leads_count += 1
print(f"  leads created: {leads_count}")

env.cr.commit()


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("SEED COMPLETE")
print("=" * 60)
counts = [
    ("styles",               "dojo.martial.art.style"),
    ("belt ranks",           "dojo.belt.rank"),
    ("programs",             "dojo.program"),
    ("class templates",      "dojo.class.template"),
    ("class sessions",       "dojo.class.session"),
    ("members",              "dojo.member"),
    ("member ranks",         "dojo.member.rank"),
    ("subscription plans",   "dojo.subscription.plan"),
    ("member subscriptions", "sale.subscription"),
    ("belt tests",           "dojo.belt.test"),
    ("belt registrations",   "dojo.belt.test.registration"),
    ("CRM leads",            "crm.lead"),
]
for label, model in counts:
    print(f"  {label:22s}: {env[model].search_count([])}")

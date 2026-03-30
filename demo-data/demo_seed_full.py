"""
Full demo seed — creates ALL demo data from scratch.

Covers: Martial art styles, programs, belt ranks, instructors, parents,
students, households, subscription plans, member subscriptions, invoices,
class templates, sessions (past + future), enrollments, attendance logs,
credit transactions, points, belt tests, emergency contacts, auto-enroll,
kiosk config, and marketing cards.

Run:
  DB_PASS=$(cat config/odoo_pg_pass)
  docker compose exec -T web odoo shell -d odoo19 --db_host db --db_port 5432 \
    --db_user odoo --db_password "$DB_PASS" < demo-data/demo_seed_full.py

Accounts (password: dojo@2026):
  instructor1@demo.com  Alex Johnson     Head Instructor (BJJ)
  instructor2@demo.com  Sam Rivera       Asst. Instructor (BJJ)
  instructor3@demo.com  Kenji Tanaka     Judo Instructor
  parent1@demo.com      Mary Smith       Smith Household guardian
  parent2@demo.com      Bob Jones        Jones Household guardian
  student1@demo.com     Jordan Smith     Kids BJJ, Smith HH
  student2@demo.com     Casey Smith      Kids BJJ, Smith HH
  student3@demo.com     Taylor Jones     Kids BJJ, Jones HH
  student4@demo.com     Morgan Jones     Kids BJJ, Jones HH
  student5@demo.com     Riley Lee        Adult BJJ, standalone
  student6@demo.com     Hiro Watanabe    Judo adult, standalone
  student7@demo.com     Emma Davis       Adult BJJ + Judo, standalone
"""
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

today = date.today()
now = datetime.now()
PASSWORD = "dojo@2026"

# ═══════════════════════════════════════════════════════════════════════════
#  CLEANUP
# ═══════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("CLEANUP: Removing prior demo data...")
print("=" * 60)

DEMO_LOGINS = [
    "instructor1@demo.com", "instructor2@demo.com", "instructor3@demo.com",
    "parent1@demo.com",     "parent2@demo.com",
    "student1@demo.com",    "student2@demo.com",
    "student3@demo.com",    "student4@demo.com",
    "student5@demo.com",    "student6@demo.com",
    "student7@demo.com",
]
existing_users = env["res.users"].search([("login", "in", DEMO_LOGINS)])
existing_partners = existing_users.mapped("partner_id")

# Attendance logs
env["dojo.attendance.log"].search([]).unlink()
# Points
if "dojo.points.transaction" in env:
    env["dojo.points.transaction"].search([]).unlink()
# Enrollments & sessions
env["dojo.class.enrollment"].search([]).unlink()
env["dojo.class.session"].search([]).unlink()
# Auto-enroll
env["dojo.course.auto.enroll"].search([]).unlink()

# Subscription invoices
_all_subs = env["sale.subscription"].search([])
if _all_subs:
    _sub_invs = env["account.move"].sudo().search([
        "|",
        ("subscription_id", "in", _all_subs.ids),
        ("dojo_subscription_ids", "in", _all_subs.ids),
    ])
    if _sub_invs:
        _sub_invs.mapped("line_ids").remove_move_reconcile()
        _sub_invs.filtered(lambda m: m.state == "posted").button_cancel()
        _sub_invs.unlink()
# Payments for demo partners
if existing_partners:
    _demo_pmts = env["account.payment"].sudo().search([
        ("partner_id", "in", existing_partners.ids)
    ])
    if _demo_pmts:
        _pmt_moves = _demo_pmts.mapped("move_id")
        if _pmt_moves:
            _pmt_moves.mapped("line_ids").remove_move_reconcile()
            _pmt_moves.filtered(lambda m: m.state == "posted").button_cancel()
            _pmt_moves.unlink()

# Credits
if "dojo.credit.transaction" in env:
    env["dojo.credit.transaction"].search([]).unlink()
# Subscriptions & plans
env["sale.subscription"].search([]).unlink()
env["dojo.subscription.plan"].search([]).unlink()
# Classes
env["dojo.class.template"].search([]).unlink()
# Programs
env["dojo.program"].search([]).unlink()
# Belt test registrations, belt tests, belt rank history
env["dojo.belt.test.registration"].search([]).unlink()
env["dojo.belt.test"].search([]).unlink()
env["dojo.member.rank"].search([]).unlink()
env["dojo.belt.rank"].search([]).unlink()
# Emergency contacts
env["dojo.emergency.contact"].search([]).unlink()
# Program enrollments
if "dojo.program.enrollment" in env:
    env["dojo.program.enrollment"].search([]).unlink()
# Members
demo_members = env["dojo.member"].search([("partner_id", "in", existing_partners.ids)])
# Payment tokens
if "payment.token" in env:
    demo_tokens = env["payment.token"].sudo().search([("partner_id", "in", existing_partners.ids)])
    if demo_tokens:
        env.cr.execute(
            "UPDATE payment_transaction SET token_id = NULL WHERE token_id IN %s",
            (tuple(demo_tokens.ids),)
        )
        demo_tokens.unlink()
demo_members.unlink()
# Instructor profiles
env["dojo.instructor.profile"].search([("user_id", "in", existing_users.ids)]).unlink()
remaining_users = env["res.users"].search([("login", "in", DEMO_LOGINS)])
if remaining_users:
    env.cr.execute(
        "UPDATE hr_employee SET user_id = NULL WHERE user_id IN %s",
        (tuple(remaining_users.ids),)
    )
    remaining_users.unlink()
# Kiosk
if "dojo.kiosk.config" in env:
    env["dojo.kiosk.config"].search([("name", "=", "Demo Kiosk")]).unlink()
# Marketing cards
if "dojo.marketing.card" in env:
    env["dojo.marketing.card"].search([("name", "ilike", "demo")]).unlink()
# Waiver config
if "dojo.waiver.config" in env:
    env["dojo.waiver.config"].search([("name", "=", "Demo Waiver")]).unlink()
# Checkout config
if "dojo.checkout.config" in env:
    env["dojo.checkout.config"].search([]).unlink()
if "dojo.checkout.upsell" in env:
    env["dojo.checkout.upsell"].search([]).unlink()
print("  cleanup done.\n")


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════
group_instructor     = env.ref("dojo_core.group_dojo_instructor")
group_user           = env.ref("base.group_user")
group_parent_student = env.ref("dojo_core.group_dojo_parent_student")


def make_user(name, login, groups):
    u = env["res.users"].create({
        "name": name, "login": login, "email": login,
        "group_ids": [(6, 0, [g.id for g in groups])],
    })
    u.password = PASSWORD
    return u


# ═══════════════════════════════════════════════════════════════════════════
#  1. MARTIAL ART STYLES
# ═══════════════════════════════════════════════════════════════════════════
print("1. Setting up martial art styles...")
styles = {}
style_defs = [
    ("Brazilian Jiu-Jitsu", "bjj", "Ground fighting, submissions, and positional control."),
    ("Judo",                "judo", "Throws, takedowns, and ground techniques."),
    ("Muay Thai",           "mt",   "Thai boxing with punches, kicks, elbows and knees."),
]
for sname, scode, sdesc in style_defs:
    existing = env["dojo.martial.art.style"].search([("code", "=", scode)], limit=1)
    if existing:
        styles[scode] = existing
    else:
        styles[scode] = env["dojo.martial.art.style"].create({
            "name": sname, "code": scode, "description": sdesc, "active": True,
        })
    print(f"  {sname} ({scode})")


# ═══════════════════════════════════════════════════════════════════════════
#  2. BELT RANKS (per style)
# ═══════════════════════════════════════════════════════════════════════════
print("\n2. Creating belt ranks...")
ranks = {}

bjj_rank_defs = [
    ("White Belt",  10,  "#ffffff", 0,   4),
    ("Yellow Belt", 20,  "#f9a825", 20,  4),
    ("Orange Belt", 30,  "#ef6c00", 30,  4),
    ("Green Belt",  40,  "#2e7d32", 40,  4),
    ("Blue Belt",   50,  "#1565c0", 50,  4),
    ("Purple Belt", 60,  "#6a1b9a", 70,  4),
    ("Brown Belt",  70,  "#4e342e", 90,  4),
    ("Black Belt",  80,  "#212529", 120, 0),
]
for rname, seq, color, threshold, max_stripes in bjj_rank_defs:
    ranks[f"bjj_{rname}"] = env["dojo.belt.rank"].create({
        "name": rname, "sequence": seq, "color": color,
        "style_id": styles["bjj"].id, "active": True,
        "attendance_threshold": threshold, "max_stripes": max_stripes,
    })
    print(f"  BJJ: {rname}")

judo_rank_defs = [
    ("White Belt (6th Kyu)",  10, "#ffffff", 0,   0),
    ("Yellow Belt (5th Kyu)", 20, "#f9a825", 25,  0),
    ("Orange Belt (4th Kyu)", 30, "#ef6c00", 35,  0),
    ("Green Belt (3rd Kyu)",  40, "#2e7d32", 50,  0),
    ("Blue Belt (2nd Kyu)",   50, "#1565c0", 65,  0),
    ("Brown Belt (1st Kyu)",  60, "#4e342e", 80,  0),
    ("Black Belt (1st Dan)",  70, "#212529", 100, 0),
]
for rname, seq, color, threshold, max_stripes in judo_rank_defs:
    ranks[f"judo_{rname}"] = env["dojo.belt.rank"].create({
        "name": rname, "sequence": seq, "color": color,
        "style_id": styles["judo"].id, "active": True,
        "attendance_threshold": threshold, "max_stripes": max_stripes,
        "is_dan": "Dan" in rname, "dan_level": 1 if "Dan" in rname else 0,
    })
    print(f"  Judo: {rname}")


# ═══════════════════════════════════════════════════════════════════════════
#  3. PROGRAMS
# ═══════════════════════════════════════════════════════════════════════════
print("\n3. Creating programs...")
prog_kids_bjj = env["dojo.program"].create({
    "name": "BJJ Kids", "code": "KIDS", "sequence": 10, "color": 3,
    "style_id": styles["bjj"].id,
    "description": "<p>Brazilian Jiu-Jitsu for children aged 5–16. "
                   "Discipline, self-defence and age-appropriate technique.</p>",
})
prog_adult_bjj = env["dojo.program"].create({
    "name": "BJJ Adults", "code": "BJJ", "sequence": 20, "color": 4,
    "style_id": styles["bjj"].id,
    "description": "<p>BJJ for adults 17+. Fundamentals through advanced competition prep.</p>",
})
prog_judo = env["dojo.program"].create({
    "name": "Judo", "code": "JUDO", "sequence": 30, "color": 5,
    "style_id": styles["judo"].id,
    "description": "<p>Traditional Judo program — throws, pins, and ne-waza.</p>",
})

# Assign belt paths
prog_kids_bjj.belt_rank_ids = [(6, 0, [
    ranks["bjj_White Belt"].id, ranks["bjj_Yellow Belt"].id,
    ranks["bjj_Orange Belt"].id, ranks["bjj_Green Belt"].id,
])]
prog_adult_bjj.belt_rank_ids = [(6, 0, [
    ranks[f"bjj_{n}"].id for n in
    ["White Belt", "Yellow Belt", "Orange Belt", "Green Belt",
     "Blue Belt", "Purple Belt", "Brown Belt", "Black Belt"]
])]
prog_judo.belt_rank_ids = [(6, 0, [
    ranks[f"judo_{n}"].id for n in
    ["White Belt (6th Kyu)", "Yellow Belt (5th Kyu)", "Orange Belt (4th Kyu)",
     "Green Belt (3rd Kyu)", "Blue Belt (2nd Kyu)", "Brown Belt (1st Kyu)",
     "Black Belt (1st Dan)"]
])]
print("  BJJ Kids, BJJ Adults, Judo")


# ═══════════════════════════════════════════════════════════════════════════
#  4. INSTRUCTORS
# ═══════════════════════════════════════════════════════════════════════════
print("\n4. Creating instructors...")
instr1_user = make_user("Alex Johnson",  "instructor1@demo.com", [group_instructor, group_user])
instr2_user = make_user("Sam Rivera",    "instructor2@demo.com", [group_instructor, group_user])
instr3_user = make_user("Kenji Tanaka",  "instructor3@demo.com", [group_instructor, group_user])
instr1 = env["dojo.instructor.profile"].create({
    "name": "Alex Johnson", "user_id": instr1_user.id,
    "partner_id": instr1_user.partner_id.id,
    "bio": "Head instructor with 15 years of BJJ experience. 3rd degree black belt.",
})
instr2 = env["dojo.instructor.profile"].create({
    "name": "Sam Rivera", "user_id": instr2_user.id,
    "partner_id": instr2_user.partner_id.id,
    "bio": "Assistant instructor specialising in advanced sparring and competition prep.",
})
instr3 = env["dojo.instructor.profile"].create({
    "name": "Kenji Tanaka", "user_id": instr3_user.id,
    "partner_id": instr3_user.partner_id.id,
    "bio": "Judo black belt (4th Dan). Former national competitor.",
})
print("  Alex Johnson, Sam Rivera, Kenji Tanaka")


# ═══════════════════════════════════════════════════════════════════════════
#  5. PARENTS (guardians)
# ═══════════════════════════════════════════════════════════════════════════
print("\n5. Creating parents...")
p1_user = make_user("Mary Smith", "parent1@demo.com", [group_parent_student])
p2_user = make_user("Bob Jones",  "parent2@demo.com", [group_parent_student])
p1_partner = p1_user.partner_id
p1_partner.write({"is_guardian": True, "phone": "555-0101", "street": "123 Oak Street", "city": "Springfield", "zip": "62701"})
p2_partner = p2_user.partner_id
p2_partner.write({"is_guardian": True, "phone": "555-0102", "street": "456 Elm Avenue", "city": "Springfield", "zip": "62702"})
print("  Mary Smith, Bob Jones")


# ═══════════════════════════════════════════════════════════════════════════
#  6. STUDENTS
# ═══════════════════════════════════════════════════════════════════════════
print("\n6. Creating students...")
students_raw = [
    # (name, login, dob, phone, is_minor, is_guardian, blood_type, allergies)
    ("Jordan Smith",   "student1@demo.com", date(2014,  3, 15), "555-0111", True,  False, "A+",  None),
    ("Casey Smith",    "student2@demo.com", date(2016,  7, 22), "555-0112", True,  False, "A+",  "Peanut allergy"),
    ("Taylor Jones",   "student3@demo.com", date(2013, 11,  5), "555-0113", True,  False, "B+",  None),
    ("Morgan Jones",   "student4@demo.com", date(2015,  4, 18), "555-0114", True,  False, "O+",  None),
    ("Riley Lee",      "student5@demo.com", date(2005,  8, 30), "555-0115", False, True,  "AB+", None),
    ("Hiro Watanabe",  "student6@demo.com", date(2000,  1, 12), "555-0116", False, True,  "O-",  None),
    ("Emma Davis",     "student7@demo.com", date(1998,  5, 20), "555-0117", False, True,  "B+",  "Latex allergy"),
]
student_members = []
for name, login, dob, phone, is_minor, is_guardian, blood_type, allergies in students_raw:
    u = make_user(name, login, [group_parent_student])
    vals = {
        "partner_id": u.partner_id.id,
        "date_of_birth": dob, "membership_state": "active",
        "phone": phone, "email": login,
        "blood_type": blood_type,
    }
    if allergies:
        vals["allergies"] = allergies
    m = env["dojo.member"].create(vals)
    u.partner_id.write({"is_minor": is_minor, "is_guardian": is_guardian})
    student_members.append(m)
    print(f"  {name}")
s1, s2, s3, s4, s5, s6, s7 = student_members


# ═══════════════════════════════════════════════════════════════════════════
#  7. EMERGENCY CONTACTS
# ═══════════════════════════════════════════════════════════════════════════
print("\n7. Creating emergency contacts...")
ec_defs = [
    (s1, "Mary Smith",   "mother",     "555-0101", "parent1@demo.com", True),
    (s1, "James Smith",  "father",     "555-0120", None,               False),
    (s2, "Mary Smith",   "mother",     "555-0101", "parent1@demo.com", True),
    (s3, "Bob Jones",    "father",     "555-0102", "parent2@demo.com", True),
    (s3, "Linda Jones",  "mother",     "555-0121", None,               False),
    (s4, "Bob Jones",    "father",     "555-0102", "parent2@demo.com", True),
    (s5, "Jamie Lee",    "sibling",    "555-0130", None,               True),
    (s6, "Yuki Watanabe","spouse",     "555-0131", None,               True),
    (s7, "Lisa Davis",   "mother",     "555-0132", None,               True),
]
for member, name, rel, phone, email, is_primary in ec_defs:
    env["dojo.emergency.contact"].create({
        "member_id": member.id, "name": name, "relationship": rel,
        "phone": phone, "email": email or False, "is_primary": is_primary,
    })
print(f"  {len(ec_defs)} emergency contacts created.")


# ═══════════════════════════════════════════════════════════════════════════
#  8. HOUSEHOLDS
# ═══════════════════════════════════════════════════════════════════════════
print("\n8. Creating households...")
smith_hh = env["res.partner"].create({
    "name": "Smith Household", "is_household": True, "is_company": True,
    "primary_guardian_id": p1_partner.id,
    "street": "123 Oak Street", "city": "Springfield", "zip": "62701",
})
for m in [s1, s2]:
    m.partner_id.parent_id = smith_hh
p1_partner.parent_id = smith_hh

jones_hh = env["res.partner"].create({
    "name": "Jones Household", "is_household": True, "is_company": True,
    "primary_guardian_id": p2_partner.id,
    "street": "456 Elm Avenue", "city": "Springfield", "zip": "62702",
})
for m in [s3, s4]:
    m.partner_id.parent_id = jones_hh
p2_partner.parent_id = jones_hh

lee_hh = env["res.partner"].create({
    "name": "Lee Household", "is_household": True, "is_company": True,
    "primary_guardian_id": s5.partner_id.id,
})
s5.partner_id.parent_id = lee_hh

watanabe_hh = env["res.partner"].create({
    "name": "Watanabe Household", "is_household": True, "is_company": True,
    "primary_guardian_id": s6.partner_id.id,
})
s6.partner_id.parent_id = watanabe_hh

davis_hh = env["res.partner"].create({
    "name": "Davis Household", "is_household": True, "is_company": True,
    "primary_guardian_id": s7.partner_id.id,
})
s7.partner_id.parent_id = davis_hh
print("  Smith, Jones, Lee, Watanabe, Davis households")


# ═══════════════════════════════════════════════════════════════════════════
#  9. BELT RANK HISTORY
# ═══════════════════════════════════════════════════════════════════════════
print("\n9. Assigning belt rank history...")
rank_awards = [
    # (member, rank_key, days_ago, instructor, program, stripe_count)
    (s1, "bjj_White Belt",  180, instr1, prog_kids_bjj, 2),
    (s2, "bjj_White Belt",  120, instr1, prog_kids_bjj, 1),
    (s3, "bjj_White Belt",  240, instr1, prog_kids_bjj, 4),
    (s3, "bjj_Yellow Belt",  90, instr1, prog_kids_bjj, 1),
    (s4, "bjj_White Belt",  150, instr1, prog_kids_bjj, 3),
    (s5, "bjj_White Belt",  365, instr2, prog_adult_bjj, 4),
    (s5, "bjj_Yellow Belt", 270, instr2, prog_adult_bjj, 4),
    (s5, "bjj_Orange Belt", 120, instr2, prog_adult_bjj, 2),
    (s5, "bjj_Green Belt",   30, instr2, prog_adult_bjj, 0),
    (s6, "judo_White Belt (6th Kyu)",  200, instr3, prog_judo, 0),
    (s6, "judo_Yellow Belt (5th Kyu)", 100, instr3, prog_judo, 0),
    (s7, "bjj_White Belt",  300, instr1, prog_adult_bjj, 4),
    (s7, "bjj_Yellow Belt", 180, instr1, prog_adult_bjj, 2),
    (s7, "judo_White Belt (6th Kyu)",  250, instr3, prog_judo, 0),
    (s7, "judo_Yellow Belt (5th Kyu)", 130, instr3, prog_judo, 0),
    (s7, "judo_Orange Belt (4th Kyu)",  40, instr3, prog_judo, 0),
]
for member, rank_key, days_ago, instructor, program, stripe_count in rank_awards:
    env["dojo.member.rank"].create({
        "member_id": member.id, "rank_id": ranks[rank_key].id,
        "date_awarded": today - timedelta(days=days_ago),
        "awarded_by": instructor.id,
        "program_id": program.id,
        "stripe_count": stripe_count,
    })
    print(f"  {member.name} → {ranks[rank_key].name} ({days_ago}d ago, {stripe_count} stripes)")


# ═══════════════════════════════════════════════════════════════════════════
# 10. CLASS TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════
print("\n10. Creating class templates...")
tmpl_little = env["dojo.class.template"].create({
    "name": "Little Champions", "code": "KIDS-BEG",
    "program_id": prog_kids_bjj.id, "level": "beginner",
    "duration_minutes": 60, "max_capacity": 12,
    "recurrence_active": True, "recurrence_time": 16.0,
    "rec_mon": True, "rec_wed": True,
    "recurrence_start_date": date(2026, 1, 12),
    "recurrence_instructor_id": instr1.id,
    "instructor_profile_ids": [(4, instr1.id)],
    "course_member_ids": [(6, 0, [s1.id, s2.id])],
    "description": "Foundational BJJ for younger kids (ages 5–10).",
})
tmpl_youth = env["dojo.class.template"].create({
    "name": "Youth Techniques", "code": "KIDS-INT",
    "program_id": prog_kids_bjj.id, "level": "intermediate",
    "duration_minutes": 75, "max_capacity": 12,
    "recurrence_active": True, "recurrence_time": 16.5,
    "rec_tue": True, "rec_thu": True,
    "recurrence_start_date": date(2026, 1, 12),
    "recurrence_instructor_id": instr1.id,
    "instructor_profile_ids": [(4, instr1.id)],
    "course_member_ids": [(6, 0, [s3.id, s4.id])],
    "description": "Intermediate BJJ for teens (ages 10–16). Sweeps, submissions and live drilling.",
})
tmpl_adult_fund = env["dojo.class.template"].create({
    "name": "Adult Fundamentals", "code": "ADV-BEG",
    "program_id": prog_adult_bjj.id, "level": "beginner",
    "duration_minutes": 60, "max_capacity": 15,
    "recurrence_active": True, "recurrence_time": 18.0,
    "rec_mon": True, "rec_wed": True, "rec_fri": True,
    "recurrence_start_date": date(2026, 1, 12),
    "recurrence_instructor_id": instr1.id,
    "instructor_profile_ids": [(4, instr1.id)],
    "course_member_ids": [(6, 0, [s5.id, s7.id])],
    "description": "Entry-level adult BJJ. Perfect for beginners.",
})
tmpl_adv = env["dojo.class.template"].create({
    "name": "Advanced Sparring", "code": "ADV-ADV",
    "program_id": prog_adult_bjj.id, "level": "advanced",
    "duration_minutes": 90, "max_capacity": 8,
    "recurrence_active": True, "recurrence_time": 19.5,
    "rec_tue": True, "rec_thu": True,
    "recurrence_start_date": date(2026, 1, 12),
    "recurrence_instructor_id": instr2.id,
    "instructor_profile_ids": [(4, instr2.id)],
    "course_member_ids": [(6, 0, [s5.id])],
    "description": "Competition-focused sparring and advanced technique.",
})
tmpl_judo = env["dojo.class.template"].create({
    "name": "Judo Fundamentals", "code": "JUDO-BEG",
    "program_id": prog_judo.id, "level": "beginner",
    "duration_minutes": 75, "max_capacity": 15,
    "recurrence_active": True, "recurrence_time": 18.0,
    "rec_tue": True, "rec_thu": True, "rec_sat": True,
    "recurrence_start_date": date(2026, 1, 12),
    "recurrence_instructor_id": instr3.id,
    "instructor_profile_ids": [(4, instr3.id)],
    "course_member_ids": [(6, 0, [s6.id, s7.id])],
    "description": "Traditional Judo — throws, pins, and ne-waza for all levels.",
})
tmpl_judo_adv = env["dojo.class.template"].create({
    "name": "Judo Randori", "code": "JUDO-ADV",
    "program_id": prog_judo.id, "level": "advanced",
    "duration_minutes": 90, "max_capacity": 10,
    "recurrence_active": True, "recurrence_time": 10.0,
    "rec_sat": True,
    "recurrence_start_date": date(2026, 1, 12),
    "recurrence_instructor_id": instr3.id,
    "instructor_profile_ids": [(4, instr3.id)],
    "course_member_ids": [(6, 0, [s6.id])],
    "description": "Free sparring and competition prep for advanced judoka.",
})
print("  Little Champions, Youth Techniques, Adult Fundamentals,")
print("  Advanced Sparring, Judo Fundamentals, Judo Randori")


# ═══════════════════════════════════════════════════════════════════════════
# 11. SUBSCRIPTION PLANS
# ═══════════════════════════════════════════════════════════════════════════
print("\n11. Creating subscription plans...")
currency = env.company.currency_id

plan_kids = env["dojo.subscription.plan"].create({
    "name": "Kids BJJ Monthly", "code": "KIDS-MTH",
    "plan_type": "program", "program_id": prog_kids_bjj.id,
    "billing_period": "monthly", "price": 80.00, "initial_fee": 50.00,
    "currency_id": currency.id,
    "description": "Unlimited BJJ Kids classes, up to 3 sessions per week.",
})
plan_adult = env["dojo.subscription.plan"].create({
    "name": "Adult BJJ Monthly", "code": "ADV-MTH",
    "plan_type": "program", "program_id": prog_adult_bjj.id,
    "billing_period": "monthly", "price": 120.00, "initial_fee": 50.00,
    "currency_id": currency.id,
    "credits_per_period": 12,
    "description": "12 credits/month. Access to all adult BJJ classes.",
})
plan_judo = env["dojo.subscription.plan"].create({
    "name": "Judo Monthly", "code": "JUDO-MTH",
    "plan_type": "program", "program_id": prog_judo.id,
    "billing_period": "monthly", "price": 100.00, "initial_fee": 40.00,
    "currency_id": currency.id,
    "credits_per_period": 10,
    "description": "10 credits/month. Judo classes.",
})
plan_private = env["dojo.subscription.plan"].create({
    "name": "Private Lessons", "code": "PRIV-MTH",
    "plan_type": "course", "billing_period": "monthly",
    "price": 250.00, "initial_fee": 0.00,
    "currency_id": currency.id, "credits_per_period": 4,
    "allowed_template_ids": [(4, tmpl_adv.id)],
    "description": "4 credits/month. Advanced Sparring sessions only.",
})
plan_unlimited = env["dojo.subscription.plan"].create({
    "name": "Unlimited All-Access", "code": "ALL-MTH",
    "plan_type": "course", "billing_period": "monthly",
    "price": 200.00, "initial_fee": 75.00,
    "currency_id": currency.id,
    "allowed_template_ids": [(6, 0, [
        tmpl_little.id, tmpl_youth.id, tmpl_adult_fund.id,
        tmpl_adv.id, tmpl_judo.id, tmpl_judo_adv.id,
    ])],
    "description": "Unlimited access to ALL programs — BJJ + Judo.",
})
print("  Kids BJJ ($80), Adult BJJ ($120), Judo ($100),")
print("  Private Lessons ($250), Unlimited All-Access ($200)")


# ═══════════════════════════════════════════════════════════════════════════
# 12. MEMBER SUBSCRIPTIONS
# ═══════════════════════════════════════════════════════════════════════════
print("\n12. Creating member subscriptions...")
sub_start = date(2026, 1, 12)
sub_next  = date(2026, 1, 12)

def make_sub(member, plan, note):
    pricelist = env["product.pricelist"].search([], limit=1)
    if not pricelist:
        pricelist = env["product.pricelist"].create({
            "name": "Default Pricelist",
            "currency_id": env.company.currency_id.id,
        })
    sub = env["sale.subscription"].create({
        "member_id": member.id, "plan_id": plan.id,
        "date_start": sub_start, "recurring_next_date": sub_next,
        "company_id": env.company.id, "note": note,
        "pricelist_id": pricelist.id,
    })
    sub.action_set_active()
    print(f"  {member.name} → {plan.name}")
    return sub

sub_s1 = make_sub(s1, plan_kids,  "Jordan Smith — Kids BJJ")
sub_s2 = make_sub(s2, plan_kids,  "Casey Smith — Kids BJJ")
sub_s3 = make_sub(s3, plan_kids,  "Taylor Jones — Kids BJJ")
sub_s4 = make_sub(s4, plan_kids,  "Morgan Jones — Kids BJJ")
sub_s5 = make_sub(s5, plan_adult, "Riley Lee — Adult BJJ")
sub_s6 = make_sub(s6, plan_judo,  "Hiro Watanabe — Judo")
sub_s7 = make_sub(s7, plan_unlimited, "Emma Davis — Unlimited All-Access (BJJ + Judo)")


# ═══════════════════════════════════════════════════════════════════════════
# 13. INVOICES (3 billing cycles)
# ═══════════════════════════════════════════════════════════════════════════
print("\n13. Seeding subscription invoices...")

# --- Ensure minimal chart of accounts and journals exist ---
Account = env["account.account"].sudo()
Journal = env["account.journal"].sudo()

def _ensure_account(account_type, name, code_store):
    acc = Account.search([("account_type", "=", account_type)], limit=1)
    if not acc:
        acc = Account.create({
            "name": name,
            "code_store": code_store,
            "account_type": account_type,
            "reconcile": account_type in ("asset_receivable", "liability_payable"),
        })
    return acc

_acc_recv = _ensure_account("asset_receivable", "Accounts Receivable", "1200")
_acc_pay = _ensure_account("liability_payable", "Accounts Payable", "2100")
_acc_income = _ensure_account("income", "Sales Income", "4000")
_acc_bank = _ensure_account("asset_current", "Bank Account", "1010")
_acc_cash = _ensure_account("asset_current", "Cash Account", "1020")
_acc_outstanding = _ensure_account("asset_current", "Outstanding Payments", "1050")

# Set default receivable/payable on company partner
env.company.partner_id.sudo().write({
    "property_account_receivable_id": _acc_recv.id,
    "property_account_payable_id": _acc_pay.id,
})
# Set transfer account for payments
if not env.company.transfer_account_id:
    env.company.sudo().transfer_account_id = _acc_outstanding

_sale_journal = Journal.search([("type", "=", "sale")], limit=1)
if not _sale_journal:
    _sale_journal = Journal.create({
        "name": "Customer Invoices",
        "type": "sale",
        "code": "INV",
        "company_id": env.company.id,
    })

print("  accounting setup: OK")

_membership_product = env.ref(
    "dojo_subscriptions.product_membership_subscription", raise_if_not_found=False
)


def _inv_lines(plan, period_start, include_fee=False):
    period_end = period_start + relativedelta(months=1) - relativedelta(days=1)
    date_range = "{} – {}".format(
        period_start.strftime("%-d %b %Y"), period_end.strftime("%-d %b %Y")
    )
    lines = []
    if include_fee and plan.initial_fee:
        fee = {
            "name": f"{plan.name} – Enrollment Fee",
            "quantity": 1.0,
            "price_unit": plan.initial_fee,
            "account_id": _acc_income.id,
        }
        if _membership_product:
            fee["product_id"] = _membership_product.id
        lines.append((0, 0, fee))
    rec = {
        "name": f"{plan.name} – Monthly Membership ({date_range})",
        "quantity": 1.0,
        "price_unit": plan.price,
        "account_id": _acc_income.id,
    }
    if _membership_product:
        rec["product_id"] = _membership_product.id
    lines.append((0, 0, rec))
    return lines


def _make_inv(partner, subs_list, line_vals, inv_date, paid=True):
    is_household = len(subs_list) > 1
    vals = {
        "move_type": "out_invoice",
        "partner_id": partner.id,
        "invoice_date": inv_date,
        "invoice_date_due": inv_date + relativedelta(days=7),
        "company_id": env.company.id,
        "invoice_line_ids": line_vals,
    }
    if is_household:
        vals["dojo_subscription_ids"] = [(6, 0, [s.id for s in subs_list])]
    else:
        vals["subscription_id"] = subs_list[0].id
    inv = env["account.move"].sudo().create(vals)
    inv.action_post()
    for sub in subs_list:
        sub.last_invoice_id = inv
    status = "posted"
    print(f"    {inv.name}  {inv_date}  {partner.name}  ${inv.amount_total:.2f}  [{status}]")
    return inv


_billing_cycles = [
    (date(2026, 1, 12), True),   # Jan
    (date(2026, 2, 12), True),   # Feb
    (date(2026, 3, 12), False),  # Mar — current
]

for _cycle_num, (_inv_date, _paid) in enumerate(_billing_cycles):
    _is_first = (_cycle_num == 0)

    # Smith Household: Mary Smith billed for Jordan + Casey
    _smith_lines = (
        _inv_lines(plan_kids, _inv_date, include_fee=_is_first)
        + _inv_lines(plan_kids, _inv_date, include_fee=False)
    )
    _make_inv(p1_partner, [sub_s1, sub_s2], _smith_lines, _inv_date, _paid)

    # Jones Household: Bob Jones billed for Taylor + Morgan
    _jones_lines = (
        _inv_lines(plan_kids, _inv_date, include_fee=_is_first)
        + _inv_lines(plan_kids, _inv_date, include_fee=False)
    )
    _make_inv(p2_partner, [sub_s3, sub_s4], _jones_lines, _inv_date, _paid)

    # Riley Lee: standalone Adult BJJ
    _riley_lines = _inv_lines(plan_adult, _inv_date, include_fee=_is_first)
    _make_inv(s5.partner_id, [sub_s5], _riley_lines, _inv_date, _paid)

    # Hiro Watanabe: standalone Judo
    _hiro_lines = _inv_lines(plan_judo, _inv_date, include_fee=_is_first)
    _make_inv(s6.partner_id, [sub_s6], _hiro_lines, _inv_date, _paid)

    # Emma Davis: standalone Unlimited
    _emma_lines = _inv_lines(plan_unlimited, _inv_date, include_fee=_is_first)
    _make_inv(s7.partner_id, [sub_s7], _emma_lines, _inv_date, _paid)

# Set next billing date to Apr 12
for _sub in [sub_s1, sub_s2, sub_s3, sub_s4, sub_s5, sub_s6, sub_s7]:
    _sub.recurring_next_date = date(2026, 4, 12)
print("  invoices done (next billing: Apr 12).")


# ═══════════════════════════════════════════════════════════════════════════
# 14. AUTO-ENROLL PREFERENCES
# ═══════════════════════════════════════════════════════════════════════════
print("\n14. Creating auto-enroll preferences...")
month_start = today.replace(day=1)
month_end   = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

auto_enroll_defs = [
    # (member, template, days_map)
    (s1, tmpl_little,    {"pref_mon": True, "pref_wed": True}),
    (s2, tmpl_little,    {"pref_mon": True, "pref_wed": True}),
    (s3, tmpl_youth,     {"pref_tue": True, "pref_thu": True}),
    (s4, tmpl_youth,     {"pref_tue": True, "pref_thu": True}),
    (s5, tmpl_adult_fund,{"pref_mon": True, "pref_wed": True}),
    (s5, tmpl_adv,       {"pref_tue": True, "pref_thu": True}),
    (s6, tmpl_judo,      {"pref_tue": True, "pref_thu": True, "pref_sat": True}),
    (s6, tmpl_judo_adv,  {"pref_sat": True}),
    (s7, tmpl_adult_fund,{"pref_mon": True, "pref_fri": True}),
    (s7, tmpl_judo,      {"pref_tue": True, "pref_thu": True}),
]
for member, template, prefs in auto_enroll_defs:
    vals = {
        "member_id": member.id, "template_id": template.id,
        "mode": "multiday", "date_from": month_start, "date_to": month_end,
    }
    vals.update(prefs)
    env["dojo.course.auto.enroll"].create(vals)
print(f"  {len(auto_enroll_defs)} auto-enroll preferences created.")


# ═══════════════════════════════════════════════════════════════════════════
# 15. CREDIT GRANTS (must come before enrollments which deduct credits)
# ═══════════════════════════════════════════════════════════════════════════
print("\n15. Granting credits...")
if "dojo.credit.transaction" in env:
    credit_subs = [
        (sub_s1, "Jordan Smith", plan_kids.credits_per_period if hasattr(plan_kids, "credits_per_period") else 0),
        (sub_s2, "Casey Smith", plan_kids.credits_per_period if hasattr(plan_kids, "credits_per_period") else 0),
        (sub_s3, "Taylor Jones", plan_kids.credits_per_period if hasattr(plan_kids, "credits_per_period") else 0),
        (sub_s4, "Morgan Jones", plan_kids.credits_per_period if hasattr(plan_kids, "credits_per_period") else 0),
        (sub_s5, "Riley Lee", plan_adult.credits_per_period if hasattr(plan_adult, "credits_per_period") else 0),
        (sub_s6, "Hiro Watanabe", plan_judo.credits_per_period if hasattr(plan_judo, "credits_per_period") else 0),
        (sub_s7, "Emma Davis", plan_unlimited.credits_per_period if hasattr(plan_unlimited, "credits_per_period") else 0),
    ]
    for sub, name, cpp in credit_subs:
        if not cpp:
            continue
        for cycle_date in [date(2026, 1, 12), date(2026, 2, 12), date(2026, 3, 12)]:
            env["dojo.credit.transaction"].create({
                "subscription_id": sub.id,
                "transaction_type": "grant",
                "amount": cpp,
                "status": "confirmed",
                "date": datetime(cycle_date.year, cycle_date.month, cycle_date.day, 0, 0),
                "note": f"Monthly grant — {name} ({cycle_date.strftime('%b %Y')})",
            })
        print(f"  {name}: 3 grants of {cpp}")
    print("  credit grants done.")
else:
    print("  (dojo.credit.transaction not available — skipped)")


# ═══════════════════════════════════════════════════════════════════════════
# 16. SESSIONS + ENROLLMENTS + ATTENDANCE
# ═══════════════════════════════════════════════════════════════════════════
print("\n16. Creating sessions, enrollments, and attendance logs...")

all_sessions = []  # track for later credit holds

def seed_sessions(template, instructor, hour, day_shift=0, enroll=None,
                  skip=None, minute=0):
    """Create 3 past (done) + 3 upcoming (open) sessions with attendance."""
    skip = skip or set()
    specs = [(-21, "done"), (-14, "done"), (-7, "done"),
             (  0, "open"), (  7, "open"), (14, "open")]
    created_sessions = []
    for idx, (offset, state) in enumerate(specs):
        day      = today + timedelta(days=offset + day_shift)
        start_dt = datetime(day.year, day.month, day.day, hour, minute)
        end_dt   = start_dt + timedelta(minutes=template.duration_minutes)
        session  = env["dojo.class.session"].create({
            "template_id": template.id,
            "instructor_profile_id": instructor.id,
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "capacity": template.max_capacity,
            "state": state,
        })
        created_sessions.append(session)
        if enroll and idx not in skip:
            att = "present" if state == "done" else "pending"
            for _m in enroll:
                enrollment = env["dojo.class.enrollment"].create({
                    "session_id": session.id,
                    "member_id": _m.id,
                    "status": "registered",
                    "attendance_state": att,
                })
                # Create attendance log for past sessions
                if state == "done" and att == "present":
                    checkin = start_dt + timedelta(minutes=(_m.id % 10))
                    checkout = end_dt - timedelta(minutes=5)
                    is_late = (_m.id % 7 == 0)  # occasional late arrival
                    env["dojo.attendance.log"].create({
                        "session_id": session.id,
                        "enrollment_id": enrollment.id,
                        "member_id": _m.id,
                        "status": "late" if is_late else "present",
                        "checkin_datetime": checkin,
                        "checkout_datetime": checkout,
                    })
    return created_sessions

# Little Champions @ 4 PM — Jordan & Casey (Mon/Wed)
sess_little = seed_sessions(tmpl_little, instr1, hour=16, day_shift=0,
              enroll=[s1, s2], skip={1, 5})
print("  Little Champions: 6 sessions (skip idx 1,5)")

# Youth Techniques @ 4:30 PM — Taylor & Morgan (Tue/Thu)
sess_youth = seed_sessions(tmpl_youth, instr1, hour=16, minute=30, day_shift=1,
              enroll=[s3, s4], skip={2, 4})
print("  Youth Techniques: 6 sessions (skip idx 2,4)")

# Adult Fundamentals @ 6 PM — Riley + Emma (Mon/Wed/Fri)
sess_adult = seed_sessions(tmpl_adult_fund, instr1, hour=18, day_shift=0,
              enroll=[s5, s7], skip={0, 5})
print("  Adult Fundamentals: 6 sessions (skip idx 0,5)")

# Advanced Sparring @ 7:30 PM — Riley (Tue/Thu)
sess_adv = seed_sessions(tmpl_adv, instr2, hour=19, minute=30, day_shift=2,
              enroll=[s5], skip={1, 4, 5})
print("  Advanced Sparring: 6 sessions (skip idx 1,4,5)")

# Judo Fundamentals @ 6 PM — Hiro + Emma (Tue/Thu/Sat)
sess_judo = seed_sessions(tmpl_judo, instr3, hour=18, day_shift=1,
              enroll=[s6, s7], skip={2, 5})
print("  Judo Fundamentals: 6 sessions (skip idx 2,5)")

# Judo Randori @ 10 AM Sat — Hiro
sess_judo_adv = seed_sessions(tmpl_judo_adv, instr3, hour=10, day_shift=5,
              enroll=[s6], skip={0, 4, 5})
print("  Judo Randori: 6 sessions (skip idx 0,4,5)")

all_sessions = sess_little + sess_youth + sess_adult + sess_adv + sess_judo + sess_judo_adv


# ═══════════════════════════════════════════════════════════════════════════
# 17. CREDIT EXPIRY TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════════════
print("\n17. Credit expiry transactions...")
if "dojo.credit.transaction" in env:
    expiry_subs = [
        (sub_s5, "Riley Lee", 12),
        (sub_s6, "Hiro Watanabe", 10),
    ]
    for sub, name, credits_per_period in expiry_subs:
        used_jan = min(credits_per_period, 5)
        leftover_jan = credits_per_period - used_jan
        if leftover_jan > 0:
            env["dojo.credit.transaction"].create({
                "subscription_id": sub.id,
                "transaction_type": "expiry",
                "amount": -leftover_jan,
                "status": "confirmed",
                "date": datetime(2026, 2, 12, 0, 0),
                "note": f"Expired unused Jan credits — {name}",
            })
        print(f"  {name}: Jan expiry ({leftover_jan})")


# ═══════════════════════════════════════════════════════════════════════════
# 18. POINTS TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════════════
print("\n18. Creating points transactions...")
if "dojo.points.transaction" in env:
    # Award attendance points for past sessions (logged attendance)
    past_logs = env["dojo.attendance.log"].search([
        ("status", "in", ["present", "late"])
    ])
    for log in past_logs:
        pts = 5 if log.status == "late" else 10
        source = "late_attendance" if log.status == "late" else "attendance"
        env["dojo.points.transaction"].create({
            "member_id": log.member_id.id,
            "source_type": source,
            "amount": pts,
            "date": log.checkin_datetime,
            "note": f"{'Late a' if log.status == 'late' else 'A'}ttendance: {log.session_id.display_name or 'Session'}",
            "attendance_log_id": log.id,
        })
    print(f"  {len(past_logs)} attendance point transactions")

    # Streak bonuses for Riley (most consistent attendee)
    env["dojo.points.transaction"].create({
        "member_id": s5.id, "source_type": "streak_bonus",
        "amount": 15, "date": now - timedelta(days=10),
        "note": "3-class streak bonus!", "streak_length": 3,
    })
    env["dojo.points.transaction"].create({
        "member_id": s7.id, "source_type": "streak_bonus",
        "amount": 15, "date": now - timedelta(days=8),
        "note": "3-class streak bonus!", "streak_length": 3,
    })
    print("  2 streak bonuses (Riley, Emma)")

    # Belt promotion bonus for Riley (Green Belt recent promotion)
    env["dojo.points.transaction"].create({
        "member_id": s5.id, "source_type": "belt_promotion",
        "amount": 100, "date": now - timedelta(days=30),
        "note": "Belt promotion: Green Belt",
    })
    # Belt promotion bonus for Emma (Yellow Belt BJJ)
    env["dojo.points.transaction"].create({
        "member_id": s7.id, "source_type": "belt_promotion",
        "amount": 100, "date": now - timedelta(days=40),
        "note": "Belt promotion: Orange Belt (4th Kyu) — Judo",
    })
    print("  2 belt promotion bonuses")


# ═══════════════════════════════════════════════════════════════════════════
# 19. BELT TESTS
# ═══════════════════════════════════════════════════════════════════════════
print("\n19. Creating belt tests...")

# Past belt test (completed)
test_past = env["dojo.belt.test"].create({
    "name": "Spring Belt Test — BJJ Kids",
    "test_date": today - timedelta(days=60),
    "location": "Main Dojo",
    "instructor_profile_id": instr1.id,
    "program_id": prog_kids_bjj.id,
    "state": "completed",
    "notes": "Spring promotion test for kids BJJ students.",
})
# Registration: Taylor passed to Yellow Belt
env["dojo.belt.test.registration"].create({
    "test_id": test_past.id, "member_id": s3.id,
    "target_rank_id": ranks["bjj_Yellow Belt"].id,
    "result": "pass",
    "notes": "Excellent technique and sportsmanship.",
})
print("  Past test: Spring Belt Test (Taylor → Yellow Belt)")

# Past belt test — Judo
test_judo_past = env["dojo.belt.test"].create({
    "name": "Winter Judo Grading",
    "test_date": today - timedelta(days=40),
    "location": "Main Dojo",
    "instructor_profile_id": instr3.id,
    "program_id": prog_judo.id,
    "state": "completed",
    "notes": "Judo winter grading for belt promotions.",
})
env["dojo.belt.test.registration"].create({
    "test_id": test_judo_past.id, "member_id": s7.id,
    "target_rank_id": ranks["judo_Orange Belt (4th Kyu)"].id,
    "result": "pass",
    "notes": "Clean ippon throws, excellent ground transitions.",
})
print("  Past test: Winter Judo Grading (Emma → Orange Belt)")

# Upcoming belt test
test_upcoming = env["dojo.belt.test"].create({
    "name": "Summer Belt Test — BJJ Adults",
    "test_date": today + timedelta(days=30),
    "location": "Main Dojo",
    "instructor_profile_id": instr2.id,
    "program_id": prog_adult_bjj.id,
    "state": "scheduled",
    "max_participants": 10,
    "notes": "Adult BJJ belt testing for summer promotions.",
})
# Pre-registrations
env["dojo.belt.test.registration"].create({
    "test_id": test_upcoming.id, "member_id": s5.id,
    "target_rank_id": ranks["bjj_Blue Belt"].id,
    "result": "pending",
    "notes": "Riley has been training consistently — ready for Blue Belt test.",
})
env["dojo.belt.test.registration"].create({
    "test_id": test_upcoming.id, "member_id": s7.id,
    "target_rank_id": ranks["bjj_Orange Belt"].id,
    "result": "pending",
    "notes": "Emma shows strong fundamentals — testing for Orange Belt.",
})
print("  Upcoming test: Summer Belt Test (Riley → Blue, Emma → Orange)")


# ═══════════════════════════════════════════════════════════════════════════
# 20. PROGRAM ENROLLMENTS
# ═══════════════════════════════════════════════════════════════════════════
print("\n20. Creating program enrollments...")
if "dojo.program.enrollment" in env:
    pe_defs = [
        (s1, prog_kids_bjj,  sub_s1),
        (s2, prog_kids_bjj,  sub_s2),
        (s3, prog_kids_bjj,  sub_s3),
        (s4, prog_kids_bjj,  sub_s4),
        (s5, prog_adult_bjj, sub_s5),
        (s6, prog_judo,      sub_s6),
        (s7, prog_adult_bjj, sub_s7),
        (s7, prog_judo,      sub_s7),  # Emma is in both programs
    ]
    for member, program, sub in pe_defs:
        env["dojo.program.enrollment"].create({
            "member_id": member.id,
            "program_id": program.id,
            "subscription_id": sub.id,
            "enrolled_date": sub_start,
            "is_active": True,
        })
    print(f"  {len(pe_defs)} program enrollments (Emma in BJJ + Judo)")


# ═══════════════════════════════════════════════════════════════════════════
# 21. KIOSK CONFIG
# ═══════════════════════════════════════════════════════════════════════════
print("\n21. Setting up kiosk config...")
if "dojo.kiosk.config" in env:
    kiosk = env["dojo.kiosk.config"].create({
        "name": "Demo Kiosk",
        "pin_code": "123456",
        "active": True,
        "theme_mode": "dark",
        "view_mode": "both",
        "show_title": True,
    })
    # Kiosk announcements
    if "dojo.kiosk.announcement" in env:
        env["dojo.kiosk.announcement"].create({
            "config_id": kiosk.id,
            "title": "Welcome Back!",
            "body": "<p>Great to see you! Remember to warm up before class.</p>",
            "sequence": 10, "active": True,
        })
        env["dojo.kiosk.announcement"].create({
            "config_id": kiosk.id,
            "title": "Belt Test Coming Up",
            "body": "<p>Summer belt test registrations are now open. Talk to your instructor!</p>",
            "sequence": 20, "active": True,
        })
    print("  Demo Kiosk with 2 announcements")
else:
    print("  (dojo.kiosk.config not installed — skipping)")


# ═══════════════════════════════════════════════════════════════════════════
# 22. WAIVER CONFIG
# ═══════════════════════════════════════════════════════════════════════════
print("\n22. Setting up waiver config...")
if "dojo.waiver.config" in env:
    env["dojo.waiver.config"].create({
        "name": "Demo Waiver",
        "content_html": """<h2>Liability Waiver & Release</h2>
<p>I understand that martial arts training involves physical contact and
inherent risks of injury. I voluntarily assume all risks associated with
my participation in classes, training, and events at this dojo.</p>
<p>I release the dojo, its instructors, and staff from any liability for
injuries sustained during training.</p>
<p><strong>By signing below, I confirm that I have read and understood this waiver.</strong></p>""",
    })
    print("  Demo waiver created")
else:
    print("  (dojo.waiver.config not installed — skipping)")


# ═══════════════════════════════════════════════════════════════════════════
# 23. CHECKOUT CONFIG
# ═══════════════════════════════════════════════════════════════════════════
print("\n23. Setting up checkout config...")
if "dojo.checkout.config" in env:
    env["dojo.checkout.config"].create({
        "plan_id": plan_kids.id,
        "cta_label": "Enroll Your Child Today!",
        "banner_text": "Join our Kids BJJ program — first month FREE!",
        "featured": True,
        "thank_you_html": "<h2>Welcome to the Dojo!</h2><p>Your child is now enrolled. See you on the mat!</p>",
    })
    env["dojo.checkout.config"].create({
        "plan_id": plan_adult.id,
        "cta_label": "Start Training Today",
        "banner_text": "Adult BJJ — Build confidence, strength, and skill.",
        "featured": True,
        "thank_you_html": "<h2>You're In!</h2><p>Welcome to the team. Your journey starts now.</p>",
    })
    env["dojo.checkout.config"].create({
        "plan_id": plan_judo.id,
        "cta_label": "Try Judo Today",
        "banner_text": "Traditional Judo — train with Sensei Tanaka.",
        "featured": False,
        "thank_you_html": "<h2>Welcome!</h2><p>See you on the mat for your first Judo class.</p>",
    })
    # Upsell item
    if "dojo.checkout.upsell" in env:
        upsell_gi = env["dojo.checkout.upsell"].create({
            "name": "Dojo Gi (Uniform)",
            "type": "uniform",
            "description": "Official dojo gi in white. All sizes available.",
            "price": 65.00,
            "currency_id": currency.id,
            "sequence": 10, "active": True,
        })
        upsell_bag = env["dojo.checkout.upsell"].create({
            "name": "Dojo Gear Bag",
            "type": "merch",
            "description": "Durable gear bag with dojo logo.",
            "price": 35.00,
            "currency_id": currency.id,
            "sequence": 20, "active": True,
        })
    print("  3 checkout configs + 2 upsell items")
else:
    print("  (dojo.checkout.config not installed — skipping)")


# ═══════════════════════════════════════════════════════════════════════════
# 24. MARKETING CARDS
# ═══════════════════════════════════════════════════════════════════════════
print("\n24. Setting up marketing cards...")
if "dojo.marketing.card" in env:
    env["dojo.marketing.card"].create({
        "name": "Support the Dojo",
        "card_type": "donate",
        "subtitle": "Help Us Grow!",
        "body": "Your donation supports scholarships and facility upgrades.",
        "active": True, "publish_kiosk": True, "publish_portal": True,
        "sequence": 10,
        "custom_url": "https://example.com/donate",
    })
    env["dojo.marketing.card"].create({
        "name": "Dojo Merch Store",
        "card_type": "merch",
        "subtitle": "Gear Up!",
        "body": "Browse our collection of gis, rash guards, and accessories.",
        "active": True, "publish_kiosk": False, "publish_portal": True,
        "sequence": 20,
        "custom_url": "https://example.com/shop",
    })
    print("  2 marketing cards")
else:
    print("  (dojo.marketing.card not installed — skipping)")


# ═══════════════════════════════════════════════════════════════════════════
# 25. RECOMPUTE + COMMIT
# ═══════════════════════════════════════════════════════════════════════════
print("\n25. Recomputing stored fields...")
all_members = env["dojo.member"].search([])
all_members._compute_has_portal_login()
all_members.flush_recordset(["has_portal_login"])

env.cr.commit()

print("""
═══════════════════════════════════════════════════════════════════════════
 DONE! All demo data created.
═══════════════════════════════════════════════════════════════════════════

Logins (password: dojo@2026)
  instructor1@demo.com  Alex Johnson     (Head Instructor, BJJ)
  instructor2@demo.com  Sam Rivera       (Asst. Instructor, BJJ)
  instructor3@demo.com  Kenji Tanaka     (Judo Instructor)
  parent1@demo.com      Mary Smith       (Smith Household)
  parent2@demo.com      Bob Jones        (Jones Household)
  student1@demo.com     Jordan Smith     (Kids BJJ, Smith HH)
  student2@demo.com     Casey Smith      (Kids BJJ, Smith HH)
  student3@demo.com     Taylor Jones     (Kids BJJ, Jones HH)
  student4@demo.com     Morgan Jones     (Kids BJJ, Jones HH)
  student5@demo.com     Riley Lee        (Adult BJJ, standalone)
  student6@demo.com     Hiro Watanabe    (Judo, standalone)
  student7@demo.com     Emma Davis       (BJJ + Judo, standalone)

Martial Art Styles
  Brazilian Jiu-Jitsu (bjj), Judo (judo), Muay Thai (mt)

Programs
  BJJ Kids   (bjj)  — belt path: White → Yellow → Orange → Green
  BJJ Adults (bjj)  — belt path: White → Yellow → Orange → Green → Blue → Purple → Brown → Black
  Judo       (judo) — belt path: 6th Kyu (White) → 5th → 4th → 3rd → 2nd → 1st Kyu → 1st Dan

Class Templates + Auto-Enroll
  Little Champions   (BJJ Kids,   beginner)     Jordan & Casey     Mon/Wed  @ 4:00 PM
  Youth Techniques   (BJJ Kids,   intermediate) Taylor & Morgan    Tue/Thu  @ 4:30 PM
  Adult Fundamentals (BJJ Adults, beginner)     Riley & Emma       Mon/Wed/Fri @ 6:00 PM
  Advanced Sparring  (BJJ Adults, advanced)     Riley              Tue/Thu  @ 7:30 PM
  Judo Fundamentals  (Judo,       beginner)     Hiro & Emma        Tue/Thu/Sat @ 6:00 PM
  Judo Randori       (Judo,       advanced)     Hiro               Sat      @ 10:00 AM

Subscription Plans
  Kids BJJ Monthly     $80/mo  + $50 setup  | program-based, ≤3/week
  Adult BJJ Monthly    $120/mo + $50 setup  | program-based, 12 credits, ≤5/week
  Judo Monthly         $100/mo + $40 setup  | program-based, 10 credits, ≤4/week
  Private Lessons      $250/mo, no setup    | course-based,  4 credits, ≤1/week
  Unlimited All-Access $200/mo + $75 setup  | unlimited, ≤7/week

Invoices (subscriptions started Jan 12, 2026)
  Smith HH (Mary)  — Jan: $210 paid, Feb: $160 paid, Mar: $160 open
  Jones HH (Bob)   — Jan: $210 paid, Feb: $160 paid, Mar: $160 open
  Riley Lee        — Jan: $170 paid, Feb: $120 paid, Mar: $120 open
  Hiro Watanabe    — Jan: $140 paid, Feb: $100 paid, Mar: $100 open
  Emma Davis       — Jan: $275 paid, Feb: $200 paid, Mar: $200 open
  Next billing: Apr 12, 2026

Sessions: 6 per template × 6 templates = 36 sessions (18 past + 18 upcoming)
Attendance logs seeded for all past sessions with realistic patterns.
Credit transactions: monthly grants + Jan expiry for credit-based plans.
Points: attendance points + streak bonuses + belt promotion bonuses.

Belt Tests
  Past: Spring BJJ Kids Test (Taylor → Yellow Belt, passed)
  Past: Winter Judo Grading (Emma → Orange 4th Kyu, passed)
  Upcoming: Summer BJJ Adults Test (Riley → Blue, Emma → Orange, pending)

Emergency Contacts: 9 total across all members
Program Enrollments: 8 (Emma in both BJJ + Judo)
Kiosk: Demo Kiosk with 2 announcements
Checkout: 3 configs + 2 upsell items
Waiver: Demo waiver template
Marketing: 2 cards (welcome + referral)
""")

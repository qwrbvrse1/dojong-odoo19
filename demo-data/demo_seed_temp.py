"""
Temporary demo seed — 2 students + 1 parent, all under "All Belts" program.

Run (production):
  sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/python3 /opt/odoo19/odoo19/odoo-bin \
    --config /etc/odoo19.conf -d prod2 --no-http \
    shell < /opt/odoo19/odoo19/custom-addons/demo-data/demo_seed_temp.py

Accounts created (password: dojo@2026):
  demo1@demo.com        Demo Student 1   — enrolled in All Belts course roster
  demo2@demo.com        Demo Student 2   — enrolled in All Belts course roster
  DemoParent@demo.com   Demo Parent      — guardian of both students
  Household             Demo Temp Household
"""

from datetime import date

PASSWORD = "dojo@2026"

DEMO_LOGINS = [
    "demo1@demo.com",
    "demo2@demo.com",
    "DemoParent@demo.com",
]

# ── Cleanup: remove any prior run of this seed ───────────────────────────
print("Cleaning up prior temp demo data...")

existing_users = env["res.users"].search([("login", "in", DEMO_LOGINS)])
if existing_users:
    existing_partners = existing_users.mapped("partner_id")
    demo_members = env["dojo.member"].search([
        ("partner_id", "in", existing_partners.ids)
    ])
    # Remove from course rosters first
    if demo_members:
        templates = env["dojo.class.template"].search([
            ("course_member_ids", "in", demo_members.ids)
        ])
        for tmpl in templates:
            tmpl.course_member_ids = [(3, m.id) for m in demo_members if m in tmpl.course_member_ids]
        demo_members.unlink()
    existing_users.unlink()

demo_hh_existing = env["res.partner"].search([
    ("name", "=", "Demo Temp Household"), ("is_household", "=", True)
])
if demo_hh_existing:
    demo_hh_existing.unlink()

print("  cleanup done.")

# ── Group references ─────────────────────────────────────────────────────
# Use base portal group (dojo_base.group_dojo_parent_student not in this prod instance)
group_parent_student = env.ref("base.group_portal")


def make_user(name, login, groups):
    u = env["res.users"].create({
        "name": name,
        "login": login,
        "email": login,
        "group_ids": [(6, 0, [g.id for g in groups])],
    })
    u.password = PASSWORD
    return u


# ── 1. Demo Parent ───────────────────────────────────────────────────────
print("Creating Demo Parent...")
parent_user = make_user("Demo Parent", "DemoParent@demo.com", [group_parent_student])
parent_partner = parent_user.partner_id
parent_partner.write({
    "is_guardian": True,
    "phone": "555-0300",
})

# ── 2. Demo Students ─────────────────────────────────────────────────────
print("Creating Demo Students...")

# ── Fix sequence: advance past any existing member_number to avoid collision ─
import re as _re
_existing_members = env["dojo.member"].search([
    ("member_number", "!=", False)
], order="id desc", limit=1)
if _existing_members:
    _last_num_match = _re.search(r"(\d+)$", _existing_members[0].member_number or "")
    if _last_num_match:
        _last_num = int(_last_num_match.group(1))
        _seq = env["ir.sequence"].search([("code", "=", "dojo.member")], limit=1)
        if _seq and _seq.number_next_actual <= _last_num:
            _seq.write({"number_next_actual": _last_num + 1})
            print(f"  Advanced dojo.member sequence to {_last_num + 1}")

students_raw = [
    ("Demo Student 1", "demo1@demo.com", date(2015, 6, 15), "555-0301"),
    ("Demo Student 2", "demo2@demo.com", date(2017, 9, 20), "555-0302"),
]

student_members = []
for name, login, dob, phone in students_raw:
    u = make_user(name, login, [group_parent_student])
    m = env["dojo.member"].create({
        "partner_id": u.partner_id.id,
        "date_of_birth": dob,
        "membership_state": "active",
        "phone": phone,
        "email": login,
    })
    u.partner_id.write({
        "is_minor": True,
        "is_guardian": False,
        "phone": phone,
    })
    print(f"  Created {name} ({login})")
    student_members.append((u, m))

(s1_user, s1), (s2_user, s2) = student_members

# ── 3. Demo Household ────────────────────────────────────────────────────
print("Creating Demo Temp Household...")
demo_hh = env["res.partner"].create({
    "name": "Demo Temp Household",
    "is_household": True,
    "is_company": True,
    "primary_guardian_id": parent_partner.id,
    "phone": "555-0300",
})

for partner in [s1.partner_id, s2.partner_id, parent_partner]:
    partner.parent_id = demo_hh

# ── 4. Enroll students in All Belts course rosters ──────────────────────
print("Assigning students to All Belts course roster...")
all_belts_program = env["dojo.program"].search([("name", "ilike", "All Belts")], limit=1)
if not all_belts_program:
    all_belts_program = env["dojo.program"].search([("name", "ilike", "All Belt")], limit=1)

if all_belts_program:
    templates = env["dojo.class.template"].search([
        ("program_id", "=", all_belts_program.id)
    ])
    print(f"  Found program: {all_belts_program.name} (id={all_belts_program.id})")
    print(f"  Found {len(templates)} course template(s) for that program")
    for tmpl in templates:
        tmpl.write({
            "course_member_ids": [(4, s1.id), (4, s2.id)]
        })
        print(f"    Added both students to template: {tmpl.name}")
else:
    print("  WARNING: 'All Belts' program not found — skipping roster assignment")
    print("  Available programs:", env["dojo.program"].search([]).mapped("name"))

env.cr.commit()

print("\n=== Temp Demo Seed Complete ===")
print(f"  Demo Student 1  : demo1@demo.com        /  {PASSWORD}  (All Belts roster)")
print(f"  Demo Student 2  : demo2@demo.com        /  {PASSWORD}  (All Belts roster)")
print(f"  Demo Parent     : DemoParent@demo.com   /  {PASSWORD}  (guardian)")
print(f"  Household       : Demo Temp Household")

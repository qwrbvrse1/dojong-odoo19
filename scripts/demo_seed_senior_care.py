from datetime import datetime, time, timedelta

from odoo import fields


company = env.company
today = fields.Date.today()


def upsert_user(login, name):
    user = env["res.users"].sudo().search([("login", "=", login)], limit=1)
    if not user:
        user = env["res.users"].with_context(no_reset_password=True).sudo().create({
            "name": name,
            "login": login,
            "email": login,
            "group_ids": [(6, 0, [env.ref("base.group_user").id])],
            "company_id": company.id,
            "company_ids": [(6, 0, [company.id])],
        })
    return user


def upsert_instructor(login, name, bio):
    user = upsert_user(login, name)
    profile = env["dojo.instructor.profile"].sudo().search(
        [("user_id", "=", user.id)], limit=1
    )
    vals = {
        "name": name,
        "user_id": user.id,
        "partner_id": user.partner_id.id,
        "company_id": company.id,
        "bio": bio,
    }
    if profile:
        profile.write(vals)
    else:
        profile = env["dojo.instructor.profile"].sudo().create(vals)
    return profile


def upsert_tag(name):
    tag = env["res.partner.category"].sudo().search([("name", "=", name)], limit=1)
    if not tag:
        tag = env["res.partner.category"].sudo().create({"name": name})
    return tag


def upsert_program(code, name, manager, description):
    program = env["dojo.program"].sudo().search([("code", "=", code)], limit=1)
    vals = {
        "name": name,
        "code": code,
        "company_id": company.id,
        "manager_instructor_id": manager.id,
        "description": description,
        "active": True,
    }
    if program:
        program.write(vals)
    else:
        program = env["dojo.program"].sudo().create(vals)
    return program


def upsert_template(code, name, program, instructors, description, capacity):
    template = env["dojo.class.template"].sudo().search([("code", "=", code)], limit=1)
    vals = {
        "name": name,
        "code": code,
        "program_id": program.id,
        "company_id": company.id,
        "level": "all",
        "duration_minutes": 60,
        "max_capacity": capacity,
        "description": description,
        "active": True,
        "instructor_profile_ids": [(6, 0, instructors.ids)],
    }
    if template:
        template.write(vals)
    else:
        template = env["dojo.class.template"].sudo().create(vals)
    return template


def upsert_member(spec, tags):
    member = env["dojo.member"].sudo().search([("email", "=", spec["email"])], limit=1)
    vals = {
        "name": spec["name"],
        "email": spec["email"],
        "phone": spec["phone"],
        "company_id": company.id,
        "membership_state": spec["membership_state"],
        "date_of_birth": spec["date_of_birth"],
        "allergies": spec["allergies"],
        "medical_notes": spec["medical_notes"],
        "emergency_note": spec["emergency_note"],
    }
    if member:
        member.write(vals)
    else:
        member = env["dojo.member"].sudo().create(vals)
    member.partner_id.category_id = [(6, 0, [tag.id for tag in tags])]
    return member


def upsert_emergency_contact(member, name, relationship, phone, email, note, is_primary=True):
    contact = env["dojo.emergency.contact"].sudo().search(
        [("member_id", "=", member.id), ("name", "=", name)], limit=1
    )
    vals = {
        "member_id": member.id,
        "name": name,
        "relationship": relationship,
        "phone": phone,
        "email": email,
        "note": note,
        "is_primary": is_primary,
    }
    if contact:
        contact.write(vals)
    else:
        contact = env["dojo.emergency.contact"].sudo().create(vals)
    return contact


def make_dt(day_offset, hour, minute=0):
    target = today + timedelta(days=day_offset)
    return datetime.combine(target, time(hour=hour, minute=minute))


def upsert_session(template, instructor, start_dt, end_dt, capacity, state):
    session = env["dojo.class.session"].sudo().search(
        [("template_id", "=", template.id), ("start_datetime", "=", start_dt)],
        limit=1,
    )
    vals = {
        "template_id": template.id,
        "company_id": company.id,
        "instructor_profile_id": instructor.id,
        "start_datetime": start_dt,
        "end_datetime": end_dt,
        "capacity": capacity,
        "state": state,
    }
    if session:
        session.write(vals)
    else:
        session = env["dojo.class.session"].sudo().create(vals)
    return session


def upsert_enrollment(session, member, status, attendance_state):
    enrollment = env["dojo.class.enrollment"].sudo().search(
        [("session_id", "=", session.id), ("member_id", "=", member.id)], limit=1
    )
    vals = {
        "session_id": session.id,
        "member_id": member.id,
        "status": status,
        "attendance_state": attendance_state,
    }
    if enrollment:
        enrollment.with_context(
            skip_capacity_check=True,
            skip_course_membership_check=True,
        ).write(vals)
    else:
        enrollment = env["dojo.class.enrollment"].sudo().with_context(
            skip_capacity_check=True,
            skip_course_membership_check=True,
        ).create(vals)
    return enrollment


def upsert_attendance_log(session, enrollment, member, status, note, minutes_after_start=5):
    if enrollment.status != "registered":
        return
    checkin = session.start_datetime + timedelta(minutes=minutes_after_start)
    checkout = session.end_datetime
    log = env["dojo.attendance.log"].sudo().search(
        [("session_id", "=", session.id), ("member_id", "=", member.id)], limit=1
    )
    vals = {
        "session_id": session.id,
        "enrollment_id": enrollment.id,
        "member_id": member.id,
        "status": status,
        "checkin_datetime": checkin,
        "checkout_datetime": checkout,
        "note": note,
    }
    if log:
        log.write(vals)
    else:
        log = env["dojo.attendance.log"].sudo().create(vals)
    return log


lead_staff = upsert_instructor(
    "maria.chen.demo@example.com",
    "Maria Chen, RN",
    "Clinical operations lead for medication rounds and high-risk follow-up.",
)
support_staff = upsert_instructor(
    "daniel.brooks.demo@example.com",
    "Daniel Brooks",
    "Mobility coordinator covering recovery rounds and family escalations.",
)

tag_falls = upsert_tag("Falls Monitoring")
tag_medication = upsert_tag("Medication Follow-Up")
tag_family = upsert_tag("Family Update Priority")

wellness_program = upsert_program(
    "SC-WELL",
    "Resident Wellness",
    lead_staff,
    "<p>Daily wellness oversight, medication adherence, and continuity check-ins.</p>",
)
recovery_program = upsert_program(
    "SC-REC",
    "Recovery and Mobility",
    support_staff,
    "<p>Post-incident mobility recovery and follow-up coordination.</p>",
)

med_round = upsert_template(
    "SC-MED-AM",
    "North Wing Medication Round",
    wellness_program,
    lead_staff | support_staff,
    "Morning medication reconciliation and resident status review for North Wing.",
    6,
)
mobility_round = upsert_template(
    "SC-MOB-PM",
    "Garden Suite Mobility Recovery",
    recovery_program,
    support_staff,
    "Mobility and recovery round for residents needing follow-up after incidents.",
    4,
)
family_round = upsert_template(
    "SC-FAM-FU",
    "Family Continuity Follow-Up",
    wellness_program,
    lead_staff,
    "Scheduled follow-up touchpoints for family communication after care changes.",
    4,
)

member_specs = [
    {
        "name": "Evelyn Parker",
        "email": "evelyn.parker.demo@example.com",
        "phone": "555-0101",
        "membership_state": "active",
        "date_of_birth": "1940-04-12",
        "allergies": "Penicillin",
        "medical_notes": "Room 214. Daily medication support and hydration reminder.",
        "emergency_note": "Primary daughter prefers SMS before 5 PM, then phone call.",
        "tags": [tag_medication, tag_family],
        "contact": {
            "name": "Monica Parker",
            "relationship": "Daughter",
            "phone": "555-1101",
            "email": "monica.parker@example.com",
            "note": "Lives locally and joins care updates after medication changes.",
        },
    },
    {
        "name": "Walter Scott",
        "email": "walter.scott.demo@example.com",
        "phone": "555-0102",
        "membership_state": "paused",
        "date_of_birth": "1938-09-03",
        "allergies": "None reported",
        "medical_notes": "Room 118. Post-fall mobility monitoring and gait reassessment.",
        "emergency_note": "Family expects update if mobility session is missed.",
        "tags": [tag_falls, tag_family],
        "contact": {
            "name": "Nina Scott",
            "relationship": "Daughter",
            "phone": "555-1102",
            "email": "nina.scott@example.com",
            "note": "Requested same-day follow-up for missed rounds or mobility setbacks.",
        },
    },
    {
        "name": "Ruth Alvarez",
        "email": "ruth.alvarez.demo@example.com",
        "phone": "555-0103",
        "membership_state": "active",
        "date_of_birth": "1944-11-08",
        "allergies": "Shellfish",
        "medical_notes": "Room 209. Needs blood-pressure follow-up after lunch rounds.",
        "emergency_note": "Nephew is backup contact only.",
        "tags": [tag_medication],
        "contact": {
            "name": "Elena Alvarez",
            "relationship": "Sister",
            "phone": "555-1103",
            "email": "elena.alvarez@example.com",
            "note": "Wants weekly updates unless there is an incident.",
        },
    },
    {
        "name": "James Holloway",
        "email": "james.holloway.demo@example.com",
        "phone": "555-0104",
        "membership_state": "active",
        "date_of_birth": "1936-01-19",
        "allergies": "Latex",
        "medical_notes": "Room 302. Strength recovery exercises after recent discharge.",
        "emergency_note": "Spouse prefers voicemail if she misses the first call.",
        "tags": [tag_falls],
        "contact": {
            "name": "Carol Holloway",
            "relationship": "Spouse",
            "phone": "555-1104",
            "email": "carol.holloway@example.com",
            "note": "Wants end-of-day summary after recovery rounds.",
        },
    },
    {
        "name": "Lila Thompson",
        "email": "lila.thompson.demo@example.com",
        "phone": "555-0105",
        "membership_state": "trial",
        "date_of_birth": "1947-07-24",
        "allergies": "None reported",
        "medical_notes": "Room 127. New intake for wellness and medication observation.",
        "emergency_note": "Son is available during business hours only.",
        "tags": [tag_medication],
        "contact": {
            "name": "Kevin Thompson",
            "relationship": "Son",
            "phone": "555-1105",
            "email": "kevin.thompson@example.com",
            "note": "Requested onboarding summary after first care round.",
        },
    },
]

members = {}
for spec in member_specs:
    member = upsert_member(spec, spec["tags"])
    members[spec["email"]] = member
    upsert_emergency_contact(member, **spec["contact"])

med_round.course_member_ids = [(6, 0, [
    members["evelyn.parker.demo@example.com"].id,
    members["walter.scott.demo@example.com"].id,
    members["ruth.alvarez.demo@example.com"].id,
    members["lila.thompson.demo@example.com"].id,
])]
mobility_round.course_member_ids = [(6, 0, [
    members["walter.scott.demo@example.com"].id,
    members["james.holloway.demo@example.com"].id,
])]
family_round.course_member_ids = [(6, 0, [
    members["evelyn.parker.demo@example.com"].id,
    members["walter.scott.demo@example.com"].id,
])]

session_defs = [
    {
        "key": "today_med_round",
        "template": med_round,
        "instructor": lead_staff,
        "start": make_dt(0, 13, 0),
        "end": make_dt(0, 14, 0),
        "capacity": 6,
        "state": "open",
        "enrollments": [
            ("evelyn.parker.demo@example.com", "registered", "pending", None),
            ("ruth.alvarez.demo@example.com", "registered", "pending", None),
            ("lila.thompson.demo@example.com", "registered", "pending", None),
        ],
    },
    {
        "key": "yesterday_med_round",
        "template": med_round,
        "instructor": lead_staff,
        "start": make_dt(-1, 13, 0),
        "end": make_dt(-1, 14, 0),
        "capacity": 6,
        "state": "done",
        "enrollments": [
            ("evelyn.parker.demo@example.com", "registered", "present", "Medication completed without issue."),
            ("ruth.alvarez.demo@example.com", "registered", "present", "Blood-pressure follow-up documented."),
            ("lila.thompson.demo@example.com", "registered", "present", "Observed first full round and tolerated well."),
        ],
    },
    {
        "key": "mobility_followup",
        "template": mobility_round,
        "instructor": support_staff,
        "start": make_dt(-2, 15, 0),
        "end": make_dt(-2, 16, 0),
        "capacity": 4,
        "state": "done",
        "enrollments": [
            ("james.holloway.demo@example.com", "registered", "present", "Completed mobility set with improved balance."),
            ("walter.scott.demo@example.com", "registered", "absent", "Missed round pending same-day follow-up."),
        ],
    },
    {
        "key": "family_followup",
        "template": family_round,
        "instructor": lead_staff,
        "start": make_dt(-3, 11, 0),
        "end": make_dt(-3, 12, 0),
        "capacity": 4,
        "state": "done",
        "enrollments": [
            ("evelyn.parker.demo@example.com", "registered", "present", "Family received continuity note after care-plan update."),
            ("walter.scott.demo@example.com", "cancelled", "pending", None),
        ],
    },
]

for session_def in session_defs:
    session = upsert_session(
        session_def["template"],
        session_def["instructor"],
        session_def["start"],
        session_def["end"],
        session_def["capacity"],
        "open" if session_def["state"] == "done" else session_def["state"],
    )
    for email, status, attendance_state, note in session_def["enrollments"]:
        enrollment = upsert_enrollment(session, members[email], status, attendance_state)
        if status == "registered" and attendance_state != "pending":
            upsert_attendance_log(session, enrollment, members[email], attendance_state, note)
    if session_def["state"] == "done":
        session.write({"state": "done"})

env.cr.commit()

print("Senior-care demo seed complete")
print("Members:", env["dojo.member"].search_count([]))
print("Instructors:", env["dojo.instructor.profile"].search_count([]))
print("Programs:", env["dojo.program"].search_count([]))
print("Templates:", env["dojo.class.template"].search_count([]))
print("Sessions:", env["dojo.class.session"].search_count([]))
print("Enrollments:", env["dojo.class.enrollment"].search_count([]))
print("Attendance Logs:", env["dojo.attendance.log"].search_count([]))

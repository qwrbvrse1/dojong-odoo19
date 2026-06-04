#!/usr/bin/env python3
# Odoo shell script: seed 5 demo accounts (admin, instructor, 2 students, parent)
# Idempotent: safe to re-run

import logging
from odoo import Command

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# Account specifications
ACCOUNTS = [
    {
        "role": "admin",
        "login": "admin@demo.com",
        "password": "admin123",
        "name": "Demo Admin",
        "groups": ["dojo_core.group_dojo_admin"],
    },
    {
        "role": "instructor",
        "login": "instructor1@demo.com",
        "password": "dojo@2026",
        "name": "Instructor One",
        "groups": ["dojo_core.group_dojo_instructor"],
    },
    {
        "role": "student",
        "login": "demo1@demo.com",
        "password": "dojo@2026",
        "name": "Demo Student One",
        "member_number": "DEMO-001",
    },
    {
        "role": "student",
        "login": "demo2@demo.com",
        "password": "dojo@2026",
        "name": "Demo Student Two",
        "member_number": "DEMO-002",
    },
    {
        "role": "parent",
        "login": "DemoParent@demo.com",
        "password": "dojo@2026",
        "name": "Demo Parent",
    },
]


def seed_accounts():
    """Upsert all demo accounts."""
    User = env["res.users"].sudo()
    Partner = env["res.partner"].sudo()
    Member = env["dojo.member"].sudo()
    InstructorProfile = env["dojo.instructor.profile"].sudo()

    # Get security group references
    group_admin = env.ref("dojo_core.group_dojo_admin")
    group_instructor = env.ref("dojo_core.group_dojo_instructor")
    group_parent_student = env.ref("dojo_core.group_dojo_parent_student")

    # Track student partners for household linkage
    student_partners = []
    household = None

    for spec in ACCOUNTS:
        login = spec["login"]
        role = spec["role"]
        _logger.info(f"Processing {role}: {login}")

        # Search for existing user
        user = User.search([("login", "=", login)], limit=1)

        if role in ("admin", "instructor"):
            # Internal users (admin, instructor)
            groups = [env.ref(group_xml) for group_xml in spec["groups"]]

            if user:
                # Update existing
                user.write({"password": spec["password"]})
                for grp in groups:
                    if grp not in user.group_ids:
                        user.write({"group_ids": [(4, grp.id)]})
                _logger.info(f"  → Updated existing user {user.id}")
            else:
                # Create new
                partner = Partner.create({
                    "name": spec["name"],
                    "email": login,
                })
                user = User.create({
                    "login": login,
                    "name": spec["name"],
                    "partner_id": partner.id,
                })
                for grp in groups:
                    user.write({"group_ids": [(4, grp.id)]})
                user.write({"password": spec["password"]})
                _logger.info(f"  → Created new user {user.id}, partner {partner.id}")

            # Special: create instructor profile
            if role == "instructor":
                profile = InstructorProfile.search([("user_id", "=", user.id)], limit=1)
                if not profile:
                    profile = InstructorProfile.create({
                        "name": spec["name"],
                        "user_id": user.id,
                        "partner_id": user.partner_id.id,
                    })
                    _logger.info(f"  → Created instructor profile {profile.id}")
                else:
                    _logger.info(f"  → Instructor profile already exists {profile.id}")

        elif role == "student":
            # Students: create dojo.member (auto-creates partner)
            member = Member.search([("email", "=", login)], limit=1)
            if member:
                # Update password if user exists
                if member.user_ids:
                    member.user_ids[0].sudo().write({"password": spec["password"]})
                    _logger.info(f"  → Updated existing member {member.id}")
                else:
                    # Grant portal access
                    creds = member._grant_portal_access_credentials()
                    if creds:
                        member.user_ids[0].sudo().write({"password": spec["password"]})
                        _logger.info(f"  → Granted portal access to member {member.id}")
            else:
                # Create new member
                member = Member.create({
                    "name": spec["name"],
                    "email": login,
                    "membership_state": "active",
                })
                # Grant portal access
                creds = member._grant_portal_access_credentials()
                if creds:
                    member.user_ids[0].sudo().write({"password": spec["password"]})
                _logger.info(f"  → Created new member {member.id}, partner {member.partner_id.id}")

            student_partners.append(member.partner_id)

        elif role == "parent":
            # Parent/guardian
            partner = Partner.search([("email", "=", login)], limit=1)
            if not partner:
                partner = Partner.create({
                    "name": spec["name"],
                    "email": login,
                    "is_guardian": True,
                })
                _logger.info(f"  → Created parent partner {partner.id}")
            else:
                partner.write({"is_guardian": True})
                _logger.info(f"  → Updated existing parent partner {partner.id}")

            # Grant portal access
            creds = partner._grant_portal_access_credentials()
            if creds:
                user = User.search([("login", "=", login)], limit=1)
                user.write({"password": spec["password"]})
                _logger.info(f"  → Granted portal access to parent")
            else:
                user = User.search([("login", "=", login)], limit=1)
                if user:
                    user.write({"password": spec["password"]})
                    _logger.info(f"  → Updated parent password")

            # Create household and link students
            household = Partner.search([("name", "=", "Demo Household")], limit=1)
            if not household:
                household = Partner.create({
                    "name": "Demo Household",
                    "is_household": True,
                    "is_company": True,
                    "primary_guardian_id": partner.id,
                })
                _logger.info(f"  → Created household {household.id}")
            else:
                household.write({"primary_guardian_id": partner.id})
                _logger.info(f"  → Updated household primary guardian")

            # Link students to household
            for student_partner in student_partners:
                student_partner.write({"parent_id": household.id})
                _logger.info(f"  → Linked student {student_partner.id} to household")

    env.cr.commit()
    _logger.info("✓ All 5 accounts seeded successfully")


# Execute
seed_accounts()

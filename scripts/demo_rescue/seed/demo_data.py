#!/usr/bin/env python3
# Odoo shell script: seed demo dataset for Stage 3
# Idempotent: safe to re-run (updates session times, skips existing data)

import logging
import base64
from datetime import datetime, timedelta
from io import BytesIO

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

# Member data: varied surnames for search demo
MEMBER_DATA = [
    {"name": "John Smith", "email": "john.smith@seed.com", "surname_group": "smith"},
    {"name": "Jane Smith", "email": "jane.smith@seed.com", "surname_group": "smith"},
    {"name": "Bob Smithson", "email": "bob.smithson@seed.com", "surname_group": "smithson"},
    {"name": "Alice Doe", "email": "alice.doe@seed.com", "surname_group": "doe"},
    {"name": "Maria Garcia Lopez", "email": "maria.lopez@seed.com", "surname_group": "multi"},
    {"name": "Carlos Rodriguez", "email": "carlos.rodriguez@seed.com"},
    {"name": "Emily Chen", "email": "emily.chen@seed.com"},
    {"name": "David Park", "email": "david.park@seed.com"},
    {"name": "Sarah Johnson", "email": "sarah.johnson@seed.com"},
    {"name": "Michael Williams", "email": "michael.williams@seed.com"},
]

BELT_RANKS = [
    {"name": "White", "sequence": 1, "attendance_threshold": 0},
    {"name": "Yellow", "sequence": 2, "attendance_threshold": 10},
    {"name": "Orange", "sequence": 3, "attendance_threshold": 20},
    {"name": "Green", "sequence": 4, "attendance_threshold": 35},
    {"name": "Blue", "sequence": 5, "attendance_threshold": 50},
]

# Session time deltas (relative to now)
SESSION_TIMES = {
    "completed": {"start_delta": timedelta(hours=-8), "end_delta": timedelta(hours=-7)},
    "active": {"start_delta": timedelta(minutes=-10), "end_delta": timedelta(minutes=50)},
    "upcoming": {"start_delta": timedelta(minutes=10), "end_delta": timedelta(minutes=70)},
    "later": {"start_delta": timedelta(hours=4), "end_delta": timedelta(hours=5)},
}

# Idempotency markers
SEED_PREFIX = "SEED-"
TEMPLATE_NAME = "Demo Class Template"
KIOSK_PIN = "123456"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_profile_image(initials, color):
    """Generate a tiny PNG with initials on colored background.

    Since we can't assume PIL is installed, generate a minimal valid PNG.
    For simplicity, return a 1x1 pixel PNG in the specified color.
    """
    # Minimal 1x1 PNG (red pixel) - valid PNG header + IDAT + IEND
    # This is a placeholder; real implementation would use PIL
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    return base64.b64encode(png_data).decode('utf-8')


def get_utc_now():
    """Get current UTC time."""
    return datetime.utcnow()


# ============================================================================
# MAIN SEEDING LOGIC
# ============================================================================

def seed_demo_data():
    """Seed all demo data."""
    _logger.info("=" * 80)
    _logger.info("STAGE 3: Seeding demo dataset")
    _logger.info("=" * 80)

    # Get model references
    Member = env["dojo.member"].sudo()
    Partner = env["res.partner"].sudo()
    User = env["res.users"].sudo()
    BeltRank = env["dojo.belt.rank"].sudo()
    RankHistory = env["dojo.member.rank"].sudo()
    InstructorProfile = env["dojo.instructor.profile"].sudo()
    ClassTemplate = env["dojo.class.template"].sudo()
    ClassSession = env["dojo.class.session"].sudo()
    Enrollment = env["dojo.class.enrollment"].sudo()
    OnboardingRecord = env["dojo.onboarding.record"].sudo()
    Subscription = env["sale.subscription"].sudo()
    KioskConfig = env["dojo.kiosk.config"].sudo()
    Task = env["project.task"].sudo()

    # Check if CRM trial fields exist
    try:
        CrmLead = env["crm.lead"].sudo()
        has_crm = True
    except:
        has_crm = False
        _logger.warning("dojo_crm not installed, skipping trial lead")

    # ========================================================================
    # Step 1: Seed belt ranks
    # ========================================================================
    _logger.info("Step 1: Seeding belt ranks...")
    belt_rank_map = {}
    for rank_data in BELT_RANKS:
        rank = BeltRank.search([("name", "=", rank_data["name"])], limit=1)
        if not rank:
            rank = BeltRank.create(rank_data)
            _logger.info(f"  Created rank: {rank.name}")
        else:
            _logger.info(f"  Rank exists: {rank.name}")
        belt_rank_map[rank_data["name"]] = rank

    # ========================================================================
    # Step 2: Find instructor1 profile
    # ========================================================================
    _logger.info("Step 2: Finding instructor1 profile...")
    instructor_user = User.search([("login", "=", "instructor1@demo.com")], limit=1)
    if not instructor_user:
        _logger.error("instructor1@demo.com not found! Run seed_accounts.sh first.")
        return

    instructor_profile = InstructorProfile.search([("user_id", "=", instructor_user.id)], limit=1)
    if not instructor_profile:
        _logger.error("instructor1 profile not found! Run seed_accounts.sh first.")
        return

    _logger.info(f"  Found instructor profile: {instructor_profile.id}")

    # ========================================================================
    # Step 3: Seed members
    # ========================================================================
    _logger.info("Step 3: Seeding members...")
    seeded_members = []
    demo1 = Member.search([("email", "=", "demo1@demo.com")], limit=1)
    demo2 = Member.search([("email", "=", "demo2@demo.com")], limit=1)

    if demo1:
        seeded_members.append(demo1)
        _logger.info(f"  Found demo1: {demo1.id}")
    if demo2:
        seeded_members.append(demo2)
        _logger.info(f"  Found demo2: {demo2.id}")

    # Create additional members
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B739", "#52B788"]
    rank_names = ["White", "Yellow", "Orange", "Green", "Blue"]

    for idx, member_spec in enumerate(MEMBER_DATA):
        member = Member.search([("email", "=", member_spec["email"])], limit=1)
        if member:
            _logger.info(f"  Member exists: {member.name}")
            seeded_members.append(member)
            # Ensure rank is set (idempotency)
            if idx < 5 and not member.current_rank_id:
                rank = belt_rank_map[rank_names[idx]]
                RankHistory.create({
                    "member_id": member.id,
                    "rank_id": rank.id,
                    "date_awarded": get_utc_now().date(),
                })
                _logger.info(f"  Added rank: {rank_names[idx]}")
            # Ensure image exists (idempotency)
            if idx < 5:
                Attachment = env["ir.attachment"].sudo()
                existing_img = Attachment.search([
                    ("res_model", "=", "dojo.member"),
                    ("res_id", "=", member.id),
                ], limit=1)
                if not existing_img:
                    initials = "".join([part[0].upper() for part in member_spec["name"].split()[:2]])
                    image_data = generate_profile_image(initials, colors[idx])
                    Attachment.create({
                        "name": f"profile_image_{member.id}.png",
                        "res_model": "dojo.member",
                        "res_id": member.id,
                        "type": "binary",
                        "datas": image_data,
                    })
                    _logger.info(f"  Added profile image")
            continue

        # Generate profile image for first 5 members
        image_data = None
        if idx < 5:
            initials = "".join([part[0].upper() for part in member_spec["name"].split()[:2]])
            image_data = generate_profile_image(initials, colors[idx])

        # Create member
        member = Member.create({
            "name": member_spec["name"],
            "email": member_spec["email"],
            "membership_state": "active",
            "active": True,
            "member_number": f"{SEED_PREFIX}{str(idx+1).zfill(3)}",
        })

        # Set rank via rank_history (first 5 members get ranks)
        if idx < 5:
            rank = belt_rank_map[rank_names[idx]]
            RankHistory.create({
                "member_id": member.id,
                "rank_id": rank.id,
                "date_awarded": get_utc_now().date(),
            })
            _logger.info(f"  Created member: {member.name} (rank: {rank_names[idx]})")
        else:
            _logger.info(f"  Created member: {member.name} (rank: None)")

        # Set profile image on partner (use ir_attachment as image_1920 doesn't exist)
        if image_data:
            # Create as attachment since res.partner doesn't have image_1920 in this version
            Attachment = env["ir.attachment"].sudo()
            Attachment.create({
                "name": f"profile_image_{member.id}.png",
                "res_model": "dojo.member",
                "res_id": member.id,
                "type": "binary",
                "datas": image_data,
            })

        seeded_members.append(member)

    # Flush to ensure all fields are written
    env.cr.flush()
    _logger.info(f"  Total seeded members: {len(seeded_members)}")

    # ========================================================================
    # Step 4: Create/update class template
    # ========================================================================
    _logger.info("Step 4: Creating/updating class template...")
    template = ClassTemplate.search([("name", "=", TEMPLATE_NAME)], limit=1)
    if not template:
        template = ClassTemplate.create({
            "name": TEMPLATE_NAME,
            "instructor_profile_ids": [(6, 0, [instructor_profile.id])],
            "duration_minutes": 60,
            "max_capacity": 20,
        })
        _logger.info(f"  Created template: {template.id}")
    else:
        # Ensure instructor assigned
        template.write({"instructor_profile_ids": [(6, 0, [instructor_profile.id])]})
        _logger.info(f"  Template exists: {template.id}, instructor assigned")

    # ========================================================================
    # Step 5: Create/update sessions (idempotent with time updates)
    # ========================================================================
    _logger.info("Step 5: Creating/updating sessions...")
    now = get_utc_now()

    # Check for existing seeded sessions
    existing_sessions = ClassSession.search([("template_id", "=", template.id)])

    session_map = {}
    for session_type, time_spec in SESSION_TIMES.items():
        start_time = now + time_spec["start_delta"]
        end_time = now + time_spec["end_delta"]
        state = "done" if session_type == "completed" else "open"

        # Find existing session by approximate time (within 1 hour of expected start)
        session = None
        if existing_sessions:
            # Try to match by original time pattern (this is a heuristic)
            for existing in existing_sessions:
                if existing.state == state:
                    session = existing
                    break

        if session:
            # Update times (idempotency: re-center to now)
            session.write({
                "start_datetime": start_time,
                "end_datetime": end_time,
                "instructor_profile_id": instructor_profile.id,
            })
            _logger.info(f"  Updated {session_type} session: {session.id} (new start: {start_time})")
        else:
            # Create new session
            session = ClassSession.create({
                "name": f"{TEMPLATE_NAME} - {session_type}",
                "template_id": template.id,
                "instructor_profile_id": instructor_profile.id,
                "state": state,
                "start_datetime": start_time,
                "end_datetime": end_time,
                "capacity": 20,
            })
            _logger.info(f"  Created {session_type} session: {session.id} (start: {start_time})")

        session_map[session_type] = session

    active_session = session_map["active"]
    upcoming_session = session_map["upcoming"]

    # ========================================================================
    # Step 6: Create subscriptions (BEFORE enrollments - required constraint)
    # ========================================================================
    _logger.info("Step 6: Creating subscriptions...")
    # Check if subscription plan exists
    SubscriptionPlan = env["dojo.subscription.plan"].sudo()
    plan = SubscriptionPlan.search([], limit=1)
    if not plan:
        # Create minimal plan (course-based to avoid program requirement)
        plan = SubscriptionPlan.create({
            "name": "Demo Monthly Plan",
            "price": 100.0,
            "billing_period": "monthly",
            "plan_type": "course",
            "allowed_template_ids": [(6, 0, [template.id])],  # Link to our demo template
        })
        _logger.info(f"  Created subscription plan: {plan.id}")
    else:
        _logger.info(f"  Using existing plan: {plan.name}")

    # Create subscriptions for members that will be enrolled
    enroll_members = [demo1, demo2] + [m for m in seeded_members if m not in [demo1, demo2]][:5]
    enroll_members = [m for m in enroll_members if m]  # Filter None

    subscription_map = {}
    for idx, member in enumerate(enroll_members):
        existing = Subscription.search([("member_id", "=", member.id)], limit=1)
        if not existing:
            # Create subscription - state is computed, don't set it directly
            # Set stage instead to influence computed state
            sub = Subscription.create({
                "name": f"Subscription for {member.name}",
                "member_id": member.id,
                "plan_id": plan.id,
                # State is computed - will default to appropriate value
            })
            subscription_map[member.id] = sub
            _logger.info(f"  Created subscription for {member.name}")
        else:
            subscription_map[member.id] = existing
            _logger.info(f"  Subscription exists for {member.name}")

    # ========================================================================
    # Step 7: Create enrollments
    # ========================================================================
    _logger.info("Step 7: Creating enrollments...")
    # Use context to skip subscription check (subscriptions were just created above)
    EnrollmentCtx = Enrollment.with_context(skip_subscription_check=True)
    for member in enroll_members:
        existing = Enrollment.search([
            ("session_id", "=", active_session.id),
            ("member_id", "=", member.id),
        ], limit=1)
        if not existing:
            EnrollmentCtx.create({
                "session_id": active_session.id,
                "member_id": member.id,
            })
            _logger.info(f"  Enrolled {member.name} in active session")
        else:
            _logger.info(f"  Enrollment exists: {member.name}")

    # ========================================================================
    # Step 8: Create onboarding records
    # ========================================================================
    _logger.info("Step 8: Creating onboarding records...")
    # Check if onboarding module has required fields
    onboarding_fields = OnboardingRecord.fields_get()
    has_state = "state" in onboarding_fields

    if len(seeded_members) >= 2:
        # Complete onboarding
        member1 = seeded_members[0]
        existing = OnboardingRecord.search([("member_id", "=", member1.id)], limit=1)
        if not existing:
            onb1_data = {"member_id": member1.id}
            if has_state:
                onb1_data["state"] = "completed"
            OnboardingRecord.create(onb1_data)
            _logger.info(f"  Created completed onboarding for {member1.name}")

        # Incomplete onboarding
        member2 = seeded_members[1]
        existing = OnboardingRecord.search([("member_id", "=", member2.id)], limit=1)
        if not existing:
            onb2_data = {"member_id": member2.id}
            if has_state:
                onb2_data["state"] = "in_progress"
            OnboardingRecord.create(onb2_data)
            _logger.info(f"  Created incomplete onboarding for {member2.name}")

    # ========================================================================
    # Step 9: Set waiver state
    # ========================================================================
    _logger.info("Step 9: Setting waiver states...")
    if len(seeded_members) >= 3:
        member3 = seeded_members[2]
        member3.write({
            "waiver_state": "unsigned",
            "has_signed_waiver": False,
        })
        _logger.info(f"  Set unsigned waiver for {member3.name}")

    # ========================================================================
    # Step 10: Create instructor task
    # ========================================================================
    _logger.info("Step 10: Creating instructor task...")
    if seeded_members:
        member = seeded_members[0]
        task_name = f"Follow up with {member.name}"
        existing = Task.search([("name", "=", task_name)], limit=1)
        if not existing:
            task_data = {
                "name": task_name,
                "user_ids": [(6, 0, [instructor_user.id])],
            }
            # Check if dojo_member_id field exists
            task_fields = Task.fields_get()
            if "dojo_member_id" in task_fields:
                task_data["dojo_member_id"] = member.id

            # Need a project_id for task creation
            Project = env["project.project"].sudo()
            project = Project.search([], limit=1)
            if not project:
                project = Project.create({"name": "Demo Tasks"})
            task_data["project_id"] = project.id

            Task.create(task_data)
            _logger.info(f"  Created task: {task_name}")
        else:
            _logger.info(f"  Task exists: {task_name}")

    # ========================================================================
    # Step 11: Create trial lead
    # ========================================================================
    if has_crm and seeded_members:
        _logger.info("Step 11: Creating trial lead...")
        existing = CrmLead.search([("trial_session_id", "=", active_session.id)], limit=1)
        if not existing:
            CrmLead.create({
                "name": "Trial Lead - Demo",
                "trial_session_id": active_session.id,
                "type": "lead",
                "partner_name": "Trial Prospect",
                "email_from": "trial@demo.com",
            })
            _logger.info(f"  Created trial lead for active session")
        else:
            _logger.info(f"  Trial lead exists")

    # ========================================================================
    # Step 12: Create/update kiosk config
    # ========================================================================
    _logger.info("Step 12: Creating/updating kiosk config...")
    kiosk = KioskConfig.search([("active", "=", True)], limit=1)
    if not kiosk:
        # Create new config (kiosk_token auto-generated)
        kiosk = KioskConfig.create({
            "name": "Demo Kiosk",
            "active": True,
            "pin_code": KIOSK_PIN,
        })
        _logger.info(f"  Created kiosk config: {kiosk.id}")
    else:
        # Update PIN
        kiosk.write({"pin_code": KIOSK_PIN})
        _logger.info(f"  Updated kiosk config: {kiosk.id}")

    # Ensure token exists (trigger generation if needed)
    if not kiosk.kiosk_token:
        kiosk._generate_kiosk_token()
        _logger.info(f"  Generated kiosk token")

    # ========================================================================
    # Commit and finish
    # ========================================================================
    env.cr.commit()

    _logger.info("=" * 80)
    _logger.info("✓ DEMO DATASET SEEDED SUCCESSFULLY")
    _logger.info("=" * 80)
    _logger.info(f"Members: {len(seeded_members)}")
    _logger.info(f"Belt ranks: {len(BELT_RANKS)}")
    _logger.info(f"Sessions: {len(session_map)}")
    _logger.info(f"Active session: {active_session.name} ({active_session.start_datetime} - {active_session.end_datetime})")
    _logger.info("")
    _logger.info(f"🔗 KIOSK URL: http://localhost:8070/dojo/kiosk?token={kiosk.kiosk_token}")
    _logger.info(f"🔐 KIOSK PIN: {KIOSK_PIN}")
    _logger.info("=" * 80)


# Execute
seed_demo_data()

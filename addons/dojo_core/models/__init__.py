from . import (
    # Base models (no _inherit on other dojo.* models)
    martial_art_style,
    belt_rank,
    emergency_contact,
    instructor_profile,
    member,
    program,
    class_template,
    class_session,
    class_enrollment,
    attendance_log,
    member_rank,
    belt_test,
    belt_test_registration,
    belt_test_automation,
    belt_promotion_wizard,
    # Extensions (use _inherit on models above)
    auto_enroll_preference,
    res_partner,
    res_users,
    # Instructor dashboard
    dojo_instructor_kpi,
    dojo_instructor_todos,
    dojo_attendance_quick_wizard,
    dojo_member_profile,
)

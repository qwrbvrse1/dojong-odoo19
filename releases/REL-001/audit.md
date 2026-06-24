---
# Audit Verdict — REL-001

> Produced by: GPT-5.3-Codex · Date: 2026-06-23
> Auditor constraint: this model did not produce the release code.

## Verdict

**APPROVED-PARTIAL**

The release diff demonstrates substantial delivery across Milestones 0-5 and the final run record shows PASS verdicts for INC-01 through INC-23, but several scope requirements are only partially met: kiosk check-in success auto-dismiss timing is inconsistent with the 3s requirement, get_member_profile does not clearly expose explicit available_actions for onboarding actions in payload shape, communication automations are implemented as custom ir.cron jobs rather than OCA automation rules as scoped, and MuK replacement is documented as accepting some feature loss rather than providing full parity. On that basis, the release is approved with partial completeness.

## Completeness (scope → diff)

| Scope item | Status | Evidence |
|---|---|---|
| M0: dojo_theme module exists with required tokens and Google Fonts override | present | addons/dojo_theme/__manifest__.py, addons/dojo_theme/static/src/css/tokens.css, addons/dojo_theme/views/fonts.xml |
| M0: sms_twilio module present and version-controlled | present | addons/sms_twilio/** added in diff |
| M1: dojo.member surname-first name_search ranking | present | addons/dojo_core/models/member.py (_name_search, probable surname parsing, last_name ranking), addons/dojo_core/tests/test_member_search.py |
| M1: get_member_profile returns onboarding statuses/progress/actions and onboarding endpoints authenticated | partial | onboarding status + progress present in addons/dojo_kiosk/models/dojo_kiosk_service.py and endpoints in addons/dojo_kiosk/controllers/kiosk_controller.py; explicit available_actions keys for complete_step/send_reminder not evident in payload shape |
| M1: get_todays_sessions returns time_state (active/upcoming_soon/upcoming/done) | present | addons/dojo_kiosk/models/dojo_kiosk_service.py (get_todays_sessions_payload time_state logic), addons/dojo_kiosk/tests/test_session_time_state.py |
| M1: dojo.member expdate stored, indexed, computed from subscription | present | addons/dojo_core/models/member.py (expdate field store/index + _compute_expdate), addons/dojo_core/views/member_views.xml, addons/dojo_core/tests/test_member_expdate.py |
| M2: dojo_instructor_dashboard implemented and installable with stats/chart/lists | present | addons/dojo_instructor_dashboard/__manifest__.py, controllers/dashboard.py, static/src/xml/dashboard.xml, tests/test_dashboard_controller.py |
| M2: instructor kiosk three-panel grid layout | present | addons/dojo_kiosk/static/src/css/kiosk_instructor.css, addons/dojo_kiosk/static/src/js/kiosk_instructor.js |
| M2: check-in success full-screen overlay + belt color + chime + 3s dismiss | partial | overlay + chime implemented in addons/dojo_kiosk/static/src/kiosk_app.js and addons/dojo_kiosk/static/src/kiosk.css; timeout values include 4000ms/3500ms paths in addition to a 3000ms path |
| M2: session auto-select active/upcoming_soon and state classes | present | addons/dojo_kiosk/static/src/kiosk_app.js (auto-selection + class mapping), addons/dojo_kiosk/static/src/kiosk.css (k-session--active/soon/upcoming/done) |
| M2: InstructorRosterTile onboarding_pct bar and open_task_count badge | present | addons/dojo_kiosk/models/dojo_kiosk_service.py (onboarding_pct/open_task_count in roster payload), addons/dojo_kiosk/static/src/kiosk_app.js rendering |
| M2: MemberProfileCard onboarding section with Mark Complete/Send Reminder/Add Note/Escalate | present | addons/dojo_kiosk/static/src/kiosk_app.js onboarding actions and addons/dojo_kiosk/models/dojo_kiosk_service.py perform_onboarding_action |
| M3: dojo_belt_progression fully implemented OWL mass promotion + undo + history | present | addons/dojo_belt_progression/**, controllers/promotion.py, static/src/js/mass_promote.js, views/promotion_history.xml |
| M3: belt test roster filter/print/save as dojo.belt.test | present | addons/dojo_belt_progression/controllers/roster.py, static/src/js/belt_test_roster.js, static/src/css/roster_print.css, views/belt_test_roster.xml |
| M3: attendance analytics (30/90, busiest classes, top attendees, zero attendance) | present | addons/dojo_instructor_dashboard/controllers/analytics.py, static/src/js/analytics.js, views/analytics.xml, tests/test_analytics.py |
| M3: dojo_members reports implemented (inactive/contact/family) | present | addons/dojo_members/controllers/reports.py, static/src/js/reports.js, static/src/xml/reports.xml, views/reports.xml |
| M3: CSV export wizard for students/attendance/promotion/rosters | present | addons/dojo_instructor_dashboard/models/export_wizard.py, controllers/export.py, views/export_wizard.xml, tests/test_export.py |
| M4: Email Center with segmentation, single-member capable send, history log | present | addons/dojo_communications/controllers/email_center.py, models/email_history.py, static/src/js/email_center.js, views/email_center.xml, tests/test_email_center.py |
| M4: Follow-up email action from Inactive Student report | present | addons/dojo_members/controllers/followup.py, static/src/js/reports.js, static/src/xml/reports.xml, tests/test_followup_email.py |
| M4: Birthday email automation via OCA automation rule (configurable) | partial | implemented as ir.cron + config + template in addons/dojo_automation/data/birthday_automation.xml and addons/dojo_automation/data/birthday_template.xml, not as explicit OCA rule record |
| M4: Membership expiry email automation via OCA automation rule (configurable) | partial | implemented as ir.cron + config + template in addons/dojo_automation/data/expiry_automation.xml and addons/dojo_automation/data/expiry_template.xml, not as explicit OCA rule record |
| M5: all seven muk_web_* modules removed from addons and uninstalled in DB | present | addons/muk_web_* directories deleted in diff; runlog INC-23 final PASS |
| M5: dojo_theme provides all visual styling previously supplied by MuK | partial | SPECIFICATION.md §3.4 and releases/REL-001/muk-audit.md document accepted losses (appsbar/chatter/dialog/refresh/group/layout SCSS not fully replaced) |
| M5: docs/ui-ux-guide updated to dojo_theme tokens, no MuK references | present | docs/ui-ux-guide.md updated with dojo_theme token system |

## Drift (diff → scope)

| Change | Increment | Assessment |
|---|---|---|
| Addition of demo rescue and usability orchestration artifacts (docs/rescue/**, docs/usability_pass/**, scripts/demo_rescue/**, scripts/usability_pass/**) | Multi-increment (not mapped in scope bullets) | unjustified drift |
| Addition of OS metadata artifacts (scripts/demo_rescue/._* entries) | Multi-increment | unjustified drift |
| Broad security ACL edits across many modules not directly tied to scoped features (multiple security/ir.model.access.csv changes) | Multi-increment | justified (supporting implementation hardening) |
| Root-level process docs and runbooks added (DEMO_RESCUE.md, DEMO_RUNBOOK.md, USABILITY_PASS*.md, CHANGELOG.md) beyond scoped feature set | Multi-increment | unjustified drift |
| odoo file/symlink addition and .gitmodules update not explicitly scoped | Multi-increment | unjustified drift |

## Spec integrity

Scope-listed affected SPEC sections are updated in the final SPECIFICATION.md: §3.1 includes dojo_theme and implemented modules; §3.4 marks MuK retirement; §3.5 removes dojo_belt_progression from stubs; §4 documents expdate and kiosk payload details; §5 reflects new dashboard/belt/reports/communications/automation features; §10 is updated for dojo_theme; and §12 marks MuK/UI guide debt items resolved. The main integrity issue is spec-vs-scope alignment on MuK and automation mechanisms: SPEC §3.4 explicitly records accepted MuK feature losses, while scope states dojo_theme should provide all visual styling previously supplied by MuK; and automation implementation is documented as ir.cron-driven logic rather than explicit OCA automation-rule records required by scope wording. Kiosk profile onboarding data in spec is broadly consistent with code, but explicit available_actions keys are not clearly present in member profile payload.

## Run record

INC-01 used 3 shots, final score 1.00, final verdict PASS. Retry shots were classified code_defect; failure reports show post-gate authentication/token failures before eventual successful pass commit bdb77bdb15a7e2a6d4a7de5c4621b378a1c922af.

INC-02 used 3 shots, final score 1.00, final verdict PASS. Retry shots were code_defect with post-gate failures (including authentication-related failures) before passing at commit 058502d88c8e947bb3c8db190af7bd2b5a16d6ba.

INC-03 used 1 shot, final score 1.00, final verdict PASS. No retries are recorded; pass commit e18ae1903f1cb6e5019103b05f0b2f0f4aae9942.

INC-04 used 2 shots, final score 1.00, final verdict PASS. First shot was code_defect with dojo_kiosk onboarding API gate failure; second shot passed at commit 8faffa1553872a9ef01354a99db1dc87f4a36570.

INC-05 used 3 shots, final score 1.00, final verdict PASS. Retries were code_defect, including test_session_time_state failures and post-gate errors, then pass at commit 78907a644c8fa95fbc0f1fed31a985e9c5f79405.

INC-06 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit bbfe4fe43feea7d23b067ca8d82db1f411e73036.

INC-07 used 3 shots, final score 1.00, final verdict PASS. Retries include code_defect and environmental classifications, with repeated post-gate failures before final pass at commit 66ab2365fe0c208d684338da80d4820173c650bc.

INC-08 used 2 shots, final score 1.00, final verdict PASS. First attempt failed gate on session summary test (code_defect), then passed at commit 23ea7352f5d919801d38908dc0a32d1f4939b725.

INC-09 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit 51519aa968dc7eea37f2ac21500dc827e5b740fe.

INC-10 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit 2458b85563e4589942b0982d3f02afbd88ff11f7.

INC-11 used 2 shots, final score 1.00, final verdict PASS. First shot failed roster badge gate (code_defect), second passed at commit 40d4c73f21385403cb64c4c285a5044d4f649fba.

INC-12 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit 52c6de11d56addfdd97a6a78d0d6ce9db4f704a9.

INC-13 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit e6e847e9ab84bbc47d8649c6639dcb97c6fb322f.

INC-14 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit cf7627ec6b3bd05e901ef5762e3b16a462436c5c.

INC-15 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit b08b431332a73910bd1f7004eaf5d269507b610d.

INC-16 used 3 shots, final score 1.00, final verdict PASS. Multiple retry cycles were classified code_defect with post-gate authentication failures in failure reports; final pass commit e5936de2e19d6ed2e3d1e9619bd762e3b4f4a33f.

INC-17 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit 889e669856ded24d00b0b057eb30b4a13fb76f7a.

INC-18 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit e1c5345dc2f26c8e733bd34e5aede0eb28ebfd34.

INC-19 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit a39048b1a5452ae7daa3c83872092bec1a22f33a.

INC-20 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit 34d285c44179bbaad14ec08d7fc5832c95bbd54e.

INC-21 used 1 shot, final score 1.00, final verdict PASS. No retries; pass commit 94ba333f4e11a631fdf83225c6906d5cf145b709.

INC-22 used 3 shots, final score 1.00, final verdict PASS. Retry classifications include environmental and code_defect; failure reports show repeated MuK dependency gate failures (2/4 gates passed in failed shots) before final pass commit e2df9000f9d9203194873245030db3e0a90b3f5a.

INC-23 used 1 shot, final score 1.00, final verdict PASS. No retries are recorded; pass commit 61352218b1a7f559d1326adba2a59d18d8f323dc.

## Recommendations

1. Normalize scope wording vs implementation mechanism for communications automation: either require OCA rule records explicitly or permit equivalent ir.cron implementation to avoid audit ambiguity.
2. Add a hard gate for kiosk success-overlay timeout to enforce exact 3s behavior across all check-in flows.
3. Add explicit payload contract tests for get_member_profile onboarding available_actions to match scope and spec text.
4. Split non-release artifacts (rescue/usability logs/scripts and OS metadata files) into a separate operations branch/release to reduce drift in feature release diffs.
5. Align MuK replacement acceptance criteria: either codify accepted losses in scope or require full parity checks before retirement claims.

---
*Auditor: GPT-5.3-Codex · Date: 2026-06-23 · Countersigned: John Bentley, II

# CHANGELOG — dojong-odoo19

Format: one entry per Release (`REL-NNN`). Each entry is written after the release audit and merge.  
Conventions: see `UnattendedBuild/templates/spec-changelog-conventions.md`.  
Full run history: `workproducts/<project>/REL-NNN/runlog.jsonl`.

---

## [REL-001] — 2026-06-23 — UFTKD Platform Feature Delivery

### Added
- `dojo_theme` — new Odoo module providing all brand design tokens (15 CSS custom properties: `--bg`, `--surface`, `--surface2`, `--surface3`, `--border`, `--red`, `--red-dim`, `--gold`, `--gold-light`, `--text`, `--text-muted`, `--text-dim`, `--green`, `--orange`, `--blue`) and fonts (Bebas Neue, Barlow, Barlow Condensed) via Google Fonts asset override. Replaces all MuK IT theme modules as the sole visual layer.
- `dojo_instructor_dashboard` — implemented from stub: four stat cards (active students, today check-ins, upcoming birthdays, expiring memberships), belt distribution bar chart, birthday list (next 7 days), expiring memberships list (next 30 days). All data sourced from `dojo.member` and `dojo.attendance.log`.
- `dojo_belt_progression` — implemented from stub: mass belt promotion OWL view with multi-select grid, single-click promote-all, in-session undo stack, per-member promotion history log (date, from-rank, to-rank, promoted-by). Belt test roster view filterable by class group and belt rank; print-ready CSS `@media print` output; saved as named `dojo.belt.test` records.
- `releases/REL-001/muk-audit.md` — MuK replacement coverage audit document produced in INC-22.

### Changed
- `dojo_kiosk` — instructor view rewritten as three-panel CSS grid (active session + countdown, member roster, notes/alerts); check-in success state now shows a full-screen overlay with member name, belt rank color, and Web Audio API chime (auto-dismisses after 3 s); session list auto-selects `active` or `upcoming_soon` on page load; session cards carry visual state classes (`k-session--active`, `k-session--soon`, `k-session--upcoming`, `k-session--done`); `InstructorRosterTile` renders `onboarding_pct` progress bar and `open_task_count` badge; `MemberProfileCard` has an Onboarding tab with per-step status and action buttons (Mark Complete, Send Reminder, Add Note, Escalate); `get_todays_sessions()` now returns `time_state` on each session; new kiosk API endpoints `/kiosk/api/onboarding/complete_step` and `/kiosk/api/onboarding/send_reminder`.
- `dojo_members` — `dojo.member` gains stored computed field `expdate` (Date, indexed) derived from linked subscription state, recomputed via `_compute_expdate`; `name_search` override ranks surname-first matches above mid-name matches; Reports views added: Inactive Student, Contact (missing guardian email/phone), Family (household groupings); CSV export wizard for students, attendance log, promotion history, belt test rosters.
- `dojo_communications` — Email Center OWL view for mass email to audience segments (class group, belt rank, expiring status) and individual member email; email history log (sent date, subject, recipient count, sender); follow-up email action wired to Inactive Student report; birthday email OCA automation (daily rule, configurable days-ahead, template); membership expiry warning OCA automation (daily rule, configurable days-ahead threshold, template).
- `sms_twilio` — module source added to `addons/sms_twilio/` and tracked in version control.
- `SPECIFICATION.md` — §3.1 module inventory updated (`dojo_theme` added; `dojo_instructor_dashboard`, `dojo_belt_progression`, `dojo_members`, `dojo_communications` promoted from stub/partial to implemented); §3.4 MuK IT theme section updated (all 7 modules retired); §3.5 stub list updated (`dojo_belt_progression` removed); §4 data model updated (`dojo.member.expdate`, kiosk API response shape); §5 deployed functionality updated for M1–M4; §10 design system updated (MuK → `dojo_theme`, migration plan marked complete); §12 tech debt items resolved.
- `docs/ui-ux-guide.md` — rewritten to document `dojo_theme` token system: all 15 CSS custom properties with values and intended use, typography stack. All MuK references removed.

### Removed
- `muk_web_theme`, `muk_web_chatter`, `muk_web_appsbar`, `muk_web_colors`, `muk_web_dialog`, `muk_web_group`, `muk_web_refresh` — all 7 MuK IT theme modules uninstalled from the `odoo19` database and directories removed from `addons/`. Visual coverage fully provided by `dojo_theme`.

### Technical Debt Addressed
- MuK IT theme dependency eliminated; `dojo_theme` is now the sole styling layer (SPEC §12).
- `docs/ui-ux-guide.md` rewritten to reflect current design system — MuK token references removed (SPEC §12).

### Deferred
- None. All 23 increments passed.

Audited by: *(pending audit)*

---

## [Unreleased]

*(Increments merged to `main` outside a formal release cycle — pre-method work.)*

### Added
- `dojo_core` (saas~19.2.4.0.0) — member management, classes, attendance, belt progression, instructor dashboard
- `dojo_kiosk` (saas~19.2.1.1.0) — tablet check-in kiosk
- `dojo_subscriptions` (saas~19.2.6.0.0) — membership plans and subscriptions
- `dojo_onboarding` (saas~19.2.1.0.0) — member onboarding wizard
- `dojo_onboarding_stripe` (saas~19.2.1.0.0) — Stripe payment method collection during onboarding
- `dojo_crm` (saas~19.2.2.0.0) — CRM pipeline, lead scoring, trial booking, convert-to-member
- `dojo_communications` (saas~19.2.1.0.0) — automated SMS/email communications
- `dojo_marketing` (saas~19.2.3.0.0) — QR promotional cards
- `dojo_sign` (saas~19.2.2.0.0) — inline waiver signing
- `dojo_stripe` (saas~19.2.2.0.0) — Stripe Billing + Stripe Issuing
- `dojo_members_portal` (saas~19.2.3.0.0) — self-service member portal
- `dojo_website` (saas~19.2.1.0.0) — public website with trial booking
- `dojo_events` (saas~19.2.1.0.0) — member-to-events linking
- `dojo_calendar` (saas~19.2.1.0.0) — class session calendar sync
- `dojo_automation` (saas~19.2.1.1.0) — visual automation builder
- `dojo_points` (saas~19.2.1.0.0) — attendance/achievement points
- `dojo_credits` (saas~19.2.1.0.0) — class credit ledger
- `dojo_social` (saas~19.2.1.0.0) — social media post scheduling
- `dojo_connect_ai` (saas~19.2.1.0.0) — AI receptionist (Kai)
- `dojo_bridge` (saas~19.2.2.0.0) — headless REST API bridge
- `dojo_checkout` (saas~19.2.2.0.0) — public checkout pages
- `dojo_firebase` (saas~19.2.1.0.0) — Firebase email relay + FCM push
- `dojo_management` (saas~19.2.1.0.0) — belt ranking analytics
- `dojo_migration` (saas~19.2.1.0.0) — SparkMembership CSV import
- `ai_assistant` (saas~19.2.1.0.0) — AI voice assistant service
- `ai_vector` (saas~19.2.1.0.0) — vector embedding layer
- `ai_mcp` (saas~19.2.1.0.0) — MCP server
- `elevenlabs_connector` (saas~19.2.1.0.0) — ElevenLabs voice integration
- `dojo_ai_caller` (saas~19.2.1.0.0) — AI outbound calling
- MuK IT theme (`muk_web_theme` + 6 supporting modules, saas~19.2.x)
- Third-party: `automation_oca`, `subscription_oca`, `bi_all_digital_sign`, `connect` (Twilio)

---

<!--
RELEASE ENTRY TEMPLATE (copy for each REL-NNN):

## [REL-NNN] — YYYY-MM-DD — <short release title>

### Added
- `module_name` (version) — brief description of new behavior

### Changed
- `module_name` — what changed and why

### Fixed
- `module_name` — what was broken, what the fix is

### Removed
- `module_name` — what was removed and why

### Technical Debt Addressed
- List any tech-debt items from SPECIFICATION.md § 12 resolved by this release

### Deferred
- List any increments that did not pass (partial release)

Audited by: <auditor> on <date>
-->

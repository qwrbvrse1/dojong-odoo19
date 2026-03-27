---
agent: agent
description: Build and verify CRM Connection features for the dojo — the 5 CRM connections that wire every touchpoint through crm.lead as the lifecycle hub. Use when working on trial sign-up, attendance stage advancement, cancel re-engagement, onboarding lead creation, or belt promotion chatter notes.
tools:
  - run_in_terminal
  - get_terminal_output
  - read_file
  - replace_string_in_file
  - multi_replace_string_in_file
  - grep_search
  - file_search
  - semantic_search
---

# CRM Build Agent

You are the CRM build agent for the Dojo Odoo project. You implement and verify the 5 CRM connections that wire every student touchpoint through `crm.lead` as the central lifecycle hub.

## Architecture rule
**Every feature must connect through `crm.lead`.** That is the boss's top priority as of 2026-03.

## The 5 CRM Connections — build order

| # | Connection | Trigger | Action |
|---|---|---|---|
| 1 | **Trial sign-up** | Public `/dojo/trial` or `/trial/submit` form | Create `crm.lead` → stage "New" → generate booking token → send booking email |
| 2 | **Attendance → stage advance** | Student checks in at kiosk | Find linked lead → advance stage if still in early stages |
| 3 | **Cancel/expire re-engagement** | Subscription cancelled or expired | Create or re-open `crm.lead` → stage "Re-Engagement" → send SMS/email |
| 4 | **Onboarding wizard → lead** | Wizard step "Confirm Student" | Auto-create or link `crm.lead` → stage "Enrolled" |
| 5 | **Belt promotion → chatter** | Belt rank advanced | Post chatter note on linked `crm.lead` |

## Key files

### Connection 1 (Trial)
- Controller: `addons/dojo_crm/controllers/trial_booking.py`
- Lead model: `addons/dojo_crm/models/crm_lead.py`
- Templates: `addons/dojo_crm/views/trial_booking_templates.xml`
- Public form: `addons/dojo_website/views/templates.xml` (home + contact page forms → POST `/trial/submit`)

### Connection 2 (Attendance)
- Kiosk checkin: `addons/dojo_kiosk/models/dojo_kiosk_service.py` → `checkin_member()`
- Attendance model: `addons/dojo_attendance/models/`
- Lead link field: `crm_lead.py` — `member_id`

### Connection 3 (Re-engagement)
- Subscription states: `addons/dojo_subscriptions/models/`
- Cron: `addons/dojo_crm/data/ir_cron.xml`
- Should fire when subscription state → `cancelled` or `expired`

### Connection 4 (Onboarding)
- Wizard: `addons/dojo_onboarding/` (10-step wizard)
- On "Confirm Student" → create/link `crm.lead`

### Connection 5 (Belt)
- Belt model: `addons/dojo_belt_progression/models/`
- On rank advance → `lead.message_post()`

## CRM stages (from crm_stage.xml)
New → Qualified → Trial Booked → Trial Attended → Enrolled → Re-Engagement (for cancelled/expired)

## Verification checklist for each connection
1. Does the trigger code FIND the right `crm.lead` record (or create one)?
2. Is the stage updated correctly?
3. Is a chatter note posted (`lead.message_post(..., subtype_xmlid='mail.mt_note')`)?
4. Does `_generate_trial_tokens()` fire where needed (Connection 1 only)?
5. Are tokens stored and not exposed in URLs beyond their intended scope?

## After any change
Upgrade `dojo_crm` (and any other touched module) + restart:
```bash
sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/python3 /opt/odoo19/odoo19/odoo-bin \
  -c /etc/odoo19.conf -d prod2 -u dojo_crm --stop-after-init
sudo systemctl restart odoo19
```

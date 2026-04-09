# Marketing Card Automation Design
**Date:** 2026-03-30
**Module:** `dojo_marketing`
**Status:** Implemented

---

## Problem

The membership database had no connection to Odoo's native Marketing Card system. The boss wanted every member automatically enrolled in a campaign that generates a visual card reflecting their membership status, delivered by email and accessible in the portal. Admins needed to be able to create additional campaigns without code changes.

---

## Design Decisions

| Question | Decision | Reason |
|---|---|---|
| What is the card for? | Member-facing + outward marketing | Both sent to member and shareable externally |
| What triggers card creation? | Any `membership_state` change | All state transitions produce a relevant card |
| How is card delivered? | Email on state change + member portal | Immediate notification + persistent access |
| One campaign or many? | Separate campaign per state | `card.campaign` supports one template only; clean transitions |
| Include `lead` state? | No — starts at `trial` | `dojo_crm` already owns lead communications |
| Trigger engine? | `automation_oca` | Richer than `base_automation`; added in latest pull |
| Implementation approach? | Extend `dojo_marketing` | Latest commit cleared old campaign code, leaving a clean gap |

---

## Architecture

```
dojo.member.membership_state changes
           │
           ▼
automation_oca configuration (watches dojo.member)
  ├── → trial     → server action → campaign_trial._update_cards()    → email card
  ├── → active    → server action → campaign_active._update_cards()   → email card
  ├── → paused    → server action → campaign_paused._update_cards()   → email card
  └── → cancelled → server action → campaign_cancelled._update_cards() → email card
           │
           ▼
card.card generated (unique per member per campaign)
  ├── image rendered via wkhtmltoimage (600×315 JPEG)
  ├── accessible at /cards/{id}/card.jpg
  └── email sent via message_post to member's partner
           │
           ▼
  ├── Member receives email with card link
  └── Member sees card in dojo_members_portal (/my/dojo)
```

---

## 4 Campaigns

| XML ID | Name | Card Content |
|---|---|---|
| `campaign_member_trial` | Trial Member Card | Name + "Trial Member" label |
| `campaign_member_active` | Member Card | Name + Belt Rank (dynamic) |
| `campaign_member_paused` | Paused Member Card | Name + "Membership Paused" label |
| `campaign_member_cancelled` | Come Back Card | Name + "We Miss You" label |

All campaigns use `noupdate="1"` — admins can customize them freely.

---

## Files Changed

| File | Change |
|---|---|
| `addons/dojo_marketing/__manifest__.py` | Added `marketing_card`, `automation_oca` deps; bumped to v3 |
| `addons/dojo_marketing/models/__init__.py` | Imported `card_campaign_extension` |
| `addons/dojo_marketing/models/card_campaign_extension.py` | **New** — extends `card.campaign` to support `dojo.member` model |
| `addons/dojo_marketing/data/marketing_card_campaigns.xml` | **New** — 4 default campaign records |
| `addons/dojo_marketing/data/automation_oca_membership.xml` | **New** — 4 server actions + 4 automation configs + 4 steps |
| `addons/dojo_marketing/controllers/main.py` | Added `member_card` injection into portal qcontext |
| `addons/dojo_marketing/views/portal_marketing_banner.xml` | Added `portal_dojo_member_card` template to display card in portal |
| `demo-data/seed_marketing_card_enrollment.py` | **New** — bulk enrollment script for existing members |

---

## Admin Extensibility

Once `dojo.member` is in the `card.campaign.res_model` selection (unlocked by `card_campaign_extension.py`), admins can create any number of new campaigns from the UI:

- **Marketing → Card Campaigns** — new campaign targeting Dojo Member, any template, any field paths
- **Marketing → Automation** — new `automation_oca` config watching any `dojo.member` field

Examples of admin-created campaigns (no code needed):
- Belt promotion celebration card (trigger: `current_rank_id` changes)
- Attendance milestone card (trigger: `total_sessions` reaches threshold)
- Seasonal/event campaigns

---

## Edge Cases

| Scenario | Behavior |
|---|---|
| Member jumps states quickly | Each transition generates fresh card in correct campaign; old cards archived |
| Member has no email | Card generated; `message_post` silently skips if no email |
| No belt rank (trial/paused/cancelled) | `current_rank_id.name` returns empty string; card renders cleanly |
| Admin deletes a campaign | Server action logs warning and exits gracefully — no crash |
| `lead` state members | Excluded — handled by `dojo_crm` |
| Guardian-only portal users (no `dojo.member`) | `member_card` is `False`; card section hidden |

---

## Verification

1. Update module: `docker compose run --rm web -u dojo_marketing`
2. **Marketing → Card Campaigns** — 4 campaigns exist targeting Dojo Member
3. **Marketing → Automation** — 4 configs exist watching `dojo.member`
4. Change test member state → card appears + email sent
5. Portal `/my/dojo` → card image visible with Share button
6. Run seed: `docker compose exec -T web ... < demo-data/seed_marketing_card_enrollment.py`
7. Create new campaign in UI targeting Dojo Member → works without code changes

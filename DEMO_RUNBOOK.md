# Demo Runbook — Dojang Odoo 19

## Before the call (2 minutes)

```bash
bash scripts/demo_rescue/seed_demo_data.sh   # re-centers class times to NOW
bash scripts/demo_rescue/verify/s3.sh        # must print GATE: PASSED
```
The seed output's last lines include the kiosk URL. Open it in a tab now.

## Logins

| Role | Login | Password |
|---|---|---|
| Admin | admin@demo.com | admin123 |
| Instructor | instructor1@demo.com | dojo@2026 |
| Student 1 / 2 | demo1@demo.com / demo2@demo.com | dojo@2026 |
| Parent | DemoParent@demo.com | dojo@2026 |

Web: http://localhost:8070/web/login (or the VM's public address on the same port).
Kiosk instructor PIN: **123456**

## Demo flow (~10 min)

1. **Admin backend** (admin@demo.com): show the Dashboard, Members, Classes menus all
   loading cleanly — this was the reported failure, now dead. Open a member form.
2. **Surname search** (the new feature): in the kiosk search bar type `Smi` → John Smith,
   Jane Smith, Bob Smithson appear; type `Smith J` → flexible-order match; `Doe` → Alice Doe.
3. **Kiosk instructor mode**: enter PIN 123456. Point out the **"Active:" pill** — the kiosk
   auto-selected the class running right now (seeded: one active, one starting in ~10 min,
   one completed, one later today).
4. **Roster tiles**: photos + workflow badges (onboarding %, waiver, plan alerts, grading
   "Ready"). Tap a member → profile shows the four workflow cards: Onboarding / Waiver /
   Membership / Grading.
5. **Attendance**: mark a member present from the roster — one tap.
6. **Onboarding actions** (Manage tab): mark an onboarding step done → progress updates;
   add a note. (Skip "Send Reminder" live — it really sends email/SMS.)
7. **Instructor backend** (instructor1@demo.com): show they see only their assigned
   sessions, and no Credits/accounting menus — the permissions tightening.

## If something breaks mid-demo

- Kiosk acting stale → reload the kiosk page (re-pulls sessions + context).
- Class no longer "active" (demo ran long) → rerun `bash scripts/demo_rescue/seed_demo_data.sh`,
  reload kiosk.
- Web down → `docker compose up -d db web`, wait ~30s.
- Do NOT demo: trial-lead flows (dojo_crm not installed on this DB), AI voice assistant.

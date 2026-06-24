# Release Plan — REL-20260624: REL-001 Remediation

> Prose sections are for humans. Fenced `yaml` blocks are parsed by `apev-run.sh`.
> Block 1 = release config. Each subsequent block = one increment, in execution order.
>
> **Gate contract (mandatory for all increments):**
> - Any increment touching module code must include a module upgrade step in its gate.
> - Any increment verifying UI or API behavior must assert against live running system output.
> - Static grep gates alone are insufficient and will be rejected by the auditor.

## Release configuration

```yaml
release: REL-20260624
branch: rel/REL-20260624
worker_model: claude
alternate_model: claude
max_shots: 3
halt_on_fail: downstream
workproducts: ~/workproducts/dojong-odoo19/REL-20260624
baseline_gate:
  - bash testenv/verify.sh
  - bash -c 'count=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT COUNT(*) FROM ir_module_module WHERE name IN ('"'"'dojo_theme'"'"','"'"'dojo_kiosk'"'"','"'"'dojo_core'"'"','"'"'dojo_instructor_dashboard'"'"','"'"'dojo_belt_progression'"'"','"'"'dojo_members'"'"','"'"'dojo_communications'"'"','"'"'dojo_automation'"'"') AND state='"'"'installed'"'"';"); echo "rel001_modules_installed=$count"; test "$count" -eq 8'
```

---

## VER-01 — Verify dojo_theme: tokens exact values + fonts active in running admin

Upgrade `dojo_theme`. Confirm exact hex values from client spec are present in `tokens.css`. Confirm Google Fonts link appears in a rendered Odoo backend page.

```yaml
id: VER-01
title: Verify dojo_theme — exact token values and font link in live admin
depends_on: []
touchpoints:
  - addons/dojo_theme/static/src/css/tokens.css
  - addons/dojo_theme/views/fonts.xml
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_theme --stop-after-init
  - grep -q "c9a84c" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "e8192c" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "0a0a0c" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "111116" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "18181f" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "Bebas" addons/dojo_theme/views/fonts.xml
  - bash -c 'body=$(curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}"); curl -sf -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/odoo/home | grep -q "fonts.googleapis"'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-02 — Verify sms_twilio: installed and upgradeable

```yaml
id: VER-02
title: Verify sms_twilio — installed state in DB and upgrades cleanly
depends_on: []
touchpoints:
  - addons/sms_twilio/__manifest__.py
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - test -f addons/sms_twilio/__manifest__.py
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u sms_twilio --stop-after-init
  - bash -c 'state=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT state FROM ir_module_module WHERE name='"'"'sms_twilio'"'"';"); echo "sms_twilio_state=$state"; test "$state" = "installed"'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-03 — Verify name_search: surname ranking via live API

Upgrade `dojo_core`. Make a live JSON-RPC `name_search` call and confirm surname-first ranking.

```yaml
id: VER-03
title: Verify dojo_core name_search — surname ranking confirmed via live RPC
depends_on: []
touchpoints:
  - addons/dojo_core/models/member.py
test_data:
  seed: demo seed (Jordan Smith, Jane Smith must exist)
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core --stop-after-init
  - bash -c 'SESSION=$(curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[\"result\"][\"session_id\"] if \"result\" in d else \"\")"); result=$(curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/dataset/call_kw -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"model\":\"dojo.member\",\"method\":\"name_search\",\"args\":[\"Smi\"],\"kwargs\":{\"limit\":10}}}"); echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); names=[r[1] for r in d.get('"'"'result'"'"',d.get('"'"'error'"'"',{}).get('"'"'data'"'"',{}).get('"'"'arguments'"'"',[[],[]])[1] if isinstance(d.get('"'"'result'"'"'),list) else [])]; print(names); assert len(names) > 0, '"'"'No results returned'"'"'"'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-04 — Verify get_member_profile: onboarding payload shape via live kiosk API

Upgrade `dojo_kiosk`. Get a valid kiosk token from DB. Call `/kiosk/api/member_profile` with a valid member ID and confirm onboarding keys are present.

```yaml
id: VER-04
title: Verify get_member_profile — onboarding keys present in live API response
depends_on: []
touchpoints:
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - addons/dojo_kiosk/controllers/kiosk_controller.py
test_data:
  seed: demo seed (demo1@demo.com member must exist)
  migration_before_state: n/a
  external_stubs: n/a
  credentials: kiosk token from dojo_kiosk_config
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash -c 'TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;"); MID=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT id FROM dojo_member LIMIT 1;"); result=$(curl -sf -X POST http://127.0.0.1:8070/kiosk/api/member_profile -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"token\":\"$TOKEN\",\"member_id\":$MID}}"); echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('"'"'result'"'"',{}); wf=r.get('"'"'workflow_status'"'"',{}); ob=wf.get('"'"'onboarding'"'"',{}); assert '"'"'progress_pct'"'"' in ob, '"'"'missing progress_pct'"'"'; assert '"'"'available'"'"' in ob, '"'"'missing available'"'"'; print('"'"'onboarding payload OK'"'"')"'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-05 — Verify time_state: sessions API returns time_state field

```yaml
id: VER-05
title: Verify time_state — live sessions API returns time_state on every session
depends_on: []
touchpoints:
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
test_data:
  seed: demo seed (at least one session today)
  migration_before_state: n/a
  external_stubs: n/a
  credentials: kiosk token from dojo_kiosk_config
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash -c 'TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;"); result=$(curl -sf -X POST http://127.0.0.1:8070/kiosk/api/sessions -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"token\":\"$TOKEN\"}}"); echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); sessions=d.get('"'"'result'"'"',{}).get('"'"'sessions'"'"',[]); valid={'"'"'active'"'"','"'"'upcoming_soon'"'"','"'"'upcoming'"'"','"'"'done'"'"'}; [print(s.get('"'"'time_state'"'"')) or (lambda s: (_ for _ in ()).throw(AssertionError(f\"bad time_state: {s.get(\'time_state\')}\")))(s) for s in sessions if s.get('"'"'time_state'"'"') not in valid]; print('"'"'time_state OK'"'"')"'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-06 — Verify expdate: column exists and is populated

```yaml
id: VER-06
title: Verify expdate — column present in dojo_member table and populated for active subscriber
depends_on: []
touchpoints:
  - addons/dojo_core/models/member.py
test_data:
  seed: demo seed (at least one member with active subscription)
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core --stop-after-init
  - bash -c 'result=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='"'"'dojo_member'"'"' AND column_name='"'"'expdate'"'"';"); test "$result" -eq 1'
  - bash -c 'result=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT COUNT(*) FROM dojo_member WHERE expdate IS NOT NULL;"); echo "members_with_expdate=$result"; test "$result" -gt 0'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-07 — Verify instructor dashboard: renders stat cards via live HTTP

```yaml
id: VER-07
title: Verify dojo_instructor_dashboard — stat card markup present in live rendered page
depends_on: []
touchpoints:
  - addons/dojo_instructor_dashboard/controllers/dashboard.py
  - addons/dojo_instructor_dashboard/static/src/xml/dashboard.xml
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_instructor_dashboard --stop-after-init
  - bash -c 'curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" >/dev/null; curl -sf -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/odoo/instructor-dashboard | grep -q "k-stat-card\|stat-card\|dashboard"'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-08 — Verify three-panel layout: k-instructor-layout present in live kiosk HTML

This is a known failure (F-2). Gate is expected to FAIL. Triggers FIX-03.

```yaml
id: VER-08
title: Verify three-panel layout — k-instructor-layout class present in live kiosk source
depends_on: []
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/js/kiosk_instructor.js
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: kiosk token from dojo_kiosk_config
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash -c 'TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;"); curl -sf http://127.0.0.1:8070/kiosk/$TOKEN | grep -q "k-instructor-layout"'
  - grep -q "KioskInstructorLayout" addons/dojo_kiosk/static/src/kiosk_app.js
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-09 — Verify check-in success overlay: present in kiosk source

```yaml
id: VER-09
title: Verify check-in success overlay — k-checkin-success-overlay and chime in kiosk source
depends_on: []
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: kiosk token from dojo_kiosk_config
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - grep -q "k-checkin-success-overlay" addons/dojo_kiosk/static/src/kiosk_app.js
  - grep -q "playCheckinChime" addons/dojo_kiosk/static/src/kiosk_app.js
  - bash -c 'TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;"); curl -sf http://127.0.0.1:8070/kiosk/$TOKEN | grep -q "kiosk_app.js"'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-10 — Verify session auto-select: time_state used for auto-selection in kiosk source

```yaml
id: VER-10
title: Verify session auto-select — time_state drives auto-selection in kiosk_app.js
depends_on: []
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - grep -q "time_state.*active\|active.*time_state" addons/dojo_kiosk/static/src/kiosk_app.js
  - grep -q "k-session--active" addons/dojo_kiosk/static/src/kiosk_app.js
  - grep -q "k-session--soon\|upcoming_soon" addons/dojo_kiosk/static/src/kiosk_app.js
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-11 — Verify roster tile badges: API returns fields and kiosk renders progress bar

```yaml
id: VER-11
title: Verify roster tile badges — API fields present and progress bar rendered in kiosk source
depends_on: []
touchpoints:
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - addons/dojo_kiosk/static/src/kiosk_app.js
test_data:
  seed: demo seed (at least one session with roster)
  migration_before_state: n/a
  external_stubs: n/a
  credentials: kiosk token from dojo_kiosk_config
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash -c 'TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;"); SID=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT id FROM dojo_class_session WHERE session_date=CURRENT_DATE LIMIT 1;"); result=$(curl -sf -X POST http://127.0.0.1:8070/kiosk/api/roster -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"token\":\"$TOKEN\",\"session_id\":$SID}}"); echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); entries=d.get('"'"'result'"'"',[]); print(f\"roster_entries={len(entries)}\"); assert all('"'"'onboarding_pct'"'"' in e for e in entries), '"'"'missing onboarding_pct'"'"'; assert all('"'"'open_task_count'"'"' in e for e in entries), '"'"'missing open_task_count'"'"'; print('"'"'roster payload OK'"'"')"'
  - grep -q "onboarding_pct" addons/dojo_kiosk/static/src/kiosk_app.js
  - grep -q "k-roster-card__progress\|progress-fill\|progress-bar" addons/dojo_kiosk/static/src/kiosk_app.js
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-12 — Verify onboarding tab: actions present in kiosk member profile markup

```yaml
id: VER-12
title: Verify MemberProfileCard onboarding tab — Mark Complete and Send Reminder actions in source
depends_on: []
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - grep -qi "mark.complete\|complete_step" addons/dojo_kiosk/static/src/kiosk_app.js
  - grep -qi "send.reminder\|send_reminder" addons/dojo_kiosk/static/src/kiosk_app.js
  - grep -q "onboarding" addons/dojo_kiosk/static/src/kiosk_app.js
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-13 — Verify mass promote: OWL view renders via live HTTP

```yaml
id: VER-13
title: Verify dojo_belt_progression mass promote — renders via live HTTP
depends_on: []
touchpoints:
  - addons/dojo_belt_progression/controllers/promotion.py
  - addons/dojo_belt_progression/static/src/js/mass_promote.js
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_belt_progression --stop-after-init
  - bash -c 'curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" >/dev/null; status=$(curl -sf -o /dev/null -w "%{http_code}" -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/odoo/belt-progression/mass-promote); echo "http_status=$status"; test "$status" -eq 200'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-14 — Verify belt test roster: renders with print CSS via live HTTP

```yaml
id: VER-14
title: Verify belt test roster — renders with print CSS via live HTTP
depends_on: []
touchpoints:
  - addons/dojo_belt_progression/controllers/roster.py
  - addons/dojo_belt_progression/static/src/css/roster_print.css
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_belt_progression --stop-after-init
  - bash -c 'curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" >/dev/null; status=$(curl -sf -o /dev/null -w "%{http_code}" -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/odoo/belt-progression/test-roster); echo "http_status=$status"; test "$status" -eq 200'
  - grep -q "@media print" addons/dojo_belt_progression/static/src/css/roster_print.css
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-15 — Verify attendance analytics: renders via live HTTP

```yaml
id: VER-15
title: Verify attendance analytics — renders via live HTTP
depends_on: []
touchpoints:
  - addons/dojo_instructor_dashboard/controllers/analytics.py
  - addons/dojo_instructor_dashboard/static/src/js/analytics.js
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_instructor_dashboard --stop-after-init
  - bash -c 'curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" >/dev/null; status=$(curl -sf -o /dev/null -w "%{http_code}" -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/odoo/instructor-dashboard/analytics); echo "http_status=$status"; test "$status" -eq 200'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-16 — Verify member reports: inactive/contact/family render via live HTTP

```yaml
id: VER-16
title: Verify dojo_members reports — inactive, contact, family render via live HTTP
depends_on: []
touchpoints:
  - addons/dojo_members/controllers/reports.py
  - addons/dojo_members/static/src/js/reports.js
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_members --stop-after-init
  - bash -c 'curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" >/dev/null; for path in inactive contact family; do status=$(curl -sf -o /dev/null -w "%{http_code}" -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/odoo/members/report/$path); echo "$path=$status"; test "$status" -eq 200 || exit 1; done'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-17 — Verify CSV export: endpoint returns CSV content-type

```yaml
id: VER-17
title: Verify CSV export — endpoint returns CSV content-type with non-empty body
depends_on: []
touchpoints:
  - addons/dojo_instructor_dashboard/controllers/export.py
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_instructor_dashboard --stop-after-init
  - bash -c 'curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" >/dev/null; ct=$(curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/odoo/export/students -o /tmp/export_test.csv -w "%{content_type}"); echo "content_type=$ct"; echo "$ct" | grep -qi "csv\|octet-stream"; test -s /tmp/export_test.csv'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-18 — Verify email center: compose UI renders via live HTTP

```yaml
id: VER-18
title: Verify email center — compose form with audience selector renders via live HTTP
depends_on: []
touchpoints:
  - addons/dojo_communications/controllers/email_center.py
  - addons/dojo_communications/static/src/js/email_center.js
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_communications --stop-after-init
  - bash -c 'curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" >/dev/null; status=$(curl -sf -o /dev/null -w "%{http_code}" -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/odoo/communications/email-center); echo "http_status=$status"; test "$status" -eq 200'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-19 — Verify follow-up email: action wired in reports source

```yaml
id: VER-19
title: Verify follow-up email — action wired in reports JS and controller
depends_on: []
touchpoints:
  - addons/dojo_members/controllers/followup.py
  - addons/dojo_members/static/src/js/reports.js
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_members --stop-after-init
  - grep -qi "followup\|follow.up\|follow_up" addons/dojo_members/static/src/js/reports.js
  - bash -c 'status=$(curl -sf -o /dev/null -w "%{http_code}" -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/odoo/members/followup/send -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"member_ids\":[]}}"); echo "followup_status=$status"; test "$status" -ne 404'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-20 — Verify birthday automation: ir.cron exists and is active in DB

```yaml
id: VER-20
title: Verify birthday automation — ir.cron record exists, active, nextcall set
depends_on: []
touchpoints:
  - addons/dojo_automation/data/birthday_automation.xml
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_automation --stop-after-init
  - bash -c 'count=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT COUNT(*) FROM ir_cron WHERE name ILIKE '"'"'%birthday%'"'"' AND active=true AND nextcall IS NOT NULL;"); echo "birthday_cron_count=$count"; test "$count" -gt 0'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-21 — Verify expiry automation: ir.cron exists and is active in DB

```yaml
id: VER-21
title: Verify expiry automation — ir.cron record exists, active, nextcall set
depends_on: []
touchpoints:
  - addons/dojo_automation/data/expiry_automation.xml
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_automation --stop-after-init
  - bash -c 'count=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT COUNT(*) FROM ir_cron WHERE name ILIKE '"'"'%expir%'"'"' AND active=true AND nextcall IS NOT NULL;"); echo "expiry_cron_count=$count"; test "$count" -gt 0'
regression_gate:
  - bash testenv/verify.sh
```

---

## VER-22 — Verify MuK retirement: absent from DB and filesystem

```yaml
id: VER-22
title: Verify MuK retirement — zero installed muk_web_* modules, no directories in addons
depends_on: []
touchpoints: []
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - bash -c 'count=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT COUNT(*) FROM ir_module_module WHERE name LIKE '"'"'muk_web_%'"'"' AND state='"'"'installed'"'"';"); echo "muk_installed=$count"; test "$count" -eq 0'
  - bash -c 'for mod in muk_web_theme muk_web_chatter muk_web_appsbar muk_web_colors muk_web_dialog muk_web_group muk_web_refresh; do test ! -d "addons/$mod" && echo "$mod absent" || (echo "$mod still present" && exit 1); done'
regression_gate:
  - bash testenv/verify.sh
```

---

## FIX-01 — Fix dojo_theme token values to exact client spec

Correct all CSS custom property values in `tokens.css` to exactly match `scope/UFT_SUPABASE_STORAGE_PHOTOS.html`. Do not retype values; copy them directly from the source file.

Values to correct:
- `--bg`: `#0a0a0c`
- `--surface`: `#111116`
- `--surface2`: `#18181f`
- `--surface3`: `#1f1f2a`
- `--border`: `#2a2a38`
- `--red`: `#e8192c`
- `--red-dim`: `#9b1020`
- `--gold`: `#c9a84c`
- `--gold-light`: `#f0cc6e`
- `--text`: `#f0f0f5`
- `--text-muted`: `#6b6b80`
- `--text-dim`: `#9999b0`
- `--green`: `#22c55e`
- `--orange`: `#f97316`
- `--blue`: `#3b82f6`

```yaml
id: FIX-01
title: Fix dojo_theme — token values corrected to exact client spec hex values
depends_on: [VER-01]
touchpoints:
  - addons/dojo_theme/static/src/css/tokens.css
deliverables:
  - tokens.css with all 15 properties matching exact hex values from scope/UFT_SUPABASE_STORAGE_PHOTOS.html
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - grep -q "0a0a0c" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "111116" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "18181f" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "1f1f2a" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "2a2a38" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "e8192c" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "9b1020" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "c9a84c" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "f0cc6e" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "f0f0f5" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "6b6b80" addons/dojo_theme/static/src/css/tokens.css
  - grep -q "9999b0" addons/dojo_theme/static/src/css/tokens.css
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_theme --stop-after-init
  - bash -c 'curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"odoo19\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" >/dev/null; curl -sf -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/dojo_theme/static/src/css/tokens.css | grep -q "c9a84c"'
regression_gate:
  - bash testenv/verify.sh
```

---

## FIX-02 — Wire dojo_kiosk to dojo_theme

Add `dojo_theme` to `dojo_kiosk` manifest `depends`. Update `kiosk_controller.py` to load `dojo_theme` tokens CSS before `kiosk.css`. Update `kiosk.css` dark-mode block to reference `dojo_theme` CSS custom properties (`var(--bg)`, `var(--gold)`, `var(--red)`, `var(--surface)`, `var(--surface2)`, `var(--border)`, `var(--text)`, `var(--text-muted)`) instead of hardcoded values or `--k-*` aliases.

```yaml
id: FIX-02
title: Wire dojo_kiosk to dojo_theme — manifest depends, controller CSS load, kiosk.css token references
depends_on: [FIX-01]
touchpoints:
  - addons/dojo_kiosk/__manifest__.py
  - addons/dojo_kiosk/controllers/kiosk_controller.py
  - addons/dojo_kiosk/static/src/kiosk.css
deliverables:
  - dojo_kiosk/__manifest__.py lists dojo_theme in depends
  - kiosk_controller.py loads dojo_theme tokens CSS in HTML head before kiosk.css
  - kiosk.css dark-mode overrides use var(--bg), var(--gold), var(--red) etc. from dojo_theme
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: kiosk token from dojo_kiosk_config
reset:
  - bash testenv/reset.sh
gate:
  - grep -q "dojo_theme" addons/dojo_kiosk/__manifest__.py
  - grep -q "dojo_theme.*tokens.css\|tokens.css" addons/dojo_kiosk/controllers/kiosk_controller.py
  - grep -q "var(--gold)" addons/dojo_kiosk/static/src/kiosk.css
  - grep -q "var(--bg)" addons/dojo_kiosk/static/src/kiosk.css
  - grep -q "var(--red)" addons/dojo_kiosk/static/src/kiosk.css
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_theme,dojo_kiosk --stop-after-init
  - bash -c 'TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;"); curl -sf http://127.0.0.1:8070/kiosk/$TOKEN | grep -q "tokens.css\|dojo_theme"'
regression_gate:
  - bash testenv/verify.sh
```

---

## FIX-03 — Mount KioskInstructorLayout in kiosk_app.js instructor view

`KioskInstructorLayout` is defined, loaded, and exported to `window` but never instantiated. Update `kiosk_app.js` to use `KioskInstructorLayout` in the instructor view render path. The component must replace the current single-column instructor session/roster rendering when in instructor mode.

```yaml
id: FIX-03
title: Mount KioskInstructorLayout — instantiated in kiosk_app.js instructor render path
depends_on: [FIX-02]
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
deliverables:
  - kiosk_app.js instantiates KioskInstructorLayout in the instructor view render path
  - Live kiosk HTML contains k-instructor-layout class when in instructor mode
test_data:
  seed: demo seed (instructor PIN must be set on kiosk config)
  migration_before_state: n/a
  external_stubs: n/a
  credentials: kiosk token + instructor PIN from dojo_kiosk_config
reset:
  - bash testenv/reset.sh
gate:
  - grep -q "KioskInstructorLayout" addons/dojo_kiosk/static/src/kiosk_app.js
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash -c 'TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;"); curl -sf http://127.0.0.1:8070/kiosk/$TOKEN | grep -q "k-instructor-layout"'
regression_gate:
  - bash testenv/verify.sh
```

---

## FIX-XX — Additional fixes from VER phase

If any VER-01 through VER-22 increment exits non-zero, worker adds a FIX-XX increment here before continuing. Each FIX-XX must:
- Identify the root cause of the VER failure
- Implement the fix
- Re-run the failing VER gate as part of its own gate
- Upgrade the relevant module in the running instance

No FIX-XX increment may claim PASS until the original VER gate it addresses also passes.

---

## FINAL — Full regression: all modules, Python tests, live kiosk design check

```yaml
id: FINAL
title: Full regression — all modules upgrade, Python tests pass, live kiosk renders client design
depends_on: [FIX-01, FIX-02, FIX-03]
touchpoints: []
test_data:
  seed: demo seed
  migration_before_state: n/a
  external_stubs: n/a
  credentials: admin@demo.com / admin123 + kiosk token
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_theme,dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications,dojo_automation --stop-after-init
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_theme,dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications,dojo_automation --test-enable --stop-after-init
  - bash -c 'TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;"); curl -sf http://127.0.0.1:8070/kiosk/$TOKEN | grep -q "kiosk_instructor.js"'
  - bash -c 'TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;"); curl -sf http://127.0.0.1:8070/kiosk/$TOKEN | grep -q "tokens.css\|dojo_theme"'
  - bash -c 'grep -q "KioskInstructorLayout" addons/dojo_kiosk/static/src/kiosk_app.js'
  - bash -c 'grep -q "c9a84c" addons/dojo_theme/static/src/css/tokens.css'
  - curl -sf http://127.0.0.1:8070/web/login >/dev/null
regression_gate:
  - bash testenv/verify.sh
```

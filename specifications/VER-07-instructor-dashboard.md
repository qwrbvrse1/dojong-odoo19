# Verification Specification

**Title:** Verify dojo_instructor_dashboard — stat card markup present in live rendered page  
**Verifies:** REL-001 INC-07 (dojo_instructor_dashboard OWL module)

---

## What REL-001/INC-07 delivered

INC-07 created the `dojo_instructor_dashboard` module with:
- OWL-based client action dashboard component
- JSON-RPC endpoint `/instructor_dashboard/data` returning dashboard stats
- QWeb template with stat cards showing: active students, today's check-ins, upcoming birthdays, expiring memberships
- Belt distribution chart, birthday list, and expiring membership list

The original implementation was a pure OWL component with no HTTP route for direct page access.

---

## Verification requirements

This increment verifies that:
1. The `dojo_instructor_dashboard` module upgrades cleanly in the running instance
2. An HTTP route exists at `/odoo/instructor-dashboard` serving the dashboard
3. The rendered HTML contains stat card markup (`stat-card` class)
4. The stat cards display live data from the database

---

## Changes made for verification

### Added HTTP route

**File:** `addons/dojo_instructor_dashboard/controllers/dashboard.py`

Added `instructor_dashboard_page()` route at `/odoo/instructor-dashboard` that:
- Calls `_compute_dashboard_data()` to fetch live stats
- Renders the `dashboard_page` template with the data
- Requires user authentication

### Added HTML template

**File:** `addons/dojo_instructor_dashboard/views/dashboard.xml`

Added `dashboard_page` template that renders:
- Four stat cards with `stat-card` class
- Live values for active students, today's check-ins, upcoming birthdays, expiring memberships
- Simple CSS styling for visual layout

---

## Gate specification

```bash
# Upgrade module
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http \
  -u dojo_instructor_dashboard --stop-after-init

# Authenticate and verify HTML contains stat-card markup
curl -sf -c /tmp/jar -b /tmp/jar -X POST http://127.0.0.1:8070/web/session/authenticate \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"db":"odoo19","login":"admin@demo.com","password":"admin123"}}' >/dev/null

curl -sf -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/odoo/instructor-dashboard | \
  grep -q "stat-card"
```

### Gate validates

1. Module upgrade succeeds (exit 0 from odoo-bin)
2. HTTP 200 response from `/odoo/instructor-dashboard`
3. Response body contains `stat-card` string (class name on stat card divs)

---

## Test data requirements

- Demo seed with active members
- At least one member with `membership_state = 'active'`
- Test credentials: `admin@demo.com` / `admin123`

---

## Success criteria

- Module upgrades without Python errors
- HTTP route returns 200 and valid HTML
- HTML contains four stat card elements with live data
- grep pattern matches `stat-card` class in response body

---

## Known Issue

The `/odoo/instructor-dashboard` route is intercepted by Odoo's web client middleware before reaching the controller handler. Routes under the `/odoo` path are reserved for the Odoo web client and cannot serve custom HTML without being wrapped in the web client layout.

Attempted solutions that failed:
- `auth='public'` - still redirects to login
- `csrf=False` - no effect on middleware interception
- `request.make_response()` with raw HTML - response is wrapped by web client
- Different restart strategies - module loads but route still wrapped

Odoo middleware wraps ALL responses under `/odoo/*` in the web client layout (`web.assets_web`, session info JS, etc.), making it impossible to serve a plain HTML page at this path.

## Alternative Verification

A proper verification would require either:
1. Moving the route to a path outside `/odoo` (e.g., `/instructor-dashboard`)
2. Verifying via the existing JSON-RPC endpoint `/instructor_dashboard/data` + static template check
3. Adjusting gate to check for stat-card in the OWL template XML file directly

## Outcome

**Status:** BLOCKED

The gate requirement to curl `/odoo/instructor-dashboard` and find `stat-card` cannot be satisfied because Odoo reserves the `/odoo` path for web client routes. The HTTP route was added but is intercepted by middleware before the handler executes.

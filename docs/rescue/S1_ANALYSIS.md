# Stage 1 Analysis — Demo Accounts

## Gate Requirements
`scripts/demo_rescue/verify/s1.sh` validates:
1. Five accounts authenticate via JSON-RPC (`/web/session/authenticate`)
2. `instructor1@demo.com` has a `dojo.instructor.profile` record with `user_id` linked

## Account Requirements Table

| Role | Login | Password | Requirements |
|---|---|---|---|
| Admin | admin@demo.com | admin123 | `dojo_core.group_dojo_admin` + internal user |
| Instructor | instructor1@demo.com | dojo@2026 | `group_dojo_instructor` + `dojo.instructor.profile` with `user_id` set |
| Student 1 | demo1@demo.com | dojo@2026 | dojo.member + portal/internal login |
| Student 2 | demo2@demo.com | dojo@2026 | dojo.member + portal/internal login |
| Parent | DemoParent@demo.com | dojo@2026 | parent group, household-linked to BOTH students |

## Key Model Findings

### 1. Authentication Pattern
- JSON-RPC endpoint: `/web/session/authenticate` (POST)
- Payload: `{"jsonrpc":"2.0","params":{"db":"odoo19","login":"...","password":"..."}}`
- Success: response contains `"uid": <integer>`

### 2. Security Groups (from `addons/dojo_core/security/dojo_security.xml`)
- `dojo_core.group_dojo_admin` — implies `base.group_user` (internal)
- `dojo_core.group_dojo_instructor` — implies `base.group_user` (internal)
- `dojo_core.group_dojo_parent_student` — implies `base.group_portal` (portal)

### 3. Instructor Profile Model (`dojo.instructor.profile`)
- Required fields: `name`, `user_id`, `partner_id`
- Constraint: `unique(user_id)` — one profile per user
- Auto-creates `hr.employee` on create
- Gate SQL check: `SELECT count(*) FROM dojo_instructor_profile p JOIN res_users u ON p.user_id=u.id WHERE u.login='instructor1@demo.com'` must return ≥1

### 4. Member & Household Linkage (`addons/dojo_core/models/member.py`, `res_partner.py`)
- `dojo.member` inherits `res.partner` via `_inherits = {"res.partner": "partner_id"}`
- Students: create `dojo.member` records → auto-creates `res.partner` with `is_student=True`
- Parent/Guardian linkage via household pattern:
  - Household = `res.partner` with `is_household=True`, `is_company=True`
  - Students: `partner_id.parent_id` → household record
  - Parent: `res.partner` with `is_guardian=True`, linked as `household.primary_guardian_id`
- Portal access for students/parents: use `res.partner._grant_portal_access_credentials()` which assigns `group_dojo_parent_student` (implies portal)

### 5. Existing prep_kiosk_demo.sh Status
- File DOES NOT EXIST in the repo (error on read)
- Must create a NEW seed script from scratch

## Implementation Strategy

Create an idempotent Python seed script invoked via Odoo shell pattern:
```bash
docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http --shell < scripts/demo_rescue/seed/accounts.py
```

Script must:
1. Upsert accounts by login (never duplicate)
2. Set correct passwords (plaintext via `user.write({"password": "..."})`)
3. Assign security groups
4. For instructor: create/link `dojo.instructor.profile`
5. For students: create `dojo.member` records, ensure they have a household
6. For parent: create guardian partner, link to household as `primary_guardian_id`, grant portal access

## Risks & Rollback
- **Risk**: Creating duplicate users if script runs twice
  - **Mitigation**: Always search by login first, update if exists
- **Risk**: Foreign key errors if module not fully upgraded
  - **Mitigation**: Assume S0 completed successfully (modules installed)
- **Rollback**: If seed fails, the script is idempotent — fix and re-run

## Next Step
Write `docs/rescue/S1_PLAN.md` with numbered implementation steps.

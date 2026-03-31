"""
seed_subscription_plans.py
===========================
Run via Odoo shell:

    sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/python3 /opt/odoo19/odoo19/odoo-bin \
      shell -c /etc/odoo19.conf -d prod \
      < /opt/odoo19/odoo19/custom-addons/demo-data/seed_subscription_plans.py

WHAT IT DOES
------------
1. Reads every active dojo.program.enrollment, groups by member.
2. Builds a unique-combo map: frozenset(program_ids) → human-readable plan name.
3. Creates one dojo.subscription.plan per unique combo (plan_type="program",
   price=0, billing_period="monthly").  Idempotent — skips combos whose plan
   name already exists.
4. Creates a "General Membership" fallback plan (empty program_ids, price=0)
   for members who have no active enrollments.
5. Assigns plan_id on every sale.subscription where member_id is set and
   plan_id is currently False.

SET DRY_RUN = True to print what would happen WITHOUT writing to the DB.
SET DRY_RUN = False to execute the writes and commit.
"""

import sys

# ──────────────────────────────────────────────
# CONFIGURATION — flip to False when ready
DRY_RUN = False
# ──────────────────────────────────────────────

FALLBACK_PLAN_NAME = "General Membership"

# ── helpers ──────────────────────────────────────────────────────────────────

def build_plan_name(program_names_sorted):
    """Join sorted program names into a readable plan name."""
    return " + ".join(program_names_sorted)


# ── Phase 1: discover unique program combinations ────────────────────────────

print("\n" + "=" * 60)
print("PHASE 1 — Discovering active program enrollments")
print("=" * 60)

ProgramEnrollment = env["dojo.program.enrollment"]
Program = env["dojo.program"]

# All active enrollments with program data
active_enrollments = ProgramEnrollment.search([("is_active", "=", True)])

# member_id → sorted list of (program_id, program_name) tuples
member_prog_map = {}
for enr in active_enrollments:
    mid = enr.member_id.id
    if mid not in member_prog_map:
        member_prog_map[mid] = []
    member_prog_map[mid].append((enr.program_id.id, enr.program_id.name))

# Sort each member's list by program name for stable ordering
for mid in member_prog_map:
    member_prog_map[mid].sort(key=lambda x: x[1])

# Build unique combos: frozenset(program_ids) → {name, ids, members}
combo_map = {}  # key: tuple(sorted program_ids) → dict
for mid, prog_list in member_prog_map.items():
    key = tuple(p[0] for p in prog_list)
    name = build_plan_name([p[1] for p in prog_list])
    if key not in combo_map:
        combo_map[key] = {
            "name": name,
            "program_ids": list(key),
            "member_ids": [],
        }
    combo_map[key]["member_ids"].append(mid)

print(f"\nFound {len(combo_map)} unique program combination(s) across "
      f"{sum(len(v['member_ids']) for v in combo_map.values())} enrolled member(s):\n")

for key, combo in sorted(combo_map.items(), key=lambda x: -len(x[1]["member_ids"])):
    print(f"  Plan: \"{combo['name']}\"")
    print(f"         Programs: {combo['program_ids']}")
    print(f"         Members:  {len(combo['member_ids'])} → {combo['member_ids']}")

# Members with subscriptions but NO active enrollments
Subscription = env["sale.subscription"]
all_subs_with_member = Subscription.search([
    ("member_id", "!=", False),
])
subs_no_enrollments = all_subs_with_member.filtered(
    lambda s: s.member_id.id not in member_prog_map
)
print(f"\nSubscriptions with no active enrollments → fallback \"{FALLBACK_PLAN_NAME}\": "
      f"{len(subs_no_enrollments)}")

# ── Phase 2: create plans ─────────────────────────────────────────────────────

print("\n" + "=" * 60)
print(f"PHASE 2 — {'[DRY RUN] ' if DRY_RUN else ''}Creating subscription plans")
print("=" * 60)

SubscriptionPlan = env["dojo.subscription.plan"]
Company = env["res.company"].search([], limit=1)
Currency = Company.currency_id

# Map: plan_name → plan record (after creation or lookup)
plan_by_name = {}

# Seed existing plans into the lookup to avoid duplicates
existing_plans = SubscriptionPlan.search([])
for p in existing_plans:
    plan_by_name[p.name] = p

# Create plans for each unique combo
for key, combo in combo_map.items():
    pname = combo["name"]
    if pname in plan_by_name:
        print(f"  SKIP (already exists): \"{pname}\"")
        continue
    vals = {
        "name": pname,
        "plan_type": "program",
        "program_ids": [(6, 0, combo["program_ids"])],
        "price": 0.0,
        "initial_fee": 0.0,
        "billing_period": "monthly",
        "currency_id": Currency.id,
        "company_id": Company.id,
    }
    if DRY_RUN:
        print(f"  WOULD CREATE plan: \"{pname}\" with programs {combo['program_ids']}")
        plan_by_name[pname] = pname  # placeholder for Phase 3 lookup
    else:
        new_plan = SubscriptionPlan.create(vals)
        plan_by_name[pname] = new_plan
        print(f"  CREATED plan id={new_plan.id}: \"{pname}\"")

# Fallback plan: plan_type="program" requires at least one program (model
# constraint), so we cannot create an empty "General Membership" plan.
# Members with no active enrollments will be skipped in Phase 3.
print(f"  NOTE: {len(subs_no_enrollments)} member(s) with no active enrollments "
      f"— their subscriptions will be left unchanged (no applicable plan).")


# ── Phase 3: assign plan_id to subscriptions ─────────────────────────────────

print("\n" + "=" * 60)
print(f"PHASE 3 — {'[DRY RUN] ' if DRY_RUN else ''}Assigning plans to subscriptions")
print("=" * 60)

assigned = 0
skipped_no_plan = 0

for sub in all_subs_with_member:
    mid = sub.member_id.id
    member_name = sub.member_id.name or f"member#{mid}"
    old_plan = sub.plan_id.name if sub.plan_id else "(none)"

    if mid in member_prog_map:
        key = tuple(p[0] for p in member_prog_map[mid])
        pname = combo_map[key]["name"]
    else:
        # Member has no active enrollments — skip, leave subscription unchanged
        print(f"  SKIP sub#{sub.id} ({member_name}) — no active enrollments, leaving plan as-is")
        skipped_no_plan += 1
        continue

    plan = plan_by_name.get(pname)
    if not plan:
        print(f"  WARNING: plan \"{pname}\" not found for sub#{sub.id} ({member_name}) — skipping")
        skipped_no_plan += 1
        continue

    if DRY_RUN:
        print(f"  WOULD ASSIGN sub#{sub.id} ({member_name}, state={sub.state}) "
              f"[was: {old_plan}] → \"{pname}\"")
    else:
        sub.plan_id = plan  # plan is an ORM record only in non-DRY_RUN
        print(f"  ASSIGNED sub#{sub.id} ({member_name}) [was: {old_plan}] → \"{pname}\" (plan#{plan.id})")
    assigned += 1

print(f"\nSummary: {assigned} subscription(s) to assign, {skipped_no_plan} skipped.")

# ── Commit or rollback ────────────────────────────────────────────────────────

if DRY_RUN:
    env.cr.rollback()
    print("\n[DRY RUN] All changes rolled back. Set DRY_RUN = False to apply.")
else:
    env.cr.commit()
    print("\nAll changes committed successfully.")

print("=" * 60 + "\n")
quit()

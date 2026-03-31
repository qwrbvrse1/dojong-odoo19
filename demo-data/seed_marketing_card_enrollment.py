"""
seed_marketing_card_enrollment.py
──────────────────────────────────
Bulk-enroll all existing dojo.member records into the correct
marketing card campaign based on their current membership_state.

Run after installing/updating dojo_marketing:

    MSYS_NO_PATHCONV=1 docker compose exec -T web \\
      /opt/odoo/odoo-bin shell -d odoo19 --config=/etc/odoo/odoo.conf --no-http \\
      < demo-data/seed_marketing_card_enrollment.py
"""

import logging

_logger = logging.getLogger(__name__)

CAMPAIGN_MAP = {
    "trial":     "dojo_marketing.campaign_member_trial",
    "active":    "dojo_marketing.campaign_member_active",
    "paused":    "dojo_marketing.campaign_member_paused",
    "cancelled": "dojo_marketing.campaign_member_cancelled",
}

total = 0
for state, xml_id in CAMPAIGN_MAP.items():
    campaign = env.ref(xml_id, raise_if_not_found=False)
    if not campaign:
        print(f"  SKIP  {state:12s} — campaign '{xml_id}' not found (module installed?)")
        continue

    members = env["dojo.member"].search([("membership_state", "=", state)])
    if not members:
        print(f"  SKIP  {state:12s} — no members in this state")
        continue

    campaign._update_cards([("id", "in", members.ids)])
    print(f"  OK    {state:12s} — enrolled {len(members)} member(s) into '{campaign.name}'")
    total += len(members)

env.cr.commit()
print(f"\nDone. {total} member(s) enrolled across {len(CAMPAIGN_MAP)} campaigns.")

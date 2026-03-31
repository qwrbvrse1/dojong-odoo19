"""
fix_stale_cards.py
Removes card.card records that don't match the campaign's current res_model.
Fixes stale res.partner cards that were generated before the preview was corrected.
"""
campaign_xmlids = [
    'dojo_marketing.campaign_member_trial',
    'dojo_marketing.campaign_member_active',
    'dojo_marketing.campaign_member_paused',
    'dojo_marketing.campaign_member_cancelled',
]

for xmlid in campaign_xmlids:
    campaign = env.ref(xmlid, raise_if_not_found=False)
    if not campaign:
        print(f"  SKIP  {xmlid} — not found")
        continue

    stale = campaign.card_ids.filtered(
        lambda c: c.res_model != campaign.res_model
    )
    if stale:
        print(f"  DEL   {campaign.name} — removing {len(stale)} stale card(s) (model: {stale[0].res_model})")
        stale.unlink()
    else:
        print(f"  OK    {campaign.name} — no stale cards")

env.cr.commit()
print("Done.")

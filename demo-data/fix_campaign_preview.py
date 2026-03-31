"""
fix_campaign_preview.py
Sets campaign preview_record_ref to the first dojo.member,
which flips res_model from 'res.partner' to 'dojo.member'.
"""
member = env['dojo.member'].search([], limit=1)
if not member:
    print("ERROR: No dojo.member records found. Create a member first.")
else:
    campaign_xmlids = [
        'dojo_marketing.campaign_member_trial',
        'dojo_marketing.campaign_member_active',
        'dojo_marketing.campaign_member_paused',
        'dojo_marketing.campaign_member_cancelled',
    ]
    for xmlid in campaign_xmlids:
        campaign = env.ref(xmlid, raise_if_not_found=False)
        if campaign:
            campaign.preview_record_ref = member
            print(f"  OK  {campaign.name} -> model now: {campaign.res_model}")
    env.cr.commit()
    print("Done.")

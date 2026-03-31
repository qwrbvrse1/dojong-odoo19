from . import models
from . import controllers


def post_init_hook(env):
    """After install, update campaign preview_record_ref to use the first
    available dojo.member so that res_model flips from 'res.partner' to
    'dojo.member' (res_model is computed from preview_record_ref._name)."""
    first_member = env['dojo.member'].search([], limit=1)
    if not first_member:
        return  # No members yet — admin must set preview manually in the UI

    campaign_xmlids = [
        'dojo_marketing.campaign_member_trial',
        'dojo_marketing.campaign_member_active',
        'dojo_marketing.campaign_member_paused',
        'dojo_marketing.campaign_member_cancelled',
    ]
    for xmlid in campaign_xmlids:
        campaign = env.ref(xmlid, raise_if_not_found=False)
        if campaign:
            campaign.preview_record_ref = first_member

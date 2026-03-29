"""
Install hooks for dojo_core.

1. Grants admin the Dojo Admin group.
2. Aligns the dojo.member sequence past any existing member numbers.
"""
import re


def _ensure_admin_dojo_group(env):
    admin_user = env.ref("base.user_admin", raise_if_not_found=False)
    if not admin_user:
        return
    group_admin = env.ref("dojo_core.group_dojo_admin", raise_if_not_found=False)
    if not group_admin:
        return
    if group_admin not in admin_user.group_ids:
        admin_user.write({"group_ids": [(4, group_admin.id)]})


def _align_member_sequence(env):
    sequence = env["ir.sequence"].search([("code", "=", "dojo.member")], limit=1)
    if not sequence:
        return
    members = env["dojo.member"].search([("member_number", "!=", False)])
    max_num = 0
    for m in members:
        match = re.search(r"(\d+)$", m.member_number or "")
        if match:
            max_num = max(max_num, int(match.group(1)))
    if max_num >= sequence.number_next:
        sequence.number_next = max_num + 1


def post_init_hook(env):
    _ensure_admin_dojo_group(env)
    _align_member_sequence(env)

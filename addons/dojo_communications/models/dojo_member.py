from odoo import models


class DojoMember(models.Model):
    _inherit = "dojo.member"
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        """Default to active/trial members for mass mailings."""
        return [("membership_state", "in", ("active", "trial"))]

    def _mail_get_partners(self, introspect_fields=False):
        """Route mailing recipients to the household's primary guardian.

        When a member belongs to a household with a primary guardian,
        mailings are delivered to the guardian instead of the member
        directly.  This ensures parents receive communications about
        their children.
        """
        result = {}
        for member in self:
            household = member.partner_id.parent_id
            if household and household.is_household and household.primary_guardian_id:
                result[member.id] = household.primary_guardian_id
            else:
                result[member.id] = member.partner_id
        return result

    def action_contact_guardian(self):
        """Open the Send Message wizard pre-loaded with this member."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Contact Guardian",
            "res_model": "dojo.send.message.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_member_ids": [(6, 0, [self.id])]},
        }

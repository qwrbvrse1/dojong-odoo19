from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    portalops_demo_location_id = fields.Many2one(
        "portalops.demo.location",
        string="PortalOps Demo Location",
        ondelete="set null",
        help="Public demo location associated with this lead outcome.",
    )
    portalops_demo_session_key = fields.Char(
        string="PortalOps Demo Session Key",
        copy=False,
        help="External or browser session key used by the public demo flow.",
    )
    portalops_demo_transcript_summary = fields.Text(
        string="PortalOps Demo Transcript Summary",
        help="Short summary captured from the public demo flow transcript.",
    )

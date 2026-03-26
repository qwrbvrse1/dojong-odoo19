from odoo import api, fields, models


class CrmLeadWaiver(models.Model):
    """Extends crm.lead with waiver fields captured during the public trial booking flow.

    When a prospect signs the waiver on the public booking portal the signature
    image, signer name, timestamp, and remote IP are persisted here.  On
    converting the lead to a ``dojo.member`` these values are forwarded to the
    member record via ``dojo.member.apply_waiver()``.
    """

    _inherit = "crm.lead"

    # ── Signature data ─────────────────────────────────────────────────────────
    lead_waiver_signature = fields.Image(
        string="Waiver Signature",
        attachment=True,
        max_width=800,
        max_height=400,
        copy=False,
        help="Hand-drawn signature captured on the public trial booking portal.",
    )
    lead_waiver_signed_by = fields.Char(
        string="Waiver Signed By",
        copy=False,
        readonly=True,
        help="Full name entered by the prospect when they signed the waiver.",
    )
    lead_waiver_signed_on = fields.Datetime(
        string="Waiver Signed On",
        copy=False,
        readonly=True,
        help="UTC timestamp when the waiver was signed via the public portal.",
    )
    lead_waiver_ip = fields.Char(
        string="Waiver Signer IP",
        copy=False,
        readonly=True,
        help="Remote IP address of the prospect at the time of signing (audit trail).",
    )

    # ── Status ────────────────────────────────────────────────────────────────
    lead_has_signed_waiver = fields.Boolean(
        string="Waiver Signed",
        compute="_compute_lead_has_signed_waiver",
        store=True,
        copy=False,
        help="True once the prospect has signed the liability waiver on the booking portal.",
    )

    @api.depends("lead_waiver_signed_on")
    def _compute_lead_has_signed_waiver(self):
        for lead in self:
            lead.lead_has_signed_waiver = bool(lead.lead_waiver_signed_on)

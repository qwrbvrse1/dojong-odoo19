import base64

from odoo import api, fields, models, _


class DojoMember(models.Model):
    """Extends dojo.member with inline waiver signature fields (Community-compatible).

    Replaces the previous Odoo Enterprise sign.request approach.  The signature
    is captured inline in the onboarding wizard via Odoo's native
    ``widget="signature"`` canvas, stored as a Binary image, and embedded into
    a QWeb PDF that is attached to the member record.
    """

    _inherit = "dojo.member"

    # ── Signature data ────────────────────────────────────────────────────────
    waiver_signature = fields.Image(
        string="Waiver Signature",
        attachment=True,
        max_width=800,
        max_height=400,
        copy=False,
        help="Hand-drawn signature captured during member onboarding.",
    )
    waiver_signed_by = fields.Char(
        string="Signed By",
        copy=False,
        readonly=True,
        help="Name of the person who signed the waiver.",
    )
    waiver_signed_on = fields.Datetime(
        string="Signed On",
        copy=False,
        readonly=True,
        help="UTC timestamp when the waiver was signed.",
    )

    # ── Status ────────────────────────────────────────────────────────────────
    waiver_state = fields.Selection(
        selection=[("unsigned", "Not Signed"), ("signed", "Signed")],
        string="Waiver Status",
        compute="_compute_waiver_state",
        store=True,
        default="unsigned",
    )
    has_signed_waiver = fields.Boolean(
        compute="_compute_waiver_state",
        store=True,
        string="Waiver Signed",
    )

    # ── Attachment link ───────────────────────────────────────────────────────
    waiver_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Waiver PDF",
        ondelete="set null",
        copy=False,
        readonly=True,
        help="Signed waiver PDF generated and attached during onboarding.",
    )

    # ── Compute ───────────────────────────────────────────────────────────────
    @api.depends("waiver_signed_on")
    def _compute_waiver_state(self):
        for member in self:
            if member.waiver_signed_on:
                member.waiver_state = "signed"
                member.has_signed_waiver = True
            else:
                member.waiver_state = "unsigned"
                member.has_signed_waiver = False

    # ── Actions ───────────────────────────────────────────────────────────────
    def action_view_waiver_pdf(self):
        """Open the signed waiver PDF in a new browser tab."""
        self.ensure_one()
        if not self.waiver_attachment_id:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.waiver_attachment_id.id}?download=true",
            "target": "new",
        }

    # ── Reusable waiver application ───────────────────────────────────────────
    def apply_waiver(self, signature=None, signed_by=None, signed_on=None):
        """Write waiver data to the member and generate the signed PDF attachment.

        Can be called from the onboarding wizard, the CRM convert-to-member
        wizard, or any other flow that has collected a signature.

        :param signature: Base64-encoded image (bytes or str); the drawn signature.
        :param signed_by: Full name of the signatory.
        :param signed_on: ``datetime`` of signing (defaults to ``now()``).
        """
        self.ensure_one()
        if signed_on is None:
            signed_on = fields.Datetime.now()
        if not signed_by:
            signed_by = self.name

        self.sudo().write(
            {
                "waiver_signature": signature,
                "waiver_signed_by": signed_by,
                "waiver_signed_on": signed_on,
            }
        )

        try:
            pdf_content, _mime = (
                self.env["ir.actions.report"]
                .sudo()
                ._render_qweb_pdf(
                    "dojo_sign.action_report_member_waiver", self.ids
                )
            )
            attachment = (
                self.env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": f"Waiver \u2013 {self.name}.pdf",
                        "type": "binary",
                        "datas": base64.b64encode(pdf_content),
                        "res_model": "dojo.member",
                        "res_id": self.id,
                        "mimetype": "application/pdf",
                    }
                )
            )
            self.sudo().waiver_attachment_id = attachment.id
        except Exception:
            # Non-fatal: signature image is already saved on the member record.
            pass


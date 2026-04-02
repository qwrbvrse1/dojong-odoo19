# -*- coding: utf-8 -*-

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ConnectRecording(models.Model):
    _inherit = "connect.recording"

    def transcribe_recording(self, openai_api_key, summary_prompt):
        """Extend to post call summary to the linked CRM lead chatter."""
        super().transcribe_recording(openai_api_key, summary_prompt)

        # After transcription completes, check if there's a linked lead
        for rec in self:
            if not rec.summary or not rec.call:
                continue

            lead = rec.call.ai_lead_id
            if not lead:
                # Try to find a lead via the partner
                partner = rec.call.partner or rec.partner
                if partner:
                    lead = self.env["crm.lead"].sudo().search(
                        [
                            ("partner_id", "=", partner.id),
                            ("active", "=", True),
                            ("stage_id.is_won", "=", False),
                        ],
                        order="create_date desc",
                        limit=1,
                    )

            if not lead:
                continue

            # Post summary to lead chatter
            body = (
                f"<p><strong>Call Recording Summary:</strong></p>"
                f"{rec.summary}"
            )
            if rec.transcript:
                body += (
                    f"<br/><details><summary>Full Transcript</summary>"
                    f"<pre>{rec.transcript}</pre></details>"
                )
            lead.sudo().message_post(
                body=body,
                subject="Call Recording Summary",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

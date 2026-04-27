# -*- coding: utf-8 -*-
import json
import logging

import requests

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_TIMEOUT = 15  # seconds


class DojoFirebaseService(models.AbstractModel):
    """Low-level HTTP client for the Firebase Cloud Functions endpoints.

    All methods use the Cloud Functions Base URL and shared Bearer secret stored
    in ir.config_parameter — no .env file involved.
    """
    _name = 'dojo.firebase.service'
    _description = 'Dojo Firebase Cloud Functions Client'

    # ── Internal helpers ──────────────────────────────────────────────────

    def _cf_base_url(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_str('firebase.cf_base_url', '')
            .rstrip('/')
        )

    def _cf_secret(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_str('firebase.cf_secret', '')
        )

    def _cf_headers(self):
        secret = self._cf_secret()
        if not secret:
            raise UserError(
                'Firebase Cloud Functions Secret is not configured. '
                'Go to Settings → Firebase Integration → Cloud Functions Secret.'
            )
        return {
            'Authorization': f'Bearer {secret}',
            'Content-Type': 'application/json',
        }

    def _post(self, endpoint, payload):
        """POST JSON payload to a Cloud Functions endpoint.

        Returns the parsed JSON response dict.
        Raises UserError on HTTP errors or connection failures.
        """
        base_url = self._cf_base_url()
        if not base_url:
            raise UserError(
                'Firebase Cloud Functions Base URL is not configured. '
                'Go to Settings → Firebase Integration → Cloud Functions Base URL.'
            )
        url = f'{base_url}/{endpoint}'
        try:
            resp = requests.post(
                url,
                headers=self._cf_headers(),
                data=json.dumps(payload).encode('utf-8'),
                timeout=_TIMEOUT,
            )
        except requests.exceptions.ConnectionError as exc:
            raise UserError(
                f'Could not connect to Firebase Cloud Functions at {url}: {exc}'
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise UserError(
                f'Firebase Cloud Functions request timed out ({_TIMEOUT}s): {exc}'
            ) from exc

        if resp.status_code not in (200, 201):
            _logger.error(
                'Firebase CF %s returned HTTP %s: %s',
                endpoint, resp.status_code, resp.text[:500],
            )
            raise UserError(
                f'Firebase Cloud Function /{endpoint} returned HTTP {resp.status_code}.'
            )

        return resp.json()

    # ── Public API ────────────────────────────────────────────────────────

    def send_email(self, to_list, subject, html_body, from_name=None):
        """Send an email via the Firebase /sendEmail Cloud Function.

        Args:
            to_list:   list of recipient address strings (or a single string)
            subject:   email subject line
            html_body: HTML email body
            from_name: optional display name shown in the From field
        """
        if isinstance(to_list, str):
            to_list = [to_list]
        to_list = [addr.strip() for addr in to_list if addr and addr.strip()]
        if not to_list:
            return

        payload = {
            'to': to_list,
            'subject': subject or '(no subject)',
            'html': html_body or '',
        }
        if from_name:
            payload['from_name'] = from_name

        result = self._post('sendEmail', payload)
        _logger.info('Firebase email sent to %s (messageId=%s)', to_list, result.get('messageId'))
        return result

    def send_push(self, tokens, title, body, data=None):
        """Send an FCM push notification multicast via the Firebase /sendPush Cloud Function.

        Args:
            tokens: list of FCM registration token strings
            title:  notification title
            body:   notification body text
            data:   optional dict of string key/value pairs for the notification data payload

        Returns the raw CF response dict including `unregistered_tokens` list.
        """
        if not tokens:
            return {}

        payload = {
            'tokens': list(tokens),
            'title': title or '',
            'body': body or '',
        }
        if data:
            payload['data'] = {str(k): str(v) for k, v in data.items()}

        result = self._post('sendPush', payload)
        _logger.info(
            'Firebase push sent: %d success, %d unregistered tokens',
            result.get('sent', 0), len(result.get('unregistered_tokens', [])),
        )
        return result

# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class FirebaseController(http.Controller):

    # ── Service Worker ────────────────────────────────────────────────────

    @http.route('/firebase-messaging-sw.js', type='http', auth='none', csrf=False, methods=['GET'])
    def firebase_service_worker(self, **kwargs):
        """Serve the FCM background messaging service worker.

        The browser requires this file to be served from the domain root.
        Rendered dynamically so the Firebase config (stored in ir.config_parameter)
        can be embedded without a build step.
        """
        icp = request.env['ir.config_parameter'].sudo()

        if not icp.get_bool('firebase.push_enabled'):
            # Return a no-op service worker — allows graceful fail on disabled installs
            return request.make_response(
                '// Firebase push notifications are not enabled.\n',
                headers=[
                    ('Content-Type', 'application/javascript'),
                    ('Cache-Control', 'no-store'),
                ],
            )

        api_key = json.dumps(icp.get_str('firebase.web_api_key', ''))
        project_id = json.dumps(icp.get_str('firebase.project_id', ''))
        sender_id = json.dumps(icp.get_str('firebase.messaging_sender_id', ''))
        app_id = json.dumps(icp.get_str('firebase.app_id', ''))

        sw_content = (
            "importScripts('https://www.gstatic.com/firebasejs/10.11.0/firebase-app-compat.js');\n"
            "importScripts('https://www.gstatic.com/firebasejs/10.11.0/firebase-messaging-compat.js');\n"
            "\n"
            "firebase.initializeApp({\n"
            f"  apiKey: {api_key},\n"
            f"  projectId: {project_id},\n"
            f"  messagingSenderId: {sender_id},\n"
            f"  appId: {app_id}\n"
            "});\n"
            "\n"
            "const messaging = firebase.messaging();\n"
            "\n"
            "messaging.onBackgroundMessage(function(payload) {\n"
            "  const title = (payload.notification && payload.notification.title) || 'Dojang';\n"
            "  const options = {\n"
            "    body: (payload.notification && payload.notification.body) || '',\n"
            "    icon: '/dojo_base/static/src/img/dojo_logo.png',\n"
            "    data: payload.data || {},\n"
            "  };\n"
            "  self.registration.showNotification(title, options);\n"
            "});\n"
        )

        return request.make_response(
            sw_content,
            headers=[
                ('Content-Type', 'application/javascript'),
                ('Cache-Control', 'no-cache, no-store, must-revalidate'),
            ],
        )

    # ── Token Registration ────────────────────────────────────────────────

    @http.route('/dojo/firebase/register-token', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def register_fcm_token(self, token=None, device_type='pwa', **kwargs):
        """Register or refresh an FCM token for the currently logged-in portal user.

        Called by firebase_push.js in the member portal after the user grants
        notification permission and the Firebase SDK returns a registration token.
        """
        if not token:
            return {'error': 'token is required'}

        partner = request.env.user.partner_id
        if not partner:
            return {'error': 'no partner for current user'}

        try:
            record = request.env['dojo.fcm.token'].sudo().register_or_refresh(
                partner_id=partner.id,
                token=token,
                device_type=device_type,
            )
            return {'success': True, 'token_id': record.id}
        except Exception as exc:
            _logger.error('FCM token registration failed for partner %s: %s', partner.id, exc)
            return {'error': str(exc)}

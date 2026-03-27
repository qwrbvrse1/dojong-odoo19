# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Firebase Integration settings block under Odoo Settings."""
    _inherit = 'res.config.settings'

    # ── Email relay ────────────────────────────────────────────────────────
    firebase_email_enabled = fields.Boolean(
        string='Enable Firebase Email Relay',
        config_parameter='firebase.email_enabled',
        help='Route all outgoing Odoo emails through the Firebase Cloud Function '
             'instead of the built-in SMTP server.',
    )
    firebase_cf_base_url = fields.Char(
        string='Cloud Functions Base URL',
        config_parameter='firebase.cf_base_url',
        help='HTTPS base URL of your deployed Firebase Cloud Functions, '
             'e.g. https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net '
             '(no trailing slash).',
    )
    firebase_cf_secret = fields.Char(
        string='Cloud Functions Secret',
        config_parameter='firebase.cf_secret',
        password=True,
        no_copy=True,
        help='Shared Bearer secret configured via: '
             'firebase functions:config:set app.secret="..."',
    )

    # ── Push notifications ─────────────────────────────────────────────────
    firebase_push_enabled = fields.Boolean(
        string='Enable FCM Push Notifications',
        config_parameter='firebase.push_enabled',
        help='Inject Firebase JS into the member portal and allow push notification '
             'registration and delivery.',
    )
    firebase_project_id = fields.Char(
        string='Firebase Project ID',
        config_parameter='firebase.project_id',
        help='Your Firebase project ID (from the Firebase console project settings).',
    )
    firebase_web_api_key = fields.Char(
        string='Web API Key',
        config_parameter='firebase.web_api_key',
        help='Firebase Web SDK apiKey (from Firebase console → Project settings → '
             'Your apps → Web app → Config).',
    )
    firebase_messaging_sender_id = fields.Char(
        string='Messaging Sender ID',
        config_parameter='firebase.messaging_sender_id',
        help='Firebase messagingSenderId (from Firebase console → Project settings).',
    )
    firebase_app_id = fields.Char(
        string='App ID',
        config_parameter='firebase.app_id',
        help='Firebase appId (from Firebase console → Project settings → Your apps).',
    )
    firebase_vapid_key = fields.Char(
        string='VAPID Key',
        config_parameter='firebase.vapid_key',
        help='Web Push certificate public key (VAPID). Generate in Firebase console → '
             'Project settings → Cloud Messaging → Web Push certificates.',
    )

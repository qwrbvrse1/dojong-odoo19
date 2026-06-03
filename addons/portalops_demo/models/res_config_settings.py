from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    portalops_demo_google_maps_browser_api_key = fields.Char(
        string="Maps JavaScript API Key",
        config_parameter="portalops_demo.google_maps_browser_api_key",
        help="Browser key used to render the live Google Map on the public demo page.",
    )
    portalops_demo_google_maps_grounding_api_key = fields.Char(
        string="Maps Grounding Lite API Key",
        config_parameter="portalops_demo.google_maps_grounding_api_key",
        help="API key used by portalops_demo to resolve PlaceTwin demo locations via Google Maps Grounding Lite.",
    )
    portalops_demo_dograh_api_key = fields.Char(
        string="Dograh API Key",
        config_parameter="portalops_demo.dograh_api_key",
    )
    portalops_demo_dograh_api_base_url = fields.Char(
        string="Dograh API Base URL",
        config_parameter="portalops_demo.dograh_api_base_url",
    )
    portalops_demo_dograh_ui_base_url = fields.Char(
        string="Dograh UI Base URL",
        config_parameter="portalops_demo.dograh_ui_base_url",
    )
    portalops_demo_dograh_auth_email = fields.Char(
        string="Dograh Auth Email",
        config_parameter="portalops_demo.dograh_auth_email",
    )
    portalops_demo_dograh_auth_password = fields.Char(
        string="Dograh Auth Password",
        config_parameter="portalops_demo.dograh_auth_password",
    )
    portalops_demo_dograh_start_url = fields.Char(
        string="Dograh Start URL",
        config_parameter="portalops_demo.dograh_start_url",
    )
    portalops_demo_dograh_webhook_secret = fields.Char(
        string="Dograh Webhook Secret",
        config_parameter="portalops_demo.dograh_webhook_secret",
    )
    portalops_demo_dograh_flow_id = fields.Char(
        string="Dograh Default Flow ID",
        config_parameter="portalops_demo.dograh_flow_id",
    )
    portalops_demo_dograh_low_vision_flow_id = fields.Char(
        string="Dograh Low Vision Flow ID",
        config_parameter="portalops_demo.dograh_low_vision_flow_id",
    )
    portalops_demo_dograh_embed_token = fields.Char(
        string="Dograh Embed Token",
        config_parameter="portalops_demo.dograh_embed_token",
    )

{
    "name": "Dojo Promotions",
    "summary": "Promotional cards with QR codes — published to kiosk carousel and member portal",
    "version": "saas~19.2.2.0.0",
    "category": "Dojo",
    "license": "LGPL-3",
    "author": "Dojang",
    "depends": [
        "dojo_core",
        "dojo_kiosk",
        "dojo_members_portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/dojo_marketing_card_views.xml",
        "views/dojo_member_badge_button.xml",
        "views/portal_marketing_banner.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "dojo_marketing/static/src/dojo_marketing.css",
        ],
    },
    "application": True,
    "installable": True,
}

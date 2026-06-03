{
    "name": "PortalOps Demo",
    "version": "saas~19.2.0.1.0",
    "summary": "Public PlaceTwin investor demo shell for grounded location storytelling",
    "author": "Dojang",
    "category": "Website",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "website",
        "dojo_crm",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/portalops_demo_seed.xml",
        "views/res_config_settings_views.xml",
        "views/portalops_demo_voice_views.xml",
        "views/portalops_demo_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "portalops_demo/static/src/css/portalops_demo.css",
            "portalops_demo/static/src/js/portalops_demo_page.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}

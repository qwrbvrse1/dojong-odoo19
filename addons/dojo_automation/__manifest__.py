{
    "name": "Dojang Automation",
    "version": "saas~19.2.1.0.0",
    "summary": "Dojang-branded UI layer for automation workflows",
    "author": "Dojo",
    "category": "Hidden",
    "depends": ["dojo_core", "automation_oca"],
    "data": ["views/automation_views_inherit.xml"],
    "assets": {
        "web.assets_backend": [
            "dojo_automation/static/src/xml/automation_stat_panel.xml",
            "dojo_automation/static/src/js/automation_stat_panel.js",
            "dojo_automation/static/src/css/automation.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}

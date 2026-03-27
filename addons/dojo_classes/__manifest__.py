{
    "name": "Dojang Classes",
    "summary": "Courses, sessions, and enrollment",
    "version": "saas~19.2.1.3.2",
    "category": "Services",
    "license": "LGPL-3",
    "author": "Dojang",
    "depends": ["dojo_members"],
    "data": [
        "security/ir.model.access.csv",
        "security/dojo_classes_security.xml",
        "data/dojo_class_recurrence_cron.xml",
        "views/dojo_class_views.xml",
        "views/dojo_auto_enroll_views.xml",
    ],
    "application": True,
    "auto_install": True,
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "dojo_classes/static/src/xml/float_time_12h.xml",
            "dojo_classes/static/src/js/float_time_12h.js",
        ],
    },
}

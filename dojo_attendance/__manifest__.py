{
    "name": "Dojang Attendance",
    "summary": "Session attendance logging",
    "version": "saas~19.2.1.0.0",
    "category": "Services",
    "license": "LGPL-3",
    "author": "Dojang",
    "depends": ["dojo_classes"],
    "data": [
        "security/ir.model.access.csv",
        "security/dojo_attendance_security.xml",
        "views/dojo_attendance_views.xml",
    ],
    "application": True,
    "auto_install": True,
    "installable": True,
}

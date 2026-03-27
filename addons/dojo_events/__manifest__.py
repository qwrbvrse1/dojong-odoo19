{
    "name": "Dojang Events",
    "version": "saas~19.2.1.0.0",
    "summary": "Links dojo members to Odoo Events — seminars, tournaments, belt test ceremonies, workshops",
    "author": "Dojang",
    "category": "Martial Arts",
    "license": "LGPL-3",
    "depends": [
        "event",
        "dojo_members",
    ],
    "data": [
        "views/dojo_member_view_event_inherit.xml",
    ],
    "installable": True,
    "auto_install": False,
}

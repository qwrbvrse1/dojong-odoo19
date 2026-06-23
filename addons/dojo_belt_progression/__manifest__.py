{
    'name': 'Dojo Belt Progression',
    'version': 'saas~19.2.1.0.0',
    'category': 'Dojo',
    'summary': 'OWL-based mass belt promotion with multi-select, single-click promote-all, undo, and promotion history',
    'author': 'Dojo Team',
    'license': 'OPL-1',
    'application': False,
    'installable': True,
    'auto_install': False,
    'depends': [
        'web',
        'dojo_core',
        'dojo_theme',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mass_promote.xml',
        'views/promotion_history.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dojo_belt_progression/static/src/css/mass_promote.css',
            'dojo_belt_progression/static/src/xml/mass_promote.xml',
            'dojo_belt_progression/static/src/js/mass_promote.js',
        ],
    },
}

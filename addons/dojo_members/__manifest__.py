{
    'name': 'Dojo Members',
    'version': 'saas~19.2.1.0.0',
    'category': 'Dojo',
    'summary': 'Dojo member reports: inactive students, contact validation, family groupings',
    'author': 'Dojo Team',
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'auto_install': False,
    'depends': [
        'dojo_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/reports.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dojo_members/static/src/js/reports.js',
            'dojo_members/static/src/xml/reports.xml',
        ],
    },
}

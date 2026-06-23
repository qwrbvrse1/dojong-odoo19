{
    'name': 'Dojo Instructor Dashboard',
    'version': 'saas~19.2.1.0.0',
    'category': 'Dojo',
    'summary': 'OWL-based instructor dashboard with stats, belt distribution, birthdays, and expiring memberships',
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
        'views/dashboard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dojo_instructor_dashboard/static/src/css/dashboard.css',
            'dojo_instructor_dashboard/static/src/xml/dashboard.xml',
            'dojo_instructor_dashboard/static/src/js/dashboard.js',
        ],
    },
}

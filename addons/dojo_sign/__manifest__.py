{
    'name': 'Dojang Sign & Waivers',
    'version': 'saas~19.2.2.0.0',
    'summary': 'Inline waiver signing during member onboarding (Community-compatible)',
    'description': """
Inline waiver signing for member onboarding (Community-compatible).
Replaces Odoo Enterprise Sign with an inline blocking waiver step using bi_all_digital_sign.
The drawn signature is embedded in a QWeb PDF attached to the member record.
""",
    'author': 'Dojo',
    'category': 'Dojo',
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'auto_install': False,
    'depends': [
        'dojo_onboarding',
        'bi_all_digital_sign',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/dojo_waiver_config_views.xml',
        'views/dojo_member_waiver_views.xml',
        'views/dojo_onboarding_waiver_views.xml',
        'report/waiver_report.xml',
    ],
}

{
    'name': 'Dojang AI Assistant',
    'version': 'saas~19.2.1.0.0',
    'summary': 'Reusable AI voice assistant service for Dojang modules',
    'description': """
        Provides a centralized AI assistant service that can be used across different Dojang modules:
        
        Features:
        - Natural language command processing
        - Two-phase confirmation flow (parse → confirm → execute)
        - Structured intent parsing with role-based permissions
        - Audit logging of all AI actions
        - Undo capability for reversible operations
        - Support for text and voice input
        
        Supported Intents:
        - Member lookup, create, update
        - Class enrollment/unenrollment
        - Attendance check-in/check-out
        - Belt rank promotion
        - Subscription management
        - Parent/guardian communication
        
        Can be integrated with:
        - Instructor Dashboard
        - Kiosk Module
        - Any other Dojang frontend
    """,
    'author': 'Dojang',
    'category': 'Dojo',
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,
    'depends': [
        'dojo_core',
        'base',
        'mail',
        'elevenlabs_connector',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ai_intent_schema_data.xml',
        'data/ir_cron.xml',
        'views/ai_assistant_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dojo_assistant/static/src/css/dojo_voice_assistant_page.css',
            'dojo_assistant/static/src/xml/dojo_voice_assistant_page.xml',
            'dojo_assistant/static/src/js/dojo_voice_assistant_page.js',
        ],
    },
    'demo': [],
    'external_dependencies': {},
}

def migrate(cr, version):
    cr.execute("""
        ALTER TABLE dojo_program
        ADD COLUMN IF NOT EXISTS is_trial BOOLEAN NOT NULL DEFAULT FALSE;
    """)

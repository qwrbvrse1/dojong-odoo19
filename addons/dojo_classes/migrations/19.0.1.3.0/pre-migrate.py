def migrate(cr, version):
    cr.execute("""
        ALTER TABLE dojo_program
        ADD COLUMN IF NOT EXISTS manager_instructor_id INTEGER
            REFERENCES dojo_instructor_profile(id) ON DELETE SET NULL;
    """)

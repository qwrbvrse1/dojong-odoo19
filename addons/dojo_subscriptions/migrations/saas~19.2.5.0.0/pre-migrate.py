"""Pre-migration: dojo.member.subscription → sale.subscription (OCA).

This script runs BEFORE the ORM loads new model definitions.  It migrates all
subscription data from the old ``dojo_member_subscription`` table into the
``sale_subscription`` table provided by subscription_oca, and re-points every
FK that previously referenced the old table.

Version bump: 19.0.4.3.0 → 19.0.5.0.0
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # ──────────────────────────────────────────────────────────────────────
    # 0.  Guard – does the old table exist?
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'dojo_member_subscription'
        )
    """)
    if not cr.fetchone()[0]:
        _logger.info("dojo_member_subscription table does not exist — skipping migration.")
        return

    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'sale_subscription'
        )
    """)
    if not cr.fetchone()[0]:
        _logger.error("sale_subscription table does not exist — subscription_oca must be installed first!")
        return

    # ──────────────────────────────────────────────────────────────────────
    # 1.  Create sale.subscription.template records from plans
    # ──────────────────────────────────────────────────────────────────────
    # We need template_ids in sale_subscription, so build them from plans first.
    # Store mapping: plan_id → template_id.

    # Add template_id column to dojo_subscription_plan if it doesn't exist yet
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'dojo_subscription_plan' AND column_name = 'template_id'
        )
    """)
    if not cr.fetchone()[0]:
        cr.execute("ALTER TABLE dojo_subscription_plan ADD COLUMN template_id integer")

    # Build billing period → OCA recurring_rule_type map
    # weekly→weeks, monthly→months, yearly→years
    cr.execute("""
        INSERT INTO sale_subscription_template
            (name, code, recurring_rule_type, recurring_interval,
             recurring_rule_boundary, recurring_rule_count,
             create_uid, write_uid, create_date, write_date)
        SELECT
            p.name,
            COALESCE(p.code, ''),
            CASE p.billing_period
                WHEN 'weekly'  THEN 'weeks'
                WHEN 'yearly'  THEN 'years'
                ELSE 'months'
            END,
            1,
            CASE WHEN COALESCE(p.duration, 0) > 0 THEN 'limited' ELSE 'unlimited' END,
            CASE WHEN COALESCE(p.duration, 0) > 0 THEN p.duration ELSE 1 END,
            1, 1, NOW(), NOW()
        FROM dojo_subscription_plan p
        WHERE p.template_id IS NULL
        RETURNING id
    """)
    template_ids = [r[0] for r in cr.fetchall()]
    _logger.info("Created %d sale.subscription.template records from plans.", len(template_ids))

    # Link template_id back to plans (ordered by plan.id)
    if template_ids:
        cr.execute("""
            WITH plan_rows AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn
                FROM dojo_subscription_plan
                WHERE template_id IS NULL
            ),
            tmpl_rows AS (
                SELECT unnest(%s::int[]) AS tmpl_id,
                       generate_series(1, %s) AS rn
            )
            UPDATE dojo_subscription_plan p
               SET template_id = t.tmpl_id
              FROM plan_rows pr
              JOIN tmpl_rows t ON t.rn = pr.rn
             WHERE p.id = pr.id
        """, [template_ids, len(template_ids)])

    # ──────────────────────────────────────────────────────────────────────
    # 2.  Ensure sale_subscription has all required dojo columns
    # ──────────────────────────────────────────────────────────────────────
    dojo_columns = {
        "member_id": "integer",
        "household_id": "integer",
        "plan_id": "integer",
        "plan_type": "varchar",
        "program_id": "integer",
        "paused": "boolean DEFAULT false",
        "last_invoice_id": "integer",
        "billing_reference": "varchar",
        "note": "text",
        "billing_failure_count": "integer DEFAULT 0",
        "last_billing_failure_date": "date",
        "grace_period_end": "date",
        "state": "varchar",
    }
    for col_name, col_type in dojo_columns.items():
        cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sale_subscription' AND column_name = %s
            )
        """, [col_name])
        if not cr.fetchone()[0]:
            cr.execute(
                "ALTER TABLE sale_subscription ADD COLUMN %s %s"
                % (col_name, col_type)
            )

    # ──────────────────────────────────────────────────────────────────────
    # 3.  Resolve stage IDs and close reason IDs for state mapping
    # ──────────────────────────────────────────────────────────────────────
    stage_map = {}  # type → stage_id
    for stype in ('draft', 'pre', 'in_progress', 'post'):
        cr.execute(
            "SELECT id FROM sale_subscription_stage WHERE type = %s LIMIT 1",
            [stype],
        )
        row = cr.fetchone()
        if row:
            stage_map[stype] = row[0]

    # We can't rely on xmlids at pre-migrate time for close_reasons since data
    # files haven't been loaded yet. We'll create them now if needed.
    cr.execute("""
        SELECT id FROM sale_subscription_close_reason
        WHERE name = 'Subscription Expired' LIMIT 1
    """)
    row = cr.fetchone()
    expired_reason_id = row[0] if row else None
    if not expired_reason_id:
        cr.execute("""
            INSERT INTO sale_subscription_close_reason (name, create_uid, write_uid, create_date, write_date)
            VALUES ('Subscription Expired', 1, 1, NOW(), NOW())
            RETURNING id
        """)
        expired_reason_id = cr.fetchone()[0]

    cr.execute("""
        SELECT id FROM sale_subscription_close_reason
        WHERE name = 'Subscription Cancelled' LIMIT 1
    """)
    row = cr.fetchone()
    cancelled_reason_id = row[0] if row else None
    if not cancelled_reason_id:
        cr.execute("""
            INSERT INTO sale_subscription_close_reason (name, create_uid, write_uid, create_date, write_date)
            VALUES ('Subscription Cancelled', 1, 1, NOW(), NOW())
            RETURNING id
        """)
        cancelled_reason_id = cr.fetchone()[0]

    # ──────────────────────────────────────────────────────────────────────
    # 4.  Get a default pricelist for required field
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("SELECT id FROM product_pricelist LIMIT 1")
    row = cr.fetchone()
    default_pricelist_id = row[0] if row else None

    if not default_pricelist_id:
        # Create a default pricelist so sale_subscription NOT NULL constraint is satisfied
        cr.execute("""
            SELECT id FROM res_currency WHERE name = 'USD' LIMIT 1
        """)
        cur_row = cr.fetchone()
        currency_id = cur_row[0] if cur_row else 1
        cr.execute("""
            INSERT INTO product_pricelist (name, currency_id, active, create_uid, write_uid, create_date, write_date)
            VALUES ('{"en_US": "Default Pricelist"}'::jsonb, %s, true, 1, 1, NOW(), NOW())
            RETURNING id
        """, [currency_id])
        default_pricelist_id = cr.fetchone()[0]
        _logger.info("Created default product_pricelist id=%d for migration.", default_pricelist_id)

    # ──────────────────────────────────────────────────────────────────────
    # 5.  Copy rows: dojo_member_subscription → sale_subscription
    # ──────────────────────────────────────────────────────────────────────
    # Map old state → (stage_id, paused, close_reason_id)
    state_stage = {
        'draft':     (stage_map.get('draft'),       False, None),
        'pending':   (stage_map.get('pre'),          False, None),
        'active':    (stage_map.get('in_progress'),  False, None),
        'paused':    (stage_map.get('in_progress'),  True,  None),
        'cancelled': (stage_map.get('post'),         False, cancelled_reason_id),
        'expired':   (stage_map.get('post'),         False, expired_reason_id),
    }

    cr.execute("SELECT COUNT(*) FROM dojo_member_subscription")
    total = cr.fetchone()[0]
    _logger.info("Migrating %d subscriptions from dojo_member_subscription → sale_subscription...", total)

    if total == 0:
        _logger.info("No subscriptions to migrate.")
        return

    # We need to find the partner_id for each subscription.  The old model
    # had member_id but not partner_id; we derive it from dojo_member.
    # Build mapping: old_sub_id → new_sub_id in a temp table.
    cr.execute("""
        CREATE TEMP TABLE _sub_id_map (
            old_id integer PRIMARY KEY,
            new_id integer
        )
    """)

    # Fetch all old subscriptions
    cr.execute("""
        SELECT
            s.id, s.member_id, s.household_id, s.plan_id, s.plan_type,
            s.program_id, s.company_id, s.last_invoice_id,
            s.state, s.billing_reference, s.start_date, s.end_date,
            s.next_billing_date, s.note, s.billing_failure_count,
            s.last_billing_failure_date, s.grace_period_end, s.name,
            s.create_uid, s.write_uid, s.create_date, s.write_date,
            p.template_id
        FROM dojo_member_subscription s
        LEFT JOIN dojo_subscription_plan p ON p.id = s.plan_id
        ORDER BY s.id
    """)
    rows = cr.fetchall()

    for row in rows:
        (old_id, member_id, household_id, plan_id, plan_type,
         program_id, company_id, last_invoice_id,
         state, billing_reference, start_date, end_date,
         next_billing_date, note, billing_failure_count,
         last_billing_failure_date, grace_period_end, name,
         create_uid, write_uid, create_date, write_date,
         template_id) = row

        # Resolve partner_id from member
        partner_id = None
        if member_id:
            cr.execute("""
                SELECT p.parent_id, p.id
                FROM dojo_member m
                JOIN res_partner p ON p.id = m.partner_id
                WHERE m.id = %s
            """, [member_id])
            prow = cr.fetchone()
            if prow:
                household_partner_id, member_partner_id = prow
                if household_partner_id:
                    # Try to get primary_guardian_id from household
                    cr.execute("""
                        SELECT primary_guardian_id FROM res_partner
                        WHERE id = %s AND primary_guardian_id IS NOT NULL
                    """, [household_partner_id])
                    grow = cr.fetchone()
                    partner_id = grow[0] if grow else member_partner_id
                else:
                    partner_id = member_partner_id

        if not partner_id:
            # Fallback — create with a dummy partner would break things,
            # just use the company partner
            cr.execute(
                "SELECT partner_id FROM res_company WHERE id = %s",
                [company_id or 1],
            )
            cpartner = cr.fetchone()
            partner_id = cpartner[0] if cpartner else 1

        stage_id, paused, close_reason_id = state_stage.get(
            state, (stage_map.get('draft'), False, None),
        )

        # Determine in_progress flag (OCA field)
        in_progress = (state in ('active', 'paused'))

        cr.execute("""
            INSERT INTO sale_subscription (
                company_id, partner_id, template_id, pricelist_id,
                stage_id, close_reason_id,
                date_start, date, recurring_next_date,
                member_id, household_id, plan_id, plan_type, program_id,
                paused, last_invoice_id, billing_reference, note,
                billing_failure_count, last_billing_failure_date, grace_period_end,
                state, name, active, in_progress,
                create_uid, write_uid, create_date, write_date
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, true, %s,
                %s, %s, %s, %s
            )
            RETURNING id
        """, [
            company_id or 1, partner_id, template_id, default_pricelist_id,
            stage_id, close_reason_id,
            start_date, end_date, next_billing_date,
            member_id, household_id, plan_id, plan_type, program_id,
            paused, last_invoice_id, billing_reference, note,
            billing_failure_count or 0, last_billing_failure_date, grace_period_end,
            state, name, in_progress,
            create_uid or 1, write_uid or 1, create_date, write_date,
        ])
        new_id = cr.fetchone()[0]
        cr.execute(
            "INSERT INTO _sub_id_map (old_id, new_id) VALUES (%s, %s)",
            [old_id, new_id],
        )

    _logger.info("Inserted %d rows into sale_subscription.", len(rows))

    # ──────────────────────────────────────────────────────────────────────
    # 6.  Re-point FK columns in dependent tables
    # ──────────────────────────────────────────────────────────────────────
    fk_tables = [
        ("dojo_program_enrollment", "subscription_id"),
        ("dojo_credit_transaction", "subscription_id"),
        ("dojo_member", "active_subscription_id"),
        ("dojo_checkout_session", "resulting_subscription_id"),
    ]
    for table, column in fk_tables:
        cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            )
        """, [table, column])
        if not cr.fetchone()[0]:
            continue
        # Drop existing FK constraints on this column first
        cr.execute("""
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_attribute att ON att.attnum = ANY(con.conkey)
                                 AND att.attrelid = con.conrelid
            WHERE con.conrelid = %s::regclass
              AND con.contype = 'f'
              AND att.attname = %s
        """, [table, column])
        for (cname,) in cr.fetchall():
            cr.execute("ALTER TABLE %s DROP CONSTRAINT %s" % (table, cname))
            _logger.info("Dropped FK constraint %s on %s.%s", cname, table, column)
        cr.execute("""
            UPDATE {table} t
               SET {column} = m.new_id
              FROM _sub_id_map m
             WHERE t.{column} = m.old_id
        """.format(table=table, column=column))
        _logger.info("Re-pointed %s.%s: %d rows.", table, column, cr.rowcount)

    # ──────────────────────────────────────────────────────────────────────
    # 7.  Migrate M2M relation table: dojo_invoice_sub_rel
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'dojo_invoice_sub_rel'
        )
    """)
    if cr.fetchone()[0]:
        cr.execute("""
            UPDATE dojo_invoice_sub_rel r
               SET subscription_id = m.new_id
              FROM _sub_id_map m
             WHERE r.subscription_id = m.old_id
        """)
        _logger.info("Re-pointed dojo_invoice_sub_rel: %d rows.", cr.rowcount)

        # Drop old FK constraint and add new one
        cr.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'dojo_invoice_sub_rel'
              AND constraint_type = 'FOREIGN KEY'
        """)
        for (cname,) in cr.fetchall():
            cr.execute("ALTER TABLE dojo_invoice_sub_rel DROP CONSTRAINT %s" % cname)
        cr.execute("""
            ALTER TABLE dojo_invoice_sub_rel
            ADD CONSTRAINT dojo_invoice_sub_rel_subscription_id_fkey
            FOREIGN KEY (subscription_id) REFERENCES sale_subscription(id) ON DELETE CASCADE
        """)
        cr.execute("""
            ALTER TABLE dojo_invoice_sub_rel
            ADD CONSTRAINT dojo_invoice_sub_rel_invoice_id_fkey
            FOREIGN KEY (invoice_id) REFERENCES account_move(id) ON DELETE CASCADE
        """)

    # ──────────────────────────────────────────────────────────────────────
    # 8.  Migrate account_move.subscription_id
    #     OCA already defines this field (FK → sale_subscription), but the
    #     old dojo code also defined it (FK → dojo_member_subscription).
    #     Re-point values.
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'account_move' AND column_name = 'subscription_id'
        )
    """)
    if cr.fetchone()[0]:
        # Check which table the FK currently references
        cr.execute("""
            SELECT ccu.table_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = 'account_move'
              AND kcu.column_name = 'subscription_id'
              AND tc.constraint_type = 'FOREIGN KEY'
        """)
        fk_row = cr.fetchone()
        if fk_row and fk_row[0] == 'dojo_member_subscription':
            # Drop old FK, re-point data, add new FK
            cr.execute("""
                SELECT constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = 'account_move'
                  AND kcu.column_name = 'subscription_id'
                  AND tc.constraint_type = 'FOREIGN KEY'
            """)
            for (cname,) in cr.fetchall():
                cr.execute("ALTER TABLE account_move DROP CONSTRAINT %s" % cname)

            cr.execute("""
                UPDATE account_move am
                   SET subscription_id = m.new_id
                  FROM _sub_id_map m
                 WHERE am.subscription_id = m.old_id
            """)
            _logger.info("Re-pointed account_move.subscription_id: %d rows.", cr.rowcount)

            cr.execute("""
                ALTER TABLE account_move
                ADD CONSTRAINT account_move_subscription_id_fkey
                FOREIGN KEY (subscription_id) REFERENCES sale_subscription(id) ON DELETE SET NULL
            """)

    # ──────────────────────────────────────────────────────────────────────
    # 9.  Drop old FK constraints on dependent tables
    #     (The ORM will recreate them pointing to sale_subscription)
    # ──────────────────────────────────────────────────────────────────────
    for table, column in fk_tables:
        cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            )
        """, [table, column])
        if not cr.fetchone()[0]:
            continue
        cr.execute("""
            SELECT tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.table_name = %s
              AND kcu.column_name = %s
              AND tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name = 'dojo_member_subscription'
        """, [table, column])
        for (cname,) in cr.fetchall():
            cr.execute("ALTER TABLE %s DROP CONSTRAINT %s" % (table, cname))
            _logger.info("Dropped old FK constraint %s on %s.%s", cname, table, column)

    # ──────────────────────────────────────────────────────────────────────
    # 10. Clean up ir_model_data for old model
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'dojo.member.subscription'
    """)
    _logger.info("Cleaned up %d ir_model_data entries for old model.", cr.rowcount)

    # ──────────────────────────────────────────────────────────────────────
    # 11. Clean up temp table
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("DROP TABLE IF EXISTS _sub_id_map")

    _logger.info(
        "Pre-migration complete: %d subscriptions migrated from "
        "dojo_member_subscription → sale_subscription.",
        total,
    )

"""
Pre-migration for dojo_core consolidation.

Merges ir_model_data XML-IDs from the five old modules
(dojo_base, dojo_members, dojo_classes, dojo_attendance,
dojo_belt_progression) into dojo_core so that Odoo's XML
loader updates the existing DB records instead of creating
duplicates.

Inherited views that were flattened into dojo_core's base
views are deleted to prevent stale xpath errors.
"""
import logging

_logger = logging.getLogger(__name__)

OLD_MODULES = (
    'dojo_base',
    'dojo_members',
    'dojo_classes',
    'dojo_attendance',
    'dojo_belt_progression',
)

# XML IDs in dojo_belt_progression that must NOT be reassigned
# (kept for historical reference — belt stub was removed).
KEEP_IN_BELT = ()


def migrate(cr, version):
    _logger.info(
        "dojo_core pre-migrate: consolidating %s into dojo_core",
        ", ".join(OLD_MODULES),
    )

    # ── 1.  Delete inherited views from old modules ──────────────
    #   These performed xpath operations on base forms (member,
    #   program, class session …) that have been flattened into
    #   dojo_core's own view definitions.  Keeping them would
    #   cause xpath-mismatch errors during upgrade.
    if KEEP_IN_BELT:
        cr.execute("""
            SELECT d.id   AS imd_id,
                   d.name AS xml_id,
                   d.module,
                   d.res_id,
                   v.name AS view_name
              FROM ir_model_data d
              JOIN ir_ui_view    v ON v.id = d.res_id
             WHERE d.module IN %s
               AND d.model  = 'ir.ui.view'
               AND v.inherit_id IS NOT NULL
               AND d.name NOT IN %s
        """, [OLD_MODULES, KEEP_IN_BELT])
    else:
        cr.execute("""
            SELECT d.id   AS imd_id,
                   d.name AS xml_id,
                   d.module,
                   d.res_id,
                   v.name AS view_name
              FROM ir_model_data d
              JOIN ir_ui_view    v ON v.id = d.res_id
             WHERE d.module IN %s
               AND d.model  = 'ir.ui.view'
               AND v.inherit_id IS NOT NULL
        """, [OLD_MODULES])

    inherited = cr.fetchall()
    if inherited:
        imd_ids  = tuple(r[0] for r in inherited)
        view_ids = tuple(r[3] for r in inherited)
        _logger.info(
            "Removing %d flattened inherited views: %s",
            len(inherited),
            [(r[2], r[1]) for r in inherited],
        )
        cr.execute("DELETE FROM ir_model_data WHERE id IN %s", [imd_ids])
        cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", [view_ids])

    # ── 2.  Reassign remaining XML-IDs to dojo_core ─────────────
    for mod in OLD_MODULES:
        # 2a.  Drop entries that would collide with an existing
        #      dojo_core record of the same name.
        cr.execute("""
            DELETE FROM ir_model_data d_old
             USING ir_model_data d_new
             WHERE d_old.module = %s
               AND d_new.module = 'dojo_core'
               AND d_old.name   = d_new.name
        """, [mod])
        deleted = cr.rowcount

        # 2b.  Move everything else (models, fields, groups, rules,
        #      base views, actions, sequences, crons, ACL rows …).
        if KEEP_IN_BELT:
            cr.execute("""
                UPDATE ir_model_data
                   SET module = 'dojo_core'
                 WHERE module = %s
                   AND name NOT LIKE 'module\_%%'
                   AND name NOT IN %s
            """, [mod, KEEP_IN_BELT])
        else:
            cr.execute("""
                UPDATE ir_model_data
                   SET module = 'dojo_core'
                 WHERE module = %s
                   AND name NOT LIKE 'module\_%%'
            """, [mod])
        moved = cr.rowcount

        _logger.info(
            "%s → dojo_core: moved %d, dropped %d duplicates",
            mod, moved, deleted,
        )

    _logger.info("dojo_core pre-migrate complete")

"""
Pre-migration for dojo_core saas~19.2.3.0.0.

Absorbs the dojo_instructor_dashboard module into dojo_core
(and partially into dojo_crm / dojo_assistant for glue code).

Steps:
  1. Delete inherited views from dojo_instructor_dashboard so
     they don't clash with the flattened copies inside dojo_core.
  2. Reassign all remaining ir_model_data XML-IDs from
     dojo_instructor_dashboard → dojo_core.
"""
import logging

_logger = logging.getLogger(__name__)

OLD_MODULE = "dojo_instructor_dashboard"


def migrate(cr, version):
    _logger.info(
        "dojo_core pre-migrate %s: absorbing %s", version, OLD_MODULE,
    )

    # ── 1.  Delete inherited views from the old module ───────────
    cr.execute("""
        SELECT d.id   AS imd_id,
               d.name AS xml_id,
               d.res_id,
               v.name AS view_name
          FROM ir_model_data d
          JOIN ir_ui_view    v ON v.id = d.res_id
         WHERE d.module = %s
           AND d.model  = 'ir.ui.view'
           AND v.inherit_id IS NOT NULL
    """, [OLD_MODULE])

    inherited = cr.fetchall()
    if inherited:
        imd_ids = tuple(r[0] for r in inherited)
        view_ids = tuple(r[2] for r in inherited)
        _logger.info(
            "Removing %d inherited views from %s: %s",
            len(inherited), OLD_MODULE,
            [r[1] for r in inherited],
        )
        cr.execute("DELETE FROM ir_model_data WHERE id IN %s", [imd_ids])
        cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", [view_ids])

    # ── 2.  Drop entries that collide with existing dojo_core IDs ─
    cr.execute("""
        DELETE FROM ir_model_data d_old
         USING ir_model_data d_new
         WHERE d_old.module = %s
           AND d_new.module = 'dojo_core'
           AND d_old.name   = d_new.name
    """, [OLD_MODULE])
    deleted = cr.rowcount

    # ── 3.  Reassign remaining XML-IDs to dojo_core ─────────────
    cr.execute("""
        UPDATE ir_model_data
           SET module = 'dojo_core'
         WHERE module = %s
           AND name NOT LIKE 'module\_%%'
    """, [OLD_MODULE])
    moved = cr.rowcount

    _logger.info(
        "%s → dojo_core: moved %d, dropped %d duplicates",
        OLD_MODULE, moved, deleted,
    )
    _logger.info("dojo_core pre-migrate %s complete", version)

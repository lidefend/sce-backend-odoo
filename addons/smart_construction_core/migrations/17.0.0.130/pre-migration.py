"""Remove retired P1 alias views by their authoritative XML ID namespace.

Version 17.0.0.76 removed the alias fields and attempted to remove dependent
views by inspecting their stored architecture.  A historical database may
contain later-rewritten copies of those views whose architecture no longer
contains the alias prefixes.  Such copies survive that content-based cleanup
and can block validation of their canonical parent views.

The source declarations were retired as one namespaced set.  Remove that set,
and any inherited descendants, deterministically before registry validation.
Business records and current canonical views are not modified.
"""


RETIRED_VIEW_XMLID_PREFIX = "view_p1_daily_business_visible_"


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        WITH RECURSIVE retired_view_ids AS (
            SELECT data.res_id AS id
              FROM ir_model_data data
             WHERE data.module = 'smart_construction_core'
               AND data.model = 'ir.ui.view'
               AND data.name LIKE %s
            UNION
            SELECT child.id
              FROM ir_ui_view child
              JOIN retired_view_ids parent ON child.inherit_id = parent.id
        ),
        deleted_view_xmlids AS (
            DELETE FROM ir_model_data
             WHERE model = 'ir.ui.view'
               AND res_id IN (SELECT id FROM retired_view_ids)
            RETURNING id
        )
        DELETE FROM ir_ui_view
         WHERE id IN (SELECT id FROM retired_view_ids)
        """,
        (RETIRED_VIEW_XMLID_PREFIX + "%",),
    )

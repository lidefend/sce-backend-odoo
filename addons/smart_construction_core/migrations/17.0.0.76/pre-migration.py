"""Remove obsolete non-stored migration aliases from the product registry."""


ALIAS_PREFIX = "p1_" + "visible_"
FORMAL_PROJECTION_PREFIX = "uc_" + "formal_"


def migrate(cr, installed_version):
    del installed_version
    patterns = (ALIAS_PREFIX + "%", FORMAL_PROJECTION_PREFIX + "%")
    cr.execute(
        """
        WITH RECURSIVE obsolete_view_ids AS (
            SELECT id
              FROM ir_ui_view
             WHERE arch_db::text LIKE %s OR arch_db::text LIKE %s
            UNION
            SELECT child.id
              FROM ir_ui_view child
              JOIN obsolete_view_ids parent ON child.inherit_id = parent.id
        ),
        deleted_view_xmlids AS (
            DELETE FROM ir_model_data
             WHERE model = 'ir.ui.view'
               AND res_id IN (SELECT id FROM obsolete_view_ids)
            RETURNING id
        )
        DELETE FROM ir_ui_view
         WHERE id IN (SELECT id FROM obsolete_view_ids)
        """,
        ("%" + ALIAS_PREFIX + "%", "%" + FORMAL_PROJECTION_PREFIX + "%"),
    )
    cr.execute(
        """
        DELETE FROM ir_model_data data
         USING ir_model_fields field
         WHERE data.model = 'ir.model.fields'
           AND data.res_id = field.id
           AND (field.name LIKE %s OR field.name LIKE %s)
        """,
        patterns,
    )
    cr.execute(
        """
        DELETE FROM ir_model_fields
         WHERE name LIKE %s OR name LIKE %s
        """,
        patterns,
    )

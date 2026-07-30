"""Remove obsolete non-stored migration aliases from the product registry."""


ALIAS_PREFIX = "p1_" + "visible_"
FORMAL_PROJECTION_PREFIX = "uc_" + "formal_"


def migrate(cr, installed_version):
    del installed_version
    patterns = (ALIAS_PREFIX + "%", FORMAL_PROJECTION_PREFIX + "%")
    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE arch_db::text LIKE %s OR arch_db::text LIKE %s
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

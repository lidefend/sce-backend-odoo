def migrate(cr, version):
    """Move user management out of business-scene composition.

    The native menu is a system-configuration entry owned by the fact layer and
    gated by the configuration-admin group. A scenario reference would make its
    availability depend on tenant business-scene selection.
    """
    del version
    cr.execute("""
        SELECT res_id
          FROM ir_model_data
         WHERE module = 'smart_construction_core'
           AND name = 'menu_sc_runtime_user_management'
           AND model = 'ir.ui.menu'
         LIMIT 1
    """)
    row = cr.fetchone()
    if row:
        cr.execute(
            "DELETE FROM sc_product_scenario_entry WHERE menu_id = %s",
            (row[0],),
        )

def migrate(cr, version):
    """Remove the retired one-scenario-per-menu database constraint."""
    del version
    cr.execute("""
        ALTER TABLE sc_product_scenario_entry
        DROP CONSTRAINT IF EXISTS sc_product_scenario_entry_menu_uniq
    """)

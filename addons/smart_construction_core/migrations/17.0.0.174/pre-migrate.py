"""Adopt existing scenario configuration without replaying deleted seed rows."""


def migrate(cr, version):
    cr.execute("SELECT to_regclass('sc_product_scenario')")
    if cr.fetchone()[0]:
        # Table existence also covers an administrator deleting every scenario.
        # It was introduced with the old automatic seed in 17.0.0.173.
        cr.execute("""
            INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
            VALUES ('smart_construction_core.scenario_seed.v1', '1', 1, 1, NOW(), NOW())
            ON CONFLICT (key) DO NOTHING
        """)

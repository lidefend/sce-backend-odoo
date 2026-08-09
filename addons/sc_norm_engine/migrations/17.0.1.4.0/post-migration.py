from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Attach legacy Sichuan 2015 specialties to the seeded versioned catalog."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    catalog = env.ref("sc_norm_engine.catalog_sc_2015")
    cr.execute(
        "UPDATE sc_norm_specialty SET catalog_id = %s WHERE catalog_id IS NULL",
        [catalog.id],
    )
    cr.execute(
        "UPDATE sc_norm_item AS item SET catalog_id = specialty.catalog_id "
        "FROM sc_norm_specialty AS specialty "
        "WHERE item.specialty_id = specialty.id AND item.catalog_id IS NULL"
    )
    cr.execute(
        "UPDATE sc_norm_import_wizard SET catalog_id = %s WHERE catalog_id IS NULL",
        [catalog.id],
    )
    cr.execute(
        "ALTER TABLE sc_norm_specialty ALTER COLUMN catalog_id SET NOT NULL"
    )
    cr.execute(
        "ALTER TABLE sc_norm_import_wizard ALTER COLUMN catalog_id SET NOT NULL"
    )

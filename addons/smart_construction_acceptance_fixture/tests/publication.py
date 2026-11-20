"""Real publication prerequisites; caller TransactionCase owns rollback."""
from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService


def publish_scenarios(env):
    params = env["ir.config_parameter"].sudo()
    params.set_param("smart_core.platform_release_db", env.cr.dbname)
    params.set_param("smart_core.release_operator.catalog_source_db", env.cr.dbname)
    return EditionReleaseSnapshotService(env).freeze_release_surface(
        product_key="construction.standard",
        version="acceptance-maintained-scenarios",
        replace_active=True,
    )

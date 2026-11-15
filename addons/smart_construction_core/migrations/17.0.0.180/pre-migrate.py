import re

from odoo.tools import parse_version


SCENARIO_ENTRY_VERSION = "17.0.0.174"
VERSION_RE = re.compile(r"^\d+(?:\.\d+){2,}$")


def _scenario_entry_table_exists(cr):
    cr.execute("SELECT to_regclass('public.sc_product_scenario_entry')")
    return bool(cr.fetchone()[0])


def _allow_missing_scenario_entry_table(cr, installed_version):
    if _scenario_entry_table_exists(cr):
        return False
    version = str(installed_version or "").strip()
    if not VERSION_RE.fullmatch(version):
        raise RuntimeError(
            "SCENARIO_ENTRY_TABLE_MISSING_UNKNOWN_VERSION: "
            "cannot validate an absent sc_product_scenario_entry table "
            "from installed version %r" % installed_version
        )
    if parse_version(version) < parse_version(SCENARIO_ENTRY_VERSION):
        return True
    raise RuntimeError(
        "SCENARIO_ENTRY_TABLE_MISSING_INVALID_STATE: "
        "installed version %s requires sc_product_scenario_entry" % version
    )


def migrate(cr, version):
    """Remove the retired one-scenario-per-menu database constraint."""
    if _allow_missing_scenario_entry_table(cr, version):
        return
    cr.execute("""
        ALTER TABLE sc_product_scenario_entry
        DROP CONSTRAINT IF EXISTS sc_product_scenario_entry_menu_uniq
    """)

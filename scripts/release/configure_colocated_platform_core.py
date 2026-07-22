"""Odoo-shell entrypoint for the explicit colocated platform DB parameter.

This script is intentionally inert unless the exact apply acknowledgement is
present.  It writes through ``ir.config_parameter`` and never creates a
database or copies data from another database.
"""

from __future__ import annotations

import json
import os


ACK = "I_ACKNOWLEDGE_COLOCATED_PLATFORM_CONFIGURATION"
PARAM = "smart_core.platform_release_db"


def main():
    current_db = str(env.cr.dbname or "").strip()  # noqa: F821
    expected_db = str(os.environ.get("PLATFORM_RELEASE_DB") or "").strip()
    if os.environ.get("SC_COLOCATED_PLATFORM_CONFIG_APPLY") != ACK:
        raise RuntimeError("COLOCATED_PLATFORM_CONFIG_APPLY_ACK_REQUIRED")
    if not current_db or expected_db != current_db:
        raise RuntimeError("PLATFORM_RELEASE_DB_MUST_MATCH_CURRENT")
    params = env["ir.config_parameter"].sudo()  # noqa: F821
    before = str(params.get_param(PARAM, "") or "").strip()
    if before and before != current_db:
        raise RuntimeError("EXISTING_PLATFORM_RELEASE_DB_CONFLICT")
    changed = before != current_db
    if changed:
        params.set_param(PARAM, current_db)
    env.cr.commit()  # noqa: F821
    print(json.dumps({
        "status": "PASS",
        "database": current_db,
        "parameter": PARAM,
        "value": current_db,
        "changed": changed,
    }, sort_keys=True))


main()

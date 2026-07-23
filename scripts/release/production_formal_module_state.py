#!/usr/bin/env python3
"""Read-only Odoo-shell state probe for the formal module closure."""

from __future__ import annotations

import ast
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path


TARGET_MODULES = (
    "smart_construction_bootstrap",
    "smart_construction_seed",
    "sc_norm_engine",
)
DEMO_FIXTURE_MODULES = (
    "smart_construction_demo",
    "smart_construction_acceptance_fixture",
)
BUSINESS_MODELS = (
    "project.project",
    "construction.contract",
    "sc.settlement.order",
    "payment.request",
)
SEED_OVERRIDE_NAMES = (
    "SC_SEED_ENABLED",
    "SC_BOOTSTRAP_MODE",
    "SC_SEED_STEPS",
    "SC_SEED_PROFILE",
)
PRODUCT_ADDONS = Path("/mnt/product-addons")


def _manifest_state(module_name: str) -> dict:
    module_root = PRODUCT_ADDONS / module_name
    manifest_path = module_root / "__manifest__.py"
    if not manifest_path.is_file():
        return {"source_exists": False}
    manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
    xml_operations = []
    for relative in manifest.get("data", []):
        if not relative.endswith(".xml"):
            continue
        root = ET.parse(module_root / relative).getroot()
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            if tag in {"record", "function"}:
                xml_operations.append(
                    {
                        "file": relative,
                        "kind": tag,
                        "model": element.attrib.get("model", ""),
                        "name": element.attrib.get("name", ""),
                    }
                )
    return {
        "source_exists": True,
        "installable": bool(manifest.get("installable", True)),
        "depends": list(manifest.get("depends", [])),
        "data": list(manifest.get("data", [])),
        "demo": list(manifest.get("demo", [])),
        "xml_operations": xml_operations,
    }


def collect_state(odoo_env) -> dict:
    formal_modules = tuple(
        item
        for item in os.environ.get("FORMAL_MODULE_CONTRACT", "").split(",")
        if item
    )
    if len(formal_modules) != 10 or len(set(formal_modules)) != 10:
        raise RuntimeError("formal module contract must contain exactly 10 modules")

    module_model = odoo_env["ir.module.module"].sudo()
    module_rows = module_model.search([("name", "in", list(formal_modules))])
    module_states = {row.name: row.state for row in module_rows}
    business_counts = {
        model: odoo_env[model].sudo().search_count([]) for model in BUSINESS_MODELS
    }
    users = odoo_env["res.users"].sudo()
    target_admin = users.with_context(active_test=False).search(
        [("login", "=", "admin")]
    )
    active_admins = odoo_env.ref("base.group_system").users.filtered(
        lambda user: user.active
    )
    config = odoo_env["ir.config_parameter"].sudo()
    result = {
        "database": odoo_env.cr.dbname,
        "formal_modules": list(formal_modules),
        "module_states": {
            name: module_states.get(name, "missing") for name in formal_modules
        },
        "pending_module_operations": module_model.search_count(
            [("state", "in", ["to install", "to upgrade", "to remove"])]
        ),
        "demo_fixture_module_count": module_model.search_count(
            [
                ("name", "in", list(DEMO_FIXTURE_MODULES)),
                ("state", "=", "installed"),
            ]
        ),
        "business_record_counts": business_counts,
        "historical_data_imported": any(business_counts.values()),
        "admin_login": target_admin.login if len(target_admin) == 1 else None,
        "active_admin_count": len(active_admins),
        "active_admin_is_target": (
            len(target_admin) == 1
            and len(active_admins) == 1
            and active_admins.id == target_admin.id
        ),
        "seed_enabled": config.get_param("sc.bootstrap.seed_enabled", "0"),
        "seed_profile_configured": bool(config.get_param("sc.seed.profile", "")),
        "seed_runtime_overrides": sorted(
            name for name in SEED_OVERRIDE_NAMES if os.environ.get(name)
        ),
        "target_manifests": {
            name: _manifest_state(name) for name in TARGET_MODULES
        },
    }
    odoo_env.cr.rollback()
    return result


def main() -> None:
    if "env" not in globals():
        raise SystemExit("this probe must run through Odoo shell")
    state = collect_state(globals()["env"])
    print("FORMAL_MODULE_STATE=" + json.dumps(state, sort_keys=True))


if __name__ == "__main__":
    main()

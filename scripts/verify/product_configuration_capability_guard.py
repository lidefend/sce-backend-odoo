#!/usr/bin/env python3
"""Validate the product configuration capability declaration.

The manifest is the single machine-readable fact for what the login workspace,
business configuration, controlled system parameters, platform administration
and support diagnostics expose to each audience. This guard checks structure and
boundaries only; it does not claim that every declared capability is implemented.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "config/product_configuration_capability_v1.json"
MODULE_MANIFEST = ROOT / "addons/smart_construction_core/data/product_configuration_capability_v1.json"
SCHEMA_VERSION = "product_configuration_capability.v1"

REQUIRED_AUDIENCES = {
    "business_full",
    "business_config_admin",
    "platform_admin",
    "support",
}
REQUIRED_HOME_BLOCKS = {
    "today_actions",
    "risks",
    "my_objects",
    "quick_actions",
    "recent",
    "capability_map",
}
REQUIRED_CONFIG_CARDS = {
    "navigation",
    "form",
    "list_search",
    "approval_permissions",
    "numbering",
    "dictionary",
    "system_parameters",
    "change_release",
}
REQUIRED_PARAMETER_CATEGORIES = {
    "business_rules",
    "finance_accounting",
    "notification_collaboration",
    "data_attachment",
    "integration",
    "feature_switches",
}
REQUIRED_CAPABILITY_KEYS = {
    "workspace.capability_map",
    "config.system_parameters",
    "config.change_set",
    "platform.tenant_company",
    "support.diagnostics",
}
ALLOWED_STATUSES = {"available", "partial", "planned"}
SECRET_TERMS = (
    "password",
    "secret",
    "token",
    "api_key",
    "private_key",
    "db_host",
    "database_url",
    "dsn",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def validate(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be %s" % SCHEMA_VERSION)
    if manifest.get("status") != "locked":
        errors.append("status must be locked")

    audiences = {
        _text(row.get("key"))
        for row in manifest.get("audiences", [])
        if isinstance(row, dict)
    }
    missing_audiences = sorted(REQUIRED_AUDIENCES - audiences)
    if missing_audiences:
        errors.append("missing audiences: %s" % ", ".join(missing_audiences))

    home = manifest.get("login_home") if isinstance(manifest.get("login_home"), dict) else {}
    home_blocks = {
        _text(row.get("key"))
        for row in home.get("blocks", [])
        if isinstance(row, dict)
    }
    missing_blocks = sorted(REQUIRED_HOME_BLOCKS - home_blocks)
    if missing_blocks:
        errors.append("missing login home blocks: %s" % ", ".join(missing_blocks))
    empty_policy = home.get("empty_state_policy") if isinstance(home.get("empty_state_policy"), dict) else {}
    for key in (
        "must_explain_scope",
        "must_offer_next_action",
        "must_distinguish_no_permission_no_data_and_not_published",
        "must_not_render_blank_screen",
    ):
        if empty_policy.get(key) is not True:
            errors.append("empty_state_policy.%s must be true" % key)

    cards = {
        _text(row.get("key"))
        for row in manifest.get("configuration_cards", [])
        if isinstance(row, dict)
    }
    missing_cards = sorted(REQUIRED_CONFIG_CARDS - cards)
    if missing_cards:
        errors.append("missing configuration cards: %s" % ", ".join(missing_cards))
    for row in manifest.get("configuration_cards", []):
        if not isinstance(row, dict):
            continue
        key = _text(row.get("key")) or "<empty>"
        for field in ("label", "status", "entry", "authority"):
            if not _text(row.get(field)):
                errors.append("configuration card %s missing %s" % (key, field))
        if _text(row.get("status")) not in ALLOWED_STATUSES:
            errors.append("configuration card %s has invalid status" % key)

    categories = {
        _text(row.get("key"))
        for row in manifest.get("system_parameter_categories", [])
        if isinstance(row, dict)
    }
    missing_categories = sorted(REQUIRED_PARAMETER_CATEGORIES - categories)
    if missing_categories:
        errors.append("missing parameter categories: %s" % ", ".join(missing_categories))
    for row in manifest.get("system_parameter_categories", []):
        if not isinstance(row, dict):
            continue
        key = _text(row.get("key")) or "<empty>"
        if not _text(row.get("label")):
            errors.append("parameter category %s missing label" % key)
        if not row.get("examples"):
            errors.append("parameter category %s missing examples" % key)

    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("capabilities must be a non-empty list")
        capabilities = []
    seen: set[str] = set()
    by_key: dict[str, dict[str, Any]] = {}
    for row in capabilities:
        if not isinstance(row, dict):
            errors.append("capability row must be an object")
            continue
        key = _text(row.get("key"))
        if not key:
            errors.append("capability row missing key")
            continue
        if key in seen:
            errors.append("duplicate capability key: %s" % key)
        seen.add(key)
        by_key[key] = row
        for field in ("label", "audience", "status", "entry", "authority", "description"):
            if not _text(row.get(field)):
                errors.append("capability %s missing %s" % (key, field))
        if _text(row.get("audience")) not in REQUIRED_AUDIENCES:
            errors.append("capability %s has unknown audience" % key)
        if _text(row.get("status")) not in ALLOWED_STATUSES:
            errors.append("capability %s has invalid status" % key)

    missing_keys = sorted(REQUIRED_CAPABILITY_KEYS - seen)
    if missing_keys:
        errors.append("missing required capabilities: %s" % ", ".join(missing_keys))

    for key in ("config.system_parameters",):
        row = by_key.get(key) or {}
        if _text(row.get("entry")) != "product_system_settings":
            errors.append("%s must enter through product_system_settings" % key)
        if _text(row.get("authority")) != "sc.product.system.settings":
            errors.append("%s authority must be sc.product.system.settings" % key)

    for key, row in by_key.items():
        audience = _text(row.get("audience"))
        if audience == "business_full" and key.startswith(("platform.", "support.")):
            errors.append("%s must not be exposed to business_full" % key)
        if audience == "business_config_admin" and key.startswith(("platform.", "support.")):
            errors.append("%s must not be exposed to business_config_admin" % key)
        if audience == "support" and not key.startswith("support."):
            errors.append("%s must not be exposed to support" % key)
        if "ir.config_parameter" in _text(row.get("entry")):
            errors.append("%s must not expose raw ir.config_parameter" % key)

    for value in _iter_strings(manifest):
        lowered = value.lower()
        for term in SECRET_TERMS:
            if term in lowered:
                errors.append("secret-like term %r found in manifest value %r" % (term, value))

    return errors


def validate_runtime_copy(
    config_path: Path = DEFAULT_MANIFEST,
    module_path: Path = MODULE_MANIFEST,
) -> list[str]:
    errors: list[str] = []
    if not module_path.is_file():
        errors.append("runtime module manifest is missing: %s" % module_path)
        return errors
    if module_path.read_bytes() != config_path.read_bytes():
        errors.append("runtime module manifest differs from product manifest")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0]) if args else DEFAULT_MANIFEST
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("[product_configuration_capability_guard] FAIL cannot read %s: %s" % (path, exc))
        return 1
    errors = validate(manifest)
    errors.extend(validate_runtime_copy(path))
    if errors:
        print("[product_configuration_capability_guard] FAIL")
        for error in errors:
            print("- %s" % error)
        return 1
    print(
        "[product_configuration_capability_guard] PASS audiences=%s cards=%s categories=%s capabilities=%s"
        % (
            len(manifest.get("audiences", [])),
            len(manifest.get("configuration_cards", [])),
            len(manifest.get("system_parameter_categories", [])),
            len(manifest.get("capabilities", [])),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

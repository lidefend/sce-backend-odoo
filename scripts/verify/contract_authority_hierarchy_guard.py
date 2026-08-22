#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED = {
    "docs/architecture/contract_authority_hierarchy_v1.md": (
        "Scene-ready contract",
        "Unified Page Contract v2",
        "statusContract.buttonStatus",
        "Fail-Closed Rules",
    ),
    "frontend/apps/web/src/app/contracts/v2/client.ts": (
        "sceneKey?: string | null;",
        "params.scene_key = options.sceneKey",
    ),
    "frontend/apps/web/src/app/resolvers/actionResolver.ts": (
        "sceneKey: String(options?.sceneKey || '').trim() || undefined",
    ),
    "frontend/apps/web/src/views/ActionView.vue": (
        "sceneKey: sceneKey.value || undefined",
    ),
    "frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts": (
        "const sceneKey = String(route.query.scene_key || route.query.scene || '').trim();",
        "sceneKey: sceneKey || undefined",
    ),
    "addons/smart_core/handlers/ui_contract_v2.py": (
        "def _validate_scene_action_binding",
        "REASON_SCENE_ACTION_BINDING_INVALID",
        "def _project_action_group_entitlements",
        "REASON_ACTION_GROUP_ACCESS_DENIED",
    ),
    "addons/smart_core/core/system_init_scene_runtime_surface_builder.py": (
        "def _platform_scene_stub",
        '"strict_contract_mode": True',
        '"scene_tier": "core"',
    ),
    "addons/smart_core/app_config_engine/models/app_nav_config.py": (
        "from psycopg2 import IntegrityError",
        "with self.env.cr.savepoint():",
        "Menu config concurrent create resolved",
    ),
    "frontend/apps/web/src/app/contracts/v2/store.ts": (
        "collectContractV2ButtonStatusById",
        "status.disabled",
    ),
}

FORBIDDEN = {
    "frontend/apps/web/src/pages/ContractFormPage.vue": ("groups_xmlids",),
}

RETIRED = (
    "frontend/apps/web/src/app/contractPolicies.ts",
)


def main() -> int:
    errors: list[str] = []
    for relative, tokens in REQUIRED.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing file: {relative}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in tokens:
            if token not in text:
                errors.append(f"{relative}: missing token: {token}")
    for relative, tokens in FORBIDDEN.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing file: {relative}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in tokens:
            if token in text:
                errors.append(f"{relative}: forbidden token: {token}")
    for relative in RETIRED:
        if (ROOT / relative).exists():
            errors.append(f"retired compatibility file must not exist: {relative}")
    if errors:
        print("[contract_authority_hierarchy_guard] FAIL")
        for error in errors:
            print(f" - {error}")
        return 2
    print("[contract_authority_hierarchy_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

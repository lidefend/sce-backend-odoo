#!/usr/bin/env python3
"""Read-only runtime proof for Platform Capability Explorer intents."""
from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor


EXPECTED_ENTRY_COUNT = int(
    os.environ.get("PLATFORM_CAPABILITY_EXPLORER_EXPECTED_ENTRY_COUNT", "282")
)
EXPECTED_SCENE_BOUND = int(
    os.environ.get("PLATFORM_CAPABILITY_EXPLORER_EXPECTED_SCENE_BOUND", "75")
)
EXPECTED_CENTER_ONLY = int(
    os.environ.get("PLATFORM_CAPABILITY_EXPLORER_EXPECTED_CENTER_ONLY", "207")
)
EXPECTED_UNCLASSIFIED = int(
    os.environ.get("PLATFORM_CAPABILITY_EXPLORER_EXPECTED_UNCLASSIFIED", "0")
)
REQUIRE_RELEASE_AUTHORITY = os.environ.get(
    "PLATFORM_CAPABILITY_EXPLORER_REQUIRE_RELEASE_AUTHORITY", "1"
).strip().lower() in {"1", "true", "yes", "on"}
MAX_LIST_QUERY_COUNT = int(
    os.environ.get("PLATFORM_CAPABILITY_EXPLORER_MAX_QUERIES", "200")
)


def _expect(condition, message):
    if not condition:
        raise AssertionError(message)


def _counts(projection):
    confidence = {}
    scene_status = {}
    release_state = {}
    for row in projection.rows:
        value = row["business_domain"]["confidence"]
        confidence[value] = confidence.get(value, 0) + 1
        value = "bound" if row["scene_usage"]["bound"] else "unbound"
        scene_status[value] = scene_status.get(value, 0) + 1
        value = row["release_state"] or "unknown"
        release_state[value] = release_state.get(value, 0) + 1
    return {
        "entry_count": len(projection.rows),
        "classification_confidence": confidence,
        "scene_status": scene_status,
        "release_states": release_state,
    }


def _concurrent_projection(registry, uid, context, language):
    from odoo import api

    from odoo.addons.smart_core.delivery.platform_capability_explorer import (
        PlatformCapabilityExplorerService,
    )

    with registry.cursor() as cr:
        local_env = api.Environment(cr, uid, dict(context, lang=language))
        projection = PlatformCapabilityExplorerService(local_env).project()
        return {
            "database": projection.meta["runtime_database"],
            "language": projection.meta["language"]["code"],
            "token": projection.meta["catalog_token"],
            "total": projection.meta["total"],
        }


def _permission_cases(handler_module):
    original_tenant = handler_module.tenant_config_scope
    original_platform = handler_module.platform_control_scope

    def decision(tenant_allowed, platform_allowed):
        handler_module.tenant_config_scope = lambda user, env=None: {
            "is_tenant_config_admin": tenant_allowed
        }
        handler_module.platform_control_scope = lambda user, env=None: {
            "is_platform_control_admin": platform_allowed
        }
        return handler_module.capability_explorer_authorization(env)

    try:
        cases = {
            "ordinary": decision(False, False)["allowed"],
            "tenant": decision(True, False)["allowed"],
            "platform": decision(False, True)["allowed"],
        }
    finally:
        handler_module.tenant_config_scope = original_tenant
        handler_module.platform_control_scope = original_platform
    _expect(cases == {
        "ordinary": False,
        "tenant": True,
        "platform": True,
    }, "capability explorer permission matrix mismatch")
    return cases


def probe(env):
    from odoo.addons.smart_core.delivery.platform_capability_explorer import (
        CatalogStaleError,
        PlatformCapabilityExplorerService,
    )
    from odoo.addons.smart_core.handlers import platform_capability_explorer as handlers
    from odoo.addons.smart_core.security.intent_authorization import registered_handlers

    service = PlatformCapabilityExplorerService(env)
    projection = service.project(include_details=True)
    counts = _counts(projection)
    _expect(
        counts["entry_count"] == EXPECTED_ENTRY_COUNT,
        f"entry count mismatch: {counts}; diagnostics={projection.diagnostics}",
    )
    _expect(
        counts["classification_confidence"].get("authoritative_scene_binding", 0)
        == EXPECTED_SCENE_BOUND,
        f"authoritative scene-bound count mismatch: {counts}",
    )
    _expect(
        counts["classification_confidence"].get("center_only", 0)
        == EXPECTED_CENTER_ONLY,
        f"center-only count mismatch: {counts}",
    )
    _expect(
        counts["classification_confidence"].get("unclassified", 0)
        == EXPECTED_UNCLASSIFIED,
        f"unexpected unclassified entries: {counts}",
    )
    _expect(
        projection.diagnostics["scene_authority_available"],
        "scene authority provider unavailable",
    )
    if REQUIRE_RELEASE_AUTHORITY:
        _expect(
            projection.diagnostics["release_authority_available"],
            "release authority provider unavailable",
        )
    _expect(
        projection.diagnostics["conflicts"] == [],
        "scene or release authority conflicts present",
    )
    _expect(
        re.fullmatch(r"sha256:[0-9a-f]{64}", projection.token) is not None,
        "invalid catalog token",
    )

    list_response = service.list_entries({"limit": 25, "offset": 0})
    _expect(list_response["meta"]["total"] == EXPECTED_ENTRY_COUNT, "list total mismatch")
    _expect(
        len(list_response["rows"]) == min(25, EXPECTED_ENTRY_COUNT),
        "list page size mismatch",
    )
    _expect(
        all("native_facts" not in row for row in list_response["rows"]),
        "list unexpectedly returned detail facts",
    )
    _expect(
        list_response["meta"]["diagnostics"]["performance"]["query_count"]
        <= MAX_LIST_QUERY_COUNT,
        "list query count indicates an unexpected N+1 path",
    )
    try:
        service.list_entries(
            {
                "expected_catalog_token": "sha256:" + "0" * 64,
            }
        )
    except CatalogStaleError:
        pass
    else:
        raise AssertionError("stale list token was accepted")

    first_row = list_response["rows"][0]
    detail = service.detail(
        {
            "entry_ref": first_row["entry_ref"],
            "expected_catalog_token": projection.token,
        }
    )
    diagnose = service.diagnose(
        {
            "entry_ref": first_row["entry_ref"],
            "expected_catalog_token": projection.token,
        }
    )
    _expect("native_facts" in detail["entry"], "detail omitted native facts")
    _expect(
        diagnose["native_valid"] == detail["entry"]["diagnostics"]["native_valid"],
        "diagnose did not reuse projection validity",
    )
    detail_json = json.dumps(detail["entry"], ensure_ascii=False)
    for secret_field in ("domain_force", "user_ids", "business_record"):
        _expect(secret_field not in detail_json, "detail exposed protected rule data")

    permission_cases = _permission_cases(handlers)
    registry = registered_handlers(env)
    for intent_name in (
        "platform.capability.explorer.list",
        "platform.capability.explorer.detail",
        "platform.capability.explorer.diagnose",
    ):
        _expect(intent_name in registry, f"intent not registered: {intent_name}")
    public_user = env.ref("base.public_user")
    public_env = env(user=public_user)
    public_decision = handlers.capability_explorer_authorization(public_env)
    _expect(not public_decision["allowed"], "public user was authorized")
    try:
        handlers.PlatformCapabilityExplorerListHandler(public_env).run(
            {"params": {"limit": 1}}
        )
    except Exception as exc:
        _expect(
            exc.__class__.__name__ == "AccessError",
            "public handler denial did not fail closed with AccessError",
        )
    else:
        raise AssertionError("public user executed the list handler")
    current_decision = handlers.capability_explorer_authorization(env)
    _expect(current_decision["allowed"], "tenant config admin was not authorized")
    _expect(
        not current_decision["platform"]["is_platform_control_admin"],
        "tenant database was misclassified as platform control",
    )

    list_handler = handlers.PlatformCapabilityExplorerListHandler(env)
    handler_response = list_handler.run({"params": {"limit": 5}})
    _expect(handler_response["ok"], "list handler failed")
    handler_metrics = handler_response["data"]["meta"]["metrics"]
    _expect(
        "serialization_ms" in handler_metrics,
        "handler serialization timing missing",
    )

    languages = [
        str(env.lang or "zh_CN"),
        "en_US" if str(env.lang or "zh_CN") != "en_US" else "zh_CN",
    ]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                _concurrent_projection,
                env.registry,
                int(env.uid),
                dict(env.context or {}),
                languages[index % len(languages)],
            )
            for index in range(4)
        ]
        concurrent = [future.result() for future in futures]
    _expect(
        all(row["database"] == env.cr.dbname for row in concurrent),
        "concurrent query crossed database identity",
    )
    _expect(
        len({row["token"] for row in concurrent if row["language"] == languages[0]})
        == 1,
        "same-language concurrent token mismatch",
    )
    _expect(
        {
            row["token"]
            for row in concurrent
            if row["language"] == languages[0]
        }.isdisjoint({
            row["token"]
            for row in concurrent
            if row["language"] == languages[1]
        }),
        "language contexts shared a catalog token",
    )

    return {
        "schema": "platform.capability.explorer.runtime_probe.v1",
        "database": env.cr.dbname,
        "catalog_token": projection.token,
        "counts": counts,
        "expected_counts": {
            "entries": EXPECTED_ENTRY_COUNT,
            "scene_bound": EXPECTED_SCENE_BOUND,
            "center_only": EXPECTED_CENTER_ONLY,
            "unclassified": EXPECTED_UNCLASSIFIED,
            "release_authority_required": REQUIRE_RELEASE_AUTHORITY,
        },
        "release_snapshots": projection.diagnostics["release_snapshots"],
        "providers": projection.diagnostics["providers"],
        "performance": {
            "full_projection": projection.diagnostics["performance"],
            "list": list_response["meta"]["diagnostics"]["performance"],
            "handler": handler_metrics,
            "max_allowed_list_query_count": MAX_LIST_QUERY_COUNT,
        },
        "permissions": {
            "matrix": permission_cases,
            "tenant_admin_allowed": current_decision["allowed"],
            "public_user_denied": not public_decision["allowed"],
            "platform_control_on_tenant": current_decision["platform"][
                "is_platform_control_admin"
            ],
        },
        "concurrent_identity_isolation": concurrent,
        "write_operations": 0,
    }


if __name__ == "__main__" and "env" in globals():
    print(json.dumps(probe(env), ensure_ascii=False, indent=2, sort_keys=True))

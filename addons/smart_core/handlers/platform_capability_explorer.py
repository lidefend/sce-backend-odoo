# -*- coding: utf-8 -*-
"""Read-only intents for the Odoo-native Platform Capability Explorer."""
from __future__ import annotations

import time
from typing import Any

from odoo.exceptions import AccessError

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_core.delivery.platform_capability_explorer import (
    PlatformCapabilityExplorerError,
    PlatformCapabilityExplorerService,
    canonical_sha256,
)
from odoo.addons.smart_core.security.platform_admin import (
    platform_control_scope,
    tenant_config_scope,
)


SOURCE_KIND = "platform_capability_explorer_intent_proxy"
SOURCE_AUTHORITIES = (
    "platform_capability_explorer_projection",
    "odoo_native_runtime_metadata",
    "extension_hook:scene_and_release_facts",
)


def capability_explorer_authorization(env) -> dict[str, Any]:
    tenant = tenant_config_scope(env.user, env=env)
    platform = platform_control_scope(env.user, env=env)
    return {
        "allowed": bool(
            tenant.get("is_tenant_config_admin")
            or platform.get("is_platform_control_admin")
        ),
        "instance_scope": "current_database_only",
        "tenant": tenant,
        "platform": platform,
    }


def source_authority_contract() -> dict[str, Any]:
    return {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projection_only": True,
        "no_business_record_authority": True,
        "no_write_authority": True,
        "runtime_carrier": "platform_capability_explorer_intents",
    }


def _canonical_json(value: Any) -> str:
    import json

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


class _PlatformCapabilityExplorerHandler(BaseIntentHandler):
    REQUIRED_GROUPS = []
    TENANT_CONFIG_ADMIN_ALLOWED = True
    MACHINE_ACCESS = "deny"
    ETAG_ENABLED = False
    SOURCE_KIND = SOURCE_KIND
    SOURCE_AUTHORITIES = SOURCE_AUTHORITIES
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls) -> dict[str, Any]:
        return source_authority_contract()

    def _check_permissions(self):
        decision = capability_explorer_authorization(self.env)
        if not decision["allowed"]:
            raise AccessError(
                "PERMISSION_DENIED: platform capability explorer requires "
                "tenant configuration or platform control administration"
            )
        self.authorization_decision = decision
        return True

    def _params(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        nested = payload.get("params")
        return dict(nested) if isinstance(nested, dict) else dict(payload)

    def _handle(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        service = PlatformCapabilityExplorerService(self.env)
        try:
            data = getattr(service, operation)(params)
        except PlatformCapabilityExplorerError as exc:
            return {
                "ok": False,
                "data": {"success": False, "reason_code": exc.code},
                "error": {
                    "code": exc.code,
                    "reason_code": exc.code,
                    "message": str(exc),
                },
                "code": exc.http_status,
                "meta": {
                    "intent": self.INTENT_TYPE,
                    "source_authority": self.source_authority_contract(),
                },
            }
        data.setdefault("meta", {})
        data["meta"]["intent"] = self.INTENT_TYPE
        data["meta"]["source_authority"] = self.source_authority_contract()
        data["meta"]["metrics"] = {
            "projection": dict(
                ((data["meta"].get("diagnostics") or {}).get("performance") or {})
            ),
            "handler_ms": int((time.perf_counter() - started) * 1000),
        }
        serialization_started = time.perf_counter()
        _canonical_json(data)
        data["meta"]["metrics"]["serialization_ms"] = int(
            (time.perf_counter() - serialization_started) * 1000
        )
        data["meta"]["metrics"]["response_sha256"] = canonical_sha256(data)
        return {
            "ok": True,
            "data": data,
            "meta": {
                "intent": self.INTENT_TYPE,
                "source_authority": self.source_authority_contract(),
            },
        }


class PlatformCapabilityExplorerListHandler(_PlatformCapabilityExplorerHandler):
    INTENT_TYPE = "platform.capability.explorer.list"
    DESCRIPTION = "List Odoo-native business entries with authoritative joins"
    VERSION = "1.0.0"

    def handle(self, payload=None, ctx=None):
        return self._handle("list_entries", self._params(payload))


class PlatformCapabilityExplorerDetailHandler(_PlatformCapabilityExplorerHandler):
    INTENT_TYPE = "platform.capability.explorer.detail"
    DESCRIPTION = "Read one Odoo-native business entry and its technical summary"
    VERSION = "1.0.0"

    def handle(self, payload=None, ctx=None):
        return self._handle("detail", self._params(payload))


class PlatformCapabilityExplorerDiagnoseHandler(_PlatformCapabilityExplorerHandler):
    INTENT_TYPE = "platform.capability.explorer.diagnose"
    DESCRIPTION = "Diagnose native validity, scene assignment and publication state"
    VERSION = "1.0.0"

    def handle(self, payload=None, ctx=None):
        return self._handle("diagnose", self._params(payload))

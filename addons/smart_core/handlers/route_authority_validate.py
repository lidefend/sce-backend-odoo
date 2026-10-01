# -*- coding: utf-8 -*-
from __future__ import annotations

from ..core.base_handler import BaseIntentHandler
from ..core.intent_execution_result import IntentExecutionResult
from ..delivery.menu_service import MenuService
from ..identity.identity_resolver import IdentityResolver


def _positive_int(value) -> int:
    try:
        parsed = int(value or 0)
    except Exception:
        return 0
    return parsed if parsed > 0 else 0


class RouteAuthorityValidateHandler(BaseIntentHandler):
    INTENT_TYPE = "route.authority.validate"
    DESCRIPTION = "Validate a delivered route authority against current session and record scope"
    VERSION = "1.0.0"
    SOURCE_KIND = "route_authority_runtime_validation"
    SOURCE_AUTHORITIES = ("route_authority", "ir.model.access", "ir.rule", "allowed_company_ids")
    REQUIRED_GROUPS = []

    def _params(self, payload) -> dict:
        params = {}
        if isinstance(payload, dict):
            inner = payload.get("params")
            params.update(inner if isinstance(inner, dict) else payload)
        if isinstance(getattr(self, "params", None), dict):
            params.update(self.params)
        return params

    def _deny(self, reason: str) -> IntentExecutionResult:
        return IntentExecutionResult(
            ok=False,
            error={"code": 403, "message": "route authority denied", "reason_code": reason},
            meta={"intent": self.INTENT_TYPE, "version": self.VERSION},
            code=403,
        )

    def handle(self, payload=None, ctx=None):
        params = self._params(payload)
        if params.get("work_item_origin") is not None:
            from ..core.work_item_action_authority import validate_work_item_action_origin
            from ..utils.extension_hooks import call_extension_hook_first
            model, record_id = str(params.get("model") or ""), _positive_int(params.get("record_id"))
            try:
                validate_work_item_action_origin(params["work_item_origin"], model=model, record_id=record_id, method_name=None,
                    authorize=lambda origin, **target: call_extension_hook_first(
                        self.env, "smart_core_authorize_work_item_origin", self.env, origin, **target))
            except ValueError as error:
                return self._deny(str(error))
            return IntentExecutionResult(ok=True, data={"allowed": True, "model": model, "record_id": record_id,
                "work_item_origin": params["work_item_origin"]})
        action_id = _positive_int(params.get("action_id"))
        if not action_id:
            return self._deny("ROUTE_ACTION_REQUIRED")

        resolver = IdentityResolver(self.env)
        surface = resolver.build_role_surface(
            resolver.user_group_xmlids(self.env.user),
            [],
            {"workspace.home"},
        )
        menu_service = MenuService(self.env)
        from .system_init import _resolve_startup_delivery_identity, _load_platform_release_gate, _filter_nav_by_release_gate
        from ..delivery.product_policy_service import ProductPolicyService
        identity = _resolve_startup_delivery_identity(self.env, {})
        policy = ProductPolicyService(self.env).get_policy(
            **{key: identity[key] for key in ("product_key", "base_product_key", "edition_key")},
            role_code=surface.get("role_code"), enforce_release=True, enforce_access=True,
        )
        release_gate = _load_platform_release_gate(self.env, product_key=policy["product_key"])
        navigation = menu_service.build_nav(policy=policy, role_surface=surface)
        navigation = [] if release_gate.get("fail_closed") else _filter_nav_by_release_gate(
            navigation, release_gate, env=self.env,
        )[0]
        authority = menu_service.build_route_authority(surface, nav=navigation)
        authority = MenuService.filter_route_authority_by_publication(
            authority, filter_nodes=lambda nodes: [] if release_gate.get("fail_closed") else
                _filter_nav_by_release_gate(nodes, release_gate, env=self.env)[0],
        )
        entries = [
            row
            for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions")
            for row in authority.get(bucket) or []
            if isinstance(row, dict) and _positive_int(row.get("action_id")) == action_id
        ]
        if len(entries) != 1:
            if any(_positive_int(row.get("action_id")) == action_id and row.get("reason_code") == "PRODUCT_ENTRY_NOT_RELEASED"
                   for row in authority.get("denied_actions") or []):
                return self._deny("PRODUCT_ENTRY_NOT_RELEASED")
            return self._deny("ROUTE_ACTION_NOT_AUTHORIZED")
        entry = entries[0]
        requirements = entry.get("context_requirements") if isinstance(entry.get("context_requirements"), dict) else {}
        for key in requirements.get("required_query") or []:
            if not _positive_int(params.get(str(key))):
                return self._deny("ROUTE_CONTEXT_REQUIRED")

        company_key = str(requirements.get("company_query") or "").strip()
        selected_record_key = str(requirements.get("selected_record_query") or "").strip()
        record_key = str(requirements.get("record_query") or "").strip()
        company_id = _positive_int(params.get(company_key)) if company_key else 0
        selected_record_id = _positive_int(params.get(selected_record_key)) if selected_record_key else 0
        record_id = _positive_int(params.get(record_key)) if record_key else 0
        if company_id and company_id not in self.env.companies.ids:
            return self._deny("ROUTE_COMPANY_SCOPE_DENIED")

        record_model = str(requirements.get("record_model") or "").strip()
        if record_model and record_id:
            if record_model not in self.env:
                return self._deny("ROUTE_CONTEXT_MODEL_MISSING")
            record = self.env[record_model].browse(record_id).exists()
            if not record:
                return self._deny("ROUTE_CONTEXT_RECORD_DENIED")
            try:
                record.check_access_rule("read")
            except Exception:
                return self._deny("ROUTE_CONTEXT_RECORD_DENIED")
            selected_record_field = str(requirements.get("record_selected_context_field") or "").strip()
            company_field = str(requirements.get("record_company_field") or "").strip()
            if selected_record_field and selected_record_id and _positive_int(getattr(record, selected_record_field, None).id) != selected_record_id:
                return self._deny("ROUTE_RECORD_CONTEXT_SCOPE_DENIED")
            if company_field and company_id and _positive_int(getattr(record, company_field, None).id) != company_id:
                return self._deny("ROUTE_COMPANY_SCOPE_DENIED")

        return IntentExecutionResult(
            ok=True,
            status="success",
            data={
                "allowed": True,
                "action_id": action_id,
                "menu_id": _positive_int(entry.get("menu_id")),
                "model": str(entry.get("model") or ""),
                "action_xmlid": str(entry.get("action_xmlid") or ""),
                "route_kind": str(entry.get("route_kind") or ""),
            },
            meta={"intent": self.INTENT_TYPE, "version": self.VERSION, "source_kind": self.SOURCE_KIND},
        )

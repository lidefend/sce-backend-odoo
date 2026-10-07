# -*- coding: utf-8 -*-
from __future__ import annotations

from ..core.base_handler import BaseIntentHandler
from ..core.intent_execution_result import IntentExecutionResult
from ..delivery.runtime_route_authority import build_runtime_route_authority


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

    def _load_relation_contract(self, *, model, record_id, action_id, menu_id):
        # Same fresh readonly native projection as execute_button's authority
        # reader. Neither metadata elevation nor the origin grants data rights.
        from .ui_contract_v2 import UiContractV2Handler
        result = UiContractV2Handler(
            self.env, su_env=self.su_env, request=self.request, context=self.context,
            payload={"params": {"op": "model", "model": model, "record_id": record_id,
                "action_id": action_id, "menu_id": menu_id, "view_type": "form",
                "render_profile": "readonly", "delivery_profile": "full", "client_type": "web_pc",
                "accepted_contract_versions": ["2.0.x"], "client_contract_capabilities": [
                    "container_tree.v2", "data_source.v2", "action_rule.v2", "relation_entry.v2", "status_contract.v2"]}},
        ).handle()
        envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        if not isinstance(envelope, dict) or envelope.get("ok") is not True or not isinstance(envelope.get("data"), dict):
            raise ValueError("ROUTE_RELATION_CONTRACT_UNAVAILABLE")
        return envelope["data"]

    def _validate_relation_parent_entry(self, action_id, menu_id, model):
        # Do not forward untrusted query/context from the child. Contextual
        # parents requiring additional query authority therefore fail closed.
        result = type(self)(self.env, su_env=self.su_env, request=self.request, context=self.context,
                           payload={"params": {"action_id": action_id}}).handle()
        envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        data = envelope.get("data", {}) if isinstance(envelope, dict) else {}
        return not (isinstance(envelope, dict) and envelope.get("ok") is True
                    and data.get("allowed") is True and data.get("action_id") == action_id
                    and data.get("menu_id") == menu_id and data.get("model") == model)

    def _validate_relation_route(self, params):
        from ..core.relation_action_authority import positive_relation_id, validate_relation_action_origin
        model = params.get("model")
        record_id = positive_relation_id(params.get("record_id"))
        action_id = positive_relation_id(params.get("action_id"))
        menu_id = positive_relation_id(params.get("menu_id"))
        if (not isinstance(model, str) or model not in self.env or not record_id or not action_id or not menu_id
                or params.get("access_mode") != "read" or params.get("render_profile") != "readonly"
                or params.get("route_path") != f"/r/{model}/{record_id}"
                or params.get("work_item_origin") is not None):
            return self._deny("ROUTE_RELATION_READ_RECORD_REQUIRED")
        try:
            validate_relation_action_origin(
                self.env, params["relation_origin"], model=model, record_id=record_id,
                target_action_id=action_id, target_menu_id=menu_id,
                load_contract=self._load_relation_contract, validate_entry=self._validate_relation_parent_entry,
            )
            child = self.env[model].browse(record_id).exists()
            if not child:
                return self._deny("ROUTE_RELATION_CHILD_NOT_FOUND")
            child.check_access_rights("read")
            child.check_access_rule("read")
            child.check_field_access_rights("read", None)
            contract = self._load_relation_contract(model=model, record_id=record_id, action_id=action_id, menu_id=menu_id)
            if contract.get("statusContract", {}).get("globalStatus", {}).get("effectiveRecordCapabilities", {}).get("read") is not True:
                return self._deny("ROUTE_RELATION_CHILD_CONTRACT_DENIED")
        except Exception:
            return self._deny("ROUTE_RELATION_ORIGIN_DENIED")
        return IntentExecutionResult(ok=True, data={"allowed": True, "model": model, "record_id": record_id,
            "action_id": action_id, "menu_id": menu_id, "access_mode": "read", "render_profile": "readonly",
            "route_path": params["route_path"]})

    def handle(self, payload=None, ctx=None):
        params = self._params(payload)
        if params.get("relation_origin") is not None:
            return self._validate_relation_route(params)
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

        # One navigation contract owns both the rendered tree and its route
        # authority (``handlers/system_init.py``), and ``sc.product.policy``
        # exposes that same published authority to server-side consumers.  A
        # second derivation here would let this gate answer a different
        # question than the client asked.
        authority = build_runtime_route_authority(self.env)
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

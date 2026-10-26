# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

from odoo.exceptions import AccessError, UserError

from ..core.base_handler import BaseIntentHandler
try:
    from ..core.project_context import record_scope_denied_response
except ImportError:  # pragma: no cover - compatibility for lightweight boundary tests
    from ..core.project_context import project_scope_denied_response as record_scope_denied_response
try:
    from ..core.project_context import record_in_business_scope
except ImportError:  # pragma: no cover - compatibility for lightweight boundary tests
    from ..core.project_context import record_in_project_scope
    try:
        from ..core.project_context import selected_record_context_id_from_context
    except ImportError:  # pragma: no cover - compatibility for older lightweight boundary tests
        from ..core.project_context import selected_project_id_from_context as selected_record_context_id_from_context

    def record_in_business_scope(env_model, record_id, params=None, context=None):
        return record_in_project_scope(env_model, record_id, selected_record_context_id_from_context(params, context))
from ..core.request_params import parse_bool, parse_positive_int
from ..core.native_onchange_spec import build_native_onchange_spec, normalize_native_onchange_values, NativeOnchangeSpecError
from ..core.draft_feedback import (
    CAPABILITY as FEEDBACK_DRAFT_CAPABILITY,
    DraftFeedbackError,
    decode_request as decode_feedback_request,
    evaluate as evaluate_feedback,
)
from ..core.unified_page_contract_v2_assembler import assemble_unified_page_patch_v2
from ..core.unified_page_contract_lite_preview import with_lite_preview_if_requested
from ..utils.reason_codes import normalize_onchange_reason_code


class ApiOnchangeHandler(BaseIntentHandler):
    INTENT_TYPE = "api.onchange"
    DESCRIPTION = "Contract-driven onchange roundtrip"
    VERSION = "1.1.0"
    REQUIRED_GROUPS = ["smart_core.group_smart_core_data_operator"]
    ACL_MODE = "explicit_check"
    SOURCE_KIND = "odoo_onchange_proxy"
    SOURCE_AUTHORITIES = ("odoo.onchange", "ir.model.fields", "ir.ui.view")
    FEEDBACK_MESSAGE_CAPABILITY = "form.feedback.message.v1"

    def _with_v2_patch_if_requested(self, response: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(response, dict) or not isinstance(params, dict):
            return response
        contract_version = str(
            params.get("contract_version")
            or params.get("contractVersion")
            or params.get("patch_contract_version")
            or params.get("patchContractVersion")
            or ""
        ).strip()
        include_v2 = parse_bool(params.get("include_v2_patch"), False) or parse_bool(params.get("includeV2Patch"), False)
        if not include_v2 and not contract_version.startswith("2."):
            return response
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        patch = assemble_unified_page_patch_v2(
            data,
            action_id="api.onchange.patch",
            request_id=str(params.get("request_id") or params.get("requestId") or "request.api.onchange.v2.patch"),
        )
        out = dict(response)
        out["unified_page_patch_v2"] = patch
        meta = dict(out.get("meta") or {})
        meta["unified_page_patch_version"] = (patch.get("meta") or {}).get("contractVersion")
        out["meta"] = meta
        return out

    def _err(self, code: int, message: str):
        return {"ok": False, "error": {"code": code, "message": message}, "code": code}

    def _onchange_error(self, code: int, reason_code: str, message: str):
        response = self._err(code, message)
        response["error"]["reason_code"] = reason_code
        return response

    def _valid_native_result(self, result: Any) -> bool:
        if not isinstance(result, dict):
            return False
        for key in ("value", "domain", "modifiers_patch"):
            if key in result and not isinstance(result[key], dict):
                return False
        if "line_patches" in result and (
            not isinstance(result["line_patches"], list)
            or any(not isinstance(item, dict) for item in result["line_patches"])
        ):
            return False
        if "warning" in result:
            warning = result["warning"]
            if not isinstance(warning, dict) and not (
                isinstance(warning, list) and all(isinstance(item, dict) for item in warning)
            ):
                return False
        return True

    def _feedback_err(self, exc: DraftFeedbackError):
        return {
            "ok": False,
            "code": exc.http_status,
            "error": {
                "code": exc.http_status,
                "reason_code": exc.code,
                "message": "草稿反馈暂时不可用",
                "details": exc.public_details(),
            },
        }

    def _feedback_record_id(self, params: Dict[str, Any]):
        for key in ("id", "res_id", "record_id"):
            raw = params.get(key)
            if raw in (None, False, ""):
                continue
            try:
                record_id = int(raw)
            except Exception as exc:
                raise DraftFeedbackError("FEEDBACK_CONFIG_INVALID", f"feedback_evaluation.{key}") from exc
            if record_id <= 0:
                raise DraftFeedbackError("FEEDBACK_CONFIG_INVALID", f"feedback_evaluation.{key}")
            return record_id
        return 0

    def _handle_feedback_evaluation(self, env_model, params: Dict[str, Any]):
        block = params.get("feedback_evaluation")
        request = decode_feedback_request(block)
        request_id = request["request_id"]
        values = params.get("values")
        changed_fields = params.get("changed_fields")
        if type(values) is not dict or values:
            raise DraftFeedbackError("FEEDBACK_CONFIG_INVALID", "values", request_id)
        if type(changed_fields) is not list or changed_fields:
            raise DraftFeedbackError("FEEDBACK_CONFIG_INVALID", "changed_fields", request_id)
        include_v2 = parse_bool(params.get("include_v2_patch"), False) or parse_bool(
            params.get("includeV2Patch"), False,
        )
        contract_version = str(
            params.get("contract_version") or params.get("contractVersion") or ""
        ).strip()
        lite_requested = (
            params.get("contractMode") == "lite_preview"
            or params.get("entryPoint") == "api_onchange"
            or params.get("contractVersion") == "2.0.0"
        )
        if include_v2 or contract_version.startswith("2.") or lite_requested:
            raise DraftFeedbackError("FEEDBACK_CONFIG_INVALID", "feedback_evaluation.mode", request_id)
        capabilities = params.get("client_contract_capabilities")
        if (type(capabilities) is not list
                or any(type(value) is not str for value in capabilities)
                or self.FEEDBACK_MESSAGE_CAPABILITY not in capabilities
                or FEEDBACK_DRAFT_CAPABILITY not in capabilities):
            raise DraftFeedbackError(
                "COMPONENT_CAPABILITY_REQUIRED",
                "feedback_evaluation.capability",
                request_id,
            )
        record_id = self._feedback_record_id(params)
        origin = env_model.browse(record_id) if record_id else None
        result = evaluate_feedback(env_model, block, origin=origin)
        return {
            "ok": True,
            "data": {
                "schema_version": "v1",
                "patch": {},
                "modifiers_patch": {},
                "line_patches": [],
                "warnings": [],
                "applied_fields": [],
                "feedback_evaluation": result,
            },
            "meta": {
                "model": str(getattr(env_model, "_name", "") or params.get("model") or ""),
                "intent": self.INTENT_TYPE,
                "version": self.VERSION,
                "feedback_evaluation_version": request["version"],
            },
        }

    def _source_authority_contract(self, model: str) -> Dict[str, Any]:
        return {
            "kind": self.SOURCE_KIND,
            "authorities": list(self.SOURCE_AUTHORITIES),
            "model": str(model or ""),
            "proxy_only": True,
        }

    def _collect_params(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if isinstance(payload, dict):
            if isinstance(payload.get("params"), dict):
                params.update(payload.get("params") or {})
            if isinstance(payload.get("payload"), dict):
                params.update(payload.get("payload") or {})
        if isinstance(self.params, dict):
            params.update(self.params)
        context: Dict[str, Any] = {}
        if isinstance(self.context, dict):
            context.update(self.context)
        if isinstance(payload, dict) and isinstance(payload.get("context"), dict):
            context.update(payload.get("context") or {})
        if isinstance(params.get("context"), dict):
            context.update(params.get("context") or {})
        if context:
            params["context"] = context
        return params

    def _normalize_values(self, env_model, values: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(values, dict):
            return {}
        out: Dict[str, Any] = {}
        for key, val in values.items():
            if key in env_model._fields:
                out[key] = val
        return out

    def _normalize_changed_fields(self, env_model, fields_raw: Any) -> List[str]:
        if isinstance(fields_raw, str):
            fields_raw = [x.strip() for x in fields_raw.split(",") if x.strip()]
        if not isinstance(fields_raw, list):
            return []
        out: List[str] = []
        for item in fields_raw:
            name = str(item or "").strip()
            if not name or name not in env_model._fields:
                continue
            out.append(name)
        return out

    def _normalize_patch(self, env_model, patch_raw: Any) -> Dict[str, Any]:
        if not isinstance(patch_raw, dict):
            return {}
        out: Dict[str, Any] = {}
        for key, value in patch_raw.items():
            name = str(key or "").strip()
            if not name or name not in env_model._fields:
                continue
            out[name] = value
        return out

    def _normalize_domain_patch(self, env_model, domain_raw: Any) -> Dict[str, Any]:
        if not isinstance(domain_raw, dict):
            return {}
        out: Dict[str, Any] = {}
        for key, value in domain_raw.items():
            name = str(key or "").strip()
            if not name or name not in env_model._fields:
                continue
            if isinstance(value, list):
                out[name] = value
        return out

    def _normalize_modifiers_patch(self, env_model, modifiers_raw: Any) -> Dict[str, Dict[str, Any]]:
        if not isinstance(modifiers_raw, dict):
            return {}
        out: Dict[str, Dict[str, Any]] = {}
        for key, bucket in modifiers_raw.items():
            name = str(key or "").strip()
            if not name or name not in env_model._fields:
                continue
            if not isinstance(bucket, dict):
                continue
            normalized: Dict[str, Any] = {}
            for marker in ("invisible", "readonly", "required", "domain"):
                if marker in bucket:
                    normalized[marker] = bucket.get(marker)
            if normalized:
                out[name] = normalized
        return out

    def _normalize_warning_list(self, warning: Any) -> List[Dict[str, str]]:
        warnings: List[Dict[str, str]] = []
        if isinstance(warning, dict):
            warnings.append(
                {
                    "title": str(warning.get("title") or "Onchange warning"),
                    "message": str(warning.get("message") or ""),
                    "reason_code": normalize_onchange_reason_code(warning.get("reason_code") or warning.get("code")),
                }
            )
            return warnings
        if isinstance(warning, list):
            for item in warning:
                if not isinstance(item, dict):
                    continue
                warnings.append(
                    {
                        "title": str(item.get("title") or "Onchange warning"),
                        "message": str(item.get("message") or ""),
                        "reason_code": normalize_onchange_reason_code(item.get("reason_code") or item.get("code")),
                    }
                )
        return warnings

    def _normalize_line_patches(self, env_model, rows_raw: Any) -> List[Dict[str, Any]]:
        if not isinstance(rows_raw, list):
            return []
        out: List[Dict[str, Any]] = []
        for item in rows_raw:
            if not isinstance(item, dict):
                continue
            field = str(item.get("field") or "").strip()
            if not field or field not in env_model._fields:
                continue
            row_patch = self._normalize_line_patch_values(env_model, field, item.get("patch"))
            row_modifiers = self._normalize_line_patch_modifiers(env_model, field, item.get("modifiers_patch"))
            warnings = self._normalize_warning_list(item.get("warnings"))
            row_state = self._normalize_row_state(item, row_patch, warnings)
            normalized: Dict[str, Any] = {
                "field": field,
                "row_key": str(item.get("row_key") or "").strip(),
                "row_id": self._safe_row_id(item.get("row_id")),
                "patch": row_patch,
                "modifiers_patch": row_modifiers,
                "warnings": warnings,
                "row_state": row_state,
                "command_hint": self._command_hint_for_row_state(row_state),
            }
            # keep compatibility for future per-line domain support
            if isinstance(item.get("domain"), list):
                normalized["domain"] = item.get("domain")
            out.append(normalized)
        return out

    def _relation_field_names(self, env_model, field_name: str) -> List[str]:
        field_obj = env_model._fields.get(field_name)
        if not field_obj:
            return []
        ftype = str(getattr(field_obj, "type", "") or "").strip().lower()
        if ftype not in ("one2many", "many2many"):
            return []
        relation = str(getattr(field_obj, "comodel_name", "") or "").strip()
        if not relation or relation not in self.env:
            return []
        try:
            return list((self.env[relation]._fields or {}).keys())
        except Exception:
            return []

    def _relation_model(self, env_model, field_name: str):
        field_obj = env_model._fields.get(field_name)
        if not field_obj:
            return None
        ftype = str(getattr(field_obj, "type", "") or "").strip().lower()
        if ftype not in ("one2many", "many2many"):
            return None
        relation = str(getattr(field_obj, "comodel_name", "") or "").strip()
        if not relation or relation not in self.env:
            return None
        try:
            return self.env[relation]
        except Exception:
            return None

    def _normalize_line_patch_values(self, env_model, field_name: str, patch_raw: Any) -> Dict[str, Any]:
        if not isinstance(patch_raw, dict):
            return {}
        child_model = self._relation_model(env_model, field_name)
        if child_model is None:
            return {}
        allowed = set(getattr(child_model, "_fields", {}).keys())
        if not allowed:
            return {}
        filtered: Dict[str, Any] = {}
        for key, value in patch_raw.items():
            name = str(key or "").strip()
            if not name or name not in allowed:
                continue
            filtered[name] = value
        if not filtered:
            return {}
        # Child line patches carry the same native relation wire objects as the
        # top-level value; normalize them so the frontend consumes one format.
        return normalize_native_onchange_values(child_model, filtered)

    def _normalize_line_patch_modifiers(self, env_model, field_name: str, modifiers_raw: Any) -> Dict[str, Dict[str, Any]]:
        if not isinstance(modifiers_raw, dict):
            return {}
        allowed = set(self._relation_field_names(env_model, field_name))
        if not allowed:
            return {}
        out: Dict[str, Dict[str, Any]] = {}
        for key, bucket in modifiers_raw.items():
            name = str(key or "").strip()
            if not name or name not in allowed:
                continue
            if not isinstance(bucket, dict):
                continue
            normalized: Dict[str, Any] = {}
            for marker in ("invisible", "readonly", "required", "domain"):
                if marker in bucket:
                    normalized[marker] = bucket.get(marker)
            if normalized:
                out[name] = normalized
        return out

    def _read_record_id(self, params: Dict[str, Any]):
        for key in ("id", "res_id", "record_id"):
            raw = params.get(key)
            if raw in (None, False, ""):
                continue
            try:
                record_id = int(raw)
            except Exception:
                return None, self._err(400, f"{key} invalid")
            if record_id < 0:
                return None, self._err(400, f"{key} invalid")
            return record_id, None
        return 0, None

    def _request_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        ctx = dict(params.get("context") or {}) if isinstance(params.get("context"), dict) else {}
        company_id, company_error = parse_positive_int(params.get("company_id"), allow_empty=True)
        if not company_error and company_id:
            ctx["allowed_company_ids"] = [company_id]
            ctx["company_id"] = company_id
        project_id, project_error = parse_positive_int(
            params.get("current_project_id") or params.get("project_id"),
            allow_empty=True,
        )
        if not project_error and project_id:
            ctx["current_project_id"] = project_id
            ctx.setdefault("default_project_id", project_id)
        operation_strategy = str(params.get("operation_strategy") or params.get("operationStrategy") or "").strip()
        if operation_strategy:
            ctx["operation_strategy"] = operation_strategy
        return ctx

    def _normalize_row_state(self, item: Dict[str, Any], row_patch: Dict[str, Any], warnings: List[Dict[str, str]]) -> str:
        raw = str(item.get("row_state") or "").strip().lower()
        if raw in ("create", "update", "remove", "keep"):
            return raw
        row_id = self._safe_row_id(item.get("row_id"))
        if row_id <= 0 and row_patch:
            return "create"
        if row_id > 0 and row_patch:
            return "update"
        if row_id > 0 and not row_patch and not warnings:
            return "remove"
        return "keep"

    def _safe_row_id(self, value: Any) -> int:
        if not str(value or "").strip():
            return 0
        try:
            row_id = int(value)
        except Exception:
            return 0
        return row_id if row_id > 0 else 0

    def _command_hint_for_row_state(self, row_state: str) -> List[int]:
        # x2many command heads in Odoo semantics:
        # create -> 0, update -> 1, remove/unlink -> 2/3, keep -> 4/6 (context-dependent)
        if row_state == "create":
            return [0]
        if row_state == "update":
            return [1]
        if row_state == "remove":
            return [2, 3]
        return [4, 6]

    def handle(self, payload=None, ctx=None):
        payload = payload or {}
        params = self._collect_params(payload)

        model = str(params.get("model") or "").strip()
        if not model:
            return self._err(400, "missing model")
        if model not in self.env:
            return self._err(404, "unknown model")

        context = self._request_context(params)
        env_model = self.env[model].with_context(context)
        record_id, record_id_error = self._read_record_id(params)
        if record_id_error:
            return record_id_error
        if record_id > 0:
            in_scope, scope_meta = record_in_business_scope(env_model, record_id, params, context)
            if not in_scope:
                return record_scope_denied_response(scope_meta)

        try:
            env_model.check_access_rights("read")
        except AccessError:
            return self._err(403, "permission denied")

        if "feedback_evaluation" in params:
            try:
                return self._handle_feedback_evaluation(env_model, params)
            except DraftFeedbackError as exc:
                return self._feedback_err(exc)

        values = self._normalize_values(env_model, params.get("values") if isinstance(params.get("values"), dict) else {})
        changed_fields = self._normalize_changed_fields(env_model, params.get("changed_fields") or params.get("changed"))
        if not changed_fields:
            response = {
                "ok": True,
                "data": {
                    "schema_version": "v1",
                    "patch": {},
                    "modifiers_patch": {},
                    "line_patches": [],
                    "warnings": [],
                    "applied_fields": [],
                },
                "meta": {"model": model, "intent": self.INTENT_TYPE, "version": self.VERSION, "source_authority": self._source_authority_contract(model)},
            }
            response = self._with_v2_patch_if_requested(response, params)
            return with_lite_preview_if_requested(response, params, "api_onchange")

        view_id, view_error = parse_positive_int(params.get("view_id"), allow_empty=True)
        if view_error:
            return self._onchange_error(400, "ONCHANGE_SPEC_INVALID", "联动视图标识无效")
        try:
            if record_id:
                env_model = env_model.browse(record_id).exists()
                if not env_model:
                    return self._err(404, "record not found")
                env_model.check_access_rule("read")
            fields_spec = build_native_onchange_spec(env_model, view_id=view_id or None)
            if any(name not in fields_spec or name not in values for name in changed_fields):
                raise NativeOnchangeSpecError("changed field absent from view or values")
            env_model.check_field_access_rights("read", list(values))
            onchange_result = env_model.onchange(values, changed_fields, fields_spec)
        except NativeOnchangeSpecError:
            return self._onchange_error(422, "ONCHANGE_SPEC_INVALID", "字段联动声明不完整或无效")
        except AccessError:
            return self._onchange_error(403, "ONCHANGE_ACCESS_DENIED", "无权执行字段联动")
        except UserError as exc:
            return self._onchange_error(400, "ONCHANGE_VALIDATION_FAILED", str(exc))
        except Exception:
            return self._onchange_error(500, "ONCHANGE_EXECUTION_FAILED", "字段联动失败，请稍后重试")

        if not self._valid_native_result(onchange_result):
            return self._onchange_error(500, "ONCHANGE_RESPONSE_INVALID", "字段联动返回格式无效")
        try:
            native_values = normalize_native_onchange_values(env_model, onchange_result.get("value", {}))
            line_patches = self._normalize_line_patches(env_model, onchange_result.get("line_patches"))
        except NativeOnchangeSpecError:
            return self._onchange_error(500, "ONCHANGE_RESPONSE_INVALID", "字段联动返回格式无效")
        patch = self._normalize_patch(env_model, native_values)
        domain_patch = self._normalize_domain_patch(env_model, onchange_result.get("domain"))
        warnings = self._normalize_warning_list(onchange_result.get("warning"))

        # Prefer backend-supplied modifier patch if exists, then merge domain as supplement.
        modifiers_patch = self._normalize_modifiers_patch(env_model, onchange_result.get("modifiers_patch"))
        for field_name, field_domain in domain_patch.items():
            prev = modifiers_patch.get(field_name, {})
            prev["domain"] = field_domain
            modifiers_patch[field_name] = prev

        response = {
            "ok": True,
            "data": {
                "schema_version": "v1",
                "patch": patch,
                "modifiers_patch": modifiers_patch,
                "line_patches": line_patches,
                "warnings": warnings,
                "applied_fields": changed_fields,
            },
            "meta": {"model": model, "intent": self.INTENT_TYPE, "version": self.VERSION, "source_authority": self._source_authority_contract(model)},
        }
        response = self._with_v2_patch_if_requested(response, params)
        return with_lite_preview_if_requested(response, params, "api_onchange")

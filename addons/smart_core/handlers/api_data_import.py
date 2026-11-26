# -*- coding: utf-8 -*-
# 📄 smart_core/handlers/api_data_import.py
# Governed collection import: the contract declares ``import`` as a
# collection-scope capability (intent ``api.data.import``); this handler is the
# single executor behind it.

import base64
import binascii
import hashlib
import logging
from typing import Any, Dict, List

from odoo import _
from odoo.exceptions import AccessError, UserError, ValidationError

from ..core.base_handler import BaseIntentHandler
from ..core.request_params import parse_bool
from ..utils.idempotency import (
    apply_idempotency_identity,
    build_idempotency_conflict_response,
    build_idempotency_fingerprint,
    find_recent_audit_entry,
    normalize_request_id,
    replay_window_seconds,
)
from ..utils.reason_codes import (
    REASON_BUSINESS_RULE_FAILED,
    REASON_MISSING_PARAMS,
    REASON_NOT_FOUND,
    REASON_PERMISSION_DENIED,
    REASON_SYSTEM_ERROR,
    REASON_UNSUPPORTED_SOURCE,
    failure_meta_for_reason,
)

_logger = logging.getLogger(__name__)

# The Odoo import kernel owns file parsing, field matching and row validation.
# These are the kernel's own web-client defaults, so this handler drives the
# native logic instead of re-implementing any of it.
IMPORT_KERNEL_MODEL = "base_import.import"
DEFAULT_IMPORT_OPTIONS = {
    "encoding": "",
    "separator": "",
    "quoting": '"',
    "has_headers": True,
    "date_format": "",
    "datetime_format": "",
    "float_thousand_separator": ",",
    "float_decimal_separator": ".",
    "keep_matches": False,
    "advanced": False,
}
PREVIEW_ROWS = 10


class ApiDataImportHandler(BaseIntentHandler):
    """Intent: api.data.import — import rows through the Odoo base_import kernel."""

    INTENT_TYPE = "api.data.import"
    DESCRIPTION = "Governed collection import through the Odoo base_import kernel"
    VERSION = "0.1.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["smart_core.group_smart_core_data_operator"]
    MACHINE_ACCESS = "write"
    ACL_MODE = "explicit_check"
    SOURCE_KIND = "odoo_native_import_proxy"
    SOURCE_AUTHORITIES = (
        "odoo.orm",
        "ir.model.access",
        "ir.rule",
        "ir.model.fields",
        "base_import.import",
    )
    IDEMPOTENCY_WINDOW_SECONDS = 120
    IDEMPOTENCY_EVENT_CODE = "API_DATA_IMPORT"

    # ---- error / authority helpers ----

    def _err(self, code: int, message: str, reason_code: str):
        return {
            "ok": False,
            "error": {
                "code": reason_code,
                "message": message,
                "reason_code": reason_code,
                **failure_meta_for_reason(reason_code),
            },
            "code": code,
        }

    def _source_authority_contract(self, model: str) -> Dict[str, Any]:
        return {
            "kind": self.SOURCE_KIND,
            "authorities": list(self.SOURCE_AUTHORITIES),
            "model": str(model or ""),
            "op": "import",
            "proxy_only": True,
        }

    # ---- idempotency helpers ----

    def _idempotency_window_seconds(self):
        return replay_window_seconds(
            self.IDEMPOTENCY_WINDOW_SECONDS,
            env_key="API_DATA_IMPORT_REPLAY_WINDOW_SEC",
        )

    def _idempotency_fingerprint(self, *, model: str, file_digest: str, fields: List[Any], dry_run: bool, idem_key: str):
        payload = {
            "intent": self.INTENT_TYPE,
            "model": str(model or ""),
            "file_digest": str(file_digest or ""),
            "fields": list(fields or []),
            "dry_run": bool(dry_run),
            "idempotency_key": str(idem_key or ""),
        }
        return build_idempotency_fingerprint(payload)

    def _write_idempotency_audit(self, *, trace_id: str, model: str, idem_key: str, idem_fingerprint: str, result: Dict[str, Any]):
        Audit = self.env.get("sc.audit.log")
        if Audit is None:
            return
        try:
            Audit.write_event(
                event_code=self.IDEMPOTENCY_EVENT_CODE,
                model=model,
                res_id=0,
                action="import",
                after={
                    "idempotency_key": idem_key,
                    "idempotency_fingerprint": idem_fingerprint,
                    "result": result,
                },
                reason="api.data.import idempotency",
                trace_id=trace_id or "",
                company_id=self.env.user.company_id.id if self.env.user and self.env.user.company_id else None,
            )
        except Exception:
            return

    def _idempotency_conflict_response(self, *, request_id: str, idempotency_key: str, idempotency_fingerprint: str, trace_id: str):
        result = build_idempotency_conflict_response(
            intent_type=self.INTENT_TYPE,
            request_id=request_id,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
            include_replay_evidence=False,
        )
        data = result.setdefault("data", {})
        data["idempotency_fingerprint"] = str(idempotency_fingerprint or "")
        data["replay_supported"] = False
        meta = result.setdefault("meta", {})
        meta["trace_id"] = str(trace_id or "")
        return result

    def _with_idempotency_contract(self, data: Dict[str, Any], *, request_id: str, idempotency_key: str, idempotency_fingerprint: str, trace_id: str, deduplicated: bool):
        contract = apply_idempotency_identity(
            data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            idempotency_fingerprint=idempotency_fingerprint,
            trace_id=trace_id,
        )
        contract["idempotent_replay"] = False
        contract["replay_supported"] = False
        contract["replay_window_expired"] = False
        contract["idempotency_replay_reason_code"] = ""
        contract["idempotency_deduplicated"] = bool(deduplicated)
        return contract

    # ---- payload helpers ----

    def _collect_params(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        params = {}
        if isinstance(payload, dict):
            if isinstance(payload.get("context"), dict):
                params.setdefault("context", {}).update(payload.get("context") or {})
            params.update(payload.get("params") or {})
            params.update(payload.get("payload") or {})
        if isinstance(self.params, dict):
            params.update(self.params)
        return params

    def _read_file_payload(self, params: Dict[str, Any]):
        raw = params.get("file") or params.get("content") or ""
        if isinstance(raw, bytes):
            content = raw
        else:
            text = str(raw or "").strip()
            if "," in text and text.lower().startswith("data:"):
                text = text.split(",", 1)[1]
            if not text:
                return b"", self._err(400, "缺少参数 file", REASON_MISSING_PARAMS)
            try:
                content = base64.b64decode(text, validate=True)
            except (binascii.Error, ValueError):
                return b"", self._err(400, "file 不是合法的 base64 内容", REASON_MISSING_PARAMS)
        if not content:
            return b"", self._err(400, "导入文件内容为空", REASON_MISSING_PARAMS)
        return content, None

    def _read_import_options(self, params: Dict[str, Any]) -> Dict[str, Any]:
        options = dict(DEFAULT_IMPORT_OPTIONS)
        raw = params.get("options")
        if isinstance(raw, dict):
            for key, value in raw.items():
                if key in options:
                    options[key] = value
        has_headers = params.get("has_headers")
        if has_headers is None:
            has_headers = params.get("hasHeaders")
        if has_headers is not None:
            options["has_headers"] = parse_bool(has_headers, True)
        limit = params.get("limit")
        try:
            limit_value = int(limit or 0)
        except (TypeError, ValueError):
            limit_value = 0
        if limit_value > 0:
            options["limit"] = limit_value
        return options

    def _read_columns(self, params: Dict[str, Any]):
        raw = params.get("columns")
        if raw is None:
            return None, None
        if not isinstance(raw, list):
            return None, self._err(400, "columns 必须是数组", REASON_MISSING_PARAMS)
        return [str(item or "") for item in raw], None

    def _read_fields(self, params: Dict[str, Any]):
        raw = params.get("fields")
        if raw is None:
            return None, None
        if not isinstance(raw, list):
            return None, self._err(400, "fields 必须是数组", REASON_MISSING_PARAMS)
        fields: List[Any] = []
        for item in raw:
            value = str(item or "").strip()
            fields.append(value or False)
        return fields, None

    @staticmethod
    def _suggested_fields(headers: List[str], matches: Any) -> List[Any]:
        """Kernel field suggestion, aligned to the file's own column order."""

        if not isinstance(matches, dict):
            return [False for _header in headers]
        fields: List[Any] = []
        for index, _header in enumerate(headers):
            # Native base_import keys suggestions by column position, not by
            # header text; repeated headers may map to distinct relation paths.
            value = matches.get(index, matches.get(str(index)))
            if isinstance(value, (list, tuple)):
                value = "/".join([str(part) for part in value if str(part or "").strip()])
            fields.append(str(value or "").strip() or False)
        return fields

    def _import_kernel(self):
        Kernel = self.env.get(IMPORT_KERNEL_MODEL)
        return Kernel

    @staticmethod
    def _row_label(rows, row_offset):
        if not isinstance(rows, dict) or type(rows.get("from")) is not int or type(rows.get("to")) is not int:
            return ""
        first, last = rows["from"] + row_offset, rows["to"] + row_offset
        return (_("第 %s 行") % first) if first == last else (_("第 %s 至 %s 行") % (first, last))

    def _kernel_result(self, result: Any, row_offset=1) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"ids": [], "messages": []}
        return {
            "ids": [int(item) for item in (result.get("ids") or []) if item],
            "messages": [
                {
                    "type": str(row.get("type") or "error"),
                    "message": str(row.get("message") or ""),
                    "record": row.get("record") if isinstance(row.get("record"), dict) else None,
                    "rows": row.get("rows") if isinstance(row.get("rows"), dict) else None,
                    "field": row.get("field"),
                    "field_path": row.get("field_path"),
                    "row_label": self._row_label(row.get("rows"), row_offset),
                }
                for row in (result.get("messages") or [])
                if isinstance(row, dict)
            ],
        }

    @staticmethod
    def _wizard_contract():
        return {
            "schema": "native_import.v1", "authority": IMPORT_KERNEL_MODEL,
            "title": _("批量导入"), "file_label": _("文件"),
            "row_count_label": _("数据行数"), "column_label": _("文件列"),
            "field_label": _("系统字段"), "preview_label": _("数据预览"),
            "ignore_label": _("不导入此列"), "validate_label": _("校验数据"),
            "execute_label": _("确认导入"), "cancel_label": _("取消"),
            "valid_label": _("校验通过，可以导入"),
            "mapping_changed_label": _("字段映射已变更，请重新校验"),
            "choose_file_label": _("选择导入文件"), "empty_file_label": _("尚未选择文件"),
            "preview_action_label": _("读取预览"), "options_label": _("文件解析选项"),
            "headers_label": _("首行为列标题"), "templates_label": _("原生导入模板"),
            "file_accept": ".csv,.xls,.xlsx,.ods",
            "done_label": _("完成并返回列表"), "result_label": _("导入结果"),
            "imported_label": _("成功记录数"), "record_ids_label": _("记录编号"),
        }

    @staticmethod
    def _option_fields():
        # Parsing settings understood by base_import; values remain kernel-owned.
        return [
            {"name": name, "label": _(label), "type": kind}
            for name, label, kind in [
                ("has_headers", "首行为列标题", "boolean"),
                ("encoding", "编码（留空自动检测）", "text"),
                ("separator", "分隔符（留空自动检测）", "text"),
                ("quoting", "文本引用符", "text"),
                ("date_format", "日期格式（留空自动检测）", "text"),
                ("datetime_format", "日期时间格式（留空自动检测）", "text"),
                ("float_thousand_separator", "千位分隔符", "text"),
                ("float_decimal_separator", "小数分隔符", "text"),
            ]
        ]

    # ---- execution ----

    def handle(self, payload=None, ctx=None):
        payload = payload or {}
        params = self._collect_params(payload)
        model = str(params.get("model") or params.get("res_model") or "").strip()
        if not model:
            return self._err(400, "缺少参数 model", REASON_MISSING_PARAMS)
        if model not in self.env:
            return self._err(404, f"未知模型: {model}", REASON_NOT_FOUND)
        Kernel = self._import_kernel()
        if Kernel is None:
            return self._err(501, "当前部署未提供 base_import 导入内核", REASON_UNSUPPORTED_SOURCE)

        if params.get("phase") == "describe":
            try:
                Model = self.env[model]
                Model.check_access_rights("create")
                templates = Model.get_import_templates() if callable(getattr(Model, "get_import_templates", None)) else []
                return {"ok": True, "data": {
                    "model": model, "phase": "describe", "file_name": "", "file_digest": "",
                    "headers": [], "mapping": [], "preview": [], "file_length": 0,
                    "native_fields": Kernel.get_fields_tree(model), "native_options": dict(DEFAULT_IMPORT_OPTIONS),
                    "native_templates": templates, "wizard": self._wizard_contract(),
                    "update_export": {
                        "enabled": bool(Model.check_access_rights("read", raise_exception=False)
                            and (self.env.is_admin() or self.env.user.has_group("base.group_allow_export"))),
                        "fields": list(dict.fromkeys(["id", Model._rec_name or "id"])),
                        "import_compatible": True,
                        "label": _("下载更新标识文件"),
                        "empty_label": _("当前范围没有可导出的记录"),
                    },
                    "option_fields": self._option_fields(),
                    "dry_run": True, "ids": [], "imported_count": 0, "messages": [], "error_count": 0, "valid": False,
                }, "meta": {"source_authority": self._source_authority_contract(model)}}
            except AccessError:
                return self._err(403, "无导入权限", REASON_PERMISSION_DENIED)

        file_name = str(params.get("file_name") or params.get("fileName") or "").strip()
        if not file_name:
            return self._err(400, "缺少参数 file_name", REASON_MISSING_PARAMS)
        content, file_error = self._read_file_payload(params)
        if file_error:
            return file_error
        dry_run = parse_bool(params.get("dry_run"), False)
        phase = str(params.get("phase") or ("validate" if dry_run else "execute"))
        if phase not in {"inspect", "validate", "execute"}:
            return self._err(400, "未知导入阶段", REASON_MISSING_PARAMS)
        if phase == "execute" and dry_run:
            return self._err(400, "dry_run 与执行阶段冲突", REASON_MISSING_PARAMS)
        dry_run = phase != "execute"
        options = self._read_import_options(params)
        columns, columns_error = self._read_columns(params)
        if columns_error:
            return columns_error
        fields, fields_error = self._read_fields(params)
        if fields_error:
            return fields_error

        env_model = self.env[model]
        try:
            env_model.check_access_rights("create")
        except AccessError as exc:
            _logger.warning("api.data.import create denied on %s: %s", model, exc)
            return self._err(403, "无导入权限", REASON_PERMISSION_DENIED)

        file_digest = hashlib.sha256(content).hexdigest()
        file_type = str(params.get("file_type") or params.get("fileType") or "").strip()

        trace_id = ""
        if isinstance(self.context, dict):
            trace_id = self.context.get("trace_id") or ""
        request_id = normalize_request_id(params.get("request_id"), prefix="adi_req")
        idempotency_key = str(params.get("idempotency_key") or "").strip() or request_id

        if not dry_run:
            idempotency_fingerprint = self._idempotency_fingerprint(
                model=model,
                file_digest=file_digest,
                fields=fields or [],
                dry_run=False,
                idem_key=idempotency_key,
            )
            recent_entry = find_recent_audit_entry(
                self.env,
                event_code=self.IDEMPOTENCY_EVENT_CODE,
                idempotency_key=idempotency_key,
                window_seconds=self._idempotency_window_seconds(),
                limit=20,
                extra_domain=[("model", "=", model)],
            )
            if recent_entry:
                payload_after = recent_entry.get("payload") or {}
                recent_fingerprint = str(payload_after.get("idempotency_fingerprint") or "")
                if recent_fingerprint and recent_fingerprint != idempotency_fingerprint:
                    return self._idempotency_conflict_response(
                        request_id=request_id,
                        idempotency_key=idempotency_key,
                        idempotency_fingerprint=idempotency_fingerprint,
                        trace_id=trace_id,
                    )
                if recent_fingerprint and recent_fingerprint == idempotency_fingerprint:
                    replay_result = payload_after.get("result")
                    base_data = replay_result if isinstance(replay_result, dict) else {
                        "model": model,
                        "file_name": file_name,
                        "dry_run": False,
                    }
                    data = self._with_idempotency_contract(
                        dict(base_data),
                        request_id=request_id,
                        idempotency_key=idempotency_key,
                        idempotency_fingerprint=idempotency_fingerprint,
                        trace_id=trace_id,
                        deduplicated=True,
                    )
                    return {
                        "ok": True,
                        "data": data,
                        "meta": {
                            "trace_id": trace_id,
                            "write_mode": "import",
                            "source": "portal-shell",
                            "source_authority": self._source_authority_contract(model),
                        },
                    }

        try:
            # base_import.import.file is declared "raw binary (not base64)":
            # the kernel reads the cached bytes directly as CSV/XLS content, so
            # the transport-level base64 payload has already been decoded into
            # ``content`` above and must be handed over as-is.
            importer = Kernel.create({
                "res_model": model,
                "file": content,
                "file_name": file_name,
                "file_type": file_type,
            })
        except (UserError, ValidationError) as exc:
            return self._err(400, str(exc) or "导入内核拒绝该文件", REASON_BUSINESS_RULE_FAILED)
        except AccessError as exc:
            _logger.warning("api.data.import kernel create denied: %s", exc)
            return self._err(403, "无导入权限", REASON_PERMISSION_DENIED)
        except Exception as exc:
            _logger.exception("api.data.import kernel init failed on %s", model)
            return self._err(500, str(exc), REASON_SYSTEM_ERROR)

        preview = importer.parse_preview(dict(options), count=PREVIEW_ROWS)
        if isinstance(preview, dict) and preview.get("error"):
            return self._err(400, str(preview.get("error") or "导入文件解析失败"), REASON_BUSINESS_RULE_FAILED)

        headers = [str(item or "") for item in (preview.get("headers") or [])]
        if not headers:
            headers = [_("列 %s") % (index + 1) for index in range(len(preview.get("preview") or []))]
        if columns is None:
            columns = headers
        if fields is None:
            fields = self._suggested_fields(headers, preview.get("matches"))
        if phase != "inspect" and not any(fields):
            return self._err(400, "未能在导入文件中匹配到任何可导入字段", REASON_BUSINESS_RULE_FAILED)

        base_data: Dict[str, Any] = {
            "model": model,
            "file_name": file_name,
            "file_digest": file_digest,
            "headers": headers,
            "mapping": fields,
            "preview": preview.get("preview") or [],
            "file_length": max(0, int(preview.get("file_length") or 0) - (1 if headers and options.get("has_headers") else 0)),
            "advanced_mode": bool(preview.get("advanced_mode")),
            "native_fields": preview.get("fields") or [],
            "native_options": preview.get("options") or dict(options),
            "phase": phase,
            "wizard": self._wizard_contract(),
        }

        if phase == "inspect":
            return {"ok": True, "data": dict(base_data, dry_run=True, ids=[], imported_count=0,
                                               messages=[], error_count=0, valid=False),
                    "meta": {"write_mode": "import_inspect", "source_authority": self._source_authority_contract(model)}}

        try:
            result = importer.execute_import(list(fields), list(columns), dict(options), dryrun=bool(dry_run))
        except (UserError, ValidationError) as exc:
            _logger.warning("api.data.import business rule blocked on %s: %s", model, exc)
            return self._err(400, str(exc) or "导入被业务规则拒绝", REASON_BUSINESS_RULE_FAILED)
        except AccessError as exc:
            _logger.warning("api.data.import AccessError on %s: %s", model, exc)
            return self._err(403, "无导入权限", REASON_PERMISSION_DENIED)
        except Exception as exc:
            _logger.exception("api.data.import failed on %s", model)
            return self._err(500, str(exc), REASON_SYSTEM_ERROR)

        kernel_result = self._kernel_result(result, row_offset=2 if headers and options.get("has_headers") else 1)
        errors = [row for row in kernel_result["messages"] if row.get("type") == "error"]
        data = dict(base_data)
        data.update(
            {
                "dry_run": bool(dry_run),
                "ids": kernel_result["ids"],
                "imported_count": len(kernel_result["ids"]),
                "messages": kernel_result["messages"],
                "error_count": len(errors),
                "valid": not errors,
            }
        )

        if dry_run:
            return {
                "ok": True,
                "data": data,
                "meta": {
                    "trace_id": trace_id,
                    "write_mode": "import_preview",
                    "source": "portal-shell",
                    "source_authority": self._source_authority_contract(model),
                },
            }

        idempotency_fingerprint = self._idempotency_fingerprint(
            model=model,
            file_digest=file_digest,
            fields=fields or [],
            dry_run=False,
            idem_key=idempotency_key,
        )
        data = self._with_idempotency_contract(
            data,
            request_id=request_id,
            idempotency_key=idempotency_key,
            idempotency_fingerprint=idempotency_fingerprint,
            trace_id=trace_id,
            deduplicated=False,
        )
        self._write_idempotency_audit(
            trace_id=trace_id,
            model=model,
            idem_key=idempotency_key,
            idem_fingerprint=idempotency_fingerprint,
            result=data,
        )
        return {
            "ok": True,
            "data": data,
            "meta": {
                "trace_id": trace_id,
                "write_mode": "import",
                "source": "portal-shell",
                "source_authority": self._source_authority_contract(model),
            },
        }

# -*- coding: utf-8 -*-
from datetime import date, datetime
from email.header import decode_header, make_header
from email.utils import parseaddr
import logging
from typing import Any, Dict, List, Optional

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
from .file_download import allowed_file_download_models, resolve_file_download_auth_subject
from ..utils.reason_codes import (
    REASON_MISSING_PARAMS,
    REASON_NOT_FOUND,
    REASON_PERMISSION_DENIED,
    REASON_SYSTEM_ERROR,
    REASON_USER_ERROR,
    failure_meta_for_reason,
)

_logger = logging.getLogger(__name__)


def _activity_status_projection(deadline: Optional[date], today: Optional[date] = None) -> Dict[str, str]:
    reference_date = today or datetime.now().date()
    if deadline and deadline < reference_date:
        return {"code": "overdue", "label": "已逾期"}
    return {"code": "pending", "label": "待处理"}


def _attachment_download_projection(model, res_id, auth_model, auth_res_id, allowed_models):
    enabled = bool(
        auth_model == model
        and int(auth_res_id or 0) == int(res_id)
        and auth_model in allowed_models
    )
    return {
        "can_download": enabled,
        "download_intent": "file.download" if enabled else "",
    }


class ChatterTimelineHandler(BaseIntentHandler):
    INTENT_TYPE = "chatter.timeline"
    DESCRIPTION = "Unified collaboration timeline for message/attachment/audit"
    SOURCE_KIND = "odoo_collaboration_timeline_projection"
    SOURCE_AUTHORITIES = ("mail.message", "ir.attachment", "mail.activity")
    AUXILIARY_AUTHORITIES = ("sc.audit.log",)
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls) -> dict:
        return {
            "kind": cls.SOURCE_KIND,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "auxiliary_authorities": list(cls.AUXILIARY_AUTHORITIES),
            "projection_only": True,
            "rebuildable": True,
            "no_business_fact_authority": cls.NO_BUSINESS_FACT_AUTHORITY,
            "runtime_carrier": cls.INTENT_TYPE,
        }

    def handle(self, payload=None, ctx=None):
        params = self.params if isinstance(self.params, dict) else {}
        model = params.get("model")
        res_id = params.get("res_id") if "res_id" in params else params.get("record_id")
        include_audit = parse_bool(params.get("include_audit"), True)
        trace_id = self.context.get("trace_id") if isinstance(self.context, dict) else ""

        if not model or _is_empty_param(res_id):
            return self._failure(REASON_MISSING_PARAMS, "缺少参数 model/res_id", 400, trace_id)
        limit, limit_error = _read_limit(params.get("limit"), default=40, cap=120)
        if limit_error:
            return self._failure(REASON_USER_ERROR, "limit 无效", 400, trace_id)
        offset, offset_error = _read_offset(params.get("offset"))
        if offset_error:
            return self._failure(REASON_USER_ERROR, "offset 无效", 400, trace_id)
        if model not in self.env:
            return self._failure(REASON_NOT_FOUND, "模型不存在", 404, trace_id)

        res_id, res_id_error = parse_positive_int(res_id)
        if res_id_error:
            return self._failure(REASON_USER_ERROR, "res_id 无效", 400, trace_id)

        try:
            Model = self.env[model]
            Model.check_access_rights("read")
            record = Model.search([("id", "=", res_id)], limit=1)
            if record:
                record.check_access_rule("read")
        except AccessError:
            return self._failure(REASON_NOT_FOUND, "记录不存在", 404, trace_id)
        except UserError as exc:
            return self._failure(REASON_USER_ERROR, str(exc) or "业务规则不允许", 400, trace_id)
        except Exception:
            return self._failure(REASON_SYSTEM_ERROR, "读取协作时间线失败", 500, trace_id)
        if not record:
            return self._failure(REASON_NOT_FOUND, "记录不存在", 404, trace_id)
        try:
            in_scope, scope_meta = record_in_business_scope(
                Model,
                int(record.id),
                params,
                self.context if isinstance(self.context, dict) else {},
            )
        except AccessError:
            return self._failure(REASON_NOT_FOUND, "记录不存在", 404, trace_id)
        if not in_scope:
            return self._failure(REASON_NOT_FOUND, "记录不存在", 404, trace_id)

        try:
            fetch_limit = offset + limit + 1
            can_reply = False
            try:
                Model.check_access_rights("write")
                record.check_access_rule("write")
                can_reply = True
            except AccessError:
                can_reply = False
            messages = self._load_messages(model, record.id, fetch_limit, can_reply=can_reply)
            attachments = self._load_attachments(model, record.id, fetch_limit)
            activity_items = self._load_activities(model, record.id, fetch_limit)
            audit_items = self._load_audit_items(model, record.id, fetch_limit) if include_audit else []
        except AccessError:
            return self._failure(REASON_PERMISSION_DENIED, "无权限读取协作时间线", 403, trace_id)
        except UserError as exc:
            return self._failure(REASON_USER_ERROR, str(exc) or "业务规则不允许", 400, trace_id)
        except Exception as exc:
            _logger.exception("chatter.timeline projection failed for %s/%s", model, res_id)
            return self._failure(REASON_SYSTEM_ERROR, "读取协作时间线失败", 500, trace_id)

        items = messages + attachments + activity_items + audit_items
        items.sort(key=lambda item: item.get("at") or "", reverse=True)
        page_items = items[offset:offset + limit]
        has_more = len(items) > offset + limit

        return {
            "items": page_items,
            "counts": {
                "messages": sum(1 for item in page_items if item.get("type") == "message"),
                "attachments": sum(1 for item in page_items if item.get("type") == "attachment"),
                "activities": sum(1 for item in page_items if item.get("type") == "activity"),
                "audit": sum(1 for item in page_items if item.get("type") == "audit"),
                "total": len(page_items),
            },
            "paging": {
                "offset": offset,
                "limit": limit,
                "next_offset": offset + len(page_items) if has_more else None,
                "has_more": has_more,
            },
            "source_authorities": list(self.SOURCE_AUTHORITIES),
            "auxiliary_authorities": list(self.AUXILIARY_AUTHORITIES) if include_audit else [],
            "source_authority": self.source_authority_contract(),
        }, {
            "source_authorities": list(self.SOURCE_AUTHORITIES),
            "auxiliary_authorities": list(self.AUXILIARY_AUTHORITIES) if include_audit else [],
            "source_authority": self.source_authority_contract(),
        }

    def _failure(self, reason_code: str, message: str, status_code: int, trace_id: str):
        return {
            "ok": False,
            "error": {
                "code": reason_code,
                "message": message,
                "reason_code": reason_code,
                **failure_meta_for_reason(reason_code),
            },
            "data": {"result": {"success": False, "reason_code": reason_code, "message": message}},
            "code": status_code,
            "meta": {"trace_id": trace_id, "source_authority": self.source_authority_contract()},
        }

    def _load_messages(self, model: str, res_id: int, limit: int, *, can_reply: bool = False) -> List[Dict[str, Any]]:
        Message = self.env["mail.message"]
        rows = Message.search(
            [("model", "=", model), ("res_id", "=", res_id)],
            order="date desc, id desc",
            limit=limit,
        )
        is_admin = self.env.user._is_admin()
        items: List[Dict[str, Any]] = []
        for row in rows:
            date_value = _to_iso(row.date)
            subtype_xmlid = _message_subtype_xmlid(row)
            type_label = "备注" if subtype_xmlid == "mail.mt_note" else "评论"
            is_owner = bool(row.author_id and row.author_id.id == self.env.user.partner_id.id)
            can_delete = bool(can_reply and (is_admin or is_owner))
            if can_delete:
                try:
                    Message.check_access_rights("unlink")
                    row.check_access_rule("unlink")
                except AccessError:
                    can_delete = False
            items.append(
                {
                    "key": f"m-{row.id}",
                    "type": "message",
                    "typeLabel": type_label,
                    "title": row.subject or type_label,
                    "meta": f"{_message_author_display(row)} · {date_value or '-'}",
                    "body": _strip_html(row.body or ""),
                    "at": date_value,
                    "id": row.id,
                    "subtype": subtype_xmlid,
                    "message": {
                        "id": row.id,
                        "author_name": _message_author_display(row),
                        "can_reply": bool(can_reply),
                        "can_edit": False,
                        "can_delete": can_delete,
                        "delete_intent": "chatter.message.delete" if can_delete else "",
                    },
                }
            )
        return items

    def _load_attachments(self, model: str, res_id: int, limit: int) -> List[Dict[str, Any]]:
        Attachment = self.env["ir.attachment"]
        domain = [("res_model", "=", model), ("res_id", "=", res_id)]
        related_ids: List[int] = []
        if model in self.env:
            record = self.env[model].browse(res_id).exists()
            record_fields = getattr(record, "_fields", {}) if record else {}
            attachment_field = record and next(
                (
                    name
                    for name, field in record_fields.items()
                    if name == "attachment_ids"
                    or (field.type == "many2many" and field.comodel_name == "ir.attachment")
                ),
                "",
            )
            if attachment_field:
                related_ids = record[attachment_field].ids
        if related_ids:
            domain = ["|", ("id", "in", related_ids), "&", ("res_model", "=", model), ("res_id", "=", res_id)]
        # 使用正常权限检查，不绕过附件访问控制
        AttachmentModel = Attachment
        rows = AttachmentModel.search(domain, order="id desc", limit=limit)
        is_admin = self.env.user._is_admin()
        download_allowed_models = allowed_file_download_models(self.env)
        items: List[Dict[str, Any]] = []
        for row in rows:
            date_value = _to_iso(row.create_date) or _to_iso(row.write_date)
            is_owner = bool(row.create_uid and row.create_uid.id == self.env.user.id)
            is_direct_attachment = row.res_model == model and int(row.res_id or 0) == int(res_id)
            can_delete = False
            download_model, download_res_id = resolve_file_download_auth_subject(self.env, row)
            download_projection = _attachment_download_projection(
                model,
                res_id,
                download_model,
                download_res_id,
                download_allowed_models,
            )
            if is_direct_attachment and (is_admin or is_owner):
                try:
                    can_delete = bool(AttachmentModel.check_access_rights("unlink", raise_exception=False))
                    if can_delete:
                        row.check_access_rule("unlink")
                except AccessError:
                    can_delete = False
            items.append(
                {
                    "key": f"a-{row.id}",
                    "type": "attachment",
                    "typeLabel": "附件",
                    "title": row.name or "Attachment",
                    "meta": f"{row.mimetype or 'unknown'} · {row.file_size or '-'}",
                    "body": "",
                    "at": date_value,
                    "id": row.id,
                    "attachment": {
                        "id": row.id,
                        "name": row.name or "",
                        "mimetype": row.mimetype or "",
                        **download_projection,
                        "can_delete": can_delete,
                        "delete_intent": "chatter.attachment.delete" if can_delete else "",
                    },
                }
            )
        return items

    def _load_activities(self, model: str, res_id: int, limit: int) -> List[Dict[str, Any]]:
        Activity = self.env.get("mail.activity")
        IrModel = self.env.get("ir.model")
        if Activity is None or IrModel is None:
            return []
        model_rec = IrModel.sudo().search([("model", "=", model)], limit=1)
        if not model_rec:
            return []
        rows = Activity.search(
            [("res_model_id", "=", model_rec.id), ("res_id", "=", res_id)],
            order="date_deadline desc, id desc",
            limit=limit,
        )
        is_admin = self.env.user._is_admin()
        items: List[Dict[str, Any]] = []
        for row in rows:
            deadline = _to_iso(row.date_deadline)
            status = _activity_status_projection(row.date_deadline)
            assignee = row.user_id.display_name or "Unknown"
            is_assignee = bool(row.user_id and row.user_id.id == self.env.user.id)
            is_owner = bool(row.create_uid and row.create_uid.id == self.env.user.id)
            items.append(
                {
                    "key": f"act-{row.id}",
                    "type": "activity",
                    "typeLabel": "计划",
                    "title": row.summary or row.activity_type_id.display_name or "计划",
                    "meta": f"{assignee} · {deadline or '-'}",
                    "body": _strip_html(row.note or ""),
                    "at": deadline,
                    "id": row.id,
                    "activity": {
                        "id": row.id,
                        "assignee_user_id": row.user_id.id or 0,
                        "assignee_name": assignee,
                        "deadline": deadline,
                        "activity_type": row.activity_type_id.display_name or "",
                        "status": status["code"],
                        "status_label": status["label"],
                        "can_complete": is_assignee or is_admin,
                        "can_cancel": is_assignee or is_admin or is_owner,
                        "update_intent": "chatter.activity.update",
                    },
                }
            )
        return items

    def _load_audit_items(self, model: str, res_id: int, limit: int) -> List[Dict[str, Any]]:
        Audit = self.env.get("sc.audit.log")
        if Audit is None:
            return []
        # TODO(权限): sc.audit.log 当前仅系统管理员/超级管理员有 read 权限
        # 暂用 sudo() 保证普通用户可见操作历史，后续应增加记录规则(Record Rules)
        # 限制用户只能读取自己有权限的记录的审计日志
        rows = Audit.sudo().search(
            [("model", "=", model), ("res_id", "=", res_id)],
            order="ts desc, id desc",
            limit=limit,
        )
        items: List[Dict[str, Any]] = []
        for row in rows:
            date_value = _to_iso(row.ts)
            actor = (row.actor_uid.display_name if row.actor_uid else "") or row.actor_login or "系统"
            event = _audit_event_label(row.action, row.event_code)
            items.append(
                {
                    "key": f"l-{row.id}",
                    "type": "audit",
                    "typeLabel": "审计",
                    "title": event,
                    "meta": f"{actor} · {date_value or '-'}",
                    "body": row.reason or "",
                    "at": date_value,
                    "id": row.id,
                    "reason_code": row.event_code or "",
                    "audit": {
                        "actor": actor,
                        "occurred_at": date_value or "",
                        "event": event,
                        "result": "已记录",
                    },
                }
            )
        if not items:
            record = self.env[model].browse(res_id).exists()
            created_at = _to_iso(getattr(record, "create_date", None)) if record else None
            creator = getattr(record, "create_uid", None) if record else None
            actor = str(getattr(creator, "display_name", "") or getattr(creator, "login", "") or "系统")
            if record and created_at:
                items.append(
                    {
                        "key": f"record-created-{res_id}",
                        "type": "audit",
                        "typeLabel": "审计",
                        "title": "创建记录",
                        "meta": f"{actor} · {created_at}",
                        "body": "",
                        "at": created_at,
                        "id": 0,
                        "reason_code": "",
                        "audit": {
                            "actor": actor,
                            "occurred_at": created_at,
                            "event": "创建记录",
                            "result": "已创建",
                        },
                    }
                )
        return items


def _read_limit(value: Any, default: int, cap: int):
    parsed, error = parse_positive_int(value, allow_empty=True)
    if error:
        return 0, error
    if parsed is None:
        return default, None
    return min(parsed, cap), None


def _read_offset(value: Any):
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0, None
    if isinstance(value, bool):
        return 0, "invalid"
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0, "invalid"
    if parsed < 0 or str(value).strip() != str(parsed):
        return 0, "invalid"
    return parsed, None


def _is_empty_param(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _to_iso(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        return datetime.fromisoformat(str(value).replace(" ", "T")).isoformat()
    except Exception:
        return str(value)


def _audit_event_label(action: Any, event_code: Any) -> str:
    """Keep technical method/event identifiers out of the product timeline."""
    for value in (action, event_code):
        label = str(value or "").strip()
        if label and not all(char.isascii() and (char.isalnum() or char in "._:-") for char in label):
            return label
    return "业务操作"


def _strip_html(value: str) -> str:
    text = str(value or "")
    out: List[str] = []
    in_tag = False
    for ch in text:
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if not in_tag:
            out.append(ch)
    return "".join(out).strip()


def _message_author_display(row: Any) -> str:
    author = getattr(row, "author_id", None)
    author_name = str(getattr(author, "display_name", "") or "").strip()
    if author_name:
        return author_name
    email_from = str(getattr(row, "email_from", "") or "").strip()
    if email_from:
        display_name, email = parseaddr(email_from)
        decoded_name = _decode_header_value(display_name)
        if decoded_name:
            return decoded_name
        if email:
            return email
        return _decode_header_value(email_from) or email_from
    create_user = getattr(row, "create_uid", None)
    create_user_name = str(getattr(create_user, "display_name", "") or "").strip()
    return create_user_name or "系统"


def _decode_header_value(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw))).strip()
    except Exception:
        return raw


def _message_subtype_xmlid(row: Any) -> str:
    subtype = getattr(row, "subtype_id", None)
    if not subtype:
        return ""
    try:
        xmlids = subtype._get_external_ids().get(subtype.id) or []
    except Exception:
        xmlids = []
    if xmlids:
        return str(xmlids[0] or "")
    return str(subtype.name or "")

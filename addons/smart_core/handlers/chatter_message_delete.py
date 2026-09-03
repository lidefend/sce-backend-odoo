# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError

from ..core.base_handler import BaseIntentHandler
from ..core.request_params import parse_positive_int
try:
    from ..core.project_context import record_scope_denied_response
    from ..core.project_context import record_in_business_scope
except ImportError:  # pragma: no cover - lightweight boundary-test compatibility
    from ..core.project_context import project_scope_denied_response as record_scope_denied_response
    from ..core.project_context import record_in_project_scope
    from ..core.project_context import selected_record_context_id_from_context

    def record_in_business_scope(env_model, record_id, params=None, context=None):
        return record_in_project_scope(env_model, record_id, selected_record_context_id_from_context(params, context))


class ChatterMessageDeleteHandler(BaseIntentHandler):
    INTENT_TYPE = "chatter.message.delete"
    DESCRIPTION = "Delete an owned collaboration message from its exact business record"
    REQUIRED_GROUPS = ["smart_core.group_smart_core_data_operator"]
    ACL_MODE = "explicit_check"
    NON_IDEMPOTENT_ALLOWED = "Deleting a message changes the collaboration record"
    SOURCE_AUTHORITY = "mail.message"
    SOURCE_KIND = "odoo_collaboration_message_delete_proxy"
    SOURCE_AUTHORITIES = ("mail.message", "odoo.orm", "ir.rule", "record_context_model")
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls) -> dict:
        return {
            "kind": cls.SOURCE_KIND,
            "authority": cls.SOURCE_AUTHORITY,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": False,
            "write_proxy": True,
            "no_business_fact_authority": cls.NO_BUSINESS_FACT_AUTHORITY,
            "runtime_carrier": cls.INTENT_TYPE,
        }

    def handle(self, payload=None, ctx=None):
        params = self.params if isinstance(self.params, dict) else {}
        model = str(params.get("model") or "").strip()
        raw_res_id = params.get("res_id") if "res_id" in params else params.get("record_id")
        raw_message_id = params.get("message_id") if "message_id" in params else params.get("id")
        if not model or raw_res_id is None or raw_message_id is None:
            return self._err(400, "缺少参数 model/res_id/message_id")
        if model not in self.env:
            return self._err(404, "模型不存在")
        res_id, res_id_error = parse_positive_int(raw_res_id)
        message_id, message_id_error = parse_positive_int(raw_message_id)
        if res_id_error or message_id_error:
            return self._err(400, "res_id/message_id 无效")

        try:
            Model = self.env[model]
            Model.check_access_rights("write")
            record = Model.browse(res_id).exists()
            if not record:
                return self._err(404, "记录不存在")
            in_scope, scope_meta = record_in_business_scope(
                Model,
                int(record.id),
                params,
                self.context if isinstance(self.context, dict) else {},
            )
            if not in_scope:
                return record_scope_denied_response(scope_meta)
            record.check_access_rule("write")

            Message = self.env["mail.message"]
            Message.check_access_rights("unlink")
            message = Message.search(
                [("id", "=", message_id), ("model", "=", model), ("res_id", "=", int(record.id))],
                limit=1,
            )
            if not message:
                return self._err(404, "消息不存在或不属于当前记录")
            message.check_access_rule("unlink")
            is_owner = bool(message.author_id and message.author_id.id == self.env.user.partner_id.id)
            if not self.env.user._is_admin() and not is_owner:
                return self._err(403, "只能删除自己发布的消息")
            deleted_id = int(message.id)
            message.unlink()
            data = {
                "result": {"message_id": deleted_id, "deleted": True},
                "source_authority": self.source_authority_contract(),
            }
            return data, {"source_authority": self.source_authority_contract()}
        except AccessError:
            return self._err(403, "无权限删除消息")
        except UserError as exc:
            return self._err(400, str(exc) or "业务规则不允许")
        except Exception:
            return self._err(500, "删除消息失败")

    def _err(self, code: int, message: str):
        return {
            "ok": False,
            "error": {"code": code, "message": message},
            "code": code,
            "meta": {"source_authority": self.source_authority_contract()},
        }

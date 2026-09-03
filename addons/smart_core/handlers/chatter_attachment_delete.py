# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError

from ..core.base_handler import BaseIntentHandler
from ..core.request_params import parse_positive_int
try:
    from ..core.project_context import record_scope_denied_response
except ImportError:  # pragma: no cover - compatibility for lightweight boundary tests
    from ..core.project_context import project_scope_denied_response as record_scope_denied_response
try:
    from ..core.project_context import record_in_business_scope
except ImportError:  # pragma: no cover
    from ..core.project_context import record_in_project_scope
    from ..core.project_context import selected_record_context_id_from_context

    def record_in_business_scope(env_model, record_id, params=None, context=None):
        return record_in_project_scope(env_model, record_id, selected_record_context_id_from_context(params, context))


class ChatterAttachmentDeleteHandler(BaseIntentHandler):
    INTENT_TYPE = "chatter.attachment.delete"
    DESCRIPTION = "Delete an owned direct attachment from a collaboration record"
    REQUIRED_GROUPS = ["smart_core.group_smart_core_data_operator"]
    ACL_MODE = "explicit_check"
    NON_IDEMPOTENT_ALLOWED = "Deleting an attachment changes the collaboration record"
    SOURCE_AUTHORITY = "ir.attachment"
    SOURCE_KIND = "odoo_collaboration_attachment_delete_proxy"
    SOURCE_AUTHORITIES = ("ir.attachment", "odoo.orm", "ir.rule", "record_context_model")
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
        raw_attachment_id = params.get("attachment_id") if "attachment_id" in params else params.get("id")
        if not model or raw_res_id is None or raw_attachment_id is None:
            return self._err(400, "缺少参数 model/res_id/attachment_id")
        if model not in self.env:
            return self._err(404, "模型不存在")
        res_id, res_id_error = parse_positive_int(raw_res_id)
        attachment_id, attachment_id_error = parse_positive_int(raw_attachment_id)
        if res_id_error or attachment_id_error:
            return self._err(400, "res_id/attachment_id 无效")

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

            Attachment = self.env["ir.attachment"]
            Attachment.check_access_rights("unlink")
            attachment = Attachment.search(
                [
                    ("id", "=", attachment_id),
                    ("res_model", "=", model),
                    ("res_id", "=", int(record.id)),
                ],
                limit=1,
            )
            if not attachment:
                return self._err(404, "附件不存在或不属于当前记录")
            attachment.check_access_rule("unlink")
            is_owner = bool(attachment.create_uid and attachment.create_uid.id == self.env.user.id)
            if not self.env.user._is_admin() and not is_owner:
                return self._err(403, "只能删除自己上传的附件")
            deleted_id = int(attachment.id)
            attachment.unlink()
            data = {
                "result": {"attachment_id": deleted_id, "deleted": True},
                "source_authority": self.source_authority_contract(),
            }
            return data, {"source_authority": self.source_authority_contract()}
        except AccessError:
            return self._err(403, "无权限删除附件")
        except UserError as exc:
            return self._err(400, str(exc) or "业务规则不允许")
        except Exception:
            return self._err(500, "删除附件失败")

    def _err(self, code: int, message: str):
        return {
            "ok": False,
            "error": {"code": code, "message": message},
            "code": code,
            "meta": {"source_authority": self.source_authority_contract()},
        }

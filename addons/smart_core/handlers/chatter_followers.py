# -*- coding: utf-8 -*-
from typing import Any

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


class _FollowerHandlerBase(BaseIntentHandler):
    REQUIRED_GROUPS = ["smart_core.group_smart_core_data_operator"]
    ACL_MODE = "explicit_check"
    SOURCE_AUTHORITY = "mail.followers"
    SOURCE_KIND = "odoo_collaboration_follower_proxy"
    SOURCE_AUTHORITIES = ("mail.followers", "mail.thread", "res.partner", "odoo.orm", "ir.rule", "record_context_model")
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls) -> dict:
        return {
            "kind": cls.SOURCE_KIND,
            "authority": cls.SOURCE_AUTHORITY,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": cls.INTENT_TYPE == "chatter.followers.list",
            "write_proxy": cls.INTENT_TYPE == "chatter.followers.update",
            "no_business_fact_authority": cls.NO_BUSINESS_FACT_AUTHORITY,
            "runtime_carrier": cls.INTENT_TYPE,
        }

    def _target(self, *, write: bool):
        params = self.params if isinstance(self.params, dict) else {}
        model = str(params.get("model") or "").strip()
        raw_res_id = params.get("res_id") if "res_id" in params else params.get("record_id")
        if not model or raw_res_id is None:
            return None, self._err(400, "缺少参数 model/res_id")
        if model not in self.env:
            return None, self._err(404, "模型不存在")
        res_id, error = parse_positive_int(raw_res_id)
        if error:
            return None, self._err(400, "res_id 无效")
        mode = "write" if write else "read"
        Model = self.env[model]
        Model.check_access_rights(mode)
        record = Model.browse(res_id).exists()
        if not record:
            return None, self._err(404, "记录不存在")
        in_scope, scope_meta = record_in_business_scope(
            Model,
            int(record.id),
            params,
            self.context if isinstance(self.context, dict) else {},
        )
        if not in_scope:
            return None, record_scope_denied_response(scope_meta)
        record.check_access_rule(mode)
        if "message_follower_ids" not in getattr(record, "_fields", {}):
            return None, self._err(400, "模型不支持关注者")
        return record, None

    def _err(self, code: int, message: str):
        return {
            "ok": False,
            "error": {"code": code, "message": message},
            "code": code,
            "meta": {"source_authority": self.source_authority_contract()},
        }


class ChatterFollowersListHandler(_FollowerHandlerBase):
    INTENT_TYPE = "chatter.followers.list"
    DESCRIPTION = "List record followers and current-user follow authority"

    def handle(self, payload=None, ctx=None):
        try:
            record, error = self._target(write=False)
            if error:
                return error
            partners = record.message_partner_ids.exists()
            partners.check_access_rule("read")
            current_partner_id = int(self.env.user.partner_id.id or 0)
            follower_ids = {int(partner.id) for partner in partners if partner.id}
            can_manage = False
            try:
                record.check_access_rule("write")
                self.env[record._name].check_access_rights("write")
                can_manage = callable(getattr(record, "message_subscribe", None)) and callable(getattr(record, "message_unsubscribe", None))
            except AccessError:
                can_manage = False
            items = [
                {
                    "partner_id": int(partner.id),
                    "name": str(partner.display_name or partner.name or "").strip(),
                    "email": str(partner.email or "").strip(),
                    "is_current_user": int(partner.id) == current_partner_id,
                }
                for partner in partners
                if partner.id
            ]
            data = {
                "items": items,
                "count": len(items),
                "is_following": current_partner_id in follower_ids,
                "can_follow": bool(can_manage and current_partner_id and current_partner_id not in follower_ids),
                "can_unfollow": bool(can_manage and current_partner_id and current_partner_id in follower_ids),
                "source_authority": self.source_authority_contract(),
            }
            return data, {"source_authority": self.source_authority_contract()}
        except AccessError:
            return self._err(403, "无权限读取关注者")
        except UserError as exc:
            return self._err(400, str(exc) or "业务规则不允许")
        except Exception:
            return self._err(500, "读取关注者失败")


class ChatterFollowersUpdateHandler(_FollowerHandlerBase):
    INTENT_TYPE = "chatter.followers.update"
    DESCRIPTION = "Follow or unfollow a record as the current user"
    NON_IDEMPOTENT_ALLOWED = "mail.thread follow state is idempotent for the current partner"

    def handle(self, payload=None, ctx=None):
        params = self.params if isinstance(self.params, dict) else {}
        action = str(params.get("action") or "").strip().lower()
        if action not in {"follow", "unfollow"}:
            return self._err(400, "action 无效")
        try:
            record, error = self._target(write=True)
            if error:
                return error
            partner_id = int(self.env.user.partner_id.id or 0)
            if not partner_id:
                return self._err(403, "当前用户没有可用联系人")
            method_name = "message_subscribe" if action == "follow" else "message_unsubscribe"
            method = getattr(record, method_name, None)
            if not callable(method):
                return self._err(400, "模型不支持关注者")
            method(partner_ids=[partner_id])
            data = {
                "result": {
                    "action": action,
                    "partner_id": partner_id,
                    "is_following": action == "follow",
                },
                "source_authority": self.source_authority_contract(),
            }
            return data, {"source_authority": self.source_authority_contract()}
        except AccessError:
            return self._err(403, "无权限更新关注状态")
        except UserError as exc:
            return self._err(400, str(exc) or "业务规则不允许")
        except Exception:
            return self._err(500, "更新关注状态失败")

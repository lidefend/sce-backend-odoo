"""Resolve the governed local.dev payment attachment M2M journey without writes."""

import json


user = env.ref("smart_construction_demo.user_demo_role_finance")
menu = env.ref("smart_construction_core.menu_sc_user_payment_apply")
action = env.ref("smart_construction_core.action_payment_request_user_payment_apply")
request = env.ref("smart_construction_demo.payment_request_floorplan_demo_record")
attachment = env.ref("smart_construction_demo.payment_request_floorplan_demo_attachment")

payment_env = env["payment.request"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
request = payment_env.browse(request.id).exists()
if not request or request.state != "draft" or not str(request.name or "").startswith("DEMO-PR-FLOORPLAN-"):
    raise RuntimeError("governed payment attachment M2M fixture is missing or not draft")
request.check_access_rights("read")
request.check_access_rights("write")
request.check_access_rule("read")
request.check_access_rule("write")

attachment_env = env["ir.attachment"].with_user(user).with_company(user.company_id).with_context(
    allowed_company_ids=user.company_ids.ids,
    active_test=False,
)
attachment = attachment_env.browse(attachment.id).exists()
if not attachment or attachment.name != "DEMO-PR-FLOORPLAN-M2M.txt":
    raise RuntimeError("governed payment attachment object is missing")
attachment.check_access_rights("read")
attachment.check_access_rule("read")

field = request._fields.get("attachment_ids")
if not field or field.type != "many2many" or field.comodel_name != "ir.attachment":
    raise RuntimeError("payment.request.attachment_ids is not the governed M2M carrier")
if menu.action != action or action.res_model != "payment.request":
    raise RuntimeError("payment attachment journey entry authority mismatch")
if not menu.active or menu.id not in env["ir.ui.menu"].with_user(user)._visible_menu_ids():
    raise RuntimeError("payment attachment journey menu is unavailable to demo_role_finance")

print(
    "LOCAL_DEV_PAYMENT_ATTACHMENT_M2M_JSON="
    + json.dumps(
        {
            "user": {"id": user.id, "login": user.login},
            "menu": {"id": menu.id, "name": menu.name},
            "action": {"id": action.id, "name": action.name},
            "request": {
                "id": request.id,
                "name": request.name,
                "state": request.state,
                "attachment_ids": request.attachment_ids.ids,
            },
            "attachment": {
                "id": attachment.id,
                "name": attachment.name,
                "exists": bool(attachment.exists()),
                "res_model": attachment.res_model,
                "res_id": attachment.res_id,
            },
            "field": {
                "name": field.name,
                "type": field.type,
                "relation": field.comodel_name,
                "save_authority": "payment.request.write",
            },
        },
        ensure_ascii=False,
    )
)

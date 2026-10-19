# -*- coding: utf-8 -*-
import base64

from odoo import fields
from odoo.exceptions import UserError

from ..registry import SeedStep, register
from ..tier_flow import approve_tier_chain
from ...tools.scenario_loader import _demo_action_record, _demo_project_members


PROJECT_EXEC_CODE = "DEMO-PJ-EXEC"
STAGE_PROJECT_CODES = [
    "DEMO-PJ-STAGE-DRAFT",
    "DEMO-PJ-STAGE-RUN",
    "DEMO-PJ-STAGE-PAUSE",
    "DEMO-PJ-STAGE-CLOSING",
    "DEMO-PJ-STAGE-DONE",
    "DEMO-PJ-STAGE-WARRANTY",
    "DEMO-PJ-STAGE-CLOSED",
]


def _get_project(env, code):
    return env["project.project"].sudo().search([("project_code", "=", code)], limit=1)


def _get_showroom_projects(env):
    Project = env["project.project"].sudo()
    domain = [
        "|",
        ("name", "ilike", "展厅-"),
        ("project_code", "ilike", "DEMO-"),
    ]
    return Project.search(domain)


def _get_or_create_dict(env, dict_type, name):
    Dictionary = env["sc.dictionary"].sudo()
    record = Dictionary.search([("type", "=", dict_type), ("name", "=", name)], limit=1)
    if record:
        return record
    return Dictionary.create({"type": dict_type, "name": name, "sequence": 10})


def _create_attachment(env, name, content, mimetype="text/plain"):
    Attachment = env["ir.attachment"]
    data = base64.b64encode(content.encode("utf-8"))
    return Attachment.create(
        {
            "name": name,
            "datas": data,
            "type": "binary",
            "mimetype": mimetype,
        }
    )


def _find_document_attachment(document, filename):
    """Return the demo attachment already linked to a document, if any.

    Draft documents are rewritten on every seed run. Reusing the named
    attachment keeps the seed idempotent and avoids orphaning the previous
    file when the document relation is replaced.
    """
    return document.attachment_ids.filtered(
        lambda attachment: attachment.name == filename
    )[:1]


def _advance_document(document, target_state):
    """把演示资料推进到声明状态，只使用产品自己的办理动作。

    ``sc.project.document`` 的 create/write 都拒绝直接写终态；草稿提交后若
    配置了审批模板会停在“审核中”，否则产品按未配置流程自动通过，再由归档
    动作到达“已归档”。因此这里不能写 state，也不能把目标状态吞掉。
    """
    if target_state == "draft":
        return document
    if document.state == "draft":
        document.action_submit()
        document.invalidate_recordset()
    if target_state == "review":
        pass
    elif target_state in ("approved", "done"):
        if document.state == "review" and document.review_ids:
            approve_tier_chain(document)
            document.invalidate_recordset()
        if document.state == "approved" and target_state == "done":
            document.action_archive()
            document.invalidate_recordset()
    else:
        raise UserError("演示资料声明了未知目标状态：%s" % target_state)
    if document.state != target_state:
        raise UserError(
            "演示资料未到达声明状态：%s 停在 %s（目标 %s）"
            % (document.name, document.state, target_state)
        )
    return document


def run(env):
    projects = [
        _get_project(env, PROJECT_EXEC_CODE),
    ]
    for code in STAGE_PROJECT_CODES:
        projects.append(_get_project(env, code))
    projects.extend(_get_showroom_projects(env))
    projects = list({p.id: p for p in projects if p}.values())
    if not projects:
        return

    doc_type = _get_or_create_dict(env, "doc_type", "技术资料")
    doc_subtype = _get_or_create_dict(env, "doc_subtype", "合同附件")

    ScDoc = _demo_action_record(env, env["sc.project.document"], "action_submit")

    documents = [
        {
            "name": "施工组织设计",
            "is_mandatory": True,
            "state": "done",
            "date_doc": fields.Date.context_today(env.user),
            "content": "施工组织设计",
        },
        {
            "name": "监理例会纪要",
            "is_mandatory": True,
            "state": "done",
            "date_doc": fields.Date.context_today(env.user),
            "content": "监理例会纪要",
        },
        {
            "name": "合同附件清单",
            "is_mandatory": True,
            # 产品只有在配置了资料审批模板时才会停留在“审核中”，未配置时提交
            # 即自动通过；因此演示只声明产品能产生的“待提交”。
            "state": "draft",
            "date_doc": fields.Date.context_today(env.user),
            "content": "合同附件清单",
        },
        {
            "name": "质量检验记录",
            "is_mandatory": True,
            "state": "draft",
            "date_doc": fields.Date.context_today(env.user),
            "content": "质量检验记录",
        },
        {
            "name": "安全交底记录",
            "is_mandatory": False,
            "state": "done",
            "date_doc": fields.Date.context_today(env.user),
            "content": "安全交底记录",
        },
    ]

    for project in projects:
        _demo_project_members(env, project, ("smart_construction_demo.user_sc_project_user",))
        for doc in documents:
            project_label = project.name or project.project_code
            name = f"{doc['name']} · {project_label}"
            existing = ScDoc.search(
                [("project_id", "=", project.id), ("name", "=", name)], limit=1
            )
            if not existing:
                existing = ScDoc.search(
                    [
                        ("project_id", "=", project.id),
                        ("name", "=like", f"{doc['name']} · %"),
                    ],
                    limit=1,
                )
                if existing:
                    existing.write({"name": name})
            vals = {
                "name": name,
                "project_id": project.id,
                "doc_type_id": doc_type.id,
                "doc_subtype_id": doc_subtype.id,
                "date_doc": doc["date_doc"],
                "is_mandatory": doc["is_mandatory"],
            }
            if not existing or existing.state == "draft":
                filename = f"{name}.txt"
                attachment = (
                    _find_document_attachment(existing, filename)
                    if existing
                    else False
                )
                if not existing:
                    attachment = _create_attachment(
                        ScDoc.env, filename, doc["content"]
                    )
                    vals["attachment_ids"] = [(6, 0, [attachment.id])]
                elif not attachment:
                    attachment = _create_attachment(
                        ScDoc.env, filename, doc["content"]
                    )
                    # Add the missing file without dropping any user attachment.
                    vals["attachment_ids"] = [(4, attachment.id)]
            if existing:
                # 已归档/已作废的资料受保护，只有草稿可以改写内容字段。
                if existing.state == "draft":
                    existing.write(vals)
                document = existing
            else:
                document = ScDoc.create(vals)
            # 产品的 _ensure_operation_allowed 禁止在“停工/关闭”项目上办理资料，
            # 这类项目只保留草稿资料，不注入绕开守卫的状态。
            target_state = (
                "draft"
                if project.lifecycle_state in ("paused", "closed")
                else doc["state"]
            )
            _advance_document(document, target_state)

    ICP = env["ir.config_parameter"].sudo()
    ICP.set_param("sc.seed.demo.attachments", fields.Datetime.now().isoformat())


register(
    SeedStep(
        name="demo_60_attachments",
        description="Seed attachments and project documents for demo.",
        run=run,
    )
)

# -*- coding: utf-8 -*-
from __future__ import annotations


class ProjectInitializationService:
    """Initialize lightweight project skeleton after intake creation."""

    def __init__(self, env):
        self.env = env

    def bootstrap(self, project):
        project.ensure_one()
        result = {
            "project_cost_ledger": "deferred",
            "project_finance_ledger": "deferred",
            "project_risk_profile": "derived",
            "project_tasks": "optional",
        }

        if hasattr(project, "message_post"):
            project.message_post(
                body=(
                    "项目初始化已完成：已建立项目管理对象；"
                    "施工任务按实际工作分解需要创建；成本/资金/风险承载采用按业务事件驱动补充。"
                )
            )

        return result


class ProjectCreationService:
    """Domain service for intake-style project creation semantics."""

    SOURCE_KIND = "project_initiation_odoo_orm_write_proxy"
    SOURCE_AUTHORITIES = (
        "project.project",
        "mail.message",
        "ir.model.access",
        "ir.rule",
        "odoo.orm",
    )

    def __init__(self, env):
        self.env = env
        self.initializer = ProjectInitializationService(env)

    @classmethod
    def source_authority_contract(cls):
        return {
            "kind": cls.SOURCE_KIND,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": False,
            "runtime_authority": "odoo.orm",
            "write_authority": "project.project.create",
        }

    def normalize_create_vals(self, vals):
        normalized = dict(vals or {})
        if not normalized.get("manager_id"):
            fallback_uid = normalized.get("user_id") or self.env.user.id
            normalized["manager_id"] = int(fallback_uid)
        if not normalized.get("phase_key"):
            normalized["phase_key"] = "initiation"
        if not normalized.get("lifecycle_state"):
            normalized["lifecycle_state"] = "draft"
        return normalized

    def post_create_bootstrap(self, projects):
        summary = {}
        for project in projects:
            summary = self.initializer.bootstrap(project)
        return summary

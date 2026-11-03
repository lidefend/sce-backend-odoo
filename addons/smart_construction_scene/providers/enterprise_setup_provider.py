# -*- coding: utf-8 -*-
from __future__ import annotations


def build(scene_key: str = "enterprise.setup", runtime: dict | None = None, context: dict | None = None) -> dict:
    """Root enterprise-setup workspace.

    Reuses the existing product bootstrap chain (company ->
    department -> post -> user) as the guided initialization mainline. The
    setup workspace itself owns no business facts and only organizes the
    enterprise-configuration entry points; it must not duplicate organization,
    user, role, approval or dictionary management.
    """
    _ = context or {}
    runtime_payload = runtime or {}
    first_step = {
        "label": "开始企业初始化",
        "scene_key": "enterprise.company",
        "route": "/s/enterprise.company",
        "semantic": "enterprise_setup_first_step",
    }
    setup_catalog = {
        "contract_version": "handling_entry_catalog.v1",
        "domain": "enterprise_setup",
        "entry_mode": "integrated_handling",
        "source_authority": "sc.scene",
        "groups": [
            {
                "key": "enterprise_bootstrap",
                "title": "企业基础初始化",
                "items": [
                    {"key": "company", "label": "企业信息", "model": "res.company", "action_xmlid": "base.action_res_company_form", "menu_xmlid": "base.menu_action_res_company_form"},
                    {"key": "department", "label": "组织架构", "model": "hr.department", "action_xmlid": "smart_construction_core.action_sc_organization_department"},
                    {"key": "post", "label": "岗位管理", "model": "hr.job", "action_xmlid": "smart_construction_core.action_sc_product_job_management_v1"},
                    {"key": "user", "label": "用户设置", "model": "res.users", "action_xmlid": "smart_construction_core.action_sc_runtime_user_management"},
                ],
            },
        ],
        "group_count": 1,
        "item_count": 4,
    }
    return {
        "scene_key": scene_key,
        "guidance": {
            "title": "企业初始化工作空间",
            "message": "按顺序完成企业信息、组织架构、岗位与用户设置，再进入业务配置与场景接入。",
        },
        "layout": {"kind": "workspace", "sidebar": "fixed", "header": "full"},
        "handling_entry_catalog": setup_catalog,
        "extensions": {"handling_entry_catalog_v1": setup_catalog},
        "primary_action": first_step,
        "next_scene": "enterprise.company",
        "next_scene_route": "/s/enterprise.company",
        "setup_mainline": [
            "enterprise.company",
            "enterprise.department",
            "enterprise.post",
            "enterprise.user",
        ],
        "runtime": {
            "role_code": runtime_payload.get("role_code"),
            "company_id": runtime_payload.get("company_id"),
        },
    }

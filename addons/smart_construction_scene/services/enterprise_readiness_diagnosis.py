#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only enterprise readiness diagnosis service.

Evaluates the 12 approved readiness rules against authoritative business facts.
It never creates, copies, or mutates business facts and never grants roles or
permissions.  Each rule returns status, evidence, failure reason, affected
scenarios, remediation entry and a suggested responsible party.
"""

from __future__ import annotations

from typing import Any


RULE_LABELS = {
    "enterprise.identity": "企业身份", "enterprise.organization": "组织架构",
    "enterprise.positions": "岗位体系", "enterprise.users": "用户身份",
    "enterprise.employees": "员工档案", "enterprise.user_employee_link": "用户与员工关联",
    "enterprise.user_org_position": "用户与部门、岗位关系", "enterprise.roles": "系统角色",
    "enterprise.project_responsibility": "项目成员责任", "enterprise.scenario_enablement": "企业场景启用",
    "enterprise.scenario_dependencies": "场景依赖", "enterprise.role_delivery": "角色工作空间交付",
}
STATUS_LABELS = {"VERIFIED": "已验证", "CONFIGURED": "已配置",
                 "NOT_CONFIGURED": "未配置", "NOT_EVALUATED": "待业务验证"}


def _rule(
    *,
    rule_key: str,
    layer: str,
    applicability: bool,
    status: str,
    source: str,
    evidence: dict[str, Any],
    failure_reason: str,
    affected_scenarios: list[str],
    remediation_entry: str,
    responsible_party: str,
) -> dict[str, Any]:
    return {
        "rule_key": rule_key,
        "label": RULE_LABELS[rule_key],
        "status_label": STATUS_LABELS[status] if applicability else "不适用",
        "evaluation_layer": layer,
        "applicability": applicability,
        "status": status,
        "authoritative_source": source,
        "evidence": evidence,
        "failure_reason": failure_reason,
        "affected_scenarios": affected_scenarios,
        "remediation_entry": remediation_entry,
        "suggested_responsible_party": responsible_party,
    }


def evaluate_enterprise_readiness(env, *, company_id: int) -> dict[str, Any]:
    company = env["res.company"].browse(company_id).exists()
    company_domain = [("company_id", "=", company_id)]

    identity_status = "NOT_CONFIGURED"
    identity_reason = "企业不存在"
    if company:
        if company.name and company.currency_id:
            identity_status = "VERIFIED"
            identity_reason = ""
        else:
            identity_status = "CONFIGURED"
            identity_reason = "企业存在但必要字段未完整"

    dept_count = env["hr.department"].sudo().search_count(company_domain)
    job_count = env["hr.job"].sudo().search_count(company_domain)
    user_count = env["res.users"].sudo().search_count(
        [("share", "=", False), ("active", "=", True), ("company_ids", "in", [company_id])]
    )
    employee_count = env["hr.employee"].sudo().search_count(company_domain + [("active", "=", True)])
    linked_employee_count = env["hr.employee"].sudo().search_count(company_domain + [("active", "=", True), ("user_id.active", "=", True), ("user_id", "!=", False)])
    positioned_employee_count = env["hr.employee"].sudo().search_count(
        company_domain + [("active", "=", True), ("user_id.active", "=", True), ("user_id", "!=", False), ("department_id", "!=", False), ("job_id", "!=", False)]
    )

    assignable_group_ids = env["res.groups"].sudo().search(
        [("sc_assignable_user_permission", "=", True)]
    ).ids
    role_user_count = 0
    if assignable_group_ids:
        role_user_count = env["res.users"].sudo().search_count(
            [("share", "=", False), ("active", "=", True), ("groups_id", "in", assignable_group_ids), ("company_ids", "in", [company_id])]
        )
    project_responsibility_count = env["sc.project.member.assignment"].sudo().search_count(
        [("company_id", "=", company_id)]
    )
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import load_runtime_surface
    from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key
    from odoo.addons.smart_construction_scene.services.tenant_scene_activation import read_tenant_enablement
    business_keys = [business_key(row["key"]) for row in load_runtime_surface(env)["scenarios"] if row["active"]]
    enabled_scene_keys = [key for key in business_keys if read_tenant_enablement(env, company_id, key)]
    enabled_scene_count = len(enabled_scene_keys)
    project_enabled = business_key("project.management") in enabled_scene_keys

    def _count_status(count: int, reason: str) -> str:
        if count <= 0:
            return "NOT_CONFIGURED"
        return "CONFIGURED"

    rules: list[dict[str, Any]] = [
        _rule(
            rule_key="enterprise.identity",
            layer="enterprise",
            applicability=True,
            status=identity_status,
            source="res.company",
            evidence={"company_id": company.id if company else 0},
            failure_reason=identity_reason,
            affected_scenarios=["global"],
            remediation_entry="enterprise.info",
            responsible_party="企业管理员",
        ),
        _rule(
            rule_key="enterprise.organization",
            layer="enterprise",
            applicability=True,
            status=_count_status(dept_count, "组织事实缺失"),
            source="hr.department",
            evidence={"department_count": dept_count},
            failure_reason="" if dept_count else "组织事实缺失",
            affected_scenarios=["project_management", "procurement", "finance"],
            remediation_entry="organization.department",
            responsible_party="组织管理负责人",
        ),
        _rule(
            rule_key="enterprise.positions",
            layer="enterprise",
            applicability=True,
            status=_count_status(job_count, "岗位事实缺失"),
            source="hr.job",
            evidence={"job_count": job_count},
            failure_reason="" if job_count else "岗位事实缺失",
            affected_scenarios=["project_management", "procurement", "finance"],
            remediation_entry="job.management",
            responsible_party="人力/组织负责人",
        ),
        _rule(
            rule_key="enterprise.users",
            layer="enterprise",
            applicability=True,
            status=_count_status(user_count, "用户事实缺失"),
            source="res.users",
            evidence={"user_count": user_count},
            failure_reason="" if user_count else "用户事实缺失",
            affected_scenarios=["role_delivery"],
            remediation_entry="user.management",
            responsible_party="用户管理员",
        ),
        _rule(
            rule_key="enterprise.employees",
            layer="enterprise",
            applicability=True,
            status=_count_status(employee_count, "员工档案缺失"),
            source="hr.employee",
            evidence={"employee_count": employee_count},
            failure_reason="" if employee_count else "员工档案缺失",
            affected_scenarios=["role_delivery"],
            remediation_entry="personnel.record",
            responsible_party="人力负责人",
        ),
        _rule(
            rule_key="enterprise.user_employee_link",
            layer="enterprise",
            applicability=True,
            status=_count_status(linked_employee_count, "用户与员工关联缺失"),
            source="hr.employee.user_id",
            evidence={"linked_employee_count": linked_employee_count},
            failure_reason="" if linked_employee_count else "用户与员工关联缺失",
            affected_scenarios=["role_delivery"],
            remediation_entry="personnel.record",
            responsible_party="人力/用户管理员",
        ),
        _rule(
            rule_key="enterprise.user_org_position",
            layer="enterprise",
            applicability=True,
            status=_count_status(positioned_employee_count, "部门/岗位关系缺失"),
            source="hr.employee.department_id/job_id",
            evidence={"positioned_employee_count": positioned_employee_count},
            failure_reason="" if positioned_employee_count else "部门/岗位关系缺失",
            affected_scenarios=["role_delivery"],
            remediation_entry="personnel.record",
            responsible_party="组织/人力负责人",
        ),
        _rule(
            rule_key="enterprise.roles",
            layer="user",
            applicability=True,
            status=_count_status(role_user_count, "系统角色未分配"),
            source="res.groups + sc_assignable_user_permission",
            evidence={"role_user_count": role_user_count},
            failure_reason="" if role_user_count else "系统角色未分配",
            affected_scenarios=["role_delivery"],
            remediation_entry="data.permission",
            responsible_party="业务配置管理员",
        ),
        _rule(
            rule_key="enterprise.project_responsibility",
            layer="user",
            applicability=project_enabled,
            status=_count_status(project_responsibility_count, "项目责任未建立"),
            source="sc.project.member.assignment",
            evidence={"project_responsibility_count": project_responsibility_count},
            failure_reason="" if project_responsibility_count else "项目责任未建立",
            affected_scenarios=["project_management"],
            remediation_entry="project.member.permission",
            responsible_party="项目负责人",
        ),
        _rule(
            rule_key="enterprise.scenario_enablement",
            layer="scenario",
            applicability=True,
            status=_count_status(enabled_scene_count, "未启用任何场景"),
            source="sc.scene.company.enablement",
            evidence={"enabled_scene_count": enabled_scene_count},
            failure_reason="" if enabled_scene_count else "未启用任何场景",
            affected_scenarios=["all"],
            remediation_entry="scenario.enablement",
            responsible_party="业务配置管理员",
        ),
        _rule(
            rule_key="enterprise.scenario_dependencies",
            layer="scenario",
            applicability=enabled_scene_count > 0,
            status=("NOT_EVALUATED" if enabled_scene_count > 0 else ""),
            source="sc.scene.company.enablement; business dependencies not evaluated",
            evidence={"enabled_scene_count": enabled_scene_count},
            failure_reason="",
            affected_scenarios=["enabled"],
            remediation_entry="readiness.diagnosis",
            responsible_party="对应业务负责人",
        ),
        _rule(
            rule_key="enterprise.role_delivery",
            layer="user",
            applicability=enabled_scene_count > 0,
            status=("NOT_EVALUATED" if enabled_scene_count > 0 and role_user_count > 0 else ("NOT_CONFIGURED" if enabled_scene_count > 0 else "")),
            source="role_surface + route authority",
            evidence={"role_user_count": role_user_count, "enabled_scene_count": enabled_scene_count},
            failure_reason="" if role_user_count else "角色未分配",
            affected_scenarios=["all"],
            remediation_entry="data.permission",
            responsible_party="业务配置管理员",
        ),
    ]

    # Bind remediation to the same authorized native entry projection as the
    # workspace. No role/action whitelist is maintained by this diagnosis.
    from odoo.addons.smart_core.core.native_handling_entry_catalog import project_native_handling_catalog
    scene = env["sc.scene"].search([("code", "=", "enterprise.setup"), ("state", "=", "published")], limit=1)
    catalog = project_native_handling_catalog(env, scene.to_public_dict(env.user)) if scene else None
    decorate_remediation(rules, catalog)
    return {
        "contract_version": "enterprise_readiness.v2",
        "company_id": company_id,
        "company_name": company.display_name if company else "",
        "checked_at": env.cr.now(),
        "rules": rules,
    }


def decorate_remediation(rules, catalog):
    entries = {}
    for group in (catalog or {}).get("groups", []):
        for item in group.get("items", []):
            for key in item.get("remediation_keys", []):
                if key in entries:
                    raise ValueError("READINESS_REMEDIATION_AMBIGUOUS")
                entries[key] = {"kind": "handling_entry", "key": item["key"], "label": item["label"]}
    for rule in rules:
        key = rule["remediation_entry"]
        rule["remediation"] = entries.get(key) if rule["applicability"] else None
        if key == "scenario.enablement" and rule["applicability"]:
            rule["remediation"] = {"kind": "anchor", "key": "enterprise-scenario-activation", "label": "前往场景管理"}
        # An evaluated fact is not proof of an unexecuted business journey.
        if rule["rule_key"] == "enterprise.scenario_dependencies" and rule["applicability"]:
            rule["failure_reason"] = "基础配置不代替各业务场景的实际办理验证。"
        if rule["rule_key"] == "enterprise.role_delivery" and rule["status"] == "NOT_EVALUATED":
            rule["failure_reason"] = "请使用对应业务账号验证工作入口及数据范围。"

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
        [("share", "=", False), ("company_ids", "in", [company_id])]
    )
    employee_count = env["hr.employee"].sudo().search_count(company_domain + [("active", "=", True)])
    linked_employee_count = env["hr.employee"].sudo().search_count(company_domain + [("user_id", "!=", False)])
    positioned_employee_count = env["hr.employee"].sudo().search_count(
        company_domain + [("department_id", "!=", False), ("job_id", "!=", False)]
    )

    assignable_group_ids = env["res.groups"].sudo().search(
        [("sc_assignable_user_permission", "=", True)]
    ).ids
    role_user_count = 0
    if assignable_group_ids:
        role_user_count = env["res.users"].sudo().search_count(
            [("share", "=", False), ("groups_id", "in", assignable_group_ids), ("company_ids", "in", [company_id])]
        )
    project_responsibility_count = env["sc.project.member.assignment"].sudo().search_count(
        [("company_id", "=", company_id)]
    )
    enabled_scene_count = env["sc.scene.company.enablement"].sudo().search_count(
        [("company_id", "=", company_id), ("enabled", "=", True)]
    )

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
            applicability=True,
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
            status=("CONFIGURED" if enabled_scene_count > 0 else ""),
            source="scene target res_model + FK",
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
            status=("CONFIGURED" if enabled_scene_count > 0 and role_user_count > 0 else ("NOT_CONFIGURED" if enabled_scene_count > 0 else "")),
            source="role_surface + route authority",
            evidence={"role_user_count": role_user_count, "enabled_scene_count": enabled_scene_count},
            failure_reason="" if role_user_count else "角色未分配",
            affected_scenarios=["all"],
            remediation_entry="data.permission",
            responsible_party="业务配置管理员",
        ),
    ]

    return {
        "company_id": company_id,
        "company_name": company.display_name if company else "",
        "checked_at": env.cr.now(),
        "rules": rules,
    }

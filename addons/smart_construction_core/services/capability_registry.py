# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import time
from typing import Any

from odoo import _
from odoo.addons.smart_construction_scene import scene_registry
from odoo.addons.smart_construction_scene.services.capability_scene_targets import (
    build_capability_entry_target,
    resolve_capability_entry_scene_key,
    resolve_capability_entry_target_payload_with_timings,
)

CAPABILITY_KEY_REGEX = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

RUNTIME_ORCHESTRATION_SCENE_KEYS = {
    "project.plan_bootstrap",
    "project.execution",
}

CAPABILITY_GROUPS: list[dict[str, Any]] = [
    {"key": "project_management", "label": "项目管理", "icon": "briefcase", "sequence": 10},
    {"key": "finance_management", "label": "财务管理", "icon": "wallet", "sequence": 20},
    {"key": "cost_management", "label": "成本管理", "icon": "calculator", "sequence": 30},
    {"key": "contract_management", "label": "合同管理", "icon": "file-text", "sequence": 40},
    {"key": "analytics", "label": "经营分析", "icon": "chart", "sequence": 50},
    {"key": "governance", "label": "治理配置", "icon": "shield", "sequence": 60},
    {"key": "material_management", "label": "物资管理", "icon": "boxes", "sequence": 70},
    {"key": "others", "label": "常用入口", "icon": "grid", "sequence": 80},
]

def _cap(
    key: str,
    label: str,
    hint: str,
    group_key: str,
    *,
    required_roles: list[str] | None = None,
    required_groups: list[str] | None = None,
    status: str = "ga",
    access_action: str = "",
    visible: bool = True,
    replacement_capabilities: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "hint": hint,
        "group_key": group_key,
        "required_roles": list(required_roles or []),
        "required_groups": list(required_groups or []),
        "status": status,
        "intent": "ui.contract",
        "access_action": access_action,
        "visible": bool(visible),
        "replacement_capabilities": list(replacement_capabilities or []),
    }


_CAPABILITIES: list[dict[str, Any]] = [
    _cap("project.initiation.enter", "项目立项", "创建并发起项目立项流程", "project_management", required_roles=["pm", "executive"]),
    _cap("project.list.open", "项目列表", "查看项目列表与筛选", "project_management", access_action="smart_construction_core.action_sc_project_list"),
    _cap("project.board.open", "项目看板", "查看项目看板与状态分布", "project_management", required_roles=["owner", "pm", "executive"]),
    _cap("project.dashboard.enter", "项目驾驶舱", "进入项目驾驶舱最小入口", "project_management", required_roles=["pm", "executive"]),
    _cap("project.dashboard.open", "项目驾驶舱入口", "进入项目驾驶舱标准入口", "project_management", required_roles=["pm", "executive"], status="deprecated"),
    _cap("project.plan_bootstrap.enter", "计划编排入口", "进入项目计划编排最小入口", "project_management", required_roles=["pm", "executive"]),
    _cap("project.execution.enter", "项目执行入口", "进入项目执行最小入口", "project_management", required_roles=["pm", "executive"]),
    _cap("project.execution.advance", "推进执行", "执行最小推进动作", "project_management", required_roles=["pm", "executive"]),
    _cap("project.lifecycle.open", "生命周期视图", "查看项目生命周期与阻塞项", "project_management", required_roles=["pm", "executive"]),
    _cap(
        "project.task.list",
        "任务列表",
        "查看项目任务与待办",
        "project_management",
        required_groups=["smart_construction_core.group_sc_cap_project_read"],
    ),
    _cap("project.task.board", "任务看板", "按状态查看任务推进", "project_management", required_roles=["pm", "executive"]),
    _cap("project.document.open", "项目文档", "进入项目文档视图", "project_management", required_roles=["pm", "executive"]),
    _cap("project.structure.manage", "执行结构", "进入执行结构与WBS能力", "project_management", required_roles=["pm", "executive"]),
    _cap("project.risk.list", "风险清单", "查看项目风险清单", "project_management", required_roles=["pm", "executive"]),
    _cap("project.weekly_report.open", "周报入口", "进入项目周报与周度复盘", "project_management", required_roles=["pm", "executive"]),
    _cap("project.lifecycle.transition", "生命周期流转", "执行项目生命周期流转动作", "project_management", required_roles=["pm", "executive"]),

    _cap(
        "finance.payment_request.list",
        "付款申请列表",
        "查看付款申请列表",
        "finance_management",
        access_action="smart_construction_core.action_payment_request_user_payment_apply",
    ),
    _cap("finance.payment_request.form", "付款申请表单", "进入付款申请详情与编辑", "finance_management", required_roles=["finance", "executive"], required_groups=["smart_construction_core.group_sc_cap_finance_read"]),
    _cap("finance.approval.center", "审批中心入口", "进入财务审批工作台", "finance_management", required_roles=["finance", "executive"]),
    _cap("finance.ledger.payment", "收付款台账", "查看收付款台账", "finance_management", access_action="smart_construction_core.action_payment_ledger"),
    _cap("finance.ledger.treasury", "资金台账", "查看资金余额与流水", "finance_management", access_action="smart_construction_core.action_sc_treasury_ledger"),
    _cap("finance.settlement.order", "结算单", "查看结算单流程", "finance_management", access_action="smart_construction_core.action_sc_settlement_order"),
    _cap("finance.invoice.list", "发票列表", "进入发票相关清单", "finance_management", required_roles=["finance", "executive"]),
    _cap("finance.plan.funding", "资金计划", "查看资金计划与安排", "finance_management", required_roles=["finance", "executive"]),
    _cap("finance.metrics.operating", "经营指标", "查看经营指标看板", "finance_management", required_roles=["finance", "executive"]),
    _cap("finance.exception.monitor", "财务异常", "查看财务异常清单", "finance_management", required_roles=["finance", "executive"]),

    _cap("cost.ledger.open", "成本台账", "进入成本台账", "cost_management", access_action="smart_construction_core.action_project_cost_ledger"),
    _cap("cost.budget.manage", "预算管理", "进入预算与控制能力", "cost_management", required_roles=["pm", "finance", "executive"]),
    _cap("cost.boq.manage", "工程量清单", "进入工程量清单能力", "cost_management", required_roles=["pm", "executive"]),
    _cap("cost.progress.report", "进度填报", "进入进度填报与对比", "cost_management", required_roles=["pm", "executive"]),
    _cap("cost.profit.compare", "盈亏对比", "查看盈亏对比分析", "cost_management", access_action="smart_construction_core.action_project_profit_compare"),

    _cap(
        "contract.center.open",
        "合同中心",
        "进入合同中心",
        "contract_management",
        access_action="smart_construction_core.action_construction_contract",
        status="deprecated",
        visible=False,
        replacement_capabilities=["contract.income.track", "contract.expense.track"],
    ),
    _cap("contract.income.track", "收入合同", "查看收入合同进展", "contract_management", access_action="smart_construction_core.action_construction_contract_income"),
    _cap("contract.expense.track", "支出合同", "查看支出合同与付款", "contract_management", access_action="smart_construction_core.action_construction_contract_expense"),
    _cap("contract.settlement.audit", "结算审核", "查看结算审核视图", "contract_management", required_roles=["finance", "executive"], required_groups=["smart_construction_core.group_sc_cap_contract_read"]),

    _cap("analytics.dashboard.executive", "经营驾驶舱", "高层经营看板", "analytics", required_roles=["executive"]),
    _cap("analytics.lifecycle.monitor", "生命周期监控", "监控生命周期推进效率", "analytics", required_roles=["pm", "executive"]),
    _cap("analytics.exception.list", "异常列表", "查看经营与执行异常", "analytics", required_roles=["executive"]),
    _cap("analytics.project.focus", "我关注的项目", "查看重点关注项目", "analytics", required_roles=["executive"]),

    _cap("governance.capability.matrix", "能力矩阵", "查看角色能力覆盖", "governance", required_roles=["pm", "finance", "executive"]),
    _cap("governance.scene.openability", "场景可打开性", "查看场景可打开性状态", "governance", required_roles=["executive"]),
    _cap("governance.runtime.audit", "运行态审计", "查看运行态治理审计", "governance", required_roles=["executive"]),

    _cap("material.catalog.open", "物资目录", "查看物资目录与分类", "material_management", required_roles=["pm", "finance", "executive"]),
    _cap("material.procurement.list", "采购清单", "查看采购与供应入口", "material_management", required_roles=["pm", "finance", "executive"]),
    _cap("labor.plan.manage", "劳务计划", "维护劳务资源计划", "material_management", required_roles=["pm", "executive"]),
    _cap("labor.request.list", "劳务申请", "查看和发起劳务申请", "material_management", required_roles=["pm", "executive"]),
    _cap("labor.attendance.list", "考勤记录", "查看劳务考勤与工时", "material_management", required_roles=["pm", "executive"]),
    _cap("labor.settlement.list", "劳务结算", "查看劳务结算", "material_management", required_roles=["pm", "finance", "executive"]),
    _cap("equipment.plan.manage", "设备计划", "维护机械设备计划", "material_management", required_roles=["pm", "executive"]),
    _cap("equipment.request.list", "设备申请", "查看和发起设备申请", "material_management", required_roles=["pm", "executive"]),
    _cap("equipment.usage.list", "设备使用登记", "查看设备使用登记", "material_management", required_roles=["pm", "executive"]),
    _cap("equipment.settlement.list", "设备结算", "查看设备结算", "material_management", required_roles=["pm", "finance", "executive"]),

    _cap("construction.plan.manage", "计划管理", "维护施工计划与计划版本", "project_management", required_roles=["pm", "executive"]),
    _cap("construction.plan.report", "计划汇报", "填报施工计划进展与偏差", "project_management", required_roles=["pm", "executive"]),
    _cap("construction.diary.open", "施工日志", "记录现场施工日志", "project_management", required_roles=["pm", "executive"]),
    _cap("quality.issue.list", "质量检查", "登记质量问题并发起闭环", "project_management", required_roles=["pm", "executive"]),
    _cap("quality.rectification.list", "质量整改", "跟踪质量整改执行", "project_management", required_roles=["pm", "executive"]),
    _cap("quality.recheck.list", "质量复验", "确认质量整改复验结果", "project_management", required_roles=["pm", "executive"]),
    _cap("safety.issue.list", "安全检查", "登记安全问题并发起闭环", "project_management", required_roles=["pm", "executive"]),
    _cap("safety.rectification.list", "安全整改", "跟踪安全整改执行", "project_management", required_roles=["pm", "executive"]),
    _cap("safety.recheck.list", "安全复验", "确认安全整改复验结果", "project_management", required_roles=["pm", "executive"]),

    _cap("workspace.today.focus", "今日关键动作", "角色首页今日关键动作", "others", required_roles=["owner", "pm", "finance", "executive"]),
    _cap("workspace.project.watch", "我关注的项目", "从角色首页进入关注项目", "others", required_roles=["owner", "pm", "finance", "executive"]),
]


def capability_groups() -> list[dict[str, Any]]:
    return [dict(item) for item in CAPABILITY_GROUPS]


def capability_definitions() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(_CAPABILITIES, start=1):
        row = dict(item)
        row.setdefault("sequence", idx * 10)
        out.append(row)
    return out


def _group_meta_map() -> dict[str, dict[str, Any]]:
    return {str(item["key"]): dict(item) for item in CAPABILITY_GROUPS}


def _resolve_role_codes_for_user(user) -> set[str]:
    if not user:
        return set()
    from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
    resolver = IdentityResolver(user.env)
    return set(resolver.assigned_role_codes(resolver.user_group_xmlids(user)))


def role_code_for_group(group_xmlid: str, *, env) -> str:
    """Project the formal role binding for a handoff hint; never infer a role."""
    from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
    text = str(group_xmlid or "").strip()
    if not text:
        return ""
    roles = IdentityResolver(env).assigned_role_codes({text})
    return roles[0] if roles else ""


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _is_group_member(user, group_xmlid: str) -> bool:
    text = str(group_xmlid or "").strip()
    if not text:
        return True
    try:
        return bool(user.has_group(text))
    except Exception:
        return False


def _published_query_pair(user, action_id):
    from odoo.addons.smart_core.delivery.runtime_route_authority import published_route_authority, iter_published_pairs
    principal_env = user.with_user(user).env
    return next((pair for pair in iter_published_pairs(published_route_authority(principal_env))
                 if pair[1] == action_id), None)


def _capability_access(defn: dict[str, Any], role_codes: set[str], user) -> tuple[bool, bool, str, str]:
    required_roles = [str(x).strip() for x in (defn.get("required_roles") or []) if str(x).strip()]
    required_groups = [str(x).strip() for x in (defn.get("required_groups") or []) if str(x).strip()]

    # Read-entry bindings use the native action, not a copied model/role table.
    # Record rules and write authorization remain in the actual ORM operation.
    access_action = defn.get("access_action")
    if access_action:
        if not user:
            return True, False, "PERMISSION_DENIED", _("需要登录后查询")
        action = user.env.ref(access_action).with_user(user)
        if action._name != "ir.actions.act_window" or not action.res_model:
            raise ValueError("Query capability requires a native window action")
        group_allowed = user._is_admin() or not action.groups_id or bool(action.groups_id & user.groups_id)
        model = user.env[action.res_model].with_user(user)
        allowed = bool(group_allowed and model.check_access_rights("read", raise_exception=False))
        if allowed and not _published_query_pair(user, action.id):
            return True, False, "NAVIGATION_AUTHORITY_DENIED", _("该入口未在当前账号的导航权限中发布")
        return True, allowed, "" if allowed else "PERMISSION_DENIED", "" if allowed else _("没有该查询入口的访问权限")

    if required_roles and not (set(required_roles) & role_codes):
        return False, False, "ROLE_SCOPE_MISMATCH", _("角色范围不匹配")

    if required_groups:
        missing_groups = [xmlid for xmlid in required_groups if not _is_group_member(user, xmlid)]
        if missing_groups:
            return True, False, "PERMISSION_DENIED", _("缺少权限组: %s") % ",".join(missing_groups)

    return True, True, "", ""


def _capability_state(defn: dict[str, Any], allowed: bool) -> tuple[str, str]:
    status = str(defn.get("status") or "ga").strip().lower()
    if not allowed:
        return "deny", ""
    if status == "alpha":
        return "coming_soon", _("能力尚在建设中，即将开放")
    if status == "beta":
        return "pending", _("能力处于试运行阶段")
    return "allow", ""


def list_capabilities_for_user(env, user) -> list[dict[str, Any]]:
    rows, _timings = list_capabilities_for_user_with_timings(env, user)
    return rows


def list_capabilities_for_user_with_timings(env, user) -> tuple[list[dict[str, Any]], dict[str, int]]:
    timings_ms: dict[str, int] = {}

    def _mark(stage: str, started_at: float) -> float:
        timings_ms[stage] = int((time.perf_counter() - started_at) * 1000)
        return time.perf_counter()

    stage_ts = time.perf_counter()
    group_meta = _group_meta_map()
    stage_ts = _mark("group_meta_map", stage_ts)
    role_codes = _resolve_role_codes_for_user(user)
    stage_ts = _mark("resolve_role_codes_for_user", stage_ts)
    definitions = capability_definitions()
    stage_ts = _mark("capability_definitions", stage_ts)

    out: list[dict[str, Any]] = []
    access_state_total_ms = 0
    entry_target_total_ms = 0
    resolve_payload_total_ms = 0
    for idx, defn in enumerate(definitions, start=1):
        if not bool(defn.get("visible", True)):
            continue
        iter_ts = time.perf_counter()
        visible, allowed, reason_code, reason = _capability_access(defn, role_codes, user)
        cap_state, cap_state_reason = _capability_state(defn, allowed)
        access_state_total_ms += int((time.perf_counter() - iter_ts) * 1000)
        if not visible:
            continue
        group_key = str(defn.get("group_key") or "others").strip() or "others"
        group = group_meta.get(group_key) or group_meta["others"]
        state = "READY"
        if cap_state in {"pending", "coming_soon"}:
            state = "PREVIEW"
        if cap_state == "deny":
            state = "LOCKED"

        capability_key = str(defn.get("key") or "").strip()
        iter_ts = time.perf_counter()
        if defn.get("access_action"):
            action = env.ref(defn["access_action"]).with_user(user)
            # The exact native action used by authorization owns navigation too.
            # Keep its context/domain on the server; /a loads the native action.
            pair = _published_query_pair(user, action.id)
            entry_target = {"target_mode": "action", "action_id": action.id,
                            "model": action.res_model}
            if pair:
                entry_target["menu_id"] = pair[0]
                entry_target["route"] = f"/a/{action.id}" + (f"?menu_id={pair[0]}" if pair[0] else "")
            payload = dict(entry_target)
            payload_timings_ms = {}
            entry_target_total_ms += int((time.perf_counter() - iter_ts) * 1000)
            iter_ts = time.perf_counter()
        else:
            entry_target = build_capability_entry_target(
                capability_key, explicit_target=defn.get("entry_target") or {}, env=env)
            entry_target_total_ms += int((time.perf_counter() - iter_ts) * 1000)
            iter_ts = time.perf_counter()
            payload, payload_timings_ms = resolve_capability_entry_target_payload_with_timings(
                env, capability_key, explicit_target=defn.get("entry_target") or {})
        resolve_payload_total_ms += int((time.perf_counter() - iter_ts) * 1000)
        if isinstance(payload_timings_ms, dict):
            for key, value in payload_timings_ms.items():
                timings_ms[f"payload.{key}"] = int(timings_ms.get(f"payload.{key}", 0) + int(value))
        item = {
            "key": capability_key,
            "name": str(defn.get("label") or defn.get("key") or "").strip(),
            "ui_label": str(defn.get("label") or defn.get("key") or "").strip(),
            "ui_hint": str(defn.get("hint") or "").strip(),
            "intent": str(defn.get("intent") or "ui.contract").strip(),
            "group_key": group_key,
            "group_label": str(group.get("label") or group_key),
            "group_icon": str(group.get("icon") or ""),
            "group_sequence": int(group.get("sequence") or 0),
            "version": "v1",
            "status": str(defn.get("status") or "ga").strip().lower(),
            "state": state,
            "capability_state": cap_state,
            "capability_state_reason": cap_state_reason,
            "reason_code": reason_code,
            "reason": reason,
            "default_payload": payload,
            "required_roles": [str(x).strip() for x in (defn.get("required_roles") or []) if str(x).strip()],
            "required_groups": [str(x).strip() for x in (defn.get("required_groups") or []) if str(x).strip()],
            "entry_target": entry_target,
            "sequence": int(defn.get("sequence") or idx * 10),
            "tags": [group_key, "registry"],
        }
        out.append(item)

    timings_ms["loop_access_and_state"] = access_state_total_ms
    timings_ms["loop_build_capability_entry_target"] = entry_target_total_ms
    timings_ms["loop_resolve_capability_entry_target_payload"] = resolve_payload_total_ms
    stage_ts = time.perf_counter()
    out.sort(key=lambda row: (int(row.get("group_sequence") or 0), int(row.get("sequence") or 0), str(row.get("key") or "")))
    _mark("final_sort", stage_ts)
    return out, timings_ms


def build_capability_matrix_for_user(env, user) -> dict[str, Any]:
    rows = list_capabilities_for_user(env, user)
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("group_key") or "others")
        bucket = grouped.setdefault(
            key,
            {
                "key": key,
                "label": row.get("group_label") or key,
                "icon": row.get("group_icon") or "",
                "sequence": int(row.get("group_sequence") or 999),
                "items": [],
            },
        )
        payload = row.get("default_payload") if isinstance(row.get("default_payload"), dict) else {}
        bucket["items"].append(
            {
                "key": row.get("key"),
                "label": row.get("ui_label") or row.get("name"),
                "icon": row.get("group_icon") or "",
                "desc": row.get("ui_hint") or "",
                "target_url": payload.get("route"),
                "action_id": payload.get("action_id"),
                "menu_id": payload.get("menu_id"),
                "scene_key": payload.get("scene_key"),
                "allowed": row.get("capability_state") != "deny",
                "deny_reason": [row.get("reason_code")] if row.get("reason_code") else [],
                "capability_state": row.get("capability_state"),
                "order": int(row.get("sequence") or 999),
            }
        )

    sections = sorted(grouped.values(), key=lambda sec: (int(sec.get("sequence") or 999), str(sec.get("key") or "")))
    for section in sections:
        section["items"] = sorted(
            section.get("items") or [],
            key=lambda item: (int(item.get("order") or 999), str(item.get("key") or "")),
        )
    return {"sections": sections}


def lint_registry(env=None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    group_keys = {str(item.get("key") or "").strip() for item in capability_groups()}
    seen: set[str] = set()
    for item in capability_definitions():
        key = str(item.get("key") or "").strip()
        if not key:
            issues.append({"code": "KEY_MISSING", "detail": item})
            continue
        if not CAPABILITY_KEY_REGEX.match(key):
            issues.append({"code": "KEY_FORMAT_INVALID", "capability_key": key})
        if key in seen:
            issues.append({"code": "KEY_DUPLICATE", "capability_key": key})
        seen.add(key)
        group_key = str(item.get("group_key") or "").strip()
        if not group_key:
            issues.append({"code": "GROUP_KEY_REQUIRED", "capability_key": key})
        elif group_key not in group_keys:
            issues.append({"code": "GROUP_KEY_UNKNOWN", "capability_key": key, "group_key": group_key})

        scene_key = resolve_capability_entry_scene_key(key)
        if item.get("access_action"):
            if scene_key:
                issues.append({"code": "DUPLICATE_QUERY_SCENE_TARGET", "capability_key": key})
            if env is not None:
                action = env.ref(item["access_action"], raise_if_not_found=False)
                if not action or action._name != "ir.actions.act_window" or not action.res_model:
                    issues.append({"code": "QUERY_ACTION_INVALID", "capability_key": key})
        elif not scene_key:
            issues.append({"code": "ENTRY_TARGET_SCENE_REQUIRED", "capability_key": key})

    if len(capability_definitions()) < 30:
        issues.append({"code": "CAPABILITY_COUNT_TOO_LOW", "count": len(capability_definitions()), "min": 30})

    if env is not None:
        scene_keys = {
            str(row.get("code") or row.get("key") or "").strip()
            for row in (scene_registry.load_scene_configs(env) or [])
            if isinstance(row, dict) and str(row.get("code") or row.get("key") or "").strip()
        }
        scene_keys.update(RUNTIME_ORCHESTRATION_SCENE_KEYS)
        for item in capability_definitions():
            key = str(item.get("key") or "").strip()
            scene_key = resolve_capability_entry_scene_key(key)
            if scene_key and scene_key not in scene_keys:
                issues.append({"code": "ENTRY_TARGET_SCENE_NOT_FOUND", "capability_key": key, "scene_key": scene_key})

    return issues


def capability_authorization_for_user(user, capability_key: str) -> dict[str, Any]:
    """Resolve one declared capability's authorization for *user*.

    Action-bound queries consume native action groups and model read ACLs; other definitions retain their
    declared role/group constraints. This returns the same decision the capability
    list publishes, so a role-gated page region and the capability matrix cannot
    drift into two rules.  An unknown key is denied rather than silently allowed.
    """
    key = str(capability_key or "").strip()
    definition = None
    for item in capability_definitions():
        if str(item.get("key") or "").strip() == key:
            definition = item
            break
    if not key or not isinstance(definition, dict):
        return {
            "capability": key,
            "state": "deny",
            "reason_code": "UNDECLARED_CAPABILITY",
            "reason": _("未声明的能力"),
        }
    role_codes = _resolve_role_codes_for_user(user)
    visible, allowed, reason_code, reason = _capability_access(definition, role_codes, user)
    if not visible:
        cap_state, cap_state_reason = "deny", reason or _("角色范围不匹配")
    else:
        cap_state, cap_state_reason = _capability_state(definition, allowed)
    authorization: dict[str, Any] = {
        "capability": key,
        "state": cap_state,
        "reason_code": reason_code or "",
        "reason": cap_state_reason or reason or "",
    }
    required_roles = [str(item).strip() for item in (definition.get("required_roles") or []) if str(item).strip()]
    required_groups = [str(item).strip() for item in (definition.get("required_groups") or []) if str(item).strip()]
    if required_roles:
        authorization["required_roles"] = required_roles
    if required_groups:
        authorization["required_groups"] = required_groups
    return authorization


def capability_registry_summary(env, user) -> dict[str, Any]:
    caps = list_capabilities_for_user(env, user)
    by_role = sorted(_resolve_role_codes_for_user(user))
    allow_count = len([row for row in caps if row.get("capability_state") in {"allow", "readonly"}])
    deny_count = len([row for row in caps if row.get("capability_state") == "deny"])
    return {
        "total": len(caps),
        "allow_count": allow_count,
        "deny_count": deny_count,
        "roles": by_role,
    }

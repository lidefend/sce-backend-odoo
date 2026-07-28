# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from pathlib import Path

from odoo import fields

from odoo.addons.smart_construction_core.services.project_decision_engine_service import ProjectDecisionEngineService
from odoo.addons.smart_construction_core.services.project_metrics_explain_service import ProjectMetricsExplainService
from odoo.addons.smart_construction_core.services.project_authorization_service import (
    ProjectAuthorizationService,
    ProjectResolution,
)
from odoo.addons.smart_construction_core.services.project_state_explain_service import (
    ProjectStateExplainService,
    lifecycle_state_label,
)
from odoo.addons.smart_construction_core.services.project_task_state_support import (
    ProjectTaskStateSupport,
)
from odoo.addons.smart_construction_core.services.evidence_chain_service import (
    EvidenceChainService,
)

from .project_dashboard_builders import BUILDERS

_logger = logging.getLogger(__name__)


class _NullEvidenceSummaryService:
    def summary_for_project(self, _project):
        return {}


class ProjectDashboardService:
    """Provide business-truth-backed dashboard data for orchestration carriers."""
    SOURCE_KIND = "project_dashboard_business_fact_projection"
    SOURCE_AUTHORITIES = (
        "project.project",
        "project.task",
        "payment.request",
        "payment.ledger",
        "project.cost.ledger",
        "sc.evidence.summary.service",
        "business_projection_models",
        "odoo.orm",
        "odoo.read_group",
    )

    ENTRY_BLOCKS = (
        ("progress", "项目进度", "deferred"),
        ("risks", "风险提醒", "deferred"),
        ("next_actions", "下一步动作", "deferred"),
    )
    ZONE_BLOCKS = (
        ("header", "项目头部信息", "hero", "stack", "block.project.header"),
        ("metrics", "关键指标", "primary", "grid", "block.project.metrics"),
        ("progress", "项目进度", "primary", "stack", "block.project.progress"),
        ("contract", "合同执行", "secondary", "stack", "block.project.contract"),
        ("cost", "成本控制", "secondary", "stack", "block.project.cost"),
        ("finance", "资金情况", "secondary", "stack", "block.project.finance"),
        ("risk", "风险提醒", "supporting", "stack", "block.project.risk"),
    )
    RUNTIME_BLOCK_MAP = {
        "progress": "block.project.progress",
        "risks": "block.project.risk",
        "risk": "block.project.risk",
        "next_actions": "block.project.next_actions",
    }

    def __init__(self, env):
        self._authorized_resolution = None
        self._bind_env(env)

    def _bind_env(self, env):
        """Bind every derived query service to the same caller-scoped env."""

        self._authorized_resolution = None
        self.env = env
        self._authorization_service = ProjectAuthorizationService(env)
        evidence_summary_service = self._model("sc.evidence.summary.service")
        self._evidence_summary_service = evidence_summary_service or _NullEvidenceSummaryService()
        self._decision_engine = ProjectDecisionEngineService(env)
        self._state_explain_service = ProjectStateExplainService(env)
        self._metrics_explain_service = ProjectMetricsExplainService(env)
        self._builders = [builder_cls(env) for builder_cls in BUILDERS]
        self._builder_map = {builder.block_key: builder for builder in self._builders}

    def bind_authorized_resolution(self, resolution):
        """Consume one caller-scoped authorization result for this request.

        Dashboard orchestration calls the project resolver more than once.
        Binding the original result prevents those internal calls from
        reinterpreting a verified single-company selection as an omitted
        selector and rebuilding the broader user company scope.
        """

        if not isinstance(resolution, ProjectResolution):
            raise ValueError("invalid project authorization result")
        project = resolution.project
        if (
            not resolution.available
            or not project
            or bool(getattr(resolution.env, "su", False))
            or int(resolution.env.uid) != int(self.env.uid)
            or int(project.env.uid) != int(resolution.env.uid)
        ):
            raise ValueError("unavailable project authorization result")
        allowed_company_ids = tuple(
            int(company_id)
            for company_id in (
                resolution.env.context.get("allowed_company_ids") or []
            )
        )
        project_company_id = int(getattr(project.company_id, "id", 0) or 0)
        if not allowed_company_ids or project_company_id not in allowed_company_ids:
            raise ValueError("project outside authorized company scope")

        self._bind_env(resolution.env)
        self._authorized_resolution = resolution
        return self

    def source_authority_contract(self):
        provider_path = self._registry_provider_path()
        return {
            "kind": self.SOURCE_KIND,
            "authorities": list(self.SOURCE_AUTHORITIES),
            "projection_only": True,
            "no_frontend_synthetic_metrics": True,
            "scene_provider_registry": {
                "scene_key": "project.management",
                "provider_path": str(provider_path) if provider_path else "",
                "resolved": bool(provider_path),
            },
        }

    def _registry_provider_path(self):
        try:
            from odoo.addons.smart_scene.core.scene_provider_registry import resolve_scene_provider_path
        except Exception:
            return None
        try:
            return resolve_scene_provider_path("project.management", Path(__file__).resolve())
        except Exception:
            return None

    def build(self, project_id=0, context=None):
        """Compatibility envelope retained for project.dashboard handler callers."""
        request_context = dict(context or {})
        project, diagnostics = self.resolve_project_with_diagnostics(project_id)
        project_data = self.project_payload(project)
        state_explain = self.build_state_explain(project)
        metrics_explain = self.build_metrics_explain(project)
        summary_rows = self.build_summary_rows(project)
        flow_map = self.build_flow_map(project)
        completion = self.build_completion(project)
        zones = {
            "header": {
                "project": project_data,
                "state_explain": state_explain,
                "resolution": diagnostics,
            },
            "metrics": {
                "items": metrics_explain,
            },
            "progress": {
                "summary_rows": summary_rows,
                "flow_map": flow_map,
                "completion": completion,
                "block": self.build_block("progress", project=project, context=request_context),
            },
            "contract": {
                "summary_rows": [
                    row for row in summary_rows if str(row.get("key") or "") in {"stage_label", "milestone_label"}
                ],
            },
            "cost": {
                "summary_rows": [row for row in summary_rows if str(row.get("key") or "") == "cost_total"],
            },
            "finance": {
                "summary_rows": [
                    row
                    for row in summary_rows
                    if str(row.get("key") or "") in {"payment_total", "payment_executed_total"}
                ],
                "next_actions": self.build_block("next_actions", project=project, context=request_context),
            },
            "risk": {
                "block": self.build_block("risks", project=project, context=request_context),
            },
        }

        return {
            "scene": {
                "key": "project.management",
                "page": "project.management.dashboard",
            },
            "page": {
                "key": "project.management.dashboard",
                "route": "/s/project.management",
            },
            "route_context": self._route_context(project),
            "project": project_data,
            "source_authority": self.source_authority_contract(),
            "summary_rows": summary_rows,
            "state_explain": state_explain,
            "metrics_explain": metrics_explain,
            "flow_map": flow_map,
            "completion": completion,
            "zones": zones,
        }

    def _route_context(self, project):
        project_id = int(getattr(project, "id", 0) or 0)
        return {
            "primary_protocol": "/s/project.management?project_id=<id>",
            "query_key": "project_id",
            "scene_route": "/s/project.management",
            "project_route_template": "/s/project.management?project_id={project_id}",
            "project_route": "/s/project.management?project_id=%s" % project_id,
            "project_id": project_id,
        }

    def build_block(self, block_key, project=None, context=None):
        normalized_key = str(block_key or "").strip().lower()
        builder_key = self.RUNTIME_BLOCK_MAP.get(normalized_key)
        if not builder_key:
            return self.error_block(normalized_key or "unknown", "UNSUPPORTED_BLOCK_KEY")

        builder = self._builder_map.get(builder_key)
        if builder is None:
            block = self.error_block(builder_key, "BLOCK_BUILDER_NOT_FOUND")
        else:
            try:
                block = builder.build(project=project, context=dict(context or {}))
            except Exception:
                block = self.error_block(builder_key, "BLOCK_BUILD_FAILED")
        return block if isinstance(block, dict) else self.error_block(builder_key, "INVALID_BLOCK_PAYLOAD")

    def _model(self, model_name):
        try:
            return self.env[model_name]
        except Exception:
            return None

    def _project_domain_for_user(self):
        model = self._model("project.project")
        if model is None:
            return []
        f = getattr(model, "_fields", {})
        uid = int(self.env.user.id)
        ors = []
        for field in ("manager_id", "owner_id", "user_id"):
            if field in f:
                ors.append((field, "=", uid))
        if "create_uid" in f:
            ors.append(("create_uid", "=", uid))
        for field in ("user_ids", "member_ids", "member_user_ids"):
            if field in f:
                ors.append((field, "in", [uid]))
        if not ors:
            return []
        if len(ors) == 1:
            return [ors[0]]
        return (["|"] * (len(ors) - 1)) + ors

    def _resolve_project(self, project_id):
        project, _diag = self.resolve_project_with_diagnostics(project_id)
        return project

    def resolve_project_with_diagnostics(self, project_id):
        if self._authorized_resolution is not None:
            resolution = self._authorized_resolution
            try:
                requested_id = int(project_id or 0)
            except (TypeError, ValueError):
                requested_id = 0
            if requested_id == int(resolution.project.id):
                return resolution.project, dict(resolution.diagnostics)
            return (
                resolution.env["project.project"].browse([]),
                {
                    "status": "unavailable",
                    "resolution_path": "project_unavailable",
                },
            )

        resolution = self._authorization_service.resolve(project_id=project_id)
        # All payload, builder, aggregate, and related-model reads that follow
        # must inherit exactly the resolver's caller identity/company scope.
        if resolution.env is not self.env:
            self._bind_env(resolution.env)
        return resolution.project, dict(resolution.diagnostics)

    def project_payload(self, project):
        def _safe_text(value):
            try:
                return str(value or "")
            except Exception:
                return ""

        def _safe_rel_name(record, field_name):
            try:
                relation = getattr(record, field_name, None)
            except Exception:
                return ""
            return _safe_text(getattr(relation, "display_name", ""))

        def _safe_field(record, field_name):
            try:
                return getattr(record, field_name, "")
            except Exception:
                return ""

        if not project:
            return {
                "id": 0,
                "name": "",
                "project_code": "",
                "partner_name": "",
                "manager_name": "",
                "stage_name": "",
                "lifecycle_state": "",
                "milestone": "",
                "state": "empty",
                "progress_percent": "0",
                "cost_total": "0",
                "payment_total": "0",
                "status": "",
                "date": str(fields.Date.today()),
            }
        progress_percent = 0.0
        try:
            task_model = self._model("project.task")
            if task_model is not None:
                total = int(task_model.search_count([("project_id", "=", int(project.id))]))
                done = int(
                    task_model.search_count(
                        [("project_id", "=", int(project.id))] + ProjectTaskStateSupport.done_domain()
                    )
                )
                if total > 0:
                    progress_percent = round((done / float(total)) * 100.0, 2)
        except Exception:
            progress_percent = 0.0
        evidence_summary = self._evidence_summary_service.summary_for_project(project)
        evidence_chain = EvidenceChainService(self.env).build_project_chain(
            int(project.id)
        )
        risk_analysis = self._decision_engine.analyze(project)
        risk_count = int(risk_analysis.get("risk_count") or 0)
        exception_model = self._model("sc.evidence.exception")
        exception_open_count = 0
        exception_resolved_count = 0
        if exception_model is not None:
            try:
                exception_open_count = int(
                    exception_model.search_count([("project_id", "=", int(project.id)), ("status", "in", ["open", "processing"])])
                )
                exception_resolved_count = int(
                    exception_model.search_count([("project_id", "=", int(project.id)), ("status", "=", "resolved")])
                )
            except Exception:
                exception_open_count = 0
                exception_resolved_count = 0
        fact_metrics = [
            {
                "key": "payment_total",
                "label": "已付款",
                "value": float(evidence_summary.get("pay_total") or 0.0),
                "unit": "元",
                "trace_action": {
                    "intent": "business.evidence.trace",
                    "payload": {
                        "business_model": "project.project",
                        "business_id": int(project.id),
                        "evidence_type": "payment",
                    },
                },
            },
            {
                "key": "cost_total",
                "label": "已发生成本",
                "value": float(evidence_summary.get("cost_total") or 0.0),
                "unit": "元",
                "trace_action": {
                    "intent": "business.evidence.trace",
                    "payload": {
                        "business_model": "project.project",
                        "business_id": int(project.id),
                        "evidence_type": "cost",
                    },
                },
            },
            {
                "key": "settlement_total",
                "label": "已结算",
                "value": float(evidence_summary.get("settlement_total") or 0.0),
                "unit": "元",
                "trace_action": {
                    "intent": "business.evidence.trace",
                    "payload": {
                        "business_model": "project.project",
                        "business_id": int(project.id),
                        "evidence_type": "settlement",
                    },
                },
            },
            {
                "key": "risk_count",
                "label": "风险事项",
                "value": risk_count,
                "unit": "项",
                "trace_action": {
                    "intent": "business.evidence.trace",
                    "payload": {
                        "business_model": "project.project",
                        "business_id": int(project.id),
                        "evidence_type": "risk",
                    },
                },
            },
        ]
        return {
            "id": int(project.id),
            "name": _safe_text(_safe_field(project, "name")),
            "project_code": _safe_text(_safe_field(project, "project_code")),
            "operation_strategy": _safe_text(_safe_field(project, "operation_strategy")),
            "operation_strategy_label": dict(project._fields["operation_strategy"].selection).get(
                _safe_text(_safe_field(project, "operation_strategy")),
                _safe_text(_safe_field(project, "operation_strategy")),
            ) if "operation_strategy" in project._fields else "",
            "partner_name": _safe_rel_name(project, "partner_id"),
            "manager_name": _safe_rel_name(project, "user_id"),
            "stage_name": lifecycle_state_label(project),
            "health_state": _safe_text(_safe_field(project, "health_state")),
            "lifecycle_state": _safe_text(_safe_field(project, "lifecycle_state")),
            "milestone": _safe_text(_safe_field(project, "sc_execution_state")),
            "state": "ready",
            "progress_percent": str(progress_percent),
            "cost_total": str(evidence_summary.get("cost_total") or 0.0),
            "payment_total": str(evidence_summary.get("pay_total") or 0.0),
            "payment_executed_total": str(evidence_summary.get("pay_done_total") or 0.0),
            "payment_executed_record_count": str(evidence_summary.get("pay_done_count") or 0),
            "evidence_refs": evidence_chain.get("evidence_refs") or [],
            "evidence_summary": evidence_summary,
            "fact_metrics": fact_metrics,
            "facts": {
                "cost_total": str(evidence_summary.get("cost_total") or 0.0),
                "payment_total": str(evidence_summary.get("pay_total") or 0.0),
                "payment_executed_total": str(evidence_summary.get("pay_done_total") or 0.0),
                "evidence_count": int(evidence_summary.get("evidence_count") or 0),
                "cost_evidence_count": int(evidence_summary.get("cost_count") or 0),
                "payment_evidence_count": int(evidence_summary.get("payment_count") or 0),
                "settlement_evidence_count": int(evidence_summary.get("settlement_count") or 0),
                "risk_count": risk_count,
                "exception_open_count": exception_open_count,
                "exception_resolved_count": exception_resolved_count,
            },
            "status": _safe_text(_safe_field(project, "health_state") or _safe_field(project, "state")),
            "date": str(fields.Date.today()),
        }

    def build_state_explain(self, project):
        state_explain = self._state_explain_service.build(project)
        if not project:
            return {
                "execution_stage_label": state_explain.get("execution_stage_label") or state_explain.get("stage_label") or "未选择项目",
                "stage_label": state_explain.get("stage_label") or "未选择项目",
                "execution_stage_explain": state_explain.get("execution_stage_explain") or state_explain.get("stage_explain") or "当前没有可用项目，无法进入项目驾驶舱。",
                "stage_explain": state_explain.get("stage_explain") or state_explain.get("execution_stage_explain") or "当前没有可用项目，无法进入项目驾驶舱。",
                "milestone_explain": "暂无项目里程碑。",
                "project_condition_explain": state_explain.get("project_condition_explain") or state_explain.get("status_explain") or "请先选择项目或创建项目。",
                "status_explain": state_explain.get("status_explain") or state_explain.get("project_condition_explain") or "请先选择项目或创建项目。",
            }
        milestone = str(getattr(project, "sc_execution_state", "") or "").strip().lower()
        milestone_explain_map = {
            "ready": "当前执行准备已完成，可以进入执行推进。",
            "in_progress": "当前执行正在推进，建议优先补齐成本与付款事实。",
            "done": "当前执行动作已完成，可继续检查成本、付款与结算结果。",
        }
        return {
            "execution_stage_label": state_explain.get("execution_stage_label") or state_explain.get("stage_label") or "未设置阶段",
            "stage_label": state_explain.get("stage_label") or "未设置阶段",
            "execution_stage_explain": state_explain.get("execution_stage_explain") or state_explain.get("stage_explain") or "当前项目处于已发布主线中，请按下一步动作推进。",
            "stage_explain": state_explain.get("stage_explain") or state_explain.get("execution_stage_explain") or "当前项目处于已发布主线中，请按下一步动作推进。",
            "milestone_explain": milestone_explain_map.get(milestone, "当前里程碑尚未进入显式执行状态。"),
            "project_condition_explain": state_explain.get("project_condition_explain") or state_explain.get("status_explain") or "当前项目整体正常。",
            "status_explain": state_explain.get("status_explain") or state_explain.get("project_condition_explain") or "当前项目整体正常。",
        }

    def build_summary_rows(self, project):
        project_payload = self.project_payload(project)
        state_explain = self.build_state_explain(project)
        metrics_explain = self.build_metrics_explain(project)
        metrics_map = {}
        for item in metrics_explain or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            metrics_map[key] = item
        return [
            {
                "key": "stage_label",
                "label": "项目执行阶段",
                "value": str(state_explain.get("execution_stage_label") or "未设置阶段"),
                "copy": "主流程位置",
            },
            {
                "key": "milestone_label",
                "label": "当前里程碑",
                "value": str(project_payload.get("milestone") or ""),
                "copy": "执行推进节点",
            },
            {
                "key": "progress_percent",
                "label": "执行进度",
                "value": "%s%%" % str(project_payload.get("progress_percent") or 0),
                "copy": str((metrics_map.get("progress") or {}).get("explain") or "任务与里程碑综合进度"),
            },
            {
                "key": "cost_total",
                "label": "成本合计",
                "value": str(project_payload.get("cost_total") or 0),
                "copy": str((metrics_map.get("cost") or {}).get("explain") or "当前经营事实"),
            },
            {
                "key": "payment_total",
                "label": "付款合计",
                "value": str(project_payload.get("payment_total") or 0),
                "copy": str((metrics_map.get("payment") or {}).get("explain") or "当前资金事实"),
            },
            {
                "key": "payment_executed_total",
                "label": "已支付证据",
                "value": str(project_payload.get("payment_executed_total") or 0),
                "copy": "%s 条 payment.ledger 台账" % str(project_payload.get("payment_executed_record_count") or 0),
            },
        ]

    def build_metrics_explain(self, project):
        return self._metrics_explain_service.build(self.project_payload(project))

    def build_flow_map(self, project):
        project_payload = self.project_payload(project)
        decision = self._decision_engine.decide(project)
        signals = (decision.get("facts") or {}).get("signals") or {}
        lifecycle_state = str(project_payload.get("lifecycle_state") or "").strip().lower()
        facts = decision.get("facts") or {}
        payment_count = int(facts.get("payment_count") or 0)
        cost_count = int(facts.get("cost_count") or 0)

        current_stage = "initiation"
        is_completed = bool(signals.get("settlement_completed"))
        if lifecycle_state == "draft":
            current_stage = "initiation"
        elif lifecycle_state in {"closing", "warranty", "done"}:
            current_stage = "settlement"
        elif payment_count > 0:
            current_stage = "payment"
        elif cost_count > 0:
            current_stage = "cost"
        elif lifecycle_state in {"in_progress"}:
            current_stage = "execution"
        elif signals.get("payment_exceeds_cost") or signals.get("ready_for_settlement"):
            current_stage = "settlement"

        stage_order = ["initiation", "execution", "cost", "payment", "settlement"]
        stage_labels = {
            "initiation": "立项",
            "execution": "执行",
            "cost": "成本",
            "payment": "付款",
            "settlement": "结算",
        }
        current_index = stage_order.index(current_stage)
        items = []
        for index, key in enumerate(stage_order):
            if is_completed:
                status = "done"
            else:
                status = "done" if index < current_index else "current" if index == current_index else "todo"
            items.append(
                {
                    "key": key,
                    "label": stage_labels.get(key) or key,
                    "status": status,
                }
            )
        return {
            "current_stage": current_stage,
            "items": items,
        }

    def build_completion(self, project):
        decision = self._decision_engine.decide(project)
        facts = decision.get("facts") or {}
        signals = facts.get("signals") or {}
        lifecycle_state = str(facts.get("lifecycle_state") or "").strip().lower()
        percent = 20
        next_target = "进入执行"
        if signals.get("settlement_completed"):
            percent = 100
            next_target = "项目已完成"
        elif signals.get("is_draft"):
            percent = 20
            next_target = "开始执行"
        elif lifecycle_state in {"closing", "warranty", "done"}:
            percent = 90
            next_target = "完成结算确认"
        elif signals.get("no_tasks"):
            percent = 35
            next_target = "创建任务"
        elif signals.get("no_cost"):
            percent = 50
            next_target = "完成成本录入"
        elif signals.get("no_payment"):
            percent = 70
            next_target = "完成付款记录"
        elif signals.get("ready_for_settlement") or signals.get("payment_exceeds_cost"):
            percent = 85
            next_target = "完成结算检查"
        return {
            "percent": percent,
            "next_target": next_target,
        }

    @staticmethod
    def error_block(block_key, code):
        return {
            "block_key": block_key,
            "block_type": "unknown",
            "title": block_key,
            "state": "error",
            "visibility": {"allowed": True, "reason_code": "OK", "reason": ""},
            "data": {},
            "error": {"code": code, "message": code},
        }

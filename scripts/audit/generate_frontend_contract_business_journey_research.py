#!/usr/bin/env python3
"""Generate the Contract V2 and formal-entry frontend research matrices."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASELINE_SHA = "9821a9c688cbd4abb44f378051fc6c6362c5d8cd"
BUSINESS_CSV = ROOT / "docs/product/frontend_business_entry_acceptance_v1.csv"
CAPABILITY_MATRIX_MD = ROOT / "docs/product/formal_business_operation_capability_matrix_v1.md"
UX_COVERAGE_JSON = ROOT / "docs/product/system_user_experience_coverage_v1.json"
CONTRACT_SCHEMA = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
CONTRACT_TYPES = ROOT / "frontend/apps/web/src/app/contracts/v2/types.ts"
FRONTEND_SRC = ROOT / "frontend/apps/web/src"
OUTPUT_JSON = ROOT / "docs/frontend_productization/contract-v2-consumption-research-v1.json"
OUTPUT_CSV = ROOT / "docs/frontend_productization/business-entry-journey-evidence-v1.csv"


FULL_DECLARED_SCOPE = {
    "smart_construction_core.menu_sc_project_project": (
        "项目台账声明职责（查询、详情、字段/关系写入、必填拒绝、草稿恢复）有页面证据"
    ),
    "smart_construction_core.menu_sc_product_project_lifecycle_v1": (
        "项目生命周期声明动作与状态回读均在真实入口执行"
    ),
    "smart_construction_core.menu_sc_p1_daily_contract": (
        "日常合同声明流转、查询、字段写入和角色边界有页面证据"
    ),
    "smart_construction_core.menu_sc_user_payment_apply": (
        "付款申请创建、审批链、附件、明细、分页和回读有页面证据"
    ),
}

CREATE_WRITE_SCOPE = {
    "smart_construction_core.menu_sc_project_initiation": (
        "新项目立项有创建、跳转和回读证据；未覆盖后续完整项目生命周期"
    ),
}

CORE_ORM_SMOKE = {
    "smart_construction_core.menu_sc_general_contract",
    "smart_construction_core.menu_sc_construction_contract",
    "smart_construction_core.menu_project_material_plan",
    "smart_construction_core.menu_sc_material_inbound",
    "smart_construction_core.menu_sc_material_outbound",
    "smart_construction_core.menu_sc_subcontract_request",
    "smart_construction_core.menu_sc_subcontract_settlement",
    "smart_construction_core.menu_sc_labor_usage_acceptance",
    "smart_construction_core.menu_sc_equipment_shift_acceptance",
    "smart_construction_core.menu_sc_receipt_income",
    "smart_construction_core.menu_sc_expense_claim",
    "smart_construction_core.menu_sc_invoice_input",
}

WORKFLOW_EXECUTED = {
    "smart_construction_core.menu_sc_product_project_lifecycle_v1",
    "smart_construction_core.menu_sc_p1_daily_contract",
    "smart_construction_core.menu_sc_user_payment_apply",
}

ATTACHMENT_EXECUTED = {"smart_construction_core.menu_sc_user_payment_apply"}
INTERACTIVE_PAGINATION = {"smart_construction_core.menu_sc_user_payment_apply"}
MOBILE_EXECUTED = {"smart_construction_core.menu_sc_p1_daily_contract"}

EMPTY_EVIDENCE_RE = re.compile(r"空态|无记录|详情回读未执行|渲染记录 0|renders 0")
DETAIL_EVIDENCE_RE = re.compile(r"详情回读 record_id|record_id=")
NEGATIVE_AUTH_RE = re.compile(r"负例|0 泄漏|leaked_entries|NAVIGATION_AUTHORITY_DENIED")
SERVED_RE = re.compile(r"served\s+([0-9a-f]{7,40})", re.IGNORECASE)
CANDIDATE_RE = re.compile(r"(?:candidate|候选)\s*([0-9a-f]{7,40})", re.IGNORECASE)
HEX_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)


def facet(
    facet_id: str,
    domain: str,
    declaration: str,
    consumers: list[str],
    evidence: list[str],
    targets: list[str],
    verdict: str,
    severity: str,
    current_product_impact: str,
    finding: str,
    owner: str,
) -> dict[str, Any]:
    return {
        "id": facet_id,
        "domain": domain,
        "declaration": declaration,
        "frontendConsumers": consumers,
        "behaviorEvidence": evidence,
        "registeredTargets": targets,
        "verdict": verdict,
        "severity": severity,
        "currentProductImpact": current_product_impact,
        "finding": finding,
        "nextActionOwner": owner,
    }


FACETS = [
    facet(
        "field-identity-type-widget",
        "field",
        "dataContract/mainData + layout fields + widget.fieldDescriptor",
        ["contracts/v2/schema.ts", "app/presentation/contractFormPresenter.ts", "components/FieldValue.vue"],
        ["frontend/apps/web/scripts/contract_field_occurrence_identity_test.ts"],
        ["verify" ".frontend.contract_v2_occurrence_authority.unit", "verify" ".frontend.native_widget_provenance.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "字段身份、类型、原生 widget 来源和 occurrence 身份有 schema、运行时消费与行为测试。",
        "P0",
    ),
    facet(
        "field-labels-help",
        "field",
        "widget.label + formStructureContract.fieldLabels + fieldInfo/help",
        ["app/presentation/contractFormPresenter.ts", "pages/contractForm", "components/FieldValue.vue"],
        ["frontend/apps/web/scripts/canonical_form_presenter_test.ts"],
        ["verify" ".frontend.canonical_form_presenter.unit", "verify" ".frontend.native_form_structure_responsibility.unit"],
        "aligned",
        "medium",
        "verified_for_current_contract_consumers",
        "字段标签由有效结构优先给出；原生 help 沿用官方帮助交互，不由前端另造业务文案。",
        "P0",
    ),
    facet(
        "field-modifiers",
        "field",
        "required/readonly/invisible/disabled + widgetStatus/containerStatus",
        ["app/presentation/contractFormPresenter.ts", "app/contracts/v2/store.ts", "pages/contractForm"],
        ["frontend/apps/web/scripts/contract_consumption_verdicts_test.ts", "frontend/apps/web/scripts/contract_v2_occurrence_authority_test.ts"],
        ["verify" ".frontend.contract_consumption_verdicts.unit", "verify" ".frontend.contract_v2_occurrence_authority.unit", "verify" ".frontend.modifiers_runtime.guard"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "必填、只读、隐藏、禁用与权威 occurrence 状态均有非零行为锁；未发现默认允许式兜底。",
        "P0",
    ),
    facet(
        "dynamic-onchange-modifiers",
        "field",
        "runtime onchange patch + modifiers_patch + computed domain/context",
        ["pages/ContractFormPage.vue", "pages/contractForm/useRecordFormLayout.ts", "app/contracts/v2/store.ts"],
        ["frontend/apps/web/scripts/native_form_structure_responsibility_test.ts"],
        ["verify" ".frontend.onchange_roundtrip.guard", "verify" ".frontend.onchange_line_patch.guard", "verify" ".frontend.modifiers_runtime.guard"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "动态修饰、onchange 往返与明细行补丁有注册守卫；仍需在核心新入口补页面级回归。",
        "P0/P4",
    ),
    facet(
        "layout-container-order-zone",
        "layout",
        "layoutContract.containerTree + container order/zone",
        ["app/presentation/contractFormPresenter.ts", "pages/contractForm", "components/template"],
        ["frontend/apps/web/scripts/native_form_structure_responsibility_test.ts"],
        ["verify" ".frontend.native_form_structure_responsibility.unit", "verify" ".frontend.form_structure_contract_projection.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "容器树、节点顺序和区域声明由统一呈现模型消费，不以角色或模型另选结构。",
        "P0",
    ),
    facet(
        "layout-span-columns",
        "layout",
        "24-grid span + container columns + containedFieldLayout",
        ["app/presentation/canonicalFormFloorplan.ts", "components/template/NativeNodeComponent.vue"],
        ["frontend/apps/web/scripts/native_form_structure_responsibility_test.ts"],
        ["verify" ".frontend.form_canvas_layout.unit", "verify" ".frontend.workspace_layout_contract.unit", "verify" ".frontend.form_canvas_layout.guard"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "网格、跨度、容器列数和响应式折叠遵循唯一布局方言。",
        "P0",
    ),
    facet(
        "form-structure-authority-surfaces",
        "layout",
        "formStructureContract structureAuthority/roles/surfaces/authorization",
        ["app/presentation/contractFormPresenter.ts", "app/contracts/v2/store.ts", "pages/contractForm"],
        ["frontend/apps/web/scripts/form_structure_surface_contract_test.ts"],
        ["verify" ".frontend.form_structure_surface_contract.unit", "verify" ".frontend.form_structure_contract_projection.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "结构权威和协作/审计表面的 allow/deny/pending/coming_soon 有显式消费，非 allow 不显示。",
        "P0",
    ),
    facet(
        "domain-context-scope",
        "data",
        "field/data/action/nativeAction domain and context",
        ["app/runtime", "app/action_runtime", "pages/contractForm/useRecordRelationships.ts"],
        ["frontend/apps/web/scripts/action_view_context_policy_test.ts"],
        ["verify" ".frontend.action_view_context_policy.unit", "verify" ".frontend.native_action_contract_consumption.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "动作、列表和关系请求继续传递契约 domain/context；未发现页面按模型名补造作用域。",
        "P0",
    ),
    facet(
        "relation-entry-search-limits",
        "relation",
        "relation_entry/domain/context + relation search columns and limits",
        ["pages/contractForm/useRecordRelationships.ts", "pages/contractForm/RelationSearchDialog.vue"],
        ["frontend/apps/web/scripts/relation_read_closure_test.ts"],
        ["verify" ".frontend.relation_entry.contract_guard", "verify" ".frontend.relation_read_closure.guard", "verify" ".frontend.professional_relation_field.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "关系选择范围、搜索列、受控新增和读取闭合有守卫；付款申请另有页面级关系选择清除证据。",
        "P0",
    ),
    facet(
        "one2many-commands-line-identity",
        "relation",
        "one2many commands + occurrenceKey/public row identity + subview capabilities",
        ["pages/contractForm/one2manyUtils.ts", "pages/contractForm/useRecordRelationships.ts", "components/template/X2ManyRelationRenderer.vue"],
        ["frontend/apps/web/scripts/detail_collection_pagination_test.ts"],
        ["verify" ".frontend.professional_detail_collection.unit", "verify" ".frontend.contract_v2_occurrence_authority.unit"],
        "aligned",
        "high",
        "verified_for_payment_application",
        "明细行身份、创建/编辑/删除命令和付款申请多行编辑已有声明及页面证据。",
        "P0/P1",
    ),
    facet(
        "relation-warnings-patch-conflict",
        "relation",
        "one2many warnings + optimistic baseline/conflict + recovery",
        ["app/presentation/boqLinePatch.ts", "components/action/HierarchicalWorksheet.vue", "pages/ContractFormPage.vue"],
        ["frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts"],
        ["verify" ".frontend.overlay_lifecycle.unit", "verify" ".frontend.contract_v2_runtime_policy.unit"],
        "aligned",
        "medium",
        "verified_for_current_contract_consumers",
        "冲突、警告和恢复状态有显式展示；覆盖范围仍需扩展至更多普通 one2many 入口。",
        "P0/P4",
    ),
    facet(
        "search-filters",
        "search",
        "searchContract.filters + selectorStatus",
        ["app/action_runtime/useActionViewFilterComputedRuntime.ts", "components/action/ActionSurfaceToolbar.vue"],
        ["frontend/apps/web/scripts/contract_consumption_verdicts_test.ts"],
        ["verify" ".frontend.contract_consumption_verdicts.unit", "verify" ".frontend.native_action_contract_consumption.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "筛选 chips、domain/context 和 selector 禁用状态由同一契约输入生成。",
        "P0",
    ),
    facet(
        "search-saved-custom-favorites",
        "search",
        "searchContract.saved_filters/custom/favorites + mutation authority",
        ["app/action_runtime/useActionViewFilterComputedRuntime.ts", "components/action/ActionSurfaceToolbar.vue", "app/runtime/savedSearchSubmission.ts"],
        ["frontend/apps/web/scripts/contract_consumption_verdicts_test.ts"],
        ["verify" ".frontend.contract_consumption_verdicts.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "自定义筛选/分组、保存筛选和删除动作消费后端声明；收藏权限缺失不被视为授权。",
        "P0",
    ),
    facet(
        "search-group-sort-page-size",
        "search",
        "group_by/default_order/defaults/order/page_size + listProfile grouping",
        ["app/action_runtime/useActionViewContractShapeRuntime.ts", "app/action_runtime/useActionViewFilterComputedRuntime.ts", "app/runtime/actionViewListPageSizeRuntime.ts"],
        ["frontend/apps/web/scripts/action_view_list_page_size_runtime_test.ts"],
        ["verify" ".frontend.action_view_page_size_runtime.unit", "verify" ".frontend.collection_view_semantics.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "分组、排序、默认顺序和页大小有契约消费；可交互换页仍在部分入口存在覆盖缺口。",
        "P0/P4",
    ),
    facet(
        "search-default-sort",
        "search",
        "searchContract.default_sort",
        ["app/action_runtime/useActionViewContractShapeRuntime.ts"],
        ["frontend/apps/web/scripts/action_view_list_page_size_runtime_test.ts"],
        ["verify" ".frontend.action_view_page_size_runtime.unit"],
        "consumption_defect",
        "medium",
        "latent_unless_producer_emits_non_empty_default_sort",
        "运行时代码读取 defaults.order 和 default_order，但未读取 searchContract.default_sort；同一契约存在两个默认顺序键而只消费一个。",
        "P0",
    ),
    facet(
        "search-fields",
        "search",
        "searchContract.fields",
        ["components/scene/SceneBlocksRenderer.vue"],
        ["frontend/apps/web/scripts/native_action_contract_consumption_test.ts"],
        ["verify" ".frontend.native_action_contract_consumption.unit"],
        "consumption_defect",
        "medium",
        "latent_search_usability_gap",
        "字段搜索声明没有进入 ActionView 搜索控件；现有消费仅是场景依赖计数，用户仍只有通用关键字输入。",
        "P0",
    ),
    facet(
        "search-panel",
        "search",
        "searchContract.search_panel",
        [],
        ["addons/smart_core/tests/test_native_view_parser_surfaces.py"],
        [],
        "consumption_defect",
        "high",
        "latent_for_current_formal_entries_active_for_views_that_emit_searchpanel",
        "后端 parser、schema 和契约序列化均声明 search_panel，但 frontend/apps/web/src 无任何运行时消费者；现有 363 字段矩阵将其误记为已交互。正式入口 XML 当前未发现 searchpanel，缺口当前处于潜在状态。",
        "P0",
    ),
    facet(
        "search-native-identity",
        "search",
        "searchContract.nativeIdentity + nativeActionContract.search",
        ["app/contracts/v2/schema.ts", "app/contracts/actionViewSurfaceContract.ts"],
        ["frontend/apps/web/scripts/native_action_contract_consumption_test.ts"],
        ["verify" ".frontend.native_action_contract_consumption.unit"],
        "aligned",
        "medium",
        "validated_identity_only",
        "原生 Search View 身份和 Action 引用一致性在解码阶段校验。",
        "P0",
    ),
    facet(
        "action-identity-method-intent",
        "action",
        "actionRule actionId/backendIdentity/actionKey/intent/button.method",
        ["app/presentation/contractFormPresenter.ts", "app/contractActionRuntime.ts", "pages/contractForm"],
        ["frontend/apps/web/scripts/canonical_form_presenter_test.ts"],
        ["verify" ".frontend.contract_v2_occurrence_authority.unit", "verify" ".frontend.contract_consumption_verdicts.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "动作身份、方法和 intent 有唯一性检查；缺失身份会阻断呈现或执行。",
        "P0",
    ),
    facet(
        "action-target-scope-refresh",
        "action",
        "targetScope/refreshMode/refreshPolicy/targetIds",
        ["app/contractActionRuntime.ts", "app/runtime", "views/ActionView.vue"],
        ["frontend/apps/web/scripts/collection_action_capability_test.ts"],
        ["verify" ".frontend.collection_action_capability.unit", "verify" ".frontend.action_view_page_actions.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "执行范围和刷新策略由声明驱动；集合与详情动作使用各自已声明的能力。",
        "P0",
    ),
    facet(
        "action-confirmation-input",
        "action",
        "actionSafety/submitPolicy/required_params/requires_reason + confirmation dialog",
        ["app/contractActionRuntime.ts", "components/business/IntentConfirmationDialog.vue", "pages/ContractFormPage.vue"],
        ["frontend/apps/web/scripts/canonical_form_presenter_test.ts"],
        ["verify" ".frontend.native_form_action_presentation.unit", "verify" ".frontend.form_header_action_primitives.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "确认、必填参数和原因输入由动作声明触发，免责/取消路径可回到原表单。",
        "P0",
    ),
    facet(
        "action-state-presentation",
        "action",
        "allowed/enabled/disabled/visible + authorizationAllowed/businessAvailable + presentation",
        ["app/presentation/contractFormPresenter.ts", "app/presentation/actionRuleDerivation.ts", "pages/contractForm/ContractFormProductHeader.vue"],
        ["frontend/apps/web/scripts/contract_consumption_verdicts_test.ts", "frontend/apps/web/scripts/contract_v2_occurrence_authority_test.ts"],
        ["verify" ".frontend.contract_consumption_verdicts.unit", "verify" ".frontend.contract_v2_occurrence_authority.unit", "verify" ".frontend.professional_workflow.unit"],
        "aligned",
        "high",
        "verified_for_current_consumers",
        "按钮可见、禁用、主次动作和拒绝原因分离；显式授权/业务状态 false 不会被默认允许覆盖。",
        "P0",
    ),
    facet(
        "global-page-permissions",
        "permission",
        "statusContract.globalStatus pageVisible/pageAuth/effectiveRenderProfile",
        ["app/contracts/v2/store.ts", "pages/ContractFormPage.vue", "app/contracts/actionViewSurfaceContract.ts"],
        ["frontend/apps/web/scripts/contract_consumption_verdicts_test.ts"],
        ["verify" ".frontend.contract_consumption_verdicts.unit", "verify" ".load_view.access.contract.guard"],
        "aligned",
        "high",
        "verified_for_current_consumers",
        "页面读写/只读判断来自 globalStatus，服务端拒绝可形成明确页面门。",
        "P0",
    ),
    facet(
        "node-and-selector-status",
        "permission",
        "widgetStatus/buttonStatus/containerStatus/selectorStatus",
        ["app/contracts/v2/store.ts", "app/presentation/contractFormPresenter.ts", "app/action_runtime"],
        ["frontend/apps/web/scripts/contract_v2_occurrence_authority_test.ts"],
        ["verify" ".frontend.contract_v2_occurrence_authority.unit", "verify" ".frontend.modifiers_runtime.guard"],
        "aligned",
        "high",
        "verified_for_current_consumers",
        "节点和筛选器状态按身份合并，重复/歧义身份不会静默选择任意一条。",
        "P0",
    ),
    facet(
        "record-capabilities-denials",
        "permission",
        "effectiveRecordCapabilities/recordDeniedReasons + deletePolicy",
        ["app/contracts/v2/store.ts", "app/presentation/recordDeleteAction.ts", "pages/ContractFormPage.vue"],
        ["frontend/apps/web/scripts/record_delete_action_test.ts"],
        ["verify" ".frontend.record_delete_action.unit", "verify" ".frontend.collection_action_capability.unit"],
        "aligned",
        "high",
        "verified_for_current_consumers",
        "删除、创建等记录能力与拒绝原因有显式门；能力未声明时默认拒绝。",
        "P0",
    ),
    facet(
        "record-version-conflict",
        "recovery",
        "runtimeContract.recordVersionPolicy + if_match",
        ["pages/ContractFormPage.vue", "pages/contractForm/useRecordFormActions.ts", "pages/contractForm/useRecordPageLifecycle.ts"],
        ["frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts"],
        ["verify" ".frontend.contract_v2_runtime_policy.unit"],
        "aligned",
        "high",
        "verified_for_declared_record_version_entries",
        "声明启用时写入携带 if_match，冲突阻止覆盖并进入恢复路径。",
        "P0",
    ),
    facet(
        "workflow-available-actions",
        "workflow",
        "workflowContract.actions/availableActions enabled/reason_code/blocked_message",
        ["app/contracts/v2/workflowActionAvailability.ts", "app/presentation/contractFormPresenter.ts", "pages/contractForm/workflowContract.ts"],
        ["frontend/apps/web/scripts/canonical_form_presenter_test.ts"],
        ["verify" ".frontend.professional_workflow.unit", "verify" ".frontend.native_form_action_presentation.unit"],
        "aligned",
        "high",
        "verified_for_current_consumers_and_three_entries",
        "业务动作可用性、原因和状态拒绝有行为消费；生命周期、日常合同、付款申请存在真实入口执行证据。",
        "P0/P1",
    ),
    facet(
        "workflow-statusbar",
        "workflow",
        "workflowContract.statusbar current/states/field + native form statusbar",
        ["pages/contractForm/workflowContract.ts", "pages/contractForm/useRecordFormLayout.ts", "pages/contractForm/ContractFormProductHeader.vue"],
        ["frontend/apps/web/scripts/canonical_form_presenter_test.ts"],
        ["verify" ".frontend.professional_workflow.unit"],
        "evidence_gap",
        "medium",
        "valid_input_consumer_present_but_invalid_shape_evidence_missing",
        "合法 statusbar 能显示，但 Contract V2 schema 未约束其结构，非法配置会静默隐藏而不是统一契约缺口停机。",
        "P0",
    ),
    facet(
        "workflow-transitions",
        "workflow",
        "workflowContract.transitions trigger/notes",
        ["pages/contractForm/contractRuntimeVm.ts", "pages/contractForm/ContractFormActionBlocks.vue"],
        ["frontend/apps/web/scripts/canonical_form_presenter_test.ts"],
        ["verify" ".frontend.professional_workflow.unit"],
        "expression_gap",
        "high",
        "transition_matching_requires_product_decision_and_stronger_identity",
        "前端只能按 trigger kind/name/label 匹配动作，transitions 没有稳定的 action/backend identity；同一标签多动作或命名漂移会丢失或误导下一步。",
        "P0/P1",
    ),
    facet(
        "workflow-submission-requirements",
        "workflow",
        "workflowContract.submissionRequirements relation_required/requiredWhen",
        ["pages/contractForm/submissionRequirements.ts", "pages/ContractFormPage.vue"],
        ["frontend/apps/web/scripts/submission_readiness_notice_contract_test.ts"],
        ["verify" ".frontend.submission_readiness_notice_contract.unit"],
        "aligned",
        "high",
        "verified_for_current_consumers",
        "提交前置关系规则按声明在提交时检查，草稿保存不触发；非法规则形成明确提示。",
        "P0",
    ),
    facet(
        "workflow-contract-schema",
        "workflow",
        "workflowContract.availableActions/actions/statusbar/transitions/evidenceGate",
        ["app/contracts/v2/schema.ts", "app/contracts/v2/workflowActionAvailability.ts", "pages/contractForm/workflowContract.ts"],
        ["frontend/apps/web/scripts/canonical_form_presenter_test.ts"],
        ["verify" ".frontend.contract_v2_runtime_policy.unit"],
        "expression_gap",
        "critical",
        "contract_validation_is_incomplete_for_runtime_business_semantics",
        "Root Contract V2 schema only types submissionRequirements and leaves all other workflowContract keys unrestricted; the 363-field authority matrix omits this carrier. Frontend therefore validates a subset ad hoc while transitions/statusbar/evidenceGate can remain malformed.",
        "P0",
    ),
    facet(
        "form-create-edit-readonly-defaults",
        "form",
        "pageInfo/renderProfile/default_get/action defaults + field state",
        ["pages/ContractFormPage.vue", "pages/contractForm/useRecordPageLifecycle.ts", "app/contracts/v2/store.ts"],
        ["frontend/apps/web/scripts/canonical_form_presenter_test.ts", "frontend/apps/web/scripts/readonly_main_data_coverage_test.ts"],
        ["verify" ".frontend.contract_v2_runtime_policy.unit", "verify" ".frontend.record_form_return.unit"],
        "aligned",
        "high",
        "verified_for_current_consumers",
        "创建、编辑、只读和业务默认值保持契约来源；页面未从数组第一项或模型名猜默认。",
        "P0",
    ),
    facet(
        "submission-readiness-notice",
        "feedback",
        "noticeContract.submissionReadiness",
        ["pages/ContractFormPage.vue", "app/contracts/v2/schema.ts"],
        ["frontend/apps/web/scripts/submission_readiness_notice_contract_test.ts"],
        ["verify" ".frontend.submission_readiness_notice_contract.unit"],
        "aligned",
        "high",
        "verified_for_current_consumers",
        "提交准备状态、解释和下一步来自 noticeContract，不使用前端推导的百分比或状态。",
        "P0",
    ),
    facet(
        "errors-focus-draft-recovery",
        "feedback",
        "field/form errors + focus target + local draft/session recovery",
        ["pages/ContractFormPage.vue", "pages/contractForm", "app/errorContext.ts", "app/sessionExpiredRecovery.ts"],
        ["frontend/apps/web/scripts/feedback_evaluation_rt_harness.ts"],
        ["verify" ".frontend.feedback_evaluation.unit", "verify" ".frontend.session_persistence.recovery.unit"],
        "aligned",
        "high",
        "verified_for_current_runtime_helpers_and_two_entries",
        "字段/表单错误、焦点、草稿保留和会话恢复有实现与定向证据；完整入口覆盖不足属于业务验收证据缺口。",
        "P0/P4",
    ),
    facet(
        "collaboration-attachments-history",
        "collaboration",
        "runtimeContract.collaboration + form surfaces + attachment/chatter actions",
        ["pages/contractForm/useRecordCollaborationPresentation.ts", "pages/ContractFormPage.vue"],
        ["artifacts/frontend-web-fix-20260928/evidence.md#WEB-UAT-01A"],
        ["verify" ".frontend.contract_form_collaboration_authority.unit", "verify" ".frontend.professional_collaboration.unit"],
        "aligned",
        "high",
        "verified_for_payment_application_only",
        "协作、附件和审计表面按声明显示；付款申请有上传/刷新/下载页面证据，其他入口尚未形成同类矩阵。",
        "P0/P4",
    ),
    facet(
        "intake-autosave",
        "recovery",
        "runtimeContract.intakeAutosave",
        ["pages/ContractFormPage.vue", "pages/contractForm/useIntakeAutosaveRuntime.ts"],
        ["frontend/apps/web/src/pages/ContractFormPage.vue#intakeAutosaveFields"],
        ["verify" ".frontend.form_structure_contract_projection.unit"],
        "consumption_defect",
        "high",
        "active_capability_is_inert_when_fields_empty",
        "合同新增入口构造 autosave runtime，但 intakeAutosaveFields 固定为空数组，且没有读取 runtimeContract.intakeAutosave；当前本地自动草稿不会持久化任何字段。",
        "P0",
    ),
    facet(
        "native-action-view-set",
        "view",
        "nativeActionContract.viewSet + orderedViews selectable/projectionStatus/rendererStatus",
        ["app/contracts/actionViewSurfaceContract.ts", "app/action_runtime/useActionViewModeRuntime.ts", "views/ActionView.vue"],
        ["frontend/apps/web/scripts/native_action_contract_consumption_test.ts"],
        ["verify" ".frontend.native_action_contract_consumption.unit", "verify" ".frontend.action_view_surface_gate_runtime.unit"],
        "aligned",
        "high",
        "verified_for_current_contract_consumers",
        "Action View 顺序、默认视图、可选视图和渲染状态由原生动作契约驱动。",
        "P0",
    ),
    facet(
        "renderer-registry-fallbacks",
        "view",
        "rendererStatus + Action Surface Renderer Registry fallback status/reasonCode",
        ["app/renderers/actionSurfaceRendererRegistry.ts", "components/action/ActionSurfaceRendererHost.vue"],
        ["frontend/apps/web/scripts/collection_view_semantics_test.ts"],
        ["verify" ".frontend.action_surface_renderer_registry.unit", "verify" ".frontend.collection_view_semantics.unit"],
        "terminal_capability_gap",
        "medium",
        "calendar_gantt_dashboard_readable_fallback",
        "calendar、gantt、dashboard 登记为 readable fallback；用户能读取数据但缺少原生时间轴/日历/仪表板交互语义，不能视为同等办理能力。",
        "P0/P1",
    ),
    facet(
        "native-action-readiness",
        "view",
        "nativeActionContract.projectionAvailability/readiness three axes",
        ["app/contracts/v2/schema.ts"],
        ["frontend/apps/web/scripts/native_action_contract_consumption_test.ts"],
        ["verify" ".frontend.native_action_contract_consumption.unit"],
        "consumption_defect",
        "high",
        "runtime_gate_not_applied",
        "三轴 readiness 被严格解码，但 ActionView 运行时不读取它；blocked/unresolved 的业务执行准备状态不会形成页面门。",
        "P0",
    ),
    facet(
        "delivery-profile-trim",
        "runtime",
        "pageInfo/runtimeContract/meta deliveryProfile + deliveryTrim",
        ["app/contracts/v2/schema.ts", "app/contracts/v2/store.ts"],
        ["frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts"],
        ["verify" ".frontend.contract_v2_runtime_policy.unit"],
        "aligned",
        "medium",
        "validated_identity_only",
        "三处交付身份一致性及裁剪计数在解码阶段校验。",
        "P0",
    ),
    facet(
        "runtime-cache-policy",
        "runtime",
        "runtimeContract.cachePolicy + etag",
        ["app/contracts/v2/runtime.ts", "app/contracts/v2/client.ts", "app/action_runtime/useActionViewLoadPreflightRuntime.ts"],
        ["frontend/apps/web/scripts/action_view_page_size_runtime_test.ts"],
        ["verify" ".frontend.action_view_page_size_runtime.unit", "verify" ".frontend.ui.typecheck.strict"],
        "aligned",
        "high",
        "verified_for_create_contract_cache",
        "snapshot/etag/none 缓存策略已实际控制合同快照复用与条件请求。",
        "P0",
    ),
    facet(
        "runtime-control-plane",
        "runtime",
        "patchStrategy/optimistic/lazyContainer/virtualization/retryPolicy/renderStrategy/hydration/patchOperations/tracePolicy/complexityBudget",
        ["app/contracts/v2/schema.ts", "app/contracts/v2/store.ts"],
        ["frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts"],
        ["verify" ".frontend.contract_v2_runtime_policy.unit"],
        "consumption_defect",
        "high",
        "latent_non_default_policy_has_no_effect",
        "这些控制面字段被解码/透传，但除 cachePolicy 外没有对应运行时执行点；非默认 patch、lazy、virtualization、retry、hydration 声明不会改变行为。",
        "P0",
    ),
    facet(
        "runtime-validation-rules",
        "runtime",
        "runtimeContract.validationRules",
        ["app/contracts/v2/schema.ts", "app/contracts/v2/store.ts"],
        ["frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts"],
        ["verify" ".frontend.contract_v2_runtime_policy.unit"],
        "consumption_defect",
        "high",
        "backend_enforcement_only_until_consumer_exists",
        "validationRules 只被解码和透传，frontend/apps/web/src 无业务表单消费点；前端不能展示声明规则对应的即时反馈。",
        "P0",
    ),
    facet(
        "runtime-field-semantics",
        "runtime",
        "runtimeContract.fieldSemantics",
        ["app/contracts/v2/schema.ts", "app/contracts/v2/store.ts"],
        ["frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts"],
        ["verify" ".frontend.contract_v2_runtime_policy.unit"],
        "consumption_defect",
        "medium",
        "latent_if_runtime_field_semantics_is_authoritative",
        "运行时 fieldSemantics 无业务消费者；字段呈现主要依赖其他 field descriptor/semantic 来源，存在同一语义两套载体的风险。",
        "P0",
    ),
    facet(
        "runtime-business-workspace-actions",
        "runtime",
        "runtimeContract.businessWorkspace/businessActions",
        ["app/contracts/v2/store.ts"],
        ["frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts"],
        ["verify" ".frontend.contract_v2_runtime_policy.unit"],
        "consumption_defect",
        "medium",
        "latent_until_producer_emits_non_empty_carrier",
        "两个 resolver 存在但没有调用方；若后端发出这些声明，前端不会据此呈现工作区或业务动作。",
        "P0",
    ),
    facet(
        "runtime-ai-envelope",
        "runtime",
        "runtimeContract.aiEnvelope suggestion-only/non-executable",
        ["app/contracts/v2/schema.ts"],
        ["frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts"],
        ["verify" ".frontend.contract_v2_runtime_policy.unit"],
        "aligned",
        "medium",
        "validated_authority_boundary_only",
        "解码器拒绝 executable=true，AI 不会被当前契约提升为业务执行者。",
        "P0",
    ),
    facet(
        "field-ownership-page-composition",
        "identity",
        "root fieldOwnership + pageComposition class/diagnostics/permissionSemanticsPreserved",
        ["app/contracts/v2/schema.ts", "pages/contractForm/useRecordFormFieldSchemas.ts"],
        ["frontend/apps/web/scripts/native_form_structure_responsibility_test.ts"],
        ["verify" ".frontend.native_form_structure_responsibility.unit"],
        "evidence_gap",
        "medium",
        "identity_and_layout_class_consumed_provenance_effect_unclear",
        "字段归属经过 schema 校验，page class 参与表单字段 schema；但 pageComposition diagnostics/permissionSemanticsPreserved 的运行时行为没有独立断言。",
        "P0",
    ),
]


def load_business_rows() -> list[dict[str, str]]:
    with BUSINESS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "menu_xmlid",
        "label",
        "domain",
        "model",
        "action_xmlid",
        "acceptance_status",
        "evidence",
        "gap",
    }
    if not required.issubset(rows[0] if rows else {}):
        raise SystemExit(f"business CSV is missing columns: {sorted(required - set(rows[0] if rows else {}))}")
    keys = [row["menu_xmlid"] for row in rows]
    if len(keys) != len(set(keys)):
        raise SystemExit("business CSV contains duplicate menu_xmlid values")
    return rows


def evidence_identities(text: str) -> list[str]:
    identities = {match.group(1).lower() for match in SERVED_RE.finditer(text)}
    identities.update(match.group(1).lower() for match in CANDIDATE_RE.finditer(text))
    if not identities:
        identities.update(
            match.group(0).lower()
            for match in HEX_RE.finditer(text)
            if not re.fullmatch(r"20\d{6}", match.group(0))
        )
    return sorted(identities)


def classify_entry(row: dict[str, str]) -> dict[str, Any]:
    menu = row["menu_xmlid"]
    text = f"{row.get('evidence', '')} {row.get('gap', '')}"
    status = row["acceptance_status"]
    identities = evidence_identities(text)
    current_bound = BASELINE_SHA in identities
    empty_only = bool(EMPTY_EVIDENCE_RE.search(text))
    detail = bool(DETAIL_EVIDENCE_RE.search(text))
    negative = bool(NEGATIVE_AUTH_RE.search(text))
    orm_smoke = menu in CORE_ORM_SMOKE
    workflow = menu in WORKFLOW_EXECUTED
    attachment = menu in ATTACHMENT_EXECUTED
    pagination = menu in INTERACTIVE_PAGINATION
    mobile = menu in MOBILE_EXECUTED

    if status != "passed":
        closure = "pending"
        boundary = "正式入口验收未完成；当前证据不能证明完整业务办理。"
    elif menu in FULL_DECLARED_SCOPE:
        closure = "full_declared_scope"
        boundary = FULL_DECLARED_SCOPE[menu]
    elif menu in CREATE_WRITE_SCOPE:
        closure = "write_create_partial"
        boundary = CREATE_WRITE_SCOPE[menu]
    elif empty_only:
        closure = "declared_empty_read_only"
        boundary = "合法空态和列表读取有证据；没有详情、保存、动作或状态回读闭环。"
    elif detail:
        closure = "read_detail_only"
        boundary = "列表和详情读取有证据；没有页面写入、业务动作或审批闭环。"
    else:
        closure = "surface_only"
        boundary = "仅有入口/呈现/授权表面证据；未取得详情或办理动作闭环。"

    return {
        "menu_xmlid": menu,
        "label": row["label"],
        "domain": row["domain"],
        "model": row["model"],
        "action_xmlid": row["action_xmlid"],
        "source_acceptance_status": status,
        "closure_level": closure,
        "closure_boundary": boundary,
        "entry_presentation_evidence": status == "passed",
        "query_surface_evidence": status == "passed",
        "declared_empty_state": empty_only,
        "detail_readback_verified": detail or menu in FULL_DECLARED_SCOPE or menu in CREATE_WRITE_SCOPE,
        "browser_write_verified": menu in FULL_DECLARED_SCOPE or menu in CREATE_WRITE_SCOPE,
        "browser_workflow_verified": workflow,
        "attachment_chain_verified": attachment,
        "interactive_pagination_verified": pagination,
        "mobile_journey_verified": mobile,
        "negative_authority_verified": negative,
        "backend_orm_create_write_smoke": orm_smoke,
        "current_baseline_rebound": current_bound,
        "evidence_source_identities": "|".join(identities),
        "source_acceptance_evidence": row.get("evidence", ""),
        "source_gap_note": row.get("gap", ""),
    }


def workflow_schema_audit(schema: dict[str, Any]) -> dict[str, Any]:
    definition = schema["properties"]["workflowContract"]
    typed = sorted((definition.get("properties") or {}).keys())
    consumed = [
        "availableActions",
        "actions",
        "statusbar",
        "transitions",
        "evidenceGate",
        "record_id",
        "model",
        "availabilityScope",
        "submissionRequirements",
    ]
    return {
        "additionalProperties": definition.get("additionalProperties", True),
        "typedProperties": typed,
        "runtimePropertiesObserved": consumed,
        "runtimePropertiesWithoutTypedShape": sorted(set(consumed) - set(typed)),
    }


def registered_make_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in [ROOT / "Makefile", *sorted((ROOT / "make").glob("*.mk"))]
    )


def build_report() -> dict[str, Any]:
    schema = json.loads(CONTRACT_SCHEMA.read_text(encoding="utf-8"))
    ux_coverage = json.loads(UX_COVERAGE_JSON.read_text(encoding="utf-8"))
    rows = [classify_entry(row) for row in load_business_rows()]
    make_text = registered_make_text()
    capability_matrix_text = CAPABILITY_MATRIX_MD.read_text(encoding="utf-8")
    capability_rows = re.findall(r"`list=\d+ form=\d+ search=0`", capability_matrix_text)
    missing_targets = sorted({
        target
        for item in FACETS
        for target in item["registeredTargets"]
        if target not in make_text
    })
    verdicts = Counter(item["verdict"] for item in FACETS)
    closure = Counter(row["closure_level"] for row in rows)
    statuses = Counter(row["source_acceptance_status"] for row in rows)
    entry_ids = {row["menu_xmlid"] for row in rows}
    matched_core_smoke = sorted(CORE_ORM_SMOKE & entry_ids)
    unmatched_core_smoke = sorted(CORE_ORM_SMOKE - entry_ids)
    if missing_targets:
        raise SystemExit(f"facet matrix cites undefined Make targets: {missing_targets}")
    return {
        "schemaVersion": "frontend-contract-business-journey-research/v1",
        "baselineSha": BASELINE_SHA,
        "method": {
            "evidenceRule": "declaration -> frontend consumer -> behavior evidence",
            "businessJoinKey": "menu_xmlid",
            "minimumEvidenceBoundary": "reachability, valid empty state, ORM smoke and full browser handling are distinct",
            "currentBaselineRule": "historical evidence is not rebound to the research baseline unless its source identity records this SHA",
        },
        "summary": {
            "formalEntryCount": len(rows),
            "sourceStatusCounts": dict(sorted(statuses.items())),
            "closureLevelCounts": dict(sorted(closure.items())),
            "coreOrmSmokeDeclaredCount": len(CORE_ORM_SMOKE),
            "coreOrmSmokeMatchedEntryCount": len(matched_core_smoke),
            "coreOrmSmokeUnmatchedEntryCount": len(unmatched_core_smoke),
            "browserWriteCount": sum(row["browser_write_verified"] for row in rows),
            "browserWorkflowCount": sum(row["browser_workflow_verified"] for row in rows),
            "attachmentChainCount": sum(row["attachment_chain_verified"] for row in rows),
            "currentBaselineReboundCount": sum(row["current_baseline_rebound"] for row in rows),
            "contractFacetCount": len(FACETS),
            "contractVerdictCounts": dict(sorted(verdicts.items())),
            "defectFacetCount": sum(
                item["verdict"] in {
                    "projection_gap",
                    "expression_gap",
                    "consumption_defect",
                    "rule_conflict",
                    "terminal_capability_gap",
                }
                for item in FACETS
            ),
        },
        "workflowContractSchema": workflow_schema_audit(schema),
        "userExperienceCoverage": {
            "journeyCount": len(ux_coverage.get("journeys", [])),
            "browserEvidenceJourneyCount": sum(
                item.get("browser_evidence") is True for item in ux_coverage.get("journeys", [])
            ),
            "withoutBrowserEvidenceJourneyIds": sorted(
                item["id"]
                for item in ux_coverage.get("journeys", [])
                if item.get("browser_evidence") is not True
            ),
            "roleJourneyAuditRegisteredInMake": "frontend_role_journey_audit.mjs" in make_text,
            "roleJourneyAuditReusesFirstRoute": True,
            "roleJourneyAuditSource": "frontend/apps/web/scripts/frontend_role_journey_audit.mjs",
        },
        "capabilityMatrixMeasurement": {
            "renderedRowsWithSearchZero": len(capability_rows),
            "searchCountAuthorityRead": "layoutContract.searchProfile",
            "contractV2DeliveryCarrier": "root searchContract",
            "verdict": "validation_tool_defect",
            "boundary": "search=0 cannot be used as evidence that formal entries lack search",
        },
        "coreOrmSmokeJoin": {
            "declaredMenuXmlids": sorted(CORE_ORM_SMOKE),
            "matchedFormalEntryMenuXmlids": matched_core_smoke,
            "unmatchedFormalEntryMenuXmlids": unmatched_core_smoke,
            "method": "exact menu_xmlid intersection; no label fallback",
        },
        "contractFacets": FACETS,
        "businessEntries": rows,
        "findings": [
            {
                "id": "R1",
                "kind": "consumption_defect",
                "owner": "P0",
                "summary": "searchContract.search_panel has serialization/schema but no frontend consumer.",
            },
            {
                "id": "R2",
                "kind": "expression_gap",
                "owner": "P0",
                "summary": "workflowContract lacks a closed schema for availableActions/actions/statusbar/transitions/evidenceGate.",
            },
            {
                "id": "R3",
                "kind": "consumption_defect",
                "owner": "P0",
                "summary": "intake autosave runtime is wired with an empty field set and does not consume runtimeContract.intakeAutosave.",
            },
            {
                "id": "R4",
                "kind": "consumption_defect",
                "owner": "P0",
                "summary": "nativeActionContract readiness and non-cache runtime control-plane declarations are not runtime gates/behaviors.",
            },
            {
                "id": "R5",
                "kind": "terminal_capability_gap",
                "owner": "P0/P1",
                "summary": "calendar, gantt and dashboard use readable-record fallbacks rather than equivalent interactive surfaces.",
            },
            {
                "id": "R6",
                "kind": "evidence_gap",
                "owner": "P4",
                "summary": "64 formal entries currently have only declared-empty read evidence; 16 have read/detail only and 3 have surface-only evidence.",
            },
            {
                "id": "R7",
                "kind": "evidence_gap",
                "owner": "P4",
                "summary": "No business-entry evidence records the research baseline SHA as its served/source identity.",
            },
            {
                "id": "R8",
                "kind": "evidence_gap",
                "owner": "P4",
                "summary": "The 12-entry core ORM smoke and the 91-entry product CSV share only 4 exact menu XMLIDs; its other 8 results cannot be rebound by label or model inference.",
            },
            {
                "id": "R9",
                "kind": "evidence_gap",
                "owner": "P4",
                "summary": "The formal operation capability matrix prints search=0 for all 81 rows because it reads the obsolete layout searchProfile location instead of root searchContract.",
            },
            {
                "id": "R10",
                "kind": "evidence_gap",
                "owner": "P4",
                "summary": "Four of twelve declared UX journeys lack browser evidence, and the role journey audit script maps multiple journey IDs to the same first route instead of executing distinct tasks.",
            },
        ],
    }


def render_csv(rows: list[dict[str, Any]]) -> str:
    fields = [
        "menu_xmlid",
        "label",
        "domain",
        "model",
        "action_xmlid",
        "source_acceptance_status",
        "closure_level",
        "closure_boundary",
        "entry_presentation_evidence",
        "query_surface_evidence",
        "declared_empty_state",
        "detail_readback_verified",
        "browser_write_verified",
        "browser_workflow_verified",
        "attachment_chain_verified",
        "interactive_pagination_verified",
        "mobile_journey_verified",
        "negative_authority_verified",
        "backend_orm_create_write_smoke",
        "current_baseline_rebound",
        "evidence_source_identities",
        "closure_evidence",
        "source_acceptance_evidence",
        "source_gap_note",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        rendered = dict(row)
        rendered["closure_evidence"] = row["closure_boundary"]
        writer.writerow({key: rendered.get(key, "") for key in fields})
    return buffer.getvalue()


def render_outputs() -> tuple[str, str, dict[str, Any]]:
    report = build_report()
    return (
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        render_csv(report["businessEntries"]),
        report,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload, business_csv, report = render_outputs()
    if args.check:
        stale = [
            str(path.relative_to(ROOT))
            for path, expected in ((OUTPUT_JSON, payload), (OUTPUT_CSV, business_csv))
            if not path.exists() or path.read_text(encoding="utf-8") != expected
        ]
        if stale:
            raise SystemExit(f"stale research matrices: {stale}; run {Path(__file__).relative_to(ROOT)}")
    else:
        OUTPUT_JSON.write_text(payload, encoding="utf-8")
        OUTPUT_CSV.write_text(business_csv, encoding="utf-8")
    summary = report["summary"]
    print(
        "[frontend_contract_business_journey_research] PASS "
        f"facets={summary['contractFacetCount']} "
        f"entries={summary['formalEntryCount']} "
        f"current_rebound={summary['currentBaselineReboundCount']}"
    )


if __name__ == "__main__":
    main()

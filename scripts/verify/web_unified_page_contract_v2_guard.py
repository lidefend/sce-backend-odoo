#!/usr/bin/env python3
"""Guard web contract API migration to Unified Page Contract v2."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB_CONTRACT_API = ROOT / "frontend/apps/web/src/api/contract.ts"
WEB_CONTRACT_CLIENT = ROOT / "frontend/apps/web/src/app/contracts/v2/client.ts"
WEB_CONTRACT_V2 = ROOT / "frontend/apps/web/src/app/contracts/unifiedPageContractV2.ts"
WEB_ACTION_SHAPE = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts"
WEB_FILTER_COMPUTED = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewFilterComputedRuntime.ts"
WEB_ACTION_PRESENTATION = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewActionPresentationRuntime.ts"
WEB_ACTION_RUNTIME = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewActionRuntime.ts"
WEB_ACTION_NAV = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewNavigationRuntime.ts"
WEB_ACTION_PREFLIGHT = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewLoadPreflightRuntime.ts"
WEB_ACTION_LOAD_REQUEST = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewLoadRequestRuntime.ts"
WEB_ACTION_META = ROOT / "frontend/apps/web/src/app/runtime/actionViewMetaRuntime.ts"
WEB_ACTION_CONTRACT_RUNTIME = ROOT / "frontend/apps/web/src/app/contractActionRuntime.ts"
WEB_SURFACE_CONTRACT = ROOT / "frontend/apps/web/src/app/contracts/actionViewSurfaceContract.ts"
WEB_ACTION_VIEW = ROOT / "frontend/apps/web/src/views/ActionView.vue"
WEB_NATIVE_LAYOUT = ROOT / "frontend/apps/web/src/pages/contractForm/nativeLayoutUtils.ts"
RETIRED_COMPAT_PROJECTION = ROOT / "frontend/apps/web/src/app/runtime/unifiedPageContractV2CompatProjection.ts"
RETIRED_CONTRACT_POLICIES = ROOT / "frontend/apps/web/src/app/contractPolicies.ts"


def main() -> int:
    source = WEB_CONTRACT_API.read_text(encoding="utf-8") if WEB_CONTRACT_API.exists() else ""
    client_source = WEB_CONTRACT_CLIENT.read_text(encoding="utf-8") if WEB_CONTRACT_CLIENT.exists() else ""
    errors: list[str] = []
    if not source:
        errors.append("frontend web contract API is missing")
    if RETIRED_COMPAT_PROJECTION.exists():
        errors.append("retired Unified Page Contract V2 compatibility projection must not exist")
    if RETIRED_CONTRACT_POLICIES.exists():
        errors.append("retired ActionContract policy evaluator must not exist")
    for retired in ("adaptUnifiedPageContractV2Raw", "loadActionContractRaw", "loadModelContractRaw"):
        if retired in source:
            errors.append(f"web contract API still exposes retired projection token: {retired}")
    v2_source = WEB_CONTRACT_V2.read_text(encoding="utf-8") if WEB_CONTRACT_V2.exists() else ""
    shape_source = WEB_ACTION_SHAPE.read_text(encoding="utf-8") if WEB_ACTION_SHAPE.exists() else ""
    filter_source = WEB_FILTER_COMPUTED.read_text(encoding="utf-8") if WEB_FILTER_COMPUTED.exists() else ""
    action_presentation_source = WEB_ACTION_PRESENTATION.read_text(encoding="utf-8") if WEB_ACTION_PRESENTATION.exists() else ""
    action_runtime_source = WEB_ACTION_RUNTIME.read_text(encoding="utf-8") if WEB_ACTION_RUNTIME.exists() else ""
    nav_source = WEB_ACTION_NAV.read_text(encoding="utf-8") if WEB_ACTION_NAV.exists() else ""
    preflight_source = WEB_ACTION_PREFLIGHT.read_text(encoding="utf-8") if WEB_ACTION_PREFLIGHT.exists() else ""
    load_request_source = WEB_ACTION_LOAD_REQUEST.read_text(encoding="utf-8") if WEB_ACTION_LOAD_REQUEST.exists() else ""
    meta_source = WEB_ACTION_META.read_text(encoding="utf-8") if WEB_ACTION_META.exists() else ""
    contract_runtime_source = WEB_ACTION_CONTRACT_RUNTIME.read_text(encoding="utf-8") if WEB_ACTION_CONTRACT_RUNTIME.exists() else ""
    surface_source = WEB_SURFACE_CONTRACT.read_text(encoding="utf-8") if WEB_SURFACE_CONTRACT.exists() else ""
    action_view_source = WEB_ACTION_VIEW.read_text(encoding="utf-8") if WEB_ACTION_VIEW.exists() else ""
    native_layout_source = WEB_NATIVE_LAYOUT.read_text(encoding="utf-8") if WEB_NATIVE_LAYOUT.exists() else ""
    field_schema_source = (ROOT / "frontend/apps/web/src/pages/contractForm/useRecordFormFieldSchemas.ts").read_text(encoding="utf-8")
    form_layout_source = (ROOT / "frontend/apps/web/src/pages/contractForm/useRecordFormLayout.ts").read_text(encoding="utf-8")
    form_page_source = (ROOT / "frontend/apps/web/src/pages/ContractFormPage.vue").read_text(encoding="utf-8")
    if "intent: 'ui.contract.v2'" not in client_source and 'intent: "ui.contract.v2"' not in client_source:
        errors.append("strict web contract client must request ui.contract.v2")
    if "intent: 'ui.contract'," in source or 'intent: "ui.contract",' in source:
        errors.append("web contract API must not request legacy ui.contract directly")
    for token in (
        "loadActionContractV2",
        "loadModelContractV2",
        "loadActionUnifiedPageContractV2",
        "loadModelUnifiedPageContractV2",
    ):
        if token not in source:
            errors.append(f"web contract API missing governed v2 token: {token}")
    if "__unified_page_contract_v2" in source:
        errors.append("web contract API must not extract the retired embedded V2 envelope")
    for token in (
        "UnifiedPageContractV2",
        "resolveUnifiedPageContractV2",
        "collectUnifiedPageContractV2FieldWidgets",
        "collectUnifiedPageContractV2FieldStatus",
        "collectUnifiedPageContractV2WidgetStatus",
        "collectUnifiedPageContractV2ButtonStatus",
        "collectUnifiedPageContractV2SelectorStatus",
        "resolveUnifiedPageContractV2SelectorStatus",
        "resolveUnifiedPageContractV2GlobalStatus",
        "collectUnifiedPageContractV2ContainerStatus",
        "collectUnifiedPageContractV2FieldContainerStatus",
        "layoutContract",
        "dataContract",
        "resolveUnifiedPageContractV2PrimaryDataSource",
    ):
        if token not in v2_source:
            errors.append(f"web v2 contract runtime missing token: {token}")
    if "resolveContractV2FieldWidgets" not in shape_source:
        errors.append("web action view shape runtime must consume canonical field widgets")
    if "resolveContractV2ActionRules" not in nav_source or "row_click" not in nav_source:
        errors.append("web row navigation runtime must derive default row open behavior from v2 list contracts")
    if "resolveContractV2PrimaryDataSource" not in preflight_source:
        errors.append("web load preflight runtime must consume v2 primary dataSource")
    if "resolveContractV2PrimaryDataSource" not in load_request_source or "domain_raw" not in load_request_source or "context_raw" not in load_request_source:
        errors.append("web load request runtime must merge v2 primary dataSource domain/context into api.data payload")
    if "snapshot.pageInfo.viewType" not in contract_runtime_source:
        errors.append("web view mode runtime must resolve view type from canonical pageInfo")
    if "resolveContractV2GlobalStatus" not in contract_runtime_source or "UNIFIED_PAGE_CONTRACT_V2_PAGE_FORBIDDEN" not in contract_runtime_source:
        errors.append("web contract action runtime must honor v2 globalStatus for page access/read guards")
    if "collectContractV2FieldStatusByCode" not in shape_source:
        errors.append("web list shape runtime must honor v2 widget status for default column visibility")
    if "resolveContractV2SelectorStatus" not in filter_source or "isSelectorEnabled" not in filter_source:
        errors.append("web filter runtime must honor v2 selectorStatus for search/filter/group controls")
    if "snapshot.pageInfo.model" not in shape_source:
        errors.append("web model resolver must read canonical pageInfo.model")
    if "contract?.snapshot.pageInfo.viewType" not in surface_source or "resolveContractV2ListProfile" not in surface_source:
        errors.append("web action surface contract must consume canonical pageInfo/listProfile")
    if "collectContractV2FieldStatusByCode" not in form_layout_source:
        errors.append("web contract form layout must consume canonical widget status")
    if "resolveContractV2GlobalStatus" not in form_page_source or "pageAuth === 'none'" not in form_page_source:
        errors.append("web contract form page must consume canonical globalStatus for form rights")
    if (
        "collectContractV2FieldContainerStatusByCode" not in field_schema_source
        or "containerStatus:collectContractV2FieldContainerStatusByCode(context.v2ContractStore.value)" not in field_schema_source
        or "containerStatus?.visible === false" not in native_layout_source
    ):
        errors.append("web contract form page must merge v2 containerStatus into layout field visibility/read state")
    if "collectContractV2ButtonStatusById" not in form_page_source:
        errors.append("web contract form page must consume canonical buttonStatus")
    if "collectContractV2ButtonStatusById" not in action_view_source or "applyActionViewV2ButtonStatus" not in action_view_source:
        errors.append("web action view toolbar actions must merge v2 buttonStatus into contract actions")
    if "normalizeV2ActionRows" not in action_presentation_source or "resolveContractV2ActionRules" not in action_presentation_source:
        errors.append("web action presentation runtime must consume canonical actionRuleList")
    if "resolveV2RefreshPolicy" not in action_presentation_source or "action.refreshMode" not in action_presentation_source:
        errors.append("web action presentation runtime must map v2 refreshMode into refreshPolicy")
    if "applyActionRefreshPolicy(action.refreshPolicy)" not in action_runtime_source:
        errors.append("web action runtime must apply action refreshPolicy after successful button execution")

    strict_action_sources = {
        "contractActionRuntime": contract_runtime_source,
        "actionShape": shape_source,
        "actionPresentation": action_presentation_source,
        "actionNavigation": nav_source,
        "actionPreflight": preflight_source,
        "actionLoadRequest": load_request_source,
    }
    for label, strict_source in strict_action_sources.items():
        for forbidden in (
            "ActionContract",
            "resolveUnifiedPageContractV2",
            ".head",
            ".views",
            ".buttons",
            ".toolbar",
            "action_groups",
            "access_policy",
            "typedContract.fields",
        ):
            if forbidden in strict_source:
                errors.append(f"{label} still contains retired Action fallback token: {forbidden}")

    for forbidden in (
        "input.contract",
        "contractRecord.buttons",
        "contractRecord.toolbar",
        "contractRecord.views",
    ):
        if forbidden in native_layout_source:
            errors.append(f"native form layout still contains retired contract fallback token: {forbidden}")

    if errors:
        print("web unified page contract v2 guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("web unified page contract v2 guard passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

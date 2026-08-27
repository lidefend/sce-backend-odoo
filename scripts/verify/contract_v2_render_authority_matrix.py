#!/usr/bin/env python3
"""Generate the strict Contract V2 render-authority classification matrix."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
OUTPUT = ROOT / "docs/frontend_productization/rendering-detail/contract-v2-render-authority-matrix-v1.json"

EXPECTED = {
    "sourceContext": "context domain contextRaw domainRaw renderProfile order limit",
    "searchContract": "default_sort default_order mode filters saved_filters group_by fields search_panel favorites custom ui_labels defaults",
    "pageInfo": "pageId sceneKey pageName model viewType layoutType renderMode contractVersion clientType deliveryProfile",
    "layoutContract": "pageId layoutType adaptMode containerTree layoutHints componentRegistry listProfile activityProfile",
    "activityProfile": (
        "activityTypeSlots deadlineSlots assigneeSlots fieldOccurrences nativeAttrs nodeOccurrences template "
        "templateQwebPresent actions actionCount sourceAuthority"
    ),
    "activitySourceAuthority": "kind authorities projection_only no_business_fact_authority runtime_carrier",
    "activityFieldOccurrence": (
        "name label widget native_locator occurrence_index source_position attributes text tail modifiers decorations "
        "field_type currency_field digits"
    ),
    "activityNodeOccurrence": "tag native_locator occurrence_index source_position attributes text tail",
    "activityNode": "tag native_locator occurrence_index source_position attributes text tail children",
    "activityTemplate": "native_locator occurrence_index nodes names",
    "container": "containerId containerType title span styleToken type name label string children widgetList",
    "nativeLayoutNode": (
        "type name string label title text displayLabel semanticTitle semanticAnchor containerId containerType span "
        "styleToken widgetId fieldCode nativeLocator occurrenceIndex sourcePosition widget componentKey componentConfig "
        "fieldInfo filename nolabel attributes modifiers action badge buttonType readonly required invisible "
        "column_invisible domain context options visible cols columns col class className fieldSize size formStructure "
        "formStructureRole sourceAuthority children widgetList fields"
    ),
    "widget": (
        "widgetId widgetType fieldCode label span componentKey capabilities componentConfig ownerContainerId "
        "nativeLocator occurrenceIndex sourcePosition fieldDescriptor formStructureRole"
    ),
    "componentRegistryEntry": "version adapter fallback selectedAdapter",
    "statusContract": "globalStatus containerStatus widgetStatus buttonStatus selectorStatus",
    "containerStatus": "containerId visible disabled reasonCode",
    "widgetStatus": "widgetId visible readonly required disabled placeholder auth reasonCode",
    "buttonStatus": "btnId visible disabled reasonCode backendIdentity",
    "selectorStatus": "selector visible readonly required disabled reasonCode",
    "actionContract": "actionRuleList dependencyGraph deletePolicy surfacePolicies identityPolicy primaryResolution",
    "actionRule": (
        "actionId triggerType sourceWidgetId targetIds dispatchMode targetScope refreshMode refreshPolicy actionKey label "
        "intent target button visible modifiers invisible visibleProfiles presentation actionSafety submitPolicy tracePolicy "
        "backendIdentity nativeIdentity sourceTrace presentationAuthority presentationPriority sourceActionKey sourceChannel "
        "permissionConstraints entitlementEvaluated allowed enabled disabled reasonCode"
    ),
    "dataContract": "mainData tableRows relationRows treeData ganttData dictData pagination dataSource dataMeta",
    "dataMeta": "businessOperationProfile visibleFields fieldGroups sourceContext",
    "visibleFields": "fields sourceAuthority",
    "fieldGroups": "groups sourceAuthority",
    "sourceAuthority": "kind runtime_carrier projection_only no_business_fact_authority source_key formal_projection",
    "contractLifecycle": "lifecycleVersion stage definition generation runtime integrity authority",
    "contractLifecycleDefinition": "schemaId schemaVersion schemaSha256 contractVersion normativeStatus",
    "contractLifecycleGeneration": "generator generatorVersion sourceType sourceSha256",
    "contractLifecycleRuntime": "requestId traceId clientType traceSource",
    "contractLifecycleIntegrity": "algorithm contractSha256",
    "runtimeContract": (
        "patchStrategy cachePolicy optimistic lazyContainer virtualization retryPolicy renderStrategy hydration patchOperations "
        "tracePolicy complexityBudget aiEnvelope interactionMode actionTarget collaboration businessWorkspace businessActions deliveryProfile "
        "intakeAutosave fieldSemantics validationRules governance recordVersionPolicy"
    ),
    "meta": "etag snapshotId traceId requestId sourceType lifecycle deliveryTrim",
    "deliveryTrim": "clientType deliveryProfile compact limits original delivered omitted",
    "deliveryCountRecord": "containers widgets actions",
    "deliveryLimitRecord": "containers widgets actions",
}

NON_VISUAL = {
    "pageInfo.pageId": "stable page identity",
    "pageInfo.sceneKey": "stable scene identity",
    "pageInfo.contractVersion": "decoder negotiation boundary",
    "layoutContract.pageId": "page identity invariant",
    "layoutContract.layoutType": "renderer selection invariant",
    "nativeLayoutNode.sourceAuthority": "projection provenance boundary",
    "widget.ownerContainerId": "layout membership identity",
    "widget.nativeLocator": "native occurrence identity",
    "widget.occurrenceIndex": "native occurrence identity",
    "widget.sourcePosition": "native source ordering identity",
    "containerStatus.containerId": "status binding identity",
    "widgetStatus.widgetId": "status binding identity",
    "buttonStatus.btnId": "status binding identity",
    "buttonStatus.backendIdentity": "action/status binding identity",
    "selectorStatus.selector": "selector binding identity",
    "actionContract.dependencyGraph": "action orchestration graph",
    "actionContract.deletePolicy": "mutation policy",
    "actionContract.surfacePolicies": "surface settlement policy",
    "actionContract.identityPolicy": "action identity policy",
    "actionRule.actionId": "action identity",
    "actionRule.triggerType": "dispatch semantics",
    "actionRule.sourceWidgetId": "dispatch source identity",
    "actionRule.targetIds": "dispatch target identity",
    "actionRule.dispatchMode": "dispatch semantics",
    "actionRule.targetScope": "dispatch scope",
    "actionRule.refreshMode": "post-action refresh semantics",
    "actionRule.refreshPolicy": "post-action refresh policy",
    "actionRule.intent": "backend action intent",
    "actionRule.target": "backend action target",
    "actionRule.button": "native execution payload",
    "actionRule.actionSafety": "mutation safety policy",
    "actionRule.submitPolicy": "submit settlement policy",
    "actionRule.tracePolicy": "trace policy",
    "actionRule.backendIdentity": "backend action identity",
    "actionRule.nativeIdentity": "native occurrence identity",
    "actionRule.sourceTrace": "selection provenance",
    "actionRule.presentationAuthority": "presentation selection provenance",
    "actionRule.presentationPriority": "presentation selection precedence",
    "actionRule.sourceActionKey": "source action identity",
    "actionRule.sourceChannel": "source channel identity",
    "actionRule.permissionConstraints": "server permission evidence",
    "actionRule.entitlementEvaluated": "server authorization proof",
    "sourceContext.context": "data request context",
    "sourceContext.domain": "data request domain",
    "sourceContext.contextRaw": "source context trace",
    "sourceContext.domainRaw": "source domain trace",
    "sourceContext.order": "data ordering policy",
    "sourceContext.limit": "data pagination policy",
    "activitySourceAuthority.kind": "activity projection provenance",
    "activitySourceAuthority.authorities": "activity projection provenance",
    "activitySourceAuthority.projection_only": "activity authority boundary",
    "activitySourceAuthority.no_business_fact_authority": "activity authority boundary",
    "activitySourceAuthority.runtime_carrier": "activity carrier identity",
    "visibleFields.sourceAuthority": "visible-field provenance",
    "fieldGroups.sourceAuthority": "field-group provenance",
    "runtimeContract.patchStrategy": "runtime patch policy",
    "runtimeContract.cachePolicy": "runtime cache policy",
    "runtimeContract.optimistic": "mutation settlement policy",
    "runtimeContract.lazyContainer": "runtime loading policy",
    "runtimeContract.retryPolicy": "runtime retry policy",
    "runtimeContract.hydration": "runtime hydration policy",
    "runtimeContract.patchOperations": "runtime patch vocabulary",
    "runtimeContract.tracePolicy": "runtime trace policy",
    "runtimeContract.complexityBudget": "runtime complexity governance",
    "runtimeContract.aiEnvelope": "AI authority boundary",
    "pageInfo.deliveryProfile": "client delivery identity",
    "runtimeContract.deliveryProfile": "client delivery identity",
    "meta.deliveryTrim": "client delivery projection evidence",
}

DECODED_RUNTIME_GAPS = {}

NON_VISUAL_DEFINITIONS = {
    "sourceAuthority": "projection provenance boundary",
    "contractLifecycle": "contract lifecycle provenance",
    "contractLifecycleDefinition": "schema definition provenance",
    "contractLifecycleGeneration": "generation provenance",
    "contractLifecycleRuntime": "request trace provenance",
    "contractLifecycleIntegrity": "integrity provenance",
    "meta": "snapshot identity and provenance",
    "deliveryTrim": "client delivery projection evidence",
    "deliveryCountRecord": "client delivery projection evidence",
    "deliveryLimitRecord": "client delivery projection limits",
}

CONSUMERS = {
    "sourceContext": "ContractV2 store / data request runtime",
    "searchContract": "ActionView search presentation runtime",
    "pageInfo": "page runtime / contractFormPresenter.identity",
    "layoutContract": "contractFormPresenter / ContractFormDriverHost",
    "activityProfile": "activity renderer registry",
    "activitySourceAuthority": "activity decoder authority guard",
    "activityFieldOccurrence": "activity renderer registry",
    "activityNodeOccurrence": "activity renderer registry",
    "activityNode": "activity renderer registry",
    "activityTemplate": "activity renderer registry",
    "container": "contractFormPresenter.presentNode",
    "nativeLayoutNode": "contractFormPresenter / canonicalNativeFormBridge / NativeFormTreeRenderer",
    "widget": "contractFormPresenter.fieldFromWidget / canonicalFormRenderer",
    "componentRegistryEntry": "professionalComponentRegistry",
    "statusContract": "ContractV2 store / contractFormPresenter",
    "containerStatus": "contractFormPresenter.presentNode",
    "widgetStatus": "contractFormPresenter.fieldFromWidget",
    "buttonStatus": "contractFormPresenter.presentAction",
    "selectorStatus": "resolveContractV2SelectorStatus / contractFormPresenter",
    "actionContract": "contractFormPresenter / contract action runtime",
    "actionRule": "contractFormPresenter.presentAction / action executor",
    "dataContract": "ContractV2 store / collection and form renderers",
    "dataMeta": "ContractV2 store / form and collection policy adapters",
    "visibleFields": "field visibility projection",
    "fieldGroups": "field grouping projection",
    "sourceAuthority": "decoder authority guard",
    "contractLifecycle": "decoder lifecycle guard",
    "contractLifecycleDefinition": "decoder lifecycle guard",
    "contractLifecycleGeneration": "decoder lifecycle guard",
    "contractLifecycleRuntime": "decoder lifecycle guard",
    "contractLifecycleIntegrity": "decoder lifecycle guard",
    "runtimeContract": "form runtime / collaboration and workspace adapters",
    "meta": "ContractV2 decoder / trace identity",
    "deliveryTrim": "ContractV2 decoder / delivery identity guard",
    "deliveryCountRecord": "ContractV2 decoder / delivery identity guard",
    "deliveryLimitRecord": "ContractV2 decoder / delivery identity guard",
}


def expected_paths() -> set[str]:
    return {
        f"{definition}.{name}"
        for definition, names in EXPECTED.items()
        for name in names.split()
    }


def schema_paths(schema: dict) -> set[str]:
    definitions = schema["$defs"]
    return {
        f"{definition}.{name}"
        for definition in EXPECTED
        for name in definitions[definition].get("properties", {})
    }


def build() -> dict:
    schema = json.loads(SCHEMA.read_text())
    expected = expected_paths()
    actual = schema_paths(schema)
    missing = sorted(actual - expected)
    stale = sorted(expected - actual)
    invalid_non_visual = sorted(set(NON_VISUAL) - expected)
    invalid_runtime_gaps = sorted(set(DECODED_RUNTIME_GAPS) - expected)
    if missing or stale or invalid_non_visual or invalid_runtime_gaps:
        raise SystemExit(
            "render authority matrix mismatch: "
            f"missing={missing} stale={stale} invalid_non_visual={invalid_non_visual} "
            f"invalid_runtime_gaps={invalid_runtime_gaps}"
        )
    rows = []
    for path in sorted(expected):
        definition = path.split(".", 1)[0]
        if path in DECODED_RUNTIME_GAPS:
            rows.append({
                "path": path,
                "classification": "decoded_runtime_authority_gap",
                "reason": DECODED_RUNTIME_GAPS[path],
                "consumer": "strict decoder only",
            })
        elif path in NON_VISUAL or definition in NON_VISUAL_DEFINITIONS:
            rows.append({
                "path": path,
                "classification": "validated_non_visual_authority",
                "reason": NON_VISUAL[path] if path in NON_VISUAL else NON_VISUAL_DEFINITIONS[definition],
                "consumer": CONSUMERS[definition],
            })
        else:
            rows.append({
                "path": path,
                "classification": "rendered_or_interaction_authority",
                "consumer": CONSUMERS[definition],
            })
    return {
        "schemaVersion": "contract-v2-render-authority-matrix/v1",
        "schemaAuthority": str(SCHEMA.relative_to(ROOT)),
        "scope": list(EXPECTED),
        "summary": {
            "schemaFieldCount": len(rows),
            "renderedOrInteractionAuthorityCount": sum(
                row["classification"] == "rendered_or_interaction_authority" for row in rows
            ),
            "validatedNonVisualAuthorityCount": sum(
                row["classification"] == "validated_non_visual_authority" for row in rows
            ),
            "decodedRuntimeAuthorityGapCount": sum(
                row["classification"] == "decoded_runtime_authority_gap" for row in rows
            ),
            "unclassifiedCount": 0,
        },
        "rows": rows,
    }


def main() -> None:
    payload = build()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if "--check" in sys.argv:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            raise SystemExit(f"stale render authority matrix: run {Path(__file__).relative_to(ROOT)}")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered)
    print(
        "[contract_v2_render_authority_matrix] PASS "
        f"fields={payload['summary']['schemaFieldCount']} unclassified=0"
    )


if __name__ == "__main__":
    main()

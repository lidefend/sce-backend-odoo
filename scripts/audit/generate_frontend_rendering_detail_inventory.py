#!/usr/bin/env python3
"""Generate a conservative rendering-detail professionalization inventory.

The scanner does not infer business authority.  It inventories source-level
state and interaction surfaces, then applies a small, explicit ownership map.
Anything relevant without an ownership declaration remains a formal gap.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/frontend_productization/rendering-detail/component-professionalization-inventory-v1.json"
SCHEMA_VERSION = "rendering-detail-component-coverage/v1"
STATUS_VALUES = {
    "governed_primitive",
    "governed_composite",
    "deliberate_native_composite",
    "p3_out_of_scope",
    "gap",
}

STATE_PATTERNS = {
    "loading": re.compile(r"loading|加载中|读取中|搜索中", re.I),
    "empty": re.compile(r"empty|暂无|没有|无匹配|未选择", re.I),
    "error": re.compile(r"error|失败|错误|不可用|异常", re.I),
    "disabled": re.compile(r"disabled|aria-disabled", re.I),
    "focus": re.compile(r"focus|tabindex|keydown|aria-selected", re.I),
}
RAW_CONTROL_PATTERNS = {
    "button": re.compile(r"<button\b"),
    "input": re.compile(r"<input\b"),
    "select": re.compile(r"<select\b"),
    "textarea": re.compile(r"<textarea\b"),
}
GOVERNED_STATE_PRIMITIVES = ("ScLoading", "ScEmptyState", "ScErrorState")

OWNERSHIP_PATH = ROOT / "docs/frontend_productization/rendering-detail/rendering-surface-ownership-v1.json"
OWNERSHIP = json.loads(OWNERSHIP_PATH.read_text(encoding="utf-8"))
P3_OWNER = OWNERSHIP["owners"]["p3-low-code-administration"]
P3_PREFIXES = tuple(P3_OWNER.get("prefixes", []))
P3_FILES = set(P3_OWNER["sources"])

DELIBERATE_NATIVE_COMPOSITES: dict[str, str] = {}

KNOWN_GOVERNED_COMPOSITES = {
    "frontend/apps/web/src/components/StatusPanel.vue",
    "frontend/apps/web/src/components/attachment/AttachmentViewer.vue",
    "frontend/apps/web/src/pages/ActivityPage.vue",
    "frontend/apps/web/src/components/product-shell/ActivityPageTabs.vue",
    "frontend/apps/web/src/components/page/blocks/BlockAccordionGroup.vue",
    "frontend/apps/web/src/components/page/blocks/BlockActivityFeed.vue",
    "frontend/apps/web/src/components/page/blocks/BlockAlertPanel.vue",
    "frontend/apps/web/src/components/page/blocks/BlockEntryGrid.vue",
    "frontend/apps/web/src/components/page/blocks/BlockMetricRow.vue",
    "frontend/apps/web/src/components/page/blocks/BlockProgressSummary.vue",
    "frontend/apps/web/src/components/page/blocks/BlockRecordSummary.vue",
    "frontend/apps/web/src/components/page/blocks/BlockRecordTable.vue",
    "frontend/apps/web/src/components/page/blocks/BlockTodoList.vue",
}

BATCH_BINDINGS = {
    "p0-inline-full-state-completion-v1": {
    "frontend/apps/web/src/layouts/AppShell.vue": {"scinlinestate": {"states": {"loading", "error", "empty"}, "minimum": 4}},
    "frontend/apps/web/src/components/GlobalMessagePanel.vue": {"scinlinestate": {"states": {"loading", "empty", "error"}, "minimum": 3}},
    "frontend/apps/web/src/components/action/UnsupportedActionSurface.vue": {"scerrorstate": {"minimum": 1}},
    "frontend/apps/web/src/components/page/BlockRenderer.vue": {"scerrorstate": {"attrs": {"density": "compact", ":heading-level": "5"}, "minimum": 1}},
    "frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue": {"scerrorstate": {"minimum": 1}, "scinlinestate": {"states": {"info", "empty"}, "minimum": 2}},
    "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue": {"scinlinestate": {"states": {"empty", "error", "info"}, "minimum": 4}},
    "frontend/apps/web/src/pages/contractForm/NativeCollaborationPanel.vue": {"scinlinestate": {"states": {"empty", "error"}, "minimum": 2}},
    "frontend/apps/web/src/pages/contractForm/ProfessionalCollaborationTimeline.vue": {"scinlinestate": {"states": {"loading", "empty"}, "minimum": 1}},
    },
    "p0-collection-state-control-completion-v1": {
        "frontend/apps/web/src/components/action/ActionSurfaceToolbar.vue": {"scbutton": {"minimum": 1}, "sccheckbox": {"minimum": 1}, "scselect": {"minimum": 1}},
        "frontend/apps/web/src/components/product-list/CollectionColumnHeaderControl.vue": {"scbutton": {"minimum": 1}, "sciconbutton": {"minimum": 1}},
        "frontend/apps/web/src/components/product-list/CollectionRowCell.vue": {"scbutton": {"minimum": 1}, "sciconbutton": {"minimum": 1}},
        "frontend/apps/web/src/components/product-list/CollectionSelectionControl.vue": {"sccheckbox": {"minimum": 1}},
        "frontend/apps/web/src/components/product-list/CollectionBatchActionBar.vue": {"section": {"attrs": {"data-semantic-component": "CollectionBatchActionBar", ":data-state": "loading ? 'loading' : selectedCount ? 'ready' : 'empty'"}}},
        "frontend/apps/web/src/components/product-list/CollectionGroupPageControls.vue": {"nav": {"attrs": {"data-semantic-component": "CollectionGroupPageControls", ":data-state": "loading ? 'loading' : 'ready'"}}},
        "frontend/apps/web/src/components/product-list/CollectionGroupingToolbar.vue": {"header": {"attrs": {"data-semantic-component": "CollectionGroupingToolbar"}}},
        "frontend/apps/web/src/components/product-list/CollectionKanbanRecordCard.vue": {"article": {"attrs": {"data-semantic-component": "CollectionKanbanRecordCard", ":aria-disabled": "disabled || undefined"}}},
        "frontend/apps/web/src/components/product-list/CollectionMobileRecordRow.vue": {"article": {"attrs": {"data-semantic-component": "CollectionMobileRecordRow", ":data-state": "selectionDisabled ? 'selection-disabled' : 'ready'"}}},
        "frontend/apps/web/src/components/product-list/CollectionPaginationFooter.vue": {"nav": {"attrs": {"data-semantic-component": "CollectionPaginationFooter", ":data-state": "loading ? 'loading' : 'ready'"}}},
        "frontend/apps/web/src/components/product-list/CollectionFilterChip.vue": {"scbutton": {"attrs": {"data-semantic-component": "CollectionFilterChip", ":aria-pressed": "active"}}},
        "frontend/apps/web/src/components/product-list/ListSurfaceHeader.vue": {"productlistheader": {"attrs": {"data-list-surface-header": ""}}},
        "frontend/apps/web/src/components/product-list/ProductListHeader.vue": {"section": {"attrs": {"data-semantic-component": "ProductListHeader", ":aria-busy": "loading || undefined"}}},
        "frontend/apps/web/src/components/product-list/ProductLoadingSkeleton.vue": {"section": {"attrs": {"data-semantic-component": "ProductLoadingSkeleton", "data-state": "loading"}}},
        "frontend/apps/web/src/pages/KanbanPage.vue": {"section": {"attrs": {"data-semantic-component": "KanbanPage", ":data-collection-state": "status"}}},
        "frontend/apps/web/src/pages/ListPage.vue": {"section": {"attrs": {"data-semantic-component": "ListPage", ":data-list-status": "status"}}},
        "frontend/apps/web/src/pages/ModelListPage.vue": {"main": {"attrs": {"data-semantic-component": "ModelListCompatibilityRedirect", "data-state": "redirecting"}}},
        "frontend/apps/web/src/views/ActionView.vue": {"scpage": {"attrs": {"data-semantic-component": "ActionView", ":data-collection-state": "status"}}},
        "frontend/apps/web/src/components/GroupSummaryBar.vue": {"section": {"attrs": {"data-semantic-component": "GroupSummaryBar"}}},
    },
    "p0-navigation-hierarchy-composite-completion-v1": {
        "frontend/apps/web/src/components/MenuTree.vue": {"tdesignmenu": {"attrs": {"data-semantic-component": "MenuTree", "data-semantic-driver": "tdesign-menu", ":data-state": "nodes.length ? 'ready' : 'empty'"}}},
        "frontend/apps/web/src/components/product-shell/CanonicalNavigationMenuNode.vue": {"tdesignmenuitem": {"attrs": {"data-navigation-node": "canonical"}}, "tdesignsubmenu": {"attrs": {"data-navigation-node": "canonical"}}},
        "frontend/apps/web/src/components/action/HierarchicalWorksheet.vue": {"section": {"attrs": {"data-semantic-component": "HierarchicalWorksheet", ":aria-busy": "loading || undefined"}}},
        "frontend/apps/web/src/components/action/HierarchyBrowser.vue": {"section": {"attrs": {"data-semantic-component": "HierarchyBrowser", ":aria-busy": "loading || undefined"}}},
        "frontend/apps/web/src/components/action/HierarchyPlanner.vue": {"section": {"attrs": {"data-semantic-component": "HierarchyPlanner", ":aria-busy": "loading || undefined"}}},
        "frontend/apps/web/src/components/action/HierarchyTreeNode.vue": {"div": {"attrs": {"data-semantic-component": "HierarchyTreeNode", ":data-state": "node.children.length ? 'branch' : 'leaf'"}}},
        "frontend/apps/web/src/components/product-shell/NavigationBreadcrumb.vue": {"nav": {"attrs": {"data-semantic-component": "NavigationBreadcrumb"}}},
        "frontend/apps/web/src/components/product-shell/ProductMobileNavigationDrawer.vue": {"aside": {"attrs": {"data-semantic-component": "ProductMobileNavigationDrawer"}}},
        "frontend/apps/web/src/components/product-shell/ProductSideNavigation.vue": {"nav": {"attrs": {"data-semantic-component": "ProductSideNavigation"}}},
        "frontend/apps/web/src/components/product-shell/WorkspaceContextIndicator.vue": {"div": {"attrs": {"data-semantic-component": "WorkspaceContextIndicator"}}},
    },
    "p0-form-relation-workflow-completion-v1": {
        "frontend/apps/web/src/components/product-record/ProductFormErrorSummary.vue": {"scerrorsummary": {"attrs": {"data-semantic-component": "ProductFormErrorSummary"}}},
        "frontend/apps/web/src/components/product-record/ProductFormLoadingSkeleton.vue": {"section": {"attrs": {"data-semantic-component": "ProductFormLoadingSkeleton", "data-state": "loading"}}},
        "frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue": {"div": {"attrs": {"data-semantic-component": "ProfessionalBaseFieldControl", ":data-state": "model.controlState"}}},
        "frontend/apps/web/src/components/professional-fields/ProfessionalBusinessValueControl.vue": {"div": {"attrs": {"data-semantic-component": "ProfessionalBusinessValueControl"}}},
        "frontend/apps/web/src/components/template/FormSection.vue": {"section": {"attrs": {"data-semantic-component": "FormSection"}}},
        "frontend/apps/web/src/components/template/NativeActionOverflowMenu.vue": {"div": {"attrs": {"data-semantic-component": "NativeActionOverflowMenu"}}},
        "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue": {"div": {"attrs": {"data-semantic-component": "NativeFormTreeRenderer"}}},
        "frontend/apps/web/src/components/template/NativeSmartAction.vue": {"scbutton": {"minimum": 1}},
        "frontend/apps/web/src/components/view/ViewFieldRenderer.vue": {"div": {"attrs": {"data-semantic-component": "ViewFieldRenderer"}}},
        "frontend/apps/web/src/components/view/ViewRelationalRenderer.vue": {"div": {"attrs": {"data-semantic-component": "ViewRelationalRenderer", ":aria-busy": "loading || undefined"}}, "scinlinestate": {"states": {"loading", "empty", "error", "info"}, "minimum": 4}},
        "frontend/apps/web/src/components/view/ViewNotebookRenderer.vue": {"sctabs": {"minimum": 1}},
        "frontend/apps/web/src/pages/ContractFormPage.vue": {"layoutshell": {"attrs": {"data-semantic-component": "ContractFormPage", ":data-state": "status"}}},
        "frontend/apps/web/src/pages/contractForm/CanonicalActionBar.vue": {"nav": {"attrs": {"data-semantic-component": "CanonicalActionBar"}}},
        "frontend/apps/web/src/pages/contractForm/CanonicalFormNodeRenderer.vue": {"section": {"attrs": {"data-semantic-component": "CanonicalFormNodeRenderer"}}},
        "frontend/apps/web/src/pages/contractForm/ContractFormActionBlocks.vue": {"scbutton": {"import": "ScButton", "minimum": 3}},
        "frontend/apps/web/src/pages/contractForm/ContractFormNativeCanvas.vue": {"section": {"attrs": {"data-semantic-component": "ContractFormNativeCanvas", ":data-state": "mode"}}},
        "frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue": {"pageheadertemplate": {"attrs": {"data-semantic-component": "ContractFormProductHeader"}}},
        "frontend/apps/web/src/pages/contractForm/ContractModeSupportPanel.vue": {"scbutton": {"import": "ScButton", "minimum": 2}},
        "frontend/apps/web/src/pages/contractForm/ContractPromptActionForm.vue": {"form": {"attrs": {"data-semantic-component": "ContractPromptActionForm"}}},
        "frontend/apps/web/src/pages/contractForm/ProfessionalAttachmentManager.vue": {"section": {"attrs": {"data-semantic-component": "ProfessionalAttachmentManager"}}},
        "frontend/apps/web/src/pages/contractForm/ProfessionalCollaborationComposer.vue": {"section": {"attrs": {"data-semantic-component": "ProfessionalCollaborationComposer"}}},
    },
    "p0-shared-utility-scene-completion-v1": {
        "frontend/apps/web/src/components/DevContextPanel.vue": {"aside": {"attrs": {"data-semantic-component": "DevContextPanel"}}},
        "frontend/apps/web/src/components/business/IntentConfirmationDialog.vue": {"scdialog": {"attrs": {"data-semantic-component": "IntentConfirmationDialog"}}},
        "frontend/apps/web/src/components/business/MyWorkApprovalWorkspace.vue": {"scsection": {"attrs": {"data-semantic-component": "MyWorkApprovalWorkspace"}}},
        "frontend/apps/web/src/components/page/PageRenderer.vue": {"section": {"attrs": {"data-semantic-component": "PageRenderer"}}},
        "frontend/apps/web/src/components/page/ZoneRenderer.vue": {"section": {"attrs": {"data-semantic-component": "ZoneRenderer"}}},
        "frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue": {"header": {"attrs": {"data-semantic-component": "ProductPageHeader"}}},
        "frontend/apps/web/src/components/product-shell/ProductIdentity.vue": {"div": {"attrs": {"data-semantic-component": "ProductIdentity"}}},
        "frontend/apps/web/src/components/role-home/WorkspaceHome.vue": {"div": {"attrs": {"data-semantic-component": "WorkspaceHome", ":aria-busy": "loading || undefined"}}, "scinlinestate": {"states": {"loading", "empty", "error"}, "minimum": 3}},
        "frontend/apps/web/src/components/scene/SceneBlocksRenderer.vue": {"section": {"attrs": {"data-semantic-component": "SceneBlocksRenderer"}}},
        "frontend/apps/web/src/views/AccessDeniedView.vue": {"scpage": {"attrs": {"data-semantic-component": "AccessDeniedView", "data-state": "error"}}},
        "frontend/apps/web/src/views/AccountActivationView.vue": {"main": {"attrs": {"data-semantic-component": "AccountActivationView"}}},
        "frontend/apps/web/src/views/ApiKeyManagementView.vue": {"scpage": {"attrs": {"data-semantic-component": "ApiKeyManagementView", ":aria-busy": "loading || undefined"}}},
        "frontend/apps/web/src/views/LoginView.vue": {"main": {"attrs": {"data-semantic-component": "LoginView", ":aria-busy": "loading || undefined"}}},
        "frontend/apps/web/src/views/MenuView.vue": {"section": {"attrs": {"data-semantic-component": "MenuView", ":aria-busy": "loading || undefined"}}},
        "frontend/apps/web/src/views/MyWorkView.vue": {"scpage": {"attrs": {"data-semantic-component": "MyWorkView"}}},
        "frontend/apps/web/src/views/NotFoundView.vue": {"scpage": {"attrs": {"data-semantic-component": "NotFoundView", "data-state": "error"}}},
        "frontend/apps/web/src/views/PasswordRecoveryView.vue": {"main": {"attrs": {"data-semantic-component": "PasswordRecoveryView"}}},
        "frontend/apps/web/src/views/PlaceholderView.vue": {"main": {"attrs": {"data-semantic-component": "PlaceholderView"}}},
        "frontend/apps/web/src/views/SceneContractBlockGridView.vue": {"section": {"attrs": {"data-semantic-component": "SceneContractBlockGridView", ":data-state": "status"}}},
        "frontend/apps/web/src/views/SceneView.vue": {"section": {"attrs": {"data-semantic-component": "SceneView", ":aria-busy": "isLoading || undefined"}}},
        "frontend/apps/web/src/views/WorkbenchView.vue": {"pagerenderer": {"attrs": {"data-semantic-component": "WorkbenchView", "data-state": "unified"}}, "section": {"attrs": {"data-semantic-component": "WorkbenchView", "data-state": "fallback"}}},
    },
}
OWNED_BINDINGS = {
    source: (batch, requirements)
    for batch, bindings in BATCH_BINDINGS.items()
    for source, requirements in bindings.items()
}
NEXT_BATCH_GAPS = set(BATCH_BINDINGS["p0-inline-full-state-completion-v1"])
NEXT_BATCH_BINDINGS = BATCH_BINDINGS["p0-inline-full-state-completion-v1"]
COMPONENT_IMPORTS = {
    "scinlinestate": "ScInlineState",
    "scerrorstate": "ScErrorState",
}


def ownership_binding_failures(
    ownership: dict[str, Any] = OWNERSHIP,
    batch_bindings: dict[str, dict[str, dict[str, dict[str, Any]]]] = BATCH_BINDINGS,
) -> list[str]:
    failures: list[str] = []
    owners = ownership.get("owners") if isinstance(ownership, dict) else None
    if not isinstance(owners, dict):
        return ["ownership registry must declare owners"]
    formal_batches = {
        key: value for key, value in owners.items()
        if isinstance(value, dict) and value.get("formalProductLayer") in {"P0", "P1"}
    }
    for batch in sorted(set(formal_batches) | set(batch_bindings)):
        owner = formal_batches.get(batch)
        bindings = batch_bindings.get(batch)
        if owner is None:
            failures.append(f"binding batch lacks formal P0/P1 owner: {batch}")
            continue
        if bindings is None:
            failures.append(f"formal P0/P1 owner lacks binding batch: {batch}")
            continue
        declared = owner.get("sources")
        if not isinstance(declared, list) or any(not isinstance(source, str) or not source for source in declared):
            failures.append(f"formal owner sources are invalid: {batch}")
            continue
        declared_set = set(declared)
        binding_set = set(bindings)
        for source in sorted(declared_set - binding_set):
            failures.append(f"formal owner source lacks binding: {batch}: {source}")
        for source in sorted(binding_set - declared_set):
            failures.append(f"binding source lacks formal ownership: {batch}: {source}")
    source_owners: dict[str, list[str]] = {}
    for batch, owner in formal_batches.items():
        for source in owner.get("sources", []):
            if isinstance(source, str):
                source_owners.setdefault(source, []).append(batch)
    for source, batches in sorted(source_owners.items()):
        if len(batches) > 1:
            failures.append(f"formal source has multiple owners: {source}: {','.join(sorted(batches))}")
    return failures


class TemplateElements(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str]]] = []
        self.stack: list[tuple[str, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        statically_dead = attributes.get("v-if", "").strip().lower() in {"false", "0", "null", "undefined"}
        reachable = not statically_dead and all(parent_reachable for _, parent_reachable in self.stack)
        if reachable:
            self.elements.append((tag, attributes))
        self.stack.append((tag, reachable))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def component_binding_failures(text: str, requirements: dict[str, dict[str, Any]]) -> list[str]:
    template_start = re.search(r"<template(?:\s[^>]*)?>", text)
    template_end = text.rfind("</template>", 0, text.find("<script"))
    script_match = re.search(r"<script\s+setup(?:\s[^>]*)?>(.*?)</script>", text, re.S)
    if not template_start or template_end < template_start.end() or not script_match:
        return ["missing template or script setup block"]
    parser = TemplateElements()
    parser.feed(text[template_start.end():template_end])
    script = re.sub(r"/\*.*?\*/|//[^\n]*", "", script_match.group(1), flags=re.S)
    imports = set(re.findall(r"import\s+([A-Za-z_$][\w$]*)\s+from\s+['\"][^'\"]*design-system/[^'\"]+['\"]", script))
    failures: list[str] = []
    for tag, rule in requirements.items():
        expected_import = rule.get("import") or COMPONENT_IMPORTS.get(tag)
        if expected_import and expected_import not in imports:
            failures.append(f"missing design-system import {expected_import}")
        nodes = [attrs for node_tag, attrs in parser.elements if node_tag == tag]
        if len(nodes) < rule.get("minimum", 1):
            failures.append(f"{expected_import or tag} template nodes {len(nodes)} < {rule.get('minimum', 1)}")
        for name, value in rule.get("attrs", {}).items():
            if not any(attrs.get(name) == value for attrs in nodes):
                failures.append(f"{expected_import or tag} missing template attribute {name}={value}")
        states = set()
        for attrs in nodes:
            if "state" in attrs:
                states.add(attrs["state"])
            expression = attrs.get(":state", "")
            states.update(re.findall(r"['\"](info|loading|empty|error)['\"]", expression))
        missing_states = set(rule.get("states", set())) - states
        if missing_states:
            failures.append(f"{expected_import or tag} missing states {','.join(sorted(missing_states))}")
    return failures


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()


def digest(paths: list[Path]) -> str:
    result = hashlib.sha256()
    for path in sorted(paths):
        result.update(rel(path).encode())
        result.update(b"\0")
        result.update(path.read_bytes())
        result.update(b"\0")
    return result.hexdigest()


def is_p3(source: str) -> bool:
    return source in P3_FILES or source.startswith(P3_PREFIXES)


def classify(source: str, text: str) -> tuple[str, str]:
    if "/components/design-system/" in source:
        return "governed_primitive", "design-system primitive source"
    if is_p3(source):
        return "p3_out_of_scope", "low-code or administration product surface; handled by a separate P3 batch"
    if source in DELIBERATE_NATIVE_COMPOSITES:
        return "deliberate_native_composite", DELIBERATE_NATIVE_COMPOSITES[source]
    raw_controls = sorted(name for name, pattern in RAW_CONTROL_PATTERNS.items() if pattern.search(text))
    if raw_controls:
        return "gap", f"formal P0/P1 surface bypasses governed adapters: {', '.join(raw_controls)}"
    if source in KNOWN_GOVERNED_COMPOSITES:
        return "governed_composite", "state/dashboard or overlay guard owns this composite"
    if source in OWNED_BINDINGS:
        _, requirements = OWNED_BINDINGS[source]
        failures = component_binding_failures(text, requirements)
        if not failures:
            return "governed_composite", "formal ownership and parsed SFC component bindings are present"
        return "gap", f"declared P0 inline/full-state completion target; invalid bindings: {'; '.join(failures)}"
    if "data-professional-" in text and any(name in text for name in GOVERNED_STATE_PRIMITIVES):
        return "governed_composite", "professional semantic marker and governed state primitive are both present"
    return "gap", "relevant state or native interaction has no explicit professionalization ownership declaration"


def build_inventory() -> dict[str, Any]:
    binding_failures = ownership_binding_failures()
    if binding_failures:
        raise ValueError("invalid rendering ownership bindings: " + "; ".join(binding_failures))
    vue_files = sorted((ROOT / "frontend/apps/web/src").rglob("*.vue"))
    surfaces: list[dict[str, Any]] = []
    for path in vue_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        state_types = [name for name, pattern in STATE_PATTERNS.items() if pattern.search(text)]
        raw_controls = {name: len(pattern.findall(text)) for name, pattern in RAW_CONTROL_PATTERNS.items()}
        raw_controls = {name: count for name, count in raw_controls.items() if count}
        governed_primitives = [name for name in GOVERNED_STATE_PRIMITIVES if name in text]
        source = rel(path)
        if not state_types and not raw_controls and not governed_primitives and source not in OWNED_BINDINGS:
            continue
        status, reason = classify(source, text)
        if status not in STATUS_VALUES:
            raise ValueError(f"invalid status for {source}: {status}")
        surfaces.append({
            "source": source,
            "formalProductLayer": "P3" if status == "p3_out_of_scope" else "P0",
            "status": status,
            "reason": reason,
            "stateTypes": state_types,
            "rawControls": raw_controls,
            "governedStatePrimitives": governed_primitives,
            "targetBatch": OWNED_BINDINGS[source][0] if source in OWNED_BINDINGS else None,
        })
    counts = Counter(item["status"] for item in surfaces)
    p0_p1_raw_bypass_surfaces = [
        item for item in surfaces
        if item["formalProductLayer"] in {"P0", "P1"}
        and item["status"] != "governed_primitive"
        and item["rawControls"]
    ]
    p0_p1_raw_bypass_controls = sum(
        sum(item["rawControls"].values()) for item in p0_p1_raw_bypass_surfaces
    )
    next_batch = None if counts.get("gap", 0) == 0 else {
        "key": "p0-shared-utility-scene-completion-v1",
        "targetSurfaceCount": len(BATCH_BINDINGS["p0-shared-utility-scene-completion-v1"]),
        "targetSources": sorted(BATCH_BINDINGS["p0-shared-utility-scene-completion-v1"]),
        "commitBudget": {"minimum": 12, "maximum": 20},
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "sourceCommit": git("merge-base", "HEAD", "origin/main"),
        "generatorDigest": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "ownershipDigest": hashlib.sha256(OWNERSHIP_PATH.read_bytes()).hexdigest(),
        "inputDigest": digest(vue_files + [OWNERSHIP_PATH]),
        "scope": "repository formal-product frontend Vue rendering-detail sources",
        "statusVocabulary": sorted(STATUS_VALUES),
        "excludedScopes": [
            "demo_addons",
            "external customer_addons",
            "runtime installed-module state",
            "Contract V2 authority changes",
            "permission and route authority changes",
        ],
        "summary": {
            "surfaceCount": len(surfaces),
            "p0P1RawControlBypassSurfaceCount": len(p0_p1_raw_bypass_surfaces),
            "p0P1RawControlBypassControlCount": p0_p1_raw_bypass_controls,
            **{key: counts.get(key, 0) for key in sorted(STATUS_VALUES)},
        },
        "nextBatch": next_batch,
        "surfaces": surfaces,
        "completionPolicy": {
            "formalP0P1UntreatedGapTarget": 0,
            "formalP0P1RawControlBypassTarget": 0,
            "gapIsFailClosed": True,
            "nativeControlRequiresExplicitCompositeOwnership": True,
            "p3DoesNotBlockP0P1Completion": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_inventory()
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != encoded:
            print(f"[frontend_rendering_detail_inventory] FAIL stale={rel(output)}")
            return 1
        print(f"[frontend_rendering_detail_inventory] PASS surfaces={report['summary']['surfaceCount']} gaps={report['summary']['gap']}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8")
    print(f"[frontend_rendering_detail_inventory] wrote {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

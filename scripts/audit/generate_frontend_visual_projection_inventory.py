#!/usr/bin/env python3
"""Generate a conservative source-to-adapter visual projection inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.verify.frontend_primitive_adapter_guard import component_style_text, direct_root_visual_overrides, p3_scope
WEB_REL = Path("frontend/apps/web/src")
DEFAULT_REFERENCE = ROOT / "docs/frontend_productization/rendering-detail/daily-frontend-reference-projection-v1.json"
DEFAULT_OUTPUT = ROOT / "docs/frontend_productization/rendering-detail/visual-projection-inventory-v1.json"
THEME = ROOT / "frontend/packages/ui/src/kits/tdesign/theme.css"
VISUAL_PARITY = ROOT / "docs/frontend_productization/rendering-detail/visual-parity-inventory-v1.json"

# A formal gap is closed only when its static authority and representative
# runtime evidence are both wired into governed Make targets.  The tracked
# parity document describes the product requirement; it is not allowed to
# self-assert closure.
FORMAL_GAP_EVIDENCE = {
    "collection.page-identity-and-primary-action": ("verify.frontend.product_page_header.unit", "verify.frontend.product_page_header.browser", "scripts/verify/frontend_product_page_header_browser.mjs", "[data-product-page-header]"),
    "collection.workspace-gutter-and-ledger-density": ("verify.frontend.collection_row_cell.unit", "local.dev.candidate.frontend.visual-smoke", "scripts/verify/local_dev_candidate_visual_smoke.mjs", "collectionMobileRecordEvidence"),
    "collection.query-filter-view-toolbar-hierarchy": ("verify.frontend.collection_action_toolbar.unit", "local.dev.candidate.frontend.visual-smoke", "scripts/verify/local_dev_candidate_visual_smoke.mjs", "collectionToolbarEvidence"),
    "collection.authoritative-status-tone": ("verify.frontend.collection_row_cell.unit", "local.dev.candidate.frontend.visual-smoke", "scripts/verify/local_dev_candidate_visual_smoke.mjs", "collectionSummaryEvidence"),
    "shell.context-and-navigation-density": ("verify.frontend.navigation_shell.unit", "local.dev.candidate.frontend.visual-smoke", "scripts/verify/local_dev_candidate_visual_smoke.mjs", "shellAdapterEvidence"),
    "form.task-field-hierarchy": ("verify.frontend.primitive_adapter.unit", "verify.frontend.rendering_detail_state.browser", "scripts/verify/frontend_rendering_detail_state_browser.mjs", "data-semantic-component"),
    "form.workspace-native-structure-density": ("verify.frontend.native_form_action_presentation.unit", "verify.frontend.native_form_action_presentation.browser", "scripts/verify/frontend_native_form_action_presentation_browser.mjs", "focusSequence"),
    "relations-x2many.lifecycle-and-table-detail": ("verify.frontend.professional_relation_lifecycle.unit", "local.dev.candidate.frontend.visual-smoke", "scripts/verify/local_dev_candidate_visual_smoke.mjs", "relationSearchDialogEvidence"),
    "workflow.action-status-disabled-reason": ("verify.frontend.professional_workflow.unit", "verify.frontend.native_form_action_presentation.browser", "scripts/verify/frontend_native_form_action_presentation_browser.mjs", "allDisabledEscapeClosed"),
    "overlay.dialog-drawer-focus-density": ("verify.frontend.overlay_lifecycle.unit", "verify.frontend.overlay_lifecycle.browser", "scripts/verify/frontend_overlay_lifecycle_browser.mjs", "bodyLocked"),
    "collaboration.chatter-activity-attachment": ("verify.frontend.professional_collaboration.unit", "verify.frontend.collaboration_primitives.browser", "scripts/verify/frontend_collaboration_primitives_browser.mjs", "filePrimitivePresent"),
    "states.loading-empty-error-disabled-focus": ("verify.frontend.rendering_detail_state.unit", "verify.frontend.rendering_detail_state.browser", "scripts/verify/frontend_rendering_detail_state_browser.mjs", "data-state"),
    "dashboard.metric-risk-todo-drilldown": ("verify.frontend.state_dashboard.unit", "verify.frontend.state_dashboard.browser", "scripts/verify/frontend_state_dashboard_browser.mjs", "dashboardActions"),
    "responsive.390-no-overflow-and-action-settlement": ("verify.frontend.rendering_detail_state.unit", "local.dev.candidate.frontend.visual-smoke", "scripts/verify/local_dev_candidate_visual_smoke.mjs", "mobileOverflow"),
}

SC_TAG_RE = re.compile(r"<(?P<name>Sc[A-Z][A-Za-z0-9]+)\b")
STYLE_RE = re.compile(r"<style[^>]*>(?P<body>.*?)</style>", re.S | re.I)
NATIVE_SELECTOR_RE = re.compile(r"(?m)(?P<selector>[^{}]*(?:^|[\s>+~,])(input|button|select|textarea)(?=[:.#[\s>+~,{]|$)[^{}]*)\{")
CONSUMER_PRIMITIVE_CHROME_RE = re.compile(
    r":deep\(\.sc-(?:input|btn|icon-button|select|textarea|checkbox|radio|dialog|drawer|tabs|table)[^)]*\)\s*\{(?P<body>[^}]*)\}",
    re.S,
)
VISUAL_CHROME_PROPERTY_RE = re.compile(r"(?:^|;)\s*(?:border(?!-(?:collapse|spacing))(?:-[a-z]+)?|background|border-radius|box-shadow|outline|color)\s*:", re.M)

ADAPTER_MARKERS = {
    "ScInput": ".sc-input.t-input__wrap[data-size='large'] > .t-input",
    "ScInputGroup": ".sc-input-group",
    "ScButton": ".sc-btn.t-button",
    "ScSelect": ".sc-select[data-size='medium'] .t-input",
    "ScTextarea": ".sc-textarea .t-textarea__inner",
    "ScTable": "[data-semantic-component='ScTable']",
    "ScDialog": ".sc-dialog",
    "ScDrawer": ".sc-design-drawer",
    "ScTabs": "[data-semantic-component='ScTabs']",
    "ScCheckbox": "[data-semantic-component='ScCheckbox']",
    "ScRadio": "[data-semantic-component='ScRadio']",
    "ScRadioGroup": "[data-semantic-component='ScRadioGroup']",
    "ScLoading": "[data-semantic-component='ScLoading']",
    "ScEmptyState": "[data-semantic-component='ScEmptyState']",
    "ScErrorState": "[data-semantic-component='ScErrorState']",
    "ScBadge": "[data-semantic-component='ScBadge']",
    "ScDropdown": "[data-semantic-component='ScDropdown']",
    "ScTooltip": "[data-semantic-component='ScTooltip']",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_source_root(root: Path) -> Path:
    candidate = root / WEB_REL
    if candidate.is_dir():
        return candidate
    if root.name == "src" and root.is_dir():
        return root
    raise ValueError(f"reference root does not contain {WEB_REL}")


def category(path: str) -> str:
    if path.endswith(("LoginView.vue", "AccountActivationView.vue", "PasswordRecoveryView.vue")):
        return "public-entry"
    if any(token in path for token in ("product-list/", "ListPage", "KanbanPage", "ActionView")):
        return "collection"
    if any(token in path for token in ("Relation", "X2Many", "one2many")):
        return "relations-x2many"
    if any(token in path for token in ("ActionBar", "Workflow", "Status")):
        return "workflow"
    if any(token in path for token in ("Dialog", "Drawer", "Overlay")):
        return "overlay"
    if any(token in path for token in ("Collaboration", "Chatter", "Activity", "Attachment")):
        return "collaboration"
    if any(token in path for token in ("Loading", "Empty", "Error", "InlineState")):
        return "states"
    if any(token in path for token in ("Dashboard", "Metric", "Risk", "Todo", "Workbench", "WorkspaceHome")):
        return "dashboard"
    if any(token in path for token in ("AppShell", "product-shell", "MenuTree")):
        return "shell"
    if any(token in path for token in ("Form", "Field", "contractForm", "professional-fields")):
        return "form-fields"
    return "other"


def inspect_source(path: Path, source_root: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    style = "\n".join(match.group("body") for match in STYLE_RE.finditer(text))
    selectors = sorted({" ".join(match.group("selector").split()) for match in NATIVE_SELECTOR_RE.finditer(style)})
    relative = path.relative_to(source_root).as_posix()
    return {
        "path": relative,
        "digest": digest(text.encode()),
        "category": category(relative),
        "scComponents": sorted(set(SC_TAG_RE.findall(text))),
        "nativeStyleSelectors": selectors,
    }


def inspect_tree(root: Path) -> list[dict[str, object]]:
    source_root = normalized_source_root(root)
    return [inspect_source(path, source_root) for path in sorted(source_root.rglob("*.vue"))]


def consumer_primitive_visual_chrome(root: Path = ROOT) -> list[str]:
    source_root = normalized_source_root(root)
    p3_files, p3_prefixes = p3_scope(root)
    violations = []
    for path in sorted(source_root.rglob("*.vue")):
        relative = path.relative_to(source_root).as_posix()
        repository_relative = path.relative_to(root).as_posix() if path.is_relative_to(root) else relative
        if relative.startswith("components/design-system/"):
            continue
        if repository_relative in p3_files or repository_relative.startswith(p3_prefixes):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        style_text = component_style_text(path, text)
        if (
            any(VISUAL_CHROME_PROPERTY_RE.search(match.group("body")) for match in CONSUMER_PRIMITIVE_CHROME_RE.finditer(style_text))
            or direct_root_visual_overrides(text, style_text)
        ):
            violations.append(relative)
    return violations


def encode(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def evaluate_formal_gap_evidence(parity: dict[str, object], root: Path = ROOT) -> list[dict[str, object]]:
    make_authority = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "make/frontend.mk", root / "make/dev.mk")
        if path.is_file()
    )
    wrapper_authority = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            root / "scripts/dev/local_dev_candidate_frontend.py",
            root / "scripts/verify/local_dev_candidate_visual_smoke.sh",
        )
        if path.is_file()
    )
    results = []
    for gap in parity.get("gaps", []):
        key = str(gap.get("key", ""))
        evidence = FORMAL_GAP_EVIDENCE.get(key)
        if evidence is None:
            results.append({"key": key, "status": "open", "reason": "evidence_binding_missing"})
            continue
        unit_target, browser_target, browser_source, assertion_marker = evidence
        source_path = root / browser_source
        source = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
        unit_wired = re.search(rf"(?m)^{re.escape(unit_target)}\s*:", make_authority) is not None
        browser_wired = re.search(rf"(?m)^{re.escape(browser_target)}\s*:", make_authority) is not None
        target_recipe_wired = browser_wired and browser_source in (make_authority + wrapper_authority)
        failure_exit_present = (
            "process.exit(1)" in source
            or "process.exitCode = 1" in source
            or ("function check" in source and "throw new Error" in source)
        )
        assertion_present = assertion_marker in source
        status = "bound" if unit_wired and target_recipe_wired and failure_exit_present and assertion_present else "invalid"
        results.append({
            "key": key,
            "status": status,
            "unitTarget": unit_target,
            "unitTargetWired": unit_wired,
            "browserTarget": browser_target,
            "browserTargetWired": browser_wired,
            "browserTargetRecipeWired": target_recipe_wired,
            "browserEvidenceSource": browser_source,
            "browserAssertionMarker": assertion_marker,
            "browserAssertionMarkerPresent": assertion_present,
            "browserFailureExitPresent": failure_exit_present,
        })
    return results


def capture_reference(root: Path, output: Path) -> None:
    sources = inspect_tree(root)
    payload = {
        "schemaVersion": "frontend.visual-projection.reference.v1",
        "referenceKind": "daily-frontend-source-snapshot",
        "sourceCount": len(sources),
        "inputDigest": digest(encode({"sources": sources}).encode()),
        "sources": sources,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encode(payload), encoding="utf-8")


def build_inventory(reference_path: Path) -> dict[str, object]:
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    reference_by_path = {row["path"]: row for row in reference["sources"]}
    current = inspect_tree(ROOT)
    theme = THEME.read_text(encoding="utf-8")
    projection = []
    for component, marker in ADAPTER_MARKERS.items():
        source = ROOT / WEB_REL / "components/design-system" / f"{component}.vue"
        driver_present = source.is_file() and "TDesign" in source.read_text(encoding="utf-8")
        marker_present = marker in theme
        projection.append({
            "component": component,
            "driverPresent": driver_present,
            "projectionMarker": marker,
            "projectionMarkerPresent": marker_present,
            "status": "projected" if driver_present and marker_present else "projection_unassessed",
        })
    differences = []
    for row in current:
        previous = reference_by_path.get(row["path"])
        if not previous or previous["digest"] != row["digest"]:
            differences.append({
                **row,
                "referencePresent": previous is not None,
                "referenceScComponents": previous.get("scComponents", []) if previous else [],
                "referenceNativeStyleSelectors": previous.get("nativeStyleSelectors", []) if previous else [],
            })
    parity = json.loads(VISUAL_PARITY.read_text(encoding="utf-8"))
    formal_gap_evidence = evaluate_formal_gap_evidence(parity)
    invalid_bindings = [gap["key"] for gap in formal_gap_evidence if gap["status"] != "bound"]
    risky = [row for row in current if row["scComponents"] and row["nativeStyleSelectors"]]
    consumer_chrome = consumer_primitive_visual_chrome(ROOT)
    return {
        "schemaVersion": "frontend.visual-projection.inventory.v1",
        "scope": "repository formal P0/P1 frontend source projection",
        "referenceInputDigest": reference["inputDigest"],
        "currentInputDigest": digest(encode({"sources": current}).encode()),
        "adapterProjection": projection,
        "changedSourceProjection": differences,
        "scAdapterWithNativeSelectorCandidates": risky,
        "consumerPrimitiveVisualChrome": consumer_chrome,
        "formalGapEvidence": formal_gap_evidence,
        "invalidFormalVisualEvidenceBindings": invalid_bindings,
        "summary": {
            "referenceSourceCount": reference["sourceCount"],
            "currentSourceCount": len(current),
            "changedSourceCount": len(differences),
            "adapterCount": len(projection),
            "projectedAdapterCount": sum(row["status"] == "projected" for row in projection),
            "unassessedAdapterCount": sum(row["status"] != "projected" for row in projection),
            "scAdapterWithNativeSelectorCandidateCount": len(risky),
            "consumerPrimitiveVisualChromeCount": len(consumer_chrome),
            "invalidFormalVisualEvidenceBindingCount": len(invalid_bindings),
        },
        "evidenceSemantics": "tracked inventory proves deterministic evidence binding only; exact-head runtime artifacts decide candidate verification and this report never asserts runtime closure",
        "excludedScopes": ["runtime permissions", "Contract authority", "database data", "customer addons", "exact-head runtime pass/fail"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-reference", type=Path)
    parser.add_argument("--reference-root", type=Path)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.capture_reference:
        if not args.reference_root:
            parser.error("--reference-root is required with --capture-reference")
        capture_reference(args.reference_root.resolve(), args.capture_reference.resolve())
        return 0
    payload = encode(build_inventory(args.reference.resolve()))
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != payload:
            print(f"[frontend_visual_projection_inventory] FAIL stale={output}")
            return 1
        print("[frontend_visual_projection_inventory] PASS")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(f"[frontend_visual_projection_inventory] wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

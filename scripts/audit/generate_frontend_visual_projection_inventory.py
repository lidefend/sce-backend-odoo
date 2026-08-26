#!/usr/bin/env python3
"""Generate a conservative source-to-adapter visual projection inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB_REL = Path("frontend/apps/web/src")
DEFAULT_REFERENCE = ROOT / "docs/frontend_productization/rendering-detail/daily-frontend-reference-projection-v1.json"
DEFAULT_OUTPUT = ROOT / "docs/frontend_productization/rendering-detail/visual-projection-inventory-v1.json"
THEME = ROOT / "frontend/packages/ui/src/kits/tdesign/theme.css"
VISUAL_PARITY = ROOT / "docs/frontend_productization/rendering-detail/visual-parity-inventory-v1.json"

SC_TAG_RE = re.compile(r"<(?P<name>Sc[A-Z][A-Za-z0-9]+)\b")
STYLE_RE = re.compile(r"<style[^>]*>(?P<body>.*?)</style>", re.S | re.I)
NATIVE_SELECTOR_RE = re.compile(r"(?m)(?P<selector>[^{}]*(?:^|[\s>+~,])(input|button|select|textarea)(?=[:.#[\s>+~,{]|$)[^{}]*)\{")

ADAPTER_MARKERS = {
    "ScInput": ".sc-input.t-input__wrap[data-size='large'] > .t-input",
    "ScButton": ".sc-btn.t-button",
    "ScSelect": ".sc-select[data-size='medium'] .t-input",
    "ScTextarea": ".sc-textarea .t-textarea__inner",
    "ScTable": ".sc-table",
    "ScDialog": ".sc-dialog",
    "ScDrawer": ".sc-design-drawer",
    "ScTabs": ".sc-tabs",
    "ScCheckbox": ".sc-checkbox",
    "ScRadio": ".sc-radio",
    "ScRadioGroup": ".sc-radio-group",
    "ScLoading": ".sc-loading",
    "ScEmptyState": ".sc-empty",
    "ScErrorState": ".sc-error-state",
    "ScBadge": ".sc-badge",
    "ScDropdown": ".sc-dropdown",
    "ScTooltip": ".sc-tooltip",
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


def encode(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


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
    open_gaps = [gap["key"] for gap in parity["gaps"] if gap["status"] == "open"]
    risky = [row for row in current if row["scComponents"] and row["nativeStyleSelectors"]]
    return {
        "schemaVersion": "frontend.visual-projection.inventory.v1",
        "scope": "repository formal P0/P1 frontend source projection",
        "referenceInputDigest": reference["inputDigest"],
        "currentInputDigest": digest(encode({"sources": current}).encode()),
        "adapterProjection": projection,
        "changedSourceProjection": differences,
        "scAdapterWithNativeSelectorCandidates": risky,
        "openFormalVisualGaps": open_gaps,
        "summary": {
            "referenceSourceCount": reference["sourceCount"],
            "currentSourceCount": len(current),
            "changedSourceCount": len(differences),
            "adapterCount": len(projection),
            "projectedAdapterCount": sum(row["status"] == "projected" for row in projection),
            "unassessedAdapterCount": sum(row["status"] != "projected" for row in projection),
            "scAdapterWithNativeSelectorCandidateCount": len(risky),
            "openFormalVisualGapCount": len(open_gaps),
        },
        "excludedScopes": ["runtime permissions", "Contract authority", "database data", "customer addons"],
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

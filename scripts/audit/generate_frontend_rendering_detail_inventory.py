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

P3_PREFIXES = (
    "frontend/apps/web/src/views/businessConfigSurface/",
)
P3_FILES = {
    "frontend/apps/web/src/pages/contractForm/CurrentFormFieldSettingsPanel.vue",
    "frontend/apps/web/src/views/BusinessConfigSurfaceView.vue",
    "frontend/apps/web/src/views/MenuConfigView.vue",
    "frontend/apps/web/src/views/ReleaseOperatorView.vue",
    "frontend/apps/web/src/views/SceneHealthView.vue",
    "frontend/apps/web/src/views/ScenePackagesView.vue",
    "frontend/apps/web/src/views/UsageAnalyticsView.vue",
}

DELIBERATE_NATIVE_COMPOSITES = {
    "frontend/apps/web/src/components/action/ActionSurfaceToolbar.vue": "collection disclosure and facet controls retain native button semantics under the collection toolbar guard",
    "frontend/apps/web/src/components/product-list/CollectionColumnHeaderControl.vue": "column sorting and disclosure are a registered collection composite",
    "frontend/apps/web/src/components/product-list/CollectionRowCell.vue": "row-cell interaction is owned by the collection row-cell guard",
    "frontend/apps/web/src/components/product-list/CollectionSelectionControl.vue": "native checkbox semantics are owned by the collection selection guard",
    "frontend/apps/web/src/components/template/NativeSmartAction.vue": "native smart action semantics are owned by the native action presentation guard",
    "frontend/apps/web/src/components/view/ViewNotebookRenderer.vue": "native notebook interaction is owned by the structured form renderer",
}

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

NEXT_BATCH_GAPS = {
    "frontend/apps/web/src/layouts/AppShell.vue",
    "frontend/apps/web/src/components/GlobalMessagePanel.vue",
    "frontend/apps/web/src/components/action/UnsupportedActionSurface.vue",
    "frontend/apps/web/src/components/page/BlockRenderer.vue",
    "frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue",
    "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue",
    "frontend/apps/web/src/pages/contractForm/NativeCollaborationPanel.vue",
    "frontend/apps/web/src/pages/contractForm/ProfessionalCollaborationTimeline.vue",
}

NEXT_BATCH_COMPLETION_MARKERS = {
    "frontend/apps/web/src/layouts/AppShell.vue": ("ScInlineState", 'state="loading"', 'state="error"', 'state="empty"'),
    "frontend/apps/web/src/components/GlobalMessagePanel.vue": ("ScInlineState", "loadingConversations ? 'loading' : 'empty'", "loadingMessages ? 'loading' : 'empty'", 'state="error"'),
    "frontend/apps/web/src/components/action/UnsupportedActionSurface.vue": ("ScErrorState", "ACTION_SURFACE_RENDERER_NOT_REGISTERED"),
    "frontend/apps/web/src/components/page/BlockRenderer.vue": ("ScErrorState", 'density="compact"', ':heading-level="5"'),
    "frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue": ("ScErrorState", "ScInlineState", "blockedActionMessage", "data-contract-form-driver-error"),
    "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue": ("ScInlineState", 'state="empty"', 'state="error"', "data-readonly-relation-empty"),
    "frontend/apps/web/src/pages/contractForm/NativeCollaborationPanel.vue": ("ScInlineState", 'state="empty"', 'state="error"'),
    "frontend/apps/web/src/pages/contractForm/ProfessionalCollaborationTimeline.vue": ("ScInlineState", "timelineLoading ? 'loading' : 'empty'"),
}


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
    if source in KNOWN_GOVERNED_COMPOSITES:
        return "governed_composite", "state/dashboard or overlay guard owns this composite"
    if source in NEXT_BATCH_GAPS:
        missing = [marker for marker in NEXT_BATCH_COMPLETION_MARKERS[source] if marker not in text]
        if not missing:
            return "governed_composite", "P0 inline/full-state completion markers are present"
        return "gap", f"declared P0 inline/full-state completion target; missing markers: {', '.join(missing)}"
    if "data-professional-" in text and any(name in text for name in GOVERNED_STATE_PRIMITIVES):
        return "governed_composite", "professional semantic marker and governed state primitive are both present"
    return "gap", "relevant state or native interaction has no explicit professionalization ownership declaration"


def build_inventory() -> dict[str, Any]:
    vue_files = sorted((ROOT / "frontend/apps/web/src").rglob("*.vue"))
    surfaces: list[dict[str, Any]] = []
    for path in vue_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        state_types = [name for name, pattern in STATE_PATTERNS.items() if pattern.search(text)]
        raw_controls = {name: len(pattern.findall(text)) for name, pattern in RAW_CONTROL_PATTERNS.items()}
        raw_controls = {name: count for name, count in raw_controls.items() if count}
        governed_primitives = [name for name in GOVERNED_STATE_PRIMITIVES if name in text]
        if not state_types and not raw_controls and not governed_primitives:
            continue
        source = rel(path)
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
            "targetBatch": "p0-inline-full-state-completion-v1" if source in NEXT_BATCH_GAPS else None,
        })
    counts = Counter(item["status"] for item in surfaces)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "sourceCommit": git("merge-base", "HEAD", "origin/main"),
        "generatorDigest": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputDigest": digest(vue_files),
        "scope": "repository formal-product frontend Vue rendering-detail sources",
        "statusVocabulary": sorted(STATUS_VALUES),
        "excludedScopes": [
            "demo_addons",
            "external customer_addons",
            "runtime installed-module state",
            "Contract V2 authority changes",
            "permission and route authority changes",
        ],
        "summary": {"surfaceCount": len(surfaces), **{key: counts.get(key, 0) for key in sorted(STATUS_VALUES)}},
        "nextBatch": {
            "key": "p0-inline-full-state-completion-v1",
            "targetSurfaceCount": len(NEXT_BATCH_GAPS),
            "targetSources": sorted(NEXT_BATCH_GAPS),
            "commitBudget": {"minimum": 12, "maximum": 20},
        },
        "surfaces": surfaces,
        "completionPolicy": {
            "formalP0P1UntreatedGapTarget": 0,
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

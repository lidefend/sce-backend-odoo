#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLOCK_ROOT = ROOT / "frontend/apps/web/src/components/page/blocks"
BLOCKS = {
    "accordion": "BlockAccordionGroup.vue",
    "activity": "BlockActivityFeed.vue",
    "alert": "BlockAlertPanel.vue",
    "entry": "BlockEntryGrid.vue",
    "metric": "BlockMetricRow.vue",
    "progress": "BlockProgressSummary.vue",
    "summary": "BlockRecordSummary.vue",
    "table": "BlockRecordTable.vue",
    "todo": "BlockTodoList.vue",
}


def validate(sources: dict[str, str] | None = None) -> list[str]:
    values = sources or {key: (BLOCK_ROOT / name).read_text(encoding="utf-8") for key, name in BLOCKS.items()}
    failures: list[str] = []
    for key, source in values.items():
        if "<ScEmptyState" not in source:
            failures.append(f"dashboard block {key} bypasses governed empty state")
        if 'density="compact"' not in source:
            failures.append(f"dashboard block {key} does not use compact block state density")
        if ':heading-level="5"' not in source:
            failures.append(f"dashboard block {key} does not preserve block heading hierarchy")
    for key in ("alert", "entry", "summary", "todo"):
        source = values[key]
        if "<ScButton" not in source:
            failures.append(f"dashboard block {key} bypasses governed command buttons")
        if "<button" in source:
            failures.append(f"dashboard block {key} retains raw command button")
    for key in ("alert", "entry", "todo"):
        if "@container (max-width: 480px)" not in values[key]:
            failures.append(f"dashboard block {key} lacks compact container adaptation")
    metric = values["metric"]
    for marker in (".metric-item[data-interactive='true']:focus-visible", "prefers-reduced-motion"):
        if marker not in metric:
            failures.append(f"dashboard metric interaction state missing: {marker}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_dashboard_state_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_dashboard_state_guard] PASS blocks=9 formal_gaps=0")

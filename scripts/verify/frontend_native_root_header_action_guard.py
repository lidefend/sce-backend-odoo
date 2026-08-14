#!/usr/bin/env python3
"""Guard native page.root header actions from disappearing in form rendering."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
source = (
    ROOT
    / "frontend/apps/web/src/pages/contractForm/contractHeaderActionPresentation.ts"
).read_text(encoding="utf-8")

required = (
    "action.sourceWidgetId === 'page.header'",
    "action.sourceWidgetId === 'page.root' && action.level === 'header'",
)
missing = [marker for marker in required if marker not in source]
if missing:
    raise SystemExit(
        "[frontend-native-root-header-action] FAIL missing=" + ",".join(missing)
    )
print("[frontend-native-root-header-action] PASS")

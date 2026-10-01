#!/usr/bin/env python3
"""Keep file line budgets in one place, and keep them advisory.

Two regressions this guard exists to stop:

1. A guard freezing its own numeric line budget again.  That is how one file
   ended up watched at twelve different sizes and every small feature turned
   into hand-editing several guards.
2. A line count becoming a blocking failure again.  Size is a direction for
   code optimization; it must not decide whether a functional iteration lands.

Structural assertions (module ownership, split tokens, forbidden dependencies)
stay blocking and are checked by their own guards.
"""
from __future__ import annotations

import re
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_budgets  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
VERIFY_DIR = Path(__file__).resolve().parent
REGISTRY = VERIFY_DIR / "line_budgets.py"
CI = ROOT / "make/ci.mk"

# A script may compare against a numeric line threshold while only *reporting*
# metrics.  It has to opt out explicitly in its own source, so this guard never
# has to keep a hardcoded list of exempt file names.
REPORTING_ONLY_MARKER = "line-threshold-reporting-only"

HARDCODED_BUDGET_RE = re.compile(r"^[A-Z][A-Z0-9_]*_(?:LINES|BUDGET)\s*=\s*\d+\s*$", re.M)
INLINE_THRESHOLD_RE = re.compile(r"\b(?:line_count|line_count\(\)|lines|line\s+count)\s*>\s*\d+\b")
BLOCKING_MESSAGE_RE = re.compile(r"line budget exceeded|exceeds \d+ lines")


def main() -> int:
    errors: list[str] = []

    hardcoded: list[str] = []
    blocking: list[str] = []
    thresholds: list[str] = []
    consumers = 0

    for path in sorted(VERIFY_DIR.glob("*.py")):
        if path.name in {"line_budgets.py", Path(__file__).name}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "line_budgets" in text:
            consumers += 1
        for match in HARDCODED_BUDGET_RE.finditer(text):
            hardcoded.append(f"{path.name}: {match.group(0).strip()}")
        for match in BLOCKING_MESSAGE_RE.finditer(text):
            blocking.append(f"{path.name}: {match.group(0).strip()}")
        if REPORTING_ONLY_MARKER not in text:
            for match in INLINE_THRESHOLD_RE.finditer(text):
                thresholds.append(f"{path.name}: {match.group(0).strip()}")

    if hardcoded:
        errors.append(
            "line budgets must come from scripts/verify/line_budgets.py, not hardcoded: "
            + "; ".join(hardcoded)
        )
    if thresholds:
        errors.append(
            "numeric line thresholds must be registered in line_budgets.py: "
            + "; ".join(thresholds)
        )
    if blocking:
        errors.append(
            "line count must stay advisory and never block a run: " + "; ".join(blocking)
        )
    if consumers < 25:
        errors.append(
            f"too few guards read the shared line budget registry: {consumers} < 25"
        )

    registered = line_budgets.registered()
    if not registered:
        errors.append("line budget registry is empty")
    for relative in sorted(registered):
        if not (ROOT / relative).is_file():
            errors.append(f"registered line budget points at a missing file: {relative}")
    if line_budgets.HEADROOM_LINES <= 0:
        errors.append("line budget headroom must stay positive")

    if "python3 scripts/verify/file_line_budget_uniform_guard.py" not in CI.read_text(
        encoding="utf-8", errors="ignore"
    ):
        errors.append("ci.local.quick must run file_line_budget_uniform_guard.py")

    if errors:
        print("[file_line_budget_uniform_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[file_line_budget_uniform_guard] PASS")
    print(
        f"registered_files={len(registered)} headroom={line_budgets.HEADROOM_LINES} "
        f"consumers={consumers} blocking_line_checks=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

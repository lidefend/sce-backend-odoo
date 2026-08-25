#!/usr/bin/env python3
"""Normalize the runtime systemwide coverage audit into reviewable evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalized(payload: dict) -> dict:
    return {
        key: payload[key]
        for key in (
            "schemaVersion", "status", "formalProductLayer", "primaryCenterAuthority",
            "excludedScopes", "summary", "deliveredReports", "centers", "surfaces", "excluded", "gaps",
        )
    }


def markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Frontend Systemwide Coverage Audit v1",
        "",
        f"- Status: **{payload['status']}**",
        f"- Primary centers: **{summary['primaryCenterCount']}**",
        f"- Runtime menu/action surfaces: **{summary['runtimeSurfaceCount']}**",
        f"- Excluded non-product surfaces: **{summary['excludedSurfaceCount']}**",
        f"- Covered surfaces: **{summary['coveredSurfaceCount']}**",
        f"- Uncovered surfaces: **{summary['uncoveredSurfaceCount']}**",
        f"- Runtime/authority gaps: **{summary['runtimeGapCount']}**",
        "",
        "## Primary-center coverage",
        "",
        "| Center | Runtime | Covered | Uncovered |",
        "|---|---:|---:|---:|",
    ]
    for row in payload["centers"]:
        lines.append(
            f"| {row['center']} | {row['surfaceCount']} | {row['coveredCount']} | {row['uncoveredCount']} |"
        )
    lines.extend(["", "## Uncovered formal runtime surfaces", ""])
    uncovered = [row for row in payload["surfaces"] if row["coverageStatus"] == "uncovered"]
    if not uncovered:
        lines.append("None.")
    else:
        for row in uncovered:
            lines.append(
                f"- `{row['center']}` — `{row['menuXmlid']}` → `{row['actionXmlid']}` "
                f"(`{row['model']}`)"
            )
    lines.extend([
        "",
        "## Boundary",
        "",
        "This report compares the locked ten-center runtime menu/action graph with exact "
        "menu/action identities in delivered domain evidence. Internal system management, "
        "demo addons, and customer overlays are excluded explicitly.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args()
    payload = normalized(json.loads(Path(args.input).read_text(encoding="utf-8")))
    Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.markdown_output).write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": payload["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

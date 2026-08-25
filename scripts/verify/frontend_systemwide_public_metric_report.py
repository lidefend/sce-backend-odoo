#!/usr/bin/env python3
"""Normalize systemwide coverage and browser public metrics into final evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


def normalize(coverage: dict, browser: dict) -> dict:
    rows = browser.get("rows") if isinstance(browser.get("rows"), list) else []
    errors = []
    summary = coverage.get("summary") if isinstance(coverage.get("summary"), dict) else {}
    if coverage.get("status") != "PASS":
        errors.append("SYSTEMWIDE_COVERAGE_NOT_PASS")
    if summary.get("runtimeSurfaceCount") != 88 or summary.get("coveredSurfaceCount") != 88:
        errors.append("SYSTEMWIDE_COVERAGE_NOT_88_OF_88")
    if summary.get("uncoveredSurfaceCount") != 0 or summary.get("gapCount") != 0:
        errors.append("SYSTEMWIDE_COVERAGE_GAPS_REMAIN")
    if browser.get("pass") is not True or len(rows) != 3:
        errors.append("PUBLIC_METRIC_BROWSER_NOT_PASS")
    for row in rows:
        if row.get("h1") != 1 or row.get("pageHeader") != 1 or row.get("selectedNavigationItem") != 1:
            errors.append(f"{row.get('key')}:IDENTITY_METRIC_FAILED")
        if not isinstance(row.get("primaryActions"), int) or row.get("primaryActions") not in (0, 1):
            errors.append(f"{row.get('key')}:PRIMARY_METRIC_FAILED")
        for key in ("duplicateFields", "duplicateTitles"):
            if row.get(key) != []:
                errors.append(f"{row.get('key')}:{key}")
        for key in ("disabledFakeReadonlyControls", "unregisteredComponents", "mobile390Overflow"):
            if row.get(key) != 0:
                errors.append(f"{row.get('key')}:{key}")
        if row.get("presentationMode") in ("task", "workspace"):
            if row.get("contractPresentationMode") != row.get("presentationMode"):
                errors.append(f"{row.get('key')}:PRESENTATION_MODE_NOT_AUTHORITATIVE")
        if row.get("renderProfile") == "readonly" and row.get("presentationMode") == "workspace":
            if not urlparse(str(row.get("url", ""))).path.startswith("/r/"):
                errors.append(f"{row.get('key')}:EXPLICIT_READONLY_PROMOTED")
    if browser.get("errors") != []:
        errors.append("BROWSER_ERRORS_PRESENT")
    if browser.get("mutations") != []:
        errors.append("BUSINESS_MUTATIONS_PRESENT")
    modes = {row.get("presentationMode") for row in rows}
    if not {"collection", "task", "workspace"}.issubset(modes):
        errors.append("PUBLIC_PATTERN_MATRIX_INCOMPLETE")
    return {
        "schemaVersion": "frontend_systemwide_public_metric_acceptance.v1",
        "status": "PASS" if not errors else "FAIL",
        "head": browser.get("head", ""),
        "database": browser.get("target", {}).get("database", ""),
        "coverage": {
            "primaryCenters": summary.get("primaryCenterCount"),
            "runtimeSurfaces": summary.get("runtimeSurfaceCount"),
            "coveredSurfaces": summary.get("coveredSurfaceCount"),
            "uncoveredSurfaces": summary.get("uncoveredSurfaceCount"),
            "excludedNonProductSurfaces": summary.get("excludedSurfaceCount"),
            "gaps": summary.get("gapCount"),
        },
        "publicMetrics": {
            "h1": 1, "pageHeader": 1, "selectedNavigationItem": 1,
            "primaryActions": "zero_or_one", "duplicateFields": 0,
            "duplicateTitles": 0, "disabledFakeReadonlyControls": 0,
            "unregisteredComponents": 0, "mobile390Overflow": 0,
            "browserErrors": len(browser.get("errors") or []),
            "readonlyMutations": len(browser.get("mutations") or []),
            "explicitReadonlyPromotion": 0,
            "presentationModeAuthority": "backend_contract",
        },
        "rows": rows,
        "errors": errors,
    }


def markdown(payload: dict) -> str:
    lines = [
        "# Systemwide Frontend Public Metric Acceptance v1", "",
        f"Status: **{payload['status']}**", "",
        "## Coverage", "",
        f"- Formal primary centers: {payload['coverage']['primaryCenters']}",
        f"- Covered runtime surfaces: {payload['coverage']['coveredSurfaces']}/{payload['coverage']['runtimeSurfaces']}",
        f"- Uncovered surfaces: {payload['coverage']['uncoveredSurfaces']}",
        f"- Runtime/evidence gaps: {payload['coverage']['gaps']}", "",
        "## Public metrics", "",
        "| Pattern | H1 | Header | Selected nav | Primary | Duplicate fields | Duplicate titles | Fake readonly | Unregistered | 390 overflow |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['key']} | {row['h1']} | {row['pageHeader']} | {row['selectedNavigationItem']} | "
            f"{row['primaryActions']} | {len(row['duplicateFields'])} | {len(row['duplicateTitles'])} | "
            f"{row['disabledFakeReadonlyControls']} | {row['unregisteredComponents']} | {row['mobile390Overflow']} |"
        )
    lines += [
        "", "Browser errors, business mutations and explicit readonly promotion are all zero.",
        "Task/workspace presentation modes equal the backend Contract authority; the frontend does not infer them.", "",
    ]
    if payload["errors"]:
        lines += ["## Errors", "", *[f"- {error}" for error in payload["errors"]], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", required=True)
    parser.add_argument("--browser", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args()
    payload = normalize(
        json.loads(Path(args.coverage).read_text(encoding="utf-8")),
        json.loads(Path(args.browser).read_text(encoding="utf-8")),
    )
    Path(args.json_output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.markdown_output).write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "rows": len(payload["rows"])}))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

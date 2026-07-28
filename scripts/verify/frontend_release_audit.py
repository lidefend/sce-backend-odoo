#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


class EvidenceError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"EVIDENCE_INVALID:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"EVIDENCE_NOT_OBJECT:{path}")
    return value


def require_sha(report: dict[str, Any], expected_sha: str, name: str) -> None:
    if str(report.get("git_sha") or "") != expected_sha:
        raise EvidenceError(f"EVIDENCE_SHA_MISMATCH:{name}")


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_navigation(report: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    require_sha(report, expected_sha, "navigation")
    total = report.get("total") or {}
    roles = report.get("roles") or {}
    if total.get("result") != "PASS" or int(total.get("expected_count") or 0) != 70:
        raise EvidenceError("NAVIGATION_NOT_70_OF_70")
    for role, count in {"finance": 42, "project_a_member": 9, "pm": 14, "owner": 5}.items():
        row = roles.get(role) or {}
        if (
            int(row.get("expected_count") or 0) != count
            or int(row.get("actual_count") or 0) != count
            or int(row.get("matched_count") or 0) != count
            or row.get("missing_leaf_keys")
            or row.get("unexpected_leaf_keys")
            or row.get("duplicate_leaf_keys")
        ):
            raise EvidenceError(f"NAVIGATION_ROLE_MISMATCH:{role}")
    return {"result": "PASS", "roles": roles, "total": total}


def validate_accessibility(report: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    require_sha(report, expected_sha, "accessibility")
    if report.get("result") != "PASS":
        raise EvidenceError("ACCESSIBILITY_NOT_PASS")
    if int(report.get("critical") or 0) or int(report.get("serious") or 0):
        raise EvidenceError("ACCESSIBILITY_BLOCKING_VIOLATIONS")
    if not report.get("scans"):
        raise EvidenceError("ACCESSIBILITY_NOT_RUN")
    return {
        "result": "PASS",
        "engine": report.get("engine"),
        "critical": 0,
        "serious": 0,
        "scan_count": len(report["scans"]),
    }


def validate_performance(report: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    require_sha(report, expected_sha, "performance")
    if report.get("result") != "PASS" or not report.get("budget_source"):
        raise EvidenceError("PERFORMANCE_NOT_PASS")
    scenarios = report.get("scenarios") or {}
    budgets = report.get("budgets") or {}
    if set(scenarios) != set(budgets):
        raise EvidenceError("PERFORMANCE_BUDGET_COVERAGE_MISMATCH")
    relative_pass = report.get("relative_budget_pass") is True
    absolute_pass = report.get("absolute_budget_pass") is True
    relative_limit = 10.0
    regressions = report.get("metric_regression_percent") or {}
    if not absolute_pass and not relative_pass:
        raise EvidenceError("PERFORMANCE_BUDGET_NOT_PASS")
    for name, metrics in scenarios.items():
        budget = budgets[name]
        if int(metrics.get("sample_count") or 0) < 5:
            raise EvidenceError(f"PERFORMANCE_SAMPLE_COUNT:{name}")
        for metric in ("median_ms", "p95_ms", "max_ms"):
            within_absolute = float(metrics.get(metric) or 0) <= float(budget.get(metric) or 0)
            within_relative = (
                metric == "median_ms"
                and isinstance((regressions.get(name) or {}).get(metric), (int, float))
                and float((regressions.get(name) or {})[metric]) <= relative_limit
            )
            if not within_absolute and not (relative_pass and within_relative):
                raise EvidenceError(f"PERFORMANCE_BUDGET_EXCEEDED:{name}:{metric}")
    return {
        "result": "PASS",
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "absolute_budget_pass": absolute_pass,
        "relative_budget_pass": relative_pass,
        "relative_baseline_path": report.get("relative_baseline_path"),
    }


def validate_runtime(report: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    require_sha(report, expected_sha, "delivery_hardening")
    runtime = report.get("runtime") or {}
    if report.get("pass") is not True:
        raise EvidenceError("DELIVERY_HARDENING_NOT_PASS")
    failures = {key: runtime.get(key) or [] for key in ("console", "pageerror", "unhandled", "http")}
    if any(failures.values()):
        raise EvidenceError("UNEXPECTED_BROWSER_RUNTIME_ERRORS")
    journeys = report.get("journeys") or {}
    if not journeys or any(value != "PASS" for value in journeys.values()):
        raise EvidenceError("CORE_JOURNEY_NOT_PASS")
    return {"result": "PASS", "journeys": journeys, "unexpected_errors": failures}


def validate_responsive(report: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    require_sha(report, expected_sha, "responsive")
    pages = report.get("pages") or []
    if not pages:
        raise EvidenceError("RESPONSIVE_NOT_RUN")
    if int(report.get("horizontal_overflow") or 0) or any(row.get("pass") is not True for row in pages):
        raise EvidenceError("RESPONSIVE_NOT_PASS")
    return {
        "result": "PASS",
        "viewports": report.get("viewports") or [],
        "page_count": len(pages),
        "horizontal_overflow": 0,
    }


def validate_error_recovery(report: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    require_sha(report, expected_sha, "error_recovery")
    required = ("network_retry", "conflict_refresh", "session_expired")
    if any(report.get(name) != "PASS" for name in required):
        raise EvidenceError("ERROR_RECOVERY_NOT_PASS")
    return {"result": "PASS", "journeys": {name: report[name] for name in required}}


def validate_static(report: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    require_sha(report, expected_sha, "static")
    checks = report.get("checks") or {}
    if report.get("result") != "PASS" or not checks or any(row.get("result") != "PASS" for row in checks.values()):
        raise EvidenceError("FRONTEND_STATIC_GUARDS_NOT_PASS")
    return {"result": "PASS", "checks": checks}


def aggregate(evidence_root: Path, expected_sha: str) -> dict[str, Any]:
    paths = {
        "static": evidence_root / "frontend-release-audit/static.json",
        "navigation": evidence_root / "frontend-page-identity/navigation-report.json",
        "delivery_hardening": evidence_root / "frontend-delivery-hardening/report.json",
        "accessibility": evidence_root / "frontend-delivery-hardening/accessibility.json",
        "performance": evidence_root / "frontend-delivery-hardening/performance.json",
        "responsive": evidence_root / "frontend-delivery-hardening/responsive.json",
        "error_recovery": evidence_root / "frontend-delivery-hardening/error-recovery.json",
    }
    validators = {
        "static": validate_static,
        "navigation": validate_navigation,
        "delivery_hardening": validate_runtime,
        "accessibility": validate_accessibility,
        "performance": validate_performance,
        "responsive": validate_responsive,
        "error_recovery": validate_error_recovery,
    }
    sections: dict[str, Any] = {}
    evidence: dict[str, Any] = {}
    failures: list[str] = []
    missing_evidence: list[str] = []
    for name, validator in validators.items():
        report: dict[str, Any] | None = None
        try:
            report = read_json(paths[name])
            sections[name] = validator(report, expected_sha)
            evidence[name] = {
                "path": str(paths[name].relative_to(ROOT)),
                "git_sha": report.get("git_sha"),
                "sha256": sha256(paths[name]),
            }
        except EvidenceError as exc:
            sections[name] = {"result": "FAIL", "reason": str(exc)}
            if name == "navigation" and report is not None:
                sections[name].update(
                    {
                        "source": report.get("source"),
                        "identity": report.get("identity"),
                        "roles": report.get("roles"),
                        "total": report.get("total"),
                    }
                )
            if str(exc).startswith(("EVIDENCE_INVALID:", "EVIDENCE_NOT_OBJECT:")):
                missing_evidence.append(str(exc))
            failures.append(str(exc))
    return {
        "schema_version": "frontend-release-audit/v2",
        "git_sha": expected_sha,
        "git_tree": git_value("rev-parse", "HEAD^{tree}"),
        "workflow": {
            "name": os.environ.get("GITHUB_WORKFLOW", "local"),
            "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
            "event": os.environ.get("GITHUB_EVENT_NAME", "local"),
            "github_sha": os.environ.get("GITHUB_SHA", expected_sha),
            "checkout_sha": expected_sha,
            "pr_head_sha": os.environ.get("FRONTEND_RELEASE_PR_HEAD_SHA", ""),
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "result": "FAIL" if failures else "PASS",
        "summary_exit_code": 2 if failures else 0,
        "blocking_failures": failures,
        "missing_evidence": missing_evidence,
        "required_sections": sorted(validators),
        "evidence": evidence,
        "sections": sections,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", default="artifacts")
    parser.add_argument("--output", default="artifacts/frontend-release-audit/report.json")
    parser.add_argument("--sha", default="")
    args = parser.parse_args()
    expected_sha = args.sha or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    try:
        report = aggregate(ROOT / args.evidence_root, expected_sha)
    except EvidenceError as exc:
        report = {
            "schema_version": "frontend-release-audit/v2",
            "git_sha": expected_sha,
            "git_tree": git_value("rev-parse", "HEAD^{tree}"),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "result": "FAIL",
            "blocking_failures": [str(exc)],
            "missing_evidence": [str(exc)],
            "sections": {},
        }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[frontend_release_audit] {report['result']} evidence={output.relative_to(ROOT)}")
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

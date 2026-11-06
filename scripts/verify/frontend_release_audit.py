#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from frontend_release_navigation_policy_guard import compare_role_projection

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


def authoritative_navigation_counts() -> dict[str, int]:
    policy = read_json(ROOT / "config/frontend/authoritative_navigation.json")
    configured_roles = policy.get("roles") or {}
    counts: dict[str, int] = {}
    for role, row in configured_roles.items():
        policy_leaf_keys = (row or {}).get("leaf_keys") or []
        policy_count = int((row or {}).get("expected_count") or 0)
        leaf_keys = (row or {}).get("browser_leaf_keys") or policy_leaf_keys
        count = int((row or {}).get("browser_expected_count") or 0)
        if policy_count <= 0 or policy_count != len(policy_leaf_keys):
            raise EvidenceError(f"AUTHORITATIVE_NAVIGATION_POLICY_INVALID:{role}")
        if count <= 0 or count != len(leaf_keys):
            raise EvidenceError(f"AUTHORITATIVE_BROWSER_NAVIGATION_POLICY_INVALID:{role}")
        if not set(leaf_keys).issubset(set(policy_leaf_keys)):
            raise EvidenceError(f"AUTHORITATIVE_BROWSER_NAVIGATION_NOT_POLICY_SUBSET:{role}")
        counts[str(role)] = count
    if not counts:
        raise EvidenceError("AUTHORITATIVE_NAVIGATION_POLICY_EMPTY")
    return counts


def validate_navigation(report: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    require_sha(report, expected_sha, "navigation")
    total = report.get("total") or {}
    roles = report.get("roles") or {}
    expected_roles = authoritative_navigation_counts()
    expected_total = sum(expected_roles.values())
    if (
        total.get("result") != "PASS"
        or int(total.get("expected_count") or 0) != expected_total
        or int(total.get("actual_count") or 0) != expected_total
        or int(total.get("matched_count") or 0) != expected_total
    ):
        raise EvidenceError("NAVIGATION_NOT_AUTHORITATIVE_TOTAL")
    if set(roles) != set(expected_roles):
        raise EvidenceError("NAVIGATION_ROLE_SET_MISMATCH")
    for role, count in expected_roles.items():
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


ROLE_RELEASE_SUBJECTS = {
    "finance": ("fixture_role_finance", "finance"),
    "project_a_member": ("fixture_role_project_a_member", "project_member"),
    "pm": ("fixture_role_pm", "pm"),
    "owner": ("fixture_role_owner", "owner"),
}


def _projection_problem_summary(problem: dict[str, Any]) -> dict[str, Any]:
    if problem.get("reason") in ("subject_identity_mismatch", "collect_error"):
        return problem
    return {
        "expected_count": problem.get("expected_count"),
        "actual_count": problem.get("actual_count"),
        "missing_count": len(problem.get("missing") or []),
        "unexpected_count": len(problem.get("unexpected") or []),
        "missing_sample": (problem.get("missing") or [])[:8],
        "unexpected_sample": (problem.get("unexpected") or [])[:8],
        "duplicate_identities": problem.get("actual_duplicates")
        or problem.get("expected_duplicates"),
        "invalid_identities": problem.get("invalid_identities"),
    }


def validate_role_release_projection(report: dict[str, Any], expected_sha: str) -> dict[str, Any]:
    """Recompute the per-role published projection from the raw identity list.

    The collector gathers identities and never prints PASS. This validator binds
    the evidence to the expected database, subjects and role codes, then
    re-derives missing/unexpected for every role instead of failing fast on the
    first difference. A report whose scope is not yet VERIFIED fails with
    ``ROLE_RELEASE_PROJECTION_SCOPE_MISMATCH`` and keeps all per-role diagnostics;
    only a VERIFIED scope is held to the hard identity equality.
    """
    require_sha(report, expected_sha, "role_release_projection")
    expected_run_id = os.environ.get("GITHUB_RUN_ID", "local")
    expected_run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    if str(report.get("run_id") or "") != expected_run_id:
        raise EvidenceError("ROLE_RELEASE_PROJECTION_RUN_ID_MISMATCH")
    if str(report.get("run_attempt") or "") != expected_run_attempt:
        raise EvidenceError("ROLE_RELEASE_PROJECTION_RUN_ATTEMPT_MISMATCH")
    snapshot = report.get("release_snapshot") or {}
    if str(snapshot.get("source_revision") or "") != expected_sha:
        raise EvidenceError("ROLE_RELEASE_PROJECTION_SNAPSHOT_MISMATCH")
    if str(report.get("db") or "") != "sc_frontend_acceptance":
        raise EvidenceError("ROLE_RELEASE_PROJECTION_DB_MISMATCH")
    manifest = read_json(ROOT / "config/frontend/authoritative_navigation.json")
    declared_roles = set((manifest.get("roles") or {}).keys())
    actual_roles = report.get("roles") or {}
    if set(actual_roles) != declared_roles:
        raise EvidenceError("ROLE_RELEASE_PROJECTION_ROLE_SET_MISMATCH")
    scope_status = str(report.get("scope_status") or "NOT_VERIFIED")
    sections: dict[str, Any] = {}
    problems: dict[str, Any] = {}
    for role in sorted(declared_roles):
        row = actual_roles.get(role) or {}
        expected_login, expected_role_code = ROLE_RELEASE_SUBJECTS[role]
        if row.get("login") != expected_login or row.get("role_code") != expected_role_code:
            problems[role] = {
                "reason": "subject_identity_mismatch",
                "expected": {"login": expected_login, "role_code": expected_role_code},
                "actual": {"login": row.get("login"), "role_code": row.get("role_code")},
            }
            sections[role] = {"result": "FAIL", "reason": "subject_identity_mismatch"}
            continue
        p0 = row.get("p0") or {}
        if p0.get("error"):
            problems[role] = {"reason": "collect_error", "error": p0["error"]}
            sections[role] = {"result": "FAIL", "reason": "collect_error"}
            continue
        identities = p0.get("primary_home_identities") or []
        comparison = compare_role_projection(
            (manifest["roles"][role].get("leaf_keys") or []), identities
        )
        sections[role] = comparison
        if not comparison["consistent"]:
            problems[role] = comparison
    identity_problems = {
        role: problem
        for role, problem in problems.items()
        if problem.get("reason") in ("subject_identity_mismatch", "collect_error")
    }
    scope_problems = {
        role: problem for role, problem in problems.items() if role not in identity_problems
    }
    summary = {
        role: _projection_problem_summary(problems.get(role, {}))
        for role in sorted(declared_roles)
    }
    if identity_problems:
        error = EvidenceError(
            "ROLE_RELEASE_PROJECTION_IDENTITY_MISMATCH:"
            + json.dumps(summary, ensure_ascii=False)
        )
        error.role_sections = sections
        raise error
    if scope_status != "VERIFIED":
        error = EvidenceError(
            "ROLE_RELEASE_PROJECTION_SCOPE_MISMATCH:"
            + json.dumps(summary, ensure_ascii=False)
        )
        error.role_sections = sections
        raise error
    if scope_problems:
        error = EvidenceError(
            "ROLE_RELEASE_PROJECTION_IDENTITY_MISMATCH:"
            + json.dumps(summary, ensure_ascii=False)
        )
        error.role_sections = sections
        raise error
    return {"result": "PASS", "roles": sections, "scope_status": scope_status}


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
    policy = read_json(ROOT / "config/frontend/release_performance_budgets_v1.json")
    if budgets != policy.get("scenarios"):
        raise EvidenceError("PERFORMANCE_BUDGET_AUTHORITY_MISMATCH")
    if set(scenarios) != set(budgets):
        raise EvidenceError("PERFORMANCE_BUDGET_COVERAGE_MISMATCH")
    relative_pass = report.get("relative_budget_pass") is True
    absolute_pass = report.get("absolute_budget_pass") is True
    if not absolute_pass:
        raise EvidenceError("PERFORMANCE_BUDGET_NOT_PASS")
    for name, metrics in scenarios.items():
        budget = budgets[name]
        samples = metrics.get("samples_ms")
        if (not isinstance(samples, list) or len(samples) < int(policy["minimum_sample_count"])
                or metrics.get("sample_count") != len(samples)):
            raise EvidenceError(f"PERFORMANCE_SAMPLE_COUNT:{name}")
        if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in samples):
            raise EvidenceError(f"PERFORMANCE_SAMPLE_INVALID:{name}")
        ordered = sorted(samples)
        observed = {"median_ms": ordered[len(ordered) // 2],
                    "p95_ms": ordered[math.ceil(len(ordered) * .95) - 1], "max_ms": ordered[-1]}
        if any(type(metrics.get(key)) not in (int, float) or metrics[key] != value for key, value in observed.items()):
            raise EvidenceError(f"PERFORMANCE_SUMMARY_MISMATCH:{name}")
        for metric in ("median_ms", "p95_ms", "max_ms"):
            within_absolute = float(metrics.get(metric) or 0) <= float(budget.get(metric) or 0)
            if not within_absolute:
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
        "role_release_projection": evidence_root / "frontend-release-audit/role-release-projection.json",
        "delivery_hardening": evidence_root / "frontend-delivery-hardening/report.json",
        "accessibility": evidence_root / "frontend-delivery-hardening/accessibility.json",
        "performance": evidence_root / "frontend-delivery-hardening/performance.json",
        "responsive": evidence_root / "frontend-delivery-hardening/responsive.json",
        "error_recovery": evidence_root / "frontend-delivery-hardening/error-recovery.json",
    }
    validators = {
        "static": validate_static,
        "navigation": validate_navigation,
        "role_release_projection": validate_role_release_projection,
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
            if name == "role_release_projection" and getattr(exc, "role_sections", None):
                sections[name]["roles"] = exc.role_sections
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

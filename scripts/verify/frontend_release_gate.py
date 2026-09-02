#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ci/frontend_release_gate_v1.json"
EXPECTED_SCHEMA = "frontend-release-audit/v2"
VALID_EVENTS = {"pull_request", "push", "schedule", "workflow_dispatch", "local"}
FAILED_OUTCOMES = {"failure", "cancelled", "skipped", "not_run", "NOT_RUN"}


class GateError(ValueError):
    pass


def fail(reason: str) -> None:
    raise GateError(reason)


def load_object(path: Path, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail(reason)
    if not isinstance(value, dict):
        fail(reason)
    return value


def validate(
    reports: list[Path],
    *,
    expected_sha: str,
    expected_tree: str,
    command_outcome: str,
    expected_event: str,
    expected_run_id: str,
    expected_run_attempt: str,
) -> dict[str, Any]:
    policy = load_object(POLICY, "POLICY_INVALID")
    if len(reports) != 1:
        fail("REPORT_MISSING" if not reports else "DUPLICATE_REPORT")
    if command_outcome.lower() in FAILED_OUTCOMES or command_outcome.lower() != "success":
        fail(f"AUTHORITATIVE_COMMAND_{command_outcome.upper()}")
    report = load_object(reports[0], "REPORT_INVALID")
    if report.get("schema_version") != EXPECTED_SCHEMA:
        fail("REPORT_SCHEMA_MISMATCH")
    if report.get("git_sha") != expected_sha:
        fail("REPORT_SHA_MISMATCH")
    if report.get("git_tree") != expected_tree:
        fail("REPORT_TREE_MISMATCH")
    if report.get("result") != "PASS" or report.get("blocking_failures"):
        fail("RELEASE_AUDIT_NOT_PASS")
    if int(report.get("summary_exit_code", -1)) != 0:
        fail("RELEASE_AUDIT_EXIT_CODE_INVALID")
    workflow = report.get("workflow") or {}
    if expected_event not in VALID_EVENTS or workflow.get("event") != expected_event:
        fail("WORKFLOW_EVENT_MISMATCH")
    if str(workflow.get("run_id")) != expected_run_id:
        fail("WORKFLOW_RUN_MISMATCH")
    if str(workflow.get("run_attempt")) != expected_run_attempt:
        fail("WORKFLOW_ATTEMPT_MISMATCH")
    if workflow.get("checkout_sha") != expected_sha:
        fail("CHECKOUT_SHA_MISMATCH")
    required = set(policy["required_sections"])
    if set(report.get("required_sections") or []) != required:
        fail("REQUIRED_SECTION_MANIFEST_MISMATCH")
    sections = report.get("sections") or {}
    evidence = report.get("evidence") or {}
    if set(sections) != required or set(evidence) != required:
        fail("REQUIRED_EVIDENCE_MISSING")
    for name in sorted(required):
        if (sections.get(name) or {}).get("result") != "PASS":
            fail(f"SECTION_{name.upper()}_NOT_PASS")
        if (evidence.get(name) or {}).get("git_sha") != expected_sha:
            fail(f"EVIDENCE_{name.upper()}_SHA_MISMATCH")
        if not (evidence.get(name) or {}).get("sha256"):
            fail(f"EVIDENCE_{name.upper()}_DIGEST_MISSING")
    return {
        "schema_version": "frontend-release-gate-result/v1",
        "result": "PASS",
        "reason_codes": [],
        "git_sha": expected_sha,
        "git_tree": expected_tree,
        "event": expected_event,
        "run_id": expected_run_id,
        "run_attempt": expected_run_attempt,
        "authoritative_command": policy["authoritative_command"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="append", default=[])
    parser.add_argument("--sha", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--command-outcome", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--output", default="artifacts/frontend-release-audit/gate-result.json")
    args = parser.parse_args()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = validate(
            [ROOT / item for item in args.report],
            expected_sha=args.sha,
            expected_tree=args.tree,
            command_outcome=args.command_outcome,
            expected_event=args.event,
            expected_run_id=args.run_id,
            expected_run_attempt=args.run_attempt,
        )
        status = 0
    except GateError as exc:
        result = {
            "schema_version": "frontend-release-gate-result/v1",
            "result": "FAIL",
            "reason_codes": [str(exc)],
            "git_sha": args.sha,
            "git_tree": args.tree,
        }
        status = 2
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"[frontend_release_gate] {result['result']} reasons={','.join(result['reason_codes']) or 'none'}")
    return status


if __name__ == "__main__":
    sys.exit(main())

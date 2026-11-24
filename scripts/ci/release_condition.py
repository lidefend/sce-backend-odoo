#!/usr/bin/env python3
"""Materialize one exact-head formal release condition from required CI runs."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.ci.scheduled_validation import scheduled_slot
    from scripts.ci.select_authoritative_workflow_run import resolve_producer_identity
except ModuleNotFoundError:
    from scheduled_validation import scheduled_slot
    from select_authoritative_workflow_run import resolve_producer_identity


REQUIRED_WORKFLOWS = {
    ".github/workflows/public_guard.yml",
    ".github/workflows/professional_quality_gate.yml",
    ".github/workflows/frontend_release_gate.yml",
    ".github/workflows/merge_policy_gate.yml",
}


def _full_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError(f"{name} must be a full lowercase SHA")
    return value


def load_runs(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid run JSON at line {line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"run at line {line_number} must be an object")
        rows.append(row)
    return rows


def build_condition(
    runs: list[dict[str, Any]],
    *,
    repository: str,
    head_sha: str,
    tree: str,
    event: str,
    head_branch: str,
    workflow_dispatch_producer: str,
    schedule_slot: str | None,
    current_main: str | None = None,
) -> dict[str, Any]:
    head_sha = _full_sha(head_sha, "head")
    tree = _full_sha(tree, "tree")
    producer_event, head_branch = resolve_producer_identity(
        event,
        head_branch,
        workflow_dispatch_producer=workflow_dispatch_producer,
    )
    if event in {"schedule", "workflow_dispatch"}:
        if current_main is None:
            raise ValueError("mainline condition requires the current remote main")
        current_main = _full_sha(current_main, "current main")
        if current_main != head_sha:
            raise ValueError(
                f"stale main: validated head {head_sha} is not current main {current_main}"
            )
    elif current_main is not None:
        raise ValueError("pull request conditions do not accept a current main")
    by_workflow: dict[str, dict[str, Any]] = {}
    for run in runs:
        path = str(run.get("path") or "")
        if path not in REQUIRED_WORKFLOWS:
            raise ValueError(f"unexpected workflow: {path}")
        if path in by_workflow:
            raise ValueError(f"duplicate workflow: {path}")
        if (run.get("repository") or {}).get("full_name") != repository:
            raise ValueError(f"repository mismatch: {path}")
        if (run.get("head_repository") or {}).get("full_name") != repository:
            raise ValueError(f"head repository mismatch: {path}")
        if run.get("head_sha") != head_sha:
            raise ValueError(f"head mismatch: {path}")
        if run.get("event") != producer_event:
            raise ValueError(f"event mismatch: {path}")
        if run.get("head_branch") != head_branch:
            raise ValueError(f"branch mismatch: {path}")
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            raise ValueError(f"workflow is not successful: {path}")
        if type(run.get("id")) is not int or run["id"] <= 0:
            raise ValueError(f"invalid run id: {path}")
        if type(run.get("run_attempt")) is not int or run["run_attempt"] <= 0:
            raise ValueError(f"invalid run attempt: {path}")
        if producer_event == "schedule":
            if not schedule_slot:
                raise ValueError("scheduled condition requires the observed slot")
            try:
                observed_slot = scheduled_slot(str(run.get("created_at") or ""))
            except ValueError as exc:
                raise ValueError(f"invalid scheduled timestamp: {path}") from exc
            if observed_slot != schedule_slot:
                raise ValueError(f"scheduled slot mismatch: {path}")
        by_workflow[path] = run
    missing = REQUIRED_WORKFLOWS - set(by_workflow)
    if missing:
        raise ValueError("missing workflows: " + ", ".join(sorted(missing)))
    kind = {
        "schedule": "scheduled_mainline",
        "pull_request": "explicit_candidate",
        "workflow_dispatch": "operator_full_audit",
    }.get(event)
    if kind is None:
        raise ValueError(f"unsupported event: {event}")
    return {
        "schema_version": "sce.release_condition.v1",
        "status": "SATISFIED",
        "kind": kind,
        "repository": repository,
        "exact_head": head_sha,
        "exact_tree": tree,
        "current_main": current_main,
        "current_main_verified": current_main == head_sha,
        "event": event,
        "producer_event": producer_event,
        "head_branch": head_branch,
        "scheduled_slot_utc": schedule_slot,
        "required_workflows": [
            {
                "workflow": path,
                "run_id": row["id"],
                "run_attempt": row["run_attempt"],
                "event": row["event"],
                "head_sha": row["head_sha"],
                "conclusion": row["conclusion"],
            }
            for path, row in sorted(by_workflow.items())
        ],
        "candidate_build_eligible": True,
        "deployment_ready": False,
        "deployment_requires": [
            "immutable_candidate_build",
            "publication_approval",
            "deployment_approval",
            "runtime_readback",
            "rollback_readiness",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--head-branch", required=True)
    parser.add_argument(
        "--workflow-dispatch-producer",
        choices=["push", "workflow_dispatch"],
        default="push",
    )
    parser.add_argument("--current-main")
    parser.add_argument("--scheduled-slot")
    args = parser.parse_args()
    try:
        result = build_condition(
            load_runs(args.runs),
            repository=args.repository,
            head_sha=args.head_sha,
            tree=args.tree,
            event=args.event,
            head_branch=args.head_branch,
            workflow_dispatch_producer=args.workflow_dispatch_producer,
            schedule_slot=args.scheduled_slot,
            current_main=args.current_main,
        )
    except (OSError, ValueError) as exc:
        print(f"[release-condition] DENY: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"[release-condition] PASS kind={result['kind']} "
        f"head={result['exact_head']} tree={result['exact_tree']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

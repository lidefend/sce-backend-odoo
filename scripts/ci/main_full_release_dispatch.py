#!/usr/bin/env python3
"""Dispatch and verify one exact-main operator full-release audit."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

try:
    from scripts.ci.main_full_release_evidence import verify_evidence
except ModuleNotFoundError:
    from main_full_release_evidence import verify_evidence


ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "lidefend/sce-backend-odoo"
EVENT = "workflow_dispatch"
BRANCH = "main"
SCHEMA = "sce.main-full-release-dispatch.v1"
WORKFLOWS = (
    "public_guard.yml",
    "professional_quality_gate.yml",
    "frontend_release_gate.yml",
    "merge_policy_gate.yml",
    "auxiliary_backend_suite.yml",
    "release_candidate_gate.yml",
)
RUN_FIELDS = (
    "databaseId,headSha,headBranch,event,status,conclusion,url,"
    "workflowName,attempt"
)
RUN_VIEW_FIELDS = (
    "databaseId,headSha,headBranch,event,status,conclusion,url,"
    "workflowName,attempt"
)


def full_sha(value: str, field: str = "commit") -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError(f"{field} must be a full lowercase SHA")
    return value


def run_command(args: list[str], *, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(f"command failed: {' '.join(args)}: {detail}")
    return result.stdout


def json_command(args: list[str]) -> object:
    text = run_command(args).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"command returned invalid JSON: {' '.join(args)}") from exc


def assert_repository(expected_repository: str) -> None:
    if expected_repository != REPOSITORY:
        raise ValueError(f"repository must be {REPOSITORY}")
    actual = run_command(
        ["gh", "repo", "view", REPOSITORY, "--json", "nameWithOwner",
         "--jq", ".nameWithOwner"]
    ).strip()
    if actual != REPOSITORY:
        raise ValueError(f"unexpected GitHub repository: {actual}")


def assert_clean_worktree() -> None:
    if run_command(["git", "status", "--porcelain=v1", "--untracked-files=all"]).strip():
        raise ValueError("worktree must be clean")


def assert_remote_main(expected_main: str) -> None:
    lines = run_command(
        ["git", "ls-remote", "origin", "refs/heads/main"]
    ).splitlines()
    if len(lines) != 1:
        raise ValueError("unable to resolve authoritative origin/main")
    fields = lines[0].split()
    if len(fields) != 2 or fields[1] != "refs/heads/main":
        raise ValueError("unexpected origin/main ref response")
    if fields[0] != expected_main:
        raise ValueError(
            f"origin/main {fields[0]} does not match expected main {expected_main}"
        )


def expected_tree(expected_main: str) -> str:
    result = subprocess.run(
        ["git", "cat-file", "-e", expected_main + "^{commit}"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        run_command(["git", "fetch", "--no-tags", "origin", expected_main])
    return full_sha(
        run_command(["git", "rev-parse", expected_main + "^{tree}"]).strip(),
        "tree",
    )


def list_runs(workflow: str, expected_main: str) -> list[dict]:
    value = json_command(
        [
            "gh", "run", "list",
            "--repo", REPOSITORY,
            "--workflow", workflow,
            "--branch", BRANCH,
            "--event", EVENT,
            "--commit", expected_main,
            "--limit", "100",
            "--json", RUN_FIELDS,
        ]
    )
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"invalid run list for {workflow}")
    return value


def normalize_run(row: dict, workflow: str, expected_main: str) -> dict:
    required = {
        "databaseId", "headSha", "headBranch", "event", "status", "conclusion",
        "url", "workflowName", "attempt",
    }
    if set(row) != required:
        raise ValueError(f"unexpected run fields for {workflow}")
    if (
        type(row["databaseId"]) is not int
        or row["databaseId"] <= 0
        or type(row["attempt"]) is not int
        or row["attempt"] <= 0
        or row["headSha"] != expected_main
        or row["headBranch"] != BRANCH
        or row["event"] != EVENT
        or row["status"] not in {"queued", "in_progress", "completed", "waiting", "pending"}
        or row["conclusion"] not in {"", "success", "failure", "cancelled", "timed_out", "skipped", "neutral"}
        or not isinstance(row["url"], str)
        or row["url"] != f"https://github.com/{REPOSITORY}/actions/runs/{row['databaseId']}"
        or not isinstance(row["workflowName"], str)
        or not row["workflowName"]
    ):
        raise ValueError(f"run identity mismatch for {workflow}")
    return {
        "workflow": workflow,
        "run_id": row["databaseId"],
        "attempt": row["attempt"],
        "workflow_name": row["workflowName"],
        "head_sha": row["headSha"],
        "head_branch": row["headBranch"],
        "event": row["event"],
        "status": row["status"],
        "conclusion": row["conclusion"],
        "url": row["url"],
    }


def assert_unique_run_ids(runs: dict[str, dict]) -> None:
    run_ids = [row["run_id"] for row in runs.values()]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("workflow dispatch manifest contains duplicate run IDs")


def find_new_runs(
    before_ids: dict[str, set[int]],
    expected_main: str,
    *,
    timeout_seconds: int,
    poll_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, dict]:
    if timeout_seconds < 1 or poll_seconds <= 0:
        raise ValueError("dispatch discovery timing must be positive")
    deadline = monotonic() + timeout_seconds
    pending = set(WORKFLOWS)
    found: dict[str, dict] = {}
    while pending:
        for workflow in sorted(pending):
            rows = [
                row for row in list_runs(workflow, expected_main)
                if row.get("databaseId") not in before_ids[workflow]
            ]
            if not rows:
                continue
            if len(rows) != 1:
                raise ValueError(f"ambiguous new runs for {workflow}: {len(rows)}")
            found[workflow] = normalize_run(rows[0], workflow, expected_main)
            pending.remove(workflow)
        if not pending:
            break
        if monotonic() >= deadline:
            raise ValueError(
                "timed out discovering exact-head workflow_dispatch runs: "
                + ", ".join(sorted(pending))
            )
        sleep(poll_seconds)
    return {workflow: found[workflow] for workflow in WORKFLOWS}


def write_manifest(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(document, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=path.name + ".",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        stream.write(serialized)
    temporary.replace(path)


def dispatch_full(
    *,
    expected_main: str,
    repository: str,
    manifest: Path,
    discovery_seconds: int = 180,
    poll_seconds: float = 10,
) -> dict:
    expected_main = full_sha(expected_main, "expected main")
    assert_repository(repository)
    assert_clean_worktree()
    assert_remote_main(expected_main)
    tree = expected_tree(expected_main)
    before_ids = {
        workflow: {
            row["databaseId"] for row in list_runs(workflow, expected_main)
            if type(row.get("databaseId")) is int
        }
        for workflow in WORKFLOWS
    }
    dispatched_at = datetime.now(timezone.utc).isoformat()
    for workflow in WORKFLOWS:
        run_command(
            [
                "gh", "workflow", "run", workflow,
                "--repo", REPOSITORY,
                "--ref", BRANCH,
            ]
        )
    runs = find_new_runs(
        before_ids,
        expected_main,
        timeout_seconds=discovery_seconds,
        poll_seconds=poll_seconds,
    )
    assert_unique_run_ids(runs)
    document = {
        "schema_version": SCHEMA,
        "repository": REPOSITORY,
        "expected_main": expected_main,
        "expected_tree": tree,
        "event": EVENT,
        "head_branch": BRANCH,
        "release_condition_kind": "operator_full_audit",
        "dispatched_at": dispatched_at,
        "workflows": [runs[workflow] for workflow in WORKFLOWS],
    }
    write_manifest(manifest, document)
    return document


def load_manifest(path: Path, expected_main: str) -> dict:
    expected_main = full_sha(expected_main, "expected main")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable dispatch manifest: {path}") from exc
    required = {
        "schema_version", "repository", "expected_main", "expected_tree", "event",
        "head_branch", "release_condition_kind", "dispatched_at", "workflows",
    }
    optional = {"verified_at", "status", "qualification_evidence"}
    if (
        not isinstance(document, dict)
        or not required <= set(document)
        or set(document) - required - optional
        or document["schema_version"] != SCHEMA
        or document["repository"] != REPOSITORY
        or document["expected_main"] != expected_main
        or document["event"] != EVENT
        or document["head_branch"] != BRANCH
        or document["release_condition_kind"] != "operator_full_audit"
        or document.get("status", "PASS") != "PASS"
        or full_sha(document["expected_tree"], "tree") != document["expected_tree"]
        or not isinstance(document["workflows"], list)
        or len(document["workflows"]) != len(WORKFLOWS)
    ):
        raise ValueError("dispatch manifest identity mismatch")
    by_workflow: dict[str, dict] = {}
    for row in document["workflows"]:
        if not isinstance(row, dict) or row.get("workflow") not in WORKFLOWS:
            raise ValueError("dispatch manifest has an invalid workflow row")
        workflow = row["workflow"]
        if workflow in by_workflow:
            raise ValueError(f"dispatch manifest duplicates {workflow}")
        normalized = normalize_run(
            {
                "databaseId": row.get("run_id"),
                "attempt": row.get("attempt"),
                "headSha": row.get("head_sha"),
                "headBranch": row.get("head_branch"),
                "event": row.get("event"),
                "status": row.get("status"),
                "conclusion": row.get("conclusion"),
                "url": row.get("url"),
                "workflowName": row.get("workflow_name"),
            },
            workflow,
            expected_main,
        )
        by_workflow[workflow] = normalized
    if set(by_workflow) != set(WORKFLOWS):
        raise ValueError("dispatch manifest does not cover every workflow")
    assert_unique_run_ids(by_workflow)
    document["workflows"] = [by_workflow[workflow] for workflow in WORKFLOWS]
    return document


def run_view(run_id: int) -> dict:
    value = json_command(
        [
            "gh", "run", "view", str(run_id),
            "--repo", REPOSITORY,
            "--json", RUN_VIEW_FIELDS,
        ]
    )
    if not isinstance(value, dict):
        raise ValueError(f"invalid run view: {run_id}")
    return value


def verify_full(
    *,
    expected_main: str,
    repository: str,
    manifest: Path,
    wait_seconds: int = 0,
    poll_seconds: float = 10,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict:
    expected_main = full_sha(expected_main, "expected main")
    assert_repository(repository)
    assert_remote_main(expected_main)
    document = load_manifest(manifest, expected_main)
    if document["expected_tree"] != expected_tree(expected_main):
        raise ValueError("manifest tree differs from exact commit tree")
    deadline = monotonic() + wait_seconds
    rows = {row["workflow"]: row for row in document["workflows"]}
    observed: set[str] = set()
    while True:
        pending = False
        for workflow in WORKFLOWS:
            expected = rows[workflow]
            if expected["status"] == "completed" and workflow in observed:
                continue
            actual = normalize_run(run_view(expected["run_id"]), workflow, expected_main)
            observed.add(workflow)
            if (
                actual["attempt"] != expected["attempt"]
                or actual["url"] != expected["url"]
            ):
                raise ValueError(f"run identity drifted for {workflow}")
            rows[workflow] = actual
            if actual["status"] != "completed":
                pending = True
        matrix = [{"workflow": workflow, "run_id": row["run_id"],
                   "attempt": row["attempt"], "status": row["status"],
                   "conclusion": row["conclusion"]} for workflow, row in rows.items()]
        failed = [row for row in matrix if row["status"] == "completed" and row["conclusion"] != "success"]
        print("[main-full-release] MATRIX " + json.dumps(matrix, sort_keys=True), flush=True)
        if failed:
            raise ValueError("full-release audit did not succeed: " + ", ".join(
                row["workflow"] + "=" + row["conclusion"] for row in failed))
        if not pending:
            break
        if monotonic() >= deadline:
            raise ValueError("full-release audit is still pending")
        sleep(poll_seconds)
    failed = {
        workflow: row["conclusion"]
        for workflow, row in rows.items()
        if row["conclusion"] != "success"
    }
    if failed:
        raise ValueError(
            "full-release audit did not succeed: "
            + ", ".join(f"{workflow}={result}" for workflow, result in sorted(failed.items()))
        )
    document["workflows"] = [rows[workflow] for workflow in WORKFLOWS]
    document["qualification_evidence"] = verify_evidence(document)
    assert_remote_main(expected_main)
    document["verified_at"] = datetime.now(timezone.utc).isoformat()
    document["status"] = "PASS"
    write_manifest(manifest, document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("dispatch", "verify"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--repository", default=REPOSITORY)
        sub.add_argument("--expected-main", required=True)
        sub.add_argument("--manifest", type=Path, required=True)
        sub.add_argument("--poll-seconds", type=float, default=10)
        if name == "dispatch":
            sub.add_argument("--discovery-seconds", type=int, default=180)
        else:
            sub.add_argument("--wait-seconds", type=int, default=0)
    args = parser.parse_args()
    try:
        if args.command == "dispatch":
            result = dispatch_full(
                expected_main=args.expected_main,
                repository=args.repository,
                manifest=args.manifest,
                discovery_seconds=args.discovery_seconds,
                poll_seconds=args.poll_seconds,
            )
            print(
                f"[main-full-release] DISPATCHED main={result['expected_main']} "
                f"tree={result['expected_tree']} manifest={args.manifest}"
            )
        else:
            result = verify_full(
                expected_main=args.expected_main,
                repository=args.repository,
                manifest=args.manifest,
                wait_seconds=args.wait_seconds,
                poll_seconds=args.poll_seconds,
            )
            print(
                f"[main-full-release] PASS main={result['expected_main']} "
                f"kind={result['release_condition_kind']}"
            )
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"[main-full-release] DENY: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

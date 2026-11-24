#!/usr/bin/env python3
"""Close all exact-head backend responsibility lanes through one receipt.

The required PR professional gate already owns a product backend run. This tool
reuses that execution when its frozen plan is full, dispatches only missing demo
and acceptance work, verifies every run and plan against one exact identity, and
writes a receipt that merge preflight can verify live.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import backend_impact_plan as impact
import backend_suite_plan as planner

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "lidefend/sce-backend-odoo"
SUITES = ("product", "demo", "acceptance")
BACKEND_WORKFLOW = "backend_test_suite.yml"
PROFESSIONAL_WORKFLOW = "professional_quality_gate.yml"
SCHEMA = "backend-iteration-lanes/v1"
DEFAULT_RECEIPT_ROOT = ROOT / ".runtime/backend-iteration"
RUN_NAME_PREFIX = "backend_test_suite"
CLOSURE_PATHS = {
    ".github/workflows/backend_test_suite.yml",
    ".github/workflows/auxiliary_backend_suite.yml",
    "make/ci.mk",
    "scripts/ci/backend_iteration_lanes.py",
    "scripts/ci/self_hosted_runner_cleanup.sh",
    "scripts/ci/test_backend_iteration_lanes.py",
    "scripts/ci/test_backend_test_suite_dispatch_contract.py",
    "scripts/test/dependency_baseline.py",
    "scripts/test/test.sh",
}
CLOSURE_PREFIXES = (
    ".github/workflows/backend_",
    "scripts/ci/backend_",
    "scripts/ci/test_backend_",
)


class LaneError(RuntimeError):
    """An exact-head lane identity or result is invalid."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def exact_sha(value: str, label: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value or ""):
        raise LaneError(f"{label} must be a full lowercase commit SHA")
    return value


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise LaneError(result.stderr.strip() or "git command failed")
    return result.stdout.rstrip("\n")


def direct_run_title(suite: str, head: str) -> str:
    return f"{RUN_NAME_PREFIX} ({suite}) {head}"


def flatten_plan_modules(plan: dict) -> list[str]:
    return [
        module
        for shard in plan.get("shards", [])
        for module in shard.get("modules", [])
    ]


def expected_suite_modules(head: str, suite: str) -> list[str]:
    if suite not in SUITES:
        raise LaneError(f"unsupported suite: {suite}")
    directories = set(
        git("ls-tree", "-r", "-d", "--name-only", head, "--", "addons", "demo_addons").splitlines()
    )
    graph = impact.snapshot(head)
    runnable = sorted(
        name for name, data in graph.items()
        if str(data.get("prefix") or "") + "tests" in directories
    )
    return planner.suite_modules(suite, runnable, graph)


def validate_plan(
    plan: dict,
    *,
    head: str,
    suite: str,
    expected_modules: list[str],
    allowed_bases: set[str],
) -> None:
    flattened = flatten_plan_modules(plan)
    if (
        plan.get("head") != head
        or plan.get("suite") != suite
        or plan.get("scope_mode") != "full"
        or plan.get("base") not in allowed_bases
        or sorted(plan.get("modules", [])) != sorted(expected_modules)
        or sorted(flattened) != sorted(expected_modules)
        or len(flattened) != len(set(flattened))
    ):
        raise LaneError(
            f"frozen plan identity/scope mismatch for suite={suite} head={head}"
        )


def required_for_paths(paths: list[str]) -> bool:
    for path in paths:
        if path in CLOSURE_PATHS or any(path.startswith(prefix) for prefix in CLOSURE_PREFIXES):
            return True
    return False


def select_latest_run(rows: list[dict], *, head: str, event: str) -> dict | None:
    eligible = [
        row for row in rows
        if row.get("headSha") == head and row.get("event") == event
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda row: int(row.get("databaseId") or 0))


def select_direct_run(rows: list[dict], *, head: str, suite: str) -> dict | None:
    title = direct_run_title(suite, head)
    eligible = [
        row for row in rows
        if row.get("headSha") == head
        and row.get("event") == "workflow_dispatch"
        and row.get("displayTitle") == title
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda row: int(row.get("databaseId") or 0))


class GitHubClient:
    def __init__(self, root: Path = ROOT):
        self.root = root

    def _run(self, args: list[str], *, binary: bool = False):
        result = subprocess.run(
            ["gh", *args],
            cwd=str(self.root),
            capture_output=True,
            check=False,
        )
        if result.returncode:
            error = result.stderr.decode("utf-8", errors="replace").strip()
            raise LaneError(error or f"gh command failed: {' '.join(args[:3])}")
        return result.stdout if binary else result.stdout.decode("utf-8")

    def _json(self, args: list[str]):
        raw = self._run(args)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LaneError("GitHub returned invalid JSON") from exc

    def repo(self) -> str:
        return self._json(["repo", "view", "--json", "nameWithOwner"])["nameWithOwner"]

    def pr(self, number: int | None = None) -> dict:
        args = ["pr", "view"]
        if number is not None:
            args.append(str(number))
        args.extend([
            "--json",
            "number,state,isDraft,headRefOid,baseRefOid,mergeStateStatus,url",
        ])
        return self._json(args)

    def pr_files(self, number: int) -> list[str]:
        raw = self._run([
            "api",
            "--paginate",
            "--jq",
            ".[].filename",
            f"repos/{REPOSITORY}/pulls/{number}/files?per_page=100",
        ])
        return [line for line in raw.splitlines() if line]

    def runs(self, workflow: str, head: str) -> list[dict]:
        return self._json([
            "run",
            "list",
            "--workflow",
            workflow,
            "--commit",
            head,
            "--limit",
            "100",
            "--json",
            "databaseId,headSha,event,status,conclusion,displayTitle,url,workflowName",
        ])

    def run(self, run_id: int) -> dict:
        return self._json([
            "run",
            "view",
            str(run_id),
            "--json",
            "databaseId,headSha,event,status,conclusion,displayTitle,url,workflowName",
        ])

    def dispatch(self, *, branch: str, suite: str, head: str) -> None:
        self._run([
            "workflow",
            "run",
            BACKEND_WORKFLOW,
            "--ref",
            branch,
            "-f",
            f"head_ref={branch}",
            "-f",
            f"head_sha={head}",
            "-f",
            f"suite={suite}",
        ])

    def artifacts(self, run_id: int) -> list[dict]:
        payload = self._json([
            "api",
            f"repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100",
        ])
        return list(payload.get("artifacts") or [])

    def artifact(self, artifact_id: int) -> dict:
        return self._json(["api", f"repos/{REPOSITORY}/actions/artifacts/{artifact_id}"])

    def artifact_zip(self, artifact_id: int) -> bytes:
        return self._run(
            ["api", f"repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip"],
            binary=True,
        )


def read_plan_artifact(client: GitHubClient, *, run_id: int, suite: str) -> dict:
    expected_name = f"backend-plan-{run_id}-{suite}"
    matches = [
        row for row in client.artifacts(run_id)
        if row.get("name") == expected_name and row.get("expired") is False
    ]
    if len(matches) != 1:
        raise LaneError(f"expected one live plan artifact {expected_name}")
    artifact_id = int(matches[0].get("id") or 0)
    artifact = client.artifact(artifact_id)
    origin = artifact.get("workflow_run") or {}
    if (
        artifact.get("id") != artifact_id
        or artifact.get("name") != expected_name
        or artifact.get("expired") is not False
        or origin.get("id") != run_id
    ):
        raise LaneError(f"plan artifact origin mismatch for {expected_name}")
    raw = client.artifact_zip(artifact_id)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if artifact.get("digest") and artifact.get("digest") != digest:
        raise LaneError(f"plan artifact digest mismatch for {expected_name}")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if archive.namelist() != ["backend-plan.json"]:
                raise LaneError("plan artifact must contain only backend-plan.json")
            plan = json.loads(archive.read("backend-plan.json"))
    except (zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise LaneError("invalid frozen plan artifact") from exc
    return {
        "artifact_id": artifact_id,
        "artifact_digest": digest,
        "plan": plan,
    }


def wait_for_run(
    client: GitHubClient,
    *,
    run_id: int,
    head: str,
    workflow: str,
    deadline: float,
    poll_seconds: float,
    direct_suite: str | None = None,
) -> dict:
    while True:
        run = client.run(run_id)
        if run.get("headSha") != head or run.get("workflowName") != workflow.removesuffix(".yml"):
            raise LaneError(f"run {run_id} drifted from exact identity")
        if direct_suite and (
            run.get("event") != "workflow_dispatch"
            or run.get("displayTitle") != direct_run_title(direct_suite, head)
        ):
            raise LaneError(f"run {run_id} is not the requested {direct_suite} lane")
        if run.get("status") == "completed":
            if run.get("conclusion") != "success":
                raise LaneError(
                    f"run {run_id} completed with {run.get('conclusion')} for {workflow}"
                )
            return run
        if time.monotonic() >= deadline:
            raise LaneError(f"run {run_id} did not complete before timeout")
        time.sleep(max(0.1, poll_seconds))


def discover_direct_run(
    client: GitHubClient,
    *,
    branch: str,
    head: str,
    suite: str,
    before_ids: set[int],
    deadline: float,
    poll_seconds: float,
) -> dict:
    client.dispatch(branch=branch, suite=suite, head=head)
    discovered: list[dict] = []
    while time.monotonic() < deadline:
        rows = client.runs(BACKEND_WORKFLOW, head)
        discovered = [
            row for row in rows
            if int(row.get("databaseId") or 0) not in before_ids
            and row.get("displayTitle") == direct_run_title(suite, head)
            and row.get("headSha") == head
            and row.get("event") == "workflow_dispatch"
        ]
        if len(discovered) > 1:
            raise LaneError(f"ambiguous new {suite} runs for exact head")
        if len(discovered) == 1:
            return discovered[0]
        time.sleep(max(0.1, poll_seconds))
    raise LaneError(f"dispatched {suite} run was not discoverable")


def start_or_reuse_direct(
    client: GitHubClient,
    *,
    branch: str,
    head: str,
    suite: str,
    discovery_seconds: float,
    poll_seconds: float,
) -> tuple[dict, bool]:
    rows = client.runs(BACKEND_WORKFLOW, head)
    existing = select_direct_run(rows, head=head, suite=suite)
    if existing:
        if existing.get("status") == "completed" and existing.get("conclusion") != "success":
            raise LaneError(
                f"latest exact-head {suite} run already failed; refusing unchanged retry"
            )
        return existing, False
    before_ids = {int(row.get("databaseId") or 0) for row in rows}
    run = discover_direct_run(
        client,
        branch=branch,
        head=head,
        suite=suite,
        before_ids=before_ids,
        deadline=time.monotonic() + discovery_seconds,
        poll_seconds=poll_seconds,
    )
    return run, True


def resolve_product_lane(
    client: GitHubClient,
    *,
    branch: str,
    head: str,
    base: str,
    expected_modules: list[str],
    professional_wait_seconds: float,
    discovery_seconds: float,
    poll_seconds: float,
) -> tuple[dict, dict | None, bool]:
    deadline = time.monotonic() + professional_wait_seconds
    professional = None
    while True:
        professional = select_latest_run(
            client.runs(PROFESSIONAL_WORKFLOW, head),
            head=head,
            event="pull_request",
        )
        if professional:
            break
        if time.monotonic() >= deadline:
            raise LaneError(
                "required professional_quality_gate run did not appear for exact PR head"
            )
        time.sleep(max(0.1, poll_seconds))

    run_id = int(professional["databaseId"])
    while True:
        if professional.get("status") == "completed" and professional.get("conclusion") != "success":
            raise LaneError("required professional_quality_gate run failed")
        artifacts = [
            row for row in client.artifacts(run_id)
            if row.get("name") == f"backend-plan-{run_id}-product"
            and row.get("expired") is False
        ]
        if artifacts:
            artifact = read_plan_artifact(client, run_id=run_id, suite="product")
            plan = artifact["plan"]
            if plan.get("scope_mode") == "full":
                validate_plan(
                    plan,
                    head=head,
                    suite="product",
                    expected_modules=expected_modules,
                    allowed_bases={"", base},
                )
                return professional, artifact, False
            break
        if professional.get("status") == "completed" and professional.get("conclusion") == "success":
            break
        if time.monotonic() >= deadline:
            raise LaneError("professional product plan did not become available")
        time.sleep(max(0.1, poll_seconds))

    direct, _ = start_or_reuse_direct(
        client,
        branch=branch,
        head=head,
        suite="product",
        discovery_seconds=discovery_seconds,
        poll_seconds=poll_seconds,
    )
    return direct, None, True


def preflight(client: GitHubClient, *, branch: str, head: str) -> tuple[dict, str, str]:
    exact_sha(head, "EXPECTED_HEAD")
    if client.repo() != REPOSITORY:
        raise LaneError("unexpected GitHub repository")
    if git("rev-parse", "HEAD") != head:
        raise LaneError("local HEAD does not match EXPECTED_HEAD")
    if git("status", "--porcelain=v2", "--untracked-files=all"):
        raise LaneError("worktree must be clean")
    remote = git("ls-remote", "--heads", "origin", f"refs/heads/{branch}").split()
    if not remote or remote[0] != head:
        raise LaneError("remote branch HEAD does not match EXPECTED_HEAD")
    pr = client.pr()
    if (
        pr.get("state") != "OPEN"
        or pr.get("isDraft")
        or pr.get("headRefOid") != head
    ):
        raise LaneError("open PR identity does not match EXPECTED_HEAD")
    base = exact_sha(str(pr.get("baseRefOid") or ""), "PR base")
    git("fetch", "origin", "main")
    if git("rev-parse", "origin/main") != base:
        raise LaneError("PR base is stale relative to current origin/main")
    tree = git("rev-parse", f"{head}^{{tree}}")
    return pr, base, tree


def close_lanes(
    client: GitHubClient,
    *,
    branch: str,
    head: str,
    output: Path,
    timeout_seconds: float,
    discovery_seconds: float,
    professional_wait_seconds: float,
    poll_seconds: float,
) -> dict:
    started = time.monotonic()
    pr, base, tree = preflight(client, branch=branch, head=head)
    deadline = started + timeout_seconds
    expected = {suite: expected_suite_modules(head, suite) for suite in SUITES}

    direct_product_before = {
        int(row.get("databaseId") or 0)
        for row in client.runs(BACKEND_WORKFLOW, head)
        if row.get("displayTitle") == direct_run_title("product", head)
    }

    direct_runs: dict[str, dict] = {}
    dispatched: list[str] = []
    for suite in ("demo", "acceptance"):
        run, created = start_or_reuse_direct(
            client,
            branch=branch,
            head=head,
            suite=suite,
            discovery_seconds=discovery_seconds,
            poll_seconds=poll_seconds,
        )
        direct_runs[suite] = run
        if created:
            dispatched.append(suite)

    product_run, product_artifact, product_dispatched = resolve_product_lane(
        client,
        branch=branch,
        head=head,
        base=base,
        expected_modules=expected["product"],
        professional_wait_seconds=professional_wait_seconds,
        discovery_seconds=discovery_seconds,
        poll_seconds=poll_seconds,
    )
    if product_dispatched:
        direct_runs["product"] = product_run
        dispatched.append("product")

    runs = {"product": product_run, **direct_runs}
    completed: dict[str, dict] = {}
    for suite, run in runs.items():
        completed[suite] = wait_for_run(
            client,
            run_id=int(run["databaseId"]),
            head=head,
            workflow=(
                PROFESSIONAL_WORKFLOW
                if suite == "product" and not product_dispatched
                else BACKEND_WORKFLOW
            ),
            deadline=deadline,
            poll_seconds=poll_seconds,
            direct_suite=None if suite == "product" and not product_dispatched else suite,
        )

    artifact_rows = {"product": product_artifact, "demo": None, "acceptance": None}
    for suite in SUITES:
        if artifact_rows[suite] is None:
            artifact_rows[suite] = read_plan_artifact(
                client,
                run_id=int(completed[suite]["databaseId"]),
                suite=suite,
            )
        validate_plan(
            artifact_rows[suite]["plan"],
            head=head,
            suite=suite,
            expected_modules=expected[suite],
            allowed_bases={"", base} if suite == "product" and not product_dispatched else {""},
        )

    direct_product_after = {
        int(row.get("databaseId") or 0)
        for row in client.runs(BACKEND_WORKFLOW, head)
        if row.get("displayTitle") == direct_run_title("product", head)
    }
    if not product_dispatched and direct_product_after != direct_product_before:
        raise LaneError("duplicate direct product dispatch occurred while reusing required CI")

    entries = {}
    for suite in SUITES:
        run = completed[suite]
        artifact = artifact_rows[suite]
        entries[suite] = {
            "source": (
                "professional_quality_gate"
                if suite == "product" and not product_dispatched
                else "backend_test_suite"
            ),
            "run_id": int(run["databaseId"]),
            "run_url": run.get("url"),
            "event": run.get("event"),
            "display_title": run.get("displayTitle"),
            "plan_artifact_id": artifact["artifact_id"],
            "plan_artifact_digest": artifact["artifact_digest"],
            "modules": expected[suite],
        }

    manifest = {
        "schema": SCHEMA,
        "created_at": utc_now(),
        "repository": REPOSITORY,
        "branch": branch,
        "pr": int(pr["number"]),
        "head": head,
        "tree": tree,
        "base": base,
        "status": "passed",
        "suites": entries,
        "efficiency": {
            "product_full_reused_from_required_ci": not product_dispatched,
            "dispatched_suites": sorted(dispatched),
            "auxiliary_dispatched_in_parallel": True,
            "direct_product_run_ids_before": sorted(direct_product_before),
            "direct_product_run_ids_after": sorted(direct_product_after),
        },
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def verify_manifest(client: GitHubClient, *, pr: int, head: str, receipt: Path) -> dict:
    branch = git("branch", "--show-current")
    pr_view, base, tree = preflight(client, branch=branch, head=head)
    if int(pr_view["number"]) != pr:
        raise LaneError("PR number does not match the current branch")
    paths = client.pr_files(pr)
    if not required_for_paths(paths):
        return {"schema": SCHEMA, "status": "not_required", "head": head, "pr": pr}
    if not receipt.is_file():
        raise LaneError(f"required backend iteration receipt is missing: {receipt}")
    manifest = json.loads(receipt.read_text())
    if (
        manifest.get("schema") != SCHEMA
        or manifest.get("status") != "passed"
        or manifest.get("repository") != REPOSITORY
        or manifest.get("branch") != branch
        or int(manifest.get("pr") or 0) != pr
        or manifest.get("head") != head
        or manifest.get("tree") != tree
        or manifest.get("base") != base
        or set(manifest.get("suites") or {}) != set(SUITES)
    ):
        raise LaneError("backend iteration receipt identity mismatch")

    run_ids = set()
    expected = {suite: expected_suite_modules(head, suite) for suite in SUITES}
    for suite in SUITES:
        entry = manifest["suites"][suite]
        run_id = int(entry.get("run_id") or 0)
        if run_id <= 0 or run_id in run_ids:
            raise LaneError("backend iteration run ids must be positive and unique")
        run_ids.add(run_id)
        source = entry.get("source")
        if source == "professional_quality_gate":
            workflow = PROFESSIONAL_WORKFLOW
            event = "pull_request"
        elif source == "backend_test_suite":
            workflow = BACKEND_WORKFLOW
            event = "workflow_dispatch"
        else:
            raise LaneError("invalid backend suite source")
        live = client.run(run_id)
        if (
            live.get("headSha") != head
            or live.get("event") != event
            or live.get("status") != "completed"
            or live.get("conclusion") != "success"
        ):
            raise LaneError(f"live {suite} run identity/result mismatch")
        if source == "professional_quality_gate":
            if live.get("workflowName") != PROFESSIONAL_WORKFLOW.removesuffix(".yml"):
                raise LaneError("professional product run workflow mismatch")
        elif live.get("displayTitle") != direct_run_title(suite, head):
            raise LaneError(f"live {suite} direct run title mismatch")

        artifact = read_plan_artifact(client, run_id=run_id, suite=suite)
        if (
            artifact["artifact_id"] != entry.get("plan_artifact_id")
            or artifact["artifact_digest"] != entry.get("plan_artifact_digest")
        ):
            raise LaneError(f"{suite} plan artifact drifted from receipt")
        validate_plan(
            artifact["plan"],
            head=head,
            suite=suite,
            expected_modules=expected[suite],
            allowed_bases={"", base} if source == "professional_quality_gate" else {""},
        )
    return {
        "schema": SCHEMA,
        "status": "passed",
        "head": head,
        "tree": tree,
        "base": base,
        "pr": pr,
        "suite_run_ids": {suite: manifest["suites"][suite]["run_id"] for suite in SUITES},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    close = sub.add_parser("close")
    close.add_argument("--branch", required=True)
    close.add_argument("--expected-head", required=True)
    close.add_argument("--output", type=Path, required=True)
    close.add_argument("--timeout-seconds", type=float, default=7200)
    close.add_argument("--discovery-seconds", type=float, default=900)
    close.add_argument("--professional-wait-seconds", type=float, default=1200)
    close.add_argument("--poll-seconds", type=float, default=15)

    verify = sub.add_parser("verify-merge")
    verify.add_argument("--pr", type=int, required=True)
    verify.add_argument("--expected-head", required=True)
    verify.add_argument("--receipt", type=Path, required=True)

    args = parser.parse_args(argv)
    client = GitHubClient()
    try:
        if args.command == "close":
            result = close_lanes(
                client,
                branch=args.branch,
                head=args.expected_head,
                output=args.output,
                timeout_seconds=args.timeout_seconds,
                discovery_seconds=args.discovery_seconds,
                professional_wait_seconds=args.professional_wait_seconds,
                poll_seconds=args.poll_seconds,
            )
        else:
            result = verify_manifest(
                client,
                pr=args.pr,
                head=args.expected_head,
                receipt=args.receipt,
            )
    except (LaneError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[backend-iteration] FAIL {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

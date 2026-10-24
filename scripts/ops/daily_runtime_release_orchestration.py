#!/usr/bin/env python3
"""Run the complete daily runtime release sequence through governed Make targets."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[2]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
FULL_DIGEST = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
CONFIRMATION = "PUBLISH_EXACT_DAILY_RUNTIME_VERSION"
ENTRY_DECLARATION = Path("config/ops/daily_runtime_entry.v1.json")
DEFAULT_REPORT_ROOT = ".runtime/final-acceptance/daily-deployed/release"
DUTY_PLAN_REPORT = ".runtime/final-acceptance/daily-deployed/database-duty-plan.json"
# Makefile exports every variable when an operator env file is present. That
# freezes recursively expanded argument builders at the parent make's values,
# so a child make can see a non-empty input while still receiving an empty
# ``--expect-entry-digest`` or missing duty/selection flags. Drop only the
# derived builders and let each child make re-expand them from this step.
FROZEN_RECURSIVE_MAKE_VARIABLES = (
    "DAILY_RUNTIME_CANDIDATE_SHA_FLAG",
    "DAILY_RUNTIME_DUTY_FLAG",
    "DAILY_RUNTIME_LEGACY_EXPECTED_SHA_FLAG",
    "DAILY_RUNTIME_FRONTEND_BUILD_REPORT",
    "DAILY_RUNTIME_DATABASE_DUTY_EXPECTED_SHA_FLAG",
    "DAILY_RUNTIME_DATABASE_DUTY_SELECTION_FLAGS",
    "DAILY_RUNTIME_ENTRY_FLAGS",
)


class ReleaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class Step:
    key: str
    target: str
    variables: dict[str, str]
    environment: dict[str, str]

    def command(self) -> list[str]:
        return [
            "make",
            "--no-print-directory",
            self.target,
            *(f"{key}={value}" for key, value in self.variables.items() if value != ""),
        ]


@dataclass(frozen=True)
class Identity:
    mode: str
    branch: str
    head: str
    expected_sha: str
    expected_old_sha: str
    expected_candidate_sha: str


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise ReleaseError(f"git {arguments[0]} failed: {result.stderr.strip()[:600]}")
    return result.stdout.strip()


def validate_identity(
    repository: Path,
    args: argparse.Namespace,
    *,
    require_workspace: bool = True,
) -> Identity:
    if args.mode not in {"main", "candidate"}:
        raise ReleaseError("mode must be main or candidate")
    for label, value in (
        ("expected-sha", args.expected_sha),
        ("expected-old-sha", args.expected_old_sha),
    ):
        if not FULL_SHA.fullmatch(value or ""):
            raise ReleaseError(f"{label} must be a full lowercase SHA")
    if args.expected_sha == args.expected_old_sha:
        raise ReleaseError("release target must differ from the deployed old SHA")
    if not SSH_HOST.fullmatch(args.ssh_host or ""):
        raise ReleaseError("ssh-host is invalid")
    if args.mode == "candidate":
        if not ALLOWED_BRANCH.fullmatch(args.source_branch or ""):
            raise ReleaseError("candidate source branch is invalid")
        if args.expected_candidate_sha:
            raise ReleaseError("candidate mode does not accept expected-candidate-sha")
    elif args.expected_candidate_sha:
        if not FULL_SHA.fullmatch(args.expected_candidate_sha):
            raise ReleaseError("expected-candidate-sha must be a full lowercase SHA")
    if require_workspace:
        branch = _git(repository, "branch", "--show-current")
        head = _git(repository, "rev-parse", "HEAD")
        if _git(repository, "status", "--porcelain"):
            raise ReleaseError("release workspace must be clean")
        if args.mode == "main" and branch != "main":
            raise ReleaseError("main release requires the main branch")
        if args.mode == "candidate" and branch != args.source_branch:
            raise ReleaseError("candidate release branch differs from source-branch")
        if head != args.expected_sha:
            raise ReleaseError(f"local HEAD {head} differs from expected-sha {args.expected_sha}")
    else:
        branch = "main" if args.mode == "main" else args.source_branch
        head = args.expected_sha
    return Identity(
        mode=args.mode,
        branch=branch,
        head=head,
        expected_sha=args.expected_sha,
        expected_old_sha=args.expected_old_sha,
        expected_candidate_sha=args.expected_candidate_sha,
    )


def load_entry(repository: Path) -> dict:
    path = repository / ENTRY_DECLARATION
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseError(f"entry declaration is unreadable: {exc}") from exc
    public = payload.get("public_entry")
    if not isinstance(public, dict):
        raise ReleaseError("entry declaration has no public_entry")
    for key in ("port", "demo_path", "platform_admin_path"):
        if public.get(key) in ("", None):
            raise ReleaseError(f"entry declaration public_entry.{key} is missing")
    return payload


def plan_steps(
    repository: Path,
    args: argparse.Namespace,
    identity: Identity,
) -> list[Step]:
    entry = load_entry(repository)
    public = entry["public_entry"]
    base = f"http://127.0.0.1:{int(public['port'])}"
    demo_base = base + str(public["demo_path"])
    platform_base = base + str(public["platform_admin_path"])
    report_root = repository / args.report_root / identity.mode / identity.expected_sha
    bundle_report = report_root / "bundle-sync.json"
    build_report = report_root / "frontend-build.json"
    refresh_report = report_root / "duty-refresh.json"
    demo_align_report = report_root / "source-revision-demo.json"
    platform_align_report = report_root / "source-revision-platform.json"
    face_report = report_root / "published-face.json"
    entry_report = report_root / "entry-verify.json"

    if identity.mode == "main":
        sync = Step(
            key="sync",
            target="daily.runtime.main.bundle_sync",
            variables={
                "DAILY_RUNTIME_EXPECTED_SHA": identity.expected_sha,
                "DAILY_RUNTIME_EXPECTED_OLD_SHA": identity.expected_old_sha,
                "DAILY_RUNTIME_EXPECTED_CANDIDATE_SHA": identity.expected_candidate_sha,
                "DAILY_RUNTIME_SSH_HOST": args.ssh_host,
                "DAILY_RUNTIME_BUNDLE_SYNC_REPORT": str(bundle_report),
            },
            environment={
                "CONFIRM_DAILY_RUNTIME_BUNDLE_SYNC":
                    "SYNC_EXACT_DAILY_MAIN_SHA_WITH_BUNDLE",
            },
        )
    else:
        sync = Step(
            key="sync",
            target="daily.runtime.candidate.bundle_sync",
            variables={
                "DAILY_CANDIDATE_SOURCE_REPOSITORY": str(repository),
                "DAILY_CANDIDATE_SOURCE_BRANCH": identity.branch,
                "DAILY_CANDIDATE_EXPECTED_SHA": identity.expected_sha,
                "DAILY_CANDIDATE_EXPECTED_OLD_SHA": identity.expected_old_sha,
                "DAILY_RUNTIME_SSH_HOST": args.ssh_host,
                "DAILY_CANDIDATE_BUNDLE_SYNC_REPORT": str(bundle_report),
            },
            environment={
                "CONFIRM_DAILY_CANDIDATE_BUNDLE_SYNC":
                    "SYNC_EXACT_DAILY_CANDIDATE_SHA_WITH_BUNDLE",
            },
        )
    common = {"DAILY_RUNTIME_SSH_HOST": args.ssh_host}
    steps = [
        sync,
        Step(
            key="frontend-build",
            target="daily.runtime.frontend.build",
            variables={
                **common,
                "DAILY_RUNTIME_FRONTEND_BUILD_SHA": identity.expected_sha,
                "DAILY_RUNTIME_FRONTEND_BUILD_RECEIPT": str(build_report),
                "DAILY_RUNTIME_FRONTEND_BUILD_REPORT": str(build_report),
            },
            environment={
                "CONFIRM_DAILY_RUNTIME_FRONTEND_BUILD":
                    "BUILD_AND_DECLARE_DAILY_RUNTIME_FRONTEND_AT_DEPLOYED_HEAD",
            },
        ),
        Step(
            key="duty-refresh",
            target="daily.runtime.database.duty.refresh",
            variables={
                **common,
                "DAILY_RUNTIME_EXPECTED_SHA": identity.expected_sha,
                "DAILY_RUNTIME_DATABASE_DUTY_SELECTION": "demo platform_control",
                "DAILY_RUNTIME_DATABASE_DUTY_DECLARATION_DIGEST": args.declaration_digest,
                "DAILY_RUNTIME_ENTRY_DECLARATION_DIGEST": args.entry_digest,
                "DAILY_RUNTIME_DATABASE_DUTY_REFRESH_REPORT": str(refresh_report),
            },
            environment={
                "SC_CONFIRM_DAILY_RUNTIME_DUTY_REFRESH":
                    "REFRESH_DAILY_RUNTIME_DUTY_STACK_AND_APPLICATION",
            },
        ),
        Step(
            key="align-demo",
            target="daily.runtime.source_revision.align",
            variables={
                **common,
                "DAILY_RUNTIME_SOURCE_REVISION_SHA": identity.expected_sha,
                "DAILY_RUNTIME_DUTY": "demo",
                "DAILY_RUNTIME_SOURCE_REVISION_BASE_URL": demo_base,
                "DAILY_RUNTIME_SOURCE_REVISION_REPORT": str(demo_align_report),
            },
            environment={
                "CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN":
                    "ALIGN_DAILY_RUNTIME_SOURCE_REVISION_WITH_DEPLOYED_HEAD",
            },
        ),
        Step(
            key="align-platform",
            target="daily.runtime.source_revision.align",
            variables={
                **common,
                "DAILY_RUNTIME_SOURCE_REVISION_SHA": identity.expected_sha,
                "DAILY_RUNTIME_DUTY": "platform_control",
                "DAILY_RUNTIME_SOURCE_REVISION_BASE_URL": platform_base,
                "DAILY_RUNTIME_SOURCE_REVISION_REPORT": str(platform_align_report),
            },
            environment={
                "CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN":
                    "ALIGN_DAILY_RUNTIME_SOURCE_REVISION_WITH_DEPLOYED_HEAD",
            },
        ),
        Step(
            key="published-face",
            target="daily.runtime.published_face.converge",
            variables={
                **common,
                "DAILY_RUNTIME_PUBLISHED_FACE_EXPECTED_SHA": identity.expected_sha,
                "DAILY_RUNTIME_DUTY": "demo",
                "DAILY_RUNTIME_PUBLISHED_FACE_LOGIN": args.published_face_login,
                "DAILY_RUNTIME_PUBLISHED_FACE_REPORT": str(face_report),
            },
            environment={
                "CONFIRM_DAILY_RUNTIME_PUBLISHED_FACE":
                    "REFRESH_DAILY_RUNTIME_PUBLISHED_FACE_FROM_LOCKED_CONTRACT",
            },
        ),
        Step(
            key="entry-verify",
            target="daily.runtime.entry.verify",
            variables={
                **common,
                "DAILY_RUNTIME_EXPECTED_SHA": identity.expected_sha,
                "DAILY_RUNTIME_ENTRY_VERIFY_REPORT": str(entry_report),
            },
            environment={},
        ),
    ]
    return steps


def derive_digests(repository: Path, args: argparse.Namespace, identity: Identity) -> tuple[str, str]:
    """Derive the reviewed declaration and entry digests from the governed plan.

    The declaration digest is over the template merged with the remote managed
    instances, so it can never be computed by hand. Run the read-only duty plan
    first, read both digests from its report, and require any operator-supplied
    value to agree. This also validates the declaration/entry/identity before
    any remote mutation happens.
    """
    plan_report = repository / DUTY_PLAN_REPORT
    command = [
        "make",
        "--no-print-directory",
        "daily.runtime.database.duty.plan",
        "DAILY_RUNTIME_SSH_HOST=" + args.ssh_host,
        "DAILY_RUNTIME_EXPECTED_SHA=" + identity.expected_sha,
        "DAILY_RUNTIME_DATABASE_DUTY_SELECTION=demo platform_control",
        "DAILY_RUNTIME_DATABASE_DUTY_PLAN_REPORT=" + str(plan_report),
    ]
    result = subprocess.run(
        command,
        cwd=repository,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise ReleaseError("governed duty plan failed; cannot derive digests: " + result.stderr.strip()[-600:])
    try:
        payload = json.loads(plan_report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseError(f"duty plan report is unreadable: {exc}") from exc
    declaration_digest = str(payload.get("declaration_digest") or "")
    entry_digest = str(payload.get("entry_digest") or "")
    if not FULL_DIGEST.fullmatch(declaration_digest) or not FULL_DIGEST.fullmatch(entry_digest):
        raise ReleaseError("duty plan report lacks valid declaration/entry digests")
    return declaration_digest, entry_digest


def resume_steps(steps: Sequence[Step], resume_from: str) -> list[Step]:
    """Skip every step before the named key; a miss is a fail-closed refusal."""
    keys = [step.key for step in steps]
    if resume_from not in keys:
        raise ReleaseError(f"resume-from {resume_from!r} is not a release step: {keys}")
    return [step for step in steps if keys.index(step.key) >= keys.index(resume_from)]


Runner = Callable[[Sequence[str], Path, dict[str, str]], tuple[int, str, str]]


def subprocess_runner(
    command: Sequence[str], cwd: Path, environment: dict[str, str]
) -> tuple[int, str, str]:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def execute(
    repository: Path,
    steps: Sequence[Step],
    *,
    runner: Runner = subprocess_runner,
    report: Path | None = None,
) -> dict:
    records = []
    status = "PASS"
    for step in steps:
        started = time.monotonic()
        environment = {**os.environ, **step.environment}
        for variable in FROZEN_RECURSIVE_MAKE_VARIABLES:
            environment.pop(variable, None)
        code, stdout, stderr = runner(step.command(), repository, environment)
        record = {
            "key": step.key,
            "target": step.target,
            "status": "PASS" if code == 0 else "FAIL",
            "returncode": code,
            "duration_seconds": round(time.monotonic() - started, 3),
            "output_tail": (stdout + "\n" + stderr).strip()[-3000:],
        }
        records.append(record)
        if code:
            status = "FAIL"
            break
    payload = {
        "schema": "daily_runtime_release_orchestration.v1",
        "status": status,
        "steps": records,
    }
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--mode", choices=["main", "candidate"], required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-old-sha", required=True)
    parser.add_argument("--expected-candidate-sha", default="")
    parser.add_argument("--source-branch", default="")
    parser.add_argument("--ssh-host", default="sc-root")
    parser.add_argument("--declaration-digest", default="")
    parser.add_argument("--entry-digest", default="")
    parser.add_argument("--published-face-login", default="demo_full")
    parser.add_argument("--report-root", default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--resume-from", default="")
    args = parser.parse_args(argv)
    repository = args.repo_root.resolve()
    try:
        identity = validate_identity(repository, args, require_workspace=not args.plan)
        steps = plan_steps(repository, args, identity)
    except ReleaseError as exc:
        print(f"[daily.runtime.release] BLOCKED {exc}")
        return 2
    if args.plan:
        print(json.dumps([
            {"key": step.key, "target": step.target, "variables": step.variables}
            for step in steps
        ], indent=2, sort_keys=True))
        return 0
    # Derive the reviewed digests from the read-only plan before any mutation.
    # This both removes the error-prone manual digest and validates the
    # declaration/entry/identity before the first remote write.
    try:
        declaration_digest, entry_digest = derive_digests(repository, args, identity)
        if args.declaration_digest and args.declaration_digest != declaration_digest:
            raise ReleaseError("operator declaration digest disagrees with the governed plan")
        if args.entry_digest and args.entry_digest != entry_digest:
            raise ReleaseError("operator entry digest disagrees with the governed plan")
        args.declaration_digest = declaration_digest
        args.entry_digest = entry_digest
        steps = plan_steps(repository, args, identity)
        if args.resume_from:
            steps = resume_steps(steps, args.resume_from)
    except ReleaseError as exc:
        print(f"[daily.runtime.release] BLOCKED {exc}")
        return 2
    if os.environ.get("CONFIRM_DAILY_RUNTIME_RELEASE") != CONFIRMATION:
        print(f"[daily.runtime.release] BLOCKED {CONFIRMATION} confirmation is required")
        return 2
    report = args.report or (
        repository
        / args.report_root
        / identity.mode
        / identity.expected_sha
        / "release.json"
    )
    payload = execute(repository, steps, report=report)
    print(json.dumps({"status": payload["status"], "report": str(report)}, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

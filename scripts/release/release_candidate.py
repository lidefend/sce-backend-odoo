#!/usr/bin/env python3
"""One-command, fail-closed orchestration for a local immutable RC candidate."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from release_candidate_report import (
    CandidateReportError,
    atomic_write_json,
    atomic_write_text,
    build_ready_report,
    load_json,
    utc_now,
    validate_build_artifacts,
    write_ready_outputs,
)


ROOT = Path(__file__).resolve().parents[2]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+$")
REQUIRED_CHECKS = (
    "public_guard",
    "professional_authorization",
    "professional_quality_gate",
)
GITEE_MAIN = "git@gitee.com:leegege/sce-product-odoo.git"
APPROVED_ORIGIN = "https://github.com/lidefend/sce-backend-odoo.git"
CONTRACT_FILES = (
    "make/release.mk",
    "scripts/release/immutable_candidate_build.sh",
    "scripts/release/immutable_candidate_scan.sh",
    "scripts/release/candidate_scan_contract.py",
    "scripts/release/release_candidate.py",
    "scripts/release/release_candidate_report.py",
    "schemas/release/release_candidate_report.v1.schema.json",
)
BUILD_OUTPUTS = (
    "candidate-image.tar",
    "frontend-build.sha256",
    "image-manifest.json",
    "reloaded-image-id.txt",
)
LOCK_FD_ENV = "RELEASE_CANDIDATE_LOCK_FD"


class CandidatePipelineError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def command_output(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise CandidatePipelineError(
            f"command failed ({' '.join(command)}): {detail}",
            exit_code=completed.returncode,
        )
    return completed.stdout.strip()


def run_logged(
    stage: str,
    command: list[str],
    log_path: Path,
    *,
    env: dict[str, str],
    cwd: Path = ROOT,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{utc_now()}] stage={stage} command={' '.join(command)}\n")
        log.flush()
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            log.write(line)
        result = process.wait()
        log.write(f"[{utc_now()}] stage={stage} exit_code={result}\n")
    if result:
        raise CandidatePipelineError(
            f"{stage} failed with exit code {result}",
            exit_code=result,
        )


def validate_version(value: str) -> str:
    if not VERSION.fullmatch(value):
        raise CandidatePipelineError("VERSION must match X.Y.Z-rc.N")
    return value


def artifact_directory(version: str) -> Path:
    return ROOT / "artifacts" / "release" / "candidates" / version


def acquire_candidate_lock(artifacts: Path) -> int:
    inherited = os.environ.get(LOCK_FD_ENV)
    if inherited:
        try:
            descriptor = int(inherited)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, ValueError) as exc:
            raise CandidatePipelineError("inherited candidate lock is invalid") from exc
        return descriptor

    artifacts.parent.mkdir(parents=True, exist_ok=True)
    lock_path = artifacts.parent / f".{artifacts.name}.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(descriptor)
        raise CandidatePipelineError(
            f"candidate already running for {artifacts.name}",
            exit_code=73,
        ) from exc
    os.set_inheritable(descriptor, True)
    return descriptor


def pipeline_contract_sha256() -> str:
    digest = hashlib.sha256()
    for relative in CONTRACT_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise CandidatePipelineError(f"release candidate contract file is missing: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def bind_pipeline_contract(artifacts: Path, contract_sha256: str) -> None:
    path = artifacts / "candidate-contract.sha256"
    existing_outputs = [name for name in BUILD_OUTPUTS if (artifacts / name).exists()]
    if path.is_file():
        if path.read_text(encoding="utf-8").strip() != contract_sha256:
            raise CandidatePipelineError("existing candidate tool contract differs")
        return
    if existing_outputs:
        raise CandidatePipelineError(
            "existing build outputs have no verified candidate tool contract"
        )
    atomic_write_text(path, contract_sha256 + "\n")


def archive_failed_report(report_path: Path) -> Path | None:
    if not report_path.is_file():
        return None
    payload = load_json(report_path, "candidate report")
    if payload.get("status") != "failed":
        return None
    failures = report_path.parent / "failures"
    failures.mkdir(parents=True, exist_ok=True)
    failed_stage = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(payload.get("failed_stage") or "unknown"))
    destination = failures / f"{time.time_ns()}-{failed_stage}.json"
    shutil.copyfile(report_path, destination)
    return destination


def state_payload(
    *,
    version: str,
    status: str,
    stage: str,
    source_sha: str | None = None,
    source_tree: str | None = None,
    pipeline_contract: str | None = None,
    error: str | None = None,
    exit_code: int | None = None,
) -> dict:
    return {
        "schema_version": "release_candidate_report.v1",
        "status": status,
        "CANDIDATE_READY": False,
        "source": {
            "commit_sha": source_sha,
            "tree_sha": source_tree,
            "product_version": version,
            "pipeline_contract_sha256": pipeline_contract,
        },
        "stage": stage,
        "failed_stage": stage if status == "failed" else None,
        "error": error,
        "exit_code": exit_code,
        "evidence": {
            "report": "release-report.json",
            "log": f"logs/{stage}.log",
        },
        "external_effects": {
            "registry_push": False,
            "git_tag": False,
            "release_publication": False,
            "deployment": False,
        },
        "updated_at": utc_now(),
    }


def write_state(path: Path, payload: dict) -> None:
    atomic_write_json(path, payload)


def ls_remote(remote: str, ref: str) -> str:
    output = command_output(["git", "ls-remote", remote, ref])
    rows = [line.split() for line in output.splitlines() if line.strip()]
    if len(rows) != 1 or not FULL_SHA.fullmatch(rows[0][0]):
        raise CandidatePipelineError(f"remote ref is missing or ambiguous: {remote} {ref}")
    return rows[0][0]


def required_check_results(source_sha: str) -> tuple[str, dict[str, str]]:
    parents = command_output(["git", "show", "-s", "--format=%P", source_sha]).split()
    check_head_sha = parents[1] if len(parents) == 2 else source_sha
    raw = command_output(
        [
            "gh",
            "api",
            f"repos/lidefend/sce-backend-odoo/commits/{check_head_sha}/check-runs",
            "-H",
            "Accept: application/vnd.github+json",
        ]
    )
    try:
        rows = json.loads(raw).get("check_runs", [])
    except (AttributeError, json.JSONDecodeError) as exc:
        raise CandidatePipelineError("GitHub required-check response is invalid") from exc
    results: dict[str, str] = {}
    for name in REQUIRED_CHECKS:
        matching = [row for row in rows if row.get("name") == name]
        if not matching:
            raise CandidatePipelineError(f"required check is missing: {name}")
        matching.sort(
            key=lambda row: str(row.get("completed_at") or row.get("started_at") or ""),
            reverse=True,
        )
        selected = matching[0]
        if selected.get("head_sha") not in (None, check_head_sha):
            raise CandidatePipelineError(f"required check head SHA differs: {name}")
        if selected.get("status") != "completed" or selected.get("conclusion") != "success":
            raise CandidatePipelineError(f"required check did not pass: {name}")
        results[name] = "success"
    return check_head_sha, results


def preflight_identity(
    version: str,
) -> tuple[str, str, dict[str, str], str, dict[str, str]]:
    branch = command_output(["git", "branch", "--show-current"])
    if branch != "main":
        raise CandidatePipelineError("main.sync did not leave the release workspace on main")
    if command_output(["git", "status", "--porcelain=v1", "--untracked-files=all"]):
        raise CandidatePipelineError("release workspace must be clean after main.sync")
    source_sha = command_output(["git", "rev-parse", "HEAD"])
    source_tree = command_output(["git", "rev-parse", "HEAD^{tree}"])
    if not FULL_SHA.fullmatch(source_sha) or not FULL_SHA.fullmatch(source_tree):
        raise CandidatePipelineError("source commit/tree identity is invalid")
    repository_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if repository_version != version:
        raise CandidatePipelineError(
            f"requested VERSION={version} differs from repository VERSION={repository_version}"
        )
    gitee_remote = os.environ.get("GITEE_RELEASE_REMOTE", GITEE_MAIN)
    remotes = {
        "github": ls_remote("origin", "refs/heads/main"),
        "gitee": ls_remote(gitee_remote, "refs/heads/main"),
    }
    if set(remotes.values()) != {source_sha}:
        raise CandidatePipelineError("local/GitHub/Gitee main identities are not aligned")
    checks_head_sha, checks = required_check_results(source_sha)
    return source_sha, source_tree, remotes, checks_head_sha, checks


def source_repository_identity(path: Path) -> tuple[str, str]:
    def output(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            raise CandidatePipelineError(f"source repository git command failed: {' '.join(args)}")
        return completed.stdout.strip()

    if (path / ".git" / "objects" / "info" / "alternates").exists():
        raise CandidatePipelineError("source repository must not use alternates")
    if output("remote", "get-url", "origin") != APPROVED_ORIGIN:
        raise CandidatePipelineError("source repository origin is not approved")
    if output("status", "--porcelain=v1", "--untracked-files=all"):
        raise CandidatePipelineError("source repository worktree is not clean")
    return output("rev-parse", "HEAD"), output("rev-parse", "HEAD^{tree}")


def prepare_source_repository(
    artifacts: Path,
    source_sha: str,
    source_tree: str,
    github_main: str,
    *,
    env: dict[str, str],
) -> Path:
    source = artifacts / "source-repository"
    if not source.exists():
        staging = artifacts / f".source-repository-{os.getpid()}"
        if staging.exists():
            raise CandidatePipelineError("source repository staging path already exists")
        run_logged(
            "source_repository_prepare",
            [
                "git",
                "clone",
                "--no-local",
                "--no-tags",
                "--single-branch",
                "--branch",
                "main",
                APPROVED_ORIGIN,
                str(staging),
            ],
            artifacts / "logs" / "source_repository_prepare.log",
            env=env,
        )
        os.replace(staging, source)
    actual_sha, actual_tree = source_repository_identity(source)
    if (actual_sha, actual_tree) != (source_sha, source_tree):
        raise CandidatePipelineError("source repository SHA/tree differs from frozen identity")
    if github_main != source_sha:
        raise CandidatePipelineError("source repository commit is not the approved GitHub main")
    return source


def validate_source_history(source: Path, artifacts: Path, *, env: dict[str, str]) -> None:
    run_logged(
        "history_hygiene",
        [
            sys.executable,
            "scripts/verify/repository_clean_history_guard.py",
            "--root",
            str(source),
            "--local-hygiene",
        ],
        artifacts / "logs" / "history_hygiene.log",
        env=env,
        cwd=source,
    )


def report_matches_identity(
    path: Path,
    version: str,
    source_sha: str,
    source_tree: str,
    pipeline_contract: str,
) -> bool:
    if not path.is_file():
        return False
    payload = load_json(path, "candidate report")
    source = payload.get("source") or {}
    if source.get("product_version") != version:
        raise CandidatePipelineError("existing candidate report version differs")
    existing_sha = source.get("commit_sha")
    if existing_sha not in (None, source_sha):
        raise CandidatePipelineError("existing candidate report source SHA differs")
    existing_tree = source.get("tree_sha")
    if existing_tree not in (None, source_tree):
        raise CandidatePipelineError("existing candidate report source tree differs")
    existing_contract = source.get("pipeline_contract_sha256")
    if existing_contract not in (None, pipeline_contract):
        raise CandidatePipelineError("existing candidate report tool contract differs")
    return payload.get("status") == "ready" and payload.get("CANDIDATE_READY") is True


def finalize_candidate(
    artifacts: Path,
    report_path: Path,
    *,
    source_sha: str,
    source_tree: str,
    version: str,
    pipeline_contract: str,
    remotes: dict[str, str],
    checks_head_sha: str,
    checks: dict[str, str],
) -> None:
    image = load_json(artifacts / "image-manifest.json", "image manifest")
    architecture = command_output(
        ["docker", "image", "inspect", image["image"], "--format", "{{.Architecture}}"]
    )
    ready = build_ready_report(
        artifacts,
        expected_source_sha=source_sha,
        expected_source_tree=source_tree,
        expected_version=version,
        expected_pipeline_contract=pipeline_contract,
        remote_main=remotes,
        required_checks=checks,
        required_checks_head_sha=checks_head_sha,
        image_architecture=architecture,
    )
    write_ready_outputs(report_path, ready)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    version = validate_version(args.version)
    environment = os.environ.get("ENV", "")
    if environment not in {"dev", "test"}:
        raise SystemExit("RELEASE_CANDIDATE_BLOCKED: ENV must be dev or test")

    artifacts = artifact_directory(version)
    report_path = artifacts / "release-report.json"
    try:
        lock_descriptor = acquire_candidate_lock(artifacts)
    except CandidatePipelineError as exc:
        print(f"RELEASE_CANDIDATE_BLOCKED: {exc}", file=sys.stderr)
        return exc.exit_code
    if artifacts.exists() and not report_path.is_file():
        raise SystemExit(
            f"RELEASE_CANDIDATE_BLOCKED: pre-existing unowned artifact directory: {artifacts}"
        )
    artifacts.mkdir(parents=True, exist_ok=True)
    previous_ready = False
    if report_path.is_file():
        existing = load_json(report_path, "candidate report")
        previous_ready = (
            existing.get("status") == "ready"
            and existing.get("CANDIDATE_READY") is True
        )
        if not previous_ready:
            archive_failed_report(report_path)
    source_sha: str | None = None
    source_tree: str | None = None
    pipeline_contract: str | None = None
    stage = "main_sync"
    env = dict(os.environ)
    synchronized = env.get("RELEASE_CANDIDATE_MAIN_SYNCED") == "1"

    try:
        if not synchronized:
            if command_output(["git", "status", "--porcelain=v1", "--untracked-files=all"]):
                raise CandidatePipelineError("release workspace must be clean before main.sync")
            if not previous_ready:
                write_state(
                    report_path,
                    state_payload(version=version, status="running", stage=stage),
                )
            run_logged(
                stage,
                ["make", "--no-print-directory", "main.sync"],
                artifacts / "logs" / f"{stage}.log",
                env=env,
            )
            # Reload the orchestrator from the synchronized main checkout. This
            # prevents a clean but stale release branch from controlling a new
            # main candidate after main.sync changes the worktree contents.
            env["RELEASE_CANDIDATE_MAIN_SYNCED"] = "1"
            env[LOCK_FD_ENV] = str(lock_descriptor)
            os.execve(
                sys.executable,
                [
                    sys.executable,
                    str(ROOT / "scripts" / "release" / "release_candidate.py"),
                    "--version",
                    version,
                ],
                env,
            )

        stage = "identity"
        source_sha, source_tree, remotes, checks_head_sha, checks = preflight_identity(version)
        pipeline_contract = pipeline_contract_sha256()
        bind_pipeline_contract(artifacts, pipeline_contract)
        if report_matches_identity(
            report_path,
            version,
            source_sha,
            source_tree,
            pipeline_contract,
        ):
            finalize_candidate(
                artifacts,
                report_path,
                source_sha=source_sha,
                source_tree=source_tree,
                version=version,
                pipeline_contract=pipeline_contract,
                remotes=remotes,
                checks_head_sha=checks_head_sha,
                checks=checks,
            )
            print(f"[release.candidate] CANDIDATE_READY=true evidence={report_path}")
            return 0
        write_state(
            report_path,
            state_payload(
                version=version,
                status="running",
                stage=stage,
                source_sha=source_sha,
                source_tree=source_tree,
                pipeline_contract=pipeline_contract,
            ),
        )

        stage = "source_repository_prepare"
        write_state(
            report_path,
            state_payload(
                version=version,
                status="running",
                stage=stage,
                source_sha=source_sha,
                source_tree=source_tree,
                pipeline_contract=pipeline_contract,
            ),
        )
        source_repository = prepare_source_repository(
            artifacts,
            source_sha,
            source_tree,
            remotes["github"],
            env=env,
        )
        stage = "history_hygiene"
        validate_source_history(source_repository, artifacts, env=env)

        stage = "build"
        try:
            validate_build_artifacts(
                artifacts,
                expected_source_sha=source_sha,
                expected_source_tree=source_tree,
                expected_version=version,
                expected_pipeline_contract=pipeline_contract,
            )
            print("[release.candidate] resume: validated build artifacts; build skipped")
        except CandidateReportError:
            run_logged(
                stage,
                [
                    "make",
                    "--no-print-directory",
                    "release.candidate.build",
                    f"SOURCE_SHA={source_sha}",
                    f"CANDIDATE_ARTIFACTS={artifacts}",
                ],
                artifacts / "logs" / f"{stage}.log",
                env=env,
                cwd=source_repository,
            )
            validate_build_artifacts(
                artifacts,
                expected_source_sha=source_sha,
                expected_source_tree=source_tree,
                expected_version=version,
                expected_pipeline_contract=pipeline_contract,
            )
        write_state(
            report_path,
            state_payload(
                version=version,
                status="running",
                stage="scan_sbom",
                source_sha=source_sha,
                source_tree=source_tree,
                pipeline_contract=pipeline_contract,
            ),
        )

        # If a previous attempt completed scan/SBOM but stopped while emitting
        # the report, finish from those verified artifacts without rescanning.
        try:
            finalize_candidate(
                artifacts,
                report_path,
                source_sha=source_sha,
                source_tree=source_tree,
                version=version,
                pipeline_contract=pipeline_contract,
                remotes=remotes,
                checks_head_sha=checks_head_sha,
                checks=checks,
            )
            print("[release.candidate] resume: validated scan/SBOM artifacts; scan skipped")
            print(f"[release.candidate] CANDIDATE_READY=true evidence={report_path}")
            return 0
        except (CandidateReportError, OSError):
            pass

        stage = "scan_sbom"
        run_logged(
            stage,
            [
                "make",
                "--no-print-directory",
                "release.candidate.scan",
                f"SOURCE_SHA={source_sha}",
                f"CANDIDATE_ARTIFACTS={artifacts}",
            ],
            artifacts / "logs" / f"{stage}.log",
            env=env,
            cwd=source_repository,
        )

        stage = "report"
        finalize_candidate(
            artifacts,
            report_path,
            source_sha=source_sha,
            source_tree=source_tree,
            version=version,
            pipeline_contract=pipeline_contract,
            remotes=remotes,
            checks_head_sha=checks_head_sha,
            checks=checks,
        )
        print(f"[release.candidate] CANDIDATE_READY=true evidence={report_path}")
        return 0
    except (CandidatePipelineError, CandidateReportError, OSError, KeyError) as exc:
        if not previous_ready:
            write_state(
                report_path,
                state_payload(
                    version=version,
                    status="failed",
                    stage=stage,
                    source_sha=source_sha,
                    source_tree=source_tree,
                    pipeline_contract=pipeline_contract,
                    error=str(exc),
                    exit_code=getattr(exc, "exit_code", 1),
                ),
            )
        print(
            f"[release.candidate] FAILED stage={stage} evidence={report_path}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

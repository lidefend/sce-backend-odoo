#!/usr/bin/env python3
"""One-command, fail-closed orchestration for a local immutable RC candidate."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
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
ATTEMPT_ID_ENV = "RELEASE_CANDIDATE_ATTEMPT_ID"
ATTEMPT_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{32}$")


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
        try:
            for line in process.stdout:
                sys.stdout.write(line)
                log.write(line)
        finally:
            process.stdout.close()
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


def new_attempt_id() -> str:
    return f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex}"


def attempt_directory(version_root: Path, attempt_id: str) -> Path:
    if not ATTEMPT_ID.fullmatch(attempt_id):
        raise CandidatePipelineError("attempt ID is invalid")
    attempts = version_root / "attempts"
    if attempts.is_symlink():
        raise CandidatePipelineError("attempts directory must not be a symlink")
    destination = attempts / attempt_id
    if destination.parent != attempts:
        raise CandidatePipelineError("attempt path escapes the version directory")
    if destination.is_symlink():
        raise CandidatePipelineError("attempt directory must not be a symlink")
    return destination


def legacy_attempt_id(report_path: Path) -> str:
    if report_path.is_symlink():
        raise CandidatePipelineError("legacy candidate report must not be a symlink")
    return f"legacy-{hashlib.sha256(report_path.read_bytes()).hexdigest()[:16]}"


def latest_index_path(version_root: Path) -> Path:
    return version_root / "latest.json"


def attempt_report_path(version_root: Path, attempt_id: str) -> Path:
    return attempt_directory(version_root, attempt_id) / "release-report.json"


def load_latest_attempt(version_root: Path) -> dict | None:
    path = latest_index_path(version_root)
    indexed: dict | None = None
    if path.is_symlink():
        raise CandidatePipelineError("candidate latest index must not be a symlink")
    if path.is_file():
        indexed = load_json(path, "candidate latest index")
        relative = indexed.get("report")
        attempt_id = indexed.get("attempt_id")
        if not isinstance(relative, str) or relative != f"attempts/{attempt_id}/release-report.json":
            raise CandidatePipelineError("candidate latest index report path is invalid")
        if not attempt_report_path(version_root, str(attempt_id)).is_file():
            raise CandidatePipelineError("candidate latest index references a missing report")

    reports: list[dict] = []
    attempts = version_root / "attempts"
    if attempts.is_dir() and not attempts.is_symlink():
        for child in attempts.iterdir():
            if child.is_symlink() or not child.is_dir() or not ATTEMPT_ID.fullmatch(child.name):
                raise CandidatePipelineError("candidate attempts directory contains an unsafe entry")
            report_path = child / "release-report.json"
            if report_path.is_symlink():
                raise CandidatePipelineError("candidate attempt report must not be a symlink")
            if report_path.is_file():
                payload = load_json(report_path, "candidate report")
                if payload.get("attempt_id") != child.name:
                    raise CandidatePipelineError("candidate attempt directory/report identity differs")
                reports.append(payload)
    if not reports:
        return indexed
    numbers = [int(item["attempt_number"]) for item in reports]
    if len(numbers) != len(set(numbers)):
        raise CandidatePipelineError("candidate attempt sequence is ambiguous")
    newest = max(reports, key=lambda item: int(item["attempt_number"]))
    return {
        "attempt_id": newest["attempt_id"],
        "report": f"attempts/{newest['attempt_id']}/release-report.json",
        "status": newest["status"],
    }


def write_latest_index(version_root: Path, report: dict) -> None:
    attempt_id = str(report["attempt_id"])
    atomic_write_json(
        latest_index_path(version_root),
        {
            "schema_version": "release_candidate_latest.v1",
            "version": report["source"]["product_version"],
            "attempt_id": attempt_id,
            "report": f"attempts/{attempt_id}/release-report.json",
            "status": report["status"],
            "updated_at": utc_now(),
        },
    )


def select_attempt(version_root: Path, version: str, requested_attempt: str | None) -> tuple[Path, str, int, str | None, bool]:
    """Select an immutable attempt. Only an explicit ID can resume an attempt."""
    latest = load_latest_attempt(version_root)
    if requested_attempt:
        report_path = attempt_report_path(version_root, requested_attempt)
        if report_path.is_symlink():
            raise CandidatePipelineError("requested resume report must not be a symlink")
        if not report_path.is_file():
            raise CandidatePipelineError("requested resume attempt does not exist")
        payload = load_json(report_path, "candidate report")
        if payload.get("attempt_id") != requested_attempt:
            raise CandidatePipelineError("requested resume attempt identity differs")
        if (payload.get("source") or {}).get("product_version") != version:
            raise CandidatePipelineError("requested resume version differs")
        if payload.get("status") != "running":
            raise CandidatePipelineError("terminal candidate attempt cannot be resumed")
        return report_path.parent, requested_attempt, int(payload["attempt_number"]), payload.get("retry_of_attempt_id"), True

    if latest:
        latest_report = load_json(
            attempt_report_path(version_root, str(latest["attempt_id"])),
            "candidate report",
        )
        if latest_report.get("status") == "ready" and latest_report.get("CANDIDATE_READY") is True:
            raise CandidatePipelineError("candidate version is already ready")
        if latest_report.get("status") != "failed":
            raise CandidatePipelineError(
                "non-terminal candidate attempt requires explicit resume"
            )
        retry_of = str(latest_report["attempt_id"])
        number = int(latest_report["attempt_number"]) + 1
    else:
        legacy_report = version_root / "release-report.json"
        retry_of = None
        number = 1
        if legacy_report.is_file():
            legacy = load_json(legacy_report, "legacy candidate report")
            if legacy.get("status") == "ready" and legacy.get("CANDIDATE_READY") is True:
                raise CandidatePipelineError("legacy candidate version is already ready")
            if legacy.get("status") != "failed":
                raise CandidatePipelineError("legacy candidate evidence is not terminal")
            retry_of = legacy_attempt_id(legacy_report)
            number = 2

    attempt_id = new_attempt_id()
    destination = attempt_directory(version_root, attempt_id)
    destination.mkdir(parents=True, exist_ok=False)
    return destination, attempt_id, number, retry_of, False


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


def validate_pipeline_contract_binding(artifacts: Path, contract_sha256: str) -> None:
    path = artifacts / "candidate-contract.sha256"
    if not path.is_file():
        raise CandidatePipelineError("resume candidate tool contract binding is missing")
    if path.read_text(encoding="utf-8").strip() != contract_sha256:
        raise CandidatePipelineError("existing candidate tool contract differs")


def state_payload(
    *,
    attempt_id: str,
    attempt_number: int,
    retry_of_attempt_id: str | None,
    created_at: str,
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
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "retry_of_attempt_id": retry_of_attempt_id,
        "created_at": created_at,
        "finished_at": utc_now() if status in {"failed", "ready"} else None,
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
    if source.is_symlink():
        raise CandidatePipelineError("source repository must not be a symlink")
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
    attempt_id: str,
    version: str,
    source_sha: str,
    source_tree: str,
    pipeline_contract: str,
) -> bool:
    if not path.is_file():
        return False
    payload = load_json(path, "candidate report")
    if payload.get("attempt_id") != attempt_id:
        raise CandidatePipelineError("existing candidate report attempt ID differs")
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
    attempt_id: str,
    attempt_number: int,
    retry_of_attempt_id: str | None,
    created_at: str,
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
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        retry_of_attempt_id=retry_of_attempt_id,
        created_at=created_at,
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

    version_root = artifact_directory(version)
    if version_root.is_symlink():
        raise SystemExit("RELEASE_CANDIDATE_BLOCKED: version directory must not be a symlink")
    try:
        lock_descriptor = acquire_candidate_lock(version_root)
    except CandidatePipelineError as exc:
        print(f"RELEASE_CANDIDATE_BLOCKED: {exc}", file=sys.stderr)
        return exc.exit_code
    requested_attempt = os.environ.get(ATTEMPT_ID_ENV)
    try:
        artifacts, attempt_id, attempt_number, retry_of_attempt_id, resuming = select_attempt(
            version_root, version, requested_attempt
        )
    except (CandidatePipelineError, CandidateReportError, OSError, KeyError, ValueError) as exc:
        print(f"RELEASE_CANDIDATE_BLOCKED: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", 1)
    report_path = artifacts / "release-report.json"
    created_at = utc_now()
    if resuming:
        existing = load_json(report_path, "candidate report")
        created_at = str(existing["created_at"])
    source_sha: str | None = None
    source_tree: str | None = None
    pipeline_contract: str | None = None
    stage = "main_sync"
    env = dict(os.environ)
    synchronized = env.get("RELEASE_CANDIDATE_MAIN_SYNCED") == "1"
    resume_identity_verified = False
    existing_contract: str | None = None

    def payload(status: str, current_stage: str, **extra: object) -> dict:
        return state_payload(
            attempt_id=attempt_id,
            attempt_number=attempt_number,
            retry_of_attempt_id=retry_of_attempt_id,
            created_at=created_at,
            version=version,
            status=status,
            stage=current_stage,
            source_sha=source_sha,
            source_tree=source_tree,
            pipeline_contract=pipeline_contract,
            **extra,
        )

    def persist(state: dict) -> None:
        write_state(report_path, state)
        write_latest_index(version_root, state)

    def finalize(
        current_source_sha: str,
        current_source_tree: str,
        current_pipeline_contract: str,
        remotes: dict[str, str],
        checks_head_sha: str,
        checks: dict[str, str],
    ) -> None:
        finalize_candidate(
            artifacts,
            report_path,
            attempt_id=attempt_id,
            attempt_number=attempt_number,
            retry_of_attempt_id=retry_of_attempt_id,
            created_at=created_at,
            source_sha=current_source_sha,
            source_tree=current_source_tree,
            version=version,
            pipeline_contract=current_pipeline_contract,
            remotes=remotes,
            checks_head_sha=checks_head_sha,
            checks=checks,
        )
        write_latest_index(version_root, load_json(report_path, "candidate report"))

    try:
        if resuming and not synchronized:
            raise CandidatePipelineError(
                "resume requires the already-synchronized attempt process"
            )
        if resuming:
            pipeline_contract = pipeline_contract_sha256()
            existing_source = (load_json(report_path, "candidate report").get("source") or {})
            existing_contract = existing_source.get("pipeline_contract_sha256")
            if existing_contract not in (None, pipeline_contract):
                raise CandidatePipelineError("existing candidate report tool contract differs")

        if not synchronized:
            if command_output(["git", "status", "--porcelain=v1", "--untracked-files=all"]):
                raise CandidatePipelineError("release workspace must be clean before main.sync")
            persist(payload("running", stage))
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
            env[ATTEMPT_ID_ENV] = attempt_id
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
        if resuming and existing_contract is not None:
            validate_pipeline_contract_binding(artifacts, pipeline_contract)
        else:
            bind_pipeline_contract(artifacts, pipeline_contract)
        already_ready = report_matches_identity(
            report_path,
            attempt_id,
            version,
            source_sha,
            source_tree,
            pipeline_contract,
        )
        resume_identity_verified = True
        if already_ready:
            finalize(source_sha, source_tree, pipeline_contract, remotes, checks_head_sha, checks)
            print(f"[release.candidate] CANDIDATE_READY=true evidence={report_path}")
            return 0
        if not resuming:
            persist(payload("running", stage))

        stage = "source_repository_prepare"
        if not resuming:
            persist(payload("running", stage))
        source_repository = prepare_source_repository(
            artifacts,
            source_sha,
            source_tree,
            remotes["github"],
            env=env,
        )
        if resuming:
            persist(payload("running", stage))
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
        persist(payload("running", "scan_sbom"))

        # If a previous attempt completed scan/SBOM but stopped while emitting
        # the report, finish from those verified artifacts without rescanning.
        try:
            finalize(source_sha, source_tree, pipeline_contract, remotes, checks_head_sha, checks)
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
        finalize(source_sha, source_tree, pipeline_contract, remotes, checks_head_sha, checks)
        print(f"[release.candidate] CANDIDATE_READY=true evidence={report_path}")
        return 0
    except (CandidatePipelineError, CandidateReportError, OSError, KeyError) as exc:
        # A resume identity mismatch must leave the existing attempt immutable.
        if not resuming or resume_identity_verified:
            failed = payload(
                "failed",
                stage,
                error=str(exc),
                exit_code=getattr(exc, "exit_code", 1),
            )
            write_state(report_path, failed)
            try:
                write_latest_index(version_root, failed)
            except (CandidateReportError, OSError, KeyError, ValueError):
                pass
        print(
            f"[release.candidate] FAILED stage={stage} evidence={report_path}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

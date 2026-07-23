#!/usr/bin/env python3
"""Resumable, evidence-preserving publication of an immutable release candidate."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from release_candidate_report import atomic_write_json, atomic_write_text


ROOT = Path(__file__).resolve().parents[2]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+$")
ATTEMPT_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{32}$")
REPOSITORY = "lidefend/sce-backend-odoo"
GITHUB_REMOTE = "origin"
GITEE_REMOTE = "gitee-mirror"
REGISTRY_REPOSITORY = "ghcr.io/lidefend/sce-product"
REQUIRED_CHECKS = (
    "public_guard",
    "professional_authorization",
    "professional_quality_gate",
)
TERMINAL_STATES = {
    "PUBLICATION_COMPLETE",
    "FAILED_PREFLIGHT",
    "FAILED_REGISTRY_PUSH",
    "FAILED_TAG_CREATE",
    "FAILED_RELEASE_CREATE",
    "REJECT_IDENTITY_MISMATCH",
    "REJECT_ALREADY_PUBLISHED",
    "REJECT_CONCURRENT_PUBLICATION",
}
RESUMABLE_STATES = {
    "PREFLIGHT_PASSED",
    "REGISTRY_PUSH_IN_PROGRESS",
    "REGISTRY_PUSHED",
    "TAG_CREATE_IN_PROGRESS",
    "TAG_CREATED",
    "RELEASE_CREATE_IN_PROGRESS",
    "FAILED_REGISTRY_PUSH",
    "FAILED_TAG_CREATE",
    "FAILED_RELEASE_CREATE",
}
WORKFLOW_FILES = (
    "make/release.mk",
    "scripts/release/release_publication.py",
    "schemas/release/release_publication_report.v1.schema.json",
    "schemas/release/release_publication_plan.v1.schema.json",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization|token|password|secret)=?[: ]+[^\s]+"),
    re.compile(r"https://[^/@\s]+:[^/@\s]+@"),
    re.compile(r"\b(?:gh[opusr]_|github_pat_)[A-Za-z0-9_]+\b"),
)


class PublicationError(RuntimeError):
    def __init__(self, message: str, *, stage: str = "preflight", exit_code: int = 1):
        super().__init__(message)
        self.stage = stage
        self.exit_code = exit_code


def sanitize_text(value: str) -> str:
    result = value
    for pattern in SECRET_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> dict:
    if path.is_symlink():
        raise PublicationError(f"{label} must not be a symlink")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationError(f"{label} is missing or invalid: {path.name}") from exc
    if not isinstance(payload, dict):
        raise PublicationError(f"{label} must be a JSON object")
    return payload


def validate_version(value: str) -> str:
    if not VERSION.fullmatch(value):
        raise PublicationError("VERSION must match X.Y.Z-rc.N")
    return value


def validate_attempt_id(value: str, label: str) -> str:
    if not ATTEMPT_ID.fullmatch(value):
        raise PublicationError(f"{label} is invalid")
    return value


def validate_source_sha(value: str) -> str:
    if not FULL_SHA.fullmatch(value):
        raise PublicationError("EXPECTED_SOURCE_SHA must be a full lowercase SHA")
    return value


def publication_id() -> str:
    return f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex}"


def workflow_digest(root: Path = ROOT) -> str:
    digest = hashlib.sha256()
    for relative in WORKFLOW_FILES:
        path = root / relative
        if not path.is_file():
            raise PublicationError(f"publication workflow file is missing: {relative}")
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def safe_relative_path(path: Path, parent: Path, label: str) -> str:
    try:
        value = path.relative_to(parent).as_posix()
    except ValueError as exc:
        raise PublicationError(f"{label} escapes the candidate directory") from exc
    if value.startswith("../") or value.startswith("/") or "\x00" in value:
        raise PublicationError(f"{label} is unsafe")
    return value


def candidate_paths(
    version: str, candidate_attempt_id: str, root: Path = ROOT
) -> tuple[Path, Path]:
    version_root = root / "artifacts" / "release" / "candidates" / version
    attempts_root = version_root / "attempts"
    if version_root.is_symlink() or attempts_root.is_symlink():
        raise PublicationError("candidate version/attempts directory must not be a symlink")
    attempt = attempts_root / candidate_attempt_id
    if attempt.parent != attempts_root or attempt.is_symlink() or not attempt.is_dir():
        raise PublicationError("candidate attempt directory is missing or unsafe")
    return version_root, attempt


def candidate_identity(
    version: str,
    candidate_attempt_id: str,
    expected_source_sha: str,
    root: Path = ROOT,
) -> dict:
    version_root, attempt = candidate_paths(
        version, candidate_attempt_id, root=root
    )
    report_path = attempt / "release-report.json"
    report = load_json(report_path, "candidate release report")
    source = report.get("source") or {}
    artifacts = report.get("artifacts") or {}
    hashes = artifacts.get("sha256") or {}
    if (
        report.get("status") != "ready"
        or report.get("CANDIDATE_READY") is not True
        or report.get("attempt_id") != candidate_attempt_id
    ):
        raise PublicationError("candidate attempt is not ready")
    if source.get("product_version") != version:
        raise PublicationError("candidate version differs")
    if source.get("commit_sha") != expected_source_sha:
        raise PublicationError("candidate source SHA differs")
    source_tree = str(source.get("tree_sha") or "")
    if not FULL_SHA.fullmatch(source_tree):
        raise PublicationError("candidate source tree is invalid")
    if source.get("remote_main") != {
        "github": expected_source_sha,
        "gitee": expected_source_sha,
    }:
        raise PublicationError("candidate report dual-remote identity differs")
    if source.get("required_checks") != {
        name: "success" for name in REQUIRED_CHECKS
    }:
        raise PublicationError("candidate report required checks differ")
    if report.get("external_effects") != {
        "registry_push": False,
        "git_tag": False,
        "release_publication": False,
        "deployment": False,
    }:
        raise PublicationError("candidate report external-effect boundary differs")
    if Path(str(artifacts.get("directory") or "")).resolve() != attempt.resolve():
        raise PublicationError("candidate artifact directory identity differs")

    required = {
        "candidate-image.tar",
        "image-manifest.json",
        "sbom.cyclonedx.json",
    }
    if not required.issubset(hashes):
        raise PublicationError("candidate report does not bind required publication evidence")
    verified_hashes: dict[str, str] = {}
    for name, expected in hashes.items():
        if (
            not isinstance(name, str)
            or "/" in name
            or name in {".", ".."}
            or not CHECKSUM.fullmatch(str(expected))
        ):
            raise PublicationError("candidate evidence hash map is unsafe")
        path = attempt / name
        if path.is_symlink() or not path.is_file():
            raise PublicationError(f"candidate evidence is missing or unsafe: {name}")
        actual = sha256_file(path)
        if actual != expected:
            raise PublicationError(f"candidate evidence hash differs: {name}")
        verified_hashes[name] = actual

    manifest = load_json(attempt / "image-manifest.json", "candidate image manifest")
    if (
        manifest.get("schema_version") != 2
        or manifest.get("source_sha") != expected_source_sha
        or manifest.get("source_tree_sha") != source_tree
        or manifest.get("product_version") != version
        or manifest.get("publish_status") != "not_published"
        or manifest.get("image_digest") is not None
        or manifest.get("registry_repository") != REGISTRY_REPOSITORY
    ):
        raise PublicationError("candidate image manifest identity differs")
    tags = manifest.get("image_tags")
    expected_tags = [
        f"{REGISTRY_REPOSITORY}:{version}",
        f"{REGISTRY_REPOSITORY}:sha-{expected_source_sha[:12]}",
    ]
    if tags != expected_tags:
        raise PublicationError("candidate image tags differ")
    local_image_id = str(manifest.get("local_image_id") or "")
    if not DIGEST.fullmatch(local_image_id):
        raise PublicationError("candidate local image ID is invalid")
    report_image = report.get("image") or {}
    if (
        report_image.get("local_image_id") != local_image_id
        or report_image.get("publish_status") != "not_published"
        or report_image.get("tags") != expected_tags
    ):
        raise PublicationError("candidate report/image manifest identity differs")

    return {
        "version_root": version_root,
        "attempt": attempt,
        "report_path": report_path,
        "report_sha256": sha256_file(report_path),
        "source_sha": expected_source_sha,
        "source_tree": source_tree,
        "candidate_tool_contract_sha256": str(
            source.get("pipeline_contract_sha256") or ""
        ),
        "artifact_hashes": verified_hashes,
        "manifest_sha256": verified_hashes["image-manifest.json"],
        "archive_sha256": verified_hashes["candidate-image.tar"],
        "sbom_sha256": verified_hashes["sbom.cyclonedx.json"],
        "local_image_id": local_image_id,
        "image_tags": expected_tags,
        "required_checks": source.get("required_checks") or {},
        "required_checks_head_sha": source.get("required_checks_head_sha"),
    }


def atomic_state(path: Path, payload: dict, *, root: Path = ROOT) -> None:
    schema = load_json(
        root / "schemas" / "release" / "release_publication_report.v1.schema.json",
        "publication report schema",
    )
    Draft202012Validator(schema).validate(payload)
    atomic_write_json(path, payload)


def append_log(path: Path, event: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise PublicationError("publication log must not be a symlink")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{utc_now()} {event}\n")


class ExternalBackend:
    """Real external-system adapter. Tests replace this with an in-memory fake."""

    @staticmethod
    def run(command: list[str], *, cwd: Path = ROOT, env: dict | None = None) -> str:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise PublicationError(
                f"external command failed ({command[0]}): {sanitize_text(detail)}",
                exit_code=completed.returncode,
            )
        return completed.stdout.strip()

    def remote_main(self, remote: str) -> tuple[str, str]:
        output = self.run(["git", "ls-remote", remote, "refs/heads/main"])
        rows = [line.split() for line in output.splitlines() if line.strip()]
        if len(rows) != 1 or not FULL_SHA.fullmatch(rows[0][0]):
            raise PublicationError(f"{remote} main is missing or ambiguous")
        sha = rows[0][0]
        tree = self.run(["git", "rev-parse", f"{sha}^{{tree}}"])
        return sha, tree

    def required_checks(self, head_sha: str) -> dict[str, str]:
        raw = self.run(
            [
                "gh",
                "api",
                f"repos/{REPOSITORY}/commits/{head_sha}/check-runs",
                "-H",
                "Accept: application/vnd.github+json",
            ]
        )
        rows = json.loads(raw).get("check_runs", [])
        results: dict[str, str] = {}
        for name in REQUIRED_CHECKS:
            matching = [row for row in rows if row.get("name") == name]
            if not matching:
                raise PublicationError(f"required check is missing: {name}")
            matching.sort(
                key=lambda row: str(row.get("completed_at") or row.get("started_at") or ""),
                reverse=True,
            )
            selected = matching[0]
            if (
                selected.get("head_sha") not in (None, head_sha)
                or selected.get("status") != "completed"
                or selected.get("conclusion") != "success"
            ):
                raise PublicationError(f"required check did not pass: {name}")
            results[name] = "success"
        return results

    def local_image_id(self, reference: str) -> str:
        return self.run(["docker", "image", "inspect", reference, "--format", "{{.Id}}"])

    def registry_credentials_ready(self) -> bool:
        docker_config = Path(
            os.environ.get("DOCKER_CONFIG", str(Path.home() / ".docker"))
        ) / "config.json"
        try:
            payload = json.loads(docker_config.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        auths = payload.get("auths") if isinstance(payload, dict) else None
        helpers = payload.get("credHelpers") if isinstance(payload, dict) else None
        return bool(
            isinstance(auths, dict)
            and any("ghcr.io" in key for key in auths)
        ) or bool(isinstance(helpers, dict) and "ghcr.io" in helpers)

    def registry_digest(self, reference: str) -> str | None:
        completed = subprocess.run(
            ["docker", "manifest", "inspect", "--verbose", reference],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            detail = (completed.stderr + completed.stdout).lower()
            if any(
                marker in detail
                for marker in (
                    "manifest unknown",
                    "no such manifest",
                    "name unknown",
                    "not found",
                )
            ):
                return None
            raise PublicationError("registry availability/identity preflight failed")
        payload = json.loads(completed.stdout)
        descriptor = payload.get("Descriptor") if isinstance(payload, dict) else None
        digest = str((descriptor or {}).get("digest") or "")
        if not DIGEST.fullmatch(digest):
            raise PublicationError("registry digest is unavailable")
        return digest

    def push_registry(self, references: list[str]) -> str:
        for reference in references:
            self.run(["docker", "push", reference])
        digests = {self.registry_digest(reference) for reference in references}
        if len(digests) != 1 or None in digests:
            raise PublicationError(
                "published registry tags do not resolve to one digest",
                stage="registry_push",
            )
        return str(next(iter(digests)))

    def verify_registry_content(
        self, repository: str, digest: str, expected_local_image_id: str
    ) -> bool:
        reference = f"{repository}@{digest}"
        self.run(["docker", "pull", reference])
        return self.local_image_id(reference) == expected_local_image_id

    def tag_commit(self, remote: str, tag: str) -> str | None:
        output = self.run(
            ["git", "ls-remote", remote, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"]
        )
        if not output:
            return None
        rows = {parts[1]: parts[0] for parts in map(str.split, output.splitlines())}
        peeled = rows.get(f"refs/tags/{tag}^{{}}")
        direct = rows.get(f"refs/tags/{tag}")
        if (
            not peeled
            or not direct
            or not FULL_SHA.fullmatch(peeled)
            or not FULL_SHA.fullmatch(direct)
        ):
            raise PublicationError(f"{remote} tag must be an annotated tag")
        return peeled

    def ensure_tags(
        self, tag: str, source_sha: str, message: str, created_at: str
    ) -> dict[str, str]:
        existing = {
            "github": self.tag_commit(GITHUB_REMOTE, tag),
            "gitee": self.tag_commit(GITEE_REMOTE, tag),
        }
        conflicts = {name: value for name, value in existing.items() if value not in (None, source_sha)}
        if conflicts:
            raise PublicationError("existing tag points to another commit", stage="tag_create")
        missing = [
            remote
            for name, remote in (("github", GITHUB_REMOTE), ("gitee", GITEE_REMOTE))
            if existing[name] is None
        ]
        if missing:
            with tempfile.TemporaryDirectory(prefix="sce-release-tag-") as temporary:
                repo = Path(temporary)
                urls = {
                    GITHUB_REMOTE: self.run(
                        ["git", "remote", "get-url", GITHUB_REMOTE]
                    ),
                    GITEE_REMOTE: self.run(
                        ["git", "remote", "get-url", GITEE_REMOTE]
                    ),
                }
                self.run(["git", "init", "--quiet"], cwd=repo)
                for remote, url in urls.items():
                    self.run(["git", "remote", "add", remote, url], cwd=repo)
                self.run(
                    ["git", "fetch", "--quiet", "--no-tags", GITHUB_REMOTE, source_sha],
                    cwd=repo,
                )
                env = os.environ.copy()
                env.update(
                    {
                        "GIT_AUTHOR_NAME": "SCE Release Automation",
                        "GIT_AUTHOR_EMAIL": "release-automation@users.noreply.github.com",
                        "GIT_COMMITTER_NAME": "SCE Release Automation",
                        "GIT_COMMITTER_EMAIL": "release-automation@users.noreply.github.com",
                        "GIT_COMMITTER_DATE": created_at,
                    }
                )
                self.run(
                    ["git", "tag", "-a", tag, source_sha, "-m", message],
                    cwd=repo,
                    env=env,
                )
                for remote in missing:
                    self.run(["git", "push", remote, f"refs/tags/{tag}"], cwd=repo)
        verified = {
            "github": self.tag_commit(GITHUB_REMOTE, tag),
            "gitee": self.tag_commit(GITEE_REMOTE, tag),
        }
        if set(verified.values()) != {source_sha}:
            raise PublicationError("tag verification failed", stage="tag_create")
        return {key: str(value) for key, value in verified.items()}

    def release(self, tag: str) -> dict | None:
        completed = subprocess.run(
            [
                "gh",
                "release",
                "view",
                tag,
                "--repo",
                REPOSITORY,
                "--json",
                "tagName,isDraft,isPrerelease,url,targetCommitish,body",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            detail = (completed.stderr + completed.stdout).lower()
            if "release not found" in detail or "not found" in detail:
                return None
            raise PublicationError("GitHub Release preflight failed")
        payload = json.loads(completed.stdout)
        return payload if isinstance(payload, dict) else None

    def create_release(self, tag: str, title: str, notes_path: Path) -> dict:
        self.run(
            [
                "gh",
                "release",
                "create",
                tag,
                "--repo",
                REPOSITORY,
                "--verify-tag",
                "--title",
                title,
                "--notes-file",
                str(notes_path),
                "--prerelease",
            ]
        )
        payload = self.release(tag)
        if not payload:
            raise PublicationError("GitHub Release verification failed", stage="release_create")
        return payload


class Publication:
    def __init__(
        self,
        *,
        version: str,
        candidate_attempt_id: str,
        expected_source_sha: str,
        requested_publication_attempt_id: str | None = None,
        backend: ExternalBackend | None = None,
        root: Path = ROOT,
    ):
        self.version = validate_version(version)
        self.candidate_attempt_id = validate_attempt_id(
            candidate_attempt_id, "CANDIDATE_ATTEMPT_ID"
        )
        self.expected_source_sha = validate_source_sha(expected_source_sha)
        self.requested_publication_attempt_id = requested_publication_attempt_id
        if requested_publication_attempt_id:
            validate_attempt_id(
                requested_publication_attempt_id, "PUBLICATION_ATTEMPT_ID"
            )
        self.backend = backend or ExternalBackend()
        self.root = root
        self.identity: dict = {}
        self.attempt_dir: Path | None = None
        self.report_path: Path | None = None
        self.plan_path: Path | None = None
        self.log_path: Path | None = None
        self.state: dict = {}
        self.lock_fd: int | None = None

    @property
    def version_root(self) -> Path:
        return self.root / "artifacts" / "release" / "candidates" / self.version

    @property
    def publications_root(self) -> Path:
        return self.version_root / "publications"

    @property
    def latest_path(self) -> Path:
        return self.publications_root / "latest.json"

    def acquire_lock(self) -> None:
        self.publications_root.mkdir(parents=True, exist_ok=True)
        if self.publications_root.is_symlink():
            raise PublicationError("publications directory must not be a symlink")
        path = self.publications_root / ".publication.lock"
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(descriptor)
            raise PublicationError(
                "publication already running for this version", exit_code=73
            ) from exc
        self.lock_fd = descriptor

    def release_lock(self) -> None:
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None

    def create_or_resume(self) -> None:
        if self.requested_publication_attempt_id:
            attempt_id = self.requested_publication_attempt_id
            attempt = self.publications_root / attempt_id
            if attempt.is_symlink() or attempt.parent != self.publications_root:
                raise PublicationError("publication attempt path is unsafe")
            report = load_json(attempt / "publication-report.json", "publication report")
            if (
                report.get("publication_attempt_id") != attempt_id
                or report.get("state") not in RESUMABLE_STATES
            ):
                raise PublicationError("publication attempt is not safely resumable")
            self.attempt_dir = attempt
            self.report_path = attempt / "publication-report.json"
            self.plan_path = attempt / "publication-plan.json"
            self.log_path = attempt / "logs" / "publication.log"
            self.state = report
            return

        if self.latest_path.is_file():
            latest = load_json(self.latest_path, "publication latest index")
            latest_attempt_id = validate_attempt_id(
                str(latest.get("publication_attempt_id") or ""),
                "latest publication attempt ID",
            )
            previous = load_json(
                self.publications_root
                / latest_attempt_id
                / "publication-report.json",
                "latest publication report",
            )
            if previous.get("state") == "PUBLICATION_COMPLETE":
                if self.same_identity(previous):
                    raise PublicationError(
                        "release version is already published", stage="already_published"
                    )
                raise PublicationError(
                    "completed publication identity conflicts", stage="identity"
                )
            if previous.get("state") in RESUMABLE_STATES:
                raise PublicationError(
                    "incomplete publication requires explicit PUBLICATION_ATTEMPT_ID"
                )

        attempt_id = publication_id()
        attempt = self.publications_root / attempt_id
        attempt.mkdir(parents=True, exist_ok=False)
        (attempt / "logs").mkdir(mode=0o700)
        self.attempt_dir = attempt
        self.report_path = attempt / "publication-report.json"
        self.plan_path = attempt / "publication-plan.json"
        self.log_path = attempt / "logs" / "publication.log"

    def same_identity(self, report: dict) -> bool:
        identity = report.get("identity") or {}
        return (
            identity.get("version") == self.version
            and identity.get("candidate_attempt_id") == self.candidate_attempt_id
            and identity.get("source_sha") == self.expected_source_sha
        )

    def build_plan(self) -> dict:
        identity = candidate_identity(
            self.version,
            self.candidate_attempt_id,
            self.expected_source_sha,
            root=self.root,
        )
        self.identity = identity
        github_sha, github_tree = self.backend.remote_main(GITHUB_REMOTE)
        gitee_sha, gitee_tree = self.backend.remote_main(GITEE_REMOTE)
        if (
            github_sha != self.expected_source_sha
            or gitee_sha != self.expected_source_sha
            or github_tree != identity["source_tree"]
            or gitee_tree != identity["source_tree"]
        ):
            raise PublicationError("GitHub/Gitee main identity differs")
        checks_head = str(identity["required_checks_head_sha"] or "")
        checks = self.backend.required_checks(checks_head)
        if checks != {name: "success" for name in REQUIRED_CHECKS}:
            raise PublicationError("required checks are incomplete")
        if not self.backend.registry_credentials_ready():
            raise PublicationError("registry credentials are not available")
        for reference in identity["image_tags"]:
            if self.backend.registry_digest(reference) is not None:
                raise PublicationError("target registry tag already exists")
        tag = f"v{self.version}"
        for remote in (GITHUB_REMOTE, GITEE_REMOTE):
            if self.backend.tag_commit(remote, tag) is not None:
                raise PublicationError("target Git tag already exists")
        if self.backend.release(tag) is not None:
            raise PublicationError("target GitHub Release already exists")
        for reference in identity["image_tags"]:
            if self.backend.local_image_id(reference) != identity["local_image_id"]:
                raise PublicationError("local candidate image identity differs")

        attempt_id = self.attempt_dir.name
        plan = {
            "schema_version": "release_publication_plan.v1",
            "publication_attempt_id": attempt_id,
            "created_at": utc_now(),
            "identity": {
                "version": self.version,
                "candidate_attempt_id": self.candidate_attempt_id,
                "source_sha": self.expected_source_sha,
                "source_tree": identity["source_tree"],
                "candidate_report_sha256": identity["report_sha256"],
                "candidate_manifest_sha256": identity["manifest_sha256"],
                "candidate_archive_sha256": identity["archive_sha256"],
                "candidate_sbom_sha256": identity["sbom_sha256"],
                "candidate_image_content_id": identity["local_image_id"],
                "candidate_tool_contract_sha256": identity[
                    "candidate_tool_contract_sha256"
                ],
                "publication_workflow_sha256": workflow_digest(self.root),
            },
            "targets": {
                "registry_repository": REGISTRY_REPOSITORY,
                "registry_tags": identity["image_tags"],
                "git_tag": tag,
                "github_repository": REPOSITORY,
                "github_release": tag,
                "gitee_tag": tag,
            },
            "preflight": {
                "github_main": github_sha,
                "gitee_main": gitee_sha,
                "source_tree": github_tree,
                "required_checks": checks,
                "external_targets_absent": True,
                "candidate_evidence_verified": True,
            },
        }
        plan_schema = load_json(
            self.root
            / "schemas"
            / "release"
            / "release_publication_plan.v1.schema.json",
            "publication plan schema",
        )
        Draft202012Validator(plan_schema).validate(plan)
        atomic_write_json(self.plan_path, plan)
        return plan

    def initial_report(self, plan: dict) -> dict:
        now = utc_now()
        return {
            "schema_version": "release_publication_report.v1",
            "publication_attempt_id": self.attempt_dir.name,
            "created_at": now,
            "updated_at": now,
            "finished_at": None,
            "previous_state": None,
            "state": "PLANNED",
            "PUBLICATION_COMPLETE": False,
            "identity": plan["identity"],
            "plan": {
                "path": "publication-plan.json",
                "sha256": sha256_file(self.plan_path),
            },
            "external": {
                "registry": {"digest": None, "tags": []},
                "tags": {"github": None, "gitee": None},
                "release": {"tag": None, "url": None},
            },
            "failure": None,
            "evidence": {"log": "logs/publication.log"},
            "publication_manifest": None,
            "history": [
                {
                    "state": "PLANNED",
                    "previous_state": None,
                    "recorded_at": now,
                }
            ],
        }

    def validate_resume(self) -> dict:
        plan = load_json(self.plan_path, "publication plan")
        identity = candidate_identity(
            self.version,
            self.candidate_attempt_id,
            self.expected_source_sha,
            root=self.root,
        )
        expected = plan.get("identity") or {}
        comparisons = {
            "version": self.version,
            "candidate_attempt_id": self.candidate_attempt_id,
            "source_sha": self.expected_source_sha,
            "source_tree": identity["source_tree"],
            "candidate_report_sha256": identity["report_sha256"],
            "candidate_manifest_sha256": identity["manifest_sha256"],
            "candidate_archive_sha256": identity["archive_sha256"],
            "candidate_sbom_sha256": identity["sbom_sha256"],
            "candidate_image_content_id": identity["local_image_id"],
            "candidate_tool_contract_sha256": identity[
                "candidate_tool_contract_sha256"
            ],
            "publication_workflow_sha256": workflow_digest(self.root),
        }
        if expected != comparisons or self.state.get("identity") != comparisons:
            raise PublicationError(
                "publication resume identity differs", stage="identity"
            )
        self.identity = identity
        return plan

    def transition(self, state: str, **updates) -> None:
        previous = self.state.get("state")
        self.state["previous_state"] = previous
        self.state["state"] = state
        self.state["updated_at"] = utc_now()
        if not state.startswith(("FAILED_", "REJECT_")):
            self.state["failure"] = None
        if state in TERMINAL_STATES:
            self.state["finished_at"] = utc_now()
        self.state.update(updates)
        self.state.setdefault("history", []).append(
            {
                "state": state,
                "previous_state": previous,
                "recorded_at": self.state["updated_at"],
            }
        )
        atomic_state(self.report_path, self.state, root=self.root)
        atomic_write_json(
            self.latest_path,
            {
                "schema_version": "release_publication_latest.v1",
                "version": self.version,
                "publication_attempt_id": self.attempt_dir.name,
                "report": f"{self.attempt_dir.name}/publication-report.json",
                "state": state,
                "updated_at": utc_now(),
            },
        )
        append_log(self.log_path, f"state={state} previous={previous}")

    def release_notes(self, plan: dict, digest: str) -> Path:
        identity = plan["identity"]
        notes = self.attempt_dir / "release-notes.md"
        atomic_write_text(
            notes,
            "\n".join(
                (
                    f"# {self.version}",
                    "",
                    f"- Source SHA: `{identity['source_sha']}`",
                    f"- Source tree: `{identity['source_tree']}`",
                    f"- Candidate attempt: `{identity['candidate_attempt_id']}`",
                    f"- Publication attempt: `{self.attempt_dir.name}`",
                    f"- Image: `{REGISTRY_REPOSITORY}@{digest}`",
                    f"- Candidate report SHA-256: `{identity['candidate_report_sha256']}`",
                    f"- Archive SHA-256: `{identity['candidate_archive_sha256']}`",
                    f"- SBOM SHA-256: `{identity['candidate_sbom_sha256']}`",
                )
            )
            + "\n",
        )
        return notes

    def verify_main_identity(self, plan: dict, *, stage: str) -> None:
        expected_tree = plan["identity"]["source_tree"]
        for remote in (GITHUB_REMOTE, GITEE_REMOTE):
            sha, tree = self.backend.remote_main(remote)
            if (sha, tree) != (self.expected_source_sha, expected_tree):
                raise PublicationError(
                    f"{remote} main moved after publication preflight",
                    stage=stage,
                )

    def write_publication_manifest(self, plan: dict) -> dict:
        path = self.attempt_dir / "publication-manifest.json"
        payload = {
            "schema_version": "release_publication_manifest.v1",
            "publication_attempt_id": self.attempt_dir.name,
            "version": self.version,
            "candidate_attempt_id": self.candidate_attempt_id,
            "source_sha": self.expected_source_sha,
            "source_tree": plan["identity"]["source_tree"],
            "candidate_manifest_sha256": plan["identity"][
                "candidate_manifest_sha256"
            ],
            "candidate_report_sha256": plan["identity"]["candidate_report_sha256"],
            "candidate_archive_sha256": plan["identity"][
                "candidate_archive_sha256"
            ],
            "candidate_sbom_sha256": plan["identity"]["candidate_sbom_sha256"],
            "registry_repository": REGISTRY_REPOSITORY,
            "registry_tags": self.state["external"]["registry"]["tags"],
            "registry_digest": self.state["external"]["registry"]["digest"],
            "github_tag_commit": self.state["external"]["tags"]["github"],
            "gitee_tag_commit": self.state["external"]["tags"]["gitee"],
            "release_tag": self.state["external"]["release"]["tag"],
            "release_url": self.state["external"]["release"]["url"],
            "verified_at": utc_now(),
        }
        if path.is_file():
            existing = load_json(path, "publication manifest")
            comparable = dict(existing)
            comparable.pop("verified_at", None)
            expected = dict(payload)
            expected.pop("verified_at", None)
            if comparable != expected:
                raise PublicationError(
                    "existing publication manifest identity differs",
                    stage="release_create",
                )
        else:
            atomic_write_json(path, payload)
        return {
            "path": "publication-manifest.json",
            "sha256": sha256_file(path),
        }

    def execute(self) -> dict:
        self.acquire_lock()
        try:
            self.create_or_resume()
            if self.requested_publication_attempt_id:
                plan = self.validate_resume()
            else:
                try:
                    plan = self.build_plan()
                    self.state = self.initial_report(plan)
                    atomic_state(self.report_path, self.state, root=self.root)
                    self.transition("PREFLIGHT_PASSED")
                except Exception as exc:
                    if self.report_path and self.attempt_dir:
                        if not self.state:
                            self.state = {
                                "schema_version": "release_publication_report.v1",
                                "publication_attempt_id": self.attempt_dir.name,
                                "created_at": utc_now(),
                                "updated_at": utc_now(),
                                "finished_at": None,
                                "previous_state": None,
                                "state": "PLANNED",
                                "PUBLICATION_COMPLETE": False,
                                "identity": {
                                    "version": self.version,
                                    "candidate_attempt_id": self.candidate_attempt_id,
                                    "source_sha": self.expected_source_sha,
                                },
                                "plan": None,
                                "external": {
                                    "registry": {"digest": None, "tags": []},
                                    "tags": {"github": None, "gitee": None},
                                    "release": {"tag": None, "url": None},
                                },
                                "failure": None,
                                "evidence": {"log": "logs/publication.log"},
                                "publication_manifest": None,
                                "history": [
                                    {
                                        "state": "PLANNED",
                                        "previous_state": None,
                                        "recorded_at": utc_now(),
                                    }
                                ],
                            }
                        self.transition(
                            "FAILED_PREFLIGHT",
                            failure={
                                "stage": "preflight",
                                "message": sanitize_text(str(exc)),
                            },
                        )
                    raise

            current = self.state["state"]
            registry = self.state["external"]["registry"]
            if current in {
                "PREFLIGHT_PASSED",
                "REGISTRY_PUSH_IN_PROGRESS",
                "FAILED_REGISTRY_PUSH",
            }:
                self.verify_main_identity(plan, stage="registry_push")
                self.transition("REGISTRY_PUSH_IN_PROGRESS")
                existing = [
                    self.backend.registry_digest(ref)
                    for ref in self.identity["image_tags"]
                ]
                known = {value for value in existing if value is not None}
                if len(known) > 1:
                    raise PublicationError(
                        "partial registry state resolves to conflicting digests",
                        stage="registry_push",
                    )
                if all(existing) and len(known) == 1:
                    digest = str(existing[0])
                else:
                    missing = [
                        reference
                        for reference, value in zip(
                            self.identity["image_tags"], existing, strict=True
                        )
                        if value is None
                    ]
                    pushed = self.backend.push_registry(missing)
                    if known and pushed not in known:
                        raise PublicationError(
                            "resumed registry tag digest conflicts",
                            stage="registry_push",
                        )
                    digest = str(next(iter(known), pushed))
                if not DIGEST.fullmatch(digest):
                    raise PublicationError(
                        "registry digest is invalid", stage="registry_push"
                    )
                for reference in self.identity["image_tags"]:
                    if self.backend.registry_digest(reference) != digest:
                        raise PublicationError(
                            "registry digest verification failed", stage="registry_push"
                        )
                if not self.backend.verify_registry_content(
                    REGISTRY_REPOSITORY,
                    digest,
                    self.identity["local_image_id"],
                ):
                    raise PublicationError(
                        "registry content does not match candidate image",
                        stage="registry_push",
                    )
                registry = {"digest": digest, "tags": self.identity["image_tags"]}
                external = dict(self.state["external"])
                external["registry"] = registry
                self.transition("REGISTRY_PUSHED", external=external)

            current = self.state["state"]
            if current in {
                "REGISTRY_PUSHED",
                "TAG_CREATE_IN_PROGRESS",
                "FAILED_TAG_CREATE",
            }:
                self.verify_main_identity(plan, stage="tag_create")
                self.transition("TAG_CREATE_IN_PROGRESS")
                tag = plan["targets"]["git_tag"]
                tags = self.backend.ensure_tags(
                    tag,
                    self.expected_source_sha,
                    f"Release {self.version}",
                    self.state["created_at"],
                )
                external = dict(self.state["external"])
                external["tags"] = tags
                self.transition("TAG_CREATED", external=external)

            current = self.state["state"]
            if current in {
                "TAG_CREATED",
                "RELEASE_CREATE_IN_PROGRESS",
                "FAILED_RELEASE_CREATE",
            }:
                self.verify_main_identity(plan, stage="release_create")
                self.transition("RELEASE_CREATE_IN_PROGRESS")
                tag = plan["targets"]["git_tag"]
                release = self.backend.release(tag)
                if release is None:
                    notes = self.release_notes(plan, registry["digest"])
                    release = self.backend.create_release(
                        tag, f"{self.version} release candidate", notes
                    )
                body = str(release.get("body") or "")
                if (
                    release.get("tagName") != tag
                    or release.get("isDraft") is not False
                    or release.get("isPrerelease") is not True
                    or self.expected_source_sha not in body
                    or self.attempt_dir.name not in body
                    or str(registry["digest"]) not in body
                ):
                    raise PublicationError(
                        "GitHub Release identity verification failed",
                        stage="release_create",
                    )
                external = dict(self.state["external"])
                external["release"] = {
                    "tag": tag,
                    "url": str(release.get("url") or ""),
                }
                self.transition("RELEASE_PUBLISHED", external=external)

            if self.state["state"] == "RELEASE_PUBLISHED":
                digest = str(self.state["external"]["registry"]["digest"])
                if not digest or any(
                    self.backend.registry_digest(ref) != digest
                    for ref in self.identity["image_tags"]
                ):
                    raise PublicationError(
                        "final registry verification failed", stage="complete"
                    )
                if not self.backend.verify_registry_content(
                    REGISTRY_REPOSITORY,
                    digest,
                    self.identity["local_image_id"],
                ):
                    raise PublicationError(
                        "final registry content verification failed", stage="complete"
                    )
                tag = plan["targets"]["git_tag"]
                if any(
                    self.backend.tag_commit(remote, tag) != self.expected_source_sha
                    for remote in (GITHUB_REMOTE, GITEE_REMOTE)
                ):
                    raise PublicationError("final tag verification failed", stage="complete")
                if self.backend.release(tag) is None:
                    raise PublicationError(
                        "final Release verification failed", stage="complete"
                    )
                self.state["PUBLICATION_COMPLETE"] = True
                publication_manifest = self.write_publication_manifest(plan)
                self.transition(
                    "PUBLICATION_COMPLETE",
                    publication_manifest=publication_manifest,
                )
            return self.state
        except PublicationError as exc:
            if self.state and self.state.get("state") not in TERMINAL_STATES:
                failure_state = {
                    "registry_push": "FAILED_REGISTRY_PUSH",
                    "tag_create": "FAILED_TAG_CREATE",
                    "release_create": "FAILED_RELEASE_CREATE",
                }.get(exc.stage)
                if failure_state:
                    self.transition(
                        failure_state,
                        failure={
                            "stage": exc.stage,
                            "message": sanitize_text(str(exc)),
                        },
                    )
            raise
        finally:
            self.release_lock()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--candidate-attempt-id", required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--publication-attempt-id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = Publication(
            version=args.version,
            candidate_attempt_id=args.candidate_attempt_id,
            expected_source_sha=args.expected_source_sha,
            requested_publication_attempt_id=args.publication_attempt_id,
        ).execute()
    except PublicationError as exc:
        print(f"[release.publish] BLOCKED stage={exc.stage}: {exc}", file=sys.stderr)
        return exc.exit_code
    print(
        "[release.publish] PUBLICATION_COMPLETE=true "
        f"attempt={report['publication_attempt_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

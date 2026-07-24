#!/usr/bin/env python3
"""Build-workspace, registry, and declaration guards for the frozen RC6 SHA."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CANDIDATE_SHA = "fb1f2b5a6e93fb4d7865023e6cda2961848c3cb8"
SOURCE_TAG = "ghcr.io/lidefend/sce-product:sha-fb1f2b5a6e93"
IMAGE_REPOSITORY = "ghcr.io/lidefend/sce-product"
REMOTE = "https://github.com/lidefend/sce-backend-odoo.git"
DECLARATION_SCHEMA = "sce.rc6_candidate_identity.v1"
DECLARATION_PATH = Path("config/releases/rc6_candidate.json")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
REQUIRED_MERGES = {
    "PR_41": "207334b97310ec0ff2afc28f68ee909df906a540",
    "PR_42": "8962c8e0b831c4ac93e15a6d503740113dcd2c57",
    "PR_43": CANDIDATE_SHA,
}
REQUIRED_CHECKS = {
    "professional_authorization",
    "python310_runtime_compatibility",
    "professional_quality_gate",
    "public_guard",
}
SUPERSESSION_POLICY = (
    "A different SHA or manifest digest requires a new reviewed declaration; "
    "main advancement and rebuilds never mutate this candidate."
)


class FreezeError(RuntimeError):
    """A fail-closed RC6 identity violation."""


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise FreezeError(f"command failed ({' '.join(command[:3])}): {detail}")
    return completed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FreezeError(f"{label} is missing or invalid") from exc
    if not isinstance(payload, dict):
        raise FreezeError(f"{label} must be a JSON object")
    return payload


def atomic_write(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    previous = os.umask(0o077)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".incomplete-", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        os.umask(previous)
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise FreezeError("freeze evidence mode must be 0600")
    return sha256_file(path)


def _git(cwd: Path, *args: str) -> str:
    return run(["git", *args], cwd=cwd).stdout.strip()


def prepare_workspace(target: Path) -> dict:
    target = target.resolve()
    parent = target.parent
    if not parent.is_dir() or parent.is_symlink():
        raise FreezeError("workspace parent must be an existing real directory")
    if target.exists() or target.is_symlink():
        raise FreezeError("frozen candidate workspace target must not exist")
    if target.name != "rc6-identity-freeze-workspace":
        raise FreezeError("frozen candidate workspace name is not approved")
    remote_main = run(["git", "ls-remote", REMOTE, "refs/heads/main"]).stdout.split()
    if not remote_main or remote_main[0] != CANDIDATE_SHA:
        raise FreezeError("authoritative main no longer equals the approved RC6 SHA")
    created = False
    try:
        run(
            [
                "git",
                "clone",
                "--depth=1",
                "--no-tags",
                "--single-branch",
                "--branch",
                "main",
                REMOTE,
                str(target),
            ]
        )
        created = True
        if _git(target, "rev-parse", "HEAD") != CANDIDATE_SHA:
            raise FreezeError("frozen workspace HEAD differs from approved RC6 SHA")
        if _git(target, "remote", "get-url", "origin") != REMOTE:
            raise FreezeError("frozen workspace remote identity differs")
        if _git(target, "status", "--porcelain", "--untracked-files=all"):
            raise FreezeError("frozen workspace is not clean")
        if _git(target, "tag", "--list"):
            raise FreezeError("frozen workspace must contain no tag refs")
        alternates = target / ".git" / "objects" / "info" / "alternates"
        if alternates.exists():
            raise FreezeError("frozen workspace must not borrow Git objects")
        run(
            [
                "python3",
                "scripts/verify/repository_clean_history_guard.py",
                "--local-hygiene",
            ],
            cwd=target,
        )
        return {
            "workspace": str(target),
            "source_sha": CANDIDATE_SHA,
            "source_tree_sha": _git(target, "rev-parse", f"{CANDIDATE_SHA}^{{tree}}"),
            "worktree_clean": True,
            "tags_present": False,
            "alternates_present": False,
            "release_hygiene_pass": True,
        }
    except Exception:
        if created and target.is_dir():
            shutil.rmtree(target)
        raise


def _docker_config_has_ghcr_auth() -> bool:
    config = Path(os.environ.get("DOCKER_CONFIG", str(Path.home() / ".docker")))
    payload = load_json(config / "config.json", "Docker client configuration")
    auths = payload.get("auths") if isinstance(payload, dict) else None
    helpers = payload.get("credHelpers") if isinstance(payload, dict) else None
    return bool(
        isinstance(auths, dict) and any("ghcr.io" in key for key in auths)
    ) or bool(isinstance(helpers, dict) and "ghcr.io" in helpers)


def _manifest_digest(reference: str) -> str | None:
    inspection = _manifest_identity(reference)
    return None if inspection is None else inspection["manifest_digest"]


def _manifest_identity(reference: str) -> dict[str, str] | None:
    completed = run(
        ["docker", "manifest", "inspect", "--verbose", reference], check=False
    )
    if completed.returncode:
        detail = (completed.stderr + completed.stdout).lower()
        if any(
            marker in detail
            for marker in ("manifest unknown", "no such manifest", "not found")
        ):
            return None
        raise FreezeError("registry manifest lookup failed without a not-found result")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise FreezeError("registry manifest response is invalid") from exc
    descriptor = payload.get("Descriptor") if isinstance(payload, dict) else None
    digest = str((descriptor or {}).get("digest") or "")
    if not DIGEST.fullmatch(digest):
        raise FreezeError("registry manifest digest is invalid")
    manifest = payload.get("OCIManifest") if isinstance(payload, dict) else None
    config = manifest.get("config") if isinstance(manifest, dict) else None
    config_digest = str((config or {}).get("digest") or "")
    if not DIGEST.fullmatch(config_digest):
        raise FreezeError("registry manifest config digest is invalid")
    return {
        "manifest_digest": digest,
        "config_digest": config_digest,
    }


def _local_image(reference: str) -> dict:
    payload = json.loads(run(["docker", "image", "inspect", reference]).stdout)
    if not isinstance(payload, list) or len(payload) != 1:
        raise FreezeError("local RC6 image inspection is invalid")
    return payload[0]


def _image_revision(image: dict) -> tuple[str, str]:
    config = image.get("Config") or {}
    revision = str((config.get("Labels") or {}).get("org.opencontainers.image.revision") or "")
    environment = [
        row.split("=", 1)[1]
        for row in (config.get("Env") or [])
        if row.startswith("SC_SOURCE_REVISION=")
    ]
    if revision != CANDIDATE_SHA or environment != [CANDIDATE_SHA]:
        raise FreezeError("image OCI/container revision differs from RC6 candidate SHA")
    image_id = str(image.get("Id") or "")
    if not DIGEST.fullmatch(image_id):
        raise FreezeError("local image config digest is invalid")
    return revision, image_id


def publish_image(artifacts: Path, output: Path) -> dict:
    artifacts = artifacts.resolve()
    manifest_path = artifacts / "image-manifest.json"
    manifest = load_json(manifest_path, "candidate image manifest")
    if manifest.get("source_sha") != CANDIDATE_SHA:
        raise FreezeError("candidate build manifest source SHA differs")
    if manifest.get("image_tags") != [
        "ghcr.io/lidefend/sce-product:1.0.0-rc.5",
        SOURCE_TAG,
    ]:
        raise FreezeError("candidate build tags differ from the approved source build")
    if manifest.get("publish_status") != "not_published":
        raise FreezeError("candidate build manifest must remain pre-publication evidence")
    if not _docker_config_has_ghcr_auth():
        raise FreezeError("Docker client has no configured GHCR credentials")
    local = _local_image(SOURCE_TAG)
    revision, config_digest = _image_revision(local)
    existing = _manifest_digest(SOURCE_TAG)
    if existing is not None:
        raise FreezeError(
            "RC6 source tag already exists; refusing a silent registry replacement"
        )
    pushed = run(["docker", "push", SOURCE_TAG])
    push_digests = set(
        re.findall(r"digest:\s*(sha256:[0-9a-f]{64})", pushed.stdout + pushed.stderr)
    )
    if len(push_digests) != 1:
        raise FreezeError("registry push did not report exactly one manifest digest")
    digest = next(iter(push_digests))
    remote_identity = _manifest_identity(SOURCE_TAG)
    if remote_identity is None or remote_identity["manifest_digest"] != digest:
        raise FreezeError("registry source tag digest verification failed")
    archive_config_digest = str(manifest.get("archive_config_digest") or "")
    if remote_identity["config_digest"] != archive_config_digest:
        raise FreezeError("registry config digest differs from the build archive")
    immutable_ref = f"{IMAGE_REPOSITORY}@{digest}"
    run(["docker", "pull", immutable_ref])
    pulled = _local_image(immutable_ref)
    pulled_revision, pulled_config = _image_revision(pulled)
    if pulled_revision != revision or pulled_config != config_digest:
        raise FreezeError("digest pull does not match the locally built candidate")
    payload = {
        "schema_version": "sce.rc6_candidate_registry_freeze.v1",
        "candidate_name": "RC6",
        "source_sha": CANDIDATE_SHA,
        "source_tree_sha": str(manifest.get("source_tree_sha") or ""),
        "product_version": str(manifest.get("product_version") or ""),
        "source_tag": SOURCE_TAG,
        "image_repository": IMAGE_REPOSITORY,
        "image_manifest_digest": digest,
        "image_ref": immutable_ref,
        "local_daemon_image_id": config_digest,
        "registry_config_digest": remote_identity["config_digest"],
        "oci_revision": revision,
        "container_source_revision": CANDIDATE_SHA,
        "build_time": str(manifest.get("build_time") or ""),
        "frontend_build_sha256": str(manifest.get("frontend_build_sha256") or ""),
        "archive_sha256": str(manifest.get("archive_sha256") or ""),
        "build_manifest_path": str(manifest_path),
        "build_manifest_sha256": sha256_file(manifest_path),
        "movable_image_reference_used": False,
        "version_tag_pushed": False,
        "registry_push_performed": True,
        "digest_pull_verification_pass": True,
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    digest_file = atomic_write(output, payload)
    return {**payload, "freeze_evidence_path": str(output), "freeze_evidence_sha256": digest_file}


def verify_published_image(artifacts: Path, output: Path) -> dict:
    artifacts = artifacts.resolve()
    manifest_path = artifacts / "image-manifest.json"
    manifest = load_json(manifest_path, "candidate image manifest")
    if manifest.get("source_sha") != CANDIDATE_SHA:
        raise FreezeError("candidate build manifest source SHA differs")
    remote_identity = _manifest_identity(SOURCE_TAG)
    if remote_identity is None:
        raise FreezeError("frozen RC6 source tag is absent from the registry")
    archive_config_digest = str(manifest.get("archive_config_digest") or "")
    if remote_identity["config_digest"] != archive_config_digest:
        raise FreezeError("registry config digest differs from the build archive")
    immutable_ref = f"{IMAGE_REPOSITORY}@{remote_identity['manifest_digest']}"
    run(["docker", "pull", immutable_ref])
    pulled = _local_image(immutable_ref)
    revision, local_daemon_image_id = _image_revision(pulled)
    payload = {
        "schema_version": "sce.rc6_candidate_registry_freeze.v1",
        "candidate_name": "RC6",
        "source_sha": CANDIDATE_SHA,
        "source_tree_sha": str(manifest.get("source_tree_sha") or ""),
        "product_version": str(manifest.get("product_version") or ""),
        "source_tag": SOURCE_TAG,
        "image_repository": IMAGE_REPOSITORY,
        "image_manifest_digest": remote_identity["manifest_digest"],
        "image_ref": immutable_ref,
        "local_daemon_image_id": local_daemon_image_id,
        "registry_config_digest": remote_identity["config_digest"],
        "oci_revision": revision,
        "container_source_revision": CANDIDATE_SHA,
        "build_time": str(manifest.get("build_time") or ""),
        "frontend_build_sha256": str(manifest.get("frontend_build_sha256") or ""),
        "archive_sha256": str(manifest.get("archive_sha256") or ""),
        "build_manifest_path": str(manifest_path),
        "build_manifest_sha256": sha256_file(manifest_path),
        "movable_image_reference_used": False,
        "version_tag_pushed": False,
        "registry_push_performed": True,
        "digest_pull_verification_pass": True,
        "manifest_to_config_chain_pass": True,
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    digest_file = atomic_write(output, payload)
    return {**payload, "freeze_evidence_path": str(output), "freeze_evidence_sha256": digest_file}


def validate_declaration(payload: dict) -> dict:
    exact = {
        "schema_version": DECLARATION_SCHEMA,
        "candidate_name": "RC6",
        "source_sha": CANDIDATE_SHA,
        "approval_status": "FROZEN",
        "ci_status": "PASS",
        "image_repository": IMAGE_REPOSITORY,
        "image_revision_label": CANDIDATE_SHA,
        "image_pull_policy": "never",
        "image_locally_available": True,
        "movable_image_reference_used": False,
        "supersession_policy": SUPERSESSION_POLICY,
    }
    for key, expected in exact.items():
        if payload.get(key) != expected:
            raise FreezeError(f"RC6 declaration mismatch: {key}")
    digest = str(payload.get("image_manifest_digest") or "")
    if not DIGEST.fullmatch(digest):
        raise FreezeError("RC6 declaration manifest digest is invalid")
    if payload.get("image_ref") != f"{IMAGE_REPOSITORY}@{digest}":
        raise FreezeError("RC6 declaration image ref is not digest bound")
    if payload.get("required_merge_commits") != REQUIRED_MERGES:
        raise FreezeError("RC6 declaration merge ancestry differs")
    checks = payload.get("ci_checks") or {}
    if set(checks) != REQUIRED_CHECKS or set(checks.values()) != {"success"}:
        raise FreezeError("RC6 declaration required checks differ")
    if not str(payload.get("ci_run_url") or "").startswith(
        "https://github.com/lidefend/sce-backend-odoo/actions/runs/"
    ):
        raise FreezeError("RC6 declaration CI run identity is invalid")
    if not RFC3339_UTC.fullmatch(str(payload.get("freeze_timestamp") or "")):
        raise FreezeError("RC6 declaration freeze timestamp is invalid")
    provenance = payload.get("build_provenance") or {}
    for key in (
        "source_tree_sha",
        "local_daemon_image_id",
        "registry_config_digest",
        "frontend_build_sha256",
        "archive_sha256",
        "build_manifest_sha256",
    ):
        value = str(provenance.get(key) or "")
        pattern = FULL_SHA if key == "source_tree_sha" else (
            DIGEST if key in {"local_daemon_image_id", "registry_config_digest"} else re.compile(r"^[0-9a-f]{64}$")
        )
        if not pattern.fullmatch(value):
            raise FreezeError(f"RC6 declaration build provenance is invalid: {key}")
    return {
        "rc6_candidate_identity_frozen": True,
        "rc6_candidate_sha": CANDIDATE_SHA,
        "rc6_image_ref": payload["image_ref"],
        "oci_revision_match": True,
        "candidate_ci_pass": True,
        "movable_image_reference_used": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "prepare-workspace",
            "publish-image",
            "verify-published",
            "verify-declaration",
        ),
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--declaration", type=Path, default=DECLARATION_PATH)
    args = parser.parse_args()
    if args.action == "prepare-workspace":
        if args.workspace is None:
            raise FreezeError("--workspace is required")
        result = prepare_workspace(args.workspace)
    elif args.action == "publish-image":
        if args.artifacts is None or args.output is None:
            raise FreezeError("--artifacts and --output are required")
        result = publish_image(args.artifacts, args.output)
    elif args.action == "verify-published":
        if args.artifacts is None or args.output is None:
            raise FreezeError("--artifacts and --output are required")
        result = verify_published_image(args.artifacts, args.output)
    else:
        result = validate_declaration(
            load_json(args.declaration, "RC6 candidate declaration")
        )
    print("RC6_CANDIDATE_IDENTITY=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (FreezeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"RC6_CANDIDATE_IDENTITY_ERROR={exc}") from exc

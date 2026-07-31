#!/usr/bin/env python3
"""Stream one verified immutable release image into the sc-prod Docker cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_ROOT = ROOT / "artifacts/release/candidates"
SSH_TARGET = "sc-prod"
CONFIRMATION = "YES_SYNC_VERIFIED_CANDIDATE_IMAGE"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
CONTENT_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_REF = re.compile(
    r"^ghcr\.io/lidefend/sce-product:(?:[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+|sha-[0-9a-f]{12})$"
)


class SyncError(RuntimeError):
    pass


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip()[:600]
        raise SyncError(f"command failed ({command[0]}): {detail}")
    return completed.stdout.strip()


def git(*arguments: str) -> str:
    return run(["git", *arguments])


def preflight(expected_sha: str) -> None:
    if not FULL_SHA.fullmatch(expected_sha):
        raise SyncError("expected live main SHA must be a full lowercase SHA")
    if git("rev-parse", "HEAD") != expected_sha or git("branch", "--show-current") != "main":
        raise SyncError("sync must run from the approved main SHA")
    if git("status", "--porcelain"):
        raise SyncError("sync worktree must be clean")
    for remote in ("origin", "gitee-mirror"):
        lines = git("ls-remote", remote, "refs/heads/main").splitlines()
        if len(lines) != 1 or lines[0].split()[0] != expected_sha:
            raise SyncError(f"{remote} main identity differs")


def archive_config_id(path: Path) -> str:
    try:
        with tarfile.open(path, "r") as archive:
            manifest_member = archive.getmember("manifest.json")
            if not manifest_member.isfile() or manifest_member.size > 1024 * 1024:
                raise SyncError("candidate archive manifest is unsafe")
            manifest_stream = archive.extractfile(manifest_member)
            if manifest_stream is None:
                raise SyncError("candidate archive manifest is unavailable")
            manifest = json.load(manifest_stream)
            if not isinstance(manifest, list) or len(manifest) != 1:
                raise SyncError("candidate archive must contain exactly one image")
            config_name = manifest[0].get("Config") if isinstance(manifest[0], dict) else None
            match = re.fullmatch(r"blobs/sha256/([0-9a-f]{64})", str(config_name or ""))
            if not match:
                raise SyncError("candidate archive config identity is invalid")
            config_member = archive.getmember(str(config_name))
            if not config_member.isfile() or config_member.size > 16 * 1024 * 1024:
                raise SyncError("candidate archive config is unsafe")
            config_stream = archive.extractfile(config_member)
            if config_stream is None:
                raise SyncError("candidate archive config is unavailable")
            observed = hashlib.sha256(config_stream.read()).hexdigest()
    except (KeyError, json.JSONDecodeError, tarfile.TarError, OSError) as exc:
        raise SyncError("candidate archive identity cannot be read") from exc
    if observed != match.group(1):
        raise SyncError("candidate archive config digest differs")
    return "sha256:" + observed


def validate_archive(path: Path, expected_digest: str) -> tuple[Path, str]:
    if not CHECKSUM.fullmatch(expected_digest):
        raise SyncError("candidate archive SHA-256 is invalid")
    if path.is_symlink() or not path.is_file():
        raise SyncError("candidate archive is missing or unsafe")
    resolved = path.resolve()
    try:
        resolved.relative_to(CANDIDATE_ROOT.resolve())
    except ValueError as exc:
        raise SyncError("candidate archive must be under the governed candidate root") from exc
    digest = hashlib.sha256()
    with resolved.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected_digest:
        raise SyncError("candidate archive SHA-256 differs")
    return resolved, archive_config_id(resolved)


def validate_image_identity(image_ref: str, expected_content_id: str) -> None:
    if not IMAGE_REF.fullmatch(image_ref):
        raise SyncError("candidate image reference is outside the governed product namespace")
    if not CONTENT_ID.fullmatch(expected_content_id):
        raise SyncError("candidate image content ID is invalid")
    observed = run(["docker", "image", "inspect", image_ref, "--format", "{{.Id}}"])
    if observed != expected_content_id:
        raise SyncError("local candidate image content ID differs")


def stream_load(archive: Path) -> None:
    with archive.open("rb") as payload:
        completed = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", SSH_TARGET, "docker", "load"],
            cwd=ROOT,
            stdin=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=False,
        )
    if completed.returncode:
        detail = completed.stderr.decode(errors="replace").strip()[:600]
        raise SyncError(f"remote docker load failed: {detail}")


def remote_image_id(image_ref: str) -> str | None:
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", SSH_TARGET, "docker", "image", "inspect", image_ref, "--format", "{{.Id}}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if completed.returncode:
        if "No such image" in completed.stderr:
            return None
        raise SyncError(f"remote image inspection failed: {completed.stderr.strip()[:600]}")
    return completed.stdout.strip()


def synchronize(
    expected_sha: str,
    archive: Path,
    archive_sha256: str,
    image_ref: str,
    content_id: str,
) -> str:
    if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
        raise SyncError("ENV=prod and PROD_DANGER=1 are required")
    if os.environ.get("CONFIRM_PRODUCTION_IMAGE_SYNC") != CONFIRMATION:
        raise SyncError("exact production image synchronization confirmation is required")
    preflight(expected_sha)
    verified_archive, expected_remote_id = validate_archive(archive, archive_sha256)
    validate_image_identity(image_ref, content_id)
    observed = remote_image_id(image_ref)
    if observed != expected_remote_id:
        stream_load(verified_archive)
        observed = remote_image_id(image_ref)
    if observed != expected_remote_id:
        raise SyncError("remote candidate image content ID differs after load")
    return expected_remote_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-live-main-sha", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--content-id", required=True)
    args = parser.parse_args()
    try:
        remote_content_id = synchronize(
            args.expected_live_main_sha,
            args.archive,
            args.archive_sha256,
            args.image_ref,
            args.content_id,
        )
    except SyncError as exc:
        raise SystemExit(f"[production.candidate.image.sync] BLOCKED: {exc}") from exc
    print(
        "[production.candidate.image.sync] PASS "
        f"ref={args.image_ref} local_content_id={args.content_id} "
        f"remote_content_id={remote_content_id} remote={SSH_TARGET}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

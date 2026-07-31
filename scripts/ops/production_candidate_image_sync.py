#!/usr/bin/env python3
"""Stream one verified immutable release image into the sc-prod Docker cache."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
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


def validate_archive(path: Path, expected_digest: str) -> Path:
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
    return resolved


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


def synchronize(
    expected_sha: str,
    archive: Path,
    archive_sha256: str,
    image_ref: str,
    content_id: str,
) -> None:
    if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
        raise SyncError("ENV=prod and PROD_DANGER=1 are required")
    if os.environ.get("CONFIRM_PRODUCTION_IMAGE_SYNC") != CONFIRMATION:
        raise SyncError("exact production image synchronization confirmation is required")
    preflight(expected_sha)
    verified_archive = validate_archive(archive, archive_sha256)
    validate_image_identity(image_ref, content_id)
    stream_load(verified_archive)
    observed = run(
        ["ssh", "-o", "BatchMode=yes", SSH_TARGET, "docker", "image", "inspect", image_ref, "--format", "{{.Id}}"]
    )
    if observed != content_id:
        raise SyncError("remote candidate image content ID differs after load")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-live-main-sha", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--content-id", required=True)
    args = parser.parse_args()
    try:
        synchronize(
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
        f"ref={args.image_ref} content_id={args.content_id} remote={SSH_TARGET}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

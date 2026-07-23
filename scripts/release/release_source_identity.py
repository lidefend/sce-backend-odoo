#!/usr/bin/env python3
"""Fail-closed source and artifact identity checks for formal releases."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Callable


EXPECTED_REPOSITORY = "lidefend/sce-backend-odoo"
EXPECTED_REMOTE_URL = "https://github.com/lidefend/sce-backend-odoo.git"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CommandRunner = Callable[[list[str], Path], str]


class ReleaseIdentityError(ValueError):
    pass


def _run(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def _require_sha(value: str, label: str) -> str:
    value = str(value or "").strip()
    if not FULL_SHA.fullmatch(value):
        raise ReleaseIdentityError(f"{label} must be a full 40-character lowercase commit SHA")
    return value


def validate_repository_identity(
    root: Path,
    source_sha: str,
    *,
    runner: CommandRunner = _run,
) -> dict[str, str]:
    source_sha = _require_sha(source_sha, "SOURCE_SHA")
    root = root.resolve()
    remote_url = runner(["git", "remote", "get-url", "origin"], root)
    if remote_url != EXPECTED_REMOTE_URL:
        raise ReleaseIdentityError(
            f"origin must be {EXPECTED_REMOTE_URL} for {EXPECTED_REPOSITORY}; got {remote_url or '<missing>'}"
        )
    worktree = runner(["git", "status", "--porcelain", "--untracked-files=all"], root)
    if worktree:
        raise ReleaseIdentityError("formal release worktree must be clean")
    head_sha = _require_sha(runner(["git", "rev-parse", "HEAD"], root), "Git HEAD")
    remote_line = runner(["git", "ls-remote", "origin", "refs/heads/main"], root)
    remote_sha = _require_sha(remote_line.split()[0] if remote_line else "", "origin/main")
    if len({source_sha, head_sha, remote_sha}) != 1:
        raise ReleaseIdentityError(
            f"release identity mismatch SOURCE_SHA={source_sha} HEAD={head_sha} origin/main={remote_sha}"
        )
    return {
        "repository": EXPECTED_REPOSITORY,
        "remote_url": remote_url,
        "source_sha": source_sha,
        "head_sha": head_sha,
        "remote_main_sha": remote_sha,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest_checksum(manifest_path: Path, checksum_path: Path) -> None:
    try:
        expected = checksum_path.read_text(encoding="utf-8").strip().split()[0]
    except (OSError, IndexError) as exc:
        raise ReleaseIdentityError("release manifest checksum is missing or invalid") from exc
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or sha256_file(manifest_path) != expected:
        raise ReleaseIdentityError("release manifest checksum mismatch")


def validate_artifact_identity(
    *,
    expected_sha: str,
    expected_image_digest: str,
    image_manifest: dict,
    release_manifest: dict,
    oci_revision: str,
    container_revision: str,
    actual_image_digest: str,
) -> dict[str, str]:
    expected_sha = _require_sha(expected_sha, "EXPECTED_RELEASE_SHA")
    revisions = {
        "image manifest source SHA": image_manifest.get("source_sha", ""),
        "image manifest OCI revision": image_manifest.get("oci_revision", ""),
        "image manifest container revision": image_manifest.get("container_source_revision", ""),
        "release manifest source SHA": release_manifest.get("source_sha", ""),
        "release manifest OCI revision": release_manifest.get("oci_revision", ""),
        "OCI revision": oci_revision,
        "container revision": container_revision,
    }
    for label, value in revisions.items():
        if _require_sha(str(value or ""), label) != expected_sha:
            raise ReleaseIdentityError(f"{label} does not match EXPECTED_RELEASE_SHA")

    expected_image_digest = str(expected_image_digest or "").strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", expected_image_digest):
        raise ReleaseIdentityError("EXPECTED_IMAGE_DIGEST must be a sha256 digest")
    digests = {
        "actual image digest": actual_image_digest,
        "image manifest digest": image_manifest.get("image_digest", ""),
        "release manifest digest": release_manifest.get("image_digest", ""),
    }
    for label, value in digests.items():
        if str(value or "").strip() != expected_image_digest:
            raise ReleaseIdentityError(f"{label} does not match EXPECTED_IMAGE_DIGEST")
    return {"source_sha": expected_sha, "image_digest": expected_image_digest}


def _load_json(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseIdentityError(f"{label} is missing or invalid") from exc
    if not isinstance(payload, dict):
        raise ReleaseIdentityError(f"{label} must be a JSON object")
    return payload


def _inspect_image(image: str) -> dict:
    completed = subprocess.run(
        ["docker", "image", "inspect", image], check=True, text=True, capture_output=True
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise ReleaseIdentityError("candidate image inspection returned an invalid payload")
    return payload[0]


def _container_revision(image_payload: dict) -> str:
    env_rows = ((image_payload.get("Config") or {}).get("Env") or [])
    values = [row.split("=", 1)[1] for row in env_rows if row.startswith("SC_SOURCE_REVISION=")]
    if len(values) != 1:
        raise ReleaseIdentityError("candidate image must contain exactly one SC_SOURCE_REVISION")
    return values[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    source = subparsers.add_parser("source-preflight")
    source.add_argument("--root", type=Path, default=Path.cwd())
    source.add_argument("--source-sha", required=True)

    artifact = subparsers.add_parser("artifact-preflight")
    artifact.add_argument("--image", required=True)
    artifact.add_argument("--image-manifest", required=True, type=Path)
    artifact.add_argument("--release-manifest", required=True, type=Path)
    artifact.add_argument("--release-manifest-checksum", required=True, type=Path)
    artifact.add_argument("--expected-release-sha", required=True)
    artifact.add_argument("--expected-image-digest", required=True)
    args = parser.parse_args()

    try:
        if args.command == "source-preflight":
            result = validate_repository_identity(args.root, args.source_sha)
        else:
            validate_manifest_checksum(args.release_manifest, args.release_manifest_checksum)
            image_manifest = _load_json(args.image_manifest, "image manifest")
            release_manifest = _load_json(args.release_manifest, "release manifest")
            image_payload = _inspect_image(args.image)
            config = image_payload.get("Config") or {}
            result = validate_artifact_identity(
                expected_sha=args.expected_release_sha,
                expected_image_digest=args.expected_image_digest,
                image_manifest=image_manifest,
                release_manifest=release_manifest,
                oci_revision=str((config.get("Labels") or {}).get("org.opencontainers.image.revision") or ""),
                container_revision=_container_revision(image_payload),
                actual_image_digest=str(image_payload.get("Id") or ""),
            )
    except (ReleaseIdentityError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise SystemExit(f"[release.identity] BLOCKED: {exc}") from exc
    print("[release.identity] PASS " + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

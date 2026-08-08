#!/usr/bin/env python3
"""Import one verified local candidate archive into the daily acceptance host."""

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
CONFIRMATION = "IMPORT_VERIFIED_CANDIDATE_TO_DAILY_ACCEPTANCE"
DAILY_HOST = "sc-root"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
CONTENT_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_REF = re.compile(
    r"^ghcr\.io/lidefend/sce-product:(?:[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+|sha-[0-9a-f]{12})$"
)


class ImportError(RuntimeError):
    pass


def run(command: list[str]) -> str:
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
        raise ImportError(f"command failed ({command[0]}): {detail[:500]}")
    return completed.stdout.strip()


def git(*arguments: str) -> str:
    return run(["git", *arguments])


def preflight(expected_sha: str, host: str) -> None:
    if not FULL_SHA.fullmatch(expected_sha):
        raise ImportError("expected main SHA must be a full lowercase SHA")
    if host != DAILY_HOST:
        raise ImportError("daily acceptance import is restricted to sc-root")
    if git("branch", "--show-current") != "main" or git("rev-parse", "HEAD") != expected_sha:
        raise ImportError("import must run from the approved main SHA")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ImportError("import worktree must be clean")
    for remote in ("origin", "gitee-mirror"):
        rows = git("ls-remote", remote, "refs/heads/main").splitlines()
        if len(rows) != 1 or rows[0].split()[0] != expected_sha:
            raise ImportError(f"{remote} main identity differs")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_archive(path: Path, expected_sha256: str, image_ref: str) -> tuple[Path, str]:
    if not CHECKSUM.fullmatch(expected_sha256):
        raise ImportError("candidate archive SHA-256 is invalid")
    if path.is_symlink() or not path.is_file():
        raise ImportError("candidate archive is missing or unsafe")
    resolved = path.resolve()
    try:
        resolved.relative_to(CANDIDATE_ROOT.resolve())
    except ValueError as exc:
        raise ImportError("candidate archive must be under the governed candidate root") from exc
    if sha256_file(resolved) != expected_sha256:
        raise ImportError("candidate archive SHA-256 differs")
    try:
        with tarfile.open(resolved, "r") as archive:
            manifest_stream = archive.extractfile("manifest.json")
            if manifest_stream is None:
                raise ImportError("candidate archive manifest is unavailable")
            manifest = json.load(manifest_stream)
            if not isinstance(manifest, list) or len(manifest) != 1:
                raise ImportError("candidate archive must contain exactly one image")
            row = manifest[0]
            tags = row.get("RepoTags") if isinstance(row, dict) else None
            if not isinstance(tags, list) or image_ref not in tags:
                raise ImportError("candidate archive does not bind the requested image reference")
            config_name = str(row.get("Config") or "")
            match = re.fullmatch(r"blobs/sha256/([0-9a-f]{64})", config_name)
            if not match:
                raise ImportError("candidate archive config identity is invalid")
            config_stream = archive.extractfile(config_name)
            if config_stream is None:
                raise ImportError("candidate archive config is unavailable")
            observed = hashlib.sha256(config_stream.read()).hexdigest()
    except (KeyError, json.JSONDecodeError, tarfile.TarError, OSError) as exc:
        raise ImportError("candidate archive identity cannot be read") from exc
    if observed != match.group(1):
        raise ImportError("candidate archive config digest differs")
    return resolved, f"sha256:{observed}"


def validate_local_image(image_ref: str, content_id: str, source_sha: str) -> None:
    if not IMAGE_REF.fullmatch(image_ref) or not CONTENT_ID.fullmatch(content_id):
        raise ImportError("candidate image identity is invalid")
    observed = run(
        [
            "docker", "image", "inspect", image_ref,
            "--format", '{{.Id}}|{{index .Config.Labels "org.opencontainers.image.revision"}}',
        ]
    )
    if observed != f"{content_id}|{source_sha}":
        raise ImportError("local candidate image identity differs")


def remote_identity(host: str, image_ref: str) -> str | None:
    completed = subprocess.run(
        [
            "ssh", "-o", "BatchMode=yes", host, "docker", "image", "inspect", image_ref,
            "--format", '{{.Id}}|{{index .Config.Labels "org.opencontainers.image.revision"}}',
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        if "No such image" in completed.stderr:
            return None
        raise ImportError(f"daily image inspection failed: {completed.stderr.strip()[:500]}")
    return completed.stdout.strip()


def stream_load(host: str, archive: Path) -> None:
    with archive.open("rb") as payload:
        completed = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", host, "docker", "load"],
            cwd=ROOT,
            stdin=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if completed.returncode:
        detail = completed.stderr.decode(errors="replace").strip()
        raise ImportError(f"daily docker load failed: {detail[:500]}")


def import_candidate(
    *, expected_sha: str, archive: Path, archive_sha256: str, image_ref: str,
    local_content_id: str, remote_config_id: str, host: str,
) -> str:
    if os.environ.get("CONFIRM_DAILY_ACCEPTANCE_CANDIDATE_IMPORT") != CONFIRMATION:
        raise ImportError("exact daily acceptance candidate import confirmation is required")
    if not CONTENT_ID.fullmatch(remote_config_id):
        raise ImportError("remote config identity is invalid")
    preflight(expected_sha, host)
    verified_archive, archive_config_id = validate_archive(archive, archive_sha256, image_ref)
    if archive_config_id != remote_config_id:
        raise ImportError("declared remote config identity differs from archive")
    validate_local_image(image_ref, local_content_id, expected_sha)
    expected_remote = f"{remote_config_id}|{expected_sha}"
    observed = remote_identity(host, image_ref)
    if observed != expected_remote:
        stream_load(host, verified_archive)
        observed = remote_identity(host, image_ref)
    if observed != expected_remote:
        raise ImportError("daily candidate identity differs after import")
    return observed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-main-sha", required=True)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--local-content-id", required=True)
    parser.add_argument("--remote-config-id", required=True)
    parser.add_argument("--host", required=True)
    args = parser.parse_args()
    try:
        identity = import_candidate(
            expected_sha=args.expected_main_sha,
            archive=args.archive,
            archive_sha256=args.archive_sha256,
            image_ref=args.image_ref,
            local_content_id=args.local_content_id,
            remote_config_id=args.remote_config_id,
            host=args.host,
        )
    except ImportError as exc:
        raise SystemExit(f"[daily.acceptance.candidate.import] BLOCKED: {exc}") from exc
    print(
        "[daily.acceptance.candidate.import] PASS "
        f"host={args.host} image={args.image_ref} identity={identity} production_writes=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Atomically synchronize one verified candidate manifest set to sc-prod."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shlex
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECURE_ROOT = ROOT.parent / ".secure"
SSH_TARGET = "sc-prod"
CONFIRMATION = "YES_SYNC_VERIFIED_CANDIDATE_MANIFESTS"
FILES = ("image-manifest.json", "product-release-manifest.json", "product-release-manifest.sha256")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+$")


class SyncError(RuntimeError):
    pass


REMOTE_INSTALL = r'''
import fcntl, hashlib, io, json, os, shutil, stat, sys, tarfile, tempfile
from pathlib import Path

version, source_sha, image_digest, expected_json = sys.argv[1:]
expected = json.loads(expected_json)
root = Path("/opt/sce/candidates")
target = root / ("v" + version)
lock_path = Path("/run/lock/sc_production-candidate-manifest-sync.lock")
payload = sys.stdin.buffer.read()
names = {"image-manifest.json", "product-release-manifest.json", "product-release-manifest.sha256"}

def verify(directory):
    if directory.is_symlink() or not directory.is_dir():
        return False
    if {item.name for item in directory.iterdir()} != names:
        return False
    for name in names:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            return False
    return True

root.mkdir(parents=True, exist_ok=True, mode=0o755)
lock_path.parent.mkdir(parents=True, exist_ok=True)
with lock_path.open("a+b") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("[production.candidate.manifest.sync] BLOCKED concurrent sync")
    if target.exists() or target.is_symlink():
        if not verify(target):
            raise SystemExit("[production.candidate.manifest.sync] BLOCKED immutable target differs")
        print(json.dumps({"status":"PASS","changed":False,"target":str(target),
                          "source_sha":source_sha,"image_digest":image_digest}))
        raise SystemExit(0)
    staging = Path(tempfile.mkdtemp(prefix=".incomplete-v" + version + "-", dir=root))
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
            members = archive.getmembers()
            if {member.name for member in members} != names or any(not member.isfile() for member in members):
                raise SystemExit("[production.candidate.manifest.sync] BLOCKED payload inventory differs")
            for member in members:
                stream = archive.extractfile(member)
                if stream is None:
                    raise SystemExit("[production.candidate.manifest.sync] BLOCKED payload member missing")
                data = stream.read()
                if hashlib.sha256(data).hexdigest() != expected[member.name]:
                    raise SystemExit("[production.candidate.manifest.sync] BLOCKED payload digest differs")
                path = staging / member.name
                path.write_bytes(data)
                os.chown(path, 0, 0)
                path.chmod(0o444)
        os.chown(staging, 0, 0)
        staging.chmod(0o755)
        if not verify(staging):
            raise SystemExit("[production.candidate.manifest.sync] BLOCKED staged manifests differ")
        os.replace(staging, target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(json.dumps({"status":"PASS","changed":True,"target":str(target),
                      "source_sha":source_sha,"image_digest":image_digest}))
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, input_bytes: bytes | None = None) -> str:
    completed = subprocess.run(
        command, cwd=ROOT, input=input_bytes, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        raise SyncError(f"command failed ({command[0]}): {completed.stderr.decode(errors='replace').strip()[:600]}")
    return completed.stdout.decode().strip()


def git(*arguments: str) -> str:
    return run(["git", *arguments])


def preflight(expected_main_sha: str) -> None:
    if not FULL_SHA.fullmatch(expected_main_sha):
        raise SyncError("expected live main SHA must be a full lowercase SHA")
    if git("rev-parse", "HEAD") != expected_main_sha or git("branch", "--show-current") != "main":
        raise SyncError("sync must run from the approved main SHA")
    if git("status", "--porcelain"):
        raise SyncError("sync worktree must be clean")
    for remote in ("origin", "gitee-mirror"):
        lines = git("ls-remote", remote, "refs/heads/main").splitlines()
        if len(lines) != 1 or lines[0].split()[0] != expected_main_sha:
            raise SyncError(f"{remote} main identity differs")


def validate(directory: Path, source_sha: str, image_digest: str, version: str) -> dict[str, str]:
    if not FULL_SHA.fullmatch(source_sha) or not DIGEST.fullmatch(image_digest) or not VERSION.fullmatch(version):
        raise SyncError("candidate identity is invalid")
    if directory.is_symlink() or not directory.is_dir():
        raise SyncError("candidate manifest directory is missing or unsafe")
    resolved = directory.resolve()
    try:
        resolved.relative_to(SECURE_ROOT.resolve())
    except ValueError as exc:
        raise SyncError("candidate manifests must come from the secure artifact root") from exc
    paths = {name: resolved / name for name in FILES}
    if any(path.is_symlink() or not path.is_file() for path in paths.values()):
        raise SyncError("candidate manifest inventory is incomplete or unsafe")
    try:
        image = json.loads(paths["image-manifest.json"].read_text())
        release = json.loads(paths["product-release-manifest.json"].read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError("candidate manifest JSON is invalid") from exc
    expected_ref = f"ghcr.io/lidefend/sce-product@{image_digest}"
    for payload in (image, release):
        if payload.get("source_sha") != source_sha or payload.get("image_digest") != image_digest:
            raise SyncError("candidate manifest source or image identity differs")
    if image.get("product_version") != version:
        raise SyncError("image manifest version differs")
    if release.get("release_version") != version or release.get("registry_repository") != "ghcr.io/lidefend/sce-product":
        raise SyncError("release manifest version or repository differs")
    if release.get("registry_refs") != [expected_ref, expected_ref]:
        raise SyncError("release manifest registry refs differ")
    checksum = paths["product-release-manifest.sha256"].read_text()
    if checksum != f"{sha256(paths['product-release-manifest.json'])}  product-release-manifest.json\n":
        raise SyncError("release manifest checksum contract differs")
    return {name: sha256(path) for name, path in paths.items()}


def payload(directory: Path) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name in FILES:
            data = (directory / name).read_bytes()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o444
            archive.addfile(member, io.BytesIO(data))
    return output.getvalue()


def synchronize(expected_main_sha: str, directory: Path, source_sha: str, image_digest: str, version: str) -> dict:
    if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
        raise SyncError("ENV=prod and PROD_DANGER=1 are required")
    if os.environ.get("CONFIRM_PRODUCTION_CANDIDATE_MANIFEST_SYNC") != CONFIRMATION:
        raise SyncError("exact candidate manifest synchronization confirmation is required")
    preflight(expected_main_sha)
    expected = validate(directory, source_sha, image_digest, version)
    command = " ".join(shlex.quote(item) for item in (
        "python3", "-c", REMOTE_INSTALL, version, source_sha, image_digest,
        json.dumps(expected, sort_keys=True, separators=(",", ":")),
    ))
    output = run(["ssh", "-o", "BatchMode=yes", SSH_TARGET, command], input_bytes=payload(directory.resolve()))
    try:
        result = json.loads(output.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise SyncError("remote synchronization evidence is invalid") from exc
    if result.get("status") != "PASS" or result.get("source_sha") != source_sha or result.get("image_digest") != image_digest:
        raise SyncError("remote synchronization evidence differs")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-live-main-sha", required=True)
    parser.add_argument("--manifest-directory", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        result = synchronize(args.expected_live_main_sha, args.manifest_directory, args.source_sha, args.image_digest, args.version)
    except SyncError as exc:
        raise SystemExit(f"[production.candidate.manifest.sync] BLOCKED: {exc}") from exc
    print("[production.candidate.manifest.sync] PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

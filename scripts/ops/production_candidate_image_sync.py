#!/usr/bin/env python3
"""Stream one verified immutable release image into the sc-prod Docker cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
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
OCI_BLOB = re.compile(r"^blobs/sha256/([0-9a-f]{64})$")
OCI_METADATA = frozenset({"index.json", "manifest.json", "oci-layout"})
REMOTE_CACHE_ROOT = "/data/backups/sc_candidate_image_blob_cache"


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


def extract_oci_layout(archive: Path, destination: Path) -> tuple[int, int]:
    blob_count = 0
    total_bytes = 0
    seen_metadata: set[str] = set()
    try:
        with tarfile.open(archive, "r") as source:
            for member in source:
                name = member.name.rstrip("/")
                if name in {"blobs", "blobs/sha256"} and member.isdir():
                    continue
                blob_match = OCI_BLOB.fullmatch(name)
                if name not in OCI_METADATA and blob_match is None:
                    raise SyncError(f"candidate archive contains an unsafe OCI member: {member.name}")
                if not member.isfile() or member.issym() or member.islnk():
                    raise SyncError(f"candidate OCI member must be a regular file: {member.name}")
                stream = source.extractfile(member)
                if stream is None:
                    raise SyncError(f"candidate OCI member is unreadable: {member.name}")
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with target.open("wb") as output:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        output.write(block)
                        digest.update(block)
                        total_bytes += len(block)
                os.chmod(target, member.mode & 0o777)
                os.utime(target, (member.mtime, member.mtime))
                if blob_match:
                    if digest.hexdigest() != blob_match.group(1):
                        raise SyncError(f"candidate OCI blob digest differs: {member.name}")
                    blob_count += 1
                else:
                    seen_metadata.add(name)
    except (tarfile.TarError, OSError) as exc:
        raise SyncError("candidate OCI layout cannot be extracted") from exc
    if seen_metadata != OCI_METADATA or blob_count == 0:
        raise SyncError("candidate OCI layout is incomplete")
    return blob_count, total_bytes


def remote_cache_has_latest() -> bool:
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", SSH_TARGET, "test", "-d", f"{REMOTE_CACHE_ROOT}/latest/blobs/sha256"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def stream_load(archive: Path, remote_config_id: str) -> dict[str, int]:
    config_digest = remote_config_id.removeprefix("sha256:")
    if not CHECKSUM.fullmatch(config_digest):
        raise SyncError("incremental cache config identity is invalid")
    remote_directory = f"{REMOTE_CACHE_ROOT}/{config_digest}"
    with tempfile.TemporaryDirectory(prefix="sce-production-candidate-oci-") as temporary:
        layout = Path(temporary)
        blob_count, layout_bytes = extract_oci_layout(archive, layout)
        run(["ssh", "-o", "BatchMode=yes", SSH_TARGET, f"install -d -m 0700 {shlex.quote(remote_directory)}"])
        command = ["rsync", "--archive", "--checksum", "--partial", "--delete", "--stats"]
        if remote_cache_has_latest():
            command.append(f"--link-dest={REMOTE_CACHE_ROOT}/latest")
        command.extend([f"{layout}/", f"{SSH_TARGET}:{remote_directory}/"])
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
        if completed.returncode:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise SyncError(f"incremental candidate transfer failed: {detail[:600]}")
        match = re.search(r"Total transferred file size:\s*([0-9.,]+)\s*bytes", completed.stdout)
        transferred_bytes = int((match.group(1) if match else "0").replace(",", "").split(".")[0])

    load_command = (
        f"set -euo pipefail; root={shlex.quote(remote_directory)}; "
        "test -s \"$root/index.json\"; test -s \"$root/manifest.json\"; test -s \"$root/oci-layout\"; "
        "checks=$(mktemp); trap 'rm -f \"$checks\"' EXIT; cd \"$root/blobs/sha256\"; count=0; "
        "for blob in *; do [[ \"$blob\" =~ ^[0-9a-f]{64}$ ]]; test -f \"$blob\"; "
        "printf '%s  %s\\n' \"$blob\" \"$blob\" >>\"$checks\"; count=$((count+1)); done; "
        "test \"$count\" -gt 0; sha256sum -c \"$checks\" >/dev/null; "
        "tar -C \"$root\" -cf - . | docker load >/dev/null"
    )
    run(["ssh", "-o", "BatchMode=yes", SSH_TARGET, f"bash -c {shlex.quote(load_command)}"])
    promote_script = (
        "import os,pathlib,re,shutil,sys; root=pathlib.Path(sys.argv[1]); digest=sys.argv[2]; "
        "link=root/'latest.next'; link.unlink(missing_ok=True); link.symlink_to(digest); "
        "os.replace(link,root/'latest'); [shutil.rmtree(p) for p in root.iterdir() if p.is_dir() and "
        "re.fullmatch(r'[0-9a-f]{64}',p.name) and p.name!=digest]"
    )
    run(["ssh", "-o", "BatchMode=yes", SSH_TARGET, shlex.join(["python3", "-c", promote_script, REMOTE_CACHE_ROOT, config_digest])])
    return {"blob_count": blob_count, "layout_bytes": layout_bytes, "transferred_bytes": transferred_bytes}


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


def digest_reference(image_ref: str, image_digest: str) -> str:
    if not CONTENT_ID.fullmatch(image_digest):
        raise SyncError("published image digest is invalid")
    repository, separator, _tag = image_ref.rpartition(":")
    if not separator or repository != "ghcr.io/lidefend/sce-product":
        raise SyncError("candidate image repository is invalid")
    return f"{repository}@{image_digest}"


def pull_remote_digest(reference: str) -> None:
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", SSH_TARGET, "docker", "pull", reference],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise SyncError(f"remote registry digest pull failed: {detail[:600]}")


def synchronize(
    expected_sha: str,
    archive: Path,
    archive_sha256: str,
    image_ref: str,
    content_id: str,
    image_digest: str,
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
        transfer = stream_load(verified_archive, expected_remote_id)
        observed = remote_image_id(image_ref)
    else:
        transfer = {"blob_count": 0, "layout_bytes": 0, "transferred_bytes": 0}
    if observed != expected_remote_id:
        raise SyncError("remote candidate image content ID differs after load")
    published_reference = digest_reference(image_ref, image_digest)
    published_id = remote_image_id(published_reference)
    if published_id != expected_remote_id:
        pull_remote_digest(published_reference)
        published_id = remote_image_id(published_reference)
    if published_id != expected_remote_id:
        raise SyncError("published digest does not resolve to the archived candidate")
    synchronize.last_transfer = transfer
    return expected_remote_id


synchronize.last_transfer = {"blob_count": 0, "layout_bytes": 0, "transferred_bytes": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-live-main-sha", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--image-digest", required=True)
    args = parser.parse_args()
    try:
        remote_content_id = synchronize(
            args.expected_live_main_sha,
            args.archive,
            args.archive_sha256,
            args.image_ref,
            args.content_id,
            args.image_digest,
        )
    except SyncError as exc:
        raise SystemExit(f"[production.candidate.image.sync] BLOCKED: {exc}") from exc
    print(
        "[production.candidate.image.sync] PASS "
        f"ref={args.image_ref} local_content_id={args.content_id} "
        f"registry_digest={args.image_digest} remote_content_id={remote_content_id} "
        f"transfer={json.dumps(synchronize.last_transfer, sort_keys=True)} remote={SSH_TARGET}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

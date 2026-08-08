#!/usr/bin/env python3
"""Import one verified local candidate archive into the daily acceptance host."""

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
CONFIRMATION = "IMPORT_VERIFIED_CANDIDATE_TO_DAILY_ACCEPTANCE"
DAILY_HOST = "sc-root"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
CONTENT_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_REF = re.compile(
    r"^ghcr\.io/lidefend/sce-product:(?:[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+|sha-[0-9a-f]{12})$"
)
OCI_BLOB = re.compile(r"^blobs/sha256/([0-9a-f]{64})$")
OCI_METADATA = frozenset({"index.json", "manifest.json", "oci-layout"})
REMOTE_CACHE_ROOT = "/data/backups/sc_candidate_image_blob_cache"


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


def preflight(expected_sha: str, host: str, allow_boundary_head: bool = False) -> None:
    if not FULL_SHA.fullmatch(expected_sha):
        raise ImportError("expected main SHA must be a full lowercase SHA")
    if host != DAILY_HOST:
        raise ImportError("daily acceptance import is restricted to sc-root")
    branch = git("branch", "--show-current")
    if git("rev-parse", "HEAD") != expected_sha:
        raise ImportError("import must run from the exact approved source SHA")
    if allow_boundary_head:
        if not re.fullmatch(r"release/tenant-rc-[a-z0-9][a-z0-9-]*", branch):
            raise ImportError("boundary import requires an exact tenant RC release branch")
    elif branch != "main":
        raise ImportError("import must run from the approved main SHA")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ImportError("import worktree must be clean")
    if not allow_boundary_head:
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
    remote_command = shlex.join([
        "docker", "image", "inspect", image_ref,
        "--format", '{{.Id}}|{{index .Config.Labels "org.opencontainers.image.revision"}}',
    ])
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, remote_command],
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


def extract_oci_layout(archive: Path, destination: Path) -> tuple[int, int]:
    """Extract only digest-addressed OCI files and verify every blob while copying."""
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
                    raise ImportError(f"candidate archive contains an unsafe OCI member: {member.name}")
                if not member.isfile() or member.issym() or member.islnk():
                    raise ImportError(f"candidate OCI member must be a regular file: {member.name}")
                stream = source.extractfile(member)
                if stream is None:
                    raise ImportError(f"candidate OCI member is unreadable: {member.name}")
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
                        raise ImportError(f"candidate OCI blob digest differs: {member.name}")
                    blob_count += 1
                else:
                    seen_metadata.add(name)
    except (tarfile.TarError, OSError) as exc:
        raise ImportError("candidate OCI layout cannot be extracted") from exc
    if seen_metadata != OCI_METADATA or blob_count == 0:
        raise ImportError("candidate OCI layout is incomplete")
    return blob_count, total_bytes


def remote_cache_has_latest(host: str) -> bool:
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, "test", "-d", f"{REMOTE_CACHE_ROOT}/latest/blobs/sha256"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    return completed.returncode == 0


def seed_remote_cache_from_daemon(host: str) -> bool:
    """Bootstrap the blob cache from the newest already verified candidate locally."""
    script = (
        f"set -euo pipefail; root={shlex.quote(REMOTE_CACHE_ROOT)}; install -d -m 0700 \"$root\"; "
        "image=$(docker image ls ghcr.io/lidefend/sce-product --format '{{.Repository}}:{{.Tag}}' "
        "| grep -E '^ghcr.io/lidefend/sce-product:sha-[0-9a-f]{12}$' | head -n 1 || true); "
        "test -n \"$image\" || exit 3; digest=$(docker image inspect \"$image\" --format '{{.Id}}'); "
        "digest=${digest#sha256:}; [[ \"$digest\" =~ ^[0-9a-f]{64}$ ]]; target=\"$root/$digest\"; "
        "install -d -m 0700 \"$target\"; docker image save \"$image\" | tar -xf - -C \"$target\"; "
        "link=\"$root/latest.next\"; rm -f \"$link\"; ln -s \"$digest\" \"$link\"; mv -Tf \"$link\" \"$root/latest\""
    )
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, f"bash -c {shlex.quote(script)}"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    if completed.returncode not in (0, 3):
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ImportError(f"remote candidate cache bootstrap failed: {detail[:500]}")
    return completed.returncode == 0


def stream_load(host: str, archive: Path, remote_config_id: str) -> dict[str, int]:
    """Transfer an OCI layout by digest, reusing unchanged remote blobs."""
    config_digest = remote_config_id.removeprefix("sha256:")
    if not CHECKSUM.fullmatch(config_digest):
        raise ImportError("incremental cache config identity is invalid")
    remote_directory = f"{REMOTE_CACHE_ROOT}/{config_digest}"
    if not remote_cache_has_latest(host):
        seed_remote_cache_from_daemon(host)
    with tempfile.TemporaryDirectory(prefix="sce-candidate-oci-") as temporary:
        layout = Path(temporary)
        blob_count, layout_bytes = extract_oci_layout(archive, layout)
        run([
            "ssh", "-o", "BatchMode=yes", host,
            f"install -d -m 0700 {shlex.quote(remote_directory)}",
        ])
        command = [
            "rsync", "--archive", "--checksum", "--partial", "--delete",
            "--stats",
        ]
        if remote_cache_has_latest(host):
            command.append(f"--link-dest={REMOTE_CACHE_ROOT}/latest")
        command.extend([f"{layout}/", f"{host}:{remote_directory}/"])
        completed = subprocess.run(
            command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, env={**os.environ, "LC_ALL": "C"},
        )
        if completed.returncode:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise ImportError(f"incremental candidate transfer failed: {detail[:500]}")
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
    run(["ssh", "-o", "BatchMode=yes", host, f"bash -c {shlex.quote(load_command)}"])
    promote_script = (
        "import os,pathlib,re,shutil,sys; root=pathlib.Path(sys.argv[1]); digest=sys.argv[2]; "
        "target=root/digest; link=root/'latest.next'; "
        "link.unlink(missing_ok=True); link.symlink_to(digest); os.replace(link,root/'latest'); "
        "[shutil.rmtree(p) for p in root.iterdir() if p.is_dir() and "
        "re.fullmatch(r'[0-9a-f]{64}',p.name) and p.name!=digest]"
    )
    run([
        "ssh", "-o", "BatchMode=yes", host,
        shlex.join(["python3", "-c", promote_script, REMOTE_CACHE_ROOT, config_digest]),
    ])
    return {
        "blob_count": blob_count,
        "layout_bytes": layout_bytes,
        "transferred_bytes": transferred_bytes,
    }


def import_candidate(
    *, expected_sha: str, archive: Path, archive_sha256: str, image_ref: str,
    local_content_id: str, remote_config_id: str, host: str,
    allow_boundary_head: bool = False,
) -> str:
    if os.environ.get("CONFIRM_DAILY_ACCEPTANCE_CANDIDATE_IMPORT") != CONFIRMATION:
        raise ImportError("exact daily acceptance candidate import confirmation is required")
    if not CONTENT_ID.fullmatch(remote_config_id):
        raise ImportError("remote config identity is invalid")
    preflight(expected_sha, host, allow_boundary_head)
    verified_archive, archive_config_id = validate_archive(archive, archive_sha256, image_ref)
    if archive_config_id != remote_config_id:
        raise ImportError("declared remote config identity differs from archive")
    validate_local_image(image_ref, local_content_id, expected_sha)
    expected_remote = f"{remote_config_id}|{expected_sha}"
    observed = remote_identity(host, image_ref)
    if observed != expected_remote:
        transfer = stream_load(host, verified_archive, remote_config_id)
        observed = remote_identity(host, image_ref)
    else:
        transfer = {"blob_count": 0, "layout_bytes": 0, "transferred_bytes": 0}
    if observed != expected_remote:
        raise ImportError("daily candidate identity differs after import")
    import_candidate.last_transfer = transfer
    return observed


import_candidate.last_transfer = {"blob_count": 0, "layout_bytes": 0, "transferred_bytes": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-main-sha", required=True)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--local-content-id", required=True)
    parser.add_argument("--remote-config-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--allow-boundary-head", action="store_true")
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
            allow_boundary_head=args.allow_boundary_head,
        )
    except ImportError as exc:
        raise SystemExit(f"[daily.acceptance.candidate.import] BLOCKED: {exc}") from exc
    print(
        "[daily.acceptance.candidate.import] PASS "
        f"host={args.host} image={args.image_ref} identity={identity} "
        f"transfer={json.dumps(import_candidate.last_transfer, sort_keys=True, separators=(',', ':'))} "
        "production_writes=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

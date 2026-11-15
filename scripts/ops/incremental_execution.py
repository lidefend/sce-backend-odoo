#!/usr/bin/env python3
"""Reusable exact-identity evidence for incremental execution planners."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


SCHEMA_VERSION = 2
NON_RUNTIME_PREFIXES = (".agent/", "docs/", ".runtime/")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def runtime_tree_sha256(root: Path) -> str:
    """Hash current runtime input bytes, including dirty and untracked source."""
    try:
        paths = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            check=True,
            stdout=subprocess.PIPE,
        ).stdout.split(b"\0")
    except subprocess.CalledProcessError:
        return ""
    digest = hashlib.sha256()
    for raw_path in sorted({path for path in paths if path}):
        relative = raw_path.decode("utf-8")
        if relative.startswith(NON_RUNTIME_PREFIXES):
            continue
        path = root / relative
        digest.update(raw_path + b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0" + os.readlink(path).encode("utf-8"))
        elif path.is_file():
            digest.update(b"file\0")
            digest.update(str(path.stat().st_mode & 0o777).encode("ascii") + b"\0")
            digest.update(path.read_bytes())
        else:
            digest.update(b"missing\0")
    return digest.hexdigest()


def committed_runtime_tree_sha256(root: Path, head: str) -> str:
    """Reproduce runtime_tree_sha256 from one immutable Git tree."""
    try:
        raw_tree = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-r", "-z", "--full-tree", head],
            check=True,
            stdout=subprocess.PIPE,
        ).stdout.split(b"\0")
        entries = []
        for raw in sorted(value for value in raw_tree if value):
            metadata, raw_path = raw.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split()
            relative = raw_path.decode("utf-8")
            if relative.startswith(NON_RUNTIME_PREFIXES) or object_type != "blob":
                continue
            entries.append((raw_path, mode, object_id))
        digest = hashlib.sha256()
        process = subprocess.Popen(
            ["git", "-C", str(root), "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdin is not None and process.stdout is not None
        for raw_path, mode, object_id in entries:
            process.stdin.write(object_id.encode("ascii") + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().rstrip(b"\n").split()
            if len(header) != 3 or header[1] != b"blob":
                raise ValueError(f"historical blob missing: {object_id}")
            size = int(header[2])
            content = process.stdout.read(size)
            process.stdout.read(1)
            digest.update(raw_path + b"\0")
            if mode == "120000":
                digest.update(b"symlink\0" + content)
            else:
                digest.update(b"file\0")
                digest.update(format(int(mode, 8) & 0o777, "o").encode("ascii") + b"\0")
                digest.update(content)
        process.stdin.close()
        stderr = process.stderr.read() if process.stderr is not None else b""
        returncode = process.wait()
        process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
        if returncode:
            raise ValueError(stderr.decode("utf-8", errors="replace"))
        return digest.hexdigest()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"cannot compute historical runtime tree digest: {exc}") from exc


def current_identity(root: Path, authority_paths: tuple[Path, ...] = ()) -> dict:
    """Bind reusable execution to VCS head, cleanliness and planner authorities."""
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        tree = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD^{tree}"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout
    except subprocess.CalledProcessError:
        return {
            "head": "",
            "tree": "",
            "worktreeClean": False,
            "runtimeTreeSha256": "",
            "authoritySha256": {},
        }
    authorities = {}
    for path in authority_paths:
        try:
            name = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            name = str(path.resolve())
        authorities[name] = sha256_file(path)
    return {
        "head": head,
        "tree": tree,
        "worktreeClean": not bool(status),
        "runtimeTreeSha256": runtime_tree_sha256(root),
        "authoritySha256": dict(sorted(authorities.items())),
    }


def reuse_identity(identity: dict) -> dict:
    """Fields that decide reuse; HEAD and cleanliness remain provenance."""
    return {
        "runtimeTreeSha256": identity.get("runtimeTreeSha256", ""),
        "authoritySha256": identity.get("authoritySha256", {}),
    }


def cache_path(root: Path, paths: list[str], targets: list[str], identity: dict) -> Path:
    key = hashlib.sha256(
        json.dumps(
            {
                "schemaVersion": SCHEMA_VERSION,
                "identity": reuse_identity(identity),
                "changedPaths": sorted(set(paths)),
                "requiredTargets": sorted(set(targets)),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return root / ".runtime/frontend-dev-validation/reuse" / f"{key}.json"


def verified_receipt(
    root: Path,
    paths: list[str],
    targets: list[str],
    identity: dict,
) -> Path | None:
    """Return a prior receipt only when identity, bytes and every target log match."""
    if not identity.get("head"):
        return None
    index = cache_path(root, paths, targets, identity)
    if not index.is_file():
        return None
    try:
        cached = json.loads(index.read_text(encoding="utf-8"))
        if (
            cached.get("schemaVersion") != SCHEMA_VERSION
            or cached.get("identity") != reuse_identity(identity)
        ):
            return None
        receipt_path = Path(str(cached["receipt"]))
        if not receipt_path.is_absolute():
            receipt_path = root / receipt_path
        if not receipt_path.resolve().is_relative_to(root.resolve()):
            return None
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            receipt.get("status") != "passed"
            or not receipt.get("verificationPassed")
            or reuse_identity(receipt.get("identity", {})) != reuse_identity(identity)
            or sorted(receipt.get("changedPaths", [])) != sorted(set(paths))
            or sorted(receipt.get("requiredTargets", [])) != sorted(set(targets))
        ):
            return None
        results = receipt.get("targetResults", [])
        if [row.get("target") for row in results] != sorted(set(targets)):
            return None
        for row in results:
            log = Path(str(row.get("log", "")))
            if not log.is_absolute():
                log = root / log
            if (
                not log.is_file()
                or not log.resolve().is_relative_to(root.resolve())
                or hashlib.sha256(log.read_bytes()).hexdigest() != row.get("logSha256")
            ):
                return None
        return receipt_path
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_index(
    root: Path,
    paths: list[str],
    targets: list[str],
    identity: dict,
    receipt: Path,
) -> None:
    index = cache_path(root, paths, targets, identity)
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(
        json.dumps(
            {
                "schemaVersion": SCHEMA_VERSION,
                "identity": reuse_identity(identity),
                "receipt": receipt.resolve().relative_to(root.resolve()).as_posix(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

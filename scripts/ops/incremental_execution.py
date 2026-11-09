#!/usr/bin/env python3
"""Reusable exact-identity evidence for incremental execution planners."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


SCHEMA_VERSION = 1
NON_RUNTIME_PREFIXES = (".agent/", "docs/")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def runtime_tree_sha256(root: Path) -> str:
    """Hash tracked runtime inputs while excluding bookkeeping-only trees."""
    try:
        listing = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-r", "--full-tree", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.splitlines()
    except subprocess.CalledProcessError:
        return ""
    rows = [
        row
        for row in listing
        if not (row.split("\t", 1)[1] if "\t" in row else "").startswith(NON_RUNTIME_PREFIXES)
    ]
    return hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest()


def current_identity(root: Path, authority_paths: tuple[Path, ...] = ()) -> dict:
    """Bind reusable execution to VCS head, cleanliness and planner authorities."""
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
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
        "worktreeClean": not bool(status),
        "runtimeTreeSha256": runtime_tree_sha256(root),
        "authoritySha256": dict(sorted(authorities.items())),
    }


def reuse_identity(identity: dict) -> dict:
    """Fields that decide reuse; HEAD remains provenance, not validity."""
    return {
        "worktreeClean": identity.get("worktreeClean", False),
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
    if not identity.get("worktreeClean") or not identity.get("head"):
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

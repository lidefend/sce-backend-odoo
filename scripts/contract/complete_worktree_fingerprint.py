#!/usr/bin/env python3
"""Create a complete tracked, staged, and untracked candidate fingerprint."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.contract.product_view_structure_common import FINGERPRINT_SCHEMA, sha256_bytes, sha256_json  # noqa: E402


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout


def build_fingerprint(baseline_sha: str) -> dict:
    head = _git("rev-parse", "HEAD").decode().strip()
    branch = _git("branch", "--show-current").decode().strip()
    raw_paths = _git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    paths = sorted({item.decode("utf-8") for item in raw_paths.split(b"\0") if item})
    index_rows = {}
    for line in _git("ls-files", "-s", "-z").split(b"\0"):
        if not line:
            continue
        metadata, path = line.decode("utf-8").split("\t", 1)
        mode, blob, stage = metadata.split()
        if stage == "0":
            index_rows[path] = {"mode": mode, "index_blob": blob}
    entries = []
    for relative in paths:
        path = ROOT / relative
        tracked = relative in index_rows
        row = {"path": relative, "tracked": tracked, **index_rows.get(relative, {"mode": "", "index_blob": ""})}
        if path.is_symlink():
            row.update({"worktree_kind": "symlink", "worktree_sha256": sha256_bytes(os.readlink(path).encode())})
        elif path.is_file():
            row.update({"worktree_kind": "file", "worktree_sha256": sha256_bytes(path.read_bytes())})
        else:
            row.update({"worktree_kind": "missing", "worktree_sha256": ""})
        entries.append(row)
    scope_sha = sha256_json(entries)
    canonical = {
        "algorithm": FINGERPRINT_SCHEMA, "git_head": head, "baseline_sha": baseline_sha,
        "branch": branch, "scope_manifest_sha256": scope_sha, "entries": entries,
    }
    return {**canonical, "digest": sha256_json(canonical)}


def validate_fingerprint(payload: dict) -> list[str]:
    errors = []
    if payload.get("algorithm") != FINGERPRINT_SCHEMA:
        errors.append("fingerprint algorithm mismatch")
    entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
    if not entries:
        errors.append("fingerprint scope is empty")
    if payload.get("scope_manifest_sha256") != sha256_json(entries):
        errors.append("fingerprint scope manifest hash is stale")
    canonical = {key: payload.get(key) for key in ("algorithm", "git_head", "baseline_sha", "branch", "scope_manifest_sha256", "entries")}
    if payload.get("digest") != sha256_json(canonical):
        errors.append("fingerprint digest is stale")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = build_fingerprint(args.baseline)
    path = ROOT / args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "path_count": len(payload["entries"]), "digest": payload["digest"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

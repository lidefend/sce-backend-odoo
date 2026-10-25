#!/usr/bin/env python3
"""Per-suite input fingerprints for the local quick matrix.

Each quick suite declares the files it reads plus its command. The fingerprint
is sha256(command + sorted input bytes), so an unchanged suite reuses its prior
outcome and only suites whose declared inputs changed are re-run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "scripts/ops/quick_suite_manifest.json"
REVIEWED_SUITES = frozenset({"verify.test.determinism", "verify.test.isolation"})


def committed_fingerprints(root: Path, head: str, rows: list[str]) -> dict[str, str]:
    """Bind declared scopes to immutable Git blobs, never today's worktree.

    Directory declarations include additions and removals. All execution and
    planning helpers live in the declared scripts tree; all Make definitions
    are bound as well. Missing/unsafe inputs fail closed.
    """
    tree = {row.partition("\t")[2]: row.partition("\t")[0] for row in rows}
    if MANIFEST not in tree:
        return {}  # Old candidates predate suite declarations.
    if not tree[MANIFEST].startswith("100644 blob "):
        raise ValueError("suite manifest must be a regular tracked file")
    manifest = json.loads(subprocess.check_output(
        ["git", "-C", str(root), "show", f"{head}:{MANIFEST}"], text=True))
    suites = manifest.get("suites")
    if not isinstance(suites, list) or not suites:
        raise ValueError("manifest.suites must be non-empty")
    result = {}
    for suite in suites:
        name = suite.get("id")
        inputs = suite.get("inputs")
        if (not isinstance(name, str) or name not in REVIEWED_SUITES or name in result
                or suite.get("command") != ["make", name]
                or suite.get("required", True) is not True
                or not isinstance(inputs, list) or not inputs):
            raise ValueError("invalid or duplicate suite declaration")
        selected = {MANIFEST: tree[MANIFEST]}
        for path in inputs:
            if (not isinstance(path, str) or not path or path.startswith("/")
                    or any(part in ("", ".", "..") for part in path.rstrip("/").split("/"))):
                raise ValueError("suite input must be a bounded repository path")
            matches = {key: value for key, value in tree.items()
                       if (key.startswith(path) if path.endswith("/") else key == path)}
            if not matches or any(not value.startswith(("100644 blob ", "100755 blob "))
                                  for value in matches.values()):
                raise ValueError(f"missing or unsafe suite input: {path}")
            selected.update(matches)
        # Mandatory authority cannot be removed by narrowing a declaration.
        for path in ("Makefile", "make/", "scripts/", "frontend/apps/web/scripts/",
                     "docs/engineering_convergence/test_inventory.csv",
                     ".github/workflows/", "frontend/apps/web/package.json"):
            if path not in inputs:
                raise ValueError(f"suite missing execution authority: {path}")
        result[name] = hashlib.sha256(json.dumps(
            {"command": suite["command"], "files": selected}, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
    return result


def fingerprint_suite(command: list[str], inputs: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(command, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    expanded = set()
    for rel in inputs:
        path = ROOT / rel
        if path.is_dir():
            expanded.update(p.relative_to(ROOT).as_posix() for p in path.rglob("*")
                            if p.is_file() and "__pycache__" not in p.parts)
        else:
            expanded.add(rel)
    for rel in sorted(expanded):
        path = ROOT / rel
        if not path.is_file():
            raise ValueError(f"declared input is missing: {rel}")
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def build_units(manifest: dict) -> dict:
    suites = manifest.get("suites")
    if not isinstance(suites, list) or not suites:
        raise ValueError("manifest.suites must be a non-empty list")
    units = []
    for suite in suites:
        suite_id = str(suite.get("id") or "")
        command = [str(item) for item in suite.get("command") or []]
        inputs = [str(item) for item in suite.get("inputs") or []]
        if not suite_id or not command or not inputs:
            raise ValueError(f"suite {suite_id!r} needs id, command and inputs")
        units.append({
            "id": suite_id,
            "fingerprint": fingerprint_suite(command, inputs),
            "required": bool(suite.get("required", True)),
        })
    return {
        "schema": "evidence_scope.units.v1",
        "check": str(manifest.get("check") or "ci.local.quick.run"),
        "identity": manifest.get("identity") or {},
        "units": units,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="scripts/ops/quick_suite_manifest.json")
    args = parser.parse_args(argv)
    manifest = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    json.dump(build_units(manifest), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

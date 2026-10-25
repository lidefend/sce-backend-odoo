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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fingerprint_suite(command: list[str], inputs: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(command, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    for rel in sorted(inputs):
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

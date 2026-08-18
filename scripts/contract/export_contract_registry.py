#!/usr/bin/env python3
"""Export contracts/generated/contract-registry.json from contracts/registry.yaml.

Cross-checks document versions before export:
- product/ domain/ extensions/ docs must carry a matching `version` key;
- api/openapi.yaml version must match its info.version;
- schemas/ versions live in the registry only (docs are pure schema maps).

Any mismatch aborts with exit code 2 (no stale artifact written).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "contracts" / "registry.yaml"
OUT_PATH = ROOT / "contracts" / "generated" / "contract-registry.json"


def load_yaml(path: Path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if data is not None else {}


def main() -> int:
    if not REGISTRY_PATH.exists():
        print(f"[contract-registry] FAIL: {REGISTRY_PATH} missing")
        return 2

    registry = load_yaml(REGISTRY_PATH)
    entries = registry.get("contracts")
    if not isinstance(entries, list) or not entries:
        print("[contract-registry] FAIL: registry.contracts must be a non-empty list")
        return 2

    errors = []
    seen_paths = set()
    for entry in entries:
        rel = entry.get("path")
        if not rel:
            errors.append("registry entry missing 'path'")
            continue
        if rel in seen_paths:
            errors.append(f"duplicate registry path: {rel}")
        seen_paths.add(rel)
        kind = entry.get("kind")
        version = entry.get("version")
        if kind not in {"product", "domain", "schema", "api", "extension"}:
            errors.append(f"{rel}: invalid kind '{kind}'")
        if version is None:
            errors.append(f"{rel}: missing version")
            continue

        doc_path = ROOT / "contracts" / rel
        if not doc_path.exists():
            errors.append(f"{rel}: registered file not found")
            continue

        doc = load_yaml(doc_path)
        if kind in {"product", "domain", "extension"}:
            doc_version = doc.get("version")
            if doc_version != version:
                errors.append(
                    f"{rel}: registry version {version!r} != document version {doc_version!r}"
                )
        elif rel == "api/openapi.yaml":
            info_version = (doc.get("info") or {}).get("version")
            if info_version != version:
                errors.append(
                    f"{rel}: registry version {version!r} != info.version {info_version!r}"
                )

    # coverage: every yaml under contracts/ (excluding generated/ and registry itself) registered
    for path in sorted((ROOT / "contracts").rglob("*.yaml")):
        rel = path.relative_to(ROOT / "contracts").as_posix()
        if rel.startswith("generated/") or rel == "registry.yaml":
            continue
        if rel not in seen_paths:
            errors.append(f"{rel}: contract file not registered in registry")

    if errors:
        for e in errors:
            print(f"[contract-registry] ERROR: {e}")
        print(f"[contract-registry] FAIL: {len(errors)} issues")
        return 2

    payload = {
        "registry_version": registry.get("registry_version", 1),
        "generated_from": "contracts/registry.yaml",
        "contracts": entries,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[contract-registry] PASS: {len(entries)} contracts -> {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

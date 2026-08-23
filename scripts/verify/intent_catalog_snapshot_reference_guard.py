#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail if intent catalog example snapshot references are missing on disk."
    )
    parser.add_argument("--catalog", default="docs/contract/exports/intent_catalog.json")
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        raise SystemExit(f"❌ missing catalog: {catalog_path}")

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    intents = payload.get("intents") if isinstance(payload, dict) else None
    if not isinstance(intents, list):
        raise SystemExit("❌ invalid catalog shape: intents must be a list")

    repo_root = Path.cwd()
    missing: list[str] = []
    invalid: list[str] = []
    for item in intents:
        if not isinstance(item, dict):
            continue
        intent = str(item.get("intent") or "").strip() or "<unknown>"
        for ex in item.get("examples") or []:
            if not isinstance(ex, dict):
                continue
            snapshot_file = str(ex.get("snapshot_file") or "").strip()
            if not snapshot_file:
                # inferred placeholders are guarded by intent_catalog_inferred_guard
                continue
            snapshot_path = repo_root / snapshot_file
            if not snapshot_path.exists():
                missing.append(f"{intent}:{snapshot_file}")
                continue
            try:
                snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            except Exception as exc:
                invalid.append(f"{intent}:{snapshot_file}:invalid-json:{exc.__class__.__name__}")
                continue
            error = snapshot.get("error") if isinstance(snapshot, dict) else None
            if isinstance(error, dict) and str(error.get("type") or "").strip() == "HandlerNotFound":
                invalid.append(f"{intent}:{snapshot_file}:HandlerNotFound")

    if missing:
        raise SystemExit("❌ missing snapshot references: " + ", ".join(sorted(set(missing))))
    if invalid:
        raise SystemExit("❌ invalid snapshot references: " + ", ".join(sorted(set(invalid))))

    print("[verify.intent_catalog.snapshot_reference_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

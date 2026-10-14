#!/usr/bin/env python3
"""Generate/check compatibility artifacts from P1-owned menu metadata.

This tool owns serialization only. Product identities, targets, versions and
roles live in smart_construction_core/data/product_menu_source.json.

The write path is executed only by contract.product_menu.generate; the check
path is executed by the read-only product menu guards.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "addons/smart_construction_core"
BASELINE = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
CHECKSUM = BASELINE.with_suffix(BASELINE.suffix + ".sha256")
PRODUCT_CONTRACT = ROOT / "config/product_menu_contract_v1.json"
RUNTIME_CONTRACT = MODULE / "data" / BASELINE.name
RUNTIME_CHECKSUM = RUNTIME_CONTRACT.with_suffix(RUNTIME_CONTRACT.suffix + ".sha256")
_spec = importlib.util.spec_from_file_location("p1_product_menu_source", MODULE / "services/product_menu_source.py")
_source = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_source)
load_source = _source.load_source
project = _source.project
resolve_native_source = _source.resolve_native_source
native_facts = _source.native_facts
SOURCE_PATH = _source.SOURCE_PATH
TARGET_CENTERS = tuple(row["name"] for row in load_source()["product_contract"]["centers"])


def promote(payload: dict) -> dict:
    # Existing callers may supply an old projection for validation, never as
    # an editable source of publication or role facts.
    for product in payload.get("products") or []:
        incoming = {group.get("group_label") for group in product.get("menu_groups") or []}
        if incoming - set(TARGET_CENTERS):
            raise ValueError(f"unapproved first-level product center: {sorted(incoming - set(TARGET_CENTERS))}")
    return project(load_source())[1]


def artifacts(source=None) -> dict[Path, str]:
    contract, publication = project(source if source is not None else load_source())
    rendered = json.dumps(publication, ensure_ascii=False, indent=2) + "\n"
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    lock = f"{digest}  {BASELINE.name}\n"
    return {
        PRODUCT_CONTRACT: json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        BASELINE: rendered, CHECKSUM: lock,
        RUNTIME_CONTRACT: rendered, RUNTIME_CHECKSUM: lock,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    outputs = artifacts()
    for path, value in outputs.items():
        if args.write:
            path.write_text(value, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != value:
            raise SystemExit(f"P1 menu source/projection drift: {path.relative_to(ROOT)}")
    print(json.dumps({"source": str(_source.SOURCE_PATH.relative_to(ROOT)), "artifacts": len(outputs), "menu_count": project(load_source())[1]["policy_strategy"]["effective_menu_count_per_product"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

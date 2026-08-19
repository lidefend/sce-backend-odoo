#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CUSTOMER_MODULE_PREFIX = "sce_customer_"


def _is_customer_module(module_name: str) -> bool:
    module_root = ROOT / "addons" / module_name
    return module_name.startswith(CUSTOMER_MODULE_PREFIX) or (
        module_root / "customer_module_manifest.json"
    ).exists()


def main() -> int:
    errors: list[str] = []
    for manifest_path in sorted((ROOT / "addons").glob("*/__manifest__.py")):
        module_name = manifest_path.parent.name
        if _is_customer_module(module_name):
            errors.append(f"customer module must stay outside product addons: addons/{module_name}")

    # R3 physical isolation (PRODUCTIZATION-P0-SPRINT-001): the demo payload
    # lives in demo_addons/ outside the product addons tree, and no
    # production image COPY whitelist may ever pull it back in.
    demo_root = ROOT / "demo_addons" / "smart_construction_demo"
    if not (demo_root / "__manifest__.py").exists():
        errors.append("demo module must live in demo_addons/smart_construction_demo")
    if (ROOT / "addons" / "smart_construction_demo").exists():
        errors.append(
            "demo module must stay physically isolated outside product addons: "
            "addons/smart_construction_demo"
        )
    for dockerfile_name in ("Dockerfile", "Dockerfile.production-candidate"):
        dockerfile = ROOT / dockerfile_name
        if not dockerfile.exists():
            continue
        for line in dockerfile.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("COPY") and (
                "demo_addons" in stripped or "smart_construction_demo" in stripped
            ):
                errors.append(
                    f"production image COPY whitelist must not include demo "
                    f"payload: {dockerfile_name}: {stripped}"
                )
    demo_manifest = ast.literal_eval((demo_root / "__manifest__.py").read_text(encoding="utf-8"))
    dependencies = set(demo_manifest.get("depends", []))
    if "smart_construction_bundle" not in dependencies:
        errors.append("demo must depend on smart_construction_bundle")
    customer_dependencies = sorted(item for item in dependencies if _is_customer_module(item))
    if customer_dependencies:
        errors.append(f"demo depends on customer modules: {customer_dependencies}")
    for path in demo_root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if CUSTOMER_MODULE_PREFIX in content:
            errors.append(f"demo contains a customer-module reference: {path.relative_to(ROOT)}")

    neutral_defaults = (
        ROOT / "make" / "release.mk",
        ROOT / "scripts" / "release" / "production_candidate_history.sh",
        ROOT / "scripts" / "deploy" / "prod_sim_oneclick.sh",
        ROOT / "scripts" / "deploy" / "fresh_production_history_init.sh",
        ROOT / "scripts" / "deploy" / "prod_sim_fresh_replay.sh",
    )
    for path in neutral_defaults:
        content = path.read_text(encoding="utf-8")
        if CUSTOMER_MODULE_PREFIX in content:
            errors.append(f"product release/deploy default references a customer module: {path.relative_to(ROOT)}")

    if errors:
        print("[customer_module_extraction_guard] FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("[customer_module_extraction_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

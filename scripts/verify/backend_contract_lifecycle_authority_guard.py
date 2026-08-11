#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs/architecture/backend_contract_lifecycle_manifest_v1.json"
SCHEMA_PATH = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
REGISTRY_PATH = ROOT / "docs/architecture/unified_page_contract_v2/enum_registry.json"
EXAMPLES_DIR = ROOT / "docs/architecture/unified_page_contract_v2/examples"
CORE_DIR = ROOT / "addons/smart_core/core"
LIFECYCLE_PATH = CORE_DIR / "contract_lifecycle.py"
ASSEMBLER_PATH = CORE_DIR / "unified_page_contract_v2_assembler.py"
HANDLER_PATH = ROOT / "addons/smart_core/handlers/ui_contract_v2.py"
MODEL_PATH = ROOT / "addons/smart_core/model/ui_business_config_contract.py"
MIGRATION_PATH = ROOT / "addons/smart_core/migrations/17.0.1.1.9/post-migration.py"
FRONTEND_TYPES_PATH = ROOT / "frontend/apps/web/src/app/contracts/v2/types.ts"
FRONTEND_SCHEMA_PATH = ROOT / "frontend/apps/web/src/app/contracts/v2/schema.ts"
MAKE_PATH = ROOT / "make/dev_test.mk"

EXPECTED_STAGES = [
    "definition",
    "generation",
    "validation",
    "persistence_versioning",
    "publication",
    "runtime_resolution",
    "observability_integrity",
    "compatibility_release",
]

DIMENSIONS = {
    "definition": 12,
    "generation": 13,
    "validation": 12,
    "persistence_versioning": 13,
    "publication": 13,
    "runtime_resolution": 13,
    "observability_integrity": 12,
    "compatibility_release": 12,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_assembler():
    sys.modules.setdefault("odoo", types.ModuleType("odoo"))
    sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
    smart_core = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
    smart_core.__path__ = [str(CORE_DIR.parent)]
    core = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
    core.__path__ = [str(CORE_DIR)]
    return load_module("odoo.addons.smart_core.core.unified_page_contract_v2_assembler_authority", ASSEMBLER_PATH)


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise AssertionError(f"{label} missing markers: {missing}")


def check_manifest() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)
    stages = manifest.get("stages") if isinstance(manifest.get("stages"), list) else []
    keys = [row.get("key") for row in stages if isinstance(row, dict)]
    if keys != EXPECTED_STAGES:
        raise AssertionError(f"lifecycle stage order mismatch: {keys}")
    for row in stages:
        if set(row) != {"key", "owner", "input", "output", "failClosed", "evidence"}:
            raise AssertionError(f"stage {row.get('key')} field set is not closed")
        if row.get("failClosed") is not True or not all(str(row.get(key) or "").strip() for key in ("owner", "input", "output", "evidence")):
            raise AssertionError(f"stage {row.get('key')} is not fail-closed and evidenced")
    return {"stageCount": len(stages), "authorityLayer": manifest.get("authorityLayer")}


def check_definition() -> dict[str, Any]:
    lifecycle = load_module("backend_contract_lifecycle_guard_target", LIFECYCLE_PATH)
    schema_digest = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
    registry = load_json(REGISTRY_PATH)
    if schema_digest != lifecycle.UNIFIED_PAGE_SCHEMA_SHA256:
        raise AssertionError("schema SHA-256 is not bound to runtime lifecycle constant")
    if registry.get("registryVersion") != "2.2.0" or registry.get("normativeStatus") != "stable":
        raise AssertionError("enum registry is not the stable 2.2.0 authority")
    schema = load_json(SCHEMA_PATH)
    lifecycle_ref = schema.get("$defs", {}).get("meta", {}).get("properties", {}).get("lifecycle", {}).get("$ref")
    if lifecycle_ref != "#/$defs/contractLifecycle":
        raise AssertionError("schema meta is not bound to contractLifecycle")
    return {"schemaSha256": schema_digest, "schemaVersion": lifecycle.UNIFIED_PAGE_SCHEMA_VERSION}


def check_generation() -> dict[str, Any]:
    assembler_text = ASSEMBLER_PATH.read_text(encoding="utf-8")
    if "sha1" in assembler_text.lower():
        raise AssertionError("SHA-1 remains in contract generation")
    assembler = load_assembler()
    lifecycle = sys.modules["odoo.addons.smart_core.core.contract_lifecycle"]
    source = {
        "model": "project.project",
        "view_type": "tree",
        "fields": {"name": {"string": "Project", "type": "char"}},
    }
    contract = assembler.assemble_unified_page_contract_v2(
        source,
        source_type="ui.contract",
        request_id="request.authority.guard",
        trace_id="trace.authority.guard",
    )
    valid, reason = lifecycle.verify_unified_page_contract_integrity(contract)
    if not valid:
        raise AssertionError(f"assembled contract integrity failed: {reason}")
    evidence = contract.get("meta", {}).get("lifecycle", {})
    if evidence.get("stage") != "assembly" or evidence.get("definition", {}).get("contractVersion") != "2.2.0":
        raise AssertionError("assembler lifecycle evidence is incomplete")
    return {"contractSha256": evidence["integrity"]["contractSha256"], "traceId": evidence["runtime"]["traceId"]}


def check_examples() -> dict[str, Any]:
    lifecycle = load_module("backend_contract_lifecycle_examples_target", LIFECYCLE_PATH)
    checked = []
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        payload = load_json(path)
        evidence = payload.get("meta", {}).get("lifecycle", {})
        expected = evidence.get("integrity", {}).get("contractSha256")
        actual = lifecycle.payload_sha256(lifecycle.contract_semantic_payload(payload))
        if expected != actual or "0" * 64 in path.read_text(encoding="utf-8"):
            raise AssertionError(f"example integrity evidence drifted: {path.name}")
        checked.append(path.name)
    if len(checked) != 4:
        raise AssertionError(f"expected four canonical examples, got {checked}")
    return {"examples": checked}


def check_persistence() -> dict[str, Any]:
    text = MODEL_PATH.read_text(encoding="utf-8")
    require_tokens(
        text,
        (
            "payload_sha256 = fields.Char",
            "definition_sha256 = fields.Char",
            "source_authority_json = fields.Json",
            "definition_json = fields.Json",
            "def replace_and_publish",
            "def restore_published_version",
            "definition_fields = {",
        ),
        "persistence authority",
    )
    if not MIGRATION_PATH.is_file():
        raise AssertionError("contract lifecycle backfill migration is missing")
    return {"migration": MIGRATION_PATH.relative_to(ROOT).as_posix()}


def check_publication() -> dict[str, Any]:
    text = MODEL_PATH.read_text(encoding="utf-8")
    require_tokens(
        text,
        (
            "FOR UPDATE",
            "def _append_published_version",
            "versions are append-only",
            "Published contract versions are immutable.",
            "latest.definition_sha256 == record.definition_sha256",
        ),
        "publication authority",
    )
    return {"rowLock": True, "idempotent": True, "appendOnly": True}


def check_runtime() -> dict[str, Any]:
    text = HANDLER_PATH.read_text(encoding="utf-8")
    trim_positions = [index for index in range(len(text)) if text.startswith("contract_v2 = trim_unified_page_contract_v2(", index)]
    seal_positions = [index for index in range(len(text)) if text.startswith("contract_v2 = seal_unified_page_contract(", index)]
    if len(trim_positions) < 2 or len(seal_positions) < 2:
        raise AssertionError("runtime full-contract paths must trim then reseal")
    if any(not any(seal > trim for seal in seal_positions) for trim in trim_positions):
        raise AssertionError("a runtime trim path is not followed by lifecycle sealing")
    require_tokens(text, ('stage="runtime_delivery"', "trace_id=trace_id"), "runtime delivery")
    return {"trimPaths": len(trim_positions), "resealPaths": len(seal_positions)}


def check_observability() -> dict[str, Any]:
    text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    require_tokens(
        text,
        (
            '"schemaSha256"',
            '"sourceSha256"',
            '"contractSha256"',
            '"requestId"',
            '"traceId"',
            "verify_unified_page_contract_integrity",
        ),
        "observability integrity",
    )
    return {"hashAlgorithm": "sha256", "traceBound": True}


def check_compatibility() -> dict[str, Any]:
    types_text = FRONTEND_TYPES_PATH.read_text(encoding="utf-8")
    decoder_text = FRONTEND_SCHEMA_PATH.read_text(encoding="utf-8")
    make_text = MAKE_PATH.read_text(encoding="utf-8")
    require_tokens(types_text, ("interface ContractV2Lifecycle", "lifecycle: ContractV2Lifecycle"), "frontend types")
    require_tokens(decoder_text, ("meta.lifecycle.definition", "meta.lifecycle.integrity", "meta.lifecycle.runtime"), "frontend decoder")
    release_block = make_text[make_text.index("verify.product.release.ready:"):]
    release_block = release_block[: release_block.index("\n\t@echo")]
    if "verify.backend.contract_lifecycle.authority" not in release_block:
        raise AssertionError("product release gate does not include backend contract lifecycle authority")
    return {"typedConsumer": True, "releaseGateBound": True}


CHECKS: dict[str, Callable[[], dict[str, Any]]] = {
    "definition": lambda: {**check_manifest(), **check_definition()},
    "generation": check_generation,
    "validation": check_examples,
    "persistence_versioning": check_persistence,
    "publication": check_publication,
    "runtime_resolution": check_runtime,
    "observability_integrity": check_observability,
    "compatibility_release": check_compatibility,
}


def build_report() -> dict[str, Any]:
    dimensions = []
    score = 0
    errors = []
    for key in EXPECTED_STAGES:
        try:
            evidence = CHECKS[key]()
            passed = True
            score += DIMENSIONS[key]
            error = ""
        except Exception as exc:
            passed = False
            evidence = {}
            error = str(exc)
            errors.append({"dimension": key, "severity": "P0", "message": error})
        dimensions.append({"key": key, "weight": DIMENSIONS[key], "passed": passed, "evidence": evidence, "error": error})
    if score >= 90 and not errors:
        level = "L4_governed_production_ready"
    elif score >= 75:
        level = "L3_standardized"
    elif score >= 50:
        level = "L2_repeatable"
    else:
        level = "L1_initial"
    return {
        "guard": "backend_contract_lifecycle_authority_guard",
        "schemaVersion": "1.0.0",
        "score": score,
        "maximumScore": 100,
        "maturityLevel": level,
        "dimensionCount": len(dimensions),
        "passedDimensionCount": sum(1 for row in dimensions if row["passed"]),
        "p0Count": len(errors),
        "dimensions": dimensions,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/architecture/backend_contract_lifecycle_authority_report.json")
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["p0Count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

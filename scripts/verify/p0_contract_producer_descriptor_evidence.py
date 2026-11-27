#!/usr/bin/env python3
"""Capture the real-ORM project ledger contracts for TS decoder evidence."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MARKER = "P0_CONTRACT_DESCRIPTOR_EVIDENCE_B64="


def writable_output_path(path: str) -> Path:
    """Keep evidence usable when a repository-root artifacts projection is root-owned."""
    requested = Path(path)
    parent = requested.parent
    try:
        if requested.exists() and not os.access(requested, os.W_OK):
            raise PermissionError(f"existing evidence file is not writable: {requested}")
        parent.mkdir(parents=True, exist_ok=True)
        probe = parent / f".write-probe-{Path.cwd().name}"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return requested
    except (PermissionError, OSError):
        fallback = ROOT / ".runtime/p0-contract-producer-evidence" / requested.name
        fallback.parent.mkdir(parents=True, exist_ok=True)
        print(
            "[p0-descriptor-evidence] output projection not writable; "
            f"using {fallback}"
        )
        return fallback


def validate_semantic_contract(contract: dict) -> list[str]:
    errors: list[str] = []

    def visit(value: object, path: str = "$") -> None:
        if isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
            return
        if not isinstance(value, dict):
            return
        for key, child in value.items():
            here = f"{path}.{key}"
            if key in {"componentKey", "component_key", "componentRegistry"}:
                errors.append(f"{here}: frontend implementation identity is forbidden")
                continue
            visit(child, here)

    visit(contract)

    def fields(rows: object) -> None:
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            for widget in row.get("widgetList") or []:
                if not isinstance(widget, dict):
                    continue
                descriptor = widget.get("fieldDescriptor")
                if isinstance(descriptor, dict) and not str(
                    descriptor.get("semanticType") or ""
                ).strip():
                    errors.append(
                        f"{widget.get('widgetId') or '<unknown>'}: field semanticType is missing"
                    )
            fields(row.get("children"))

    layout = contract.get("layoutContract")
    if isinstance(layout, dict):
        fields(layout.get("containerTree"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--form-output", required=True)
    parser.add_argument("--polymorphic-output")
    parser.add_argument("--relation-actions-output")
    args = parser.parse_args()

    tags = ["p0_contract_descriptor_conformance_evidence"]
    if args.polymorphic_output:
        tags.append("p0_polymorphic_reference_evidence")
    if args.relation_actions_output:
        tags.append("p0_relation_active_actions_evidence")
    if args.polymorphic_output:
        test_tags_arg = "TEST_TAGS=p0_contract_descriptor_conformance_evidence,p0_polymorphic_reference_evidence"
    elif args.relation_actions_output:
        test_tags_arg = "TEST_TAGS=p0_contract_descriptor_conformance_evidence,p0_relation_active_actions_evidence"
    else:
        test_tags_arg = "TEST_TAGS=p0_contract_descriptor_conformance_evidence"
    run = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "local.test.test",
            "MODULE=smart_construction_core",
            test_tags_arg,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(run.stdout, end="")
    print(run.stderr, end="")
    if run.returncode:
        return run.returncode

    receipt_match = re.search(r"^\[local.test\] receipt=(.+)$", run.stdout, re.M)
    if not receipt_match:
        print("[p0-descriptor-evidence] FAIL receipt path missing")
        return 2
    receipt_path = Path(receipt_match.group(1).strip())
    if not receipt_path.is_absolute():
        receipt_path = ROOT / receipt_path
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "passed" or int(receipt.get("count") or 0) < 1:
        print("[p0-descriptor-evidence] FAIL ORM evidence test did not pass non-zero")
        return 3
    log_path = Path(str(receipt.get("log") or ""))
    if not log_path.is_absolute():
        log_path = ROOT / log_path
    marker = next(
        (
            line.split(MARKER, 1)[1].strip()
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if MARKER in line
        ),
        "",
    )
    if not marker:
        print("[p0-descriptor-evidence] FAIL contract marker missing")
        return 4
    try:
        payload = json.loads(base64.b64decode(marker).decode("utf-8"))
    except Exception as exc:
        print(f"[p0-descriptor-evidence] FAIL marker decode: {exc}")
        return 5

    contract = payload.get("form")
    if not isinstance(contract, dict):
        print("[p0-descriptor-evidence] FAIL form contract missing")
        return 6
    semantic_errors = validate_semantic_contract(contract)
    if semantic_errors:
        print("[p0-descriptor-evidence] FAIL " + "; ".join(semantic_errors[:10]))
        return 7
    output = writable_output_path(args.form_output)
    output.write_text(
        json.dumps(contract, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.polymorphic_output:
        from jsonschema import Draft202012Validator
        prefix = "P0_POLYMORPHIC_REFERENCE_EVIDENCE_B64="
        encoded = next((line.split(prefix, 1)[1].strip() for line in
                        log_path.read_text(encoding="utf-8").splitlines() if prefix in line), "")
        if not encoded:
            print("[p0-descriptor-evidence] FAIL polymorphic producer output missing")
            return 8
        polymorphic = json.loads(base64.b64decode(encoded).decode("utf-8"))
        validator = Draft202012Validator(json.loads((ROOT / "docs/architecture/p0_contract_producer_01/contract_v2_field_descriptor.schema.json").read_text()))
        descriptors = []
        def collect(rows):
            for row in rows:
                descriptors.extend(widget["fieldDescriptor"] for widget in row.get("widgetList", []) if widget.get("fieldDescriptor"))
                collect(row.get("children", []))
        collect(polymorphic["notification"]["layoutContract"]["containerTree"])
        descriptors.append(polymorphic["native_reference"])
        if not any(row.get("fieldType") == "many2one_reference" for row in descriptors):
            raise ValueError("real contract must contain many2one_reference")
        for descriptor in descriptors:
            validator.validate(descriptor)
        polymorphic["producer_evidence"] = {"receipt": str(receipt_path), "descriptors": len(descriptors)}
        target = writable_output_path(args.polymorphic_output)
        target.write_text(json.dumps(polymorphic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[p0-descriptor-evidence] polymorphic_schema=PASS descriptors={len(descriptors)} output={target}")

    if args.relation_actions_output:
        from jsonschema import Draft202012Validator
        prefix = "P0_RELATION_ACTIVE_ACTIONS_EVIDENCE_B64="
        encoded = next((line.split(prefix, 1)[1].strip() for line in
                        log_path.read_text(encoding="utf-8").splitlines() if prefix in line), "")
        if not encoded:
            print("[p0-descriptor-evidence] FAIL relation-active-actions producer output missing")
            return 9
        evidence = json.loads(base64.b64decode(encoded).decode("utf-8"))
        contract = evidence.get("contract")
        if not isinstance(contract, dict):
            print("[p0-descriptor-evidence] FAIL relation-active-actions contract missing")
            return 10
        validator = Draft202012Validator(json.loads((ROOT / "docs/architecture/p0_contract_producer_01/contract_v2_field_descriptor.schema.json").read_text()))
        descriptors = []

        def collect_descriptors(rows):
            for row in rows:
                widgets = row.get("widgetList", [])
                descriptors.extend(
                    widget["fieldDescriptor"]
                    for widget in widgets
                    if isinstance(widget, dict) and isinstance(widget.get("fieldDescriptor"), dict)
                )
                for widget in widgets:
                    if not isinstance(widget, dict):
                        continue
                    if "relationActiveActions" in widget.get("componentConfig", {}):
                        raise ValueError("componentConfig retained a second relationActions declaration")
                    if "relation_active_actions" in widget.get("componentConfig", {}):
                        raise ValueError("componentConfig retained raw relation_active_actions")
                collect_descriptors(row.get("children", []))

        collect_descriptors(contract["layoutContract"]["containerTree"])
        relation_descriptors = [
            descriptor for descriptor in descriptors
            if "relationActiveActions" in descriptor
        ]
        if len(relation_descriptors) != 3:
            raise ValueError("real assembler must emit three occurrence-level relation descriptors")
        for descriptor in relation_descriptors:
            validator.validate(descriptor)
        evidence["producer_evidence"] = {
            "receipt": str(receipt_path),
            "descriptors": len(descriptors),
            "relation_descriptors": len(relation_descriptors),
        }
        target = writable_output_path(args.relation_actions_output)
        target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            "[p0-descriptor-evidence] relation_active_actions_schema=PASS "
            f"descriptors={len(relation_descriptors)} output={target}"
        )

    print(
        "[p0-descriptor-evidence] PASS "
        f"project_id={payload.get('project_id')} form={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

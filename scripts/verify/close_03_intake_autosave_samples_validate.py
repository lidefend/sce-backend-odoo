#!/usr/bin/env python3
"""Validate CLOSE-03 project-intake autosave contract samples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
DEFAULT_SAMPLES = (
    ROOT
    / ".runtime/agent-runs/CLOSE-03-PROJECT-INTAKE-DRAFT-RESTORE-20261119"
    / "intake_autosave_samples"
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_payload(path: Path) -> dict:
    body = load(path)
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    if not isinstance(data, dict):
        raise RuntimeError(f"{path}: contract payload is not an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--samples", default=str(DEFAULT_SAMPLES))
    args = parser.parse_args()

    validator = Draft202012Validator(load(Path(args.schema)))
    root = Path(args.samples)
    summary = load(root / "summary.json")
    if summary.get("schema") != "close_03.intake_autosave_samples.v1":
        raise RuntimeError("unexpected sample schema")
    if summary.get("summary", {}).get("status") != "PASS":
        raise RuntimeError("sample collection did not pass")
    entries = summary.get("entries") or {}
    required_entries = {"project_intake", "project_record", "payment_create"}
    if set(entries) != required_entries:
        raise RuntimeError(f"entry set mismatch: {sorted(entries)}")

    validation_rows = []
    for key in sorted(required_entries):
        entry = entries[key]
        contract = contract_payload(root / str(entry["contract_path"]))
        errors = sorted(validator.iter_errors(contract), key=lambda error: list(error.path))
        if errors:
            raise RuntimeError(
                f"{key} schema errors: "
                + "; ".join(
                    f"$.{'.'.join(map(str, error.path))}: {error.message}"
                    for error in errors[:8]
                )
            )
        policy = ((contract.get("runtimeContract") or {}).get("intakeAutosave") or {})
        if key == "project_intake":
            if policy.get("enabled") is not True:
                raise RuntimeError("project-intake policy is not enabled")
            if policy.get("scope") != "project_intake_standard":
                raise RuntimeError("project-intake scope mismatch")
            if policy.get("retention", {}).get("seconds") != 86400:
                raise RuntimeError("project-intake retention is not 24 hours")
            if not policy.get("fields"):
                raise RuntimeError("project-intake allowed fields are empty")
            if not any(row.get("inputKind") == "relation" and row.get("relation") for row in policy["fields"]):
                raise RuntimeError("project-intake relation field is missing")
            if entry.get("minimal_create_values", {}).get("name") in (None, ""):
                raise RuntimeError("minimal create input has no name")
        elif policy.get("enabled"):
            raise RuntimeError(f"{key} unexpectedly enables intake autosave")
        validation_rows.append({
            "entry": key,
            "schema": "passed",
            "policy_enabled": policy.get("enabled") is True,
            "field_count": len(policy.get("fields") or []),
        })

    result = {
        "schema": "close_03.intake_autosave_validation.v1",
        "status": "PASS",
        "entries": validation_rows,
    }
    (root / "validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[close-03-intake-samples] VALIDATION PASS entries={len(validation_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

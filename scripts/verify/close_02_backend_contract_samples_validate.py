#!/usr/bin/env python3
"""Validate raw CLOSE-02 V2 contracts and field-query sample invariants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
DEFAULT_SAMPLES = ROOT / ".runtime/agent-runs/CLOSE-02-FIELD-QUERY-SORT-DETAIL-20261118/search_contract_samples"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--samples", default=str(DEFAULT_SAMPLES))
    args = parser.parse_args()

    schema = _load(Path(args.schema))
    validator = Draft202012Validator(schema)
    samples_root = Path(args.samples)
    summary = _load(samples_root / "summary.json")
    if summary.get("schema") != "close_02.backend_search_contract_samples.v1":
        raise RuntimeError("unexpected sample schema")
    if summary.get("summary", {}).get("status") != "PASS":
        raise RuntimeError("runtime sample collection did not pass")

    checks: list[dict[str, Any]] = []
    for entry in summary.get("entries") or []:
        key = str(entry.get("key") or "")
        envelope = _load(samples_root / str(entry["contract_path"]))
        contract = envelope.get("data") if isinstance(envelope.get("data"), dict) else envelope
        errors = sorted(validator.iter_errors(contract), key=lambda error: list(error.path))
        if errors:
            raise RuntimeError("%s contract schema errors: %s" % (
                key,
                "; ".join("%s: %s" % ("$." + ".".join(map(str, error.path)), error.message) for error in errors[:8]),
            ))

        primary_order = str(
            (((contract.get("dataContract") or {}).get("dataSource") or {}).get("primary") or {})
            .get("params", {})
            .get("order")
            or ""
        ).strip()
        search = contract.get("searchContract") if isinstance(contract.get("searchContract"), dict) else {}
        fields = search.get("fields") if isinstance(search.get("fields"), list) else []
        if not primary_order:
            raise RuntimeError("%s primary order missing" % key)
        if str(((search.get("defaults") or {}).get("order") or "")).strip() != primary_order:
            raise RuntimeError("%s search defaults order mismatch" % key)
        if not fields:
            raise RuntimeError("%s native search fields missing" % key)
        for row in fields:
            if not isinstance(row, dict):
                raise RuntimeError("%s native search field row is not an object" % key)
            for required in ("field", "type", "operator", "operators", "occurrence_key", "native_locator"):
                if not row.get(required):
                    raise RuntimeError("%s native search field %s missing %s" % (
                        key,
                        row.get("field") or "<unknown>",
                        required,
                    ))
        samples = entry.get("samples") if isinstance(entry.get("samples"), dict) else {}
        if int(((samples.get("zero_result") or {}).get("total") or 0)) != 0:
            raise RuntimeError("%s valid-zero sample is not zero" % key)
        if not (samples.get("text_hit") or {}).get("page_2_ids"):
            raise RuntimeError("%s second page is empty" % key)
        checks.append({
            "entry": key,
            "schema": "passed",
            "field_count": len(fields),
            "order": primary_order,
            "page_size": entry.get("effective", {}).get("page_size"),
            "zero_result": 0,
        })

    result = {
        "schema": "close_02.backend_search_contract_validation.v1",
        "status": "PASS",
        "entries": checks,
    }
    output = samples_root / "validation.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[close-02-backend-samples] VALIDATION PASS entries=%s" % len(checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

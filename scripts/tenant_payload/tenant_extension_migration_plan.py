#!/usr/bin/env python3
"""Validate a private tenant-extension migration plan.

The product repository owns this neutral validator only. Customer-specific
column maps and values stay in a private user-data package. The default and
only repository-safe mode is dry-run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


STABLE_KEY = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
ALLOWED_TYPES = {
    "char",
    "text",
    "boolean",
    "integer",
    "float",
    "monetary",
    "date",
    "datetime",
    "selection",
    "many2one",
}


def validate(plan: object) -> dict[str, object]:
    errors: list[dict[str, object]] = []
    entries = plan.get("entries") if isinstance(plan, dict) else None
    if not isinstance(entries, list):
        entries = []
        errors.append({"reason_code": "PLAN_ENTRIES_REQUIRED"})
    identities = set()
    for index, raw in enumerate(entries):
        if not isinstance(raw, dict):
            errors.append({"index": index, "reason_code": "ENTRY_OBJECT_REQUIRED"})
            continue
        identity = (
            str(raw.get("company_scope") or ""),
            str(raw.get("model") or ""),
            str(raw.get("extension_key") or ""),
        )
        if not all(identity):
            errors.append({"index": index, "reason_code": "OWNER_IDENTITY_REQUIRED"})
        elif identity in identities:
            errors.append({"index": index, "reason_code": "DUPLICATE_EXTENSION_IDENTITY"})
        identities.add(identity)
        key = identity[2]
        if not STABLE_KEY.fullmatch(key) or key.startswith(
            ("x_", "p1_", "uc_", "legacy_")
        ):
            errors.append({"index": index, "reason_code": "UNSTABLE_EXTENSION_KEY"})
        if raw.get("data_type") not in ALLOWED_TYPES:
            errors.append({"index": index, "reason_code": "UNSUPPORTED_DATA_TYPE"})
        if raw.get("owner_confirmed") is not True:
            errors.append({"index": index, "reason_code": "OWNER_NOT_CONFIRMED"})
        if raw.get("drop_old_column") is True:
            errors.append({"index": index, "reason_code": "OLD_COLUMN_DROP_FORBIDDEN"})
    digest = hashlib.sha256(
        json.dumps(plan, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return {
        "schema_version": "field-arch-p0-03.migration-plan.v1",
        "result": "PASS" if not errors else "BLOCKED",
        "mode": "dry-run",
        "entry_count": len(entries),
        "plan_sha256": digest,
        "old_columns_deleted": 0,
        "business_values_modified": 0,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--mode", choices=("dry-run",), default="dry-run")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = validate(json.loads(Path(args.plan).read_text(encoding="utf-8")))
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

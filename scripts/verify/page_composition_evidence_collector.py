#!/usr/bin/env python3
"""Independent Page Composition Evidence Collector.

Consumes a raw, potentially handwritten evidence file, validates each item
against the Evidence Contract, binds it to a target page, and emits a bundle
plus a guard-consumable projection. Handwritten JSON is treated as untrusted
input: an item can only reach ``VERIFIED`` when its provenance integrity,
scope and freshness checks all pass, and human-provided declarations can never
be promoted to trusted evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from page_composition_evidence_contract import (
    COLLECTOR_VERSION,
    utc_now_iso,
    validate_evidence_item,
)

GUARD_EVIDENCE_KEY_BY_RULE = {
    "PC-007": "legacy_fallback_sources",
    "PC-008": "permission_evidence",
    "PC-009": "version_compatibility_evidence",
    "PC-010": "historical_node_identity_evidence",
}


def collect(raw: dict[str, Any], repository_sha: str, contract_version: str | None = None) -> dict[str, Any]:
    target_page = raw.get("target_page") or {}
    model = target_page.get("model")
    action_id = target_page.get("action_id")
    view_id = target_page.get("view_id")
    if not all((model is not None, action_id is not None, view_id is not None)):
        raise ValueError("target_page must declare model, action_id and view_id")

    sha = repository_sha
    version = contract_version or raw.get("contract_version") or ""

    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_item in raw.get("items") or []:
        if not isinstance(raw_item, dict):
            items.append(
                {
                    "evidence_id": _text(str(raw_item)),
                    "verification_status": "INVALID",
                    "evidence_grade": "NOT_VERIFIED",
                    "structural_errors": ["item is not a mapping"],
                    "scope_matched": False,
                    "stale": False,
                }
            )
            continue
        result = validate_evidence_item(raw_item, target_page, sha)
        evidence_id = str(raw_item.get("evidence_id") or "")
        if evidence_id in seen_ids:
            result = dict(result)
            result["verification_status"] = "INVALID"
            result["evidence_grade"] = "NOT_VERIFIED"
            result["structural_errors"] = list(result.get("structural_errors") or []) + [
                f"duplicate evidence_id: {evidence_id}"
            ]
            result["item"]["verification_status"] = "INVALID"
            result["item"]["evidence_grade"] = "NOT_VERIFIED"
        if evidence_id:
            seen_ids.add(evidence_id)
        items.append(result)

    summary = {
        "total": len(items),
        "VERIFIED": sum(1 for r in items if r["verification_status"] == "VERIFIED"),
        "UNVERIFIED": sum(1 for r in items if r["verification_status"] == "UNVERIFIED"),
        "SCOPE_MISMATCH": sum(1 for r in items if r["verification_status"] == "SCOPE_MISMATCH"),
        "STALE": sum(1 for r in items if r["verification_status"] == "STALE"),
        "INVALID": sum(1 for r in items if r["verification_status"] == "INVALID"),
    }

    guard_evidence: dict[str, list[dict[str, Any]]] = {}
    for rule, key in GUARD_EVIDENCE_KEY_BY_RULE.items():
        guard_evidence.setdefault(key, [])
        for result in items:
            item = result.get("item")
            if isinstance(item, dict) and item.get("applies_to_rule") == rule:
                guard_evidence[key].append(item)

    untrusted = [
        result.get("item", {}).get("evidence_id")
        for result in items
        if result["verification_status"] != "VERIFIED"
    ]

    return {
        "collector_version": COLLECTOR_VERSION,
        "collected_at": utc_now_iso(),
        "repository_sha": sha,
        "contract_version": version,
        "target_page": target_page,
        "items": [r["item"] for r in items],
        "summary": summary,
        "untrusted": untrusted,
        "guard_evidence": guard_evidence,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--repository-sha", required=True)
    parser.add_argument("--contract-version", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        raw_text = Path(args.input).read_text(encoding="utf-8")
    except OSError as exc:
        print(json.dumps({"collector_error": f"input unreadable: {exc}"}), file=sys.stderr)
        return 2

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(json.dumps({"collector_error": f"invalid JSON: {exc}"}), file=sys.stderr)
        return 2

    if not isinstance(raw, dict):
        print(json.dumps({"collector_error": "input must be a JSON object"}), file=sys.stderr)
        return 2

    try:
        bundle = collect(raw, args.repository_sha, args.contract_version or None)
    except ValueError as exc:
        print(json.dumps({"collector_error": str(exc)}), file=sys.stderr)
        return 2

    Path(args.output).write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

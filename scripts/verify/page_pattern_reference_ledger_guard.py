#!/usr/bin/env python3
"""Fail-closed guard for the page-pattern reference detail ledger.

The ledger records reference details that cannot be implemented safely from the
current authoritative payload, and it states its own completion rule: no
``needs_work`` item may remain, and every contract gap must name an
authoritative owner, evidence and a follow-up target.  Nothing enforced that
rule, so a gap could sit in the file with no owner, no next action and no way to
tell a deliberate difference from an unrecorded defect.

This guard makes the stated rule real.  It does not judge whether a gap is
acceptable; it refuses a ledger entry that does not say who owns it and what
closes it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = (
    ROOT
    / "docs/frontend_productization/rendering-detail/page-pattern-reference-detail-ledger-v1.json"
)

SURFACES = frozenset(
    {"login", "shell", "collection", "readonly-detail", "task", "workspace", "responsive"}
)
OWNER_RE = re.compile(r"^(?:P[0-4]\b|evidence\b)")
MIN_FOLLOW_UP = 12


def audit(ledger: object) -> list[str]:
    """Return the list of rule violations.  An empty list means the ledger holds."""
    findings: list[str] = []
    if not isinstance(ledger, dict):
        return ["ledger must be a JSON object"]

    vocabulary = ledger.get("statusVocabulary")
    if not isinstance(vocabulary, list) or not vocabulary:
        findings.append("statusVocabulary must be a non-empty list")
        vocabulary = []
    vocabulary = [str(item) for item in vocabulary]

    if not str(ledger.get("completionRule") or "").strip():
        findings.append("completionRule must be stated")

    details = ledger.get("details")
    if not isinstance(details, list) or not details:
        findings.append("details must be a non-empty list")
        return findings

    seen_keys: set[str] = set()
    for index, entry in enumerate(details):
        where = f"details[{index}]"
        if not isinstance(entry, dict):
            findings.append(f"{where}: entry must be an object")
            continue

        key = str(entry.get("key") or "").strip()
        if not key:
            findings.append(f"{where}: key is required")
        elif key in seen_keys:
            findings.append(f"{where}: duplicate key {key}")
        else:
            seen_keys.add(key)
        where = f"{key or where}"

        status = str(entry.get("status") or "").strip()
        if status not in vocabulary:
            findings.append(f"{where}: status {status!r} is not in the declared vocabulary")
            continue

        surface = str(entry.get("surface") or "").strip()
        if surface not in SURFACES:
            findings.append(f"{where}: unknown surface {surface!r}")

        if status == "needs_work":
            findings.append(
                f"{where}: needs_work may not remain in a ledger declared complete"
            )
            continue

        if status != "contract_gap":
            continue

        owner = str(entry.get("owner") or "").strip()
        if not OWNER_RE.match(owner):
            findings.append(
                f"{where}: contract gap must name an authoritative owner "
                f"(P0-P4 layer or evidence); got {owner!r}"
            )

        follow_up = str(entry.get("followUp") or "").strip()
        if len(follow_up) < MIN_FOLLOW_UP:
            findings.append(
                f"{where}: contract gap must name the follow-up target that closes it"
            )

        if not str(entry.get("authority") or "").strip():
            findings.append(f"{where}: contract gap must name its authority")

    return findings


def main() -> int:
    if not LEDGER.is_file():
        print(f"[page_pattern_reference_ledger_guard] FAIL missing={LEDGER}")
        return 1
    try:
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"[page_pattern_reference_ledger_guard] FAIL invalid json: {error}")
        return 1

    findings = audit(ledger)
    if findings:
        print(f"[page_pattern_reference_ledger_guard] FAIL findings={len(findings)}")
        for finding in findings:
            print(f"- {finding}")
        return 1

    details = ledger.get("details") or []
    gaps = sum(1 for item in details if isinstance(item, dict) and item.get("status") == "contract_gap")
    print(f"[page_pattern_reference_ledger_guard] PASS entries={len(details)} owned_gaps={gaps}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

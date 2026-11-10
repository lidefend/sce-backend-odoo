#!/usr/bin/env python3
"""Require every frontend split site to have an explicit parsing owner."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = ROOT / "docs/architecture/split_usage_allowlist.json"
SPLIT_RE = re.compile(r"\.split\s*\(")


def inspect(root: Path = ROOT, allowlist_path: Path | None = None) -> dict:
    web_src = root / "frontend/apps/web/src"
    allowlist_path = allowlist_path or root / "docs/architecture/split_usage_allowlist.json"
    errors: list[str] = []
    try:
        payload = json.loads(allowlist_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return {"errors": [f"invalid allowlist: {exc}"], "files": {}, "total": 0}

    if payload.get("schema_version") != 1:
        errors.append("allowlist schema_version must be 1")
    if payload.get("scope") != "frontend/apps/web/src":
        errors.append("allowlist scope must be frontend/apps/web/src")
    mechanisms = payload.get("mechanisms")
    registered = payload.get("files")
    if not isinstance(mechanisms, dict) or not mechanisms:
        errors.append("allowlist mechanisms must be a non-empty object")
        mechanisms = {}
    if not isinstance(registered, dict):
        errors.append("allowlist files must be an object")
        registered = {}

    for name, record in mechanisms.items():
        if not isinstance(record, dict):
            errors.append(f"mechanism {name} must be an object")
            continue
        if not str(record.get("owner", "")).strip():
            errors.append(f"mechanism {name} is missing owner")
        if not str(record.get("reason", "")).strip():
            errors.append(f"mechanism {name} is missing reason")
        if name == "record_identity_contract_gap" and not str(record.get("contract_defect", "")).strip():
            errors.append("record_identity_contract_gap must name a contract defect")

    discovered: dict[str, int] = {}
    for path in sorted(web_src.rglob("*")):
        if path.suffix not in {".vue", ".ts", ".js", ".html"} or not path.is_file():
            continue
        count = len(SPLIT_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))
        if count:
            discovered[path.relative_to(root).as_posix()] = count

    for relative, record in sorted(registered.items()):
        if not isinstance(record, dict):
            errors.append(f"allowlist file entry must be an object: {relative}")
            continue
        expected = record.get("count")
        mechanism = record.get("mechanism")
        if not isinstance(expected, int) or expected <= 0:
            errors.append(f"allowlist count must be positive: {relative}")
        if mechanism not in mechanisms:
            errors.append(f"unknown split mechanism: {relative}: {mechanism}")
        actual = discovered.get(relative)
        if actual is None:
            errors.append(f"stale split allowlist entry: {relative}")
        elif expected != actual:
            errors.append(f"split count drift: {relative}: declared={expected} actual={actual}")

    for relative, count in sorted(discovered.items()):
        if relative not in registered:
            errors.append(f"unregistered split site: {relative} count={count}")

    return {
        "errors": errors,
        "files": {relative: registered.get(relative, {}) for relative in sorted(discovered)},
        "total": sum(discovered.values()),
    }


def main() -> int:
    result = inspect()
    if result["errors"]:
        print("[frontend_split_usage_guard] FAIL")
        for error in result["errors"]:
            print(f"- {error}")
        return 1
    mechanisms = {
        value.get("mechanism")
        for value in result["files"].values()
        if isinstance(value, dict)
    }
    print("[frontend_split_usage_guard] PASS")
    print(f"files={len(result['files'])} occurrences={result['total']} mechanisms={len(mechanisms - {None})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

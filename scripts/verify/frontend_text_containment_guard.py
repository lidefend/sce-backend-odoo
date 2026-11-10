#!/usr/bin/env python3
"""Validate information-containment ownership and governed cascade overrides."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = ROOT / "docs/architecture/text_containment_allowlist.json"
NOWRAP_RE = re.compile(r"white-space\s*:\s*nowrap")
ELLIPSIS_RE = re.compile(r"text-overflow\s*:\s*ellipsis")
IMPORTANT_RE = re.compile(r"!important\b")
MY_WORK = "frontend/apps/web/src/components/business/MyWorkApprovalWorkspace.vue"


def inspect(root: Path = ROOT, allowlist_path: Path | None = None) -> dict:
    web_src = root / "frontend/apps/web/src"
    allowlist_path = allowlist_path or root / "docs/architecture/text_containment_allowlist.json"
    errors: list[str] = []
    try:
        policy = json.loads(allowlist_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return {"errors": [f"invalid text containment allowlist: {exc}"], "nowrap_files": 0, "important": 0}

    nowrap_files: set[str] = set()
    overlap_files: set[str] = set()
    important_by_file: dict[str, int] = {}
    for path in sorted(web_src.rglob("*")):
        if path.suffix not in {".vue", ".ts", ".css", ".html"} or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        if NOWRAP_RE.search(text):
            nowrap_files.add(relative)
            if ELLIPSIS_RE.search(text):
                overlap_files.add(relative)
        important_count = len(IMPORTANT_RE.findall(text))
        if important_count:
            important_by_file[relative] = important_count

    important = sum(important_by_file.values())
    important_overrides = {
        str(record.get("file", "")).strip(): record.get("max")
        for record in policy.get("importantOverrides", [])
        if isinstance(record, dict) and str(record.get("file", "")).strip()
    }
    for relative, count in sorted(important_by_file.items()):
        limit = important_overrides.get(relative, 0)
        if not isinstance(limit, int) or limit < 0:
            limit = 0
        if count > limit:
            errors.append(
                f"unregistered !important declarations in {relative}: {count} (allowed {limit})"
            )

    structural = {
        str(record.get("file", "")).strip()
        for record in policy.get("structuralOverlapExceptions", [])
        if isinstance(record, dict)
    }
    information_records = [
        record for record in policy.get("informationOverlapFiles", [])
        if isinstance(record, dict)
    ]
    information = {str(record.get("styleLocation", "")).strip() for record in information_records}
    expected_overlap = structural | information
    unregistered = sorted(overlap_files - expected_overlap)
    stale = sorted(expected_overlap - overlap_files)
    for relative in unregistered:
        errors.append(f"unregistered information-bearing nowrap/ellipsis overlap: {relative}")
    for relative in stale:
        errors.append(f"stale nowrap/ellipsis allowlist entry: {relative}")

    for record in information_records:
        owner = str(record.get("fallbackOwner", "")).strip()
        owner_path = root / owner
        if not owner_path.is_file():
            errors.append(f"information overlap fallback owner is missing: {owner}")
            continue
        owner_text = owner_path.read_text(encoding="utf-8", errors="ignore")
        if "title" not in owner_text and "aria-label" not in owner_text:
            errors.append(f"information overlap fallback owner has no full-value fallback: {owner}")

    runtime_policy = policy.get("policy") if isinstance(policy.get("policy"), dict) else {}
    identity_lines = runtime_policy.get("recordIdentityTemporaryMaxLines")
    if not isinstance(identity_lines, int) or identity_lines <= 0:
        errors.append("recordIdentityTemporaryMaxLines must be a positive integer")
    else:
        my_work = root / MY_WORK
        text = my_work.read_text(encoding="utf-8") if my_work.is_file() else ""
        if f"-webkit-line-clamp: {identity_lines};" not in text:
            errors.append(f"temporary record identity clamp does not match policy: expected {identity_lines}")

    title_lines = runtime_policy.get("businessTitleMaxLines")
    if not isinstance(title_lines, int) or title_lines <= 0:
        errors.append("businessTitleMaxLines must be a positive integer")

    return {
        "errors": errors,
        "nowrap_files": len(nowrap_files),
        "overlap_files": len(overlap_files),
        "information_files": len(information),
        "important": important,
    }


def main() -> int:
    result = inspect()
    if result["errors"]:
        print("[frontend_text_containment_guard] FAIL")
        for error in result["errors"]:
            print(f"- {error}")
        return 1
    print("[frontend_text_containment_guard] PASS")
    print(
        f"nowrap_files={result['nowrap_files']} overlap_files={result['overlap_files']} "
        f"information_files={result['information_files']} important={result['important']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

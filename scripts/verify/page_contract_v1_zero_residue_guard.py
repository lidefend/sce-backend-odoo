#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config/contract/page_contract_v1_retirement_manifest.json"
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".vue", ".mk", ".json", ".yml", ".yaml", ".md"}


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"root must be object: {path}")
    return payload


def _files(path: Path):
    if path.is_file():
        yield path
        return
    for candidate in path.rglob("*"):
        if candidate.is_file() and candidate.suffix.lower() in TEXT_SUFFIXES:
            yield candidate


def _token_pattern(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")


def _v1_values(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            if "v1" in str(key).lower():
                yield str(key)
            yield from _v1_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _v1_values(child)
    elif "v1" in str(value).lower():
        yield str(value)


def main() -> int:
    errors: list[str] = []
    manifest = _load(MANIFEST)
    allowed = {
        (str(row.get("token") or ""), str(row.get("path") or "")): str(row.get("classification") or "")
        for row in manifest.get("allowlist") or []
        if isinstance(row, dict)
    }
    used_allowlist: set[tuple[str, str]] = set()
    for root_name in manifest.get("scanRoots") or []:
        scan_root = ROOT / str(root_name)
        if not scan_root.exists():
            errors.append(f"scan root missing: {root_name}")
            continue
        for path in _files(scan_root):
            relative = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in manifest.get("forbiddenTokens") or []:
                token = str(token)
                if not _token_pattern(token).search(text):
                    continue
                occurrence = (token, relative)
                if occurrence in allowed:
                    matching_lines = [line for line in text.splitlines() if _token_pattern(token).search(line)]
                    classification = allowed[occurrence]
                    if classification == "negative_assertion" and not all(
                        "assertNotIn" in line or "assert not in" in line for line in matching_lines
                    ):
                        errors.append(f"allowlisted negative assertion has positive occurrence {token}: {relative}")
                    elif classification not in {"negative_assertion", "negative_guard"}:
                        errors.append(f"unsupported allowlist classification {classification}: {token}: {relative}")
                    else:
                        used_allowlist.add(occurrence)
                else:
                    errors.append(f"unregistered retired token {token}: {relative}")
    stale = sorted(set(allowed) - used_allowlist)
    for token, path in stale:
        errors.append(f"stale allowlist entry {token}: {path}")

    architecture_snapshot_root = ROOT / "docs/architecture/unified_page_contract_v2/snapshots"
    for legacy_snapshot in sorted(architecture_snapshot_root.glob("*_v1.json")):
        errors.append(f"retired architecture snapshot filename: {legacy_snapshot.relative_to(ROOT).as_posix()}")
    for row in manifest.get("requiredArchitectureSnapshots") or []:
        if not isinstance(row, dict):
            errors.append("required architecture snapshot entry must be object")
            continue
        relative = str(row.get("path") or "")
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"required architecture snapshot missing: {relative}")
            continue
        try:
            payload = _load(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"required architecture snapshot invalid {relative}: {exc}")
            continue
        if payload.get("snapshotVersion") != row.get("snapshotVersion"):
            errors.append(f"architecture snapshotVersion mismatch: {relative}")
        if payload.get("contractVersion") != row.get("contractVersion"):
            errors.append(f"architecture contractVersion mismatch: {relative}")

    required_snapshots: dict[str, dict] = {}
    for snapshot_name in manifest.get("requiredSnapshots") or []:
        snapshot_path = ROOT / str(snapshot_name)
        if not snapshot_path.is_file():
            errors.append(f"required snapshot missing: {snapshot_name}")
            continue
        try:
            snapshot = _load(snapshot_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"required snapshot invalid {snapshot_name}: {exc}")
            continue
        required_snapshots[str(snapshot_name)] = snapshot
        if snapshot.get("error"):
            errors.append(f"required snapshot contains error: {snapshot_name}")

    system_snapshot = required_snapshots.get("docs/contract/snapshots/system_init_intent_admin.json", {})
    if system_snapshot.get("error"):
        errors.append("system.init snapshot contains error")
    system_data = system_snapshot.get("ui_contract_raw") if isinstance(system_snapshot.get("ui_contract_raw"), dict) else {}
    allowed_v1_values = {str(value) for value in manifest.get("allowedSystemInitV1Values") or []}
    for value in sorted(set(_v1_values(system_data))):
        if value not in allowed_v1_values:
            errors.append(f"unregistered v1 value in system.init snapshot: {value}")
    navigation = system_data.get("navigation") if isinstance(system_data.get("navigation"), dict) else {}
    route_authority = navigation.get("route_authority") if isinstance(navigation.get("route_authority"), dict) else {}
    scene_ready = system_data.get("scene_ready_contract") if isinstance(system_data.get("scene_ready_contract"), dict) else {}
    page_contracts = system_data.get("page_contracts") if isinstance(system_data.get("page_contracts"), dict) else {}
    for label, contract in (
        ("navigation", navigation),
        ("route_authority", route_authority),
        ("scene_ready_contract", scene_ready),
        ("page_contracts", page_contracts),
    ):
        if contract.get("contract_version") != "2.0.0" or contract.get("schema_version") != "2.0.0":
            errors.append(f"{label} must expose contract/schema version 2.0.0")

    v2_snapshot = required_snapshots.get("docs/contract/snapshots/ui_contract_v2_intent_admin.json", {})
    if v2_snapshot.get("error"):
        errors.append("ui.contract.v2 snapshot contains error")
    v2_data = v2_snapshot.get("ui_contract_raw") if isinstance(v2_snapshot.get("ui_contract_raw"), dict) else {}
    for key in ("pageInfo", "layoutContract", "dataContract", "actionContract", "statusContract"):
        if not isinstance(v2_data.get(key), dict):
            errors.append(f"ui.contract.v2 snapshot missing {key}")

    if errors:
        print("[page_contract_v1_zero_residue_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[page_contract_v1_zero_residue_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

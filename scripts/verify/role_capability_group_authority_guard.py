#!/usr/bin/env python3
"""Lock the role -> capability -> entry visibility authorization direction."""

from __future__ import annotations

import ast
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = ROOT / "addons/smart_construction_core"
MANIFEST = MODULE_ROOT / "__manifest__.py"
REBINDING_MAP = MODULE_ROOT / "data/menu_entry_group_rebinding.json"
ACCEPTANCE_CSV = ROOT / "docs/product/frontend_business_entry_acceptance_v1.csv"
DEFAULT_MODULE = "smart_construction_core."
REF_CALL = re.compile(r"ref\(\s*'([^']+)'\s*\)")


def _qualify(xmlid: str) -> str:
    value = str(xmlid or "").strip()
    if not value:
        return ""
    return value if "." in value else DEFAULT_MODULE + value


def manifest_group_xml_paths(manifest: Path = MANIFEST) -> list[Path]:
    body = ast.literal_eval(manifest.read_text(encoding="utf-8"))
    data = body.get("data") or []
    return [
        manifest.parent / relative
        for relative in data
        if str(relative).endswith(".xml")
    ]


def _commands(eval_text: str) -> list[tuple]:
    normalized = REF_CALL.sub(lambda match: repr(_qualify(match.group(1))), str(eval_text or ""))
    try:
        value = ast.literal_eval(normalized)
    except (SyntaxError, ValueError) as exc:
        raise ValueError(f"invalid implied_ids eval: {eval_text!r}") from exc
    return value if isinstance(value, list) else []


def group_graph(paths: list[Path]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for path in paths:
        if not path.is_file():
            continue
        root = ET.parse(path).getroot()
        for record in root.findall(".//record[@model='res.groups']"):
            group = _qualify(record.get("id") or "")
            if not group:
                continue
            edges = graph.setdefault(group, set())
            for field in record.findall("field[@name='implied_ids']"):
                for command in _commands(field.get("eval") or ""):
                    if not isinstance(command, (list, tuple)) or not command:
                        continue
                    operation = int(command[0])
                    if operation == 6 and len(command) >= 3:
                        edges.clear()
                        edges.update(_qualify(item) for item in command[2] or [])
                    elif operation == 4 and len(command) >= 2:
                        payload = command[1]
                        values = payload if isinstance(payload, (list, tuple)) else [payload]
                        edges.update(_qualify(item) for item in values if str(item).strip())
                    elif operation == 3 and len(command) >= 2:
                        payload = command[1]
                        values = payload if isinstance(payload, (list, tuple)) else [payload]
                        edges.difference_update(_qualify(item) for item in values if str(item).strip())
    return graph


def reference_order_violations(paths: list[Path]) -> list[dict]:
    defined = set()
    errors = []
    for path in paths:
        if not path.is_file():
            continue
        root = ET.parse(path).getroot()
        for record in root.findall(".//record[@model='res.groups']"):
            group = _qualify(record.get("id") or "")
            for field in record.findall("field[@name='implied_ids']"):
                for command in _commands(field.get("eval") or ""):
                    if not isinstance(command, (list, tuple)) or not command:
                        continue
                    if int(command[0]) not in {4, 6}:
                        continue
                    payload = command[2] if int(command[0]) == 6 and len(command) >= 3 else command[1]
                    values = payload if isinstance(payload, (list, tuple)) else [payload]
                    for target in values:
                        target = _qualify(target)
                        if target.startswith(DEFAULT_MODULE) and target not in defined:
                            errors.append({
                                "code": "GROUP_REFERENCE_BEFORE_DEFINITION",
                                "group": group,
                                "target": target,
                                "file": path.relative_to(ROOT).as_posix(),
                            })
            if group:
                defined.add(group)
    return errors


def _kind(group: str) -> str:
    if ".group_sc_role_" in group or group.endswith(".group_sc_business_full"):
        return "role"
    if ".group_sc_cap_" in group or group.endswith(".group_sc_internal_user"):
        return "capability"
    if ".group_sc_entry_p" in group:
        return "entry"
    return "native_or_other"


def violations(graph: dict[str, set[str]]) -> list[dict]:
    errors: list[dict] = []
    for group, targets in sorted(graph.items()):
        kind = _kind(group)
        for target in sorted(targets):
            target_kind = _kind(target)
            if kind == "role" and target_kind not in {"role", "capability"}:
                errors.append({
                    "code": "ROLE_DIRECT_PERMISSION_EDGE",
                    "group": group,
                    "target": target,
                    "target_kind": target_kind,
                })
            elif kind == "capability" and target_kind == "role":
                errors.append({
                    "code": "CAPABILITY_TO_ROLE_EDGE",
                    "group": group,
                    "target": target,
                })
            elif kind == "entry" and target_kind in {"role", "capability"}:
                errors.append({
                    "code": "ENTRY_REVERSE_EDGE",
                    "group": group,
                    "target": target,
                })
            elif kind == "capability" and target_kind == "entry" and ".group_sc_cap_entry_scope_p" not in group:
                errors.append({
                    "code": "ENTRY_CARRIER_BYPASSES_SCOPE_CAPABILITY",
                    "group": group,
                    "target": target,
                })

    for number in range(1, 15):
        suffix = f"p{number:02d}"
        capability = f"smart_construction_core.group_sc_cap_entry_scope_{suffix}"
        carrier = f"smart_construction_core.group_sc_entry_{suffix}"
        if graph.get(capability) != {carrier}:
            errors.append({
                "code": "ENTRY_SCOPE_CAPABILITY_MISMATCH",
                "group": capability,
                "expected": [carrier],
                "actual": sorted(graph.get(capability, set())),
            })

    full = "smart_construction_core.group_sc_cap_entry_scope_full"
    expected_full = {
        f"smart_construction_core.group_sc_cap_entry_scope_p{number:02d}"
        for number in range(1, 15)
    }
    if graph.get(full) != expected_full:
        errors.append({
            "code": "FULL_ENTRY_SCOPE_MISMATCH",
            "group": full,
            "missing": sorted(expected_full - graph.get(full, set())),
            "unexpected": sorted(graph.get(full, set()) - expected_full),
        })

    business_full = "smart_construction_core.group_sc_cap_business_full"
    if full not in graph.get(business_full, set()):
        errors.append({
            "code": "BUSINESS_FULL_SCOPE_NOT_DERIVED",
            "group": business_full,
            "missing": [full],
        })
    return errors


def acceptance_role_authority_violations(
    rebinding_path: Path = REBINDING_MAP,
    acceptance_path: Path = ACCEPTANCE_CSV,
) -> list[dict]:
    rebinding = json.loads(rebinding_path.read_text(encoding="utf-8"))
    with acceptance_path.open(encoding="utf-8", newline="") as handle:
        rows = {row["menu_xmlid"]: row for row in csv.DictReader(handle)}
    errors = []
    for menu_xmlid, entry_key in sorted(rebinding.items()):
        row = rows.get(menu_xmlid)
        if row is None:
            errors.append({"code": "ACCEPTANCE_ROW_MISSING", "menu_xmlid": menu_xmlid})
            continue
        try:
            authority = json.loads(row.get("role_authority") or "")
        except (TypeError, ValueError):
            errors.append({"code": "ACCEPTANCE_AUTHORITY_INVALID", "menu_xmlid": menu_xmlid})
            continue
        layer = next(
            (
                item for item in authority.get("menu_chain") or []
                if isinstance(item, dict) and item.get("menu_xmlid") == menu_xmlid
            ),
            None,
        )
        expected = [f"smart_construction_core.group_sc_{entry_key}"]
        if layer is None:
            errors.append({"code": "ACCEPTANCE_ENTRY_LAYER_MISSING", "menu_xmlid": menu_xmlid})
        elif layer.get("groups") != expected:
            errors.append({
                "code": "ACCEPTANCE_MENU_GROUP_DRIFT",
                "menu_xmlid": menu_xmlid,
                "expected": expected,
                "actual": layer.get("groups") or [],
            })
    return errors


def main() -> int:
    paths = manifest_group_xml_paths()
    report = reference_order_violations(paths)
    report.extend(violations(group_graph(paths)))
    report.extend(acceptance_role_authority_violations())
    if report:
        print("role_capability_group_authority_guard FAIL")
        for row in report:
            print(f"  - {row}")
        return 1
    print(
        "role_capability_group_authority_guard PASS: "
        "role groups have no direct permission edges; entry carriers are capability-owned; "
        "acceptance menu authority matches the rebinding fact"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Static regression: settlement capabilities gain contract read, never contract write."""
from __future__ import annotations

import csv
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SECURITY = ROOT / "addons" / "smart_construction_core" / "security"

# Mirrors smart_construction_core/__manifest__.py data order for res.groups.
GROUP_FILES = (
    "sc_groups.xml",
    "sc_capability_groups.xml",
    "contract_settlement_capability_bridge.xml",
    "sc_role_groups.xml",
    "runtime_user_permission_groups.xml",
)

MODULE = "smart_construction_core."
SETTLEMENT_USER = MODULE + "group_sc_cap_settlement_user"
SETTLEMENT_MANAGER = MODULE + "group_sc_cap_settlement_manager"
CONTRACT_READ = MODULE + "group_sc_cap_contract_read"
CONTRACT_MODEL = "model_construction_contract"

REF_RE = re.compile(r"ref\('([^']+)'\)")
OP_RE = re.compile(r"\((\d+),\s*(?:0,\s*)?(\[[^\]]*\]|ref\('([^']+)'\))\)", re.S)


def _ref(value):
    return value if "." in value else MODULE + value


def _implied_operations():
    for filename in GROUP_FILES:
        for record in ET.parse(SECURITY / filename).getroot().iter("record"):
            if record.get("model") != "res.groups" or not record.get("id"):
                continue
            group = _ref(record.get("id"))
            for field in record.findall("field"):
                if field.get("name") != "implied_ids":
                    continue
                value = field.get("eval") or ""
                if not value.strip():
                    continue
                if value.strip() == "[]":
                    yield group, [(6, set())]
                    continue
                operations = []
                for match in OP_RE.finditer(value):
                    payload = match.group(2)
                    refs = (
                        {_ref(item) for item in REF_RE.findall(payload)}
                        if payload.startswith("[")
                        else {_ref(match.group(3))}
                    )
                    operations.append((int(match.group(1)), refs))
                if not operations:
                    raise AssertionError(
                        "unsupported implied_ids eval for %s: %s" % (group, value)
                    )
                yield group, operations


def _graph():
    graph = {}
    for group, operations in _implied_operations():
        current = graph.setdefault(group, set())
        for code, refs in operations:
            if code == 6:
                current.clear()
                current.update(refs)
            elif code == 4:
                current.update(refs)
            elif code == 3:
                current.difference_update(refs)
            elif code == 5:
                current.clear()
            else:
                raise AssertionError(
                    "unsupported implied_ids command %s for %s" % (code, group)
                )
    return graph


def _closure(graph, start):
    seen = set()
    stack = [start]
    while stack:
        for implied in graph.get(stack.pop(), ()):
            if implied not in seen:
                seen.add(implied)
                stack.append(implied)
    return seen


def _contract_acl_rows():
    rows = []
    with (SECURITY / "ir.model.access.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["model_id:id"] != CONTRACT_MODEL:
                continue
            rows.append(
                (
                    row["group_id:id"],
                    tuple(
                        int(row[key])
                        for key in (
                            "perm_read",
                            "perm_write",
                            "perm_create",
                            "perm_unlink",
                        )
                    ),
                )
            )
    return rows


class TestSettlementContractReadCapability(unittest.TestCase):
    def test_settlement_user_explicitly_implies_contract_read(self):
        graph = _graph()
        self.assertIn(SETTLEMENT_USER, graph)
        self.assertIn(CONTRACT_READ, graph[SETTLEMENT_USER])

    def test_settlement_manager_inherits_user_and_contract_read(self):
        graph = _graph()
        self.assertIn(SETTLEMENT_MANAGER, graph)
        self.assertIn(SETTLEMENT_USER, graph[SETTLEMENT_MANAGER])
        self.assertIn(CONTRACT_READ, _closure(graph, SETTLEMENT_MANAGER))

    def test_contract_read_acl_is_read_only(self):
        rows = [perms for group, perms in _contract_acl_rows() if group == CONTRACT_READ]
        self.assertEqual(rows, [(1, 0, 0, 0)])

    def test_settlement_user_closure_has_no_contract_write_group(self):
        write_groups = {
            group for group, perms in _contract_acl_rows() if perms != (1, 0, 0, 0)
        }
        self.assertTrue(write_groups)
        self.assertFalse(_closure(_graph(), SETTLEMENT_USER) & write_groups)


if __name__ == "__main__":
    unittest.main()

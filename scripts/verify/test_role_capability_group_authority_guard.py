from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify.role_capability_group_authority_guard import (
    acceptance_role_authority_violations,
    group_graph,
    manifest_group_xml_paths,
    reference_order_violations,
    replay_drift_violations,
    violations,
)


VALID = """<?xml version="1.0"?>
<odoo><data>
  <record id="group_sc_entry_p01" model="res.groups"/>
  <record id="group_sc_cap_entry_scope_p01" model="res.groups">
    <field name="implied_ids" eval="[(4, ref('group_sc_entry_p01'))]"/>
  </record>
  <record id="group_sc_role_example" model="res.groups">
    <field name="implied_ids" eval="[(4, ref('group_sc_cap_entry_scope_p01'))]"/>
  </record>
</data></odoo>
"""


def _graph(text: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "groups.xml"
        path.write_text(text, encoding="utf-8")
        return group_graph([path])


def _with_record(record: str) -> str:
    return VALID.replace("</data>", record + "</data>")


class RoleCapabilityGroupAuthorityGuardTest(unittest.TestCase):
    def test_installed_group_declarations_replay_without_intermediate_changes(self):
        self.assertEqual(replay_drift_violations(manifest_group_xml_paths()), [])

    def test_guard_rejects_reset_then_restore_despite_same_final_graph(self):
        text = _with_record("""
          <record id="group_sc_role_example" model="res.groups">
            <field name="implied_ids" eval="[(6, 0, [])]"/>
          </record>
          <record id="group_sc_role_example" model="res.groups">
            <field name="implied_ids" eval="[(4, ref('group_sc_cap_entry_scope_p01'))]"/>
          </record>
        """)
        self.assertEqual(_graph(text), _graph(VALID))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "groups.xml"
            path.write_text(text)
            self.assertEqual(len(replay_drift_violations([path])), 2)

    def test_role_can_reach_entry_only_through_capability(self):
        graph = _graph(VALID)
        self.assertEqual(
            graph["smart_construction_core.group_sc_role_example"],
            {"smart_construction_core.group_sc_cap_entry_scope_p01"},
        )

    def test_role_identity_composition_is_not_a_permission_edge(self):
        graph = _graph(_with_record("""
        <record id="group_sc_role_composite" model="res.groups">
          <field name="implied_ids" eval="[(4, ref('group_sc_role_example'))]"/>
        </record>
        """))
        self.assertNotIn(
            "ROLE_DIRECT_PERMISSION_EDGE",
            {row["code"] for row in violations(graph)},
        )

    def test_direct_role_to_entry_edge_is_rejected(self):
        graph = _graph(VALID.replace(
            "ref('group_sc_cap_entry_scope_p01')",
            "ref('group_sc_entry_p01')",
        ))
        codes = {row["code"] for row in violations(graph)}
        self.assertIn("ROLE_DIRECT_PERMISSION_EDGE", codes)

    def test_capability_to_role_reverse_edge_is_rejected(self):
        graph = _graph(_with_record("""
        <record id="group_sc_cap_example" model="res.groups">
          <field name="implied_ids" eval="[(4, ref('group_sc_role_example'))]"/>
        </record>
        """))
        codes = {row["code"] for row in violations(graph)}
        self.assertIn("CAPABILITY_TO_ROLE_EDGE", codes)

    def test_non_scope_capability_cannot_bypass_into_entry_carrier(self):
        graph = _graph(_with_record("""
        <record id="group_sc_cap_example" model="res.groups">
          <field name="implied_ids" eval="[(4, ref('group_sc_entry_p01'))]"/>
        </record>
        """))
        codes = {row["code"] for row in violations(graph)}
        self.assertIn("ENTRY_CARRIER_BYPASSES_SCOPE_CAPABILITY", codes)

    def test_repository_role_to_entry_closure_is_preserved(self):
        graph = group_graph(manifest_group_xml_paths())

        def closure(group):
            seen = set()
            pending = [group]
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                pending.extend(graph.get(current, ()))
            return {
                node.rsplit(".group_sc_entry_", 1)[-1]
                for node in seen
                if ".group_sc_entry_p" in node
            }

        expected = {
            "group_sc_role_accounting_read": {f"p{n:02d}" for n in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14)},
            "group_sc_role_accounting_user": {f"p{n:02d}" for n in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14)},
            "group_sc_role_accounting_manager": {f"p{n:02d}" for n in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14)},
            "group_sc_role_cost_user": {f"p{n:02d}" for n in (2, 3, 6, 7, 8, 9, 10, 11, 13)},
            "group_sc_role_executive": {f"p{n:02d}" for n in (3, 5, 7, 13)},
            "group_sc_role_finance_user": {f"p{n:02d}" for n in (2, 3, 5, 6, 8, 13)},
            "group_sc_role_finance_manager": {f"p{n:02d}" for n in (2, 3, 5, 6, 8, 13)},
            "group_sc_role_owner": {f"p{n:02d}" for n in (2, 3, 5, 6, 7, 9, 11, 13, 14)},
            "group_sc_role_project_manager": {f"p{n:02d}" for n in (2, 5, 6, 7, 11, 13, 14)},
            "group_sc_role_project_user": {f"p{n:02d}" for n in (3, 5, 6, 7, 8, 9, 10, 11, 14)},
            "group_sc_role_operation_user": {"p06"},
            "group_sc_business_full": {f"p{n:02d}" for n in range(1, 15)},
            "group_sc_role_experience": {f"p{n:02d}" for n in (1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14)},
        }
        for role, expected_carriers in expected.items():
            xmlid = f"smart_construction_core.{role}"
            self.assertEqual(closure(xmlid), expected_carriers, role)

    def test_experience_non_entry_closure_has_no_business_capability(self):
        graph = group_graph(manifest_group_xml_paths())
        role = "smart_construction_core.group_sc_role_experience"
        bridge = "smart_construction_core.group_sc_cap_internal_identity"
        self.assertEqual(graph[bridge], {"base.group_user"})
        seen, pending = set(), [role]
        while pending:
            node = pending.pop()
            if node not in seen:
                seen.add(node)
                pending.extend(graph.get(node, ()))
        non_entry = {node for node in seen if not any(
            token in node for token in (".group_sc_entry_p", ".group_sc_cap_entry_scope_")
        )}
        self.assertEqual(non_entry, {role, bridge, "base.group_user"})

    def test_repository_acceptance_authority_matches_rebinding_fact(self):
        self.assertEqual(acceptance_role_authority_violations(), [])

    def test_repository_group_references_respect_data_load_order(self):
        self.assertEqual(reference_order_violations(manifest_group_xml_paths()), [])


if __name__ == "__main__":
    unittest.main()

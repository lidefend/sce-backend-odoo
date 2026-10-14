#!/usr/bin/env python3
"""Negative controls for the derived company-scope ceiling generator."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sc_data_scope_ceiling_generate as gen  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def write_tree(tmp: str, declaration: dict, owner: str = "demo_module") -> tuple[Path, Path]:
    root = Path(tmp)
    models = root / "addons" / owner / "models"
    models.mkdir(parents=True, exist_ok=True)
    models.joinpath("definition.py").write_text(
        '_name = "demo.company"\n_name = "demo.widget"\n', encoding="utf-8"
    )
    target = root / "config/tenant/module_sets.v1.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"product_modules": [owner]}), encoding="utf-8")
    declarations = root / "declarations.json"
    declarations.write_text(json.dumps(declaration), encoding="utf-8")
    return root, declarations


class CeilingGeneratorTest(unittest.TestCase):
    def test_committed_record_set_matches_the_declaration(self) -> None:
        """The repository's own record set is exactly what the declaration renders,
        so a hand edit or a stale regeneration fails here instead of shipping."""
        declared = json.loads(
            (ROOT / "scripts/verify/data_scope_declarations.json").read_text(encoding="utf-8")
        )
        expected = gen.render(ROOT, declared)
        committed = gen.OUTPUT.read_text(encoding="utf-8")
        self.assertEqual(expected, committed)
        self.assertGreater(expected.count('model="ir.rule"'), 0)

    def test_enforced_and_deferred_render_one_record_each(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, _ = write_tree(
                raw,
                {
                    "enforced": [{"model": "demo.company", "anchor": "company_id"}],
                    "deferred": [
                        {"issue": "DEMO-1", "anchor": "project_id", "models": ["demo.widget"]}
                    ],
                },
            )
            body = gen.render(root, json.loads((root / "declarations.json").read_text()))
            self.assertEqual(2, body.count('model="ir.rule"'))
            self.assertIn("rule_sc_data_scope_demo_company", body)
            self.assertIn("rule_sc_data_scope_demo_widget", body)
            self.assertIn("('company_id'", body)
            self.assertIn("('project_id'", body)

    def test_entries_dedupe_and_prefer_the_enforced_anchor(self) -> None:
        pairs = gen.entries(
            {
                "enforced": [{"model": "demo.company", "anchor": "company_id"}],
                "deferred": [
                    {"issue": "DEMO-1", "anchor": "project_id", "unsetOwner": "unknown",
                     "models": ["demo.company", "demo.widget"]}
                ],
            }
        )
        self.assertEqual(
            [("demo.company", "company_id", None), ("demo.widget", "project_id", "unknown")],
            pairs,
        )

    def test_cross_module_model_reference_is_prefixed(self) -> None:
        local = gen.record_xml("demo.company", "company_id", gen.OWNER_MODULE)
        foreign = gen.record_xml("demo.company", "company_id", "other_module")
        self.assertIn('ref="model_demo_company"', local)
        self.assertIn('ref="other_module.model_demo_company"', foreign)

    def test_rule_is_global_and_covers_the_anchor(self) -> None:
        xml = gen.record_xml("demo.company", "company_id", gen.OWNER_MODULE)
        self.assertNotIn('name="groups"', xml)
        # The unset-owner branch is an explicit '&' conjunct and the XML escapes it.
        self.assertIn(
            "['|', ('company_id', '=', False), '&amp;', ('company_id', 'in', company_ids), "
            "('company_id', 'in', user._sc_data_company_ids())]",
            xml,
        )
        self.assertEqual(4, xml.count("eval=\"True\""))

    def test_own_company_anchor_keeps_global_configuration_visible(self) -> None:
        """An unset own company column is Odoo global configuration, so it stays
        visible while the purpose scope still bounds the owned records."""
        self.assertEqual(
            "['|', ('company_id', '=', False), '&', ('company_id', 'in', company_ids), "
            "('company_id', 'in', user._sc_data_company_ids())]",
            gen.ceiling_domain("company_id"),
        )

    def test_unset_branch_needs_an_explicit_conjunct(self) -> None:
        """A bare implicit AND would bind the purpose term to the whole
        disjunction and silently drop the pass-through instead of keeping it."""
        domain = gen.ceiling_domain("company_id")
        self.assertIn("'&'", domain)
        self.assertNotIn("('company_id', '=', False), ('company_id', 'in', company_ids),",
                         domain)

    def test_relation_anchor_default_keeps_shared_reference_visible(self) -> None:
        """A relation anchor without a declared unset-owner reading stays at the
        shared-reference default: an unset optional link is shared data.

        The unset branch has to name the traversed relation itself: Odoo compiles
        ``('project_id.company_id', '=', False)`` to ``project_id IN (SELECT id
        FROM project_project WHERE company_id IS NULL)``, which is NULL for a
        record whose ``project_id`` is NULL. A single ``= False`` term therefore
        hid exactly the unattributed records the shared reading keeps visible.
        """
        self.assertEqual(
            "['|', '|', ('project_id', '=', False), "
            "('project_id.company_id', '=', False), '&', "
            "('project_id.company_id', 'in', company_ids), "
            "('project_id.company_id', 'in', user._sc_data_company_ids())]",
            gen.ceiling_domain("project_id.company_id"),
        )

    def test_traversal_unset_branch_is_the_union_of_parent_and_own_column(self) -> None:
        """The unset reading covers both facts the declaration means."""
        self.assertEqual(
            ["('project_id', '=', False)", "('project_id.company_id', '=', False)"],
            gen.unset_branch_terms("project_id.company_id"),
        )
        self.assertEqual(
            ["('company_id', '=', False)"], gen.unset_branch_terms("company_id")
        )

    def test_traversal_unknown_stays_strict_without_an_unset_term(self) -> None:
        """A declared unknown reading must not gain the union branch."""
        domain = gen.ceiling_domain("project_id.company_id", "unknown")
        self.assertNotIn("= False", domain)
        self.assertNotIn("('project_id', '=', False)", domain)

    def test_declared_unknown_ownership_renders_a_strict_ceiling(self) -> None:
        """A model whose only ownership path is optional declares that an unset
        anchor is incomplete attribution, so the pass-through must disappear."""
        domain = gen.ceiling_domain("project_id.company_id", "unknown")
        self.assertNotIn("= False", domain)
        self.assertEqual(
            "[('project_id.company_id', 'in', company_ids), "
            "('project_id.company_id', 'in', user._sc_data_company_ids())]",
            domain,
        )
        xml = gen.record_xml("demo.owner", "project_id.company_id", gen.OWNER_MODULE, "unknown")
        self.assertNotIn("= False", xml)

    def test_unknown_unset_owner_value_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            gen.ceiling_domain("company_id", "sometimes")

    def test_purpose_authority_is_the_single_company_source(self) -> None:
        """The data-purpose dimension is resolved by the principal method, not
        by a second predicate declared per model."""
        xml = gen.record_xml("demo.owner", "project_id.company_id", gen.OWNER_MODULE)
        self.assertIn("user._sc_data_company_ids()", xml)
        self.assertNotIn("data_purpose", xml)

    def test_model_without_an_owning_product_module_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, _ = write_tree(
                raw, {"enforced": [{"model": "ghost.model", "anchor": "company_id"}]}
            )
            with self.assertRaises(SystemExit):
                gen.render(root, json.loads((root / "declarations.json").read_text()))

    def test_display_survives_an_out_of_root_output(self) -> None:
        self.assertEqual("/tmp/x.xml", gen.display(Path("/tmp/x.xml"), Path("/repo")))


if __name__ == "__main__":
    unittest.main()

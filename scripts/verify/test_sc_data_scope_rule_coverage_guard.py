#!/usr/bin/env python3
"""Negative controls for the data-scope rule coverage guard."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sc_data_scope_rule_coverage_guard as guard  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

RULE = """
    <record id="rule_{ident}" model="ir.rule">
        <field name="name">scope {ident}</field>
        <field name="model_id" ref="{ref}"/>
        <field name="domain_force">{domain}</field>
        <field name="perm_read" eval="True"/>
{groups}    </record>
"""


def define(tmp: Path, module: str, model: str) -> None:
    target = tmp / "addons" / module / "models" / "definition.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f'_name = "{model}"\n', encoding="utf-8")


def write_case(tmp: Path, rules: list[dict], declarations: dict) -> tuple[Path, Path]:
    fixture = tmp / "addons/demo_module/security/demo_rules.xml"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    define(tmp, "demo_module", "demo.model")
    body = "".join(
        RULE.format(
            ident=rule["ident"],
            ref=rule["ref"],
            domain=rule["domain"],
            groups=rule.get("groups", ""),
        )
        for rule in rules
    )
    fixture.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<odoo><data noupdate="0">\n'
        + body
        + "</data></odoo>\n",
        encoding="utf-8",
    )
    declarations_path = tmp / "declarations.json"
    declarations_path.write_text(json.dumps(declarations), encoding="utf-8")
    return tmp, declarations_path


GLOBAL_DOMAIN = "['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]"


class DataScopeRuleCoverageGuardTest(unittest.TestCase):
    def test_repository_declaration_passes(self) -> None:
        report = guard.check(ROOT, ROOT / "scripts/verify/data_scope_declarations.json")
        self.assertEqual([], report["failures"])
        self.assertGreater(report["enforced"], 0)

    def test_missing_rule_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertIn("no ir.rule references", report["failures"][0])

    def test_group_scoped_rule_is_not_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [{"ident": "a", "ref": "model_demo_model", "domain": GLOBAL_DOMAIN,
                  "groups": '        <field name="groups" eval="[(4, ref(\'base.group_user\'))]"/>\n'}],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertIn("group-scoped", report["failures"][0])

    def test_wrong_anchor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [{"ident": "a", "ref": "model_demo_model",
                  "domain": "['|', ('project_id.company_id', '=', False)]"}],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertIn("none constrains company_id", report["failures"][0])

    def test_exempt_without_reason_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [],
                {"enforced": [], "exempt": [{"model": "demo.model", "reason": "  "}]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertIn("exemption without a reason", report["failures"][0])

    def test_enforced_and_exempt_overlap_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [{"ident": "a", "ref": "model_demo_model", "domain": GLOBAL_DOMAIN}],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}],
                 "exempt": [{"model": "demo.model", "reason": "claimed both"}]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("enforced and exempt" in f for f in report["failures"]))

    def test_duplicate_rule_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [{"ident": "a", "ref": "model_demo_model", "domain": GLOBAL_DOMAIN},
                 {"ident": "a", "ref": "model_demo_other", "domain": GLOBAL_DOMAIN}],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("duplicate ir.rule xml ids" in f for f in report["failures"]))

    def test_prefixed_cross_module_ref_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [{"ident": "a", "ref": "other_module.model_demo_model", "domain": GLOBAL_DOMAIN}],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            define(root, "other_module", "demo.model")
            report = guard.check(root, declarations)
            self.assertEqual([], report["failures"])

    def test_unresolvable_rule_ref_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [{"ident": "a", "ref": "other_module.model_demo_model", "domain": GLOBAL_DOMAIN}],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("cannot resolve" in f for f in report["failures"]))

    def test_ref_to_other_model_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [{"ident": "a", "ref": "model_demo_other", "domain": GLOBAL_DOMAIN}],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertIn("no ir.rule references", report["failures"][0])


if __name__ == "__main__":
    unittest.main()

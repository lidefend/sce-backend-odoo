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



COMPANY_MODEL = """
class DemoCompany(models.Model):
    _name = "demo.company"
    company_id = fields.Many2one("res.company")


class DemoWizard(models.TransientModel):
    _name = "demo.wizard"
    company_id = fields.Many2one("res.company")
"""

WIZARD_ONLY = """
class DemoWizard(models.TransientModel):
    _name = "demo.wizard"
    company_id = fields.Many2one("res.company")
"""


def write_company_case(tmp: Path, rules: list[dict], declarations: dict,
                       module_sets: dict | None = None) -> tuple[Path, Path]:
    """A fixture whose module defines company-bearing models, so the guard's
    source-derived coverage universe is non-empty."""
    root, declarations_path = write_case(tmp, rules, declarations)
    (root / "addons/demo_module/models/company.py").write_text(COMPANY_MODEL, encoding="utf-8")
    if module_sets is not None:
        target = root / "config/tenant/module_sets.v1.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(module_sets), encoding="utf-8")
    return root, declarations_path


def company_rule(ref: str, ident: str = "c") -> dict:
    return {"ident": ident, "ref": ref, "domain": GLOBAL_DOMAIN}


class DataScopeRuleCoverageGuardTest(unittest.TestCase):
    def test_repository_declaration_passes(self) -> None:
        report = guard.check(ROOT, ROOT / "scripts/verify/data_scope_declarations.json")
        self.assertEqual([], report["failures"])
        self.assertGreater(report["enforced"], 0)
        self.assertEqual([], report["uncovered"])
        self.assertGreater(report["universe"], report["enforced"])
        self.assertGreater(report["deferred"], 0)

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


    def test_uncovered_company_model_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw), [],
                {"enforced": [], "exempt": []},
            )
            (root / "addons/demo_module/models/company.py").write_text(
                COMPANY_MODEL, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("no company ceiling" in f for f in report["failures"]))
            self.assertIn("demo.company", report["uncovered"])

    def test_transient_company_model_is_not_a_gap(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw), [],
                {"enforced": [], "exempt": [{"model": "demo.wizard", "dimension": "transient",
                                             "owner_module": "demo_module",
                                             "reason": "transient wizard"}]},
            )
            (root / "addons/demo_module/models/company.py").write_text(
                WIZARD_ONLY, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertNotIn("demo.wizard", report["uncovered"])
            self.assertEqual([], report["failures"])

    def test_source_company_rule_covers_without_a_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [company_rule("model_demo_company")],
                {"enforced": [], "exempt": []},
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual([], report["failures"])
            self.assertIn("demo.company", [m for m in ["demo.company"]])
            self.assertEqual(1, report["source_company_rule"])

    def test_exempt_requires_a_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw), [],
                {"enforced": [], "exempt": [{"model": "demo.model", "owner_module": "demo_module",
                                             "reason": "platform reference"}]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("must name one dimension" in f for f in report["failures"]))

    def test_exempt_unknown_dimension_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw), [],
                {"enforced": [], "exempt": [{"model": "demo.model", "dimension": "whatever",
                                             "owner_module": "demo_module",
                                             "reason": "platform reference"}]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("must name one dimension" in f for f in report["failures"]))

    def test_exempt_owner_module_must_define_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw), [],
                {"enforced": [], "exempt": [{"model": "demo.model", "dimension": "master_data",
                                             "owner_module": "other_module",
                                             "reason": "shared reference"}]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("does not define this model" in f for f in report["failures"]))

    def test_placeholder_reason_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw), [],
                {"enforced": [], "exempt": [{"model": "demo.model", "dimension": "master_data",
                                             "owner_module": "demo_module",
                                             "reason": "needs an ownership anchor: record as an anchor gap"}]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("placeholder" in f for f in report["failures"]))

    def test_declared_transient_must_be_transient(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw), [],
                {"enforced": [], "exempt": [{"model": "demo.company", "dimension": "transient",
                                             "owner_module": "demo_module",
                                             "reason": "claimed transient"}]},
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("not a TransientModel" in f for f in report["failures"]))

    def test_deferred_group_requires_issue_and_reason(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw), [],
                {"enforced": [], "exempt": [],
                 "deferred": [{"anchor": "company_id", "owner_module": "demo_module",
                               "models": ["demo.company"]}]},
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("issue id" in f for f in report["failures"]))
            self.assertTrue(any("reason is missing" in f for f in report["failures"]))

    def test_deferred_model_without_a_ceiling_rule_fails(self) -> None:
        """A deferred model still needs the global ceiling; deferral orders the
        delivery, it does not excuse the missing isolation."""
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw), [],
                {"enforced": [], "exempt": [],
                 "deferred": [{"issue": "DEMO-1", "anchor": "company_id",
                               "owner_module": "demo_module",
                               "reason": "ceiling derived from the declaration",
                               "models": ["demo.company"]}]},
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("no ir.rule references" in f for f in report["failures"]))
            self.assertTrue(any("(deferred DEMO-1)" in f for f in report["failures"]))

    def test_deferred_model_with_its_ceiling_rule_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [company_rule("model_demo_company")],
                {"enforced": [], "exempt": [],
                 "deferred": [{"issue": "DEMO-1", "anchor": "company_id",
                               "owner_module": "demo_module",
                               "reason": "ceiling derived from the declaration",
                               "models": ["demo.company"]}]},
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual([], report["failures"])
            self.assertEqual("passed", report["status"])
            self.assertEqual(1, report["deferred"])

    def test_deferred_model_with_only_a_group_rule_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [{"ident": "c", "ref": "model_demo_company", "domain": GLOBAL_DOMAIN,
                  "groups": '        <field name="groups" eval="[(4, ref(\'base.group_user\'))]"/>\n'}],
                {"enforced": [], "exempt": [],
                 "deferred": [{"issue": "DEMO-1", "anchor": "company_id",
                               "owner_module": "demo_module",
                               "reason": "group union must not widen the ceiling",
                               "models": ["demo.company"]}]},
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("group union could widen it" in f for f in report["failures"]))

    def test_deferred_and_exempt_overlap_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw), [],
                {"enforced": [],
                 "exempt": [{"model": "demo.company", "dimension": "master_data",
                             "owner_module": "demo_module", "reason": "shared reference"}],
                 "deferred": [{"issue": "DEMO-1", "anchor": "company_id",
                               "owner_module": "demo_module",
                               "reason": "claims the same model twice",
                               "models": ["demo.company"]}]},
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("exempt and deferred" in f for f in report["failures"]))


if __name__ == "__main__":
    unittest.main()

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

# The ceiling an ``enforced`` model receives from the generator intersects the
# allowed-company selector with the purpose authority. A ``source_bounded`` model
# must carry the same two facts in its named rule; a company-only domain is a
# different (weaker) fact and must not stand in for it.
SOURCE_BOUNDED_DOMAIN = (
    "[('company_id', 'in', company_ids), "
    "('company_id', 'in', user._sc_data_company_ids())]"
)



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

CONSTANT_NAMED_MODEL = '''
POLICY_MODEL = "demo.policy"


class DemoPolicy(models.Model):
    _name = POLICY_MODEL
    company_id = fields.Many2one("res.company")
'''

EXTENSION_ONLY_COMPANY_MODEL = '''
class DemoOwner(models.Model):
    _name = "demo.owner"
    project_id = fields.Many2one("project.project")


class DemoOwnerExtension(models.Model):
    _inherit = "demo.owner"
    company_id = fields.Many2one("res.company", related="project_id.company_id", store=True)
'''

UNRESOLVABLE_INHERIT_MODEL = '''
class DemoOwner(models.Model):
    _name = "demo.owner"
    project_id = fields.Many2one("project.project")


class DemoOwnerExtension(models.Model):
    _inherit = EXTERNAL_COMPANY_MIXIN
    company_id = fields.Many2one("res.company")
'''

UNRESOLVABLE_NAMED_MODEL = '''
class DemoBroken(models.Model):
    _name = DYNAMIC_NAME
    company_id = fields.Many2one("res.company")
'''


RELATION_ANCHORED_MODEL = '''
class DemoOwner(models.Model):
    _name = "demo.owner"
    project_id = fields.Many2one("project.project")
'''


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


def source_bounded_rule(ref: str, ident: str = "c") -> dict:
    return {"ident": ident, "ref": ref, "domain": SOURCE_BOUNDED_DOMAIN}


WIZARD_EXEMPT = {
    "model": "demo.wizard",
    "dimension": "transient",
    "owner_module": "demo_module",
    "reason": "transient wizard carries no persistent company rows",
}


class DataScopeRuleCoverageGuardTest(unittest.TestCase):
    def test_extension_class_company_field_enters_universe(self) -> None:
        """A company_id declared by an _inherit-only class still owns the model."""
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [company_rule("model_demo_model")],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            (root / "addons/demo_module/models/extension.py").write_text(
                EXTENSION_ONLY_COMPANY_MODEL, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("demo.owner" in f for f in report["failures"]), report["failures"]
            )

        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [
                    company_rule("model_demo_model"),
                    company_rule("model_demo_owner", "owner"),
                    company_rule("model_demo_company", "company"),
                ],
                {
                    "enforced": [
                        {"model": "demo.model", "anchor": "company_id"},
                        {"model": "demo.owner", "anchor": "company_id"},
                        {"model": "demo.company", "anchor": "company_id"},
                    ],
                    "exempt": [WIZARD_EXEMPT],
                },
                {"product_modules": ["demo_module"]},
            )
            (root / "addons/demo_module/models/extension.py").write_text(
                EXTENSION_ONLY_COMPANY_MODEL, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertEqual([], report["failures"])
            self.assertEqual([], report["uncovered"])
            self.assertEqual(3, report["universe"])

    def test_unresolvable_inherit_on_company_class_fails_closed(self) -> None:
        """A company-bearing class whose _inherit cannot resolve must not escape."""
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [company_rule("model_demo_model")],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            (root / "addons/demo_module/models/extension.py").write_text(
                UNRESOLVABLE_INHERIT_MODEL, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("does not resolve to a model name" in f for f in report["failures"]),
                report["failures"],
            )

    def test_repository_declaration_passes(self) -> None:
        report = guard.check(ROOT, ROOT / "scripts/verify/data_scope_declarations.json")
        self.assertEqual([], report["failures"])
        self.assertGreater(report["enforced"], 0)
        self.assertEqual([], report["uncovered"])
        self.assertGreater(report["deferred"], 0)
        self.assertGreater(report["source_bounded_count"], 0)
        # every universe model carries exactly one explicit declaration; a
        # source_bounded entry may name a relation-anchored model outside the
        # company_id universe, so the accounting must use its in-universe count
        self.assertEqual(
            report["universe"],
            report["enforced_in_universe"]
            + report["exempt_in_universe"]
            + report["deferred_in_universe"]
            + report["source_bounded_in_universe"]
            + len(report["uncovered"]),
        )

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

    def test_group_clear_command_is_global_coverage(self) -> None:
        """A rule that clears every group is global, not group-scoped.

        ``(5, 0, 0)`` is the ORM unlink-all command and ``(6, 0, [])`` replaces
        the group set with nothing. Both leave a rule that no group union can
        widen, so reading them as a group scope under-reported the global rules.
        """
        for expression in ("[(5, 0, 0)]", "[(6, 0, [])]"):
            with self.subTest(expression=expression):
                with tempfile.TemporaryDirectory() as raw:
                    root, declarations = write_case(
                        Path(raw),
                        [{"ident": "a", "ref": "model_demo_model", "domain": GLOBAL_DOMAIN,
                          "groups": f'        <field name="groups" eval="{expression}"/>\n'}],
                        {"enforced": [{"model": "demo.model", "anchor": "company_id"}],
                         "exempt": []},
                    )
                    report = guard.check(root, declarations)
                    self.assertEqual("passed", report["status"], report["failures"])
                    self.assertEqual(1, report["global_rules_seen"])

    def test_group_clear_command_beside_a_real_group_stays_group_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [{"ident": "a", "ref": "model_demo_model", "domain": GLOBAL_DOMAIN,
                  "groups": ('        <field name="groups" eval="[(5, 0, 0), '
                             '(4, ref(\'base.group_user\'))]"/>\n')}],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}],
                 "exempt": []},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertIn("group-scoped", report["failures"][0])
            self.assertEqual(0, report["global_rules_seen"])

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
            self.assertTrue(any("carries no enforced" in f for f in report["failures"]))
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

    def test_undeclared_transient_model_still_fails(self) -> None:
        """Transient is a declaration, not an automatic pass."""
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw), [], {"enforced": [], "exempt": []}
            )
            (root / "addons/demo_module/models/company.py").write_text(
                WIZARD_ONLY, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertIn("demo.wizard", report["uncovered"])

    def test_constant_named_company_model_is_still_in_the_universe(self) -> None:
        """A model that names itself through a constant must not escape the universe."""
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw), [],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            (root / "addons/demo_module/models/policy.py").write_text(
                CONSTANT_NAMED_MODEL, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertIn("demo.policy", report["uncovered"])

    def test_declared_constant_named_model_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw),
                [
                    {"ident": "m", "ref": "model_demo_model", "domain": GLOBAL_DOMAIN},
                    {"ident": "p", "ref": "model_demo_policy", "domain": GLOBAL_DOMAIN},
                ],
                {
                    "enforced": [
                        {"model": "demo.model", "anchor": "company_id"},
                        {"model": "demo.policy", "anchor": "company_id"},
                    ],
                    "exempt": [],
                },
            )
            (root / "addons/demo_module/models/policy.py").write_text(
                CONSTANT_NAMED_MODEL, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertEqual([], report["failures"])
            # the constant-named model is the universe and carries its ceiling
            self.assertEqual(1, report["universe"])
            self.assertEqual(1, report["enforced_in_universe"])
            self.assertEqual([], report["uncovered"])

    def test_unresolvable_model_name_fails_closed(self) -> None:
        """An identity the guard cannot resolve must stop the run, not hide a model."""
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_case(
                Path(raw), [],
                {"enforced": [{"model": "demo.model", "anchor": "company_id"}], "exempt": []},
            )
            (root / "addons/demo_module/models/broken.py").write_text(
                UNRESOLVABLE_NAMED_MODEL, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("does not resolve to a model name" in f for f in report["failures"])
            )
            self.assertTrue(report["unresolved_model_names"])

    def test_source_rule_alone_is_not_coverage(self) -> None:
        """A rule that mentions a company column is not a declaration."""
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [company_rule("model_demo_company")],
                {"enforced": [], "exempt": []},
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertIn("demo.company", report["uncovered"])
            self.assertEqual(0, report["source_bounded_count"])

    def test_source_bounded_names_a_verified_global_rule(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [source_bounded_rule("model_demo_company")],
                {
                    "enforced": [],
                    "exempt": [WIZARD_EXEMPT],
                    "source_bounded": [
                        {
                            "model": "demo.company",
                            "anchor": "company_id",
                            "rule": "rule_c",
                            "file": "addons/demo_module/security/demo_rules.xml",
                            "reason": "bounded by the named global company rule rule_c",
                        }
                    ],
                },
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual([], report["failures"])
            self.assertEqual(["demo.company"], report["source_bounded"])

    def test_source_bounded_relation_anchored_model_stays_explicit(self) -> None:
        """A model without its own company_id column can still be company scoped
        through a parent anchor. Naming the global rule keeps that decision
        explicit instead of leaving it to absence, and the coverage accounting
        must not count it against the company_id universe."""
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [
                    company_rule("model_demo_company"),
                    {
                        "ident": "owner",
                        "ref": "model_demo_owner",
                        "domain": "[('project_id.company_id', 'in', company_ids), "
                                  "('project_id.company_id', "
                                  "'in', user._sc_data_company_ids())]",
                    },
                ],
                {
                    "enforced": [{"model": "demo.company", "anchor": "company_id"}],
                    "exempt": [WIZARD_EXEMPT],
                    "source_bounded": [
                        {
                            "model": "demo.owner",
                            "anchor": "project_id.company_id",
                            "rule": "rule_owner",
                            "file": "addons/demo_module/security/demo_rules.xml",
                            "reason": "bounded by the named global rule rule_owner on the "
                                      "parent project company anchor",
                        }
                    ],
                },
                {"product_modules": ["demo_module"]},
            )
            (root / "addons/demo_module/models/owner.py").write_text(
                RELATION_ANCHORED_MODEL, encoding="utf-8"
            )
            report = guard.check(root, declarations)
            self.assertEqual([], report["failures"])
            self.assertEqual(2, report["universe"])
            self.assertEqual(1, report["source_bounded_count"])
            self.assertEqual(0, report["source_bounded_in_universe"])
            self.assertEqual(["demo.owner"], report["source_bounded_out_of_universe"])

    def test_source_bounded_unknown_model_still_fails_closed(self) -> None:
        """Dropping the company_id requirement must not let a phantom model in."""
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [company_rule("model_demo_company")],
                {
                    "enforced": [{"model": "demo.company", "anchor": "company_id"}],
                    "exempt": [WIZARD_EXEMPT],
                    "source_bounded": [
                        {
                            "model": "ghost.line",
                            "anchor": "company_id",
                            "rule": "rule_ghost",
                            "file": "addons/demo_module/security/demo_rules.xml",
                            "reason": "bounded by the named global rule rule_ghost",
                        }
                    ],
                },
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("ghost.line" in f for f in report["failures"]), report["failures"]
            )

    def test_source_bounded_group_scoped_rule_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [{"ident": "c", "ref": "model_demo_company", "domain": GLOBAL_DOMAIN,
                  "groups": '        <field name="groups" eval="[(4, ref(\'base.group_user\'))]"/>\n'}],
                {
                    "enforced": [],
                    "exempt": [],
                    "source_bounded": [
                        {
                            "model": "demo.company",
                            "anchor": "company_id",
                            "rule": "c",
                            "file": "addons/demo_module/security/demo_rules.xml",
                            "reason": "bounded by the named global company rule c",
                        }
                    ],
                },
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("group-scoped" in f for f in report["failures"]))

    def test_source_bounded_missing_rule_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [company_rule("model_demo_company")],
                {
                    "enforced": [],
                    "exempt": [],
                    "source_bounded": [
                        {
                            "model": "demo.company",
                            "anchor": "company_id",
                            "rule": "not_a_rule",
                            "file": "addons/demo_module/security/demo_rules.xml",
                            "reason": "bounded by the named global company rule",
                        }
                    ],
                },
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("is missing, group-scoped" in f for f in report["failures"]))

    def test_source_bounded_company_only_rule_fails(self) -> None:
        """A company-only ceiling is not the data-purpose ceiling.

        The generated ceiling an ``enforced`` model gets intersects the company
        selector with ``user._sc_data_company_ids()``. A named source rule that
        constrains only the company column would still let a customer principal
        read a demo/test company's rows, so naming it must not pass.
        """
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [company_rule("model_demo_company")],
                {
                    "enforced": [],
                    "exempt": [WIZARD_EXEMPT],
                    "source_bounded": [
                        {
                            "model": "demo.company",
                            "anchor": "company_id",
                            "rule": "rule_c",
                            "file": "addons/demo_module/security/demo_rules.xml",
                            "reason": "bounded by the named global company rule rule_c",
                        }
                    ],
                },
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("user._sc_data_company_ids()" in f for f in report["failures"]),
                report["failures"],
            )

    def test_source_bounded_wrong_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, declarations = write_company_case(
                Path(raw),
                [source_bounded_rule("model_demo_company")],
                {
                    "enforced": [],
                    "exempt": [],
                    "source_bounded": [
                        {
                            "model": "demo.company",
                            "anchor": "company_id",
                            "rule": "rule_c",
                            "file": "addons/demo_module/security/elsewhere.xml",
                            "reason": "bounded by the named global company rule rule_c",
                        }
                    ],
                },
                {"product_modules": ["demo_module"]},
            )
            report = guard.check(root, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("not the declared" in f for f in report["failures"]))

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
                {"enforced": [], "exempt": [WIZARD_EXEMPT],
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

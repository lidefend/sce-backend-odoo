#!/usr/bin/env python3
"""Negative controls for the money-fact source guard."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fact_source_coverage_guard as guard  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

STANDARD_MODEL = '''
class DemoStandard(models.Model):
    _name = "demo.standard"
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: (self.env.ref("base.CNY", raise_if_not_found=False) or self.env.company.currency_id).id,
    )
'''

CALLER_CONTEXT_MODEL = '''
class DemoDerived(models.Model):
    _name = "demo.derived"
    company_id = fields.Many2one("res.company", related="project_id.company_id", store=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id)
'''

PLAIN_MODEL = '''
class DemoPlain(models.Model):
    _name = "demo.plain"
    currency_id = fields.Many2one("res.currency", required=True)
'''

INHERITED_CALLER_MODEL = '''
class DemoFactMixin(models.AbstractModel):
    _name = "demo.fact.mixin"
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id)


class DemoInheritor(models.Model):
    _name = "demo.inheritor"
    _inherit = "demo.fact.mixin"
    project_id = fields.Many2one("project.project")
'''

NO_COMPANY_COLUMN_MODEL = '''
class DemoSettlement(models.Model):
    _name = "demo.settlement"
    project_id = fields.Many2one("project.project", required=True)
    currency_id = fields.Many2one(
        "res.currency", required=True, default=lambda self: self.env.company.currency_id.id
    )
'''

WRITE_PATH_MODEL = '''
class DemoWritePath(models.Model):
    _name = "demo.writepath"
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id)

    @api.onchange("partner_id")
    def _onchange_partner(self):
        for rec in self:
            rec.currency_id = rec.partner_id.currency_id
'''

EXTENSION_OVERRIDE_MODEL = '''
class DemoOverridden(models.Model):
    _name = "demo.overridden"
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency")


class DemoOverriddenExtension(models.Model):
    _inherit = "demo.overridden"
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
'''

CONSTANT_NAMED_MODEL = '''
STANDARD_CURRENCY_MODEL = "demo.standard"


class DemoStandard(models.Model):
    _name = STANDARD_CURRENCY_MODEL
    company_id = fields.Many2one("res.company")
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: (self.env.ref("base.CNY", raise_if_not_found=False) or self.env.company.currency_id).id,
    )
'''


# The extension fixture is declared twice on the same model and both classes
# live in one file, so the duplicate registry names the same file in both roles.
# The same declaration is also a money-field override, so both registries apply.
DUPLICATE_OVERRIDE_DECLARATION = {
    "company_field_overrides": {
        "reason": "a redefinition is a decision, not a silent override",
        "models": [
            {
                "model": "demo.overridden",
                "field": "currency_id",
                "file": "models/definition.py",
                "reason": "the extension derives the currency from the owning company",
            }
        ],
    },
    "duplicate_field_declarations": {
        "reason": "a field declared twice is the union of both definitions",
        "models": [
            {
                "model": "demo.overridden",
                "field": "currency_id",
                "declarations": [
                    {
                        "file": "addons/demo_module/models/definition.py",
                        "role": "owning class",
                        "adds": "the base definition",
                    },
                    {
                        "file": "addons/demo_module/models/definition.py",
                        "role": "extension class",
                        "adds": "the company-derived currency",
                    },
                ],
                "reason": "the extension derives the currency from the owning company",
            }
        ],
    }
}


COMPANY_CURRENCY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="base.main_company" model="res.company">
        <field name="currency_id" ref="base.CNY"/>
    </record>
</odoo>
"""


def write_case(
    tmp: Path,
    source: str,
    declarations: dict,
    pin: str = "MODELS = []\n",
    extra_files: dict | None = None,
):
    module = tmp / "addons/demo_module"
    (module / "models").mkdir(parents=True, exist_ok=True)
    (module / "models/definition.py").write_text(source, encoding="utf-8")
    (module / "models/company_currency_pin.py").write_text(
        "def _ensure_standard_currency(self):\n"
        '    return "base.CNY"\n',
        encoding="utf-8",
    )
    for relative, content in (extra_files or {}).items():
        target = tmp / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    sets = tmp / "config/tenant/module_sets.v1.json"
    sets.parent.mkdir(parents=True, exist_ok=True)
    sets.write_text(json.dumps({"product_modules": ["demo_module"]}), encoding="utf-8")
    declarations_path = tmp / "declarations.json"
    declarations_path.write_text(json.dumps(declarations), encoding="utf-8")
    pin_path = tmp / "pin.py"
    pin_path.write_text(pin, encoding="utf-8")
    return tmp, declarations_path, pin_path


def run(
    tmp: Path,
    source: str,
    declarations: dict,
    pin: str = "MODELS = []\n",
    extra_files: dict | None = None,
):
    root, declarations_path, pin_path = write_case(tmp, source, declarations, pin, extra_files)
    return guard.check(root, declarations_path, "config/tenant/module_sets.v1.json", pin_path)


def authority_declaration(**overrides) -> dict:
    authority = {
        "model": "res.company",
        "module": "demo_module",
        "method": "_ensure_standard_currency",
        "currency": "CNY",
        "reason": "the named pin that keeps the company currency at the tenant standard currency",
    }
    authority.update(overrides)
    return authority


def standard_declaration(*models: str) -> dict:
    return {
        "standard_currency": {
            "currency": "CNY",
            "models": [{"model": m, "reason": "tenant standard currency document"} for m in models],
        },
        "company_currency_authority": authority_declaration(),
    }


class FactSourceCoverageGuardTest(unittest.TestCase):
    def test_repository_declaration_passes(self) -> None:
        report = guard.check(ROOT, ROOT / "scripts/verify/fact_source_declarations.json")
        self.assertEqual([], report["failures"])
        self.assertGreater(len(report["standard_currency_models"]), 0)
        self.assertGreater(len(report["caller_context_currency_models"]), 0)
        self.assertGreater(len(report["currency_write_paths"]), 0)
        self.assertEqual("verified", report["company_currency_authority"]["status"])
        self.assertGreater(len(report["duplicate_field_declarations"]), 0)
        self.assertGreater(len(report["company_currency_write_sites"]), 0)

    def test_undeclared_standard_currency_default_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), STANDARD_MODEL, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("undeclared standard-currency default" in f for f in report["failures"]))

    def test_declared_standard_model_missing_from_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), PLAIN_MODEL, standard_declaration("demo.plain"))
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("drifted from source" in f for f in report["failures"]))

    def test_standard_currency_requires_a_reason(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(
                Path(raw), STANDARD_MODEL,
                {"standard_currency": {"currency": "CNY", "models": [{"model": "demo.standard"}]}},
            )
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("without a reason" in f for f in report["failures"]))

    def test_declared_standard_currency_matches_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), STANDARD_MODEL, standard_declaration("demo.standard"))
            self.assertEqual([], report["failures"])

    def test_undeclared_runtime_pin_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(
                Path(raw), STANDARD_MODEL, standard_declaration("demo.standard"),
                pin='MODELS = [\n    "demo.standard",\n    "demo.other",\n]\n',
            )
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("undeclared models" in f for f in report["failures"]))

    def test_undeclared_caller_context_currency_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), CALLER_CONTEXT_MODEL, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("register it or derive the currency" in f for f in report["failures"]))

    def test_declared_caller_context_model_matches_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {"currency": "CNY", "models": []},
                "caller_context_currency": {
                    "issue": "CURRENCY-OWNER-ALIGNMENT-01",
                    "owner_module": "demo_module",
                    "reason": "registered money-fact alignment owed to the owning company",
                    "models": ["demo.derived"],
                },
            }
            report = run(Path(raw), CALLER_CONTEXT_MODEL, declarations)
            self.assertEqual([], report["failures"])

    def test_caller_context_requires_an_issue(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {"currency": "CNY", "models": []},
                "caller_context_currency": {
                    "owner_module": "demo_module",
                    "reason": "registered money-fact alignment owed to the owning company",
                    "models": ["demo.derived"],
                },
            }
            report = run(Path(raw), CALLER_CONTEXT_MODEL, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("without an issue id" in f for f in report["failures"]))

    def test_currency_related_and_defaulted_fails(self) -> None:
        source = '''
class DemoContradiction(models.Model):
    _name = "demo.contradiction"
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", default=lambda self: self.env.company.currency_id)
'''
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), source, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("both related and defaulted" in f for f in report["failures"]))

    def test_hard_coded_other_currency_fails(self) -> None:
        source = '''
class DemoOther(models.Model):
    _name = "demo.other"
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.USD", raise_if_not_found=False))
'''
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), source, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("hard-codes base.USD" in f for f in report["failures"]))

    def test_constant_named_model_money_fact_is_declared_or_fails(self) -> None:
        """A constant-named model is a real money fact and must be declared."""
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), CONSTANT_NAMED_MODEL, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("undeclared standard-currency default" in f for f in report["failures"]))

        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), CONSTANT_NAMED_MODEL, standard_declaration("demo.standard"))
            self.assertEqual([], report["failures"])

    def test_inherited_caller_context_currency_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), INHERITED_CALLER_MODEL, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("caller's environment company" in f for f in report["failures"]), report["failures"]
            )
            self.assertEqual(
                ["demo.inheritor"], report["caller_context_inherited_models"]
            )

        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {"currency": "CNY", "models": []},
                "caller_context_currency": {
                    "issue": "CURRENCY-OWNER-ALIGNMENT-01",
                    "owner_module": "demo_module",
                    "reason": "registered money-fact alignment owed to the owning company",
                    "models": ["demo.fact.mixin", "demo.inheritor"],
                },
            }
            report = run(Path(raw), INHERITED_CALLER_MODEL, declarations)
            self.assertEqual([], report["failures"])

    def test_caller_context_without_company_column_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), NO_COMPANY_COLUMN_MODEL, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("caller's environment company" in f for f in report["failures"]), report["failures"]
            )

        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {"currency": "CNY", "models": []},
                "caller_context_currency": {
                    "issue": "CURRENCY-OWNER-ALIGNMENT-01",
                    "owner_module": "demo_module",
                    "reason": "registered money-fact alignment owed to the owning company",
                    "models": ["demo.settlement"],
                },
            }
            report = run(Path(raw), NO_COMPANY_COLUMN_MODEL, declarations)
            self.assertEqual([], report["failures"])

    def test_currency_write_path_requires_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), WRITE_PATH_MODEL, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("written outside the field default" in f for f in report["failures"]),
                report["failures"],
            )
            self.assertEqual(["demo.writepath._onchange_partner"], report["currency_write_paths"])

        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {"currency": "CNY", "models": []},
                "currency_write_paths": {
                    "reason": "a method assignment is a second money-fact source",
                    "models": [
                        {
                            "model": "demo.writepath",
                            "methods": ["_onchange_partner"],
                            "source": "partner_id.currency_id",
                            "reason": "copies the currency of the selected partner",
                        }
                    ],
                },
            }
            report = run(Path(raw), WRITE_PATH_MODEL, declarations)
            self.assertEqual([], report["failures"])

    def test_currency_write_path_without_source_or_reason_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {"currency": "CNY", "models": []},
                "currency_write_paths": {"models": [{"model": "demo.writepath", "methods": ["_onchange_partner"]}]},
            }
            report = run(Path(raw), WRITE_PATH_MODEL, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(any("without the source relation" in f for f in report["failures"]))
            self.assertTrue(any("without a reason" in f for f in report["failures"]))

    def test_extension_class_field_override_requires_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), EXTENSION_OVERRIDE_MODEL, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("redefines company_id/currency_id" in f for f in report["failures"]),
                report["failures"],
            )
            self.assertEqual(["demo.overridden"], report["company_field_overrides"])

        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {"currency": "CNY", "models": []},
                **DUPLICATE_OVERRIDE_DECLARATION,
            }
            report = run(Path(raw), EXTENSION_OVERRIDE_MODEL, declarations)
            self.assertEqual([], report["failures"])

    def test_duplicate_field_declaration_requires_registration(self) -> None:
        """A field declared by two classes is a union and must be registered."""
        with tempfile.TemporaryDirectory() as raw:
            report = run(
                Path(raw), EXTENSION_OVERRIDE_MODEL,
                {"standard_currency": {"currency": "CNY", "models": []}},
            )
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("declared by more than one class" in f for f in report["failures"]),
                report["failures"],
            )
            self.assertEqual(
                ["demo.overridden.currency_id"], report["duplicate_field_declarations"]
            )

    def test_registered_duplicate_field_declaration_matches_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {"currency": "CNY", "models": []},
                **DUPLICATE_OVERRIDE_DECLARATION,
            }
            report = run(Path(raw), EXTENSION_OVERRIDE_MODEL, declarations)
            self.assertEqual([], report["failures"])
            self.assertEqual(
                ["demo.overridden.currency_id"], report["duplicate_field_declarations"]
            )

    def test_duplicate_field_declaration_without_reason_fails(self) -> None:
        declarations = {
            "standard_currency": {"currency": "CNY", "models": []},
            "duplicate_field_declarations": {
                "models": [{"model": "demo.overridden", "field": "currency_id"}]
            },
        }
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), EXTENSION_OVERRIDE_MODEL, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any(
                    "demo.overridden.currency_id: duplicate field declaration without a reason" in f
                    for f in report["failures"]
                ),
                report["failures"],
            )

    def test_duplicate_field_declaration_site_drift_fails(self) -> None:
        declarations = json.loads(json.dumps(DUPLICATE_OVERRIDE_DECLARATION))
        entry = declarations["duplicate_field_declarations"]["models"][0]
        entry["declarations"][1]["role"] = "owning class"
        declarations["standard_currency"] = {"currency": "CNY", "models": []}
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), EXTENSION_OVERRIDE_MODEL, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("do not match source" in f for f in report["failures"]),
                report["failures"],
            )

    def test_stale_duplicate_field_declaration_fails(self) -> None:
        """A registration that no longer matches source must not stay silent."""
        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {"currency": "CNY", "models": []},
                **DUPLICATE_OVERRIDE_DECLARATION,
            }
            report = run(Path(raw), PLAIN_MODEL, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("no longer matches source" in f for f in report["failures"]),
                report["failures"],
            )

    def test_company_currency_write_site_requires_registration(self) -> None:
        """An XML record that sets the company currency is a second fact source."""
        extra = {"addons/demo_module/data/currency.xml": COMPANY_CURRENCY_XML}
        with tempfile.TemporaryDirectory() as raw:
            report = run(
                Path(raw), STANDARD_MODEL, standard_declaration("demo.standard"),
                extra_files=extra,
            )
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("without a registration" in f for f in report["failures"]),
                report["failures"],
            )
            self.assertEqual(
                ["addons/demo_module/data/currency.xml:xml_record:base.main_company"],
                report["company_currency_write_sites"],
            )

    def test_registered_company_currency_write_site_matches_source(self) -> None:
        extra = {"addons/demo_module/data/currency.xml": COMPANY_CURRENCY_XML}
        declarations = standard_declaration("demo.standard")
        declarations["company_currency_write_sites"] = {
            "reason": "every source that writes the company currency is named",
            "sites": [
                {
                    "file": "addons/demo_module/data/currency.xml",
                    "kind": "xml_record",
                    "site": "base.main_company",
                    "reason": "the demo bootstrap sets the main company to the standard currency",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), STANDARD_MODEL, declarations, extra_files=extra)
            self.assertEqual([], report["failures"])

    def test_registered_company_currency_write_site_drift_fails(self) -> None:
        extra = {"addons/demo_module/data/currency.xml": COMPANY_CURRENCY_XML}
        declarations = standard_declaration("demo.standard")
        declarations["company_currency_write_sites"] = {
            "reason": "every source that writes the company currency is named",
            "sites": [
                {
                    "file": "addons/demo_module/data/currency.xml",
                    "kind": "xml_record",
                    "site": "base.other_company",
                    "reason": "stale identifier",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), STANDARD_MODEL, declarations, extra_files=extra)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("no longer matches source" in f for f in report["failures"]),
                report["failures"],
            )

    def test_company_currency_write_site_without_reason_fails(self) -> None:
        extra = {"addons/demo_module/data/currency.xml": COMPANY_CURRENCY_XML}
        declarations = standard_declaration("demo.standard")
        declarations["company_currency_write_sites"] = {
            "models": [],
            "sites": [
                {
                    "file": "addons/demo_module/data/currency.xml",
                    "kind": "xml_record",
                    "site": "base.main_company",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), STANDARD_MODEL, declarations, extra_files=extra)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("company-currency write site without a reason" in f for f in report["failures"]),
                report["failures"],
            )

    def test_company_currency_authority_required_with_standard_currency(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = {
                "standard_currency": {
                    "currency": "CNY",
                    "models": [{"model": "demo.standard", "reason": "tenant standard currency document"}],
                }
            }
            report = run(Path(raw), STANDARD_MODEL, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("company-currency authority is not registered" in f for f in report["failures"]),
                report["failures"],
            )

    def test_company_currency_authority_missing_method_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = standard_declaration("demo.standard")
            declarations["company_currency_authority"] = authority_declaration(method="_absent_pin")
            report = run(Path(raw), STANDARD_MODEL, declarations)
            self.assertEqual("failed", report["status"])
            self.assertTrue(
                any("is not defined in" in f for f in report["failures"]), report["failures"]
            )

    def test_no_currency_field_is_not_a_gap(self) -> None:
        source = '''
class DemoNoMoney(models.Model):
    _name = "demo.nomoney"
    company_id = fields.Many2one("res.company")
'''
        with tempfile.TemporaryDirectory() as raw:
            report = run(Path(raw), source, {"standard_currency": {"currency": "CNY", "models": []}})
            self.assertEqual([], report["failures"])
            self.assertEqual(0, report["currency_models"])


STATE_MACHINE = '''
class ScStateMachine:
    DEMO = "demo.lifecycle"

    DEMO_STATES = [
        ("draft", "草稿"),
        ("done", "完成"),
    ]
    DEMO_TRANSITIONS = {
        "draft": {"done"},
        "done": set(),
    }

    _REGISTRY = {
        DEMO: (DEMO_STATES, DEMO_TRANSITIONS),
    }
'''

ENFORCED_MODEL = '''
class DemoLifecycle(models.Model):
    _name = "demo.lifecycle"
    state = fields.Selection(ScStateMachine.selection(ScStateMachine.DEMO))

    def write(self, vals):
        if "state" in vals:
            ScStateMachine.assert_transition(self._name, self.state, vals["state"])
        return super().write(vals)
'''


def write_state_case(tmp: Path, source: str, declarations: dict, state_source: str = STATE_MACHINE):
    module = tmp / "addons/demo_module"
    (module / "models/support").mkdir(parents=True, exist_ok=True)
    (module / "models/definition.py").write_text(source, encoding="utf-8")
    (module / "models/support/state_machine.py").write_text(state_source, encoding="utf-8")
    sets = tmp / "config/tenant/module_sets.v1.json"
    sets.parent.mkdir(parents=True, exist_ok=True)
    sets.write_text(json.dumps({"product_modules": ["demo_module"]}), encoding="utf-8")
    declarations_path = tmp / "declarations.json"
    declarations_path.write_text(json.dumps(declarations), encoding="utf-8")
    pin_path = tmp / "pin.py"
    pin_path.write_text("MODELS = []\n", encoding="utf-8")
    return tmp, declarations_path, pin_path


def run_state(tmp: Path, source: str, declarations: dict, state_source: str = STATE_MACHINE):
    root, declarations_path, pin_path = write_state_case(tmp, source, declarations, state_source)
    return guard.check(root, declarations_path, "config/tenant/module_sets.v1.json", pin_path)


def state_declaration(**overrides) -> dict:
    declaration = {
        "state_fact": {
            "issue": "STATE-FACT-SINGLE-SOURCE-01",
            "owner_module": "demo_module",
            "reason": "the declared lifecycle is the one fact every writer obeys",
            "enforcements": [
                {
                    "model": "demo.lifecycle",
                    "file": "addons/demo_module/models/definition.py",
                    "token": "ScStateMachine.assert_transition",
                    "enforced": True,
                }
            ],
            "transition_tables": [],
            "selection_stage_references": [],
            "bypass_sites": [],
        }
    }
    declaration["state_fact"].update(overrides)
    return declaration


class StateFactGuardTest(unittest.TestCase):
    def test_enforced_registered_model_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run_state(Path(raw), ENFORCED_MODEL, state_declaration())
            self.assertEqual([], report["failures"], report["failures"])
            self.assertEqual(
                ["demo.lifecycle"], report["state_fact"]["enforced_models"]
            )

    def test_registered_model_without_a_declared_enforcement_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = state_declaration(enforcements=[])
            report = run_state(Path(raw), ENFORCED_MODEL, declarations)
            self.assertTrue(
                any(
                    "demo.lifecycle is registered but has no declared enforcement" in f
                    for f in report["failures"]
                ),
                report["failures"],
            )

    def test_enforcement_token_must_exist_in_the_declared_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = state_declaration(
                enforcements=[
                    {
                        "model": "demo.lifecycle",
                        "file": "addons/demo_module/models/definition.py",
                        "token": "_validate_lifecycle_transition",
                        "enforced": True,
                    }
                ]
            )
            report = run_state(Path(raw), ENFORCED_MODEL, declarations)
            self.assertTrue(
                any("enforcement token" in f and "is absent from" in f for f in report["failures"]),
                report["failures"],
            )

    def test_unenforced_model_needs_a_reason_and_a_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = state_declaration(
                enforcements=[{"model": "demo.lifecycle", "enforced": False}]
            )
            report = run_state(Path(raw), ENFORCED_MODEL, declarations)
            self.assertTrue(
                any("demo.lifecycle is unenforced without a reason" in f for f in report["failures"]),
                report["failures"],
            )
            self.assertTrue(
                any("demo.lifecycle is unenforced without a next step" in f for f in report["failures"]),
                report["failures"],
            )

    def test_second_transition_table_must_be_declared(self) -> None:
        source = ENFORCED_MODEL + '''

class DemoLifecycleCopy(models.Model):
    _inherit = "demo.lifecycle"
    _LIFECYCLE_TRANSITIONS = {"draft": {"done"}}
'''
        with tempfile.TemporaryDirectory() as raw:
            report = run_state(Path(raw), source, state_declaration())
            self.assertTrue(
                any("declares a second transition table _LIFECYCLE_TRANSITIONS" in f for f in report["failures"]),
                report["failures"],
            )
            declared = state_declaration(
                transition_tables=[
                    {
                        "file": "addons/demo_module/models/definition.py",
                        "name": "_LIFECYCLE_TRANSITIONS",
                        "reason": "the test copy is declared, so it is a decision",
                    }
                ]
            )
            report = run_state(Path(raw), source, declared)
            self.assertEqual([], report["failures"], report["failures"])

    def test_borrowed_lifecycle_selection_must_be_declared(self) -> None:
        source = ENFORCED_MODEL + '''

class DemoStage(models.Model):
    _name = "demo.stage"
    lifecycle_state = fields.Selection(ScStateMachine.selection(ScStateMachine.DEMO))
'''
        with tempfile.TemporaryDirectory() as raw:
            report = run_state(Path(raw), source, state_declaration())
            self.assertTrue(
                any("demo.stage borrows the DEMO lifecycle selection undeclared" in f for f in report["failures"]),
                report["failures"],
            )
            declared = state_declaration(
                selection_stage_references=[
                    {"model": "demo.stage", "key": "DEMO", "reason": "a stage reference, not a status"}
                ]
            )
            report = run_state(Path(raw), source, declared)
            self.assertEqual([], report["failures"], report["failures"])

    def test_bypass_site_must_be_declared(self) -> None:
        source = '''
class DemoLifecycle(models.Model):
    _name = "demo.lifecycle"
    state = fields.Selection(ScStateMachine.selection(ScStateMachine.DEMO))

    def action_done(self):
        return self.with_context(allow_transition=True).write({"state": "done"})

    def write(self, vals):
        if "state" in vals:
            ScStateMachine.assert_transition(self._name, self.state, vals["state"])
        return super().write(vals)
'''
        with tempfile.TemporaryDirectory() as raw:
            report = run_state(Path(raw), source, state_declaration())
            self.assertTrue(
                any(
                    "bypasses the declared table in action_done undeclared" in f
                    for f in report["failures"]
                ),
                report["failures"],
            )
            declared = state_declaration(
                bypass_sites=[
                    {
                        "file": "addons/demo_module/models/definition.py",
                        "method": "action_done",
                        "reason": "the method writes the target under an explicit bypass",
                    }
                ]
            )
            report = run_state(Path(raw), source, declared)
            self.assertEqual([], report["failures"], report["failures"])

    def test_disappeared_declaration_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = state_declaration(
                transition_tables=[
                    {"file": "addons/demo_module/models/definition.py", "name": "_GONE_TRANSITIONS"}
                ]
            )
            report = run_state(Path(raw), ENFORCED_MODEL, declarations)
            self.assertTrue(
                any("declared transition table" in f and "is gone" in f for f in report["failures"]),
                report["failures"],
            )


NUMBER_MODEL = '''
class DemoDoc(models.Model):
    _name = "demo.doc"

    def create(self, vals_list):
        for vals in vals_list:
            vals["name"] = self.env["ir.sequence"].next_by_code("demo.doc.no") or _("Demo")
        return super().create(vals_list)
'''

NUMBER_LABEL_FALLBACK_MODEL = '''
class DemoDoc(models.Model):
    _name = "demo.doc"

    def action_submit(self):
        self.ensure_one()
        if self.name == "新建":
            self.name = self.env["ir.sequence"].next_by_code("demo.doc.no") or self.name
'''

NUMBER_DYNAMIC_MODEL = '''
class DemoDoc(models.Model):
    _name = "demo.doc"

    def create(self, vals_list):
        for vals in vals_list:
            vals["name"] = self.env["ir.sequence"].next_by_code(seq_code) or _("Demo")
        return super().create(vals_list)
'''

NUMBER_SEQUENCE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="seq_demo_doc" model="ir.sequence">
        <field name="code">demo.doc.no</field>
    </record>
</odoo>
"""

NUMBER_READER = "addons/demo_module/models/definition.py"


def number_declaration(**overrides) -> dict:
    declaration = {
        "business_number_authority": {
            "issue": "BUSINESS-NUMBER-AUTHORITY-01",
            "owner_module": "demo_module",
            "reason": "one published ir.sequence is the single generator of the demo document number",
            "reader_files": [{"file": NUMBER_READER, "codes": ["demo.doc.no"]}],
            "codes": [],
            "dynamic_reads": [],
            "second_value_sites": [],
        }
    }
    declaration["business_number_authority"].update(overrides)
    return declaration


def run_number(tmp: Path, source: str, declarations: dict, sequence_xml: str = NUMBER_SEQUENCE_XML, extra_files: dict | None = None):
    files = {"addons/demo_module/data/sequence.xml": sequence_xml}
    files.update(extra_files or {})
    return run(tmp, source, declarations, extra_files=files)


class BusinessNumberAuthorityGuardTest(unittest.TestCase):
    def test_registered_reader_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run_number(Path(raw), NUMBER_MODEL, number_declaration())
            self.assertEqual([], report["failures"], report["failures"])
            self.assertEqual(1, report["business_number_authority"]["reader_files"])
            self.assertEqual(1, report["business_number_authority"]["codes"])

    def test_undeclared_authority_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run_number(Path(raw), NUMBER_MODEL, {})
            self.assertTrue(
                any("business_number_authority is not declared" in f for f in report["failures"]),
                report["failures"],
            )

    def test_unregistered_reader_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run_number(Path(raw), NUMBER_MODEL, number_declaration(reader_files=[]))
            self.assertTrue(
                any("without naming it in" in f for f in report["failures"]),
                report["failures"],
            )

    def test_reader_code_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = number_declaration(
                reader_files=[{"file": NUMBER_READER, "codes": ["demo.doc.other"]}]
            )
            report = run_number(Path(raw), NUMBER_MODEL, declarations)
            self.assertTrue(
                any("business-number codes changed to" in f for f in report["failures"]),
                report["failures"],
            )

    def test_unread_published_rule_needs_registration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            xml = NUMBER_SEQUENCE_XML.replace(
                "</odoo>",
                '    <record id="seq_orphan" model="ir.sequence">\n'
                '        <field name="code">demo.orphan.no</field>\n'
                "    </record>\n</odoo>",
            )
            report = run_number(Path(raw), NUMBER_MODEL, number_declaration(), sequence_xml=xml)
            self.assertTrue(
                any("publishes this business-number rule but no" in f for f in report["failures"]),
                report["failures"],
            )

    def test_unread_published_rule_registered_with_reason_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            xml = NUMBER_SEQUENCE_XML.replace(
                "</odoo>",
                '    <record id="seq_orphan" model="ir.sequence">\n'
                '        <field name="code">demo.orphan.no</field>\n'
                "    </record>\n</odoo>",
            )
            declarations = number_declaration(
                codes=[{"code": "demo.orphan.no", "reason": "kept until a demo document consumer lands"}]
            )
            report = run_number(Path(raw), NUMBER_MODEL, declarations, sequence_xml=xml)
            self.assertEqual([], report["failures"], report["failures"])

    def test_unpublished_read_code_registered_with_reason_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            xml = NUMBER_SEQUENCE_XML.replace("demo.doc.no", "demo.other.no")
            declarations = number_declaration(
                codes=[
                    {"code": "demo.doc.no", "reason": "the demo read has no publication yet"},
                    {"code": "demo.other.no", "reason": "published while no demo code reads it"},
                ]
            )
            report = run_number(Path(raw), NUMBER_MODEL, declarations, sequence_xml=xml)
            self.assertEqual([], report["failures"], report["failures"])
            self.assertEqual(
                ["demo.doc.no"], report["business_number_authority"]["unpublished_codes"]
            )

    def test_exception_without_a_reason_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            xml = NUMBER_SEQUENCE_XML.replace("demo.doc.no", "demo.other.no")
            declarations = number_declaration(codes=[{"code": "demo.doc.no"}])
            report = run_number(Path(raw), NUMBER_MODEL, declarations, sequence_xml=xml)
            self.assertTrue(
                any("business-number exception without a reason" in f for f in report["failures"]),
                report["failures"],
            )

    def test_normal_code_registered_as_an_exception_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = number_declaration(
                codes=[{"code": "demo.doc.no", "reason": "should not be needed"}]
            )
            report = run_number(Path(raw), NUMBER_MODEL, declarations)
            self.assertTrue(
                any("source has no publication/read mismatch" in f for f in report["failures"]),
                report["failures"],
            )

    def test_second_value_site_needs_registration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run_number(Path(raw), NUMBER_LABEL_FALLBACK_MODEL, number_declaration())
            self.assertTrue(
                any("fall back to a second fact" in f for f in report["failures"]),
                report["failures"],
            )

    def test_benign_second_value_class_passes_without_an_issue(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = number_declaration(
                second_value_sites=[
                    {
                        "file": NUMBER_READER,
                        "function": "action_submit",
                        "class": "name_label_fallback",
                        "reason": "the name field falls back to its own declared label",
                    }
                ]
            )
            report = run_number(Path(raw), NUMBER_LABEL_FALLBACK_MODEL, declarations)
            self.assertEqual([], report["failures"], report["failures"])

    def test_registered_second_value_class_needs_the_owning_issue(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = number_declaration(
                second_value_sites=[
                    {
                        "file": NUMBER_READER,
                        "function": "create",
                        "class": "unique_key_second_generator",
                        "reason": "the document key falls back to a generated token",
                    }
                ]
            )
            source = NUMBER_MODEL.replace('vals["name"]', 'vals["document_no"]').replace(
                '_("Demo")', 'self.id'
            )
            report = run_number(Path(raw), source, declarations)
            self.assertTrue(
                any("still needs the owning issue" in f for f in report["failures"]),
                report["failures"],
            )

    def test_dynamic_read_needs_registration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = run_number(
                Path(raw),
                NUMBER_DYNAMIC_MODEL,
                number_declaration(
                    reader_files=[],
                    codes=[{"code": "demo.doc.no", "reason": "resolved through the dynamic read"}],
                ),
            )
            self.assertTrue(
                any("non-literal code" in f for f in report["failures"]),
                report["failures"],
            )

    def test_registered_dynamic_read_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = number_declaration(
                reader_files=[],
                codes=[{"code": "demo.doc.no", "reason": "resolved only through the dynamic read"}],
                dynamic_reads=[
                    {
                        "file": NUMBER_READER,
                        "function": "create",
                        "argument": "seq_code",
                        "reason": "the demo document resolves its sequence code at runtime",
                    }
                ],
            )
            report = run_number(Path(raw), NUMBER_DYNAMIC_MODEL, declarations)
            self.assertEqual([], report["failures"], report["failures"])

    def test_registered_fallback_site_no_longer_in_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            declarations = number_declaration(
                second_value_sites=[
                    {
                        "file": NUMBER_READER,
                        "function": "action_submit",
                        "class": "name_label_fallback",
                        "reason": "the name field falls back to its own declared label",
                    }
                ]
            )
            report = run_number(Path(raw), NUMBER_MODEL, declarations)
            self.assertTrue(
                any("fallback site no longer" in f for f in report["failures"]),
                report["failures"],
            )


if __name__ == "__main__":
    unittest.main()

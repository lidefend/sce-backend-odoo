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


def write_case(tmp: Path, source: str, declarations: dict, pin: str = "MODELS = []\n"):
    module = tmp / "addons/demo_module"
    (module / "models").mkdir(parents=True, exist_ok=True)
    (module / "models/definition.py").write_text(source, encoding="utf-8")
    (module / "models/company_currency_pin.py").write_text(
        "def _ensure_standard_currency(self):\n"
        '    return "base.CNY"\n',
        encoding="utf-8",
    )
    sets = tmp / "config/tenant/module_sets.v1.json"
    sets.parent.mkdir(parents=True, exist_ok=True)
    sets.write_text(json.dumps({"product_modules": ["demo_module"]}), encoding="utf-8")
    declarations_path = tmp / "declarations.json"
    declarations_path.write_text(json.dumps(declarations), encoding="utf-8")
    pin_path = tmp / "pin.py"
    pin_path.write_text(pin, encoding="utf-8")
    return tmp, declarations_path, pin_path


def run(tmp: Path, source: str, declarations: dict, pin: str = "MODELS = []\n"):
    root, declarations_path, pin_path = write_case(tmp, source, declarations, pin)
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
            }
            report = run(Path(raw), EXTENSION_OVERRIDE_MODEL, declarations)
            self.assertEqual([], report["failures"])

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


if __name__ == "__main__":
    unittest.main()

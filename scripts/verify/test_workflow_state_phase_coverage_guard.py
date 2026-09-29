#!/usr/bin/env python3
"""Tests for the workflow state_phase coverage guard."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import workflow_contract_profile_loader as profile_loader  # noqa: E402
import workflow_state_phase_coverage_guard as guard  # noqa: E402

REAL_REGISTRY = guard.REGISTRY

SAMPLE_MODELS = '''
from odoo import _, fields, models

from .state_machine import ScStateMachine


class DemoPlain(models.Model):
    _name = "demo.plain"
    _inherit = ["mail.thread"]

    state = fields.Selection(
        [("draft", _("草稿")), ("running", _("执行中")), ("cancel", _("已取消"))],
        string="状态",
        default="draft",
    )


class DemoMixin(models.AbstractModel):
    _name = "demo.mixin"

    state = fields.Selection(
        [("draft", _("草稿")), ("done", _("完成"))],
        string="状态",
    )


class DemoMixinUser(models.Model):
    _name = "demo.mixin.user"
    _inherit = ["demo.mixin", "mail.thread"]


class DemoBase(models.Model):
    _name = "demo.base"

    state = fields.Selection(
        ScStateMachine.selection(ScStateMachine.DEMO),
        string="状态",
        default="draft",
    )


class DemoDelegate(models.Model):
    _name = "demo.delegate"
    _inherits = {"demo.base": "base_id"}


class DemoExtension(models.Model):
    _inherit = "demo.plain"

    note = fields.Char(string="备注")
'''

SAMPLE_STATE_MACHINE = '''
from odoo import _


class ScStateMachine:
    DEMO = "demo.base"

    DEMO_STATES = [
        ("alpha", _("甲")),
        ("beta", _("乙")),
    ]
'''


class GuardCase(unittest.TestCase):
    """Base case that redirects the guard at a self-contained addon tree."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        models = root / "addons" / "demo" / "models"
        models.mkdir(parents=True)
        (models / "sample.py").write_text(SAMPLE_MODELS, encoding="utf-8")
        (models / "state_machine.py").write_text(SAMPLE_STATE_MACHINE, encoding="utf-8")
        self._root = guard.ROOT
        self._machine = guard.STATE_MACHINE
        guard.ROOT = root
        guard.STATE_MACHINE = models / "state_machine.py"
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        guard.ROOT = self._root
        guard.STATE_MACHINE = self._machine
        self._tmp.cleanup()

    def resolve(self, model: str) -> set[str]:
        return guard._resolve_state_keys(model, guard._model_index(), guard._state_machine_states())

    def scan(self, profiles):
        return guard.scan(profiles)


class ResolverTests(GuardCase):
    def test_literal_selection_is_resolved(self) -> None:
        self.assertEqual(self.resolve("demo.plain"), {"draft", "running", "cancel"})

    def test_state_machine_selection_is_resolved(self) -> None:
        self.assertEqual(self.resolve("demo.base"), {"alpha", "beta"})

    def test_delegating_model_follows_the_delegate_base(self) -> None:
        self.assertEqual(self.resolve("demo.delegate"), {"alpha", "beta"})

    def test_mixin_provider_does_not_absorb_its_users(self) -> None:
        # A model with its own ``_name`` only *uses* the mixin.  Counting it as an
        # extension used to union every user's selection into the mixin's set.
        self.assertEqual(self.resolve("demo.mixin"), {"draft", "done"})
        self.assertEqual(self.resolve("demo.mixin.user"), {"draft", "done"})

    def test_in_place_extension_is_followed(self) -> None:
        self.assertEqual(self.resolve("demo.plain"), {"draft", "running", "cancel"})

    def test_unknown_model_resolves_to_nothing(self) -> None:
        self.assertEqual(self.resolve("demo.absent"), set())


class ValidateTests(GuardCase):
    def test_missing_phase_is_reported(self) -> None:
        profiles = {
            "demo.plain": {
                "state_field": "state",
                "state_phase": {"draft": "draft", "cancel": "cancelled"},
                "state_actions": {"draft": []},
            }
        }
        errors, dead, scanned = self.scan(profiles)
        self.assertEqual(scanned, 1)
        self.assertTrue(any("'running'" in error for error in errors), errors)
        self.assertEqual(dead, {})

    def test_unresolvable_model_is_reported_not_skipped(self) -> None:
        profiles = {"demo.absent": {"state_field": "state", "state_phase": {"draft": "draft"}}}
        errors, _, scanned = self.scan(profiles)
        self.assertEqual(scanned, 1)
        self.assertTrue(any("refuses to skip" in error for error in errors), errors)

    def test_guard_refuses_a_vacuous_scan(self) -> None:
        self.assertTrue(guard.validate({"entries": []}, {}))

    def test_dead_entry_must_be_registered(self) -> None:
        profiles = {
            "demo.plain": {
                "state_field": "state",
                "state_phase": {"draft": "draft", "running": "open", "cancel": "cancelled", "ghost": "draft"},
                "state_actions": {"draft": [], "ghost": []},
            }
        }
        errors = guard.validate({"entries": []}, profiles)
        self.assertTrue(any("dead profile" in error for error in errors), errors)

    def test_registered_dead_entry_is_accepted(self) -> None:
        profiles = {
            "demo.plain": {
                "state_field": "state",
                "state_phase": {"draft": "draft", "running": "open", "cancel": "cancelled", "ghost": "draft"},
                "state_actions": {"draft": [], "ghost": []},
            }
        }
        payload = {
            "entries": [
                {
                    "model": "demo.plain",
                    "keys": ["actions:ghost", "phase:ghost"],
                    "reason": "template alias the model cannot produce",
                }
            ]
        }
        self.assertEqual(guard.validate(payload, profiles), [])

    def test_stale_registration_fails(self) -> None:
        profiles = {
            "demo.plain": {
                "state_field": "state",
                "state_phase": {"draft": "draft", "running": "open", "cancel": "cancelled"},
                "state_actions": {"draft": []},
            }
        }
        payload = {"entries": [{"model": "demo.plain", "keys": ["phase:ghost"], "reason": "x"}]}
        errors = guard.validate(payload, profiles)
        self.assertTrue(any("stale entry" in error for error in errors), errors)

    def test_key_mismatch_fails(self) -> None:
        profiles = {
            "demo.plain": {
                "state_field": "state",
                "state_phase": {"draft": "draft", "running": "open", "cancel": "cancelled", "ghost": "draft"},
                "state_actions": {"ghost": []},
            }
        }
        payload = {"entries": [{"model": "demo.plain", "keys": ["phase:ghost"], "reason": "x"}]}
        errors = guard.validate(payload, profiles)
        self.assertTrue(any("do not match the computed ones" in error for error in errors), errors)

    def test_registration_without_reason_fails(self) -> None:
        profiles = {
            "demo.plain": {
                "state_field": "state",
                "state_phase": {"draft": "draft", "running": "open", "cancel": "cancelled", "ghost": "draft"},
                "state_actions": {"ghost": []},
            }
        }
        payload = {"entries": [{"model": "demo.plain", "keys": ["actions:ghost", "phase:ghost"]}]}
        errors = guard.validate(payload, profiles)
        self.assertTrue(any("without a reason" in error for error in errors), errors)


class RealRegistryTests(unittest.TestCase):
    """The repository's own registry must satisfy the guard as committed."""

    def test_every_adopted_model_is_scanned_and_covered(self) -> None:
        profiles = profile_loader.load_profiles()
        self.assertTrue(profiles)
        payload = json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))
        errors, dead, scanned = guard.scan(profiles)
        self.assertEqual(scanned, len(profiles))
        self.assertEqual(errors, [])
        self.assertEqual(guard.validate(payload, profiles), [])
        self.assertEqual(set(dead), {entry["model"] for entry in payload["entries"]})

    def test_the_delegating_profiles_follow_their_base(self) -> None:
        index = guard._model_index()
        machine = guard._state_machine_states()
        base = guard._resolve_state_keys("construction.contract", index, machine)
        self.assertIn("running", base)
        self.assertEqual(guard._resolve_state_keys("construction.contract.expense", index, machine), base)
        self.assertEqual(guard._resolve_state_keys("construction.contract.income", index, machine), base)


if __name__ == "__main__":
    unittest.main(verbosity=2)

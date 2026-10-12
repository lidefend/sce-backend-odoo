#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Falsification test for the contract-v2 entry-equivalence guard.

The guard reads shipped carriers (a TypeScript contract client, the backend
entry branch, the permission resolver and the capability rule), so the only way
to know it still proves anything is to break one fact at a time and assert that
it reports that exact break.  The first case leaves every carrier intact, so the
baseline is proven good before any injected defect is trusted.
"""
from __future__ import annotations

import unittest

import contract_v2_entry_equivalence_guard as guard

CLIENT = guard.CLIENT_TS
HANDLER = guard.HANDLER_PY
ASSEMBLER = guard.ASSEMBLER_PY
PERMISSIONS = guard.PERMISSIONS_PY
CAPABILITY = guard.CAPABILITY_PY


class ContractV2EntryEquivalenceGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = CLIENT.read_text(encoding="utf-8")
        cls.handler = HANDLER.read_text(encoding="utf-8")
        cls.assembler = ASSEMBLER.read_text(encoding="utf-8")
        cls.permissions = PERMISSIONS.read_text(encoding="utf-8")
        cls.capability = CAPABILITY.read_text(encoding="utf-8")

    def probe(self, **overrides):
        return guard.probe(**overrides)

    def mutate(self, source: str, old: str, new: str) -> str:
        self.assertIn(old, source)
        mutated = source.replace(old, new, 1)
        self.assertNotEqual(mutated, source)
        return mutated

    def assert_reports(self, errors, fragment: str):
        self.assertTrue(any(fragment in error for error in errors), errors)

    # --- baseline ---
    def test_shipped_carriers_project_one_business_fact(self):
        self.assertEqual([], self.probe())

    # --- frontend: one fetch authority, one decode authority ---
    def test_a_second_decode_authority_is_rejected(self):
        mutated = self.mutate(
            self.client,
            "  const snapshot = decodeContractV2Snapshot(response.data);",
            "  const snapshot = decodeContractV2Snapshot(response.data);\n  decodeContractV2Snapshot(response.data);",
        )
        self.assert_reports(self.probe(client_ts=mutated), "exactly one decode authority")

    def test_a_loader_owning_its_own_fetch_path_is_rejected(self):
        mutated = self.mutate(
            self.client,
            "  const cacheable = renderProfile === 'create'",
            "  await intentRequestRaw<ContractV2Dictionary>({ intent: 'ui.contract.v2', params });\n"
            "  const cacheable = renderProfile === 'create'",
        )
        errors = self.probe(client_ts=mutated)
        self.assert_reports(errors, "must not own a private intentRequestRaw path")

    # --- backend: one entry branch, one dispatcher, both entry kinds mapped ---
    def test_dropping_the_model_entry_mapping_is_rejected(self):
        mutated = self.mutate(
            self.handler,
            '            direct_params["subject"] = "model"',
            '            direct_params["subject"] = "action"',
        )
        self.assert_reports(self.probe(handler_py=mutated), "must map both entry kinds")

    def test_a_second_dispatcher_is_rejected(self):
        mutated = self.mutate(
            self.handler,
            "        result = ActionDispatcher(env, su_env).dispatch(direct_params)",
            "        result = ActionDispatcher(env, su_env).dispatch(direct_params)\n"
            "        second = ActionDispatcher(env, su_env).dispatch(direct_params)",
        )
        errors = self.probe(handler_py=mutated)
        self.assert_reports(errors, "exactly one ActionDispatcher")
        self.assert_reports(errors, "must dispatch exactly once")

    # --- permission facts must not be able to see the entry ---
    def test_an_entry_argument_on_the_permission_resolver_is_rejected(self):
        mutated = self.mutate(
            self.assembler,
            "def _ui_contract_permission_rights(source: dict[str, Any], ui: dict[str, Any]) -> dict[str, Any]:",
            "def _ui_contract_permission_rights(\n"
            "    source: dict[str, Any], ui: dict[str, Any], op: str = \"\"\n"
            ") -> dict[str, Any]:",
        )
        self.assert_reports(self.probe(assembler_py=mutated), "must take only the contract payload")

    def test_consulting_entry_identity_in_the_resolver_is_rejected(self):
        mutated = self.mutate(
            self.permissions,
            "    root = _dict(permission_contract)",
            "    root = _dict(permission_contract)\n"
            "    entry_kind = str(permission_contract.get('op') or '') if isinstance(permission_contract, dict) else ''\n"
            "    del entry_kind",
        )
        self.assert_reports(self.probe(permissions_py=mutated), "must not consult entry identity")

    # --- the capability rule takes facts only ---
    def test_a_model_parameter_on_the_capability_rule_is_rejected(self):
        mutated = self.mutate(
            self.capability,
            "    selection_actions: Iterable[str],",
            '    model: str = "",\n    selection_actions: Iterable[str],',
        )
        self.assert_reports(self.probe(capability_py=mutated), "must take only facts")

    # --- the behavioural claim itself must be falsifiable ---
    def test_a_carrier_dependent_resolution_is_rejected(self):
        def carrier_dependent(contract):
            if isinstance(contract, dict) and isinstance(contract.get("effective"), dict):
                return {"read": True}
            return dict(guard.CARRIER_RIGHTS)

        errors = self.probe(resolve_rights=carrier_dependent, build_caps=lambda **_: {})
        self.assert_reports(errors, f"{guard.PERMISSION_RESOLVER} must resolve the same rights from carrier")

    def test_promoting_a_non_boolean_right_is_rejected(self):
        def lax(contract):
            root = contract if isinstance(contract, dict) else {}
            effective = root.get("effective") if isinstance(root.get("effective"), dict) else {}
            rights = effective.get("rights") or effective or root.get("rights") or root
            return dict(rights) if isinstance(rights, dict) else {}

        errors = self.probe(resolve_rights=lax, build_caps=lambda **_: {})
        self.assert_reports(errors, "must not promote a non-boolean right")


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/verify/frontend_contract_basis_guard.py"
SPEC = importlib.util.spec_from_file_location("frontend_contract_basis_guard", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FrontendContractBasisGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = MODULE.load_ledger()

    def test_repository_ledger_passes(self) -> None:
        self.assertEqual(MODULE.check(self.ledger), [])

    def test_missing_declaration_site_fails_closed(self) -> None:
        broken = copy.deepcopy(self.ledger)
        broken["declarationBindings"][0]["declaredSymbol"] = "not_published_anywhere"
        errors = MODULE.check(broken)
        self.assertTrue(any("declaration site" in error for error in errors), errors)

    def test_binding_without_stop_behaviour_fails_closed(self) -> None:
        broken = copy.deepcopy(self.ledger)
        broken["declarationBindings"][0]["onMissing"] = "frontend_default"
        errors = MODULE.check(broken)
        self.assertTrue(any("fail closed" in error for error in errors), errors)

    def test_mechanism_exemption_cannot_carry_product_semantics(self) -> None:
        broken = copy.deepcopy(self.ledger)
        broken["registeredMechanismExemptions"][0]["carriesProductSemantics"] = True
        errors = MODULE.check(broken)
        self.assertTrue(any("product semantics" in error for error in errors), errors)

    def test_open_contract_defect_requires_owner_and_closure(self) -> None:
        broken = copy.deepcopy(self.ledger)
        broken["openContractDefects"] = [{"id": "CD-TEST"}]
        errors = MODULE.check(broken)
        self.assertGreaterEqual(len(errors), 3, errors)

    def test_unknown_regression_guard_is_rejected(self) -> None:
        broken = copy.deepcopy(self.ledger)
        broken["declarationBindings"][0]["regressionGuard"] = "verify.not.a.real.target"
        errors = MODULE.check(broken)
        self.assertTrue(any("not a registered make target" in error for error in errors), errors)

    def test_enforce_stops_while_open_defect_exists(self) -> None:
        # 机制：出现前端判断即停机，回契约要结果 —— 交付车道禁止带未闭合缺陷放行。
        # 用合成台账锁定机制本身，不依赖仓库台账当时的缺陷数量。
        with_defect = copy.deepcopy(self.ledger)
        with_defect["openContractDefects"] = [{
            "id": "CD-TEST-OPEN",
            "missing": "测试用未闭合声明缺口",
            "owner": "P0:test",
            "closureCondition": "由声明层补齐声明后删除本条目",
        }]
        with_defect["frontendLogicInventory"][0]["verdict"] = "contract_defect_open"
        with_defect["frontendLogicInventory"][0]["defectId"] = "CD-TEST-OPEN"
        reasons = MODULE.enforcement_stop_reasons(with_defect)
        self.assertTrue(reasons, "an open contract defect must stop the delivery lane")
        self.assertTrue(any("CD-TEST-OPEN" in r for r in reasons), reasons)

    def test_repository_ledger_has_no_open_defect(self) -> None:
        # 收口后仓库台账必须为零未闭合缺陷，否则交付冻结门会停机。
        self.assertEqual(MODULE.enforcement_stop_reasons(self.ledger), [])

    def test_enforce_clears_when_defects_closed(self) -> None:
        closed = copy.deepcopy(self.ledger)
        for entry in closed["frontendLogicInventory"]:
            if entry.get("verdict") == "contract_defect_open":
                entry["verdict"] = "contract_declared_consumption"
                entry.pop("defectId", None)
        closed["openContractDefects"] = []
        self.assertEqual(MODULE.enforcement_stop_reasons(closed), [])
        self.assertEqual(MODULE.check(closed), [])

    def test_mechanism_is_declared_and_wired(self) -> None:
        # 机制：出现前端判断即停机，回契约要结果。锁定声明（台账）与实际接线（make/冻结门）。
        mech = self.ledger.get("mechanism", {})
        self.assertEqual(mech.get("id"), "FRONTEND-JUDGEMENT-STOP")
        layers = {layer.get("layer") for layer in mech.get("enforcementLayers", [])}
        self.assertEqual(layers, {"runtime", "static", "delivery"}, layers)
        frontend_mk = (MODULE.ROOT / "make/frontend.mk").read_text(encoding="utf-8")
        self.assertIn("verify.frontend.contract_basis.enforce", frontend_mk)
        ci_mk = (MODULE.ROOT / "make/ci.mk").read_text(encoding="utf-8")
        freeze_line = next(
            line for line in ci_mk.splitlines() if line.startswith("ci.delivery.freeze.prepare:")
        )
        self.assertIn("verify.frontend.contract_basis.enforce", freeze_line)

    def test_ledger_is_valid_json_with_expected_schema(self) -> None:
        payload = json.loads(MODULE.LEDGER.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "frontend.contract-basis.ledger.v1")


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

from scripts.verify.baseline_readiness_verifier import (
    ManifestError,
    ObservationError,
    evaluate,
    load_manifest,
    validate_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "scripts/verify/baseline_readiness_manifest.json"


def _small_manifest() -> dict:
    return {
        "schema_version": 1,
        "id": "test.baseline.readiness",
        "owner_layer": "P4",
        "gates": [
            {
                "gate": "G0",
                "title": "tenant",
                "applicable": True,
                "requirements": [
                    {"key": "company", "kind": "hard", "authority": "res.company", "owner_layer": "P2", "repair_hint": "add company"},
                    {"key": "currency", "kind": "hard", "authority": "res.currency", "owner_layer": "P2", "repair_hint": "add currency"},
                ],
            },
            {
                "gate": "G1",
                "title": "org",
                "applicable": True,
                "requirements": [
                    {"key": "departments", "kind": "hard", "authority": "hr.department", "owner_layer": "P2", "repair_hint": "add departments"},
                    {"key": "approval_positions", "kind": "conditional", "authority": "sc.approval.policy", "owner_layer": "P1", "repair_hint": "add approval positions"},
                ],
            },
            {
                "gate": "GX",
                "title": "not applicable",
                "applicable": False,
                "requirements": [
                    {"key": "n_a_item", "kind": "conditional", "authority": "none", "owner_layer": "P4", "repair_hint": ""},
                ],
            },
        ],
    }


def _all_present() -> dict:
    return {"company": True, "currency": True, "departments": True, "approval_positions": True}


class BaselineReadinessVerifierTest(unittest.TestCase):
    def _gate(self, report: dict, gid: str) -> dict:
        for gate in report["gates"]:
            if gate["gate"] == gid:
                return gate
        self.fail(f"gate {gid} not found in report")

    def test_real_manifest_loads_and_declares_g0_g6(self):
        manifest = load_manifest(MANIFEST_PATH)
        self.assertEqual(manifest["id"], "demo.baseline.readiness")
        gate_ids = [g["gate"] for g in manifest["gates"]]
        for expected in ("G0", "G1", "G2", "G3", "G4", "G5", "G6"):
            self.assertIn(expected, gate_ids)

    def test_real_manifest_g0_g4_are_hard_baseline(self):
        manifest = load_manifest(MANIFEST_PATH)
        for gid in ("G0", "G1", "G2", "G3", "G4"):
            gate = next(g for g in manifest["gates"] if g["gate"] == gid)
            self.assertTrue(gate["applicable"])
            self.assertTrue(gate["requirements"], f"{gid} has no requirements")

    def test_evaluate_ready(self):
        report = evaluate(_small_manifest(), _all_present())
        self.assertEqual(report["overall_status"], "ready")
        self.assertEqual(self._gate(report, "G0")["status"], "ready")
        self.assertEqual(self._gate(report, "G0")["missing"], [])

    def test_evaluate_partial_on_conditional_missing(self):
        obs = {"company": True, "currency": True, "departments": True, "approval_positions": False}
        report = evaluate(_small_manifest(), obs)
        self.assertEqual(report["overall_status"], "partial")
        self.assertEqual(self._gate(report, "G1")["status"], "partial")
        self.assertEqual(self._gate(report, "G1")["missing"], ["approval_positions"])

    def test_evaluate_blocked_on_hard_missing(self):
        obs = {"company": False, "currency": True, "departments": True, "approval_positions": True}
        report = evaluate(_small_manifest(), obs)
        self.assertEqual(report["overall_status"], "blocked")
        self.assertEqual(self._gate(report, "G0")["status"], "blocked")
        self.assertEqual(self._gate(report, "G0")["missing"], ["company"])

    def test_not_applicable_gate(self):
        report = evaluate(_small_manifest(), _all_present())
        self.assertEqual(self._gate(report, "GX")["status"], "not_applicable")
        self.assertFalse(self._gate(report, "GX")["applicable"])

    def test_missing_observed_key_fails_closed(self):
        obs = {"company": True, "currency": True, "departments": True}
        with self.assertRaises(ObservationError):
            evaluate(_small_manifest(), obs)

    def test_undeclared_observation_key_fails_closed(self):
        obs = dict(_all_present(), ghost=True)
        with self.assertRaises(ObservationError):
            evaluate(_small_manifest(), obs)

    def test_non_boolean_observation_fails_closed(self):
        obs = dict(_all_present(), currency=1)
        with self.assertRaises(ObservationError):
            evaluate(_small_manifest(), obs)

    def test_duplicate_requirement_key_rejected(self):
        manifest = {
            "schema_version": 1,
            "id": "dup",
            "gates": [
                {
                    "gate": "G0",
                    "title": "t",
                    "requirements": [
                        {"key": "a", "kind": "hard", "authority": "x", "owner_layer": "P2", "repair_hint": ""},
                        {"key": "a", "kind": "hard", "authority": "x", "owner_layer": "P2", "repair_hint": ""},
                    ],
                }
            ],
        }
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_orm_probe_hard_keys_match_manifest(self):
        import ast
        import re

        manifest = load_manifest(MANIFEST_PATH)
        g0_g4_hard = sorted(
            req["key"]
            for gate in manifest["gates"]
            if gate["gate"] in ("G0", "G1", "G2", "G3", "G4")
            for req in gate["requirements"]
            if req["kind"] == "hard"
        )
        orm_test = (
            REPO_ROOT
            / "demo_addons/smart_construction_demo/tests/test_demo_baseline_readiness.py"
        )
        source = orm_test.read_text(encoding="utf-8")
        match = re.search(r"HARD_KEYS = frozenset\(\[(.*?)\]\)", source, re.S)
        self.assertIsNotNone(match, "HARD_KEYS block not found in ORM readiness test")
        body = match.group(1)
        lines = [line for line in body.splitlines() if not line.strip().startswith("#")]
        probe_keys = ast.literal_eval("[" + "\n".join(lines) + "]")
        self.assertEqual(sorted(probe_keys), g0_g4_hard)


if __name__ == "__main__":
    unittest.main()

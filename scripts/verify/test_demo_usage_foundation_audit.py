import unittest
from pathlib import Path

from scripts.verify.demo_usage_foundation_audit import (
    ManifestError,
    audit,
    load_manifest,
    validate_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "docs/demo/demo_usage_foundation_manifest_v1.json"


def _small_manifest() -> dict:
    return {
        "schema_version": 1,
        "id": "test.usage.foundation",
        "owner_layer": "P4",
        "authority": "test",
        "layers": {
            "U0": {
                "title": "identity",
                "owner_layers": ["P2"],
                "blocking_batch": "F2",
                "seedable": True,
            },
            "U1": {
                "title": "master",
                "owner_layers": ["P1"],
                "blocking_batch": "F3",
                "seedable": True,
            },
        },
        "user_actions": [
            {"key": "login", "title": "login", "layer": "U0", "blocking_batch": "F2"},
            {"key": "select", "title": "select", "layer": "U1", "blocking_batch": "F3"},
        ],
        "requirements": [
            {
                "key": "company",
                "layer": "U0",
                "user_action": "login",
                "prerequisite": "hard",
                "read_entry": "res.company",
                "scope": "company",
                "owner_layer": "P2",
                "repair_hint": "add company",
                "acceptance_method": "company non-empty",
                "gap_ref": None,
            },
            {
                "key": "partners",
                "layer": "U1",
                "user_action": "select",
                "prerequisite": "hard",
                "read_entry": "res.partner",
                "scope": "partners",
                "owner_layer": "P1",
                "repair_hint": "add partners",
                "acceptance_method": "partners selectable",
                "gap_ref": "GAP-1",
            },
        ],
        "gaps": [
            {
                "id": "GAP-1",
                "title": "partners gap",
                "owner_layer": "P4",
                "blocking_batches": ["F3"],
                "repair_hint": "fix partners",
                "status": "open",
            }
        ],
    }


class DemoUsageFoundationAuditTest(unittest.TestCase):
    def test_real_manifest_loads_and_is_structurally_valid(self):
        manifest = load_manifest(MANIFEST_PATH)
        self.assertEqual(manifest["id"], "demo.usage.foundation")
        self.assertEqual(manifest["owner_layer"], "P4")
        validate_manifest(manifest)

    def test_real_manifest_covers_all_declared_actions(self):
        manifest = load_manifest(MANIFEST_PATH)
        report = audit(manifest)
        self.assertTrue(report["coverage_complete"])
        self.assertEqual(report["summary"]["missing"], 0)
        declared = {a["key"] for a in manifest["user_actions"]}
        audited = {a["key"] for a in report["actions"]}
        self.assertEqual(declared, audited)

    def test_real_manifest_covers_layers_u0_to_u6(self):
        manifest = load_manifest(MANIFEST_PATH)
        layer_keys = set(manifest["layers"].keys())
        for layer in ("U0", "U1", "U2", "U3", "U4", "U5", "U6"):
            self.assertIn(layer, layer_keys)
        requirement_layers = {r["layer"] for r in manifest["requirements"]}
        for layer in ("U0", "U1", "U2", "U3", "U4", "U5", "U6"):
            self.assertIn(layer, requirement_layers, f"{layer} has no requirement")

    def test_real_manifest_reports_current_foundation_as_blocked(self):
        report = audit(load_manifest(MANIFEST_PATH))
        self.assertEqual(report["overall_status"], "blocked")
        self.assertGreater(report["summary"]["blocked"], 0)
        self.assertEqual(report["data_readback"], "not_run")

    def test_real_manifest_gaps_all_registered_with_owner_and_batch(self):
        manifest = load_manifest(MANIFEST_PATH)
        self.assertEqual([g["id"] for g in manifest["gaps"]], [
            "DUF-01",
            "DUF-02",
            "DUF-03",
            "DUF-04",
            "DUF-05",
        ])
        for gap in manifest["gaps"]:
            self.assertIn(gap["owner_layer"], ("P0", "P1", "P2", "P3", "P4"))
            self.assertTrue(gap["blocking_batches"])
            self.assertTrue(gap["repair_hint"])
            self.assertIn(gap["status"], ("open", "closed"))

    def test_real_manifest_batch_blockers_expose_cross_cutting_gaps(self):
        report = audit(load_manifest(MANIFEST_PATH))
        blockers = report["batch_blockers"]
        self.assertEqual(blockers["F1"], ["DUF-02"])
        self.assertEqual(blockers["F2"], ["DUF-03"])
        self.assertEqual(blockers["F3"], ["DUF-02", "DUF-04"])
        self.assertEqual(blockers["F5"], ["DUF-02"])
        self.assertEqual(blockers["F7"], ["DUF-01", "DUF-05"])
        self.assertEqual(blockers["F8"], ["DUF-03", "DUF-04"])
        self.assertNotIn("F4", blockers)
        self.assertNotIn("F6", blockers)

    def test_missing_action_is_reported(self):
        manifest = _small_manifest()
        manifest["requirements"] = [r for r in manifest["requirements"] if r["key"] != "partners"]
        report = audit(manifest)
        self.assertFalse(report["coverage_complete"])
        self.assertEqual(report["overall_status"], "missing")
        select = next(a for a in report["actions"] if a["key"] == "select")
        self.assertEqual(select["status"], "missing")
        self.assertEqual(select["requirement_keys"], [])

    def test_open_gap_blocks_action_and_requirement(self):
        report = audit(_small_manifest())
        select = next(a for a in report["actions"] if a["key"] == "select")
        self.assertEqual(select["status"], "blocked")
        self.assertEqual(select["open_gaps"], ["GAP-1"])
        partners = next(r for r in report["requirements"] if r["key"] == "partners")
        self.assertEqual(partners["status"], "blocked")
        company = next(r for r in report["requirements"] if r["key"] == "company")
        self.assertEqual(company["status"], "observed")

    def test_closed_gap_unblocks_action(self):
        manifest = _small_manifest()
        manifest["gaps"][0]["status"] = "closed"
        report = audit(manifest)
        select = next(a for a in report["actions"] if a["key"] == "select")
        self.assertEqual(select["status"], "observed")
        self.assertEqual(report["overall_status"], "ready")

    def test_illegal_prerequisite_rejected(self):
        manifest = _small_manifest()
        manifest["requirements"][0]["prerequisite"] = "maybe"
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_illegal_owner_layer_rejected(self):
        manifest = _small_manifest()
        manifest["requirements"][0]["owner_layer"] = "P9"
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_illegal_layer_reference_rejected(self):
        manifest = _small_manifest()
        manifest["requirements"][0]["layer"] = "U9"
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_illegal_action_reference_rejected(self):
        manifest = _small_manifest()
        manifest["requirements"][0]["user_action"] = "ghost"
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_illegal_gap_reference_rejected(self):
        manifest = _small_manifest()
        manifest["requirements"][0]["gap_ref"] = "GHOST"
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_duplicate_requirement_key_rejected(self):
        manifest = _small_manifest()
        manifest["requirements"].append(dict(manifest["requirements"][0]))
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_duplicate_gap_id_rejected(self):
        manifest = _small_manifest()
        manifest["gaps"].append(dict(manifest["gaps"][0]))
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)

    def test_duplicate_action_key_rejected(self):
        manifest = _small_manifest()
        manifest["user_actions"].append(dict(manifest["user_actions"][0]))
        with self.assertRaises(ManifestError):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()

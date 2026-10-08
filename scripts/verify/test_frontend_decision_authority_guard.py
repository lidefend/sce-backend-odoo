import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.verify import frontend_decision_authority as authority

ROOT = Path(__file__).resolve().parents[2]

WORKBENCH = "frontend/apps/web/src/views/WorkbenchView.vue"
LIST_PAGE = "frontend/apps/web/src/pages/ListPage.vue"
ANCHOR = "import { computed, h, onBeforeUnmount, onMounted, ref, useSlots, watch } from 'vue';"


def _real_read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _injecting_read_text(rel_path: str, needle: str, replacement: str):
    def read_text(path: str) -> str:
        value = _real_read_text(path)
        if path == rel_path:
            assert needle in value, f"injection anchor missing in {rel_path}: {needle!r}"
            return value.replace(needle, replacement, 1)
        return value

    return read_text


class FrontendDecisionAuthorityGuardTests(unittest.TestCase):
    def test_baseline_is_clean_and_non_trivial(self):
        """Negative-case precondition: the un-injected baseline must pass."""
        result = authority.reconcile()
        self.assertEqual([], result["failures"])
        summary = result["inventory"]["summary"]
        self.assertEqual(0, summary["unclassified"])
        self.assertGreater(summary["totalFindings"], 0)
        self.assertGreater(summary["contractDerived"], 0)
        self.assertEqual(0, summary["frontendLogicDefects"])

    def test_committed_ledger_matches_live_scan(self):
        result = authority.reconcile(compare_committed=True)
        self.assertEqual([], result["failures"])

    def test_new_business_state_decision_is_detected(self):
        read_text = _injecting_read_text(
            WORKBENCH, "state === 'disabled_capability'", "state === 'brand_new_business_state'"
        )
        result = authority.reconcile(read_text=read_text)
        self.assertTrue(
            any("unregistered decision" in item for item in result["failures"]),
            result["failures"],
        )
        self.assertTrue(
            any("brand_new_business_state" in item for item in result["failures"]),
            result["failures"],
        )

    def test_new_capability_literal_gate_is_detected(self):
        read_text = _injecting_read_text(
            LIST_PAGE,
            "import { computed, h, onBeforeUnmount, onMounted, ref, useSlots, watch } from 'vue';",
            "if (hasCapability('brand.new.capability')) { /* x */ }\nconst canCreate =",
        )
        result = authority.reconcile(read_text=read_text)
        self.assertTrue(
            any("R1_capability_literal_gate" in item for item in result["failures"]),
            result["failures"],
        )

    def test_new_intent_literal_is_detected(self):
        read_text = _injecting_read_text(
            LIST_PAGE,
            ANCHOR,
            "// injected: intent: 'brand.new.intent'\nconst injectedIntent = { intent: 'brand.new.intent' };\nexport",
        )
        result = authority.reconcile(read_text=read_text)
        self.assertTrue(
            any("brand.new.intent" in item for item in result["failures"]),
            result["failures"],
        )

    def test_new_action_id_literal_is_detected(self):
        read_text = _injecting_read_text(
            LIST_PAGE,
            ANCHOR,
            "const injected = { action_id: 'brand_new_action_id' };\nexport",
        )
        result = authority.reconcile(read_text=read_text)
        self.assertTrue(
            any("R5_action_id_literal" in item for item in result["failures"]),
            result["failures"],
        )

    def test_declared_ui_state_literal_is_not_a_failure(self):
        """The declared render/interaction class must keep UI states green."""
        read_text = _injecting_read_text(
            WORKBENCH,
            "state === 'disabled_capability'",
            "state === 'disabled_capability' || state === 'loading'",
        )
        result = authority.reconcile(read_text=read_text)
        self.assertEqual([], result["failures"])

    def test_contract_derived_intent_must_be_declared_in_catalog(self):
        catalog = json.loads((ROOT / "docs/contract/exports/intent_catalog.json").read_text("utf-8"))
        catalog["intents"] = [item for item in catalog["intents"] if item.get("intent") != "chatter.post"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_catalog = Path(tmp) / "intent_catalog.json"
            tmp_catalog.write_text(json.dumps(catalog), encoding="utf-8")
            with mock.patch.object(authority, "INTENT_CATALOG_PATH", tmp_catalog):
                result = authority.reconcile()
        self.assertTrue(
            any("chatter.post" in item for item in result["failures"]),
            result["failures"],
        )

    def test_missing_evidence_file_is_detected(self):
        patched = dict(authority.AUTHORITY)
        patched["R4_business_state_literal|brand_new_business_state"] = {
            "classification": "contract-derived",
            "evidence": "addons/does/not/exist.py:1",
        }
        read_text = _injecting_read_text(
            WORKBENCH, "state === 'disabled_capability'", "state === 'brand_new_business_state'"
        )
        with mock.patch.object(authority, "AUTHORITY", patched):
            result = authority.reconcile(read_text=read_text)
        self.assertTrue(
            any("missing evidence file" in item for item in result["failures"]),
            result["failures"],
        )

    def test_stale_committed_ledger_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "inventory.json"
            stale.write_text(json.dumps({"schemaVersion": 1}), encoding="utf-8")
            with mock.patch.object(authority, "INVENTORY_PATH", stale):
                result = authority.reconcile(compare_committed=True)
        self.assertTrue(
            any("out of sync" in item for item in result["failures"]),
            result["failures"],
        )

    def test_missing_committed_ledger_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "absent.json"
            with mock.patch.object(authority, "INVENTORY_PATH", missing):
                result = authority.reconcile(compare_committed=True)
        self.assertTrue(
            any("ledger is missing" in item for item in result["failures"]),
            result["failures"],
        )


if __name__ == "__main__":
    unittest.main()

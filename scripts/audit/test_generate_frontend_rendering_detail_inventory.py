#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import copy
import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/audit/generate_frontend_rendering_detail_inventory.py"
SPEC = importlib.util.spec_from_file_location("rendering_detail_inventory", MODULE_PATH)
assert SPEC and SPEC.loader
INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)


class FrontendRenderingDetailInventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = INVENTORY.build_inventory()
        cls.by_source = {item["source"]: item for item in cls.report["surfaces"]}

    def test_status_vocabulary_is_closed(self) -> None:
        self.assertEqual(set(self.report["statusVocabulary"]), INVENTORY.STATUS_VALUES)
        self.assertTrue(all(item["status"] in INVENTORY.STATUS_VALUES for item in self.report["surfaces"]))

    def test_unowned_relevant_surface_fails_closed_as_gap(self) -> None:
        status, _ = INVENTORY.classify("frontend/apps/web/src/components/UnknownSurface.vue", "loading <button>")
        self.assertEqual(status, "gap")

    def test_next_batch_sources_have_machine_proven_completion(self) -> None:
        self.assertGreaterEqual(len(INVENTORY.NEXT_BATCH_GAPS), 8)
        for source in INVENTORY.NEXT_BATCH_GAPS:
            self.assertIn(source, self.by_source)
            self.assertEqual(self.by_source[source]["status"], "governed_composite")
            self.assertEqual(self.by_source[source]["targetBatch"], "p0-inline-full-state-completion-v1")

    def test_collection_batch_sources_have_machine_proven_completion(self) -> None:
        batch = "p0-collection-state-control-completion-v1"
        sources = INVENTORY.BATCH_BINDINGS[batch]
        self.assertEqual(len(sources), 19)
        for source in sources:
            self.assertIn(source, self.by_source)
            self.assertEqual(self.by_source[source]["status"], "governed_composite")
            self.assertEqual(self.by_source[source]["targetBatch"], batch)

    def test_navigation_hierarchy_sources_have_machine_proven_completion(self) -> None:
        batch = "p0-navigation-hierarchy-composite-completion-v1"
        sources = INVENTORY.BATCH_BINDINGS[batch]
        self.assertEqual(len(sources), 10)
        for source in sources:
            self.assertEqual(self.by_source[source]["status"], "governed_composite")
            self.assertEqual(self.by_source[source]["targetBatch"], batch)

    def test_form_relation_workflow_sources_have_machine_proven_completion(self) -> None:
        batch = "p0-form-relation-workflow-completion-v1"
        sources = INVENTORY.BATCH_BINDINGS[batch]
        self.assertEqual(len(sources), 21)
        for source in sources:
            self.assertEqual(self.by_source[source]["status"], "governed_composite")
            self.assertEqual(self.by_source[source]["targetBatch"], batch)

    def test_shared_utility_scene_sources_have_machine_proven_completion(self) -> None:
        batch = "p0-shared-utility-scene-completion-v1"
        sources = INVENTORY.BATCH_BINDINGS[batch]
        self.assertEqual(len(sources), 21)
        for source in sources:
            self.assertEqual(self.by_source[source]["status"], "governed_composite")
            self.assertEqual(self.by_source[source]["targetBatch"], batch)

    def test_zero_gap_report_has_no_stale_next_batch(self) -> None:
        self.assertEqual(self.report["summary"]["gap"], 0)
        self.assertIsNone(self.report["nextBatch"])

    def test_collection_ownership_without_semantic_binding_fails_closed(self) -> None:
        source = "frontend/apps/web/src/components/product-list/CollectionPaginationFooter.vue"
        fake = """<template><nav :data-state=\"loading ? 'loading' : 'ready'\"></nav></template>
<script setup lang=\"ts\"></script>"""
        status, reason = INVENTORY.classify(source, fake)
        self.assertEqual(status, "gap")
        self.assertIn("data-semantic-component", reason)

    def test_next_batch_missing_marker_fails_closed(self) -> None:
        source = "frontend/apps/web/src/components/page/BlockRenderer.vue"
        status, reason = INVENTORY.classify(source, "<ScErrorState />")
        self.assertEqual(status, "gap")
        self.assertIn("invalid bindings", reason)

    def test_comment_and_unused_import_cannot_fake_completion(self) -> None:
        source = "frontend/apps/web/src/components/page/BlockRenderer.vue"
        fake = """<template><!-- <ScErrorState density=\"compact\" :heading-level=\"5\" /> --></template>
<script setup>import ScErrorState from '../design-system/ScErrorState.vue';</script>"""
        status, _ = INVENTORY.classify(source, fake)
        self.assertEqual(status, "gap")

    def test_statically_dead_template_binding_cannot_fake_completion(self) -> None:
        source = "frontend/apps/web/src/components/page/BlockRenderer.vue"
        fake = """<template><section v-if=\"false\">
<ScErrorState density=\"compact\" :heading-level=\"5\" />
</section></template>
<script setup>import ScErrorState from '../design-system/ScErrorState.vue';</script>"""
        status, reason = INVENTORY.classify(source, fake)
        self.assertEqual(status, "gap")
        self.assertIn("template nodes 0", reason)

    def test_native_composites_require_explicit_reason(self) -> None:
        for source, reason in INVENTORY.DELIBERATE_NATIVE_COMPOSITES.items():
            self.assertEqual(self.by_source[source]["status"], "deliberate_native_composite")
            self.assertEqual(self.by_source[source]["reason"], reason)
            self.assertTrue(reason.strip())

    def test_formal_surface_cannot_regress_to_raw_control(self) -> None:
        source = "frontend/apps/web/src/components/template/NativeSmartAction.vue"
        fake = """<template><button>办理</button><ScButton>办理</ScButton></template>
<script setup>import ScButton from '../design-system/ScButton.vue';</script>"""
        status, reason = INVENTORY.classify(source, fake)
        self.assertEqual(status, "gap")
        self.assertIn("bypasses governed adapters", reason)

    def test_p0_p1_raw_control_bypass_is_zero(self) -> None:
        self.assertEqual(self.report["summary"]["p0P1RawControlBypassSurfaceCount"], 0)
        self.assertEqual(self.report["summary"]["p0P1RawControlBypassControlCount"], 0)
        self.assertEqual(self.report["completionPolicy"]["formalP0P1RawControlBypassTarget"], 0)

    def test_p3_surfaces_do_not_masquerade_as_p0_completion(self) -> None:
        for source in INVENTORY.P3_FILES:
            if source in self.by_source:
                self.assertEqual(self.by_source[source]["status"], "p3_out_of_scope")
                self.assertEqual(self.by_source[source]["formalProductLayer"], "P3")
        low_code = "frontend/apps/web/src/pages/contractForm/LowCodeFieldCreateDialog.vue"
        self.assertEqual(self.by_source[low_code]["status"], "p3_out_of_scope")

    def test_report_binds_generator_and_all_vue_inputs(self) -> None:
        self.assertNotIn("sourceCommit", self.report)
        self.assertRegex(self.report["sourceIdentity"], r"^[0-9a-f]{64}$")
        self.assertRegex(self.report["generatorDigest"], r"^[0-9a-f]{64}$")
        self.assertRegex(self.report["inputDigest"], r"^[0-9a-f]{64}$")
        self.assertRegex(self.report["ownershipDigest"], r"^[0-9a-f]{64}$")
        expected_identity = hashlib.sha256(
            (
                f"{self.report['generatorDigest']}:"
                f"{self.report['ownershipDigest']}:"
                f"{self.report['inputDigest']}"
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(self.report["sourceIdentity"], expected_identity)
        self.assertGreater(self.report["summary"]["surfaceCount"], 0)
        self.assertEqual(self.report["completionPolicy"]["formalP0P1UntreatedGapTarget"], 0)

    def test_formal_owner_source_cannot_be_removed_while_binding_remains(self) -> None:
        ownership = copy.deepcopy(INVENTORY.OWNERSHIP)
        batch = "p0-collection-state-control-completion-v1"
        removed = ownership["owners"][batch]["sources"].pop()
        failures = INVENTORY.ownership_binding_failures(ownership, INVENTORY.BATCH_BINDINGS)
        self.assertTrue(any("binding source lacks formal ownership" in failure and removed in failure for failure in failures))

    def test_formal_owner_batch_cannot_exist_without_bindings(self) -> None:
        ownership = copy.deepcopy(INVENTORY.OWNERSHIP)
        ownership["owners"]["p0-unbound-test"] = {
            "formalProductLayer": "P0",
            "sources": ["frontend/apps/web/src/components/Unbound.vue"],
        }
        failures = INVENTORY.ownership_binding_failures(ownership, INVENTORY.BATCH_BINDINGS)
        self.assertIn("formal P0/P1 owner lacks binding batch: p0-unbound-test", failures)

    def test_formal_source_cannot_have_multiple_owners(self) -> None:
        ownership = copy.deepcopy(INVENTORY.OWNERSHIP)
        duplicate = ownership["owners"]["p0-collection-state-control-completion-v1"]["sources"][0]
        ownership["owners"]["p0-navigation-hierarchy-composite-completion-v1"]["sources"].append(duplicate)
        failures = INVENTORY.ownership_binding_failures(ownership, INVENTORY.BATCH_BINDINGS)
        self.assertTrue(any("formal source has multiple owners" in failure and duplicate in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()

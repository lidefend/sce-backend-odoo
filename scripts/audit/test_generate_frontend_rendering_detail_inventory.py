#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
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
        self.assertEqual(len(sources), 13)
        self.assertEqual(self.report["nextBatch"]["key"], batch)
        for source in sources:
            self.assertIn(source, self.by_source)
            self.assertEqual(self.by_source[source]["status"], "governed_composite")
            self.assertEqual(self.by_source[source]["targetBatch"], batch)

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

    def test_p3_surfaces_do_not_masquerade_as_p0_completion(self) -> None:
        for source in INVENTORY.P3_FILES:
            if source in self.by_source:
                self.assertEqual(self.by_source[source]["status"], "p3_out_of_scope")
                self.assertEqual(self.by_source[source]["formalProductLayer"], "P3")
        low_code = "frontend/apps/web/src/pages/contractForm/LowCodeFieldCreateDialog.vue"
        self.assertEqual(self.by_source[low_code]["status"], "p3_out_of_scope")

    def test_report_binds_generator_and_all_vue_inputs(self) -> None:
        self.assertRegex(self.report["generatorDigest"], r"^[0-9a-f]{64}$")
        self.assertRegex(self.report["inputDigest"], r"^[0-9a-f]{64}$")
        self.assertRegex(self.report["ownershipDigest"], r"^[0-9a-f]{64}$")
        self.assertGreater(self.report["summary"]["surfaceCount"], 0)
        self.assertEqual(self.report["completionPolicy"]["formalP0P1UntreatedGapTarget"], 0)


if __name__ == "__main__":
    unittest.main()

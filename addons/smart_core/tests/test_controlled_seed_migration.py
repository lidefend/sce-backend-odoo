# -*- coding: utf-8 -*-
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load():
    module_name = "odoo.addons.smart_core.core.controlled_seed_migration"
    spec = importlib.util.spec_from_file_location(
        module_name, ROOT / "core" / "controlled_seed_migration.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class ControlledSeedMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load()

    def identity(self, module="smart_construction_core", external_id="seed_x"):
        return self.m.SeedIdentity(module=module, external_id=external_id)

    def plan(self, classification="VERSIONED_CODE_TEMPLATE", *, current="a", target="b",
             expected_source=None, seed_version="v1"):
        return self.m.plan_migration(
            self.identity(),
            classification,
            seed_version=seed_version,
            current_digest=current,
            target_digest=target,
            expected_source_digest=expected_source,
        )

    def test_new_seed_normal_migration(self):
        plan = self.plan(current="a", target="b")
        self.assertEqual(plan["outcome"], "migrate")
        self.assertTrue(plan["migration_id"])

    def test_no_change_skips(self):
        plan = self.plan(current="a", target="a")
        self.assertEqual(plan["outcome"], "skip")
        self.assertEqual(plan["reason"], "no_change")

    def test_duplicate_migration_id_is_idempotent(self):
        mid = self.m.migration_id("smart_construction_core", "seed_x", "v1", "b")
        self.assertEqual(self.m.decide_execution("applied")["action"], "skip_idempotent")
        self.assertTrue(mid)

    def test_same_external_id_across_modules_differs(self):
        a = self.m.migration_id("m1", "seed_x", "v1", "b")
        b = self.m.migration_id("m2", "seed_x", "v1", "b")
        self.assertNotEqual(a, b)

    def test_source_digest_mismatch(self):
        plan = self.plan(current="a", target="b", expected_source="expected")
        self.assertEqual(plan["outcome"], "error")
        self.assertEqual(plan["reason"], "source_digest_mismatch")

    def test_target_digest_mismatch_detected(self):
        self.assertFalse(self.m.verify_target_digest({"x": 1}, "target"))
        self.assertTrue(self.m.verify_target_digest(
            {"x": 1}, self.m._stable_digest({"x": 1}),
        ))

    def test_interruption_leaves_no_applied_state(self):
        self.assertEqual(self.m.decide_execution("running")["action"], "reject_concurrent")

    def test_snapshot_rollback_reference(self):
        ref = self.m.rollback_reference({"definition_sha256": "d", "payload_sha256": "p"})
        self.assertEqual(ref["kind"], "version_snapshot")
        self.assertEqual(ref["definition_digest"], "d")

    def test_restore_digest_consistent(self):
        payload = {"composition_mode": "entry_semantic_surface"}
        digest = self.m._stable_digest(payload)
        self.assertTrue(self.m.verify_target_digest(payload, digest))

    def test_failed_retry_requires_cleanup(self):
        self.assertEqual(self.m.decide_execution("failed")["action"], "require_cleanup_verification")
        self.assertEqual(self.m.decide_execution("failed", cleanup_verified=True)["action"], "retry")

    def test_running_state_rejects_concurrency(self):
        self.assertEqual(self.m.decide_execution("running")["action"], "reject_concurrent")

    def test_tenant_lowcoding_not_runner_target(self):
        plan = self.plan("USER_OWNED_CONFIGURATION")
        self.assertEqual(plan["outcome"], "skip")
        self.assertEqual(plan["reason"], "user_owned")

    def test_user_preference_not_runner_target(self):
        plan = self.plan("IMMUTABLE_CODE_SEED")
        self.assertEqual(plan["reason"], "immutable_frozen")

    def test_retired_seed_skipped(self):
        plan = self.plan("RETIRED_CONFIGURATION")
        self.assertEqual(plan["outcome"], "skip")
        self.assertEqual(plan["reason"], "retired")

    def test_plan_includes_publication_gate_signal(self):
        plan = self.plan(current="a", target="b")
        self.assertEqual(plan["outcome"], "migrate")
        self.assertIn("source_digest", plan)
        self.assertIn("target_digest", plan)

    def test_post_migration_digest_selects_effective_config(self):
        payload = {"composition_mode": "native_semantic_surface"}
        self.assertTrue(self.m.verify_target_digest(payload, self.m._stable_digest(payload)))


class _FakeRecord:
    def __init__(self, payload, source="smart_construction_core.product_release",
                 active=True, view_type="form", composition_mode="", has_sections=False,
                 name="seed"):
        self.contract_json = payload
        self.source = source
        self.active = active
        self.view_type = view_type
        self.composition_mode = composition_mode
        self.has_sections = has_sections
        self.name = name
        self.definition_sha256 = _load()._stable_digest(payload)
        self.restored = None
        self.published = None

    def latest_published_version(self):
        return {"definition_sha256": self.definition_sha256}

    def replace_and_publish(self, payload):
        self.published = payload
        self.contract_json = payload

    def restore_published_version(self, version):
        self.restored = version


class RunMigrationAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load()

    def test_classify_lowcode_is_user_owned(self):
        self.assertEqual(
            self.m.classify_record(source="smart_core.lowcode.business_config", active=True, view_type="form"),
            "USER_OWNED_CONFIGURATION",
        )

    def test_classify_retired(self):
        self.assertEqual(
            self.m.classify_record(source="x", active=False, view_type="form"),
            "RETIRED_CONFIGURATION",
        )

    def test_classify_entry_sections_as_versioned_template(self):
        self.assertEqual(
            self.m.classify_record(
                source="smart_construction_core.product_release", active=True,
                view_type="form", composition_mode="entry_semantic_surface",
            ),
            "VERSIONED_CODE_TEMPLATE",
        )

    def test_run_migration_applies(self):
        record = _FakeRecord(
            {"composition_mode": "entry_semantic_surface", "sections": [{"title": "a"}]},
            composition_mode="entry_semantic_surface",
        )
        target = {"composition_mode": "entry_semantic_surface", "sections": [{"key": "a", "title": "a", "fields": ["name"]}]}
        result = self.m.run_migration(
            record, module="smart_construction_core", external_id="seed_x",
            seed_version="v1", target_payload=target,
        )
        self.assertEqual(result["outcome"], "applied")
        self.assertEqual(record.published, target)

    def test_run_migration_skips_no_change(self):
        payload = {"composition_mode": "native_semantic_surface"}
        record = _FakeRecord(payload)
        result = self.m.run_migration(
            record, module="smart_construction_core", external_id="seed_x",
            seed_version="v1", target_payload=payload,
        )
        self.assertEqual(result["outcome"], "skip")

    def test_run_migration_target_mismatch_restores(self):
        class _MismatchRecord(_FakeRecord):
            def replace_and_publish(self, payload):
                # Simulate Odoo normalizing the payload into a shape that no
                # longer matches the target digest.
                self.published = dict(payload, _unexpected="x")
                self.contract_json = self.published

        record = _MismatchRecord(
            {"composition_mode": "entry_semantic_surface"},
            composition_mode="entry_semantic_surface",
        )
        target = {"composition_mode": "entry_semantic_surface", "sections": [{"key": "a", "title": "a", "fields": ["name"]}]}
        result = self.m.run_migration(
            record, module="smart_construction_core", external_id="seed_x",
            seed_version="v1", target_payload=target,
        )
        self.assertEqual(result["outcome"], "error")
        self.assertEqual(result["reason"], "target_digest_mismatch")
        self.assertIsNotNone(record.restored)


if __name__ == "__main__":
    unittest.main()

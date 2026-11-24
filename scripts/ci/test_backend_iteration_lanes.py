import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import backend_iteration_lanes as lanes


HEAD = "a" * 40
BASE = "b" * 40
TREE = "c" * 40


def plan(*, suite="product", head=HEAD, base="", modules=None):
    modules = modules or [f"{suite}_module"]
    return {
        "head": head,
        "base": base,
        "suite": suite,
        "scope_mode": "full",
        "modules": modules,
        "shards": [{"index": 0, "modules": modules}],
    }


class PlanTests(unittest.TestCase):
    def test_plan_binds_exact_head_suite_base_and_complete_membership(self):
        lanes.validate_plan(
            plan(base=BASE),
            head=HEAD,
            suite="product",
            expected_modules=["product_module"],
            allowed_bases={BASE},
        )
        for change in (
            {"head": "d" * 40},
            {"suite": "demo"},
            {"scope_mode": "focused"},
            {"base": ""},
            {"modules": ["other"]},
            {"shards": [{"modules": ["product_module", "product_module"]}]},
        ):
            with self.subTest(change=change), self.assertRaises(lanes.LaneError):
                lanes.validate_plan(
                    {**plan(base=BASE), **change},
                    head=HEAD,
                    suite="product",
                    expected_modules=["product_module"],
                    allowed_bases={BASE},
                )

    def test_closure_surface_is_exact_and_unknown_paths_do_not_require_all_lanes(self):
        for path in (
            ".github/workflows/backend_test_suite.yml",
            "make/ci.mk",
            "scripts/ci/backend_suite_plan.py",
            "scripts/test/test.sh",
        ):
            self.assertTrue(lanes.required_for_paths([path]), path)
        for path in (
            "addons/smart_construction_core/models/project.py",
            "docs/ops/readme.md",
            "frontend/apps/web/src/App.vue",
        ):
            self.assertFalse(lanes.required_for_paths([path]), path)

    def test_direct_run_selection_requires_exact_title_head_and_event(self):
        title = lanes.direct_run_title("demo", HEAD)
        rows = [
            {"databaseId": 1, "headSha": HEAD, "event": "workflow_dispatch", "displayTitle": title},
            {"databaseId": 2, "headSha": HEAD, "event": "workflow_dispatch",
             "displayTitle": lanes.direct_run_title("acceptance", HEAD)},
            {"databaseId": 3, "headSha": "d" * 40, "event": "workflow_dispatch", "displayTitle": title},
        ]
        self.assertEqual(1, lanes.select_direct_run(rows, head=HEAD, suite="demo")["databaseId"])


class FakeArtifactClient:
    def __init__(self, *, name, run_id, raw):
        self.name = name
        self.run_id = run_id
        self.raw = raw
        self.digest = "sha256:" + lanes.hashlib.sha256(raw).hexdigest()

    def artifacts(self, run_id):
        return [{"id": 9, "name": self.name, "expired": False}]

    def artifact(self, artifact_id):
        return {
            "id": artifact_id,
            "name": self.name,
            "expired": False,
            "digest": self.digest,
            "workflow_run": {"id": self.run_id},
        }

    def artifact_zip(self, artifact_id):
        return self.raw


class ArtifactTests(unittest.TestCase):
    def test_plan_artifact_is_digest_bound_and_single_file(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("backend-plan.json", json.dumps(plan()))
        raw = archive.getvalue()
        client = FakeArtifactClient(name="backend-plan-7-product", run_id=7, raw=raw)
        result = lanes.read_plan_artifact(client, run_id=7, suite="product")
        self.assertEqual("product", result["plan"]["suite"])
        self.assertTrue(result["artifact_digest"].startswith("sha256:"))

    def test_plan_artifact_rejects_digest_or_origin_drift(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("backend-plan.json", json.dumps(plan()))
        raw = archive.getvalue()
        client = FakeArtifactClient(name="backend-plan-7-product", run_id=7, raw=raw)
        client.digest = "sha256:" + "0" * 64
        with self.assertRaises(lanes.LaneError):
            lanes.read_plan_artifact(client, run_id=7, suite="product")


class CloseEfficiencyTests(unittest.TestCase):
    def test_full_product_from_required_ci_reuses_and_dispatches_only_auxiliary(self):
        class Client:
            def runs(self, workflow, head):
                return []

        product_run = {
            "databaseId": 10, "headSha": HEAD, "event": "pull_request",
            "status": "completed", "conclusion": "success",
            "displayTitle": "professional_quality_gate",
            "url": "https://example.test/10", "workflowName": "professional_quality_gate",
        }
        demo_run = {
            "databaseId": 11, "headSha": HEAD, "event": "workflow_dispatch",
            "status": "completed", "conclusion": "success",
            "displayTitle": lanes.direct_run_title("demo", HEAD),
            "url": "https://example.test/11", "workflowName": "backend_test_suite",
        }
        acceptance_run = {
            "databaseId": 12, "headSha": HEAD, "event": "workflow_dispatch",
            "status": "completed", "conclusion": "success",
            "displayTitle": lanes.direct_run_title("acceptance", HEAD),
            "url": "https://example.test/12", "workflowName": "backend_test_suite",
        }
        artifacts = {
            "product": {"artifact_id": 20, "artifact_digest": "sha256:" + "1" * 64,
                        "plan": plan()},
            "demo": {"artifact_id": 21, "artifact_digest": "sha256:" + "2" * 64,
                     "plan": plan(suite="demo")},
            "acceptance": {"artifact_id": 22, "artifact_digest": "sha256:" + "3" * 64,
                           "plan": plan(suite="acceptance")},
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "receipt.json"
            with patch.object(lanes, "preflight", return_value=(
                    {"number": 99}, BASE, TREE)), patch.object(
                    lanes, "expected_suite_modules",
                    side_effect=lambda head, suite: [f"{suite}_module"]), patch.object(
                    lanes, "start_or_reuse_direct",
                    side_effect=[(demo_run, True), (acceptance_run, True)]), patch.object(
                    lanes, "resolve_product_lane",
                    return_value=(product_run, artifacts["product"], False)), patch.object(
                    lanes, "wait_for_run",
                    side_effect=[product_run, demo_run, acceptance_run]), patch.object(
                    lanes, "read_plan_artifact",
                    side_effect=[artifacts["demo"], artifacts["acceptance"]]):
                manifest = lanes.close_lanes(
                    Client(),
                    branch="fix/lane",
                    head=HEAD,
                    output=output,
                    timeout_seconds=60,
                    discovery_seconds=1,
                    professional_wait_seconds=1,
                    poll_seconds=0.1,
                )
        self.assertTrue(manifest["efficiency"]["product_full_reused_from_required_ci"])
        self.assertEqual(["acceptance", "demo"], manifest["efficiency"]["dispatched_suites"])
        self.assertEqual(
            "professional_quality_gate", manifest["suites"]["product"]["source"]
        )
        self.assertEqual("", artifacts["product"]["plan"]["base"])


class MergeGateTests(unittest.TestCase):
    def test_harness_change_requires_receipt_and_unrelated_pr_does_not(self):
        class Client:
            def __init__(self, paths):
                self.paths = paths

            def pr_files(self, number):
                return self.paths

        with tempfile.TemporaryDirectory() as tmp, patch.object(
            lanes, "preflight",
            return_value=({"number": 99}, BASE, TREE),
        ):
            missing = Path(tmp) / "missing.json"
            with self.assertRaisesRegex(lanes.LaneError, "receipt is missing"):
                lanes.verify_manifest(
                    Client(["make/ci.mk"]),
                    pr=99,
                    head=HEAD,
                    receipt=missing,
                )
            self.assertEqual(
                "not_required",
                lanes.verify_manifest(
                    Client(["addons/smart_construction_core/models/project.py"]),
                    pr=99,
                    head=HEAD,
                    receipt=missing,
                )["status"],
            )


if __name__ == "__main__":
    unittest.main()

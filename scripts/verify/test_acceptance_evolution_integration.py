# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

import acceptance_evolution_binding_guard as guard  # noqa: E402
import acceptance_evolution_integration as integration  # noqa: E402


HEAD = "a" * 40
OTHER = "b" * 40


class TestAcceptanceIntegrationPlanner(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "suites": {
                "list": {
                    "description": "list evidence",
                    "entrypoints": ["make verify.list"],
                    "evidence": {"adapter": "list_surface"},
                    "integration": {
                        "targets": [
                            "verify.list.unit",
                            "verify.list.browser",
                        ],
                        "evidence": [".runtime/list/*/{head}/summary.json"],
                    },
                    "stages": ["merge"],
                },
                "relation": {
                    "description": "relation evidence",
                    "entrypoints": ["make verify.relation"],
                    "evidence": {"adapter": "relation_roundtrip"},
                    "integration": {
                        "targets": ["verify.relation.browser"],
                        "evidence": [".runtime/relation/{head}/summary.json"],
                    },
                    "stages": ["merge"],
                },
            },
            "rules": [],
            "policy": {
                "evidence_carry_forward": {
                    "enabled": True,
                    "mode": "suite_input_fingerprint",
                }
            },
        }
        self.plan = {
            "base_sha": OTHER,
            "head_sha": HEAD,
            "required_evidence_suites": ["list"],
            "deferred_evidence_suites": [],
            "stage": "merge",
        }

    def test_plan_marks_only_required_suite_for_run(self):
        with tempfile.TemporaryDirectory() as raw:
            result = integration.build_run_plan(
                self.registry,
                self.plan,
                Path(raw) / "evidence.json",
                HEAD,
            )
        self.assertEqual(result["status"], "planned")
        self.assertEqual([row["suite"] for row in result["run"]], ["list"])
        self.assertEqual(result["reuse"], [])
        self.assertEqual(result["not_required"], ["relation"])

    def test_deferred_suite_is_not_reported_as_not_required(self):
        plan = {**self.plan, "deferred_evidence_suites": ["relation"]}
        with tempfile.TemporaryDirectory() as raw:
            result = integration.build_run_plan(
                self.registry,
                plan,
                Path(raw) / "evidence.json",
                HEAD,
            )
        self.assertEqual(result["deferred_suites"], ["relation"])
        self.assertEqual(result["not_required"], [])

    def test_full_or_reverify_requires_explicit_reason(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest = Path(raw) / "evidence.json"
            with self.assertRaisesRegex(integration.IntegrationError, "full.*reason"):
                integration.build_run_plan(
                    self.registry, self.plan, manifest, HEAD, full=True
                )
            with self.assertRaisesRegex(integration.IntegrationError, "reverify.*reason"):
                integration.build_run_plan(
                    self.registry,
                    self.plan,
                    manifest,
                    HEAD,
                    reverify_suites=("list",),
                )
            with self.assertRaisesRegex(integration.IntegrationError, "outside"):
                integration.build_run_plan(
                    self.registry,
                    self.plan,
                    manifest,
                    HEAD,
                    reverify_suites=("relation",),
                    reverify_reason="not in current required set",
                )

    def test_reusable_suite_is_not_executed(self):
        reusable = {"bound_head": OTHER, "input_sha256": "a" * 64}
        with tempfile.TemporaryDirectory() as raw, patch.object(
            integration.recorder, "_reuse_suite_record", return_value=reusable
        ):
            result = integration.build_run_plan(
                self.registry,
                self.plan,
                Path(raw) / "evidence.json",
                HEAD,
            )
        self.assertEqual(result["status"], "reuse_only")
        self.assertEqual(result["run"], [])
        self.assertEqual([row["suite"] for row in result["reuse"]], ["list"])

    def test_execution_uses_declared_targets_then_records_evidence(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs["cwd"]))
            return subprocess.CompletedProcess(command, 0)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            evidence = root / ".runtime" / "list" / "run" / HEAD / "summary.json"
            evidence.parent.mkdir(parents=True)
            evidence.write_text('{"status":"pass"}\n', encoding="utf-8")
            output = root / "integration-plan.json"
            run_plan = integration.build_run_plan(
                self.registry,
                self.plan,
                root / "evidence.json",
                HEAD,
            )
            with patch.object(
                integration.recorder, "_require_clean_worktree"
            ), patch.object(
                integration.recorder,
                "record_manifest",
                return_value=(
                    {"recorded_at": "2026-11-17T00:00:00Z"},
                    ["list"],
                    [],
                ),
            ) as record:
                result = integration.execute_run_plan(
                    self.registry,
                    self.plan,
                    root / "evidence.json",
                    run_plan,
                    head=HEAD,
                    output=output,
                    prepare_target="acceptance.prepare",
                    root=root,
                    runner=runner,
                )
        self.assertEqual(
            [command for command, _ in calls],
            [
                ["make", "--no-print-directory", "acceptance.prepare"],
                ["make", "--no-print-directory", "verify.list.unit"],
                ["make", "--no-print-directory", "verify.list.browser"],
            ],
        )
        self.assertTrue(all(path == root for _, path in calls))
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["recorded_suites"], ["list"])
        self.assertEqual(record.call_args.args[4], {"list": [evidence]})

    def test_reuse_only_execution_performs_no_runtime_preparation(self):
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0)

        run_plan = {
            "schema": integration.SCHEMA,
            "head_sha": HEAD,
            "base_sha": OTHER,
            "required_suites": ["list"],
            "deferred_suites": [],
            "run": [],
            "reuse": [{"suite": "list", "bound_head": OTHER}],
            "not_required": ["relation"],
            "status": "reuse_only",
            "candidate_evidence": False,
            "writes_authorized": False,
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with patch.object(
                integration.recorder, "_require_clean_worktree"
            ), patch.object(
                integration.recorder, "record_manifest"
            ) as record:
                result = integration.execute_run_plan(
                    self.registry,
                    self.plan,
                    root / "evidence.json",
                    run_plan,
                    head=HEAD,
                    output=root / "integration-plan.json",
                    prepare_target="acceptance.prepare",
                    root=root,
                    runner=runner,
                )
        self.assertEqual(calls, [])
        self.assertEqual(result["status"], "reuse_only")
        self.assertTrue(result["candidate_evidence"])
        record.assert_not_called()

    def test_integration_metadata_does_not_invalidate_suite_inputs(self):
        base = guard._git("rev-parse", "HEAD")
        before = guard.suite_input_sha256(
            guard.load_registry(guard.DEFAULT_REGISTRY),
            "list_surface_structure",
            base,
        )
        registry = guard.load_registry(guard.DEFAULT_REGISTRY)
        registry["suites"]["list_surface_structure"]["integration"]["targets"].append(
            "verify.list.additional"
        )
        after = guard.suite_input_sha256(registry, "list_surface_structure", base)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_evolution_binding_guard as guard  # noqa: E402

HEAD = "a" * 40
OTHER = "b" * 40


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _entry_verify(head: str = HEAD, passed: bool = True) -> dict:
    return {
        "status": "PASS" if passed else "FAIL",
        "expected_sha": head,
        "head": head,
        "checks": [
            {"name": "one", "passed": True},
            {"name": "two", "passed": passed},
        ],
    }


def _path_ns(head: str = HEAD) -> dict:
    return {
        "schema": "path-ns-c.acceptance.v1",
        "provenance": {"expected_sha": head},
        "summary": {"total": 23, "passed": 23, "failed": 0, "status": "PASS"},
    }


def _list_surface(head: str = HEAD) -> dict:
    return {
        "schema": "frontend_list_surface_structure_browser.v1",
        "passed": True,
        "failures": 0,
        "summary": {"observations": 6, "gated": {"total": 12}, "runtime_errors": 0},
        "source": {"acceptance": {"provenance": {"expectedSha": head}}},
    }


def _relation(head: str = HEAD) -> dict:
    return {
        "schema": "record-relation-roundtrip-acceptance.v1",
        "status": "pass",
        "expected_sha": head,
        "failures": [],
        "declared_entry_count": 4,
        "declared_openable": [{}, {}, {}, {}],
    }


class TestGlobAndPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = guard.load_registry(
            ROOT / "config" / "acceptance" / "evolution_binding.v1.json"
        )

    def test_glob_semantics(self):
        self.assertTrue(guard.path_matches("addons/**", "addons/a.py"))
        self.assertTrue(guard.path_matches("addons/**", "addons/a/b.py"))
        self.assertFalse(guard.path_matches("addons/**", "addons_other/a.py"))
        self.assertTrue(guard.path_matches("**/*.md", "README.md"))
        self.assertTrue(guard.path_matches("**/*.md", "docs/a/b.md"))
        self.assertTrue(guard.path_matches("docker-compose*.yml", "docker-compose.ci.yml"))
        self.assertFalse(guard.path_matches("docker-compose*.yml", "nested/docker-compose.yml"))

    def test_plan_maps_runtime_changes_to_acceptance_suites(self):
        plan = guard.build_plan(
            self.registry,
            ["addons/smart_core/app_config_engine/models/app_nav_config.py"],
            "base",
            HEAD,
        )
        self.assertEqual(plan["status"], "PASS")
        self.assertEqual(plan["required_suites"], ["backend_contract", "daily_runtime_entry"])
        self.assertEqual(plan["required_evidence_suites"], ["daily_runtime_entry"])

    def test_plan_keeps_docs_only_changes_out_of_runtime_evidence(self):
        plan = guard.build_plan(self.registry, ["docs/ops/readme.md"], "base", HEAD)
        self.assertEqual(plan["status"], "PASS")
        self.assertEqual(plan["required_suites"], [])
        self.assertEqual(plan["required_evidence_suites"], [])

    def test_plan_fails_closed_for_unclassified_paths(self):
        plan = guard.build_plan(self.registry, ["new_surface/unknown.txt"], "base", HEAD)
        self.assertEqual(plan["status"], "FAIL")
        self.assertEqual(plan["unclassified"], ["new_surface/unknown.txt"])

    def test_every_declared_suite_is_reachable_from_a_rule(self):
        referenced = {
            suite_id
            for rule in self.registry["rules"]
            for suite_id in rule["suites"]
        }
        self.assertEqual(set(self.registry["suites"]), referenced)


class TestAdapters(unittest.TestCase):
    def test_entry_verify_adapter(self):
        counts = guard.validate_evidence_file
        self.assertEqual(
            guard._adapter_entry_verify(_entry_verify(), HEAD)["counts"]["passed"], 2
        )
        with self.assertRaises(guard.BindingError):
            guard._adapter_entry_verify(_entry_verify(OTHER), HEAD)
        with self.assertRaises(guard.BindingError):
            guard._adapter_entry_verify(_entry_verify(passed=False), HEAD)
        self.assertIs(counts, guard.validate_evidence_file)

    def test_path_namespace_adapter(self):
        result = guard._adapter_path_ns_c(_path_ns(), HEAD)
        self.assertEqual(result["counts"], {"total": 23, "passed": 23, "failed": 0})
        with self.assertRaises(guard.BindingError):
            guard._adapter_path_ns_c(_path_ns(OTHER), HEAD)

    def test_list_surface_adapter(self):
        result = guard._adapter_list_surface(_list_surface(), HEAD)
        self.assertEqual(result["counts"]["failures"], 0)
        broken = _list_surface()
        broken["passed"] = False
        with self.assertRaises(guard.BindingError):
            guard._adapter_list_surface(broken, HEAD)
        with self.assertRaises(guard.BindingError):
            guard._adapter_list_surface(_list_surface(OTHER), HEAD)

    def test_relation_roundtrip_adapter(self):
        result = guard._adapter_relation_roundtrip(_relation(), HEAD)
        self.assertEqual(result["counts"]["openable_entries"], 4)
        broken = _relation()
        broken["failures"] = ["x"]
        with self.assertRaises(guard.BindingError):
            guard._adapter_relation_roundtrip(broken, HEAD)


class TestManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = guard.load_registry(
            ROOT / "config" / "acceptance" / "evolution_binding.v1.json"
        )
        cls.plan = {
            "required_evidence_suites": ["daily_runtime_entry"],
        }

    def _manifest(self, directory: Path, head: str = HEAD) -> Path:
        evidence = _write(directory / "entry.json", _entry_verify(head))
        payload = {
            "schema": guard.EVIDENCE_SCHEMA,
            "head_sha": head,
            "base_sha": "c" * 40,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "suites": {
                "daily_runtime_entry": {
                    "status": "pass",
                    "evidence": [
                        {
                            "path": str(evidence),
                            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                        }
                    ],
                }
            },
        }
        return _write(directory / "manifest.json", payload)

    def test_exact_head_manifest_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            result = guard.validate_manifest(
                self.registry, self.plan, self._manifest(Path(raw)), HEAD
            )
            self.assertEqual(result["status"], "PASS")
            self.assertIn("daily_runtime_entry", result["suites"])

    def test_manifest_head_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(guard.BindingError):
                guard.validate_manifest(
                    self.registry, self.plan, self._manifest(Path(raw), OTHER), HEAD
                )

    def test_missing_required_suite_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest = self._manifest(Path(raw))
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["suites"] = {}
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(guard.BindingError):
                guard.validate_manifest(self.registry, self.plan, manifest, HEAD)

    def test_evidence_tampering_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest = self._manifest(directory)
            _write(directory / "entry.json", _entry_verify(OTHER))
            with self.assertRaises(guard.BindingError):
                guard.validate_manifest(self.registry, self.plan, manifest, HEAD)

    def test_stale_manifest_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest = self._manifest(Path(raw))
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["recorded_at"] = "2000-01-01T00:00:00Z"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(guard.BindingError):
                guard.validate_manifest(self.registry, self.plan, manifest, HEAD)


if __name__ == "__main__":
    unittest.main()

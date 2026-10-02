#!/usr/bin/env python3
"""Offline lock for the contract version consumer-compatibility core.

Baseline first: the N-1 / N / N+1 drill passes over an additive evolution. Each
negative then injects exactly one breaking move and requires the owning reason
code, so "compatible" cannot be produced by an unconditional default.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_PATH = ROOT / "addons/smart_core/core/contract_version_compatibility.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


COMPAT = load_module("contract_version_compatibility", CORE_PATH)


def _versions() -> dict:
    base = {
        "renderStrategy": {"type": "string", "required": True, "enum": ["incremental", "full"],
                           "open_enum": True},
        "fieldCount": {"type": "integer", "required": True, "enum": []},
        "governance": {"type": "object", "required": False, "enum": []},
    }
    middle = dict(base)
    middle["owner"] = {"type": "string", "required": False, "enum": []}
    newer = dict(middle)
    newer["renderStrategy"] = {
        "type": "string",
        "required": True,
        "enum": ["incremental", "full", "streamed"],
        "open_enum": True,
    }
    newer["virtualization"] = {"type": "object", "required": False, "enum": []}
    return {"n_minus_one": base, "n": middle, "n_plus_one": newer}


def _payloads() -> dict:
    return {
        "n_minus_one": {"renderStrategy": "incremental", "fieldCount": 12},
        "n": {"renderStrategy": "incremental", "fieldCount": 12, "owner": "platform"},
        "n_plus_one": {
            "renderStrategy": "streamed",
            "fieldCount": 12,
            "owner": "platform",
            "virtualization": {},
        },
    }


class DrillBaselineTest(unittest.TestCase):
    def test_baseline_adjacent_drill_passes(self):
        report = COMPAT.drill_adjacent(_versions(), _payloads())
        self.assertEqual(report["failedCount"], 0, report["failed"])
        self.assertEqual(report["checkCount"], len(COMPAT.check_names()))
        self.assertEqual([check["name"] for check in report["checks"]], list(COMPAT.check_names()))
        self.assertEqual(report["deltaLower"]["delta"], COMPAT.DELTA_ADDITIVE)
        self.assertEqual(report["deltaUpper"]["delta"], COMPAT.DELTA_ADDITIVE)

    def test_identical_declaration_is_identical_not_additive(self):
        versions = _versions()
        report = COMPAT.compare_declarations(versions["n"], versions["n"])
        self.assertEqual(report["delta"], COMPAT.DELTA_IDENTICAL)
        self.assertEqual(report["findingCount"], 0)


class DeltaClassificationTest(unittest.TestCase):
    def test_removed_key_is_breaking(self):
        versions = _versions()
        report = COMPAT.compare_declarations(versions["n"], versions["n_minus_one"])
        self.assertTrue(report["breaking"])
        self.assertEqual(report["findings"][0]["reason"], COMPAT.REASON_KEY_REMOVED)

    def test_newly_required_key_is_breaking(self):
        report = COMPAT.compare_declarations(
            {"a": {"type": "string", "required": True, "enum": []}},
            {"a": {"type": "string", "required": True, "enum": []},
             "b": {"type": "string", "required": True, "enum": []}},
        )
        self.assertTrue(report["breaking"])
        self.assertEqual(report["findings"][0]["reason"], COMPAT.REASON_REQUIRED_KEY_ADDED)

    def test_newly_optional_key_is_additive(self):
        report = COMPAT.compare_declarations(
            {"a": {"type": "string", "required": True, "enum": []}},
            {"a": {"type": "string", "required": True, "enum": []},
             "b": {"type": "string", "required": False, "enum": []}},
        )
        self.assertFalse(report["breaking"])
        self.assertEqual(report["delta"], COMPAT.DELTA_ADDITIVE)
        self.assertEqual(report["findings"][0]["reason"], COMPAT.REASON_OPTIONAL_KEY_ADDED)

    def test_type_change_is_breaking(self):
        report = COMPAT.compare_declarations(
            {"a": {"type": "integer", "required": True, "enum": []}},
            {"a": {"type": "string", "required": True, "enum": []}},
        )
        self.assertTrue(report["breaking"])
        self.assertEqual(report["findings"][0]["reason"], COMPAT.REASON_TYPE_CHANGED)

    def test_removed_enum_member_is_breaking(self):
        report = COMPAT.compare_declarations(
            {"a": {"type": "string", "required": True, "enum": ["x", "y"]}},
            {"a": {"type": "string", "required": True, "enum": ["x"]}},
        )
        self.assertTrue(report["breaking"])
        self.assertEqual(report["findings"][0]["reason"], COMPAT.REASON_ENUM_MEMBER_REMOVED)

    def test_added_enum_member_to_an_open_enum_is_additive(self):
        report = COMPAT.compare_declarations(
            {"a": {"type": "string", "required": True, "enum": ["x"], "open_enum": True}},
            {"a": {"type": "string", "required": True, "enum": ["x", "y"], "open_enum": True}},
        )
        self.assertFalse(report["breaking"])
        self.assertEqual(report["findings"][0]["reason"], COMPAT.REASON_ENUM_MEMBER_ADDED)

    def test_added_enum_member_to_a_closed_enum_is_breaking(self):
        report = COMPAT.compare_declarations(
            {"a": {"type": "string", "required": True, "enum": ["x"]}},
            {"a": {"type": "string", "required": True, "enum": ["x", "y"]}},
        )
        self.assertTrue(report["breaking"])
        self.assertEqual(report["findings"][0]["reason"], COMPAT.REASON_ENUM_MEMBER_ADDED_TO_CLOSED_ENUM)

    def test_tightened_required_flag_is_breaking(self):
        report = COMPAT.compare_declarations(
            {"a": {"type": "string", "required": False, "enum": []}},
            {"a": {"type": "string", "required": True, "enum": []}},
        )
        self.assertTrue(report["breaking"])
        self.assertEqual(report["findings"][0]["reason"], COMPAT.REASON_REQUIRED_TIGHTENED)


class ConsumerRefusalTest(unittest.TestCase):
    def test_unknown_payload_keys_are_tolerated(self):
        result = COMPAT.check_consumer(
            {"a": {"type": "string", "required": True, "enum": []}},
            {"a": "x", "brand_new": {"nested": True}, "another": 1},
        )
        self.assertTrue(result["compatible"], result["refusals"])
        self.assertEqual(result["checkedKeys"], 1)

    def test_missing_required_key_is_refused(self):
        result = COMPAT.check_consumer(
            {"a": {"type": "string", "required": True, "enum": []}}, {"b": 1}
        )
        self.assertFalse(result["compatible"])
        self.assertEqual(result["refusals"][0]["reason"], COMPAT.REASON_MISSING_REQUIRED_KEY)

    def test_missing_optional_key_is_accepted(self):
        result = COMPAT.check_consumer(
            {"a": {"type": "string", "required": False, "enum": []}}, {}
        )
        self.assertTrue(result["compatible"])

    def test_type_mismatch_is_refused(self):
        result = COMPAT.check_consumer(
            {"a": {"type": "integer", "required": True, "enum": []}}, {"a": "12"}
        )
        self.assertFalse(result["compatible"])
        self.assertEqual(result["refusals"][0]["reason"], COMPAT.REASON_TYPE_MISMATCH)

    def test_boolean_is_not_accepted_as_integer(self):
        result = COMPAT.check_consumer(
            {"a": {"type": "integer", "required": True, "enum": []}}, {"a": True}
        )
        self.assertFalse(result["compatible"])

    def test_out_of_enum_value_is_refused(self):
        result = COMPAT.check_consumer(
            {"a": {"type": "string", "required": True, "enum": ["x"]}}, {"a": "z"}
        )
        self.assertFalse(result["compatible"])
        self.assertEqual(result["refusals"][0]["reason"], COMPAT.REASON_ENUM_VALUE_NOT_ALLOWED)

    def test_an_open_enum_tolerates_a_value_it_does_not_know(self):
        result = COMPAT.check_consumer(
            {"a": {"type": "string", "required": True, "enum": ["x"], "open_enum": True}},
            {"a": "z"},
        )
        self.assertTrue(result["compatible"], result["refusals"])

    def test_non_object_payload_is_refused(self):
        result = COMPAT.check_consumer({"a": "string"}, ["not", "an", "object"])
        self.assertFalse(result["compatible"])
        self.assertEqual(result["refusals"][0]["reason"], "payload_not_object")


class RollbackDrillTest(unittest.TestCase):
    def test_append_only_rollback_accepts_a_strictly_increasing_sequence(self):
        ok, reason = COMPAT.append_only_rollback([1, 2, 3])
        self.assertTrue(ok, reason)

    def test_append_only_rollback_refuses_a_reused_version(self):
        ok, reason = COMPAT.append_only_rollback([1, 2, 2])
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("version_not_strictly_increasing"))

    def test_append_only_rollback_refuses_a_regression(self):
        ok, reason = COMPAT.append_only_rollback([1, 3, 2])
        self.assertFalse(ok)
        self.assertEqual(reason, "version_not_strictly_increasing:3->2")

    def test_empty_version_sequence_is_refused(self):
        ok, reason = COMPAT.append_only_rollback([])
        self.assertFalse(ok)
        self.assertEqual(reason, "empty_version_sequence")

    def test_rollback_rule_mirrors_the_published_version_authority(self):
        # The real authority (addons/smart_core/model/ui_business_config_contract.py
        # _append_published_version) computes
        #   next = max(record.version_no, latest.version_no) + 1
        # and restore_published_version re-publishes through the same path, so a
        # publish -> rollback -> publish history only ever appends a higher
        # number. The offline rule must agree with that sequence and must refuse
        # a rewrite of an already-published number.
        history = [1]
        latest = 1
        for _ in range(2):
            latest = max(latest, latest) + 1
            history.append(latest)
        self.assertEqual(history, [1, 2, 3])
        ok, reason = COMPAT.append_only_rollback(history)
        self.assertTrue(ok, reason)
        rewrite = [1, 2, 3, 3]
        ok, reason = COMPAT.append_only_rollback(rewrite)
        self.assertFalse(ok)
        self.assertEqual(reason, "version_not_strictly_increasing:3->3")


class DrillNegativeTest(unittest.TestCase):
    def test_a_breaking_change_in_the_upper_delta_fails_the_drill(self):
        versions = _versions()
        payloads = _payloads()
        broken = dict(versions["n_plus_one"])
        broken["fieldCount"] = {"type": "string", "required": True, "enum": []}
        versions["n_plus_one"] = broken
        report = COMPAT.drill_adjacent(versions, payloads)
        self.assertIn("delta_n_to_n_plus_one_is_additive", report["failed"])
        self.assertGreater(report["failedCount"], 0)

    def test_a_removed_key_fails_the_forward_consumer_check(self):
        versions = _versions()
        payloads = _payloads()
        payloads["n"] = {"renderStrategy": "incremental"}
        report = COMPAT.drill_adjacent(versions, payloads)
        self.assertIn("n_minus_one_consumer_reads_n_payload", report["failed"])

    def test_a_missing_matrix_key_is_refused(self):
        versions = _versions()
        versions.pop("n_plus_one")
        with self.assertRaises(COMPAT.CompatibilityError):
            COMPAT.drill_adjacent(versions, _payloads())


class CompatibilityCoreBoundaryTest(unittest.TestCase):
    def test_payload_projection_treats_an_appended_list_element_as_additive(self):
        left = {"views": {"form": {"fields": [{"name": "name"}]}}}
        right = {"views": {"form": {"fields": [{"name": "name"}, {"name": "email"}]}}}
        declaration = COMPAT.declaration_from_payload(left)
        self.assertIn("views.form.fields[0].name", declaration)
        self.assertNotIn("views.form.fields[1].name", declaration)
        report = COMPAT.compare_declarations(declaration, COMPAT.declaration_from_payload(right))
        self.assertEqual(report["delta"], COMPAT.DELTA_ADDITIVE)
        self.assertEqual(report["findings"][0]["key"], "views.form.fields[1].name")

    def test_payload_projection_treats_a_removed_path_as_breaking(self):
        contract = {"a": {"b": 1}}
        narrowed = {"a": {}}
        report = COMPAT.compare_declarations(
            COMPAT.declaration_from_payload(contract), COMPAT.declaration_from_payload(narrowed)
        )
        self.assertTrue(report["breaking"])
        self.assertEqual(report["findings"][0]["reason"], COMPAT.REASON_KEY_REMOVED)
        self.assertEqual(report["findings"][0]["key"], "a.b")

    def test_payload_projection_records_leaf_types(self):
        declaration = COMPAT.declaration_from_payload({"count": 3, "flag": True, "ratio": 1.5,
                                                       "name": "x", "items": [], "nothing": None})
        self.assertEqual(declaration["count"]["type"], "integer")
        self.assertEqual(declaration["flag"]["type"], "boolean")
        self.assertEqual(declaration["ratio"]["type"], "number")
        self.assertEqual(declaration["name"]["type"], "string")
        self.assertEqual(declaration["items"]["type"], "array")
        self.assertEqual(declaration["nothing"]["type"], "null")

    def test_projection_drills_a_real_unified_page_envelope_shape(self):
        # Bound to the key surface a real ui.contract.v2 delivery exposes, so the
        # drill is exercised on the production shape and not only on toys.
        def envelope(fields, include_stage=True):
            lifecycle = {"schemaSha256": "0" * 64, "lifecycleVersion": "2.2.0"}
            if include_stage:
                lifecycle["stage"] = "runtime"
            return {
                "ok": True,
                "data": {
                    "meta": {"lifecycle": lifecycle},
                    "views": {"form": {"fields": fields, "groups": []}},
                    "actions": [{"name": "save", "kind": "primary"}],
                },
            }

        n = COMPAT.declaration_from_payload(envelope([{"name": "name", "widget": "char"}]))
        self.assertIn("data.meta.lifecycle.stage", n)
        self.assertIn("data.views.form.fields[0].widget", n)
        self.assertEqual(n["data.views.form.groups"]["type"], "array")

        additive = COMPAT.compare_declarations(
            n,
            COMPAT.declaration_from_payload(
                envelope([{"name": "name", "widget": "char"}, {"name": "email", "widget": "char"}])
            ),
        )
        self.assertEqual(additive["delta"], COMPAT.DELTA_ADDITIVE)
        self.assertIn("data.views.form.fields[1].name", [f["key"] for f in additive["findings"]])

        breaking = COMPAT.compare_declarations(
            n,
            COMPAT.declaration_from_payload(
                envelope([{"name": "name", "widget": "char"}], include_stage=False)
            ),
        )
        self.assertTrue(breaking["breaking"])
        self.assertEqual(breaking["findings"][0]["key"], "data.meta.lifecycle.stage")
        self.assertEqual(breaking["findings"][0]["reason"], COMPAT.REASON_KEY_REMOVED)

    def test_core_imports_no_odoo(self):
        tree = ast.parse(CORE_PATH.read_text(encoding="utf-8"))
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        self.assertNotIn("odoo", roots, "the compatibility core must stay offline-verifiable")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline lock for the contract SLO retention cron wiring.

The retention horizon is configuration; the scheduled sweep is what actually
enforces it. The store grew without bound once persistence was on because the
horizon had no carrier, so this suite pins the *declaration consumption* rather
than the presence of a file name:

* the cron record must target the model derived from the model's own ``_name``,
  so a rename cannot leave the cron pointing at a model that no longer exists;
* the model file must expose the called method, delegate to the pure store's
  prune helper, and stay fail-open;
* the manifest must load the data file after the ACLs it depends on.

A cron that exists but is inactive, mis-targeted, or calls a missing method is
not retention, so those are failures here rather than a documentation note.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "addons/smart_core"
MANIFEST = MODULE / "__manifest__.py"
MODEL_FILE = MODULE / "models/contract_slo_observation.py"
CRON_FILE = MODULE / "data/contract_slo_retention_cron.xml"
CORE_FILE = MODULE / "core/contract_slo_persistence.py"

CRON_XMLID = "ir_cron_sc_contract_slo_observation_prune"
CRON_CODE = "model.cron_prune()"
MODEL_METHOD = "cron_prune"
# A retention sweep must not lag the horizon by more than the horizon itself.
ALLOWED_UNITS = ("minutes", "hours", "days")
MAX_INTERVAL_DAYS = 30


def _manifest() -> dict:
    tree = ast.parse(MANIFEST.read_text(encoding="utf-8"), filename=str(MANIFEST))
    expression = next((node for node in tree.body if isinstance(node, ast.Expr)), None)
    return ast.literal_eval(expression.value) if expression else {}


def _model_name() -> str:
    tree = ast.parse(MODEL_FILE.read_text(encoding="utf-8"), filename=str(MODEL_FILE))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if (
                    isinstance(item, ast.Assign)
                    and len(item.targets) == 1
                    and isinstance(item.targets[0], ast.Name)
                    and item.targets[0].id == "_name"
                    and isinstance(item.value, ast.Constant)
                ):
                    return str(item.value.value)
    raise AssertionError("model _name not found")


def _model_class() -> ast.ClassDef:
    tree = ast.parse(MODEL_FILE.read_text(encoding="utf-8"), filename=str(MODEL_FILE))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            return node
    raise AssertionError("model class not found")


def _cron_fields() -> dict:
    root = ET.parse(CRON_FILE).getroot()
    records = root.findall(".//record")
    if len(records) != 1:
        raise AssertionError(f"expected exactly one record, got {len(records)}")
    record = records[0]
    fields = {}
    for field in record.findall("field"):
        value = (field.text or "").strip()
        if not value and field.attrib.get("ref"):
            value = f"ref:{field.attrib['ref']}"
        fields[field.attrib["name"]] = value
    return fields


class CronWiringTest(unittest.TestCase):
    def setUp(self):
        self.fields = _cron_fields()
        self.model_name = _model_name()

    def test_the_record_targets_the_model_the_model_file_declares(self):
        self.assertEqual(self.fields.get("model_id"), f"ref:model_{self.model_name.replace('.', '_')}")

    def test_the_record_calls_the_method_the_model_file_exposes(self):
        self.assertEqual(self.fields.get("code"), CRON_CODE)
        names = {node.name for node in _model_class().body if isinstance(node, ast.FunctionDef)}
        self.assertIn(MODEL_METHOD, names)

    def test_the_sweep_is_active_and_recurring(self):
        self.assertEqual(self.fields.get("active"), "True")
        self.assertEqual(self.fields.get("numbercall"), "-1")

    def test_the_interval_is_bounded_by_the_default_horizon(self):
        self.assertIn(self.fields.get("interval_type"), ALLOWED_UNITS)
        interval = int(self.fields.get("interval_number") or "0")
        self.assertGreaterEqual(interval, 1)
        days = {"minutes": interval / 1440, "hours": interval / 24, "days": float(interval)}
        self.assertLessEqual(days[self.fields["interval_type"]], MAX_INTERVAL_DAYS)

    def test_the_sweep_delegates_to_the_pure_store_prune(self):
        method = next(
            node for node in _model_class().body if isinstance(node, ast.FunctionDef) and node.name == MODEL_METHOD
        )
        self.assertTrue(
            any(isinstance(decorator, ast.Attribute) and decorator.attr == "model" for decorator in method.decorator_list),
            "cron method must be an @api.model method",
        )
        called = {
            node.func.attr
            for node in ast.walk(method)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("prune_observations", called)
        core_tree = ast.parse(CORE_FILE.read_text(encoding="utf-8"), filename=str(CORE_FILE))
        core_defs = {node.name for node in core_tree.body if isinstance(node, ast.FunctionDef)}
        self.assertIn("prune_observations", core_defs)

    def test_the_sweep_ignores_the_persist_switch(self):
        method = next(
            node for node in _model_class().body if isinstance(node, ast.FunctionDef) and node.name == MODEL_METHOD
        )
        referenced = {
            node.id for node in ast.walk(method) if isinstance(node, ast.Name)
        } | {
            node.attr for node in ast.walk(method) if isinstance(node, ast.Attribute)
        }
        self.assertNotIn(
            "persistence_enabled",
            referenced,
            "rows written while persistence was on must still age out after it is switched off",
        )

    def test_the_sweep_does_not_raise(self):
        method = next(
            node for node in _model_class().body if isinstance(node, ast.FunctionDef) and node.name == MODEL_METHOD
        )
        self.assertEqual(
            [node for node in ast.walk(method) if isinstance(node, (ast.Raise, ast.Assert))],
            [],
            "the retention sweep must stay fail-open",
        )


class ManifestWiringTest(unittest.TestCase):
    def test_the_data_file_is_loaded_after_the_acl_it_depends_on(self):
        data = list(_manifest().get("data") or [])
        entry = "data/contract_slo_retention_cron.xml"
        self.assertIn(entry, data)
        self.assertLess(data.index("security/ir.model.access.csv"), data.index(entry))

    def test_every_declared_data_file_exists(self):
        for entry in _manifest().get("data") or []:
            path = MODULE / str(entry)
            if path.suffix in (".xml", ".csv"):
                self.assertTrue(path.is_file(), f"declared data file missing: {entry}")


if __name__ == "__main__":
    unittest.main()

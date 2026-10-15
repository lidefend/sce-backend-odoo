# -*- coding: utf-8 -*-
"""Demo BOQ source must be a real file consumed by the native importer.

The ORM test in test_demo_action_roles proves persisted batch identity, native
preview payload, line/source binding, amount and idempotency. These offline
checks pin the input file and prevent reinstating handwritten import results.
"""

import ast
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parents[1]

BOQ_XML = DEMO_ROOT / "data/scenario/s00_min_path/10_project_boq.xml"
PROJECTS_XML = DEMO_ROOT / "data/base/20_projects.xml"
LOADER_PY = DEMO_ROOT / "tools/scenario_loader.py"

BATCH_MODEL = "project.boq.import.batch"
VERSION_MODEL = "project.boq.version"
LINE_MODEL = "project.boq.line"

BATCH_XMLID = "smart_construction_demo.sc_demo_boq_import_batch_001"
VERSION_XMLID = "smart_construction_demo.sc_demo_boq_version_contract_v1"

PREVIEW_SCHEMA = "sc.boq.import.preview.v1"


def _field_text(record, name):
    for field in record.findall("field"):
        if field.get("name") == name:
            return (field.text or "").strip()
    return None


def _field_literal(record, name):
    """Read a field whose value is an eval'd Python literal.

    Json fields must be seeded via the ``eval`` attribute with a dict
    literal: the plain text path makes Odoo store a JSON *string scalar*
    (``jsonb_typeof = 'string'``), and the projection handler's
    ``isinstance(preview, dict)`` check then degrades the snapshot to {}.
    """
    for field in record.findall("field"):
        if field.get("name") == name:
            if field.get("eval"):
                return ast.literal_eval(field.get("eval"))
            return json.loads((field.text or "").strip())
    return None


def _field_ref(record, name):
    for field in record.findall("field"):
        if field.get("name") == name:
            return field.get("ref") or (field.text or "").strip()
    return None


def _records(root, model):
    return [record for record in root.iter("record") if record.get("model") == model]


class TestDemoBoqImportBatchSeed(unittest.TestCase):
    def test_seed_calls_native_import_wrapper_and_creates_no_result_records(self):
        root = ET.parse(BOQ_XML).getroot()
        self.assertFalse(list(root.iter("record")))
        calls = list(root.iter("function"))
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0].get("model"), calls[0].get("name")),
                         ("project.project", "sc_demo_import_boq"))

    def test_uploaded_file_contains_the_declared_business_rows(self):
        import csv
        with (BOQ_XML.parent / "contract_boq.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([r["清单编码"] for r in rows], ["010101", "020202"])
        self.assertEqual(sum(float(r["工程量"]) * float(r["单价"]) for r in rows), 762000)
        self.assertTrue(all(r["单位"] and r["成本项"] for r in rows))

    def test_adapter_uses_public_preflight_before_import(self):
        tree = ast.parse(LOADER_PY.read_text(encoding="utf-8"))
        method = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_import_demo_boq")
        calls = [n for n in ast.walk(method) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        preflight = [n for n in calls if n.func.attr == "action_preflight"]
        imports = [n for n in calls if n.func.attr == "action_import"]
        self.assertEqual(len(preflight), 1)
        self.assertEqual(len(imports), 1)
        self.assertLess(preflight[0].lineno, imports[0].lineno)
        self.assertFalse([n for n in calls if n.func.attr.startswith("_parse")])


class TestDemoBoqVisibilitySeed(unittest.TestCase):
    """Pin the record-rule visibility wiring for the demo BOQ batch.

    The ``project.boq.import.batch`` "project member scope" record rule
    grants read access only to the project manager (``project_id.user_id``)
    or message followers. Without the wiring below, demo users see zero
    batches and the dashboard boq_preview block renders empty even though
    the seed exists.

    Both wirings must live in the scenario loader hook, not in the seed
    XML: ``data/base/20_projects.xml`` loads before ``sc_demo_users.xml``
    in the manifest data order, so a ``user_id`` ref in the project seed
    fails module install with Error 255; ``<function>`` tags inside
    noupdate data blocks are silently skipped on update.
    """

    def test_demo_project_seed_has_no_user_id_ref(self):
        """Pin the manifest load-order trap.

        20_projects.xml loads before sc_demo_users.xml; a user_id ref to
        the demo PM would abort module installation.
        """
        root = ET.parse(PROJECTS_XML).getroot()
        projects = [
            record
            for record in root.iter("record")
            if record.get("model") == "project.project"
            and record.get("id") == "sc_demo_project_001"
        ]
        self.assertEqual(len(projects), 1, "base seed must define sc_demo_project_001")
        self.assertIsNone(
            _field_ref(projects[0], "user_id"),
            "20_projects.xml must NOT assign user_id: it loads before "
            "sc_demo_users.xml (manifest data order) and the ref would "
            "fail module install with Error 255; PM assignment belongs "
            "to the _ensure_s00_boq_visibility loader hook",
        )

    def test_loader_assigns_demo_pm_and_subscribes_cost_user(self):
        source = LOADER_PY.read_text(encoding="utf-8")
        self.assertIn(
            "def _ensure_s00_boq_visibility(env)",
            source,
            "scenario_loader must define _ensure_s00_boq_visibility",
        )
        self.assertIn(
            'if scenario == "s00_min_path":\n        _ensure_s00_boq_visibility(env)',
            source,
            "load_scenario must invoke _ensure_s00_boq_visibility for s00_min_path",
        )
        self.assertIn(
            "smart_construction_demo.user_sc_pm_01",
            source,
            "the visibility hook must assign the demo PM as project manager",
        )
        self.assertIn(
            'project.write({"user_id": pm_user.id})',
            source,
            "the visibility hook must write user_id for the PM assignment",
        )
        self.assertIn(
            "smart_construction_demo.user_sc_cost_01",
            source,
            "the visibility hook must reference the demo cost user",
        )
        self.assertIn(
            "message_subscribe(partner_ids=[partner.id])",
            source,
            "the visibility hook must subscribe through message_subscribe",
        )


if __name__ == "__main__":
    unittest.main()

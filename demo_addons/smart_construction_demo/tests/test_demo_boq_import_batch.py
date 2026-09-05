# -*- coding: utf-8 -*-
"""Hermetic guard: demo BOQ import batch seed discipline.

The project dashboard boq_preview block (ProjectBoqPreviewBuilder) and the
``project.boq.import.preview.fetch`` intent both key off
``project.boq.import.batch`` rows for the demo project. The s00 demo seed
must therefore keep one coherent import batch:

- required identity fields (filename / file_digest / parser_schema) present,
- ``preview_payload`` parses as the wizard-shaped ``sc.boq.import.preview.v1``
  snapshot (numeric counts + amount) so the frontend projection renders the
  ready state instead of the missing-payload degradation,
- row/item counts and amount agree with the demo BOQ lines that reference the
  batch (amount == sum(quantity * price) of linked lines),
- batch / lines / version stay inside one project scope (model constraint
  ``_check_project_scope`` / ``_check_structure_binding``),
- batch state stays ``imported`` — publishing a batch is a side effect of the
  version publish action, and the demo version remains a draft.

This test parses the scenario XML statically (no Odoo runtime), mirroring
``test_demo_funding_baseline_lifecycle``.
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
    def setUp(self):
        self.root = ET.parse(BOQ_XML).getroot()
        self.batches = _records(self.root, BATCH_MODEL)
        self.lines = _records(self.root, LINE_MODEL)
        self.versions = _records(self.root, VERSION_MODEL)

    def test_single_demo_import_batch_exists(self):
        self.assertEqual(
            len(self.batches),
            1,
            "s00 must seed exactly one project.boq.import.batch record",
        )
        batch = self.batches[0]
        self.assertEqual(batch.get("id"), BATCH_XMLID.split(".")[-1])

    def test_batch_identity_fields_present(self):
        batch = self.batches[0]
        for field in ("filename", "file_digest", "parser_schema"):
            value = _field_text(batch, field)
            self.assertTrue(
                value,
                f"batch#{batch.get('id')}: required field {field} must not be empty",
            )
        digest = _field_text(batch, "file_digest")
        self.assertRegex(
            digest,
            r"^[0-9a-f]{64}$",
            "file_digest must be a 64-hex sha256 string (wizard parity)",
        )

    def test_preview_payload_uses_eval_dict_literal(self):
        """Pin the Json-field seeding trap.

        A plain-text <field name="preview_payload">{...}</field> makes Odoo
        store a JSON string scalar (jsonb_typeof='string'); the projection
        handler then degrades the snapshot to {}. The seed must therefore
        carry the dict via the eval attribute.
        """
        batch = self.batches[0]
        for field in batch.findall("field"):
            if field.get("name") == "preview_payload":
                self.assertTrue(
                    field.get("eval"),
                    "preview_payload must be seeded via eval= with a dict "
                    "literal (plain text double-encodes as a JSON string)",
                )
                return
        self.fail("preview_payload field not found")

    def test_batch_state_stays_imported(self):
        batch = self.batches[0]
        state = _field_text(batch, "state")
        self.assertEqual(
            state,
            "imported",
            "demo batch must stay imported; advancing to published is a "
            "version publish side effect and the demo version is a draft",
        )
        version = self.versions[0]
        version_state = _field_text(version, "state")
        self.assertIsNone(
            version_state,
            "demo version record must not set state (draft default; "
            "publish belongs to the governed version actions)",
        )

    def test_batch_scope_matches_version_and_lines(self):
        batch = self.batches[0]
        batch_project = _field_ref(batch, "project_id")
        batch_version = _field_ref(batch, "version_id")
        self.assertEqual(batch_version, VERSION_XMLID)
        for line in self.lines:
            self.assertEqual(
                _field_ref(line, "version_id"),
                batch_version,
                f"line#{line.get('id')}: must reference the batch version",
            )
            self.assertEqual(
                _field_ref(line, "project_id"),
                batch_project,
                f"line#{line.get('id')}: must stay inside the batch project scope",
            )

    def test_linked_lines_reference_batch(self):
        batch = self.batches[0]
        batch_id = batch.get("id")
        linked = [
            line
            for line in self.lines
            if _field_ref(line, "import_batch_id")
            == f"smart_construction_demo.{batch_id}"
        ]
        self.assertEqual(
            len(linked),
            len(self.lines),
            "every demo BOQ line must reference the demo import batch",
        )

    def test_counts_and_amount_agree_with_lines(self):
        batch = self.batches[0]
        linked = self.lines
        expected_rows = len(linked)
        expected_amount = sum(
            float(_field_text(line, "quantity")) * float(_field_text(line, "price"))
            for line in linked
        )
        self.assertEqual(int(_field_text(batch, "row_count")), expected_rows)
        self.assertEqual(int(_field_text(batch, "item_count")), expected_rows)
        payload = _field_literal(batch, "preview_payload")
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("schema"), PREVIEW_SCHEMA)
        self.assertEqual(int(payload.get("row_count")), expected_rows)
        self.assertEqual(int(payload.get("item_count")), expected_rows)
        self.assertAlmostEqual(
            float(payload.get("amount")),
            expected_amount,
            places=2,
            msg="preview_payload.amount must equal sum(quantity * price) of linked lines",
        )
        for key in ("skipped_count", "warning_count"):
            self.assertEqual(
                int(payload.get(key, 0)),
                0,
                f"demo snapshot {key} must stay 0 (clean import)",
            )
        self.assertEqual(
            payload.get("source_diagnostics"),
            [],
            "demo snapshot must carry no diagnostics",
        )


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

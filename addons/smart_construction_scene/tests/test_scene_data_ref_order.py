# -*- coding: utf-8 -*-
"""Fresh-install data-ordering guard for smart_construction_scene.

Simulates Odoo's sequential processing of the module's data XML files (in
manifest order) and asserts that every module-local ``ref=`` resolves at the
moment its record is processed.

Rationale: on an existing database the upgrade path tolerates forward
references because the referenced xmlids already exist in ``ir_model_data``.
A fresh-database install, however, processes records strictly in file order
and fails with ``ValueError: External ID not found in the system`` — exactly
what the isolated demo-tenant rehearsal exposed on 2026-09-05 for
``sc_scene_portal_shortcuts`` / ``sc_scene_portal_notifications`` (their
``sc.scene`` base records were missing from ``sc_scene_orchestration.xml``
while ``sc_scene_layout.xml`` referenced them from earlier ``sc.scene.version``
records).

Run directly (repo convention, no Odoo runtime required)::

    python addons/smart_construction_scene/tests/test_scene_data_ref_order.py
"""
import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCENE_DIR = Path(__file__).resolve().parents[1]
MODULE = "smart_construction_scene"


def _manifest_data_files():
    manifest = ast.literal_eval((SCENE_DIR / "__manifest__.py").read_text(encoding="utf-8"))
    return [d for d in manifest.get("data", []) if d.endswith(".xml")]


def _iter_records(path: Path):
    tree = ET.parse(path)
    for rec in tree.iter("record"):
        yield rec


class TestSceneDataRefOrder(unittest.TestCase):
    def test_all_module_local_refs_resolve_in_load_order(self):
        defined = set()
        problems = []
        for rel in _manifest_data_files():
            for rec in _iter_records(SCENE_DIR / rel):
                rid = rec.get("id")
                if rid:
                    defined.add(rid)
                for field in rec:
                    ref = field.get("ref")
                    if not ref:
                        continue
                    mod, _, xid = ref.partition(".")
                    if mod != MODULE:
                        # bare module-local ref like ref="sc_scene_portal_dashboard"
                        if "." in ref:
                            continue  # cross-module ref, out of scope
                        xid = ref
                    if xid not in defined:
                        problems.append(
                            "%s: record id=%s field=%s ref=%s not defined yet"
                            % (rel, rid, field.get("name"), ref)
                        )
        self.assertEqual(
            problems,
            [],
            "Forward/missing module-local ref(s) would break a fresh-database "
            "install of %s:\n%s" % (MODULE, "\n".join(problems)),
        )

    def test_portal_shortcuts_and_notifications_have_base_scene_records(self):
        orchestration = (SCENE_DIR / "data" / "sc_scene_orchestration.xml").read_text(encoding="utf-8")
        for scene_id in ("sc_scene_portal_shortcuts", "sc_scene_portal_notifications"):
            self.assertIn(
                '<record id="%s" model="sc.scene">' % scene_id,
                orchestration,
                "%s must have a base sc.scene record in sc_scene_orchestration.xml "
                "(loaded before sc_scene_layout.xml) so the layout version record "
                "does not forward-reference an undefined xmlid on fresh installs"
                % scene_id,
            )


if __name__ == "__main__":
    unittest.main()

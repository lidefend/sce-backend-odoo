import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "platform_capability_explorer_contributions.py"
)
SPEC = importlib.util.spec_from_file_location(
    "platform_capability_explorer_contributions_under_test",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ReleaseCenterContributionTests(unittest.TestCase):
    def test_release_center_maps_declared_native_menu_xmlid_without_name_guessing(self):
        source = {
            "product_contract": {
                "centers": [
                    {
                        "key": "project_management",
                        "name": "项目管理",
                        "sequence": 10,
                        "level_two": [
                            {
                                "binding": {
                                    "menu_xmlid": "smart_construction_core.menu_project_ledger"
                                }
                            }
                        ],
                    }
                ]
            }
        }
        centers, conflicts = MODULE._release_center_map(source)
        self.assertEqual(conflicts, [])
        self.assertEqual(
            centers["smart_construction_core.menu_project_ledger"]["key"],
            "project_management",
        )
        self.assertEqual(
            centers["smart_construction_core.menu_project_ledger"]["source"],
            MODULE.RELEASE_CENTER_SOURCE,
        )

    def test_conflicting_center_claims_do_not_overwrite_an_authority(self):
        leaf = {"binding": {"menu_xmlid": "smart_construction_core.menu_same"}}
        source = {
            "product_contract": {
                "centers": [
                    {
                        "key": "center.a",
                        "name": "A",
                        "sequence": 10,
                        "level_two": [leaf],
                    },
                    {
                        "key": "center.b",
                        "name": "B",
                        "sequence": 20,
                        "level_two": [leaf],
                    },
                ]
            }
        }
        centers, conflicts = MODULE._release_center_map(source)
        self.assertNotIn("smart_construction_core.menu_same", centers)
        self.assertEqual(conflicts[0]["kind"], "release_center")
        self.assertEqual(conflicts[0]["center_keys"], ["center.a", "center.b"])

    def test_published_center_map_uses_active_policy_identity_and_version(self):
        projection = {
            "release_centers": {
                "smart_construction_core.menu_project_ledger": {
                    "center_key": "construction.center.project",
                    "center_label": "项目交付中心",
                    "center_sequence": 25,
                    "product_key": "construction.standard",
                    "snapshot_id": 17,
                    "version": "center-v2",
                }
            }
        }
        centers, conflicts = MODULE._published_release_center_map(projection)
        self.assertEqual(conflicts, [])
        center = centers["smart_construction_core.menu_project_ledger"]
        self.assertEqual(center["key"], "construction.center.project")
        self.assertEqual(center["label"], "项目交付中心")
        self.assertEqual(center["sequence"], 25)
        self.assertEqual(center["snapshot_id"], 17)
        self.assertEqual(center["version"], "center-v2")
        self.assertEqual(center["source"], "published_product_policy")

    def test_explorer_release_authority_never_opens_a_second_database(self):
        called = []
        projection = MODULE.load_capability_explorer_release_projection(
            SimpleNamespace(cr=SimpleNamespace(dbname="sc_tenant")),
            platform_database_resolver=lambda env: "sc_platform_control",
            projection_loader=lambda env: called.append(True) or {},
        )
        self.assertEqual(called, [])
        self.assertFalse(projection["authority_available"])
        self.assertEqual(projection["authority_reason"], "PLATFORM_RELEASE_DB_ISOLATED")
        self.assertEqual(projection["menu_release_states"], {})
        self.assertTrue(
            all(row["applied"] is False for row in projection["snapshots"])
        )

    def test_explorer_release_authority_reads_only_when_colocated(self):
        projection = MODULE.load_capability_explorer_release_projection(
            SimpleNamespace(cr=SimpleNamespace(dbname="sc_demo")),
            platform_database_resolver=lambda env: "sc_demo",
            projection_loader=lambda env: {
                "menu_release_states": {"menu.a": "released"},
                "snapshots": [],
                "standard_applied": True,
                "preview_applied": False,
            },
        )
        self.assertTrue(projection["authority_available"])
        self.assertEqual(projection["authority_reason"], "OK")
        self.assertEqual(projection["menu_release_states"], {"menu.a": "released"})

    def test_explorer_release_authority_is_unknown_when_resolution_fails(self):
        projection = MODULE.load_capability_explorer_release_projection(
            SimpleNamespace(cr=SimpleNamespace(dbname="sc_tenant")),
            platform_database_resolver=lambda env: (_ for _ in ()).throw(
                RuntimeError("unavailable")
            ),
            projection_loader=lambda env: self.fail("cross-database loader called"),
        )
        self.assertFalse(projection["authority_available"])
        self.assertEqual(
            projection["authority_reason"],
            "PLATFORM_RELEASE_DATABASE_UNRESOLVED",
        )

    def test_product_qualification_uses_active_snapshot_evidence(self):
        qualification = MODULE._product_qualifications(
            ["smart_construction_core.menu_sc_project_project"],
            {
                "authority_available": True,
                "menu_release_states_by_product": {
                    "construction.standard": {
                        "smart_construction_core.menu_sc_project_project": "released"
                    },
                    "construction.preview": {},
                },
                "snapshots": [
                    {
                        "product_key": "construction.standard",
                        "applied": True,
                        "snapshot_id": 17,
                        "version": "v17",
                        "fingerprint": "sha256:v17",
                    },
                    {
                        "product_key": "construction.preview",
                        "applied": False,
                        "snapshot_id": 0,
                        "version": "",
                        "fingerprint": "",
                        "reason": "ACTIVE_RELEASE_SNAPSHOT_NOT_FOUND",
                    },
                ],
            },
        )["smart_construction_core.menu_sc_project_project"]
        self.assertEqual(qualification["standard"], "qualified")
        self.assertEqual(qualification["preview"], "not_qualified")
        evidence = {
            row["product_key"]: row for row in qualification["evidence"]
        }
        self.assertTrue(evidence["construction.standard"]["qualified"])
        self.assertEqual(evidence["construction.standard"]["snapshot_id"], 17)
        self.assertEqual(evidence["construction.standard"]["version"], "v17")
        self.assertFalse(evidence["construction.preview"]["qualified"])

    def test_product_qualification_keeps_full_product_keys_independent(self):
        qualification = MODULE._product_qualifications(
            ["smart_construction_core.menu_sc_project_project"],
            {
                "authority_available": True,
                "selected_product_key": "platform.standard",
                "menu_release_states_by_product": {
                    "construction.standard": {
                        "smart_construction_core.menu_sc_project_project": "released"
                    },
                    "platform.standard": {},
                },
                "snapshots": [
                    {
                        "product_key": "construction.standard",
                        "applied": True,
                        "snapshot_id": 17,
                        "version": "v17",
                    },
                    {
                        "product_key": "platform.standard",
                        "applied": True,
                        "snapshot_id": 31,
                        "version": "v31",
                    },
                ],
            },
            product_keys=["construction.standard", "platform.standard"],
        )["smart_construction_core.menu_sc_project_project"]
        self.assertEqual(
            qualification["by_product"],
            {
                "construction.standard": "qualified",
                "platform.standard": "not_qualified",
            },
        )
        self.assertEqual(qualification["selected_status"], "not_qualified")
        self.assertEqual(qualification["standard"], "qualified")
        self.assertEqual(qualification["preview"], "not_verified")

    def test_non_construction_snapshot_establishes_release_authority(self):
        projection = MODULE.load_capability_explorer_release_projection(
            SimpleNamespace(cr=SimpleNamespace(dbname="sc_demo")),
            platform_database_resolver=lambda env: "sc_demo",
            projection_loader=lambda env, product_keys=None: {
                "snapshots": [{
                    "product_key": "platform.standard",
                    "applied": True,
                    "snapshot_id": 31,
                }],
            },
            product_keys=["platform.standard"],
        )
        self.assertTrue(projection["authority_available"])
        self.assertEqual(projection["authority_reason"], "OK")

    def test_menu_release_without_active_product_evidence_is_not_qualified(self):
        qualification = MODULE._product_qualifications(
            ["smart_construction_core.menu_sc_project_project"],
            {
                "authority_available": False,
                "menu_release_states_by_product": {},
                "snapshots": [],
                "authority_reason": "PLATFORM_RELEASE_DB_ISOLATED",
            },
        )["smart_construction_core.menu_sc_project_project"]
        self.assertEqual(qualification["standard"], "not_verified")
        self.assertEqual(qualification["reason_code"], "PLATFORM_RELEASE_DB_ISOLATED")

    def test_contribution_is_orm_read_only(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in (".write(", ".create(", ".unlink(", ".sudo().create("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn("get_platform_capability_explorer_scope", source)
        self.assertIn("get_platform_capability_explorer_contributions", source)
        self.assertNotIn("Registry(", source)
        self.assertNotIn("SUPERUSER_ID", source)


if __name__ == "__main__":
    unittest.main()

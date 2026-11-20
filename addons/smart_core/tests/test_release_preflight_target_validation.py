# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]


def _load_module(module_name: str, relative_path: str):
    target = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _install_stubs():
    odoo = sys.modules.setdefault("odoo", types.ModuleType("odoo"))
    odoo.SUPERUSER_ID = 1
    odoo.api = SimpleNamespace(Environment=lambda cr, uid, ctx: None)
    odoo.fields = SimpleNamespace(Datetime=SimpleNamespace(now=lambda: "2026-01-01 00:00:00"))
    sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
    modules_pkg = sys.modules.setdefault("odoo.modules", types.ModuleType("odoo.modules"))
    registry_mod = types.ModuleType("odoo.modules.registry")
    registry_mod.Registry = lambda db: None
    sys.modules["odoo.modules.registry"] = registry_mod
    modules_pkg.registry = registry_mod

    smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
    smart_core_pkg.__path__ = [str(ROOT / "addons/smart_core")]
    core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
    core_pkg.__path__ = [str(ROOT / "addons/smart_core/core")]
    delivery_pkg = sys.modules.setdefault("odoo.addons.smart_core.delivery", types.ModuleType("odoo.addons.smart_core.delivery"))
    delivery_pkg.__path__ = [str(ROOT / "addons/smart_core/delivery")]

    _load_module(
        "odoo.addons.smart_core.core.source_authority",
        "addons/smart_core/core/source_authority.py",
    )

    delivery_engine_stub = types.ModuleType("odoo.addons.smart_core.delivery.delivery_engine")
    delivery_engine_stub.DeliveryEngine = type("DeliveryEngine", (), {"__init__": lambda self, env: None})
    sys.modules["odoo.addons.smart_core.delivery.delivery_engine"] = delivery_engine_stub

    promotion_stub = types.ModuleType("odoo.addons.smart_core.delivery.edition_release_snapshot_promotion_service")
    promotion_stub.EditionReleaseSnapshotPromotionService = type(
        "EditionReleaseSnapshotPromotionService",
        (),
        {"__init__": lambda self, env: None},
    )
    sys.modules["odoo.addons.smart_core.delivery.edition_release_snapshot_promotion_service"] = promotion_stub

    policy_stub = types.ModuleType("odoo.addons.smart_core.delivery.product_policy_service")
    policy_stub.ProductPolicyService = type("ProductPolicyService", (), {"__init__": lambda self, env: None})
    sys.modules["odoo.addons.smart_core.delivery.product_policy_service"] = policy_stub


_install_stubs()
TARGET = _load_module(
    "odoo.addons.smart_core.delivery.edition_release_snapshot_service",
    "addons/smart_core/delivery/edition_release_snapshot_service.py",
)
COMPOSITION = sys.modules[
    "odoo.addons.smart_core.delivery.product_scene_composition"
]


class TestReleasePreflightTargetValidation(unittest.TestCase):
    def test_business_scene_composition_changes_draft_identity(self):
        service = TARGET.EditionReleaseSnapshotService(env={})
        policy = {
            "product_key": "construction.standard",
            "state": "stable",
            "access_level": "public",
            "allowed_role_codes": [],
            "menu_groups": [],
            "scenes": [],
            "capabilities": [],
        }
        first = {
            "schema": "construction.scenario_product_surface.v2",
            "scenarios": [{"key": "project", "name": "Project", "sequence": 10}],
        }
        second = deepcopy(first)
        second["scenarios"][0]["name"] = "Project renamed"

        with patch.object(COMPOSITION, "normalize_product_policy_for_env", side_effect=lambda env, row: deepcopy(row)):
            with patch.object(COMPOSITION, "call_extension_hook_first", return_value=first):
                first_policy = service._compose_policy_draft(policy)
            with patch.object(COMPOSITION, "call_extension_hook_first", return_value=second):
                second_policy = service._compose_policy_draft(policy)

        self.assertEqual(
            first_policy["business_scene_composition"],
            first,
        )
        self.assertNotEqual(
            TARGET.EditionReleaseSnapshotService._draft_fingerprint(
                policy=first_policy,
                pages=[],
            ),
            TARGET.EditionReleaseSnapshotService._draft_fingerprint(
                policy=second_policy,
                pages=[],
            ),
        )

    def test_freeze_surface_carries_published_scene_composition(self):
        composition = {
            "schema": "construction.scenario_product_surface.v2",
            "centers": [{
                "key": "construction.center.project",
                "name": "Project",
                "sequence": 20,
                "scenarios": ["project"],
            }],
            "source_db": "product_db",
            "scenarios": [{
                "key": "project",
                "name": "Project",
                "active": True,
                "sequence": 0,
                "bindings": [{
                    "menu_key": "menu:7",
                    "menu_id": 7,
                    "center_key": "construction.center.project",
                    "intent": "view",
                    "sequence": 0,
                }],
            }],
        }
        policy = {
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
            "state": "stable",
            "access_level": "public",
            "allowed_role_codes": [],
            "label": "Construction",
            "version": "v1",
            "menu_groups": [],
            "scenes": [],
            "capabilities": [],
        }
        action = SimpleNamespace(res_model="project.project")
        menu = SimpleNamespace(
            id=7,
            _name="ir.ui.menu",
            action=action,
            get_external_id=lambda: {},
        )
        menu_model = SimpleNamespace(
            sudo=lambda: menu_model,
            browse=lambda menu_id: SimpleNamespace(
                exists=lambda: menu if menu_id == 7 else [],
            ),
        )
        class Env:
            cr = SimpleNamespace(dbname="product_db")

            def __getitem__(self, model_name):
                if model_name == "ir.ui.menu":
                    return menu_model
                raise KeyError(model_name)

            def ref(self, *args, **kwargs):
                return None

        env = Env()
        service = TARGET.EditionReleaseSnapshotService(env=env)
        service.policy_service.resolve_policy_identity = lambda **kwargs: (
            "construction.standard",
            "construction",
            "standard",
        )
        service.policy_service.get_policy = lambda **kwargs: deepcopy(policy)
        service.policy_service.center_index = lambda payload: {
            "centers": [],
            "by_menu": {},
        }
        service._default_requested_role_context = lambda **kwargs: {
            "role_code": "owner",
            "source": "explicit",
        }
        service._model_registered = lambda model_name: model_name in {
            "ir.ui.menu",
            "project.project",
        }
        service.delivery_engine = SimpleNamespace(
            build=lambda **kwargs: {
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
                "nav": [],
                "capabilities": [],
                "scenes": [],
                "meta": {},
            }
        )

        with patch.object(COMPOSITION, "normalize_product_policy_for_env", side_effect=lambda env, row: deepcopy(row)), patch.object(
            COMPOSITION,
            "call_extension_hook_first",
            return_value=composition,
        ):
            payload = service.build_freeze_surface(
                product_key="construction.standard",
            )

        self.assertEqual(
            payload["policy"]["business_scene_composition"],
            composition,
        )
        self.assertEqual(payload["business_scene_composition"], composition)

    def test_freeze_accepts_valid_scene_composition_without_legacy_pages(self):
        composition = {
            "schema": "construction.scenario_product_surface.v2",
            "centers": [{
                "key": "construction.center.project",
                "name": "Project",
                "sequence": 20,
                "scenarios": ["project"],
            }],
            "source_db": "product_db",
            "scenarios": [{
                "key": "project",
                "name": "Project",
                "active": True,
                "sequence": 0,
                "bindings": [{
                    "menu_key": "menu:7",
                    "menu_id": 7,
                    "center_key": "construction.center.project",
                    "intent": "view",
                    "sequence": 0,
                }],
            }],
        }
        policy = {
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
            "state": "stable",
            "access_level": "public",
            "allowed_role_codes": [],
            "label": "Construction",
            "version": "v1",
            "menu_groups": [],
            "scenes": [],
            "capabilities": [],
        }

        class SnapshotRecord:
            id = 91

            def __init__(self, values):
                self.values = values

            def to_runtime_dict(self):
                return {
                    "id": self.id,
                    "product_key": self.values["product_key"],
                    "version": self.values["version"],
                    "snapshot_json": self.values["snapshot_json"],
                    "meta_json": self.values["meta_json"],
                }

        class SnapshotModel:
            def __init__(self):
                self.created = []

            def search(self, *args, **kwargs):
                return []

            def create(self, values):
                record = SnapshotRecord(deepcopy(values))
                self.created.append(record)
                return record

        action = SimpleNamespace(res_model="project.project")
        menu = SimpleNamespace(
            id=7,
            _name="ir.ui.menu",
            action=action,
            get_external_id=lambda: {},
        )
        menu_model = SimpleNamespace(
            sudo=lambda: menu_model,
            browse=lambda menu_id: SimpleNamespace(
                exists=lambda: menu if menu_id == 7 else [],
            ),
        )

        class Env:
            cr = SimpleNamespace(dbname="product_db")

            def __getitem__(self, model_name):
                if model_name == "ir.ui.menu":
                    return menu_model
                raise KeyError(model_name)

            def ref(self, *args, **kwargs):
                return None

        service = TARGET.EditionReleaseSnapshotService(env=Env())
        model = SnapshotModel()
        service._model = lambda: model
        service._model_registered = lambda model_name: model_name in {
            "ir.ui.menu",
            "project.project",
        }
        service.now = lambda: "2026-11-20 00:00:00"
        service.policy_service.resolve_policy_identity = lambda **kwargs: (
            "construction.standard",
            "construction",
            "standard",
        )
        service.policy_service.get_policy = lambda **kwargs: deepcopy(policy)
        service.policy_service.center_index = lambda payload: {
            "centers": [],
            "by_menu": {},
        }
        service._default_requested_role_context = lambda **kwargs: {
            "role_code": "owner",
            "source": "explicit",
        }
        service.delivery_engine = SimpleNamespace(
            build=lambda **kwargs: {
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
                "nav": [],
                "capabilities": [],
                "scenes": [],
                "meta": {},
            }
        )
        service.promotion_service = SimpleNamespace(
            promote_to_approved=lambda record_id, **kwargs: {},
            promote_to_released=lambda record_id, **kwargs: model.created[0].to_runtime_dict(),
        )

        with patch.object(COMPOSITION, "normalize_product_policy_for_env", side_effect=lambda env, row: deepcopy(row)), patch.object(
            COMPOSITION,
            "call_extension_hook_first",
            return_value=composition,
        ):
            result = service.freeze_release_surface(
                product_key="construction.standard",
                version="v2",
            )

        self.assertEqual(result["id"], 91)
        self.assertEqual(len(model.created), 1)
        frozen_policy = model.created[0].values["snapshot_json"]["policy"]
        self.assertEqual(
            frozen_policy["business_scene_composition"],
            composition,
        )
        self.assertEqual(frozen_policy["menu_groups"], [])

    def test_numeric_scene_reference_rejects_cross_database_source(self):
        class Env:
            cr = SimpleNamespace(dbname="execution_db")

            def __getitem__(self, model_name):
                raise KeyError(model_name)

        service = TARGET.EditionReleaseSnapshotService(env=Env())
        service._model_registered = lambda model_name: model_name == "ir.ui.menu"

        check = service._business_scene_composition_check({
            "business_scene_composition": {
                "schema": "construction.scenario_product_surface.v2",
                "centers": [{
                    "key": "construction.center.project",
                    "name": "Project",
                    "sequence": 20,
                    "scenarios": ["project"],
                }],
                "source_db": "catalog_db",
                "scenarios": [{
                    "key": "project",
                    "active": True,
                    "bindings": [{
                        "menu_key": "menu:21",
                        "menu_id": 21,
                        "center_key": "construction.center.project",
                        "source_db": "catalog_db",
                    }],
                }],
            },
        })

        self.assertTrue(check["blocking"])
        self.assertEqual(check["issues"][0]["code"], "BUSINESS_SCENE_MENU_UNRESOLVED")

    def test_cross_database_stable_xmlid_uses_source_validation(self):
        class Env:
            cr = SimpleNamespace(dbname="sc_platform_control")
            context = {}

            def __getitem__(self, model_name):
                raise KeyError(model_name)

        service = TARGET.EditionReleaseSnapshotService(env=Env())
        service._model_registered = lambda model_name: model_name == "ir.ui.menu"
        check = service._business_scene_composition_check(
            {
                "business_scene_composition": {
                    "schema": "construction.scenario_product_surface.v2",
                    "centers": [{
                        "key": "construction.center.project",
                        "name": "Project",
                        "sequence": 20,
                        "scenarios": ["project.initiation"],
                    }],
                    "source_db": "sc_dev_demo",
                    "scenarios": [{
                        "key": "project.initiation",
                        "active": True,
                        "bindings": [{
                            "menu_key": "smart_construction_core.menu_sc_project_initiation",
                            "center_key": "construction.center.project",
                            "source_db": "sc_dev_demo",
                        }],
                    }],
                },
            },
            published_pages=[{
                "menu_xmlid": "smart_construction_core.menu_sc_project_initiation",
                "scene_key": "project.initiation",
                "route": "",
                "action_id": 0,
            }],
        )
        self.assertFalse(check["blocking"], check["issues"])
        self.assertEqual(check["ready_binding_count"], 1)

    def test_actionless_scene_entry_is_a_valid_business_composition_page(self):
        menu = SimpleNamespace(
            id=10,
            action=False,
            _name="ir.ui.menu",
            get_external_id=lambda: {10: "smart_construction_core.menu_sc_workspace_home"},
        )
        env = SimpleNamespace(
            cr=SimpleNamespace(dbname="sc_dev_demo"),
            context={},
            ref=lambda xmlid, raise_if_not_found=False: menu,
        )
        service = TARGET.EditionReleaseSnapshotService(env=env)
        service._model_registered = lambda model_name: model_name == "ir.ui.menu"
        check = service._business_scene_composition_check(
            {
                "business_scene_composition": {
                    "schema": "construction.scenario_product_surface.v2",
                    "centers": [{
                        "key": "workspace.home.workbench",
                        "name": "Workbench",
                        "sequence": 10,
                        "scenarios": ["work.my_queue"],
                    }],
                    "source_db": "sc_dev_demo",
                    "scenarios": [{
                        "key": "work.my_queue",
                        "active": True,
                        "bindings": [{
                            "menu_key": "smart_construction_core.menu_sc_workspace_home",
                            "menu_id": 10,
                            "center_key": "workspace.home.workbench",
                            "source_db": "sc_dev_demo",
                        }],
                    }],
                },
            },
            published_pages=[{
                "menu_xmlid": "smart_construction_core.menu_sc_workspace_home",
                "scene_key": "workspace.home",
                "route": "",
                "action_id": 0,
            }],
        )
        self.assertFalse(check["blocking"], check["issues"])
        self.assertEqual(check["ready_binding_count"], 1)

    def test_release_requires_every_published_page_to_belong_to_a_scenario(self):
        service = TARGET.EditionReleaseSnapshotService(env={})
        check = service._business_scene_composition_check(
            {
                "business_scene_composition": {
                    "schema": "construction.scenario_product_surface.v2",
                    "centers": [{
                        "key": "construction.center.project",
                        "name": "Project",
                        "sequence": 20,
                        "scenarios": ["project.management"],
                    }],
                    "source_db": "product_db",
                    "scenarios": [{
                        "key": "project.management",
                        "active": True,
                        "bindings": [{
                            "menu_key": "menu.project",
                            "menu_id": 10,
                            "center_key": "construction.center.project",
                            "source_db": "product_db",
                        }],
                    }],
                },
            },
            published_pages=[
                {"menu_xmlid": "menu.project"},
                {"menu_xmlid": "menu.unassigned"},
            ],
        )

        self.assertTrue(check["blocking"])
        self.assertEqual(check["published_page_count"], 2)
        self.assertEqual(check["scenario_bound_page_count"], 1)
        self.assertEqual(check["unassigned_page_count"], 1)
        self.assertIn(
            "BUSINESS_SCENE_PAGE_UNASSIGNED",
            [row["code"] for row in check["issues"]],
        )

    def test_action_menu_with_fake_scene_key_blocks_release(self):
        service = TARGET.EditionReleaseSnapshotService(env={})
        check = service._target_integrity_check(
            [
                {
                    "page_key": "smart_construction_core.menu_sc_workbench_my_todo_fact",
                    "label": "我的待办",
                    "route": "/a/640?menu_id=471",
                    "scene_key": "smart_construction_core.menu_sc_workbench_my_todo_fact",
                    "menu_id": 471,
                    "action_id": 640,
                    "menu_xmlid": "smart_construction_core.menu_sc_workbench_my_todo_fact",
                    "res_model": "sc.workbench.item",
                }
            ]
        )

        self.assertTrue(check.get("blocking"))
        self.assertEqual(check.get("status"), "fail")
        self.assertEqual(((check.get("issues") or [{}])[0]).get("code"), "ACTION_MENU_HAS_SCENE_KEY")

    def test_action_menu_with_compatibility_target_passes(self):
        service = TARGET.EditionReleaseSnapshotService(env={})
        check = service._target_integrity_check(
            [
                {
                    "page_key": "smart_construction_core.menu_sc_workbench_my_todo_fact",
                    "label": "我的待办",
                    "route": "/a/640?menu_id=471",
                    "scene_key": "",
                    "menu_id": 471,
                    "action_id": 640,
                    "menu_xmlid": "smart_construction_core.menu_sc_workbench_my_todo_fact",
                    "res_model": "sc.workbench.item",
                }
            ]
        )

        self.assertFalse(check.get("blocking"))
        self.assertEqual(check.get("status"), "pass")
        self.assertEqual(check.get("issue_count"), 0)

    def test_action_menu_keeps_action_target_when_scene_association_exists(self):
        service = TARGET.EditionReleaseSnapshotService(env={})
        pages = service._draft_pages_from_policy(
            {
                "product_key": "construction.standard",
                "access_level": "public",
                "menu_groups": [
                    {
                        "group_label": "\u884c\u653f\u4e2d\u5fc3",
                        "menus": [
                            {
                                "page_key": "smart_construction_core.menu_sc_organization_department",
                                "menu_key": "smart_construction_core.menu_sc_organization_department",
                                "menu_xmlid": "smart_construction_core.menu_sc_organization_department",
                                "label": "\u90e8\u95e8\u7ba1\u7406",
                                "route": "/a/802?menu_id=427",
                                "menu_id": 427,
                                "action_id": 802,
                                "res_model": "hr.department",
                                "target_scene_key": "enterprise.department",
                            }
                        ],
                    }
                ],
            }
        )

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].get("scene_key"), "")
        self.assertEqual(pages[0].get("route"), "/a/802?menu_id=427")
        check = service._target_integrity_check(pages)
        self.assertFalse(check.get("blocking"))
        self.assertEqual(check.get("issue_count"), 0)


    def test_declared_scene_entry_projects_scene_key(self):
        service = TARGET.EditionReleaseSnapshotService(env={})
        pages = service._draft_pages_from_policy(
            {
                "product_key": "construction.standard",
                "access_level": "public",
                "menu_groups": [
                    {
                        "group_label": "\u5de5\u4f5c\u53f0",
                        "menus": [
                            {
                                "page_key": "smart_construction_core.menu_sc_workspace_home",
                                "menu_key": "smart_construction_core.menu_sc_workspace_home",
                                "menu_xmlid": "smart_construction_core.menu_sc_workspace_home",
                                "label": "\u89d2\u8272\u9996\u9875",
                                "route": "/s/workspace.home",
                                "menu_id": 1004,
                                "action_id": 0,
                                "entry_target_policy": "scene_entry",
                                "target_scene_key": "workspace.home",
                            }
                        ],
                    }
                ],
            }
        )

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].get("scene_key"), "workspace.home")
        check = service._target_integrity_check(pages)
        self.assertFalse(check.get("blocking"))
        self.assertEqual(check.get("issue_count"), 0)


if __name__ == "__main__":
    unittest.main()

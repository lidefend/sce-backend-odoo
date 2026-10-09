# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


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


class TestReleasePreflightTargetValidation(unittest.TestCase):
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

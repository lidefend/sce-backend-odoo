# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[1] / "core"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


sys.modules.setdefault("odoo", types.ModuleType("odoo"))
sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
smart_core_pkg.__path__ = [str(CORE_DIR.parent)]
core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
core_pkg.__path__ = [str(CORE_DIR)]
smart_core_pkg.core = core_pkg

target = _load_module(
    "odoo.addons.smart_core.core.system_init_payload_builder",
    CORE_DIR / "system_init_payload_builder.py",
)


class TestSystemInitCapabilitySceneSubset(unittest.TestCase):
    def test_includes_authorized_deliverable_capability_targets(self):
        subset = target.SystemInitPayloadBuilder.resolve_startup_scene_subset(
            {
                "default_route": {"scene_key": "workspace.home"},
                "role_surface": {},
                "capabilities": [
                    self._capability("project.read", "allow", "projects.list", "exclusive"),
                    self._capability("project.ledger.read", "readonly", "projects.ledger", "shared"),
                ],
            }
        )

        self.assertEqual(subset, ["workspace.home", "projects.list", "projects.ledger"])

    def test_rejects_denied_locked_placeholder_preview_and_missing_targets(self):
        subset = target.SystemInitPayloadBuilder.resolve_startup_scene_subset(
            {
                "default_route": {"scene_key": "workspace.home"},
                "role_surface": {},
                "capabilities": [
                    self._capability("denied", "deny", "denied.scene", "exclusive"),
                    self._capability("locked", "allow", "locked.scene", "exclusive", state="LOCKED"),
                    self._capability("placeholder", "allow", "placeholder.scene", "placeholder"),
                    self._capability("missing-target", "allow", "", "exclusive"),
                    self._capability("pending", "pending", "pending.scene", "shared", state="PREVIEW"),
                ],
            }
        )

        self.assertEqual(subset, ["workspace.home"])

    def test_deduplicates_capability_role_and_deep_link_targets(self):
        subset = target.SystemInitPayloadBuilder.resolve_startup_scene_subset(
            {
                "default_route": {"scene_key": "workspace.home"},
                "role_surface": {"scene_candidates": ["projects.list", "task.center"]},
                "capabilities": [
                    self._capability("project.read", "allow", "projects.list", "exclusive"),
                    self._capability("project.read.alias", "allow", "projects.list", "shared"),
                ],
            },
            params={"route": "/s/task.center"},
        )

        self.assertEqual(subset, ["workspace.home", "task.center", "projects.list"])

    def test_minimal_payload_adds_scene_targets_without_expanding_capabilities(self):
        allowed = self._capability("project.read", "allow", "projects.list", "exclusive")
        denied = self._capability("project.write", "deny", "projects.admin", "exclusive", state="LOCKED")
        payload = target.SystemInitPayloadBuilder.build_startup_surface(
            {
                "user": {"id": 1},
                "nav": [],
                "nav_meta": {},
                "default_route": {"scene_key": "workspace.home"},
                "intents": [],
                "feature_flags": {},
                "role_surface": {"landing_scene_key": "workspace.home"},
                "capabilities": [allowed, denied],
            }
        )

        self.assertEqual((payload.get("init_meta") or {}).get("scene_subset"), ["workspace.home", "projects.list"])
        self.assertEqual((payload.get("init_meta") or {}).get("scene_subset_count"), 2)
        self.assertEqual(payload.get("capabilities"), [allowed, denied])

    @staticmethod
    def _capability(key, capability_state, target_scene_key, delivery_level, *, state="READY"):
        return {
            "key": key,
            "capability_state": capability_state,
            "state": state,
            "delivery_level": delivery_level,
            "target_scene_key": target_scene_key,
        }


if __name__ == "__main__":
    unittest.main()

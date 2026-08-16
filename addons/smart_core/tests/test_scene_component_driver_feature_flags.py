# -*- coding: utf-8 -*-
import importlib.util
import sys
import unittest
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[1] / "core"
SPEC = importlib.util.spec_from_file_location(
    "scene_component_driver_feature_flags",
    CORE_DIR / "scene_component_driver_feature_flags.py",
)
TARGET = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = TARGET
SPEC.loader.exec_module(TARGET)


class TestSceneComponentDriverFeatureFlags(unittest.TestCase):
    def test_navigation_cannot_self_authorize_scene_driver(self):
        result = TARGET.resolve_system_feature_flags(
            {"ai_enabled": True, TARGET.SCENE_COMPONENT_DRIVER_FLAG: {"enabled": True}},
            {},
        )

        self.assertEqual(result, {"ai_enabled": True})

    def test_valid_entitlement_policy_is_normalized(self):
        result = TARGET.resolve_system_feature_flags(
            {"ai_enabled": True},
            {
                TARGET.SCENE_COMPONENT_DRIVER_FLAG: {
                    "enabled": True,
                    "read_only_only": True,
                    "models": ["res.company", "res.company", ""],
                    "action_ids": ["12", -1, "bad"],
                    "allowed_kits": ["sc-native", "ui5-horizon", "unknown"],
                    "system_default_kit": "ui5-horizon",
                    "organization_default_kit": "unknown",
                    "allow_user_override": True,
                    "untrusted_extra": "drop-me",
                }
            },
        )

        self.assertEqual(
            result[TARGET.SCENE_COMPONENT_DRIVER_FLAG],
            {
                "enabled": True,
                "read_only_only": True,
                "form_modes": [],
                "action_ids": [12],
                "models": ["res.company"],
                "scene_keys": [],
                "allowed_kits": ["sc-native", "ui5-horizon"],
                "system_default_kit": "ui5-horizon",
                "allow_user_override": True,
                "allow_preview_override": False,
            },
        )

    def test_missing_scope_fails_closed(self):
        result = TARGET.resolve_system_feature_flags(
            {},
            {
                TARGET.SCENE_COMPONENT_DRIVER_FLAG: {
                    "enabled": True,
                    "read_only_only": True,
                    "allowed_kits": ["sc-native", "tdesign-modern"],
                }
            },
        )

        self.assertNotIn(TARGET.SCENE_COMPONENT_DRIVER_FLAG, result)

    def test_missing_safe_driver_fails_closed(self):
        result = TARGET.resolve_system_feature_flags(
            {},
            {
                TARGET.SCENE_COMPONENT_DRIVER_FLAG: {
                    "enabled": True,
                    "read_only_only": True,
                    "models": ["res.company"],
                    "allowed_kits": ["ui5-horizon"],
                }
            },
        )

        self.assertNotIn(TARGET.SCENE_COMPONENT_DRIVER_FLAG, result)

    def test_locked_driver_disables_user_override(self):
        result = TARGET.resolve_system_feature_flags(
            {},
            {
                TARGET.SCENE_COMPONENT_DRIVER_FLAG: {
                    "enabled": True,
                    "read_only_only": True,
                    "scene_keys": ["company-directory"],
                    "allowed_kits": ["sc-native", "tdesign-modern"],
                    "locked_kit": "tdesign-modern",
                    "allow_user_override": True,
                }
            },
        )

        policy = result[TARGET.SCENE_COMPONENT_DRIVER_FLAG]
        self.assertEqual(policy["locked_kit"], "tdesign-modern")
        self.assertFalse(policy["allow_user_override"])

    def test_explicit_form_modes_enable_form_without_collection_authority(self):
        result = TARGET.resolve_system_feature_flags(
            {},
            {
                TARGET.SCENE_COMPONENT_DRIVER_FLAG: {
                    "enabled": True,
                    "read_only_only": False,
                    "form_modes": ["create", "edit", "readonly", "unknown", "edit"],
                    "models": ["project.project"],
                    "allowed_kits": ["sc-native", "tdesign-modern"],
                    "system_default_kit": "tdesign-modern",
                }
            },
        )

        policy = result[TARGET.SCENE_COMPONENT_DRIVER_FLAG]
        self.assertFalse(policy["read_only_only"])
        self.assertEqual(policy["form_modes"], ["create", "edit", "readonly"])

    def test_non_readonly_policy_without_explicit_form_modes_fails_closed(self):
        result = TARGET.resolve_system_feature_flags(
            {},
            {
                TARGET.SCENE_COMPONENT_DRIVER_FLAG: {
                    "enabled": True,
                    "read_only_only": False,
                    "models": ["project.project"],
                    "allowed_kits": ["sc-native", "tdesign-modern"],
                }
            },
        )

        self.assertNotIn(TARGET.SCENE_COMPONENT_DRIVER_FLAG, result)


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""Backend scene / surface authority boundary — behavior lock.

This locks the two boundary facts that the backend "场景化" used to blur:

1. The delivery-surface name space (``scene_surface``) is a *closed* channel
   vocabulary, not a business ``scene_key``.  A business scene identity can
   never be delivered as a surface name.
2. Scene entry visibility is decided by the delivery policy in a *fail-closed*
   direction once the policy is enabled: unpublished / internal / demo /
   hidden / role-pruned / capability-blocked scenes are excluded with a
   reason code from the closed ``ALLOWED_REASON_CODES`` vocabulary.

It executes the projection function and reads its result.  It does not assert
that a token merely appears in a source file.
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _install_module(name, **attrs):
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_policy_module():
    _install_module("odoo")
    _install_module("odoo.addons")
    smart_core = _install_module("odoo.addons.smart_core")
    core = _install_module("odoo.addons.smart_core.core")
    utils = _install_module("odoo.addons.smart_core.utils")
    smart_core.__path__ = [str(ROOT)]
    core.__path__ = [str(ROOT / "core")]
    utils.__path__ = [str(ROOT / "utils")]

    _install_module(
        "odoo.addons.smart_core.utils.extension_hooks",
        call_extension_hook_first=lambda *args, **kwargs: None,
    )

    for module_name, relative in (
        ("odoo.addons.smart_core.core.source_authority", "core/source_authority.py"),
    ):
        sys.modules.pop(module_name, None)
        spec = importlib.util.spec_from_file_location(module_name, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

    module_name = "odoo.addons.smart_core.core.scene_delivery_policy"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "core/scene_delivery_policy.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


POLICY = _load_policy_module()


def _published_scene(code, **extra):
    scene = {"code": code, "state": "published", "target": {"route": "/s/%s" % code}}
    scene.update(extra)
    return scene


def _reasons(result):
    return {row["code"]: row["reason_code"] for row in result["excluded"]}


class SceneSurfaceChannelVocabularyTest(unittest.TestCase):
    """A delivery surface is a channel name, never a business scene_key."""

    def test_default_and_legacy_alias_map_to_canonical_channels(self):
        normalizer = POLICY._normalize_surface
        self.assertEqual(normalizer(""), "default")
        self.assertEqual(normalizer("default"), "default")
        # Legacy alias collapses to the canonical channel, not to a scene_key.
        self.assertEqual(normalizer("workspace_pm_v1"), "workspace_default_v1")

    def test_unregistered_surface_is_passed_through_verbatim_known_boundary(self):
        """Registered boundary gap: the surface name space is open.

        An unregistered value (including a business scene_key) survives as the
        surface name, and ``_select_surface_policy`` then returns ``enabled=False``
        so the surface allowlist is not applied.  This is the documented
        fail-open edge; the test pins it so a future change is deliberate.
        """
        normalizer = POLICY._normalize_surface
        self.assertEqual(normalizer("projects.ledger"), "projects.ledger")
        policy = POLICY._select_surface_policy("projects.ledger", env=None)
        self.assertFalse(policy["enabled"])
        self.assertEqual(policy["source"], "none")

    def test_business_scene_key_is_not_an_internal_or_demo_surface(self):
        for scene_key in ("projects.ledger", "finance.center", "workspace.home"):
            self.assertFalse(POLICY._is_internal_surface(scene_key))
            self.assertFalse(POLICY._is_demo_surface(scene_key))


class RegisteredSurfaceAllowlistIsFailClosedTest(unittest.TestCase):
    """A registered surface delivers only its allowlisted scenes."""

    def _filter(self, scenes, surface):
        return POLICY.filter_delivery_scenes(
            scenes,
            surface=surface,
            role_surface={"capabilities": ["a"]},
            enabled=True,
        )

    def test_allowlisted_scene_is_delivered_and_other_scene_is_excluded(self):
        scenes = [_published_scene("workspace.home"), _published_scene("projects.ledger")]
        result = self._filter(scenes, "workspace_default_v1")
        self.assertEqual({s["code"] for s in result["delivery_scenes"]}, {"workspace.home"})
        reasons = _reasons(result)
        self.assertEqual(reasons["projects.ledger"], POLICY.REASON_SCENE_SURFACE_MISMATCH)

    def test_legacy_alias_applies_the_same_registered_allowlist(self):
        scenes = [_published_scene("workspace.home"), _published_scene("projects.ledger")]
        result = self._filter(scenes, "workspace_pm_v1")
        self.assertEqual({s["code"] for s in result["delivery_scenes"]}, {"workspace.home"})
        self.assertEqual(result["meta"]["surface"], "workspace_default_v1")


class SceneDeliveryFailClosedTest(unittest.TestCase):
    """Once enabled, an unentitled scene must not be delivered."""

    def _filter(self, scenes, **kwargs):
        kwargs.setdefault("surface", "default")
        kwargs.setdefault("role_surface", {"capabilities": ["a", "b"]})
        kwargs.setdefault("enabled", True)
        return POLICY.filter_delivery_scenes(scenes, **kwargs)

    def test_enabled_filter_excludes_each_reason_with_closed_vocabulary(self):
        scenes = [
            {"code": "no_code_target"},
            _published_scene("no.target", target={}),
            _published_scene("unpublished", state="draft"),
            _published_scene("hidden", delivery_mode="hidden"),
            _published_scene("internal", delivery_mode="internal"),
            _published_scene("demo", delivery_mode="demo"),
            _published_scene("role_pruned", access={"allowed": False}),
            _published_scene("cap_blocked", required_capabilities=["z"]),
            _published_scene("deep_link", delivery_mode="deep_link_only"),
            _published_scene("delivered"),
        ]
        result = self._filter(scenes)
        reasons = _reasons(result)

        self.assertEqual(reasons["no.target"], POLICY.REASON_SCENE_TARGET_UNRESOLVED)
        self.assertEqual(reasons["unpublished"], POLICY.REASON_SCENE_UNPUBLISHED)
        self.assertEqual(reasons["hidden"], POLICY.REASON_SCENE_DELIVERY_HIDDEN)
        self.assertEqual(reasons["internal"], POLICY.REASON_SCENE_INTERNAL_ONLY)
        self.assertEqual(reasons["demo"], POLICY.REASON_SCENE_DEMO_ONLY)
        self.assertEqual(reasons["role_pruned"], POLICY.REASON_SCENE_ROLE_PRUNED)
        self.assertEqual(reasons["cap_blocked"], POLICY.REASON_SCENE_CAPABILITY_BLOCKED)
        self.assertEqual(reasons["deep_link"], POLICY.REASON_SCENE_DELIVERY_DEEP_LINK_ONLY)

        delivered = {s["code"] for s in result["delivery_scenes"]}
        self.assertEqual(delivered, {"delivered"})
        deep_link = {s["code"] for s in result["deep_link_scenes"]}
        self.assertEqual(deep_link, {"deep_link"})

        for row in result["excluded"]:
            self.assertIn(row["reason_code"], POLICY.ALLOWED_REASON_CODES)
        # Delivered and excluded sets must not overlap.
        self.assertFalse(delivered & set(reasons))

    def test_internal_scene_requires_an_internal_surface_even_when_entitled(self):
        scene = _published_scene("ops.internal", delivery_mode="internal")
        on_default = self._filter([scene])
        self.assertEqual(_reasons(on_default)["ops.internal"], POLICY.REASON_SCENE_INTERNAL_ONLY)
        on_internal = self._filter([scene], surface="internal")
        self.assertEqual({s["code"] for s in on_internal["delivery_scenes"]}, {"ops.internal"})

    def test_disabled_filter_is_an_explicit_fail_open_boundary(self):
        scenes = [_published_scene("internal", delivery_mode="internal")]
        result = POLICY.filter_delivery_scenes(scenes, surface="default", role_surface={}, enabled=False)
        self.assertFalse(result["meta"]["enabled"])
        self.assertEqual([s["code"] for s in result["delivery_scenes"]], ["internal"])
        self.assertEqual(result["excluded"], [])


class SceneDeliveryRuntimeResolutionTest(unittest.TestCase):
    def test_runtime_default_is_off_and_default_surface(self):
        runtime = POLICY.resolve_delivery_policy_runtime(None, {})
        self.assertFalse(runtime["enabled"])
        self.assertEqual(runtime["surface"], "default")

    def test_runtime_param_override_is_respected(self):
        enabled = POLICY.resolve_delivery_policy_runtime(None, {"scene_delivery_policy_enabled": True})
        self.assertTrue(enabled["enabled"])
        disabled = POLICY.resolve_delivery_policy_runtime(None, {"scene_delivery_policy_enabled": False})
        self.assertFalse(disabled["enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

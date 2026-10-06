# -*- coding: utf-8 -*-
"""Backend scene / surface authority boundary — behavior lock.

This locks the three boundary facts that the backend "场景化" used to blur:

1. The delivery-surface name space (``scene_surface``) is a *closed* channel
   vocabulary, not a business ``scene_key``.  A business scene identity can
   never be delivered as a surface name.
2. An *unregistered* surface name is a closed channel once the delivery policy
   is enabled: it delivers nothing instead of falling through to a fail-open
   pass-through.  Only an authorized development bypass re-opens it.
3. Scene entry visibility is decided by the delivery policy in a *fail-closed*
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

# The kernel resolves every surface policy through ``call_extension_hook_first``
# (the same path the P1 industry module uses).  The offline harness installs a
# stub that reads this registry at call time, so a test can exercise the real
# extension path — including the P1 development bypass — without an Odoo
# registry, and can prove that no hook means no bypass.
_HOOKS: dict = {}


def _stub_call_extension_hook_first(env, hook_name, *args, **kwargs):
    hook = _HOOKS.get(hook_name)
    if callable(hook):
        return hook(*args, **kwargs)
    return None


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
        call_extension_hook_first=_stub_call_extension_hook_first,
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


class _HookRegistryTest(unittest.TestCase):
    """Base class that keeps the injected hook registry isolated per test."""

    def setUp(self):
        _HOOKS.clear()

    def tearDown(self):
        _HOOKS.clear()


class SceneSurfaceChannelVocabularyTest(unittest.TestCase):
    """A delivery surface is a channel name, never a business scene_key."""

    def test_default_and_legacy_alias_map_to_canonical_channels(self):
        normalizer = POLICY._normalize_surface
        self.assertEqual(normalizer(""), "default")
        self.assertEqual(normalizer("default"), "default")
        # Legacy alias collapses to the canonical channel, not to a scene_key.
        self.assertEqual(normalizer("workspace_pm_v1"), "workspace_default_v1")

    def test_unregistered_surface_name_is_preserved_as_a_closed_channel(self):
        """The name space is closed by policy, not by string rewriting.

        An unregistered value (including a business scene_key) is still reported
        verbatim as the requested channel, and ``_select_surface_policy`` marks
        that channel closed instead of returning a fail-open ``enabled=False``.
        """
        normalizer = POLICY._normalize_surface
        self.assertEqual(normalizer("projects.ledger"), "projects.ledger")
        policy = POLICY._select_surface_policy("projects.ledger", env=None)
        self.assertNotEqual(policy["enabled"], False)
        self.assertTrue(policy["unregistered"])
        self.assertTrue(policy["closed"])
        self.assertEqual(policy["source"], POLICY.SURFACE_POLICY_SOURCE_UNREGISTERED_CLOSED)

    def test_business_scene_key_is_not_an_internal_or_demo_surface(self):
        for scene_key in ("projects.ledger", "finance.center", "workspace.home"):
            self.assertFalse(POLICY._is_internal_surface(scene_key))
            self.assertFalse(POLICY._is_demo_surface(scene_key))


class UnregisteredSurfaceClosedChannelTest(_HookRegistryTest):
    """An unregistered surface delivers nothing instead of passing through."""

    def _closed_result(self, scenes, surface):
        return POLICY.filter_delivery_scenes(
            scenes,
            surface=surface,
            role_surface={"capabilities": ["a"]},
            enabled=True,
        )

    def test_closed_surface_excludes_every_scene_with_the_surface_reason(self):
        scenes = [_published_scene("projects.ledger"), _published_scene("workspace.home")]
        result = self._closed_result(scenes, "projects.ledger")

        self.assertEqual(result["delivery_scenes"], [])
        self.assertEqual(result["deep_link_scenes"], [])
        reasons = _reasons(result)
        self.assertEqual(set(reasons), {"projects.ledger", "workspace.home"})
        for reason in reasons.values():
            self.assertEqual(reason, POLICY.REASON_SCENE_SURFACE_UNREGISTERED)
        self.assertIn(POLICY.REASON_SCENE_SURFACE_UNREGISTERED, POLICY.ALLOWED_REASON_CODES)
        self.assertTrue(result["meta"]["surface_policy_unregistered"])
        self.assertFalse(result["meta"]["surface_policy_bypass"])

    def test_business_scene_key_used_as_surface_cannot_open_the_product_face(self):
        # The historic bypass: pass a business scene_key as the surface and the
        # product-surface allowlist was skipped.  It is now a closed channel.
        scenes = [_published_scene("finance.center"), _published_scene("workspace.home")]
        result = self._closed_result(scenes, "finance.center")
        self.assertEqual(result["delivery_scenes"], [])
        self.assertEqual(set(_reasons(result)), {"finance.center", "workspace.home"})


class UnregisteredSurfaceDevelopmentBypassTest(_HookRegistryTest):
    """Only an authorized role, inside a runtime environment, re-opens it."""

    def setUp(self):
        super().setUp()
        self.env = types.SimpleNamespace(user=object())

    def _register_bypass(self, payload):
        calls = []

        def _hook(env, surface, runtime_env):
            calls.append((env, surface, runtime_env))
            return payload

        _HOOKS[POLICY.UNREGISTERED_SURFACE_BYPASS_HOOK] = _hook
        return calls

    def test_authorized_bypass_reopens_the_legacy_pass_through(self):
        calls = self._register_bypass({"authorized": True, "role_code": "system_admin"})
        policy = POLICY._select_surface_policy("projects.ledger", env=self.env, runtime_env="dev")

        self.assertEqual(policy["source"], POLICY.SURFACE_POLICY_SOURCE_UNREGISTERED_BYPASS)
        self.assertTrue(policy["unregistered"])
        self.assertTrue(policy["bypass"])
        self.assertFalse(policy["enabled"])
        # The runtime environment is forwarded to the product hook, so the
        # development-stage gate is decided with the real stage, not a default.
        self.assertEqual(calls, [(self.env, "projects.ledger", "dev")])

        result = POLICY.filter_delivery_scenes(
            [_published_scene("projects.ledger")],
            surface="projects.ledger",
            role_surface={"capabilities": ["a"]},
            runtime_env="dev",
            enabled=True,
            env=self.env,
        )
        self.assertEqual([row["code"] for row in result["delivery_scenes"]], ["projects.ledger"])
        self.assertTrue(result["meta"]["surface_policy_bypass"])
        self.assertTrue(result["meta"]["surface_policy_unregistered"])

    def test_bypass_requires_a_runtime_environment(self):
        self._register_bypass({"authorized": True, "role_code": "system_admin"})
        policy = POLICY._select_surface_policy("projects.ledger", env=None, runtime_env="dev")
        self.assertFalse(policy.get("bypass"))
        self.assertTrue(policy["closed"])

    def test_unauthorized_or_malformed_answer_stays_closed(self):
        self._register_bypass({"authorized": False, "role_code": "project_member"})
        self.assertTrue(POLICY._select_surface_policy("projects.ledger", env=self.env)["closed"])

        _HOOKS[POLICY.UNREGISTERED_SURFACE_BYPASS_HOOK] = lambda *args, **kwargs: "yes"
        self.assertTrue(POLICY._select_surface_policy("projects.ledger", env=self.env)["closed"])

        _HOOKS.pop(POLICY.UNREGISTERED_SURFACE_BYPASS_HOOK, None)
        self.assertTrue(POLICY._select_surface_policy("projects.ledger", env=self.env)["closed"])


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


class SceneDeliveryFailClosedTest(_HookRegistryTest):
    """Once enabled, an unentitled scene must not be delivered."""

    def _filter(self, scenes, **kwargs):
        # ``workspace_default_v1`` is a registered builtin channel.  It replaces
        # the old ``default`` fixture, which is now an unregistered closed
        # channel and would mask the per-scene reason codes under test.
        kwargs.setdefault("surface", "workspace_default_v1")
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
            _published_scene("workspace.home"),
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
        self.assertEqual(delivered, {"workspace.home"})
        deep_link = {s["code"] for s in result["deep_link_scenes"]}
        self.assertEqual(deep_link, {"deep_link"})

        for row in result["excluded"]:
            self.assertIn(row["reason_code"], POLICY.ALLOWED_REASON_CODES)
        # Delivered and excluded sets must not overlap.
        self.assertFalse(delivered & set(reasons))

    def test_internal_scene_needs_an_internal_surface_and_an_authorized_bypass(self):
        scene = _published_scene("ops.internal", delivery_mode="internal")

        # The internal channel is unregistered, so without a bypass it is closed
        # even though the delivery mode would accept an internal surface.
        without_bypass = self._filter([scene], surface="internal")
        self.assertEqual(
            _reasons(without_bypass)["ops.internal"], POLICY.REASON_SCENE_SURFACE_UNREGISTERED
        )

        # An authorized development bypass opens the internal channel; the
        # delivery-mode gate still keeps internal scenes off a registered
        # non-internal surface.
        _HOOKS[POLICY.UNREGISTERED_SURFACE_BYPASS_HOOK] = lambda *args, **kwargs: {
            "authorized": True,
            "role_code": "system_admin",
        }
        env = types.SimpleNamespace(user=object())
        opened = self._filter([scene], surface="internal", env=env)
        self.assertEqual({s["code"] for s in opened["delivery_scenes"]}, {"ops.internal"})

        registered = self._filter([scene], surface="workspace_default_v1", env=env)
        self.assertEqual(_reasons(registered)["ops.internal"], POLICY.REASON_SCENE_INTERNAL_ONLY)

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

    def test_runtime_reports_the_resolved_surface_policy_state(self):
        runtime = POLICY.resolve_delivery_policy_runtime(None, {"scene_delivery_policy_enabled": True})
        # No product policy source in the offline run: the platform default
        # channel is the registered builtin surface, not the closed sentinel.
        self.assertEqual(runtime["surface"], "workspace_default_v1")
        self.assertEqual(runtime["surface_policy_name"], "workspace_default_v1")
        self.assertFalse(runtime["surface_policy_unregistered"])
        self.assertFalse(runtime["surface_policy_bypass"])
        self.assertEqual(runtime["surface_policy_source"], "builtin")


_CONSTRUCTION_BYPASS_MODULE = (
    ROOT.parent / "smart_construction_core" / "core_extension_surface_bypass.py"
)
_SENTINEL_DEFAULT = object()


def _install_role_resolver(role_codes, *, raises=False):
    """Install the published role resolver the P1 bypass module asks for."""
    _install_module("odoo.addons.smart_core.identity")

    class _StubResolver:
        def __init__(self, env):
            self.env = env

        def user_group_xmlids(self, user):
            return ()

        def resolve_role_codes_with_evidence(self, groups):
            if raises:
                raise RuntimeError("role resolver unavailable")
            return (list(role_codes), {})

    _install_module(
        "odoo.addons.smart_core.identity.identity_resolver",
        IdentityResolver=_StubResolver,
    )


def _load_bypass_policy_module():
    module_name = "codex_test.smart_construction_core.core_extension_surface_bypass"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, _CONSTRUCTION_BYPASS_MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class UnregisteredSurfaceBypassPolicyTest(unittest.TestCase):
    """Drives the *real* P1 policy module, not an injected hook answer.

    The kernel test above proves the kernel honours only a positive hook answer.
    This class proves what the product policy actually answers, so the stage gate
    and the role resolution are locked at the owning layer instead of being
    assumed.  The published role resolver is replaced with a deterministic stub,
    so no Odoo registry is required.
    """

    def setUp(self):
        self.env = types.SimpleNamespace(user=object())
        self.bypass = _load_bypass_policy_module()

    def _answer(self, role_codes, runtime_env="dev", *, env=_SENTINEL_DEFAULT):
        _install_role_resolver(role_codes)
        target = self.env if env is _SENTINEL_DEFAULT else env
        return self.bypass.smart_core_surface_unregistered_bypass(
            target, "projects.ledger", runtime_env
        )

    def test_grant_requires_system_admin_in_a_development_stage(self):
        grant = self._answer(["system_admin"])
        self.assertTrue(grant["authorized"])
        self.assertEqual(grant["role_code"], "system_admin")
        self.assertEqual(grant["runtime_env"], "dev")
        self.assertEqual(grant["surface"], "projects.ledger")
        self.assertEqual(
            grant["reason_code"], self.bypass.UNREGISTERED_SURFACE_DEV_BYPASS_REASON
        )
        self.assertEqual(tuple(self.bypass.DEVELOPMENT_BYPASS_ROLES), ("system_admin",))

    def test_no_runtime_environment_means_no_bypass(self):
        _install_role_resolver(["system_admin"])
        self.assertIsNone(
            self.bypass.smart_core_surface_unregistered_bypass(
                None, "projects.ledger", "dev"
            )
        )

    def test_environment_without_an_acting_user_is_not_authorized(self):
        _install_role_resolver(["system_admin"])
        self.assertIsNone(
            self.bypass.smart_core_surface_unregistered_bypass(
                types.SimpleNamespace(), "projects.ledger", "dev"
            )
        )

    def test_non_admin_roles_are_never_authorized(self):
        for role in ("project_manager", "finance_manager", "customer_admin", "portal_user"):
            self.assertIsNone(self._answer([role]), role)

    def test_non_development_stages_stay_closed(self):
        for stage in ("prod", "production", "release", "saas"):
            self.assertIsNone(self._answer(["system_admin"], runtime_env=stage), stage)

    def test_role_resolution_failure_fails_closed(self):
        _install_role_resolver(["system_admin"], raises=True)
        self.assertIsNone(
            self.bypass.smart_core_surface_unregistered_bypass(
                self.env, "projects.ledger", "dev"
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "addons/smart_core/core/extension_hook_contracts.py"
RESOLVER_PATH = ROOT / "addons/smart_core/utils/extension_hooks.py"


def _load_modules():
    odoo = types.ModuleType("odoo")
    odoo.__path__ = []
    addons = types.ModuleType("odoo.addons")
    addons.__path__ = []
    smart_core = types.ModuleType("odoo.addons.smart_core")
    smart_core.__path__ = []
    core = types.ModuleType("odoo.addons.smart_core.core")
    core.__path__ = []
    utils = types.ModuleType("odoo.addons.smart_core.utils")
    utils.__path__ = []
    loader = types.ModuleType("odoo.addons.smart_core.core.extension_loader")
    env_modules = []
    loader.extension_runtime_context = lambda env: SimpleNamespace(modules=tuple(env_modules))
    sys.modules.update({
        "odoo": odoo,
        "odoo.addons": addons,
        "odoo.addons.smart_core": smart_core,
        "odoo.addons.smart_core.core": core,
        "odoo.addons.smart_core.utils": utils,
        "odoo.addons.smart_core.core.extension_loader": loader,
    })

    contract_name = "odoo.addons.smart_core.core.extension_hook_contracts"
    contract_spec = importlib.util.spec_from_file_location(contract_name, CONTRACT_PATH)
    contract = importlib.util.module_from_spec(contract_spec)
    sys.modules[contract_name] = contract
    contract_spec.loader.exec_module(contract)

    resolver_name = "odoo.addons.smart_core.utils.extension_hooks"
    resolver_spec = importlib.util.spec_from_file_location(resolver_name, RESOLVER_PATH)
    resolver = importlib.util.module_from_spec(resolver_spec)
    sys.modules[resolver_name] = resolver
    resolver_spec.loader.exec_module(resolver)
    return resolver, env_modules


RESOLVER, ENV_MODULES = _load_modules()
TEST_ENV = SimpleNamespace(registry=object())


def _module(name, **hooks):
    module = types.ModuleType("odoo.addons.%s" % name)
    for hook_name, value in hooks.items():
        setattr(module, hook_name, value)
    sys.modules[module.__name__] = module


class ExtensionHookResolverTests(unittest.TestCase):
    def setUp(self):
        ENV_MODULES[:] = []

    def test_single_owner_rejects_multiple_providers(self):
        _module(
            "provider_a",
            smart_core_identity_profile=lambda env: {"a": 1},
        )
        _module(
            "provider_b",
            smart_core_identity_profile=lambda env: {"b": 2},
        )
        ENV_MODULES[:] = ["provider_a", "provider_b"]
        with self.assertRaisesRegex(
            RESOLVER.ExtensionHookAuthorityError,
            "single_owner hook has multiple providers",
        ):
            RESOLVER.call_extension_hook_first(
                TEST_ENV,
                "smart_core_identity_profile",
                object(),
            )

    def test_ordered_merge_uses_declared_provider_order(self):
        seen = []

        def core_provider(env, *, request_context=None):
            del env
            seen.append(("smart_construction_core", request_context))
            return {
                "menu_scene_map": {"shared": "core", "core_only": "core"},
                "action_xmlid_scene_map": {},
                "model_view_scene_map": {},
            }

        def scene_provider(env, *, request_context=None):
            del env
            seen.append(("smart_construction_scene", request_context))
            return {
                "menu_scene_map": {"shared": "scene", "scene_only": "scene"},
                "action_xmlid_scene_map": {"action": "scene"},
                "model_view_scene_map": {},
            }

        _module(
            "smart_construction_core",
            smart_core_nav_scene_maps=core_provider,
        )
        _module(
            "smart_construction_scene",
            smart_core_nav_scene_maps=scene_provider,
        )
        ENV_MODULES[:] = ["smart_construction_scene", "smart_construction_core"]
        request_context = object()
        result = RESOLVER.call_extension_hook_first(
            TEST_ENV,
            "smart_core_nav_scene_maps",
            object(),
            request_context=request_context,
        )
        self.assertEqual(result["menu_scene_map"]["shared"], "scene")
        self.assertEqual(result["menu_scene_map"]["core_only"], "core")
        self.assertEqual(result["menu_scene_map"]["scene_only"], "scene")
        self.assertEqual(result["action_xmlid_scene_map"]["action"], "scene")
        self.assertEqual(
            seen,
            [
                ("smart_construction_core", request_context),
                ("smart_construction_scene", request_context),
            ],
        )

    def test_ordered_merge_unions_scene_targets(self):
        _module(
            "smart_construction_core",
            smart_core_critical_scene_target_overrides=lambda env: {"core"},
        )
        _module(
            "smart_construction_scene",
            smart_core_critical_scene_target_overrides=lambda env: {"scene"},
        )
        ENV_MODULES[:] = ["smart_construction_core", "smart_construction_scene"]
        self.assertEqual(
            RESOLVER.call_extension_hook_first(
                TEST_ENV,
                "smart_core_critical_scene_target_overrides",
                object(),
            ),
            {"core", "scene"},
        )

    def test_provider_error_is_not_silently_ignored(self):
        def broken(env):
            del env
            raise RuntimeError("boom")

        _module("provider_error", smart_core_identity_profile=broken)
        ENV_MODULES[:] = ["provider_error"]
        with self.assertRaisesRegex(RESOLVER.ExtensionHookAuthorityError, "boom"):
            RESOLVER.call_extension_hook_first(
                TEST_ENV,
                "smart_core_identity_profile",
                object(),
            )

    def test_incompatible_provider_signature_fails_explicitly(self):
        _module(
            "provider_signature",
            smart_core_identity_profile=lambda env, required_extra: {
                "env": env,
                "required_extra": required_extra,
            },
        )
        ENV_MODULES[:] = ["provider_signature"]

        with self.assertRaisesRegex(
            RESOLVER.ExtensionHookAuthorityError,
            "signature is incompatible",
        ):
            RESOLVER.call_extension_hook_first_compatible(
                TEST_ENV,
                "smart_core_identity_profile",
                object(),
            )

    def test_environment_without_registry_has_no_extension_providers(self):
        self.assertIsNone(
            RESOLVER.call_extension_hook_first(
                object(),
                "smart_core_identity_profile",
                object(),
            )
        )

    def test_undeclared_first_hook_fails(self):
        with self.assertRaisesRegex(
            RESOLVER.ExtensionHookAuthorityError,
            "no declared invocation contract",
        ):
            RESOLVER.call_extension_hook_first(object(), "smart_core_undeclared", object())

    def test_run_all_hook_is_rejected_by_first_owner_entrypoint(self):
        with self.assertRaisesRegex(
            RESOLVER.ExtensionHookAuthorityError,
            "run-all entrypoint",
        ):
            RESOLVER.call_extension_hook_first(
                TEST_ENV,
                "smart_core_register",
                {},
            )


if __name__ == "__main__":
    unittest.main()

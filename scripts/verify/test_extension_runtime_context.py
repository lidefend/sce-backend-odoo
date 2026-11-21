from __future__ import annotations

import ast
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
LOADER_PATH = ROOT / "addons/smart_core/core/extension_loader.py"


def _install_extension_module(name: str, marker: str):
    module = types.ModuleType("odoo.addons.%s" % name)

    def register(registry):
        registry[marker] = marker

    module.smart_core_register = register
    sys.modules["odoo.addons.%s" % name] = module


def _load_loader():
    package = "arch_close_extension_runtime_test"
    core_package = "%s.core" % package
    sys.modules[package] = types.ModuleType(package)
    sys.modules[package].__path__ = []
    sys.modules[core_package] = types.ModuleType(core_package)
    sys.modules[core_package].__path__ = []

    source = types.ModuleType("%s.source_authority" % core_package)
    source.build_source_authority_contract = lambda **kwargs: dict(kwargs)
    sys.modules[source.__name__] = source

    registry = types.ModuleType("%s.handler_registry" % core_package)
    registry.base_handlers = lambda: {"base.handler": object}
    sys.modules[registry.__name__] = registry

    contracts = types.ModuleType("%s.extension_hook_contracts" % core_package)

    def contract_for(hook_name):
        if hook_name == "extension_run_all":
            return SimpleNamespace(mode="run_all")
        if hook_name == "extension_single_owner":
            return SimpleNamespace(mode="single_owner")
        raise KeyError(hook_name)

    contracts.contract_for = contract_for
    sys.modules[contracts.__name__] = contracts

    name = "%s.extension_loader" % core_package
    spec = importlib.util.spec_from_file_location(name, LOADER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _Param:
    def __init__(self, env):
        self.env = env

    def sudo(self):
        return self

    def get_param(self, key, default=""):
        if key == "sc.core.extension_modules":
            return self.env.configured
        return default


class _Modules:
    def __init__(self, env):
        self.env = env

    def sudo(self):
        return self

    def with_context(self, **kwargs):
        del kwargs
        return self

    def search_read(self, domain, fields):
        del fields
        names = set((domain[0][2] if domain else []) or [])
        return [
            {"name": name, "state": self.env.states[name]}
            for name in sorted(names)
            if name in self.env.states
        ]


class _Env:
    def __init__(self, registry, configured, states):
        self.registry = registry
        self.configured = configured
        self.states = states
        self.context = {}

    def __getitem__(self, model):
        if model == "ir.config_parameter":
            return _Param(self)
        if model == "ir.module.module":
            return _Modules(self)
        raise KeyError(model)


class ExtensionRuntimeContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        odoo = types.ModuleType("odoo")
        odoo.__path__ = []
        addons = types.ModuleType("odoo.addons")
        addons.__path__ = []
        sys.modules["odoo"] = odoo
        sys.modules["odoo.addons"] = addons
        _install_extension_module("extension_alpha", "ALPHA_HANDLER")
        _install_extension_module("extension_beta", "BETA_HANDLER")
        cls.loader = _load_loader()

    def test_registry_identity_isolated_and_installed_state_enforced(self):
        registry_a = SimpleNamespace()
        registry_b = SimpleNamespace()
        env_a = _Env(
            registry_a,
            "extension_alpha",
            {"extension_alpha": "installed"},
        )
        env_b = _Env(
            registry_b,
            "extension_beta",
            {"extension_beta": "installed"},
        )

        handlers_a = self.loader.handlers_for_env(env_a)
        handlers_b = self.loader.handlers_for_env(env_b)

        self.assertIn("ALPHA_HANDLER", handlers_a)
        self.assertNotIn("BETA_HANDLER", handlers_a)
        self.assertIn("BETA_HANDLER", handlers_b)
        self.assertNotIn("ALPHA_HANDLER", handlers_b)
        self.assertIsNot(handlers_a, handlers_b)

    def test_handler_catalog_import_is_lazy_to_avoid_registry_cycle(self):
        tree = ast.parse(LOADER_PATH.read_text(encoding="utf-8"))
        eager_imports = {
            alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }

        self.assertNotIn("base_handlers", eager_imports)

    def test_config_change_rebuilds_same_registry(self):
        registry = SimpleNamespace()
        env = _Env(
            registry,
            "extension_alpha",
            {
                "extension_alpha": "installed",
                "extension_beta": "installed",
            },
        )
        self.assertIn("ALPHA_HANDLER", self.loader.handlers_for_env(env))
        env.configured = "extension_beta"
        handlers = self.loader.handlers_for_env(env)
        self.assertIn("BETA_HANDLER", handlers)
        self.assertNotIn("ALPHA_HANDLER", handlers)

    def test_uninstalled_or_missing_configuration_fails_closed(self):
        for state in ("uninstalled", "to upgrade", "missing"):
            with self.subTest(state=state):
                env = _Env(
                    SimpleNamespace(),
                    "extension_alpha",
                    (
                        {}
                        if state == "missing"
                        else {"extension_alpha": state}
                    ),
                )
                with self.assertRaises(self.loader.ExtensionConfigurationError) as caught:
                    self.loader.handlers_for_env(env)
                self.assertEqual(caught.exception.configured, ("extension_alpha",))

    def test_installed_but_not_enabled_is_not_loaded(self):
        env = _Env(
            SimpleNamespace(),
            "extension_alpha",
            {
                "extension_alpha": "installed",
                "extension_beta": "installed",
            },
        )
        handlers = self.loader.handlers_for_env(env)
        self.assertNotIn("BETA_HANDLER", handlers)

    def test_environment_without_registry_has_no_extension_modules(self):
        self.assertEqual(self.loader.iter_extension_modules(object()), [])

    def test_run_all_entrypoint_rejects_other_hook_modes(self):
        env = _Env(
            SimpleNamespace(),
            "extension_alpha",
            {"extension_alpha": "installed"},
        )
        with self.assertRaisesRegex(
            self.loader.ExtensionRuntimeError,
            "non-run_all hook",
        ):
            self.loader.run_extension_hooks(env, "extension_single_owner")

    def test_run_all_entrypoint_executes_every_configured_provider(self):
        calls = []
        for module_name in ("extension_alpha", "extension_beta"):
            setattr(
                sys.modules["odoo.addons.%s" % module_name],
                "extension_run_all",
                lambda provider=module_name: calls.append(provider),
            )
        env = _Env(
            SimpleNamespace(),
            "extension_beta,extension_alpha",
            {
                "extension_alpha": "installed",
                "extension_beta": "installed",
            },
        )

        self.loader.run_extension_hooks(env, "extension_run_all")

        self.assertEqual(calls, ["extension_beta", "extension_alpha"])


if __name__ == "__main__":
    unittest.main()

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


def _install_duplicate_extension_module(name: str, marker: str):
    module = types.ModuleType("odoo.addons.%s" % name)

    def register(registry):
        registry["duplicate.handler"] = marker

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
            return SimpleNamespace(
                mode="run_all",
                providers=("extension_beta", "extension_alpha"),
                allow_undeclared=True,
            )
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


    def set_param(self, key, value):
        assert key == "sc.core.extension_modules"
        self.env.configured = value


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
    def __init__(self, registry, configured, states, context=None):
        self.registry = registry
        self.configured = configured
        self.states = states
        self.context = dict(context or {})

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
        _install_extension_module("extension_gamma", "GAMMA_HANDLER")
        cls.loader = _load_loader()

    def test_native_uninstall_hooks_remove_only_their_own_exact_name(self):
        names = ("smart_construction_core", "smart_construction_scene", "smart_construction_bundle",
                 "smart_owner_core", "smart_owner_bundle", "smart_license_core", "smart_construction_portal")
        for name in names:
            with self.subTest(module=name):
                path = ROOT / "addons" / name
                manifest = ast.literal_eval((path / "__manifest__.py").read_text())
                self.assertEqual(manifest["uninstall_hook"], "uninstall_hook")
                init_tree = ast.parse((path / "__init__.py").read_text())
                self.assertTrue(any(isinstance(n, ast.ImportFrom) and n.module == "hooks"
                                    and any(a.name == "uninstall_hook" for a in n.names) for n in init_tree.body))
                hook = next(n for n in ast.parse((path / "hooks.py").read_text()).body
                            if isinstance(n, ast.FunctionDef) and n.name == "uninstall_hook")
                namespace = {}
                exec(compile(ast.Module(body=[hook], type_ignores=[]), str(path / "hooks.py"), "exec"), namespace)
                env = _Env(SimpleNamespace(), f"other,{name}_extra, {name},other_two,{name}", {})
                from unittest.mock import patch
                with patch.dict(sys.modules, {"odoo.addons.smart_core.core.extension_loader": self.loader}):
                    namespace["uninstall_hook"](env)
                    self.assertEqual(env.configured, f"other,{name}_extra,other_two")
                    namespace["uninstall_hook"](env)
                    self.assertEqual(env.configured, f"other,{name}_extra,other_two")

    def test_production_contribution_orders_are_explicit_and_config_order_independent(self):
        from scripts.verify.extension_hook_contract_guard import load_contract_module
        from unittest.mock import patch
        contracts = load_contract_module()
        contract_stub = sys.modules[self.loader.__package__ + ".extension_hook_contracts"]
        for hook_name in ("get_system_init_fact_contributions", "get_intent_handler_contributions",
                          "smart_core_extend_system_init"):
            contract = contracts.contract_for(hook_name)
            self.assertTrue(contract.providers)
            self.assertNotIn("smart_enterprise_base", contract.providers)
            fake_modules = {}
            unknown_provider = "third_party_extension"
            for name in contract.providers:
                module = types.ModuleType("odoo.addons." + name)
                setattr(module, hook_name, lambda name=name: {"winner": name})
                fake_modules[module.__name__] = module
            module = types.ModuleType("odoo.addons." + unknown_provider)
            setattr(module, hook_name, lambda: {"winner": unknown_provider})
            fake_modules[module.__name__] = module
            with patch.dict(sys.modules, fake_modules), patch.object(contract_stub, "contract_for", contracts.contract_for):
                for order in (
                    contract.providers + (unknown_provider,),
                    (unknown_provider,) + tuple(reversed(contract.providers)),
                ):
                    env = _Env(SimpleNamespace(), ",".join(order), dict.fromkeys(order, "installed"))
                    rows = self.loader.run_extension_hooks(env, hook_name)
                    self.assertEqual(
                        tuple(name for name, _ in rows),
                        contract.providers + (unknown_provider,),
                    )
                    merged = {}
                    for _, contribution in rows:
                        merged.update(contribution)
                    self.assertEqual(merged["winner"], unknown_provider)

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

    def test_registry_transition_filters_modules_without_raising(self):
        registry = SimpleNamespace(ready=False, _init_modules={"extension_beta"})
        env = _Env(
            registry,
            "extension_alpha,extension_beta",
            {
                "extension_alpha": "to upgrade",
                "extension_beta": "installed",
            },
        )
        context = self.loader.extension_runtime_context(env)
        self.assertTrue(context.lifecycle_transition)
        self.assertEqual(context.modules, ("extension_beta",))
        self.assertIn("BETA_HANDLER", context.handlers)
        self.assertNotIn("ALPHA_HANDLER", context.handlers)

        env.states["extension_alpha"] = "installed"
        not_loaded = self.loader.extension_runtime_context(env)
        self.assertNotIn("ALPHA_HANDLER", not_loaded.handlers)
        registry._init_modules.add("extension_alpha")
        progressed = self.loader.extension_runtime_context(env)
        self.assertIn("ALPHA_HANDLER", progressed.handlers)
        self.assertIsNot(context, progressed)

        registry.ready = True
        env.states["extension_alpha"] = "to remove"
        with self.assertRaises(self.loader.ExtensionConfigurationError):
            self.loader.extension_runtime_context(env)

    def test_request_context_cannot_enable_an_installed_extension(self):
        env = _Env(
            SimpleNamespace(),
            "",
            {
                "extension_alpha": "installed",
            },
            context={"sc.core.extension_modules": "extension_alpha"},
        )
        context = self.loader.extension_runtime_context(env)
        self.assertEqual(context.modules, ())
        self.assertNotIn("ALPHA_HANDLER", context.handlers)

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
        for module_name in ("extension_alpha", "extension_beta", "extension_gamma"):
            setattr(
                sys.modules["odoo.addons.%s" % module_name],
                "extension_run_all",
                lambda provider=module_name: calls.append(provider),
            )
        env = _Env(
            SimpleNamespace(),
            "extension_alpha,extension_gamma,extension_beta",
            {
                "extension_alpha": "installed",
                "extension_beta": "installed",
                "extension_gamma": "installed",
            },
        )

        self.loader.run_extension_hooks(env, "extension_run_all")

        self.assertEqual(calls, ["extension_beta", "extension_alpha", "extension_gamma"])

    def test_extension_intent_collision_fails_closed(self):
        _install_duplicate_extension_module("extension_duplicate_a", object())
        _install_duplicate_extension_module("extension_duplicate_b", object())
        env = _Env(
            SimpleNamespace(),
            "extension_duplicate_a,extension_duplicate_b",
            {
                "extension_duplicate_a": "installed",
                "extension_duplicate_b": "installed",
            },
        )
        with self.assertRaisesRegex(
            self.loader.ExtensionRuntimeError,
            "duplicate intent registration",
        ):
            self.loader.handlers_for_env(env)

    def test_run_all_shared_data_order_is_declared_not_configured(self):
        for name in ("extension_alpha", "extension_beta"):
            module = sys.modules["odoo.addons." + name]
            module.extension_run_all = lambda data, name=name: data.update(winner=name)
        results = []
        for names in ("extension_alpha,extension_beta", "extension_beta,extension_alpha"):
            env = _Env(SimpleNamespace(), names, {
                "extension_alpha": "installed", "extension_beta": "installed",
            })
            data = {}
            self.loader.run_extension_hooks(env, "extension_run_all", data)
            results.append(data)
        self.assertEqual(results, [{"winner": "extension_alpha"}] * 2)

    def test_enabled_non_provider_does_not_violate_run_all_contract(self):
        _install_extension_module("extension_unrelated", "UNRELATED")
        env = _Env(SimpleNamespace(), "extension_alpha,extension_unrelated", {
            "extension_alpha": "installed", "extension_unrelated": "installed",
        })
        sys.modules["odoo.addons.extension_alpha"].extension_run_all = lambda: "alpha"
        self.assertEqual(self.loader.run_extension_hooks(env, "extension_run_all"),
                         [("extension_alpha", "alpha")])


if __name__ == "__main__":
    unittest.main()

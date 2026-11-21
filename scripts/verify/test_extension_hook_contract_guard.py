from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.verify.extension_hook_contract_guard import (
    collect_failures,
    load_contract_module,
)


class _Contracts:
    SINGLE_OWNER_HOOKS = frozenset({"smart_core_single"})
    ORDERED_MERGE_HOOKS = {
        "smart_core_merge": type(
            "Contract",
            (),
            {
                "providers": (
                    "smart_core",
                    "industry",
                )
            },
        )()
    }
    RUN_ALL_HOOKS = frozenset()


class ExtensionHookContractGuardTests(unittest.TestCase):
    def test_noninstallable_fixture_is_not_a_production_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            module = root / "addons/industry"
            (module / "__manifest__.py").write_text("{'installable': False}")
            (module / "__init__.py").write_text("from .core import get_facts\n")
            contract = type("Contract", (), {"providers": ("industry",)})()
            contracts = type("Contracts", (), {"SINGLE_OWNER_HOOKS": set(),
                             "ORDERED_MERGE_HOOKS": {}, "RUN_ALL_HOOKS": {"get_facts": contract}})()
            self.assertTrue(any("run_all" in row and "actual=[]" in row
                                for row in collect_failures(root, contracts)))

    def test_run_all_contract_allows_declared_third_party_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            (root / "addons/industry/__init__.py").write_text(
                "from .core import get_facts\n"
            )
            third_party = root / "addons/third_party"
            third_party.mkdir()
            (third_party / "__init__.py").write_text(
                "from .core import get_facts\n"
            )
            contract = type(
                "Contract",
                (),
                {
                    "providers": ("industry",),
                    "allow_undeclared": True,
                },
            )()
            contracts = type(
                "Contracts",
                (),
                {
                    "SINGLE_OWNER_HOOKS": set(),
                    "ORDERED_MERGE_HOOKS": {},
                    "RUN_ALL_HOOKS": {"get_facts": contract},
                },
            )()

            self.assertEqual(collect_failures(root, contracts), [])

    def test_run_all_final_provider_must_be_declared(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            contract = type(
                "Contract",
                (),
                {
                    "providers": ("industry",),
                    "final_providers": ("undeclared_final",),
                    "allow_undeclared": True,
                },
            )()
            contracts = type(
                "Contracts",
                (),
                {
                    "SINGLE_OWNER_HOOKS": set(),
                    "ORDERED_MERGE_HOOKS": {},
                    "RUN_ALL_HOOKS": {"get_facts": contract},
                },
            )()

            failures = collect_failures(root, contracts)

        self.assertTrue(any("final providers are not declared" in row for row in failures))

    def test_run_all_hook_has_an_explicit_contract(self):
        contracts = load_contract_module()

        self.assertEqual(contracts.contract_for("smart_core_register").mode, "run_all")

    def _root(self, directory: str) -> Path:
        root = Path(directory)
        for module in ("smart_core", "industry"):
            path = root / "addons" / module
            path.mkdir(parents=True)
            (path / "__init__.py").write_text("")
        return root

    def test_valid_single_owner_and_ordered_merge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            (root / "addons/smart_core/__init__.py").write_text(
                "from .core import smart_core_single, smart_core_merge\n"
            )
            (root / "addons/industry/__init__.py").write_text(
                "from .core import smart_core_merge\n"
            )
            calls = root / "addons/smart_core/calls.py"
            calls.write_text(
                textwrap.dedent(
                    """
                    def run(env):
                        call_extension_hook_first(env, "smart_core_single", env)
                        call_extension_hook_first(env, "smart_core_merge", env)
                    """
                )
            )
            self.assertEqual(collect_failures(root, _Contracts()), [])

    def test_duplicate_single_owner_and_undeclared_call_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            (root / "addons/smart_core/__init__.py").write_text(
                "from .core import smart_core_single, smart_core_merge, smart_core_hidden\n"
            )
            (root / "addons/industry/__init__.py").write_text(
                "from .core import smart_core_single, smart_core_merge\n"
            )
            calls = root / "addons/smart_core/calls.py"
            calls.write_text(
                textwrap.dedent(
                    """
                    def run(env):
                        call_extension_hook_first(env, "smart_core_hidden", env)
                    """
                )
            )
            failures = collect_failures(root, _Contracts())
            self.assertTrue(any("missing contracts" in item for item in failures))
            self.assertTrue(any("smart_core_single" in item for item in failures))

    def test_hook_with_multiple_modes_fails(self):
        contracts = type(
            "Contracts",
            (),
            {
                "SINGLE_OWNER_HOOKS": frozenset({"smart_core_single"}),
                "ORDERED_MERGE_HOOKS": {},
                "RUN_ALL_HOOKS": frozenset({"smart_core_single"}),
            },
        )()
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)

            failures = collect_failures(root, contracts)

        self.assertTrue(any("multiple modes" in item for item in failures))

    def test_variable_hook_name_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            calls = root / "addons/smart_core/calls.py"
            calls.write_text(
                textwrap.dedent(
                    """
                    HOOK_NAME = "smart_core_hidden"

                    def run(env):
                        call_extension_hook_first(env, HOOK_NAME, env)
                    """
                )
            )

            failures = collect_failures(root, _Contracts())

        self.assertTrue(any("smart_core_hidden" in item for item in failures))

    def test_hook_name_forwarding_wrapper_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            calls = root / "addons/smart_core/calls.py"
            calls.write_text(
                textwrap.dedent(
                    """
                    def resolve_service(env, hook_name, fallback_name):
                        del fallback_name
                        return call_extension_hook_first(env, hook_name, env)

                    def build_service(env):
                        return resolve_service(
                            env,
                            "smart_core_hidden",
                            "smart_core_hidden_fallback",
                        )
                    """
                )
            )

            failures = collect_failures(root, _Contracts())

        self.assertTrue(any("smart_core_hidden" in item for item in failures))


if __name__ == "__main__":
    unittest.main()

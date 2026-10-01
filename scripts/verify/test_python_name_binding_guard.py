#!/usr/bin/env python3
"""Self-test for scripts/verify/python_name_binding_guard.py.

The name-binding guard is the only cheap static line of defence against the
defect family that produced a production HTTP 500 (a helper called but never
imported). A guard that never fails would be worse than none, so this test
proves it reports unbound names, honours the repository's existing
``# noqa: F821`` acknowledgement, and applies the Odoo-shell exemption only
where it is legitimate.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

GUARD_PATH = Path(__file__).resolve().with_name("python_name_binding_guard.py")
_spec = importlib.util.spec_from_file_location("python_name_binding_guard", GUARD_PATH)
assert _spec and _spec.loader
guard = importlib.util.module_from_spec(_spec)
sys.modules["python_name_binding_guard"] = guard
_spec.loader.exec_module(guard)


def analyze(source: str, rel_path: str) -> tuple[list, bool]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / Path(rel_path).name
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return guard.analyze_file(path, rel_path)


def violations_for(source: str, rel_path: str) -> list:
    violations, _skipped = analyze(source, rel_path)
    return violations


def violation_names(source: str, rel_path: str) -> list[str]:
    return sorted(item.detail for item in violations_for(source, rel_path))


class NameBindingGuardTest(unittest.TestCase):
    def test_unbound_call_is_reported(self) -> None:
        source = """
        def handler():
            return missing_helper(1)
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), ["missing_helper"])

    def test_unbound_global_in_method_is_reported(self) -> None:
        source = """
        class Service:
            def run(self):
                return _("label")
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), ["_"])

    def test_noqa_f821_suppresses(self) -> None:
        source = """
        def f():
            return env.cr.dbname  # noqa: F821
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), [])

    def test_noqa_with_other_code_does_not_suppress(self) -> None:
        source = """
        def f():
            return env.cr.dbname  # noqa: E501
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), ["env"])

    def test_partial_acknowledgement_still_reports_other_lines(self) -> None:
        source = """
        def f():
            first = env.cr.dbname  # noqa: F821
            return other_unbound(first)
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), ["other_unbound"])

    def test_builtins_and_imports_are_allowed(self) -> None:
        source = """
        from pathlib import Path

        def f(items):
            return len(items) + Path("x").name.__len__()
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), [])

    def test_closure_variable_is_not_reported(self) -> None:
        source = """
        def outer():
            captured = 1

            def inner():
                return captured

            return inner
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), [])

    def test_star_import_skips_module(self) -> None:
        source = """
        from somewhere import *

        def f():
            return star_name()
        """
        violations, skipped = analyze(source, "addons/smart_core/x.py")
        self.assertEqual(violations, [])
        self.assertTrue(skipped)

    def test_globals_update_skips_module(self) -> None:
        source = """
        globals().update({"INJECTED": 1})

        def f():
            return INJECTED
        """
        violations, skipped = analyze(source, "addons/smart_core/x.py")
        self.assertEqual(violations, [])
        self.assertTrue(skipped)

    def test_scripts_env_is_exempt_from_odoo_shell_injection(self) -> None:
        source = """
        def f():
            return env.cr.dbname
        """
        self.assertEqual(violation_names(source, "scripts/verify/x.py"), [])

    def test_addons_env_is_not_exempt(self) -> None:
        source = """
        def f():
            return env.cr.dbname
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), ["env"])

    # --- family 2: env.get("<model>") used for truthiness ------------------

    def test_env_get_inline_truthiness_is_reported(self) -> None:
        source = """
        def f(env):
            if env.get("sc.audit.log"):
                return 1
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), ["sc.audit.log"])

    def test_env_get_negated_truthiness_is_reported(self) -> None:
        source = """
        def f(env):
            if not env.get("sc.audit.log"):
                return
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), ["sc.audit.log"])

    def test_env_get_bound_to_variable_then_tested_is_reported(self) -> None:
        source = """
        def f(self):
            Audit = self.env.get("sc.audit.log")
            if Audit:
                return Audit
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), ["sc.audit.log"])

    def test_env_get_ternary_truthiness_is_reported(self) -> None:
        source = """
        def f(self):
            Audit = self.env.get("sc.audit.log")
            return Audit.sudo() if Audit else None
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), ["sc.audit.log"])

    def test_env_get_explicit_none_check_is_allowed(self) -> None:
        source = """
        def f(self):
            Audit = self.env.get("sc.audit.log")
            if Audit is None:
                return None
            return Audit.sudo()
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), [])

    def test_env_get_noqa_acknowledgement_is_honoured(self) -> None:
        source = """
        def f(env):
            if env.get("sc.audit.log"):  # noqa
                return 1
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), [])

    def test_plain_dict_get_is_not_flagged(self) -> None:
        source = """
        import os

        def f():
            if os.environ.get("ENV") != "prod":
                return 1
        """
        self.assertEqual(violation_names(source, "addons/smart_core/x.py"), [])

    def test_repository_is_clean(self) -> None:
        self.assertEqual(guard.main(["addons", "scripts"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

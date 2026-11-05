from __future__ import annotations

import unittest

from scripts.verify.test_coverage_registry_audit import (
    STATUS_GATED,
    STATUS_ON_DEMAND,
    STATUS_UNWIRED,
    audit_failures,
    default_entry,
    parse_tagged_declarations,
    tag_token_pattern,
)


def item(group: str, status: str, kind: str = "odoo_tag", declarations: int = 1) -> dict:
    return {
        "group": group,
        "status": status,
        "kind": kind,
        "declarations": declarations,
        "files": [f"addons/smart_core/tests/{group}.py"],
        "owner": "platform-team",
        "evidence": [],
    }


class TaggedDeclarationParsingTest(unittest.TestCase):
    def test_standard_exclusion_preserves_real_demo_groups(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scripts.verify import test_coverage_registry_audit as audit
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "addons/demo/tests/test_roles.py"
            source.parent.mkdir(parents=True)
            source.write_text('@tagged("-standard", "demo_loaded_chains")\n'
                              'class TestLoaded(TransactionCase): pass\n'
                              '@tagged("demo_action_roles")\n'
                              'class TestRoles(TransactionCase): pass\n')
            with patch.object(audit, "ROOT", root), patch.object(audit, "ADDON_ROOTS", ["addons"]):
                groups = audit.collect_tag_declarations()
            self.assertEqual(set(groups), {"demo_loaded_chains", "demo_action_roles"})
            self.assertEqual(groups["demo_loaded_chains"]["classes"], {"TestLoaded"})
            self.assertEqual(groups["demo_action_roles"]["classes"], {"TestRoles"})
            self.assertEqual(groups["demo_loaded_chains"]["files"], {"addons/demo/tests/test_roles.py"})

    def test_single_line_decorator_binds_class(self) -> None:
        text = (
            '@tagged("post_install", "-at_install", "uc4_native_lowcode")\n'
            "class TestThing(TransactionCase):\n"
            "    pass\n"
        )
        self.assertEqual(
            parse_tagged_declarations(text),
            [
                ("post_install", "TestThing"),
                ("-at_install", "TestThing"),
                ("uc4_native_lowcode", "TestThing"),
            ],
        )

    def test_multiline_decorator_is_parsed(self) -> None:
        """The 2026-10-10 defect: multi-line @tagged(...) was invisible."""
        text = (
            "@tagged(\n"
            '    "post_install",\n'
            '    "-at_install",\n'
            '    "acceptance_fixture_execution_freeze",\n'
            ")\n"
            "class TestFreeze(TransactionCase):\n"
            "    pass\n"
        )
        self.assertIn(
            ("acceptance_fixture_execution_freeze", "TestFreeze"),
            parse_tagged_declarations(text),
        )

    def test_decorator_on_method_has_no_class(self) -> None:
        text = '@tagged("post_install", "relation_entry_override")\ndef test_x(self):\n    pass\n'
        self.assertIn(("relation_entry_override", None), parse_tagged_declarations(text))

    def test_stacked_decorators_still_bind_class(self) -> None:
        text = (
            '@tagged("post_install")\n'
            "@classmethod\n"
            'class TestStacked(TransactionCase):\n'
            "    pass\n"
        )
        self.assertIn(("post_install", "TestStacked"), parse_tagged_declarations(text))


class ExplicitCoTagConsumerTest(unittest.TestCase):
    def test_registered_core_classes_reach_actual_default_module_consumer(self):
        import ast
        import os
        import re
        import subprocess
        import yaml
        from scripts.verify import test_coverage_registry_audit as audit

        registry = {row['group']: row for row in audit.load_registry()['entries']}
        workflow_path = '.github/workflows/backend_test_suite.yml'
        workflow = yaml.safe_load((audit.ROOT / workflow_path).read_text())
        script = next(step['run'] for step in workflow['jobs']['backend_suite']['steps']
                      if step.get('name') == 'Run backend test suite per module')
        selection = script[script.index('module_test_tags="${TEST_TAGS_INPUT}"'):
                           script.index('module_env_file=""')]
        consumer = re.search(r'make test MODULE="\$\{module\}" TEST_TAGS="\$\{module_test_tags\}" '
                             r'\\\n\s*DB_NAME="\$\{attempt_db\}"', script)
        self.assertIsNotNone(consumer, 'default module tags must reach the real test runner')
        for group in ('product_policy_fact_authority', 'scenario_direct_initialization'):
            with self.subTest(group=group):
                entry = registry[group]
                self.assertEqual('unwired', entry['status'])  # Alias is not selected literally.
                self.assertEqual('class-selected', entry['dispose'])
                bound = entry['selection']
                self.assertEqual('smart_construction_core', bound['module'])
                self.assertEqual('sc_gate', bound['tag'])
                self.assertEqual(workflow_path + ' :: sc_gate/${module}', entry['gate'])
                tests = audit.ROOT / 'addons' / bound['module'] / 'tests'
                declarations = parse_tagged_declarations((tests / bound['file']).read_text())
                classes = {klass for tag, klass in declarations if tag == group}
                self.assertEqual({bound['class']}, classes)
                self.assertIn((bound['tag'], bound['class']), declarations)
                self.assertNotIn(('-' + bound['tag'], bound['class']), declarations)
                imports = ast.parse((tests / '__init__.py').read_text())
                self.assertTrue(any(isinstance(node, ast.ImportFrom) and node.level == 1
                                    and node.module is None
                                    and any(alias.name == bound['file'][:-3] for alias in node.names)
                                    for node in imports.body), 'ORM class must actually be imported')
                # Execute the actual default-selection fragment and actual make
                # consumer. Only external changed-test lookup and make are stubbed;
                # no Odoo process or database is started by this wiring regression.
                command = ('python3() { return 0; }\n'
                           'make() { printf "%s\\n" "$@"; }\n' + selection + consumer.group(0))
                outcome = subprocess.run(['bash', '-eu', '-c', command], env={**os.environ,
                    'module': bound['module'], 'TEST_TAGS_INPUT': '', 'RUNNER_TEMP': '/unused',
                    'attempt_db': 'unused'}, text=True, capture_output=True, check=True)
                args = outcome.stdout.splitlines()
                self.assertIn('MODULE=' + bound['module'], args)
                selected = next(arg.removeprefix('TEST_TAGS=') for arg in args
                                if arg.startswith('TEST_TAGS='))
                self.assertIn(bound['tag'] + '/' + bound['module'], selected.split(','))
                self.assertNotIn(group, selected)


class TagTokenMatchingTest(unittest.TestCase):
    def test_module_qualified_expression_selects_tag(self) -> None:
        pattern = tag_token_pattern("sc_gate")
        self.assertTrue(pattern.search("sc_smoke/${module},sc_gate/${module}"))

    def test_prefix_and_suffix_neighbours_do_not_match(self) -> None:
        pattern = tag_token_pattern("sc_gate")
        self.assertIsNone(pattern.search("sc_smoke"))
        self.assertIsNone(pattern.search("sc_gate_v2"))
        self.assertIsNone(pattern.search("my_sc_gate"))

    def test_bare_tag_still_matches(self) -> None:
        self.assertTrue(tag_token_pattern("sc_perm").search("sc_gate,sc_perm"))


class AuditFailureTest(unittest.TestCase):
    def test_gated_group_needs_no_entry(self) -> None:
        failures = audit_failures([item("sc_gate", STATUS_GATED)], [], {"entries": []})
        self.assertEqual(failures, [])

    def test_undispositioned_unwired_group_fails(self) -> None:
        failures = audit_failures(
            [item("uc4_native_lowcode", STATUS_UNWIRED, declarations=17)],
            [],
            {"entries": []},
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("uc4_native_lowcode", failures[0])
        self.assertIn("not dispositioned", failures[0])

    def test_dispositioned_unwired_group_passes(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "uc4_native_lowcode",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "construction-product",
                    "dispose": "wire-pending",
                    "reason": "no governed selection yet",
                    "review_by": "2026-12-31",
                }
            ]
        }
        self.assertEqual(
            audit_failures([item("uc4_native_lowcode", STATUS_UNWIRED)], [], registry), []
        )

    def test_unwired_entry_without_review_by_fails(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "uc4_native_lowcode",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "construction-product",
                    "dispose": "wire-pending",
                    "reason": "no governed selection yet",
                }
            ]
        }
        failures = audit_failures([item("uc4_native_lowcode", STATUS_UNWIRED)], [], registry)
        self.assertTrue(any("review_by" in failure for failure in failures))

    def test_class_selected_disposition_requires_gate(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "user_feedback",
                    "kind": "odoo_tag",
                    "status": STATUS_ON_DEMAND,
                    "owner": "construction-product",
                    "dispose": "class-selected",
                    "reason": "reached via a class-name make target",
                }
            ]
        }
        failures = audit_failures([item("user_feedback", STATUS_ON_DEMAND)], [], registry)
        self.assertTrue(any("must name its gate" in failure for failure in failures))

    def test_stale_entry_fails(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "removed_group",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "platform-team",
                    "dispose": "wire-pending",
                    "reason": "gone",
                    "review_by": "2026-12-31",
                }
            ]
        }
        failures = audit_failures([item("live_group", STATUS_GATED)], [], registry)
        self.assertTrue(any("removed_group" in failure for failure in failures))

    def test_registry_that_now_gates_is_inconsistent(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "sc_perm",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "platform-team",
                    "dispose": "wire-pending",
                    "reason": "was unwired",
                    "review_by": "2026-12-31",
                }
            ]
        }
        failures = audit_failures([item("sc_perm", STATUS_GATED)], [], registry)
        self.assertTrue(any("still records status" in failure for failure in failures))

    def test_unknown_dispose_fails(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "uc4_native_lowcode",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "construction-product",
                    "dispose": "invented",
                    "reason": "typo",
                    "review_by": "2026-12-31",
                }
            ]
        }
        failures = audit_failures([item("uc4_native_lowcode", STATUS_UNWIRED)], [], registry)
        self.assertTrue(any("unknown dispose" in failure for failure in failures))


class DefaultEntryTest(unittest.TestCase):
    def test_unwired_defaults_to_wire_pending_with_deadline(self) -> None:
        entry = default_entry(item("uc4_native_lowcode", STATUS_UNWIRED, declarations=17))
        self.assertEqual(entry["dispose"], "wire-pending")
        self.assertTrue(entry["review_by"])
        self.assertEqual(entry["owner"], "platform-team")

    def test_on_demand_defaults_to_class_selected_with_gate(self) -> None:
        entry = default_entry(
            {
                **item("user_feedback", STATUS_ON_DEMAND),
                "evidence": ["make:verify.workflow_contract.backend :: /TestUserFeedbackBusinessViews"],
            }
        )
        self.assertEqual(entry["dispose"], "class-selected")
        self.assertIn("make:verify.workflow_contract.backend", entry["gate"])
        self.assertNotIn("review_by", entry)


if __name__ == "__main__":
    unittest.main()

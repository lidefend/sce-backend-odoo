#!/usr/bin/env python3
"""Behavior tests for exact-tree backend scope, including destructive changes."""
import os
import textwrap
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backend_impact_plan as planner


def module(deps=(), tests=True):
    return {'depends': set(deps), 'tests': tests, 'installable': True}


class ImpactSelectionTest(unittest.TestCase):
    def setUp(self):
        self.graph = {'kernel': module(), 'industry': module(['kernel']),
                      'bundle': module(['industry']), 'unrelated': module()}

    def test_leaf_does_not_run_every_module(self):
        plan = planner.select(['addons/bundle/models/a.py'], self.graph, self.graph)
        self.assertEqual(plan['modules'], ['bundle'])
        self.assertEqual(plan['mode'], 'incremental')

    def test_transitive_consumers_selected(self):
        plan = planner.select(['addons/industry/models/a.py'], self.graph, self.graph)
        self.assertEqual(plan['modules'], ['bundle', 'industry'])

    def test_deleted_dependency_keeps_old_consumers(self):
        after = {**self.graph, 'bundle': module()}
        plan = planner.select(['addons/industry/__manifest__.py'], self.graph, after)
        self.assertEqual(plan['modules'], ['bundle', 'industry'])

    def test_removed_module_selects_surviving_consumers(self):
        after = {k: v for k, v in self.graph.items() if k != 'industry'}
        self.assertEqual(planner.select(['addons/industry/models/a.py'], self.graph, after)['modules'], ['bundle'])

    def test_shared_runner_forces_full(self):
        plan = planner.select(['scripts/ci/orm_result_guard.sh'], self.graph, self.graph)
        self.assertEqual(plan['modules'], sorted(self.graph))
        self.assertEqual(plan['mode'], 'full')

    def test_unknown_path_is_not_a_skip(self):
        self.assertEqual(planner.select(['new_runtime/loader.py'], self.graph, self.graph)['mode'], 'full')

    def test_docs_and_frontend_have_explicit_empty_backend_scope(self):
        plan = planner.select(['docs/a.md', 'frontend/apps/web/src/a.ts'], self.graph, self.graph)
        self.assertEqual(plan['modules'], [])
        self.assertEqual(plan['mode'], 'incremental')

    def test_empty_diff_is_not_green_skip(self):
        self.assertEqual(planner.select([], self.graph, self.graph)['mode'], 'full')

    def test_scheduled_full_cannot_be_narrowed_by_paths(self):
        self.assertEqual(planner.select(['docs/a.md'], self.graph, self.graph, full=True)['modules'], sorted(self.graph))

    def test_module_without_tests_cannot_silently_pass(self):
        graph = {**self.graph, 'untested': module(tests=False)}
        with self.assertRaisesRegex(ValueError, 'no runnable test coverage'):
            planner.select(['addons/untested/models/a.py'], graph, graph)

    def test_covered_seed_cannot_mask_an_uncovered_seed(self):
        graph = {**self.graph, 'untested': module(tests=False)}
        with self.assertRaisesRegex(ValueError, 'no runnable test coverage: untested'):
            planner.select(['addons/untested/a.py', 'addons/bundle/a.py'], graph, graph)

    def test_invalid_path_rejected(self):
        with self.assertRaises(ValueError):
            planner.select(['../a'], self.graph, self.graph)

    def test_base_head_and_rename_are_read_from_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
            git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid')
            for name in ('old', 'new', 'consumer'):
                path = root / 'addons' / name
                (path / 'tests').mkdir(parents=True)
                (path / '__manifest__.py').write_text(repr({'depends': ['old'] if name == 'consumer' else []}))
                (path / 'tests/test_a.py').write_text('# fixture\n')
            git('add', '.'); git('commit', '-qm', 'base'); base = git('rev-parse', 'HEAD')
            git('mv', 'addons/old/tests/test_a.py', 'addons/new/tests/test_moved.py')
            git('commit', '-qm', 'rename'); head = git('rev-parse', 'HEAD')
            with patch.object(planner, 'ROOT', root):
                paths = planner.git('diff', '--no-renames', '--name-only', base, head, '--').splitlines()
                self.assertIn('addons/old/tests/test_a.py', paths)
                self.assertIn('addons/new/tests/test_moved.py', paths)
                plan = planner.select(paths, planner.snapshot(base), planner.snapshot(head))
            self.assertEqual(plan['modules'], ['consumer', 'new'])

    def test_required_check_executes_failure_truth_table(self):
        text = (planner.ROOT / '.github/workflows/professional_quality_gate.yml').read_text()
        block = text.split('- name: Enforce affected backend execution', 1)[1].split('- name:', 1)[0]
        script = textwrap.dedent(block.split('run: |', 1)[1])
        for auth, required, result, expected in (
            ('success', 'true', 'success', 0),
            ('success', 'false', 'skipped', 0),
            ('failure', '', 'skipped', 1),
            ('success', '', 'skipped', 1),
            ('success', 'true', 'failure', 1),
            ('success', 'true', 'cancelled', 1),
            ('success', 'true', 'skipped', 1),
            ('success', 'false', 'success', 1),
        ):
            with self.subTest(auth=auth, required=required, result=result):
                outcome = subprocess.run(['bash', '-c', script], env={**os.environ,
                    'AUTHORIZATION_RESULT': auth, 'IMPACT_REQUIRED': required,
                    'IMPACT_RESULT': result, 'EVENT_NAME': 'pull_request'})
                self.assertEqual(outcome.returncode, expected)

    def test_required_check_depends_on_runtime_and_rejects_failure(self):
        text = (planner.ROOT / '.github/workflows/professional_quality_gate.yml').read_text()
        job = text.split('  professional_quality_gate:\n', 1)[1]
        self.assertIn('needs: [professional_authorization, backend_impact_suite, professional_quality_checks, python310_runtime_compatibility]', job)
        self.assertIn('always() &&', job)
        condition = job.split('runs-on:', 1)[0]
        self.assertNotIn("needs.professional_authorization.result == 'success'", condition)
        self.assertIn('test "${AUTHORIZATION_RESULT}" = success', job)
        self.assertIn('test "${IMPACT_REQUIRED}" = true || test "${IMPACT_REQUIRED}" = false', job)
        self.assertIn('test "${IMPACT_RESULT}" = success', job)
        self.assertIn('test "${IMPACT_RESULT}" = skipped', job)
        suite = (planner.ROOT / '.github/workflows/backend_test_suite.yml').read_text()
        self.assertIn('workflow_call:', suite)
        self.assertIn('--base "${IMPACT_BASE}"', suite)
        self.assertIn('module_test_tags="sc_smoke/${module},sc_gate/${module}"', suite)
        self.assertIn('if ! evaluate_orm_outcome', suite)
        self.assertIn('cron: "37 19 * * *"', suite)


if __name__ == '__main__':
    unittest.main()

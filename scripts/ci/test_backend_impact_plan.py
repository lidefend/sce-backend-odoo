#!/usr/bin/env python3
"""Behavior tests for exact-tree backend scope, including destructive changes."""
import os
import sys
import textwrap
import io
import contextlib
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

    def test_control_plane_selects_owning_checks_not_orm(self):
        for path, target in planner.CONTROL_PLANE.items():
            with self.subTest(path=path):
                plan = planner.select([path], self.graph, self.graph)
                self.assertEqual([], plan['modules'])
                self.assertEqual([target], plan['tool_checks'])
                self.assertEqual('NOT_APPLICABLE', plan['scope_status'])

    def test_control_plane_file_read_by_test_still_selects_reader(self):
        path = 'scripts/ci/backend_suite_plan.py'
        graph = {**self.graph, 'reader': {**module(), 'file_inputs': [path]}}
        self.assertEqual(['reader'], planner.select([path],graph,graph)['modules'])

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

    def test_p4_tooling_scripts_are_not_orm_runtime(self):
        for path in ('scripts/ops/branch_cleanup_safe.sh',
                     'scripts/ops/agent_run_context.py',
                     'scripts/ci/generate_test_inventory.py'):
            with self.subTest(path=path):
                plan = planner.select([path], self.graph, self.graph)
                self.assertEqual([], plan['modules'])
                self.assertEqual('NOT_APPLICABLE', plan['scope_status'])

    def test_real_scene_json_readers_trigger_only_their_consumer(self):
        path = 'addons/smart_construction_scene/tests/test_action_only_scene_semantic_supply.py'
        reads, _ = planner.test_file_reads((planner.ROOT / path).read_text(), path)
        expected = [
            'docs/product/delivery/v1/construction_pm_v1_scene_surface_policy.json',
            'docs/product/delivery/v1/delivery_menu_tree_source_v1.json',
            'docs/product/delivery/v1/module_scene_capability_source_v1.json',
        ]
        graph = {'scene': {**module(), 'file_inputs': reads}, 'unrelated': module()}
        for filename in expected:
            with self.subTest(filename=filename):
                self.assertIn(filename, reads)
                self.assertEqual(['scene'], planner.select([filename], graph, graph)['modules'])
        self.assertEqual([], planner.select(['docs/product/delivery/v1/unread.json'], graph, graph)['modules'])

    def test_old_file_reader_survives_removal_and_rename(self):
        before = {'industry': {**module(), 'file_inputs': ['docs/old.json']},
                  'bundle': module(['industry']), 'unrelated': module()}
        after = {**before, 'industry': {**module(), 'file_inputs': ['config/new.json']}}
        for path in ['docs/old.json', 'config/new.json']:
            with self.subTest(path=path):
                self.assertIn('industry', planner.select([path], before, after)['modules'])
        self.assertEqual(['industry'], planner.select(['docs/old.json'], before, after)['modules'])
        self.assertEqual(['bundle', 'industry'], planner.select(['addons/industry/models/a.py'], before, after)['modules'])

    def test_concrete_fixture_reads_are_extracted_without_running_test(self):
        source = '''from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
raise RuntimeError("must not execute")
def test_fixture():
    fixture = ROOT / "config" / "fixture.json"
    fixture.read_bytes()
'''
        reads, unknown = planner.test_file_reads(source, 'addons/sample/tests/test_a.py')
        self.assertEqual(['config/fixture.json'], reads)
        self.assertEqual([], unknown)

    def test_dynamic_and_shadowed_reads_are_visible_not_guessed(self):
        source = '''from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
def dynamic(name):
    (ROOT / "docs" / name).read_text()
def shadowed(ROOT):
    (ROOT / "docs" / "a.json").read_text()
'''
        reads, unknown = planner.test_file_reads(source, 'addons/sample/tests/test_a.py')
        self.assertEqual([], reads)
        self.assertEqual([4, 6], unknown)

    def test_known_reader_cannot_weaken_unknown_impact_fallback(self):
        graph = {'one': {**module(), 'file_inputs': ['config/flags.json']},
                 'two': {**module(), 'unresolved_file_reads': ['tests/test_a.py:4']}}
        result = planner.select(['config/flags.json'], graph, graph)
        self.assertEqual('full', result['mode'])
        self.assertEqual(['one', 'two'], result['modules'])

    def test_method_does_not_inherit_class_local_path(self):
        source = '''from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
class Tests:
    ROOT = ROOT / "wrong"
    def test_input(self):
        (ROOT / "docs" / "actual.json").read_text()
'''
        reads, unknown = planner.test_file_reads(source, 'addons/sample/tests/test_a.py')
        self.assertEqual(['docs/actual.json'], reads)
        self.assertEqual([], unknown)

    def test_unsupported_binding_forms_invalidate_outer_values(self):
        for statement in ['ROOT /= "child.json"',
                          'ROOT: Path = Path(__file__).resolve().parent',
                          'for ROOT in values: pass',
                          'with manager() as ROOT: pass']:
            with self.subTest(statement=statement):
                source = ('from pathlib import Path\nROOT = Path(__file__).resolve().parents[3]\n'
                          'def test_a():\n    '+statement+'\n    ROOT.read_text()\n')
                reads, unknown = planner.test_file_reads(source, 'addons/sample/tests/test_a.py')
                self.assertEqual([], reads)
                self.assertTrue(unknown)

    def test_lambda_reads_are_unresolved_and_defaults_use_outer_scope(self):
        source = '''from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
reader = lambda ROOT: (ROOT / "docs" / "lambda.json").read_text()
def test_input(payload=(ROOT / "docs" / "default.json").read_text()):
    pass
'''
        reads, unknown = planner.test_file_reads(source, 'addons/sample/tests/test_a.py')
        self.assertEqual(['docs/default.json'], reads)
        self.assertEqual([3], unknown)

    def test_exact_tree_snapshot_keeps_deleted_input_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
            git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid')
            target = root / 'addons/scene/tests/test_a.py'
            target.parent.mkdir(parents=True)
            target.write_text('from pathlib import Path\nROOT = Path(__file__).resolve().parents[3]\ndef test_a():\n    (ROOT / "docs" / "input.json").read_text ()\n')
            (target.parent.parent / '__manifest__.py').write_text("{'depends': []}")
            (root / 'docs').mkdir(); (root / 'docs/input.json').write_text('{}')
            git('add', '.'); git('commit', '-qm', 'base'); base = git('rev-parse', 'HEAD')
            git('rm', 'docs/input.json'); git('commit', '-qm', 'remove input'); head = git('rev-parse', 'HEAD')
            with patch.object(planner, 'ROOT', root):
                before, after = planner.snapshot(base), planner.snapshot(head)
                self.assertEqual(['docs/input.json'], after['scene']['file_inputs'])
                self.assertEqual(['scene'], planner.select(['docs/input.json'], before, after)['modules'])

    def test_exact_empty_diff_requires_no_backend_work(self):
        plan = planner.select([], self.graph, self.graph)
        self.assertEqual([], plan['modules'])
        self.assertEqual('NOT_APPLICABLE', plan['scope_status'])

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

    def test_control_plane_tool_checks_are_enforced_by_final_gate(self):
        text = (planner.ROOT / '.github/workflows/professional_quality_gate.yml').read_text()
        block = text.split('- name: Enforce control-plane tool check execution', 1)[1].split('- name:', 1)[0]
        script = textwrap.dedent(block.split('run: |', 1)[1])
        for checks, ran, expected in (
            ('', '', 0),
            ('verify.ci.workflow.contract', 'true', 0),
            ('verify.ci.workflow.contract verify.verification.lane_coverage', 'true', 0),
            ('verify.ci.workflow.contract', '', 1),
            ('verify.ci.workflow.contract', 'false', 1),
            ('verify.ci.workflow.contract', 'skipped', 1),
        ):
            with self.subTest(checks=checks, ran=ran):
                outcome = subprocess.run(['bash', '-c', script], env={**os.environ,
                    'TOOL_CHECKS': checks, 'TOOL_CHECKS_RAN': ran})
                self.assertEqual(outcome.returncode, expected)

    def test_github_output_emits_tool_checks_and_scope_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
            git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid')
            module = root / 'addons' / 'sample'
            (module / 'tests').mkdir(parents=True)
            (module / '__manifest__.py').write_text("{'depends': []}")
            (module / 'tests' / 'test_a.py').write_text('# fixture\n')
            control = root / 'scripts' / 'ci'
            control.mkdir(parents=True)
            (control / 'backend_impact_plan.py').write_text('# control plane\n')
            git('add', '.'); git('commit', '-qm', 'base'); base = git('rev-parse', 'HEAD')
            (control / 'backend_impact_plan.py').write_text('# control plane changed\n')
            git('commit', '-aqm', 'control-plane change'); head = git('rev-parse', 'HEAD')
            out = root / 'out.json'; gho = root / 'github-output.txt'
            with patch.object(planner, 'ROOT', root):
                with patch.object(sys, 'argv', ['backend_impact_plan.py', '--base', base,
                                                '--head', head, '--output', str(out),
                                                '--github-output', str(gho)]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        planner.main()
            emitted = gho.read_text()
            self.assertIn('required=false', emitted)
            self.assertIn('tool_checks=verify.ci.workflow.contract', emitted)
            self.assertIn('scope_status=NOT_APPLICABLE', emitted)

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

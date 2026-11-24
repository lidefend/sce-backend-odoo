"""Behavioral counterexamples for complete, bounded backend shard selection."""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
import copy
from pathlib import Path
from unittest.mock import patch

import backend_suite_plan as planner


class ShardPlanTest(unittest.TestCase):
    def test_frozen_file_lookups_do_not_rebuild_the_plan(self):
        plan = {
            'scope_mode': 'focused',
            'focused_selectors': {'core': ['*/core:TestOne.test_one']},
            'focused_orm_files': {'core': ['addons/core/tests/test_orm.py']},
            'focused_python_files': {'core': ['addons/core/tests/test_plain.py']},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = f'{tmp}/plan.json'
            raw = (json.dumps(plan) + '\n').encode()
            with open(path, 'wb') as stream:
                stream.write(raw)
            digest = hashlib.sha256(raw).hexdigest()
            for flag, expected in (
                ('--selectors', '*/core:TestOne.test_one'),
                ('--orm-files', 'addons/core/tests/test_orm.py'),
                ('--python-files', 'addons/core/tests/test_plain.py'),
            ):
                with self.subTest(flag=flag), patch.object(
                    planner,
                    'build_plan',
                    side_effect=AssertionError('frozen lookup rebuilt the plan'),
                ), patch.object(
                    sys,
                    'argv',
                    [
                        'backend_suite_plan.py',
                        '--focused',
                        '--head',
                        'a' * 40,
                        '--frozen-plan',
                        path,
                        '--plan-sha256',
                        digest,
                        '--module',
                        'core',
                        flag,
                    ],
                ), contextlib.redirect_stdout(io.StringIO()) as output:
                    planner.main()
                self.assertEqual(expected, output.getvalue().strip())

    def test_partition_preserves_exact_union_without_duplicates(self):
        for size in range(1, 31):
            names = [f'module_{index}' for index in range(size)]
            shards = planner.partition(names)
            self.assertEqual(len(shards), min(4, size))
            actual = [name for shard in shards for name in shard['modules']]
            self.assertEqual(sorted(actual), sorted(names))
            self.assertEqual(len(set(actual)), size)
            self.assertTrue(all(shard['modules'] for shard in shards))

    def test_order_is_deterministic(self):
        self.assertEqual(planner.partition(['c', 'b', 'a']), planner.partition(['a', 'b', 'c']))

    def test_historical_durations_balance_without_changing_scope(self):
        modules = [f'module_{index}' for index in range(14)]
        durations = {
            'module_0': 900,
            'module_1': 300,
            'module_2': 280,
            'module_3': 240,
            'module_4': 180,
            'module_5': 120,
            'module_6': 90,
            'module_7': 60,
        }
        weighted = planner.partition(modules, durations=durations)
        ordered = sorted(modules)
        round_robin_loads = [
            sum(durations.get(name, 1) for name in ordered[index::4])
            for index in range(4)
        ]
        all_modules = [name for shard in weighted for name in shard['modules']]
        self.assertEqual(sorted(all_modules), sorted(modules))
        self.assertEqual(len(all_modules), len(set(all_modules)))
        self.assertLess(
            max(shard['estimated_duration_seconds'] for shard in weighted),
            max(round_robin_loads),
        )
        self.assertEqual(
            weighted,
            planner.partition(list(reversed(modules)), durations=dict(reversed(list(durations.items())))),
        )

    def test_invalid_duration_weights_fail_closed(self):
        for durations in (
            {'missing': 1},
            {'a': -1},
            {'a': float('nan')},
            {'a': float('inf')},
            {'a': True},
        ):
            with self.subTest(durations=durations), self.assertRaises(ValueError):
                planner.partition(['a', 'b'], durations=durations)

    def test_zero_duration_weights_seed_every_shard_and_pass_plan_validation(self):
        for modules, durations in (
            (['a', 'b'], {'a': 0, 'b': 0}),
            (['a', 'b', 'c'], {'a': 10, 'b': 0, 'c': 0}),
            (['a', 'b', 'c', 'd'], {'a': 0, 'b': 0, 'c': 0, 'd': 0}),
        ):
            with self.subTest(modules=modules, durations=durations):
                required = {
                    'base': 'b' * 40,
                    'head': 'a' * 40,
                    'modules': sorted(modules),
                    'changed_test_coverage': [],
                }
                decisions = [
                    {
                        'target': module,
                        'decision': 'RUN',
                        'previous_actual_duration': durations[module],
                    }
                    for module in modules
                ]
                plan = planner.apply_reuse_decision(required, decisions)
                shards = plan['shards']
                self.assertTrue(all(shard['modules'] for shard in shards))
                flattened = [
                    module for shard in shards for module in shard['modules']
                ]
                self.assertEqual(sorted(flattened), sorted(modules))
                self.assertEqual(len(flattened), len(set(flattened)))
                self.assertEqual(
                    plan,
                    planner.validate_execution_plan(plan, required),
                )

    def test_dependency_affinity_keeps_one_preparation_and_exact_coverage(self):
        modules = ['core', 'demo', 'bundle', 'portal', 'seed', 'fixture', 'norm', 'small']
        group = ['bundle', 'portal', 'seed', 'fixture', 'norm']
        durations = dict(core=580, demo=500, bundle=490, portal=420, seed=420, fixture=430, norm=427, small=20)
        shards = planner.partition(modules, durations=durations, groups=[group])
        owners = {name: row['index'] for row in shards for name in row['modules']}
        self.assertEqual(len({owners[name] for name in group}), 1)
        self.assertNotEqual(owners['core'], owners['demo'])
        self.assertNotEqual(owners['core'], owners['portal'])
        self.assertNotEqual(owners['demo'], owners['portal'])
        self.assertEqual(sorted(owners), sorted(modules))
        self.assertEqual(shards, planner.partition(list(reversed(modules)), durations=durations, groups=[list(reversed(group))]))
        one = planner.partition(group, groups=[group])
        self.assertEqual(len(one), 1)
        self.assertEqual(one[0]['modules'], sorted(group))

    def test_invalid_affinity_groups_fail_closed(self):
        for groups in ([[]], [['a', 'a']], [['missing']], [['a'], ['a', 'b']]):
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                planner.partition(['a', 'b'], groups=groups)

    def test_preparation_affinity_uses_manifest_closure_not_test_imports(self):
        graph = {
            'smart_construction_core': {'manifest_depends': {'smart_core'}},
            'smart_construction_demo': {'manifest_depends': {'smart_construction_core'}},
            'portal': {'manifest_depends': {'smart_construction_core'}},
            'bundle': {'manifest_depends': {'portal'}},
            'test_reader': {'depends': {'smart_construction_core'}, 'manifest_depends': set()},
        }
        with patch.dict(planner.os.environ, {'TEST_TAGS_INPUT': ''}):
            self.assertEqual(planner.preparation_groups(graph, list(graph)), [['bundle', 'portal']])
        with patch.dict(planner.os.environ, {'TEST_TAGS_INPUT': 'sc_gate'}):
            self.assertEqual(planner.preparation_groups(graph, list(graph)), [])

    def test_affinity_survives_history_partition_and_frozen_identity_validation(self):
        required = dict(base='b'*40, head='a'*40, modules=['a', 'b', 'c'], changed_test_coverage=[], preparation_groups=[['a', 'b']])
        decisions = [dict(target=name, decision='RUN', previous_actual_duration=100) for name in required['modules']]
        plan = planner.apply_reuse_decision(required, decisions)
        self.assertEqual(plan['shards'][0]['modules'], ['a', 'b'])
        self.assertEqual(plan, planner.validate_execution_plan(plan, required))
        tampered = copy.deepcopy(plan)
        tampered['preparation_groups'] = []
        with self.assertRaises(ValueError):
            planner.validate_execution_plan(tampered, required)

    def test_invalid_scope_is_not_a_green_empty_matrix(self):
        for names in ([], ['a', 'a'], ['../a'], ['a;exit'], ['a\nb']):
            with self.subTest(names=names), self.assertRaises(ValueError):
                planner.partition(names)

    def test_parallelism_is_bounded(self):
        for limit in (0, 5):
            with self.assertRaises(ValueError):
                planner.partition(['a'], limit)

    def test_premerge_cannot_override_scope(self):
        with patch.object(planner.impact, 'git', return_value='a' * 40), \
                patch.object(planner.impact, 'snapshot', return_value={}):
            with self.assertRaisesRegex(ValueError, 'cannot be overridden'):
                planner.build_plan('base', 'head', 'one_module')

    def test_scheduled_run_keeps_full_scope(self):
        graph = {name: {'depends': set(), 'tests': True, 'prefix': f'addons/{name}/'}
                 for name in ['a', 'b', 'c']}
        graph['c'].update(installable=False, tests=False)
        def git(*args):
            return '\n'.join(f'addons/{name}/tests' for name in graph) if args[0] == 'ls-tree' else 'a' * 40
        with patch.object(planner.impact, 'git', side_effect=git), \
                patch.object(planner.impact, 'snapshot', return_value=graph):
            plan = planner.build_plan('', 'head')
        self.assertEqual(plan['modules'], ['a', 'b', 'c'])
        self.assertEqual(plan['suite'], 'product')
        self.assertIn('explicit_full', plan['reasons'])

    def test_full_suites_partition_product_demo_and_acceptance(self):
        graph = {
            'product': {'prefix': 'addons/product/'},
            'acceptance_fixture': {'prefix': 'addons/acceptance_fixture/'},
            'demo': {'prefix': 'demo_addons/demo/'},
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config/tenant').mkdir(parents=True)
            (root / 'config/tenant/module_sets.v1.json').write_text(json.dumps({
                'forbidden_implicit_modules': ['acceptance_fixture'],
            }))
            with patch.object(planner.impact, 'ROOT', root):
                product = planner.suite_modules('product', ['product', 'acceptance_fixture', 'demo'], graph)
                demo = planner.suite_modules('demo', ['product', 'acceptance_fixture', 'demo'], graph)
                acceptance = planner.suite_modules(
                    'acceptance',
                    ['product', 'acceptance_fixture', 'demo'],
                    graph,
                )
        self.assertEqual(product, ['product'])
        self.assertEqual(demo, ['demo'])
        self.assertEqual(acceptance, ['acceptance_fixture'])
        self.assertEqual(set(product + demo + acceptance), set(graph))
        self.assertEqual(len(product + demo + acceptance), len(set(product + demo + acceptance)))

    def test_incremental_product_suite_excludes_demo_and_acceptance_fixture(self):
        graph = {
            'product': {
                'prefix': 'addons/product/',
                'depends': set(),
                'manifest_depends': set(),
            },
            'acceptance_fixture': {
                'prefix': 'addons/acceptance_fixture/',
                'depends': set(),
                'manifest_depends': set(),
            },
            'demo': {
                'prefix': 'demo_addons/demo/',
                'depends': set(),
                'manifest_depends': set(),
            },
        }
        selected = {
            'modules': ['product', 'acceptance_fixture', 'demo'],
            'mode': 'full',
            'reasons': ['shared_runtime'],
        }
        coverage = [
            {'module': 'product', 'path': 'addons/product/tests/test_model.py'},
            {'module': 'acceptance_fixture', 'path': 'addons/acceptance_fixture/tests/test_fixture.py'},
            {'module': 'demo', 'path': 'demo_addons/demo/tests/test_demo.py'},
        ]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config/tenant').mkdir(parents=True)
            (root / 'config/tenant/module_sets.v1.json').write_text(json.dumps({
                'forbidden_implicit_modules': ['acceptance_fixture'],
            }))
            with patch.object(planner.impact, 'ROOT', root), \
                    patch.object(planner.impact, 'snapshot', return_value=graph), \
                    patch.object(planner.impact, 'select', return_value=selected), \
                    patch.object(planner.impact, 'git') as git, \
                    patch.object(planner.changed_coverage, 'changed_tests', return_value=coverage):
                git.side_effect = lambda *args: {
                    ('rev-parse', '--verify', 'base^{commit}'): 'b' * 40,
                    ('rev-parse', '--verify', 'head^{commit}'): 'a' * 40,
                    ('diff', '--no-renames', '--name-only', 'b' * 40, 'a' * 40, '--'): 'addons/product/model.py',
                    ('diff', '--no-renames', '--diff-filter=D', '--name-only', 'b' * 40, 'a' * 40, '--'): '',
                }[args]
                plan = planner.build_plan('base', 'head', suite='product')
        self.assertEqual(plan['modules'], ['product'])
        self.assertEqual(plan['suite'], 'product')
        self.assertEqual(plan['changed_test_coverage'], coverage[:1])

    def test_full_plan_demands_registered_managed_methods(self):
        module = planner.changed_coverage.MANAGED_MODULE
        graph = {module: {'depends': set(), 'tests': True, 'prefix': f'addons/{module}/'}}
        rows = [{
            'module': module,
            'selector': '/fixture:Test.test_one',
            'owner': 'acceptance.frontend.fixture_orm',
        }]
        def git(*args):
            return f'addons/{module}/tests' if args[0] == 'ls-tree' else 'a' * 40
        with patch.object(planner.impact, 'git', side_effect=git), \
                patch.object(planner.impact, 'snapshot', return_value=graph), \
                patch.object(planner.changed_coverage, 'managed_tests', return_value=rows) as managed:
            plan = planner.build_plan('', 'head', suite='acceptance')
        self.assertEqual(rows, plan['changed_test_coverage'])
        self.assertEqual(plan['suite'], 'acceptance')
        managed.assert_called_once()

    def test_dispatch_rejects_unknown_or_duplicate_modules(self):
        graph = {'a': {'depends': set(), 'tests': True, 'prefix': 'addons/a/'}}
        def git(*args):
            return 'addons/a/tests' if args[0] == 'ls-tree' else 'a' * 40
        with patch.object(planner.impact, 'git', side_effect=git), \
                patch.object(planner.impact, 'snapshot', return_value=graph):
            for names in ('unknown', 'a,a'):
                with self.subTest(names=names), self.assertRaises(ValueError):
                    planner.build_plan('', 'head', names)

    def test_premerge_preserves_runtime_full_fallback(self):
        graph = {name: {'depends': set(), 'tests': True} for name in ['a', 'b']}
        def git(*args):
            return 'scripts/render_odoo_conf.py\n' if args[0] == 'diff' else 'a' * 40
        with patch.object(planner.impact, 'git', side_effect=git), \
                patch.object(planner.impact, 'snapshot', return_value=graph):
            plan = planner.build_plan('base', 'head')
        self.assertEqual(plan['modules'], ['a', 'b'])
        self.assertEqual(plan['mode'], 'full')

    def test_focused_request_preserves_existing_families_and_dependency_modules(self):
        complete = {
            'base': 'b' * 40,
            'head': 'a' * 40,
            'mode': 'incremental',
            'scope_mode': 'full',
            'reasons': [],
            'modules': ['core', 'scene'],
            'changed_paths': [
                'addons/core/tests/test_flow.py',
                'addons/scene/tests/test_scene.py',
            ],
            'preparation_groups': [],
            'changed_test_coverage': [
                {
                    'path': 'addons/core/tests/test_flow.py',
                    'module': 'core',
                    'owner': 'backend_suite',
                    'kind': 'orm',
                    'execution_selector': '*/core:TestFlow.test_one',
                },
                {
                    'path': 'addons/core/tests/test_flow.py',
                    'module': 'core',
                    'owner': 'backend_suite',
                    'kind': 'orm',
                    'execution_selector': '*/core:TestFlow.test_two',
                },
                {
                    'module': 'fixture',
                    'owner': 'acceptance.frontend.fixture_orm',
                    'execution_selector': '*/fixture:TestFixture.test_managed',
                },
            ],
        }
        with patch.object(planner, 'build_plan', return_value=complete), \
                patch.object(planner.impact, 'snapshot', return_value={}), \
                patch.object(planner, 'preparation_groups', return_value=[]):
            planned = planner.build_focused_plan('b' * 40, 'a' * 40)
        self.assertEqual(complete, planned)
        self.assertEqual('full', planned['scope_mode'])
        self.assertEqual(['core', 'scene'], planned['modules'])
        self.assertNotIn('focused_selectors', planned)

    def test_focused_plan_uses_exact_selectors_for_test_only_modules(self):
        complete = {
            'base': 'b' * 40,
            'head': 'a' * 40,
            'mode': 'incremental',
            'scope_mode': 'full',
            'reasons': [],
            'modules': ['core'],
            'changed_paths': ['addons/core/tests/test_flow.py'],
            'preparation_groups': [],
            'shards': [{'index': 0, 'modules': ['core']}],
            'changed_test_coverage': [
                {
                    'path': 'addons/core/tests/test_flow.py',
                    'module': 'core',
                    'owner': 'backend_suite',
                    'kind': 'orm',
                    'execution_selector': '*/core:TestFlow.test_one',
                },
                {
                    'path': 'addons/core/tests/test_flow.py',
                    'module': 'core',
                    'owner': 'backend_suite',
                    'kind': 'orm',
                    'execution_selector': '*/core:TestFlow.test_two',
                },
            ],
        }
        with patch.object(planner, 'build_plan', return_value=complete):
            planned = planner.build_focused_plan('b' * 40, 'a' * 40)
        self.assertEqual('focused', planned['scope_mode'])
        self.assertEqual('test_only_changed_tests', planned['focused_reason'])
        self.assertEqual(['core'], planned['focused_modules'])
        self.assertEqual(
            ['*/core:TestFlow.test_one', '*/core:TestFlow.test_two'],
            planned['focused_selectors']['core'],
        )
        self.assertEqual(
            {'core': ['addons/core/tests/test_flow.py']},
            planned['focused_orm_files'],
        )

    def test_focused_plan_uses_changed_tests_for_production_module_changes(self):
        complete = {
            'base': 'b' * 40,
            'head': 'a' * 40,
            'mode': 'full',
            'scope_mode': 'full',
            'reasons': ['shared_runtime:docker-compose.yml'],
            'modules': ['core', 'scene'],
            'changed_paths': [
                'addons/core/models/document.py',
                'addons/core/tests/test_flow.py',
                'docker-compose.yml',
            ],
            'changed_deletions': [],
            'preparation_groups': [['core', 'scene']],
            'changed_test_coverage': [{
                'path': 'addons/core/tests/test_flow.py',
                'module': 'core',
                'owner': 'backend_suite',
                'kind': 'orm',
                'execution_selector': '*/core:TestFlow.test_one',
            }],
        }
        with patch.object(planner, 'build_plan', return_value=complete):
            planned = planner.build_focused_plan('b' * 40, 'a' * 40)
        self.assertEqual('focused', planned['scope_mode'])
        self.assertEqual('changed_module_tests_cover_runtime_changes', planned['focused_reason'])
        self.assertEqual(['core'], planned['modules'])
        self.assertEqual(
            ['*/core:TestFlow.test_one'],
            planned['focused_selectors']['core'],
        )

    def test_focused_plan_narrows_dependent_modules_to_changed_test_owners(self):
        complete = {
            'base': 'b' * 40,
            'head': 'a' * 40,
            'mode': 'incremental',
            'scope_mode': 'full',
            'reasons': [],
            'modules': ['core', 'scene'],
            'changed_paths': [
                'addons/core/tests/test_flow.py',
                'docs/ops/iteration.md',
            ],
            'changed_deletions': [],
            'preparation_groups': [['core', 'scene']],
            'shards': [
                {'index': 0, 'modules': ['core', 'scene']},
            ],
            'changed_test_coverage': [{
                'path': 'addons/core/tests/test_flow.py',
                'module': 'core',
                'owner': 'backend_suite',
                'kind': 'orm',
                'execution_selector': '*/core:TestFlow.test_one',
            }],
        }
        with patch.object(planner, 'build_plan', return_value=complete):
            planned = planner.build_focused_plan('b' * 40, 'a' * 40)
        self.assertEqual('focused', planned['scope_mode'])
        self.assertEqual(['core'], planned['modules'])
        self.assertEqual([], planned['preparation_groups'])
        self.assertEqual([['core']], [row['modules'] for row in planned['shards']])

    def test_focused_plan_binds_python_file_scope(self):
        complete = {
            'base': 'b' * 40,
            'head': 'a' * 40,
            'mode': 'incremental',
            'scope_mode': 'full',
            'reasons': [],
            'modules': ['core'],
            'changed_paths': ['addons/core/tests/test_flow.py'],
            'preparation_groups': [],
            'changed_test_coverage': [{
                'path': 'addons/core/tests/test_flow.py',
                'module': 'core',
                'owner': 'backend_suite',
                'kind': 'python',
                'execution_selector': '*/core:TestFlow.test_one',
            }],
        }
        with patch.object(planner, 'build_plan', return_value=complete):
            planned = planner.build_focused_plan('b' * 40, 'a' * 40)
        self.assertEqual(
            {'core': ['addons/core/tests/test_flow.py']},
            planned['focused_python_files'],
        )
        self.assertEqual({}, planned['focused_selectors'])

    def test_focused_plan_binds_each_changed_python_file_once(self):
        paths = [
            'addons/core/tests/test_flow.py',
            'addons/core/tests/test_other.py',
        ]
        complete = {
            'base': 'b' * 40,
            'head': 'a' * 40,
            'mode': 'incremental',
            'scope_mode': 'full',
            'reasons': [],
            'modules': ['core'],
            'changed_paths': paths,
            'preparation_groups': [],
            'changed_test_coverage': [
                {
                    'path': path,
                    'module': 'core',
                    'owner': 'backend_suite',
                    'kind': 'python',
                    'execution_selector': '*/core:TestFlow.test_one',
                }
                for path in (paths[0], paths[1], paths[0])
            ],
        }
        with patch.object(planner, 'build_plan', return_value=complete):
            planned = planner.build_focused_plan('b' * 40, 'a' * 40)
        self.assertEqual(paths, planned['focused_python_files']['core'])
        self.assertEqual({}, planned['focused_selectors'])

    def test_mixed_tests_keep_orm_selectors_and_python_files_separate(self):
        orm_path = 'addons/core/tests/test_orm.py'
        python_path = 'addons/core/tests/test_plain.py'
        complete = {
            'base': 'b' * 40,
            'head': 'a' * 40,
            'mode': 'incremental',
            'scope_mode': 'full',
            'reasons': [],
            'modules': ['core'],
            'changed_paths': [orm_path, python_path],
            'changed_deletions': [],
            'preparation_groups': [],
            'changed_test_coverage': [
                {
                    'path': orm_path,
                    'module': 'core',
                    'owner': 'backend_suite',
                    'kind': 'orm',
                    'execution_selector': '*/core:TestOrm.test_one',
                },
                {
                    'path': python_path,
                    'module': 'core',
                    'owner': 'backend_suite',
                    'kind': 'python',
                    'execution_selector': '*/core:TestPlain.test_two',
                },
                {
                    'path': 'addons/fixture/tests/test_managed.py',
                    'module': 'fixture',
                    'owner': 'acceptance.frontend.fixture_orm',
                    'kind': 'orm',
                    'execution_selector': '*/fixture:TestManaged.test_one',
                },
            ],
        }
        with patch.object(planner, 'build_plan', return_value=complete):
            planned = planner.build_focused_plan('b' * 40, 'a' * 40)
        self.assertEqual(
            {'core': ['*/core:TestOrm.test_one']},
            planned['focused_selectors'],
        )
        self.assertEqual(
            {'core': [orm_path]},
            planned['focused_orm_files'],
        )
        self.assertEqual(
            {'core': [python_path]},
            planned['focused_python_files'],
        )

    def test_focused_plan_retains_full_scope_when_changed_test_is_deleted(self):
        deleted = 'addons/core/tests/test_removed.py'
        added = 'addons/core/tests/test_flow.py'
        complete = {
            'base': 'b' * 40,
            'head': 'a' * 40,
            'mode': 'incremental',
            'scope_mode': 'full',
            'reasons': [],
            'modules': ['core'],
            'changed_paths': [added, deleted],
            'changed_deletions': [deleted],
            'preparation_groups': [],
            'changed_test_coverage': [{
                'path': added,
                'module': 'core',
                'owner': 'backend_suite',
                'kind': 'python',
                'execution_selector': '*/core:TestFlow.test_one',
            }],
        }
        with patch.object(planner, 'build_plan', return_value=complete):
            planned = planner.build_focused_plan('b' * 40, 'a' * 40)
        self.assertEqual('full', planned['scope_mode'])
        self.assertNotIn('focused_python_files', planned)

    def test_focused_plan_retains_full_scope_for_production_or_helper_changes(self):
        rows = [{
            'module': 'core',
            'owner': 'backend_suite',
            'execution_selector': '*/core:TestFlow.test_one',
        }]
        for path in (
            'addons/core/models/record.py',
            'addons/core/tests/perm_matrix.py',
            'addons/core/tests/test_flow.py',
        ):
            complete = {
                'base': 'b' * 40,
                'head': 'a' * 40,
                'mode': 'incremental',
                'scope_mode': 'full',
                'reasons': [],
                'modules': ['core'],
                'changed_paths': [path],
                'preparation_groups': [],
                'changed_test_coverage': rows,
            }
            with self.subTest(path=path), patch.object(
                planner,
                'build_plan',
                return_value=complete,
            ):
                planned = planner.build_focused_plan('b' * 40, 'a' * 40)
                expected = (
                    'focused'
                    if path.endswith('/tests/test_flow.py')
                    else 'full'
                )
                self.assertEqual(expected, planned['scope_mode'])

    def test_focused_plan_falls_back_to_complete_modules_without_changed_tests(self):
        complete = {
            'base': 'b' * 40,
            'head': 'a' * 40,
            'mode': 'incremental',
            'scope_mode': 'full',
            'reasons': ['backend_runtime_change'],
            'modules': ['core'],
            'preparation_groups': [],
            'changed_test_coverage': [],
        }
        with patch.object(planner, 'build_plan', return_value=complete):
            planned = planner.build_focused_plan('b' * 40, 'a' * 40)
        self.assertEqual(complete, planned)
        self.assertEqual('full', planned['scope_mode'])
        self.assertEqual(['core'], planned['modules'])
        self.assertNotIn('focused_selectors', planned)

    def test_focused_plan_rejects_selectors_outside_impact_scope(self):
        complete = {
            'modules': ['core'],
            'changed_test_coverage': [{
                'module': 'scene',
                'owner': 'backend_suite',
                'execution_selector': '*/scene:TestFlow.test_one',
            }],
        }
        with self.assertRaisesRegex(ValueError, 'outside the impact-safe'):
            planner.focused_scope(complete, complete['changed_test_coverage'])


class FrozenExecutionPlanTest(unittest.TestCase):
    def setUp(self):
        self.required = {'base': 'b' * 40, 'head': 'a' * 40,
                         'modules': ['a', 'b', 'c', 'd']}
        self.plan = {**self.required, 'shards': planner.partition(['b', 'c', 'd']),
                     'reuse_decision': {'reuse': ['a'], 'decisions': [
                         {'target': 'a', 'previous_receipt': {'locator': {'module': 'a'}}}]}}

    def test_reused_first_module_does_not_drop_last_module(self):
        with patch.object(planner, 'select_historical_receipts', return_value={
                'decisions': [{'target': 'a', 'decision': 'REUSE'}]}):
            result = planner.validate_execution_plan(self.plan, self.required)
        self.assertEqual([s['modules'] for s in result['shards']], [['b'], ['c'], ['d']])

    def test_missing_duplicate_overlap_and_wrong_identity_are_rejected(self):
        for mutation in ('missing', 'duplicate', 'overlap', 'head', 'base', 'modules'):
            plan = copy.deepcopy(self.plan)
            if mutation == 'missing': plan['shards'].pop()
            elif mutation == 'duplicate': plan['shards'][1]['modules'] = ['b']
            elif mutation == 'overlap': plan['shards'][0]['modules'] = ['a', 'b']
            else: plan[mutation] = 'invalid'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                planner.validate_execution_plan(plan, self.required)

    def test_expired_reuse_is_not_trusted_from_plan(self):
        with patch.object(planner, 'select_historical_receipts', return_value={
                'decisions': [{'target': 'a', 'decision': 'RUN'}]}), self.assertRaises(ValueError):
            planner.validate_execution_plan(self.plan, self.required)

    def test_certified_isolated_reuse_is_rechecked_without_repartition(self):
        row = {'target': 'a', 'decision': 'REUSE', 'authority': 'isolated_python',
               'image_id': 'sha256:' + 'f' * 64, 'previous_receipt': {'locator': {'module': 'a'}}}
        self.plan['reuse_decision']['decisions'] = [row]
        with patch.object(planner, 'isolated_plan_reuse', return_value=row), patch.object(
                planner, 'select_historical_receipts', return_value={'decisions': []}):
            self.assertEqual(self.plan, planner.validate_execution_plan(self.plan, self.required))
        with patch.object(planner, 'isolated_plan_reuse', return_value=None), self.assertRaises(ValueError):
            planner.validate_execution_plan(self.plan, self.required)

    def test_actual_receipts_cover_each_executed_module_once(self):
        receipts = [{'source_head': self.plan['head'], 'integration_base': self.plan['base'],
                     'exit_code': 0, 'test_count': 1, 'module': m} for m in ['b', 'c', 'd']]
        planner.verify_execution_coverage(self.plan, receipts)
        for bad in (receipts[:-1], receipts + receipts[:1],
                    [dict(r, source_head='old') for r in receipts],
                    [dict(r, test_count=0) for r in receipts],
                    [dict(r, module='a') for r in receipts]):
            with self.assertRaises(ValueError): planner.verify_execution_coverage(self.plan, bad)

    def test_same_module_orm_and_multiple_python_executions_are_distinct(self):
        plan = {'base': 'b' * 40, 'head': 'a' * 40, 'shards': [{'index': 0, 'modules': ['core']}]}
        base = {'source_head': plan['head'], 'integration_base': plan['base'],
                'exit_code': 0, 'test_count': 23, 'module': 'core'}
        receipts = [
            {**base, 'kind': 'orm', 'execution': ''},
            {**base, 'kind': 'python', 'execution': 'test_ui_contract_v2_boundaries', 'test_count': 162},
            {**base, 'kind': 'python', 'execution': 'test_unified_page_contract_v2_mobile_compact', 'test_count': 137},
        ]
        planner.verify_execution_coverage(plan, receipts)
        with self.assertRaises(ValueError):
            planner.verify_execution_coverage(plan, receipts + [dict(receipts[2])])
        with self.assertRaises(ValueError):
            planner.verify_execution_coverage(plan, receipts + [
                {**base, 'kind': 'python', 'execution': 'bad/name', 'test_count': 1}])


class InputInventoryTest(unittest.TestCase):
    def setUp(self):
        self.graph={'core':{'prefix':'addons/core/','depends':{'base'},'file_inputs':[]},
                    'scene':{'prefix':'addons/scene/','depends':{'core'},'file_inputs':['docs/policy.json']},
                    'other':{'prefix':'addons/other/','depends':set(),'file_inputs':[]}}
        paths=['addons/core/model.py','addons/scene/tests/test_scene.py','addons/other/tests/test_other.py',
               'docs/policy.json','docs/narrative.md','scripts/test/test.sh']
        self.entries={path:{'mode':'100644','kind':'blob','oid':str(index+1)*40} for index,path in enumerate(paths)}

    def inventory(self,**kwargs):
        return planner.inventory_from_tree(kwargs.get('graph',self.graph),['scene','other'],kwargs.get('entries',self.entries))

    def test_transitive_sources_and_real_json_are_bound(self):
        result=self.inventory();target=result['targets']['scene']
        self.assertEqual(['core','scene'],target['declared_module_closure'])
        self.assertIn('docs/policy.json',target['input_paths'])
        self.assertIn('addons/core/model.py',target['input_paths'])
        self.assertNotIn('docs/narrative.md',result['files'])
        self.assertNotIn('docs/policy.json',result['targets']['other']['input_paths'])
        self.assertEqual(['base'],target['external_modules'])
        self.assertTrue(target['static_inputs_resolved'])
        self.assertFalse(target['dependency_closure_complete']);self.assertFalse(target['reuse_ready'])
        self.assertIn('dynamic_dependency_closure_not_certified', target['blockers'])

    def test_external_imports_and_sql_reads_are_bound_to_inputs(self):
        graph=copy.deepcopy(self.graph)
        graph['scene'].update(external_imports=['xlrd'], sql_reads=['deadbeef'])
        result=self.inventory(graph=graph)['targets']['scene']
        self.assertEqual(['xlrd'],result['external_imports'])
        self.assertEqual(['deadbeef'],result['sql_reads'])
        self.assertTrue(result['static_inputs_resolved'])
        self.assertFalse(result['dependency_closure_complete'])

    def test_unresolved_import_or_sql_blocks_closure(self):
        for key,blocker in [('unresolved_imports','unresolved_python_imports'),
                            ('unresolved_sql','unresolved_sql_execute_sites')]:
            with self.subTest(key=key):
                graph=copy.deepcopy(self.graph)
                graph['scene'][key]=['addons/scene/models/a.py:9']
                result=self.inventory(graph=graph)['targets']['scene']
                self.assertFalse(result['dependency_closure_complete'])
                self.assertIn(blocker,result['blockers'])

    def test_known_input_changes_only_change_matching_inventory(self):
        before=self.inventory()['targets']
        for changed,affected in [('docs/policy.json',{'scene'}),('addons/core/model.py',{'scene'}),
                                  ('scripts/test/test.sh',{'scene','other'}),('docs/narrative.md',set())]:
            entries=copy.deepcopy(self.entries);entries[changed]['oid']='a'*40
            after=self.inventory(entries=entries)['targets']
            self.assertEqual(affected,{name for name in before if before[name]['known_inputs_sha256']!=after[name]['known_inputs_sha256']})

    def test_missing_unresolved_and_special_inputs_remain_explicit(self):
        graph=copy.deepcopy(self.graph);graph['scene']['unresolved_file_reads']=['addons/scene/tests/test_scene.py:9']
        entries=copy.deepcopy(self.entries);del entries['docs/policy.json'];entries['addons/core/model.py']['mode']='120000'
        result=self.inventory(graph=graph,entries=entries)['targets']['scene']
        self.assertEqual(['docs/policy.json'],result['missing_file_inputs'])
        self.assertEqual(['addons/scene/tests/test_scene.py:9'],result['unresolved_file_reads'])
        self.assertEqual(['addons/core/model.py'],result['special_git_entries'])
        self.assertFalse(result['reuse_ready'])

    def test_cycles_and_order_do_not_change_result(self):
        self.graph['core']['depends'].add('scene')
        first=self.inventory()
        second=planner.inventory_from_tree(dict(reversed(list(self.graph.items()))),['other','scene'],dict(reversed(list(self.entries.items()))))
        self.assertEqual(first,second)

    def test_inventory_does_not_change_existing_selection_or_shards(self):
        graph={'a':{'depends':set(),'prefix':'addons/a/','tests':True}}
        def git(*args):return 'addons/a/tests' if args[0]=='ls-tree' else 'a'*40
        with patch.object(planner.impact,'git',side_effect=git),patch.object(planner.impact,'snapshot',return_value=graph), \
             patch.object(planner,'target_input_inventory',return_value={'diagnostic':True}):
            original=planner.build_plan('','head')
            observed=planner.build_plan('','head',include_inputs=True)
        self.assertEqual({'diagnostic':True},observed.pop('input_inventory'))
        self.assertEqual(original,observed)

    def test_tree_mode_and_blob_are_both_recorded(self):
        raw='100755 blob '+'a'*40+'\taddons/scene/tests/test_scene.py\0'
        with patch.object(planner.impact,'git',return_value=raw):
            result=planner.target_input_inventory('a'*40,self.graph,['scene'])
        self.assertEqual({'mode':'100755','kind':'blob','oid':'a'*40},result['files']['addons/scene/tests/test_scene.py'])
        self.assertFalse(result['reuse_authority'])


class CandidateComparisonTest(unittest.TestCase):
    def setUp(self):
        self.base, self.previous, self.head = 'a'*40, 'b'*40, 'c'*40
        self.plan = {'base': self.base, 'head': self.head, 'modules': ['core', 'scene'],
                     'shards': planner.partition(['core', 'scene'])}
        self.graph = {name: {'prefix': 'addons/'+name+'/', 'depends':set(), 'file_inputs':[]}
                      for name in self.plan['modules']}
        self.entries = {'addons/'+name+'/tests/test_one.py':
                        {'mode':'100644','kind':'blob','oid':'d'*40} for name in self.graph}
        self.before = planner.inventory_from_tree(self.graph, self.plan['modules'], self.entries)
        self.after = copy.deepcopy(self.before)

    def compare(self):
        with patch.object(planner.impact, 'git', side_effect=lambda *args: '1' if args[0]=='rev-list' else '') as git, \
             patch.object(planner.impact, 'snapshot', return_value=self.graph), \
             patch.object(planner, 'target_input_inventory', side_effect=[self.after, self.before]):
            result = planner.compare_previous_candidate(self.plan, self.previous)
        git.assert_any_call('merge-base', '--is-ancestor', self.previous, self.head)
        return result

    def test_distinct_baselines_and_no_ci_selection_mutation(self):
        original = copy.deepcopy(self.plan)
        result = self.compare()
        self.assertEqual(self.plan, original)
        self.assertEqual(self.base, result['integration_base'])
        self.assertEqual(self.previous, result['incremental_base'])
        self.assertFalse(result['execution_selection_changed'])
        self.assertEqual({'RUN':0,'REUSE':0,'BLOCK':2}, result['counts'])

    def test_changed_inputs_require_only_matching_target(self):
        entries = copy.deepcopy(self.entries)
        path = 'addons/scene/tests/test_one.py'; entries[path]['oid']='e'*40
        self.after = planner.inventory_from_tree(self.graph, self.plan['modules'], entries)
        result = self.compare()
        self.assertEqual({'RUN':1,'REUSE':0,'BLOCK':1}, result['counts'])
        row = next(row for row in result['decisions'] if row['target']=='scene')
        self.assertEqual([path], row['changed_known_inputs'])
        self.assertEqual('known_inputs_changed', row['reason'])

    def test_deleted_input_and_file_mode_are_not_equal(self):
        for mode in ('100755', None):
            entries = copy.deepcopy(self.entries); path='addons/core/tests/test_one.py'
            if mode: entries[path]['mode']=mode
            else: del entries[path]
            self.after=planner.inventory_from_tree(self.graph,self.plan['modules'],entries)
            with self.subTest(mode=mode):
                row=self.compare()['decisions'][0]
                self.assertEqual('RUN',row['decision'])
                self.assertEqual([path],row['changed_known_inputs'])

    def test_absent_previous_target_requires_run(self):
        del self.before['targets']['scene']
        row=self.compare()['decisions'][1]
        self.assertEqual('RUN',row['decision'])
        self.assertEqual('no_previous_target',row['reason'])

    def test_inventory_cannot_self_authorize_success_or_reuse(self):
        for target in self.before['targets'].values():
            target.update(status='passed',reuse_ready=True,dependency_closure_complete=True)
        result=self.compare()
        self.assertEqual(0,result['counts']['REUSE'])
        self.assertFalse(result['reuse_authority'])
        self.assertTrue(all(row['previous_receipt'] is None for row in result['decisions']))

    def test_non_exact_or_non_ancestor_candidate_refused(self):
        with self.assertRaises(ValueError):
            planner.compare_previous_candidate(self.plan, 'HEAD~1')
        import subprocess
        with patch.object(planner.impact,'git',side_effect=subprocess.CalledProcessError(1,['git'])):
            with self.assertRaises(subprocess.CalledProcessError):
                planner.compare_previous_candidate(self.plan,self.previous)

    def compare_history(self, history, inventories, distances):
        def git(*args):
            if args[0]=='rev-list':
                return str(distances[args[-1].split('..')[0]])
            return ''
        def inventory(sha, graph, modules):
            return self.after if sha==self.head else inventories[sha]
        with patch.object(planner.impact,'git',side_effect=git), \
             patch.object(planner.impact,'snapshot',return_value=self.graph), \
             patch.object(planner,'target_input_inventory',side_effect=inventory):
            return planner.compare_candidate_history(self.plan,history)

    def test_targets_can_select_different_historical_candidates(self):
        older='e'*40
        recent_entries=copy.deepcopy(self.entries)
        recent_entries['addons/scene/tests/test_one.py']['oid']='f'*40
        older_entries=copy.deepcopy(self.entries)
        older_entries['addons/core/tests/test_one.py']['oid']='f'*40
        histories={self.previous:planner.inventory_from_tree(self.graph,self.plan['modules'],recent_entries),
                   older:planner.inventory_from_tree(self.graph,self.plan['modules'],older_entries)}
        result=self.compare_history([self.previous,older],histories,{self.previous:1,older:3})
        self.assertEqual([self.previous,older],[r['input_comparison_candidate'] for r in result['decisions']])
        self.assertEqual({'RUN':0,'REUSE':0,'BLOCK':2},result['counts'])
        self.assertEqual(self.base,result['integration_base'])

    def test_history_order_and_duplicates_do_not_affect_selection(self):
        older='e'*40
        histories={self.previous:self.before,older:self.before}
        distances={self.previous:1,older:3}
        a=self.compare_history([older,self.previous,older],histories,distances)
        b=self.compare_history([self.previous,older],histories,distances)
        self.assertEqual(a,b)
        self.assertEqual([self.previous,self.previous],[r['input_comparison_candidate'] for r in a['decisions']])

    def test_same_candidate_retry_does_not_fabricate_success(self):
        result=self.compare_history([self.head],{}, {self.head:0})
        self.assertTrue(all(row['same_candidate_retry'] for row in result['decisions']))
        self.assertEqual({'RUN':0,'REUSE':0,'BLOCK':2},result['counts'])
        self.assertFalse(result['previous_candidate_execution_verified'])
        self.assertTrue(all(row['previous_receipt'] is None for row in result['decisions']))

    def test_empty_history_is_not_a_successful_empty_plan(self):
        with self.assertRaises(ValueError):
            planner.compare_candidate_history(self.plan,[])


class HistoricalReceiptSelectionTest(unittest.TestCase):
    def setUp(self):
        self.head='c'*40;self.old='b'*40
        self.plan={'head':self.head,'base':'a'*40,'modules':['core','scene']}
        self.inventory={'targets':{name:{'known_inputs_sha256':fingerprint,'blockers':['scope_not_certified']}
            for name,fingerprint in [('core','d'*64),('scene','e'*64)]}}
        self.results={}

    def locator(self,module,artifact,**overrides):
        return dict({'module':module,'head':self.old,'run_id':10,'attempt':1,'artifact_id':artifact,'shard':0},**overrides)

    def result(self,module,**overrides):
        return dict({'module':module,'source_head':self.old,'integrity':'verified','platform_origin':'verified',
            'scope_plan':{'target':module,'known_inputs_sha256':self.inventory['targets'][module]['known_inputs_sha256']},
            'issued_at':'2026-10-24T10:00:00+00:00','receipt_sha256':'f'*64,
            'actual_duration_seconds':12,'blockers':['environment_not_attested'],'reuse_ready':False},**overrides)

    def select(self,locators):
        def verify(**kwargs):
            value=self.results[kwargs['artifact_id']]
            if isinstance(value,Exception):raise value
            return value
        with patch.object(planner.impact,'git',return_value=''), \
             patch.object(planner.impact,'snapshot',return_value={}), \
             patch.object(planner,'target_input_inventory',return_value=self.inventory), \
             patch.object(planner.execution_receipt,'verify_github_origin',side_effect=verify):
            return planner.select_historical_receipts(self.plan,locators)

    def test_each_target_uses_its_authenticated_history(self):
        self.results={1:self.result('core'),2:self.result('scene',source_head=self.head)}
        rows=[self.locator('core',1),self.locator('scene',2,head=self.head,attempt=2)]
        original=copy.deepcopy(self.plan);result=self.select(rows)
        self.assertEqual(original,self.plan)
        self.assertEqual({'RUN':0,'REUSE':0,'BLOCK':2},result['counts'])
        self.assertEqual([1,2],[r['previous_receipt']['locator']['artifact_id'] for r in result['decisions']])

    def test_failed_or_expired_latest_does_not_hide_older_success(self):
        self.results={1:self.result('core'),2:ValueError('expired or failed attempt')}
        result=self.select([self.locator('core',2,attempt=2),self.locator('core',1)])
        row=result['decisions'][0]
        self.assertEqual(1,row['previous_receipt']['locator']['artifact_id'])
        self.assertEqual(1,len(row['rejected_candidates']))

    def test_matching_input_beats_newer_incompatible_result(self):
        self.results={1:self.result('core'),2:self.result('core',issued_at='2026-10-24T11:00:00+00:00',
            scope_plan={'target':'core','known_inputs_sha256':'0'*64})}
        result=self.select([self.locator('core',2),self.locator('core',1)])
        self.assertEqual(1,result['decisions'][0]['previous_receipt']['locator']['artifact_id'])

    def test_changed_inputs_require_run(self):
        self.results={1:self.result('core',scope_plan={'target':'core','known_inputs_sha256':'0'*64})}
        self.assertEqual('RUN',self.select([self.locator('core',1)])['decisions'][0]['decision'])

    def test_all_rejected_history_blocks_instead_of_green(self):
        self.results={1:ValueError('foreign repository')}
        result=self.select([self.locator('core',1)])
        self.assertEqual('BLOCK',result['decisions'][0]['decision'])
        self.assertEqual('history_authentication_failed',result['decisions'][0]['reason'])

    def test_isolated_authority_matching_receipt_selects_reuse(self):
        self.results={1:self.result('core',isolated_execution_authority='verified_workflow_execution')}
        result=self.select([self.locator('core',1)])
        row=result['decisions'][0]
        self.assertEqual('REUSE',row['decision'])
        self.assertTrue(row['reuse_authorized'])
        self.assertEqual('authenticated_reuse_ready_inputs_match',row['reason'])
        self.assertEqual(12,row['estimated_saved_time'])
        self.assertTrue(result['reuse_authority'])
        self.assertEqual({'RUN':1,'REUSE':1,'BLOCK':0},result['counts'])
        self.assertEqual('RUN',result['decisions'][1]['decision'])

    def test_locator_cannot_supply_verdict_or_escape_target(self):
        for change in ({'reuse_ready':True},{'head':'main'},{'module':'other'},{'attempt':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.select([{**self.locator('core',1),**change}])

    def test_source_authentication_does_not_authorize_reuse(self):
        self.results={1:self.result('core',reuse_ready=True,blockers=[])}
        result=self.select([self.locator('core',1)])
        self.assertFalse(result['reuse_authority'])
        self.assertEqual('BLOCK',result['decisions'][0]['decision'])
        self.assertEqual(0,result['decisions'][0]['estimated_saved_time'])

    def test_apply_reuse_decision_partitions_only_run_and_validates_coverage(self):
        decisions=[{'target':'core','decision':'REUSE'},
                   {'target':'scene','decision':'RUN','previous_actual_duration':20}]
        result=planner.apply_reuse_decision(self.plan,decisions)
        self.assertEqual(['scene'],[m for shard in result['shards'] for m in shard['modules']])
        self.assertEqual(['scene'],result['reuse_decision']['run'])
        self.assertEqual(['core'],result['reuse_decision']['reuse'])
        self.assertTrue(result['reuse_decision']['execution_required'])
        self.assertEqual(['scene'],result['shard_scheduling']['weighted_modules'])

    def test_apply_reuse_decision_all_reuse_has_zero_shards(self):
        decisions=[{'target':'core','decision':'REUSE'},{'target':'scene','decision':'REUSE'}]
        result=planner.apply_reuse_decision(self.plan,decisions)
        self.assertEqual([],result['shards'])
        self.assertFalse(result['reuse_decision']['execution_required'])

    def test_apply_reuse_decision_refuses_blocked_targets(self):
        decisions=[{'target':'core','decision':'BLOCK'},{'target':'scene','decision':'RUN'}]
        with self.assertRaisesRegex(ValueError,'blocked targets'):
            planner.apply_reuse_decision(self.plan,decisions)

    def test_apply_reuse_decision_refuses_incomplete_or_invalid_scope(self):
        for decisions in ([], [{'target':'core','decision':'REUSE'}],
                [{'target':'core','decision':'REUSE'},{'target':'core','decision':'RUN'}],
                [{'target':'core','decision':'RUN'},{'target':'other','decision':'RUN'}],
                [{'target':'core','decision':'MAYBE'},{'target':'scene','decision':'RUN'}]):
            with self.subTest(decisions=decisions):
                with self.assertRaises(ValueError):
                    planner.apply_reuse_decision(self.plan,decisions)

    def test_empty_history_requires_execution_not_zero_test_pass(self):
        self.assertEqual({'RUN':2,'REUSE':0,'BLOCK':0},self.select([])['counts'])


if __name__ == '__main__':
    unittest.main()

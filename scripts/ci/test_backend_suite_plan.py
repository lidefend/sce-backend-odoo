"""Behavioral counterexamples for complete, bounded backend shard selection."""
import unittest
from unittest.mock import patch

import backend_suite_plan as planner


class ShardPlanTest(unittest.TestCase):
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
        self.assertIn('explicit_full', plan['reasons'])

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


if __name__ == '__main__':
    unittest.main()

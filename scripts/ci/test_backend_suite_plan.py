"""Behavioral counterexamples for complete, bounded backend shard selection."""
import unittest
import copy
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
        self.assertFalse(target['dependency_closure_complete']);self.assertFalse(target['reuse_ready'])

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


if __name__ == '__main__':
    unittest.main()

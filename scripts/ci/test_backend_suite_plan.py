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
        decisions=[{'target':'core','decision':'REUSE'},{'target':'scene','decision':'RUN'}]
        result=planner.apply_reuse_decision(self.plan,decisions)
        self.assertEqual(['scene'],[m for shard in result['shards'] for m in shard['modules']])
        self.assertEqual(['scene'],result['reuse_decision']['run'])
        self.assertEqual(['core'],result['reuse_decision']['reuse'])
        self.assertTrue(result['reuse_decision']['execution_required'])

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

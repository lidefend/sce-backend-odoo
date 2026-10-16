"""Execute the diagnostic script against a fake environment; no database needed."""
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('local_dev_runtime_performance.py')


class RuntimeObservationTests(unittest.TestCase):
    def execute(self, mode='observe', case='web_startup', fail=False, baseline=False):
        calls = []
        rollback = []
        cursor = SimpleNamespace(dbname='sc_dev_demo', sql_log_count=0)
        cursor.commit = lambda: None
        cursor.rollback = lambda: rollback.append(True)
        def query(*args, **kwargs):
            cursor.sql_log_count += 1
        cursor.execute = query
        user = SimpleNamespace(active=True, share=False, id=7,
                               company_id=SimpleNamespace(id=1), company_ids=SimpleNamespace(ids=[1]))
        class Environment:
            cr = cursor
            su = False
            def ref(self, xmlid):
                return user
            def __getitem__(self, model):
                return SimpleNamespace(search_count=lambda domain: 3, browse=lambda rid: SimpleNamespace(exists=lambda: SimpleNamespace(res_model="x.test")))
        env = Environment()
        class FakeAppViewConfig:
            def _generate_from_fields_view_get(self, model_name, view_type):
                return SimpleNamespace(get_contract_api=lambda **kwargs: {})
            def _safe_get_view_data(self, *args, **kwargs):
                return {}
            def build_final_contract(self, **kwargs):
                return {}
        class FakeNativeParseService:
            def parse_with_primary_parser(self, *args, **kwargs):
                return {}
        class FakeParseFallbackService:
            def resolve_parsed_contract(self, *args, **kwargs):
                return {}
        class FakePageAssembler:
            include_relation_search_dialogs = True
            def __init__(self, *args, **kwargs):
                pass
            def _inject_relation_entry_contract(self, data, model_name='', stage_timings=None, relation_cache_key=''):
                fields = data.setdefault('fields', {})
                fields.setdefault('partner_id', {'type': 'many2one', 'relation': 'res.partner'})
                declaration = self._relation_demand_declaration(data, model_name=model_name)
                required = declaration['dialog_required_fields']
                projection_cache = {}
                fields['partner_id']['relation_entry'] = self._build_relation_entry_for_field(
                    'partner_id', fields['partner_id'], {},
                    model_name=model_name,
                    relation_projection_cache=projection_cache,
                    include_search_dialog=(
                        self.include_relation_search_dialogs and 'partner_id' in required))
            def _relation_demand_declaration(self, data, model_name='', layout_relation_overrides=None):
                return {
                    'model': model_name,
                    'sources': {'view_fields': ['partner_id'],
                                'explicit_override_fields': [], 'hierarchy_fields': []},
                    'targets': {'partner_id': {'relation': 'res.partner', 'type': 'many2one',
                                               'sources': ['model_field_expansion', 'resolved_view_field'],
                                               'stages': ['permission', 'navigation', 'search_dialog']}},
                    'dialog_required_fields': {'partner_id'},
                }
            def _build_relation_entry_for_field(self, field_name, descriptor, base_entry, model_name='',
                                                contract_context=None, relation_projection_cache=None,
                                                relation_cache_key='', include_search_dialog=True):
                entry = {'field': field_name, 'can_read': True}
                if include_search_dialog:
                    # Mirror the product pipeline: the dialog is cached per relation
                    # target so the baseline reconstruction reuses it instead of
                    # rebuilding a duplicate.
                    cache = relation_projection_cache if isinstance(relation_projection_cache, dict) else {}
                    key = ('search_dialog', descriptor.get('relation'), model_name)
                    dialog = cache.get(key)
                    if not isinstance(dialog, dict):
                        dialog = self._build_relation_search_dialog_contract(
                            descriptor.get('relation'), model_name=model_name)
                        cache[key] = dialog
                    entry['search_dialog'] = dialog
                return entry
            def _build_relation_search_dialog_contract(self, relation, model_name=''):
                FakeAppViewConfig()._generate_from_fields_view_get(relation, 'tree')
                return {'source': 'relation_target_native_view', 'columns': [{'name': 'name'}]}
        self._last_assembler_class = FakePageAssembler
        self._last_stage_classes = (FakeAppViewConfig, FakeNativeParseService, FakeParseFallbackService)
        class Handler:
            def __init__(self, **kwargs):
                pass
            def handle(self, payload):
                calls.append(payload)
                cursor.execute('private query', ['PRIVATE_SECRET'])
                if fail and len(calls) == 2:
                    raise RuntimeError('injected failure')
                if mode in {'relation_attribution', 'relation_stage_probe', 'relation_demand_probe'}:
                    FakePageAssembler()._inject_relation_entry_contract(
                        {'views': [{'type': 'field', 'name': 'partner_id'}], 'context': {}},
                        model_name='payment.request')
                if mode in {'preference_profile', 'preference_compare', 'contract_profile', 'relation_attribution', 'relation_stage_probe', 'relation_demand_probe'}:
                    return {'ok': True, 'data': {'preference': {'hidden_columns': ['PRIVATE_VALUE']}}}
                return SimpleNamespace(ok=True, meta={'startup_profile': {'timings_ms': {'stage': 1}}},
                                       data={'scene_ready_contract': {'scenes': [{'scene': {'key': 'sample'}}]}})
        handler_module = SimpleNamespace(SystemInitHandler=Handler,
                                        _strip_ui_base_contract_for_frontend=lambda value: value)
        modules = {'odoo': SimpleNamespace(api=SimpleNamespace(Environment=lambda *args: env)),
                   'odoo.addons.smart_core.handlers': SimpleNamespace(system_init=handler_module),
                   'odoo.addons.smart_core.handlers.system_init': handler_module,
                   'odoo.addons.smart_core.handlers.ui_contract_v2': SimpleNamespace(UiContractV2Handler=Handler),
                   'odoo.addons.smart_core.handlers.user_view_preference': SimpleNamespace(UserViewPreferenceGetHandler=Handler),
                   'odoo.addons.smart_core.handlers.ui_contract': SimpleNamespace(UiContractHandler=type('UiContractHandler', (), {'read_list_preference_profile': lambda *args: {}})),
                   'odoo.addons.smart_core.core.intent_execution_result': SimpleNamespace(adapt_handler_result=lambda x:x),
                   'odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler': SimpleNamespace(PageAssembler=FakePageAssembler),
                   'odoo.addons.smart_core.app_config_engine.models.app_view_config': SimpleNamespace(AppViewConfig=FakeAppViewConfig),
                   'odoo.addons.smart_core.app_config_engine.services.native_parse_service': SimpleNamespace(NativeParseService=FakeNativeParseService),
                   'odoo.addons.smart_core.app_config_engine.services.parse_fallback_service': SimpleNamespace(ParseFallbackService=FakeParseFallbackService),
                   'odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher': SimpleNamespace(ActionDispatcher=Handler)}
        original_commit = cursor.commit
        output = io.StringIO()
        with patch.dict(sys.modules, modules), patch.dict(os.environ, {
            'PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID': '1',
            'PRODUCT_PERFORMANCE_PREFERENCE_SHA256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
            **{'PRODUCT_PERFORMANCE_' + key + '_SHA256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest() for key in ('UI', 'ASSEMBLER', 'DISPATCHER', 'V2')},
            'PRODUCT_PERFORMANCE_MODE': mode, 'PRODUCT_PERFORMANCE_REQUEST_CASE': case,
            **({'PRODUCT_PERFORMANCE_DEMAND_BASELINE': '1'} if baseline else {}),
            'PRODUCT_PERFORMANCE_HANDLER_SHA256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        }), patch('inspect.getsourcefile', return_value=str(SCRIPT)), contextlib.redirect_stdout(output):
            try:
                runpy.run_path(str(SCRIPT), init_globals={'env': env})
            finally:
                self.assertIs(cursor.commit, original_commit)
                self.assertIs(cursor.execute, query)
                self.assertGreaterEqual(len(rollback), 2)
        self.assertNotIn('PRIVATE_SECRET', output.getvalue())
        return json.loads(output.getvalue().split('=', 1)[1]), calls

    def test_contract_profile_matches_observed_request_and_does_not_export_values(self):
        report, calls = self.execute(mode='contract_profile')
        self.assertEqual(calls, [{'params': {'action_id': 1, 'op': 'action_open'}}] * 2)
        self.assertEqual(report['request_case'], 'action_open_contract')
        self.assertNotIn('PRIVATE_VALUE', json.dumps(report))
        self.assertTrue(report['contract_handler_sha256'])

    def test_contract_profile_failure_rolls_back(self):
        with self.assertRaisesRegex(RuntimeError, 'injected failure'):
            self.execute(mode='contract_profile', fail=True)

    def test_relation_attribution_records_targets_and_restores_owner(self):
        report, calls = self.execute(mode='relation_attribution')
        self.assertEqual(len(calls), 2)
        self.assertEqual(report['request_case'], 'action_open_contract')
        detail = report['companies'][0]['relation_attribution']
        # Two scoped samples, one relation field and one dialog per sample.
        self.assertEqual(detail['inject_count'], 2)
        self.assertEqual(detail['field_count'], 2)
        self.assertEqual(detail['dialog_count'], 2)
        self.assertEqual(detail['dialog_targets'], ['res.partner'])
        self.assertEqual(detail['include_relation_search_dialogs'], [True])
        samples = report['companies'][0]['samples']
        self.assertEqual(samples[0]['relation_attribution']['dialog_targets'], ['res.partner'])
        self.assertEqual(len(samples[1]['relation_attribution']['dialog_calls']), 1)
        field_record = detail and samples[0]['relation_attribution']['field_calls'][0]
        self.assertTrue(field_record['in_main_view'])
        self.assertFalse(field_record['in_hierarchy_dialog'])
        # The diagnostic wrapper must not leave a patched product owner behind.
        owner = getattr(self._last_assembler_class, '_inject_relation_entry_contract')
        self.assertIn('FakePageAssembler', owner.__qualname__)
        self.assertNotIn('PRIVATE_SECRET', json.dumps(report))

    def test_relation_stage_probe_splits_stages_and_restores_owners(self):
        report, calls = self.execute(mode='relation_stage_probe')
        self.assertEqual(report['request_case'], 'action_open_contract')
        probe = report['companies'][0]['stage_probe']
        self.assertEqual(probe['status'], 'observed')
        self.assertEqual(probe['owner_model'], 'x.test')
        # The real assembly runs once under a session frame and records its dialog.
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(probe['dialogs']), 1)
        self.assertEqual(probe['dialogs'][0]['relation'], 'res.partner')
        self.assertGreater(probe['dialogs'][0]['stages']['view_generate']['calls'], 0)
        self.assertGreater(probe['session']['elapsed_ms'], 0)
        self.assertTrue(probe['session']['stages']['view_generate']['calls'] > 0)
        # Ordered isolated probes run every requested target, repeats included.
        isolated = probe['isolated']
        self.assertEqual([row['relation'] for row in isolated],
                         ['res.partner', 'res.currency', 'res.partner', 'res.currency', 'res.users', 'res.users'])
        self.assertTrue(all(row['scope'] == 'isolated' for row in isolated))
        self.assertTrue(all(row['stages'] for row in isolated))
        # The diagnostic must not leave any wrapped product owner behind.
        for owner in (self._last_assembler_class, *self._last_stage_classes):
            for name, value in vars(owner).items():
                if callable(value):
                    self.assertIn(owner.__name__, value.__qualname__)
        self.assertNotIn('PRIVATE_SECRET', json.dumps(report))

    def test_preference_comparison_alternates_six_bounded_calls(self):
        report, calls = self.execute(mode='preference_compare')
        samples = report['companies'][0]['samples']
        self.assertEqual(len(calls), 6)
        self.assertEqual([x['variant'] for x in samples], ['previous', 'candidate', 'candidate', 'previous', 'previous', 'candidate'])
        self.assertEqual(len({x['response_sha256'] for x in samples}), 1)

    def test_relation_demand_probe_binds_declaration_to_materialization(self):
        report, calls = self.execute(mode='relation_demand_probe')
        self.assertEqual(len(calls), 1)
        detail = report['companies'][0]['demand_probe']
        self.assertEqual(detail['status'], 'observed')
        self.assertFalse(detail['baseline_reconstruction'])
        # Declaration -> materialization: the declared dialog field is the one built.
        self.assertEqual(detail['declarations'][0]['dialog_required_fields'], ['partner_id'])
        self.assertEqual(detail['dialog_present_fields'], ['partner_id'])
        self.assertEqual(detail['dialog_build_count'], 1)
        self.assertEqual(detail['relation_field_count'], 1)
        # The diagnostic must not leave a wrapped product owner behind.
        for name in ('_inject_relation_entry_contract', '_build_relation_entry_for_field',
                     '_build_relation_search_dialog_contract', '_relation_demand_declaration'):
            owner = getattr(self._last_assembler_class, name)
            self.assertIn('FakePageAssembler', owner.__qualname__)
        self.assertNotIn('PRIVATE_SECRET', json.dumps(report))

    def test_relation_demand_probe_baseline_reconstruction_restores_dialog(self):
        report, _ = self.execute(mode='relation_demand_probe', baseline=True)
        detail = report['companies'][0]['demand_probe']
        self.assertTrue(detail['baseline_reconstruction'])
        # The reconstructed pipeline re-publishes the dialog for the same field.
        self.assertEqual(detail['dialog_present_fields'], ['partner_id'])
        self.assertEqual(detail['dialog_build_count'], 1)

    def test_preference_profile_failure_restores_cursor_and_rolls_back(self):
        with self.assertRaisesRegex(RuntimeError, 'injected failure'):
            self.execute(mode='preference_profile', fail=True)

    def test_preference_profile_executes_only_two_scoped_reads_without_values(self):
        result = self.execute(mode='preference_profile')
        report, calls = result
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call['params']['preference_key'] == 'list_columns' for call in calls))
        self.assertNotIn('PRIVATE_VALUE', json.dumps(report))
        self.assertEqual(len(report['companies'][0]['samples']), 2)

    def test_cache_state_uses_read_only_authority_and_reports_each_reason(self):
        from unittest.mock import Mock
        tree = ast.parse(SCRIPT.read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'menu_cache_state')
        ns = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SCRIPT), 'exec'), ns)
        model = Mock()
        model.sudo.return_value.with_context.return_value = model
        # Simple real protocol object avoids MagicMock truthiness masking missing rows.
        class Actor:
            lang = 'zh_CN'
            company = SimpleNamespace(id=1)
            context = {}
            def __getitem__(self, key):
                self_key = key
                assert self_key == 'app.menu.config'
                return model
        actor = Actor()
        for cfg, changed, expected in [(None, False, 'missing'),
                (SimpleNamespace(id=2, version=3, last_generated=None, is_active=False), False, 'inactive'),
                (SimpleNamespace(id=2, version=3, last_generated='time', is_active=True), True, 'metadata_changed'),
                (SimpleNamespace(id=2, version=3, last_generated='time', is_active=True), False, 'valid')]:
            model.search.return_value = cfg
            model._menu_metadata_changed_since.return_value = changed
            self.assertEqual(ns['menu_cache_state'](actor)['reason'], expected)
        model._generate_from_menus.assert_not_called()
        model._get_or_generate_from_menus.assert_not_called()

    def test_default_measures_declared_web_registry_request(self):
        report, calls = self.execute()
        self.assertEqual(len(calls), 6)
        self.assertTrue(all(row['params']['scene_ready_mode'] == 'registry' for row in calls))
        self.assertTrue(all(row['params']['with'] == ['workspace_home'] for row in calls))
        self.assertFalse(report['acceptance_pass'])
        self.assertEqual(len(report['companies'][0]['samples']), 6)

    def test_first_profile_has_no_hidden_warmup_and_marks_instrumentation(self):
        report, calls = self.execute(mode='profile_first')
        self.assertEqual(len(calls), 1)
        self.assertTrue(report['companies'][0]['samples'][0]['profiled'])
        self.assertTrue(report['companies'][0]['diagnostic_self_top'])
        self.assertFalse(report['acceptance_pass'])

    def test_full_path_is_explicitly_distinguished(self):
        report, calls = self.execute(case='full_default')
        self.assertEqual(report['request_case'], 'full_default')
        self.assertTrue(all(row['params'] == {} for row in calls))

    def test_sql_diagnostic_is_bounded_and_does_not_export_query_values(self):
        report, calls = self.execute(mode='sql')
        self.assertEqual(len(calls), 2)
        self.assertEqual(sum(row['count'] for row in report['companies'][0]['sql_origins'].values()), 1)

    def test_failure_restores_cursor_and_rolls_back(self):
        with self.assertRaisesRegex(RuntimeError, 'injected failure'):
            self.execute(mode='sql', fail=True)

    def test_browser_identity_rejects_wrong_runtime_without_exposing_environment(self):
        code = r"""
import assert from 'node:assert/strict';
import { validateBackend, requestShape, projectionTiming } from './scripts/verify/local_dev_runtime_performance_browser.mjs';
assert.deepEqual(requestShape({intent:'api.data', params:{model:'payment.request',op:'read',fields:['name'],password:'PRIVATE_SECRET',domain:[['name','=','PRIVATE_SECRET']]}}), {intent:'api.data',model:'payment.request',op:'read',preference_key:null,projection:null,view_type:null,action_id:null,fields:['name']});
assert.deepEqual(projectionTiming({status:'hit',reason:'valid',secret:'PRIVATE_SECRET',stages_ms:{build:3,bad:NaN,negative:-1,secret:'PRIVATE_SECRET'}}), {status:'hit',reason:'valid',stages_ms:{build:3}});
const row = {Id:'fixture',Config:{Labels:{'com.docker.compose.project':'sc-local-dev'},
 Env:['DB_NAME=sc_dev_demo','ODOO_DBFILTER=^sc_dev_demo$','JWT_SECRET=PRIVATE_SECRET']},
 State:{Running:true,StartedAt:'fixture'},Mounts:[{Destination:'/mnt/source-addons',Source:'/fixture/addons'},
 {Destination:'/var/lib/odoo',Name:'sc_local_dev_odoo_data'}]};
assert.equal(validateBackend(row, '/fixture').database, 'sc_dev_demo');
assert.ok(!JSON.stringify(validateBackend(row, '/fixture')).includes('PRIVATE_SECRET'));
for (const change of [r=>r.State.Running=false,r=>r.Config.Env[0]='DB_NAME=other',
 r=>r.Config.Env[1]='ODOO_DBFILTER=.*',r=>r.Mounts[0].Source='/wrong/addons',
 r=>r.Mounts[1].Name='other_volume',r=>r.Config.Labels['com.docker.compose.project']='other']) {
 const bad=structuredClone(row);change(bad);assert.throws(()=>validateBackend(bad,'/fixture'));
}
"""
        result = subprocess.run(['node', '--input-type=module', '-e', code], cwd=SCRIPT.parents[2], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class IntentControllerTimingTests(unittest.TestCase):
    def test_real_router_reports_handler_once_and_preserves_result(self):
        source = SCRIPT.parents[2] / 'addons/smart_core/core/intent_router.py'
        tree = ast.parse(source.read_text())
        methods = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {'_dispatch','route_intent_payload'}]
        clock = [0.0]
        calls = []
        result = {'ok':True, 'data':{'value':'unchanged'}}
        def step(name, duration, value):
            calls.append(name)
            clock[0] += duration
            return value
        class Handler:
            def __init__(self, **kwargs):
                step('construct', .003, None)
            def run(self, **kwargs):
                return step('run', .100, result)
        env = SimpleNamespace(registry='registry',cr=SimpleNamespace(dbname='sc_dev_demo'),uid=7)
        ns = dict(time=SimpleNamespace(perf_counter=lambda:clock[0]),
            request=SimpleNamespace(env=env), HANDLER_REGISTRY={},
            load_extensions=lambda *a:step('extensions',.001,None),
            resolve_handler=lambda i:step('resolve',.002,Handler),
            _build_envs=lambda *a,**kw:step('environment',.004,(env,env,None)),
            preview_write_error=lambda *a,**kw:None, result_is_success=lambda r:True,
            Optional=__import__('typing').Optional, Dict=dict, Any=object)
        exec(compile(ast.Module(body=methods,type_ignores=[]),str(source),'exec'),ns)
        durations = {}
        actual = ns['route_intent_payload']({'intent':'user.view.preference.get'},None,observe=lambda name,duration:durations.update({name:duration}))
        self.assertIs(actual,result)
        self.assertEqual(calls,['extensions','resolve','environment','construct','run'])
        self.assertAlmostEqual(durations['environment'],4)
        self.assertAlmostEqual(durations['handler_run'],100)
        self.assertAlmostEqual(sum(durations.values()),110)

    def test_real_controller_separates_auth_permission_dispatch_and_serialization(self):
        source = SCRIPT.parents[2] / 'addons/smart_core/controllers/intent_dispatcher.py'
        tree = ast.parse(source.read_text())
        owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'IntentDispatcher')
        method = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == 'handle_intent')
        method.decorator_list = []
        clock = [0.0]
        calls = []
        response = SimpleNamespace(headers={})
        def step(name, duration, result):
            calls.append(name)
            clock[0] += duration
            return result
        ctx = SimpleNamespace()
        request = SimpleNamespace(
            httprequest=SimpleNamespace(headers={}, method='POST', get_json=lambda **kw: {'intent':'user.view.preference.get', 'params':{}}),
            session=SimpleNamespace(db='sc_dev_demo'),
            env=SimpleNamespace(cr=SimpleNamespace(dbname='sc_dev_demo')),
            make_json_response=lambda *a, **kw: step('serialize', .04, response))
        from unittest.mock import Mock
        ns = dict(request=request, time=SimpleNamespace(time=lambda:clock[0], perf_counter=lambda:clock[0]),
            get_trace_id=lambda h:'test-trace', _logger=Mock(), _canon_intent=lambda x:x,
            normalize_database_params=lambda p, **kw:(p, kw['effective_db']),
            _is_anon_req=lambda h:False,
            RequestContext=SimpleNamespace(from_payload=lambda p:step('auth', .01, ctx)),
            check_intent_permission=lambda c:step('permission', .02, None),
            route_intent_payload=lambda *a, **kw:step('dispatch', .03, {'ok':True, 'data':{}}),
            _is_response=lambda r:False, _normalize_result_shape=lambda r:r, normalize_result_ok=lambda r:None,
            _cors_headers=lambda:{}, result_http_status=lambda r:200,
            _contract_version_for_intent=lambda i:'1', _schema_version_for_intent=lambda i:'1',
            result_is_success=lambda r:True, result_transaction_action=lambda *a:'none', API_VERSION='v1')
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), ns)
        self.assertIs(ns['handle_intent'](SimpleNamespace()), response)
        self.assertEqual(calls, ['auth','permission','dispatch','serialize'])
        durations = dict((part.split(';dur=')[0], float(part.split(';dur=')[1])) for part in response.headers['Server-Timing'].split(', '))
        self.assertEqual(durations['context_auth'], 10)
        self.assertEqual(durations['permission'], 20)
        self.assertEqual(durations['dispatch'], 30)
        self.assertEqual(durations['json_response'], 40)
        self.assertEqual(sum(durations.values()), 100)


if __name__ == '__main__':
    unittest.main()

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

from scripts.verify import backend_contract_fact_readback_probe as probe

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('readback_lifecycle',ROOT/'addons/smart_core/core/contract_lifecycle.py')
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)


class ReadbackTest(unittest.TestCase):
    def test_observer_sees_actual_post_seal_source_without_changing_result(self):
        source = {'model':'fixture'}
        result = {'actual':'return'}
        def original(owner, source_payload):
            source_payload['runtime_fact'] = 7
            return result
        authority = SimpleNamespace(seal_runtime_contract=original)
        seen = []
        with probe.observe_delivery(authority,lambda args,value:seen.append((dict(args['source_payload']),value))):
            self.assertIs(result,authority.seal_runtime_contract(object(),source))
        self.assertIs(original,authority.seal_runtime_contract)
        self.assertEqual(7,seen[0][0]['runtime_fact'])
        self.assertIs(result,seen[0][1])

    def test_exception_restores_observer_and_preserves_failure(self):
        for at_observer in (True,False):
            def original(owner,source_payload):
                if not at_observer:raise RuntimeError('delivery failed')
                return {}
            def observer(args,result):raise ValueError('bad source')
            authority=SimpleNamespace(seal_runtime_contract=original)
            with self.subTest(observer=at_observer),self.assertRaises((RuntimeError,ValueError)):
                with probe.observe_delivery(authority,observer):authority.seal_runtime_contract(None,{})
            self.assertIs(original,authority.seal_runtime_contract)

    def test_contract_and_source_mutations_are_rejected(self):
        source={'model':'fixture','record':{'id':7,'amount':10}}
        contract=lifecycle.seal_unified_page_contract({'dataContract':{'mainData':{'id':7,'amount':10}}},
                  source_payload=source,source_type='ui.contract',request_id='fixture')
        matched=probe.binding(lifecycle,source,contract)
        self.assertEqual(matched['source_sha256'],contract['meta']['lifecycle']['generation']['sourceSha256'])
        source['record']['amount']=11
        with self.assertRaisesRegex(ValueError,'source fact binding'):probe.binding(lifecycle,source,contract)
        source['record']['amount']=10
        contract['dataContract']['mainData']['amount']=11
        with self.assertRaisesRegex(ValueError,'integrity'):probe.binding(lifecycle,source,contract)

    def test_binding_does_not_return_raw_business_values(self):
        source={'model':'fixture','record':{'private_note':'fixture-no-export'}}
        contract=lifecycle.seal_unified_page_contract({'dataContract':{'mainData':source['record']}},
                  source_payload=source,source_type='ui.contract',request_id='fixture')
        self.assertNotIn('fixture-no-export',str(probe.binding(lifecycle,source,contract)))

    def test_authorization_and_dispatch_use_identical_envelope(self):
        envelope={'intent':'ui.contract.v2','params':{'record_id':7}}
        observed=[]
        def context(actor,user,params,**kwargs):return SimpleNamespace(params=params)
        def permission(ctx):observed.append(ctx.params);return True
        def route(request,ctx):
            self.assertIs(request,ctx.params);observed.append(request);return 'delivered'
        result=probe.authorized_dispatch(None,None,None,envelope,{},context,
              SimpleNamespace(check_intent_permission=permission),SimpleNamespace(route_intent_payload=route))
        self.assertEqual('delivered',result)
        self.assertIs(envelope,observed[0]);self.assertIs(envelope,observed[1])

    def test_denial_never_dispatches(self):
        def context(*args,**kwargs):return None
        def route(*args,**kwargs):self.fail('denied request dispatched')
        with self.assertRaisesRegex(ValueError,'permission denied'):
            probe.authorized_dispatch(None,None,None,{'intent':'ui.contract.v2'},{},context,
                SimpleNamespace(check_intent_permission=lambda ctx:False),SimpleNamespace(route_intent_payload=route))

    def test_wrong_or_absent_target_never_binds_to_selected_record(self):
        source={'model':'fixture'}
        contract={'pageInfo':{'model':'fixture'},'dataContract':{'mainData':{'id':7}}}
        probe.assert_target(source,contract,'fixture',7)
        for row in ({'id':8},{},{'id':True}):
            contract['dataContract']['mainData']=row
            with self.assertRaisesRegex(ValueError,'target mismatch'):probe.assert_target(source,contract,'fixture',7)
        contract['dataContract']['mainData']={'id':7};contract['pageInfo']['model']='other'
        with self.assertRaisesRegex(ValueError,'target mismatch'):probe.assert_target(source,contract,'fixture',7)



    def test_three_way_scalar_value_parity(self):
        metadata={'amount':{'type':'monetary','store':True},'state':{'type':'selection','store':True}}
        values={'id':7,'amount':10.5,'state':'draft'}
        result=probe.value_parity(lifecycle.canonical_json,metadata,values,dict(values),dict(values))
        self.assertEqual(['amount','state'],result['checked_fields'])
        self.assertTrue(result['full_projection_parity'])
        for changed in range(3):
            rows=[dict(values) for _ in range(3)];rows[changed]['amount']=11
            result=probe.value_parity(lifecycle.canonical_json,metadata,*rows)
            self.assertEqual(['amount'],result['mismatch_fields'])
            self.assertEqual('failed',result['status'])

    def test_missing_and_transformed_fields_remain_uncovered(self):
        metadata={'plain':{'type':'char','store':True},'related':{'type':'char','store':True,'related':True},
                  'computed':{'type':'float','store':True,'compute':True},'company':{'type':'char','store':True,'company_dependent':True},
                  'translated':{'type':'char','store':True,'translate':True},'partner':{'type':'many2one','store':True},
                  'missing':{'type':'integer','store':True}}
        values={key:1 for key in metadata};values['plain']='ok';facts=dict(values);del facts['missing']
        result=probe.value_parity(lifecycle.canonical_json,metadata,values,dict(values),facts)
        self.assertEqual(['plain'],result['checked_fields'])
        self.assertEqual(set(metadata)-{'plain'},set(result['uncovered_fields']))
        self.assertFalse(result['full_projection_parity'])

    def test_zero_comparable_fields_never_pass(self):
        with self.assertRaisesRegex(ValueError,'no comparable'):
            probe.value_parity(lifecycle.canonical_json,{}, {'id':7},{'id':7},{'id':7})
        with self.assertRaisesRegex(ValueError,'explicit source'):
            probe.value_parity(lifecycle.canonical_json,{},None,{}, {})

    def test_scalar_types_are_not_coerced_to_hide_mismatch(self):
        metadata={'value':{'type':'integer','store':True}}
        for projected in ('1',True,None,False):
            result=probe.value_parity(lifecycle.canonical_json,metadata,{'value':1},{'value':projected},{'value':1})
            self.assertEqual(['value'],result['mismatch_fields'])

    def test_existing_datetime_delivery_serialization_is_reused(self):
        from datetime import datetime
        metadata={'at':{'type':'datetime','store':True}}
        source={'at':'2026-10-24 00:00:00'}
        facts={'at':datetime(2026,10,24)}
        result=probe.value_parity(lifecycle.canonical_json,metadata,source,dict(source),facts)
        self.assertEqual('passed',result['status'])

    def test_candidate_head_identity_binds_exact_head_and_tree(self):
        self.assertEqual({'source_head':None,'source_tree':None},
                         probe.candidate_head_identity({}))
        identity=probe.candidate_head_identity({'CANDIDATE_GIT_HEAD':'a'*40,'CANDIDATE_GIT_TREE':'b'*40})
        self.assertEqual({'source_head':'a'*40,'source_tree':'b'*40},identity)
        for env in ({'CANDIDATE_GIT_HEAD':'short'},{'CANDIDATE_GIT_TREE':'not-hex'}):
            with self.subTest(env=env):
                with self.assertRaises(ValueError):
                    probe.candidate_head_identity(env)

    def test_candidate_database_resolves_env_over_default(self):
        self.assertEqual(probe.DATABASE,probe.candidate_database({}))
        self.assertEqual(probe.DATABASE,probe.candidate_database({'CANDIDATE_DB_NAME':''}))
        self.assertEqual('sc_demo_suite_ci',probe.candidate_database({'CANDIDATE_DB_NAME':'sc_demo_suite_ci'}))
        with self.assertRaises(ValueError):
            probe.candidate_database({'CANDIDATE_DB_NAME':'not valid!'})

    def test_candidate_role_xmlid_resolves_env_over_default(self):
        self.assertEqual(probe.ROLE_XMLID,probe.candidate_role_xmlid({}))
        self.assertEqual('smart_construction_core.user_demo_role_finance',
                         probe.candidate_role_xmlid({'CANDIDATE_ROLE_XMLID':'smart_construction_core.user_demo_role_finance'}))
        for bad in ({'CANDIDATE_ROLE_XMLID':'no_dot'},{'CANDIDATE_ROLE_XMLID':'Bad.Case'}):
            with self.subTest(env=bad), self.assertRaises(ValueError):
                probe.candidate_role_xmlid(bad)

    def test_candidate_action_xmlid_resolves_env_over_default(self):
        self.assertEqual(probe.ACTION_XMLID,probe.candidate_action_xmlid({}))
        self.assertEqual('smart_construction_core.action_payment_request_pay',
                         probe.candidate_action_xmlid({'CANDIDATE_ACTION_XMLID':'smart_construction_core.action_payment_request_pay'}))
        with self.assertRaises(ValueError):
            probe.candidate_action_xmlid({'CANDIDATE_ACTION_XMLID':'bad action xmlid'})


if __name__ == '__main__':unittest.main()

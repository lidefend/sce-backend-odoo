import hashlib
import json
import os
from contextlib import ExitStack
import tempfile
from pathlib import Path
from unittest import TestCase, main, mock
from scripts.ops import daily_personnel_views as host
from scripts.ops import daily_personnel_views_transaction as tx


class IdentityTests(TestCase):
    def test_other_duty_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'only the demo'):
            host.bound_identity({}, 'platform_control', 'a'*40, 'a'*40)

    def test_candidate_drift_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'SHA mismatch'):
            host.bound_identity({}, 'demo', 'b'*40, 'a'*40)

    def test_wrong_source_root_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'source root'):
            host.bound_identity({'duties':[{'duty':'demo','stack':{'product_root':'/wrong'}}]}, 'demo', 'a'*40, 'a'*40)

    def test_interrupted_json_write_never_publishes_partial_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'apply.json'
            def partial(value, stream, **kwargs):
                stream.write('{')
                raise RuntimeError('interrupted')
            with mock.patch.object(host.json,'dump',side_effect=partial):
                with self.assertRaisesRegex(RuntimeError,'interrupted'):
                    host.save_new(path,{'committed':True})
            self.assertFalse(path.exists())
            host.save_new(path,{'committed':True})
            self.assertEqual(json.loads(path.read_text()),{'committed':True})

    def test_receipt_is_private_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'plan.json'
            host.save_new(p, {'saved':1})
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                host.save_new(p, {'saved':2})
            self.assertIn('1',p.read_text())


class SourceTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'views.xml'
        self.source='<odoo>'+''.join('<record id="%s" model="ir.ui.view"><field name="arch"><%s/></field></record>'%(k.split('.')[1],v) for k,v in tx.VIEW_TYPES.items())+'</odoo>'
        self.path.write_text(self.source)

    def parse(self):
        return tx.source_views(self.path,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_exact_three_views(self):
        self.assertEqual(set(self.parse()),set(tx.VIEW_TYPES))

    def test_digest_mismatch(self):
        with self.assertRaisesRegex(RuntimeError,'digest'):
            tx.source_views(self.path,'0'*64)

    def test_missing_view(self):
        self.path.write_text(self.source.replace('view_sc_runtime_user_tree','other'))
        with self.assertRaisesRegex(RuntimeError,'missing'):
            self.parse()

    def test_wrong_type(self):
        self.path.write_text(self.source.replace('<tree/>','<form/>'))
        with self.assertRaisesRegex(RuntimeError,'type'):
            self.parse()


class TransactionTests(TestCase):
    def setUp(self):
        self.env=mock.MagicMock()
        self.before={'views':{k:{'en_US':'old','zh_CN':'旧'} for k in tx.VIEW_TYPES},'facts':{'res_users':[3,'oldhash']}}
        self.after={'views':{k:{'en_US':'new','zh_CN':'新'} for k in tx.VIEW_TYPES},'facts':self.before['facts']}
        self.snapshot=mock.Mock(return_value=self.after)
        self.validate=mock.Mock()
        self.restore=mock.Mock()
        self.replacements=dict.fromkeys(tx.VIEW_TYPES,'<form/>')

    def apply(self,saved=None):
        return tx.execute_change(self.env,'apply',self.before,saved or self.before,self.replacements,self.snapshot,self.validate,self.restore)

    def test_success_validates_before_commit(self):
        commit = self.env.cr.commit
        self.validate.side_effect=lambda:commit.assert_not_called()
        self.assertEqual(self.apply(),self.after)
        self.env.cr.commit.assert_called_once();self.env.cr.rollback.assert_not_called()

    def test_validation_cannot_commit_early(self):
        self.validate.side_effect=lambda:self.env.cr.commit()
        with self.assertRaisesRegex(RuntimeError,'premature'):self.apply()
        self.env.cr.commit.assert_not_called()
        self.env.cr.rollback.assert_called_once()

    def test_fact_drift_rolls_back(self):
        self.snapshot.return_value={**self.after,'facts':{'res_users':[4,'changed']}}
        with self.assertRaisesRegex(RuntimeError,'facts changed'):self.apply()
        self.env.cr.commit.assert_not_called();self.env.cr.rollback.assert_called_once()

    def test_second_view_error_rolls_back(self):
        self.env.ref.return_value.with_context.return_value.write.side_effect=[None,RuntimeError('second')]
        with self.assertRaisesRegex(RuntimeError,'second'):self.apply()
        self.env.cr.commit.assert_not_called();self.env.cr.rollback.assert_called_once()

    def test_contract_failure_rolls_back(self):
        self.validate.side_effect=RuntimeError('contract')
        with self.assertRaisesRegex(RuntimeError,'contract'):self.apply()
        self.env.cr.commit.assert_not_called();self.env.cr.rollback.assert_called_once()

    def test_commit_failure_is_not_success(self):
        self.env.cr.commit.side_effect=RuntimeError('commit')
        with self.assertRaisesRegex(RuntimeError,'commit'):self.apply()
        self.env.cr.rollback.assert_called_once()

    def test_stale_plan_refuses_all_writes(self):
        with self.assertRaisesRegex(RuntimeError,'drift'):self.apply({**self.before,'facts':{}})
        self.env.ref.assert_not_called();self.env.cr.commit.assert_not_called()

    def test_extra_plan_xmlid_refused(self):
        with self.assertRaisesRegex(RuntimeError,'write set'):self.apply({**self.before,'views':{**self.before['views'],'extra':'x'}})
        self.env.ref.assert_not_called()

    def test_restore_rejects_subsequent_edit(self):
        with self.assertRaisesRegex(RuntimeError,'restore refuses'):
            tx.execute_change(self.env,'restore',self.before,{'before':self.before,'after':self.after},self.replacements,self.snapshot,self.validate,self.restore)
        self.restore.assert_not_called();self.env.cr.commit.assert_not_called()

    def test_restore_preserves_raw_translation_map(self):
        self.snapshot.return_value=self.before
        tx.execute_change(self.env,'restore',self.after,{'before':self.before,'after':self.after},self.replacements,self.snapshot,self.validate,self.restore)
        self.restore.assert_called_once_with(self.before['views'])
        self.env.cr.commit.assert_called_once()


class ConnectionAndReconcileTests(TestCase):
    def test_same_database_different_cluster_refused(self):
        env=mock.MagicMock();env.cr.dbname='same_db'
        env.cr.fetchone.return_value=['old-cluster']
        with self.assertRaisesRegex(RuntimeError,'connected cluster'):
            tx.validate_connection(env, {'dbfilter':'^same_db$'}, dict(database='same_db',dbfilter='^same_db$',system_identifier='new-cluster',database_role='app'))

    def test_effective_dbfilter_refused_before_query(self):
        env=mock.MagicMock();env.cr.dbname='same_db'
        with self.assertRaisesRegex(RuntimeError,'effective dbfilter'):
            tx.validate_connection(env, {'dbfilter':'.*'}, dict(database='same_db',dbfilter='^same_db$'))
        env.cr.execute.assert_not_called()

    def test_wrong_role_refused(self):
        env=mock.MagicMock();env.cr.dbname='same_db';env.cr.fetchone.side_effect=[['cluster'],['other']]
        with self.assertRaisesRegex(RuntimeError,'database role'):
            tx.validate_connection(env, {'dbfilter':'^same_db$'}, dict(database='same_db',dbfilter='^same_db$',system_identifier='cluster',database_role='app'))

    def test_actual_connection_matches(self):
        env=mock.MagicMock();env.cr.dbname='same_db';env.cr.fetchone.side_effect=[['cluster'],['app']]
        tx.validate_connection(env, {'dbfilter':'^same_db$'}, dict(database='same_db',dbfilter='^same_db$',system_identifier='cluster',database_role='app'))

    def setUp(self):
        self.old={'facts':{'users':[2,'h']},'views':{k:{'en_US':'<old/>'} for k in tx.VIEW_TYPES}}
        self.replacements={k:'<%s/>'%v for k,v in tx.VIEW_TYPES.items()}
        self.new={'facts':self.old['facts'],'views':{k:{'en_US':v} for k,v in self.replacements.items()}}

    def test_interrupted_before_commit_identified(self):
        self.assertEqual(tx.reconcile_state(self.old,self.old,self.replacements)['outcome'],'not_committed')

    def test_commit_without_host_receipt_identified(self):
        result=tx.reconcile_state(self.new,self.old,self.replacements)
        self.assertEqual(result['outcome'],'committed_observed')
        self.assertEqual(result['before'],self.old)

    def test_conflicting_partial_state_is_not_success(self):
        self.new['views'][next(iter(tx.VIEW_TYPES))]={'en_US':'<different/>'}
        with self.assertRaisesRegex(RuntimeError,'view conflict'):
            tx.reconcile_state(self.new,self.old,self.replacements)

    def test_fact_change_is_not_success(self):
        self.new['facts']={}
        with self.assertRaisesRegex(RuntimeError,'fact conflict'):
            tx.reconcile_state(self.new,self.old,self.replacements)


class HostInterruptionTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.head='a'*40
        self.ops=self.root/'ops';self.ops.mkdir()
        self.decl=self.root/'config/ops/daily_runtime_database_duties.v1.json';self.decl.parent.mkdir(parents=True)
        self.raw={'duty':'demo','database':'test_db','cluster':{'maintenance_role':'maint','system_identifier':'sys','compose_project':'test'},'stack':{'product_root':str(self.root),'services':['odoo']}}
        self.decl.write_text(json.dumps({'duties':[self.raw],'ops_root':str(self.ops)}))
        xml=self.root/'addons/smart_construction_core/views/support/runtime_user_management_views.xml';xml.parent.mkdir(parents=True);xml.write_text('<odoo/>')
        self.evidence=self.ops/'personnel-view-closeout'/self.head;self.evidence.mkdir(parents=True)
        self.before={'views':{k:{'en_US':'<old/>'} for k in tx.VIEW_TYPES},'facts':{}}
        self.after={'views':{k:{'en_US':'<new/>'} for k in tx.VIEW_TYPES},'facts':{}}
        plan=self.evidence/'plan.json';host.save_new(plan,{'candidate':self.head,'declaration_sha256':host.digest(self.decl),'state':self.before})
        self.argv=['entry','--duty','demo','--expected-sha',self.head,'--declaration-sha256',host.digest(self.decl),'--plan-sha256',host.digest(plan)]
        duty={'database':'test_db','database_role':'app','dbfilter':'^test_db$','database_container':'db','database_volume':'dbvol','odoo_data_volume':'filestore'}
        container={'container':'odoo','container_id':'id','mounts':{'/mnt/source-addons':{'source':str(self.root/'addons')},'/mnt/scripts':{'source':str(self.root/'scripts')},'/var/lib/odoo':{'name':'filestore'}}}
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(host,'ROOT',self.root))
        self.stack.enter_context(mock.patch.object(host.identity,'resolve',return_value=duty))
        self.stack.enter_context(mock.patch.object(host.identity,'duty_env_path',return_value=self.ops/'env'))
        self.stack.enter_context(mock.patch.object(host.runtime,'read_duty_env',return_value={'ODOO_DBFILTER':'^test_db$'}))
        self.stack.enter_context(mock.patch.object(host.runtime,'inspect_odoo_container',return_value=container))
        self.stack.enter_context(mock.patch.dict(os.environ,{'CONFIRM_DAILY_PERSONNEL_VIEWS':'UPDATE_ONLY_THREE_PERSONNEL_VIEWS'}))
        self.program=mock.Mock()
        def run(command,**kwargs):
            if command[0]=='git': return self.head if command[-1]=='HEAD' else ''
            if command[:2]==['docker','inspect']: return json.dumps([{'Mounts':[{'Name':'dbvol','Destination':'/var/lib/postgresql/data'}]}])
            if 'psql' in command:return 'sys'
            return self.program(**kwargs)
        self.stack.enter_context(mock.patch.object(host.runtime,'run',side_effect=run))

    def invoke(self,action):
        with mock.patch('sys.argv',self.argv+['--action',action]):host.main()

    def test_lost_apply_reply_blocks_replay_and_allows_reconcile(self):
        self.program.side_effect=RuntimeError('reply lost after commit')
        with self.assertRaisesRegex(RuntimeError,'reply lost'):self.invoke('apply')
        self.assertTrue((self.evidence/'apply-attempt.json').exists())
        self.assertFalse((self.evidence/'apply.json').exists())
        with self.assertRaises(FileExistsError):self.invoke('apply')
        self.assertEqual(self.program.call_count,1)
        self.program.side_effect=None
        self.program.return_value=host.MARKER+json.dumps({'outcome':'committed_observed','before':self.before,'after':self.after})
        self.invoke('reconcile')
        self.assertTrue((self.evidence/'reconcile-apply.json').exists())
        self.program.return_value=host.MARKER+json.dumps(self.after)
        self.invoke('verify')
        self.assertTrue((self.evidence/'verify-apply.json').exists())


if __name__=='__main__':main()

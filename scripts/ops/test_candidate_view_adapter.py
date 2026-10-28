import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts.ops import candidate_view_adapter as a

OLD = '<tree create="false" edit="false" delete="false"><field name="name"/></tree>'
NEW = OLD.replace('create="false"', 'create="true"')
XML = ('<odoo><record id="view_payment_request_formal_payment_apply_tree" model="ir.ui.view"><field name="arch" type="xml">'+NEW+'</field></record></odoo>').encode()


def fixture():
    candidate={'sha':'a'*40,'image':'ghcr.io/lidefend/sce-product@sha256:'+'b'*64,'frontend_sha256':'c'*64,'xml_sha256':a.digest(XML)}
    target={'registration_id':'candidate-view-unit','database':'sc_candidate_view_unit','uuid':'11111111-1111-4111-8111-111111111111','runtime_sha':candidate['sha'],'image':candidate['image'],'frontend_sha256':candidate['frontend_sha256']}
    snapshot={'source_database':'sc_demo','source_uuid':'22222222-2222-4222-8222-222222222222','source_sha':'d'*40,'database_sha256':'e'*64,'filestore_sha256':'f'*64,'manifest_sha256':'0'*64}
    req={'schema':'candidate_view_request.v1','candidate':candidate,'target':target,'snapshot':snapshot,'view':{'xmlid':a.XMLID,'id':42,'original_arch':OLD,'original_sha256':a.digest(OLD.encode()),'expected_after_state_sha256':'0'*64},'effects':{'before_state_sha256':'0'*64,'recovery_receipt_sha256':'1'*64}}
    before={'target':target,'snapshot':snapshot,'view_matches':[42],'view_arch':OLD,'arch_prev':'previous','view_metadata':{'priority':16},'queue':{'keys':['existing'],'meta':{'added':0}},'assets':[],'cache_state':'before','business_digest':'2'*64,'other_views_digest':'3'*64,'form_binding':{'form_xmlid':'existing.form','default_type':'pay','category':'finance.payment.apply.pay'}}
    after=copy.deepcopy(before);after['view_arch']=a.build_plan(req,XML)['arch'];after['arch_prev']=OLD;after['queue']['meta']={'added':0,'reason':'event:ir.ui.view.write'};after['cache_state']='invalidated'
    req['effects']['before_state_sha256']=a.canonical_hash(before);req['view']['expected_after_state_sha256']=a.canonical_hash(after)
    return req,before,after


class MemoryPort:
    """Unit-only stand-in. No recovery success is inferred from these tests."""
    def __init__(self, req, before, after):
        self.req=req;self.before=before;self.after=after;self.events=[];self.written=False;self.recovered=True
    def source_bytes(self): return XML
    @contextlib.contextmanager
    def exclusive(self):
        self.events.append('lock')
        try: yield
        finally:self.events.append('unlock')
    def registration(self):return self.req['target']
    def recovery_binding(self):return {'request_sha256':a.canonical_hash(self.req),'receipt_sha256':self.req['effects']['recovery_receipt_sha256']} if self.recovered else {}
    def snapshot(self):return copy.deepcopy(self.after if self.written else self.before)
    def orm_write(self, view, vals):
        self.events.append(('orm',view,vals));self.written=True
    def commit(self):self.events.append('commit')
    def rollback(self):self.events.append('rollback')
    def quarantine(self):self.events.append('quarantine')


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.req,self.before,self.after=fixture()
        self.port=MemoryPort(self.req,self.before,self.after)
    def plan(self):return a.build_plan(self.req,XML)
    def rejected(self, change):
        change(self.req)
        with self.assertRaises(a.Refused):self.plan()
        self.assertFalse(self.port.events)
    def test_plan_only_source_data_revision_separate(self):
        p=self.plan();self.assertFalse(p['write_authorized']);self.assertNotEqual(p['request']['candidate']['sha'],p['request']['snapshot']['source_sha'])
    def test_unknown_field_rejected(self):self.rejected(lambda r:r.update(verified=True))
    def test_sha_mismatch(self):self.rejected(lambda r:r['target'].update(runtime_sha='b'*40))
    def test_image_mutable(self):self.rejected(lambda r:r['candidate'].update(image='latest'))
    def test_frontend_mismatch(self):self.rejected(lambda r:r['target'].update(frontend_sha256='e'*64))
    def test_no_historical_uuid_fallback(self):self.rejected(lambda r:r['target'].update(uuid=''))
    def test_original_acceptance_forbidden(self):self.rejected(lambda r:r['target'].update(database='sc_frontend_acceptance'))
    def test_source_target_collision(self):self.rejected(lambda r:r['target'].update(uuid=r['snapshot']['source_uuid']))
    def test_candidate_xml_digest(self):self.rejected(lambda r:r['candidate'].update(xml_sha256='0'*64))
    def test_other_view(self):self.rejected(lambda r:r['view'].update(xmlid='other.view'))
    def test_original_hash(self):self.rejected(lambda r:r['view'].update(original_sha256='0'*64))
    def test_boolean_id(self):self.rejected(lambda r:r['view'].update(id=True))
    def test_missing_snapshot_provenance(self):self.rejected(lambda r:r['snapshot'].pop('manifest_sha256'))
    def test_ambiguous_source(self):
        raw=XML.replace(b'</odoo>',XML[len(b'<odoo>'):]);self.req['candidate']['xml_sha256']=a.digest(raw)
        with self.assertRaisesRegex(a.Refused,'ambiguous'):a.build_plan(self.req,raw)
    def test_scope_cannot_change_edit_or_fields(self):
        for raw in (XML.replace(b'edit="false"',b'edit="true"'),XML.replace(b'name="name"',b'name="other"')):
            self.req['candidate']['xml_sha256']=a.digest(raw)
            with self.assertRaises(a.Refused):a.build_plan(self.req,raw)
    def test_xml_entities_rejected(self):
        raw=b'<!DOCTYPE odoo>'+XML;self.req['candidate']['xml_sha256']=a.digest(raw)
        with self.assertRaises(a.Refused):a.build_plan(self.req,raw)
    def test_bounded_protocol_commits_after_exact_readback(self):
        result=a.execute(self.plan(),self.port)
        self.assertEqual([e if isinstance(e,str) else e[0] for e in self.port.events],['lock','orm','commit','unlock'])
        self.assertEqual(result['after']['form_binding'],self.before['form_binding'])
        self.assertEqual(result['browser_acceptance'],'not_run')
    def test_target_uuid_drift_no_write(self):
        plan=self.plan();self.port.before['target']=dict(self.req['target'],uuid='33333333-3333-4333-8333-333333333333')
        with self.assertRaises(a.Refused):a.execute(plan,self.port)
        self.assertFalse(self.port.written)
    def test_original_arch_drift_no_write(self):
        plan=self.plan();self.before['view_arch']='changed'
        with self.assertRaises(a.Refused):a.execute(plan,self.port)
        self.assertFalse(self.port.written)
    def test_no_or_multiple_matches_no_write(self):
        for matches in ([],[42,43]):
            self.before['view_matches']=matches;self.req['effects']['before_state_sha256']=a.canonical_hash(self.before)
            with self.assertRaisesRegex(a.Refused,'unique'):a.execute(self.plan(),self.port)
            self.assertFalse(self.port.written)
    def test_unverified_recovery_no_write(self):
        self.port.recovered=False
        with self.assertRaisesRegex(a.Refused,'recovery'):a.execute(self.plan(),self.port)
        self.assertFalse(self.port.written)
    def test_post_write_effects_fail_rollback_and_quarantine(self):
        for field in ('business_digest','other_views_digest','queue','assets','arch_prev','form_binding','cache_state'):
            with self.subTest(field=field):
                req,before,after=fixture();after[field]='unexpected';port=MemoryPort(req,before,after)
                with self.assertRaises(a.Refused):a.execute(a.build_plan(req,XML),port)
                self.assertNotIn('commit',port.events);self.assertEqual(port.events[-3:],['rollback','quarantine','unlock'])
    def test_orm_error_not_swallowed(self):
        with patch.object(self.port,'orm_write',side_effect=RuntimeError('ORM failure')):
            with self.assertRaisesRegex(RuntimeError,'ORM failure'):a.execute(self.plan(),self.port)
        self.assertIn('rollback',self.port.events);self.assertIn('quarantine',self.port.events)
    def test_commit_failure_quarantines_indeterminate_state(self):
        with patch.object(self.port,'commit',side_effect=RuntimeError('commit failed')):
            with self.assertRaisesRegex(RuntimeError,'commit failed'):a.execute(self.plan(),self.port)
        self.assertIn('rollback',self.port.events);self.assertIn('quarantine',self.port.events)
    def test_missing_state_witness_rejected_before_write(self):
        self.before.pop('assets');self.req['effects']['before_state_sha256']=a.canonical_hash(self.before)
        with self.assertRaisesRegex(a.Refused,'state witness'):a.execute(self.plan(),self.port)
        self.assertFalse(self.port.written)
    def test_self_signed_plan_not_authority(self):
        plan=self.plan();plan['arch']=NEW.replace('edit="false"','edit="true"');plan['arch_sha256']=a.digest(plan['arch'].encode())
        with self.assertRaises(a.Refused):a.execute(plan,self.port)
        self.assertFalse(self.port.events)
    def test_cli_apply_fails_even_with_valid_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'request.json';p.write_text(json.dumps(self.req))
            with patch.object(a,'read_candidate',return_value=XML),contextlib.redirect_stdout(io.StringIO()) as stdout:
                code=a.main(['apply','--request',str(p)])
            self.assertEqual(code,2);body=json.loads(stdout.getvalue());self.assertIn('runtime_driver_not_supported',body['reason']);self.assertFalse(body['write_attempted'])
    def test_actual_cli_reads_exact_git_blob_and_no_other_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/a.SOURCE;source.parent.mkdir(parents=True);source.write_bytes(XML)
            for args in (['init','-q'],['add','.'],['-c','user.name=Unit','-c','user.email=unit@example.invalid','commit','-qm','fixture']):
                subprocess.run(['git','-C',tmp,*args],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            sha=subprocess.check_output(['git','-C',tmp,'rev-parse','HEAD'],text=True).strip();self.req['candidate']['sha']=sha;self.req['target']['runtime_sha']=sha
            request=root/'request.json';request.write_text(json.dumps(self.req))
            with contextlib.redirect_stdout(io.StringIO()) as out:self.assertEqual(a.main(['plan','--request',str(request),'--repository',tmp]),0)
            self.assertEqual(json.loads(out.getvalue())['request']['candidate']['sha'],sha)
            source.write_bytes(b'not the committed candidate')
            self.assertEqual(a.read_candidate(root,sha,a.SOURCE),XML)


if __name__ == '__main__':unittest.main()

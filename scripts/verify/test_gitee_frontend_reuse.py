import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scripts.ci import gitee_frontend_reuse as reuse
from scripts.ops import gitee_frontend_reuse as publisher


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.identity = dict(repository='leegege/sce-product-odoo', source_branch='fix/test',
                             target_branch='main', head_sha='a'*40, base_sha='b'*40, pr_number=30)
        self.want = dict(schema=reuse.SCHEMA, identity=self.identity, source_tree='c'*40,
                         dependency_key='d'*64, policy_hashes=reuse.policy_hashes(),
                         commands=[['pnpm', '-C', 'frontend/apps/web', s] for s in reuse.STEPS],
                         environment=reuse.environment(), platform=['Linux','x86_64',[3,12]],
                         issuer='owner-ssh-governed-local-execution')
        self.files = {n: b'OK\n' for n in reuse.LOGS}
        self.files['test.log'] = b'Ran 3 tests in 0.01s\nOK\n'
        self.files['build.tar.gz'] = reuse.pack({'index.html': b'<html>fixture</html>', 'assets/a.js': b'fixture'})
        self.receipt = {**self.want, 'status':'passed', 'tests':3,
                        'steps':[{'step':s,'exit_code':0} for s in reuse.STEPS],
                        'dependency_archive_sha256':'e'*64,
                        'log_hashes':{n:reuse.sha(self.files[n]) for n in reuse.LOGS},
                        'artifact':{'sha256':reuse.sha(self.files['build.tar.gz']),
                                    'files':{n:reuse.sha(b) for n,b in reuse.archive_files(self.files['build.tar.gz']).items()}}}
        self.update()

    def update(self):
        self.files['attestation.json'] = reuse.canonical(self.receipt)

    def test_valid_nonzero_receipt(self):
        self.assertEqual(reuse.validate(self.files,self.want)['tests'],3)

    def test_every_identity_dimension_is_bound(self):
        for key,value in [('repository','other/repo'),('source_branch','fix/other'),('target_branch','other'),
                          ('head_sha','f'*40),('base_sha','f'*40),('pr_number',31)]:
            want=copy.deepcopy(self.want);want['identity'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):reuse.validate(self.files,want)

    def test_recipe_environment_tree_dependencies_and_tools_are_bound(self):
        for key in ['commands','environment','source_tree','dependency_key','policy_hashes','platform']:
            want=copy.deepcopy(self.want);want[key]='changed'
            with self.subTest(key=key),self.assertRaises(ValueError):reuse.validate(self.files,want)

    def test_failed_partial_cancelled_receipts_rejected(self):
        for status in ['running','failed','timed_out','cancelled']:
            self.receipt['status']=status;self.update()
            with self.subTest(status=status),self.assertRaises(ValueError):reuse.validate(self.files,self.want)

    def test_missing_or_failed_step_rejected(self):
        for rows in [self.receipt['steps'][:-1],[{'step':s,'exit_code':1} for s in reuse.STEPS]]:
            self.receipt['steps']=rows;self.update()
            with self.assertRaises(ValueError):reuse.validate(self.files,self.want)

    def test_zero_and_all_skipped_tests_rejected_even_with_matching_hash(self):
        for log in [b'Ran 0 tests in 0.1s\nOK',b'Ran 2 tests in 0.1s\nOK (skipped=2)',b'OK']:
            self.files['test.log']=log;self.receipt['log_hashes']['test.log']=reuse.sha(log);self.update()
            with self.assertRaises(ValueError):reuse.validate(self.files,self.want)

    def test_log_tamper_rejected(self):
        self.files['build.log']=b'changed'
        with self.assertRaises(ValueError):reuse.validate(self.files,self.want)

    def test_artifact_tamper_rejected(self):
        self.files['build.tar.gz']=reuse.pack({'index.html':b'changed'})
        with self.assertRaises(ValueError):reuse.validate(self.files,self.want)

    def test_missing_or_extra_files_rejected(self):
        for files in [{k:v for k,v in self.files.items() if k!='build.log'}, {**self.files,'extra':b'x'}]:
            with self.assertRaises(ValueError):reuse.validate(files,self.want)

    def test_archive_escape_links_and_duplicate_names_rejected(self):
        for name,link,duplicate in [('../escape',False,False),('/absolute',False,False),('link',True,False),('same',False,True)]:
            data=io.BytesIO()
            with tarfile.open(fileobj=data,mode='w:gz') as tf:
                m=tarfile.TarInfo(name)
                if link:m.type=tarfile.SYMTYPE;m.linkname='/etc/passwd'
                else:m.size=1
                tf.addfile(m,None if link else io.BytesIO(b'x'))
                if duplicate:tf.addfile(m,io.BytesIO(b'y'))
            with self.subTest(name=name),self.assertRaises(ValueError):reuse.archive_files(data.getvalue())

    def test_build_must_exist_and_have_nonempty_index(self):
        dist=self.root/'dist';dist.mkdir()
        with self.assertRaises(ValueError):reuse.build_archive(dist,self.root)
        (dist/'index.html').write_text('fixture');(dist/'link').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):reuse.build_archive(dist,self.root)

    def test_build_parent_symlink_cannot_read_host_fixture(self):
        private=self.root/'host-fixture';(private/'dist').mkdir(parents=True)
        (private/'dist/index.html').write_text('must not be exported')
        work=self.root/'work';(work/'frontend/apps').mkdir(parents=True)
        (work/'frontend/apps/web').symlink_to(private)
        with self.assertRaisesRegex(ValueError,'reuse_build_parent'):
            reuse.build_archive(work/'frontend/apps/web/dist',work)

    def test_oversized_build_rejected_before_reading_file(self):
        dist=self.root/'dist';dist.mkdir();p=dist/'index.html'
        with p.open('wb') as f:f.truncate(reuse.LIMIT+1)
        with patch.object(Path,'read_bytes',side_effect=AssertionError('unbounded read')),self.assertRaisesRegex(ValueError,'reuse_build_size'):
            reuse.build_archive(dist,self.root)

    def install(self,data=None):
        data=data or reuse.pack(self.files)
        with patch.object(reuse.os,'geteuid',return_value=0),patch.object(reuse,'trusted'):
            return reuse.install(data,reuse.sha(data),self.root/'store')

    def test_append_atomic_install_and_same_bundle_idempotence(self):
        self.assertEqual(self.install()['status'],'installed')
        self.assertEqual(self.install()['status'],'already_installed')
        folder=self.root/'store'/reuse.identity_key(self.identity)
        self.assertEqual(set(p.name for p in folder.iterdir()),set(reuse.FILES))
        self.assertFalse(list((self.root/'store').glob('.publish-*')))

    def test_existing_different_payload_never_overwritten(self):
        self.install();self.files['lint-src.log']=b'new valid run'
        self.receipt['log_hashes']['lint-src.log']=reuse.sha(self.files['lint-src.log']);self.update()
        with self.assertRaises(ValueError):self.install()

    def test_unprivileged_install_cannot_publish(self):
        data=reuse.pack(self.files)
        with patch.object(reuse.os,'geteuid',return_value=1000),self.assertRaises(ValueError):
            reuse.install(data,reuse.sha(data),self.root/'store')
        self.assertFalse((self.root/'store').exists())

    def test_corrupt_transport_is_rejected_before_write(self):
        with patch.object(reuse.os,'geteuid',return_value=0),self.assertRaises(ValueError):
            reuse.install(b'bad','f'*64,self.root/'store')
        self.assertFalse((self.root/'store').exists())

    def test_untrusted_symlink_and_writable_storage_rejected(self):
        link=self.root/'link';link.symlink_to('missing')
        with self.assertRaises(ValueError):reuse.trusted(link)
        p=self.root/'writable';p.write_text('x');p.chmod(0o666)
        with self.assertRaises(ValueError):reuse.trusted(p)

    def test_consumer_validates_then_falls_back_on_tamper(self):
        self.install()
        with patch.object(reuse,'expected',return_value=self.want),patch.object(reuse,'trusted'):
            self.assertEqual(reuse.consume(self.root,self.identity,self.root/'store')['status'],'verified_local_execution')
            folder=self.root/'store'/reuse.identity_key(self.identity)
            (folder/'test.log').write_text('tamper')
            self.assertEqual(reuse.consume(self.root,self.identity,self.root/'store')['status'],'fallback')

    def test_missing_evidence_falls_back(self):
        with patch.object(reuse,'expected',return_value=self.want):
            self.assertEqual(reuse.consume(self.root,self.identity,self.root/'absent')['reason'],'receipt_missing')

    def test_real_seal_consumes_build_and_execution_logs(self):
        work=self.root/'work';dist=work/'frontend/apps/web/dist';dist.mkdir(parents=True)
        (dist/'index.html').write_text('built fixture')
        attempt=self.root/'attempt';attempt.mkdir()
        for name in reuse.LOGS:(attempt/name).write_bytes(self.files[name])
        result={'status':'passed','archive_sha256':'e'*64,
                'steps':[{'step':s,'exit_code':0,**({'python_tests':3} if s=='test' else {})} for s in reuse.STEPS]}
        reuse.seal(work,attempt,result,self.want)
        files=reuse.archive_files((attempt/'reuse-bundle.tar.gz').read_bytes())
        self.assertEqual(reuse.validate(files,self.want)['tests'],3)

    def test_publisher_cannot_upload_a_previous_receipt_without_running_verifier(self):
        with patch.object(publisher,'assert_clean'),patch.object(publisher,'expected',return_value=self.want), \
             patch.object(publisher,'verify',side_effect=ValueError('actual verifier failed')) as verify, \
             patch.object(publisher.subprocess,'run') as run:
            with self.assertRaises(ValueError):publisher.publish(self.root,self.root,'node',self.identity,apply=True)
            verify.assert_called_once();run.assert_not_called()

    def test_preview_never_executes_or_publishes(self):
        with patch.object(publisher,'assert_clean'),patch.object(publisher,'expected',return_value=self.want), \
             patch.object(publisher,'verify') as verify:
            self.assertEqual(publisher.publish(self.root,self.root,'node',self.identity)['writes'],0)
            verify.assert_not_called()

    def test_policy_binds_execution_dependencies(self):
        hashes=reuse.policy_hashes()
        for name in ['scripts/ci/gitee_ci_acceptance.py','scripts/ci/gitee_formal_executor.py',
                     'scripts/ci/gitee_frontend_reuse.py','scripts/ops/gitee_frontend_reuse.py',
                     'scripts/ops/gitee_frontend_cache.py']:
            self.assertEqual(len(hashes[name]),64)

    def test_remote_bootstrap_loads_only_active_installed_controller(self):
        command=publisher.remote_command('f'*64)
        self.assertIn('/etc/gitee-ci/sce-product-odoo-worker.env',command)
        self.assertIn('/opt/gitee-ci/formal/',command)
        self.assertNotIn(str(self.root),command)
        with self.assertRaises(ValueError):publisher.remote_command('bad; command')


if __name__=='__main__':unittest.main()

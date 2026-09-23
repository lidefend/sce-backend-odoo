import base64
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from scripts.ops.gitee_ci_incremental_update import Update, MODULES, INSTALL, ENVS, UNIT, CREDENTIALS, DB, UNITS, digest, env_update


class FakeUpdate(Update):
    def __init__(self, root):
        super().__init__(root);self.calls=[];self.fail_probe=False;self.fail_start=False;self.corrupt_backup=False
        self.states={u:'active' for u in UNITS};self.mirror='inactive';self.package_installed=False
    def token_metadata(self): return {"mode":0o600,"uid":os.getuid(),"gid":os.getgid()}
    def run(self,*args):
        self.calls.append(args)
        if args[:2]==('systemctl','show'):
            if 'UnitFileState' in args[3]:return 'disabled'
            return self.states.get(args[2],self.mirror)
        if args[:2]==('systemctl','stop'):self.states[args[2]]='inactive'
        if args[:2]==('systemctl','start'):
            if self.fail_start:raise RuntimeError('injected startup failure')
            self.states[args[2]]='active'
        return ''
    def install_package(self):self.package_installed=True
    def probe(self):
        if self.fail_probe:raise RuntimeError('unsupported sandbox')
    def backup(self,desired):
        folder,manifest=super().backup(desired)
        if self.corrupt_backup:
            (folder/'0').write_bytes(b'corrupt')
        return folder,manifest


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.u=FakeUpdate(Path(self.tmp.name))
        for path in [*(INSTALL+n for n in MODULES),*ENVS,UNIT,*CREDENTIALS,DB]:self.u.path(path).parent.mkdir(parents=True,exist_ok=True)
        self.u.path(INSTALL+MODULES[0]).write_bytes(b'old-worker')
        for f in ENVS:self.u.path(f).write_bytes(b'# preserved\nGITEE_WEBHOOK_SECRET=test-only-secret\nGIT_SSH_COMMAND=fixed\nCUSTOM_SETTING=keep\nGITEE_MIRROR_SOURCE_REPO=/var/lib/gitee-mirror/source.git\n')
        self.u.path(UNIT).write_bytes(b'[Service]\nReadWritePaths=/var/lib/gitee-ci /var/log/gitee-ci /var/lib/gitee-mirror/source.git\nNoNewPrivileges=true\n')
        for f in CREDENTIALS:self.u.path(f).write_bytes(b'test-only-credential');self.u.path(f).chmod(0o400)
        with sqlite3.connect(self.u.path(DB)) as db:db.execute('CREATE TABLE jobs(status TEXT)')
        self.payload={'source_sha':'a'*40,'modules':{n:{'content':base64.b64encode(('new-'+n).encode()).decode(),'sha256':digest(('new-'+n).encode())} for n in MODULES}}
        self.before={f:self.u.path(f).read_bytes() for f in [INSTALL+MODULES[0],*ENVS,UNIT,*CREDENTIALS]}
    def apply(self):return self.u.apply(self.payload,self.u.plan(self.payload)['plan_sha256'],'APPLY_REVIEWED_CI_INCREMENTAL_UPDATE')
    def assert_restored(self):
        for f,data in self.before.items():self.assertEqual(self.u.path(f).read_bytes(),data,f)
        for name in MODULES[1:]:self.assertFalse(self.u.path(INSTALL+name).exists())
        self.assertTrue(all(s=='inactive' for s in self.u.states.values()))
    def test_plan_no_mutation_or_secret_values(self):
        before=list(self.u.root.rglob('*'));r=self.u.plan(self.payload)
        self.assertEqual(before,list(self.u.root.rglob('*')))
        self.assertEqual(r['writes'],0);self.assertNotIn('test-only-secret',json.dumps(r))
        self.assertFalse(self.u.package_installed)
    def test_install_preserves_credentials_and_unrelated_configuration(self):
        r=self.apply();self.assertEqual(r['status'],'installed')
        for f in CREDENTIALS:self.assertEqual(self.u.path(f).read_bytes(),self.before[f]);self.assertEqual(self.u.path(f).stat().st_mode&0o777,0o400)
        for f in ENVS:
            text=self.u.path(f).read_text();self.assertIn('CUSTOM_SETTING=keep',text);self.assertIn('GITEE_WEBHOOK_SECRET=test-only-secret',text);self.assertIn('GITEE_CI_MODE=ci-only',text)
        self.assertNotIn('GITEE_MIRROR_SOURCE_REPO',self.u.path(ENVS[1]).read_text())
        self.assertTrue((Path(r['backup'])/'queue.sqlite3').is_file())
        self.assertTrue(all('runner' not in ' '.join(c) for c in self.u.calls))
    def test_plan_drift_rejected_before_stop(self):
        plan=self.u.plan(self.payload);self.u.path(ENVS[0]).write_bytes(b'changed')
        with self.assertRaises(ValueError):self.u.apply(self.payload,plan['plan_sha256'],'APPLY_REVIEWED_CI_INCREMENTAL_UPDATE')
        self.assertFalse(any(c[:2]==('systemctl','stop') for c in self.u.calls))
    def test_credential_drift_invalidates_approved_plan(self):
        plan=self.u.plan(self.payload)
        self.u.path(CREDENTIALS[0]).chmod(0o600)
        with self.assertRaises(ValueError):self.u.apply(self.payload,plan['plan_sha256'],'APPLY_REVIEWED_CI_INCREMENTAL_UPDATE')
        self.assertFalse(self.u.package_installed)

    def test_backup_preserves_original_bytes_and_integrity(self):
        desired=self.u.desired(self.payload);folder,manifest=self.u.backup(desired)
        for f,entry in manifest.items():
            if entry['metadata']: self.assertEqual((folder/entry['file']).read_bytes(),self.before[f])
        with sqlite3.connect(folder/'queue.sqlite3') as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertEqual(folder.stat().st_mode&0o777,0o700)

    def test_remote_readonly_program_compiles_without_running_cli(self):
        from scripts.ops import gitee_ci_incremental_update as module
        source=Path(module.__file__).read_text().rsplit("\nif __name__ == '__main__':",1)[0]
        compile(source+'\nprint("plan")\n','remote-plan','exec')

    def test_wrong_confirmation(self):
        with self.assertRaises(ValueError):self.u.apply(self.payload,self.u.plan(self.payload)['plan_sha256'],'yes')
        self.assertFalse(self.u.package_installed)
    def test_active_mirror_rejected(self):
        self.u.mirror='active'
        with self.assertRaises(ValueError):self.apply()
        self.assertFalse(self.u.package_installed)
    def test_queued_jobs_rejected(self):
        with sqlite3.connect(self.u.path(DB)) as db:db.execute("INSERT INTO jobs VALUES ('pending')")
        with self.assertRaises(ValueError):self.apply()
        self.assertFalse(self.u.package_installed)
    def test_sandbox_failure_restores_without_fallback(self):
        self.u.fail_probe=True
        with self.assertRaises(RuntimeError):self.apply()
        self.assert_restored();self.assertFalse(any(c[:2]==('systemctl','start') for c in self.u.calls))
    def test_start_failure_restores_files_and_leaves_stopped(self):
        self.u.fail_start=True
        with self.assertRaises(RuntimeError):self.apply()
        self.assert_restored()
    def test_corrupt_backup_never_claims_restoration(self):
        self.u.corrupt_backup=True;self.u.fail_start=True
        with self.assertRaises(ValueError):self.apply()
        self.assertTrue(all(s=='inactive' for s in self.u.states.values()))
    def test_module_digest_and_scope(self):
        self.payload['modules'][MODULES[0]]['sha256']='0'*64
        with self.assertRaises(ValueError):self.u.plan(self.payload)
    def test_symlink_rejected(self):
        p=self.u.path(ENVS[0]);p.unlink();p.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):self.u.plan(self.payload)
    def test_checks_token_plan_omits_value_and_install_private(self):
        from scripts.ops.gitee_ci_incremental_update import CHECKS_TOKEN
        self.payload['checks_token']=base64.b64encode(b'fixture-checks-token-only').decode()
        plan=self.u.plan(self.payload)
        self.assertNotIn('fixture-checks-token-only',json.dumps(plan))
        self.apply()
        self.assertEqual(self.u.path(CHECKS_TOKEN).read_bytes(),b'fixture-checks-token-only\n')
        self.assertEqual(self.u.path(CHECKS_TOKEN).stat().st_mode&0o777,0o600)
        self.assertIn(b'GITEE_CHECKS_TOKEN_FILE=',self.u.path(ENVS[1]).read_bytes())
        self.assertNotIn(b'GITEE_CHECKS_TOKEN_FILE=',self.u.path(ENVS[0]).read_bytes())
        worker=self.u.path(ENVS[1]).read_bytes()
        self.assertEqual(worker,env_update(worker,worker=True))
        self.assertEqual(self.u.desired(self.payload)[ENVS[1]],worker)
    def test_failed_checks_install_restores_and_removes_new_token(self):
        from scripts.ops.gitee_ci_incremental_update import CHECKS_TOKEN
        self.payload['checks_token']=base64.b64encode(b'fixture-checks-token-only').decode()
        self.u.fail_start=True
        with self.assertRaises(RuntimeError): self.apply()
        self.assert_restored();self.assertFalse(self.u.path(CHECKS_TOKEN).exists())
    def test_token_rotation_failure_restores_old_private_file(self):
        from scripts.ops.gitee_ci_incremental_update import CHECKS_TOKEN
        p=self.u.path(CHECKS_TOKEN);p.write_bytes(b'old-fixture-token');p.chmod(0o600)
        self.payload['checks_token']=base64.b64encode(b'fixture-checks-token-only').decode()
        self.u.fail_start=True
        with self.assertRaises(RuntimeError): self.apply()
        self.assertEqual(p.read_bytes(),b'old-fixture-token');self.assertEqual(p.stat().st_mode&0o777,0o600)

    def test_env_patch_idempotence_and_preservation(self):
        source=b'# keep\nOTHER=hello\nGITEE_CI_MODE=legacy\n'
        changed=env_update(source);self.assertEqual(changed,env_update(changed));self.assertIn(b'OTHER=hello\n',changed)

if __name__=='__main__':unittest.main()

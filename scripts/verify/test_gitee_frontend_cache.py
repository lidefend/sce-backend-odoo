import json
from pathlib import Path
import tempfile
import subprocess
import tarfile
import io
import os
import time
from scripts.ci.gitee_ci_acceptance import Executor, Interrupted
import unittest
from scripts.ops.gitee_frontend_cache import inputs, key, extract_pnpm, prepare, attempt_receipt, unpack_dependencies

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.fe=self.root/'frontend';self.fe.mkdir()
        (self.fe/'package.json').write_text(json.dumps({'packageManager':'pnpm@9.12.3'}))
        (self.fe/'pnpm-lock.yaml').write_text('lockfileVersion: 9.0')
        (self.fe/'pnpm-workspace.yaml').write_text('packages:\n  - apps/*\n  - packages/*\n')
        (self.fe/'apps/web').mkdir(parents=True)
        (self.fe/'apps/web/package.json').write_text('{}')
    def test_input_drift_changes_key(self):
        for name in ('pnpm-lock.yaml','pnpm-workspace.yaml','apps/web/package.json'):
            before=key(inputs(self.root));f=self.fe/name;old=f.read_text()
            f.write_text(old+' ');self.assertNotEqual(before,key(inputs(self.root)));f.write_text(old)
    def test_extra_workspace_is_bound(self):
        before=key(inputs(self.root));d=self.fe/'packages/new';d.mkdir(parents=True)
        (d/'package.json').write_text('{}');self.assertNotEqual(before,key(inputs(self.root)))
    def test_pnpm_version_rejected(self):
        (self.fe/'package.json').write_text('{"packageManager":"pnpm@10"}')
        with self.assertRaises(ValueError):inputs(self.root)
    def test_hooks_and_config_rejected(self):
        for name in ('.npmrc','.pnpmfile.cjs','pnpmfile.cjs'):
            f=self.fe/'apps/web'/name;f.write_text('')
            with self.subTest(name=name),self.assertRaises(ValueError):inputs(self.root)
            f.unlink()
    def test_external_dependency_rejected(self):
        for value in ('file:../../../private','link:/private','git+https://example.test/repo','https://example.test/a.tgz'):
            (self.fe/'apps/web/package.json').write_text(json.dumps({'dependencies':{'x':value}}))
            with self.subTest(value=value),self.assertRaises(ValueError):inputs(self.root)
    def test_workspace_dependency_allowed(self):
        (self.fe/'apps/web/package.json').write_text('{"dependencies":{"@sc/ui":"workspace:*"}}')
        self.assertIn('frontend/apps/web/package.json',inputs(self.root)['files'])
    def test_package_names_containing_file_are_allowed(self):
        (self.fe/"pnpm-lock.yaml").write_text("  excludeLinksFromLockfile: false\n  isbinaryfile: 5.0.2\n  jsonfile: 6.2.1")
        self.assertTrue(inputs(self.root))
    def test_tarball_lock_rejected(self):
        (self.fe/'pnpm-lock.yaml').write_text('tarball: https://example.test/a')
        with self.assertRaises(ValueError):inputs(self.root)
    def test_symlink_input_rejected(self):
        f=self.fe/'pnpm-lock.yaml';f.unlink();f.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):inputs(self.root)
    def test_wrong_archive_rejected_before_extract(self):
        f=self.root/'fake.tgz';f.write_bytes(b'not a package');dest=self.root/'out'
        with self.assertRaises(ValueError):extract_pnpm(f,dest)
        self.assertFalse(dest.exists())
    def test_timeout_receipt_is_new_and_terminal(self):
        old=self.root/'verification.json';old.write_text('{"status":"passed"}')
        result={}
        with self.assertRaises(subprocess.TimeoutExpired):
            with attempt_receipt(self.root,result) as attempt:
                (attempt/'test.log').write_text('partial')
                raise subprocess.TimeoutExpired('fixture',1)
        saved=json.loads((attempt/'verification.json').read_text())
        self.assertEqual(saved['status'],'timed_out')
        self.assertIn('test.log',saved['log_hashes'])
        self.assertEqual(json.loads(old.read_text())['status'],'passed')
        self.assertNotEqual(attempt,self.root)
    def test_count_failure_cannot_retain_pass(self):
        result={'status':'passed'}
        with self.assertRaises(ValueError):
            with attempt_receipt(self.root,result) as attempt:raise ValueError('zero')
        self.assertEqual(json.loads((attempt/'verification.json').read_text())['status'],'failed')

    def test_unrecognized_workspace_patterns_rejected(self):
        (self.fe/'pnpm-workspace.yaml').write_text('packages: [external/*]')
        with self.assertRaises(ValueError):inputs(self.root)
    def bundle(self,name,link=None):
        path=self.root/'bundle.tgz'
        with tarfile.open(path,'w:gz') as tf:
            m=tarfile.TarInfo(name)
            if link is not None:m.type=tarfile.SYMTYPE;m.linkname=link;tf.addfile(m)
            else:m.size=1;tf.addfile(m,io.BytesIO(b'x'))
        return path
    def test_archive_cannot_overlay_source(self):
        path=self.bundle('frontend/src/source.js')
        with self.assertRaises(ValueError):unpack_dependencies(path,self.root,['frontend/node_modules'])
        self.assertFalse((self.fe/'src').exists())
    def test_existing_dependency_symlink_rejected(self):
        (self.fe/'node_modules').symlink_to('missing-target')
        path=self.bundle('frontend/node_modules/x.js')
        with self.assertRaises(ValueError):unpack_dependencies(path,self.root,['frontend/node_modules'])
    def test_external_link_rejected(self):
        path=self.bundle('frontend/node_modules/x','../../../../etc/passwd')
        with self.assertRaises(ValueError):unpack_dependencies(path,self.root,['frontend/node_modules'])
    def test_valid_dependency_extract(self):
        path=self.bundle('frontend/node_modules/x.js')
        unpack_dependencies(path,self.root,['frontend/node_modules'])
        self.assertEqual((self.fe/'node_modules/x.js').read_bytes(),b'x')

    def test_real_sandbox_timeout_kills_background_child(self):
        marker=self.root/'escaped'
        script="import subprocess,time;subprocess.Popen(['python3','-c',\"import time,pathlib;time.sleep(0.5);pathlib.Path('/work/escaped').write_text('x')\"]);time.sleep(10)"
        command=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session',
                 '--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib',
                 '--symlink','usr/lib64','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp',
                 '--bind',str(self.root),'/work','python3','-c',script]
        with (self.root/'process.log').open('wb') as log,self.assertRaises(Interrupted) as caught:
            Executor(self.root).command(command,self.root,log,lambda:False,time.monotonic()+.15,{'PATH':'/usr/bin:/bin'})
        self.assertEqual(caught.exception.status,'timed_out');time.sleep(.6)
        self.assertFalse(marker.exists())

    def test_output_scope_rejected(self):
        with self.assertRaises(ValueError):prepare(self.root,self.root/'outside','unused','unused','unused')

if __name__=='__main__':unittest.main()

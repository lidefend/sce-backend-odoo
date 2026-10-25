import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.dev import local_test_runner as runner


class LocalTestRunnerTest(unittest.TestCase):
    def profile_file(self, root, **changes):
        values = dict(runner.IDENTITY, SC_ENVIRONMENT='dev', DB_PASSWORD='private', ADMIN_PASSWD='private', JWT_SECRET='private')
        values.update(changes)
        path = Path(root) / '.env.local.test'
        path.write_text(''.join(f'{key}={value}\n' for key,value in values.items()))
        path.chmod(0o600)
        return path

    def test_exact_registered_profile_and_legacy_purpose_are_read_only(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.profile_file(root)
            before = path.read_bytes()
            with patch.object(runner, 'PROFILE', path):
                self.assertEqual(runner.profile(path)['DB_NAME'], 'sc_test')
            self.assertEqual(before, path.read_bytes())

    def test_foreign_identity_rejected_before_any_docker_command(self):
        for key in runner.IDENTITY:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as root:
                path = self.profile_file(root, **{key:'foreign'})
                with patch.object(runner, 'PROFILE', path), patch.object(runner, 'command') as command:
                    self.assertEqual(runner.main(['test','--env-file',str(path),'--module','smart_core']),2)
                    command.assert_not_called()

    def test_missing_module_rejected_before_profile_or_docker(self):
        with patch.object(runner, 'profile') as profile, patch.object(runner, 'command') as command:
            self.assertEqual(runner.main(['test']),2)
            profile.assert_not_called()
            command.assert_not_called()

    def test_foreign_file_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.profile_file(root)
            with self.assertRaises(ValueError): runner.profile(path)
            alias = Path(root)/'alias';alias.symlink_to(path)
            with patch.object(runner,'PROFILE',alias), self.assertRaises(ValueError): runner.profile(alias)

    def test_shell_payload_duplicate_and_readable_secret_file_rejected(self):
        for extra in ('X=$(touch /tmp/never)\n', 'DB_NAME=sc_test\n'):
            with tempfile.TemporaryDirectory() as root:
                path=self.profile_file(root);path.write_text(path.read_text()+extra)
                with patch.object(runner,'PROFILE',path),self.assertRaises(ValueError): runner.profile(path)
        with tempfile.TemporaryDirectory() as root:
            path=self.profile_file(root);path.chmod(0o644)
            with patch.object(runner,'PROFILE',path),self.assertRaises(ValueError): runner.profile(path)

    def test_module_and_tags_cannot_inject_shell(self):
        for module,tags in [('smart_core;true',''),('smart_core','$(id)'),('../smart_core',''),('missing_module','')]:
            with self.subTest(module=module,tags=tags),self.assertRaises(ValueError): runner.selection(module,tags)
        self.assertEqual(runner.selection('smart_core',''),('smart_core','/smart_core'))

    def test_nonzero_unique_case_identities_and_module_are_required(self):
        line='2026-10-26 00:00:00,000 1 INFO sc_test odoo.addons.smart_core.tests.test_example: Starting Example.test_one ...\n'
        self.assertEqual(runner.outcome(line,'smart_core'),['smart_core.tests.test_example:Example.test_one'])
        for text in ('',line+line,line.replace('sc_test','sc_dev_demo'),line.replace('smart_core','other')):
            with self.assertRaises(ValueError): runner.outcome(text,'smart_core')

    def test_make_and_environment_overrides_do_not_reach_compose(self):
        with tempfile.TemporaryDirectory() as root:
            path=self.profile_file(root)
            with patch.object(runner,'PROFILE',path), patch.dict(runner.os.environ,{'DB_NAME':'sc_dev_demo','MAKEFLAGS':'DB_NAME=sc_dev_demo','MAKEOVERRIDES':'DB_NAME=sc_dev_demo','COMPOSE_PROJECT_NAME':'foreign','COMPOSE_FILE':'foreign.yml'}),patch.object(runner,'command',side_effect=ValueError('stop')) as command:
                self.assertEqual(runner.main(['prepare','--env-file',str(path)]),2)
                argv,env=command.call_args.args
                self.assertEqual(env['DB_NAME'],'sc_test')
                self.assertEqual(env['SC_ENVIRONMENT'],'test')
                for key in ('MAKEFLAGS','MAKEOVERRIDES','COMPOSE_FILE'): self.assertNotIn(key,env)
                self.assertIn('sc-local-test',argv)


    def test_cleanup_only_removes_exact_owned_carrier_and_checks_absence(self):
        from types import SimpleNamespace
        name='sc-local-test-attempt-123'
        row={'Name':'/'+name,'Id':'exact-id','Config':{'Labels':{'com.docker.compose.project':'sc-local-test','com.docker.compose.service':'odoo'}}}
        replies=[name,json.dumps([row]),'', '']
        with patch.object(runner,'command',side_effect=[SimpleNamespace(stdout=x) for x in replies]) as command:
            self.assertEqual(runner.cleanup_carrier(name,{}),'removed_exact_carrier')
            self.assertEqual(command.call_args_list[2].args[0],['docker','rm','-f','exact-id'])
        row['Config']['Labels']['com.docker.compose.project']='sc-local-dev'
        with patch.object(runner,'command',side_effect=[SimpleNamespace(stdout=name),SimpleNamespace(stdout=json.dumps([row]))]) as command:
            with self.assertRaises(ValueError): runner.cleanup_carrier(name,{})
            self.assertEqual(command.call_count,2)

    def test_source_fingerprint_detects_untracked_changes_deletions_and_mode(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); f=root/'test.py';f.write_text('first')
            with patch.object(runner,'ROOT',root),patch.object(runner,'command',return_value=SimpleNamespace(stdout='test.py\0new.py\0')):
                before=runner.source_fingerprint({})
                (root/'new.py').write_text('new');self.assertNotEqual(before,runner.source_fingerprint({}))
                before=runner.source_fingerprint({});f.chmod(0o755);self.assertNotEqual(before,runner.source_fingerprint({}))
                before=runner.source_fingerprint({});f.unlink();self.assertNotEqual(before,runner.source_fingerprint({}))

if __name__=='__main__': unittest.main()

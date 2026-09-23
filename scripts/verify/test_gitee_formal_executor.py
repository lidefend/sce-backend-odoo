import copy
import os
import json
import subprocess
import time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.ci.gitee_formal_executor import FormalExecutor, recipes, nonzero_tests, verify_snapshot, IDENTITY_KEYS
from scripts.ci.gitee_gate_plan import plan, digest


class LocalExecutor(FormalExecutor):
    # These process tests use generated sandbox fixtures rather than a release
    # checkout. Selection and real-Git manifests are tested independently.
    def validate_selection(self, candidate): pass
    def validate_paths(self, workspace, candidate): pass

    def checkout(self, workspace, sha, log, cancelled, deadline):
        (workspace/'repo').mkdir()
        self.workspace = workspace
        return sha

    def command(self, args, *a, **kw):
        if args[:2] == ['git', 'merge-base']: return 0
        return super().command(args, *a, **kw)


class FormalTests(unittest.TestCase):
    def candidate(self):
        p = plan(head='a'*40, base='b'*40, source_branch='fix/unit', pr_number=1, paths=['docs/unit.md'])
        p['source_hashes'] = {}
        p.pop('plan_sha256'); p['plan_sha256'] = digest(p)
        return p

    def run_case(self, script, *, timeout=10, refresh=None, cancel=lambda:False):
        p = self.candidate()
        snapshot = {k:p[k] for k in IDENTITY_KEYS}
        snapshot.update(pr_identity_verified=True, remote_refs_verified=True)
        with tempfile.TemporaryDirectory() as root:
            executor = LocalExecutor(Path(root)/'logs', timeout=timeout)
            with patch('scripts.ci.gitee_formal_executor.recipes', return_value=[(['python3','-c',script],True)]):
                result = executor.execute_plan(p, refresh or (lambda:snapshot), cancel)
            self.assertFalse(executor.workspace.exists())
            return result

    def test_real_sandbox_credentials_network_and_counts(self):
        script = """import os,pathlib,socket
assert 'PRIVATE_TEST_TOKEN' not in os.environ
assert os.environ['GOMEMLIMIT'] == '256MiB'
assert os.environ['GOMAXPROCS'] == '2'
assert os.environ['MAKEFLAGS'] == '-j1'
assert os.environ['NODE_OPTIONS'] == '--max-old-space-size=2048'
assert not pathlib.Path('/etc/gitee-ci').exists()
assert not pathlib.Path('/var/run/docker.sock').exists()
try: socket.create_connection(('1.1.1.1',443),timeout=.1)
except OSError: pass
else: raise AssertionError('network escaped')
print('Ran 2 tests in 0.001s')
print('OK')
"""
        with patch.dict(os.environ, PRIVATE_TEST_TOKEN='synthetic-private-token',
                        GOMEMLIMIT='off', GOMAXPROCS='64', MAKEFLAGS='-j64',
                        NODE_OPTIONS='--max-old-space-size=8192'):
            result = self.run_case(script)
        self.assertEqual(result['status'],'success')
        self.assertEqual([x['tests'] for x in result['checks']],[2]*4)
        self.assertFalse(result['integration_eligible'])

    def test_zero_tests_rejected(self):
        self.assertNotEqual(self.run_case("print('Ran 0 tests in 0.001s')")['status'],'success')

    def test_failed_command_not_success(self):
        result = self.run_case("print('Ran 2 tests in 0.001s');raise SystemExit(1)")
        self.assertEqual(result['status'],'failed')
        self.assertTrue(all(x['status']=='failed' for x in result['checks']))

    def test_timeout(self):
        self.assertEqual(self.run_case('import time;time.sleep(10)',timeout=.15)['status'],'timed_out')

    def test_cancel(self):
        self.assertEqual(self.run_case("print('Ran 1 test in 0.1s')",cancel=lambda:True)['status'],'cancelled')

    def test_late_base_change_invalidates_results(self):
        p=self.candidate(); s={k:p[k] for k in IDENTITY_KEYS}
        s.update(pr_identity_verified=True,remote_refs_verified=True)
        changed={**s,'base_sha':'c'*40}; samples=iter([s,changed])
        result=self.run_case("print('Ran 1 test in 0.001s')",refresh=lambda:next(samples))
        self.assertEqual(result['status'],'environment_error')

    def test_corrupt_plan_rejected_before_checkout(self):
        p=self.candidate();p['base_sha']='c'*40
        with tempfile.TemporaryDirectory() as root, self.assertRaises(ValueError):
            LocalExecutor(root).execute_plan(p,lambda:{})

    def test_counts_nonzero_and_not_all_skipped(self):
        for text in ['', 'Ran 0 tests in 1s', 'Ran 2 tests in 1s\nOK (skipped=2)',
                     'Ran 2 tests in 1s\nRan 0 tests in 1s']:
            with self.subTest(text=text),self.assertRaises(ValueError): nonzero_tests(text)
        self.assertEqual(nonzero_tests('Ran 3 tests in 1s\nOK (skipped=1)'),2)

    def test_full_and_frontend_lanes_not_downgraded(self):
        for name,mode in [('professional_quality_gate','full'),('frontend_release_gate','full')]:
            with self.subTest(name=name,mode=mode),self.assertRaises(ValueError): recipes(name,mode,'a'*40)

    def test_standard_frontend_commands_preserve_required_steps(self):
        commands=recipes('frontend_release_gate','standard','a'*40)
        self.assertEqual([c[-1] for c,_ in commands[1:]],['lint:src','typecheck:strict','test','build'])
        self.assertTrue(commands[3][1])
    def test_standard_frontend_quality_preserves_workflow_guards(self):
        commands=recipes("professional_quality_gate","standard_frontend","a"*40)
        flat=" ".join(" ".join(c) for c,_ in commands)
        for target in ["frontend_professional_extension_guard.py", "test_ci_risk_classifier.py",
                       "test_github_actions_security_guard.py", "verify.product.release.version",
                       "ci.generated_reports.guard", "architecture.complexity_baseline_lock"]:
            self.assertIn(target,flat)
        self.assertTrue(any(test for _,test in commands))

    def test_supported_backend_recipe_keeps_all_required_targets(self):
        commands=recipes('professional_quality_gate','standard_backend','a'*40)
        flat=' '.join(' '.join(c) for c,_ in commands)
        for target in ['test.unit','test.contract','test.e2e.preflight','verify.tenant.payload_boundary',
                       'ci.generated_reports.guard','architecture.complexity_baseline_lock']:
            self.assertIn(target,flat)
        self.assertTrue(commands[0][1])

    def test_forged_modes_and_source_hashes_rejected(self):
        p=plan(head='a'*40,base='b'*40,source_branch='fix/unit',pr_number=1,paths=['scripts/ci/unit.py'])
        with tempfile.TemporaryDirectory() as root:
            executor=FormalExecutor(root)
            executor.validate_selection(p)
            for key, value in [('checks',[]),('source_hashes',{}),('toolchain',{})]:
                altered=copy.deepcopy(p);altered[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError): executor.validate_selection(altered)

    def test_checkout_uses_policy_approved_remote_name(self):
        from scripts.verify.repository_clean_history_guard import remote_errors
        from scripts.ci.gitee_ci_acceptance import REMOTE
        root=Path(__file__).resolve().parents[2]
        policy=json.loads((root/'config/security/repository_clean_history_policy.v1.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            workspace=Path(temp);executor=FormalExecutor(workspace/'logs');seen=[]
            def command(args,*unused):
                seen.append(args)
                if args[1]=='clone':
                    subprocess.run(['git','init',str(workspace/'repo')],check=True,capture_output=True)
                    subprocess.run(['git','-C',str(workspace/'repo'),'remote','add',args[3],args[-2]],check=True)
                if args[-3:-1]==['checkout','--detach']:
                    (workspace/'repo/.git/HEAD').write_text(args[-1]+'\n')
                return 0
            with patch.object(executor,'command',side_effect=command), (workspace/'log').open('wb') as log:
                self.assertEqual(executor.checkout(workspace,'a'*40,log,lambda:False,time.monotonic()+5),'a'*40)
            self.assertEqual(remote_errors(workspace/'repo',policy['allowed_remotes']),set())
            self.assertIn('gitee-mirror',seen[1])

    def test_static_guards_are_not_test_counts(self):
        commands=recipes('public_guard','required','a'*40)
        self.assertTrue(any(is_test for _,is_test in commands))
        self.assertTrue(any(not is_test for _,is_test in commands))


if __name__=='__main__': unittest.main()

from pathlib import Path
import subprocess
import os
import tempfile
import unittest
from scripts.dev.local_environment_readiness import inspect_profile, evaluate, PROFILES


class LocalReadinessTest(unittest.TestCase):
    def observe(self, name='clean', prepared=False, resource=False, failed_inventory=False, health=0, wrong_profile=False, duplicate=False, extra_line=""):
        calls = []
        def runner(args):
            calls.append(args)
            if args[0] == 'docker':
                return subprocess.CompletedProcess(args, 1 if failed_inventory else 0,
                                                   'existing\n' if resource else '', '')
            return subprocess.CompletedProcess(args, health, 'private output must not escape', '')
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory) / '.env'
            if prepared:
                project, database, prefix, _ = PROFILES[name]
                values = dict(ENV='dev', COMPOSE_PROJECT_NAME=project, DB_NAME=database,
                              ODOO_DBFILTER=f'^{database}$', DB_DATA=f'{prefix}_db_data',
                              REDIS_DATA=f'{prefix}_redis_data', ODOO_DATA=f'{prefix}_odoo_data',
                              ISOLATED_REHEARSAL_DATABASE='1', TECHNICAL_SAMPLE_DATABASE='1')
                if wrong_profile:
                    values['DB_NAME'] = 'sc_other_isolated'
                content = '\n'.join(f'{k}={v}' for k,v in values.items())+'\nSECRET=never_print\n'
                if duplicate:
                    content += 'DB_NAME=sc_clean\n'
                env.write_text(content + extra_line + "\n")
            row = inspect_profile(name, env, Path(directory), runner)
        return row, calls

    def test_optional_absence_is_not_a_runtime_pass(self):
        row, calls = self.observe()
        self.assertEqual(row['status'], 'not_prepared')
        self.assertEqual(row['health'], 'not_run')
        self.assertTrue(evaluate([row]))
        self.assertEqual(len(calls), 4)

    def test_required_absence_fails(self):
        row, _ = self.observe(name='dev')
        self.assertFalse(evaluate([row]))

    def test_missing_authority_with_stopped_resources_fails(self):
        row, calls = self.observe(resource=True)
        self.assertEqual(row['reason'], 'credential_authority_missing_with_existing_resources')
        self.assertIn('-a', calls[0])
        self.assertFalse(evaluate([row]))

    def test_docker_failure_is_not_absence(self):
        row, calls = self.observe(failed_inventory=True)
        self.assertEqual(row['reason'], 'resource_inventory_failed')
        self.assertFalse(evaluate([row]))
        self.assertEqual(len(calls), 1)

    def test_governed_health_failure_blocks(self):
        row, _ = self.observe(prepared=True, health=2)
        self.assertEqual(row['health'], 'failed')
        self.assertFalse(evaluate([row]))

    def test_exact_health_entry_and_env_binding(self):
        row, calls = self.observe(prepared=True, resource=True)
        self.assertEqual(row['status'], 'passed')
        self.assertIn('local.clean.health', calls[-1])
        self.assertTrue(calls[-1][-1].startswith('LOCAL_CLEAN_ENV_FILE='))
        self.assertNotIn('private', str(row))
        self.assertNotIn('never_print', str(row))

    def test_inventory_exact_resources_and_no_write_commands(self):
        _, calls = self.observe(name='sample')
        self.assertIn('label=com.docker.compose.project=sc-local-sample', calls[0])
        for part, call in zip(('db', 'redis', 'odoo'), calls[1:]):
            self.assertIn(f'name=^sc_local_sample_{part}_data$', call)
            self.assertEqual(call[:3], ['docker', 'volume', 'ls'])

    def test_other_clean_environment_cannot_impersonate_canonical_profile(self):
        row, calls = self.observe(prepared=True, wrong_profile=True)
        self.assertEqual(row['reason'], 'profile_identity_mismatch')
        self.assertFalse(evaluate([row]))
        self.assertFalse(any(call[0] == 'make' for call in calls))

    def test_duplicate_identity_is_rejected_before_health(self):
        row, calls = self.observe(prepared=True, duplicate=True)
        self.assertEqual(row['reason'], 'ambiguous_profile_identity')
        self.assertFalse(any(call[0] == 'make' for call in calls))

    def test_export_whitespace_cannot_hide_identity_override(self):
        for prefix in ('  export ', 'export\t'):
            with self.subTest(prefix=prefix):
                row, calls = self.observe(prepared=True, extra_line=prefix+'DB_NAME=sc_other')
                self.assertEqual(row['reason'], 'ambiguous_profile_identity')
                self.assertFalse(any(call[0] == 'make' for call in calls))

    def test_executable_env_cannot_override_identity(self):
        for line in ('source another.env', 'X=$(export DB_NAME=sc_other)', 'X=ok; DB_NAME=sc_other'):
            with self.subTest(line=line):
                row, calls = self.observe(prepared=True, extra_line=line)
                self.assertEqual(row['reason'], 'unsupported_environment_syntax')
                self.assertFalse(any(call[0] == 'make' for call in calls))

    def test_aggregate_failure_cannot_be_hidden_by_optional_absence(self):
        self.assertFalse(evaluate([{'status':'passed'}, {'status':'not_prepared'}, {'status':'failed'}]))


class ReadinessMakeWiringTest(unittest.TestCase):
    def test_governed_make_entry_passes_all_profile_authorities(self):
        repository = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / 'bin'
            fake_bin.mkdir()
            python = fake_bin / 'python3'
            python.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$TRACE"\n')
            python.chmod(0o755)
            harness = root / 'Makefile'
            harness.write_text(f'include {repository}/make/dev.mk\nguard.prod.forbid:\n\t@:\n')
            trace = root / 'trace'
            env_files = {name: root / f'{name}.env' for name in ('dev', 'sample', 'clean')}
            args = ['make', '--no-print-directory', '-f', str(harness), 'local.env.readiness', f'ROOT_DIR={repository}']
            args += [f'LOCAL_{name.upper()}_ENV_FILE={path}' for name, path in env_files.items()]
            result = subprocess.run(args, cwd=repository, env={**os.environ, 'PATH':str(fake_bin)+os.pathsep+os.environ['PATH'], 'TRACE':str(trace)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            actual = trace.read_text().splitlines()
            self.assertEqual(actual[:3], ['scripts/dev/local_environment_readiness.py', '--root', str(repository)])
            for name, path in env_files.items():
                self.assertEqual(actual[actual.index(f'--{name}-env')+1], str(path))


class AuthorityProbeNoDependencyMutationTest(unittest.TestCase):
    def test_actual_shell_entry_does_not_start_or_recreate_dependencies(self):
        script = Path(__file__).resolve().parents[2] / 'scripts/dev/local_dev_demo_authority_verify.sh'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            common = root / 'scripts/common'
            common.mkdir(parents=True)
            (common / 'env.sh').write_text('DB_NAME=sc_dev_demo\nDB_USER=synthetic\nDB_PASSWORD=synthetic\nODOO_CONF=/synthetic.conf\nADDONS_EXTERNAL_MOUNT=/synthetic\n')
            (common / 'guard_prod.sh').write_text('guard_prod_forbid() { :; }\n')
            (common / 'demo_data_guard.sh').write_text('guard_demo_data_scope() { :; }\n')
            (common / 'compose.sh').write_text('compose_dev() { printf "%s\\n" "$@" > "$TRACE"; cat >/dev/null; }\n')
            preflight = root / 'scripts/dev/local_dev_demo_authority_preflight.py'
            preflight.parent.mkdir(parents=True)
            preflight.write_text('# synthetic read-only probe\n')
            trace = root / 'trace'
            result = subprocess.run(['bash', str(script)], env={**os.environ, 'ROOT_DIR':str(root), 'TRACE':str(trace)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = trace.read_text().splitlines()
            self.assertEqual(args[:4], ['run', '--rm', '-T', '--no-deps'])
            self.assertNotIn('up', args)
            self.assertNotIn('restart', args)


if __name__ == '__main__':
    unittest.main()

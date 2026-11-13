"""Refusal boundaries for pristine CI preparation; no business database needed."""
import tempfile
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import types

from scripts.test import dependency_baseline as baseline


class PreparationTests(unittest.TestCase):
    def environment(self):
        return dict(GITHUB_RUN_ID='12', GITHUB_RUN_ATTEMPT='1', SHARD_INDEX='0',
                    SOURCE_SHA='a'*40, COMPOSE_PROJECT_NAME='sc-suite-12-0',
                    SC_ENVIRONMENT='test', SC_TEST_TARGET_MODULE='portal',
                    SC_TEST_TARGET_DB='sc_suite_ci_portal')

    def test_exact_run_identity_changes_with_candidate_attempt_and_shard(self):
        env = self.environment()
        original = baseline.identity(env)
        for key, value in [('SOURCE_SHA', 'b'*40), ('GITHUB_RUN_ATTEMPT', '2')]:
            self.assertNotEqual(original, baseline.identity(dict(env, **{key: value})))
        self.assertNotEqual(original, baseline.identity(dict(env, SHARD_INDEX='1', COMPOSE_PROJECT_NAME='sc-suite-12-1')))

    def test_reject_persistent_demo_wrong_target_and_unknown_identity(self):
        for key, value in [('COMPOSE_PROJECT_NAME', 'sc-local-test'),
                           ('SC_ENVIRONMENT', 'demo'), ('SC_ALLOW_DEMO_DATA', '1'),
                           ('SC_TEST_TARGET_DB', 'sc_dev_demo'),
                           ('SC_TEST_TARGET_DB', 'sc_suite_ci_other'),
                           ('SC_TEST_TARGET_MODULE', 'portal;DROP'),
                           ('GITHUB_RUN_ID', ''), ('SOURCE_SHA', 'unknown')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                baseline.identity(dict(self.environment(), **{key: value}))

    def test_retry_has_distinct_target_and_same_pristine_baseline(self):
        env = self.environment()
        self.assertEqual(baseline.identity(env), baseline.identity(dict(env, SC_TEST_TARGET_DB='sc_suite_ci_portal_retry1')))

    def test_only_transitive_industry_consumers_use_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, dependencies in [('wrapper', ['middle']), ('middle', [baseline.CORE]), ('other', ['base']), ('cycle', ['cycle'])]:
                (root/name).mkdir()
                (root/name/'__manifest__.py').write_text(repr({'depends': dependencies}))
            self.assertTrue(baseline.eligible('wrapper', (root,)))
            for name in ('other', 'cycle', baseline.CORE, 'smart_construction_demo'):
                self.assertFalse(baseline.eligible(name, (root,)))

    def test_demo_bypasses_preparation_even_with_its_separate_authority(self):
        with patch.object(baseline, 'identity', side_effect=AssertionError('must remain fresh')):
            baseline.prepare({'SC_TEST_TARGET_MODULE': 'smart_construction_demo'})

    def test_ambiguous_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            roots = [Path(folder)/'a', Path(folder)/'b']
            for root in roots:
                (root/'wrapper').mkdir(parents=True)
                (root/'wrapper'/'__manifest__.py').write_text(repr({'depends': [baseline.CORE]}))
            with self.assertRaises(ValueError):
                baseline.eligible('wrapper', roots)


    def test_pristine_baseline_installed_once_and_filestore_clones_are_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            existing, queries, installs = set(), [], []
            cursor = MagicMock()
            result = []
            def execute(query, parameters=None):
                queries.append(str(query))
                result.clear()
                if str(query).startswith('SELECT datname'):
                    result.extend((name,) for name in parameters if name in existing)
                elif str(query).startswith('SELECT name'):
                    result.extend([(baseline.CORE, 'installed'), (parameters[1], 'uninstalled')])
            cursor.execute.side_effect = execute
            cursor.fetchall.side_effect = lambda: list(result)
            connection = MagicMock()
            connection.cursor.return_value.__enter__.return_value = cursor
            connection.__enter__.return_value = connection
            driver = types.ModuleType('psycopg2')
            driver.connect = MagicMock(return_value=connection)
            driver.sql = MagicMock()
            def install(command, **kwargs):
                installs.append(command)
                db = command[command.index('-d')+1]
                existing.add(db)
                (data/'filestore'/db).mkdir(parents=True)
                (data/'filestore'/db/'attachment').write_text('pristine')
                return types.SimpleNamespace(returncode=0)
            env = dict(self.environment(), DB_USER='odoo', DB_PASSWORD='unused-fixture')
            with patch.dict('sys.modules', {'psycopg2': driver}), patch.object(baseline, 'DATA', data), patch.object(baseline, 'eligible', return_value=True), patch.object(baseline.subprocess, 'run', side_effect=install):
                baseline.prepare(env)
                (data/'filestore'/env['SC_TEST_TARGET_DB']/'attachment').write_text('test mutation')
                second = dict(env, SC_TEST_TARGET_MODULE='seed', SC_TEST_TARGET_DB='sc_suite_ci_seed')
                baseline.prepare(second)
                self.assertEqual((data/'filestore'/second['SC_TEST_TARGET_DB']/'attachment').read_text(), 'pristine')
                self.assertEqual(len(installs), 1)
                self.assertNotIn('--test-enable', installs[0])
                self.assertFalse(any(x.startswith('--test-tags') for x in installs[0]))
                self.assertEqual(installs[0][installs[0].index('-i')+1], baseline.CORE)
                # The same target cannot be overwritten after it has run tests.
                with self.assertRaises(ValueError):
                    baseline.prepare(env)
                # Missing provenance must never adopt an arbitrary existing DB.
                next((data/'ci-dependency-preparation').glob('*.json')).unlink()
                with self.assertRaises(ValueError):
                    baseline.prepare(dict(env, SC_TEST_TARGET_MODULE='new', SC_TEST_TARGET_DB='sc_suite_ci_new'))


    def test_real_shell_gate_disables_preparation_for_explicit_test_tags(self):
        script = (Path(__file__).with_name('test.sh')).read_text()
        fragment = script.split('PREPARATION_ARGS=()', 1)[1].split('RUN_RM=', 1)[0]
        env = dict(os.environ, SC_TEST_DEPENDENCY_PREPARATION='1', ROOT_DIR='/fixture',
                   MODULE='portal', DB_NAME='sc_suite_ci_portal', COMPOSE_PROJECT_NAME='sc-suite-12-0',
                   ADDONS_EXTERNAL_MOUNT='/fixture/external')
        for override in ('', 'sc_gate/smart_construction_core,sc_gate/portal', 'sc_gate'):
            with self.subTest(override=override):
                result = subprocess.run(['bash', '-eu', '-c', 'PREPARATION_ARGS=()\n' + fragment
                                         + '\nprintf "%s" "$PREPARATION_COMMAND"'],
                                        env=dict(env, TEST_TAGS_INPUT=override), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(bool(result.stdout), not bool(override))


if __name__ == '__main__':
    unittest.main()

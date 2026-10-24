import re
import os
import subprocess
import tempfile
from pathlib import Path
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[2]


class BackendTestSuiteDispatchContractTest(unittest.TestCase):
    def test_control_plane_tool_checks_are_wired_through_the_final_gate(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/professional_quality_gate.yml').read_text())
        authorization = workflow['jobs']['professional_authorization']
        self.assertEqual(authorization['outputs']['tool_checks'],
                         '${{ steps.backend_impact.outputs.tool_checks }}')
        checks = workflow['jobs']['professional_quality_checks']
        self.assertEqual(checks['outputs']['tool_checks_ran'],
                         '${{ steps.tool_checks.outputs.ran }}')
        self.assertEqual(checks['env']['TOOL_CHECKS'],
                         '${{ needs.professional_authorization.outputs.tool_checks }}')
        step = next(s for s in checks['steps'] if s.get('id') == 'tool_checks')
        self.assertEqual(step['if'], "env.TOOL_CHECKS != ''")
        self.assertIn('make ${TOOL_CHECKS}', step['run'])
        self.assertIn('echo "ran=true" >> "${GITHUB_OUTPUT}"', step['run'])
        gate = workflow['jobs']['professional_quality_gate']
        enforce = next(s for s in gate['steps'] if s['name'] == 'Enforce control-plane tool check execution')
        self.assertEqual(enforce['env']['TOOL_CHECKS'],
                         '${{ needs.professional_authorization.outputs.tool_checks }}')
        self.assertEqual(enforce['env']['TOOL_CHECKS_RAN'],
                         '${{ needs.professional_quality_checks.outputs.tool_checks_ran }}')
        self.assertIn('if [ -n "${TOOL_CHECKS}" ]; then', enforce['run'])
        self.assertIn('test "${TOOL_CHECKS_RAN}" = true', enforce['run'])

    def test_verify_coverage_enforces_run_success_and_reuse_authority(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        plan = workflow['jobs']['plan']
        self.assertEqual('${{ steps.scope.outputs.reuse_authority }}', plan['outputs']['reuse_authority'])
        verify = workflow['jobs']['verify_coverage']
        self.assertEqual(['plan', 'backend_suite'], verify['needs'])
        self.assertIn('always() && !cancelled()', verify['if'])
        script = next(s['run'] for s in verify['steps'] if s['name'] == 'Enforce complete backend coverage')
        for required, suite, reuse, expected in (
            ('true', 'success', '', 0),
            ('true', 'failure', '', 1),
            ('true', 'skipped', '', 1),
            ('false', 'skipped', 'false', 0),
            ('false', 'skipped', 'true', 0),
            ('false', 'success', 'false', 1),
        ):
            with self.subTest(required=required, suite=suite, reuse=reuse):
                outcome = subprocess.run(['bash', '-c', script], env={**os.environ,
                    'REQUIRED': required, 'SUITE_RESULT': suite, 'REUSE_AUTHORITY': reuse},
                    capture_output=True, text=True)
                self.assertEqual(expected, outcome.returncode)

    def test_matrix_cannot_hide_failed_or_cancelled_shards(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        plan = workflow['jobs']['plan']
        suite = workflow['jobs']['backend_suite']
        self.assertIn('github.event.pull_request.head.repo.full_name == github.repository', plan['if'])
        self.assertEqual(suite['needs'], 'plan')
        self.assertFalse(suite['strategy']['fail-fast'])
        self.assertEqual(suite['strategy']['max-parallel'], 4)
        self.assertEqual(suite['strategy']['matrix'], '${{ fromJSON(needs.plan.outputs.matrix) }}')
        self.assertNotIn('continue-on-error', suite)
        self.assertIn('${{ matrix.index }}', suite['env']['COMPOSE_PROJECT_NAME'])

    def test_cache_reuses_layers_not_test_success_or_database_state(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        steps = {s['name']: s for s in workflow['jobs']['backend_suite']['steps']}
        cache = steps['Restore frontend build layers']['with']
        self.assertEqual(cache['path'], '${{ runner.temp }}/backend-frontend-buildkit')
        self.assertIn('frontend/**', cache['key'])
        self.assertIn('Dockerfile.production-frontend-builder', cache['key'])
        self.assertNotIn("hashFiles('Dockerfile'", cache['key'])
        build = steps['Calculate frontend build fingerprint']
        self.assertNotIn('if', build)
        self.assertIn('--cache-from', build['run'])
        self.assertIn('--cache-to', build['run'])
        self.assertIn('--file Dockerfile.production-frontend-builder', build['run'])
        self.assertIn('--target frontend-dist', build['run'])
        self.assertNotIn('frontend-artifact', build['run'])
        self.assertIn('test -s "${dist_dir}/index.html"', build['run'])
        self.assertIn('test "${calculated_hash}" = "${EXPECTED_FRONTEND_BUILD_SHA256}"', build['run'])
        self.assertIn('FRONTEND_DIST_DIR=', build['run'])
        for name in ('Build images and start database', 'Run backend test suite per module'):
            self.assertNotIn('if', steps[name])

    def test_pip_download_cache_reaches_test_container_without_caching_results(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        suite = workflow['jobs']['backend_suite']
        steps = {s['name']: s for s in suite['steps']}
        cache = steps['Restore backend test pip downloads']['with']
        for name in ('Prepare isolated pip download cache','Run backend test suite per module','Return pip cache ownership to runner'):
            self.assertEqual(steps[name]['env']['SC_TEST_PIP_CACHE_HOST'], cache['path'])
        # GitHub evaluates job env before a runner exists; YAML parsing alone
        # cannot detect this server-side expression error.
        for job in workflow['jobs'].values():
            for value in job.get('env', {}).values():
                self.assertNotRegex(str(value), r'\$\{\{[^}]*\brunner\.')
        for dependency in ('Dockerfile', 'requirements-odoo.txt', 'config/requirements-test.txt'):
            self.assertIn(dependency, cache['key'])
        script = (ROOT / 'scripts/test/test.sh').read_text()
        self.assertIn('"${RECEIPT_ARGS[@]}" "${PIP_CACHE_ARGS[@]}"', script)
        self.assertIn('pip3 install -q -r ${CONFIG_MOUNT_CONT}/requirements-test.txt', script)
        self.assertNotIn('if', steps['Run backend test suite per module'])
        fragment = script.split('PIP_CACHE_ARGS=()', 1)[1].split('RUN_RM=', 1)[0]
        with tempfile.TemporaryDirectory(prefix='pip cache ') as folder:
            cases = [(None, 0), (folder, 0), ('relative', 2), ('/', 2),
                     (folder + ':other', 2), (folder + '/missing', 2), (folder + '\n', 2)]
            for value, code in cases:
                with self.subTest(value=value):
                    env = dict(os.environ)
                    env.pop('SC_TEST_PIP_CACHE_HOST', None)
                    if value is not None:
                        env['SC_TEST_PIP_CACHE_HOST'] = value
                    result = subprocess.run(['bash', '-eu', '-c',
                        'PIP_CACHE_ARGS=()\n' + fragment +
                        'printf "<%s>\\n" "${PIP_CACHE_ARGS[@]}"'],
                        env=env, text=True, capture_output=True)
                    self.assertEqual(code, result.returncode, result.stderr)
                    if value == folder:
                        self.assertEqual(['<-v>', '<' + folder + ':/tmp/sc-test-pip-cache>',
                            '<-e>', '<PIP_CACHE_DIR=/tmp/sc-test-pip-cache>'], result.stdout.splitlines())
                    elif value is None:
                        self.assertNotIn('/tmp/sc-test-pip-cache', result.stdout)

    def test_pip_cache_ownership_is_restored_even_after_failed_tests(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        steps = {s['name']: s for s in workflow['jobs']['backend_suite']['steps']}
        restore = steps['Return pip cache ownership to runner']
        self.assertEqual('always()', restore['if'])
        for name in ('Prepare isolated pip download cache', 'Return pip cache ownership to runner'):
            command = steps[name]['run']
            self.assertIn('test "${SC_TEST_PIP_CACHE_HOST}" = "${RUNNER_TEMP}/backend-test-pip-cache"', command)
            self.assertIn('test ! -L "${SC_TEST_PIP_CACHE_HOST}"', command)
            self.assertIn('sudo chown -R -- "$(id -u):$(id -g)" "${SC_TEST_PIP_CACHE_HOST}"', command)
        names = list(steps)
        self.assertLess(names.index('Run backend test suite per module'), names.index('Return pip cache ownership to runner'))
        self.assertLess(names.index('Return pip cache ownership to runner'), names.index('Cleanup'))

    def test_scheduled_baseline_is_full_and_reuse_is_explicitly_accounted(self):
        workflow=yaml.safe_load((ROOT/'.github/workflows/backend_test_suite.yml').read_text())
        suite=workflow['jobs']['backend_suite']
        self.assertEqual('1',suite['env']['SC_BACKEND_ISOLATED_PYTHON'])
        step=next(s for s in suite['steps'] if s['name']=='Run backend test suite per module')
        body=step['run']
        self.assertIn('if [ "${GITHUB_EVENT_NAME}" != pull_request ]; then',body)
        self.assertIn('full_args=(--force-full)',body)
        self.assertIn('isolated-python',body)
        self.assertIn('"$((attempted + reused))" -ne "${planned_total}"',body)
        self.assertIn('attempted=$((attempted - 1))',body)
        self.assertIn('reused=$((reused + 1))',body)
        self.assertEqual('${{ github.token }}',step['env']['GH_TOKEN'])
        self.assertEqual('read',workflow['permissions']['actions'])

    def test_frontend_fingerprint_uses_dedicated_builder_stage(self):
        workflows = (
            ROOT / '.github/workflows/backend_test_suite.yml',
            ROOT / '.github/workflows/demo-ci.yml',
        )
        for path in workflows:
            with self.subTest(workflow=path.name):
                workflow = yaml.safe_load(path.read_text())
                steps = {
                    step['name']: step
                    for job in workflow['jobs'].values()
                    for step in job.get('steps', [])
                    if 'name' in step
                }
                build = steps['Calculate frontend build fingerprint']['run']
                self.assertIn('--file Dockerfile.production-frontend-builder', build)
                self.assertIn('--target frontend-dist', build)
                self.assertNotIn('--target frontend-artifact', build)
                self.assertNotIn('frontend-verified', build)
                self.assertIn('find . -type f -print0', build)

    def test_dispatch_is_exact_head_and_full_suite_only(self):
        makefile = (ROOT / "make/ci.mk").read_text(encoding="utf-8")
        target = makefile.split("ci.backend_test_suite.dispatch:", 1)[1].split("\n.PHONY:", 1)[0]

        for required in (
            "guard.prod.forbid",
            "EXPECTED_HEAD",
            "git status --porcelain",
            "git rev-parse HEAD",
            "git ls-remote --heads origin",
            "cut -f1",
            "gh pr view --json headRefOid",
            "gh workflow run backend_test_suite.yml",
            '-f "head_ref=$$branch"',
        ):
            self.assertIn(required, target)

        self.assertNotIn("modules=", target)
        self.assertNotIn("test_tags=", target)

    def test_workflow_supports_governed_dispatch_inputs(self):
        workflow = (ROOT / ".github/workflows/backend_test_suite.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("head_ref:", workflow)
        self.assertIn("HEAD_REF: ${{ inputs.head_ref || github.event.inputs.head_ref || github.ref_name }}", workflow)
        self.assertIn("CI_PROJECT_NAME: sc-suite-${{ github.run_id }}", workflow)
        self.assertIn("docker compose down -v --remove-orphans", workflow)


class BackendTestSuiteStepIntegrityTest(unittest.TestCase):
    """The per-module step must not be able to report a truncated scope as a pass.

    2026-10-10 triage: GitHub executes ``shell: bash`` steps with errexit on.
    The step accumulated failures in ``failed`` and asserted it at the end, but
    left errexit enabled, so the first failing module aborted the step and every
    later module - plus the whole ``failed`` accumulation - became dead code.
    The 2026-10-09 nightly reported green from that truncated scope.
    """

    def _step(self) -> str:
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        return next(step['run'] for step in workflow['jobs']['backend_suite']['steps']
                    if step['name'] == 'Run backend test suite per module')

    def test_step_declares_the_bash_shell_that_enables_errexit(self) -> None:
        workflow = (ROOT / ".github/workflows/backend_test_suite.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("shell: bash", workflow)

    def test_step_disables_errexit_before_accumulating(self) -> None:
        step = self._step()
        self.assertIn("set +e", step)
        for line in step.splitlines():
            stripped = line.strip()
            if not stripped.startswith("set "):
                continue
            self.assertFalse(
                re.search(r"(?<![\w+])-[a-z]*e", stripped),
                f"errexit must stay disabled in the accumulation loop: {stripped!r}",
            )

    def test_step_asserts_the_executed_scope_equals_the_planned_scope(self) -> None:
        step = self._step()
        self.assertIn("attempted=$((attempted + 1))", step)
        self.assertIn("execution truncated", step)
        self.assertIn('test "${failed}" -eq 0', step)

    def test_step_keeps_the_zero_test_guard(self) -> None:
        step = self._step()
        self.assertIn('source scripts/ci/orm_result_guard.sh', step)
        self.assertIn('if ! evaluate_orm_outcome "${module_status}" "${module_log}"; then', step)
        self.assertIn('orm_expect_identity="odoo.addons.${module}.tests."', step)
        self.assertIn('orm_expect_database="${attempt_db}"', step)


class AttemptArchiveControlFlowTest(unittest.TestCase):
    def test_real_workflow_loop_preserves_failures_and_retry_history(self):
        workflow=yaml.safe_load((ROOT/'.github/workflows/backend_test_suite.yml').read_text())
        step=next(s['run'] for s in workflow['jobs']['backend_suite']['steps'] if s['name']=='Run backend test suite per module')
        # Only the external executors are stubbed. Execute the actual YAML loop
        # and real ORM result guard, without Docker, a database or product tests.
        stubs=r"""
make() {
  local db='' arg
  for arg in "$@"; do case "$arg" in DB_NAME=*) db="${arg#DB_NAME=}";; esac; done
  if [ "$CASE" = orm_fail ]; then return 1; fi
  if [[ "$CASE" == retry* ]] && [[ "$db" != *_retry1 ]]; then return 137; fi
  printf '2026-10-24 00:00:00 INFO %s odoo.addons.example.tests.test_fixture: Starting Fixture.test_one ...\n' "$db"
  printf "0 failed, 0 error(s) of 1 tests when loading database '%s'\n" "$db"
}
python3() {
  if [ "$1" = -m ]; then
    if [ "$CASE" = python_fail ]; then return 1; fi
    printf 'Ran 1 test in 0.001s\n\nOK\n'; return 0
  fi
  if [ "$1" = -c ]; then
    if [ "$CASE" = python_isolated_reuse ]; then printf 'REUSE\n'; else printf 'RUN\n'; fi
    return 0
  fi
  printf '%s\n' "$*" >> "$RUNNER_TEMP/calls"
  if [ "$2" = isolated-python ]; then
    if [ "$CASE" = python_isolated_fail ]; then return 1; fi
    mkdir -p "$RUNNER_TEMP/backend-receipts-fixture-0"
    printf '{"decision":"fixture"}\n' > "$RUNNER_TEMP/backend-receipts-fixture-0/isolated-decision-smart_construction_scene.json"
    return 0
  fi
  if [ "$CASE" = archive_fail ] && [ "$2" = archive-attempt ]; then return 1; fi
  return 0
}
tee() { command tee "$@"; if [ "$CASE" = log_fail ] || { [ "$CASE" = retry_log_fail ] && [[ "$1" == *attempt1.log ]]; }; then return 7; fi; }
"""
        for case,expected,archives,records in [('pass',0,1,1),('retry',0,2,1),('orm_fail',1,1,0),
                ('log_fail',1,1,0),('python_fail',1,1,0),('python_pass',0,1,1),('archive_fail',1,1,0),('retry_log_fail',1,2,0),
                ('python_isolated_run',0,0,0),('python_isolated_reuse',0,0,0),('python_isolated_fail',1,0,0)]:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);(folder/'backend-plan.json').write_text('{}')
                environment={**os.environ,'CASE':case,'RUNNER_TEMP':tmp,'GITHUB_RUN_ID':'fixture',
                    'GITHUB_ENV':str(folder/'env'),'GITHUB_STEP_SUMMARY':str(folder/'summary'),
                    'HEAD_SHA':'a'*40,'IMPACT_BASE':'b'*40,'SHARD_INDEX':'0','DB_NAME':'fixture_db',
                    'ENV_FILE':str(folder/'managed.env'),'TEST_TAGS_INPUT':'','GITHUB_EVENT_NAME':'pull_request',
                    'SC_BACKEND_ISOLATED_PYTHON':'1' if case.startswith('python_isolated') else '0',
                    'MODULES':'' if case.startswith('python') else 'example',
                    'PYTHON_MODULES':'smart_construction_scene' if case.startswith('python') else ''}
                result=subprocess.run(['bash','-e','-c',stubs+step],cwd=ROOT,env=environment,capture_output=True,text=True)
                self.assertEqual(expected,result.returncode,result.stdout+result.stderr)
                calls=(folder/'calls').read_text().splitlines()
                self.assertEqual(archives,sum(' archive-attempt ' in line for line in calls))
                self.assertEqual(records,sum(' record ' in line for line in calls))
                if case in ('log_fail', 'retry_log_fail'):
                    attempts=[line for line in calls if ' archive-attempt ' in line]
                    self.assertIn('--log-status 7', attempts[0])
                    self.assertIn('--status 137' if case=='retry_log_fail' else '--status 0', attempts[0])
                if case=='retry':
                    attempts=[line for line in calls if ' archive-attempt ' in line]
                    self.assertIn('--attempt 1',attempts[0]);self.assertIn('--status 137',attempts[0])
                    self.assertIn('--attempt 2',attempts[1]);self.assertIn('--status 0',attempts[1])


if __name__ == "__main__":
    unittest.main()

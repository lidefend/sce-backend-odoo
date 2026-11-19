import re
import os
import subprocess
import tempfile
from pathlib import Path
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[2]


class BackendTestSuiteDispatchContractTest(unittest.TestCase):
    def test_local_workflow_contract_reports_root_complexity(self):
        source = (ROOT / 'make/ci.mk').read_text()
        recipe = source.split('verify.ci.workflow.contract:', 1)[1].split('\n\n', 1)[0]
        self.assertIn('python3 scripts/ci/enforce_complexity_baseline_lock.py', recipe)

    def test_make_env_file_exports_only_declared_assignments(self):
        # Execute the real Make graph without Docker or a database. The unrelated
        # lazy probe must never run simply to construct a recipe environment.
        for assignments in ("", "CI_FILE_ONLY=fixture\nexport CI_EXPORTED := explicit\nCI_DEFAULT ?= fallback\nCI_APPEND = first\nCI_APPEND += second\nDB_NAME=file_db\n"):
            with self.subTest(assignments=bool(assignments)), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                env_file = folder / "managed.env"
                env_file.write_text(assignments)
                marker = folder / "unrelated-probe"
                overlay = folder / "probe.mk"
                overlay.write_text(
                    f"CI_UNRELATED_LAZY = $(shell touch {marker})\n"
                    ".PHONY: ci-env-probe\nci-env-probe:\n"
                    "\t@test \"$$DB_NAME\" = cli_db\n"
                    + ("\t@test \"$$CI_FILE_ONLY\" = fixture\n"
                       "\t@test \"$$CI_EXPORTED\" = explicit\n"
                       "\t@test \"$$CI_DEFAULT\" = fallback\n"
                       "\t@test \"$$CI_APPEND\" = 'first second'\n" if assignments else "")
                )
                result = subprocess.run(
                    [os.environ.get("CI_MAKE_TEST_BINARY", "make"), "--no-print-directory",
                     "-f", "Makefile", "-f", str(overlay), "ci-env-probe",
                     f"ENV_FILE={env_file}", "DB_NAME=cli_db"],
                    cwd=ROOT, env={"PATH": os.environ["PATH"]},
                    text=True, capture_output=True, timeout=10,
                )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertFalse(marker.exists(), "unrelated lazy Make variable was expanded")

    def test_heartbeat_stops_promptly_and_leaves_no_sleep_process(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        run = next(s['run'] for s in workflow['jobs']['backend_suite']['steps']
                   if s['name'] == 'Run backend test suite per module')
        functions = run[run.index('start_heartbeat()'):run.index('planned_odoo=')]
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(['bash', '-eu', '-c', functions + r'''
start_heartbeat fixture "$RUNNER_TEMP/log" 1
sleep 0.1
child=$(pgrep -P "$heartbeat_pid" sleep)
test -n "$child"
stop_heartbeat
! kill -0 "$child" 2>/dev/null
'''], env={**os.environ, 'RUNNER_TEMP': tmp, 'GITHUB_RUN_ID': '1',
                       'SHARD_INDEX': '0', 'BACKEND_MODULE_HEARTBEAT_SECONDS': '30'},
                text=True, capture_output=True, timeout=3)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_image_cache_preserves_current_revision_and_build_inputs(self):
        source = (ROOT / 'Dockerfile').read_text()
        self.assertGreater(source.index('ARG SOURCE_SHA'), source.rindex('COPY '))
        self.assertIn('org.opencontainers.image.revision=${SOURCE_SHA}', source)
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        steps = {s['name']: s for s in workflow['jobs']['backend_suite']['steps']}
        cache = steps['Restore backend image layers']['with']
        self.assertEqual('${{ runner.temp }}/backend-build-cache', cache['path'])
        self.assertIn('inputs.head_sha || github.sha', cache['key'])
        build = steps['Build images and start database']['run']
        self.assertIn('--load odoo', build)
        self.assertIn('odoo.cache-from=type=local,src=${RUNNER_TEMP}/backend-build-cache', build)
        self.assertIn('odoo.cache-to=type=local,dest=${RUNNER_TEMP}/backend-build-cache-new,mode=max', build)
        self.assertNotIn('cache-hit', build)
        self.assertIn('--allow "fs.read=${RUNNER_TEMP}/backend-build-cache"', build)
        self.assertIn('--allow "fs.write=${RUNNER_TEMP}/backend-build-cache-new"', build)
        self.assertLess(build.index('mkdir -p "${RUNNER_TEMP}/backend-build-cache"'),
                        build.index('docker buildx bake'))
        self.assertNotIn('BUILDX_BAKE_ENTITLEMENTS_FS=0', build)
        self.assertNotIn('fs=*', build)

    def test_test_carriers_disable_only_application_health_probe(self):
        overlay = yaml.safe_load((ROOT / 'docker-compose.test-isolation.yml').read_text())
        self.assertEqual({'services': {'odoo': {'healthcheck': {'disable': True}}}}, overlay)
        shell = (ROOT / 'scripts/test/test.sh').read_text()
        self.assertIn('-f "${ROOT_DIR}/docker-compose.test-isolation.yml" run --no-deps', shell)
        runner = (ROOT / 'scripts/dev/local_test_runner.py').read_text()
        self.assertIn("'-f', str(ROOT / 'docker-compose.test-isolation.yml')", runner)
        base = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
        self.assertNotIn('disable', base['services']['odoo']['healthcheck'])

    def test_control_plane_tool_checks_are_wired_through_the_final_gate(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/professional_quality_gate.yml').read_text())
        authorization = workflow['jobs']['professional_authorization']
        self.assertEqual(
            authorization['outputs']['tool_checks'],
            "${{ steps.backend_impact.outputs.tool_checks || '' }}",
        )
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

    def test_frozen_plan_worker_passes_authentication_to_reuse_validation(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        step = next(s for s in workflow['jobs']['backend_suite']['steps']
                    if s.get('name') == 'Resolve module list')
        self.assertEqual(step['env']['GH_TOKEN'], '${{ github.token }}')
        self.assertEqual(step['env']['PLAN_SHA256'], '${{ needs.plan.outputs.plan_sha256 }}')
        # Execute the real workflow shell; stub only external git/planner calls.
        # The planner reauthenticates historical receipts when consuming this
        # frozen plan, so the token must be inherited by that exact invocation.
        stubs = r"""
git() { printf '%s\n' "$HEAD_SHA"; }
python3() {
  if [ "$1" = scripts/ci/backend_suite_plan.py ]; then
    [ "${GH_TOKEN:-}" = fixture-token ] || return 4
    case " $* " in
      *" --frozen-plan $RUNNER_TEMP/frozen-plan/backend-plan.json --plan-sha256 fixture-digest --shard 0 "*) ;;
      *) return 9 ;;
    esac
    printf 'smart_construction_scene\n'
  fi
}
"""
        for authenticated in (True, False):
            with self.subTest(authenticated=authenticated), tempfile.TemporaryDirectory() as tmp:
                env = {**os.environ, 'HEAD_SHA': 'a' * 40, 'IMPACT_BASE': '',
                       'MODULE_OVERRIDE': '', 'RUNNER_TEMP': tmp,
                       'PLAN_SHA256': 'fixture-digest', 'SHARD_INDEX': '0',
                       'GITHUB_ENV': str(Path(tmp) / 'env'),
                       'GITHUB_STEP_SUMMARY': str(Path(tmp) / 'summary')}
                env.pop('GH_TOKEN', None)
                if authenticated:
                    env['GH_TOKEN'] = 'fixture-token'
                result = subprocess.run(['bash', '-e', '-c', stubs + step['run']],
                                        cwd=ROOT, env=env, text=True, capture_output=True)
                self.assertEqual(0 if authenticated else 4, result.returncode,
                                 result.stdout + result.stderr)
                self.assertEqual(authenticated, (Path(tmp) / 'env').exists())

    def test_verify_coverage_enforces_run_success_and_reuse_authority(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        plan = workflow['jobs']['plan']
        self.assertEqual('${{ steps.scope.outputs.reuse_authority }}', plan['outputs']['reuse_authority'])
        verify = workflow['jobs']['verify_coverage']
        self.assertEqual(['plan', 'backend_suite'], verify['needs'])
        self.assertIn('always() && !cancelled()', verify['if'])
        script = next(s['run'] for s in verify['steps'] if s.get('name') == 'Enforce complete backend coverage')
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

    def test_ordinary_pr_uses_focused_scope_with_bounded_module_execution(self):
        workflow = yaml.safe_load(
            (ROOT / '.github/workflows/backend_test_suite.yml').read_text()
        )
        professional = yaml.safe_load(
            (ROOT / '.github/workflows/professional_quality_gate.yml').read_text()
        )
        events = workflow.get('on', workflow.get(True))
        self.assertEqual(events['workflow_call']['inputs']['scope_mode']['default'], 'full')
        self.assertEqual(
            professional['jobs']['backend_impact_suite']['with']['scope_mode'],
            "${{ needs.professional_authorization.outputs.candidate_requested == 'true' && 'full' || 'focused' }}",
        )
        plan = workflow['jobs']['plan']
        self.assertEqual('${{ steps.scope.outputs.scope_mode }}', plan['outputs']['scope_mode'])
        scope = next(s for s in plan['steps'] if s.get('id') == 'scope')
        self.assertEqual("${{ inputs.scope_mode || 'full' }}", scope['env']['SCOPE_MODE'])
        self.assertIn('focused_args=(--focused)', scope['run'])
        self.assertIn('scope_mode=${plan_mode}', scope['run'])

        suite = workflow['jobs']['backend_suite']
        self.assertEqual('${{ needs.plan.outputs.scope_mode }}', suite['env']['SUITE_MODE'])
        self.assertEqual('1', suite['env']['KEEP_TEST_CONTAINER'])
        self.assertEqual(
            "${{ needs.plan.outputs.scope_mode == 'focused' && '600' || '1200' }}",
            suite['env']['BACKEND_MODULE_TIMEOUT_SECONDS'],
        )
        self.assertEqual('30', suite['env']['BACKEND_MODULE_HEARTBEAT_SECONDS'])
        run = next(s['run'] for s in suite['steps'] if s['name'] == 'Run backend test suite per module')
        self.assertIn('timeout --foreground --signal=TERM --kill-after=10', run)
        self.assertIn('"${BACKEND_MODULE_TIMEOUT_SECONDS:-1200}"', run)
        self.assertIn('start_heartbeat "${module}" "${module_log}" "${module_attempt}"', run)
        self.assertIn('pipeline_status=("${PIPESTATUS[@]}")', run)
        self.assertNotIn('scripts/ci/run_backend_module_test.py', run)
        self.assertIn('--module "${module}" --selectors', run)
        self.assertIn('2>&1 | tee "${module_log}"', run)
        resolve = next(
            step for step in suite['steps']
            if step.get('name') == 'Resolve module list'
        )
        self.assertIn(
            'echo "PLAN_SHA256=${PLAN_SHA256}" >> "${GITHUB_ENV}"',
            resolve['run'],
        )

    def test_shard_materializes_mainline_ref_before_running_module_tests(self):
        workflow = yaml.safe_load(
            (ROOT / '.github/workflows/backend_test_suite.yml').read_text()
        )
        steps = workflow['jobs']['backend_suite']['steps']
        resolve_index = next(
            index for index, step in enumerate(steps)
            if step.get('name') == 'Resolve module list'
        )
        test_index = next(
            index for index, step in enumerate(steps)
            if step.get('name') == 'Run backend test suite per module'
        )
        self.assertLess(resolve_index, test_index)

        resolve = steps[resolve_index]['run']
        self.assertIn(
            'git fetch --no-tags origin "${IMPACT_BASE}"',
            resolve,
        )
        self.assertIn(
            'git update-ref refs/remotes/origin/main "${IMPACT_BASE}"',
            resolve,
        )
        self.assertIn(
            '"main:refs/remotes/origin/main"',
            resolve,
        )
        self.assertIn(
            'test "${mainline_base}" = "${IMPACT_BASE}"',
            resolve,
        )
        self.assertIn(
            'echo "VIEW_STRUCTURE_BASELINE_SHA=${mainline_base}" >> "${GITHUB_ENV}"',
            resolve,
        )

    def test_failed_container_diagnostics_remain_project_scoped(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        suite = workflow['jobs']['backend_suite']
        self.assertEqual('1', suite['env']['KEEP_TEST_CONTAINER'])
        steps = {step['name']: step for step in suite['steps']}
        for body in (steps['Dump logs on failure']['run'], steps['Cleanup']['run']):
            self.assertIn('label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}', body)
        self.assertIn('docker logs --tail=400', steps['Dump logs on failure']['run'])
        self.assertIn('docker rm -f "${container}"', steps['Cleanup']['run'])

    def test_dependency_install_failure_stops_before_odoo(self):
        script = (ROOT / 'scripts/test/test.sh').read_text()
        self.assertIn('--interactive=false', script)
        container = script.split('--entrypoint bash odoo -lc "', 1)[1].rsplit('"', 1)[0]
        container = container.replace('\\$', '$').replace('\\"', '"')
        container = container.split('exec /usr/bin/odoo', 1)[0] + "printf 'unexpected_odoo\n'\n"
        result = subprocess.run(
            ['bash', '-c', 'pip3() { return 17; };\n' + container],
            env={'PATH': os.environ['PATH'], 'CONFIG_MOUNT_CONT': '/unused',
                 'PREPARATION_COMMAND': ':'}, text=True, capture_output=True,
        )
        self.assertEqual(17, result.returncode, result.stdout + result.stderr)
        self.assertNotIn('unexpected_odoo', result.stdout)

    def test_orm_suite_does_not_build_unconsumed_frontend(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/backend_test_suite.yml').read_text())
        steps = {s['name']: s for s in workflow['jobs']['backend_suite']['steps']}
        self.assertNotIn('Calculate frontend build fingerprint', steps)
        build = steps['Build images and start database']['run']
        self.assertIn('docker buildx bake --builder "${BUILDX_BUILDER}" -f docker-compose.yml', build)
        self.assertIn('docker compose pull db redis', build)
        self.assertNotIn('FRONTEND_BUILD_SHA256', str(steps))
        self.assertNotIn('frontend', (ROOT / 'Dockerfile').read_text().split('FROM ')[0])

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
        self.assertNotIn('full_args=()', body)
        self.assertIn('full_args=(--force-full)',body)
        self.assertIn('isolated-python',body)
        self.assertIn('"$((attempted + reused))" -ne "${planned_total}"',body)
        self.assertIn('attempted=$((attempted - 1))',body)
        self.assertIn('reused=$((reused + 1))',body)
        self.assertEqual('${{ github.token }}',step['env']['GH_TOKEN'])
        self.assertEqual('read',workflow['permissions']['actions'])

    def test_frontend_fingerprint_uses_dedicated_builder_stage(self):
        workflows = (
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

    def test_frontend_release_dispatch_is_exact_head_and_reads_back(self):
        makefile = (ROOT / "make/ci.mk").read_text(encoding="utf-8")
        target = makefile.split("ci.frontend_release_gate.dispatch:", 1)[1].split("\n.PHONY:", 1)[0]

        for required in (
            "guard.prod.forbid",
            "EXPECTED_HEAD",
            "CI_DISPATCH_BRANCH",
            "git status --porcelain",
            "git ls-remote --heads origin",
            "gh workflow run frontend_release_gate.yml",
            '--ref "$$branch"',
            "gh run list --workflow frontend_release_gate.yml",
            "headSha",
            "databaseId",
            "before_ids",
        ):
            self.assertIn(required, target)

        self.assertIn('"$$repo" != "lidefend/sce-backend-odoo"', target)
        self.assertIn('"$$remote_head" != "$$expected"', target)
        self.assertIn('"$$head_sha" = "$$expected"', target)

    def test_workflow_supports_governed_dispatch_inputs(self):
        workflow = (ROOT / ".github/workflows/backend_test_suite.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("head_ref:", workflow)
        self.assertIn("HEAD_REF: ${{ inputs.head_ref || github.event.inputs.head_ref || github.ref_name }}", workflow)
        self.assertIn("CI_PROJECT_NAME: sc-suite-${{ github.run_id }}", workflow)
        self.assertIn("docker compose down -v --remove-orphans", workflow)

    def test_cross_job_artifacts_survive_failed_job_rerun(self):
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/backend_test_suite.yml").read_text(encoding="utf-8")
        )
        plan = workflow["jobs"]["plan"]
        upload_plan = next(step for step in plan["steps"] if step.get("name") == "Upload stable execution plan")
        self.assertEqual(
            upload_plan["with"]["name"],
            "backend-plan-${{ github.run_id }}",
        )
        self.assertTrue(upload_plan["with"]["overwrite"])

        suite = workflow["jobs"]["backend_suite"]
        download_plan = next(
            step for step in suite["steps"] if step.get("name") == "Download immutable execution plan"
        )
        self.assertEqual(
            download_plan["with"]["name"],
            "backend-plan-${{ github.run_id }}",
        )
        upload_execution = next(
            step for step in suite["steps"]
            if step.get("name") == "Preserve per-target execution observations"
        )
        self.assertEqual(
            upload_execution["with"]["name"],
            "backend-execution-${{ github.run_id }}-${{ matrix.index }}",
        )
        self.assertTrue(upload_execution["with"]["overwrite"])

        coverage = workflow["jobs"]["verify_coverage"]
        coverage_downloads = [
            step for step in coverage["steps"]
            if step.get("name") == "Download coverage evidence"
        ]
        self.assertEqual(coverage_downloads[0]["with"]["name"], "backend-plan-${{ github.run_id }}")
        self.assertEqual(
            coverage_downloads[1]["with"]["pattern"],
            "backend-execution-${{ github.run_id }}-*",
        )
        upload_coverage = next(
            step for step in coverage["steps"] if step.get("name") == "Publish changed test coverage"
        )
        self.assertEqual(
            upload_coverage["with"]["name"],
            "changed-test-coverage-${{ github.run_id }}",
        )
        self.assertTrue(upload_coverage["with"]["overwrite"])

        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                artifact = (step.get("with") or {}).get("name", "")
                if any(token in artifact for token in (
                    "backend-plan-",
                    "backend-execution-",
                    "changed-test-coverage-",
                )):
                    self.assertNotIn("github.run_attempt", artifact)


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
timeout() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --foreground|--signal=*|--kill-after=*) shift ;;
      *[!0-9.]*) break ;;
      *) shift; break ;;
    esac
  done
  "$@"
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
"""
        for case,expected,archives,records in [('pass',0,1,1),('retry',0,2,1),('orm_fail',1,1,0),
                ('python_fail',1,1,0),('python_pass',0,1,1),('archive_fail',1,1,0),
                ('python_isolated_run',0,0,0),('python_isolated_reuse',0,0,0),('python_isolated_fail',1,0,0)]:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);(folder/'backend-plan.json').write_text('{}')
                environment={**os.environ,'CASE':case,'RUNNER_TEMP':tmp,'GITHUB_RUN_ID':'fixture',
                    'GITHUB_ENV':str(folder/'env'),'GITHUB_STEP_SUMMARY':str(folder/'summary'),
                    'HEAD_SHA':'a'*40,'IMPACT_BASE':'b'*40,'SHARD_INDEX':'0','DB_NAME':'fixture_db',
                    'ENV_FILE':str(folder/'managed.env'),'TEST_TAGS_INPUT':'','GITHUB_EVENT_NAME':'pull_request',
                    'BACKEND_MODULE_TIMEOUT_SECONDS':'2','BACKEND_MODULE_HEARTBEAT_SECONDS':'0.05',
                    'SC_BACKEND_ISOLATED_PYTHON':'1' if case.startswith('python_isolated') else '0',
                    'MODULES':'' if case.startswith('python') else 'example',
                    'PYTHON_MODULES':'smart_construction_scene' if case.startswith('python') else ''}
                result=subprocess.run(['bash','-e','-c',stubs+step],cwd=ROOT,env=environment,capture_output=True,text=True)
                self.assertEqual(expected,result.returncode,result.stdout+result.stderr)
                calls=(folder/'calls').read_text().splitlines()
                self.assertEqual(archives,sum(' archive-attempt ' in line for line in calls))
                self.assertEqual(records,sum(' record ' in line for line in calls))
                if case=='retry':
                    attempts=[line for line in calls if ' archive-attempt ' in line]
                    self.assertIn('--attempt 1',attempts[0]);self.assertIn('--status 137',attempts[0])
                    self.assertIn('--attempt 2',attempts[1]);self.assertIn('--status 0',attempts[1])


if __name__ == "__main__":
    unittest.main()

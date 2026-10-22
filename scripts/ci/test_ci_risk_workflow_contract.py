#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
# The remote gate invokes this file directly, without PYTHONPATH.
sys.path.insert(0, str(ROOT))


class CIRiskWorkflowContractTests(unittest.TestCase):
    def text(self, name: str) -> str:
        return (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")

    def test_merge_policy_gate_is_the_single_required_aggregation_job(self) -> None:
        contracts = {
            "public_guard.yml": ("  public_guard:", "    name: public_guard"),
            "professional_quality_gate.yml": (
                "  professional_authorization:",
                "    name: professional_authorization",
                "  professional_quality_gate:",
                "    name: professional_quality_gate",
            ),
            "frontend_release_gate.yml": (
                "  frontend_release_gate:",
                "    name: frontend_release_gate",
            ),
            "release_candidate_gate.yml": (
                "  release_candidate_gate:",
                "    name: release_candidate_gate",
            ),
        }
        for workflow, required in contracts.items():
            text = self.text(workflow)
            self.assertNotIn("\n    paths:", text)
            self.assertNotIn("\n    paths-ignore:", text)
            self.assertIn("cancel-in-progress: true", text)
            for item in required:
                self.assertIn(item, text)
        aggregate = self.text("merge_policy_gate.yml")
        self.assertIn("name: merge_policy_gate", aggregate)
        self.assertIn("name: merge_policy_gate", aggregate)
        self.assertIn("needs: [classify, fast, wait_for_fact_checks]", aggregate)
        self.assertIn("Resolve merge-policy lane once", aggregate)
        merge_job = aggregate.split("  merge_policy_gate:", 1)[1]
        wait_job = aggregate.split("  wait_for_fact_checks:", 1)[1].split(
            "  merge_policy_gate:", 1
        )[0]
        self.assertIn("select_authoritative_workflow_run.py", wait_job)
        self.assertIn("actions/workflows/${workflow}/runs", wait_job)
        self.assertNotIn('test "$count" = 1', aggregate)
        self.assertNotIn("continue-on-error:", aggregate)

    def test_candidate_checks_run_once_per_explicit_candidate_head(self) -> None:
        workflows = (
            "merge_policy_gate.yml",
            "public_guard.yml",
            "professional_quality_gate.yml",
            "frontend_release_gate.yml",
            "release_candidate_gate.yml",
        )
        for workflow in workflows:
            text = self.text(workflow)
            self.assertIn(
                "types: [opened, reopened, synchronize, labeled]",
                text,
            )
            self.assertIn("workflow_dispatch:", text)
            self.assertIn("github.event.label.name == 'ci:candidate'", text)
            self.assertNotIn("inputs.expected_head", text)
            self.assertNotIn("inputs.expected_base", text)
        candidate_gate = self.text("release_candidate_gate.yml")
        self.assertIn('test "$result" = success || test "$result" = skipped', candidate_gate)

        makefile = (ROOT / "make/codex.mk").read_text(encoding="utf-8")
        dispatch = makefile.split("candidate.required_checks.dispatch:", 1)[1].split(
            "candidate.mirror.gitee:", 1
        )[0]
        self.assertIn("exactly_one_open_pr_required", dispatch)
        self.assertIn("pr_head_mismatch", dispatch)
        self.assertIn("invalid_pr_base", dispatch)
        self.assertIn("pr_head_changed_before_dispatch", dispatch)
        self.assertIn("gh label create ci:candidate", dispatch)
        self.assertIn("--force", dispatch)
        self.assertIn("--remove-label ci:candidate", dispatch)
        self.assertIn("--add-label ci:candidate", dispatch)

    def test_frontend_lane_commands_are_explicit(self) -> None:
        text = self.text("frontend_release_gate.yml")
        self.assertIn("CANDIDATE_REQUESTED:", text)
        self.assertIn("Resolve effective frontend lane", text)
        self.assertIn("steps.effective_lane.outputs.frontend_mode", text)
        self.assertIn('[ "${CANDIDATE_REQUESTED}" != "true" ] && [ "${mode}" = "full" ]', text)
        self.assertIn("frontend_mode == 'full'", text)
        self.assertIn("frontend_mode == 'standard'", text)
        self.assertIn("frontend_mode != 'full'", text)
        self.assertIn("pnpm test:release", text)
        self.assertIn("pnpm -C frontend/apps/web lint:src", text)
        self.assertIn("pnpm -C frontend/apps/web typecheck:strict", text)
        self.assertIn("pnpm -C frontend/apps/web build", text)
        self.assertIn("pnpm -C frontend/apps/web test", text)
        self.assertIn("python3 scripts/ci/frontend_professional_extension_guard.py", text)
        self.assertNotIn("continue-on-error:", text)
        self.assertNotIn("|| true", text)

        package = json.loads((ROOT / "frontend/apps/web/package.json").read_text(encoding="utf-8"))
        self.assertIn("verify.frontend.pr.unit", package["scripts"]["test"])
        self.assertIn("verify.frontend.release.audit", package["scripts"]["test:release"])
        makefile = (ROOT / "make/frontend.mk").read_text(encoding="utf-8")
        merge_units = makefile.split("verify.frontend.pr.unit:", 1)[1].split("\n", 1)[0]
        self.assertIn("verify.frontend.component_driver_takeover.unit", merge_units)
        self.assertIn("verify.frontend.primitive_adapter.unit", merge_units)
        self.assertIn("verify.frontend.navigation_shell.unit", merge_units)
        self.assertIn("verify.frontend.state_dashboard.unit", merge_units)
        self.assertNotIn("verify.frontend.professional_audit.unit", merge_units)

    def test_professional_gate_pins_the_node_runtime_of_the_syntax_sweep(self) -> None:
        """The sweep behind ``test.unit``/``test.contract`` parses ``.js`` files.

        Those targets check ``.js`` through ``node --input-type``, so the job
        that runs them must pin the runtime instead of inheriting whatever the
        runner image ships. The step is read from the parsed workflow, so a
        changed version, an unpinned ``@v4`` action, a commented-out version or
        an ``if: false`` guard cannot satisfy it by matching text.
        """
        workflow = yaml.safe_load(self.text("professional_quality_gate.yml"))
        steps = workflow["jobs"]["professional_quality_checks"]["steps"]
        names = [step.get("name") for step in steps]
        pin_name = "Install pinned Node.js runtime for the syntax sweep"
        self.assertEqual(names.count(pin_name), 1, "the sweep job must pin the node runtime once")
        pin = steps[names.index(pin_name)]
        self.assertEqual(pin.get("uses"), "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020")
        self.assertEqual(pin.get("with"), {"node-version": "22.17.0"})
        self.assertNotIn("if", pin)
        for gate in (
            "Run full professional quality gate (serialized artifact writers)",
            "Run standard backend quality gate",
        ):
            self.assertIn(gate, names)
            self.assertLess(names.index(pin_name), names.index(gate), f"{gate} must run after the pin")

    def test_public_guard_skips_history_scan_only_for_fast_lane(self) -> None:
        text = self.text("public_guard.yml")
        self.assertIn("name: public_guard_classify", text)
        self.assertIn("steps.risk.outputs.lane", text)
        self.assertIn("if: needs.classify.outputs.lane != 'FAST'", text)
        self.assertIn("Scan governed product history", text)
        self.assertIn('case "${GITHUB_EVENT_NAME}" in', text)
        self.assertIn("schedule|workflow_dispatch)", text)
        self.assertIn("pull_request|push)", text)
        self.assertIn('git cat-file -e "${BASE_SHA}^{commit}"', text)
        self.assertIn('git merge-base --is-ancestor "${BASE_SHA}" HEAD', text)
        self.assertIn("trusted_base_unavailable", text)
        self.assertIn('repository_clean_history_guard.py --trusted-base "${BASE_SHA}"', text)
        self.assertIn("make verify.repository.clean_history", text)

    def test_professional_lane_commands_are_explicit(self) -> None:
        text = self.text("professional_quality_gate.yml")
        self.assertIn("frontend_changed: ${{ steps.risk.outputs.frontend_changed }}", text)
        self.assertIn("backend_changed: ${{ steps.risk.outputs.backend_changed }}", text)
        self.assertIn("candidate_requested:", text)
        self.assertIn("CANDIDATE_REQUESTED:", text)
        self.assertIn("PROFESSIONAL_MODE == 'governance'", text)
        self.assertIn("github.event.action == 'labeled' && github.event.label.name == 'ci:candidate'", text)
        self.assertIn(
            "FRONTEND_CHANGED: ${{ github.event_name == 'schedule' && 'true' || needs.professional_authorization.outputs.frontend_changed }}",
            text,
        )
        self.assertIn(
            "BACKEND_CHANGED: ${{ github.event_name == 'schedule' && 'true' || needs.professional_authorization.outputs.backend_changed }}",
            text,
        )
        self.assertIn("github.event_name == 'schedule' && 'full'", text)
        self.assertIn("PROFESSIONAL_MODE == 'full'", text)
        self.assertIn("PROFESSIONAL_MODE == 'standard_backend'", text)
        self.assertIn("PROFESSIONAL_MODE == 'fast'", text)
        self.assertIn("PROFESSIONAL_MODE == 'mainline'", text)
        self.assertIn("github.event_name != 'push'", text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn("make ci.professional.backend", text)
        self.assertNotIn("run: make ci\n", text)
        self.assertIn("env.ORM_REQUIRED == 'true'", text)
        authorization_section = text.split("  professional_authorization:", 1)[1].split(
            "  python310_runtime_compatibility:", 1
        )[0]
        self.assertNotIn("test.chatter-timeline.authorization.orm", authorization_section)
        self.assertIn("make test.candidate.contract-profiles.orm", text)
        self.assertIn('"${CANDIDATE_REQUESTED}" = true', text)
        preparation = text.split(
            "- name: Prepare host-owned artifact root before container checks", 1
        )[1].split("- name: Report ORM verification selection", 1)[0]
        self.assertIn("if: env.PROFESSIONAL_MODE == 'full'", preparation)
        self.assertIn("python3 scripts/verify/ci_artifact_host_write_guard.py", preparation)
        full_section = text.split(
            "- name: Run full professional quality gate (serialized artifact writers)", 1
        )[1].split("- name: Run mainline integrity gate", 1)[0]
        expected_order = (
            "python3 scripts/verify/ci_artifact_host_write_guard.py",
            "make ci.professional.backend.shard-verify",
            "python3 scripts/verify/ci_artifact_host_write_guard.py",
            "make ci.professional.backend.shard-reports",
            "python3 scripts/verify/ci_artifact_host_write_guard.py",
            "make ci.professional.backend.shard-tests",
        )
        cursor = -1
        for command in expected_order:
            cursor = full_section.find(command, cursor + 1)
            self.assertGreaterEqual(cursor, 0, command)
        self.assertNotIn("pnpm -C frontend install", text)
        self.assertIn("make test.unit test.contract test.e2e.preflight", text)
        self.assertIn("make verify.product.release.version", text)
        governance_section = text.split("- name: Run governance-only quality gate", 1)[1].split(
            "- name: Run Fast lightweight quality gate", 1
        )[0]
        self.assertIn("if: env.PROFESSIONAL_MODE == 'governance'", governance_section)
        self.assertIn("test_ci_risk_workflow_contract.py", governance_section)
        self.assertIn("ci.generated_reports.guard", governance_section)
        self.assertNotIn("make ci.professional.backend", governance_section)

        fast_section = text.split("- name: Run Fast lightweight quality gate", 1)[1].split(
            "- name: Run standard frontend quality gate", 1
        )[0]
        self.assertIn("if: env.PROFESSIONAL_MODE == 'fast'", fast_section)
        self.assertNotIn("verify.contract.lint", fast_section)
        self.assertNotIn("verify.guard.registry", fast_section)
        standard_frontend_section = text.split(
            "- name: Run standard frontend quality gate", 1
        )[1].split("- name: Clean isolated runner state", 1)[0]
        self.assertIn("if: env.PROFESSIONAL_MODE == 'standard_frontend'", standard_frontend_section)
        self.assertNotIn("verify.contract.lint", standard_frontend_section)
        self.assertNotIn("verify.guard.registry", standard_frontend_section)
        self.assertIn("python3 scripts/ci/frontend_professional_extension_guard.py", standard_frontend_section)
        self.assertNotIn("continue-on-error:", text)
        self.assertNotIn("|| true", text)
        mainline_section = text.split("- name: Run mainline integrity gate", 1)[1].split(
            "- name: Run standard backend quality gate", 1
        )[0]
        self.assertIn("test_ci_risk_workflow_contract.py", mainline_section)
        self.assertIn("github_actions_security_guard.py", mainline_section)
        self.assertIn("ci.generated_reports.guard", mainline_section)
        self.assertNotIn("ci.professional.backend", mainline_section)

    def test_orm_selection_is_distinct_from_broad_backend_static_paths(self) -> None:
        text = self.text('professional_quality_gate.yml')
        self.assertIn('orm_required: ${{ steps.risk.outputs.orm_required }}', text)
        self.assertIn("ORM_REQUIRED: ${{ github.event_name == 'schedule' || needs.professional_authorization.outputs.orm_required != 'false' }}", text)
        block = text.split('- name: Prove settlement component profile with real ORM', 1)[1].split('- name:', 1)[0]
        self.assertIn("if: env.ORM_REQUIRED == 'true'", block)
        self.assertNotIn('env.BACKEND_CHANGED', block)
        self.assertIn('make test.payment-settlement.component-profile.orm', block)
        self.assertIn('Report ORM verification selection', text)

    def test_settlement_component_profile_orm_gate_stays_wired(self) -> None:
        """Keep the settlement ORM lane wired, and record where it can run.

        The Gitee formal executor runs static lanes inside a docker-less
        bubblewrap sandbox, so it cannot execute a container-backed Odoo
        TransactionCase. This contract is therefore only a *wiring* check that
        the merge path can enforce: it fails when the runtime lane, the make
        target, the fixed tag whitelist, the zero-test rejection or the timeout
        guard is removed. Coverage of the settlement assertions comes solely
        from the isolated ORM execution, never from these names.
        """
        workflow = self.text("professional_quality_gate.yml")
        self.assertIn("- name: Prove settlement component profile with real ORM", workflow)
        self.assertIn("make test.payment-settlement.component-profile.orm", workflow)

        makefile = (ROOT / "make/dev_test.mk").read_text(encoding="utf-8")
        self.assertIn(
            "test.payment-settlement.component-profile.orm: guard.prod.forbid", makefile
        )
        self.assertIn(
            "SC_AUTHORIZATION_ORM_TEST_TAGS=payment_settlement_component_profile", makefile
        )

        runner = (ROOT / "scripts/test/admin_vis_p3_project_record_rule_orm.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("payment_settlement_component_profile)", runner)
        self.assertIn("timeout --signal=TERM --kill-after=30", runner)
        self.assertIn('source "$ROOT_DIR/scripts/ci/orm_result_guard.sh"', runner)
        self.assertIn("evaluate_orm_outcome", runner)
        # A 0 timeout would disable the watchdog and an unbounded one would let a
        # wedged run outlive every gate, so the runner validates the budget and
        # pins the identity/count of the fixed tag it launches.
        self.assertIn('validate_orm_timeout "$orm_timeout_seconds" || exit 2', runner)
        self.assertIn("orm_expect_count=7", runner)
        self.assertIn('orm_expect_identity="test_payment_settlement_component_profile"', runner)
        self.assertIn("validate_orm_expect_count", runner)
        self.assertIn("ADMIN_VIS_P3_CLEANUP_OK=", runner)

        # The rejection rules are container-free on purpose: this is the part of
        # the settlement ORM lane the docker-less Gitee executor can execute.
        guard = (ROOT / "scripts/ci/orm_result_guard.sh").read_text(encoding="utf-8")
        self.assertIn("validate_orm_timeout", guard)
        self.assertIn("validate_orm_expect_count", guard)
        self.assertIn("orm_expect_identity", guard)
        # Collection is proven from module-qualified test start lines only. A
        # bare `Starting ` count also matches Odoo lifecycle lines such as
        # `odoo.service.server: Starting post tests`, so it would both inflate
        # the count and satisfy the identity pin without the test running.
        self.assertIn("odoo\\.addons\\.[[:alnum:]_.]+: Starting ", guard)
        self.assertNotIn("grep -c 'Starting '", guard)
        self.assertIn('grep -F -- "${token}" >/dev/null', guard)
        self.assertNotIn('grep -qF -- "${token}"', guard)
        self.assertIn("odoo.service.server: Starting post tests", guard)
        self.assertIn("return 4", guard)
        self.assertIn("return 5", guard)
        self.assertIn("return 6", guard)
        self.assertIn("return 7", guard)
        self.assertIn("return 8", guard)
        self.assertIn('"${1:-}" == "--self-test"', guard)

        executor = (ROOT / "scripts/ci/gitee_formal_executor.py").read_text(encoding="utf-8")
        self.assertIn("unsupported_lane_requires_runtime_preparation", executor)
        self.assertIn('static("bash", "scripts/ci/orm_result_guard.sh", "--self-test")', executor)

        # Candidate PRs on Gitee resolve to public_guard/required, so the guard
        # self-test must be part of that lane's argv, not only of the
        # professional lanes that are not reachable without a runtime host.
        from scripts.ci.gitee_formal_executor import recipes

        public_guard_argv = [
            argv
            for argv, _ in recipes("public_guard", "required", "39a90e6da4f25c6942fdddb7aa07032dd02da7cc")
            if "orm_result_guard" in " ".join(argv)
        ]
        self.assertEqual(
            public_guard_argv,
            [["bash", "scripts/ci/orm_result_guard.sh", "--self-test"]],
        )

        module = (
            ROOT / "addons/smart_construction_core/tests/test_payment_settlement_component_profile.py"
        ).read_text(encoding="utf-8")
        self.assertIn('@tagged("payment_settlement_component_profile"', module)

    def test_shared_orm_installation_preserves_independent_verdicts(self) -> None:
        runner = (ROOT / "scripts/test/admin_vis_p3_project_record_rule_orm.sh").read_text()
        expectation = runner.split('set_suite_expectation() {', 1)[1].split('\ncase "${ENV:-dev}"', 1)[0]
        loop = runner.split('# Share only installation:', 1)[1]
        loop = loop[loop.index('base_test_log='):]
        # Execute the actual shell loop with a fake Odoo process, retaining the
        # real result guard. A clean first suite must never mask a bad second.
        fake = r"""
        timeout() {
          local tag= arg count=5 i
          while [ "$#" -gt 0 ]; do
            arg="$1"; shift
            if [ "$arg" = --test-tags ]; then tag="$1"; shift; fi
          done
          echo "$tag" >> "$CALLS"
          [ "$tag" != payment_settlement_component_profile ] || count=7
          if [ "$tag" = "$BAD_SUITE" ]; then
            case "$BAD_KIND" in
              exit) return 1 ;;
              zero) count=0 ;;
              truncated) count=6 ;;
              foreign) tag=wrong_suite ;;
            esac
          fi
          for ((i=0; i<count; i++)); do
            echo "INFO db odoo.addons.smart_core.tests.test_${tag}: Starting TestSuite.test_${i} ..."
          done
          echo "0 failed, 0 error(s) of $count tests"
        }
        """
        for bad_suite, kind in [('', ''), ('chatter_timeline_authorization_orm', 'zero'),
                                ('payment_settlement_component_profile', 'zero'),
                                ('payment_settlement_component_profile', 'truncated'),
                                ('payment_settlement_component_profile', 'foreign'),
                                ('payment_settlement_component_profile', 'exit')]:
            with self.subTest(suite=bad_suite, kind=kind), tempfile.TemporaryDirectory() as directory:
                script = ('set -euo pipefail\nsource scripts/ci/orm_result_guard.sh\n'
                          + 'set_suite_expectation() {' + expectation + '\n' + fake
                          + '\nsuite_tags=(chatter_timeline_authorization_orm payment_settlement_component_profile)\n'
                          + 'compose=(fake); odoo_common=(odoo); orm_timeout_seconds=30\n'
                          + 'test_log="$TEST_ROOT/test.log"; test_logs=()\n' + loop)
                result = subprocess.run(['bash', '-c', script], cwd=ROOT, text=True,
                                        capture_output=True, env={**os.environ, 'TEST_ROOT': directory,
                                        'CALLS': directory + '/calls', 'BAD_SUITE': bad_suite, 'BAD_KIND': kind})
                calls = Path(directory, 'calls').read_text().splitlines()
                self.assertEqual(result.returncode == 0, not bad_suite, result.stdout + result.stderr)
                self.assertEqual(len(calls), 1 if bad_suite.startswith('chatter') else 2)
                if not bad_suite:
                    self.assertEqual(result.stdout.count('suite='), 2)

    def test_nightly_candidate_is_separate_from_main_push(self) -> None:
        for workflow in (
            "frontend_release_gate.yml",
            "merge_policy_gate.yml",
            "professional_quality_gate.yml",
            "public_guard.yml",
            "release_candidate_gate.yml",
        ):
            text = self.text(workflow)
            self.assertIn("cron: '30 18 * * *'", text)
        frontend = self.text("frontend_release_gate.yml")
        self.assertIn("github.event_name == 'schedule'", frontend)
        self.assertIn("mode='full'", frontend)
        # The nightly schedule must not be cancelled by a concurrent main push:
        # every gate keys its concurrency group by the event kind, so push,
        # schedule and pull_request runs never share a group, while same-kind
        # re-runs still collapse. This is the concrete enforcement of the
        # separation asserted above.
        for workflow in (
            "frontend_release_gate.yml",
            "merge_policy_gate.yml",
            "professional_quality_gate.yml",
            "public_guard.yml",
            "release_candidate_gate.yml",
        ):
            group_lines = [
                line.strip()
                for line in self.text(workflow).splitlines()
                if line.strip().startswith("group:")
            ]
            self.assertEqual(len(group_lines), 1, workflow)
            self.assertIn("github.event_name", group_lines[0], workflow)
        self.assertNotIn("github.event_name != 'pull_request' || github.event.action", frontend)
        professional = self.text("professional_quality_gate.yml")
        self.assertEqual(
            professional.count(
                "if: github.event_name == 'schedule' || steps.risk.outputs.professional_mode == 'full'"
            ),
            2,
        )
        release = self.text("release_candidate_gate.yml")
        self.assertNotIn("  push:\n    branches: [main]", release)

        makefile = (ROOT / "make/ci.mk").read_text(encoding="utf-8")
        professional_target = makefile.split("ci.professional.backend:", 1)[1].split("\n", 1)[0]
        self.assertIn("verify.unified_page_contract.v2.professional_backend", professional_target)
        self.assertNotIn("verify.unified_page_contract.v2.frontend_static", professional_target)

    def test_cache_keys_bind_lockfile_and_runtime(self) -> None:
        text = self.text("frontend_release_gate.yml")
        self.assertIn("actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830", text)
        self.assertIn("actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020", text)
        self.assertIn("node-version: 22.17.0", text)
        self.assertIn("hashFiles('frontend/pnpm-lock.yaml')", text)
        self.assertIn("node22.17.0", text)

    def test_frontend_full_policy_is_surface_specific(self) -> None:
        policy = json.loads(
            (ROOT / "config/ci/risk_tiering_v1.json").read_text(encoding="utf-8")
        )
        patterns = set(policy["frontend_full_paths"])
        self.assertIn("frontend/pnpm-lock.yaml", patterns)
        self.assertIn(".github/workflows/frontend_release_gate.yml", patterns)
        self.assertNotIn("scripts/release/**", patterns)

    def test_professional_frontend_extension_surface_is_narrow_and_standard(self) -> None:
        policy = json.loads(
            (ROOT / "config/ci/risk_tiering_v1.json").read_text(encoding="utf-8")
        )
        owned = set(policy["standard_frontend_owned_paths"])
        self.assertEqual(
            owned,
            {
                "make/frontend_professional_extensions.mk",
                "scripts/verify/frontend_professional_*",
                "scripts/verify/test_frontend_professional_*",
            },
        )
        overrides = set(policy["high_risk_override_paths"])
        self.assertEqual(
            overrides,
            {
                "make/frontend_professional_extensions.mk",
                "scripts/ops/tooling_maintenance.py",
                "scripts/ops/test_tooling_maintenance.py",
            },
        )
        self.assertNotIn("make/frontend.mk", owned)
        self.assertNotIn("make/**", overrides)

    def test_high_risk_policy_contains_mandatory_surfaces(self) -> None:
        policy = json.loads(
            (ROOT / "config/ci/risk_tiering_v1.json").read_text(encoding="utf-8")
        )
        patterns = set(policy["high_risk_paths"])
        required = {
            ".github/workflows/**",
            "**/security/**",
            "**/ir.model.access.csv",
            "**/*tenant*payload*",
            "migrations/**",
            "deployment/**",
            "release/**",
            "Dockerfile*",
            "docker-compose*",
            "**/*identity*lock*",
            "**/pnpm-lock.yaml",
        }
        self.assertEqual(policy["default_lane"], "HIGH_RISK")
        self.assertFalse(required - patterns)

    def test_github_is_the_only_automatic_heavy_validator(self) -> None:
        duplicated = [
            path
            for path in ROOT.glob(".gitee/**/*")
            if path.is_file() and path.suffix in {".yml", ".yaml"}
        ]
        self.assertEqual(duplicated, [])


class ParallelQualityExecutionTest(unittest.TestCase):
    def jobs(self):
        return yaml.safe_load((ROOT / '.github/workflows/professional_quality_gate.yml').read_text())['jobs']

    def test_independent_work_is_parallel_and_protected_name_is_unique(self):
        jobs = self.jobs()
        self.assertEqual(jobs['professional_quality_checks']['needs'], 'professional_authorization')
        self.assertEqual(jobs['backend_impact_suite']['needs'], 'professional_authorization')
        self.assertEqual(set(jobs['professional_quality_gate']['needs']), {
            'professional_authorization', 'backend_impact_suite',
            'professional_quality_checks', 'python310_runtime_compatibility'})
        self.assertEqual(sum(job.get('name') == 'professional_quality_gate' for job in jobs.values()), 1)
        self.assertIn('!cancelled()', jobs['professional_quality_checks']['if'])
        self.assertIn("needs.professional_authorization.result == 'success'", jobs['professional_quality_checks']['if'])
        self.assertIn('always() && !cancelled()', jobs['professional_quality_gate']['if'])
        self.assertNotIn('always()', jobs['professional_quality_checks']['if'])
        self.assertTrue(all('checkout' not in step.get('name', '').lower()
                            for step in jobs['professional_quality_gate']['steps']))

    def test_actual_aggregate_script_rejects_missing_failed_cancelled_and_skipped(self):
        steps = self.jobs()['professional_quality_gate']['steps']
        step = next(s for s in steps if s['name'] == 'Enforce quality and compatibility execution')
        self.assertEqual(step['env']['QUALITY_RESULT'], '${{ needs.professional_quality_checks.result }}')
        self.assertEqual(step['env']['PYTHON_RESULT'], '${{ needs.python310_runtime_compatibility.result }}')
        for event in ('pull_request', 'schedule', 'workflow_dispatch', 'push'):
            for quality in ('success', 'failure', 'cancelled', 'skipped', ''):
                for python in ('success', 'failure', 'cancelled', 'skipped', ''):
                    with self.subTest(event=event, quality=quality, python=python):
                        expected = quality == 'success' and python == ('skipped' if event == 'push' else 'success')
                        result = subprocess.run(['bash', '-c', step['run']],
                            env={**os.environ, 'EVENT_NAME': event, 'QUALITY_RESULT': quality, 'PYTHON_RESULT': python},
                            capture_output=True, text=True)
                        self.assertEqual(result.returncode == 0, expected)


if __name__ == "__main__":
    unittest.main()

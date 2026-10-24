#!/usr/bin/env python3
from __future__ import annotations

import unittest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import ci_risk_classifier

from ci_risk_classifier import classify


class CIRiskClassifierTests(unittest.TestCase):
    def lane(self, *paths: str, event: str = "pull_request", ref: str = "") -> str:
        return classify(paths, event_name=event, ref=ref).lane

    def test_git_diff_includes_deletions_and_both_rename_owners(self):
        with patch.object(ci_risk_classifier.subprocess, 'run', return_value=SimpleNamespace(
                stdout='addons/old/models/a.py\naddons/new/models/a.py\n')) as run:
            paths = ci_risk_classifier.changed_paths('base', 'head')
        command = run.call_args.args[0]
        self.assertIn('--no-renames', command)
        self.assertFalse(any(value.startswith('--diff-filter') for value in command))
        self.assertTrue(classify(paths, event_name='pull_request').orm_required)

    def test_documentation_is_fast(self) -> None:
        self.assertEqual(self.lane("docs/ops/runbook.md"), "FAST")

    def test_tooling_maintenance_lane_is_fast(self) -> None:
        result = classify(
            [
                "scripts/ops/tooling_maintenance.py",
                "scripts/ops/test_tooling_maintenance.py",
                "docs/ops/tooling_maintenance_fast_lane_20261020.md",
            ],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "FAST")
        self.assertEqual(result.professional_mode, "fast")
        self.assertEqual(result.frontend_mode, "skip")
        self.assertFalse(result.backend_changed)

    def test_agent_workflow_metadata_is_fast(self) -> None:
        result = classify(
            [
                ".agent/workflows/frontend-professionalization.yaml",
                "docs/ops/iterations/delivery_context_switch_log_v1.md",
            ],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "FAST")
        self.assertEqual(result.frontend_mode, "skip")
        self.assertEqual(result.professional_mode, "fast")

    def test_other_agent_authority_remains_fail_closed(self) -> None:
        self.assertEqual(self.lane(".agent/context.yaml"), "HIGH_RISK")
        self.assertEqual(self.lane(".agent/decisions/runtime-authority.yaml"), "HIGH_RISK")

    def test_version_only_change_is_fast_but_not_unclassified(self) -> None:
        result = classify(["VERSION"], event_name="pull_request")
        self.assertEqual(result.lane, "FAST")
        self.assertEqual(result.professional_mode, "fast")
        self.assertEqual(result.frontend_mode, "skip")

    def test_frontend_is_standard(self) -> None:
        result = classify(
            ["frontend/apps/web/src/pages/ProjectListPage.vue"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "STANDARD")
        self.assertEqual(result.frontend_mode, "standard")

    def test_professional_frontend_delivery_batch_avoids_release_and_backend_lanes(self) -> None:
        result = classify(
            [
                "frontend/apps/web/src/components/professional/ProfessionalWbsTree.vue",
                "frontend/apps/web/scripts/professional_wbs_tree_model_test.ts",
                "scripts/verify/frontend_professional_wbs_tree_guard.py",
                "scripts/verify/test_frontend_professional_wbs_tree_guard.py",
                "make/frontend_professional_extensions.mk",
            ],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "STANDARD")
        self.assertEqual(result.frontend_mode, "standard")
        self.assertEqual(result.professional_mode, "standard_frontend")
        self.assertTrue(result.frontend_changed)
        self.assertFalse(result.backend_changed)
        self.assertFalse(result.frontend_full_required)

    def test_only_exact_frontend_extension_makefile_is_standard(self) -> None:
        self.assertEqual(
            self.lane("make/frontend_professional_extensions.mk"),
            "STANDARD",
        )
        self.assertEqual(self.lane("make/frontend.mk"), "HIGH_RISK")
        self.assertEqual(self.lane("make/ci.mk"), "HIGH_RISK")

    def test_non_frontend_verify_script_remains_backend(self) -> None:
        result = classify(
            ["scripts/verify/backend_contract_guard.py"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "STANDARD")
        self.assertTrue(result.backend_changed)
        self.assertFalse(result.frontend_changed)

    def test_frontend_guard_name_cannot_override_identity_high_risk_rule(self) -> None:
        result = classify(
            ["scripts/verify/frontend_professional_identity_lock_guard.py"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.professional_mode, "full")

    def test_backend_is_standard(self) -> None:
        result = classify(
            ["addons/smart_construction_core/models/project.py"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "STANDARD")
        self.assertEqual(result.professional_mode, "standard_backend")

    def test_p4_executor_batch_does_not_require_orm(self) -> None:
        result = classify([
            '.agent/context.yaml', '.agent/runs/P4-INCREMENTAL-RESUME/run.json',
            '.codex/skills/project-governance-codex/SKILL.md', 'AGENTS.md',
            'make/ci.mk', 'make/codex.mk', 'scripts/ops/agent_run_context.py',
            'scripts/verify/test_agent_run_context.py', 'scripts/verify/frontend_dev_incremental.py',
            'scripts/ci/trusted_scan_scope.py', 'config/ci/risk_tiering_v1.json',
            '.github/workflows/professional_quality_gate.yml',
        ], event_name='pull_request')
        self.assertEqual(result.lane, 'HIGH_RISK')
        self.assertTrue(result.backend_changed)  # broad existing static-test ownership retained
        self.assertFalse(result.orm_required)
        self.assertEqual(result.outputs()['orm_required'], 'false')

    def test_orm_runtime_and_runner_changes_still_require_orm(self) -> None:
        for path in ('addons/smart_core/models/core.py', 'customer_addons/acme/models.py',
                     'addons_external/oca_server_ux/security/ir.model.access.csv',
                     'addons_external/oca_server_ux/models/model.py',
                     'addons_external/oca_server_ux/__manifest__.py',
                     'addons_external/oca_server_ux/security/groups.xml',
                     'demo_addons/demo/security/ir.model.access.csv',
                     'addons/smart_construction_core/tests/test_payment_settlement_component_profile.py',
                     'scripts/test/admin_vis_p3_project_record_rule_orm.sh', 'scripts/ci/orm_result_guard.sh',
                     'make/dev_test.mk', 'requirements-odoo.txt', 'Dockerfile', 'docker-compose.yml',
                     'migrations/upgrade.py', 'tests/runtime/test_model.py'):
            with self.subTest(path=path):
                self.assertTrue(classify([path], event_name='pull_request').orm_required)
        self.assertTrue(classify(['scripts/ops/agent_run_context.py',
                                 'addons/smart_core/models/core.py'], event_name='pull_request').orm_required)

    def test_orm_unknown_empty_release_and_missing_policy_fail_closed(self) -> None:
        for paths in ([], ['unclassified/runtime.bin'], ['../invalid.py']):
            self.assertTrue(classify(paths, event_name='pull_request').orm_required)
        self.assertTrue(classify(['docs/readme.md'], event_name='workflow_dispatch').orm_required)
        self.assertTrue(classify(['docs/readme.md'], event_name='push', ref='refs/tags/v1').orm_required)
        from ci_risk_classifier import load_policy
        policy = load_policy();policy.pop('orm_runtime_paths')
        with self.assertRaises(ValueError):
            classify(['docs/readme.md'], event_name='pull_request', policy=policy)
        for key in ('orm_runtime_paths', 'orm_non_runtime_context_paths'):
            for bad in ('addons/**', [False], ['']):
                policy = load_policy();policy[key] = bad
                with self.assertRaises(ValueError):
                    classify(['docs/readme.md'], event_name='pull_request', policy=policy)

    def test_security_xml_is_high_risk(self) -> None:
        self.assertEqual(
            self.lane("addons/smart_core/security/smart_core_groups.xml"),
            "HIGH_RISK",
        )

    def test_importer_is_high_risk(self) -> None:
        self.assertEqual(
            self.lane("addons/smart_core/services/tenant_payload_importer.py"),
            "HIGH_RISK",
        )

    def test_migration_is_high_risk(self) -> None:
        self.assertEqual(self.lane("migrations/18.0.1/post.py"), "HIGH_RISK")

    def test_workflow_is_high_risk(self) -> None:
        result = classify(
            [".github/workflows/professional_quality_gate.yml"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "skip")

    def test_frontend_gate_workflow_requires_full_frontend_release(self) -> None:
        result = classify(
            [".github/workflows/frontend_release_gate.yml"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "full")

    def test_ci_risk_policy_change_is_high_risk_without_product_frontend_release(self) -> None:
        result = classify(
            [
                "config/ci/risk_tiering_v1.json",
                "scripts/ci/test_ci_risk_classifier.py",
            ],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.professional_mode, "full")
        self.assertEqual(result.frontend_mode, "skip")

    def test_docker_and_release_are_high_risk_on_pr(self) -> None:
        self.assertEqual(self.lane("Dockerfile"), "HIGH_RISK")
        result = classify(["scripts/release/publish.py"], event_name="pull_request")
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "skip")
        self.assertEqual(result.professional_mode, "full")

    def test_frontend_release_image_is_full(self) -> None:
        result = classify(
            ["Dockerfile.production-frontend-builder"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "full")

    def test_mixed_change_uses_highest_risk(self) -> None:
        self.assertEqual(
            self.lane("docs/readme.md", "addons/smart_core/security/ir.model.access.csv"),
            "HIGH_RISK",
        )

    def test_unknown_path_fails_closed(self) -> None:
        self.assertEqual(self.lane("unexpected/new-surface.bin"), "HIGH_RISK")

    def test_empty_change_set_fails_closed(self) -> None:
        self.assertEqual(self.lane(), "HIGH_RISK")

    def test_dispatch_and_tag_are_release(self) -> None:
        self.assertEqual(self.lane(event="workflow_dispatch"), "RELEASE")
        self.assertEqual(
            self.lane("docs/release.md", event="push", ref="refs/tags/v1.0.0"),
            "RELEASE",
        )

    def test_lockfiles_are_high_risk(self) -> None:
        result = classify(["frontend/pnpm-lock.yaml"], event_name="pull_request")
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "full")

    def test_mixed_backend_risk_and_frontend_source_is_standard_frontend(self) -> None:
        result = classify(
            [
                "addons/smart_core/security/ir.model.access.csv",
                "frontend/apps/web/src/App.vue",
            ],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "standard")

    def test_path_escape_fails_closed(self) -> None:
        self.assertEqual(self.lane("../security.xml"), "HIGH_RISK")


class BackendRecipeScopeTests(unittest.TestCase):
    before = ('SHARED := unchanged\n'
              'verify.ci.workflow.contract: guard.prod.forbid verify.ci.orm_selection.unit\n'
              '\t@python3 scripts/ci/test_a.py\n'
              '\t@echo "PASS"\n\n'
              'frontend.other:\n\t@echo "frontend"\n')
    after = before.replace('\t@python3 scripts/ci/test_a.py\n',
                           '\t@python3 scripts/ci/test_a.py\n'
                           '\t@python3 -m unittest scripts.verify.test_backend_probe\n')

    def test_literal_backend_recipe_change_is_recognized(self):
        self.assertTrue(ci_risk_classifier.backend_recipe_only(self.before, self.after))
        self.assertTrue(ci_risk_classifier.backend_recipe_only(self.after, self.before))
        self.assertFalse(ci_risk_classifier.backend_recipe_only(self.before, self.before))

    def test_other_bytes_and_dynamic_commands_remain_conservative(self):
        for changed in (
            self.after.replace('unchanged', 'changed'),
            self.after.replace('guard.prod.forbid ', ''),
            self.after.replace('echo "frontend"', 'echo "changed"'),
            self.after + 'include extra.mk\n',
            self.after + '\t$(eval SHARED := changed)\n',
            self.after.replace('scripts.verify.test_backend_probe', '$(PROBE)'),
            self.after.replace('scripts.verify.test_backend_probe', 'scripts.verify.test_backend_probe; false'),
            self.after.replace('scripts.verify.test_backend_probe\n', 'scripts.verify.test_backend_probe\\\n\tmore\n'),
            self.after.replace('scripts.verify.test_backend_probe', 'scripts.verify.test_backend_probe # extra'),
            self.after.replace('\t@echo "PASS"', '\t@echo "different"'),
        ):
            with self.subTest(changed=changed):
                self.assertFalse(ci_risk_classifier.backend_recipe_only(self.before, changed))

    def test_path_only_and_missing_identity_keep_full(self):
        self.assertEqual(classify(['make/ci.mk'], event_name='pull_request').frontend_mode, 'full')
        self.assertFalse(ci_risk_classifier.git_backend_recipe_only('main', 'HEAD'))
        with patch.object(ci_risk_classifier.subprocess, 'run', side_effect=subprocess.TimeoutExpired('git', 15)):
            self.assertFalse(ci_risk_classifier.git_backend_recipe_only('a'*40, 'b'*40))

    def test_exact_git_scope_preserves_other_triggers_and_ignores_dirty_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
                    '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    '-c', 'commit.gpgsign=false', '-c', 'core.autocrlf=false', *args], cwd=root, stderr=subprocess.DEVNULL,
                    text=True).strip()
            git('init', '-q'); (root/'make').mkdir()
            path = root/'make/ci.mk'; path.write_text(self.before)
            git('add', '.'); git('commit', '-qm', 'base'); base = git('rev-parse', 'HEAD')
            path.write_text(self.after)
            git('add', '.'); git('commit', '-qm', 'backend recipe'); head = git('rev-parse', 'HEAD')
            path.write_text('uncommitted unrelated content\n')
            with patch.object(ci_risk_classifier, 'ROOT', root):
                result = classify(['make/ci.mk'], event_name='pull_request', base=base, head=head)
                self.assertEqual(result.frontend_mode, 'skip')
                self.assertEqual(result.professional_mode, 'full')
                self.assertEqual(result.lane, 'HIGH_RISK')
                self.assertIn('make_ci_backend_recipe_only_exact_git_scope', result.reasons)
                for extra, expected in [('frontend/pnpm-lock.yaml', 'full'),
                                        ('frontend/apps/web/src/new.ts', 'standard')]:
                    self.assertEqual(classify(['make/ci.mk', extra], event_name='pull_request',
                        base=base, head=head).frontend_mode, expected)
                self.assertEqual(classify(['make/ci.mk'], event_name='workflow_dispatch',
                    base=base, head=head).frontend_mode, 'full')
                for newline in ('\r\n', '\r'):
                    path.write_bytes(self.after.replace('unchanged\n', 'unchanged'+newline).encode())
                    git('add', '.'); git('commit', '-qm', 'retained newline bytes change')
                    self.assertFalse(ci_risk_classifier.git_backend_recipe_only(base, git('rev-parse', 'HEAD')))
                path.write_text(self.after.replace('unchanged', 'changed'))
                git('add', '.'); git('commit', '-qm', 'global change'); global_head = git('rev-parse', 'HEAD')
                self.assertEqual(classify(['make/ci.mk'], event_name='pull_request',
                    base=base, head=global_head).frontend_mode, 'full')
                # Diverged target branch: scope is merge-base..head, not base..head.
                git('checkout', '-q', base)
                path.write_text(self.before.replace('unchanged', 'other branch'))
                git('add', '.'); git('commit', '-qm', 'base advances'); advanced = git('rev-parse', 'HEAD')
                self.assertTrue(ci_risk_classifier.git_backend_recipe_only(advanced, head))
                git('checkout', '-q', head); path.unlink(); path.symlink_to('other.mk')
                git('add', '.'); git('commit', '-qm', 'symlink'); link_head = git('rev-parse', 'HEAD')
                self.assertFalse(ci_risk_classifier.git_backend_recipe_only(base, link_head))


if __name__ == "__main__":
    unittest.main()

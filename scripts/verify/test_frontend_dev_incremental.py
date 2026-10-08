from __future__ import annotations

import io
import re
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.verify.frontend_dev_incremental import (
    FALLBACK_TARGET,
    RULES,
    iteration_plan,
    print_plan,
    select_targets,
    worktree_changed_paths,
)
from scripts.verify.frontend_style_system_guard import (
    RECORD_RUNTIME_SIZE_LIMITS,
    SIZE_LIMITS,
)


class FrontendDevelopmentIncrementalTest(unittest.TestCase):
    def test_auth_entry_changes_select_only_auth_surface_checks(self) -> None:
        targets = select_targets(["frontend/apps/web/src/views/LoginView.vue"])
        self.assertEqual(
            targets,
            [
                "verify.frontend.auth_credential.guard",
                "verify.frontend.auth_surface.guard",
                "verify.frontend.page_pattern_reference_parity.unit",
            ],
        )

    def test_activation_and_recovery_changes_share_auth_surface_checks(self) -> None:
        for path in (
            "frontend/apps/web/src/views/AccountActivationView.vue",
            "frontend/apps/web/src/views/PasswordRecoveryView.vue",
        ):
            self.assertEqual(
                select_targets([path]),
                [
                    "verify.frontend.auth_credential.guard",
                    "verify.frontend.auth_surface.guard",
                    "verify.frontend.page_pattern_reference_parity.unit",
                ],
            )

    def test_related_changes_are_merged_and_deduplicated(self) -> None:
        targets = select_targets(
            [
                "frontend/apps/web/src/layouts/AppShell.vue",
                "frontend/apps/web/src/layouts/AppShell.css",
                "frontend/apps/web/src/components/design-system/ScCard.vue",
            ]
        )
        self.assertEqual(targets.count("verify.frontend.page_pattern_reference_parity.unit"), 1)
        self.assertIn("verify.frontend.navigation_shell.unit", targets)
        self.assertIn("verify.frontend.primitive_adapter.unit", targets)

    def test_scene_route_change_recommends_scene_entry_contract(self) -> None:
        # The scene runtime is cached by <KeepAlive> and its route ownership rule
        # must be re-verified whenever the view or the rule module changes.
        for path in (
            "frontend/apps/web/src/views/SceneView.vue",
            "frontend/apps/web/src/app/sceneEntryContract.ts",
        ):
            self.assertEqual(
                select_targets([path]),
                [
                    "verify.frontend.navigation_shell.unit",
                    "verify.frontend.scene_entry_contract.unit",
                ],
            )

    def test_size_ratcheted_files_route_to_the_size_guard(self) -> None:
        # A file with a size ratchet can only be caught by style_system.guard.
        # If the ratchet is extended without extending the routing, the file
        # silently falls back to typecheck and can grow past its limit again.
        ratcheted = [path.relative_to(Path(__file__).resolve().parents[2]).as_posix() for path in SIZE_LIMITS]
        ratcheted += [
            f"frontend/apps/web/src/pages/contractForm/{name}"
            for name in RECORD_RUNTIME_SIZE_LIMITS
        ]
        self.assertTrue(ratcheted)
        for path in ratcheted:
            with self.subTest(path=path):
                self.assertIn("verify.frontend.style_system.guard", select_targets([path]))

    def test_contract_basis_ledger_and_guard_changes_route_to_the_contract_gate(self) -> None:
        # The ledger and its guard are the direct inputs of the contract-basis
        # behavioural lock. A change to either one that falls through as
        # "unmapped" leaves the completeness gap to be found only at delivery
        # freeze time, so both must route to the contract gate explicitly.
        for path in (
            "docs/architecture/frontend_contract_basis_ledger.json",
            "scripts/verify/frontend_contract_basis_guard.py",
            "scripts/verify/test_frontend_contract_basis_guard.py",
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                self.assertIn("verify.frontend.contract_basis.unit", targets)
                self.assertIn("verify.frontend.contract_basis.enforce", targets)

    def test_planner_change_routes_to_the_planner_behaviour_lock(self) -> None:
        # The planner code, its lock and the makefile that defines the target
        # names are one contract. Without this route a renamed target turns
        # "reuse the smallest affected check" into a hard make failure.
        for path in (
            "scripts/verify/frontend_dev_incremental.py",
            "scripts/verify/test_frontend_dev_incremental.py",
            "make/frontend.mk",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.dev.incremental.unit"],
                )

    def test_every_recommended_target_is_defined_by_a_makefile(self) -> None:
        # A recommendation that no makefile defines would break the smallest
        # affected check and push the reader back to a manual, broad run.
        makefiles = sorted((Path(__file__).resolve().parents[2] / "make").glob("*.mk"))
        self.assertTrue(makefiles)
        text = "\n".join(path.read_text(encoding="utf-8") for path in makefiles)
        targets = sorted({target for rule in RULES for target in rule.targets} | {FALLBACK_TARGET})
        self.assertTrue(targets)
        for target in targets:
            with self.subTest(target=target):
                self.assertRegex(text, rf"(?m)^{re.escape(target)}:")

    def test_run_bookkeeping_alone_is_not_an_unmapped_product_path(self) -> None:
        # Reconciling `.agent/` state carries no frontend source input: reporting
        # it as unmapped would demand a manual L2 selection with nothing to pick.
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(
                    [
                        ".agent/active-runs.json",
                        ".agent/runs/TEST/run.json",
                    ]
                ),
                0,
            )
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual(payload["unmappedPaths"], [])
        self.assertFalse(payload["manualNonZeroL2Required"])

    def test_real_unmapped_path_still_requires_manual_l2(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(
                    [
                        ".agent/active-runs.json",
                        "addons/smart_core/models/example.py",
                    ]
                ),
                0,
            )
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual(payload["unmappedPaths"], ["addons/smart_core/models/example.py"])
        self.assertTrue(payload["manualNonZeroL2Required"])

    def test_template_consumer_change_recommends_primitive_adapter(self) -> None:
        targets = select_targets(
            ["frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue"]
        )
        self.assertIn("verify.frontend.primitive_adapter.unit", targets)

    def test_ui_package_theme_change_recommends_primitive_adapter(self) -> None:
        targets = select_targets(["frontend/packages/ui/src/kits/tdesign/theme.css"])
        self.assertIn("verify.frontend.primitive_adapter.unit", targets)

    def test_unmapped_frontend_change_fails_safe_to_typecheck(self) -> None:
        self.assertEqual(
            select_targets(["frontend/apps/web/src/new-area/NewSurface.vue"]),
            [FALLBACK_TARGET],
        )

    def test_non_frontend_change_does_not_trigger_frontend_validation(self) -> None:
        self.assertEqual(select_targets(["docs/example.md"]), [])

    def test_development_selection_never_contains_candidate_work(self) -> None:
        targets = select_targets(
            [
                "frontend/apps/web/src/views/LoginView.vue",
                "frontend/apps/web/src/pages/contractForm/ContractForm.vue",
            ]
        )
        joined = " ".join(targets)
        for forbidden in ("quick", "build", "browser", "release", "fingerprint"):
            self.assertNotIn(forbidden, joined)

    def test_worktree_plan_includes_committed_dirty_and_untracked_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Codex Test"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "codex-test@example.invalid"],
                check=True,
            )
            baseline = root / "baseline.txt"
            baseline.write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "baseline.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)
            baseline_sha = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(root), "update-ref", "refs/remotes/origin/main", baseline_sha],
                check=True,
            )

            committed = root / "frontend/apps/web/src/components/template/Committed.vue"
            committed.parent.mkdir(parents=True)
            committed.write_text("committed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "topic"], check=True)
            committed.write_text("dirty\n", encoding="utf-8")
            untracked = root / "frontend/packages/ui/src/new-theme.css"
            untracked.parent.mkdir(parents=True)
            untracked.write_text("untracked\n", encoding="utf-8")

            self.assertEqual(
                worktree_changed_paths(root),
                [
                    "frontend/apps/web/src/components/template/Committed.vue",
                    "frontend/packages/ui/src/new-theme.css",
                ],
            )

    def test_plan_reports_recommendations_without_running_tests(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(["frontend/packages/ui/src/kits/tdesign/theme.css"]),
                0,
            )
        text = output.getvalue()
        self.assertIn('"status": "recommendation_only"', text)
        self.assertIn('"testsRun": false', text)
        self.assertIn("verify.frontend.primitive_adapter.unit", text)

    def test_plan_keeps_manual_l2_for_unmapped_paths_in_mixed_change(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(
                    [
                        "frontend/packages/ui/src/kits/tdesign/theme.css",
                        "addons/smart_core/models/example.py",
                    ]
                ),
                0,
            )
        text = output.getvalue()
        self.assertIn('"manualNonZeroL2Required": true', text)
        self.assertIn('"unmappedPathCount": 1', text)
        self.assertIn('"unmappedPaths": ["addons/smart_core/models/example.py"]', text)
        self.assertIn("verify.frontend.primitive_adapter.unit", text)


class RunScopedPlannerTest(unittest.TestCase):
    def setUp(self):
        from scripts.verify.test_agent_run_context import RunContextTest
        self.fixture = RunContextTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_registered_run_does_not_need_origin_or_reinventory_branch_history(self):
        fixture = self.fixture
        fixture.run['baseline_sha'] = fixture.git('rev-parse', 'HEAD')
        fixture.save()
        fixture.write('source/new.py', 'change')
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(iteration_plan(fixture.root), 0)
        self.assertIn('.agent/runs/TEST/run.json', output.getvalue())
        self.assertNotIn('branch_fallback', output.getvalue())
        self.assertNotIn('source/a.py', output.getvalue())
        self.assertIn('source/new.py', output.getvalue())

    def test_receipt_advice_never_claims_tests_ran(self):
        self.fixture.receipt()
        output = io.StringIO()
        with redirect_stdout(output): iteration_plan(self.fixture.root)
        self.assertIn('reusable', output.getvalue())
        self.assertIn('"testsRun": false', output.getvalue())

    def test_reusable_target_is_not_recommended_again(self):
        self.fixture.receipt()
        output = io.StringIO()
        with redirect_stdout(output): iteration_plan(self.fixture.root)
        payload = json.loads(output.getvalue().split('] ', 1)[1])
        self.assertIn('verify.test', payload['reusedTargets'])
        self.assertNotIn('verify.test', payload['targets'])

    def test_unchanged_failure_is_blocked_not_blindly_retried(self):
        self.fixture.receipt('failed', 2)
        output = io.StringIO()
        with redirect_stdout(output): iteration_plan(self.fixture.root)
        payload = json.loads(output.getvalue().split('] ', 1)[1])
        self.assertIn('verify.test', payload['blockedTargets'])
        self.assertNotIn('verify.test', payload['targets'])

    def test_missing_registration_cannot_trigger_full_branch_inventory(self):
        from scripts.ops.agent_run_context import RunError
        (self.fixture.root / ".agent/active-runs.json").unlink()
        with self.assertRaises(RunError): iteration_plan(self.fixture.root)

    def test_invalid_registration_cannot_silently_fallback(self):
        from scripts.ops.agent_run_context import RunError
        self.fixture.run['branch'] = 'fix/other'
        self.fixture.save()
        with self.assertRaises(RunError): iteration_plan(self.fixture.root)


if __name__ == "__main__":
    unittest.main()

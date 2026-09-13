from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.verify.frontend_dev_incremental import (
    FALLBACK_TARGET,
    print_plan,
    select_targets,
    worktree_changed_paths,
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


if __name__ == "__main__":
    unittest.main()

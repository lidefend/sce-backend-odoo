from __future__ import annotations

import unittest

from scripts.verify.frontend_dev_incremental import FALLBACK_TARGET, select_targets


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


if __name__ == "__main__":
    unittest.main()

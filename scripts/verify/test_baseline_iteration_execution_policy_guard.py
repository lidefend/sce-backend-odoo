#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import baseline_iteration_execution_policy_guard as guard


class BaselineIterationExecutionPolicyGuardTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        for relative, fragments in guard.DOCUMENT_REQUIREMENTS.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join((guard.MARKER, *fragments)), encoding="utf-8")
        for relative, targets in guard.MAKE_TARGET_REQUIREMENTS.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            text = "\n".join(f"{target}:" for target in targets)
            if relative == Path("make/codex.mk"):
                text = text.replace(
                    f"{guard.PR_PUSH_TEST_TARGET}:",
                    f"{guard.PR_PUSH_TEST_TARGET}:\n\t@{guard.PR_PUSH_TEST_COMMAND}",
                    1,
                )
            if relative == Path("make/ci.mk"):
                text += "\n" + guard.ITERATION_TARGET + ": " + " ".join(
                    item for item in guard.ITERATION_REQUIRED if " " not in item
                )
                text += "\n\t@git diff --check"
                text += "\n\t@python3 scripts/verify/frontend_dev_incremental.py --plan-worktree"
                text += "\n\t@git status --porcelain=v1 --untracked-files=all"
                text += "\n" + guard.QUICK_TARGET + ": " + " ".join(guard.QUICK_DIRECT_REQUIRED)
                text += "\n" + guard.FREEZE_PREPARE_TARGET + ":"
                for step in guard.FREEZE_PREPARE_REQUIRED_ORDER:
                    text += f"\n\t@$(MAKE) --no-print-directory {step}"
                for owner, dependency in guard.TYPECHECK_CHAIN:
                    text += f"\n{owner}: {dependency}"
            path.write_text(text, encoding="utf-8")
        frontend_make = root / "make/frontend.mk"
        frontend_make.parent.mkdir(parents=True, exist_ok=True)
        frontend_make.write_text(
            f"{guard.TYPECHECK_TARGET}:\n"
            f"\t@scripts/dev/{guard.TYPECHECK_COMMAND}\n"
            f"{guard.FRONTEND_INCREMENTAL_TEST_TARGET}:\n"
            f"\t@{guard.FRONTEND_INCREMENTAL_TEST_COMMAND}\n",
            encoding="utf-8",
        )

    def test_complete_policy_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            self.assertEqual(guard.validate(root), [])

    def test_missing_rule_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "AGENTS.md"
            path.write_text(guard.MARKER, encoding="utf-8")
            self.assertTrue(any("missing locked rule" in error for error in guard.validate(root)))

    def test_every_locked_document_rule_is_enforced(self) -> None:
        for relative, fragments in guard.DOCUMENT_REQUIREMENTS.items():
            for fragment in fragments:
                with self.subTest(relative=str(relative), fragment=fragment):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        self.fixture(root)
                        path = root / relative
                        text = path.read_text(encoding="utf-8")
                        path.write_text(text.replace(fragment, "", 1), encoding="utf-8")
                        errors = guard.validate(root)
                        self.assertIn(
                            f"{relative}: missing locked rule {fragment!r}",
                            errors,
                        )

    def test_missing_authoritative_target_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/runtime_ops.mk"
            path.write_text("acceptance.module.upgrade:\n", encoding="utf-8")
            self.assertTrue(any("authoritative target missing" in error for error in guard.validate(root)))

    def test_iteration_target_rejects_broad_inner_loop_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    guard.ITERATION_TARGET + ":",
                    guard.ITERATION_TARGET + ": security.personal_data_scan",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/ci.mk: ci.local.iteration includes forbidden broad gate 'security.personal_data_scan'",
                guard.validate(root),
            )

    def test_iteration_target_requires_dirty_scope_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "next=risk_selected_non_zero_L2_targets_required",
                    "next=none",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/ci.mk: ci.local.iteration missing lightweight contract "
                "'next=risk_selected_non_zero_L2_targets_required'",
                guard.validate(root),
            )

    def test_iteration_target_requires_untracked_path_detection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "git status --porcelain=v1 --untracked-files=all",
                    "git status --porcelain=v1",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/ci.mk: ci.local.iteration missing lightweight contract "
                "'git status --porcelain=v1 --untracked-files=all'",
                guard.validate(root),
            )

    def test_iteration_target_requires_frontend_l2_recommendation_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "python3 scripts/verify/frontend_dev_incremental.py --plan-worktree",
                    "echo no-l2-plan",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/ci.mk: ci.local.iteration missing lightweight contract "
                "'frontend_dev_incremental.py --plan-worktree'",
                guard.validate(root),
            )

    def test_quick_target_requires_deduplicated_frontend_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    " " + guard.QUICK_DIRECT_REQUIRED[1],
                    "",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/ci.mk: ci.local.quick.run missing deduplicated prerequisite "
                "'verify.frontend.lint.src'",
                guard.validate(root),
            )

    def test_quick_target_requires_incremental_planner_unit_suite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    " " + guard.FRONTEND_INCREMENTAL_TEST_TARGET,
                    "",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/ci.mk: ci.local.quick.run missing deduplicated prerequisite "
                f"'{guard.FRONTEND_INCREMENTAL_TEST_TARGET}'",
                guard.validate(root),
            )

    def test_freeze_prepare_requires_all_steps_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            text = path.read_text(encoding="utf-8")
            first, second = guard.FREEZE_PREPARE_REQUIRED_ORDER[:2]
            text = text.replace(
                f"\t@$(MAKE) --no-print-directory {first}\n"
                f"\t@$(MAKE) --no-print-directory {second}",
                f"\t@$(MAKE) --no-print-directory {second}\n"
                f"\t@$(MAKE) --no-print-directory {first}",
                1,
            )
            path.write_text(text, encoding="utf-8")
            self.assertIn(
                "make/ci.mk: ci.delivery.freeze.prepare generated-evidence steps are out of order",
                guard.validate(root),
            )

    def test_incremental_planner_unit_target_is_registered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/frontend.mk"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    guard.FRONTEND_INCREMENTAL_TEST_COMMAND,
                    "echo missing-unit-suite",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/frontend.mk: verify.frontend.dev.incremental.unit must invoke its unit suite exactly once",
                guard.validate(root),
            )

    def test_push_self_test_target_is_registered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/codex.mk"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    guard.PR_PUSH_TEST_COMMAND,
                    "echo missing-push-self-test",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/codex.mk: verify.pr.push.unit must invoke its self-test exactly once",
                guard.validate(root),
            )

    def test_quick_target_rejects_direct_strict_typecheck_edge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    guard.QUICK_TARGET + ":",
                    guard.QUICK_TARGET + ": verify.frontend.typecheck.strict",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/ci.mk: ci.local.quick.run duplicates transitive prerequisite "
                "'verify.frontend.typecheck.strict'",
                guard.validate(root),
            )

    def test_quick_target_requires_complete_strict_typecheck_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            owner, dependency = guard.TYPECHECK_CHAIN[-1]
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    f"{owner}: {dependency}",
                    f"{owner}:",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                f"make/ci.mk: strict typecheck chain broken: {owner} -> {dependency}",
                guard.validate(root),
            )

    def test_quick_target_rejects_repeated_frontend_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/ci.mk"
            quick_line = guard.QUICK_TARGET + ": " + " ".join(guard.QUICK_DIRECT_REQUIRED)
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    quick_line,
                    quick_line
                    + "\n\t@scripts/dev/pnpm_exec.sh -C frontend/apps/web typecheck:strict",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "make/ci.mk: ci.local.quick.run repeats prerequisite command "
                "'pnpm_exec.sh -C frontend/apps/web typecheck:strict'",
                guard.validate(root),
            )


if __name__ == "__main__":
    unittest.main()

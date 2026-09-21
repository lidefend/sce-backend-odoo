#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
import node_syntax_check

ROOT = node_syntax_check.ROOT
MAKE_CI = ROOT / "make" / "ci.mk"

SWEEP_SCRIPT = "scripts/ci/node_syntax_check.py"
# The exact recipe line every gate must carry: the corpus-wide sweep with NO
# argument. Matching the whole line (not a substring) is what stops the calling
# point from being silently narrowed to a subset of the corpus.
SWEEP_RECIPE = f"\t@python3 {SWEEP_SCRIPT}"
SWEEP_SELF_TEST_RECIPE = "\t@python3 scripts/ci/test_node_syntax_check.py"
SWEEP_CALL_RE = re.compile(rf"(?:^|\s){re.escape(SWEEP_SCRIPT)}(?:\s|$)")

# The hand-maintained list test.contract used before this gate existed. The
# sweep must keep covering every one of them.
HISTORIC_CONTRACT_FILES = (
    "frontend/apps/web/scripts/config_workbench_operation_acceptance.mjs",
    "frontend/apps/web/scripts/business_form_user_perspective_acceptance.mjs",
    "frontend/apps/web/scripts/system_user_experience_shell_acceptance.mjs",
    "frontend/apps/web/scripts/user_page_visual_coverage.cjs",
    "frontend/apps/web/scripts/system_user_experience_full_browser_summary_guard.mjs",
)
# Regression anchor: changed by the U-C4 G16 data permission round while no
# syntax gate covered it.
REGRESSION_ANCHOR = "frontend/apps/web/scripts/formal_form_representative_journey.mjs"


def sweep_invocation_failures(body: str) -> list[str]:
    """Reasons ``body`` does not invoke the corpus-wide sweep once, verbatim."""
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    calls = [line for line in lines if SWEEP_CALL_RE.search(line)]
    if not calls:
        return [f"{SWEEP_RECIPE!r} is missing"]
    if calls != [SWEEP_RECIPE]:
        return [f"unexpected sweep invocation(s): {calls!r}"]
    return []


def _target_body(target: str) -> str:
    text = MAKE_CI.read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(target)}:.*?(?=\n\S|\n\Z)", text, flags=re.DOTALL | re.MULTILINE)
    if match is None:
        raise AssertionError(f"make target not found: {target}")
    return match.group(0)


class NodeSyntaxCheckTests(unittest.TestCase):
    def test_tracked_corpus_covers_frontend_automation(self) -> None:
        tracked = {path.relative_to(ROOT).as_posix() for path in node_syntax_check.tracked_node_files()}
        for path in (*HISTORIC_CONTRACT_FILES, REGRESSION_ANCHOR):
            self.assertIn(path, tracked)

    def test_tracked_corpus_expands_beyond_the_frontend_app(self) -> None:
        tracked = [path.relative_to(ROOT).as_posix() for path in node_syntax_check.tracked_node_files()]
        self.assertTrue(tracked)
        self.assertTrue(any(path.startswith("scripts/verify/") for path in tracked))
        self.assertFalse([path for path in tracked if path.startswith("tmp/")])

    def test_directory_scan_keeps_only_node_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested").mkdir()
            (root / "ok.mjs").write_text("export const ok = 1;\n", encoding="utf-8")
            (root / "handler.cjs").write_text("module.exports = 1;\n", encoding="utf-8")
            (root / "nested" / "inner.mjs").write_text("export const inner = 1;\n", encoding="utf-8")
            (root / "typed.ts").write_text("export const typed: number = 1;\n", encoding="utf-8")
            (root / "notes.md").write_text("syntax\n", encoding="utf-8")

            found = {path.name for path in node_syntax_check.iter_node_files([str(root)])}

        self.assertEqual(found, {"ok.mjs", "handler.cjs", "inner.mjs"})

    def test_missing_target_fails_closed(self) -> None:
        with self.assertRaises(FileNotFoundError):
            node_syntax_check.iter_node_files(["scripts/ci/does_not_exist.mjs"])

    def test_valid_module_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "valid.mjs"
            path.write_text("import { readFileSync } from 'node:fs';\nexport default readFileSync;\n", encoding="utf-8")
            self.assertIsNone(node_syntax_check.check_file(path))

    def test_syntax_error_is_reported_with_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.mjs"
            path.write_text("const value = ;\n", encoding="utf-8")
            detail = node_syntax_check.check_file(path)

        self.assertIsNotNone(detail)
        self.assertIn("1:", detail or "")
        self.assertIn("SyntaxError", detail or "")

    def test_esm_only_syntax_error_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken_esm.mjs"
            path.write_text('import { missing } from "./missing.mjs";\nexport default ;\n', encoding="utf-8")
            detail = node_syntax_check.check_file(path)

        self.assertIsNotNone(detail)
        self.assertIn("2:", detail or "")

    def test_runner_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.mjs").write_text("export const ok = 1;\n", encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as errors:
                self.assertEqual(node_syntax_check.main([str(root)]), 0)
            self.assertEqual(errors.getvalue(), "")

            (root / "broken.mjs").write_text("export default ;\n", encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as errors:
                self.assertEqual(node_syntax_check.main([str(root)]), 1)
            self.assertIn("broken.mjs", errors.getvalue())

            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(node_syntax_check.main(["scripts/ci/does_not_exist.mjs"]), 2)

    def test_contract_and_quick_gates_invoke_the_sweep(self) -> None:
        for target in ("test.contract", "ci.local.quick.run"):
            body = _target_body(target)
            self.assertEqual(
                sweep_invocation_failures(body),
                [],
                f"{target} must invoke the corpus-wide sweep verbatim",
            )
            self.assertNotIn("node --check frontend/apps/web/scripts/", body, f"{target} keeps a hand-maintained file list")

    def test_wiring_validator_rejects_a_narrowed_call(self) -> None:
        self.assertEqual(sweep_invocation_failures(f"test.contract: x\n{SWEEP_RECIPE}\n"), [])
        self.assertTrue(sweep_invocation_failures("test.contract: x\n\t@echo ok\n"))
        self.assertTrue(
            sweep_invocation_failures(
                f"test.contract: x\n{SWEEP_RECIPE} frontend/apps/web/scripts\n"
            )
        )
        self.assertTrue(
            sweep_invocation_failures(f"test.contract: x\n{SWEEP_RECIPE}\n{SWEEP_RECIPE}\n")
        )

    def test_self_reference_is_not_mistaken_for_the_sweep(self) -> None:
        self.assertIsNone(SWEEP_CALL_RE.search(SWEEP_SELF_TEST_RECIPE))

    def test_unit_gate_runs_this_self_test(self) -> None:
        body_lines = {line.rstrip() for line in _target_body("test.unit").splitlines()}
        self.assertIn(SWEEP_SELF_TEST_RECIPE, body_lines)

    def test_corpus_enumeration_fails_closed_without_git(self) -> None:
        with mock.patch.object(node_syntax_check.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(RuntimeError, "git is required"):
                node_syntax_check.tracked_node_files()
        failure = mock.Mock(returncode=128, stderr=b"fatal: not a git repository\n")
        with mock.patch.object(node_syntax_check.subprocess, "run", return_value=failure):
            with self.assertRaisesRegex(RuntimeError, "git ls-files failed"):
                node_syntax_check.tracked_node_files()
        with mock.patch.object(
            node_syntax_check, "tracked_node_files", side_effect=RuntimeError("git is required")
        ), redirect_stdout(StringIO()), redirect_stderr(StringIO()) as errors:
            self.assertEqual(node_syntax_check.main([]), 2)
        self.assertIn("git is required", errors.getvalue())


if __name__ == "__main__":
    unittest.main()

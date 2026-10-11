#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
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
# JavaScript anchors: the ``.js`` sweep only earns its keep if it reaches the
# Node verify scripts and the Odoo browser assets, which no other gate parses.
# ``JS_MODULE_ANCHORS`` hold ES-module syntax, the case ``node --check <file>.js``
# passes without parsing when it resolves the file to a module.
JS_MODULE_ANCHORS = (
    "scripts/verify/business_real_user_browser_closure.js",
    "addons/smart_construction_core/static/src/config/domain_nav_map.js",
)
JS_BROWSER_ASSET_ANCHOR = "addons/smart_construction_core/static/src/js/auth_favicon.js"


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

    def test_tracked_corpus_matches_an_independent_git_enumeration(self) -> None:
        """Corpus membership is asserted against git, not against sample paths.

        Narrowing ``tracked_node_files`` to a subset (for example dropping the
        scripts/dev|ops|release|ui entries) would keep every sample-point
        assertion above green while silently shrinking the gate, so the corpus
        is compared to an independent enumeration instead.
        """
        listed = subprocess.run(
            ["git", "ls-files", "-z", "--", *node_syntax_check.TRACKED_PATTERNS],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8").split("\0")
        expected = {Path(name) for name in listed if name}

        actual = {path.relative_to(ROOT) for path in node_syntax_check.tracked_node_files()}

        self.assertEqual(actual, expected)
        self.assertTrue(expected)
        for path in actual:
            self.assertIn(path.suffix, node_syntax_check.NODE_SUFFIXES)

    def test_corpus_patterns_are_pinned_by_literals(self) -> None:
        """Pin the patterns themselves, not just the function body.

        Sharing ``TRACKED_PATTERNS`` with the implementation would let a
        constant-level narrowing shrink both sides of
        ``test_tracked_corpus_matches_an_independent_git_enumeration`` while the
        gate silently drops whole directories.
        """
        self.assertEqual(tuple(node_syntax_check.TRACKED_PATTERNS), ("*.mjs", "*.cjs", "*.js"))
        self.assertEqual(tuple(node_syntax_check.NODE_SUFFIXES), (".mjs", ".cjs", ".js"))
        self.assertEqual(tuple(node_syntax_check.JS_INPUT_TYPES), ("commonjs", "module"))
        self.assertEqual(
            tuple((mode, source) for mode, source in node_syntax_check.NODE_FORMAT_PROBES),
            (("commonjs", b"module.exports = 1;\n"), ("module", b"export const ok = 1;\n")),
        )
        # Every format the sweep forces must be proven by the capability probe,
        # otherwise a format can be added (or a probe dropped) while the
        # documented single-message fail-closed contract silently degrades.
        self.assertEqual(
            tuple(mode for mode, _ in node_syntax_check.NODE_FORMAT_PROBES),
            tuple(node_syntax_check.JS_INPUT_TYPES),
        )

    def test_tracked_corpus_covers_the_javascript_anchors(self) -> None:
        tracked = {path.relative_to(ROOT).as_posix() for path in node_syntax_check.tracked_node_files()}
        for path in (*JS_MODULE_ANCHORS, JS_BROWSER_ASSET_ANCHOR):
            self.assertIn(path, tracked)

    def test_javascript_module_source_is_parsed(self) -> None:
        """A broken ``.js`` that only parses as a module must still be reported.

        ``node --check <file>.js`` exits 0 without parsing a file it resolves to
        an ES module, so this is the regression trap for a ``check_file`` that
        goes back to the single native invocation.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken_module.js"
            path.write_text('import { missing } from "./missing.js";\nexport default ;\n', encoding="utf-8")
            detail = node_syntax_check.check_file(path)

        self.assertIsNotNone(detail)
        self.assertIn("2:", detail or "")
        self.assertIn("as module", detail or "")

    def test_javascript_commonjs_source_is_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handler.js"
            path.write_text("module.exports = function run() {\n  return 1;\n};\n", encoding="utf-8")
            self.assertIsNone(node_syntax_check.check_file(path))

    def test_sloppy_javascript_commonjs_source_is_parsed(self) -> None:
        """A ``.js`` file is CommonJS unless its CommonJS parse fails.

        This source is valid CommonJS and invalid as a module, so a gate that
        demanded the module grammar would reject a file the runtime runs.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sloppy.js"
            path.write_text("function pick(first, first) {\n  return first;\n}\nmodule.exports = pick;\n", encoding="utf-8")
            self.assertIsNone(node_syntax_check.check_file(path))

    def test_javascript_syntax_error_is_reported_with_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.js"
            path.write_text("const value = ;\n", encoding="utf-8")
            detail = node_syntax_check.check_file(path)

        self.assertIsNotNone(detail)
        self.assertIn("1:", detail or "")
        self.assertIn("SyntaxError", detail or "")
        self.assertIn("as commonjs", detail or "")
        self.assertIn("as module", detail or "")

    def test_format_capability_is_proved_on_this_runtime(self) -> None:
        self.assertIsNone(node_syntax_check.format_capability_failure())

    def test_incapable_runtime_is_reported_with_the_required_version(self) -> None:
        incapable = mock.Mock(returncode=9, stdout=b"", stderr=b"node: bad option: --input-type\n")
        with mock.patch.object(node_syntax_check.subprocess, "run", return_value=incapable):
            reason = node_syntax_check.format_capability_failure()

        self.assertIn("--input-type", reason or "")
        self.assertIn("22.17.0", reason or "")

    def test_missing_node_runtime_is_reported_as_a_capability_failure(self) -> None:
        with mock.patch.object(node_syntax_check.subprocess, "run", side_effect=FileNotFoundError):
            reason = node_syntax_check.format_capability_failure()

        self.assertEqual(reason, "the node runtime is not on PATH")

    def test_capability_failure_stops_the_run_with_one_message(self) -> None:
        with mock.patch.object(
            node_syntax_check, "format_capability_failure", return_value="node 18 cannot parse module sources"
        ), redirect_stdout(StringIO()), redirect_stderr(StringIO()) as errors:
            code = node_syntax_check.main([JS_MODULE_ANCHORS[0]])

        self.assertEqual(code, 2)
        self.assertEqual(errors.getvalue().count("[FAIL]"), 1)
        self.assertIn("cannot parse module sources", errors.getvalue())

    def test_directory_scan_keeps_only_node_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested").mkdir()
            (root / "ok.mjs").write_text("export const ok = 1;\n", encoding="utf-8")
            (root / "handler.cjs").write_text("module.exports = 1;\n", encoding="utf-8")
            (root / "legacy.js").write_text("module.exports = 1;\n", encoding="utf-8")
            (root / "nested" / "inner.mjs").write_text("export const inner = 1;\n", encoding="utf-8")
            (root / "typed.ts").write_text("export const typed: number = 1;\n", encoding="utf-8")
            (root / "notes.md").write_text("syntax\n", encoding="utf-8")

            found = {path.name for path in node_syntax_check.iter_node_files([str(root)])}

        self.assertEqual(found, {"ok.mjs", "handler.cjs", "legacy.js", "inner.mjs"})

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

            (root / "broken.js").write_text("const value = ;\n", encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as errors:
                self.assertEqual(node_syntax_check.main([str(root)]), 1)
            self.assertIn("broken.js", errors.getvalue())

            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(node_syntax_check.main(["scripts/ci/does_not_exist.mjs"]), 2)

    # The corpus-wide sweep is declared exactly once, inside the shared contract
    # & architecture guard suite. Both the remote required backend gate and the
    # local exact-head lane must REACH that suite rather than each carrying a
    # private copy of the invocation: duplicated per-lane lists are how a gate
    # ends up enforced on only one side (2026-10-11 systemic audit).
    SHARED_SUITE = "verify.contract.architecture.suite"

    def test_shared_suite_invokes_the_sweep_verbatim(self) -> None:
        body = _target_body(self.SHARED_SUITE)
        self.assertEqual(
            sweep_invocation_failures(body),
            [],
            f"{self.SHARED_SUITE} must invoke the corpus-wide sweep verbatim",
        )
        self.assertNotIn(
            "node --check frontend/apps/web/scripts/",
            body,
            f"{self.SHARED_SUITE} keeps no hand-maintained file list",
        )

    def test_every_gate_reaches_the_corpus_wide_sweep(self) -> None:
        # test.contract owns a direct invocation; the quick and remote lanes must
        # both depend on the shared suite so neither can silently drop it.
        body = _target_body("test.contract")
        self.assertEqual(sweep_invocation_failures(body), [], "test.contract must invoke the corpus-wide sweep verbatim")
        self.assertNotIn("node --check frontend/apps/web/scripts/", body)

        for target in ("ci.local.quick.run", "ci.professional.backend.shard-verify"):
            body = _target_body(target)
            declaration = body.split("\n")[0]
            self.assertIn(
                self.SHARED_SUITE,
                declaration.split(),
                f"{target} must depend on {self.SHARED_SUITE}, not carry a private sweep copy",
            )

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

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name("daily_runtime_release_orchestration.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_release_orchestration", SCRIPT)
orchestration = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = orchestration
SPEC.loader.exec_module(orchestration)

HEAD = "a" * 40
OLD = "b" * 40
CANDIDATE = "c" * 40


def arguments(mode: str = "candidate") -> argparse.Namespace:
    return argparse.Namespace(
        mode=mode,
        expected_sha=HEAD,
        expected_old_sha=OLD,
        expected_candidate_sha=CANDIDATE if mode == "main" else "",
        source_branch="fix/release-orchestration",
        ssh_host="sc-root",
        declaration_digest="d" * 64,
        entry_digest="e" * 64,
        published_face_login="demo_full",
        report_root=".runtime/release-test",
    )


def identity(mode: str = "candidate") -> orchestration.Identity:
    return orchestration.Identity(
        mode=mode,
        branch="main" if mode == "main" else "fix/release-orchestration",
        head=HEAD,
        expected_sha=HEAD,
        expected_old_sha=OLD,
        expected_candidate_sha=CANDIDATE if mode == "main" else "",
    )


class DailyRuntimeReleaseOrchestrationTest(unittest.TestCase):
    def test_candidate_sequence_has_the_complete_required_order(self):
        steps = orchestration.plan_steps(ROOT, arguments(), identity())
        self.assertEqual(
            [step.key for step in steps],
            [
                "sync",
                "frontend-build",
                "duty-refresh",
                "align-demo",
                "align-platform",
                "published-face",
                "entry-verify",
            ],
        )
        self.assertEqual(steps[0].target, "daily.runtime.candidate.bundle_sync")
        self.assertEqual(steps[1].target, "daily.runtime.frontend.build")
        self.assertEqual(
            steps[1].variables["DAILY_RUNTIME_FRONTEND_BUILD_RECEIPT"],
            steps[1].variables["DAILY_RUNTIME_FRONTEND_BUILD_REPORT"],
        )
        self.assertTrue(
            steps[1].variables["DAILY_RUNTIME_FRONTEND_BUILD_REPORT"].endswith(
                "/frontend-build.json"
            )
        )
        self.assertEqual(steps[2].variables["DAILY_RUNTIME_DATABASE_DUTY_SELECTION"],
                         "demo platform_control")
        self.assertEqual(
            steps[2].variables["DAILY_RUNTIME_DATABASE_DUTY_DECLARATION_DIGEST"],
            "d" * 64,
        )
        self.assertEqual(
            steps[2].variables["DAILY_RUNTIME_ENTRY_DECLARATION_DIGEST"],
            "e" * 64,
        )
        self.assertEqual(
            steps[2].environment["SC_CONFIRM_DAILY_RUNTIME_DUTY_REFRESH"],
            "REFRESH_DAILY_RUNTIME_DUTY_STACK_AND_APPLICATION",
        )
        self.assertEqual(
            [step.variables["DAILY_RUNTIME_DUTY"] for step in steps[3:5]],
            ["demo", "platform_control"],
        )
        self.assertTrue(
            steps[3].variables["DAILY_RUNTIME_SOURCE_REVISION_BASE_URL"].endswith("/t/demo")
        )
        self.assertTrue(
            steps[4].variables["DAILY_RUNTIME_SOURCE_REVISION_BASE_URL"].endswith("/platform-admin")
        )

    def test_main_sequence_uses_the_main_bundle_entry(self):
        steps = orchestration.plan_steps(ROOT, arguments("main"), identity("main"))
        self.assertEqual(steps[0].target, "daily.runtime.main.bundle_sync")
        self.assertEqual(
            steps[0].variables["DAILY_RUNTIME_EXPECTED_CANDIDATE_SHA"],
            CANDIDATE,
        )

    def test_execute_stops_at_the_first_failed_step_and_records_receipt(self):
        steps = orchestration.plan_steps(ROOT, arguments(), identity())
        calls = []

        def runner(command, cwd, environment):
            calls.append((list(command), environment))
            if len(calls) == 2:
                return 7, "", "frontend build failed"
            return 0, "ok", ""

        report = ROOT / ".runtime" / "test-release-orchestration.json"
        payload = orchestration.execute(
            ROOT,
            steps,
            runner=runner,
            report=report,
        )
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual([row["key"] for row in payload["steps"]],
                         ["sync", "frontend-build"])
        self.assertEqual(len(calls), 2)
        self.assertTrue(report.is_file())
        self.assertIn(
            "BUILD_AND_DECLARE_DAILY_RUNTIME_FRONTEND_AT_DEPLOYED_HEAD",
            calls[1][1]["CONFIRM_DAILY_RUNTIME_FRONTEND_BUILD"],
        )

    def test_execute_releases_frozen_recursive_make_arguments(self):
        steps = orchestration.plan_steps(ROOT, arguments(), identity())
        frozen = {
            variable: "stale-parent-value"
            for variable in orchestration.FROZEN_RECURSIVE_MAKE_VARIABLES
        }
        observed = {}

        def runner(command, cwd, environment):
            observed.update(environment)
            return 0, "ok", ""

        with mock.patch.dict(os.environ, frozen):
            orchestration.execute(
                ROOT,
                [steps[2]],
                runner=runner,
                report=ROOT / ".runtime" / "test-release-environment.json",
            )

        for variable in orchestration.FROZEN_RECURSIVE_MAKE_VARIABLES:
            self.assertNotIn(variable, observed)
        self.assertEqual(
            observed["SC_CONFIRM_DAILY_RUNTIME_DUTY_REFRESH"],
            "REFRESH_DAILY_RUNTIME_DUTY_STACK_AND_APPLICATION",
        )

    def test_every_step_is_a_defined_make_target(self):
        makefile = (ROOT / "make" / "codex.mk").read_text(encoding="utf-8")
        for step in orchestration.plan_steps(ROOT, arguments(), identity()):
            self.assertIn(f"{step.target}:", makefile, step.target)

    def test_release_entries_use_the_single_orchestrator(self):
        makefile = (ROOT / "make" / "codex.mk").read_text(encoding="utf-8")
        self.assertIn("daily.runtime.main.release:", makefile)
        self.assertIn("daily.runtime.candidate.release:", makefile)
        self.assertIn("daily_runtime_release_orchestration.py --mode main", makefile)
        self.assertIn("daily_runtime_release_orchestration.py --mode candidate", makefile)
        ci_makefile = (ROOT / "make" / "ci.mk").read_text(encoding="utf-8")
        self.assertIn(
            "verify.daily.runtime.release_orchestration.unit",
            ci_makefile,
        )

    def test_execution_requires_the_single_release_confirmation(self):
        argv = [
            "--mode", "candidate",
            "--expected-sha", HEAD,
            "--expected-old-sha", OLD,
            "--source-branch", "fix/release-orchestration",
            "--declaration-digest", "d" * 64,
            "--entry-digest", "e" * 64,
        ]
        with mock.patch.object(
            orchestration, "validate_identity", return_value=identity()
        ), mock.patch.object(
            orchestration, "derive_digests", return_value=("d" * 64, "e" * 64)
        ) as derive_digests, mock.patch.object(
            orchestration, "execute", return_value={"status": "PASS"}
        ) as execute, mock.patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(orchestration.main(argv), 2)
            execute.assert_not_called()

    def test_derive_digests_reads_the_governed_plan_and_refuses_manual_mismatch(self):
        plan_report = ROOT / ".runtime" / "test-duty-plan.json"
        plan_report.parent.mkdir(parents=True, exist_ok=True)
        plan_report.write_text(
            '{"declaration_digest":"' + "a" * 64 + '","entry_digest":"' + "b" * 64 + '"}'
        )
        run = mock.Mock(return_value=type(
            "Result", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )())
        with mock.patch.object(orchestration, "DUTY_PLAN_REPORT", ".runtime/test-duty-plan.json"):
            with mock.patch.object(orchestration.subprocess, "run", run):
                declaration_digest, entry_digest = orchestration.derive_digests(
                    ROOT, arguments(), identity()
                )
        self.assertEqual("a" * 64, declaration_digest)
        self.assertEqual("b" * 64, entry_digest)
        command = run.call_args[0][0]
        self.assertIn("daily.runtime.database.duty.plan", command)
        self.assertIn("DAILY_RUNTIME_EXPECTED_SHA=" + OLD, command)
        self.assertNotIn("DAILY_RUNTIME_EXPECTED_SHA=" + HEAD, command)
        plan_report.unlink()

    def test_derive_digests_fails_closed_when_plan_fails(self):
        with mock.patch.object(orchestration.subprocess, "run", return_value=type(
            "Result", (), {"returncode": 2, "stdout": "", "stderr": "plan refused"}
        )()):
            with self.assertRaises(orchestration.ReleaseError):
                orchestration.derive_digests(ROOT, arguments(), identity())

    def test_resume_steps_skips_prefix_and_refuses_unknown_key(self):
        steps = orchestration.plan_steps(ROOT, arguments(), identity())
        resumed = orchestration.resume_steps(steps, "duty-refresh")
        self.assertEqual(
            ["duty-refresh", "align-demo", "align-platform", "published-face", "entry-verify"],
            [step.key for step in resumed],
        )
        with self.assertRaises(orchestration.ReleaseError):
            orchestration.resume_steps(steps, "not-a-step")


if __name__ == "__main__":
    unittest.main()

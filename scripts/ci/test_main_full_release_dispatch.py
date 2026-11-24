#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main_full_release_dispatch as dispatch


MAIN = "a" * 40
TREE = "b" * 40


def run_row(run_id: int, workflow: str, *, status: str = "queued",
            conclusion: str = "", head: str = MAIN) -> dict:
    return {
        "databaseId": run_id,
        "headSha": head,
        "headBranch": "main",
        "event": "workflow_dispatch",
        "status": status,
        "conclusion": conclusion,
        "url": f"https://github.com/lidefend/sce-backend-odoo/actions/runs/{run_id}",
        "workflowName": workflow.removesuffix(".yml"),
        "attempt": 1,
    }


class DispatchTest(unittest.TestCase):
    def test_make_entry_and_scheduled_owner_are_wired(self) -> None:
        makefile = (dispatch.ROOT / "make/ci.mk").read_text(encoding="utf-8")
        for required in (
            "release.main_full: guard.prod.forbid",
            "release.main_full.dispatch: guard.prod.forbid",
            "release.main_full.verify: guard.prod.forbid",
            "scripts/ci/main_full_release_dispatch.py dispatch",
            "scripts/ci/main_full_release_dispatch.py verify",
            "--expected-main \"$(MAIN_FULL_RELEASE_EXPECTED_MAIN)\"",
            "--wait-seconds \"$(MAIN_FULL_RELEASE_WAIT_SECONDS)\"",
        ):
            self.assertIn(required, makefile)
        gate = makefile.split("verify.ci.scheduled_gates:", 1)[1].splitlines()[0]
        self.assertIn("verify.ci.main_full_release.unit", gate)
        allowlist = (
            dispatch.ROOT / "docs/ops/codex_execution_allowlist.md"
        ).read_text(encoding="utf-8")
        self.assertIn("make release.main_full EXPECTED_MAIN=<full-40-char-sha>", allowlist)
        self.assertIn("operator_full_audit", allowlist)
        self.assertIn("不得冒充 `scheduled_mainline`", allowlist)

    def test_dispatch_uses_new_exact_main_runs_only(self) -> None:
        calls = []
        dispatched = set()
        next_ids = {
            workflow: 200 + index * 10
            for index, workflow in enumerate(dispatch.WORKFLOWS)
        }

        def list_runs(workflow: str, expected_main: str) -> list[dict]:
            self.assertEqual(MAIN, expected_main)
            rows = [run_row(100, workflow)]
            if workflow in dispatched:
                rows.append(run_row(next_ids[workflow], workflow))
            return rows

        def command(args: list[str], *, cwd: Path = dispatch.ROOT) -> str:
            calls.append(args)
            if args[:3] == ["gh", "workflow", "run"]:
                workflow = args[3]
                next_ids[workflow] -= 1
                dispatched.add(workflow)
                return ""
            self.fail(f"unexpected command: {args}")

        with tempfile.TemporaryDirectory() as tmp, patch.object(
            dispatch, "assert_repository"
        ), patch.object(dispatch, "assert_clean_worktree"), patch.object(
            dispatch, "assert_remote_main"
        ), patch.object(dispatch, "expected_tree", return_value=TREE), patch.object(
            dispatch, "list_runs", side_effect=list_runs
        ), patch.object(dispatch, "run_command", side_effect=command):
            manifest = Path(tmp) / "manifest.json"
            document = dispatch.dispatch_full(
                expected_main=MAIN,
                repository=dispatch.REPOSITORY,
                manifest=manifest,
                discovery_seconds=1,
                poll_seconds=0.01,
            )
        self.assertEqual(
            [workflow for workflow in dispatch.WORKFLOWS],
            [row["workflow"] for row in document["workflows"]],
        )
        self.assertEqual(
            [row["run_id"] for row in document["workflows"]],
            [199 + index * 10 for index in range(len(dispatch.WORKFLOWS))],
        )
        self.assertEqual(
            [args[3] for args in calls],
            list(dispatch.WORKFLOWS),
        )
        self.assertEqual("operator_full_audit", document["release_condition_kind"])

    def test_new_run_discovery_rejects_old_wrong_and_ambiguous_runs(self) -> None:
        before = {workflow: {1} for workflow in dispatch.WORKFLOWS}
        for rows in (
            [run_row(1, dispatch.WORKFLOWS[0]), run_row(2, dispatch.WORKFLOWS[0], head="c" * 40)],
            [run_row(1, dispatch.WORKFLOWS[0]), run_row(2, dispatch.WORKFLOWS[0]),
             run_row(3, dispatch.WORKFLOWS[0])],
        ):
            with self.subTest(rows=rows), patch.object(
                dispatch, "list_runs", side_effect=[
                    rows if workflow == dispatch.WORKFLOWS[0] else []
                    for workflow in sorted(dispatch.WORKFLOWS)
                ],
            ), self.assertRaises(ValueError):
                dispatch.find_new_runs(
                    before,
                    MAIN,
                    timeout_seconds=1,
                    poll_seconds=0.01,
                    sleep=lambda _seconds: None,
                    monotonic=lambda: 0,
                )


class VerifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "workflow": workflow,
                "run_id": 300 + index,
                "attempt": 1,
                "workflow_name": workflow.removesuffix(".yml"),
                "head_sha": MAIN,
                "head_branch": "main",
                "event": "workflow_dispatch",
                "status": "queued",
                "conclusion": "",
                "url": f"https://github.com/lidefend/sce-backend-odoo/actions/runs/{300 + index}",
            }
            for index, workflow in enumerate(dispatch.WORKFLOWS)
        ]
        self.document = {
            "schema_version": dispatch.SCHEMA,
            "repository": dispatch.REPOSITORY,
            "expected_main": MAIN,
            "expected_tree": TREE,
            "event": "workflow_dispatch",
            "head_branch": "main",
            "release_condition_kind": "operator_full_audit",
            "dispatched_at": "2026-11-24T00:00:00+00:00",
            "workflows": self.rows,
        }

    def test_verify_waits_and_requires_every_workflow_success(self) -> None:
        views = {
            row["run_id"]: run_row(row["run_id"], row["workflow"])
            for row in self.rows
        }
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            dispatch, "assert_repository"
        ), patch.object(dispatch, "assert_remote_main"), patch.object(
            dispatch, "run_view", side_effect=lambda run_id: views[run_id]
        ):
            path = Path(tmp) / "manifest.json"
            dispatch.write_manifest(path, copy.deepcopy(self.document))
            for row in self.rows:
                views[row["run_id"]].update(status="completed", conclusion="success")
            result = dispatch.verify_full(
                expected_main=MAIN,
                repository=dispatch.REPOSITORY,
                manifest=path,
                wait_seconds=1,
                poll_seconds=0.01,
                sleep=lambda _seconds: None,
                monotonic=lambda: 0,
            )
            self.assertEqual("PASS", result["status"])
            self.assertEqual("PASS", dispatch.load_manifest(path, MAIN)["status"])

        failed = copy.deepcopy(views)
        failed[self.rows[0]["run_id"]].update(status="completed", conclusion="failure")
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            dispatch, "assert_repository"
        ), patch.object(dispatch, "assert_remote_main"), patch.object(
            dispatch, "run_view", side_effect=lambda run_id: failed[run_id]
        ):
            path = Path(tmp) / "manifest.json"
            dispatch.write_manifest(path, copy.deepcopy(self.document))
            with self.assertRaisesRegex(ValueError, "did not succeed"):
                dispatch.verify_full(
                    expected_main=MAIN,
                    repository=dispatch.REPOSITORY,
                    manifest=path,
                    wait_seconds=1,
                    poll_seconds=0.01,
                    sleep=lambda _seconds: None,
                    monotonic=lambda: 0,
                )

    def test_manifest_rejects_wrong_main_or_missing_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            for mutation in ("main", "workflow"):
                document = copy.deepcopy(self.document)
                if mutation == "main":
                    document["expected_main"] = "c" * 40
                else:
                    document["workflows"].pop()
                path.write_text(json.dumps(document), encoding="utf-8")
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    dispatch.load_manifest(path, MAIN)


if __name__ == "__main__":
    unittest.main()

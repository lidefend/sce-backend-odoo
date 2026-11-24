#!/usr/bin/env python3
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.ci.release_condition import REQUIRED_WORKFLOWS, build_condition


HEAD = "a" * 40
TREE = "b" * 40
REPOSITORY = "lidefend/sce-backend-odoo"
SLOT = "2026-11-17T18:00:00+00:00"


def run(path: str, index: int, *, event: str = "schedule",
        head_branch: str | None = None) -> dict:
    return {
        "id": 1000 + index,
        "run_attempt": 1,
        "path": path,
        "event": event,
        "head_branch": head_branch or ("feature/candidate" if event == "pull_request" else "main"),
        "status": "completed",
        "conclusion": "success",
        "head_sha": HEAD,
        "created_at": "2026-11-18T01:00:00Z",
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
    }


class ReleaseConditionTests(unittest.TestCase):
    def runs(self, event: str = "schedule") -> list[dict]:
        return [run(path, index, event=event) for index, path in enumerate(sorted(REQUIRED_WORKFLOWS))]

    def build(self, runs: list[dict], event: str = "schedule",
              head_branch: str | None = None,
              current_main: str | None = HEAD) -> dict:
        return build_condition(
            runs,
            repository=REPOSITORY,
            head_sha=HEAD,
            tree=TREE,
            event=event,
            head_branch=head_branch or ("feature/candidate" if event == "pull_request" else "main"),
            workflow_dispatch_producer="workflow_dispatch",
            schedule_slot=SLOT if event == "schedule" else None,
            current_main=current_main,
        )

    def test_scheduled_condition_binds_exact_identity_and_all_workflows(self) -> None:
        result = self.build(self.runs())
        self.assertEqual(result["status"], "SATISFIED")
        self.assertEqual(result["kind"], "scheduled_mainline")
        self.assertEqual(result["exact_head"], HEAD)
        self.assertEqual(result["exact_tree"], TREE)
        self.assertEqual(result["current_main"], HEAD)
        self.assertTrue(result["current_main_verified"])
        self.assertTrue(result["candidate_build_eligible"])
        self.assertFalse(result["deployment_ready"])
        self.assertEqual(
            {row["workflow"] for row in result["required_workflows"]},
            REQUIRED_WORKFLOWS,
        )

    def test_explicit_candidate_keeps_the_same_exact_identity(self) -> None:
        result = self.build(
            self.runs("pull_request"),
            event="pull_request",
            current_main=None,
        )
        self.assertEqual(result["kind"], "explicit_candidate")
        self.assertEqual(result["producer_event"], "pull_request")
        self.assertEqual(result["head_branch"], "feature/candidate")
        self.assertIsNone(result["scheduled_slot_utc"])

    def test_operator_dispatch_requires_same_event_full_audit_evidence(self) -> None:
        result = self.build(self.runs("workflow_dispatch"), event="workflow_dispatch")
        self.assertEqual(result["kind"], "operator_full_audit")
        self.assertEqual(result["event"], "workflow_dispatch")
        self.assertEqual(result["producer_event"], "workflow_dispatch")
        self.assertEqual(result["head_branch"], "main")
        self.assertEqual(
            {row["event"] for row in result["required_workflows"]},
            {"workflow_dispatch"},
        )

    def test_operator_dispatch_rejects_push_only_evidence(self) -> None:
        with self.assertRaises(ValueError):
            self.build(self.runs("push"), event="workflow_dispatch")

    def test_mainline_conditions_require_the_current_authoritative_main(self) -> None:
        for event in ("schedule", "workflow_dispatch"):
            with self.subTest(event=event):
                runs = self.runs(event)
                with self.assertRaisesRegex(ValueError, "current remote main"):
                    self.build(runs, event=event, current_main=None)
                with self.assertRaisesRegex(ValueError, "stale main"):
                    self.build(runs, event=event, current_main="c" * 40)

    def test_pull_request_condition_does_not_claim_mainline_freshness(self) -> None:
        result = self.build(
            self.runs("pull_request"),
            event="pull_request",
            current_main=None,
        )
        self.assertIsNone(result["current_main"])
        self.assertFalse(result["current_main_verified"])

    def test_missing_duplicate_wrong_identity_and_unsuccessful_runs_fail_closed(self) -> None:
        cases = []
        missing = self.runs()[:-1]
        cases.append(missing)
        duplicate = self.runs() + [copy.deepcopy(self.runs()[0])]
        cases.append(duplicate)
        wrong_head = self.runs()
        wrong_head[0]["head_sha"] = "c" * 40
        cases.append(wrong_head)
        wrong_event = self.runs()
        wrong_event[0]["event"] = "push"
        cases.append(wrong_event)
        wrong_branch = self.runs()
        wrong_branch[0]["head_branch"] = "feature/other"
        cases.append(wrong_branch)
        wrong_repository = self.runs()
        wrong_repository[0]["head_repository"] = {"full_name": "other/repo"}
        cases.append(wrong_repository)
        failed = self.runs()
        failed[0]["conclusion"] = "failure"
        cases.append(failed)
        wrong_slot = self.runs()
        wrong_slot[0]["created_at"] = "2026-11-18T19:00:00Z"
        cases.append(wrong_slot)
        for runs in cases:
            with self.subTest(runs=runs), self.assertRaises(ValueError):
                self.build(runs)

    def test_invalid_identity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "head"):
            build_condition(
                self.runs(),
                repository=REPOSITORY,
                head_sha="main",
                tree=TREE,
                event="schedule",
                head_branch="main",
                workflow_dispatch_producer="workflow_dispatch",
                schedule_slot=SLOT,
                current_main=HEAD,
            )


if __name__ == "__main__":
    unittest.main()

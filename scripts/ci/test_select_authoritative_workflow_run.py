#!/usr/bin/env python3
from __future__ import annotations

import unittest

try:
    from scripts.ci.select_authoritative_workflow_run import select_latest_run
except ModuleNotFoundError:  # direct `python scripts/ci/...` execution
    from select_authoritative_workflow_run import select_latest_run


REPOSITORY = "lidefend/sce-backend-odoo"
WORKFLOW = ".github/workflows/public_guard.yml"
HEAD = "a" * 40


def run(run_id: int, *, status: str, conclusion: str | None, **overrides):
    row = {
        "id": run_id,
        "repository": {"full_name": REPOSITORY},
        "path": WORKFLOW,
        "head_sha": HEAD,
        "event": "pull_request",
        "status": status,
        "conclusion": conclusion,
    }
    row.update(overrides)
    return row


class AuthoritativeWorkflowRunTests(unittest.TestCase):
    def select(self, *rows):
        return select_latest_run(
            {"workflow_runs": list(rows)},
            repository=REPOSITORY,
            workflow_path=WORKFLOW,
            head_sha=HEAD,
            event="pull_request",
        )

    def test_same_producer_old_cancelled_then_new_success_selects_success(self):
        selected = self.select(
            run(10, status="completed", conclusion="cancelled"),
            run(11, status="completed", conclusion="success"),
        )
        self.assertEqual(selected["id"], 11)
        self.assertEqual(selected["conclusion"], "success")

    def test_foreign_later_success_cannot_override_formal_failure(self):
        selected = self.select(
            run(10, status="completed", conclusion="failure"),
            run(
                99,
                status="completed",
                conclusion="success",
                path=".github/workflows/spoof.yml",
            ),
            run(
                100,
                status="completed",
                conclusion="success",
                repository={"full_name": "attacker/fork"},
            ),
        )
        self.assertEqual(selected["id"], 10)
        self.assertEqual(selected["conclusion"], "failure")

    def test_latest_formal_failure_remains_failure(self):
        selected = self.select(
            run(10, status="completed", conclusion="success"),
            run(11, status="completed", conclusion="failure"),
        )
        self.assertEqual(selected["conclusion"], "failure")

    def test_latest_formal_pending_remains_pending(self):
        selected = self.select(
            run(10, status="completed", conclusion="success"),
            run(11, status="in_progress", conclusion=None),
        )
        self.assertEqual(selected["status"], "in_progress")
        self.assertIsNone(selected["conclusion"])


if __name__ == "__main__":
    unittest.main()

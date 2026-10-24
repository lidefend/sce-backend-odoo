#!/usr/bin/env python3
from __future__ import annotations

import unittest

try:
    from scripts.ci.select_authoritative_workflow_run import select_latest_run, select_successful_history
except ModuleNotFoundError:  # direct `python scripts/ci/...` execution
    from select_authoritative_workflow_run import select_latest_run, select_successful_history


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


class SuccessfulHistoryTests(unittest.TestCase):
    def row(self, number, **overrides):
        return run(number, status='completed', conclusion='success',
                   head_repository={'full_name':REPOSITORY}, run_attempt=1, **overrides)

    def select(self, rows, event='schedule', head=None):
        return select_successful_history({'workflow_runs':rows},repository=REPOSITORY,
            workflow_path=WORKFLOW,event=event,head_sha=head)

    def test_schedule_history_spans_multiple_candidate_heads(self):
        rows=[self.row(1,event='schedule'),self.row(2,event='schedule',head_sha='b'*40)]
        self.assertEqual([2,1],[r['id'] for r in self.select(rows)])
        self.assertEqual([1],[r['id'] for r in self.select(rows,head=HEAD)])

    def test_pr_and_branch_history_do_not_require_main(self):
        for event in ('pull_request','push','workflow_dispatch'):
            self.assertEqual(1,len(self.select([self.row(1,event=event)],event=event)))

    def test_failures_incomplete_foreign_and_wrong_producers_excluded(self):
        good=self.row(1,event='schedule')
        for change in ({'conclusion':'failure'},{'status':'in_progress'},
                       {'head_repository':{'full_name':'other/repo'}},{'path':'other.yml'},
                       {'event':'pull_request'},{'id':True},{'run_attempt':None},{'head_sha':'main'}):
            with self.subTest(change=change):
                self.assertEqual([],self.select([{**good,**change}]))

    def test_same_candidate_attempts_are_not_collapsed(self):
        a=self.row(1,event='schedule');b={**a,'run_attempt':2}
        self.assertEqual([2,1],[r['run_attempt'] for r in self.select([a,b,a])])

    def test_conflicting_identity_is_rejected(self):
        a=self.row(1,event='schedule')
        with self.assertRaises(ValueError):self.select([a,{**a,'head_sha':'b'*40}])

    def test_invalid_filter_refused(self):
        with self.assertRaises(ValueError):self.select([],event='pull_request_target')
        with self.assertRaises(ValueError):self.select([],head='main')


if __name__ == "__main__":
    unittest.main()

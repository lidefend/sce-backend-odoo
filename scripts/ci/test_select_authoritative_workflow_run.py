#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

try:
    from scripts.ci.select_authoritative_workflow_run import (
        resolve_producer_identity,
        select_latest_run,
        select_successful_history,
    )
except ModuleNotFoundError:  # direct `python scripts/ci/...` execution
    from select_authoritative_workflow_run import (
        resolve_producer_identity,
        select_latest_run,
        select_successful_history,
    )


REPOSITORY = "lidefend/sce-backend-odoo"
WORKFLOW = ".github/workflows/public_guard.yml"
HEAD = "a" * 40
SCRIPT = Path(__file__).with_name("select_authoritative_workflow_run.py")


def run(run_id: int, *, status: str, conclusion: str | None, **overrides):
    row = {
        "id": run_id,
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
        "path": WORKFLOW,
        "head_sha": HEAD,
        "event": "pull_request",
        "head_branch": "feature/candidate",
        "status": status,
        "conclusion": conclusion,
    }
    row.update(overrides)
    return row


class AuthoritativeWorkflowRunTests(unittest.TestCase):
    def test_aggregate_events_resolve_only_authorized_producer_identity(self):
        self.assertEqual(("schedule", "main"), resolve_producer_identity("schedule", "main"))
        self.assertEqual(("push", "main"), resolve_producer_identity("push", "main"))
        self.assertEqual(("pull_request", "feature/candidate"),
                         resolve_producer_identity("pull_request", "feature/candidate"))
        self.assertEqual(("push", "main"), resolve_producer_identity("workflow_dispatch", "main"))
        for aggregate, branch in (("push", "feature/candidate"),
                                  ("workflow_dispatch", "feature/candidate"),
                                  ("pull_request", None),
                                  ("workflow_run", "main")):
            with self.subTest(aggregate=aggregate, branch=branch), self.assertRaises(ValueError):
                resolve_producer_identity(aggregate, branch)

    def test_scheduled_gate_never_accepts_previous_day_same_head(self):
        try:
            from scripts.ci.scheduled_validation import scheduled_slot, observation
        except ModuleNotFoundError:
            from scheduled_validation import scheduled_slot, observation
        old = run(10, status='completed', conclusion='success', event='schedule',
                  created_at='2026-11-03T23:30:00Z')
        current = run(11, status='in_progress', conclusion=None, event='schedule',
                      created_at='2026-11-05T01:08:23Z')
        options = dict(repository=REPOSITORY, workflow_path=WORKFLOW, head_sha=HEAD,
                       event='schedule', schedule_slot=scheduled_slot('2026-11-04T23:51:01Z'))
        self.assertIsNone(select_latest_run({'workflow_runs': [old]}, **options))
        self.assertEqual(11, select_latest_run({'workflow_runs': [old, current]}, **options)['id'])
        current.update(run_attempt=2, run_started_at='2026-11-05T02:49:40Z')
        report = observation(current)
        self.assertEqual('2026-11-05T02:00:00+08:00', report['nominal_slot_shanghai'])
        self.assertEqual(428.4, report['trigger_delay_minutes'])
        self.assertEqual(2, report['attempt'])
        self.assertEqual(scheduled_slot('2026-11-04T18:00:00Z'), options['schedule_slot'])
        with self.assertRaises(ValueError): scheduled_slot('2026-11-04T18:30:00')

    def select(self, *rows):
        return select_latest_run(
            {"workflow_runs": list(rows)},
            repository=REPOSITORY,
            workflow_path=WORKFLOW,
            head_sha=HEAD,
            event="pull_request",
        )

    def test_workflow_dispatch_reuses_exact_mainline_push_evidence(self):
        selected = select_latest_run(
            {"workflow_runs": [
                run(1, status="completed", conclusion="success",
                    event="workflow_dispatch", head_branch="main"),
                run(2, status="completed", conclusion="success",
                    event="push", head_branch="main"),
            ]},
            repository=REPOSITORY,
            workflow_path=WORKFLOW,
            head_sha=HEAD,
            event="push",
            head_branch="main",
            head_repository=REPOSITORY,
        )
        self.assertEqual(2, selected["id"])
        self.assertEqual("push", selected["event"])
        self.assertEqual("main", selected["head_branch"])

    def test_cli_aggregate_dispatch_selects_exact_mainline_push(self):
        payload = {"workflow_runs": [
            run(1, status="completed", conclusion="success",
                event="workflow_dispatch", head_branch="main"),
            run(2, status="completed", conclusion="success",
                event="push", head_branch="main"),
        ]}
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repository", REPOSITORY,
                "--workflow-path", WORKFLOW,
                "--head", HEAD,
                "--aggregate-event", "workflow_dispatch",
                "--head-branch", "main",
                "--head-repository", REPOSITORY,
            ],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        selected = json.loads(proc.stdout)
        self.assertEqual(2, selected["id"])
        self.assertEqual("push", selected["event"])

    def test_cross_branch_and_cross_repository_runs_are_rejected(self):
        rows = [
            run(1, status="completed", conclusion="success",
                event="pull_request", head_branch="feature/other"),
            run(2, status="completed", conclusion="success",
                event="pull_request", head_repository={"full_name": "other/repo"}),
        ]
        self.assertIsNone(select_latest_run(
            {"workflow_runs": rows},
            repository=REPOSITORY,
            workflow_path=WORKFLOW,
            head_sha=HEAD,
            event="pull_request",
            head_branch="feature/candidate",
            head_repository=REPOSITORY,
        ))

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

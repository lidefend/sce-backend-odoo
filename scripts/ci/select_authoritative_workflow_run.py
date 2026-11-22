#!/usr/bin/env python3
"""Select the latest run from one exact, repository-owned workflow producer."""
from __future__ import annotations

import argparse
import json
import re
import sys
import os
try:
    from scripts.ci.scheduled_validation import scheduled_slot
except ModuleNotFoundError:
    from scheduled_validation import scheduled_slot
from typing import Any


PRODUCER_EVENT_BY_AGGREGATE = {
    "schedule": "schedule",
    "push": "push",
    "pull_request": "pull_request",
}
WORKFLOW_DISPATCH_PRODUCERS = {"push", "workflow_dispatch"}


def resolve_producer_identity(
    aggregate_event: str,
    head_branch: str | None,
    *,
    workflow_dispatch_producer: str = "push",
) -> tuple[str, str]:
    """Resolve the only producer event/branch approved for an aggregate run."""
    if aggregate_event == "workflow_dispatch":
        if workflow_dispatch_producer not in WORKFLOW_DISPATCH_PRODUCERS:
            raise ValueError(
                f"unsupported workflow_dispatch producer: {workflow_dispatch_producer}"
            )
        producer_event = workflow_dispatch_producer
    else:
        try:
            producer_event = PRODUCER_EVENT_BY_AGGREGATE[aggregate_event]
        except KeyError as exc:
            raise ValueError(f"unsupported aggregate event: {aggregate_event}") from exc
    if not head_branch:
        raise ValueError("aggregate selection requires the source branch")
    if aggregate_event in {"schedule", "push", "workflow_dispatch"} and head_branch != "main":
        raise ValueError(f"{aggregate_event} dependency must come from main")
    return producer_event, head_branch


def select_latest_run(
    payload: dict[str, Any],
    *,
    repository: str,
    workflow_path: str,
    head_sha: str,
    event: str,
    schedule_slot: str | None = None,
    head_branch: str | None = None,
    head_repository: str | None = None,
) -> dict[str, Any] | None:
    matches = []
    for run in payload.get("workflow_runs") or []:
        if not isinstance(run, dict):
            continue
        run_repository = run.get("repository") or {}
        if str(run_repository.get("full_name") or "") != repository:
            continue
        if str(run.get("path") or "") != workflow_path:
            continue
        if str(run.get("head_sha") or "") != head_sha:
            continue
        if str(run.get("event") or "") != event:
            continue
        if head_branch is not None and str(run.get("head_branch") or "") != head_branch:
            continue
        if head_repository is not None:
            run_head_repository = run.get("head_repository") or {}
            if str(run_head_repository.get("full_name") or "") != head_repository:
                continue
        if schedule_slot:
            try:
                if scheduled_slot(run.get('created_at', '')) != schedule_slot:
                    continue
            except (ValueError, TypeError):
                continue
        run_id = run.get("id")
        if not isinstance(run_id, int) or run_id <= 0:
            continue
        matches.append(run)
    return max(matches, key=lambda row: row["id"], default=None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow-path", required=True)
    parser.add_argument("--head")
    event_source = parser.add_mutually_exclusive_group(required=True)
    event_source.add_argument("--event", help="Exact producer event to select")
    event_source.add_argument(
        "--aggregate-event",
        help="Aggregate event whose approved producer identity should be selected",
    )
    parser.add_argument("--head-branch")
    parser.add_argument("--head-repository")
    parser.add_argument(
        "--workflow-dispatch-producer",
        choices=sorted(WORKFLOW_DISPATCH_PRODUCERS),
        default="push",
        help="Producer event authorized for workflow_dispatch aggregate runs",
    )
    parser.add_argument("--history", action="store_true", help="Return successful producer history across candidates; not reuse authorization")
    args = parser.parse_args()
    payload = json.load(sys.stdin)
    if args.history:
        if args.aggregate_event:
            parser.error('--history requires an exact --event')
        json.dump(select_successful_history(payload, repository=args.repository,
            workflow_path=args.workflow_path, event=args.event, head_sha=args.head), sys.stdout,
            separators=(",", ":"), sort_keys=True)
        return 0
    if not args.head:
        parser.error('--head is required unless --history is selected')
    if args.aggregate_event:
        if not args.head_repository:
            parser.error('--head-repository is required with --aggregate-event')
        if args.head_repository != args.repository:
            parser.error('--head-repository must match --repository')
        try:
            event, head_branch = resolve_producer_identity(
                args.aggregate_event,
                args.head_branch,
                workflow_dispatch_producer=args.workflow_dispatch_producer,
            )
        except ValueError as exc:
            parser.error(str(exc))
    else:
        event, head_branch = args.event, args.head_branch
    slot = os.environ.get('SCHEDULED_SLOT') if event == 'schedule' else None
    if event == 'schedule' and not slot:
        parser.error('scheduled selection requires the observed SCHEDULED_SLOT')
    selected = select_latest_run(
        payload,
        repository=args.repository,
        workflow_path=args.workflow_path,
        head_sha=args.head,
        event=event,
        schedule_slot=slot,
        head_branch=head_branch,
        head_repository=args.head_repository,
    )
    if selected is not None:
        json.dump(selected, sys.stdout, separators=(",", ":"), sort_keys=True)
    return 0


def select_successful_history(payload: dict[str, Any], *, repository: str,
                              workflow_path: str, event: str,
                              head_sha: str | None = None) -> list[dict[str, Any]]:
    """Discover eligible producers, not reusable target results.

    Schedules, PRs, branch pushes and explicit runs are queried separately by
    event. No main/head assumption; target/attempt artifacts need their own
    authentication after discovery. The existing latest-run gate is unchanged.
    """
    if head_sha is not None and not re.fullmatch('[0-9a-f]{40}', head_sha):
        raise ValueError('history head must be an exact commit')
    if event not in {'schedule', 'pull_request', 'push', 'workflow_dispatch'}:
        raise ValueError('unsupported history event')
    matches = {}
    for run in payload.get('workflow_runs') or []:
        if not isinstance(run, dict):
            continue
        source, head_repository = run.get('repository'), run.get('head_repository')
        if not isinstance(source, dict) or not isinstance(head_repository, dict):
            continue
        if source.get('full_name') != repository or head_repository.get('full_name') != repository:
            continue
        if run.get('path') != workflow_path or run.get('event') != event:
            continue
        sha = run.get('head_sha')
        if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{40}', sha):
            continue
        if head_sha is not None and sha != head_sha:
            continue
        if run.get('status') != 'completed' or run.get('conclusion') != 'success':
            continue
        if any(type(run.get(key)) is not int or run[key] <= 0 for key in ('id', 'run_attempt')):
            continue
        key = (run['id'], run['run_attempt'])
        if key in matches and matches[key] != run:
            raise ValueError('conflicting history identity')
        matches[key] = run
    return [matches[key] for key in sorted(matches, reverse=True)]


if __name__ == "__main__":
    raise SystemExit(main())

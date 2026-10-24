#!/usr/bin/env python3
"""Select the latest run from one exact, repository-owned workflow producer."""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


def select_latest_run(
    payload: dict[str, Any],
    *,
    repository: str,
    workflow_path: str,
    head_sha: str,
    event: str,
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
    parser.add_argument("--event", required=True)
    parser.add_argument("--history", action="store_true", help="Return successful producer history across candidates; not reuse authorization")
    args = parser.parse_args()
    payload = json.load(sys.stdin)
    if args.history:
        json.dump(select_successful_history(payload, repository=args.repository,
            workflow_path=args.workflow_path, event=args.event, head_sha=args.head), sys.stdout,
            separators=(",", ":"), sort_keys=True)
        return 0
    if not args.head:
        parser.error('--head is required unless --history is selected')
    selected = select_latest_run(
        payload,
        repository=args.repository,
        workflow_path=args.workflow_path,
        head_sha=args.head,
        event=args.event,
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

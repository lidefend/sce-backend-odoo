#!/usr/bin/env python3
"""Select the latest run from one exact, repository-owned workflow producer."""
from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--head", required=True)
    parser.add_argument("--event", required=True)
    args = parser.parse_args()
    payload = json.load(sys.stdin)
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


if __name__ == "__main__":
    raise SystemExit(main())

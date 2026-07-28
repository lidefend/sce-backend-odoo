#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from frontend_release_evidence import (
    EvidenceBundleError,
    create_deterministic_zip,
    generate_bundle,
    sha256_file,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--frontend-root", type=Path, required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--statuses", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--branch-protection", type=Path, required=True)
    parser.add_argument("--build-metadata", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--candidate-tree", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--source-run-attempt", required=True)
    args = parser.parse_args()
    try:
        manifest = generate_bundle(
            args.output,
            frontend_root=args.frontend_root,
            dist=args.dist,
            raw_checks=args.checks,
            run_metadata=args.runs,
            statuses=args.statuses,
            artifacts=args.artifacts,
            branch_protection=args.branch_protection,
            build_metadata=args.build_metadata,
            candidate_sha=args.candidate_sha,
            candidate_tree=args.candidate_tree,
            source_run_id=args.source_run_id,
            source_run_attempt=args.source_run_attempt,
        )
        digest = create_deterministic_zip(args.output, args.archive)
        args.archive.with_suffix(args.archive.suffix + ".sha256").write_text(
            f"{digest}  {args.archive.name}\n", encoding="utf-8"
        )
    except EvidenceBundleError as exc:
        print(f"[frontend_release_evidence] BLOCKED reason={exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "result": "PASS",
                "qualification_state": manifest["qualification_state"],
                "candidate_sha": manifest["candidate_sha"],
                "candidate_tree": manifest["candidate_tree"],
                "archive": str(args.archive),
                "archive_sha256": sha256_file(args.archive),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

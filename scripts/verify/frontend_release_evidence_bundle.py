#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "release"))
from frontend_release_evidence import EvidenceBundleError, verify_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--expected-bundle-sha256", default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = verify_bundle(
            args.bundle,
            args.expected_sha,
            args.expected_tree,
            args.expected_bundle_sha256,
        )
        status = 0
    except EvidenceBundleError as exc:
        report = {
            "schema_version": "frontend-release-evidence-verification/v1",
            "result": "BLOCKED",
            "reason_codes": [str(exc)],
            "verified_sha": args.expected_sha,
            "verified_tree": args.expected_tree,
        }
        status = 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())

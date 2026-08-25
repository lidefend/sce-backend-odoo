#!/usr/bin/env python3
"""Create deterministic checked-in accounting-center rollout evidence."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def _load_shared_reporter():
    shared_path = Path(__file__).with_name("frontend_project_domain_rollout_report.py")
    spec = importlib.util.spec_from_file_location("frontend_project_domain_rollout_report_shared", shared_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"shared domain rollout reporter is unavailable: {shared_path}")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    return shared


_SHARED = _load_shared_reporter()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args()
    payload = _SHARED.normalized_snapshot(json.loads(Path(args.input).read_text(encoding="utf-8")))
    Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.markdown_output).write_text(_SHARED.markdown(payload, "Accounting Center Frontend Rollout v1"), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "actions": len(payload["actions"])}))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())


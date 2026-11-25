#!/usr/bin/env python3
"""Capture the real-ORM project ledger contracts for TS decoder evidence."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MARKER = "P0_CONTRACT_DESCRIPTOR_EVIDENCE_B64="


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--form-output", required=True)
    args = parser.parse_args()

    run = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "local.test.test",
            "MODULE=smart_construction_core",
            "TEST_TAGS=p0_contract_descriptor_conformance_evidence",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(run.stdout, end="")
    print(run.stderr, end="")
    if run.returncode:
        return run.returncode

    receipt_match = re.search(r"^\[local.test\] receipt=(.+)$", run.stdout, re.M)
    if not receipt_match:
        print("[p0-descriptor-evidence] FAIL receipt path missing")
        return 2
    receipt_path = Path(receipt_match.group(1).strip())
    if not receipt_path.is_absolute():
        receipt_path = ROOT / receipt_path
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "passed" or int(receipt.get("count") or 0) < 1:
        print("[p0-descriptor-evidence] FAIL ORM evidence test did not pass non-zero")
        return 3
    log_path = Path(str(receipt.get("log") or ""))
    if not log_path.is_absolute():
        log_path = ROOT / log_path
    marker = next(
        (
            line.split(MARKER, 1)[1].strip()
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if MARKER in line
        ),
        "",
    )
    if not marker:
        print("[p0-descriptor-evidence] FAIL contract marker missing")
        return 4
    try:
        payload = json.loads(base64.b64decode(marker).decode("utf-8"))
    except Exception as exc:
        print(f"[p0-descriptor-evidence] FAIL marker decode: {exc}")
        return 5

    contract = payload.get("form")
    if not isinstance(contract, dict):
        print("[p0-descriptor-evidence] FAIL form contract missing")
        return 6
    output = Path(args.form_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(contract, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "[p0-descriptor-evidence] PASS "
        f"project_id={payload.get('project_id')} form={args.form_output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

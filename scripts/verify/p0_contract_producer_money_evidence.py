#!/usr/bin/env python3
"""Capture the real-ORM P0-A monetary Page Block contract for decoder evidence."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MARKER = "P0A_REAL_ORM_MONEY_CONTRACT_B64="


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    run = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "local.test.test",
            "MODULE=smart_construction_core",
            "TEST_TAGS=p0_contract_producer_p0a_money_evidence",
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
        print("[p0a-money-evidence] FAIL receipt path missing")
        return 2
    receipt_path = Path(receipt_match.group(1).strip())
    if not receipt_path.is_absolute():
        receipt_path = ROOT / receipt_path
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "passed" or int(receipt.get("count") or 0) < 1:
        print("[p0a-money-evidence] FAIL ORM evidence test did not pass non-zero")
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
        print("[p0a-money-evidence] FAIL contract marker missing")
        return 4
    try:
        contract = json.loads(base64.b64decode(marker).decode("utf-8"))
    except Exception as exc:
        print(f"[p0a-money-evidence] FAIL marker decode: {exc}")
        return 5

    data = contract["block_data_contracts"]["ds_budget_active_cost_target"]
    row = data["rows"][0]
    identity = str(row["values"].get("company_currency_id") or "")
    currency = data["context"]["currencies"].get(identity) or {}
    if not identity or not currency:
        print("[p0a-money-evidence] FAIL currency identity is not resolvable")
        return 6
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(contract, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "[p0a-money-evidence] PASS "
        f"value={row['values'].get('value')!r} currency={currency.get('code')} output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

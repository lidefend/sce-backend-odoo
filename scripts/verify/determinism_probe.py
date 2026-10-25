#!/usr/bin/env python3
"""Determinism probe: same command, same output, or the baseline is not real.

The precondition for any reproducible baseline is "same input -> same output".
This probe runs one governed command N times and fails on any exit-code or
normalized-output divergence, after stripping only timing/timestamp noise.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \d+ (INFO|WARNING|ERROR|DEBUG) "
)
TIMING_RE = re.compile(r"^(Ran \d+ tests?) in \d+(\.\d+)?s$")
ELAPSED_RE = re.compile(r"\([0-9.]+s\)")


def normalize(text: str) -> str:
    """Strip timing/timestamp noise without touching result-bearing content."""
    lines = []
    for line in (text or "").splitlines():
        line = TIMESTAMP_RE.sub("", line)
        line = ELAPSED_RE.sub("(elapsed)", line)
        match = TIMING_RE.match(line)
        if match:
            line = match.group(1)
        lines.append(line.rstrip())
    return "\n".join(lines)


def run(command: list[str]) -> tuple[int, str]:
    proc = subprocess.run(command, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.runs < 2:
        parser.error("--runs must be at least 2")

    command = [item for item in args.command if item != "--"]
    if not command:
        print("[determinism-probe] empty command", file=sys.stderr)
        return 2

    baseline_code, baseline_out = run(command)
    if baseline_code:
        print(f"[determinism-probe] FAIL baseline exit={baseline_code}")
        return 1
    if re.search(r"^Ran 0 tests? in ", baseline_out, re.MULTILINE):
        print("[determinism-probe] FAIL zero tests collected")
        return 1
    for run_no in range(2, args.runs + 1):
        code, out = run(command)
        if code != baseline_code:
            print(
                f"[determinism-probe] FAIL run {run_no} exit={code} != baseline "
                f"{baseline_code}"
            )
            return 1
        if normalize(out) != normalize(baseline_out):
            print(f"[determinism-probe] FAIL run {run_no} output diverges")
            return 1

    print(f"[determinism-probe] PASS runs={args.runs} exit={baseline_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

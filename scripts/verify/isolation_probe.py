#!/usr/bin/env python3
"""Isolation probe: test order must not change the outcome.

Order-dependence is the classic "passes alone, fails in the suite" smell. This
probe runs a list of test modules in the given order and in reversed order and
fails on any exit-code or normalized-output divergence.
"""
from __future__ import annotations

import argparse
import re

from scripts.verify.determinism_probe import normalize, run


def run_modules(prefix: list[str], modules: list[str]) -> tuple[int, str]:
    return run(prefix + modules)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("modules", nargs="+")
    args = parser.parse_args(argv)

    prefix = ["python3", "-m", "unittest"]
    forward_code, forward_out = run_modules(prefix, list(args.modules))
    reversed_modules = list(reversed(args.modules))
    reverse_code, reverse_out = run_modules(prefix, reversed_modules)

    if forward_code or reverse_code:
        print(f"[isolation-probe] FAIL forward exit={forward_code} reversed exit={reverse_code}")
        return 1

    for output in (forward_out, reverse_out):
        count = re.search(r"^Ran ([0-9]+) tests? in ", output, re.MULTILINE)
        if count is None or int(count.group(1)) == 0:
            print("[isolation-probe] FAIL missing or zero test count")
            return 1

    if forward_code != reverse_code:
        print(
            f"[isolation-probe] FAIL forward exit={forward_code} "
            f"!= reversed exit={reverse_code}"
        )
        return 1
    if normalize(forward_out) != normalize(reverse_out):
        print("[isolation-probe] FAIL forward output != reversed output")
        return 1

    print(
        f"[isolation-probe] PASS modules={len(args.modules)} "
        f"exit={forward_code}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

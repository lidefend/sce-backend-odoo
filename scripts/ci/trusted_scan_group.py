#!/usr/bin/env python3
"""Run the declared governed scan targets concurrently, fail closed.

The three trusted scans are independent read-only passes over the same
repository: each resolves its own trusted scope, writes only its own per-kind
coverage proof, and asserts its own result. Declared as a serial prerequisite
chain, every lane paid their sum, and a full rescan -- exactly what a change to
the scan authority costs -- added about seven minutes of pure wall clock to the
local lane.

Make-level parallelism cannot remove that sum: the governed makefile declares
``.NOTPARALLEL`` for the local lane, so an in-make ``-j`` is accepted and then
ignored (measured: 7m14s, the serial signature). This entry therefore runs the
same governed targets as separate make processes, which the declaration cannot
serialize, and no target is re-implemented here: every member still runs through
the make entry point that owns its command and its unit prerequisite.

It adds no assertion and removes none: a failing member still fails the group,
and the group only reports success when every member exited zero.

Concurrency is derived from the machine rather than a fixed constant, so a small
runner degrades towards the serial order instead of thrashing: at most one worker
per two CPUs, at most one per 3 GiB of available memory, and never more workers
than members. ``SC_TRUSTED_SCAN_JOBS=1`` (or ``--serial``) restores that order
explicitly.
"""

from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

# The declaration consumed by the parallel entry point: the group covers exactly
# these governed targets, each of which still owns its own command and unit
# prerequisite. Keeping the list here rather than in a recipe makes the covered
# set one reviewable fact instead of a command-line string.
SCAN_MEMBERS = (
    "security.secrets.scan",
    "security.personal_data_scan",
    "repository.clean_history.scan",
)
MAKE = ("make", "--no-print-directory")
MEMORY_PER_WORKER = 3 * 1024**3
CPUS_PER_WORKER = 2


@dataclass(frozen=True)
class MemberResult:
    target: str
    returncode: int
    output: str
    duration: float


def available_bytes() -> int | None:
    """Best-effort MemAvailable; an unknown machine keeps the CPU bound only."""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, IndexError, ValueError):
        return None
    return None


def resolve_jobs(requested: int | None, members: int, cpu: int | None = None,
                 memory: int | None = None) -> int:
    """Workers for this machine. Never exceeds the member count, never below one."""
    if members < 1:
        raise ValueError("the group needs at least one member")
    if requested is not None:
        if requested < 1:
            raise ValueError("jobs must be a positive integer")
        return min(requested, members)
    limit = max(1, (os.cpu_count() if cpu is None else cpu) // CPUS_PER_WORKER)
    free = available_bytes() if memory is None else memory
    if free is not None:
        limit = min(limit, max(1, free // MEMORY_PER_WORKER))
    return max(1, min(members, limit))


def run_members(root: Path, targets: tuple[str, ...], jobs: int,
                popen=subprocess.Popen) -> list[MemberResult]:
    """Run every member, at most ``jobs`` at a time, and keep the declared order."""
    pending: queue.Queue[int] = queue.Queue()
    for index in range(len(targets)):
        pending.put(index)
    results: list[MemberResult | None] = [None] * len(targets)
    lock = threading.Lock()

    def worker() -> None:
        while True:
            try:
                index = pending.get_nowait()
            except queue.Empty:
                return
            target = targets[index]
            started = time.monotonic()
            process = popen([*MAKE, target], cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
            output, _ = process.communicate()
            with lock:
                results[index] = MemberResult(target, process.returncode,
                                              output or "", time.monotonic() - started)

    threads = [threading.Thread(target=worker, daemon=True)
               for _ in range(max(1, min(jobs, len(targets))))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if any(result is None for result in results):
        raise RuntimeError("the scan group lost a member result")
    return [result for result in results if result is not None]


def report(results: list[MemberResult], jobs: int) -> int:
    failed = [result for result in results if result.returncode]
    print(f"[trusted_scan_group] members={len(results)} jobs={jobs} "
          f"status={'failed' if failed else 'passed'}")
    for result in results:
        print(f"[trusted_scan_group] --- {result.target} "
              f"rc={result.returncode} {result.duration:.1f}s")
        sys.stdout.write(result.output)
        if result.output and not result.output.endswith("\n"):
            sys.stdout.write("\n")
    if failed:
        print("[trusted_scan_group] FAIL "
              + ", ".join(f"{result.target} (rc={result.returncode})" for result in failed))
        return 1
    print("[trusted_scan_group] PASS every governed scan target exited zero")
    return 0


def _env_jobs() -> int | None:
    raw = os.environ.get("SC_TRUSTED_SCAN_JOBS")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        print(f"[trusted_scan_group] DENY SC_TRUSTED_SCAN_JOBS={raw!r} is not an integer",
              file=sys.stderr)
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--serial", action="store_true")
    args = parser.parse_args(argv)
    targets = tuple(dict.fromkeys(SCAN_MEMBERS))
    if len(targets) != len(SCAN_MEMBERS):
        print("[trusted_scan_group] DENY duplicate member target", file=sys.stderr)
        return 2
    serial = args.serial or os.environ.get("SC_TRUSTED_SCAN_SERIAL") == "1"
    try:
        jobs = 1 if serial else resolve_jobs(
            args.jobs if args.jobs is not None else _env_jobs(), len(targets))
    except ValueError as exc:
        print(f"[trusted_scan_group] DENY {exc}", file=sys.stderr)
        return 2
    return report(run_members(args.root, targets, jobs), jobs)


if __name__ == "__main__":
    raise SystemExit(main())

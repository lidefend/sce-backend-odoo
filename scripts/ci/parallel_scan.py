#!/usr/bin/env python3
"""Bounded, deterministic parallelism shared by the governed scan members.

One mechanism, three call sites. The secrets, personal-data and clean-history
passes all enumerate Git blobs and then run pure per-blob rules with no
cross-blob state. Both of their avoidable serial costs were measured on this
machine (18 cores / 15 GiB, ~24k scanned blobs / 1.17 GB of text):

* one ``git cat-file blob`` process per object: 2.74 ms of spawn each, so about
  66 s of the clean-history pass was process creation, not scanning; and
* a single-threaded regex pass over 1.17 GB at 9 MB/s, i.e. ~130 s with the
  other 15+ cores idle.

This module removes both without changing what a scan covers. A scan function is
mapped over an ordered item list in a bounded worker pool, and every worker
reads its objects from one long-lived ``git cat-file --batch`` stream instead of
one process per object.

Determinism
    :func:`map_ordered` returns exactly one result per input item, in the
    declared input order, so a scan produces the same output whether it ran
    with one worker or many.

Fail closed
    A worker that raises fails the whole scan. A missing object is an error, not
    an empty read -- the same contract the previous per-blob ``check=True``
    spawn had. Worker counts are never silently reduced to hide a defect.

Budget
    The worker count is measured, not guessed: the machine budget is
    ``min(cpu - CPU_HEADROOM, MemAvailable // MEMORY_PER_WORKER)`` and the
    calling group's own concurrency divides it, so co-scheduled scans share one
    machine instead of oversubscribing it. ``SC_SCAN_WORKERS`` pins a count and
    ``SC_SCAN_SERIAL=1`` restores the historical serial order for diagnosis.
"""

from __future__ import annotations

import multiprocessing
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence, TypeVar

# Measured reservation for one scan worker: a worker holds one blob plus regex
# state at a time, so its resident cost is bounded by the largest scanned blob
# rather than by the repository size. 512 MiB is a conservative multiple of the
# measured peak and keeps the memory bound from becoming the binding one first.
MEMORY_PER_WORKER = 512 * 1024**2
# Leave the scheduler and any co-scheduled lane cores rather than claiming every
# CPU for one scan kind.
CPU_HEADROOM = 2
# Chunks are finer than workers so unequal blob sizes still balance; the parent
# scatters results back by original index, so the extra chunks cost no ordering.
CHUNKS_PER_WORKER = 4
WORKERS_ENV = "SC_SCAN_WORKERS"
SERIAL_ENV = "SC_SCAN_SERIAL"
GROUP_JOBS_ENV = "SC_TRUSTED_SCAN_GROUP_JOBS"

T = TypeVar("T")
R = TypeVar("R")


class ObjectReadError(RuntimeError):
    """A scan could not read an object it is required to cover."""


def available_bytes() -> int | None:
    """Best-effort MemAvailable; an unknown machine keeps the CPU bound only."""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, IndexError, ValueError):
        return None
    return None


def cpu_count() -> int:
    return os.cpu_count() or 1


def machine_budget(cpu: int | None = None, memory: int | None = None) -> int:
    """Total scan workers this machine may hold across every concurrent scan."""
    limit = max(1, (cpu_count() if cpu is None else cpu) - CPU_HEADROOM)
    free = available_bytes() if memory is None else memory
    if free is not None:
        limit = min(limit, max(1, free // MEMORY_PER_WORKER))
    return max(1, limit)


def group_jobs() -> int:
    """Concurrency the calling group already holds; 1 when nothing declared it."""
    raw = os.environ.get(GROUP_JOBS_ENV)
    if not raw:
        return 1
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{GROUP_JOBS_ENV}={raw!r} is not an integer") from None
    if value < 1:
        raise ValueError(f"{GROUP_JOBS_ENV}={raw!r} is not a positive integer")
    return value


def resolve_workers(item_count: int, *, cpu: int | None = None,
                    memory: int | None = None) -> int:
    """Workers for one scan of ``item_count`` items. Never zero, never idle-only."""
    if item_count < 1:
        return 1
    if os.environ.get(SERIAL_ENV) == "1":
        return 1
    raw = os.environ.get(WORKERS_ENV)
    if raw:
        try:
            pinned = int(raw)
        except ValueError:
            raise ValueError(f"{WORKERS_ENV}={raw!r} is not an integer") from None
        if pinned < 1:
            raise ValueError(f"{WORKERS_ENV}={raw!r} is not a positive integer")
        return max(1, min(pinned, item_count))
    shared = machine_budget(cpu, memory) // group_jobs()
    return max(1, min(shared, item_count))


class BatchBlobReader:
    """One long-lived ``git cat-file --batch`` shared by a whole worker.

    Replaces one ``git cat-file blob`` process per object. ``read`` keeps the
    old fail-closed contract: a missing object raises instead of returning
    empty bytes, so a coverage hole can never look like a clean object.
    """

    def __init__(self, root: Path):
        self._root = Path(root)
        self._process: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> "BatchBlobReader":
        self._process = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            cwd=self._root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        for stream in (process.stdin, process.stdout):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def read(self, object_id: str) -> bytes:
        process = self._process
        if process is None or process.stdin is None or process.stdout is None:
            raise ObjectReadError("the batch reader is not open")
        request = f"{object_id}\n".encode("utf-8")
        try:
            process.stdin.write(request)
            process.stdin.flush()
            header = process.stdout.readline()
        except (BrokenPipeError, ValueError) as exc:
            raise ObjectReadError(f"batch reader stopped serving objects: {exc}") from exc
        if not header:
            raise ObjectReadError("batch reader closed before answering")
        parts = header.rstrip(b"\n").split(b" ")
        if len(parts) >= 2 and parts[1] == b"missing":
            raise ObjectReadError(f"git cannot resolve object {object_id}")
        if len(parts) != 3 or not parts[2].isdigit():
            raise ObjectReadError(f"unexpected batch header for {object_id}")
        size = int(parts[2])
        payload = process.stdout.read(size)
        if payload is None or len(payload) != size:
            raise ObjectReadError(f"truncated batch payload for {object_id}")
        process.stdout.read(1)  # the newline git writes after every payload
        return payload


def _chunk_indices(count: int, item_count: int) -> list[list[int]]:
    """Stride ``item_count`` indices into ``count`` ordered groups of positions."""
    groups: list[list[int]] = [[] for _ in range(count)]
    for index in range(item_count):
        groups[index % count].append(index)
    return groups


def _pool(workers: int, initializer: Callable[..., None] | None,
          initargs: Sequence[object]) -> multiprocessing.pool.Pool:
    contexts = []
    if hasattr(os, "fork"):
        contexts.append(multiprocessing.get_context("fork"))
    contexts.append(multiprocessing.get_context())
    last: Exception | None = None
    for context in contexts:
        try:
            return context.Pool(workers, initializer=initializer, initargs=tuple(initargs))
        except (OSError, ValueError) as exc:  # pragma: no cover - platform fallback
            last = exc
    raise RuntimeError(f"cannot start a scan worker pool: {last}")


def map_ordered(items: Sequence[T], worker: Callable[[list[T]], list[R]], workers: int,
                *, initializer: Callable[..., None] | None = None,
                initargs: Sequence[object] = ()) -> list[R]:
    """Apply ``worker`` to every item and return results in the declared order.

    ``worker`` receives a non-empty list of items and must return one result per
    item in the same order. With one worker this is a plain in-process call that
    still runs ``initializer``, so a serial run and a parallel run share a single
    code path and a serial run cannot silently miss worker setup.
    """
    ordered = list(items)
    if not ordered:
        return []
    if workers <= 1:
        if initializer is not None:
            initializer(*initargs)
        return list(worker(ordered))
    count = max(1, min(workers * CHUNKS_PER_WORKER, len(ordered)))
    index_groups = _chunk_indices(count, len(ordered))
    chunks = [[ordered[index] for index in group] for group in index_groups]
    with _pool(min(workers, len(chunks)), initializer, initargs) as pool:
        parts = pool.map(worker, chunks, chunksize=1)
    results: list[R | None] = [None] * len(ordered)
    for group, part in zip(index_groups, parts):
        if len(part) != len(group):
            raise RuntimeError("a scan worker returned an unexpected result count")
        for index, value in zip(group, part):
            results[index] = value
    if any(value is None for value in results):
        raise RuntimeError("a scan worker produced no result")
    return [value for value in results if value is not None]


def report() -> str:
    """One-line fact statement, printed by callers that want the budget visible."""
    return (f"[parallel_scan] workers={resolve_workers(1)} "
            f"machine_budget={machine_budget()} group_jobs={group_jobs()} "
            f"cpu={cpu_count()}")


if __name__ == "__main__":  # pragma: no cover - diagnostic entry
    print(report(), file=sys.stdout)

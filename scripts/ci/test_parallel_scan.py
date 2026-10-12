#!/usr/bin/env python3
"""Unit coverage for the shared parallel scan mechanism."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import parallel_scan


def _square(chunk: list[int]) -> list[int]:
    return [value * value for value in chunk]


def _fail_on(chunk: list[int]) -> list[int]:
    for value in chunk:
        if value == 7:
            raise ValueError("declared worker failure")
    return list(chunk)


def _read_batch(chunk: list[tuple[str, list[str]]]) -> list[int]:
    return [len(_read_one(payload)) for payload in chunk]


def _read_one(payload: tuple[str, list[str]]) -> list[str]:
    root, object_ids = payload
    with parallel_scan.BatchBlobReader(Path(root)) as reader:
        return [reader.read(object_id).decode("utf-8") for object_id in object_ids]


def _truncating(chunk: list[int]) -> list[int]:
    return list(chunk)[:-1]


class MapOrderedTests(unittest.TestCase):
    def test_parallel_and_serial_agree_on_order(self) -> None:
        items = list(range(1, 200))
        serial = parallel_scan.map_ordered(items, _square, 1)
        parallel = parallel_scan.map_ordered(items, _square, 6)
        self.assertEqual(serial, [value * value for value in items])
        self.assertEqual(serial, parallel)

    def test_empty_input_returns_no_result(self) -> None:
        self.assertEqual(parallel_scan.map_ordered([], _square, 4), [])

    def test_single_item_runs_in_process(self) -> None:
        self.assertEqual(parallel_scan.map_ordered([3], _square, 8), [9])

    def test_worker_exception_fails_the_whole_scan(self) -> None:
        with self.assertRaises(ValueError):
            parallel_scan.map_ordered(list(range(1, 40)), _fail_on, 4)

    def test_serial_path_still_runs_the_worker_initializer(self) -> None:
        seen: list[str] = []

        def initialize(marker: str) -> None:
            seen.append(marker)

        self.assertEqual(
            parallel_scan.map_ordered([1, 2, 3], _square, 1,
                                      initializer=initialize, initargs=("seeded",)),
            [1, 4, 9],
        )
        self.assertEqual(seen, ["seeded"])

    def test_worker_result_count_mismatch_is_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            parallel_scan.map_ordered(list(range(20)), _truncating, 4)


class ResolveWorkersTests(unittest.TestCase):
    def test_item_count_bounds_the_pool(self) -> None:
        self.assertEqual(parallel_scan.resolve_workers(2), 2)

    def test_serial_escape_restores_one_worker(self) -> None:
        with mock.patch.dict(os.environ, {parallel_scan.SERIAL_ENV: "1"}):
            self.assertEqual(parallel_scan.resolve_workers(100), 1)

    def test_explicit_workers_are_pinned_but_never_over_the_items(self) -> None:
        with mock.patch.dict(os.environ, {parallel_scan.WORKERS_ENV: "5"}):
            self.assertEqual(parallel_scan.resolve_workers(100), 5)
            self.assertEqual(parallel_scan.resolve_workers(3), 3)

    def test_invalid_worker_count_is_rejected(self) -> None:
        for raw in ("0", "-2", "many"):
            with self.subTest(raw=raw):
                with mock.patch.dict(os.environ, {parallel_scan.WORKERS_ENV: raw}):
                    with self.assertRaises(ValueError):
                        parallel_scan.resolve_workers(10)

    def test_group_concurrency_divides_one_machine_budget(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(parallel_scan.WORKERS_ENV, None)
            os.environ.pop(parallel_scan.SERIAL_ENV, None)
            os.environ.pop(parallel_scan.GROUP_JOBS_ENV, None)
            alone = parallel_scan.resolve_workers(1000, cpu=18, memory=64 * 1024**3)
            os.environ[parallel_scan.GROUP_JOBS_ENV] = "3"
            try:
                shared = parallel_scan.resolve_workers(1000, cpu=18, memory=64 * 1024**3)
            finally:
                os.environ.pop(parallel_scan.GROUP_JOBS_ENV, None)
        self.assertEqual(alone, 16)
        self.assertEqual(shared, 5)
        self.assertLessEqual(shared * 3, alone)

    def test_memory_can_be_the_binding_bound(self) -> None:
        self.assertEqual(
            parallel_scan.machine_budget(cpu=64, memory=2 * parallel_scan.MEMORY_PER_WORKER),
            2,
        )

    def test_invalid_group_concurrency_is_rejected(self) -> None:
        with mock.patch.dict(os.environ, {parallel_scan.GROUP_JOBS_ENV: "0"}):
            with self.assertRaises(ValueError):
                parallel_scan.resolve_workers(10)


class BatchBlobReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self._git("init", "-q")
        self._git("config", "user.email", "scan@example.invalid")
        self._git("config", "user.name", "scan")
        for index in range(6):
            (self.root / f"file{index}.txt").write_text(f"payload {index}\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "fixture")

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ).stdout

    def _object_ids(self) -> list[str]:
        listing = self._git("ls-tree", "-r", "HEAD")
        return [line.split("\t")[0].split()[2] for line in listing.splitlines() if "\t" in line]

    def test_one_process_serves_many_objects(self) -> None:
        object_ids = self._object_ids()
        self.assertGreater(len(object_ids), 1)
        with mock.patch.object(subprocess, "Popen", wraps=subprocess.Popen) as popen:
            with parallel_scan.BatchBlobReader(self.root) as reader:
                payloads = [reader.read(object_id) for object_id in object_ids]
        self.assertEqual(popen.call_count, 1)
        self.assertTrue(any(b"payload" in payload for payload in payloads))

    def test_payloads_match_the_per_object_reader(self) -> None:
        object_ids = self._object_ids()
        expected = [
            subprocess.run(["git", "cat-file", "blob", object_id], cwd=self.root,
                           check=True, stdout=subprocess.PIPE).stdout
            for object_id in object_ids
        ]
        with parallel_scan.BatchBlobReader(self.root) as reader:
            actual = [reader.read(object_id) for object_id in object_ids]
        self.assertEqual(expected, actual)

    def test_missing_object_fails_closed(self) -> None:
        with parallel_scan.BatchBlobReader(self.root) as reader:
            with self.assertRaises(parallel_scan.ObjectReadError):
                reader.read("0" * 40)

    def test_closed_reader_fails_closed(self) -> None:
        reader = parallel_scan.BatchBlobReader(self.root)
        with self.assertRaises(parallel_scan.ObjectReadError):
            reader.read("1" * 40)

    def test_workers_read_their_own_batch_stream(self) -> None:
        object_ids = self._object_ids()
        chunks = [(str(self.root), object_ids[index::3]) for index in range(3)]
        results = parallel_scan.map_ordered(chunks, _read_batch, 3)
        self.assertEqual(len(results), len(chunks))
        self.assertEqual(sum(results), len(object_ids))
        self.assertTrue(all(count > 0 for count in results))


if __name__ == "__main__":
    unittest.main()

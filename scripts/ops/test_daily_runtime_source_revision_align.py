#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shlex
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("daily_runtime_source_revision_align.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_source_revision_align", SCRIPT)
assert SPEC and SPEC.loader
align_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(align_module)

SHA = "a" * 40
OLD_SHA = "b" * 40


def evidence(**overrides: object) -> bytes:
    payload: dict[str, object] = {
        "status": "PASS",
        "expected_sha": SHA,
        "head": SHA,
        "previous_revision": OLD_SHA,
        "env_file": "/opt/projects/repos/sce-product-odoo/.env.dev",
        "env_written": True,
        "backup_path": "/opt/projects/repos/sce-product-odoo/.env.dev.bak",
        "restarted": True,
        "rolled_back": False,
        "served": {
            "git_sha": SHA,
            "source_revision": SHA,
            "database": "sc_demo",
            "environment": "dev",
        },
        "remote_root": align_module.REMOTE_ROOT,
        "restart_tail": "",
    }
    payload.update(overrides)
    return (json.dumps(payload) + "\n").encode()


class DailyRuntimeSourceRevisionAlignTests(unittest.TestCase):
    def test_preflight_requires_confirmation(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(align_module.AlignError, "confirmation"):
                align_module.preflight(SHA, "sc-root")

    def test_preflight_rejects_non_commit_revision(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN": align_module.CONFIRMATION},
        ):
            with self.assertRaisesRegex(align_module.AlignError, "commit SHA"):
                align_module.preflight("HEAD", "sc-root")
            with self.assertRaisesRegex(align_module.AlignError, "host alias"):
                align_module.preflight(SHA, "sc-root; rm -rf /")

    def test_preflight_accepts_governed_inputs(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN": align_module.CONFIRMATION},
        ):
            align_module.preflight(SHA, "sc-root")

    def test_remote_command_binds_exact_revision(self) -> None:
        command = align_module.remote_command(SHA, "dev", ".env.dev", "odoo", "http://127.0.0.1:18081")
        self.assertEqual(
            shlex.split(command),
            [
                "python3",
                "-c",
                align_module.REMOTE_ALIGN,
                SHA,
                "dev",
                ".env.dev",
                "odoo",
                "http://127.0.0.1:18081",
                align_module.REMOTE_ROOT,
            ],
        )

    def test_align_accepts_matching_evidence(self) -> None:
        completed = mock.Mock(returncode=0, stdout=evidence(), stderr=b"")
        with mock.patch.dict(
            os.environ,
            {"CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN": align_module.CONFIRMATION},
        ), mock.patch.object(align_module, "run", return_value=completed):
            result = align_module.align(SHA, "sc-root", "dev", ".env.dev", "odoo", "http://127.0.0.1:18081")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["expected_sha"], SHA)

    def test_align_rejects_stale_served_revision(self) -> None:
        stale = evidence(served={"git_sha": OLD_SHA})
        completed = mock.Mock(returncode=0, stdout=stale, stderr=b"")
        with mock.patch.dict(
            os.environ,
            {"CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN": align_module.CONFIRMATION},
        ), mock.patch.object(align_module, "run", return_value=completed):
            with self.assertRaisesRegex(align_module.AlignError, "evidence differs"):
                align_module.align(SHA, "sc-root", "dev", ".env.dev", "odoo", "http://127.0.0.1:18081")

    def test_align_rejects_rolled_back_result(self) -> None:
        rolled = evidence(status="BLOCKED", rolled_back=True)
        completed = mock.Mock(returncode=0, stdout=rolled, stderr=b"")
        with mock.patch.dict(
            os.environ,
            {"CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN": align_module.CONFIRMATION},
        ), mock.patch.object(align_module, "run", return_value=completed):
            with self.assertRaisesRegex(align_module.AlignError, "evidence differs"):
                align_module.align(SHA, "sc-root", "dev", ".env.dev", "odoo", "http://127.0.0.1:18081")

    def test_align_reports_remote_failure(self) -> None:
        completed = mock.Mock(returncode=1, stdout=b"", stderr=b"BLOCKED remote HEAD differs")
        with mock.patch.dict(
            os.environ,
            {"CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN": align_module.CONFIRMATION},
        ), mock.patch.object(align_module, "run", return_value=completed):
            with self.assertRaisesRegex(align_module.AlignError, "remote HEAD differs"):
                align_module.align(SHA, "sc-root", "dev", ".env.dev", "odoo", "http://127.0.0.1:18081")


if __name__ == "__main__":
    unittest.main()

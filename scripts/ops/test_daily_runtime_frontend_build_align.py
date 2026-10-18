#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("daily_runtime_frontend_build_align.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_frontend_build_align", SCRIPT)
assert SPEC and SPEC.loader
build_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_module)

SHA = "a" * 40
OLD_SHA = "b" * 40
FINGERPRINT = "c" * 64
OLD_FINGERPRINT = "d" * 64
ENTRY_ASSET = "index-DPFnm5JE.js"
ADMIN_DB = "sc_platform_control"
OLD_ADMIN_DB = "sc_platform_core"
CONFIRM = {"CONFIRM_DAILY_RUNTIME_FRONTEND_BUILD": build_module.CONFIRMATION}


def evidence(**overrides: object) -> bytes:
    payload: dict[str, object] = {
        "status": "PASS",
        "expected_sha": SHA,
        "head": SHA,
        "reused": False,
        "rebuilt": True,
        "fingerprint": FINGERPRINT,
        "entry_asset": ENTRY_ASSET,
        "env_file": "/opt/projects/repos/sce-product-odoo/.env.dev",
        "env_written": True,
        "backup_path": "/opt/projects/repos/sce-product-odoo/.env.dev.bak",
        "restarted": True,
        "runtime_refresh_required": True,
        "rolled_back": False,
        "served": {
            "git_sha": SHA,
            "source_revision": SHA,
            "database": "sc_demo",
            "environment": "dev",
            "frontend_build_sha256": FINGERPRINT,
        },
        "served_entry_asset": ENTRY_ASSET,
        "platform_admin_database": ADMIN_DB,
        "platform_admin_baked": True,
        "platform_admin_written": False,
        "dist_dir": "/opt/projects/repos/sce-product-odoo/frontend/apps/web/dist-dev",
        "remote_root": build_module.REMOTE_ROOT,
        "build_tail": "",
        "fingerprint_tail": "",
        "restart_tail": "",
    }
    payload.update(overrides)
    return (json.dumps(payload) + "\n").encode()


def write_receipt(directory: str, **overrides: object) -> str:
    payload: dict[str, object] = {
        "status": "PASS",
        "expected_sha": SHA,
        "head": SHA,
        "remote_root": build_module.REMOTE_ROOT,
        "fingerprint": FINGERPRINT,
        "entry_asset": ENTRY_ASSET,
    }
    payload.update(overrides)
    path = Path(directory) / "frontend-build.json"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return str(path)


def call_align(**overrides: object):
    args: dict[str, object] = {
        "expected_sha": SHA,
        "ssh_host": "sc-root",
        "env_name": "dev",
        "env_file": ".env.dev",
        "database": "sc_demo",
        "base_url": "http://127.0.0.1:18081",
        "fingerprint_hint": "",
        "entry_hint": "",
        "platform_admin_database": ADMIN_DB,
    }
    args.update(overrides)
    return build_module.align(**args)  # type: ignore[arg-type]


class DailyRuntimeFrontendBuildAlignTests(unittest.TestCase):
    def test_preflight_requires_confirmation(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(build_module.BuildError, "confirmation"):
                build_module.preflight(SHA, "sc-root", ADMIN_DB)

    def test_preflight_rejects_non_commit_revision(self) -> None:
        with mock.patch.dict(os.environ, CONFIRM):
            with self.assertRaisesRegex(build_module.BuildError, "commit SHA"):
                build_module.preflight("HEAD", "sc-root", ADMIN_DB)
            with self.assertRaisesRegex(build_module.BuildError, "host alias"):
                build_module.preflight(SHA, "sc-root; rm -rf /", ADMIN_DB)

    def test_preflight_accepts_governed_inputs(self) -> None:
        with mock.patch.dict(os.environ, CONFIRM):
            build_module.preflight(SHA, "sc-root", ADMIN_DB)

    def test_preflight_requires_the_declared_platform_admin_database(self) -> None:
        with mock.patch.dict(os.environ, CONFIRM):
            for bad in ("", "sc platform", "-control", "SC_Platform_Control"):
                with self.assertRaisesRegex(build_module.BuildError, "platform-admin database"):
                    build_module.preflight(SHA, "sc-root", bad)
            build_module.preflight(SHA, "sc-root", ADMIN_DB)

    def test_the_entry_ships_no_bare_database_default(self) -> None:
        """The served database is a governance fact, not an entry default.

        A database *name* does not identify a carrier: the rebuilt demo duty and
        the preserved historic source both answer to ``sc_demo``.  A shipped
        literal would also silently bake a stale name after a declaration change.
        """
        self.assertEqual(build_module.DEFAULT_DATABASE, "")

    def test_an_unset_or_illegal_served_database_fails_closed(self) -> None:
        for bad in ("", "sc demo", "-sc_demo", "SC_DEMO"):
            with mock.patch.dict(os.environ, CONFIRM):
                with self.assertRaisesRegex(build_module.BuildError, "served database"):
                    call_align(database=bad)

    def test_the_make_lane_derives_the_served_database_from_the_declaration(self) -> None:
        makefile = Path(__file__).resolve().parents[2] / "make" / "codex.mk"
        text = makefile.read_text(encoding="utf-8")
        self.assertNotIn("DAILY_RUNTIME_FRONTEND_BUILD_DATABASE ?= sc_demo", text)
        self.assertIn("daily_runtime_database_duties.v1.json", text)

    def test_remote_command_binds_exact_revision_and_reuse_hint(self) -> None:
        command = build_module.remote_command(
            SHA, "dev", ".env.dev", "sc_demo", "http://127.0.0.1:18081", FINGERPRINT,
            ENTRY_ASSET, ADMIN_DB,
        )
        self.assertEqual(
            shlex.split(command),
            [
                "python3",
                "-c",
                build_module.REMOTE_BUILD,
                SHA,
                "dev",
                ".env.dev",
                "sc_demo",
                "http://127.0.0.1:18081",
                build_module.REMOTE_ROOT,
                FINGERPRINT,
                ENTRY_ASSET,
                ADMIN_DB,
            ],
        )

    def test_remote_command_declares_governed_entries(self) -> None:
        for token in (
            "verify.frontend.build",
            "frontend_build_fingerprint.sh",
            "FRONTEND_BUILD_SHA256",
            "VITE_PLATFORM_ADMIN_DB",
            "make",
            "restart",
            "/api/runtime-version",
        ):
            self.assertIn(token, build_module.REMOTE_BUILD)

    def test_reuse_hint_missing_receipt_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                build_module.reuse_hint(str(Path(directory) / "absent.json"), SHA), ("", "")
            )

    def test_reuse_hint_returns_recorded_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_receipt(directory)
            self.assertEqual(build_module.reuse_hint(path, SHA), (FINGERPRINT, ENTRY_ASSET))

    def test_reuse_hint_ignores_other_commit_or_invalid_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(build_module.reuse_hint(write_receipt(directory, head=OLD_SHA), SHA), ("", ""))
            self.assertEqual(build_module.reuse_hint(write_receipt(directory, status="BLOCKED"), SHA), ("", ""))
            self.assertEqual(build_module.reuse_hint(write_receipt(directory, fingerprint="nope"), SHA), ("", ""))
            self.assertEqual(build_module.reuse_hint(write_receipt(directory, entry_asset="../evil.js"), SHA), ("", ""))

    def test_align_accepts_matching_evidence(self) -> None:
        completed = mock.Mock(returncode=0, stdout=evidence(), stderr=b"")
        with mock.patch.dict(os.environ, CONFIRM), mock.patch.object(
            build_module, "run", return_value=completed
        ):
            result = call_align()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["fingerprint"], FINGERPRINT)
        self.assertEqual(result["served_entry_asset"], ENTRY_ASSET)

    def test_align_accepts_reused_generation(self) -> None:
        completed = mock.Mock(
            returncode=0, stdout=evidence(reused=True, rebuilt=False, env_written=False), stderr=b""
        )
        with mock.patch.dict(os.environ, CONFIRM), mock.patch.object(
            build_module, "run", return_value=completed
        ):
            result = call_align(fingerprint_hint=FINGERPRINT, entry_hint=ENTRY_ASSET)
        self.assertTrue(result["reused"])

    def test_align_accepts_stale_runtime_identity_until_duty_refresh(self) -> None:
        stale = evidence(
            served={
                "git_sha": SHA,
                "database": "sc_demo",
                "environment": "dev",
                "frontend_build_sha256": OLD_FINGERPRINT,
            }
        )
        completed = mock.Mock(returncode=0, stdout=stale, stderr=b"")
        with mock.patch.dict(os.environ, CONFIRM), mock.patch.object(
            build_module, "run", return_value=completed
        ):
            result = call_align()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["served"]["frontend_build_sha256"], OLD_FINGERPRINT)

    def test_align_rejects_a_non_boolean_runtime_refresh_marker(self) -> None:
        malformed = evidence(runtime_refresh_required="yes")
        completed = mock.Mock(returncode=0, stdout=malformed, stderr=b"")
        with mock.patch.dict(os.environ, CONFIRM), mock.patch.object(
            build_module, "run", return_value=completed
        ):
            with self.assertRaisesRegex(build_module.BuildError, "evidence differs"):
                call_align()

    def test_align_rejects_served_entry_mismatch(self) -> None:
        mismatched = evidence(served_entry_asset="index-OTHER.js")
        completed = mock.Mock(returncode=0, stdout=mismatched, stderr=b"")
        with mock.patch.dict(os.environ, CONFIRM), mock.patch.object(
            build_module, "run", return_value=completed
        ):
            with self.assertRaisesRegex(build_module.BuildError, "evidence differs"):
                call_align()

    def test_align_rejects_rolled_back_result(self) -> None:
        rolled = evidence(status="BLOCKED", rolled_back=True)
        completed = mock.Mock(returncode=0, stdout=rolled, stderr=b"")
        with mock.patch.dict(os.environ, CONFIRM), mock.patch.object(
            build_module, "run", return_value=completed
        ):
            with self.assertRaisesRegex(build_module.BuildError, "evidence differs"):
                call_align()

    def test_align_rejects_a_bundle_that_does_not_bake_the_declared_authority(self) -> None:
        """The env line says what the next build should bake; the artifact says what is served.

        A bundle built before the switch still mounts the previous database, so
        an entry that only read the env file would report a switched authority
        while the browser kept loading the old one.
        """
        unswitched = evidence(platform_admin_baked=False)
        completed = mock.Mock(returncode=0, stdout=unswitched, stderr=b"")
        with mock.patch.dict(os.environ, CONFIRM), mock.patch.object(
            build_module, "run", return_value=completed
        ):
            with self.assertRaisesRegex(build_module.BuildError, "evidence differs"):
                call_align()

    def test_align_rejects_a_bundle_baked_with_another_authority(self) -> None:
        other = evidence(platform_admin_database=OLD_ADMIN_DB)
        completed = mock.Mock(returncode=0, stdout=other, stderr=b"")
        with mock.patch.dict(os.environ, CONFIRM), mock.patch.object(
            build_module, "run", return_value=completed
        ):
            with self.assertRaisesRegex(build_module.BuildError, "evidence differs"):
                call_align()

    def test_the_build_input_is_declared_before_the_build_and_the_outcome_after(self) -> None:
        program = build_module.REMOTE_BUILD
        declare = program.index("env_write_line(\n        platform_admin_key, platform_admin_database\n    )")
        build_call = program.index("code, build_tail = build()")
        outcome = program.index('env_write_line("FRONTEND_BUILD_SHA256", fingerprint)')
        self.assertLess(
            declare, build_call,
            "a value the build consumes must be declared before the build runs, or the "
            "served bundle and the declaration disagree",
        )
        self.assertLess(
            build_call, outcome,
            "the recorded build identity describes the artifact, so it is declared after it",
        )

    def test_a_build_that_fails_restores_the_declaration_it_changed(self) -> None:
        self.assertIn("restore_env()", build_module.REMOTE_BUILD)
        body = build_module.REMOTE_BUILD.split("code, build_tail = build()", 1)[1]
        self.assertIn(
            "restore_env()", body.split("blocked(", 1)[0],
            "leaving the new authority declared while the old bundle is served is the "
            "drift this entry exists to prevent",
        )

    def test_reuse_requires_the_baked_authority_to_match(self) -> None:
        """A recorded generation is only reusable while it carries the declared authority.

        Reusing on the fingerprint alone would re-serve the previous authority
        whenever the recorded generation happened to be the one on disk.
        """
        reuse = build_module.REMOTE_BUILD.split("reused = bool(", 1)[1].split("\n    )", 1)[0]
        self.assertIn("declared_admin == platform_admin_database", reuse)
        self.assertIn("baked_admin()", reuse)

    def test_align_reports_remote_failure(self) -> None:
        completed = mock.Mock(
            returncode=1, stdout=b"", stderr=b"BLOCKED remote worktree is not clean"
        )
        with mock.patch.dict(os.environ, CONFIRM), mock.patch.object(
            build_module, "run", return_value=completed
        ):
            with self.assertRaisesRegex(build_module.BuildError, "worktree is not clean"):
                call_align()


if __name__ == "__main__":
    unittest.main()

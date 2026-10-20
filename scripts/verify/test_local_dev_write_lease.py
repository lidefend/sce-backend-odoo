#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEASE = ROOT / "scripts/dev/local_dev_write_lease.sh"


class LocalDevWriteLeaseTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.lock_file = str(Path(self.tempdir.name) / "write.lock")
        self.env = dict(os.environ)
        self.env.update(
            {
                "SC_LOCAL_DEV_WRITE_LOCK_TEST": "1",
                "SC_LOCAL_DEV_WRITE_LOCK_FILE": self.lock_file,
                "SC_LOCAL_DEV_WRITE_LOCK_TIMEOUT": "0",
            }
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def run_lease(self, *args, timeout=10):
        return subprocess.run(
            [str(LEASE), *args],
            cwd=ROOT,
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )

    def test_second_writer_fails_closed_while_lease_held(self):
        holder_env = dict(self.env)
        holder_env["SC_LOCAL_DEV_WRITE_LOCK_TIMEOUT"] = "5"
        holder = subprocess.Popen(
            [str(LEASE), "hold", "--", "bash", "-c", "sleep 2"],
            cwd=ROOT,
            env=holder_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.time() + 5
            while time.time() < deadline:
                status = self.run_lease("--status")
                if status.returncode == 1 and "LOCAL_DEV_WRITE_LEASE_BUSY" in status.stdout:
                    break
                time.sleep(0.05)
            else:
                self.fail("lease was not observed as held")

            blocked = self.run_lease("second", "--", "true")
            self.assertEqual(blocked.returncode, 75)
            self.assertIn("LOCAL_DEV_WRITE_LEASE_BUSY", blocked.stderr)
        finally:
            holder.communicate(timeout=5)

    def test_waiter_acquires_after_release(self):
        holder_env = dict(self.env)
        holder_env["SC_LOCAL_DEV_WRITE_LOCK_TIMEOUT"] = "5"
        holder = subprocess.Popen(
            [str(LEASE), "hold", "--", "bash", "-c", "sleep 1"],
            cwd=ROOT,
            env=holder_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(0.2)
        waiter_env = dict(self.env)
        waiter_env["SC_LOCAL_DEV_WRITE_LOCK_TIMEOUT"] = "5"
        waiter = subprocess.run(
            [str(LEASE), "waiter", "--", "true"],
            cwd=ROOT,
            env=waiter_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        holder.communicate(timeout=5)
        self.assertEqual(waiter.returncode, 0, waiter.stderr)

    def test_require_rejects_direct_internal_target(self):
        result = self.run_lease("--require")
        self.assertEqual(result.returncode, 75)
        self.assertIn("LOCAL_DEV_WRITE_LEASE_REQUIRED", result.stderr)

    def test_require_accepts_leased_inner_command(self):
        result = self.run_lease("leased", "--", str(LEASE), "--require")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_override_is_forbidden_without_test_flag(self):
        env = dict(self.env)
        env.pop("SC_LOCAL_DEV_WRITE_LOCK_TEST", None)
        result = subprocess.run(
            [str(LEASE), "bad", "--", "true"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("LOCAL_DEV_WRITE_LOCK_OVERRIDE_FORBIDDEN", result.stderr)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REVERSE_SYNC_SCRIPT = ROOT / "scripts" / "ops" / "gitee_to_github_mirror.sh"
RULESET_SCRIPT = ROOT / "scripts" / "ops" / "configure_github_mirror_ruleset.sh"
RULESET_GUARD = ROOT / "scripts" / "verify" / "github_non_mirror_push_denied.sh"
WORKER_UNIT = ROOT / "deploy" / "gitee-ci" / "gitee-ci-worker.service"
CI_INSTALL = ROOT / "deploy" / "gitee-ci" / "install.sh"


class MirrorGateTests(unittest.TestCase):
    def test_reverse_sync_is_unconditionally_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake_git = Path(temporary) / "git"
            invocation_log = Path(temporary) / "git.log"
            fake_git.write_text(
                f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> {invocation_log}\nexit 91\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o700)
            result = subprocess.run(
                ["bash", str(REVERSE_SYNC_SCRIPT)],
                env={**os.environ, "PATH": f"{temporary}:{os.environ['PATH']}"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("BLOCKED reverse_sync_disabled", result.stderr)
            self.assertFalse(invocation_log.exists())

    def test_ruleset_has_no_deploy_key_or_bypass(self) -> None:
        text = RULESET_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('repository="lidefend/sce-backend-odoo"', text)
        self.assertIn('ruleset_name="main-github-authoritative-pr"', text)
        self.assertIn("bypass_actors: []", text)
        self.assertIn("write_deploy_key_present", text)
        self.assertNotIn('actor_type: "DeployKey"', text)
        self.assertNotIn("read_only=false", text)

    def test_ruleset_guard_requires_no_bypass_or_write_key(self) -> None:
        text = RULESET_GUARD.read_text(encoding="utf-8")
        self.assertIn('repository="lidefend/sce-backend-odoo"', text)
        self.assertIn('ruleset_name="main-github-authoritative-pr"', text)
        self.assertIn("(.bypass_actors | length) == 0", text)
        self.assertIn('select(.read_only == false)', text)

    def test_worker_sandbox_keeps_legacy_reverse_credential_out(self) -> None:
        text = WORKER_UNIT.read_text(encoding="utf-8")
        read_write = next(line for line in text.splitlines() if line.startswith("ReadWritePaths="))
        self.assertIn("/var/lib/gitee-mirror/source.git", read_write.split())
        self.assertNotIn("/etc/gitee-mirror", read_write)
        self.assertNotIn("github_ed25519", text)
        install_text = CI_INSTALL.read_text(encoding="utf-8")
        self.assertIn("GITEE_MIRROR_SOURCE_REPO=/var/lib/gitee-mirror/source.git", install_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

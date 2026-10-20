#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ops" / "controlled_main_cutover.py"
SPEC = importlib.util.spec_from_file_location("controlled_main_cutover", SCRIPT)
assert SPEC and SPEC.loader
cutover = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cutover
SPEC.loader.exec_module(cutover)


class ControlledMainCutoverTests(unittest.TestCase):
    def test_token_file_requires_private_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "token"
            path.write_text("x" * 32, encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaisesRegex(cutover.CutoverError, "mode must be"):
                cutover.read_token(path)
            path.chmod(0o600)
            self.assertEqual("x" * 32, cutover.read_token(path))

    def test_ruleset_restore_payload_preserves_rules(self) -> None:
        source = {
            "name": cutover.RULESET_NAME,
            "target": "branch",
            "enforcement": "active",
            "bypass_actors": [],
            "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
            "rules": [{"type": "non_fast_forward"}],
            "id": 123,
            "_links": {"self": "not-writeable"},
        }
        disabled = cutover.ruleset_payload(source, "disabled")
        restored = cutover.ruleset_payload(source, "active")
        self.assertEqual("disabled", disabled["enforcement"])
        self.assertEqual("active", restored["enforcement"])
        self.assertEqual(source["rules"], restored["rules"])
        self.assertNotIn("id", restored)
        self.assertNotIn("_links", restored)

    def test_push_main_uses_exact_lease(self) -> None:
        target = "a" * 40
        old = "b" * 40
        completed = cutover.subprocess.CompletedProcess([], 0, "", "")
        with mock.patch.object(cutover, "run", return_value=completed) as runner:
            with mock.patch.object(cutover, "remote_sha", return_value=target):
                cutover.push_main("origin", target, old)
        runner.assert_called_once_with(
            "git",
            "push",
            f"--force-with-lease=refs/heads/main:{old}",
            "origin",
            f"{target}:refs/heads/main",
        )

    def test_required_checks_bind_unique_successful_run_ids(self) -> None:
        target = "a" * 40
        runs = []
        for index, name in enumerate(cutover.REQUIRED_CHECKS, start=101):
            runs.append(
                {
                    "id": index,
                    "name": name,
                    "status": "completed",
                    "conclusion": "success",
                    "head_sha": target,
                    "details_url": f"https://checks.example/{index}",
                }
            )
        with mock.patch.object(cutover, "gh_json", return_value={"check_runs": runs}):
            evidence = cutover.verify_required_checks(target)
        self.assertEqual(101, evidence[cutover.REQUIRED_CHECKS[0]]["check_run_id"])
        self.assertEqual("PASS", evidence[cutover.REQUIRED_CHECKS[0]]["result"])

    def test_post_cutover_revalidates_bound_ids_despite_new_duplicate(self) -> None:
        target = "a" * 40
        bound = {
            name: {
                "result": "PASS",
                "check_run_id": index,
                "details_url": f"https://checks.example/{index}",
            }
            for index, name in enumerate(cutover.REQUIRED_CHECKS, start=201)
        }

        def exact_check(path: str) -> dict[str, object]:
            check_id = int(path.rsplit("/", 1)[-1])
            name = cutover.REQUIRED_CHECKS[check_id - 201]
            return {
                "id": check_id,
                "name": name,
                "status": "completed",
                "conclusion": "success",
                "head_sha": target,
                "details_url": f"https://checks.example/{check_id}",
            }

        with mock.patch.object(cutover, "gh_json", side_effect=exact_check) as api:
            verified = cutover.verify_bound_required_checks(target, bound)
        self.assertEqual(bound, verified)
        self.assertEqual(len(cutover.REQUIRED_CHECKS), api.call_count)

    def test_post_cutover_bound_check_fails_closed_on_sha_change(self) -> None:
        bound = {
            name: {"result": "PASS", "check_run_id": index, "details_url": ""}
            for index, name in enumerate(cutover.REQUIRED_CHECKS, start=301)
        }
        item = {
            "id": 301,
            "name": cutover.REQUIRED_CHECKS[0],
            "status": "completed",
            "conclusion": "success",
            "head_sha": "b" * 40,
        }
        with mock.patch.object(cutover, "gh_json", return_value=item):
            with self.assertRaisesRegex(cutover.CutoverError, "SHA mismatch"):
                cutover.verify_bound_required_checks("a" * 40, bound)

    def test_recovery_root_must_be_outside_repository(self) -> None:
        pre = cutover.Preflight(
            branch="fix/example",
            target_sha="a" * 40,
            target_tree="b" * 40,
            github_old_sha="c" * 40,
            gitee_old_sha="d" * 40,
            github_ruleset_id=1,
            github_ruleset={},
            gitee_protected=True,
            required_checks={},
        )
        with self.assertRaisesRegex(cutover.CutoverError, "outside"):
            cutover.create_recovery_bundle(pre, ROOT / "addons", "20260731T000000Z")

    def test_script_contains_no_customer_or_production_action(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("docker", text)
        self.assertNotIn("psql", text)
        self.assertNotIn("odoo-bin", text)
        self.assertNotIn("docker compose", text)
        self.assertIn("production_deployed", text)
        self.assertIn("False", text)

    def test_apply_confirmation_is_exact(self) -> None:
        argv = [
            str(SCRIPT),
            "--target-sha",
            "a" * 40,
            "--target-tree",
            "b" * 40,
            "--github-old-sha",
            "c" * 40,
            "--gitee-old-sha",
            "d" * 40,
            "--gitee-token-file",
            "/tmp/token",
            "--recovery-root",
            "/tmp/recovery",
            "--evidence-dir",
            "/tmp/evidence",
            "--run-id",
            "20260731T000000Z",
            "--authorization-id",
            "CONTROLLED-MAIN-CUTOVER-01",
            "--apply",
        ]
        with mock.patch.object(cutover.sys, "argv", argv):
            with self.assertRaises(SystemExit):
                cutover.parse_args()


if __name__ == "__main__":
    unittest.main(verbosity=2)

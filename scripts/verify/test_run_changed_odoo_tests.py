from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.dev import run_changed_odoo_tests as runner


class RunChangedOdooTestsTest(unittest.TestCase):
    def test_plan_excludes_modules_with_production_changes(self):
        paths = [
            "addons/smart_construction_core/tests/test_one.py",
            "addons/smart_construction_acceptance_fixture/tests/test_fixture.py",
            "addons/smart_construction_acceptance_fixture/tools/fixture_tools.py",
            "addons/smart_core/handlers/handler.py",
            "addons/smart_core/tests/test_two.py",
        ]
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(
                    runner,
                    "resolve_run",
                    return_value=("run", {"baseline_sha": "a" * 40}),
                ), \
                mock.patch.object(runner, "delta_paths", return_value=paths), \
                mock.patch.object(
                    runner.changed_odoo_tests,
                    "selection",
                    return_value=["/module:TestOne"],
                ) as selection:
            result = runner.plan(Path(directory))
        self.assertEqual(
            result,
            {
                "smart_construction_acceptance_fixture": ["/module:TestOne"],
                "smart_construction_core": ["/module:TestOne"],
            },
        )
        self.assertEqual(selection.call_count, 2)

    def test_empty_plan_and_first_failure_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(runner.run(root, {}), 2)
            failed = mock.Mock(returncode=7)
            with mock.patch.object(
                runner,
                "test_surface_fingerprint",
                return_value="b" * 64,
            ), mock.patch.object(
                runner.subprocess,
                "run",
                side_effect=[
                    mock.Mock(stdout="a" * 40 + "\n"),
                    failed,
                ],
            ) as execute:
                self.assertEqual(
                    runner.run(
                        root,
                        {
                            "smart_core": ["/smart_core:TestOne"],
                            "smart_construction_core": ["/smart_construction_core:TestTwo"],
                        },
                    ),
                    7,
                )
            self.assertEqual(execute.call_count, 2)
            env = execute.call_args.kwargs["env"]
            self.assertEqual(env["LOCAL_TEST_TEMPLATE_MODULE"], "smart_core")
            self.assertEqual(env["LOCAL_TEST_REUSE_DATABASE"], "1")

    def test_receipt_reuse_requires_exact_selection_source_and_log_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / ".runtime/test-baseline/1/odoo.log"
            log.parent.mkdir(parents=True)
            log.write_text("ok\n")
            receipt = root / ".runtime/test-baseline/1/receipt.json"
            payload = {
                "status": "passed",
                "head": "a" * 40,
                "source_fingerprint": "b" * 64,
                "test_surface_fingerprint": "b" * 64,
                "test_surface_unchanged": True,
                "source_unchanged": True,
                "profile_unchanged": True,
                "image_unchanged": True,
                "module": "smart_core",
                "tags": "/smart_core:TestOne",
                "count": 1,
                "log": ".runtime/test-baseline/1/odoo.log",
                "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            }
            receipt.write_text(json.dumps(payload))
            self.assertEqual(
                runner.reusable_receipt(
                    root,
                    "smart_core",
                    ["/smart_core:TestOne"],
                    head="a" * 40,
                    test_surface_fingerprint="b" * 64,
                ),
                ".runtime/test-baseline/1/receipt.json",
            )
            log.write_text("changed\n")
            self.assertEqual(
                runner.reusable_receipt(
                    root,
                    "smart_core",
                    ["/smart_core:TestOne"],
                    head="a" * 40,
                    test_surface_fingerprint="b" * 64,
                ),
                "",
            )


if __name__ == "__main__":
    unittest.main()

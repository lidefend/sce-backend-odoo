#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import os
import unittest
from unittest import mock

from scripts.verify import scene_company_snapshot_collect as collector


class SceneCompanySnapshotCollectProfilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline_profiles = [
            {
                "key": "baseline",
                "company_id": 1,
                "login": "admin",
                "password": "baseline-secret",
                "state_file": "artifacts/backend/baseline.json",
            }
        ]
        self.baseline = {"profiles": self.baseline_profiles}

    def test_defaults_to_baseline_profiles_when_override_is_unset(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(collector.PROFILES_JSON_ENV, None)
            profiles = collector._resolve_profiles(self.baseline)

        self.assertIs(profiles, self.baseline_profiles)

    def test_main_uses_baseline_profiles_when_override_is_unset(self) -> None:
        state_payload = {"company_id": 1, "scene_count": 1}
        output = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(collector.PROFILES_JSON_ENV, None)
            with mock.patch.object(
                collector,
                "_load_json",
                side_effect=[self.baseline, state_payload],
            ), mock.patch.object(collector, "_write"), mock.patch.object(
                collector, "_run_snapshot", return_value=(0, "guard ok")
            ) as run_snapshot, contextlib.redirect_stdout(output):
                exit_code = collector.main()

        self.assertEqual(exit_code, 0)
        run_snapshot.assert_called_once_with(
            "baseline",
            1,
            "artifacts/backend/baseline.json",
            True,
            "admin",
            "baseline-secret",
        )

    def test_json_override_takes_precedence_over_baseline_profiles(self) -> None:
        override = [
            {
                "key": "acceptance_pm",
                "company_id": 42,
                "login": "acceptance-pm",
                "password": "override-secret",
                "state_file": "artifacts/backend/acceptance-pm.json",
            }
        ]
        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: json.dumps(override)},
            clear=False,
        ):
            profiles = collector._resolve_profiles(self.baseline)

        self.assertEqual(profiles, override)
        self.assertNotEqual(profiles, self.baseline_profiles)

    def test_invalid_json_override_is_rejected_without_echoing_value(self) -> None:
        secret_input = '[{"password":"do-not-print"}'
        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: secret_input},
            clear=False,
        ):
            with self.assertRaisesRegex(ValueError, "must be a valid JSON array") as raised:
                collector._resolve_profiles(self.baseline)

        self.assertNotIn("do-not-print", str(raised.exception))

    def test_main_rejects_invalid_override_without_printing_raw_json(self) -> None:
        raw_override = '[{"password":"raw-json-secret"}'
        output = io.StringIO()
        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: raw_override},
            clear=False,
        ), mock.patch.object(collector, "_load_json", return_value=self.baseline), contextlib.redirect_stdout(
            output
        ):
            exit_code = collector.main()

        self.assertEqual(exit_code, 1)
        self.assertNotIn(raw_override, output.getvalue())
        self.assertNotIn("raw-json-secret", output.getvalue())

    def test_non_array_json_override_is_rejected(self) -> None:
        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: '{"key":"not-an-array"}'},
            clear=False,
        ):
            with self.assertRaisesRegex(ValueError, "must be a JSON array"):
                collector._resolve_profiles(self.baseline)

    def test_empty_array_override_is_rejected(self) -> None:
        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: "[]"},
            clear=False,
        ):
            with self.assertRaisesRegex(ValueError, f"{collector.PROFILES_JSON_ENV} is empty"):
                collector._resolve_profiles(self.baseline)

    def test_override_profiles_reuse_required_field_validation_without_printing_password(self) -> None:
        override = [
            {
                "company_id": 42,
                "password": "profile-secret",
                "state_file": "artifacts/backend/acceptance-pm.json",
            }
        ]
        output = io.StringIO()
        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: json.dumps(override)},
            clear=False,
        ), mock.patch.object(collector, "_load_json", return_value=self.baseline), mock.patch.object(
            collector, "_write"
        ), mock.patch.object(collector, "_run_snapshot") as run_snapshot, contextlib.redirect_stdout(
            output
        ):
            exit_code = collector.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("profile key is required", output.getvalue())
        self.assertNotIn("profile-secret", output.getvalue())
        run_snapshot.assert_not_called()

    def test_override_profile_without_state_file_fails_closed(self) -> None:
        override = [{"key": "acceptance_pm", "password": "profile-secret"}]
        output = io.StringIO()
        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: json.dumps(override)},
            clear=False,
        ), mock.patch.object(collector, "_load_json", return_value=self.baseline), mock.patch.object(
            collector, "_write"
        ), mock.patch.object(collector, "_run_snapshot") as run_snapshot, contextlib.redirect_stdout(
            output
        ):
            exit_code = collector.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("acceptance_pm: state_file is required", output.getvalue())
        self.assertNotIn("profile-secret", output.getvalue())
        run_snapshot.assert_not_called()

    def test_child_guard_output_is_redacted_before_reports_are_written(self) -> None:
        override = [
            {
                "key": "acceptance_pm",
                "company_id": 42,
                "login": "acceptance-pm",
                "password": "profile-secret",
                "state_file": "artifacts/backend/acceptance-pm.json",
            }
        ]
        state_payload = {"company_id": 42, "scene_count": 1}
        writes: list[str] = []

        def capture_write(_path: object, content: str) -> None:
            writes.append(content)

        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: json.dumps(override)},
            clear=False,
        ), mock.patch.object(
            collector,
            "_load_json",
            side_effect=[self.baseline, state_payload],
        ), mock.patch.object(collector, "_write", side_effect=capture_write), mock.patch.object(
            collector,
            "_run_snapshot",
            return_value=(0, "stdout profile-secret\nstderr profile-secret"),
        ):
            exit_code = collector.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(writes), 2)
        rendered_reports = "\n".join(writes)
        self.assertNotIn("profile-secret", rendered_reports)
        self.assertIn("stdout [REDACTED]", rendered_reports)

    def test_child_guard_output_redacts_passwords_from_all_profiles(self) -> None:
        override = [
            {
                "key": "acceptance_pm",
                "company_id": 42,
                "password": "first-secret",
                "state_file": "artifacts/backend/acceptance-pm.json",
            },
            {
                "key": "acceptance_finance",
                "company_id": 43,
                "password": "second-secret",
                "state_file": "artifacts/backend/acceptance-finance.json",
            },
        ]
        state_payloads = [
            {"company_id": 42, "scene_count": 1},
            {"company_id": 43, "scene_count": 1},
        ]
        writes: list[str] = []

        def capture_write(_path: object, content: str) -> None:
            writes.append(content)

        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: json.dumps(override)},
            clear=False,
        ), mock.patch.object(
            collector,
            "_load_json",
            side_effect=[self.baseline, *state_payloads],
        ), mock.patch.object(collector, "_write", side_effect=capture_write), mock.patch.object(
            collector,
            "_run_snapshot",
            side_effect=[
                (0, "first output first-secret and second-secret"),
                (0, "second output second-secret and first-secret"),
            ],
        ):
            exit_code = collector.main()

        self.assertEqual(exit_code, 0)
        rendered_reports = "\n".join(writes)
        self.assertNotIn("first-secret", rendered_reports)
        self.assertNotIn("second-secret", rendered_reports)
        self.assertGreaterEqual(rendered_reports.count("[REDACTED]"), 4)

    def test_snapshot_child_environment_excludes_profiles_override(self) -> None:
        process = mock.Mock(returncode=0, stdout="guard ok", stderr="")
        with mock.patch.dict(
            os.environ,
            {collector.PROFILES_JSON_ENV: '[{"password":"must-not-reach-child"}]'},
            clear=False,
        ), mock.patch.object(collector.subprocess, "run", return_value=process) as run:
            collector._run_snapshot(
                "acceptance_pm",
                42,
                "artifacts/backend/acceptance-pm.json",
                True,
                "acceptance-pm",
                "profile-secret",
            )

        child_env = run.call_args.kwargs["env"]
        self.assertNotIn(collector.PROFILES_JSON_ENV, child_env)
        self.assertEqual(child_env["E2E_PASSWORD"], "profile-secret")

    def test_empty_password_does_not_modify_child_guard_output(self) -> None:
        self.assertEqual(collector._redact_password("guard output", ""), "guard output")


if __name__ == "__main__":
    unittest.main(verbosity=2)

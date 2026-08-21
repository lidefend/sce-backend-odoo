#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import os
import unittest
from unittest import mock

from scripts.verify import scene_company_access_preflight_guard as guard


class SceneCompanyAccessPreflightProfilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline_profiles = [
            {
                "key": "primary",
                "target_company_id": 1,
                "state_file": "artifacts/backend/primary.json",
            }
        ]
        self.baseline = {
            "profiles": self.baseline_profiles,
            "min_reachable_count_block": 1,
            "min_reachable_count_target": 2,
            "report_json": "artifacts/backend/custom-report.json",
            "report_md": "artifacts/backend/custom-report.md",
        }

    def test_unset_override_keeps_baseline_profiles(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(guard.PROFILES_JSON_ENV, None)
            profiles = guard._resolve_profiles(self.baseline)
        self.assertIs(profiles, self.baseline_profiles)

    def test_override_replaces_only_profiles(self) -> None:
        override = [
            {
                "key": "primary",
                "target_company_id": 2,
                "state_file": "artifacts/backend/primary.json",
            },
            {
                "key": "secondary",
                "target_company_id": 3,
                "state_file": "artifacts/backend/secondary.json",
            },
        ]
        with mock.patch.dict(os.environ, {guard.PROFILES_JSON_ENV: json.dumps(override)}, clear=False):
            profiles = guard._resolve_profiles(self.baseline)
        self.assertEqual(profiles, override)
        self.assertEqual(self.baseline["min_reachable_count_block"], 1)
        self.assertEqual(self.baseline["min_reachable_count_target"], 2)
        self.assertEqual(self.baseline["report_json"], "artifacts/backend/custom-report.json")
        self.assertEqual(self.baseline["report_md"], "artifacts/backend/custom-report.md")

    def test_invalid_json_fails_without_echoing_raw_value(self) -> None:
        raw_value = '[{"sensitive":"do-not-print"}'
        with mock.patch.dict(os.environ, {guard.PROFILES_JSON_ENV: raw_value}, clear=False):
            with self.assertRaisesRegex(ValueError, "must be a valid JSON array") as raised:
                guard._resolve_profiles(self.baseline)
        self.assertNotIn(raw_value, str(raised.exception))
        self.assertNotIn("do-not-print", str(raised.exception))

    def test_non_array_and_empty_overrides_fail_closed(self) -> None:
        for raw_value, expected in (("{}", "must be a JSON array"), ("[]", "is empty")):
            with self.subTest(raw_value=raw_value):
                with mock.patch.dict(os.environ, {guard.PROFILES_JSON_ENV: raw_value}, clear=False):
                    with self.assertRaisesRegex(ValueError, expected):
                        guard._resolve_profiles(self.baseline)

    def test_main_uses_override_targets_and_baseline_policy(self) -> None:
        override = [
            {
                "key": "primary",
                "target_company_id": 2,
                "state_file": "artifacts/backend/primary.json",
            },
            {
                "key": "secondary",
                "target_company_id": 3,
                "state_file": "artifacts/backend/secondary.json",
            },
        ]
        writes: list[tuple[object, str]] = []
        states = [
            self.baseline,
            {"company_id": 2, "allowed_company_ids": [2]},
            {"company_id": 3, "allowed_company_ids": [3]},
        ]
        with mock.patch.dict(os.environ, {guard.PROFILES_JSON_ENV: json.dumps(override)}, clear=False), mock.patch.object(
            guard, "_load_json", side_effect=states
        ), mock.patch.object(guard, "_write", side_effect=lambda path, content: writes.append((path, content))):
            result = guard.main()
        self.assertEqual(result, 0)
        self.assertEqual([str(path) for path, _ in writes], [
            str(guard.ROOT / "artifacts/backend/custom-report.json"),
            str(guard.ROOT / "artifacts/backend/custom-report.md"),
        ])
        report = json.loads(writes[0][1])
        self.assertEqual(report["summary"]["reachable_count"], 2)
        self.assertEqual(report["summary"]["min_reachable_count_block"], 1)
        self.assertEqual(report["summary"]["min_reachable_count_target"], 2)
        self.assertEqual([row["target_company_id"] for row in report["profiles"]], [2, 3])

    def test_invalid_profile_fields_fail_closed(self) -> None:
        override = [{"key": "primary", "target_company_id": 0}]
        output = io.StringIO()
        with mock.patch.dict(os.environ, {guard.PROFILES_JSON_ENV: json.dumps(override)}, clear=False), mock.patch.object(
            guard, "_load_json", return_value=self.baseline
        ), mock.patch.object(guard, "_write"), contextlib.redirect_stdout(output):
            result = guard.main()
        self.assertEqual(result, 1)
        self.assertIn("invalid profile config", output.getvalue())

    def test_derived_target_uses_requested_non_primary_company(self) -> None:
        override = [
            {
                "key": "secondary",
                "target_company_id": 0,
                "derive_target_from_state": True,
                "exclude_company_ids": [1],
                "state_file": "artifacts/backend/secondary.json",
            }
        ]
        baseline = {**self.baseline, "min_reachable_count_target": 1}
        writes: list[tuple[object, str]] = []
        with mock.patch.dict(
            os.environ,
            {guard.PROFILES_JSON_ENV: json.dumps(override)},
            clear=False,
        ), mock.patch.object(
            guard,
            "_load_json",
            side_effect=[
                baseline,
                {
                    "company_id": 5,
                    "allowed_company_ids": [1, 5],
                    "login_company_id_requested": 5,
                },
            ],
        ), mock.patch.object(
            guard,
            "_write",
            side_effect=lambda path, content: writes.append((path, content)),
        ):
            result = guard.main()

        self.assertEqual(result, 0)
        report = json.loads(writes[0][1])
        self.assertEqual(report["profiles"][0]["target_company_id"], 5)
        self.assertTrue(report["profiles"][0]["reachable"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

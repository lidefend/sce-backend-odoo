#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV_LOADER = ROOT / "scripts/common/env.sh"


class CommonEnvironmentExplicitPathTest(unittest.TestCase):
    @staticmethod
    def _write_environment_file(path: Path) -> None:
        path.write_text(
            "ENV_FILE=.env.dev\n"
            "DB_USER=loaded-user\n"
            "DB_PASSWORD=loaded-password\n"
            "ADMIN_PASSWD=loaded-admin\n"
            "JWT_SECRET=loaded-jwt\n"
            "ODOO_DBFILTER=^loaded$\n",
            encoding="utf-8",
        )

    def test_explicit_environment_file_survives_values_loaded_from_that_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            environment_file = Path(temporary_directory) / "acceptance.env"
            self._write_environment_file(environment_file)
            environment = {
                **os.environ,
                "ROOT_DIR": str(ROOT),
                "ENV_FILE": str(environment_file),
                "COMPOSE_PROJECT_NAME": "common-env-explicit-path-test",
                "PROJECT": "common-env-explicit-path-test",
                "DB_NAME": "common_env_explicit_path_test",
            }
            result = subprocess.run(
                ["bash", "-c", f'source "{ENV_LOADER}"; printf "%s" "$ENV_FILE"'],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.stdout, str(environment_file))

    def test_make_runner_keeps_explicit_environment_file_absolute(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            environment_file = Path(temporary_directory) / "acceptance.env"
            self._write_environment_file(environment_file)
            result = subprocess.run(
                [
                    "make",
                    "-n",
                    "test",
                    f"ENV_FILE={environment_file}",
                    "COMPOSE_PROJECT_NAME=common-env-explicit-path-test",
                    "PROJECT=common-env-explicit-path-test",
                    "DB_NAME=common_env_explicit_path_test",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn(f'ENV_FILE="{environment_file}"', result.stdout)


if __name__ == "__main__":
    unittest.main()

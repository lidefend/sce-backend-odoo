from __future__ import annotations

import os
import subprocess
import textwrap
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMMON_PATH = ROOT / "scripts/dev/frontend_acceptance_carrier_common.sh"
COMMON = COMMON_PATH.read_text(encoding="utf-8")


def _write_fake_resolver(fake_root: Path, base_env: Path) -> None:
    resolver = fake_root / "scripts/dev/frontend_acceptance_runtime_profile.py"
    resolver.parent.mkdir(parents=True, exist_ok=True)
    resolver.write_text(
        textwrap.dedent(
            f"""
            import sys
            base_env = {str(base_env)!r}
            values = {{
                "SC_ACCEPTANCE_RUNTIME_PROFILE": "candidate",
                "SC_ACCEPTANCE_BASE_ENV_FILE": base_env,
                "COMPOSE_PROJECT_NAME": "sc-fe-candidate-770",
                "PROJECT": "sc-fe-candidate-770",
                "SC_ACCEPTANCE_CREDENTIAL_CONTAINER": "sc-fe-candidate-770-odoo-1",
                "DB_NAME": "sc_frontend_acceptance_candidate",
                "DB": "sc_frontend_acceptance_candidate",
                "ODOO_DB": "sc_frontend_acceptance_candidate",
                "ODOO_DBFILTER": "^sc_frontend_acceptance_candidate$",
                "DB_DATA": "sc_fe_candidate_770_db",
                "REDIS_DATA": "sc_fe_candidate_770_redis",
                "ODOO_DATA": "sc_fe_candidate_770_odoo",
                "SC_ENVIRONMENT": "acceptance",
                "SC_ALLOW_DEMO_DATA": "1",
            }}
            if "--get" in sys.argv:
                print(values.get(sys.argv[-1], ""))
            else:
                for key, value in values.items():
                    print(f"{{key}}={{value}}")
            """
        ),
        encoding="utf-8",
    )


def _write_fake_env(base_env: Path) -> None:
    base_env.parent.mkdir(parents=True, exist_ok=True)
    base_env.write_text(
        textwrap.dedent(
            """
            ENV=dev
            ENV_FILE=.env.dev
            DB_USER=odoo
            DB_PASSWORD=odoo
            ADMIN_PASSWD=admin
            JWT_SECRET=jwt
            """
        ).lstrip(),
        encoding="utf-8",
    )


class CarrierResolveProfileIdentityTests(unittest.TestCase):
    def test_env_file_reanchored_to_absolute_base_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_root = Path(tmp)
            base_env = fake_root / "primary/.env.dev"
            _write_fake_resolver(fake_root, base_env)
            _write_fake_env(base_env)
            script = textwrap.dedent(
                f"""
                set -euo pipefail
                export ROOT_DIR={str(fake_root)!r}
                export SC_ACCEPTANCE_RUNTIME_PROFILE=candidate
                source {str(COMMON_PATH)!r}
                carrier_resolve_profile_identity
                echo "resolved_ENV=${{ENV}}"
                echo "resolved_ENV_FILE=${{ENV_FILE}}"
                """
            )
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=fake_root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("resolved_ENV=dev", result.stdout)
            self.assertIn(f"resolved_ENV_FILE={base_env}", result.stdout)
            self.assertNotIn("resolved_ENV_FILE=.env.dev", result.stdout)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "local_platform_control",
    ROOT / "scripts/dev/local_platform_control.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class LocalPlatformControlTest(unittest.TestCase):
    def test_declaration_is_an_independent_platform_control_unit(self):
        declaration = MODULE.load_declaration()
        self.assertEqual(declaration["project"], "sc-local-platform")
        self.assertEqual(declaration["database"], "sc_platform_control")
        self.assertEqual(declaration["database_role"], "sc_platform_control_app")
        self.assertEqual(
            declaration["maintenance_role"],
            "sc_platform_control_maintenance",
        )
        self.assertEqual(declaration["module"], "smart_core")
        self.assertNotEqual(
            declaration["database_role"],
            declaration["maintenance_role"],
        )

    def test_prepare_env_is_private_and_preserves_exact_identity(self):
        declaration = MODULE.load_declaration()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / ".env.dev"
            target = root / ".env.local.platform"
            source.write_text(
                "SC_ENTRY_SHARED_SECRET=entry-secret\n"
                "SC_ENTRY_ROUTE_VERSION=v1\n",
                encoding="utf-8",
            )
            prepared = MODULE.prepare_env(
                declaration=declaration,
                source_env=source,
                target_env=target,
            )
            self.assertEqual(prepared, target)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            values = MODULE.parse_env(target)
            self.assertEqual(values["COMPOSE_PROJECT_NAME"], "sc-local-platform")
            self.assertEqual(values["DB_NAME"], "sc_platform_control")
            self.assertEqual(values["DB_USER"], "sc_platform_control_app")
            self.assertEqual(
                values["DB_MAINTENANCE_USER"],
                "sc_platform_control_maintenance",
            )
            self.assertEqual(values["ODOO_DBFILTER"], "^sc_platform_control$")
            self.assertEqual(values["SC_ALLOW_DEMO_DATA"], "0")
            self.assertEqual(values["SC_ENTRY_SHARED_SECRET"], "entry-secret")
            first = target.read_text(encoding="utf-8")
            MODULE.prepare_env(
                declaration=declaration,
                source_env=source,
                target_env=target,
            )
            self.assertEqual(target.read_text(encoding="utf-8"), first)

    def test_prepare_env_rebinds_existing_identity_to_current_source(self):
        declaration = MODULE.load_declaration()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / ".env.dev"
            target = root / ".env.local.platform"
            source.write_text(
                "SC_ENTRY_SHARED_SECRET=entry-secret\n"
                "SC_ENTRY_ROUTE_VERSION=v1\n",
                encoding="utf-8",
            )
            target.write_text(
                "COMPOSE_PROJECT_NAME=sc-local-platform\n"
                "DB_NAME=sc_platform_control\n"
                "DB_USER=sc_platform_control_app\n"
                "DB_MAINTENANCE_USER=sc_platform_control_maintenance\n"
                "ODOO_DBFILTER=^sc_platform_control$\n"
                "DB_PASSWORD=preserved-secret\n"
                "SC_PRODUCT_ROOT=/stale/worktree\n"
                "SC_SOURCE_REVISION=" + "a" * 40 + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                MODULE, "ROOT", root
            ), mock.patch.object(
                MODULE, "run", return_value=mock.Mock(stdout="b" * 40 + "\n")
            ):
                MODULE.prepare_env(
                    declaration=declaration,
                    source_env=source,
                    target_env=target,
                )
            values = MODULE.parse_env(target)
            self.assertEqual(values["SC_PRODUCT_ROOT"], str(root))
            self.assertEqual(values["SC_SOURCE_REVISION"], "b" * 40)
            self.assertEqual(values["SC_DEPLOY_ENV"], "local")
            self.assertEqual(
                values["FRONTEND_DIST_DIR"],
                str(root / "frontend/apps/web/dist-clean"),
            )
            self.assertEqual(values["DB_PASSWORD"], "preserved-secret")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_upgrade_module_uses_odoo_update_not_install(self):
        declaration = MODULE.load_declaration()
        env_file = Path("/tmp/local-platform-test.env")
        with mock.patch.object(
            MODULE,
            "parse_env",
            return_value={
                "DB_USER": declaration["database_role"],
                "DB_PASSWORD": "secret",
            },
        ), mock.patch.object(MODULE, "render_config") as render_config, mock.patch.object(
            MODULE, "compose"
        ) as compose:
            MODULE.upgrade_module(declaration, env_file)
        render_config.assert_called_once_with(declaration, env_file)
        command = compose.call_args.args[2:]
        self.assertIn("-u", command)
        self.assertNotIn("-i", command)
        self.assertEqual(command[-1], "--stop-after-init")


if __name__ == "__main__":
    unittest.main()

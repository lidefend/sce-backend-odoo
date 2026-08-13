#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("production_acceptance_clone_runtime.py")
RELEASE_MAKE = SCRIPT.parents[2] / "make/release.mk"
SPEC = importlib.util.spec_from_file_location("production_acceptance_clone_runtime", SCRIPT)
assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class ProductionAcceptanceCloneRuntimeTests(unittest.TestCase):
    def test_accepts_generic_tenant_module_identity(self) -> None:
        RUNTIME.validate_identity(
            "sc_restore_20260808t102000z_4d7e91a2",
            "1" * 40,
            "sce_customer_sample",
            "sha256:" + "2" * 64,
            18095,
        )

    def test_rejects_module_path_escape(self) -> None:
        with self.assertRaisesRegex(RUNTIME.CloneRuntimeError, "tenant module"):
            RUNTIME.validate_identity(
                "sc_restore_20260808t102000z_4d7e91a2",
                "1" * 40,
                "../private_addon",
                "sha256:" + "2" * 64,
                18095,
            )

    def test_rejects_non_loopback_acceptance_port_range(self) -> None:
        with self.assertRaisesRegex(RUNTIME.CloneRuntimeError, "loopback port"):
            RUNTIME.validate_identity(
                "sc_restore_20260808t102000z_4d7e91a2",
                "1" * 40,
                "sce_customer_sample",
                "sha256:" + "2" * 64,
                8069,
            )

    def test_database_snapshot_uses_fixed_protected_counts(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="115|923|1031") as runner:
            result = RUNTIME.database_snapshot("restore_db", "r10e_restore")
        self.assertEqual(
            result,
            {"res_users": 115, "project_project": 923, "ir_attachment": 1031},
        )
        command = runner.call_args.args[0]
        self.assertEqual(command[:3], ["docker", "exec", "restore_db"])
        self.assertIn("res_users", command[-1])
        self.assertIn("project_project", command[-1])
        self.assertIn("ir_attachment", command[-1])

    def test_module_state_requires_installed_and_no_pending(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="2|0"):
            result = RUNTIME.module_state(
                "restore_db", "r10e_restore", ("smart_core", "sce_customer_sample")
            )
        self.assertEqual(result, {"installed": 2, "pending": 0})

    def test_restore_rebinds_single_database_release_snapshot_authority(self) -> None:
        database = "r10e_sc_restore_20260810t093000z_352c22d4"
        with mock.patch.object(RUNTIME, "run", return_value="1|0|1|1") as runner:
            self.assertTrue(
                RUNTIME.rebind_platform_release_database("restore_db", database)
            )
        command = runner.call_args.args[0]
        self.assertEqual(command[:3], ["docker", "exec", "restore_db"])
        self.assertNotIn(f"target_db={database}", command)
        self.assertIn(f"'{database}'", command[-1])
        self.assertIn("smart_core.platform_release_db", command[-1])

    def test_restore_release_snapshot_rebind_is_idempotent(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="1|1|0|1"):
            self.assertFalse(
                RUNTIME.rebind_platform_release_database(
                    "restore_db",
                    "r10e_sc_restore_20260810t093000z_352c22d4",
                )
            )

    def test_restore_release_snapshot_rebind_fails_closed(self) -> None:
        for observed in ("0|0|0|0", "2|0|2|1"):
            with self.subTest(observed=observed):
                with mock.patch.object(RUNTIME, "run", return_value=observed):
                    with self.assertRaisesRegex(
                        RUNTIME.CloneRuntimeError, "was not rebound"
                    ):
                        RUNTIME.rebind_platform_release_database(
                            "restore_db",
                            "r10e_sc_restore_20260810t093000z_352c22d4",
                        )
        with self.assertRaisesRegex(
            RUNTIME.CloneRuntimeError, "database identity is invalid"
        ):
            RUNTIME.rebind_platform_release_database("restore_db", "sc_production")

    def test_uninstalled_tenant_module_is_explicitly_installed(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="uninstalled") as runner:
            operation = RUNTIME.tenant_module_operation(
                "restore_db", "r10e_restore", "sce_customer_sample"
            )
        self.assertEqual(operation, "install")
        self.assertIn("WHERE name = 'sce_customer_sample'", runner.call_args.args[0][-1])

    def test_new_locked_tenant_module_is_explicitly_installed(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value=""):
            operation = RUNTIME.tenant_module_operation(
                "restore_db", "r10e_restore", "sce_customer_sample"
            )
        self.assertEqual(operation, "install")

    def test_installed_tenant_module_is_upgraded(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="installed"):
            operation = RUNTIME.tenant_module_operation(
                "restore_db", "r10e_restore", "sce_customer_sample"
            )
        self.assertEqual(operation, "upgrade")

    def test_pending_tenant_module_state_fails_closed(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="to install"):
            with self.assertRaisesRegex(RUNTIME.CloneRuntimeError, "not eligible"):
                RUNTIME.tenant_module_operation(
                    "restore_db", "r10e_restore", "sce_customer_sample"
                )

    def test_runtime_has_one_authoritative_product_module_set(self) -> None:
        modules = RUNTIME.product_modules()
        self.assertIn("smart_construction_core", modules)
        self.assertIn("smart_construction_bundle", modules)
        self.assertIn("smart_construction_seed", modules)
        self.assertEqual(len(modules), len(set(modules)))

    def test_odoo_runtime_containers_have_acceptance_identity_label(self) -> None:
        command = RUNTIME.odoo_container_args(
            name="sc_restore_20260808t102000z_4d7e91a2_acceptance_upgrade",
            network="sc_restore_20260808t102000z_4d7e91a2_internal",
            filestore="sc_restore_20260808t102000z_4d7e91a2_filestore",
            tenant_root=Path("/opt/sce/tenant-addons/acceptance/" + "1" * 40),
            config=Path("/tmp/acceptance/odoo.conf"),
            image="sha256:" + "2" * 64,
        )
        self.assertIn("sc.production-acceptance-clone=true", command)

    def test_filestore_mount_matches_explicit_odoo_data_dir(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('f"{filestore}:/var/lib/odoo/filestore"', source)
        self.assertIn('"data_dir = /var/lib/odoo\\n"', source)

    def test_platform_snapshot_refresh_uses_locked_policy_and_image_version(self) -> None:
        command = RUNTIME.platform_snapshot_container_args(
            name="sc_restore_20260808t102000z_4d7e91a2_acceptance_snapshot",
            network="sc_restore_20260808t102000z_4d7e91a2_internal",
            filestore="sc_restore_20260808t102000z_4d7e91a2_filestore",
            tenant_root=Path("/opt/sce/tenant-addons/acceptance/" + "1" * 40),
            config=Path("/tmp/acceptance/odoo.conf"),
            image="sha256:" + "2" * 64,
            database="r10e_sc_restore_20260808t102000z_4d7e91a2",
            version="1.0.0-rc.17",
        )
        self.assertEqual(command[2], "--rm")
        self.assertIn(
            "PLATFORM_RELEASE_PRODUCT_KEY=construction.standard",
            command,
        )
        self.assertIn("PLATFORM_RELEASE_VERSION=1.0.0-rc.17", command)
        self.assertIn("PLATFORM_RELEASE_DB=r10e_sc_restore_20260808t102000z_4d7e91a2", command)
        self.assertIn("initialize_colocated_platform_snapshot.py", command[-1])

    def test_platform_snapshot_version_comes_from_immutable_image_label(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="1.0.0-rc.17") as runner:
            self.assertEqual(RUNTIME.image_release_version("sha256:" + "2" * 64), "1.0.0-rc.17")
        self.assertIn("org.opencontainers.image.version", runner.call_args.args[0][-1])

    def test_platform_database_rebind_precedes_module_upgrade(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        activate_source = source[source.index("def activate(") :]
        self.assertLess(
            activate_source.index("rebind_platform_release_database("),
            activate_source.index("upgrade_args = odoo_container_args("),
        )

    def test_retry_removes_stopped_upgrade_from_exact_isolated_network(self) -> None:
        network = "sc_restore_20260808t102000z_4d7e91a2_internal"
        with mock.patch.object(
            RUNTIME,
            "run",
            side_effect=[f"exited|false|{network}|", ""],
        ) as runner:
            self.assertTrue(
                RUNTIME.remove_verified_failed_upgrade(
                    "sc_restore_20260808t102000z_4d7e91a2", network
                )
            )
        self.assertEqual(
            runner.call_args_list[-1].args[0],
            ["docker", "rm", "sc_restore_20260808t102000z_4d7e91a2_acceptance_upgrade"],
        )

    def test_retry_rejects_running_upgrade_container(self) -> None:
        network = "sc_restore_20260808t102000z_4d7e91a2_internal"
        with mock.patch.object(
            RUNTIME,
            "run",
            return_value=f"running|true|{network}|true",
        ):
            with self.assertRaisesRegex(RUNTIME.CloneRuntimeError, "not safely stopped"):
                RUNTIME.remove_verified_failed_upgrade(
                    "sc_restore_20260808t102000z_4d7e91a2", network
                )

    def test_retry_rejects_upgrade_container_outside_restore_network(self) -> None:
        with mock.patch.object(
            RUNTIME,
            "run",
            return_value="exited|false|foreign_network|true",
        ):
            with self.assertRaisesRegex(RUNTIME.CloneRuntimeError, "identity differs"):
                RUNTIME.remove_verified_failed_upgrade(
                    "sc_restore_20260808t102000z_4d7e91a2",
                    "sc_restore_20260808t102000z_4d7e91a2_internal",
                )

    def test_retry_admits_only_tool_generated_runtime_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = Path(temporary) / "acceptance-runtime"
            runtime_root.mkdir()
            (runtime_root / "odoo.conf").write_text("[options]\n", encoding="utf-8")
            RUNTIME.ensure_retryable_runtime_root(runtime_root)
            self.assertEqual(runtime_root.stat().st_mode & 0o777, 0o700)

    def test_retry_creates_missing_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = Path(temporary) / "acceptance-runtime"
            RUNTIME.ensure_retryable_runtime_root(runtime_root)
            self.assertTrue(runtime_root.is_dir())
            self.assertEqual(runtime_root.stat().st_mode & 0o777, 0o700)

    def test_retry_rejects_unmanaged_runtime_root_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = Path(temporary) / "acceptance-runtime"
            runtime_root.mkdir()
            (runtime_root / "foreign.txt").write_text("foreign", encoding="utf-8")
            with self.assertRaisesRegex(RUNTIME.CloneRuntimeError, "unmanaged files"):
                RUNTIME.ensure_retryable_runtime_root(runtime_root)

    def test_existing_tenant_package_still_consumes_archive_stream(self) -> None:
        source = RELEASE_MAKE.read_text(encoding="utf-8")
        tenant_target = source.split(
            "production.acceptance.tenant.remote_install:", 1
        )[1].split("production.acceptance.clone.remote_activate:", 1)[0]
        self.assertIn("cat >/dev/null; exit 0", tenant_target)

    def test_existing_tool_package_still_consumes_archive_stream(self) -> None:
        source = RELEASE_MAKE.read_text(encoding="utf-8")
        tool_target = source.split(
            "production.acceptance.backup.remote_install:", 1
        )[1].split("production.acceptance.backup.remote_sync:", 1)[0]
        self.assertIn("tar -tf - >/dev/null", tool_target)

    def test_clone_runtime_includes_formal_external_dependencies(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("/mnt/addons_external/oca_server_ux", source)

    def test_health_falls_back_to_private_internal_address(self) -> None:
        with mock.patch.object(RUNTIME, "url_ready", side_effect=[False, True]), mock.patch.object(
            RUNTIME, "run", return_value="172.27.0.3"
        ):
            url, loopback_bound = RUNTIME.container_endpoint(
                "acceptance", 8069, "/web/health", loopback_port=18098
            )
        self.assertEqual(url, "http://172.27.0.3:8069/web/health")
        self.assertFalse(loopback_bound)

    def test_health_rejects_non_private_fallback(self) -> None:
        with mock.patch.object(RUNTIME, "url_ready", return_value=False), mock.patch.object(
            RUNTIME, "run", return_value="8.8.8.8"
        ):
            self.assertEqual(
                RUNTIME.container_endpoint(
                    "acceptance", 8069, "/web/health", loopback_port=18098
                ),
                ("", False),
            )

    def test_url_readiness_treats_connection_reset_as_not_ready(self) -> None:
        with mock.patch.object(
            RUNTIME.urllib.request,
            "urlopen",
            side_effect=ConnectionResetError(104, "reset"),
        ):
            self.assertFalse(RUNTIME.url_ready("http://127.0.0.1:18081/"))

    def test_public_frontend_binds_only_the_approved_port(self) -> None:
        with mock.patch.object(RUNTIME, "run") as runner:
            RUNTIME.start_frontend(
                web_container="acceptance_web",
                network="acceptance_internal",
                image="sha256:" + "2" * 64,
                database="r10e_acceptance",
                host="0.0.0.0",
                port=18081,
                ingress_network="acceptance_public_ingress",
            )
        commands = [call.args[0] for call in runner.call_args_list]
        command = commands[0]
        self.assertEqual(command[:2], ["docker", "create"])
        self.assertIn("0.0.0.0:18081:80", command)
        self.assertIn("sc.production-acceptance-clone=true", command)
        self.assertEqual(command[command.index("--user") + 1], "root")
        self.assertIn(
            ["docker", "network", "connect", "acceptance_internal", "acceptance_web"],
            commands,
        )
        self.assertEqual(commands[-1], ["docker", "start", "acceptance_web"])

    def test_public_ingress_disables_ip_masquerade(self) -> None:
        with mock.patch.object(RUNTIME, "run", side_effect=["", "network-id"]) as runner:
            network = RUNTIME.ensure_public_ingress_network(
                "sc_restore_20260808t102000z_4d7e91a2"
            )
        self.assertEqual(network, "sc_restore_20260808t102000z_4d7e91a2_public_ingress")
        create = runner.call_args_list[1].args[0]
        self.assertIn("com.docker.network.bridge.enable_ip_masquerade=false", create)
        self.assertIn("sc.production-acceptance-clone=true", create)

    def test_replace_removes_only_verified_isolated_runtime(self) -> None:
        network = "sc_restore_20260808t102000z_4d7e91a2_net"
        with mock.patch.object(
            RUNTIME,
            "run",
            side_effect=[
                f"true||{network}",
                "true||sc_restore_20260808t102000z_4d7e91a2_public_ingress",
                "",
                "",
            ],
        ) as runner:
            self.assertTrue(
                RUNTIME.remove_verified_runtime(
                    "sc_restore_20260808t102000z_4d7e91a2", network
                )
            )
        commands = [call.args[0] for call in runner.call_args_list]
        self.assertEqual(
            commands[-2:],
            [
                ["docker", "rm", "-f", "sc_restore_20260808t102000z_4d7e91a2_acceptance_web"],
                ["docker", "rm", "-f", "sc_restore_20260808t102000z_4d7e91a2_acceptance_odoo"],
            ],
        )

    def test_replace_accepts_legacy_label_only_on_exact_isolated_network(self) -> None:
        network = "sc_restore_20260808t102000z_4d7e91a2_net"
        with mock.patch.object(
            RUNTIME,
            "run",
            side_effect=[
                f"|true|{network}",
                f"|true|{network}",
                "",
                "",
            ],
        ):
            self.assertTrue(
                RUNTIME.remove_verified_runtime(
                    "sc_restore_20260808t102000z_4d7e91a2", network
                )
            )

    def test_replace_rejects_unlabelled_backend(self) -> None:
        with mock.patch.object(RUNTIME, "run", return_value="||foreign_network"):
            with self.assertRaisesRegex(RUNTIME.CloneRuntimeError, "backend identity"):
                RUNTIME.remove_verified_runtime(
                    "sc_restore_20260808t102000z_4d7e91a2",
                    "sc_restore_20260808t102000z_4d7e91a2_net",
                )


if __name__ == "__main__":
    unittest.main()

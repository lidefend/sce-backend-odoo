"""Bounded identity/refusal tests; physical outcomes require the governed lane."""
import ast
import copy
import json
from pathlib import Path
import unittest
import tempfile
import types
from unittest.mock import MagicMock
from unittest.mock import patch

from scripts.ops import platform_database_rehearsal as lane


def function(name, **bindings):
    path = lane.ROOT / "scripts/ops/platform_database_rehearsal_runtime.py"
    tree = ast.parse(path.read_text())
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), bindings)
    return bindings[name]


class TestRehearsalIdentity(unittest.TestCase):
    def setUp(self):
        self.declared = lane.declaration()
        self.config = {
            "name": self.declared["project"],
            "services": {name: {"image": "sha256:pinned", "volumes": []}
                         for name in ("db", "control", "target_namespace")},
            "volumes": {str(i): {"name": name} for i, name in enumerate(self.declared["volumes"])},
            "networks": {"default": {"internal": True}},
        }

    def test_fixed_isolated_configuration_accepted(self):
        lane.validate_configuration(self.config, self.declared)

    def test_other_project_refused(self):
        self.config["name"] = "sc-local-dev"
        with self.assertRaisesRegex(ValueError, "IDENTITY"):
            lane.validate_configuration(self.config, self.declared)

    def test_existing_runtime_volume_refused(self):
        self.config["volumes"]["0"]["name"] = "sc_local_dev_db_data"
        with self.assertRaisesRegex(ValueError, "VOLUME"):
            lane.validate_configuration(self.config, self.declared)

    def test_host_port_or_unpinned_image_refused(self):
        for field, value in [("ports", [18081]), ("image", "odoo:latest")]:
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config["services"]["control"][field] = value
                with self.assertRaisesRegex(ValueError, "PORT_OR_IMAGE"):
                    lane.validate_configuration(config, self.declared)

    def test_repository_root_or_foreign_secret_mount_refused(self):
        for source in (str(lane.ROOT), "/home/user/.env.dev", "/var/run/docker.sock"):
            self.config["services"]["control"]["volumes"] = [{"type": "bind", "source": source}]
            with self.assertRaisesRegex(ValueError, "FOREIGN_BIND"):
                lane.validate_configuration(self.config, self.declared)

    def test_external_network_refused(self):
        self.config["networks"]["default"]["internal"] = False
        with self.assertRaisesRegex(ValueError, "NETWORK"):
            lane.validate_configuration(self.config, self.declared)

    def test_maintenance_execution_credentials_match_preflight(self):
        validate = function("validate_maintenance_identity")
        maintenance = {"host": "db", "port": 5432, "user": self.declared["maintenance_role"],
                       "password": "synthetic", "cluster_system_identifier": "123"}
        validate(self.declared, {"maintenance": "synthetic"}, maintenance)
        for key in ("host", "port", "user", "password"):
            changed = dict(maintenance, **{key: "other"})
            with self.assertRaisesRegex(ValueError, "CREDENTIAL_DRIFT"):
                validate(self.declared, {"maintenance": "synthetic"}, changed)

    def test_runtime_source_has_no_unconditional_failure_compensation(self):
        # Structural ownership guard: exercise must leave recovery to its
        # explicit reconciler rather than bypassing commit-unknown semantics.
        tree = ast.parse((lane.ROOT / "scripts/ops/platform_database_rehearsal_runtime.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "exercise")
        for handler in [n for n in ast.walk(node) if isinstance(n, ast.ExceptHandler)]:
            calls = {n.func.id for n in ast.walk(handler) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            self.assertFalse(calls & {"recover", "_restore_admission_after_audit"})

    def test_missing_credential_authority_never_adopts_old_volume(self):
        with patch.object(lane, "execute", return_value=self.declared["volumes"][0]):
            with self.assertRaisesRegex(ValueError, "EXISTING_VOLUME_WITHOUT_AUTHORITY"):
                lane.volume_inventory(require_absent=True)


class TestAuditBoundReuse(unittest.TestCase):
    def test_resume_uses_declared_request_not_receipt_self_comparison(self):
        from scripts.ops import platform_database_register as registration
        from scripts.ops import platform_database_lifecycle_apply as lifecycle
        from scripts.ops.platform_database_receipt import validate_success
        declared = lane.declaration()
        expected = function("expected_request", registration=registration, lifecycle=lifecycle)
        verify = function("verify_audit_receipt", registration=registration, lifecycle=lifecycle,
                          expected_request=expected, validate_success=validate_success)
        snapshot = {"operation_request": {"execution_id": "a" * 32, "reason": "synthetic reason"}}
        for operation in ("register", "provision", "activate"):
            module = registration if operation == "register" else lifecycle
            audit = types.SimpleNamespace(id=1, operation=operation, result=snapshot)
            receipt = {"operation_id": 1, "registration_readback": snapshot, "entry": module.ENTRY,
                       "db_name": declared["target_database"], "operation": operation,
                       "execution_id": "a" * 32, "ok": True, "status": "passed",
                       "request": expected(declared, operation, "synthetic reason")}
            verify(audit, receipt, declared)
            for key in ("entry", "db_name", "operation", "execution_id", "request"):
                bad = dict(receipt, **{key: {} if key == "request" else "wrong"})
                with self.subTest(operation=operation, key=key), self.assertRaises(ValueError):
                    verify(audit, bad, declared)

    def test_actual_maintenance_connection_verifies_cluster_before_return(self):
        from scripts.ops import platform_database_lifecycle_apply as lifecycle
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ("cluster-A",)
        driver = types.SimpleNamespace(connect=MagicMock(return_value=connection))
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "maintenance.json"
            data = {"host": "db", "port": 5432, "user": "synthetic", "password": "synthetic",
                    "cluster_system_identifier": "cluster-A"}
            config.write_text(json.dumps(data))
            with patch.dict("sys.modules", {"psycopg2": driver}), patch.dict("os.environ", {"PLATFORM_DATABASE_MAINTENANCE_CONFIG": str(config)}):
                self.assertIs(lifecycle.maintenance_connection(), connection)
                connection.close.assert_not_called()
                data["cluster_system_identifier"] = "cluster-B"
                config.write_text(json.dumps(data))
                with self.assertRaisesRegex(lifecycle.LifecycleApplyError, "CLUSTER_MISMATCH"):
                    lifecycle.maintenance_connection()
                connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()

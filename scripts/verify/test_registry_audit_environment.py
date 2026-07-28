from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "ops" / "registry_audit_environment.py"
SPEC = importlib.util.spec_from_file_location(
    "registry_audit_environment_under_test",
    MODULE_PATH,
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)

GENERIC_POLICY_PATH = (
    ROOT
    / "scripts"
    / "ops"
    / "registry_audit"
    / "generic_policy_metadata.py"
)
GENERIC_POLICY_SPEC = importlib.util.spec_from_file_location(
    "generic_policy_metadata_under_test",
    GENERIC_POLICY_PATH,
)
assert GENERIC_POLICY_SPEC and GENERIC_POLICY_SPEC.loader
generic_policy = importlib.util.module_from_spec(GENERIC_POLICY_SPEC)
GENERIC_POLICY_SPEC.loader.exec_module(generic_policy)

ROUTE_POLICY_PATH = (
    ROOT
    / "scripts"
    / "ops"
    / "registry_audit"
    / "route_policy_metadata.py"
)
ROUTE_POLICY_SPEC = importlib.util.spec_from_file_location(
    "route_policy_metadata_under_test",
    ROUTE_POLICY_PATH,
)
assert ROUTE_POLICY_SPEC and ROUTE_POLICY_SPEC.loader
route_policy = importlib.util.module_from_spec(ROUTE_POLICY_SPEC)
ROUTE_POLICY_SPEC.loader.exec_module(route_policy)


class RecordingRunner:
    def __init__(self) -> None:
        self.calls = []

    def run(self, args, **kwargs):
        self.calls.append((list(args), dict(kwargs)))
        return audit.CommandResult(stdout="", stderr="", returncode=0)


class RegistryAuditEnvironmentTests(unittest.TestCase):
    def _generic_policy_fixture(self):
        handlers = [
            {
                "intent": intent,
                "handler_class": f"odoo.addons.smart_core.handlers.{intent}.Handler",
                "source_file": f"addons/smart_core/handlers/{intent}.py",
            }
            for intent in generic_policy.GENERIC_INTENTS
        ]
        aliases = [
            {
                "alias": "api.data.write",
                "canonical_intent": "api.data.create",
            }
        ]
        runtime_models = [
            {
                "model": "project.project",
                "field_names": ["id", "name"],
            },
            {
                "model": "project.task",
                "field_names": ["id", "name", "project_id"],
            },
            {
                "model": "res.partner",
                "field_names": ["id", "name"],
            },
        ]
        project_fields = [
            {"model": "project.task", "field": "project_id"},
        ]
        rpc_candidates = [
            {
                "model": "project.task",
                "methods": [{"method": "action_open"}],
            }
        ]
        return generic_policy.build_generic_policy_metadata(
            handlers=handlers,
            aliases=aliases,
            runtime_models=runtime_models,
            project_fields=project_fields,
            rpc_candidates=rpc_candidates,
            write_allowlist={
                "project.task": ["name", "project_id"],
                "res.partner": ["name"],
            },
            unlink_policies={
                "project.project": {"allowed": True},
            },
            mutation_policies={},
            source_symbols={
                "write_allowlist": "policy.write",
                "mutation": "policy.mutation",
                "create_execution": "policy.create",
                "unlink": "policy.unlink",
                "execute_button": "policy.execute",
            },
        )

    def test_generic_policy_metadata_enumerates_all_handlers_and_aliases(self):
        payload = self._generic_policy_fixture()
        records = payload["policy_records"]
        self.assertEqual(
            [record["registry_key"] for record in records],
            list(generic_policy.GENERIC_INTENTS),
        )
        self.assertEqual(len(records), 7)
        write = next(
            record
            for record in records
            if record["registry_key"] == "api.data.write"
        )
        self.assertEqual(write["canonical_handler"], "api.data.create")
        self.assertEqual(write["model_selector_type"], "EXPLICIT_ALLOWLIST")
        self.assertEqual(
            write["field_policies"]["write"]["project.task"],
            ["name", "project_id"],
        )
        self.assertEqual(write["default_model_decision"], "DENY")
        self.assertEqual(write["denied_models"], ["project.project"])
        api_data = next(
            record
            for record in records
            if record["registry_key"] == "api.data"
        )
        self.assertEqual(api_data["model_selector_type"], "DEFAULT_ALLOW")
        self.assertEqual(api_data["denied_models"], [])
        self.assertTrue(
            generic_policy.POLICY_REQUIRED_KEYS <= set(write)
        )

    def test_generic_policy_metadata_decides_every_project_model_and_field(self):
        payload = self._generic_policy_fixture()
        model_rows = payload["project_model_decisions"]
        field_rows = payload["project_field_decisions"]
        self.assertEqual(
            [row["model"] for row in model_rows],
            ["project.task"],
        )
        self.assertEqual(
            model_rows[0]["generic_api_reachability"],
            "PARTIALLY_ALLOWED",
        )
        self.assertEqual(
            model_rows[0]["callable_methods"][0]["status"],
            "UNRESOLVED_DYNAMIC",
        )
        self.assertEqual(
            [(row["model"], row["field"]) for row in field_rows],
            [("project.task", "project_id")],
        )
        self.assertTrue(field_rows[0]["readable"])
        self.assertTrue(field_rows[0]["creatable"])
        self.assertTrue(field_rows[0]["writable"])

    def test_generic_policy_metadata_never_executes_dynamic_behavior(self):
        payload = self._generic_policy_fixture()
        self.assertFalse(payload["business_handlers_executed"])
        self.assertFalse(payload["business_model_methods_executed"])
        self.assertFalse(payload["policy_predicates_executed"])
        self.assertFalse(payload["business_data_read"])
        self.assertGreater(len(payload["dynamic_unresolved_items"]), 0)
        for item in payload["dynamic_unresolved_items"]:
            self.assertTrue(item["registry_key"])
            self.assertTrue(item["provider_source"])
            self.assertTrue(item["dynamic_inputs"])
            self.assertTrue(item["reason"])

    def test_route_policy_metadata_merges_decorator_overrides_without_execution(self):
        def base_route():
            raise AssertionError("route method must not execute")

        base_route.original_routing = {
            "routes": ["/api/example"],
            "auth": "public",
            "type": "http",
            "methods": ["GET"],
            "csrf": False,
        }

        def override_route():
            raise AssertionError("route method must not execute")

        override_route.original_routing = {
            "auth": "user",
            "methods": ["POST"],
        }

        BaseController = type(
            "BaseController",
            (),
            {
                "__module__": "odoo.addons.demo.controllers",
                "endpoint": base_route,
            },
        )
        ChildController = type(
            "ChildController",
            (BaseController,),
            {
                "__module__": "odoo.addons.demo.controllers",
                "endpoint": override_route,
            },
        )
        payload = route_policy.project_route_policies(
            [ChildController],
            source_file_resolver=lambda _value: "addons/demo/controllers.py",
        )
        self.assertEqual(len(payload["records"]), 1)
        record = payload["records"][0]
        self.assertEqual(record["route"], "/api/example")
        self.assertEqual(record["auth"], "user")
        self.assertEqual(record["methods"], ["POST"])
        self.assertFalse(record["csrf"])
        self.assertFalse(record["executed_during_audit"])
        self.assertFalse(payload["controller_methods_executed"])
        self.assertFalse(payload["http_requests_executed"])

    def test_route_policy_metadata_gates_winner_until_true_conflict_is_proven(self):
        def first_endpoint():
            raise AssertionError("route method must not execute")

        first_endpoint.original_routing = {
            "routes": ["/api/duplicate"],
            "auth": "public",
            "type": "http",
            "methods": ["POST"],
        }

        def second_endpoint():
            raise AssertionError("route method must not execute")

        second_endpoint.original_routing = {
            "routes": ["/api/duplicate"],
            "auth": "user",
            "type": "json",
            "methods": ["POST"],
        }
        First = type(
            "First",
            (),
            {
                "__module__": "odoo.addons.first.controllers",
                "endpoint": first_endpoint,
            },
        )
        Second = type(
            "Second",
            (),
            {
                "__module__": "odoo.addons.second.controllers",
                "endpoint": second_endpoint,
            },
        )
        framework_rules = [
            {
                "route": "/api/duplicate",
                "methods": ["POST"],
                "endpoint_symbol": "runtime.first",
                "effective_implementation": (
                    "odoo.addons.first.controllers.first_endpoint"
                ),
                "module_order": 1,
                "controller_registration_order": 1,
                "routing_map_order": 1,
                "routing_map_id": "ROUTING-MAP-FIXTURE",
                "route_surface": "CUSTOM_FRONTEND_BACKEND_API",
                "match_dimensions": {
                    "route": "/api/duplicate",
                    "methods": ["POST"],
                    "host": "",
                    "subdomain": "",
                    "converters": [],
                    "compiled_pattern": "^/api/duplicate$",
                    "defaults": {},
                    "build_only": False,
                    "websocket": False,
                },
            },
            {
                "route": "/api/duplicate",
                "methods": ["POST"],
                "endpoint_symbol": "runtime.second",
                "effective_implementation": (
                    "odoo.addons.second.controllers.second_endpoint"
                ),
                "module_order": 2,
                "controller_registration_order": 2,
                "routing_map_order": 2,
                "routing_map_id": "ROUTING-MAP-FIXTURE",
                "route_surface": "CUSTOM_FRONTEND_BACKEND_API",
                "match_dimensions": {
                    "route": "/api/duplicate",
                    "methods": ["POST"],
                    "host": "",
                    "subdomain": "",
                    "converters": [],
                    "compiled_pattern": "^/api/duplicate$",
                    "defaults": {},
                    "build_only": False,
                    "websocket": False,
                },
            },
        ]
        payload = route_policy.project_route_policies(
            [First, Second],
            source_file_resolver=lambda _value: "addons/demo/controllers.py",
            framework_rules=framework_rules,
            matcher_order_proof={
                "leaf_rule_iteration_detected": True,
                "leaf_rule_return_detected": True,
                "source_sha256": "a" * 64,
                "source_executed": False,
                "matcher_executed": False,
            },
        )
        self.assertEqual(payload["schema_version"], 4)
        self.assertEqual(len(payload["collisions"]), 1)
        conflict = payload["collisions"][0]
        self.assertEqual(
            conflict["conflict_classification"],
            "TRUE_RUNTIME_CONFLICT",
        )
        self.assertTrue(conflict["same_final_routing_map"])
        self.assertTrue(conflict["winner_analysis_permitted"])
        self.assertEqual(
            conflict["winner_analysis_status"],
            "NOT_RUN_AFTER_TRUE_CONFLICT_GATE",
        )
        self.assertEqual(conflict["effective_implementation"], "")
        self.assertTrue(conflict["policy_change_across_override"])
        self.assertFalse(conflict["request_match_executed"])
        self.assertFalse(conflict["endpoint_executed"])

        for rule in framework_rules:
            rule["ordering_key_repr"] = "(False, 0, [], 0, [])"
            rule["ordering_key_executed"] = True
        resolved = route_policy.project_route_policies(
            [First, Second],
            source_file_resolver=lambda _value: "addons/demo/controllers.py",
            framework_rules=framework_rules,
            matcher_order_proof={
                "analysis_stage": "CURRENT_FRAMEWORK_LINEAR_ORDER_PROVEN",
                "map_iter_rules_order_proven": True,
                "map_stable_sort_proven": True,
                "adapter_first_match_return_proven": True,
                "map_adapter_match_source_sha256": "a" * 64,
                "source_executed": False,
                "matcher_executed": False,
            },
        )
        conflict = resolved["collisions"][0]
        self.assertEqual(conflict["enumeration_status"], "RESOLVED")
        self.assertEqual(
            conflict["winner_analysis_status"],
            "RESOLVED_NONINVASIVE",
        )
        self.assertEqual(
            conflict["effective_implementation"],
            "odoo.addons.first.controllers.first_endpoint",
        )

    def test_run_id_and_resource_names_are_exact_and_unique(self):
        run_id = f"{audit.SAFE_PREFIX}-0123456789ab"
        self.assertEqual(audit._validate_run_id(run_id), run_id)
        names = audit._resource_names(run_id)
        self.assertEqual(names["compose_project"], run_id)
        self.assertEqual(
            names["database"],
            "sc_admin_vis_p3_registry_audit_0123456789ab",
        )
        self.assertEqual(
            names["containers"],
            [
                f"{run_id}-postgres",
                f"{run_id}-odoo-registry",
            ],
        )
        with self.assertRaises(audit.AuditError):
            audit._validate_run_id("sc-demo")

    def test_sanitized_environment_drops_database_and_proxy_inheritance(self):
        run_id = f"{audit.SAFE_PREFIX}-0123456789ab"
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                os.environ,
                {
                    "REGISTRY_AUDIT_OUTPUT_ROOT": temporary,
                    "HTTP_PROXY": "http://forbidden",
                    "DATABASE_URL": "postgres://forbidden",
                    "DB_NAME": "sc_demo",
                },
                clear=False,
            ):
                manifest = audit._initial_manifest(run_id)
                value = audit._sanitized_environment(
                    manifest,
                    {"user": "audit", "password": "temporary"},
                )
        self.assertNotIn("HTTP_PROXY", value)
        self.assertNotIn("DATABASE_URL", value)
        self.assertNotIn("DB_NAME", value)
        self.assertEqual(
            value["REGISTRY_AUDIT_DATABASE_NAME"],
            "sc_admin_vis_p3_registry_audit_0123456789ab",
        )

    def test_compose_contract_has_internal_network_and_no_dangerous_mounts(self):
        audit._validate_compose_static(
            ROOT / "docker-compose.registry-audit.yml"
        )
        text = (ROOT / "docker-compose.registry-audit.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("internal: true", text)
        self.assertIn("ports:", text)
        self.assertNotIn("network_mode: host", text)
        self.assertNotIn("/var/run/docker.sock", text)
        self.assertNotIn("external: true", text)
        self.assertNotIn("env_file:", text)
        self.assertNotIn('user: "0:0"', text)
        self.assertIn(
            "registry_audit_extraaddons:/mnt/extra-addons",
            text,
        )
        exporter = (
            ROOT / "scripts" / "ops" / "registry_audit" / "registry_export.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(".sudo()", exporter)

    def test_manifest_rejects_resource_outside_exact_run_scope(self):
        run_id = f"{audit.SAFE_PREFIX}-0123456789ab"
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                os.environ,
                {"REGISTRY_AUDIT_OUTPUT_ROOT": temporary},
                clear=False,
            ):
                manifest = audit._initial_manifest(run_id)
        audit._validate_manifest_identity(manifest, run_id)
        manifest["resources"]["volumes"][0] = "foreign-volume"
        with self.assertRaises(audit.AuditError):
            audit._validate_manifest_identity(manifest, run_id)

    def test_manifest_predeclares_every_resource_before_creation(self):
        run_id = f"{audit.SAFE_PREFIX}-0123456789ab"
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                os.environ,
                {"REGISTRY_AUDIT_OUTPUT_ROOT": temporary},
                clear=False,
            ):
                manifest, _credentials = audit._prepare(run_id)
                persisted = audit._read_json(audit._paths(run_id)["manifest"])
        self.assertEqual(manifest["schema_version"], 2)
        for kind, names in manifest["resources"].items():
            records = persisted["resource_records"][kind]
            self.assertEqual([record["name"] for record in records], names)
            self.assertTrue(all(record["id"] == "" for record in records))
            self.assertTrue(all(record["created"] is False for record in records))

    def test_manifest_write_failure_occurs_before_any_runtime_command(self):
        run_id = f"{audit.SAFE_PREFIX}-abcdef012345"
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                os.environ,
                {"REGISTRY_AUDIT_OUTPUT_ROOT": temporary},
                clear=False,
            ), mock.patch.object(
                audit,
                "_atomic_json",
                side_effect=audit.AuditError("forced manifest failure"),
            ):
                with self.assertRaises(audit.AuditError):
                    audit._prepare(run_id)

    def test_cleanup_refuses_foreign_label_before_delete_command(self):
        runner = RecordingRunner()
        expected = {
            **audit.RESOURCE_LABELS,
            "com.smartconstruction.audit.run-id": (
                f"{audit.SAFE_PREFIX}-0123456789ab"
            ),
        }
        foreign = dict(expected)
        foreign["com.smartconstruction.audit.run-id"] = (
            f"{audit.SAFE_PREFIX}-abcdefabcdef"
        )
        with mock.patch.object(
            audit,
            "_inspect_labels",
            return_value=foreign,
        ), mock.patch.object(
            audit,
            "_inspect_resource_id",
            return_value=f"{audit.SAFE_PREFIX}-0123456789ab-pgdata",
        ):
            with self.assertRaises(audit.AuditError):
                audit._remove_resource(
                    runner,
                    "volumes",
                    f"{audit.SAFE_PREFIX}-0123456789ab-pgdata",
                    expected,
                    f"{audit.SAFE_PREFIX}-0123456789ab-pgdata",
                )
        self.assertEqual(runner.calls, [])

    def test_general_cleanup_refuses_unlabelled_resource(self):
        runner = RecordingRunner()
        run_id = f"{audit.SAFE_PREFIX}-0123456789ab"
        name = f"{run_id}-pgdata"
        with mock.patch.object(
            audit,
            "_inspect_labels",
            return_value={"com.docker.volume.anonymous": ""},
        ), mock.patch.object(
            audit,
            "_inspect_resource_id",
            return_value=name,
        ):
            with self.assertRaises(audit.AuditError):
                audit._remove_resource(
                    runner,
                    "volumes",
                    name,
                    audit._labels_for(run_id),
                    name,
                )
        self.assertEqual(runner.calls, [])

    def test_cleanup_is_idempotent_when_resources_are_absent(self):
        runner = RecordingRunner()
        with mock.patch.object(
            audit,
            "_inspect_labels",
            return_value=None,
        ):
            removed = audit._remove_resource(
                runner,
                "containers",
                f"{audit.SAFE_PREFIX}-0123456789ab-postgres",
                {
                    **audit.RESOURCE_LABELS,
                    "com.smartconstruction.audit.run-id": (
                        f"{audit.SAFE_PREFIX}-0123456789ab"
                    ),
                },
                f"{audit.SAFE_PREFIX}-0123456789ab-postgres",
            )
        self.assertFalse(removed)
        self.assertEqual(runner.calls, [])

    def test_database_health_wait_fails_closed_and_accepts_healthy(self):
        runner = RecordingRunner()
        runner.run = mock.Mock(
            side_effect=[
                audit.CommandResult(stdout="starting\n", stderr="", returncode=0),
                audit.CommandResult(stdout="healthy\n", stderr="", returncode=0),
            ]
        )
        with mock.patch.object(audit.time, "sleep"):
            audit._wait_for_healthy_database(
                runner,
                "ephemeral-postgres",
                attempts=2,
                interval_seconds=0,
            )
        self.assertEqual(runner.run.call_count, 2)

    def test_export_schema_rejects_secret_shaped_keys(self):
        run_id = f"{audit.SAFE_PREFIX}-0123456789ab"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "export.json"
            with mock.patch.dict(
                os.environ,
                {"REGISTRY_AUDIT_OUTPUT_ROOT": temporary + "-root"},
                clear=False,
            ):
                manifest = audit._initial_manifest(run_id)
            payload = {key: [] for key in audit.REQUIRED_EXPORT_KEYS}
            payload["run_metadata"] = {
                "run_id": run_id,
                "git_head": manifest["git_head"],
                "git_tree": manifest["git_tree"],
                "database_role": manifest["database_role"],
            }
            payload["generic_api_policies"] = {
                "schema_version": 2,
                "policy_records": [
                    {
                        key: (
                            1
                            if key == "load_order_index"
                            else True
                            if key == "policy_metadata_statically_readable"
                            else []
                            if key
                            in {
                                "aliases",
                                "replaced_implementations",
                                "policy_metadata_source",
                                "allowed_models",
                                "denied_models",
                                "project_id_input_sources",
                                "dynamic_inputs",
                            }
                            else {}
                            if key
                            in {
                                "model_operation_policies",
                                "field_policies",
                                "method_policies",
                                "domain_policy",
                                "context_policy",
                                "model_default_injection",
                            }
                            else "fixture"
                        )
                        for key in audit.REQUIRED_GENERIC_POLICY_KEYS
                    }
                ],
                "project_model_decisions": [],
                "project_field_decisions": [],
                "dynamic_unresolved_items": [],
                "business_handlers_executed": False,
                "business_model_methods_executed": False,
                "policy_predicates_executed": False,
                "business_data_read": False,
            }
            payload["route_policies"] = {
                "schema_version": 4,
                "enumeration_source": "fixture",
                "records": [],
                "framework_rules": [
                    {
                        "routing_map_id": "ROUTING-MAP-FIXTURE",
                        "routing_map_class": "werkzeug.routing.Map",
                        "routing_map_order": 0,
                        "route": "/web",
                        "methods": [],
                        "endpoint_symbol": "fixture.web",
                        "effective_implementation": "fixture.web",
                        "route_surface": "ODOO_NATIVE_WEB_ROUTE",
                        "match_dimensions": {
                            "route": "/web",
                            "methods": [],
                            "host": "",
                            "subdomain": "",
                            "converters": [],
                            "compiled_pattern": "^/web$",
                            "defaults": {},
                            "redirect_to": None,
                            "alias": False,
                            "build_only": False,
                            "websocket": False,
                            "strict_slashes": False,
                            "merge_slashes": False,
                        },
                        "dispatch_dimensions": {
                            "endpoint": "fixture.web",
                            "effective_implementation": "fixture.web",
                            "type": "http",
                        },
                        "security_dimensions": {
                            "auth": "none",
                            "csrf": True,
                            "cors": "",
                            "readonly": False,
                            "save_session": True,
                        },
                        "ordering_key_repr": "",
                        "ordering_key_executed": False,
                        "endpoint_executed": False,
                        "matcher_executed": False,
                    }
                ],
                "matcher_order_proof": {
                    "source_executed": False,
                    "matcher_executed": False,
                },
                "collisions": [],
                "unresolved_items": [],
                "controller_methods_executed": False,
                "http_requests_executed": False,
                "request_match_executed": False,
                "business_model_methods_executed": False,
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            audit._validate_export(path, manifest)
            payload["run_metadata"]["password"] = "forbidden"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(audit.AuditError):
                audit._validate_export(path, manifest)
            del payload["run_metadata"]["password"]
            payload["unresolved_runtime_nodes"] = ["temporary-password-value"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(audit.AuditError):
                audit._validate_export(
                    path,
                    manifest,
                    ("temporary-password-value",),
                )

    def test_snapshot_comparison_ignores_only_manifest_resources(self):
        run_id = f"{audit.SAFE_PREFIX}-0123456789ab"
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                os.environ,
                {"REGISTRY_AUDIT_OUTPUT_ROOT": temporary},
                clear=False,
            ):
                manifest = audit._initial_manifest(run_id)
        before = {
            "containers": [{"id": "c1", "name": "existing"}],
            "networks": [{"id": "n1", "name": "existing-net"}],
            "volumes": [{"id": "existing-vol", "name": "local"}],
        }
        self.assertTrue(
            audit._snapshot_unchanged(before, dict(before), manifest)
        )
        changed = json.loads(json.dumps(before))
        changed["containers"][0]["id"] = "changed"
        self.assertFalse(
            audit._snapshot_unchanged(before, changed, manifest)
        )

    def test_implementation_has_no_global_prune_command(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("volume prune", source)
        self.assertNotIn("system prune", source)
        self.assertNotIn("docker prune", source)


if __name__ == "__main__":
    unittest.main()

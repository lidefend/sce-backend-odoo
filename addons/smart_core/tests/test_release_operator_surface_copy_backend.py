# -*- coding: utf-8 -*-
import ast
import importlib.util
import json
import sys
import types
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
DELIVERY_DIR = ROOT / "addons" / "smart_core" / "delivery"


def _load_module(module_name: str, relative_path: str):
    target = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


sys.modules.setdefault("odoo", types.ModuleType("odoo"))
sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
smart_core_pkg.__path__ = [str(DELIVERY_DIR.parent)]
delivery_pkg = sys.modules.setdefault("odoo.addons.smart_core.delivery", types.ModuleType("odoo.addons.smart_core.delivery"))
delivery_pkg.__path__ = [str(DELIVERY_DIR)]
smart_core_pkg.delivery = delivery_pkg

approval_stub = types.ModuleType("odoo.addons.smart_core.delivery.release_approval_policy_service")
approval_stub.ReleaseApprovalPolicyService = type(
    "ReleaseApprovalPolicyService",
    (),
    {"__init__": lambda self, env: None},
)
sys.modules["odoo.addons.smart_core.delivery.release_approval_policy_service"] = approval_stub

audit_stub = types.ModuleType("odoo.addons.smart_core.delivery.release_audit_trail_service")
audit_stub.ReleaseAuditTrailService = type(
    "ReleaseAuditTrailService",
    (),
    {"__init__": lambda self, env: None},
)
sys.modules["odoo.addons.smart_core.delivery.release_audit_trail_service"] = audit_stub

_load_module(
    "odoo.addons.smart_core.delivery.release_operator_contract_versions",
    "addons/smart_core/delivery/release_operator_contract_versions.py",
)
_load_module(
    "odoo.addons.smart_core.delivery.product_identity",
    "addons/smart_core/delivery/product_identity.py",
)
_load_module(
    "odoo.addons.smart_core.delivery.release_operator_contract_registry",
    "addons/smart_core/delivery/release_operator_contract_registry.py",
)
_load_module(
    "odoo.addons.smart_core.delivery.release_operator_read_model_service",
    "addons/smart_core/delivery/release_operator_read_model_service.py",
)
MANAGEMENT_ACTIONS = sys.modules[
    "odoo.addons.smart_core.delivery.platform_management_action_contract"
]
READ_MODEL = sys.modules[
    "odoo.addons.smart_core.delivery.release_operator_read_model_service"
].ReleaseOperatorReadModelService
READ_MODEL_MODULE = sys.modules[
    "odoo.addons.smart_core.delivery.release_operator_read_model_service"
]
COMPOSITION = sys.modules[
    "odoo.addons.smart_core.delivery.product_scene_composition"
]
EXTENSION_HOOKS = sys.modules[
    "odoo.addons.smart_core.utils.extension_hooks"
]
TARGET = _load_module(
    "odoo.addons.smart_core.delivery.release_operator_surface_service",
    "addons/smart_core/delivery/release_operator_surface_service.py",
)


class _ApprovalPolicyService:
    def _release_identity(self, *, product_key: str):
        edition_key = "preview" if product_key.endswith("preview") else "standard"
        return {
            "product_key": product_key,
            "base_product_key": "construction",
            "edition_key": edition_key,
        }

    def resolve_policy(self, *, action_type: str, product_key: str):
        return {"allowed_executor_role_codes": ["release_manager"]}

    def resolve_actor_role_codes(self, user):
        return ["release_manager"]

    def resolve_actor_role_context(self, user):
        return {
            "actor_role_codes": ["release_manager"],
            "role_source": "test",
            "source_authority": {"kind": "release_approval_policy_projection"},
        }

    def roles_match(self, actor_roles, allowed_roles):
        return bool(set(actor_roles or []).intersection(set(allowed_roles or [])))

    def can_approve(self, *, action, user):
        return True, "OK", {"source": "test"}


class _AuditTrailService:
    def build_audit_trail(self, *, product_key: str, action_limit: int):
        return {
            "active_released_snapshot": {
                "id": 11,
                "product_key": product_key,
                "edition_key": "standard",
                "version": "v11",
                "state": "released",
                "rollback_target_snapshot_id": 7,
                "business_scene_composition": _composition("生效项目组合"),
            },
            "release_actions": [
                {"id": 21, "action_type": "promote_snapshot", "state": "done", "approval_state": "approved"}
            ],
            "release_snapshots": [
                {"id": 11, "product_key": product_key, "edition_key": "standard", "version": "v11", "state": "released"},
                {
                    "id": 12,
                    "product_key": product_key,
                    "edition_key": "standard",
                    "version": "v12",
                    "state": "candidate",
                    "business_scene_composition": _composition("候选项目组合"),
                },
            ],
            "runtime": {
                "release_audit_trail_summary": {
                    "active_snapshot_version": "v11",
                    "latest_action_type": "promote_snapshot",
                    "latest_action_approval_state": "approved",
                },
                "released_snapshot_lineage": {"active_snapshot_id": 11},
            },
        }


def _composition(name, *, sequence=10, intent="view"):
    return {
        "schema": "construction.scenario_product_surface.v1",
        "source_db": "sc_test",
        "runtime_scope": "maintained_draft",
        "scenarios": [
            {
                "key": "project",
                "name": name,
                "active": True,
                "sequence": sequence,
                "source_db": "sc_test",
                "bindings": [
                    {
                        "entry_id": 1,
                        "menu_id": 21,
                        "menu_key": "project.menu_ledger",
                        "intent": intent,
                        "sequence": 0,
                        "source_db": "sc_test",
                    }
                ],
            }
        ],
    }


def _maintenance_declaration():
    return {
        "provider": "smart_construction_core",
        "action_xmlid": "smart_construction_core.action_sc_product_scenario",
        "menu_xmlid": (
            "smart_construction_core.menu_sc_product_scenario_business_config"
        ),
        "model": "sc.product.scenario",
        "scope": {
            "kind": "shared_maintenance_library",
            "label": "当前维护库共享业务场景定义",
            "applies_to": (
                "construction_product_drafts_in_this_maintenance_database"
            ),
            "filter_by_current_product": False,
        },
    }


class _RecordSet(list):
    def sudo(self):
        return self

    def search(self, domain, order=None, limit=None):
        return self


class _ReleaseActionRow:
    id = 31
    active = True
    approval_required = True
    approval_state = "pending_approval"
    state = "pending"

    def to_runtime_dict(self):
        return {
            "id": 31,
            "action_type": "rollback_snapshot",
            "product_key": "construction.standard",
            "target_snapshot_id": 7,
            "approval_state": "pending_approval",
            "state": "pending",
        }


class _SnapshotRow:
    def __init__(self, row_id, *, active=True):
        self.id = row_id
        self.active = active
        self.product_key = "construction.standard"
        self.state = "superseded"

    def exists(self):
        return self if self.active else self.__class__(self.id, active=False)


class _SnapshotRows(_RecordSet):
    def __init__(self, rows):
        super().__init__(rows)
        self.by_id = {row.id: row for row in rows}

    def browse(self, row_id):
        return self.by_id.get(int(row_id), _SnapshotRow(int(row_id), active=False))


class _Env(dict):
    def __init__(self):
        super().__init__()
        self.user = object()
        self["sc.release.action"] = _RecordSet([_ReleaseActionRow()])
        self["sc.edition.release.snapshot"] = _SnapshotRows([
            _SnapshotRow(7, active=True),
        ])
        # A deployment with the construction bundle installed publishes both
        # product bases; the platform-only deployment publishes just `platform`.
        self["ir.config_parameter"] = _ConfigParameter(
            "",
            params={"smart_core.release_operator.product_base_keys": "construction,platform"},
        )


class _ConfigParameter:
    def __init__(self, default_base, params=None):
        self.default_base = default_base
        self.params = dict(params or {})

    def sudo(self):
        return self

    def get_param(self, key, default=""):
        if key in self.params:
            return self.params[key]
        if key == "smart_core.release_operator.default_base_product_key":
            return self.default_base
        return default


class TestReleaseOperatorSurfaceCopyBackend(unittest.TestCase):
    def test_registered_extension_root_exports_business_scenario_hooks(self):
        extension_path = (
            ROOT / "addons/smart_construction_core/core_extension.py"
        )
        extension_tree = ast.parse(extension_path.read_text(encoding="utf-8"))
        extension_functions = {
            node.name
            for node in extension_tree.body
            if isinstance(node, ast.FunctionDef)
        }
        init_path = ROOT / "addons/smart_construction_core/__init__.py"
        init_tree = ast.parse(init_path.read_text(encoding="utf-8"))
        exported = {
            alias.name
            for node in init_tree.body
            if isinstance(node, ast.ImportFrom)
            and node.module == "core_extension"
            for alias in node.names
        }
        required = {
            "smart_core_business_scenario_maintenance",
            "smart_core_product_scene_composition",
        }
        self.assertTrue(required.issubset(extension_functions))
        self.assertTrue(required.issubset(exported))

        root_module = types.ModuleType(
            "odoo.addons.smart_construction_core"
        )
        for hook_name in required:
            setattr(
                root_module,
                hook_name,
                lambda *_args, _name=hook_name, **_kwargs: _name,
            )

        class Env(dict):
            def __init__(self):
                super().__init__({
                    "ir.config_parameter": _ConfigParameter(
                        "",
                        params={
                            "sc.core.extension_modules": (
                                "smart_construction_core"
                            )
                        },
                    )
                })

        with patch.object(
            EXTENSION_HOOKS.importlib,
            "import_module",
            return_value=root_module,
        ):
            for hook_name in sorted(required):
                self.assertEqual(
                    EXTENSION_HOOKS.call_extension_hook_first(
                        Env(),
                        hook_name,
                    ),
                    hook_name,
                )

    def test_platform_action_definitions_declare_complete_policy_inputs(self):
        definition = MANAGEMENT_ACTIONS.management_action_definition(
            "update_policy"
        )
        self.assertEqual(
            definition["accepted_fields"],
            [
                "product_key",
                "state",
                "access_level",
                "active",
                "allowed_role_codes",
                "center_updates",
                "entry_placements",
            ],
        )
        fields = {
            row["key"]: row
            for row in definition["editable_fields"]
        }
        self.assertEqual(
            [row["value"] for row in fields["state"]["options"]],
            ["draft", "preview", "stable", "archived"],
        )
        self.assertEqual(
            [row["value"] for row in fields["access_level"]["options"]],
            ["public", "internal", "role_restricted"],
        )

    def test_declared_confirmation_is_not_overridden_by_dynamic_default(self):
        decorated = READ_MODEL._decorate_operator_action(
            {
                "key": "freeze:test",
                "label": "Freeze",
                "intent": "release.operator.freeze",
                "enabled": True,
                "reason_code": "OK",
                "prerequisites": {"confirmation_required": False},
            },
            actor={"user_id": 7},
            target_scope={"product_key": "construction.standard"},
            operation_object={"product_key": "construction.standard"},
            confirm_required=True,
        )
        self.assertFalse(
            decorated["prerequisites"]["confirmation_required"]
        )
        self.assertEqual(
            decorated["prerequisites"]["confirmation_source"],
            "platform_action_definition",
        )

    def test_rollback_action_uses_dedicated_snapshot_rollback_authority(self):
        source = (
            ROOT / "addons/smart_core/handlers/release_operator.py"
        ).read_text(encoding="utf-8")
        rollback_branch = source.split('elif action_type == "rollback_snapshot":', 1)[1].split(
            "else:",
            1,
        )[0]
        self.assertIn("rollback_to_snapshot(", rollback_branch)
        self.assertNotIn("promote_to_released(", rollback_branch)
        service_source = (
            ROOT
            / "addons/smart_core/delivery/edition_release_snapshot_service.py"
        ).read_text(encoding="utf-8")
        self.assertIn("ROLLBACK_TARGET_INACTIVE", service_source)
        self.assertIn("if not target.active:", service_source)

    def test_inactive_rollback_target_is_not_declared_executable(self):
        env = _Env()
        env["sc.edition.release.snapshot"] = _SnapshotRows([
            _SnapshotRow(7, active=False),
        ])
        service = TARGET.ReleaseOperatorSurfaceService(env)
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        surface = service.build_surface(
            product_key="construction.standard",
            action_limit=5,
        )
        rollback = (surface.get("available_actions") or {}).get("rollback") or {}
        self.assertFalse(rollback.get("enabled"))
        self.assertEqual(rollback.get("reason_code"), "ROLLBACK_TARGET_INACTIVE")
        pending = (surface.get("pending_approval") or {}).get("actions") or []
        approve_action = pending[0].get("approve_action") or {}
        self.assertFalse(approve_action.get("enabled"))
        self.assertEqual(
            approve_action.get("reason_code"),
            "ROLLBACK_TARGET_INACTIVE",
        )

    def test_surface_build_includes_backend_owned_copy_payload(self):
        service = TARGET.ReleaseOperatorSurfaceService(_Env())
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        payload = service.build_surface(product_key="construction.standard", action_limit=5)

        self.assertEqual((payload.get("source_authority") or {}).get("kind"), "release_operator_surface_projection")
        self.assertEqual((((payload.get("read_model_v1") or {}).get("source_authority") or {}).get("kind")), "release_operator_read_model_projection")
        self.assertEqual(
            (
                (
                    (payload.get("read_model_v1") or {})
                    .get("contract_registry") or {}
                ).get("contracts") or {}
            ).get("platform_management_actions", {}).get("contract_version"),
            "platform_management_actions.v1",
        )
        self.assertEqual((payload.get("copy") or {}).get("title"), "发布控制台")
        self.assertIn("候选快照", (payload.get("copy") or {}).get("hint_candidate", ""))
        self.assertEqual((((payload.get("read_model_v1") or {}).get("copy") or {}).get("section_pending")), "待审批动作")
        self.assertEqual((((payload.get("read_model_v1") or {}).get("copy") or {}).get("rollback_action_label")), "回滚产品版本")
        self.assertEqual((((payload.get("available_actions") or {}).get("freeze") or {}).get("intent")), "release.operator.freeze")
        self.assertEqual((((payload.get("available_actions") or {}).get("sync_policy") or {}).get("intent")), "release.operator.sync_policy")
        self.assertEqual((((payload.get("available_actions") or {}).get("update_policy") or {}).get("intent")), "release.operator.update_policy")
        self.assertEqual((((payload.get("available_actions") or {}).get("set_page_enabled") or {}).get("intent")), "release.operator.set_page_enabled")
        self.assertEqual((((payload.get("available_actions") or {}).get("update_page_policy") or {}).get("intent")), "release.operator.update_page_policy")
        self.assertEqual((((payload.get("available_actions") or {}).get("runtime_probe") or {}).get("intent")), "release.operator.runtime_probe")
        self.assertIn("runtime_user_probe", (payload.get("release_pipeline") or {}))
        self.assertEqual(
            (payload.get("actor_scope") or {}).get("operator_kind"),
            "authorized_release_operator",
        )
        readback = payload.get("operation_readback") or {}
        self.assertEqual(readback.get("product_key"), "construction.standard")
        self.assertEqual(
            (readback.get("active_snapshot") or {}).get("version"),
            "v11",
        )
        self.assertEqual(readback.get("rollback_target_snapshot_id"), 7)
        freeze = (payload.get("available_actions") or {}).get("freeze") or {}
        self.assertEqual(
            (freeze.get("target_scope") or {}).get("kind"),
            "product_release",
        )
        self.assertTrue(
            (freeze.get("target_scope") or {}).get("is_global_product_release")
        )
        self.assertEqual(
            (freeze.get("operation_object") or {}).get("kind"),
            "release_snapshot",
        )
        self.assertEqual(
            (freeze.get("prerequisites") or {}).get("reason_code"),
            "OK",
        )
        self.assertEqual(
            (freeze.get("readback") or {}).get("mode"),
            "authoritative_after_write",
        )
        promote = (payload.get("available_actions") or {}).get("promote") or []
        self.assertEqual(len(promote), 1)
        self.assertEqual((promote[0].get("params") or {}).get("snapshot_id"), 12)
        self.assertEqual(
            (promote[0].get("operation_object") or {}).get("snapshot_id"),
            12,
        )
        self.assertEqual(
            (promote[0].get("actor") or {}).get("operator_kind"),
            "authorized_release_operator",
        )
        self.assertEqual(
            (promote[0].get("target_scope") or {}).get("product_key"),
            "construction.standard",
        )
        self.assertEqual(
            (promote[0].get("prerequisites") or {}).get("reason_code"),
            "OK",
        )
        self.assertTrue(
            (promote[0].get("prerequisites") or {}).get("confirmation_required")
        )
        self.assertEqual(
            (promote[0].get("readback") or {}).get("mode"),
            "authoritative_after_write",
        )
        update_policy = (payload.get("available_actions") or {}).get("update_policy") or {}
        self.assertEqual(
            update_policy.get("accepted_fields"),
            [
                "product_key",
                "state",
                "access_level",
                "active",
                "allowed_role_codes",
                "center_updates",
                "entry_placements",
            ],
        )
        self.assertEqual(
            {
                field.get("key")
                for field in update_policy.get("editable_fields") or []
            },
            {
                "state",
                "access_level",
                "active",
                "allowed_role_codes",
                "center_updates",
                "entry_placements",
            },
        )
        pending = (payload.get("pending_approval") or {}).get("actions") or []
        self.assertEqual(len(pending), 1)
        approve_action = pending[0].get("approve_action") or {}
        self.assertEqual(approve_action.get("intent"), "release.operator.approve")
        self.assertEqual(
            (approve_action.get("params") or {}).get("action_id"),
            31,
        )
        self.assertTrue(
            (approve_action.get("prerequisites") or {}).get(
                "confirmation_required"
            )
        )
        rollback = (payload.get("available_actions") or {}).get("rollback") or {}
        self.assertTrue(rollback.get("enabled"))
        self.assertEqual(
            (rollback.get("params") or {}).get("target_snapshot_id"),
            7,
        )

    def test_surface_copy_has_no_legacy_english_operator_labels(self):
        service = TARGET.ReleaseOperatorSurfaceService(_Env())
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        payload = service.build_surface(product_key="construction.standard", action_limit=5)
        encoded = json.dumps(payload.get("copy") or {}, ensure_ascii=False)

        for retired in (
            "Release Operator Surface",
            "Active Released Snapshot",
            "Latest Action",
            "Approval State",
            "Rollback Target",
            "Promote",
        ):
            self.assertNotIn(retired, encoded)

    def test_surface_exposes_product_center_editor_contract(self):
        service = TARGET.ReleaseOperatorSurfaceService(_Env())
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        payload = service.build_surface(
            product_key="construction.standard",
            action_limit=5,
        )
        editor = payload.get("product_center_editor") or {}
        self.assertEqual(editor.get("contract_version"), "product_center_editor.v1")
        self.assertEqual(editor.get("product_key"), "construction.standard")
        self.assertEqual(
            (editor.get("save_action") or {}).get("intent"),
            "release.operator.update_policy",
        )
        self.assertEqual(
            (payload.get("available_actions") or {})
            .get("update_policy", {})
            .get("editor_contract"),
            "product_center_editor.v1",
        )

    def test_surface_exposes_draft_candidate_and_active_composition_states(self):
        service = TARGET.ReleaseOperatorSurfaceService(_Env())
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        payload = service.build_surface(
            product_key="construction.standard",
            action_limit=5,
        )
        states = payload.get("business_scene_composition_states") or {}
        self.assertEqual(
            states.get("contract_version"),
            "business_scene_composition_management.v1",
        )
        self.assertEqual(
            (states.get("candidate") or {}).get("status"),
            "candidate",
        )
        self.assertEqual(
            (states.get("candidate") or {}).get("identity", {}).get(
                "snapshot_id"
            ),
            12,
        )
        self.assertEqual((states.get("active") or {}).get("status"), "active")
        self.assertEqual(
            (states.get("active") or {}).get("identity", {}).get(
                "snapshot_id"
            ),
            11,
        )
        self.assertEqual(
            (states.get("candidate") or {}).get("scenarios", [])[0].get(
                "name"
            ),
            "候选项目组合",
        )
        self.assertEqual(
            (states.get("active") or {}).get("scenarios", [])[0].get(
                "name"
            ),
            "生效项目组合",
        )

    def test_composition_diff_detects_name_and_intent_without_count_change(self):
        service = READ_MODEL(_Env())
        control_scope = {
            "business_scene_composition": _composition(
                "项目组合",
                sequence=10,
                intent="view",
            ),
            "draft_identity": {
                "product_key": "construction.standard",
                "policy_id": 5,
                "version": "v1",
            },
        }
        candidate_snapshots = [
            {
                "id": 12,
                "product_key": "construction.standard",
                "version": "v12",
                "state": "candidate",
                "frozen_at": "2026-11-20 01:00:00",
                "business_scene_composition": _composition(
                    "项目组合改名",
                    sequence=10,
                    intent="handle",
                ),
            }
        ]
        current_release_state = {
            "active_snapshot": {
                "id": 11,
                "product_key": "construction.standard",
                "version": "v11",
                "state": "released",
                "released_at": "2026-11-19 01:00:00",
                "business_scene_composition": _composition(
                    "项目组合",
                    sequence=10,
                    intent="view",
                ),
            }
        }
        states = service._build_business_scene_composition_states(
            product_key="construction.standard",
            control_scope=control_scope,
            candidate_snapshots=candidate_snapshots,
            current_release_state=current_release_state,
        )
        candidate_diff = states["comparisons"]["draft_vs_candidate"]
        self.assertEqual(candidate_diff["state"], "changed")
        self.assertEqual(candidate_diff["changed_scenario_keys"], ["project"])
        self.assertTrue(candidate_diff["changed_entry_keys"])
        self.assertEqual(
            states["comparisons"]["draft_vs_active"]["state"],
            "identical",
        )

    def test_composition_preserves_signed_values_and_zero_center_sequence(self):
        first = _composition("项目组合")
        first["scenarios"][0]["sequence"] = -1
        first["scenarios"][0]["bindings"][0]["sequence"] = -2
        first["scenarios"][0]["bindings"][0]["center_sequence"] = 0
        second = deepcopy(first)
        second["scenarios"][0]["bindings"][0]["center_sequence"] = 10
        left = READ_MODEL_MODULE._project_business_scene_composition(
            first,
            status="draft",
            identity={"product_key": "construction.standard"},
        )
        right = READ_MODEL_MODULE._project_business_scene_composition(
            second,
            status="candidate",
            identity={"product_key": "construction.standard"},
        )
        self.assertEqual(left["scenarios"][0]["sequence"], -1)
        self.assertEqual(left["scenarios"][0]["entries"][0]["sequence"], -2)
        self.assertEqual(
            left["scenarios"][0]["entries"][0]["center_sequence"],
            0,
        )
        self.assertEqual(
            READ_MODEL_MODULE._business_scene_composition_diff(left, right)[
                "state"
            ],
            "changed",
        )

    def test_missing_candidate_and_active_states_are_explicit(self):
        service = READ_MODEL(_Env())
        states = service._build_business_scene_composition_states(
            product_key="construction.standard",
            control_scope={
                "business_scene_composition": {
                    "schema": "construction.scenario_product_surface.v1",
                    "scenarios": [],
                }
            },
            candidate_snapshots=[],
            current_release_state={"active_snapshot": {}},
        )
        self.assertEqual(states["draft"]["reason_code"], "BUSINESS_SCENE_COMPOSITION_EMPTY")
        self.assertEqual(states["candidate"]["status"], "not_frozen")
        self.assertFalse(states["candidate"]["available"])
        self.assertEqual(states["active"]["status"], "no_active_release")
        self.assertFalse(states["active"]["available"])

    def test_snapshot_release_draft_is_read_from_snapshot_json_projection(self):
        serialized = READ_MODEL(_Env())._serialize_snapshot({
            "id": 12,
            "product_key": "construction.standard",
            "state": "candidate",
            "release_draft": {
                "page_count": 4,
                "total_page_count": 6,
                "business_scenario_count": 2,
                "business_scene_composition_sha256": "b" * 64,
            },
            "meta": {},
        })
        self.assertEqual(
            serialized["release_draft"]["business_scenario_count"],
            2,
        )
        self.assertEqual(
            serialized["release_draft"][
                "business_scene_composition_sha256"
            ],
            "b" * 64,
        )

    def test_shared_composition_is_the_same_source_for_freeze_and_management(self):
        policy = {"product_key": "construction.standard"}
        composed = _composition("共享维护组合")
        with patch.object(
            COMPOSITION,
            "normalize_product_policy_for_env",
            side_effect=lambda env, value: dict(value),
        ), patch.object(
            COMPOSITION,
            "call_extension_hook_first",
            return_value=composed,
        ):
            result = COMPOSITION.compose_product_policy(_Env(), policy)
        self.assertEqual(
            result["business_scene_composition"]["scenarios"][0]["name"],
            "共享维护组合",
        )

    def test_native_scenario_maintenance_entry_declares_shared_scope(self):
        action = types.SimpleNamespace(
            id=71,
            name="业务场景定义",
            res_model="sc.product.scenario",
            view_mode="tree,form",
            groups_id=[types.SimpleNamespace(id=11)],
        )
        menu = types.SimpleNamespace(
            id=72,
            name="业务场景定义",
            action=action,
            groups_id=[types.SimpleNamespace(id=11)],
        )
        elevated_model = types.SimpleNamespace(
            _fields={
                "name": object(),
                "entry_ids": object(),
            },
            check_access_rights=lambda operation, raise_exception=False: True,
        )
        model = types.SimpleNamespace(
            _fields={},
            sudo=lambda: elevated_model,
            check_access_rights=lambda operation, raise_exception=False: True,
        )

        class Env(_Env):
            user = types.SimpleNamespace(
                id=7,
                groups_id=[types.SimpleNamespace(id=11)],
            )

            def ref(self, xmlid, raise_if_not_found=False):
                return {
                    "smart_construction_core.action_sc_product_scenario": action,
                    "smart_construction_core.menu_sc_product_scenario_business_config": menu,
                }.get(xmlid)

        Env.__getitem__ = (
            lambda self, key: model
            if key == "sc.product.scenario"
            else _Env.__getitem__(self, key)
        )
        env = Env()
        env.user = types.SimpleNamespace(
            id=7,
            groups_id=[types.SimpleNamespace(id=11)],
        )
        with patch.object(
            READ_MODEL_MODULE,
            "call_extension_hook_first",
            return_value=_maintenance_declaration(),
        ):
            service = READ_MODEL(env)
            entry = service._build_business_scenario_maintenance(
                product_key="construction.standard"
            )
        self.assertTrue(entry["enabled"])
        self.assertTrue(entry["applicable"])
        self.assertEqual(entry["provider"], "smart_construction_core")
        self.assertEqual(entry["reason_code"], "SCENARIO_MAINTENANCE_AVAILABLE")
        self.assertEqual(entry["action"]["id"], 71)
        self.assertEqual(entry["menu"]["id"], 72)
        self.assertEqual(
            entry["scope"]["kind"],
            "shared_maintenance_library",
        )
        self.assertFalse(entry["scope"]["has_product_key"])
        self.assertFalse(entry["scope"]["has_company_id"])
        self.assertFalse(entry["scope"]["filter_by_current_product"])
        self.assertEqual(
            entry["future_freeze_product_key"],
            "construction.standard",
        )
        self.assertEqual(
            entry["return_readback"]["intent"],
            "release.operator.surface",
        )

    def test_native_scenario_maintenance_entry_does_not_widen_denied_write(self):
        action = types.SimpleNamespace(
            id=71,
            name="业务场景定义",
            res_model="sc.product.scenario",
            view_mode="tree,form",
            groups_id=[],
        )
        menu = types.SimpleNamespace(
            id=72,
            name="业务场景定义",
            action=action,
            groups_id=[],
        )
        elevated_model = types.SimpleNamespace(
            _fields={},
            check_access_rights=lambda operation, raise_exception=False: True,
        )
        model = types.SimpleNamespace(
            _fields={},
            sudo=lambda: elevated_model,
            check_access_rights=lambda operation, raise_exception=False: operation == "read",
        )

        class Env(_Env):
            user = types.SimpleNamespace(id=7, groups_id=[])

            def ref(self, xmlid, raise_if_not_found=False):
                return {
                    "smart_construction_core.action_sc_product_scenario": action,
                    "smart_construction_core.menu_sc_product_scenario_business_config": menu,
                }.get(xmlid)

        Env.__getitem__ = (
            lambda self, key: model
            if key == "sc.product.scenario"
            else _Env.__getitem__(self, key)
        )
        env = Env()
        env.user = types.SimpleNamespace(id=7, groups_id=[])
        with patch.object(
            READ_MODEL_MODULE,
            "call_extension_hook_first",
            return_value=_maintenance_declaration(),
        ):
            entry = READ_MODEL(env)._build_business_scenario_maintenance(
                product_key="construction.standard"
            )
        self.assertFalse(entry["enabled"])
        self.assertFalse(entry["access"]["write_allowed"])
        self.assertEqual(
            entry["reason_code"],
            "SCENARIO_MAINTENANCE_WRITE_DENIED",
        )

    def test_native_scenario_maintenance_entry_honors_menu_and_action_groups(self):
        action = types.SimpleNamespace(
            id=71,
            name="业务场景定义",
            res_model="sc.product.scenario",
            view_mode="tree,form",
            groups_id=[types.SimpleNamespace(id=81)],
        )
        menu = types.SimpleNamespace(
            id=72,
            name="业务场景定义",
            action=action,
            groups_id=[types.SimpleNamespace(id=80)],
        )
        model = types.SimpleNamespace(
            _fields={},
            sudo=lambda: model,
            check_access_rights=lambda operation, raise_exception=False: True,
        )

        class Env(_Env):
            user = types.SimpleNamespace(
                id=7,
                groups_id=[types.SimpleNamespace(id=11)],
            )

            def ref(self, xmlid, raise_if_not_found=False):
                return {
                    "smart_construction_core.action_sc_product_scenario": action,
                    "smart_construction_core.menu_sc_product_scenario_business_config": menu,
                }.get(xmlid)

        Env.__getitem__ = (
            lambda self, key: model
            if key == "sc.product.scenario"
            else _Env.__getitem__(self, key)
        )
        env = Env()
        env.user = types.SimpleNamespace(
            id=7,
            groups_id=[types.SimpleNamespace(id=11)],
        )
        with patch.object(
            READ_MODEL_MODULE,
            "call_extension_hook_first",
            return_value=_maintenance_declaration(),
        ):
            entry = READ_MODEL(env)._build_business_scenario_maintenance(
                product_key="construction.standard"
            )
        self.assertFalse(entry["enabled"])
        self.assertFalse(entry["access"]["menu_groups_allowed"])
        self.assertFalse(entry["access"]["action_groups_allowed"])
        self.assertEqual(
            entry["reason_code"],
            "SCENARIO_MAINTENANCE_MENU_GROUP_DENIED",
        )
        self.assertIn(
            "SCENARIO_MAINTENANCE_ACTION_GROUP_DENIED",
            entry["blockers"],
        )

    def test_native_scenario_maintenance_is_not_applicable_to_platform_product(self):
        with patch.object(
            READ_MODEL_MODULE,
            "call_extension_hook_first",
            return_value=None,
        ):
            entry = READ_MODEL(_Env())._build_business_scenario_maintenance(
                product_key="platform.standard"
            )
        self.assertFalse(entry["applicable"])
        self.assertFalse(entry["enabled"])
        self.assertEqual(
            entry["reason_code"],
            "SCENARIO_MAINTENANCE_NOT_APPLICABLE",
        )
        self.assertEqual(entry["action"]["id"], 0)
        self.assertEqual(entry["menu"]["id"], 0)

    def test_platform_kernel_empty_surface_is_not_reported_as_blocked(self):
        service = TARGET.ReleaseOperatorSurfaceService(_Env())
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        payload = service.build_surface(product_key="platform.standard", action_limit=5)
        readiness = (payload.get("product_delivery_console") or {}).get("readiness") or {}
        self.assertEqual(readiness.get("status"), "not_configured")
        self.assertEqual(readiness.get("blocking_count"), 0)
        self.assertEqual(readiness.get("unconfigured_count"), 1)
        checks = (payload.get("release_pipeline") or {}).get("preflight_checks") or []
        page_check = next((row for row in checks if row.get("key") == "has_product_pages"), {})
        self.assertEqual(page_check.get("status"), "not_configured")
        self.assertIn("平台内核", page_check.get("message", ""))
        self.assertEqual((payload.get("read_model_v1") or {}).get("identity", {}).get("label"), "平台内核标准版")

    def test_preview_product_copy_mentions_preview_edition(self):
        service = TARGET.ReleaseOperatorSurfaceService(_Env())
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        payload = service.build_surface(product_key="construction.preview", action_limit=5)

        self.assertIn("预览版", (payload.get("copy") or {}).get("description", ""))

    def test_operator_products_include_platform_and_construction_portfolio(self):
        service = TARGET.ReleaseOperatorSurfaceService(_Env())
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        payload = service.build_surface(product_key="platform.preview", action_limit=5)
        read_model = payload.get("read_model_v1") or {}
        products = read_model.get("products") or []

        self.assertEqual((read_model.get("identity") or {}).get("product_key"), "platform.preview")
        self.assertEqual(
            [row.get("product_key") for row in products],
            ["platform.standard", "platform.preview", "construction.standard", "construction.preview"],
        )
        self.assertIn("施工管理标准版", [row.get("label") for row in products])
        self.assertEqual((((read_model.get("identity") or {}).get("source_authority") or {}).get("kind")), "delivery_product_identity_resolver")

    def test_operator_default_base_product_is_configurable(self):
        env = _Env()
        env["ir.config_parameter"] = _ConfigParameter("platform")
        service = TARGET.ReleaseOperatorSurfaceService(env)
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        payload = service.build_surface(product_key="", action_limit=5)
        read_model = payload.get("read_model_v1") or {}

        self.assertEqual((read_model.get("identity") or {}).get("product_key"), "platform.standard")
        self.assertEqual((read_model.get("identity") or {}).get("default_base_source"), "config")

    def test_product_delivery_console_merges_product_extension_facts(self):
        module = types.ModuleType("odoo.addons.test_product_delivery_extension")
        module.get_system_init_fact_contributions = lambda env, user, context=None: {
            "module": "product",
            "facts": {
                "bundle": {
                    "name": "test_bundle",
                    "profile": {"product_key": "construction.standard", "label": "测试交付包"},
                    "capabilities": [{"key": "product.project.delivery", "label": "项目交付"}],
                    "scenes": [{"code": "projects.dashboard", "name": "项目驾驶舱"}],
                    "recommended_roles": ["pm"],
                    "default_dashboard": "projects.dashboard",
                },
                "license": {
                    "level": "enterprise",
                    "tiers": ["community", "pro", "enterprise"],
                    "customer_visible": True,
                    "upgrade_hint": "联系管理员升级",
                },
            },
        }
        sys.modules["odoo.addons.test_product_delivery_extension"] = module
        env = _Env()
        env["ir.config_parameter"] = _ConfigParameter(
            "",
            params={"sc.core.extension_modules": "test_product_delivery_extension"},
        )
        service = TARGET.ReleaseOperatorSurfaceService(env)
        service.read_model_service.audit_service = _AuditTrailService()
        service.read_model_service.approval_policy_service = _ApprovalPolicyService()

        payload = service.build_surface(product_key="construction.standard", action_limit=5)
        console = payload.get("product_delivery_console") or {}

        self.assertEqual((console.get("profile") or {}).get("label"), "测试交付包")
        self.assertEqual(((console.get("license") or {}).get("level")), "enterprise")
        self.assertEqual(((console.get("bundle") or {}).get("capability_count")), 1)
        self.assertEqual(((console.get("source_authority") or {}).get("kind")), "release_operator_product_delivery_console_projection")


if __name__ == "__main__":
    unittest.main()

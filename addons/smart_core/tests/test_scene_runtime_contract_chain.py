# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.scene_ready_contract_builder import build_scene_ready_contract
from odoo.addons.smart_core.core.ui_base_contract_adapter import adapt_ui_base_contract


def _sample_ui_base_contract(model: str = "project.project") -> dict:
    return {
        "model": model,
        "views": {
            "tree": {
                "columns": ["name", "state", "manager_id"],
                "fields": ["name", "state", "manager_id"],
            },
            "form": {
                "fields": ["name", "manager_id", "start_date"],
            },
        },
        "fields": {
            "name": {"type": "char", "string": "项目名称"},
            "manager_id": {"type": "many2one", "string": "项目经理"},
            "state": {"type": "selection", "string": "状态"},
            "start_date": {"type": "date", "string": "开始日期"},
        },
        "search": {
            "default_sort": "write_date desc",
            "filters": [{"key": "my", "label": "我的项目", "domain": [["manager_id", "=", "uid"]]}],
            "group_by": [{"field": "state", "label": "按状态"}],
            "fields": ["name", "manager_id"],
        },
        "permissions": {
            "visible": True,
            "allowed": True,
            "required_capabilities": ["projects.list"],
        },
        "workflow": {
            "state_field": "state",
            "states": ["draft", "active"],
            "transitions": [{"key": "confirm", "from": "draft", "to": "active"}],
        },
        "validator": {
            "required_fields": ["name", "manager_id"],
        },
        "actions": {
            "items": [
                {"key": "create_project", "label": "创建项目", "intent": "record.create"},
                {"key": "export_list", "label": "导出", "intent": "record.export"},
            ]
        },
    }


@tagged("post_install", "-at_install", "smart_core", "scene_runtime_chain")
class TestSceneRuntimeContractChain(TransactionCase):
    def test_ui_base_adapter_emits_seven_fact_buckets(self):
        payload = adapt_ui_base_contract(_sample_ui_base_contract(), scene_key="projects.list")
        orchestrator_input = payload.get("orchestrator_input") or {}
        self.assertEqual(orchestrator_input.get("scene_key"), "projects.list")
        for key in (
            "view_fact",
            "field_fact",
            "search_fact",
            "action_fact",
            "permission_fact",
            "workflow_fact",
            "validation_fact",
        ):
            self.assertIn(key, orchestrator_input)

    def test_scene_ready_list_runtime_chain(self):
        contract = build_scene_ready_contract(
            scenes=[
                {
                    "code": "projects.list",
                    "name": "项目列表",
                    "layout": {"kind": "list"},
                    "target": {"route": "/s/projects.list", "model": "project.project"},
                    "related_scenes": ["projects.ledger"],
                    "ui_base_contract": _sample_ui_base_contract(),
                },
                {
                    "code": "projects.ledger",
                    "name": "项目台账",
                    "layout": {"kind": "ledger"},
                    "target": {"route": "/s/projects.ledger", "model": "project.project"},
                    "ui_base_contract": _sample_ui_base_contract(),
                }
            ],
            role_surface={"landing_scene_key": "projects.list"},
        )
        entries = contract.get("scenes") or []
        self.assertEqual(contract.get("contract_version"), "2.0.0")
        self.assertEqual(contract.get("schema_version"), "2.0.0")
        self.assertEqual(len(entries), 2)
        row = next(
            (
                item
                for item in entries
                if ((item.get("scene") or {}).get("key")) == "projects.list"
            ),
            {},
        )
        switch_surface = row.get("switch_surface") or {}
        switch_items = switch_surface.get("items") or []
        self.assertTrue((row.get("search_surface") or {}).get("filters"))
        self.assertTrue((row.get("permission_surface") or {}).get("allowed"))
        self.assertTrue((row.get("action_surface") or {}).get("counts"))
        self.assertTrue(((row.get("meta") or {}).get("ui_base_orchestrator_input") or {}).get("view_fact"))
        self.assertEqual(((row.get("view_modes") or [])[0] or {}).get("key"), "tree")
        self.assertEqual(((row.get("action_surface") or {}).get("selection_mode")), "single")
        self.assertEqual(((switch_items[0] or {}).get("label")), "项目列表")
        self.assertEqual(((switch_items[1] or {}).get("key")), "projects.ledger")
        self.assertEqual(((switch_items[1] or {}).get("route")), "/s/projects.ledger")

    def test_scene_ready_form_runtime_chain(self):
        contract = build_scene_ready_contract(
            scenes=[
                {
                    "code": "projects.intake",
                    "name": "项目立项",
                    "layout": {"kind": "form"},
                    "target": {"route": "/s/projects.intake", "model": "project.project", "view_mode": "form"},
                    "blocks": [{"type": "form_block", "zone": "main", "source": "ui_base_contract.views.form"}],
                    "next_scene": "project.management",
                    "ui_base_contract": _sample_ui_base_contract(),
                }
            ],
            role_surface={"landing_scene_key": "projects.intake"},
        )
        row = (contract.get("scenes") or [])[0]
        validation_surface = row.get("validation_surface") or {}
        workflow_surface = row.get("workflow_surface") or {}
        self.assertIn("name", validation_surface.get("required_fields") or [])
        self.assertEqual(workflow_surface.get("state_field"), "state")
        self.assertIn("form", [item.get("key") for item in (row.get("view_modes") or []) if isinstance(item, dict)])
        self.assertEqual(((row.get("action_surface") or {}).get("selection_mode")), "single")
        self.assertEqual(row.get("next_scene"), "project.management")
        self.assertEqual(row.get("next_scene_route"), "/s/project.management")

    def test_scene_ready_form_next_scene_from_provider(self):
        def _provider(scene_key: str = "", runtime: dict | None = None, context: dict | None = None):
            _ = runtime or {}
            _ = context or {}
            return {
                "scene_key": scene_key,
                "next_scene": "contracts.workspace",
                "next_scene_route": "/s/contracts.workspace",
            }

        contract = build_scene_ready_contract(
            scenes=[
                {
                    "code": "projects.intake",
                    "name": "项目立项",
                    "layout": {"kind": "form"},
                    "target": {"route": "/s/projects.intake", "model": "project.project", "view_mode": "form"},
                    "blocks": [{"type": "form_block", "zone": "main", "source": "ui_base_contract.views.form"}],
                    "providers": [{"key": "test.intake.provider"}],
                    "provider_registry": {
                        "test.intake.provider": _provider,
                    },
                    "ui_base_contract": _sample_ui_base_contract(),
                }
            ],
            role_surface={"landing_scene_key": "projects.intake"},
        )
        row = (contract.get("scenes") or [])[0]
        self.assertTrue(bool(row.get("next_scene")))
        self.assertTrue(bool(row.get("next_scene_route")))

    def test_scene_ready_workspace_runtime_chain(self):
        contract = build_scene_ready_contract(
            scenes=[
                {
                    "code": "workspace.home",
                    "name": "工作台",
                    "layout": {"kind": "workspace"},
                    "target": {"route": "/s/workspace.home"},
                    "ui_base_contract": _sample_ui_base_contract(),
                }
            ],
            role_surface={"landing_scene_key": "workspace.home"},
        )
        row = (contract.get("scenes") or [])[0]
        search_surface = row.get("search_surface") or {}
        self.assertEqual(search_surface.get("fields"), [])
        self.assertEqual(search_surface.get("group_by"), [])

    def test_scene_ready_finance_actions_do_not_infer_mutation_model(self):
        contract = build_scene_ready_contract(
            scenes=[
                {
                    "code": "finance.payment_requests",
                    "name": "付款申请审批",
                    "layout": {"kind": "list"},
                    "target": {"route": "/s/finance.payment_requests", "model": "finance.payment.request"},
                    "ui_base_contract": _sample_ui_base_contract(model="finance.payment.request"),
                }
            ],
            role_surface={"landing_scene_key": "finance.payment_requests"},
        )
        row = (contract.get("scenes") or [])[0]
        actions = row.get("actions") or []
        self.assertGreaterEqual(len(actions), 3)
        first_target = (actions[0] or {}).get("target") or {}
        self.assertNotIn("mutation", first_target)

    def test_scene_ready_risk_actions_do_not_infer_mutation_model(self):
        contract = build_scene_ready_contract(
            scenes=[
                {
                    "code": "risk.center",
                    "name": "风险中心",
                    "layout": {"kind": "workspace"},
                    "target": {"route": "/s/risk.center", "model": "project.risk.action"},
                    "ui_base_contract": _sample_ui_base_contract(model="project.risk.action"),
                }
            ],
            role_surface={"landing_scene_key": "risk.center"},
        )
        row = (contract.get("scenes") or [])[0]
        actions = row.get("actions") or []
        self.assertGreaterEqual(len(actions), 3)
        first_target = (actions[0] or {}).get("target") or {}
        self.assertNotIn("mutation", first_target)

    def test_pilot_core_scenes_materialize_strict_contract_fields(self):
        scenes = [
            {
                "code": "workspace.home",
                "name": "工作台",
                "layout": {"kind": "workspace"},
                "target": {"route": "/my-work"},
                "ui_base_contract": _sample_ui_base_contract(model="project.risk.action"),
            },
            {
                "code": "finance.payment_requests",
                "name": "付款申请审批",
                "layout": {"kind": "list"},
                "target": {"route": "/s/finance.payment_requests", "model": "finance.payment.request"},
                "ui_base_contract": _sample_ui_base_contract(model="finance.payment.request"),
            },
            {
                "code": "risk.center",
                "name": "风险中心",
                "layout": {"kind": "workspace"},
                "target": {"route": "/s/risk.center", "model": "project.risk.action"},
                "ui_base_contract": _sample_ui_base_contract(model="project.risk.action"),
            },
            {
                "code": "project.management",
                "name": "项目驾驶舱",
                "layout": {"kind": "workspace"},
                "target": {"route": "/s/project.management", "model": "project.project"},
                "ui_base_contract": _sample_ui_base_contract(model="project.project"),
            },
        ]

        contract = build_scene_ready_contract(
            scenes=scenes,
            role_surface={"landing_scene_key": "workspace.home"},
        )
        rows = contract.get("scenes") or []
        self.assertEqual(len(rows), 4)
        rows_by_key = {
            ((row.get("scene") or {}).get("key") or ""): row
            for row in rows
            if isinstance(row, dict)
        }
        workspace_row = rows_by_key.get("workspace.home") or {}
        self.assertEqual(workspace_row.get("scene_tier"), "core")
        self.assertTrue(bool((workspace_row.get("runtime_policy") or {}).get("strict_contract_mode")))
        for key in ("workspace.home", "finance.payment_requests", "risk.center", "project.management"):
            row = rows_by_key.get(key) or {}
            surface = row.get("surface") or {}
            self.assertTrue(bool(surface.get("kind")))
            self.assertTrue(bool((surface.get("intent") or {}).get("title")))
            self.assertTrue(isinstance(row.get("projection"), dict))
            self.assertTrue(isinstance(row.get("action_surface"), dict))

    def test_scene_ready_respects_declared_runtime_policy_and_tier(self):
        contract = build_scene_ready_contract(
            scenes=[
                {
                    "code": "finance.payment_requests",
                    "name": "付款申请审批",
                    "layout": {"kind": "list"},
                    "runtime_policy": {"strict_contract_mode": False, "scene_tier": "standard"},
                    "target": {"route": "/s/finance.payment_requests", "model": "finance.payment.request"},
                    "ui_base_contract": _sample_ui_base_contract(model="finance.payment.request"),
                }
            ],
            role_surface={"landing_scene_key": "finance.payment_requests"},
        )
        row = (contract.get("scenes") or [])[0]
        self.assertEqual(row.get("scene_tier"), "standard")
        runtime_policy = row.get("runtime_policy") or {}
        self.assertFalse(bool(runtime_policy.get("strict_contract_mode")))
        self.assertEqual(runtime_policy.get("scene_tier"), "standard")

    def test_strict_scene_emits_contract_guard_for_missing_semantic_contract(self):
        contract = build_scene_ready_contract(
            scenes=[
                {
                    "code": "projects.list",
                    "name": "项目列表",
                    "layout": {"kind": "list"},
                    "runtime_policy": {"strict_contract_mode": True, "scene_tier": "core"},
                    "target": {"route": "/s/projects.list", "model": "project.project"},
                    "ui_base_contract": _sample_ui_base_contract(model="project.project"),
                }
            ],
            role_surface={"landing_scene_key": "projects.list"},
        )
        row = (contract.get("scenes") or [])[0]
        guard = row.get("contract_guard") or {}
        self.assertTrue(bool(guard.get("strict_mode")))
        self.assertTrue(bool(guard.get("contract_ready")))
        source_missing = guard.get("source_missing") or []
        self.assertIn("surface.kind", source_missing)
        self.assertIn("view_modes", source_missing)
        self.assertEqual(guard.get("missing") or [], [])
        self.assertTrue(isinstance(guard.get("defaults_applied"), list))
        self.assertIn("surface", guard.get("defaults_applied") or [])

    def test_non_pilot_scene_without_declared_policy_stays_non_strict(self):
        contract = build_scene_ready_contract(
            scenes=[
                {
                    "code": "projects.list",
                    "name": "项目列表",
                    "layout": {"kind": "list"},
                    "target": {"route": "/s/projects.list", "model": "project.project"},
                    "ui_base_contract": _sample_ui_base_contract(model="project.project"),
                }
            ],
            role_surface={"landing_scene_key": "projects.list"},
        )
        row = (contract.get("scenes") or [])[0]
        runtime_policy = row.get("runtime_policy") or {}
        self.assertFalse(bool(runtime_policy.get("strict_contract_mode")))
        self.assertIn(row.get("scene_tier"), (None, ""))
        self.assertIn(row.get("contract_guard"), (None, {}))

# -*- coding: utf-8 -*-
"""ADMIN-CLOSE-01 governed runtime sample for the project ledger."""
from __future__ import annotations

import json
from copy import deepcopy
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
    EditionReleaseSnapshotService,
)
from odoo.addons.smart_core.delivery.platform_capability_explorer import (
    PlatformCapabilityExplorerService,
    access_layer_assessment,
    _merge_extension_contributions,
)
from odoo.addons.smart_core.delivery.release_operator_read_model_service import (
    ReleaseOperatorReadModelService,
)
from odoo.addons.smart_core.handlers.release_operator import (
    ReleaseOperatorApproveHandler,
    ReleaseOperatorPromoteHandler,
)
from odoo.addons.smart_core.security.platform_admin import platform_control_scope
from odoo.addons.smart_core.security.namespace_resolver import resolve_instance
from odoo.addons.smart_construction_core.services.platform_capability_explorer_contributions import (
    get_platform_capability_explorer_contributions,
)
from odoo.addons.smart_construction_scene.handlers.scenario_activation import (
    ScenarioActivationSetHandler,
    _catalog,
)
from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key
from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
    ENABLEMENT_STORAGE_SOURCE,
    enablement_param_key,
    read_tenant_enablement,
    write_tenant_enablement,
)


PROJECT_MENU_XMLID = "smart_construction_core.menu_sc_project_project"


@tagged("post_install", "-at_install", "admin_close_01")
class TestAdminClose01PlatformToEnterprise(TransactionCase):
    def setUp(self):
        super().setUp()
        self.menu = self.env.ref(PROJECT_MENU_XMLID)
        self.action = self.menu.action
        self.assertTrue(self.action, "project ledger action must exist")
        # The disposable technical test database ships the native record but
        # intentionally deactivates demo-facing menus. Activate only the
        # selected project-ledger carrier and its native parent path inside this
        # rolled-back transaction so the real production projection executes.
        menu_path_ids = [
            int(value)
            for value in self.menu.parent_path.strip("/").split("/")
            if value
        ]
        project_path = self.env["ir.ui.menu"].sudo().with_context(
            active_test=False
        ).browse(menu_path_ids).exists()
        project_path.filtered(lambda row: not row.active).write({"active": True})
        project_path.invalidate_recordset()
        self.env.flush_all()
        self.env["ir.ui.menu"].invalidate_model()
        self.assertTrue(self.menu.with_context(active_test=False).active)
        self.env["ir.config_parameter"].sudo().set_param(
            "smart_core.release_operator.catalog_source_db", self.env.cr.dbname
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "smart_core.platform_release_db", self.env.cr.dbname
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "sc.core.extension_modules", "smart_construction_core"
        )
        self.actor = self.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "ADMIN CLOSE 01 Project User",
                "login": "admin_close_01_project_user",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            *sorted(
                                set(self.menu.groups_id.ids)
                                | set(self.action.groups_id.ids)
                            ),
                        ],
                    )
                ],
            }
        )
        self.actor_env = self.env(user=self.actor)
        self.snapshot = self.env["sc.edition.release.snapshot"].sudo().search(
            [
                ("product_key", "=", "construction.standard"),
                ("state", "=", "released"),
                ("is_active", "=", True),
                ("active", "=", True),
            ],
            order="released_at desc, activated_at desc, id desc",
            limit=1,
        )
        if not self.snapshot:
            released = EditionReleaseSnapshotService(self.env).freeze_release_surface(
                product_key="construction.standard",
                version="admin-close-01-runtime-sample",
                note="ADMIN-CLOSE-01 governed runtime sample",
                replace_active=True,
            )
            self.snapshot = self.env["sc.edition.release.snapshot"].browse(
                int(released["id"])
            )
        base_snapshot_id = int(self.snapshot.id)
        policy = self.env["sc.product.policy"].sudo().search(
            [("product_key", "=", "construction.standard"), ("active", "=", True)],
            limit=1,
        )
        self.assertTrue(policy, "construction standard policy must exist")
        menu_groups = deepcopy(policy.menu_groups)
        changed_page = ""
        for group in menu_groups:
            for menu in group.get("menus") or []:
                if (
                    menu.get("menu_xmlid") != PROJECT_MENU_XMLID
                    and menu.get("enabled", True)
                    and str(menu.get("release_state") or "") == "released"
                ):
                    menu["enabled"] = False
                    menu["release_state"] = "hidden"
                    changed_page = str(
                        menu.get("page_key")
                        or menu.get("menu_key")
                        or menu.get("menu_xmlid")
                        or ""
                    )
                    break
            if changed_page:
                break
        self.assertTrue(changed_page)
        policy.write({"menu_groups": menu_groups})
        released_v2 = EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard",
            version="admin-close-01-runtime-sample-v2",
            note="ADMIN-CLOSE-01 draft difference sample",
            replace_active=True,
        )
        self.snapshot = self.env["sc.edition.release.snapshot"].browse(
            int(released_v2["id"])
        )
        self.base_snapshot_id = base_snapshot_id
        self.changed_page = changed_page

    def test_project_ledger_capability_release_and_enterprise_facts(self):
        menu_id = int(self.menu.id)
        contribution = get_platform_capability_explorer_contributions(
            self.actor_env, [menu_id], {menu_id: PROJECT_MENU_XMLID}
        )
        qualification = (
            contribution.get("product_qualifications") or {}
        ).get(PROJECT_MENU_XMLID) or {}
        self.assertEqual(qualification.get("standard"), "qualified", qualification)
        self.assertTrue(qualification.get("evidence"), qualification)

        bindings = (contribution.get("scene_bindings") or {}).get(str(menu_id)) or []
        scene_keys = [
            str(row.get("scenario_key") or "").strip()
            for row in bindings
            if isinstance(row, dict) and str(row.get("scenario_key") or "").strip()
        ]
        self.assertTrue(scene_keys, bindings)
        write_tenant_enablement(
            self.actor_env, self.actor_env.company.id, business_key(scene_keys[0]), True
        )

        explorer_service = PlatformCapabilityExplorerService(self.actor_env)
        action_xmlid = self.action.get_external_id()[self.action.id]
        root = self.env.ref("smart_construction_core.menu_sc_root")
        native_row = {
            "menu_id": int(self.menu.id),
            "menu_xmlid": PROJECT_MENU_XMLID,
            "menu_name": self.menu.name,
            "menu_path": [
                row.name
                for row in self.env["ir.ui.menu"].sudo().with_context(
                    active_test=False
                ).browse(
                    [
                        int(value)
                        for value in self.menu.parent_path.strip("/").split("/")
                        if value
                    ]
                )
            ],
            "menu_sequence": self.menu.sequence,
            "action_id": int(self.action.id),
            "action_xmlid": action_xmlid,
            "action_model": self.action._name,
            "res_model": getattr(self.action, "res_model", ""),
            "view_modes": [
                value.strip()
                for value in str(getattr(self.action, "view_mode", "") or "").split(",")
                if value.strip()
            ],
            "owner_module": PROJECT_MENU_XMLID.split(".", 1)[0],
        }
        facts = explorer_service._load_native_facts([native_row], [int(root.id)])
        runtime_contributions = _merge_extension_contributions(
            self.actor_env, [native_row]
        )
        _, explorer = explorer_service._build_row(
            native_row,
            facts=facts,
            contributions=runtime_contributions,
            root_menu_ids=[int(root.id)],
            include_detail=True,
        )
        self.assertIsNotNone(explorer)
        self.assertEqual(explorer["native_facts"]["model"]["name"], "project.project")
        self.assertEqual(
            explorer["qualification"]["standard"],
            "qualified",
            explorer["qualification"],
        )
        self.assertTrue(explorer["enterprise_enablement"]["enabled"])
        self.assertTrue(
            explorer["visibility"]["can_use"],
            explorer["visibility"],
        )
        self.assertEqual(
            explorer["diagnostics"]["visibility_reason"],
            "CURRENT_USER_ENTRY_AVAILABLE",
        )

        scenario_catalog = _catalog(
            self.actor_env, company_id=self.actor_env.company.id
        )
        project_row = next(
            row
            for row in scenario_catalog["business_scenarios"]
            if row.get("scene_key") == scene_keys[0]
        )
        self.assertTrue(project_row["product_released"])
        self.assertTrue(project_row["tenant_enabled"])
        self.assertEqual(
            project_row["product_qualification"]["status"], "qualified"
        )
        self.assertEqual(project_row["enablement_blockers"], [])
        self.assertEqual(
            scenario_catalog["target_scope"]["company_id"],
            self.actor_env.company.id,
        )
        self.assertFalse(
            scenario_catalog["target_scope"]["is_global_product_release"]
        )

        release_model = ReleaseOperatorReadModelService(self.actor_env).build_read_model(
            product_key="construction.standard"
        )
        active = (release_model.get("operation_readback") or {}).get(
            "active_snapshot"
        ) or {}
        self.assertEqual(active.get("product_key"), "construction.standard")
        self.assertTrue(active.get("version"))
        self.assertEqual(active.get("version"), "admin-close-01-runtime-sample-v2")
        self.assertEqual(
            active.get("rollback_target_snapshot_id"), self.base_snapshot_id
        )
        self.assertGreaterEqual(
            int((active.get("release_diff") or {}).get("changed_page_count") or 0),
            1,
        )
        self.assertEqual(
            (release_model.get("actor_scope") or {}).get("user_id"),
            self.actor_env.user.id,
        )
        freeze_action = (
            release_model.get("available_operator_actions") or {}
        ).get("freeze") or {}
        self.assertEqual(
            (freeze_action.get("target_scope") or {}).get("kind"),
            "product_release",
        )

        sample = {
            "schema": "admin_close_01.project_ledger.runtime_sample.v1",
            "database": self.actor_env.cr.dbname,
            "company": {
                "id": self.actor_env.company.id,
                "name": self.actor_env.company.name,
            },
            "actor": scenario_catalog["actor"],
            "entry": {
                "menu_xmlid": PROJECT_MENU_XMLID,
                "menu_id": menu_id,
                "action_xmlid": self.action.get_external_id()[self.action.id],
                "action_id": self.action.id,
                "model": getattr(self.action, "res_model", ""),
            },
            "product": {
                "qualification": qualification,
                "active_snapshot": active,
            },
            "enterprise": {
                "scene_keys": scene_keys,
                "enablement": explorer["enterprise_enablement"],
                "target_scope": scenario_catalog["target_scope"],
            },
            "visibility": explorer["visibility"],
            "fact_layers": explorer["fact_layers"],
            "operation_readback": release_model.get("operation_readback") or {},
        }
        print(
            "ADMIN_CLOSE_01_SAMPLE="
            + json.dumps(sample, ensure_ascii=False, sort_keys=True, default=str)
        )

    def test_project_ledger_denial_is_explained_without_granting_access(self):
        denied_user = self.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "ADMIN CLOSE 01 Denied User",
                "login": "admin_close_01_denied_user",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [
                    (6, 0, [self.env.ref("base.group_user").id])
                ],
            }
        )
        denied_env = self.env(user=denied_user)
        action_xmlid = self.action.get_external_id()[self.action.id]
        native_row = {
            "menu_id": int(self.menu.id),
            "menu_xmlid": PROJECT_MENU_XMLID,
            "menu_name": self.menu.name,
            "menu_path": [self.menu.name],
            "menu_sequence": self.menu.sequence,
            "action_id": int(self.action.id),
            "action_xmlid": action_xmlid,
            "action_model": self.action._name,
            "res_model": getattr(self.action, "res_model", ""),
            "view_modes": [
                value.strip()
                for value in str(getattr(self.action, "view_mode", "") or "").split(",")
                if value.strip()
            ],
            "owner_module": PROJECT_MENU_XMLID.split(".", 1)[0],
        }
        service = PlatformCapabilityExplorerService(denied_env)
        facts = service._load_native_facts([native_row], [])
        contributions = _merge_extension_contributions(
            denied_env, [native_row]
        )
        _, detail = service._build_row(
            native_row,
            facts=facts,
            contributions=contributions,
            root_menu_ids=[],
            include_detail=True,
        )
        self.assertIsNotNone(detail)
        self.assertFalse(detail["visibility"]["can_use"])
        self.assertIn(
            detail["visibility"]["reason_code"],
            {
                "ENTERPRISE_SCENARIO_NOT_ENABLED",
                "ENTRY_GROUP_DENIED",
                "MODEL_READ_ACL_DENIED",
                "MODEL_READ_ACL_MISSING",
            },
        )
        print(
            "ADMIN_CLOSE_01_DENIED_SAMPLE="
            + json.dumps(
                {
                    "entry": detail["entry_ref"],
                    "actor": detail["current_user_access"],
                    "visibility": detail["visibility"],
                    "enterprise_enablement": detail["enterprise_enablement"],
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )

    def test_r1_management_contract_enable_disable_and_readback(self):
        candidate = EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard",
            version="admin-close-01-r1-candidate",
            note="ADMIN-CLOSE-01-R1 candidate contract sample",
            replace_active=False,
        )
        self.assertEqual(candidate.get("state"), "approved")
        release_model = ReleaseOperatorReadModelService(self.actor_env).build_read_model(
            product_key="construction.standard"
        )
        promote_actions = (
            release_model.get("available_operator_actions") or {}
        ).get("promote") or []
        candidate_action = next(
            (
                action
                for action in promote_actions
                if int((action.get("params") or {}).get("snapshot_id") or 0)
                == int(candidate.get("id") or 0)
            ),
            None,
        )
        self.assertIsNotNone(candidate_action)
        for field in (
            "actor",
            "target_scope",
            "operation_object",
            "prerequisites",
            "readback",
        ):
            self.assertTrue(candidate_action.get(field), field)
        self.assertEqual(
            candidate_action["operation_object"]["snapshot_id"],
            int(candidate["id"]),
        )

        config_actor = self.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "ADMIN CLOSE 01 R1 Config Admin",
                "login": "admin_close_01_r1_config_admin",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "smart_construction_core.group_sc_cap_business_config_admin"
                            ).id,
                            *sorted(
                                set(self.menu.groups_id.ids)
                                | set(self.action.groups_id.ids)
                            ),
                        ],
                    )
                ],
            }
        )
        config_env = self.env(user=config_actor)
        catalog = _catalog(config_env, company_id=config_env.company.id)
        contribution = get_platform_capability_explorer_contributions(
            config_env,
            [int(self.menu.id)],
            {int(self.menu.id): PROJECT_MENU_XMLID},
        )
        bindings = (contribution.get("scene_bindings") or {}).get(
            str(int(self.menu.id))
        ) or []
        scene_key = next(
            (
                str(row.get("scenario_key") or "").strip()
                for row in bindings
                if isinstance(row, dict) and str(row.get("scenario_key") or "").strip()
            ),
            "",
        )
        self.assertTrue(scene_key)
        scenario = next(
            (
                row
                for row in catalog.get("business_scenarios") or []
                if row.get("scene_key") == scene_key
            ),
            None,
        )
        self.assertIsNotNone(scenario)
        self.assertTrue(scenario["enable_allowed"], scenario)

        other_company = self.env["res.company"].create(
            {"name": "ADMIN CLOSE 01 R1 Other Company"}
        )
        handler = ScenarioActivationSetHandler(config_env)
        handler.params = {}
        enable_result = handler.handle(
            {
                "company_id": config_env.company.id,
                "scene_key": scene_key,
                "enablement_scope": scenario["enablement_scope"],
                "enabled": True,
            }
        )
        self.assertTrue(enable_result["ok"], enable_result)
        enable_readback = enable_result["data"]["readback"]
        self.assertTrue(enable_readback["enabled"])
        self.assertEqual(enable_readback["source"], ENABLEMENT_STORAGE_SOURCE)
        self.assertEqual(
            enable_readback["storage_key"],
            enablement_param_key(
                config_env.company.id,
                enable_readback["stored_scene_key"],
            ),
        )
        self.assertIs(enable_readback["target_state"], True)
        self.assertFalse(enable_readback["access_granted"])
        self.assertTrue(
            read_tenant_enablement(
                config_env,
                config_env.company.id,
                enable_readback["stored_scene_key"],
            )
        )
        self.assertFalse(
            read_tenant_enablement(
                config_env,
                other_company.id,
                enable_readback["stored_scene_key"],
            )
        )

        disable_result = handler.handle(
            {
                "company_id": config_env.company.id,
                "scene_key": scene_key,
                "enablement_scope": scenario["enablement_scope"],
                "enabled": False,
            }
        )
        self.assertTrue(disable_result["ok"], disable_result)
        disable_readback = disable_result["data"]["readback"]
        self.assertFalse(disable_readback["enabled"])
        self.assertIs(disable_readback["target_state"], False)
        self.assertEqual(disable_readback["source"], ENABLEMENT_STORAGE_SOURCE)
        self.assertFalse(
            read_tenant_enablement(
                config_env,
                config_env.company.id,
                disable_readback["stored_scene_key"],
            )
        )
        self.assertFalse(
            read_tenant_enablement(
                config_env,
                other_company.id,
                disable_readback["stored_scene_key"],
            )
        )

        held_groups = config_env.user.groups_id.ids
        positive_access = access_layer_assessment(
            native_present=True,
            native_blockers=[],
            consumer_supported=True,
            held_group_ids=held_groups,
            acl_rows=[
                {
                    "read": True,
                    "group_id": group_id,
                }
                for group_id in self.env["ir.model.access"]
                .sudo()
                .search([("model_id.model", "=", "project.project"), ("perm_read", "=", True)])
                .mapped("group_id")
                .ids
            ],
            standard_qualified="qualified",
            enterprise_enablement={"status": "enabled"},
            entry_group_ids=sorted(
                set(self.menu.groups_id.ids) | set(self.action.groups_id.ids)
            ),
            menu_group_ids=self.menu.groups_id.ids,
            action_group_ids=self.action.groups_id.ids,
        )
        self.assertTrue(positive_access["entry_groups_allowed"], positive_access)

        print(
            "ADMIN_CLOSE_01_R1_SAMPLE="
            + json.dumps(
                {
                    "schema": "admin_close_01_r1.management_contract.v1",
                    "database": self.env.cr.dbname,
                    "entry": {
                        "menu_xmlid": PROJECT_MENU_XMLID,
                        "menu_id": int(self.menu.id),
                        "action_xmlid": self.action.get_external_id()[self.action.id],
                        "action_id": int(self.action.id),
                        "model": self.action.res_model,
                    },
                    "candidate": {
                        "snapshot": candidate,
                        "promote_action": candidate_action,
                    },
                    "enterprise": {
                        "company_id": config_env.company.id,
                        "other_company_id": other_company.id,
                        "scene_key": scene_key,
                        "enablement_scope": scenario["enablement_scope"],
                        "enable": enable_result["data"],
                        "disable": disable_result["data"],
                    },
                    "native_group_diagnosis": positive_access,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )

    def test_r2_release_operator_promote_and_approve_execute_real_path(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("sc.platform.control_db", self.env.cr.dbname)
        Namespace = self.env["sc.platform.namespace"].sudo()
        namespace = Namespace.search(
            [("database_name", "=", self.env.cr.dbname)],
            limit=1,
        )
        if namespace:
            namespace.write(
                {
                    "display_name": "ADMIN CLOSE 01 R2 Platform Control",
                    "lifecycle_state": "active",
                    "duty_key": "platform_control",
                    "audience": "platform-admin",
                }
            )
        else:
            namespace = Namespace.create(
                {
                    "namespace_id": "ns_00000000000f",
                    "display_name": "ADMIN CLOSE 01 R2 Platform Control",
                    "lifecycle_state": "active",
                    "database_name": self.env.cr.dbname,
                    "duty_key": "platform_control",
                    "audience": "platform-admin",
                }
            )
        self.assertTrue(namespace)
        platform_admin = self.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "ADMIN CLOSE 01 R2 Platform Admin",
                "login": "admin_close_01_r2_platform_admin",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("smart_core.group_smart_core_admin").id,
                        ],
                    )
                ],
            }
        )
        platform_env = self.env(user=platform_admin)
        instance_namespace = resolve_instance(platform_env)
        self.assertEqual(instance_namespace.audience, "platform-admin")
        with patch(
            "odoo.addons.smart_core.security.platform_admin._current_identity_audience",
            return_value="platform-admin",
        ):
            platform_scope = platform_control_scope(platform_admin, env=platform_env)
            self.assertTrue(
                platform_scope["is_platform_control_admin"],
                platform_scope,
            )
        previous_active = self.env["sc.edition.release.snapshot"].sudo().search(
            [
                ("product_key", "=", "construction.standard"),
                ("state", "=", "released"),
                ("is_active", "=", True),
                ("active", "=", True),
            ],
            order="activated_at desc, id desc",
            limit=1,
        )
        self.assertTrue(previous_active)
        candidate = EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard",
            version="admin-close-01-r2-promotion-candidate",
            note="ADMIN-CLOSE-01-R2 real promotion execution",
            replace_active=False,
        )
        candidate_id = int(candidate["id"])
        self.assertEqual(candidate["state"], "approved")

        with patch(
            "odoo.addons.smart_core.security.platform_admin._current_identity_audience",
            return_value="platform-admin",
        ):
            promote_handler = ReleaseOperatorPromoteHandler(platform_env)
            self.assertTrue(promote_handler._check_permissions())
            promote_result = promote_handler.handle(
                {
                    "product_key": "construction.standard",
                    "snapshot_id": candidate_id,
                    "replace_active": True,
                    "note": "R2 promote through formal release operator",
                }
            )
            action = promote_result["data"]["action"]
            if action["approval_state"] == "pending_approval":
                approve_handler = ReleaseOperatorApproveHandler(platform_env)
                self.assertTrue(approve_handler._check_permissions())
                approve_result = approve_handler.handle(
                    {
                        "action_id": int(action["id"]),
                        "note": "R2 approve through formal release operator",
                    }
                )
                action = approve_result["data"]["action"]
                surface = approve_result["data"]["surface"]
            else:
                surface = promote_result["data"]["surface"]
        self.assertEqual(action["state"], "done", action)
        readback = surface["operation_readback"]
        self.assertEqual(readback["product_key"], "construction.standard")
        self.assertEqual(
            int(readback["active_snapshot"]["id"]),
            candidate_id,
        )
        self.assertEqual(
            readback["active_snapshot"]["version"],
            "admin-close-01-r2-promotion-candidate",
        )
        self.assertEqual(
            int(readback["rollback_target_snapshot_id"]),
            int(previous_active.id),
        )
        self.assertEqual(
            int(action["result_snapshot_id"]),
            candidate_id,
        )
        print(
            "ADMIN_CLOSE_01_R2_PROMOTION_SAMPLE="
            + json.dumps(
                {
                    "schema": "admin_close_01_r2.release_promotion.v1",
                    "database": self.env.cr.dbname,
                    "platform_actor": {
                        "user_id": platform_admin.id,
                        "login": platform_admin.login,
                    },
                    "candidate_snapshot_id": candidate_id,
                    "action": action,
                    "operation_readback": readback,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )

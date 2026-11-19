# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE_FILE = Path(__file__).resolve()
ADDONS_ROOT = next(
    parent
    for parent in SOURCE_FILE.parents
    if (parent / "smart_core").is_dir()
    and (parent / "smart_construction_core").is_dir()
)


def _load_module(module_name: str, relative_path: str):
    path = Path(relative_path)
    target = (
        ADDONS_ROOT / path.relative_to("addons")
        if path.parts[0] == "addons"
        else SOURCE_FILE.parents[3] / path
    )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _ensure_stub_packages():
    odoo_module = sys.modules.setdefault("odoo", types.ModuleType("odoo"))
    odoo_module.api = SimpleNamespace(Environment=lambda *args, **kwargs: None)
    odoo_module.fields = SimpleNamespace(Datetime=SimpleNamespace(now=lambda: "2026-01-01 00:00:00"))
    odoo_module.SUPERUSER_ID = 1
    sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
    sys.modules.setdefault("odoo.modules", types.ModuleType("odoo.modules"))
    registry_module = sys.modules.setdefault("odoo.modules.registry", types.ModuleType("odoo.modules.registry"))
    registry_module.Registry = lambda *args, **kwargs: None
    smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
    smart_core_pkg.__path__ = [str(ADDONS_ROOT / "smart_core")]
    core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
    core_pkg.__path__ = [str(ADDONS_ROOT / "smart_core/core")]
    delivery_pkg = sys.modules.setdefault(
        "odoo.addons.smart_core.delivery",
        types.ModuleType("odoo.addons.smart_core.delivery"),
    )
    delivery_pkg.__path__ = [str(ADDONS_ROOT / "smart_core/delivery")]
    sys.modules.setdefault("odoo.exceptions", types.ModuleType("odoo.exceptions"))
    sys.modules["odoo.exceptions"].AccessError = type("AccessError", (Exception,), {})


_ensure_stub_packages()
_load_module(
    "odoo.addons.smart_core.core.scene_contract_parser_semantic_bridge",
    "addons/smart_core/core/scene_contract_parser_semantic_bridge.py",
)
_load_module(
    "odoo.addons.smart_core.core.scene_contract_semantic_orchestration_bridge",
    "addons/smart_core/core/scene_contract_semantic_orchestration_bridge.py",
)
_load_module(
    "odoo.addons.smart_core.core.released_scene_semantic_surface_bridge",
    "addons/smart_core/core/released_scene_semantic_surface_bridge.py",
)


SCENE_CONTRACT_BUILDER = _load_module(
    "smart_core_scene_contract_builder_test",
    "addons/smart_core/core/scene_contract_builder.py",
)
PRODUCT_POLICY_SERVICE = _load_module(
    "smart_core_product_policy_service_test",
    "addons/smart_core/delivery/product_policy_service.py",
)
_load_module(
    "odoo.addons.smart_core.delivery.runtime_capability_catalog",
    "addons/smart_core/delivery/runtime_capability_catalog.py",
)
PRODUCT_POLICY_CATALOG_SYNC_SERVICE = _load_module(
    "odoo.addons.smart_core.delivery.product_policy_catalog_sync_service",
    "addons/smart_core/delivery/product_policy_catalog_sync_service.py",
)
SYSTEM_INIT_ROWS = _load_module(
    "smart_construction_core_system_init_rows_test",
    "addons/smart_construction_core/core_extension_system_init_rows.py",
)


def _use_construction_catalog_source(service):
    service._catalog_source_config = lambda source_env: {
        "module": "smart_construction_core",
        "xmlid_prefix": "smart_construction_core.",
        "root_label": "智慧施工管理平台",
    }
    return service


class _FakeAction:
    def __init__(
        self,
        action_id: int,
        res_model: str = "",
        *,
        model_name: str = "",
        model_id=None,
        action_xmlid="",
        view_mode="",
    ):
        self.id = action_id
        self.res_model = res_model
        self.model_name = model_name
        self.model_id = model_id
        self.view_mode = view_mode
        self._xmlid = action_xmlid
        self._name = "ir.actions.act_window"

    def get_external_id(self):
        return {self.id: self._xmlid}


class _FakeMenu:
    def __init__(
        self,
        menu_id: int,
        name: str,
        *,
        xmlid: str,
        parent=None,
        action=None,
        sequence=10,
        active=True,
    ):
        self._name = "ir.ui.menu"
        self.id = menu_id
        self.name = name
        self.parent_id = parent
        self.action = action
        self.sequence = sequence
        self.active = active
        self._xmlid = xmlid
        self.child_id = []
        if parent is not None and hasattr(parent, "child_id"):
            parent.child_id.append(self)

    def get_external_id(self):
        return {self.id: self._xmlid}


class _FakeMenuModel:
    def __init__(self, records):
        self.records = records
        self.last_domain = None
        self.browsed_ids = []

    def sudo(self):
        return self

    def search(self, domain, order=None):
        self.last_domain = list(domain or [])
        if domain == [("action", "!=", False)]:
            return []
        return list(self.records)

    def browse(self, ids):
        self.browsed_ids = list(ids or [])
        return _FakeRecordset([record for record in self.records if record.id in self.browsed_ids])


class _FakeRecordset(list):
    def exists(self):
        return self


class _FakeModelDataRow:
    def __init__(self, res_id: int):
        self.res_id = res_id


class _FakeModelDataModel:
    def __init__(self, menu_ids):
        self.menu_ids = menu_ids
        self.last_domain = None

    def sudo(self):
        return self

    def search(self, domain):
        self.last_domain = list(domain or [])
        return [_FakeModelDataRow(menu_id) for menu_id in self.menu_ids]


class _FakeSourceEnv:
    def __init__(self, menu_model, model_data_model):
        self.menu_model = menu_model
        self.model_data_model = model_data_model

    def __getitem__(self, key):
        if key == "ir.ui.menu":
            return self.menu_model
        if key == "ir.model.data":
            return self.model_data_model
        raise KeyError(key)


class _NativeSourceEnv:
    def __init__(self, menu):
        self.menu = menu

    def ref(self, xmlid, raise_if_not_found=False):
        return self.menu if xmlid == self.menu.get_external_id().get(self.menu.id) else None


class _PolicyServiceEnv:
    registry = SimpleNamespace(models={})
    cr = SimpleNamespace(dbname="sc_test")

    def __getitem__(self, key):
        if key == "ir.config_parameter":
            return SimpleNamespace(
                sudo=lambda: SimpleNamespace(get_param=lambda *args: "")
            )
        raise KeyError(key)


class _SyncPolicyRecord:
    def __init__(self, payload):
        self.payload = deepcopy(payload)
        self.written = None

    def to_runtime_dict(self):
        return deepcopy(self.payload)

    def write(self, values):
        self.written = deepcopy(values)


class _SyncPolicyModel:
    def __init__(self, record):
        self.record = record

    def sudo(self):
        return self

    def with_context(self, **kwargs):
        return self

    def search(self, domain, limit=None):
        return self.record


class _SyncPolicyEnv:
    def __init__(self, model, *, dbname="sc_test"):
        self.model = model
        self.cr = SimpleNamespace(dbname=dbname)

    def __getitem__(self, key):
        if key == "sc.product.policy":
            return self.model
        if key == "ir.config_parameter":
            return SimpleNamespace(
                sudo=lambda: SimpleNamespace(get_param=lambda *args: "")
            )
        raise KeyError(key)


class TestBackendSemanticCopySupply(unittest.TestCase):
    def test_release_surface_contract_keeps_backend_description_and_scope(self):
        contract = SCENE_CONTRACT_BUILDER.build_release_surface_scene_contract_from_delivery_entry(
            {
                "scene_key": "payment",
                "label": "FR-4 付款记录",
                "route": "/release/fr4",
                "product_key": "fr4",
                "capability_key": "delivery.fr4.payment_tracking",
                "requires_project_context": True,
                "description": "查看与记录项目付款事实。",
                "scope": "项目执行 -> 成本 -> 付款记录 -> 付款汇总。",
            }
        )
        identity = contract.get("identity") or {}
        self.assertEqual(identity.get("description"), "查看与记录项目付款事实。")
        self.assertEqual(identity.get("scope"), "项目执行 -> 成本 -> 付款记录 -> 付款汇总。")

    def test_missing_construction_policy_uses_empty_platform_shell(self):
        service = PRODUCT_POLICY_SERVICE.ProductPolicyService(_PolicyServiceEnv())
        policy = service.get_policy(product_key="construction.standard")

        self.assertEqual(policy.get("product_key"), "construction.standard")
        self.assertEqual(((policy.get("policy_source_authority") or {}).get("kind")), "minimal_default_product_policy_provider")
        self.assertEqual(policy.get("menu_groups") or [], [])
        self.assertEqual(policy.get("scenes") or [], [])
        self.assertEqual(policy.get("capabilities") or [], [])

    def test_default_product_policy_fallback_is_provider_scoped_and_parameterized(self):
        service = PRODUCT_POLICY_SERVICE.ProductPolicyService(_PolicyServiceEnv())
        source = service.default_policy_source_authority_contract()
        policy = service.get_policy(product_key="platform.preview")

        self.assertEqual(source.get("kind"), "platform_default_product_policy_provider")
        self.assertTrue(source.get("no_business_fact_authority"))
        self.assertEqual(policy.get("product_key"), "platform.preview")
        self.assertEqual(policy.get("base_product_key"), "platform")
        self.assertEqual(policy.get("edition_key"), "preview")
        self.assertEqual(policy.get("label"), "Platform Preview")
        self.assertEqual(((policy.get("policy_source_authority") or {}).get("kind")), "minimal_default_product_policy_provider")
        self.assertEqual(policy.get("scenes") or [], [])

    def test_enterprise_enablement_contract_supplies_status_label(self):
        user = SimpleNamespace(company_id=SimpleNamespace(id=3, name="Demo Co"))
        payload = SYSTEM_INIT_ROWS.build_enterprise_enablement_contract(env=None, user=user)
        steps = (((payload or {}).get("mainline") or {}).get("steps")) or []
        self.assertTrue(steps)
        self.assertTrue(all(isinstance(row, dict) and row.get("status_label") for row in steps))

    def test_catalog_sync_extracts_project_center_when_action_domain_is_stale(self):
        root = _FakeMenu(1, "智慧施工管理平台", xmlid="smart_construction_core.menu_sc_root")
        project_center = _FakeMenu(
            2,
            "项目中心",
            xmlid="smart_construction_core.menu_sc_project_center",
            parent=root,
        )
        project_group = _FakeMenu(
            3,
            "项目管理",
            xmlid="smart_construction_core.menu_sc_project_management_group",
            parent=project_center,
        )
        project_ledger = _FakeMenu(
            4,
            "项目台账",
            xmlid="smart_construction_core.menu_sc_project_project",
            parent=project_group,
            action=_FakeAction(506, "project.project"),
        )
        menu_model = _FakeMenuModel([root, project_center, project_group, project_ledger])
        model_data_model = _FakeModelDataModel([root.id, project_center.id, project_group.id, project_ledger.id])
        service = _use_construction_catalog_source(
            PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(env=None)
        )

        pages = service._extract_user_menu_pages(_FakeSourceEnv(menu_model, model_data_model))

        self.assertEqual(menu_model.last_domain, None)
        self.assertEqual(menu_model.browsed_ids, [1, 2, 3, 4])
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["group_label"], "项目中心")
        self.assertEqual(pages[0]["visible_menu_path"], "智慧施工管理平台 / 项目中心 / 项目管理 / 项目台账")
        self.assertEqual(pages[0]["menu_xmlid"], "smart_construction_core.menu_sc_project_project")

    def test_catalog_sync_extracts_server_action_model_target(self):
        root = _FakeMenu(1, "智慧施工管理平台", xmlid="smart_construction_core.menu_sc_root")
        project_center = _FakeMenu(
            2,
            "项目中心",
            xmlid="smart_construction_core.menu_sc_project_center",
            parent=root,
        )
        project_group = _FakeMenu(
            3,
            "项目管理",
            xmlid="smart_construction_core.menu_sc_project_management_group",
            parent=project_center,
        )
        execution_structure = _FakeMenu(
            4,
            "执行结构",
            xmlid="smart_construction_core.menu_sc_project_wbs",
            parent=project_group,
            action=_FakeAction(519, model_name="project.project"),
        )
        menu_model = _FakeMenuModel([root, project_center, project_group, execution_structure])
        model_data_model = _FakeModelDataModel([root.id, project_center.id, project_group.id, execution_structure.id])
        service = _use_construction_catalog_source(
            PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(env=None)
        )

        pages = service._extract_user_menu_pages(_FakeSourceEnv(menu_model, model_data_model))

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["menu_xmlid"], "smart_construction_core.menu_sc_project_wbs")
        self.assertEqual(pages[0]["res_model"], "project.project")

    def test_catalog_sync_skips_action_directories_and_non_product_roots(self):
        root = _FakeMenu(1, "智慧施工管理平台", xmlid="smart_construction_core.menu_sc_root")
        contract_center = _FakeMenu(
            2,
            "合同中心",
            xmlid="smart_construction_core.menu_sc_contract_center",
            parent=root,
            action=_FakeAction(578, "construction.contract.income"),
        )
        income_ledger = _FakeMenu(
            3,
            "收入合同台账",
            xmlid="smart_construction_core.menu_sc_contract_income",
            parent=contract_center,
            action=_FakeAction(578, "construction.contract.income"),
        )
        native_root = _FakeMenu(10, "项目", xmlid="project.menu_main_pm")
        native_budget = _FakeMenu(
            11,
            "项目预算",
            xmlid="smart_construction_core.menu_project_budget",
            parent=native_root,
            action=_FakeAction(507, "project.budget"),
        )
        menu_model = _FakeMenuModel([root, contract_center, income_ledger, native_root, native_budget])
        model_data_model = _FakeModelDataModel([1, 2, 3, 10, 11])
        service = _use_construction_catalog_source(
            PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(env=None)
        )

        pages = service._extract_user_menu_pages(_FakeSourceEnv(menu_model, model_data_model))

        self.assertEqual([page["menu_xmlid"] for page in pages], ["smart_construction_core.menu_sc_contract_income", "smart_construction_core.menu_project_budget"])

    def test_rebound_menu_does_not_inherit_release_of_another_native_action(self):
        service = PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(env=None)
        old = {"menu_groups": [{"menus": [{"page_key": "m.menu", "menu_xmlid": "m.menu", "action_id": 10, "enabled": True, "release_state": "released"}]}]}
        new = {"menu_groups": [{"menus": [{"page_key": "native.entry.m.menu.action:11", "menu_xmlid": "m.menu", "action_id": 11, "enabled": False, "release_state": "hidden"}]}]}
        service._merge_existing_page_controls(new, old)
        self.assertFalse(new["menu_groups"][0]["menus"][0]["enabled"])
        new["menu_groups"][0]["menus"][0]["action_id"] = 10
        service._merge_existing_page_controls(new, old)
        self.assertTrue(new["menu_groups"][0]["menus"][0]["enabled"])

    def test_policy_payload_preserves_distinct_native_entries_with_same_label_and_model(self):
        service = PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(env=None)

        payload = service._build_catalog_policy_payload_from_menu_pages(
            identity={
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
            },
            menu_pages=[
                {
                    "group_key": "construction.contract",
                    "group_label": "合同中心",
                    "page_key": "smart_construction_core.menu_a",
                    "page_label": "历史采购/一般合同事实",
                    "menu_key": "smart_construction_core.menu_a",
                    "route": "/a/714?menu_id=1",
                    "app_id": "contract",
                    "menu_id": 1,
                    "menu_xmlid": "smart_construction_core.menu_a",
                    "action_id": 714,
                    "res_model": "sc.legacy.purchase.contract.fact",
                },
                {
                    "group_key": "construction.contract",
                    "group_label": "合同中心",
                    "page_key": "smart_construction_core.menu_b",
                    "page_label": "历史采购/一般合同事实",
                    "menu_key": "smart_construction_core.menu_b",
                    "route": "/a/798?menu_id=2",
                    "app_id": "contract",
                    "menu_id": 2,
                    "menu_xmlid": "smart_construction_core.menu_b",
                    "action_id": 798,
                    "res_model": "sc.legacy.purchase.contract.fact",
                },
            ],
            menu_source={"source_db": "sc_demo", "source": "test"},
        )

        menus = payload["menu_groups"][0]["menus"]
        self.assertEqual(len(menus), 2)
        self.assertEqual({row["action_id"] for row in menus}, {714, 798})
        self.assertTrue(all(not row["enabled"] and row["release_state"] == "hidden" for row in menus))
        self.assertNotEqual(menus[0]["capability_key"], menus[1]["capability_key"])
        self.assertEqual(menus[0]["menu_xmlid"], "smart_construction_core.menu_a")

    def test_existing_policy_sync_preserves_maintained_draft_and_refreshes_only_sources(self):
        service = PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(env=None)
        current = {
            "active": False,
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
            "state": "stable",
            "access_level": "role_restricted",
            "allowed_role_codes": ["project_manager"],
            "label": "Maintained construction product",
            "version": "v7",
            "scene_version_bindings": {"scene.project": {"version": "v3"}},
            "note": "",
            "menu_groups": [
                {
                    "group_key": "construction.center.project",
                    "group_label": "Admin renamed project center",
                    "sequence": 0,
                    "menus": [
                        {
                            "menu_xmlid": "project.menu_ledger",
                            "menu_key": "project.menu_ledger",
                            "menu_id": 10,
                            "page_key": "project.ledger",
                            "action_xmlid": "project.action_ledger",
                            "action_id": 11,
                            "label": "Maintained project ledger",
                            "page_label": "Maintained project ledger",
                            "sequence": 0,
                            "enabled": False,
                            "release_state": "hidden",
                            "access_level": "role_restricted",
                            "policy_note": "maintained",
                            "entry_intent": "handling",
                            "model": "project.project",
                            "res_model": "project.project",
                            "visible_menu_path": "Maintained / Project / Ledger",
                        }
                    ],
                },
                {
                    "group_key": "external.center.accounting",
                    "group_label": "External accounting",
                    "sequence": 80,
                    "menus": [
                        {
                            "menu_xmlid": "account.menu_move",
                            "menu_key": "account.menu_move",
                            "menu_id": 20,
                            "page_key": "account.move",
                            "action_xmlid": "account.action_move",
                            "action_id": 21,
                            "label": "External journal entries",
                            "sequence": 30,
                            "enabled": True,
                            "release_state": "preview",
                            "access_level": "internal",
                        }
                    ],
                },
            ],
            "scenes": [
                {
                    "scene_key": "scene.project",
                    "capability_key": "business.project.ledger",
                    "label": "Maintained project scene",
                }
            ],
            "capabilities": [
                {
                    "capability_key": "catalog.menu.project_menu_ledger",
                    "menu_xmlid": "project.menu_ledger",
                    "action_xmlid": "project.action_ledger",
                    "action_id": 11,
                    "provider_authority": "native_menu_action_entry",
                    "res_model": "project.project",
                },
                {
                    "capability_key": "business.project.ledger",
                    "menu_xmlid": "project.menu_ledger",
                    "target_page_key": "project.ledger",
                    "business_capability": True,
                    "provider_authority": "scene_entry_target",
                    "entry_intent_label": "Review",
                    "action_xmlid": "business.action.review",
                    "action_id": 99,
                    "action_model": "ir.actions.server",
                    "res_model": "custom.business.model",
                },
                {
                    "capability_key": "catalog.menu.account_menu_move",
                    "menu_xmlid": "account.menu_move",
                    "action_xmlid": "account.action_move",
                    "action_id": 21,
                    "res_model": "account.move",
                },
            ],
        }
        generated = {
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
            "state": "stable",
            "access_level": "public",
            "allowed_role_codes": [],
            "label": "Native catalog label",
            "version": "v1",
            "note": "synced from native catalog",
            "scene_version_bindings": {"scene.native": {"version": "v1"}},
            "menu_groups": [
                {
                    "group_key": "catalog.project",
                    "group_label": "Native project center",
                    "sequence": 99,
                    "menus": [
                        {
                            "menu_xmlid": "project.menu_ledger",
                            "menu_key": "project.menu_ledger",
                            "page_key": "native.project.ledger",
                            "action_xmlid": "project.action_ledger",
                            "action_id": 11,
                            "label": "Native project ledger",
                            "sequence": 77,
                            "enabled": True,
                            "release_state": "released",
                            "access_level": "public",
                            "res_model": "project.project.refreshed",
                            "visible_menu_path": "Native / Project / Ledger",
                            "view_modes": ["tree", "form"],
                        },
                        {
                            "menu_xmlid": "project.menu_new_catalog_entry",
                            "menu_key": "project.menu_new_catalog_entry",
                            "page_key": "project.new",
                            "action_xmlid": "project.action_new",
                            "action_id": 12,
                            "label": "Newly discovered",
                            "sequence": 90,
                            "enabled": False,
                            "release_state": "hidden",
                        },
                    ],
                }
            ],
            "scenes": [{"scene_key": "scene.native"}],
            "capabilities": [
                {
                    "capability_key": "catalog.menu.project_menu_ledger",
                    "menu_xmlid": "project.menu_ledger",
                    "action_xmlid": "project.action_ledger",
                    "action_id": 11,
                    "res_model": "project.project.refreshed",
                },
                {
                    "capability_key": "catalog.menu.project_menu_new_catalog_entry",
                    "menu_xmlid": "project.menu_new_catalog_entry",
                    "action_xmlid": "project.action_new",
                    "action_id": 12,
                    "res_model": "project.new",
                },
            ],
            "policy_source_authority": {
                "source": "current_db_ir_ui_menu",
                "source_db": "sc_test",
            },
        }

        business_capability_before = deepcopy(current["capabilities"][1])

        def native_source(row):
            if row["menu_xmlid"] == "project.menu_ledger":
                return {
                    "menu_id": 110,
                    "menu_xmlid": "project.menu_ledger",
                    "menu_key": "project.menu_ledger",
                    "action_id": 111,
                    "action_xmlid": "project.action_ledger",
                    "action_model": "ir.actions.act_window",
                    "res_model": "project.project",
                    "model": "project.project",
                    "view_modes": ["tree", "form"],
                    "visible_menu_path": "Native / Project / Ledger",
                }
            self.assertEqual(row["menu_xmlid"], "account.menu_move")
            return {
                "menu_id": 201,
                "menu_xmlid": "account.menu_move",
                "menu_key": "account.menu_move",
                "action_id": 21,
                "action_xmlid": "account.action_move",
                "action_model": "ir.actions.act_window",
                "res_model": "account.move",
                "model": "account.move",
                "visible_menu_path": "Accounting / Journal Entries",
            }

        service._read_native_source_facts = native_source
        values = service.build_sync_values(
            payload=generated,
            current=current,
            identity={
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
            },
        )

        self.assertFalse(values["active"])
        self.assertEqual(values["allowed_role_codes"], ["project_manager"])
        self.assertEqual(values["label"], "Maintained construction product")
        self.assertEqual(values["version"], "v7")
        self.assertEqual(values["note"], "")
        self.assertEqual(
            values["scene_version_bindings"],
            {"scene.project": {"version": "v3"}},
        )
        self.assertEqual(values["scenes"], current["scenes"])
        self.assertEqual(
            [group["group_key"] for group in values["menu_groups"]],
            ["construction.center.project", "external.center.accounting"],
        )
        project_group = values["menu_groups"][0]
        self.assertEqual(project_group["group_label"], "Admin renamed project center")
        self.assertEqual(project_group["sequence"], 0)
        self.assertEqual(len(project_group["menus"]), 1)
        project_menu = project_group["menus"][0]
        self.assertEqual(project_menu["label"], "Maintained project ledger")
        self.assertEqual(project_menu["sequence"], 0)
        self.assertFalse(project_menu["enabled"])
        self.assertEqual(project_menu["release_state"], "hidden")
        self.assertEqual(project_menu["access_level"], "role_restricted")
        self.assertEqual(project_menu["policy_note"], "maintained")
        self.assertEqual(project_menu["entry_intent"], "handling")
        self.assertEqual(project_menu["page_key"], "project.ledger")
        self.assertEqual(project_menu["menu_id"], 110)
        self.assertEqual(project_menu["action_id"], 111)
        self.assertEqual(project_menu["model"], "project.project")
        self.assertEqual(project_menu["res_model"], "project.project")
        self.assertEqual(project_menu["visible_menu_path"], "Native / Project / Ledger")
        self.assertEqual(project_menu["view_modes"], ["tree", "form"])
        self.assertEqual(
            values["menu_groups"][1]["menus"][0]["label"],
            "External journal entries",
        )
        capability_keys = {
            row["capability_key"] for row in values["capabilities"]
        }
        self.assertIn("business.project.ledger", capability_keys)
        self.assertIn("catalog.menu.account_menu_move", capability_keys)
        self.assertNotIn(
            "catalog.menu.project_menu_new_catalog_entry",
            capability_keys,
        )
        business_capability = next(
            row
            for row in values["capabilities"]
            if row["capability_key"] == "business.project.ledger"
        )
        self.assertTrue(business_capability["business_capability"])
        self.assertEqual(business_capability["provider_authority"], "scene_entry_target")
        self.assertEqual(business_capability["entry_intent_label"], "Review")
        self.assertEqual(business_capability, business_capability_before)

        repeated = service.build_sync_values(
            payload=generated,
            current=values,
            identity={
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
            },
        )
        self.assertEqual(repeated, values)

    def test_native_source_read_returns_execution_ids_and_uniform_model_path(self):
        root = _FakeMenu(
            1,
            "Project",
            xmlid="project.menu_root",
        )
        center = _FakeMenu(
            2,
            "Ledger",
            xmlid="project.menu_center",
            parent=root,
        )
        action = _FakeAction(
            31,
            "project.project",
            action_xmlid="project.action_ledger",
            view_mode="tree,form",
        )
        menu = _FakeMenu(
            21,
            "Ledger Entries",
            xmlid="project.menu_ledger",
            parent=center,
            action=action,
        )
        service = PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(
            _NativeSourceEnv(menu)
        )

        source = service._read_native_source_facts({"menu_xmlid": "project.menu_ledger"})

        self.assertEqual(source["menu_id"], 21)
        self.assertEqual(source["action_id"], 31)
        self.assertEqual(source["action_xmlid"], "project.action_ledger")
        self.assertEqual(source["action_model"], "ir.actions.act_window")
        self.assertEqual(source["model"], "project.project")
        self.assertEqual(source["res_model"], "project.project")
        self.assertEqual(source["view_modes"], ["tree", "form"])
        self.assertEqual(source["visible_menu_path"], "Project / Ledger / Ledger Entries")

    def test_non_catalog_sync_uses_native_truth_and_rejects_before_write(self):
        current = {
            "active": True,
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
            "state": "stable",
            "access_level": "public",
            "allowed_role_codes": [],
            "label": "Construction",
            "version": "v1",
            "scene_version_bindings": {},
            "note": "",
            "menu_groups": [
                {
                    "group_key": "construction.center.project",
                    "menus": [
                        {
                            "menu_xmlid": "project.menu_ledger",
                            "menu_key": "project.menu_ledger",
                            "page_key": "project.ledger",
                            "menu_id": 21,
                            "action_xmlid": "project.action_ledger",
                            "action_id": 31,
                            "action_model": "ir.actions.act_window",
                            "model": "project.project",
                            "res_model": "project.project",
                            "sequence": 0,
                            "enabled": True,
                        }
                    ],
                }
            ],
            "scenes": [],
            "capabilities": [],
        }
        identity = {
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
        }
        for failure, reason_code in (
            ("missing", "PRODUCT_SYNC_SOURCE_MISSING"),
            ("model_rebind", "PRODUCT_SYNC_ACTION_IDENTITY_CHANGED"),
            ("action_type_rebind", "PRODUCT_SYNC_ACTION_IDENTITY_CHANGED"),
        ):
            with self.subTest(failure=failure):
                record = _SyncPolicyRecord(current)
                service = PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(
                    _SyncPolicyEnv(_SyncPolicyModel(record))
                )
                service._is_catalog_backed_product = lambda *, identity: False

                def native_source(_row):
                    if failure == "missing":
                        raise PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncError(
                            "PRODUCT_SYNC_SOURCE_MISSING",
                            "native menu source not found",
                            entry="project.menu_ledger",
                        )
                    return {
                        "menu_id": 21,
                        "menu_xmlid": "project.menu_ledger",
                        "menu_key": "project.menu_ledger",
                        "action_id": 31,
                        "action_xmlid": "project.action_ledger",
                        "action_model": (
                            "ir.actions.server"
                            if failure == "action_type_rebind"
                            else "ir.actions.act_window"
                        ),
                        "res_model": "account.move",
                        "model": "account.move",
                    }

                service._read_native_source_facts = native_source
                with patch.object(
                    PRODUCT_POLICY_CATALOG_SYNC_SERVICE,
                    "resolve_product_identity",
                    return_value=identity,
                ), patch.object(
                    PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyService,
                    "get_policy",
                    return_value=current,
                ):
                    with self.assertRaisesRegex(
                        PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncError,
                        reason_code,
                    ):
                        service.sync_policy(product_key="construction.standard")
                self.assertIsNone(record.written)
                self.assertEqual(record.to_runtime_dict(), current)

    def test_sync_resolves_catalog_xmlids_to_execution_database_ids(self):
        service = PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(env=None)
        current = {
            "active": True,
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
            "state": "stable",
            "access_level": "public",
            "allowed_role_codes": [],
            "label": "Construction",
            "version": "v1",
            "scene_version_bindings": {},
            "note": "",
            "menu_groups": [{
                "group_key": "construction.center.project",
                "menus": [{
                    "menu_xmlid": "project.menu_ledger",
                    "menu_key": "project.menu_ledger",
                    "menu_id": 21,
                    "action_xmlid": "project.action_ledger",
                    "action_id": 31,
                    "model": "project.project",
                    "res_model": "project.project",
                    "enabled": True,
                }],
            }],
            "scenes": [],
            "capabilities": [{
                "capability_key": "catalog.menu.project_menu_ledger",
                "menu_xmlid": "project.menu_ledger",
                "action_xmlid": "project.action_ledger",
                "action_id": 31,
                "model": "stale.model",
                "res_model": "project.project",
            }],
        }
        external_payload = {
            **deepcopy(current),
            "menu_groups": [{
                "group_key": "catalog.project",
                "menus": [{
                    "menu_xmlid": "project.menu_ledger",
                    "menu_key": "project.menu_ledger",
                    "menu_id": 101,
                    "action_xmlid": "project.action_ledger",
                    "action_id": 201,
                    "res_model": "project.project",
                    "model": "project.project",
                }],
            }],
            "policy_source_authority": {
                "source": "external_db_ir_ui_menu",
                "source_db": "catalog_db",
            },
        }
        service._read_native_source_facts = lambda _row: {
            "menu_id": 21,
            "menu_xmlid": "project.menu_ledger",
            "menu_key": "project.menu_ledger",
            "action_id": 31,
            "action_xmlid": "project.action_ledger",
            "action_model": "ir.actions.act_window",
            "res_model": "project.project",
            "model": "project.project",
        }
        values = service.build_sync_values(
            payload=external_payload,
            current=current,
            identity={
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
            },
        )
        menu = values["menu_groups"][0]["menus"][0]
        capability = values["capabilities"][0]
        self.assertEqual((menu["menu_id"], menu["action_id"]), (21, 31))
        self.assertEqual(
            (
                capability["action_id"],
                capability["model"],
                capability["res_model"],
            ),
            (31, "project.project", "project.project"),
        )
        self.assertEqual(menu["model"], menu["res_model"])

    def test_initial_sync_uses_execution_ids_for_catalog_sources(self):
        service = PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(env=None)
        external_payload = {
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
            "state": "stable",
            "access_level": "public",
            "allowed_role_codes": [],
            "label": "Construction",
            "version": "v1",
            "scene_version_bindings": {},
            "menu_groups": [{
                "group_key": "catalog.project",
                "menus": [{
                    "menu_xmlid": "project.menu_ledger",
                    "menu_key": "project.menu_ledger",
                    "menu_id": 101,
                    "action_xmlid": "project.action_ledger",
                    "action_id": 201,
                    "model": "project.project",
                    "res_model": "project.project",
                }],
            }],
            "scenes": [],
            "capabilities": [{
                "capability_key": "catalog.menu.project_menu_ledger",
                "menu_xmlid": "project.menu_ledger",
                "action_xmlid": "project.action_ledger",
                "action_id": 201,
                "model": "stale.model",
                "res_model": "project.project",
            }],
            "policy_source_authority": {
                "source": "external_db_ir_ui_menu",
                "source_db": "catalog_db",
            },
        }
        service._read_native_source_facts = lambda _row: {
            "menu_id": 21,
            "menu_xmlid": "project.menu_ledger",
            "menu_key": "project.menu_ledger",
            "action_id": 31,
            "action_xmlid": "project.action_ledger",
            "action_model": "ir.actions.act_window",
            "res_model": "project.project",
            "model": "project.project",
        }

        values = service.build_sync_values(
            payload=external_payload,
            current={},
            identity={
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
            },
        )

        menu = values["menu_groups"][0]["menus"][0]
        capability = values["capabilities"][0]
        self.assertEqual((menu["menu_id"], menu["action_id"]), (21, 31))
        self.assertEqual((menu["model"], menu["res_model"]), (
            "project.project",
            "project.project",
        ))
        self.assertEqual((capability["action_id"], capability["model"]), (
            31,
            "project.project",
        ))

    def test_current_database_catalog_read_failure_is_stable_and_zero_write(self):
        current = {
            "active": True,
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
            "state": "stable",
            "access_level": "public",
            "allowed_role_codes": [],
            "label": "Construction",
            "version": "v1",
            "scene_version_bindings": {},
            "note": "",
            "menu_groups": [],
            "scenes": [],
            "capabilities": [],
        }
        record = _SyncPolicyRecord(current)
        service = PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(
            _SyncPolicyEnv(_SyncPolicyModel(record))
        )
        service._is_catalog_backed_product = lambda *, identity: True
        service._catalog_product_label = lambda *, identity: "Construction"
        service._extract_user_menu_pages = lambda _env: (_ for _ in ()).throw(
            RuntimeError("catalog read exploded")
        )
        with patch.object(
            PRODUCT_POLICY_CATALOG_SYNC_SERVICE,
            "resolve_product_identity",
            return_value={
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
            },
        ):
            with self.assertRaisesRegex(
                PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncError,
                "PRODUCT_SYNC_SOURCE_READ_FAILED",
            ):
                service.sync_policy(product_key="construction.standard")
        self.assertIsNone(record.written)
        self.assertEqual(record.to_runtime_dict(), current)

    def test_sync_rejects_catalog_source_read_failure_and_keeps_empty_policy(self):
        current = {
            "active": False,
            "product_key": "construction.standard",
            "base_product_key": "construction",
            "edition_key": "standard",
            "state": "stable",
            "access_level": "public",
            "allowed_role_codes": [],
            "label": "Archived empty policy",
            "version": "v1",
            "scene_version_bindings": {},
            "note": "",
            "menu_groups": [],
            "scenes": [],
            "capabilities": [],
        }
        payload = {
            **current,
            "policy_source_authority": {
                "source": "external_db_ir_ui_menu_failed",
                "error": "source database unavailable",
            },
        }
        service = PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncService(
            env=None
        )
        with self.assertRaisesRegex(
            PRODUCT_POLICY_CATALOG_SYNC_SERVICE.ProductPolicyCatalogSyncError,
            "PRODUCT_SYNC_SOURCE_READ_FAILED",
        ):
            service.build_sync_values(
                payload=payload,
                current=current,
                identity={
                    "product_key": "construction.standard",
                    "base_product_key": "construction",
                    "edition_key": "standard",
                },
            )
        self.assertFalse(current["active"])
        self.assertEqual(current["menu_groups"], [])

        usable_payload = deepcopy(payload)
        usable_payload["policy_source_authority"] = {
            "source": "current_db_ir_ui_menu",
            "source_db": "sc_test",
        }
        usable_payload["menu_groups"] = [
            {
                "group_key": "catalog.project",
                "menus": [
                    {
                        "menu_xmlid": "project.menu_discovered",
                        "action_xmlid": "project.action_discovered",
                        "action_id": 41,
                    }
                ],
            }
        ]
        values = service.build_sync_values(
            payload=usable_payload,
            current=current,
            identity={
                "product_key": "construction.standard",
                "base_product_key": "construction",
                "edition_key": "standard",
            },
        )
        self.assertFalse(values["active"])
        self.assertEqual(values["menu_groups"], [])
        self.assertEqual(values["capabilities"], [])


if __name__ == "__main__":
    unittest.main()

import copy
import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "delivery"
    / "platform_capability_explorer.py"
)
SPEC = importlib.util.spec_from_file_location(
    "platform_capability_explorer_under_test",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def native_row(**overrides):
    row = {
        "menu_id": 10,
        "menu_xmlid": "smart_construction_core.menu_project_ledger",
        "menu_name": "项目台账",
        "menu_path": ["智慧施工管理平台", "项目中心", "项目台账"],
        "menu_sequence": 20,
        "action_id": 20,
        "action_xmlid": "smart_construction_core.action_project_ledger",
        "action_model": "ir.actions.act_window",
        "res_model": "project.project",
        "view_modes": ["tree", "form"],
        "owner_module": "smart_construction_core",
    }
    row.update(overrides)
    return row


def native_projection(rows=None, root_menu_ids=None):
    return SimpleNamespace(
        rows=[native_row()] if rows is None else rows,
        diagnostics={
            "root_menu_ids": [1] if root_menu_ids is None else root_menu_ids,
            "capability_count": 1,
        },
    )


def native_facts(rows=None, root_menu_ids=None):
    return {
        "menus": {
            1: {
                "id": 1,
                "xmlid": "smart_construction_core.menu_sc_root",
                "name": "智慧施工管理平台",
                "parent_path": "1/",
                "sequence": 1,
                "groups": [],
            },
            2: {
                "id": 2,
                "xmlid": "smart_construction_core.menu_sc_project_center",
                "name": "项目中心",
                "parent_path": "1/2/",
                "sequence": 10,
                "groups": [],
            },
            10: {
                "id": 10,
                "xmlid": "smart_construction_core.menu_project_ledger",
                "name": "项目台账",
                "parent_path": "1/2/10/",
                "sequence": 20,
                "groups": ["smart_construction_core.group_sc_entry_p01"],
            },
        },
        "actions": {
            20: {
                "id": 20,
                "xmlid": "smart_construction_core.action_project_ledger",
                "type": "ir.actions.act_window",
                "res_model": "project.project",
                "groups": ["smart_construction_core.group_sc_project_read"],
            }
        },
        "modules": {
            "smart_construction_core": {
                "name": "smart_construction_core",
                "state": "installed",
                "version": "17.0.0.182",
                "dependencies": ["project", "smart_core"],
            }
        },
        "models": {
            "project.project": {
                "name": "project.project",
                "description": "项目",
            }
        },
        "fields": {
            "project.project": [
                {"name": "name", "type": "char", "required": True, "readonly": False}
            ]
        },
        "field_counts": {"project.project": 1},
        "views": {
            "project.project": {
                "count": 4,
                "sha256": "view-sha-v1",
            }
        },
        "acl": {
            "project.project": {
                "row_count": 2,
                "group_xmlids": ["smart_construction_core.group_sc_project_read"],
                "sha256": "acl-sha-v1",
            }
        },
        "rules": {
            "project.project": {
                "count": 2,
                "group_xmlids": ["smart_construction_core.group_sc_project_read"],
                "sha256": "rule-sha-v1",
            }
        },
        "installed_modules": [
            {
                "name": "smart_construction_core",
                "state": "installed",
                "version": "17.0.0.182",
            }
        ],
        "root_menu_ids": [1] if root_menu_ids is None else root_menu_ids,
    }


def contributions():
    return {
        "scene_bindings": {
            "10": [
                {
                    "entry_id": 101,
                    "scenario_key": "project.management",
                    "scenario_name": "项目管理",
                    "scenario_active": True,
                    "scenario_sequence": 10,
                    "sequence": 10,
                    "intent": "contract",
                }
            ]
        },
        "release_states": {
            "smart_construction_core.menu_project_ledger": "released"
        },
        "release_centers": {
            "smart_construction_core.menu_project_ledger": {
                "key": "project_management",
                "label": "项目管理",
                "sequence": 10,
            }
        },
        "product_qualifications": {},
        "release_snapshots": [
            {
                "product_key": "construction.standard",
                "applied": True,
                "snapshot_id": 5,
                "version": "v5",
                "fingerprint": "release-v5",
            }
        ],
        "scene_authority_available": True,
        "release_authority_available": True,
        "providers": [{"module": "smart_construction_core", "status": "ok"}],
        "conflicts": [],
        "token_facts": [{"scene_version": "v1"}],
    }


def identity(language="zh_CN"):
    return {
        "database": "sc_test",
        "source_revision": "a" * 40,
        "language": {"code": language, "name": language, "active": True},
    }


def build_service(
    *,
    rows=None,
    facts=None,
    contribution_payload=None,
    language="zh_CN",
    clock=None,
):
    rows = [native_row()] if rows is None else rows
    facts = native_facts(rows) if facts is None else facts
    contribution_payload = contributions() if contribution_payload is None else contribution_payload
    return MODULE.PlatformCapabilityExplorerService(
        None,
        native_collector=lambda: native_projection(rows),
        facts_loader=lambda current_rows, root_ids: copy.deepcopy(facts),
        contribution_loader=lambda current_rows: copy.deepcopy(contribution_payload),
        identity_loader=lambda: identity(language),
        clock=clock or (lambda: datetime(2026, 11, 15, 1, 2, 3, tzinfo=timezone.utc)),
    )


class ClassificationTests(unittest.TestCase):
    def test_single_scene_binding_is_the_only_business_domain_authority(self):
        result = MODULE.classify_business_domain(
            scene_bindings=[
                {
                    "scenario_key": "project.management",
                    "scenario_name": "项目管理",
                    "scenario_active": True,
                }
            ],
            center_key="smart_construction_core.menu_sc_project_center",
        )
        self.assertEqual(result["key"], "project.management")
        self.assertEqual(result["confidence"], "authoritative_scene_binding")
        self.assertEqual(result["source"], "sc.product.scenario.entry")

    def test_native_center_never_guesses_a_business_domain(self):
        result = MODULE.classify_business_domain(
            scene_bindings=[],
            center_key="smart_construction_core.menu_sc_project_center",
        )
        self.assertEqual(result["key"], "")
        self.assertEqual(result["confidence"], "center_only")
        self.assertEqual(result["reason_code"], "NO_SCENE_BINDING")

    def test_multiple_active_scene_bindings_are_ambiguous(self):
        result = MODULE.classify_business_domain(
            scene_bindings=[
                {"scenario_key": "project.management", "scenario_active": True},
                {"scenario_key": "cost.budget", "scenario_active": True},
            ],
            center_key="smart_construction_core.menu_sc_project_center",
        )
        self.assertEqual(result["key"], "")
        self.assertEqual(result["confidence"], "unclassified")
        self.assertEqual(result["reason_code"], "AMBIGUOUS_SCENE_BINDING")


class ProjectionContractTests(unittest.TestCase):
    def test_row_keeps_classification_technical_and_qualification_facts_separate(self):
        payload = contributions()
        payload["product_qualifications"] = {
            "smart_construction_core.menu_project_ledger": {
                "preview": "qualified",
                "standard": "not_verified",
            }
        }
        projection = build_service(contribution_payload=payload).project(
            include_details=True
        )
        row = projection.rows[0]
        detail = projection.details[
            (
                "smart_construction_core.menu_project_ledger",
                "smart_construction_core.action_project_ledger",
            )
        ]
        self.assertEqual(
            row["business_domain"]["confidence"],
            "authoritative_scene_binding",
        )
        self.assertTrue(row["draft_eligibility"]["selectable"])
        self.assertTrue(detail["scene_assignment"]["assignable"])
        self.assertEqual(row["product_qualification"]["preview"], "qualified")
        self.assertEqual(row["product_qualification"]["standard"], "not_verified")
        self.assertEqual(row["release_state"], "released")

    def test_missing_scene_authority_blocks_assignment_without_changing_native_validity(self):
        payload = contributions()
        payload["scene_authority_available"] = False
        projection = build_service(contribution_payload=payload).project(
            include_details=True
        )
        key = (
            "smart_construction_core.menu_project_ledger",
            "smart_construction_core.action_project_ledger",
        )
        detail = projection.details[key]
        self.assertTrue(detail["diagnostics"]["native_valid"])
        self.assertFalse(detail["diagnostics"]["draft_selectable"] is False)
        self.assertFalse(detail["diagnostics"]["scene_assignable"])
        self.assertEqual(
            detail["scene_assignment"]["blockers"],
            ["SCENE_AUTHORITY_UNAVAILABLE"],
        )

    def test_token_changes_for_every_participating_fact_family(self):
        baseline = build_service().project().token
        mutations = []

        language_service = build_service(language="en_US")
        mutations.append(("language", language_service.project().token))

        facts = native_facts()
        facts["modules"]["smart_construction_core"]["version"] = "17.0.0.183"
        mutations.append(("module", build_service(facts=facts).project().token))

        rows = [native_row(menu_name="Project ledger")]
        mutations.append(("menu", build_service(rows=rows).project().token))

        facts = native_facts()
        facts["views"]["project.project"]["sha256"] = "view-sha-v2"
        mutations.append(("view", build_service(facts=facts).project().token))

        facts = native_facts()
        facts["acl"]["project.project"]["sha256"] = "acl-sha-v2"
        mutations.append(("acl", build_service(facts=facts).project().token))

        facts = native_facts()
        facts["rules"]["project.project"]["sha256"] = "rule-sha-v2"
        mutations.append(("rule", build_service(facts=facts).project().token))

        payload = contributions()
        payload["scene_bindings"]["10"][0]["scenario_key"] = "cost.budget"
        mutations.append(("scene", build_service(contribution_payload=payload).project().token))

        payload = contributions()
        payload["release_snapshots"][0]["fingerprint"] = "release-v6"
        mutations.append(("release", build_service(contribution_payload=payload).project().token))

        for name, token in mutations:
            with self.subTest(name=name):
                self.assertNotEqual(token, baseline)

    def test_token_is_scoped_to_the_current_database(self):
        baseline = build_service().project().token
        service = build_service()
        service._identity_loader = lambda: {
            **identity(),
            "database": "sc_other_tenant",
        }
        self.assertNotEqual(service.project().token, baseline)

    def test_list_is_stable_paginated_and_rejects_stale_token(self):
        second = native_row(
            menu_id=11,
            menu_xmlid="smart_construction_core.menu_second",
            action_id=21,
            action_xmlid="smart_construction_core.action_second",
            menu_name="项目A",
            menu_sequence=10,
        )
        facts = native_facts()
        facts["menus"][11] = {
            **facts["menus"][10],
            "id": 11,
            "xmlid": second["menu_xmlid"],
            "name": second["menu_name"],
            "sequence": 10,
        }
        facts["actions"][21] = {
            **facts["actions"][20],
            "id": 21,
            "xmlid": second["action_xmlid"],
        }
        service = build_service(rows=[second, native_row()], facts=facts)
        first = service.list_entries({"limit": 1, "offset": 0})
        self.assertTrue(first["meta"]["has_more"])
        self.assertEqual(first["meta"]["filtered_total"], 2)
        self.assertEqual(first["meta"]["next_offset"], 1)
        self.assertEqual(first["rows"][0]["label"], "项目A")
        with self.assertRaises(MODULE.CatalogStaleError):
            service.list_entries(
                {
                    "expected_catalog_token": "sha256:stale",
                }
            )

    def test_list_filters_do_not_infer_unknown_business_domains(self):
        payload = contributions()
        payload["scene_bindings"] = {}
        result = build_service(contribution_payload=payload).list_entries(
            {
                "filters": {
                    "classification_confidence": ["center_only"],
                    "business_domain_keys": ["unclassified"],
                }
            }
        )
        self.assertEqual(result["meta"]["filtered_total"], 1)
        self.assertEqual(
            result["meta"]["diagnostics"]["performance"]["query_count"],
            0,
        )

    def test_detail_and_diagnose_require_exact_native_identity(self):
        service = build_service()
        detail = service.detail(
            {
                "entry_ref": {
                    "menu_xmlid": "smart_construction_core.menu_project_ledger",
                    "action_xmlid": "smart_construction_core.action_project_ledger",
                }
            }
        )
        self.assertEqual(detail["entry"]["native_facts"]["views"]["count"], 4)
        diagnose = service.diagnose(
            {
                "entry_ref": detail["entry"]["entry_ref"],
            }
        )
        self.assertTrue(diagnose["native_valid"])
        self.assertTrue(diagnose["draft_selectable"])
        self.assertTrue(diagnose["scene_assignable"])
        self.assertEqual(diagnose["preview_qualified"], "not_verified")
        with self.assertRaises(MODULE.CapabilityEntryNotFound):
            service.detail(
                {
                    "entry_ref": {
                        "menu_xmlid": "smart_construction_core.missing",
                        "action_xmlid": "smart_construction_core.missing_action",
                    }
                }
            )

    def test_sort_is_allowlisted_and_always_has_native_tie_breakers(self):
        service = build_service()
        result = service.list_entries({"sort": "label:desc"})
        self.assertEqual(
            result["meta"]["sort"],
            ["label:desc", "menu_xmlid:asc", "action_xmlid:asc"],
        )
        with self.assertRaises(MODULE.InvalidExplorerRequest):
            service.list_entries({"sort": "arbitrary_sql:asc"})

    def test_handler_source_declares_all_three_read_only_intents_and_permission_gate(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "handlers"
            / "platform_capability_explorer.py"
        ).read_text(encoding="utf-8")
        self.assertIn('INTENT_TYPE = "platform.capability.explorer.list"', source)
        self.assertIn('INTENT_TYPE = "platform.capability.explorer.detail"', source)
        self.assertIn('INTENT_TYPE = "platform.capability.explorer.diagnose"', source)
        self.assertIn("def _check_permissions", source)
        self.assertIn("raise AccessError", source)
        self.assertNotIn("cross_database_target", source)


if __name__ == "__main__":
    unittest.main()

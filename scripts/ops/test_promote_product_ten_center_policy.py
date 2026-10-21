#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import unittest
import tempfile
from pathlib import Path

from scripts.ops.promote_product_ten_center_policy import (
    BASELINE,
    TARGET_CENTERS,
    promote, load_source, project, artifacts, resolve_native_source, native_facts, SOURCE_PATH,
)


class ProductTenCenterPolicyPromotionTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(BASELINE.read_text(encoding="utf-8"))

    def test_promotion_is_idempotent_and_preserves_unique_identity(self):
        first = promote(copy.deepcopy(self.payload))
        second = promote(copy.deepcopy(first))
        self.assertEqual(first, second)
        declared = second["policy_strategy"]["menu_count_by_product"]
        for product in second["products"]:
            self.assertEqual([group["group_label"] for group in product["menu_groups"]], list(TARGET_CENTERS))
            rows = [menu for group in product["menu_groups"] for menu in group["menus"]]
            xmlids = [row["menu_xmlid"] for row in rows]
            # The promoted surface must equal the count the contract declares;
            # the number itself is contract data and is expected to iterate.
            self.assertEqual(len(rows), declared[product["product_key"]])
            self.assertEqual(len(xmlids), len(set(xmlids)))

    def test_retired_centers_are_absent_and_accounting_is_real(self):
        promoted = promote(copy.deepcopy(self.payload))
        product = promoted["products"][0]
        groups = {group["group_label"]: group for group in product["menu_groups"]}
        self.assertFalse({"物资与分包", "施工管理", "组织行政", "配置中心"}.intersection(groups))
        expected = {
            "account.menu_action_move_journal_line_form", "account.menu_action_account_moves_all",
            "account.menu_action_account_form", "smart_construction_core.menu_sc_account_journal_foundation",
            "smart_construction_core.menu_sc_analytic_account_foundation", "smart_construction_core.menu_sc_analytic_distribution_foundation",
        }
        actual = {row["menu_xmlid"] for row in groups["会计账务中心"]["menus"]}
        self.assertEqual(actual, expected)
        self.assertFalse(actual.intersection({"account.menu_action_account_journal_form", "account.account_analytic_def_account", "account.menu_analytic__distribution_model"}))
        self.assertEqual(
            sum(xmlid.startswith("smart_construction_core.") for xmlid in actual),
            3,
        )
        self.assertTrue(all(row.get("action_xmlid") and row.get("res_model") for row in groups["会计账务中心"]["menus"]))

    def test_unapproved_first_level_center_fails_closed(self):
        payload = copy.deepcopy(self.payload)
        payload["products"][0]["menu_groups"][0]["group_label"] = "临时中心"
        with self.assertRaisesRegex(ValueError, "unapproved first-level"):
            promote(payload)

    def test_only_project_center_uses_level_three(self):
        promoted = promote(copy.deepcopy(self.payload))
        for product in promoted["products"]:
            for group in product["menu_groups"]:
                for row in group["menus"]:
                    depth = len([part for part in row["visible_menu_path"].split(" / ") if part])
                    if group["group_label"] == "项目中心":
                        self.assertEqual(depth, 4)
                    else:
                        self.assertEqual(depth, 3)

    def test_iterating_finance_entries_publish_only_in_preview_without_permission_overrides(self):
        raw = json.loads(SOURCE_PATH.read_text())
        keys = {"smart_construction_core." + key for key in (
            "menu_payment_ledger", "menu_sc_treasury_ledger", "menu_sc_settlement_order")}
        selected = [row for row in raw["entries"] if row["menu_xmlid"] in keys]
        self.assertEqual(len(selected), 3)
        for row in selected:
            self.assertEqual(row["release_state"], "preview")
            self.assertFalse({"groups_id", "required_roles", "readonly", "domain"} & set(row))
        _, publication = project(load_source())
        for product in publication["products"]:
            rows = {row["menu_xmlid"]: row for group in product["menu_groups"] for row in group["menus"]}
            if product["edition_key"] == "standard":
                self.assertFalse(keys & set(rows))
            else:
                self.assertTrue(keys <= set(rows))
                for key in keys:
                    self.assertEqual(rows[key]["release_state"], "preview")
                    self.assertEqual(rows[key]["action_xmlid"], native_facts()[key]["action"])

    def test_unreleased_quick_creation_is_only_in_preview(self):
        _, publication = project(load_source())
        for product in publication["products"]:
            quick = [row for group in product["menu_groups"] for row in group["menus"] if row["menu_xmlid"] == "smart_construction_core.menu_sc_project_quick_create"]
            if product["edition_key"] == "standard":
                self.assertEqual(quick, [])
                continue
            self.assertEqual(len(quick), 1)
            self.assertEqual(quick[0]["action_xmlid"], "smart_construction_core.action_project_initiation_quick")
            self.assertEqual(quick[0]["visible_menu_path"], "智慧施工管理平台 / 项目中心 / 项目创建 / 快速创建项目")

    def test_generated_copies_cannot_drift_from_source(self):
        for path, expected in artifacts().items():
            self.assertEqual(path.read_text(encoding="utf-8"), expected, str(path))

    def test_duplicate_identity_fails_closed(self):
        source = load_source()
        leaves = source["product_contract"]["centers"][0]["level_two"]
        leaves[1]["binding"]["menu_xmlid"] = leaves[0]["binding"]["menu_xmlid"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            project(source)

    def test_missing_native_target_fails_closed(self):
        source = load_source()
        source["product_contract"]["centers"][0]["level_two"][1]["binding"].pop("action_xmlid")
        with self.assertRaisesRegex(ValueError, "action and model"):
            project(source)

    def test_publication_template_cannot_supply_second_menu_facts(self):
        source = load_source()
        source["product_policy_profiles"]["products"][0]["menu_groups"] = []
        with self.assertRaisesRegex(ValueError, "redefine menu facts"):
            project(source)

    def test_source_change_projects_all_carriers_without_editing_ops(self):
        source = load_source()
        leaf = source["product_contract"]["centers"][1]["level_two"][0]["children"][1]
        leaf["name"] = "测试快速入口"
        contract, publication = project(source)
        self.assertEqual(contract["centers"][1]["level_two"][0]["children"][1]["name"], "测试快速入口")
        for product in publication["products"]:
            if product["edition_key"] == "standard":
                continue
            row = next(row for group in product["menu_groups"] for row in group["menus"] if row["menu_xmlid"] == leaf["binding"]["menu_xmlid"])
            self.assertEqual(row["label"], "测试快速入口")
            self.assertTrue(row["visible_menu_path"].endswith(" / 测试快速入口"))

    def test_native_fact_change_flows_without_second_menu_declaration(self):
        raw = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        facts = native_facts()
        key = "smart_construction_core.menu_sc_project_quick_create"
        facts[key]["name"] = "原生新名称"
        contract, publication = project(resolve_native_source(raw, facts))
        for product in publication["products"]:
            if product["edition_key"] == "standard":
                continue
            row = next(row for group in product["menu_groups"] for row in group["menus"] if row["menu_xmlid"] == key)
            self.assertEqual(row["label"], "原生新名称")
            self.assertTrue(row["visible_menu_path"].endswith(" / 原生新名称"))
            self.assertEqual(row["view_modes"], ["form"])

    def test_native_move_flows_and_inactive_publication_fails(self):
        raw = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        facts = native_facts()
        key = "smart_construction_core.menu_sc_project_quick_create"
        facts[key]["parent_id"] = "smart_construction_core.menu_sc_project_partner_group_wave1"
        _, publication = project(resolve_native_source(raw, facts))
        row = next(row for group in publication["products"][1]["menu_groups"] for row in group["menus"] if row["menu_xmlid"] == key)
        self.assertIn(" / 客商管理 / ", row["visible_menu_path"])
        facts[key]["active"] = "False"
        with self.assertRaisesRegex(ValueError, "inactive"):
            resolve_native_source(raw, facts)

    def test_own_menu_source_has_no_duplicate_native_facts(self):
        raw = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        for entry in raw["entries"]:
            if entry["menu_xmlid"].startswith("smart_construction_core."):
                self.assertFalse(set(entry) & {"name", "label", "action_xmlid", "model", "parent_id", "sequence", "external_presentation"})

    def test_native_parent_inactive_and_duplicate_facts_are_rejected(self):
        raw = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        facts = native_facts()
        facts["smart_construction_core.menu_sc_project_management_group"]["active"] = "False"
        with self.assertRaisesRegex(ValueError, "inactive native parent"):
            resolve_native_source(raw, facts)
        raw["entries"][0]["name"] = "another authority"
        with self.assertRaisesRegex(ValueError, "redefine native facts"):
            resolve_native_source(raw)

    def test_shared_dependency_does_not_replay_old_menu_over_a_later_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            definitions = {
                "base_product": ([], '<record id="menu" model="ir.ui.menu"><field name="name">original</field></record>'),
                "first": (["base_product"], '<record id="base_product.menu" model="ir.ui.menu"><field name="name">override</field></record>'),
                "second": (["base_product"], ''),
                "product": (["first", "second"], ''),
            }
            for module, (dependencies, xml) in definitions.items():
                folder = root / module
                folder.mkdir()
                (folder / "__manifest__.py").write_text(repr({"depends":dependencies,"data":["menus.xml"]}))
                (folder / "menus.xml").write_text("<odoo>" + xml + "</odoo>")
            self.assertEqual(native_facts(root / "product")["base_product.menu"]["name"], "override")

    def test_menu_configuration_uses_native_platform_action(self):
        _, publication = project(load_source())
        for product in publication["products"]:
            if product["edition_key"] == "standard":
                continue
            row = next(row for group in product["menu_groups"] for row in group["menus"] if row["menu_xmlid"] == "smart_construction_core.menu_ui_menu_config_policy_business_config")
            self.assertEqual(row["action_xmlid"], "smart_core.action_ui_menu_config_policy")
            self.assertEqual(row["res_model"], "ui.menu.config.policy")
            self.assertEqual(row["visible_menu_path"], "智慧施工管理平台 / 产品配置 / 菜单配置")

    def test_external_adaptation_requires_unavailable_source_and_provenance(self):
        raw = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        external = next(row for row in raw["entries"] if row.get("external_presentation"))
        external["external_presentation"].pop("integration_reason")
        with self.assertRaisesRegex(ValueError, "integration reason"):
            resolve_native_source(raw)
        external["external_presentation"]["integration_reason"] = "test adapter"
        external["menu_xmlid"] = "smart_core.unresolved_menu"
        external["external_presentation"]["source_module"] = "smart_core"
        with self.assertRaisesRegex(ValueError, "module-owned"):
            resolve_native_source(raw)

    def test_selection_cannot_shadow_native_permissions_or_view_facts(self):
        raw = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        for field in ("groups_id", "domain", "view_id", "view_modes", "readonly", "active"):
            with self.subTest(field=field):
                candidate = copy.deepcopy(raw)
                candidate["entries"][0][field] = "duplicate authority"
                with self.assertRaisesRegex(ValueError, "redefine native facts"):
                    resolve_native_source(candidate)

    def test_external_accounting_placement_preserves_existing_product_order(self):
        _, publication = project(load_source())
        for product in publication["products"]:
            group = next(group for group in product["menu_groups"] if group["group_label"] == "会计账务中心")
            rows = group["menus"]
            self.assertEqual([row["menu_xmlid"] for row in sorted(rows, key=lambda row: row["sequence"])],
                             [row["menu_xmlid"] for row in rows])
        raw = json.loads(SOURCE_PATH.read_text())
        next(row for row in raw["entries"] if row.get("external_presentation"))["external_presentation"].pop("sequence")
        with self.assertRaisesRegex(ValueError, "placement sequence"):
            resolve_native_source(raw)

    def test_edition_projection_and_promotion_share_one_native_identity(self):
        source = load_source()
        def menus(payload):
            return {product["edition_key"]: {row["menu_xmlid"]: row for group in product["menu_groups"] for row in group["menus"]} for product in payload["products"]}
        before = menus(project(source)[1])
        self.assertEqual(len(before["standard"]), 91)
        self.assertTrue({
            "smart_construction_core.menu_sc_project_quick_create",
        } <= set(before["preview"]) - set(before["standard"]))
        self.assertIn("smart_construction_core.menu_ui_menu_config_policy_business_config", before["standard"])
        for key, row in before["standard"].items():
            self.assertEqual(row, before["preview"][key])
            self.assertEqual(row["release_state"], "released")
        leaf = source["product_contract"]["centers"][1]["level_two"][0]["children"][1]
        key = leaf["binding"]["menu_xmlid"]
        self.assertEqual(before["preview"][key]["release_state"], "preview")
        leaf["binding"]["release_state"] = "released"
        after = menus(project(source)[1])
        self.assertEqual(set(after["standard"]) - set(before["standard"]), {key})
        self.assertEqual(set(after["preview"]), set(before["preview"]))
        self.assertEqual(after["standard"][key], after["preview"][key])

    def test_missing_state_and_standard_preview_widening_fail_closed(self):
        raw = json.loads(SOURCE_PATH.read_text())
        raw["entries"][0].pop("release_state")
        with self.assertRaisesRegex(ValueError, "explicit release state"):
            resolve_native_source(raw)
        source = load_source()
        source["product_policy_profiles"]["products"][0]["included_release_states"].append("preview")
        with self.assertRaisesRegex(ValueError, "edition release scope"):
            project(source)

    def test_retired_experimental_entry_cannot_enter_preview(self):
        raw = json.loads(SOURCE_PATH.read_text())
        retired = raw["excluded_entries"][0]
        self.assertEqual(retired["disposition"], "retired_experiment")
        raw["entries"].append({"menu_xmlid": retired["menu_xmlid"], "release_state": "preview", "delivery": "PREVIEW_FOUNDATION", "source_kind": "p1_locked_menu_surface_projection"})
        with self.assertRaisesRegex(ValueError, "retired product entry"):
            resolve_native_source(raw)


if __name__ == "__main__":
    unittest.main()

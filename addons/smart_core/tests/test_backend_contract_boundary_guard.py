# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "verify" / "backend_contract_boundary_guard.py"
DOC_PATH = Path(__file__).resolve().parents[3] / "docs" / "architecture" / "backend_contract_boundaries.md"
spec = importlib.util.spec_from_file_location("backend_contract_boundary_guard", MODULE_PATH)
guard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(guard)


class BackendContractBoundaryGuardTests(unittest.TestCase):
    def test_guard_report_is_classified_and_clean(self):
        report = guard.build_report()

        self.assertEqual(report["guard"], "backend_contract_boundary_guard")
        self.assertEqual(report["schema_version"], "1.0")
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["contract_writer_count"], 6)
        self.assertEqual(report["approval_policy_writer_count"], 1)
        self.assertEqual(report["lowcoding_policy_writer_count"], 5)
        self.assertEqual(report["writer_boundary_count"], 12)
        self.assertEqual(report["writer_file_count"], 8)
        self.assertIn("addons/smart_core/handlers/form_field_configuration.py", report["writer_paths"])
        self.assertIn("addons/smart_core/handlers/menu_configuration.py", report["writer_paths"])
        self.assertEqual(
            {row["category"] for row in report["writers"]},
            {
                "business_config_contract",
                "approval_policy_runtime",
                "lowcoding_policy_runtime",
            },
        )

    def test_guard_rules_are_declared_once(self):
        rules = guard.BOUNDARY_RULES

        self.assertEqual(
            [rule["category"] for rule in rules],
            [
                "business_config_contract",
                "approval_policy_runtime",
                "lowcoding_policy_runtime",
            ],
        )
        for rule in rules:
            self.assertIn("report_key", rule)
            self.assertIn("rows_key", rule)
            self.assertIn("count_key", rule)
            self.assertTrue(callable(rule["predicate"]))
            self.assertTrue(rule["allowed"])

    def test_contract_appearance_rule_rejects_client_structure(self):
        leaks = guard.scan_contract_appearance(
            'payload = {"sections": [{"label": "表单字段与布局", "appearance": "section-tab"}]}',
            "addons/smart_core/handlers/business_config_surface.py",
        )
        dom_leaks = guard.scan_contract_appearance(
            'row = {"role": "tab", "aria-label": "配置类型"}\nmarkup = "<div class=\'x\'></div>"',
            "addons/smart_core/handlers/business_config_surface.py",
        )
        clean = guard.scan_contract_appearance(
            'row = {"label": "表单字段与布局", "boundary": "business_contract"}',
            "addons/smart_core/handlers/business_config_surface.py",
        )

        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0]["line"], 1)
        self.assertTrue(dom_leaks)
        self.assertEqual(clean, [])

    def test_managed_layout_channel_is_not_outlawed_by_the_appearance_rule(self):
        # 布局契约是合法的一层：arch 投影与低代码呈现配置用它表达顺序、分组、显隐、
        # 列集合和受管尺寸档位。外观规则不得把它当成外观。
        for key in guard.MANAGED_LAYOUT_CHANNEL_KEYS:
            with self.subTest(key=key):
                self.assertEqual(
                    guard.scan_contract_appearance('"%s": 1,' % key, "managed-layout-channel"),
                    [],
                )
        self.assertEqual(guard.managed_layout_channel_conflicts(), [])
        self.assertEqual(
            guard.scan_contract_appearance(
                'section = {"group_title": "结算信息", "visible": True, "sequence": 10, '
                '"columns": 2, "cols": 2, "field_size": "wide"}\n'
                'layout = {"layoutType": "form", "layoutHints": {"group_title": "结算信息"}}\n'
                'contract = {"layoutContract": {"containerTree": [{"class": "o_group"}]}, '
                '"listProfile": {}, "pivotProfile": {}}',
                "addons/smart_core/handlers/form_field_configuration.py",
            ),
            [],
        )
        # 受管布局通道放行，不等于外观规则失效：设计系统内部取值仍被拦下。
        self.assertTrue(
            guard.scan_contract_appearance('hint = {"density": "compact"}', "managed-layout-channel")
        )

    def test_terminal_bound_contract_is_rejected(self):
        # 同一份契约要驱动 Web、移动 App 等终端；契约带上终端维度就开始按终端分叉。
        leaked = guard.scan_terminal_bound_contract(
            'payload = {"render_target": "form"}\n'
            'brand = {"terminal_overrides": {"mobile": 1}}\n'
            'scope = {"platform": "mobile"}',
            "addons/smart_core/handlers/form_field_configuration.py",
        )
        preview_scope = guard.scan_terminal_bound_contract(
            'preview = {"device": _text(params.get("device")) if _text(params.get("device"))'
            ' in {"desktop", "tablet", "mobile"} else "desktop"}',
            "addons/smart_core/handlers/business_config_change_set.py",
        )

        self.assertEqual(len(leaked), 3)
        self.assertEqual([row["line"] for row in leaked], [1, 2, 3])
        # 草稿预览作用域是 runtime carrier，不写回已发布契约。
        self.assertEqual(preview_scope, [])

    def test_multi_terminal_boundary_is_declared_and_clean(self):
        report = guard.build_report()

        self.assertEqual(report["managed_layout_channel_conflicts"], [])
        self.assertEqual(report["terminal_bound_contract_errors"], [])
        self.assertIn("layoutContract", report["managed_layout_channel_keys"])
        self.assertIn("field_size", report["managed_layout_channel_keys"])

    def test_report_keys_match_declared_rules(self):
        report = guard.build_report()

        for rule in guard.BOUNDARY_RULES:
            self.assertIn(rule["report_key"], report)
            self.assertIn(rule["rows_key"], report)
            self.assertIn(rule["count_key"], report)
            self.assertEqual(report[rule["count_key"]], len(report[rule["rows_key"]]))
            self.assertEqual(
                sorted(row["path"] for row in report[rule["report_key"]]),
                sorted(rule["allowed"]),
            )

    def test_guard_tracks_expected_writer_boundaries(self):
        report = guard.build_report()
        by_boundary = {
            (row["path"], row["boundary"]): row
            for row in report["writers"]
        }
        allowed_by_boundary = {
            (row["path"], row["boundary"]): row
            for row in report["allowed_lowcoding_policy_runtime_writers"]
        }

        self.assertEqual(
            by_boundary[
                ("addons/smart_core/handlers/business_config_change_set.py", "atomic_lowcode_change_set_publish")
            ]["expected_source"],
            "ui.business.config.change.set",
        )
        self.assertEqual(
            by_boundary[
                ("addons/smart_core/handlers/form_field_configuration.py", "form_lowcode_runtime_config")
            ]["expected_source"],
            "smart_core.lowcode.form_field_policy",
        )
        self.assertEqual(
            by_boundary[
                ("addons/smart_core/handlers/form_field_configuration.py", "form_field_policy_runtime_configuration")
            ]["target_models"],
            ["ui.form.field.policy"],
        )
        self.assertEqual(
            by_boundary[
                ("addons/smart_core/handlers/menu_configuration.py", "menu_lowcode_runtime_config")
            ]["expected_source"],
            "smart_core.lowcode.menu_config",
        )
        self.assertEqual(
            by_boundary[
                (
                    "addons/smart_construction_core/handlers/approval_policy_configuration.py",
                    "approval_policy_runtime_configuration",
                )
            ]["expected_source"],
            "smart_core.lowcode.approval_policy",
        )
        self.assertEqual(
            allowed_by_boundary[
                (
                    "addons/smart_construction_core/models/support/product_policy_sync.py",
                    "industry_product_menu_policy_projection",
                )
            ]["layer"],
            "L2",
        )
        self.assertEqual(
            by_boundary[
                (
                    "addons/smart_construction_core/migrations/17.0.0.61/post-migration.py",
                    "industry_stale_contract_scope_cleanup_migration",
                )
            ]["expected_source"],
            "smart_construction_core.stale_contract_scope_cleanup",
        )
        self.assertEqual(
            allowed_by_boundary[
                (
                    "addons/smart_construction_core/migrations/17.0.0.61/post-migration.py",
                    "industry_product_menu_policy_baseline_migration",
                )
            ]["expected_source"],
            "smart_construction_core.config_center_label_migration",
        )
        self.assertEqual(
            allowed_by_boundary[
                ("addons/smart_core/handlers/menu_configuration.py", "menu_config_policy_runtime_configuration")
            ]["expected_source"],
            "smart_core.lowcode.menu_config",
        )

    def test_boundary_document_lists_allowed_writer_paths(self):
        report = guard.build_report()
        document = DOC_PATH.read_text(encoding="utf-8")

        for row in report["writers"]:
            self.assertIn(row["path"], document)
            self.assertIn(row["boundary"], document)
            self.assertIn(str(row["expected_source"]), document)


if __name__ == "__main__":
    unittest.main()

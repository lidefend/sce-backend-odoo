from __future__ import annotations

import unittest
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PARTNER_VIEWS = ROOT / "addons/smart_construction_core/views/support/account_extend_views.xml"
DECISION = ROOT / "docs/architecture/native_first_form_structure_authority_v1.md"


def _form(record_id: str) -> ET.Element:
    root = ET.parse(PARTNER_VIEWS).getroot()
    record = root.find(f".//record[@id='{record_id}']")
    if record is None:
        raise AssertionError(f"missing view record: {record_id}")
    arch = record.find("field[@name='arch']")
    if arch is None:
        raise AssertionError(f"missing arch: {record_id}")
    form = arch.find("form")
    if form is None:
        raise AssertionError(f"missing form: {record_id}")
    return form


class FormStructureAuthorityUnificationTest(unittest.TestCase):
    def _run_bridge_guard(self, changed_path=None, replacement=None):
        import contextlib
        import io
        import runpy
        import sys
        from unittest import mock

        original_read = Path.read_text

        def read(path, *args, **kwargs):
            if path == changed_path:
                return replacement
            return original_read(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", read), mock.patch.object(sys, "path", [str(ROOT / "scripts/verify"), *sys.path]), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(ROOT / "scripts/verify/frontend_scene_component_bridge_guard.py"), run_name="__main__")

    def test_native_surface_guard_accepts_current_extracted_bridge(self):
        self._run_bridge_guard()

    def test_native_surface_guard_rejects_broken_bridge_bindings(self):
        folder = ROOT / "frontend/apps/web/src/pages/contractForm"
        for file, original, broken in (
            ("ContractFormDriverHost.vue", ':native-bridge="nativeBridge"', ':native-bridge="null"'),
            ("ContractFormDriverHost.vue", ':render-mode="renderModel.identity.mode"', ':render-mode="\'edit\'"'),
            ("ContractFormDriverHost.vue", ':section-links="workspaceSectionLinks"', ':section-links="[]"'),
            ("ContractFormDriverHost.vue", '@action-ref="emit(\'action-ref\', $event)"', '@action-ref="undefined"'),
            ("CanonicalNativeFormSurface.vue", ':nodes="nativeBridge.subordinateNodes"', ':nodes="nativeBridge.primaryNodes"'),
            ("CanonicalNativeFormSurface.vue", ':is-node-visible="nativeBridge.nodeVisible"', ':is-node-visible="() => true"'),
            ("CanonicalNativeFormSurface.vue", ':native-action-state-resolver="nativeBridge.actionStateForNode"', ':native-action-state-resolver="undefined"'),
            ("CanonicalNativeFormSurface.vue", "if (action) emit('action-ref', action)", "emit('action-ref', payload)"),
        ):
            with self.subTest(file=file, binding=original):
                path = folder / file
                source = path.read_text()
                # For host action forwarding, mutate only the extracted surface call.
                start = source.index("<CanonicalNativeFormSurface") if file == "ContractFormDriverHost.vue" else 0
                prefix, tail = source[:start], source[start:]
                self.assertIn(original, tail)
                changed = prefix + tail.replace(original, broken, 1)
                with self.assertRaisesRegex(SystemExit, "governed native surface bridge"):
                    self._run_bridge_guard(path, changed)

    def test_structure_policy_guard_accepts_formal_enum_but_rejects_legacy_aliases(self):
        import contextlib
        import io
        from unittest import mock
        from scripts.verify import frontend_v2_policy_projection_guard as guard

        source = guard.STRICT_SCHEMA.read_text(encoding="utf-8")
        self.assertIn('"const": "container_tree_authority"', guard.BACKEND_SCHEMA.read_text(encoding="utf-8"))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(guard.main(), 0)
            for forbidden in ("raw.container_tree", "root.form_structure_contract"):
                with self.subTest(forbidden=forbidden), mock.patch.object(guard, "STRICT_SCHEMA", wraps=guard.STRICT_SCHEMA) as schema:
                    schema.read_text.return_value = source + "\nconst invalid = " + forbidden + ";\n"
                    self.assertEqual(guard.main(), 1)

    def test_tender_groups_preserve_contents_without_promoting_internal_titles(self):
        root = ET.parse(ROOT / "addons/smart_construction_core/views/support/tender_views.xml")
        form = root.find(".//record[@id='view_tender_bid_form']/field[@name='arch']/form")
        sheet = form.find("sheet")
        sections = [g for g in sheet.findall("group") if g.get("invisible") != "1"]
        self.assertEqual([g.get("string") for g in sections],
                         ["投标信息", "中标事实确认", "清单", "投标过程", "资料与备注"])
        for anchor, fields in {
            "tender-process": {"doc_purchase_ids", "survey_ids", "review_ids", "opening_ids", "guarantee_ids"},
            "tender-materials": {"tech_attachment_ids", "biz_attachment_ids", "note"},
        }.items():
            section = next(g for g in sections if g.get("data-sc-anchor") == anchor)
            children = section.findall("group")
            self.assertEqual({f.get("name") for g in children for f in g.findall("field")}, fields)
            self.assertTrue(all(g.get("data-sc-navigation-role") == "subordinate" for g in children))
            self.assertTrue(all(g.get("data-sc-anchor") and g.get("col") == "1" for g in children))
        source = form.find(".//field[@name='award_opening_id']")
        self.assertEqual(source.get("domain"), "[('bid_id','=',id),('result','=','won')]")
        self.assertEqual(source.get("readonly"), "award_confirmed_at")

    def test_opening_result_label_is_native_in_inline_list_and_record_views(self):
        root = ET.parse(ROOT / "addons/smart_construction_core/views/support/tender_views.xml")
        for view in ("view_tender_bid_form", "view_tender_opening_tree", "view_tender_opening_form", "view_tender_opening_search"):
            result = root.find(f".//record[@id='{view}']/field[@name='arch']/.//field[@name='result']")
            self.assertIsNotNone(result, view)
            self.assertEqual(result.get("string"), "开标结果", view)

    def test_customer_native_sections_are_the_only_page_level_business_groups(self) -> None:
        form = _form("view_sc_customer_partner_form")
        sheet = form.find("sheet")
        self.assertIsNotNone(sheet)
        direct_groups = sheet.findall("group")  # type: ignore[union-attr]
        actual = [
            (group.get("data-sc-anchor"), group.get("string"), group.get("col"))
            for group in direct_groups
        ]
        self.assertEqual(
            actual,
            [
                ("customer-basic", "基本资料", "3"),
                ("customer-registration", "工商信息", "3"),
                ("customer-contact-details", "联系方式", "3"),
                ("customer-finance", "账户与财务", "3"),
                ("customer-contacts", "联系人", "1"),
                ("customer-bank-accounts", "账户明细", "1"),
                ("customer-notes", "附件与备注", "1"),
            ],
        )
        self.assertNotIn("业务信息", {group.get("string") for group in form.iter("group")})
        self.assertNotIn("关联业务明细", {group.get("string") for group in form.iter("group")})

    def test_customer_relation_collections_keep_full_width_native_ownership(self) -> None:
        form = _form("view_sc_customer_partner_form")
        expected = {
            "child_ids": "customer-contacts",
            "bank_ids": "customer-bank-accounts",
        }
        for field_name, anchor in expected.items():
            field = form.find(f".//field[@name='{field_name}']")
            self.assertIsNotNone(field)
            owning_group = next(
                group
                for group in form.iter("group")
                if group.get("data-sc-anchor") == anchor
            )
            self.assertEqual(owning_group.get("col"), "1")
            self.assertIn(field, list(owning_group))

    def test_customer_business_groups_preserve_distinct_authorities(self) -> None:
        form = _form("view_sc_customer_partner_form")
        groups = {g.get("data-sc-anchor"): {f.get("name") for f in g.findall("field")}
                  for g in form.find("sheet").findall("group")}
        self.assertEqual(groups["customer-basic"], {"name", "company_type", "is_company", "active", "user_id", "category_id"})
        self.assertIn("vat", groups["customer-registration"])
        self.assertIn("phone", groups["customer-contact-details"])
        self.assertTrue({"sc_bank_account", "sc_default_tax_rate", "sc_default_tax_rate_text"}.issubset(groups["customer-finance"]))
        self.assertEqual(groups["customer-bank-accounts"], {"bank_ids"})

    def test_compatibility_retirement_has_a_measurable_terminal_condition(self) -> None:
        text = DECISION.read_text(encoding="utf-8")
        self.assertIn("正式 89 菜单范围的兼容消费者归零后", text)
        self.assertIn("删除后端二次结构解释", text)
        self.assertIn("禁止无明确退役日期地新增", text)


def load_tests(loader, tests, pattern):
    # Existing owning-layer suites, reused under this registered focused entry.
    for name in ("test_view_orchestrator", "test_ui_contract_v2_boundaries"):
        path = ROOT / "addons/smart_core/tests" / (name + ".py")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tests.addTests(loader.loadTestsFromModule(module))
    path = ROOT / "scripts/verify/test_local_dev_candidate_frontend.py"
    spec = importlib.util.spec_from_file_location("candidate_frontend_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tests.addTests(loader.loadTestsFromModule(module))
    return tests


if __name__ == "__main__":
    unittest.main()

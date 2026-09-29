# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[1] / "core"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


sys.modules.setdefault("odoo", types.ModuleType("odoo"))
sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
smart_core_pkg.__path__ = [str(CORE_DIR.parent)]
core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
core_pkg.__path__ = [str(CORE_DIR)]
smart_core_pkg.core = core_pkg

parser_bridge = _load_module(
    "odoo.addons.smart_core.core.page_contract_parser_semantic_bridge",
    CORE_DIR / "page_contract_parser_semantic_bridge.py",
)
core_pkg.page_contract_parser_semantic_bridge = parser_bridge
semantic_bridge = _load_module(
    "odoo.addons.smart_core.core.page_contract_semantic_orchestration_bridge",
    CORE_DIR / "page_contract_semantic_orchestration_bridge.py",
)
core_pkg.page_contract_semantic_orchestration_bridge = semantic_bridge

target = _load_module(
    "odoo.addons.smart_core.core.page_contracts_builder",
    CORE_DIR / "page_contracts_builder.py",
)


class TestPageContractsBuilderBoundaries(unittest.TestCase):
    def test_public_auth_projection_is_bounded_and_canonical(self):
        public = target.build_public_auth_page_contracts()
        self.assertEqual(set(public), {"schema_version", "pages"})
        self.assertEqual(set(public["pages"]), {"login", "account_activation", "password_recovery"})
        for key, page in public["pages"].items():
            self.assertEqual(set(page), {"schema_version", "texts", "sections", "page_orchestration"})
            self.assertEqual(set(page["page_orchestration"]), {"page", "action_schema", "zones", "data_sources"})
            for name, action in page["page_orchestration"]["action_schema"]["actions"].items():
                self.assertEqual(action["target"], target._action_target(name, key))
                self.assertEqual(action["target"]["kind"], "route.path")
                self.assertIn(action["target"]["path"], {"/login", "/activate-account", "/password-recovery"})
        self.assertEqual(public["pages"]["password_recovery"]["page_orchestration"]["action_schema"]["actions"]["open_login"]["target"]["path"], "/login")

    def test_public_projection_has_no_identity_or_private_page_data(self):
        def check(value):
            if isinstance(value, dict):
                self.assertFalse(set(value) & {"role_code", "role_source_code", "role_variant", "navigation", "company_id", "user_id", "context", "diagnostics"})
                for item in value.values():
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)
        check(target.build_public_auth_page_contracts())

    def test_public_sections_keep_the_canonical_consumption_structure(self):
        for page in target.build_public_auth_page_contracts()["pages"].values():
            orchestration = page["page_orchestration"]
            blocks = [block for zone in orchestration["zones"] for block in zone["blocks"]]
            self.assertEqual({block["section_key"] for block in blocks}, {section["key"] for section in page["sections"]})
            for block in blocks:
                self.assertTrue(orchestration["data_sources"][block["data_source"]]["source_type"])
                section = next(row for row in page["sections"] if row["key"] == block["section_key"])
                self.assertEqual(block["payload"]["enabled"], section["enabled"])
                self.assertEqual(block["payload"]["tag"], section["tag"])

    def test_public_projection_has_no_caller_context_parameter(self):
        with self.assertRaises(TypeError):
            target.build_public_auth_page_contracts({"role_code": "owner"})

    def test_page_contract_builder_declares_projection_source(self):
        source = target.source_authority_contract()

        self.assertEqual(source.get("kind"), "page_contract_projection")
        self.assertTrue(source.get("projection_only"))
        self.assertTrue(source.get("no_business_fact_authority"))
        self.assertEqual(source.get("page_text_override_source"), "page_text_override_projection")

    def test_page_text_override_boundary_is_declared(self):
        payload = target.build_page_contracts({})
        diagnostics = payload.get("diagnostics") or {}

        self.assertEqual((payload.get("source_authority") or {}).get("kind"), "page_contract_projection")
        self.assertEqual(
            ((diagnostics.get("page_text_override_source_authority") or {}).get("kind")),
            "page_text_override_projection",
        )
        self.assertTrue(((diagnostics.get("page_text_override_source_authority") or {}).get("no_business_fact_authority")))

    def test_page_text_overrides_are_applied_from_profile_overrides(self):
        payload = target.build_page_contracts(
            {
                "page_profile_overrides": {
                    "page_texts": {
                        "login": {
                            "brand_name": "行业产品平台",
                        }
                    }
                }
            }
        )

        self.assertEqual(payload["pages"]["login"]["texts"]["brand_name"], "行业产品平台")


if __name__ == "__main__":
    unittest.main()

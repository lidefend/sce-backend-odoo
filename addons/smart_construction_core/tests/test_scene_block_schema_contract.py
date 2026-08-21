from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "services" / "scene_block_schema.py"
SPEC = importlib.util.spec_from_file_location("scene_block_schema_contract_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SceneBlockSchemaContractTest(unittest.TestCase):
    def test_builder_projects_canonical_page_contract_and_datasets(self) -> None:
        block = MODULE.metric_card(
            "project_total",
            "项目总数",
            3,
            target=MODULE.action_target(action_xmlid="x.action_projects"),
        )
        contract = MODULE.build_contract(
            scene_key="workspace.home",
            title="角色首页",
            blocks=[block],
        )

        self.assertEqual(contract["schema_version"], "2.0.0")
        orchestration = contract["page_orchestration"]
        self.assertEqual(orchestration["contract_version"], "2.0.0")
        self.assertEqual(orchestration["schema_version"], "2.0.0")
        self.assertEqual(orchestration["zones"][0]["blocks"][0]["data_source"], "ds_project_total")
        self.assertEqual(contract["datasets"]["ds_project_total"][0]["value"], 3)

    def test_builder_has_no_legacy_version_carriers(self) -> None:
        contract = MODULE.build_contract(
            scene_key="workspace.home",
            title="角色首页",
            blocks=[],
        )
        rendered = repr(contract)
        self.assertNotIn("scene_contract", rendered)
        self.assertNotIn("page_orchestration_v1", rendered)
        self.assertNotIn("block_schema_v1", rendered)


if __name__ == "__main__":
    unittest.main()

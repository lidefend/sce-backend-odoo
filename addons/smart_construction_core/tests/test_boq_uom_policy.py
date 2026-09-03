# -*- coding: utf-8 -*-
"""BOQ 导入计量单位白名单策略单测（R-G2-01）。

纯常量模块直测：不依赖 Odoo 运行时。
"""
import importlib.util
import sys
import unittest
from pathlib import Path


def _load_policy():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "boq_uom_policy_under_test", root / "wizard" / "boq_uom_policy.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BoqUomWhitelistPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = _load_policy()
        self.whitelist = self.policy.UOM_AUTO_CREATE_WHITELIST

    def test_whitelist_covers_construction_standard_units(self):
        for unit in ["项", "m", "m2", "m3", "km", "t", "kg", "根", "套", "台", "工日", "台班", "元", "%"]:
            self.assertIn(unit, self.whitelist, unit)

    def test_whitelist_rejects_garbage_and_unbounded_names(self):
        for unit in ["", "  ", "abc", "100m", "very-long-garbage-unit-name", "项；DROP TABLE", "车"]:
            self.assertNotIn(unit.strip() or unit, self.whitelist, unit)

    def test_whitelist_is_frozen_and_lowercase_canonical(self):
        self.assertIsInstance(self.whitelist, frozenset)
        # 规范名一律小写（与向导 _normalize_uom_name 的全角转半角+小写口径一致）
        for unit in self.whitelist:
            self.assertEqual(unit, unit.lower(), unit)
            self.assertEqual(unit, unit.strip(), unit)

    def test_module_has_no_odoo_runtime_dependency(self):
        source = (Path(__file__).resolve().parents[1] / "wizard" / "boq_uom_policy.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("from odoo", "import odoo", "models.TransientModel", "fields.", "api."):
            self.assertNotIn(forbidden, source, forbidden)


if __name__ == "__main__":
    unittest.main()

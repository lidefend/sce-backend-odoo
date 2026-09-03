# -*- coding: utf-8 -*-
"""G3.3-A ProjectBoqPreviewBuilder 单元测试（桩加载模式，零 Odoo 运行时）。

builder 与 base 模块均无 Odoo 运行时依赖；base 含相对导入，需伪造
包上下文后 spec_from_file_location 加载（模式仿
test_boq_import_preview_fetch_handler.py 的桩加载）。
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


BUILDERS_DIR = Path(
    __file__).resolve().parents[1] / "services" / "project_dashboard_builders"

PKG = "sc_test_dash_builders"

_pkg = types.ModuleType(PKG)
_pkg.__path__ = [str(BUILDERS_DIR)]
sys.modules[PKG] = _pkg


def _load(dotted_name, relpath):
    spec = importlib.util.spec_from_file_location(dotted_name, BUILDERS_DIR / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = module
    spec.loader.exec_module(module)
    return module


base_mod = _load(f"{PKG}.base", "base.py")
builder_mod = _load(f"{PKG}.project_boq_preview_builder", "project_boq_preview_builder.py")


class _FakeBatchModel:
    def __init__(self, count):
        self._count = int(count)
        self._fields = {"project_id": True}
        self.domains = []

    def search_count(self, domain):
        self.domains.append(list(domain or []))
        return self._count


class _FakeEnv(dict):
    pass


class _FakeProject:
    def __init__(self, pid):
        self.id = int(pid)


class TestProjectBoqPreviewBuilder(unittest.TestCase):
    def _builder(self, batch_count=0):
        env = _FakeEnv({"project.boq.import.batch": _FakeBatchModel(batch_count)})
        return builder_mod.ProjectBoqPreviewBuilder(env), env

    def test_block_identity(self):
        builder, _ = self._builder()
        self.assertEqual(builder.block_key, "block.project.boq_preview")
        self.assertEqual(builder.block_type, "boq_import_preview")

    def test_empty_when_no_project(self):
        builder, _ = self._builder()
        envelope = builder.build(project=None, context=None)
        self.assertEqual(envelope["state"], "empty")
        self.assertEqual(envelope["data"]["project_id"], 0)
        self.assertEqual(envelope["data"]["batch_count"], 0)

    def test_ready_with_batches(self):
        builder, _ = self._builder(batch_count=2)
        envelope = builder.build(project=_FakeProject(7), context=None)
        self.assertEqual(envelope["state"], "ready")
        self.assertEqual(envelope["data"]["project_id"], 7)
        self.assertEqual(envelope["data"]["batch_count"], 2)
        self.assertEqual(
            envelope["data"]["fetch_intent"],
            "project.boq.import.preview.fetch",
        )
        self.assertEqual(envelope["data"]["fetch_params"], {"project_id": 7})
        self.assertTrue(envelope["data"]["readonly"])

    def test_empty_state_still_carries_project_reference(self):
        builder, _ = self._builder(batch_count=0)
        envelope = builder.build(project=_FakeProject(9), context=None)
        self.assertEqual(envelope["state"], "empty")
        self.assertEqual(envelope["data"]["project_id"], 9)
        self.assertEqual(envelope["data"]["fetch_params"], {"project_id": 9})

    def test_visibility_allowed_for_internal_user(self):
        builder, _ = self._builder()
        envelope = builder.build(project=_FakeProject(1), context=None)
        self.assertEqual(envelope["visibility"]["allowed"], True)

    def test_forbidden_when_group_missing(self):
        class _Gated(builder_mod.ProjectBoqPreviewBuilder):
            required_groups = ("smart_construction_core.group_sc_cap_cost_read",)

        class _DeniedUser:
            def has_group(self, _xmlid):
                return False

        class _GatedEnv(dict):
            user = _DeniedUser()

        builder = _Gated(_GatedEnv())
        envelope = builder.build(project=_FakeProject(1), context=None)
        self.assertEqual(envelope["state"], "forbidden")
        self.assertEqual(envelope["visibility"]["reason_code"], "PERMISSION_DENIED")

    def test_batch_domain_scoped_to_project(self):
        builder, _ = self._builder(batch_count=1)
        builder.build(project=_FakeProject(42), context=None)
        batch_model = builder.env["project.boq.import.batch"]
        self.assertEqual(batch_model.domains, [[("project_id", "=", 42)]])


if __name__ == "__main__":
    unittest.main()

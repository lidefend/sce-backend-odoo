# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
import copy
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path


SMART_CORE_DIR = Path(__file__).resolve().parents[1]


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
smart_core_pkg.__path__ = [str(SMART_CORE_DIR)]
governance_pkg = sys.modules.setdefault("odoo.addons.smart_core.governance", types.ModuleType("odoo.addons.smart_core.governance"))
governance_pkg.__path__ = [str(SMART_CORE_DIR / "governance")]
utils_pkg = sys.modules.setdefault("odoo.addons.smart_core.utils", types.ModuleType("odoo.addons.smart_core.utils"))
utils_pkg.__path__ = [str(SMART_CORE_DIR / "utils")]

reason_codes = types.ModuleType("odoo.addons.smart_core.utils.reason_codes")
reason_codes.REASON_OK = "OK"
reason_codes.REASON_PERMISSION_DENIED = "PERMISSION_DENIED"
reason_codes.failure_meta_for_reason = lambda code: {"reason_code": code}
sys.modules["odoo.addons.smart_core.utils.reason_codes"] = reason_codes

drift_engine = types.ModuleType("odoo.addons.smart_core.governance.scene_drift_engine")


def _append_resolve_error(resolve_errors, **kwargs):
    if isinstance(resolve_errors, list):
        resolve_errors.append(kwargs)


drift_engine.append_resolve_error = _append_resolve_error
sys.modules["odoo.addons.smart_core.governance.scene_drift_engine"] = drift_engine

target = _load_module(
    "odoo.addons.smart_core.governance.scene_normalizer",
    SMART_CORE_DIR / "governance" / "scene_normalizer.py",
)


class _RefRecord:
    def __init__(self, record_id: int):
        self.id = record_id


class _StubEnv:
    def __init__(self, refs: dict[str, int]):
        self._refs = refs

    def ref(self, xmlid: str, raise_if_not_found: bool = False):
        record_id = self._refs.get(xmlid)
        if record_id is None:
            return None
        return _RefRecord(record_id)


class TestSceneNormalizerEntryTarget(unittest.TestCase):
    def test_resolve_targets_adds_scene_entry_target(self):
        normalizer = target.SceneNormalizer()
        scenes = [
            {
                "code": "projects.list",
                "target": {
                    "model": "project.project",
                    "record_id": 42,
                    "action_xmlid": "smart_construction_core.action_sc_project_list",
                    "menu_xmlid": "smart_construction_core.menu_sc_root",
                },
            }
        ]
        diagnostics = {
            "normalize_warnings": [],
            "resolve_errors": [],
        }
        env = _StubEnv(
            {
                "smart_construction_core.action_sc_project_list": 502,
                "smart_construction_core.menu_sc_root": 202,
            }
        )

        normalizer.resolve_targets(env, scenes, [], diagnostics)

        target_payload = (scenes[0] or {}).get("target") or {}
        self.assertEqual((target_payload.get("entry_target") or {}).get("type"), "scene")
        self.assertEqual((target_payload.get("entry_target") or {}).get("scene_key"), "projects.list")
        self.assertEqual((((target_payload.get("entry_target") or {}).get("compatibility_refs") or {}).get("action_id")), 502)
        self.assertEqual((((target_payload.get("entry_target") or {}).get("compatibility_refs") or {}).get("menu_id")), 202)
        self.assertEqual((((target_payload.get("entry_target") or {}).get("record_entry") or {}).get("model")), "project.project")
        self.assertEqual((((target_payload.get("entry_target") or {}).get("record_entry") or {}).get("record_id")), 42)
        self.assertEqual((((target_payload.get("entry_target") or {}).get("record_entry") or {}).get("action_id")), 502)
        self.assertEqual((((target_payload.get("entry_target") or {}).get("record_entry") or {}).get("menu_id")), 202)


class TestSceneReferenceBatch(unittest.TestCase):
    def make_env(self, fail=False):
        refs = {'sample.action': ('ir.actions.act_window', 1), 'sample.menu': ('ir.ui.menu', 1),
                'sample.alias': ('ir.ui.menu', 1), 'sample.deleted': ('ir.ui.menu', 2)}
        queries = []
        class Env:
            def ref(self, key, **kwargs):
                pair = refs.get(key)
                return SimpleNamespace(id=pair[1]) if pair and pair[1] == 1 else None
            def __getitem__(self, model):
                if model == 'ir.model.data':
                    return SimpleNamespace(_xmlid_to_res_model_res_id=lambda key, **kwargs: refs.get(key, (False, False)))
                def browse(ids):
                    queries.append((model, ids))
                    if fail:
                        raise PermissionError('unresolved batch')
                    return SimpleNamespace(exists=lambda: SimpleNamespace(ids=[rid for rid in ids if rid == 1]))
                return SimpleNamespace(browse=browse)
        return Env(), queries

    def test_same_numeric_ids_remain_model_scoped_and_missing_stays_missing(self):
        env, queries = self.make_env()
        result = target._resolve_xmlids_batch(env, ['sample.action', 'sample.menu', 'sample.alias', 'sample.menu', 'sample.deleted', 'sample.missing'])
        self.assertEqual(result, {'sample.action': 1, 'sample.menu': 1, 'sample.alias': 1, 'sample.deleted': None, 'sample.missing': None})
        self.assertEqual(queries, [('ir.actions.act_window', [1]), ('ir.ui.menu', [1, 2])])

    def test_normalization_and_diagnostics_match_single_reference_resolution(self):
        env, _ = self.make_env()
        source = [{'code': 'test.one', 'target': {'action_xmlid': 'sample.action', 'action_id': 999, 'menuXmlid': 'sample.menu'}},
                  {'code': 'test.two', 'target': {'action_xmlid': 'sample.missing', 'menu_xmlid': 'sample.deleted'}},
                  {'code': 'test.three', 'target': {'actionXmlid': 'sample.action', 'menu_xmlid': 'sample.alias'}}]
        old, current = copy.deepcopy(source), copy.deepcopy(source)
        old_errors, current_errors = [], []
        with patch.object(target, '_resolve_xmlids_batch', return_value={}):
            target._normalize_scene_targets(env, old, {}, old_errors)
        target._normalize_scene_targets(env, current, {}, current_errors)
        self.assertEqual(current, old)
        self.assertEqual(current_errors, old_errors)
        self.assertIn('TARGET_ID_XMLID_MISMATCH', {row['code'] for row in current_errors})
        self.assertIn('XMLID_NOT_FOUND', {row['code'] for row in current_errors})

    def test_failed_batch_retains_single_reference_behavior(self):
        env, _ = self.make_env(fail=True)
        self.assertEqual(target._resolve_xmlids_batch(env, ['sample.action']), {})
        scenes = [{'code': 'test.one', 'target': {'action_xmlid': 'sample.action'}}]
        target._normalize_scene_targets(env, scenes, {}, [])
        self.assertEqual(scenes[0]['target']['action_id'], 1)

    def test_generator_matches_list_including_diagnostics_and_public_return(self):
        env, _ = self.make_env()
        rows = [{'code': 'test.one', 'target': {'action_xmlid': 'sample.action', 'action_id': 999}},
                {'code': 'test.missing', 'target': {'action_xmlid': 'sample.missing'}}]
        expected_diagnostics = {'normalize_warnings': [], 'resolve_errors': []}
        actual_diagnostics = copy.deepcopy(expected_diagnostics)
        normalizer = target.SceneNormalizer()
        expected = normalizer.resolve_targets(env, copy.deepcopy(rows), [], expected_diagnostics)
        actual = normalizer.resolve_targets(env, (row for row in copy.deepcopy(rows)), [], actual_diagnostics)
        self.assertEqual(actual, expected)
        self.assertEqual(actual_diagnostics, expected_diagnostics)
        direct_errors = []
        direct = target._normalize_scene_targets(env, (row for row in copy.deepcopy(rows)), {}, direct_errors)
        self.assertEqual(direct, expected)
        self.assertEqual(direct_errors, expected_diagnostics['resolve_errors'])


if __name__ == "__main__":
    unittest.main()

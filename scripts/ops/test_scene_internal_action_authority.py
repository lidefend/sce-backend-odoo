#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import types
import unittest


def _load_module():
    pkg = types.ModuleType("odoo.addons.smart_core.core.scene_internal_action_authority")
    path = "addons/smart_core/core/scene_internal_action_authority.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location(pkg.__name__, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load_module()


class _FakeAction:
    def __init__(self, action_id, res_model, name="action", view_mode="tree,form"):
        self.id = action_id
        self.res_model = res_model
        self.name = name
        self.view_mode = view_mode


class _FakeMenu:
    def __init__(self, menu_id):
        self.id = menu_id


class _FakeEnv:
    def __init__(self, refs):
        self._refs = refs

    def ref(self, xmlid, raise_if_not_found=False):
        return self._refs.get(xmlid)


class TestSceneInternalActionAuthority(unittest.TestCase):
    def test_resolves_valid_scene_internal_action(self):
        env = _FakeEnv({
            "base.action_res_company_form": _FakeAction(52, "res.company"),
            "base.menu_action_res_company_form": _FakeMenu(57),
        })
        scenes = [{
            "code": "enterprise.setup",
            "handling_entry_catalog": {
                "groups": [{
                    "items": [{
                        "key": "company",
                        "model": "res.company",
                        "action_xmlid": "base.action_res_company_form",
                        "menu_xmlid": "base.menu_action_res_company_form",
                    }],
                }],
            },
        }]
        out = _mod.build_scene_internal_actions(env, scenes)
        self.assertIn("enterprise.setup:company", out)
        row = out["enterprise.setup:company"]
        self.assertEqual(row["action_id"], 52)
        self.assertEqual(row["menu_id"], 57)
        self.assertTrue(row["allowed"])

    def test_skips_model_mismatch(self):
        env = _FakeEnv({"smart_construction_core.action_sc_product_job_management_v1": _FakeAction(953, "hr.job")})
        scenes = [{
            "code": "enterprise.setup",
            "handling_entry_catalog": {
                "groups": [{
                    "items": [{
                        "key": "post",
                        "model": "sc.enterprise.post",
                        "action_xmlid": "smart_construction_core.action_sc_product_job_management_v1",
                    }],
                }],
            },
        }]
        self.assertEqual(_mod.build_scene_internal_actions(env, scenes), {})

    def test_skips_missing_xmlid(self):
        env = _FakeEnv({})
        scenes = [{
            "code": "enterprise.setup",
            "handling_entry_catalog": {
                "groups": [{
                    "items": [{
                        "key": "company",
                        "action_xmlid": "base.action_res_company_form",
                    }],
                }],
            },
        }]
        self.assertEqual(_mod.build_scene_internal_actions(env, scenes), {})


if __name__ == "__main__":
    unittest.main()

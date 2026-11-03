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


class TestNativeHandlingProjection(unittest.TestCase):
    def setUp(self):
        import importlib.util
        from xml.etree import ElementTree as etree
        spec = importlib.util.spec_from_file_location(
            "native_handling_entry_catalog", "addons/smart_core/core/native_handling_entry_catalog.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.project = module.project_native_handling_catalog
        self.arch = etree.fromstring(b'<form><sheet><group name="setup" string="Setup"><button name="test.action" type="action" string="Profile"/></group></sheet></form>')
        self.groups = {"test.config"}
        self.denied_models = set()
        self.action = types.SimpleNamespace(
            _name="ir.actions.act_window", id=7, res_model="res.company", name="Company",
            groups_id={"test.config"}, get_external_id=lambda: {7: "test.action"})
        self.view = types.SimpleNamespace(
            _name="ir.ui.view", active=True, type="form", model="res.company", groups_id={"test.config"},
            _get_combined_arch=lambda: self.arch)
        refs = {"test.view": self.view, "test.action": self.action}
        case = self

        class Env:
            user = types.SimpleNamespace(groups_id=case.groups, has_group=lambda group: group in case.groups)

            def ref(self, xmlid, raise_if_not_found=False):
                return refs.get(xmlid)

            def __getitem__(self, model):
                return types.SimpleNamespace(check_access_rights=lambda operation, raise_exception=False: model not in case.denied_models)

        self.env = Env()
        self.scene = {"code": "test.setup", "extensions": {"native_handling_entry_source": {"view_xmlid": "test.view"}}}

    def test_native_label_order_and_action_identity(self):
        self.arch.find(".//button").set("string", "Updated native label")
        catalog = self.project(self.env, self.scene)
        self.assertEqual(catalog["item_count"], 1)
        item = catalog["groups"][0]["items"][0]
        self.assertEqual(item["label"], "Updated native label")
        self.assertEqual(item["target"], {"type": "action", "action_xmlid": "test.action"})
        self.assertEqual(item["model"], self.action.res_model)

    def test_remediation_uses_only_authorized_native_metadata(self):
        self.arch.find('.//button').set('data-sc-remediation', ' profile, personnel ')
        item = self.project(self.env, self.scene)['groups'][0]['items'][0]
        self.assertEqual(item['remediation_keys'], ['profile', 'personnel'])
        self.action.groups_id = {'test.admin'}
        self.assertEqual(self.project(self.env, self.scene)['item_count'], 0)

    def test_denied_view_never_falls_back_to_historical_catalog(self):
        self.scene["handling_entry_catalog"] = {"groups": [{"items": [{"key": "stale"}]}]}
        self.groups.clear()
        self.assertEqual(self.project(self.env, self.scene)["item_count"], 0)

    def test_denied_action_group(self):
        self.action.groups_id = {"test.admin"}
        self.assertEqual(self.project(self.env, self.scene)["item_count"], 0)

    def test_denied_target_model_acl(self):
        self.action.res_model = "res.users"
        self.denied_models.add("res.users")
        self.assertEqual(self.project(self.env, self.scene)["item_count"], 0)

    def test_ancestor_and_negative_groups(self):
        sheet = self.arch.find("sheet")
        for restriction in ("test.admin", "!test.config", "test.config,!test.config"):
            with self.subTest(restriction=restriction):
                sheet.set("groups", restriction)
                self.assertEqual(self.project(self.env, self.scene)["item_count"], 0)

    def test_invisible_ancestor(self):
        self.arch.find("sheet").set("invisible", "1")
        self.assertEqual(self.project(self.env, self.scene)["item_count"], 0)

    def test_record_dependent_visibility_rejected(self):
        self.arch.find("sheet").set("invisible", "state == 'draft'")
        with self.assertRaisesRegex(ValueError, "MODIFIER_UNSUPPORTED"):
            self.project(self.env, self.scene)

    def test_untransported_button_context_rejected(self):
        self.arch.find(".//button").set("context", "{'default_active': False}")
        with self.assertRaisesRegex(ValueError, "CONTEXT_UNSUPPORTED"):
            self.project(self.env, self.scene)

    def test_missing_declared_source_fails_closed(self):
        self.scene["extensions"]["native_handling_entry_source"]["view_xmlid"] = "test.missing"
        with self.assertRaisesRegex(ValueError, "VIEW_UNAVAILABLE"):
            self.project(self.env, self.scene)

    def test_legacy_scene_is_unchanged(self):
        self.assertIsNone(self.project(None, {"code": "legacy"}))

    def test_native_source_requires_principal(self):
        with self.assertRaisesRegex(ValueError, "ENV_REQUIRED"):
            self.project(None, self.scene)


if __name__ == "__main__":
    unittest.main()

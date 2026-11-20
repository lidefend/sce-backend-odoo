# -*- coding: utf-8 -*-
"""Pure contract tests for the enterprise initialization diagnosis."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


SCENE_DIR = Path(__file__).resolve().parents[1]


def _package(name):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []
    return module


def _load(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


for package_name in (
    "odoo",
    "odoo.addons",
    "odoo.addons.smart_construction_core",
    "odoo.addons.smart_construction_core.services",
    "odoo.addons.smart_construction_scene",
    "odoo.addons.smart_construction_scene.services",
    "odoo.addons.smart_core",
    "odoo.addons.smart_core.core",
):
    _package(package_name)


class ControlledEnv:
    def __init__(
        self,
        *,
        surface_scenes,
        enabled_scene_keys,
        department_count=1,
        job_count=1,
        user_count=1,
        employee_count=1,
        linked_employee_count=1,
        positioned_employee_count=1,
        role_user_count=1,
        project_responsibility_count=0,
    ):
        self.company = types.SimpleNamespace(
            id=7,
            name="企业七",
            display_name="企业七",
            currency_id=1,
            exists=lambda: self.company,
        )
        self.surface_scenes = surface_scenes
        self.enabled_scene_keys = set(enabled_scene_keys)
        self.counts = {
            "hr.department": department_count,
            "hr.job": job_count,
            "res.users": user_count if role_user_count is None else role_user_count,
            "hr.employee": employee_count,
            "sc.project.member.assignment": project_responsibility_count,
        }
        self.linked_employee_count = linked_employee_count
        self.positioned_employee_count = positioned_employee_count
        self.role_user_count = role_user_count
        self.user = types.SimpleNamespace(id=9)
        self.cr = types.SimpleNamespace(now=lambda: "2026-11-20T00:00:00Z")

    def __getitem__(self, model):
        if model == "res.company":
            return types.SimpleNamespace(browse=lambda _company_id: self.company)
        if model == "hr.department":
            return self._counter(self.counts[model])
        if model == "hr.job":
            return self._counter(self.counts[model])
        if model == "res.users":
            calls = {"count": 0}

            class Users:
                def sudo(self):
                    return self

                def search_count(self, domain):
                    calls["count"] += 1
                    return self_model.counts["res.users"] if calls["count"] == 1 else self_model.role_user_count

            self_model = self
            return Users()
        if model == "hr.employee":
            employee_calls = {"count": 0}

            class Employees:
                def sudo(self):
                    return self

                def search_count(self, domain):
                    employee_calls["count"] += 1
                    if employee_calls["count"] == 1:
                        return self_model.counts["hr.employee"]
                    if employee_calls["count"] == 2:
                        return self_model.linked_employee_count
                    return self_model.positioned_employee_count

            self_model = self
            return Employees()
        if model == "res.groups":
            class Groups:
                def sudo(self):
                    return self

                def search(self, domain):
                    return types.SimpleNamespace(ids=[11])

            return Groups()
        if model == "sc.project.member.assignment":
            return self._counter(self.counts[model])
        if model == "sc.scene":
            scene = types.SimpleNamespace(to_public_dict=lambda _user: {"code": "enterprise.setup"})
            return types.SimpleNamespace(
                search=lambda domain, limit=1: scene,
            )
        raise AssertionError(f"unexpected model access: {model}")

    @staticmethod
    def _counter(value):
        return types.SimpleNamespace(
            sudo=lambda: types.SimpleNamespace(search_count=lambda domain: value)
        )


def _load_diagnosis(env):
    core_services = _package("odoo.addons.smart_construction_core.services")
    core_services.__path__ = []
    scene_services = _package("odoo.addons.smart_construction_scene.services")
    scene_services.__path__ = []
    native_core = _package("odoo.addons.smart_core.core")
    native_core.__path__ = []

    surface = types.ModuleType(
        "odoo.addons.smart_construction_core.services.scenario_surface_projection"
    )
    surface.load_runtime_surface = lambda _env: {"scenarios": env.surface_scenes}
    sys.modules[surface.__name__] = surface

    business = types.ModuleType(
        "odoo.addons.smart_construction_scene.services.business_scene_enablement"
    )
    business.business_key = lambda key: f"business.v1:{key}"
    sys.modules[business.__name__] = business

    activation = types.ModuleType(
        "odoo.addons.smart_construction_scene.services.tenant_scene_activation"
    )
    activation.read_tenant_enablement = (
        lambda _env, _company_id, key: key.removeprefix("business.v1:")
        in env.enabled_scene_keys
    )
    sys.modules[activation.__name__] = activation

    native_catalog = types.ModuleType(
        "odoo.addons.smart_core.core.native_handling_entry_catalog"
    )
    native_catalog.project_native_handling_catalog = lambda _env, _scene: {
        "contract_version": "handling_entry_catalog.v1",
        "groups": [{
            "key": "enterprise_bootstrap",
            "title": "企业基础初始化",
            "items": [
                {
                    "key": "smart_construction_core.action_sc_enterprise_company",
                    "label": "企业信息",
                    "remediation_keys": ["enterprise.info"],
                },
                {
                    "key": "smart_construction_core.action_sc_organization_department",
                    "label": "组织架构",
                    "remediation_keys": ["organization.department"],
                },
                {
                    "key": "smart_construction_core.action_sc_product_job_management_v1",
                    "label": "岗位管理",
                    "remediation_keys": ["job.management"],
                },
                {
                    "key": "smart_construction_core.action_sc_runtime_user_management",
                    "label": "人员与账号",
                    "remediation_keys": ["user.management", "personnel.record"],
                },
                {
                    "key": "smart_construction_core.action_sc_product_data_permission_v1",
                    "label": "业务权限分配",
                    "remediation_keys": ["data.permission", "project.member.permission"],
                },
            ],
        }],
    }
    sys.modules[native_catalog.__name__] = native_catalog

    return _load(
        "enterprise_readiness_contract",
        SCENE_DIR / "services" / "enterprise_readiness_diagnosis.py",
    )


class TestEnterpriseReadinessContract(unittest.TestCase):
    def test_contract_declares_sections_summary_scope_and_pending_validation(self):
        env = ControlledEnv(
            surface_scenes=[
                {"key": "project.management", "active": True},
                {"key": "finance.payments", "active": True},
            ],
            enabled_scene_keys={"project.management"},
        )
        diagnosis = _load_diagnosis(env)
        result = diagnosis.evaluate_enterprise_readiness(env, company_id=7)

        self.assertEqual(result["contract_version"], "enterprise_readiness.v2")
        self.assertEqual(result["company_id"], 7)
        self.assertEqual(result["company_name"], "企业七")
        self.assertEqual(result["maintenance_scope"], {
            "kind": "enterprise_configuration",
            "company_id": 7,
            "company_name": "企业七",
            "enterprise_managed": [
                "企业信息",
                "组织架构与岗位",
                "人员与账号",
                "业务角色与允许公司",
                "企业场景选择",
            ],
            "platform_managed": [
                "企业创建",
                "首个企业管理员",
                "产品版本发布",
                "平台技术配置",
            ],
            "business_validation_required": [
                "场景依赖",
                "角色工作空间交付",
            ],
        })
        self.assertEqual(result["summary"], {
            "rule_count": 12,
            "applicable_count": 12,
            "verified_count": 1,
            "configured_count": 8,
            "needs_attention_count": 1,
            "pending_business_validation_count": 2,
            "not_applicable_count": 0,
        })
        rules = {rule["rule_key"]: rule for rule in result["rules"]}
        self.assertEqual(rules["enterprise.identity"]["section_key"], "enterprise_foundation")
        self.assertEqual(rules["enterprise.roles"]["section_label"], "人员、账号与权限")
        self.assertEqual(rules["enterprise.scenario_enablement"]["section_sequence"], 30)
        self.assertEqual(
            rules["enterprise.project_responsibility"]["status"],
            "NOT_CONFIGURED",
        )
        self.assertEqual(
            rules["enterprise.scenario_dependencies"]["status"],
            "NOT_EVALUATED",
        )
        self.assertIn("实际办理验证", rules["enterprise.scenario_dependencies"]["failure_reason"])
        self.assertEqual(
            rules["enterprise.role_delivery"]["status"],
            "NOT_EVALUATED",
        )
        self.assertEqual(
            rules["enterprise.roles"]["remediation"],
            {
                "kind": "handling_entry",
                "key": "smart_construction_core.action_sc_product_data_permission_v1",
                "label": "业务权限分配",
            },
        )
        self.assertEqual(
            rules["enterprise.scenario_enablement"]["remediation"],
            {
                "kind": "anchor",
                "key": "enterprise-scenario-activation",
                "label": "前往场景管理",
            },
        )

    def test_inapplicable_project_and_scenario_rules_are_not_reported_as_attention(self):
        env = ControlledEnv(
            surface_scenes=[{"key": "finance.payments", "active": True}],
            enabled_scene_keys=set(),
        )
        diagnosis = _load_diagnosis(env)
        result = diagnosis.evaluate_enterprise_readiness(env, company_id=7)
        rules = {rule["rule_key"]: rule for rule in result["rules"]}

        self.assertFalse(rules["enterprise.project_responsibility"]["applicability"])
        self.assertFalse(rules["enterprise.scenario_dependencies"]["applicability"])
        self.assertFalse(rules["enterprise.role_delivery"]["applicability"])
        self.assertEqual(result["summary"]["not_applicable_count"], 3)
        self.assertEqual(result["summary"]["needs_attention_count"], 1)
        self.assertEqual(result["summary"]["pending_business_validation_count"], 0)
        self.assertEqual(
            result["summary"]["rule_count"],
            sum(result["summary"][key] for key in (
                "verified_count",
                "configured_count",
                "needs_attention_count",
                "pending_business_validation_count",
                "not_applicable_count",
            )),
        )

    def test_saved_scene_selection_is_counted_when_product_is_temporarily_unavailable(self):
        env = ControlledEnv(
            surface_scenes=[
                {"key": "finance.payments", "active": False},
            ],
            enabled_scene_keys={"finance.payments"},
        )
        diagnosis = _load_diagnosis(env)
        result = diagnosis.evaluate_enterprise_readiness(env, company_id=7)
        rules = {rule["rule_key"]: rule for rule in result["rules"]}

        self.assertEqual(
            rules["enterprise.scenario_enablement"]["evidence"]["enabled_scene_count"],
            1,
        )
        self.assertEqual(
            rules["enterprise.scenario_enablement"]["status"],
            "CONFIGURED",
        )
        self.assertEqual(
            rules["enterprise.scenario_dependencies"]["status"],
            "NOT_EVALUATED",
        )


if __name__ == "__main__":
    unittest.main()

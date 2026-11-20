# -*- coding: utf-8 -*-
"""Static contract audit for the five enterprise initialization entries."""
import csv
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET


CORE_DIR = Path(__file__).resolve().parents[1]


def _root(relative_path):
    return ET.parse(str(CORE_DIR / relative_path)).getroot()


def _record(root, record_id):
    match = root.find(".//record[@id='%s']" % record_id)
    if match is None:
        raise AssertionError("missing native record: %s" % record_id)
    return match


def _field(record, field_name):
    return record.find("field[@name='%s']" % field_name)


def _field_text(record, field_name):
    field = _field(record, field_name)
    if field is None:
        return ""
    return str(field.text or field.get("eval") or "").strip()


def _arch(record):
    arch = _field(record, "arch")
    if arch is None or not len(arch):
        raise AssertionError("native view has no arch")
    return arch[0]


def _access_rows():
    with (CORE_DIR / "security/ir.model.access.csv").open(newline="", encoding="utf-8") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


class TestEnterpriseSetupNativeContracts(unittest.TestCase):
    def test_initialization_declares_all_five_native_entries(self):
        root = _root("views/support/enterprise_initialization_views.xml")
        view = _record(root, "view_sc_enterprise_initialization_form")
        group = _arch(view).find(".//group[@name='enterprise_bootstrap']")
        self.assertIsNotNone(group)
        actual = {
            button.get("string"): (
                button.get("name"),
                button.get("data-sc-remediation"),
            )
            for button in group.findall("button")
        }
        self.assertEqual(actual, {
            "企业信息": ("%(action_sc_enterprise_company)d", "enterprise.info"),
            "组织架构": ("%(action_sc_organization_department)d", "organization.department"),
            "岗位管理": ("%(action_sc_product_job_management_v1)d", "job.management"),
            "人员与账号": ("%(action_sc_runtime_user_management)d", "user.management,personnel.record"),
            "业务权限分配": ("%(action_sc_product_data_permission_v1)d", "data.permission,project.member.permission"),
        })
        action = _record(root, "action_sc_enterprise_initialization")
        self.assertEqual(_field_text(action, "res_model"), "res.company")
        self.assertEqual(_field_text(action, "view_mode"), "form")
        self.assertIn("allowed_company_ids[0]", _field_text(action, "domain"))
        self.assertIn("'create': False", _field_text(action, "context"))
        self.assertIn("group_sc_cap_business_config_admin", _field_text(action, "groups_id"))

    def test_enterprise_and_organization_entries_preserve_scope_and_editability(self):
        initialization = _root("views/support/enterprise_initialization_views.xml")
        company_action = _record(initialization, "action_sc_enterprise_company")
        self.assertEqual(_field_text(company_action, "view_mode"), "tree,form")
        self.assertIn("allowed_company_ids[0]", _field_text(company_action, "domain"))
        self.assertIn("'create': False", _field_text(company_action, "context"))
        self.assertIn("'delete': False", _field_text(company_action, "context"))
        company_form = _arch(_record(initialization, "view_sc_enterprise_company_form"))
        self.assertEqual(company_form.get("create"), "0")
        self.assertEqual(company_form.get("delete"), "0")
        self.assertEqual(
            company_form.find(".//field[@name='currency_id']").get("readonly"),
            "1",
        )
        for field_name in ("name", "phone", "email", "website", "country_id", "city"):
            self.assertIsNotNone(company_form.find(".//field[@name='%s']" % field_name))

        organization = _root("views/support/organization_department_views.xml")
        organization_action = _record(organization, "action_sc_organization_department")
        self.assertEqual(_field_text(organization_action, "res_model"), "hr.department")
        self.assertEqual(_field_text(organization_action, "view_mode"), "tree,form")
        self.assertIn("Administration", _field_text(organization_action, "domain"))
        self.assertIn(
            "group_sc_cap_business_config_admin",
            _field_text(organization_action, "groups_id"),
        )
        organization_form = _arch(_record(organization, "view_sc_organization_department_form"))
        for field_name in ("name", "parent_id", "manager_id", "company_id", "active"):
            self.assertIsNotNone(organization_form.find(".//field[@name='%s']" % field_name))
        self.assertEqual(
            organization_form.find(".//field[@name='child_ids']").get("readonly"),
            "1",
        )
        access = _access_rows()["access_hr_department_business_config"]
        self.assertEqual(
            (access["perm_read"], access["perm_write"], access["perm_create"], access["perm_unlink"]),
            ("1", "1", "1", "1"),
        )

    def test_job_entry_preserves_headcount_and_company_authority(self):
        root = _root("views/menu_product_contract_completion_v1.xml")
        action = _record(root, "action_sc_product_job_management_v1")
        self.assertEqual(_field_text(action, "res_model"), "hr.job")
        self.assertEqual(_field_text(action, "view_mode"), "tree,form")
        self.assertIn("'delete': False", _field_text(action, "context"))
        self.assertIn(
            "group_sc_cap_business_config_admin",
            _field_text(action, "groups_id"),
        )
        form = _arch(_record(root, "view_sc_product_job_form_v1"))
        self.assertEqual(form.get("delete"), "0")
        for field_name in (
            "sc_job_code", "name", "department_id", "company_id", "active",
            "expected_employees", "no_of_employee", "sc_responsibility", "sc_qualification",
        ):
            self.assertIsNotNone(form.find(".//field[@name='%s']" % field_name))
        self.assertEqual(
            form.find(".//field[@name='no_of_employee']").get("readonly"),
            "1",
        )
        rules = _root("security/sc_record_rules.xml")
        rule = _record(rules, "rule_hr_job_sc_business_config_company")
        self.assertIn("company_id", _field_text(rule, "domain_force"))

    def test_people_and_account_entry_preserve_company_scope_and_safe_fields(self):
        root = _root("views/support/runtime_user_management_views.xml")
        action = _record(root, "action_sc_runtime_user_management")
        self.assertEqual(_field_text(action, "res_model"), "res.users")
        self.assertIn("sc_runtime_company_maintainable", _field_text(action, "domain"))
        self.assertIn(
            "sc_runtime_user_management",
            _field_text(action, "context"),
        )
        self.assertIn(
            "group_sc_cap_business_config_admin",
            _field_text(action, "groups_id"),
        )
        tree = _arch(_record(root, "view_sc_runtime_user_tree"))
        self.assertEqual(
            (tree.get("create"), tree.get("edit"), tree.get("delete")),
            ("1", "1", "0"),
        )
        form = _arch(_record(root, "view_sc_runtime_user_form"))
        for field_name in (
            "name", "phone", "email", "employee_id", "sc_personnel_department_id",
            "sc_personnel_job_id", "sc_personnel_active", "login", "active",
            "password", "company_id",
        ):
            self.assertIsNotNone(form.find(".//field[@name='%s']" % field_name))
        for forbidden in (
            "company_ids",
            "sc_user_role_group_ids",
            "sc_user_permission_group_ids",
            "sc_project_member_assignment_ids",
        ):
            self.assertIsNone(form.find(".//field[@name='%s']" % forbidden))
        access = _access_rows()["access_res_users_business_config_user"]
        self.assertEqual(
            (access["perm_read"], access["perm_write"], access["perm_create"], access["perm_unlink"]),
            ("1", "1", "1", "0"),
        )

    def test_business_permission_entry_preserves_role_and_project_boundaries(self):
        root = _root("views/menu_product_contract_completion_v1.xml")
        action = _record(root, "action_sc_product_data_permission_v1")
        self.assertEqual(_field_text(action, "res_model"), "res.users")
        self.assertIn("sc_runtime_company_maintainable", _field_text(action, "domain"))
        self.assertIn("'create': False", _field_text(action, "context"))
        self.assertIn("'delete': False", _field_text(action, "context"))
        for group_xmlid in (
            "group_sc_cap_config_admin",
            "group_sc_cap_business_config_admin",
        ):
            self.assertIn(group_xmlid, _field_text(action, "groups_id"))

        runtime = _root("views/support/runtime_user_management_views.xml")
        form = _arch(_record(runtime, "view_sc_data_permission_user_form"))
        self.assertEqual(form.get("create"), "0")
        self.assertEqual(form.get("delete"), "0")
        for field_name in ("name", "login", "active"):
            field = form.find(
                ".//group[@name='sc_permission_identity']/field[@name='%s']" % field_name
            )
            self.assertEqual(field.get("readonly"), "1")
        for field_name in ("company_id", "company_ids"):
            field = form.find(
                ".//group[@name='sc_permission_company_scope']/field[@name='%s']" % field_name
            )
            self.assertIsNotNone(field)
            self.assertNotEqual(field.get("readonly"), "1")
        role_field = form.find(
            ".//group[@name='sc_permission_business_roles']/field[@name='sc_user_permission_group_ids']"
        )
        self.assertIn("sc_assignable_user_permission", role_field.get("domain"))
        assignment_field = form.find(
            ".//group[@name='sc_permission_project_scope']/field[@name='sc_project_member_assignment_ids']"
        )
        self.assertEqual(assignment_field.get("readonly"), "not id")
        self.assertEqual(
            assignment_field.find("./tree/field[@name='project_id']").get("readonly"),
            "id",
        )


if __name__ == "__main__":
    unittest.main()

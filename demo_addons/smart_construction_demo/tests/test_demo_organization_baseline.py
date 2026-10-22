# -*- coding: utf-8 -*-
"""Hermetic guard for the demo organization baseline.

This test is deliberately independent from the Odoo runtime and database. It
parses the module seed XML with ElementTree and pins the facts that must survive
a module upgrade or a fresh demo rebuild:

* departments and jobs are well-formed, stable-XMLID records in main company;
* the department tree is resolvable and acyclic;
* every seeded employee points at an existing user, department and job, and
  mirrors the user's name and email;
* organization seeds carry no permission/scope semantics;
* manifest and BASE_SEED_FILES load users and departments before employees;
* user-visible seed values carry no Demo/演示/测试 markers;
* the upgrade migration and manifest version converge existing databases.

``sc_demo_users.xml`` is the pre-existing authorization carrier and still
declares legacy ``company_ids``/``groups_id`` fields; the permission-field
assertion therefore targets the organization seeds owned by this baseline.
"""

from __future__ import annotations

import ast
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[1]
MODULE = "smart_construction_demo"
MODULE_PREFIX = MODULE + "."

DEPARTMENTS_BASE = "data/base/12_departments.xml"
DEPARTMENTS_TREE = "data/base/13_departments_tree.xml"
JOBS = "data/base/14_jobs.xml"
USERS = "data/demo/sc_demo_users.xml"
ROLE_MATRIX_USERS = "data/demo/role_matrix_demo_users.xml"
EMPLOYEES = "data/demo/sc_demo_employees.xml"
BINDINGS = "data/demo/sc_demo_organization_bindings.xml"
MIGRATION = "migrations/17.0.0.4.0/post-migration.py"
FULL_PRODUCT_USERS = "data/demo/wutao_full_product_user.xml"
EXPECTED_MANIFEST_VERSION = "17.0.0.4.0"

USER_SEED_FILES = [USERS, ROLE_MATRIX_USERS]
ORG_SEED_FILES = [DEPARTMENTS_BASE, DEPARTMENTS_TREE, JOBS, EMPLOYEES, BINDINGS]
ALL_SEED_FILES = [DEPARTMENTS_BASE, DEPARTMENTS_TREE, JOBS, USERS, ROLE_MATRIX_USERS,
                  EMPLOYEES, BINDINGS]

BANNED_PERMISSION_FIELDS = {
    "sc_user_role_group_ids",
    "sc_user_permission_group_ids",
    "sc_project_member_assignment_ids",
    "company_ids",
    "groups_id",
}

# User-visible values must read like real tenant data. Technical identifiers
# (XMLID, login, project_code, model/table names) may still contain "demo".
BANNED_VISIBLE_TOKENS = (
    "Demo-",
    "Demo ",
    "【Demo",
    "（演示）",
    "演示",
    "测试-",
    "测试",
    "示例",
    "样例",
    "Demo",
    "DEMO",
    "某某",
)

# Repository boundary rules require synthetic legal company identities to carry
# an explicit marker (示例/某某); only that marker is allowed inside company names.
LEGAL_COMPANY = re.compile(r"[\u4e00-\u9fff]{4,}(?:建设|建筑)?集团有限公司")
SYNTHETIC_IDENTITY_MARKERS = ("示例", "某某")


def _banned_tokens_for(value: str) -> tuple[str, ...]:
    if LEGAL_COMPANY.search(value):
        return tuple(
            token for token in BANNED_VISIBLE_TOKENS
            if token not in SYNTHETIC_IDENTITY_MARKERS
        )
    return BANNED_VISIBLE_TOKENS


# Values in these fields are technical identity/format carriers, not end-user
# labels. They may legitimately keep "demo" semantics after visible data has
# been rewritten to real business language.
TECHNICAL_VALUE_FIELDS = {
    "login",
    "project_code",
    "version_code",
    "code",
    "key",
    "pack_id",
    "source_pack_id",
    "pack_hash",
    "source_hash",
    "tags",
    "signed_by",
    "amount_source",
}

VISIBLE_VALUE_FIELDS = {
    "name",
    "description",
    "title",
    "subtitle",
    "label",
    "ui_label",
    "ui_hint",
    "note",
    "notes",
    "changelog",
    "subject",
    "applicant_name",
    "handler_name",
    "employee_name",
    "contact_name",
    "foreman_name",
    "operator_name",
    "invoice_holder",
    "project_manager",
    "sc_supplier_note",
    "reason",
    "content",
    "conclusion",
    "source",
    "vendor",
    "text",
    "message",
    "summary",
    "detail",
    "address",
    "location",
    "remark",
    "comment",
    "display_name",
}

LEGACY_SEED_LITERALS = (
    "Demo-全能力",
    "Demo-项目经理",
    "Demo-财务经办",
    "Demo-成控经办",
    "Demo-数据审计",
    "Demo-只读",
    "Demo-业主单位",
    "Demo-合同相对方",
    "Demo 合同-收入",
    "Demo 合同清单",
    "Demo 目标成本计划",
    "Demo 手工",
    "演示项目 ·",
    "演示业主 ·",
    "演示供应商 ·",
    "演示分包 ·",
    "演示园区",
    "演示年度资金计划",
    "演示采购服务",
    "演示采购行",
    "演示版",
    "测试-",
)

REQUIRED_USERS = {
    "user_sc_pm_01": "pm1",
    "user_sc_contract_01": "ct1",
    "user_sc_fin_01": "fin1",
    "user_sc_fin_mgr_01": "fin_mgr",
    "user_sc_cost_01": "cost1",
    "user_sc_material_01": "mat1",
    "user_sc_material_mgr_01": "mat_mgr",
    "user_sc_purchase_01": "pur1",
    "user_demo_role_owner": "demo_role_owner",
    "user_demo_role_executive": "demo_role_executive",
    "user_sc_business_config_demo": "sc_demo_business_config",
    "user_sc_operation_demo": "sc_demo_operation",
    "user_sc_accounting_manager_demo": "sc_demo_accounting_manager",
}

REQUIRED_JOB_NAMES = {
    "项目经理",
    "合同管理员",
    "出纳",
    "财务经理",
    "成本工程师",
    "材料员",
    "物资主管",
    "采购员",
    "总经理",
    "管理层",
    "业务配置管理员",
    "经营主管",
    "会计主管",
}

REQUIRED_DEPARTMENT_NAMES = {
    "总经办",
    "经营管理部",
    "项目管理部",
    "工程管理部",
    "质量安全部",
    "商务合约部",
    "成本管理部",
    "采购部",
    "物资设备部",
    "财务部",
    "人力行政部",
}


def _path(relative: str) -> Path:
    return DEMO_ROOT / relative


def _local_xmlid(ref: str | None) -> str | None:
    if ref is None:
        return None
    return ref[len(MODULE_PREFIX):] if ref.startswith(MODULE_PREFIX) else ref


def _field(record: ET.Element, name: str) -> ET.Element | None:
    return record.find("field[@name='%s']" % name)


def _field_text(record: ET.Element, name: str) -> str | None:
    field = _field(record, name)
    if field is None:
        return None
    return (field.text or "").strip()


def _field_ref(record: ET.Element, name: str) -> str | None:
    field = _field(record, name)
    if field is None:
        return None
    return _local_xmlid(field.get("ref"))


def _records(relative: str, model: str | None = None) -> list[ET.Element]:
    root = ET.parse(_path(relative)).getroot()
    return [
        record
        for record in root.iter("record")
        if model is None or record.get("model") == model
    ]


def _merge_records(files: list[str], model: str) -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for relative in files:
        for record in _records(relative, model):
            values = merged.setdefault(record.get("id"), {})
            for field in record.findall("field"):
                name = field.get("name")
                if field.get("ref") is not None:
                    values[name] = _local_xmlid(field.get("ref"))
                else:
                    values[name] = (field.text or "").strip()
    return merged


def _manifest_dict() -> dict:
    tree = ast.parse(_path("__manifest__.py").read_text(encoding="utf-8"))
    return ast.literal_eval(tree.body[0].value)


def _manifest_data_order() -> list[str]:
    return list(_manifest_dict()["data"])


def _base_seed_order() -> list[str]:
    tree = ast.parse(_path("tools/scenario_loader.py").read_text(encoding="utf-8"))
    declaration = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and getattr(node.target, "id", None) == "BASE_SEED_FILES"
    )
    return list(ast.literal_eval(declaration.value))


def _index(order: list[str], relative: str) -> int:
    return order.index(relative)


def _all_data_xml() -> list[Path]:
    return sorted((DEMO_ROOT / "data").rglob("*.xml"))


def _seed_python_files() -> list[Path]:
    return sorted((DEMO_ROOT / "seed").rglob("*.py")) + [
        DEMO_ROOT / "tools" / "scenario_loader.py"
    ]


class TestDemoOrganizationBaseline(unittest.TestCase):
    def test_seed_xml_is_well_formed(self):
        for relative in ALL_SEED_FILES:
            with self.subTest(file=relative):
                ET.parse(_path(relative))

    def test_seed_xmlids_are_unique_except_the_declared_department_rereference(self):
        seen: dict[str, list[tuple[str, str | None]]] = {}
        for relative in ALL_SEED_FILES:
            local_ids: set[str] = set()
            for record in _records(relative):
                xmlid = record.get("id")
                model = record.get("model")
                self.assertTrue(xmlid, "%s has a record without id" % relative)
                self.assertNotIn(xmlid, local_ids, "%s declares %s twice" % (relative, xmlid))
                local_ids.add(xmlid)
                previous = seen.setdefault(xmlid, [])
                if previous:
                    declarable_in = {DEPARTMENTS_TREE, BINDINGS}
                    if xmlid == "sc_demo_department_001":
                        declarable_in.add(DEPARTMENTS_BASE)
                    allowed = (
                        relative in declarable_in
                        and model == "hr.department"
                        and all(previous_model == model and previous_file in declarable_in
                                for previous_file, previous_model in previous)
                    )
                    self.assertTrue(
                        allowed,
                        "%s reuses XMLID %s already declared by %s"
                        % (relative, xmlid, previous[0][0]),
                    )
                previous.append((relative, model))

    def test_department_001_is_preserved_and_tree_is_complete(self):
        departments = _merge_records([DEPARTMENTS_BASE, DEPARTMENTS_TREE], "hr.department")
        self.assertIn("sc_demo_department_001", departments)
        self.assertEqual(departments["sc_demo_department_001"].get("name"), "工程管理部")
        self.assertEqual(
            departments["sc_demo_department_001"].get("parent_id"),
            "sc_demo_department_project",
        )
        names = {values.get("name") for values in departments.values()}
        self.assertEqual(names, REQUIRED_DEPARTMENT_NAMES)
        self.assertEqual(
            departments["sc_demo_department_quality"].get("parent_id"),
            "sc_demo_department_project",
        )

    def test_department_parents_resolve_without_cycles_and_share_one_company(self):
        departments = _merge_records([DEPARTMENTS_BASE, DEPARTMENTS_TREE], "hr.department")
        parents: dict[str, str | None] = {}
        for xmlid, values in departments.items():
            with self.subTest(department=xmlid):
                self.assertEqual(values.get("company_id"), "base.main_company")
                parent = values.get("parent_id")
                if parent is not None:
                    self.assertIn(parent, departments)
                parents[xmlid] = parent

        for start in parents:
            visited: list[str] = []
            current: str | None = start
            while current is not None:
                self.assertNotIn(current, visited, "department cycle at %s" % start)
                visited.append(current)
                current = parents[current]

    def test_jobs_cover_the_business_chain_and_share_one_company(self):
        jobs = _merge_records([JOBS], "hr.job")
        names = {values.get("name") for values in jobs.values()}
        self.assertEqual(names, REQUIRED_JOB_NAMES)
        for xmlid, values in jobs.items():
            with self.subTest(job=xmlid):
                self.assertEqual(values.get("company_id"), "base.main_company")

    def test_employees_mirror_users_and_reference_organization_records(self):
        users = _merge_records(USER_SEED_FILES, "res.users")
        departments = _merge_records([DEPARTMENTS_BASE, DEPARTMENTS_TREE], "hr.department")
        jobs = _merge_records([JOBS], "hr.job")
        employees = _records(EMPLOYEES, "hr.employee")
        self.assertGreaterEqual(len(employees), len(REQUIRED_USERS))

        employee_user_refs: set[str] = set()
        for employee in employees:
            xmlid = employee.get("id")
            user_ref = _field_ref(employee, "user_id")
            with self.subTest(employee=xmlid):
                self.assertIsNotNone(user_ref)
                self.assertIn(user_ref, users, "missing user record for %s" % user_ref)
                self.assertEqual(_field_text(employee, "name"), users[user_ref].get("name"))
                self.assertEqual(_field_text(employee, "work_email"), users[user_ref].get("email"))
                self.assertEqual(_field_ref(employee, "company_id"), "base.main_company")
                self.assertIn(_field_ref(employee, "department_id"), departments)
                self.assertIn(_field_ref(employee, "job_id"), jobs)
            employee_user_refs.add(user_ref)

        self.assertTrue(set(REQUIRED_USERS).issubset(employee_user_refs))

    def test_capability_and_fixture_accounts_stay_out_of_the_business_tree(self):
        users = _merge_records(USER_SEED_FILES, "res.users")
        employee_user_refs = {
            _field_ref(employee, "user_id")
            for employee in _records(EMPLOYEES, "hr.employee")
        }
        allowed_sc_accounts = {
            "sc_demo_business_config",
            "sc_demo_operation",
            "sc_demo_accounting_manager",
        }
        for user_ref in employee_user_refs:
            login = users[user_ref].get("login")
            with self.subTest(login=login):
                self.assertFalse(login.startswith("fixture_role_"))
                self.assertNotEqual(login, "svc_e2e_smoke")
                self.assertFalse(login.endswith("_cap"))
                if login.startswith("sc_"):
                    self.assertIn(login, allowed_sc_accounts)
                if login.startswith("demo_role_"):
                    self.assertIn(login, {"demo_role_owner", "demo_role_executive"})

    def test_organization_seeds_carry_no_permission_semantics(self):
        for relative in ORG_SEED_FILES:
            for record in _records(relative):
                with self.subTest(file=relative, record=record.get("id")):
                    self.assertNotEqual(record.get("model"), "res.users")
                    for field in record.findall("field"):
                        self.assertNotIn(field.get("name"), BANNED_PERMISSION_FIELDS)

    def test_organization_seeds_are_reapplied_on_upgrade(self):
        def noupdate(relative: str) -> str | None:
            data = ET.parse(_path(relative)).getroot().find("data")
            return data.get("noupdate")

        self.assertEqual(noupdate(DEPARTMENTS_BASE), "1")
        for relative in (DEPARTMENTS_TREE, JOBS, EMPLOYEES, BINDINGS):
            with self.subTest(file=relative):
                self.assertEqual(noupdate(relative), "0")

    def test_department_managers_reference_seeded_employees(self):
        employees = {record.get("id") for record in _records(EMPLOYEES, "hr.employee")}
        departments = _merge_records([DEPARTMENTS_BASE, DEPARTMENTS_TREE], "hr.department")
        bindings = _records(BINDINGS, "hr.department")
        self.assertEqual(len(bindings), len(departments))
        for binding in bindings:
            with self.subTest(department=binding.get("id")):
                self.assertIn(binding.get("id"), departments)
                self.assertIn(_field_ref(binding, "manager_id"), employees)

    def test_manifest_loads_users_and_departments_before_employees(self):
        order = _manifest_data_order()
        self.assertLess(_index(order, DEPARTMENTS_BASE), _index(order, DEPARTMENTS_TREE))
        for prerequisite in (DEPARTMENTS_TREE, JOBS, USERS, ROLE_MATRIX_USERS):
            with self.subTest(prerequisite=prerequisite):
                self.assertLess(_index(order, prerequisite), _index(order, EMPLOYEES))
        self.assertLess(_index(order, EMPLOYEES), _index(order, BINDINGS))

    def test_base_seed_loads_users_and_departments_before_employees(self):
        order = _base_seed_order()
        for prerequisite in (USERS, DEPARTMENTS_BASE, DEPARTMENTS_TREE, JOBS):
            with self.subTest(prerequisite=prerequisite):
                self.assertLess(_index(order, prerequisite), _index(order, EMPLOYEES))
        self.assertLess(_index(order, EMPLOYEES), _index(order, BINDINGS))

    def test_base_seed_does_not_replay_the_role_matrix_permission_carrier(self):
        self.assertNotIn(ROLE_MATRIX_USERS, _base_seed_order())

    def test_visible_seed_values_carry_no_demo_markers(self):
        for path in _all_data_xml():
            root = ET.parse(path).getroot()
            for element in root.iter():
                candidates: list[tuple[str, str]] = []
                if element.tag == "field":
                    field_name = element.get("name") or ""
                    if field_name in VISIBLE_VALUE_FIELDS:
                        candidates.append((field_name, element.text or ""))
                        if element.get("eval"):
                            candidates.append((field_name + "@eval", element.get("eval") or ""))
                else:
                    for attribute in ("name", "string", "help", "title"):
                        value = element.get(attribute)
                        if value:
                            candidates.append(("<%s %s>" % (element.tag, attribute), value))
                for label, value in candidates:
                    for token in _banned_tokens_for(value):
                        self.assertNotIn(
                            token,
                            value,
                            "%s %s still carries %r" % (path, label, token),
                        )

    def test_every_non_technical_field_value_avoids_placeholder_markers(self):
        for path in _all_data_xml():
            root = ET.parse(path).getroot()
            for field in root.iter("field"):
                field_name = field.get("name") or ""
                if field_name in TECHNICAL_VALUE_FIELDS:
                    continue
                for value in (field.text or "", field.get("eval") or ""):
                    if not value:
                        continue
                    for token in _banned_tokens_for(value):
                        self.assertNotIn(
                            token,
                            value,
                            "%s field %s still carries %r"
                            % (path, field_name, token),
                        )

    def test_seed_python_has_no_legacy_visible_literals(self):
        for path in _seed_python_files():
            text = path.read_text(encoding="utf-8")
            for literal in LEGACY_SEED_LITERALS:
                self.assertNotIn(
                    literal,
                    text,
                    "%s still carries legacy visible literal %r" % (path, literal),
                )

    def test_generated_visible_names_use_business_labels(self):
        my_work = (
            DEMO_ROOT / "seed/steps/step_z_demo_full_my_work.py"
        ).read_text(encoding="utf-8")
        self.assertIn("TASK_TITLES", my_work)
        self.assertNotIn('f"{MARKER}-', my_work)
        attachments = (
            DEMO_ROOT / "seed/steps/step_60_attachments_demo.py"
        ).read_text(encoding="utf-8")
        self.assertIn("project_label = project.name or project.project_code", attachments)
        contracts = (
            DEMO_ROOT / "seed/steps/step_40_contracts_demo.py"
        ).read_text(encoding="utf-8")
        self.assertIn('f"JS-{settlement_year}-', contracts)
        payment = (
            DEMO_ROOT / "seed/steps/step_payment_request_floorplan_demo.py"
        ).read_text(encoding="utf-8")
        self.assertIn('FIXTURE_NAME = "PRQ-2026-001"', payment)

    def test_locale_normalize_only_fills_missing_zh_cn(self):
        source = (
            DEMO_ROOT / "models/demo_locale_normalize.py"
        ).read_text(encoding="utf-8")
        self.assertIn('if not source or payload.get("zh_CN"):', source)
        self.assertIn('with_context(lang="zh_CN").write', source)
        seed_registry = (DEMO_ROOT / "seed/registry.py").read_text(encoding="utf-8")
        self.assertIn('env["demo.locale.normalize"].sudo().run()', seed_registry)

    def test_upgrade_migration_and_manifest_version_converge_existing_databases(self):
        self.assertTrue(_path(MIGRATION).is_file(), "missing upgrade migration")
        self.assertEqual(_manifest_dict()["version"], EXPECTED_MANIFEST_VERSION)

        migration = _path(MIGRATION).read_text(encoding="utf-8")
        self.assertIn("_is_demo_database", migration)
        self.assertIn("sc_dev_demo", migration)
        for login in ("pm1", "ct1", "fin1", "fin_mgr", "cost1", "mat1", "mat_mgr",
                      "pur1", "demo_role_owner", "demo_role_executive",
                      "sc_demo_operation", "sc_demo_accounting_manager",
                      "sc_demo_business_config", "wutao"):
            with self.subTest(login=login):
                self.assertIn('"%s"' % login, migration)
        for value in ("德阳智能制造产教融合项目", "城东片区安置房项目",
                      "运营管理场景", "运营管理场景包"):
            with self.subTest(value=value):
                self.assertIn(value, migration)

    def test_upgrade_migration_does_not_write_computed_user_name_column(self):
        migration = _path(MIGRATION).read_text(encoding="utf-8")

        self.assertNotIn("UPDATE res_users SET name", migration)
        self.assertIn("UPDATE res_partner SET name", migration)

    def test_upgrade_migration_writes_translated_jsonb_names_with_language_keys(self):
        migration = _path(MIGRATION).read_text(encoding="utf-8")

        self.assertIn("JSONB_TRANSLATABLE_COLUMNS", migration)
        self.assertIn('("account_account", "name")', migration)
        self.assertIn('("project_project", "name")', migration)
        self.assertIn("jsonb_set(", migration)
        self.assertIn("'{{en_US}}'", migration)
        self.assertIn("'{{zh_CN}}'", migration)
        self.assertIn('_update_jsonb_text(cr, "project_project", "name"', migration)
        self.assertIn("column == \"payload_json\"", migration)
        self.assertNotIn("SET name = %s, description = %s", migration)

    def test_company_identity_and_second_company_are_real_business_names(self):
        import runpy
        hooks = runpy.run_path(
            str(DEMO_ROOT / "hooks.py"), run_name="demo_company_names_test"
        )
        main = hooks["DEMO_COMPANY_NAME"]
        second = hooks["DEMO_COMPANY_SECOND_NAME"]
        for value in (main, second):
            for token in ("Demo", "demo", "演示", "测试", "My Company"):
                with self.subTest(value=value, token=token):
                    self.assertNotIn(token, value)
        self.assertNotEqual(main, second)
        self.assertTrue(second.startswith(main[:-len("有限公司")]))
        self.assertTrue(second.endswith("有限公司"))

    def test_company_second_step_is_declared_between_identity_and_projects(self):
        tree = ast.parse((DEMO_ROOT / "seed/registry.py").read_text())
        profiles = next(ast.literal_eval(n.value) for n in tree.body
                        if isinstance(n, ast.AnnAssign) and n.target.id == "_PROFILES")
        steps = profiles["demo_full"]
        self.assertEqual(steps[0], "demo_company_identity")
        self.assertLess(steps.index("demo_company_identity"),
                        steps.index("demo_company_secondary"))
        self.assertLess(steps.index("demo_company_secondary"),
                        steps.index("demo_20_projects"))
        self.assertLess(steps.index("demo_10_users"),
                        steps.index("demo_company_membership"))
        self.assertLess(steps.index("demo_company_membership"),
                        steps.index("demo_user_prefs"))

    def test_company_second_step_uses_stable_xmlid_and_data_space_registration(self):
        step = _path("seed/steps/step_company_secondary.py").read_text(encoding="utf-8")
        self.assertIn("apply_demo_company_secondary", step)
        self.assertIn("register_demo_company_secondary", step)
        self.assertIn("guard_demo_data_space", step)
        hooks = _path("hooks.py").read_text(encoding="utf-8")
        self.assertIn('"name": "demo_company_second"', hooks)
        self.assertIn("DEMO_COMPANY_SECOND_NAME", hooks)
        self.assertNotIn('"company_id": 2', hooks)
        self.assertNotIn("company_id=2", hooks)

    def test_company_second_members_are_business_seats_not_fixtures(self):
        import runpy
        hooks = runpy.run_path(
            str(DEMO_ROOT / "hooks.py"), run_name="demo_company_members_test"
        )
        logins = hooks["DEMO_COMPANY_SECOND_MEMBER_LOGINS"]
        self.assertIn("admin", logins)
        self.assertIn("wutao", logins)
        self.assertIn("demo_finance", logins)
        for login in logins:
            with self.subTest(login=login):
                self.assertFalse(login.startswith(("fixture_", "svc_", "acceptance_")))

    def test_full_product_user_xml_does_not_reset_runtime_company_membership(self):
        root = ET.parse(DEMO_ROOT / FULL_PRODUCT_USERS).getroot()
        records = {
            record.get("id"): record
            for record in root.findall(".//record")
            if record.get("model") == "res.users"
        }
        self.assertEqual(
            {"user_wutao_full_product", "user_demo_full"},
            set(records),
        )
        for record_id, record in records.items():
            with self.subTest(record=record_id):
                self.assertFalse(
                    any(field.get("name") == "company_ids" for field in record.findall("field")),
                    "runtime company_ids must be owned by demo_company_membership, not module XML",
                )

    def test_verify_step_checks_second_company_registration_and_membership(self):
        verify = _path("seed/steps/step_90_verify_demo.py").read_text(encoding="utf-8")
        for token in ("_verify_company_secondary(env)", "DEMO_COMPANY_SECOND_NAME",
                      "DEMO_COMPANY_SECOND_MEMBER_LOGINS", "data_purpose"):
            with self.subTest(token=token):
                self.assertIn(token, verify)


if __name__ == "__main__":
    unittest.main()

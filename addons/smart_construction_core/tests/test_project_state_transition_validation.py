# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "project_state")
class TestProjectStateTransitionValidation(TransactionCase):
    def test_profile_name_write_rejects_empty_without_partial_changes(self):
        project = self.env["project.project"].create({"name": "Profile baseline", "description": "Before"})
        original_description = project.description
        for value in ("", "   ", False, None):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    project.write({"name": value, "description": "Must not persist"})
                project.invalidate_recordset(["name", "description"])
                self.assertEqual(project.name, "Profile baseline")
                self.assertEqual(project.description, original_description)

    def test_profile_name_guard_preserves_partial_and_valid_writes(self):
        project = self.env["project.project"].create({"name": "Profile baseline"})
        project.write({"description": "Updated notes"})
        saved_description = project.description
        self.assertIn("Updated notes", saved_description)
        self.assertEqual(project.name, "Profile baseline")
        project.write({"name": "Updated profile"})
        self.assertEqual(project.name, "Updated profile")
        self.assertEqual(project.description, saved_description)

    def test_profile_name_guard_rejects_batch_before_any_record_changes(self):
        projects = self.env["project.project"].create([{"name": "Profile A"}, {"name": "Profile B"}])
        with self.assertRaises(ValidationError):
            projects.write({"name": "", "description": "Must not persist"})
        projects.invalidate_recordset(["name", "description"])
        self.assertEqual(projects.mapped("name"), ["Profile A", "Profile B"])
        self.assertFalse(any(projects.mapped("description")))

    def setUp(self):
        super().setUp()
        self.env.user.groups_id = [(4, self.env.ref("smart_construction_core.group_sc_cap_project_manager").id)]
        self.uom_unit = self.env.ref("uom.product_uom_unit")

    def _create_boq(self, project):
        version = self.env["project.boq.version"].create(
            {
                "name": "Lifecycle BOQ V1",
                "code": "V1",
                "project_id": project.id,
                "source_type": "contract",
            }
        )
        self.env["project.boq.line"].create(
            {
                "project_id": project.id,
                "version_id": version.id,
                "code": "BOQ-001",
                "name": "BOQ Item",
                "uom_id": self.uom_unit.id,
                "quantity": 1.0,
                "price": 1.0,
            }
        )
        version.action_validate()
        version.action_publish()

    def _create_project_user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@invalid.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(group_xmlid).id,
                        ],
                    )
                ],
            }
        )

    def test_draft_submit_reports_missing_fields_without_blocking(self):
        project = self.env["project.project"].create(
            {"name": "Draft Project", "company_id": self.env.company.id}
        )
        project.action_sc_submit()
        project.action_set_lifecycle_state("in_progress")
        self.assertEqual(project.lifecycle_state, "in_progress")
        self.assertIn("建议完善", project.lifecycle_advisory)
        self.assertIn("建议后续导入工程量清单", project.lifecycle_advisory)

    def test_lifecycle_permission_is_enforced_by_model(self):
        reader = self._create_project_user(
            "lifecycle_reader",
            "smart_construction_core.group_sc_cap_project_read",
        )
        operator = self._create_project_user(
            "lifecycle_operator",
            "smart_construction_core.group_sc_cap_project_user",
        )
        manager = self._create_project_user(
            "lifecycle_manager",
            "smart_construction_core.group_sc_cap_project_manager",
        )
        project = self.env["project.project"].create(
            {
                "name": "Lifecycle Permission Project",
                "company_id": self.env.company.id,
                "manager_id": operator.id,
                "user_id": operator.id,
            }
        )
        with self.assertRaises(UserError):
            project.with_user(reader).action_set_lifecycle_state("in_progress")
        project.with_user(operator).action_sc_submit()
        project.with_user(operator).action_set_lifecycle_state("in_progress")
        with self.assertRaises(UserError):
            project.with_user(operator).action_set_lifecycle_state("paused")
        project.with_user(manager).action_set_lifecycle_state("paused")
        project.with_user(manager).action_set_lifecycle_state("in_progress")
        self.assertEqual(project.lifecycle_state, "in_progress")

# -*- coding: utf-8 -*-
import base64
import json

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.handlers.chatter_timeline import ChatterTimelineHandler


@tagged("post_install", "-at_install", "chatter_timeline_authorization_orm")
class TestChatterTimelineAuthorizationOrm(TransactionCase):
    """Real-ORM proof that timeline metadata follows its parent record."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create(
            {"name": "Timeline authorization company B"}
        )
        cls.base_user = cls.env.ref("base.group_user")
        cls.project_read = cls.env.ref(
            "smart_construction_core.group_sc_cap_project_read"
        )
        cls.authorized_user = cls._create_user(
            "timeline_authorized",
            cls.company_a,
            [cls.company_a, cls.company_b],
        )
        cls.other_project_user = cls._create_user(
            "timeline_other_project",
            cls.company_a,
            [cls.company_a],
        )
        cls.same_company_denied_user = cls._create_user(
            "timeline_same_company_denied",
            cls.company_a,
            [cls.company_a],
        )
        cls.cross_company_user = cls._create_user(
            "timeline_cross_company",
            cls.company_b,
            [cls.company_b],
        )

        context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "mail_auto_subscribe_no_notify": True,
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(context)
        cls.project_a = Project.create(
            {
                "name": "Timeline authorized project",
                "company_id": cls.company_a.id,
                "user_id": cls.authorized_user.id,
                "privacy_visibility": "followers",
            }
        )
        cls.project_a_other = Project.create(
            {
                "name": "Timeline other project",
                "company_id": cls.company_a.id,
                "user_id": cls.other_project_user.id,
                "privacy_visibility": "followers",
            }
        )
        cls.project_b = Project.create(
            {
                "name": "Timeline company B project",
                "company_id": cls.company_b.id,
                "user_id": cls.cross_company_user.id,
                "privacy_visibility": "followers",
            }
        )
        Task = cls.env["project.task"].with_context(context)
        cls.task_a = Task.create(
            {"name": "TIMELINE_AUTHORIZED_RECORD", "project_id": cls.project_a.id}
        )
        cls.task_a_other = Task.create(
            {
                "name": "TIMELINE_OTHER_PROJECT_SECRET",
                "project_id": cls.project_a_other.id,
            }
        )
        cls.task_b = Task.create(
            {
                "name": "TIMELINE_CROSS_COMPANY_SECRET",
                "project_id": cls.project_b.id,
            }
        )
        cls.nonexistent_id = max(
            cls.task_a.id,
            cls.task_a_other.id,
            cls.task_b.id,
        ) + 1000000

        cls.task_a.message_post(
            subject="TIMELINE_AUTHORIZED_MESSAGE",
            body="<p>authorized message body</p>",
        )
        cls.task_a_other.message_post(
            subject="TIMELINE_OTHER_PROJECT_MESSAGE_SECRET",
            body="<p>other project message secret</p>",
        )
        cls.task_b.message_post(
            subject="TIMELINE_CROSS_COMPANY_MESSAGE_SECRET",
            body="<p>cross company message secret</p>",
        )
        cls.attachment_a = cls._attach(
            cls.task_a,
            "TIMELINE_AUTHORIZED_ATTACHMENT.txt",
        )
        cls.attachment_other = cls._attach(
            cls.task_a_other,
            "TIMELINE_OTHER_PROJECT_ATTACHMENT_SECRET.txt",
        )
        cls.attachment_b = cls._attach(
            cls.task_b,
            "TIMELINE_CROSS_COMPANY_ATTACHMENT_SECRET.txt",
        )
        cls.env["mail.activity"].create(
            {
                "res_model_id": cls.env["ir.model"]._get_id("project.task"),
                "res_id": cls.task_a.id,
                "activity_type_id": cls.env.ref("mail.mail_activity_data_todo").id,
                "summary": "TIMELINE_AUTHORIZED_ACTIVITY",
                "user_id": cls.authorized_user.id,
            }
        )
        cls.env["sc.audit.log"].sudo().create(
            {
                "event_code": "TIMELINE_AUTHORIZED_AUDIT",
                "action": "timeline-test",
                "model": "project.task",
                "res_id": cls.task_a.id,
                "actor_uid": cls.env.user.id,
                "actor_login": cls.env.user.login,
                "reason": "authorized audit event",
                "company_id": cls.company_a.id,
                "project_id": cls.project_a.id,
            }
        )

    @classmethod
    def _create_user(cls, login, company, companies):
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": company.id,
                "company_ids": [(6, 0, [row.id for row in companies])],
                "groups_id": [
                    (6, 0, [cls.base_user.id, cls.project_read.id])
                ],
            }
        )

    @classmethod
    def _attach(cls, task, name):
        return cls.env["ir.attachment"].create(
            {
                "name": name,
                "type": "binary",
                "datas": base64.b64encode(b"timeline authorization evidence"),
                "mimetype": "text/plain",
                "res_model": "project.task",
                "res_id": task.id,
            }
        )

    def _env(self, user, company_ids):
        return self.env(
            user=user,
            context={
                **self.env.context,
                "allowed_company_ids": [row.id for row in company_ids],
                "tracking_disable": True,
            },
        )

    def _timeline(self, env, record_id):
        return ChatterTimelineHandler(
            env,
            context={"trace_id": "timeline-authorization-proof"},
            payload={
                "params": {
                    "model": "project.task",
                    "res_id": record_id,
                    "include_audit": True,
                    "limit": 120,
                }
            },
        ).handle()

    def _denial_observation(self, env, record_id):
        result = self._timeline(env, record_id)
        self.assertIsInstance(result, dict)
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
        for secret in (
            "TIMELINE_OTHER_PROJECT",
            "TIMELINE_CROSS_COMPANY",
        ):
            self.assertNotIn(secret, serialized)
        self.assertNotIn("items", result)
        self.assertNotIn("counts", result)
        return result

    @staticmethod
    def _count_without_leak(model, domain):
        try:
            return model.search_count(domain)
        except AccessError:
            return 0

    @staticmethod
    def _groups_without_leak(model, domain):
        try:
            return model.read_group(domain, ["id:count"], ["res_id"])
        except AccessError:
            return []

    def test_authorized_member_and_administrator_receive_timeline(self):
        caller = self._env(
            self.authorized_user,
            [self.company_a],
        )
        data, _meta = self._timeline(caller, self.task_a.id)
        serialized = json.dumps(data, ensure_ascii=False)
        self.assertIn("TIMELINE_AUTHORIZED_MESSAGE", serialized)
        self.assertIn("TIMELINE_AUTHORIZED_ATTACHMENT", serialized)
        self.assertIn("TIMELINE_AUTHORIZED_ACTIVITY", serialized)
        self.assertIn("TIMELINE_AUTHORIZED_AUDIT", serialized)
        self.assertGreaterEqual(data["counts"]["messages"], 1)
        self.assertGreaterEqual(data["counts"]["attachments"], 1)
        self.assertGreaterEqual(data["counts"]["activities"], 1)
        self.assertGreaterEqual(data["counts"]["audit"], 1)

        admin_data, _admin_meta = self._timeline(
            self.env(
                context={
                    **self.env.context,
                    "allowed_company_ids": [
                        self.company_a.id,
                        self.company_b.id,
                    ],
                }
            ),
            self.task_b.id,
        )
        self.assertIn(
            "TIMELINE_CROSS_COMPANY_MESSAGE_SECRET",
            json.dumps(admin_data, ensure_ascii=False),
        )

    def test_direct_id_unauthorized_and_nonexistent_are_equivalent(self):
        caller = self._env(
            self.same_company_denied_user,
            [self.company_a],
        )
        denied = self._denial_observation(caller, self.task_a_other.id)
        missing = self._denial_observation(caller, self.nonexistent_id)
        self.assertEqual(denied, missing)
        self.assertEqual(denied["code"], 404)
        self.assertEqual(denied["error"]["reason_code"], "NOT_FOUND")

    def test_cross_project_and_cross_company_records_are_hidden(self):
        authorized = self._env(self.authorized_user, [self.company_a])
        other_project = self._denial_observation(
            authorized,
            self.task_a_other.id,
        )
        cross_company = self._denial_observation(
            authorized,
            self.task_b.id,
        )
        nonexistent = self._denial_observation(
            authorized,
            self.nonexistent_id,
        )
        self.assertEqual(other_project, nonexistent)
        self.assertEqual(cross_company, nonexistent)

        company_b_user = self._env(
            self.cross_company_user,
            [self.company_b],
        )
        self.assertEqual(
            self._denial_observation(company_b_user, self.task_a.id),
            self._denial_observation(company_b_user, self.nonexistent_id),
        )

    def test_allowed_company_context_cannot_bypass_project_membership(self):
        expanded = self._env(
            self.authorized_user,
            [self.company_a, self.company_b],
        )
        self.assertEqual(
            self._denial_observation(expanded, self.task_b.id),
            self._denial_observation(expanded, self.nonexistent_id),
        )

    def test_message_attachment_and_aggregate_surfaces_do_not_leak(self):
        caller = self._env(
            self.same_company_denied_user,
            [self.company_a],
        )
        message_domain = [
            ("model", "=", "project.task"),
            ("res_id", "=", self.task_a_other.id),
        ]
        attachment_domain = [("id", "=", self.attachment_other.id)]
        self.assertEqual(
            self._count_without_leak(caller["mail.message"], message_domain),
            0,
        )
        self.assertEqual(
            self._groups_without_leak(caller["mail.message"], message_domain),
            [],
        )
        self.assertEqual(
            self._count_without_leak(
                caller["ir.attachment"],
                attachment_domain,
            ),
            0,
        )
        self.assertFalse(caller["project.task"].search([("id", "=", self.task_a_other.id)]))
        self.assertEqual(
            caller["project.task"].search_count(
                [("id", "in", [self.task_a.id, self.task_a_other.id])]
            ),
            0,
        )

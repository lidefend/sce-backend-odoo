# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "labor_product")
class TestLaborProductCapability(TransactionCase):
    def _user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@invalid.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [self.env.ref("base.group_user").id, self.env.ref(group_xmlid).id],
                    )
                ],
            }
        )

    def test_labor_surfaces_use_project_capabilities_and_non_blocking_advisories(self):
        operator = self._user(
            "labor_product_operator", "smart_construction_core.group_sc_cap_project_user"
        )
        reader = self._user(
            "labor_product_reader", "smart_construction_core.group_sc_cap_project_read"
        )
        unrelated_internal = self._user(
            "labor_unrelated_internal", "smart_construction_core.group_sc_internal_user"
        )
        project = self.env["project.project"].create({"name": "劳务产品能力测试项目"})

        with self.assertRaises(AccessError):
            self.env["sc.labor.worker"].with_user(unrelated_internal).create(
                {"name": "越权人员", "project_id": project.id}
            )

        worker = self.env["sc.labor.worker"].with_user(operator).create(
            {"name": "张三", "project_id": project.id}
        )
        notification = worker.with_user(operator).action_activate()
        self.assertEqual(worker.state, "active")
        self.assertEqual(notification.get("tag"), "display_notification")
        self.assertIn("建议补充证件号码", worker.processing_advisory)
        self.assertEqual(worker.with_user(reader).read(["name"])[0]["name"], "张三")
        with self.assertRaises(AccessError):
            worker.with_user(reader).write({"trade": "木工"})

        deduction = self.env["sc.labor.deduction"].with_user(operator).create(
            {
                "project_id": project.id,
                "worker_id": worker.id,
                "amount": 100,
            }
        )
        deduction_notice = deduction.with_user(operator).action_confirm()
        self.assertEqual(deduction.state, "confirmed")
        self.assertEqual(deduction_notice.get("tag"), "display_notification")
        self.assertIn("建议补充扣款事由", deduction.processing_advisory)

        usage = self.env["sc.labor.usage"].with_user(operator).create(
            {
                "project_id": project.id,
                "labor_team": "一班",
                "work_content": "现场作业",
                "worker_qty": 1,
            }
        )
        self.assertTrue(usage.with_user(operator).action_submit())
        self.assertEqual(usage.state, "approved")
        self.assertIn("建议补充用工单价", usage.processing_advisory)

    def test_the_labor_usage_record_rules_match_its_siblings(self):
        """G09: 871 的行级规则必须与 570／575 同形。

        `只读 ⊂ 经办` 是蕴含关系，所以把 own-or-member 规则挂在**只读**上，
        等于让只读身份凭 `create_uid = user.id` 看到「本人创建但已非项目成员」的记录
        （570／575 不会）。本测试把「经办挂 own-or-member ＋ 只读挂仅成员读域」固定下来，
        并附一条行为反例：只读身份看不到自己创建但非其项目成员的项目下的记录。
        """
        own = self.env.ref("smart_construction_core.rule_sc_internal_labor_usage")
        read = self.env.ref("smart_construction_core.rule_sc_project_read_labor_usage")
        self.assertEqual(
            own.groups.mapped("id"),
            [self.env.ref("smart_construction_core.group_sc_cap_project_user").id],
            "own-or-member 必须挂在经办（与 570／575 同形），不能挂在只读",
        )
        self.assertEqual(
            read.groups.mapped("id"),
            [self.env.ref("smart_construction_core.group_sc_cap_project_read").id],
        )
        self.assertEqual(
            [
                name
                for name, key in (("read", "perm_read"), ("write", "perm_write"),
                                  ("create", "perm_create"), ("unlink", "perm_unlink"))
                if read[key]
            ],
            ["read"],
            "只读组的规则只应给读权限",
        )
        self.assertNotIn("create_uid", read.domain_force)

        reader = self._user(
            "labor_product_rule_reader", "smart_construction_core.group_sc_cap_project_read"
        )
        foreign_project = self.env["project.project"].create({"name": "劳务规则他方项目"})
        record = (
            self.env["sc.labor.usage"]
            .with_user(reader)
            .sudo()
            .create(
                {
                    "project_id": foreign_project.id,
                    "labor_team": "规则反例班组",
                    "work_content": "规则反例",
                    "worker_qty": 1.0,
                    "work_hours": 1.0,
                }
            )
        )
        self.assertEqual(record.create_uid, reader)
        self.assertEqual(
            self.env["sc.labor.usage"].with_user(reader).search_count([("id", "=", record.id)]),
            0,
            "只读身份不应看到本人创建但非其项目成员的记录（与 570／575 同口径）",
        )

    def test_the_labor_usage_approval_is_capability_governed_like_its_siblings(self):
        """G09: 871 的审批步必须与 570／575 同口径，经办不得自审自批。

        `只读 ⊂ 经办 ⊂ 审批` 是严格蕴含：经办与审批都持 `write`，所以 ACL 与
        行级规则都无法表达「经办不得审批」。570／575 用方法级门禁补这一层，
        本测试把 871 的同口径修复固定下来（经办可提交、不可确认；审批可确认；
        只读连建档都被 ACL 拒绝），并保留「审批仍能正常办理」的正例。
        """
        reader = self._user(
            "labor_usage_gate_reader", "smart_construction_core.group_sc_cap_project_read"
        )
        operator = self._user(
            "labor_usage_gate_operator", "smart_construction_core.group_sc_cap_project_user"
        )
        manager = self._user(
            "labor_usage_gate_manager", "smart_construction_core.group_sc_cap_project_manager"
        )
        project = self.env["project.project"].create(
            {"name": "劳务审批能力测试项目", "company_id": self.env.company.id}
        )
        payload = {
            "project_id": project.id,
            "labor_team": "G09 审批门禁班组",
            "work_content": "G09 审批门禁验证",
            "worker_qty": 1.0,
            "work_hours": 2.0,
        }

        # 只读：连建档都不允许（ACL 无 create），所以不存在「看得见却办不了」的入口。
        with self.assertRaises(AccessError):
            self.env["sc.labor.usage"].with_user(reader).create(dict(payload))

        # 经办：办理（草稿 → 已提交）合法，审批不合法。
        usage = self.env["sc.labor.usage"].with_user(operator).create(dict(payload))
        self.assertEqual(usage.state, "draft")
        usage.action_submit()
        self.assertEqual(usage.state, "approved")

        with self.assertRaises(UserError):
            usage.action_confirm()
        usage.invalidate_recordset()
        self.assertEqual(usage.state, "approved", "被拒的审批不得推进状态")

        # 审批：同一条事实仍可被合法推进，说明这是角色门禁而不是禁止确认。
        usage.with_user(manager).action_confirm()
        usage.invalidate_recordset()
        self.assertEqual(usage.state, "confirmed")

    def test_the_labor_usage_return_to_draft_and_cancel_are_capability_governed(self):
        """退回草稿／取消已提交件需审批能力；取消自己的草稿只需经办能力。

        `action_reset_draft` 是「已取消 → 草稿」的受控退回，会让事实重新可改；
        `action_cancel` 对已提交件同理。两者都不应由经办单独完成。
        """
        operator = self._user(
            "labor_usage_gate_operator2", "smart_construction_core.group_sc_cap_project_user"
        )
        manager = self._user(
            "labor_usage_gate_manager2", "smart_construction_core.group_sc_cap_project_manager"
        )
        project = self.env["project.project"].create(
            {"name": "劳务退回能力测试项目", "company_id": self.env.company.id}
        )

        def make_usage():
            return self.env["sc.labor.usage"].with_user(operator).create({
                "project_id": project.id,
                "labor_team": "G09 退回门禁班组",
                "work_content": "G09 退回门禁验证",
                "worker_qty": 1.0,
                "work_hours": 2.0,
            })

        # 草稿件的取消属于经办范围内的更正。
        draft_usage = make_usage()
        draft_usage.action_cancel()
        self.assertEqual(draft_usage.state, "cancel")

        # 已提交件的取消需要审批能力。
        submitted_usage = make_usage()
        submitted_usage.action_submit()
        with self.assertRaises(UserError):
            submitted_usage.action_cancel()
        submitted_usage.invalidate_recordset()
        self.assertEqual(submitted_usage.state, "approved")
        submitted_usage.with_user(manager).action_cancel()
        submitted_usage.invalidate_recordset()
        self.assertEqual(submitted_usage.state, "cancel")

        # 已取消 → 草稿同样需要审批能力。
        with self.assertRaises(UserError):
            submitted_usage.action_reset_draft()
        submitted_usage.invalidate_recordset()
        self.assertEqual(submitted_usage.state, "cancel")
        submitted_usage.with_user(manager).action_reset_draft()
        submitted_usage.invalidate_recordset()
        self.assertEqual(submitted_usage.state, "draft")

        self.assertEqual(
            self.env.ref("smart_construction_core.action_sc_product_labor_realname_v1").res_model,
            "sc.labor.worker",
        )
        self.assertEqual(
            self.env.ref("smart_construction_core.action_sc_product_labor_deduction_v1").res_model,
            "sc.labor.deduction",
        )

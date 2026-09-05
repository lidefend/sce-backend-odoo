# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install", "sc_gate", "security_gate")
class TestTierActionGroupsUnion(TransactionCase):
    """统一审批回调动作的组并集守门。

    OCA base_tier_validation_server_action 在多级线性链的*每一级*审批后
    都会触发回调，而 ir.actions.server.run() 的 groups 检查对着原始调用
    用户做（即使 OCA 用 sudo() 包裹 action 执行）。因此回调动作的
    groups_id 必须等于该模型审批链各级评审组的并集——只绑终审 manager
    组会让中间级评审人 approve 时直接 AccessError 回滚。
    """

    def _create_partner(self, name):
        return self.env["res.partner"].create({"name": name})

    def _create_project(self, name):
        owner = self._create_partner("%s Owner" % name)
        return self.env["project.project"].create(
            {
                "name": name,
                "company_id": self.env.company.id,
                "owner_id": owner.id,
                "manager_id": self.env.user.id,
                "location": "Test Location",
            }
        )

    def test_settlement_callback_groups_cover_all_chain_reviewers(self):
        """结算单回调动作的组必须覆盖四级链的全部评审组。"""
        action = self.env.ref(
            "smart_construction_core.server_action_settlement_order_on_approved"
        )
        group_xmlids = {
            xmlid
            for xmlid in action.sudo().groups_id.mapped(
                lambda g: g.get_external_id().get(g.id) or ""
            )
            if xmlid
        }
        expected = {
            "smart_construction_core.group_sc_role_settlement_user",
            "smart_construction_core.group_sc_cap_settlement_manager",
        }
        self.assertTrue(
            expected.issubset(group_xmlids),
            "结算单审批回调 groups 缺少链上评审组：%s vs %s"
            % (sorted(expected - group_xmlids), sorted(group_xmlids)),
        )

    def test_all_tier_callback_groups_equal_union_of_chain_reviewer_groups(self):
        """每个带 tier 链的模型，回调动作组 == 其链上评审组并集。"""
        Step = self.env["sc.approval.step"].sudo()
        Policy = self.env["sc.approval.policy"].sudo()
        problems = []
        for policy in Policy.search([]):
            approve_xmlid, _reject_xmlid = policy._tier_server_action_xmlids(
                policy.target_model
            )
            if not approve_xmlid:
                continue
            expected_groups = set(
                Step.search(
                    [
                        ("policy_id.target_model", "=", policy.target_model),
                        ("approve_group_id", "!=", False),
                    ]
                ).mapped("approve_group_id").ids
            )
            if not expected_groups:
                continue
            action = self.env.ref(approve_xmlid, raise_if_not_found=False)
            if not action:
                continue
            actual_groups = set(action.sudo().groups_id.ids)
            if actual_groups != expected_groups:
                problems.append(
                    "%s: expected %s, got %s"
                    % (
                        approve_xmlid,
                        sorted(expected_groups),
                        sorted(actual_groups),
                    )
                )
        self.assertFalse(
            problems,
            "tier 回调动作组未等于链上评审组并集：%s" % "; ".join(problems),
        )

    def test_mid_chain_server_action_callback_does_not_advance_draft(self):
        """中间级 server action 回调不得推进状态（server_action_tier no-op）。"""
        # financing_loan: 回调对 draft 直接写 confirmed；带 server_action_tier
        # 且链未完成时必须 no-op。
        project = self._create_project("TIER-UNION-MIDCHAIN")
        record = self.env["sc.financing.loan"].create(
            {
                "project_id": project.id,
                "partner_id": self._create_partner("TIER-UNION-MIDCHAIN Partner").id,
                "loan_type": "loan_registration",
                "direction": "financing_in",
                "amount": 1000.0,
            }
        )
        self.assertEqual(record.state, "draft")
        record.with_context(server_action_tier=1).action_on_tier_approved()
        record.invalidate_recordset()
        self.assertEqual(
            record.state,
            "draft",
            "中间级回调不得把融资借款推进为 confirmed",
        )
        # 完整链（validated）后回调照常推进。
        self.env.cr.execute(
            "UPDATE sc_financing_loan SET validation_status=%s WHERE id=%s",
            ("validated", record.id),
        )
        record.invalidate_recordset()
        record.with_context(server_action_tier=1).action_on_tier_approved()
        record.invalidate_recordset()
        self.assertEqual(record.state, "confirmed")

    def test_mid_chain_server_action_callback_does_not_raise(self):
        """带 raise 语义的回调在中间级 server action 触发时不得 raise。"""
        # expense_claim: 未 validated 直接调用会 raise；server action
        # 中间级触发必须静默跳过。
        project = self._create_project("TIER-UNION-NORAISE")
        record = self.env["sc.expense.claim"].create(
            {
                "project_id": project.id,
                "partner_id": self._create_partner("TIER-UNION-NORAISE Partner").id,
                "business_category_id": self.env.ref(
                    "smart_construction_core.business_category_finance_deduction_bill"
                ).id,
                "claim_type": "expense",
                "amount": 100.0,
            }
        )
        self.env.cr.execute(
            "UPDATE sc_expense_claim SET state=%s, validation_status=%s WHERE id=%s",
            ("submit", "pending", record.id),
        )
        record.invalidate_recordset()
        record.with_context(server_action_tier=1).action_on_tier_approved()
        record.invalidate_recordset()
        self.assertEqual(
            record.state,
            "submit",
            "中间级回调不得推进费用单状态",
        )

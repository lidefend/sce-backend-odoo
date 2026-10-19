# -*- coding: utf-8 -*-

import logging
from datetime import date, timedelta

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProjectDemoCockpitSeed(models.Model):
    _inherit = "project.project"

    # ``payment.request._check_project_lifecycle`` refuses to submit or approve
    # a payment on a 保修/关闭 project, so the showcase must not try to create
    # such a fact there.
    _DEMO_PAYMENT_BLOCKED_LIFECYCLES = ("warranty", "closed")
    # ``project.project._ensure_operation_allowed`` blocks 记载成本台账 in these
    # lifecycle states; the seed must respect the same guard.
    _DEMO_COST_BLOCKED_LIFECYCLES = ("paused", "closed")
    _OFFICIAL_SAMPLE_PROFILES = {
        "天府数谷智慧园区运营中心": {
            "profile": "execution",
            "showcase_ready": True,
            "seed_costs": False,
            "seed_payments": False,
            "health_state": "warn",
            "execution_state": "in_progress",
            "target_lifecycle_state": "in_progress",
        },
        "中江装配式住宅试点项目": {
            "profile": "payment",
            "showcase_ready": True,
            "seed_costs": True,
            "seed_payments": False,
            "health_state": "warn",
            "execution_state": "done",
            "target_lifecycle_state": "in_progress",
        },
        "东汽数字化产线改造工程": {
            "profile": "settlement_complete",
            "showcase_ready": True,
            "seed_costs": True,
            "seed_payments": True,
            "health_state": "good",
            "execution_state": "done",
            "target_lifecycle_state": "done",
        },
    }

    @api.model
    def sc_demo_seed_cockpit_round2(self):
        from ..hooks import assert_demo_seed_principal, guard_demo_scope

        assert_demo_seed_principal(self.env)
        guard_demo_scope(self.env)
        from ..tools.scenario_loader import _demo_project_members, _DEMO_PAYMENT_SCOPED_SEATS
        contract_actor = self.env.ref("smart_construction_demo.user_sc_contract_manager_cap")
        cost_actor = self.env.ref("smart_construction_demo.user_sc_cost_01")
        finance_actor = self.env.ref("smart_construction_demo.user_sc_fin_mgr_01")
        partner_model = self.env["res.partner"]
        cost_code_model = self.env["project.cost.code"]
        contract_model = self.env["construction.contract"].with_user(contract_actor).sudo(False)
        contract_line_model = self.env["construction.contract.line"].with_user(contract_actor).sudo(False)
        cost_ledger_model = self.env["project.cost.ledger"].with_user(cost_actor).sudo(False)
        payment_request_model = self.env["payment.request"].with_user(finance_actor).sudo(False)
        activity_model = self.env["mail.activity"]
        model_model = self.env["ir.model"]

        projects = self._sc_demo_release_projects()

        partner_fallback = partner_model.search([("is_company", "=", True)], limit=1)
        cost_code = cost_code_model.search([], order="id asc", limit=1)
        model_id = model_model._get_id("project.project")
        todo_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)

        for project in projects:
            _demo_project_members(self.env, project, _DEMO_PAYMENT_SCOPED_SEATS + (
                "smart_construction_demo.user_sc_contract_manager_cap",
                "smart_construction_demo.user_sc_cost_01",
                "smart_construction_demo.user_sc_project_manager_cap",
            ))
            profile = self._sc_demo_profile(project)
            partner = project.partner_id or partner_fallback
            if not partner:
                continue

            self._sc_demo_seed_contracts(
                project=project,
                partner=partner,
                contract_model=contract_model,
                contract_line_model=contract_line_model,
            )
            if profile.get("seed_costs", True):
                self._sc_demo_seed_cost_ledger(
                    project=project,
                    partner=partner,
                    cost_code=cost_code,
                    cost_ledger_model=cost_ledger_model,
                )
            if profile.get("seed_payments", True):
                self._sc_demo_seed_payments(
                    project=project,
                    partner=partner,
                    payment_request_model=payment_request_model,
                )
            self._sc_demo_seed_risk_signals(
                project=project,
                activity_model=activity_model,
                todo_type=todo_type,
                model_id=model_id,
                profile=profile,
            )
            self._sc_demo_apply_showcase_profile(project, profile)

        return True

    @api.model
    def _sc_demo_release_projects(self):
        """Pick showroom-first projects for cockpit demo seeding."""

        project_model = self.with_context(active_test=False)
        projects = project_model.browse()

        sample_names = list(self._OFFICIAL_SAMPLE_PROFILES.keys())
        if sample_names:
            projects |= project_model.search(
                [("active", "=", True), ("name", "in", sample_names)],
                order="id asc",
            )

        from ..seed.showroom_catalog import SHOWROOM_PROJECT_NAMES

        projects |= project_model.search(
            [("active", "=", True), ("name", "in", list(SHOWROOM_PROJECT_NAMES))],
            order="id asc",
            limit=24,
        )

        if len(projects) < 12:
            projects |= project_model.search(
                [("active", "=", True), ("project_code", "ilike", "DEMO-%")],
                order="id asc",
                limit=24,
            )

        return projects

    @api.model
    def _sc_demo_profile(self, project):
        profile = dict(
            self._OFFICIAL_SAMPLE_PROFILES.get(
                str(project.name or "").strip(),
                {
                    "profile": "showroom",
                    "showcase_ready": False,
                    "seed_costs": True,
                    "seed_payments": True,
                    "health_state": "warn",
                    "execution_state": "done",
                    "target_lifecycle_state": str(getattr(project, "lifecycle_state", "") or "").strip().lower() or "in_progress",
                },
            )
        )
        profile.setdefault("profile", "showroom")
        profile.setdefault("showcase_ready", False)
        profile.setdefault("seed_costs", True)
        profile.setdefault("seed_payments", True)
        profile.setdefault("health_state", "warn")
        profile.setdefault("execution_state", "done")
        profile.setdefault(
            "target_lifecycle_state",
            str(getattr(project, "lifecycle_state", "") or "").strip().lower() or "in_progress",
        )
        return profile

    @api.model
    def _sc_demo_seed_contracts(self, project, partner, contract_model, contract_line_model):
        from ..tools.scenario_loader import drive_seeded_record

        samples = [
            ("out", f"{project.name}-补充收入合同", "补充收入合同", 8_000_000.0 + (project.id % 7) * 1_100_000.0),
            ("in", f"{project.name}-补充支出合同", "补充支出合同", (8_000_000.0 + (project.id % 7) * 1_100_000.0) * 0.62),
        ]
        existing = contract_model.search_count(
            [("project_id", "=", project.id), ("subject", "in", [spec[1] for spec in samples])]
        )
        if existing:
            return

        for contract_type, subject, line_note, amount in samples:
            contract = contract_model.create(
                {
                    "subject": subject,
                    "type": contract_type,
                    "project_id": project.id,
                    "partner_id": partner.id,
                }
            )
            contract_line_model.create(
                {
                    "contract_id": contract.id,
                    "qty_contract": 1.0,
                    "price_contract": amount,
                    "note": line_note,
                }
            )
            if contract.state in ("draft", "confirmed"):
                # The contract only reaches 执行中 through its own 确认 and
                # 执行中 actions, with the declared approval seat deciding the
                # submission; a direct state write would skip that guard.
                drive_seeded_record(self.env, contract, "running")

    @api.model
    def _sc_demo_seed_cost_ledger(self, project, partner, cost_code, cost_ledger_model):
        """Seed cost facts only where the product allows them.

        ``project.cost.ledger.create`` refuses 记载成本台账 on a project that is
        停工/关闭, so a showcase project parked in one of those states gets no
        cost samples: that is the product's rule, not a demo exception.
        """
        if not cost_code:
            return
        if project.lifecycle_state in self._DEMO_COST_BLOCKED_LIFECYCLES:
            return

        base = date.today()
        samples = [
            ("材料采购", 1_180_000.0, 5),
            ("人工费用", 820_000.0, 15),
            ("机械费用", 430_000.0, 25),
            ("分包结算", 1_650_000.0, 35),
        ]
        for note_text, amount, days in samples:
            entry_note = note_text
            existing = cost_ledger_model.search_count(
                [
                    ("project_id", "=", project.id),
                    ("note", "=", entry_note),
                ]
            )
            if existing:
                continue
            happen_day = base - timedelta(days=days)
            cost_ledger_model.create(
                {
                    "project_id": project.id,
                    "cost_code_id": cost_code.id,
                    "date": happen_day,
                    "period": happen_day.strftime("%Y-%m"),
                    "amount": amount,
                    "partner_id": partner.id,
                    "note": entry_note,
                }
            )

    @api.model
    def _sc_demo_seed_payments(self, project, partner, payment_request_model):
        """Seed the cockpit payment samples as product-legal facts.

        The samples used to declare ``state`` at create time.  A document now
        reaches a terminal state only through its own actions, so writing it
        directly (and hiding the refusal in a bare ``except``) would silently
        drop the whole showcase set.  Each sample is therefore created as a
        draft and carried with the product's own flow: the 节点回款 samples are
        submitted and approved, and the completed one continues through
        收款登记 (``sc.receipt.income``) so an 已收款 fact stays real.  A
        project whose lifecycle blocks payment submission gets no samples:
        that is the product's rule, not a demo exception.
        """
        if project.lifecycle_state in self._DEMO_PAYMENT_BLOCKED_LIFECYCLES:
            return
        contract_model = self.env["construction.contract"].sudo()
        # 申请的收付方向必须与合同方向一致（产品 _check_contract_direction），
        # 回款挂收入合同，付款挂支出合同。
        contracts = {
            contract_type: contract_model.search(
                [
                    ("project_id", "=", project.id),
                    ("type", "=", contract_type),
                    (
                        "subject",
                        "in",
                        [
                            f"{project.name}-补充收入合同",
                            f"{project.name}-补充支出合同",
                        ],
                    ),
                ],
                limit=1,
            )
            for contract_type in ("out", "in")
        }
        samples = [
            ("receive", "approved", 2_800_000.0, "节点回款A"),
            ("receive", "done", 1_650_000.0, "节点回款B"),
            ("pay", "draft", 1_200_000.0, "分包付款A"),
            ("pay", "draft", 860_000.0, "材料付款B"),
        ]
        for req_type, target_state, amount, note_text in samples:
            req_note = note_text
            contract = contracts["out" if req_type == "receive" else "in"]
            request = payment_request_model.search(
                [("project_id", "=", project.id), ("note", "=", req_note)], limit=1
            )
            if not request:
                request = payment_request_model.create(
                    {
                        "project_id": project.id,
                        "partner_id": partner.id,
                        "type": req_type,
                        "contract_id": contract.id if contract else False,
                        "amount": amount,
                        "note": req_note,
                    }
                )
            if target_state == "draft":
                continue
            self._sc_demo_advance_payment_request(request, contract, target_state, note_text)
        return True

    @api.model
    def _sc_demo_advance_payment_request(self, request, contract, target_state, note_text):
        """Carry one cockpit sample to its declared state with product actions."""
        from odoo.addons.smart_construction_demo.tools.scenario_loader import (
            _demo_drive_approval,
        )

        if request.state == "draft":
            _demo_drive_approval(self.env, request)
        request.invalidate_recordset()
        if target_state == "approved":
            if request.state not in ("approved", "done"):
                raise UserError(
                    "演示付款申请未能通过正式审批状态机：%s 停在 %s"
                    % (request.name, request.state)
                )
            return request
        if target_state != "done":
            raise UserError("演示付款样本声明了未知目标状态：%s" % target_state)
        if not contract:
            raise UserError("演示收款样本缺少收入合同，无法办理收款登记：%s" % request.name)
        from ..tools.scenario_loader import _demo_action_record, _demo_finish_reviews

        receipt_model = _demo_action_record(self.env, self.env["sc.receipt.income"], "action_confirm")
        receipt = receipt_model.search([("payment_request_id", "=", request.id)], limit=1)
        if not receipt:
            receipt = receipt_model.create(
                {
                    "payment_request_id": request.id,
                    "project_id": request.project_id.id,
                    "contract_id": contract.id,
                    "partner_id": request.partner_id.id,
                    "amount": request.amount,
                    "note": request.note,
                }
            )
        if receipt.state == "draft":
            receipt.action_confirm()
        _demo_finish_reviews(self.env, receipt)
        if receipt.state == "confirmed":
            finance_manager = self.env.ref(
                "smart_construction_demo.user_sc_fin_mgr_01", raise_if_not_found=False
            )
            receipt.with_user(finance_manager).action_received()
        request.invalidate_recordset()
        if request.state != "done":
            raise UserError(
                "演示收款样本未回写为已完成：%s 停在 %s" % (request.name, request.state)
            )
        return request

    @api.model
    def _sc_demo_seed_risk_signals(self, project, activity_model, todo_type, model_id, profile=None):
        profile = dict(profile or {})
        target_health = str(profile.get("health_state") or "warn").strip().lower() or "warn"
        if "health_state" in project._fields and (project.health_state or "") != target_health:
            project.write({"health_state": target_health})

        if not todo_type or not model_id:
            return

        marker_summary = "成本偏差复核"
        existing = activity_model.search_count(
            [
                ("res_model", "=", "project.project"),
                ("res_id", "=", project.id),
                ("summary", "=", marker_summary),
            ]
        )
        if existing:
            return
        activity_model.create(
            {
                "activity_type_id": todo_type.id,
                "res_model_id": model_id,
                "res_id": project.id,
                "summary": marker_summary,
                "note": "请复核本周成本偏差。",
                "user_id": project.user_id.id or self.env.user.id,
                "date_deadline": date.today() - timedelta(days=2),
            }
        )

    @api.model
    def _sc_demo_apply_showcase_profile(self, project, profile):
        vals = {
            "sc_project_showcase": True,
            "sc_project_showcase_ready": bool(profile.get("showcase_ready")),
        }
        if "health_state" in project._fields:
            vals["health_state"] = str(profile.get("health_state") or "warn")
        if "sc_execution_state" in project._fields:
            vals["sc_execution_state"] = str(profile.get("execution_state") or "done")
        project.write(vals)

        target_lifecycle = str(profile.get("target_lifecycle_state") or "").strip().lower()
        if target_lifecycle and getattr(project, "lifecycle_state", "") != target_lifecycle:
            manager = self.env.ref("smart_construction_demo.user_sc_project_manager_cap")
            project.with_user(manager).sudo(False).action_set_lifecycle_state(target_lifecycle)

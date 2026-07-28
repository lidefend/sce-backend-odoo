# -*- coding: utf-8 -*-
from psycopg2 import OperationalError

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare


class ScSubcontractPlan(models.Model):
    _name = "sc.subcontract.plan"
    _description = "分包计划"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "plan_date desc, id desc"

    name = fields.Char(string="计划单号", required=True, default="新建", tracking=True)
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, tracking=True)
    contract_id = fields.Many2one("construction.contract", string="关联合同", index=True)
    plan_date = fields.Date(string="计划日期", required=True, default=fields.Date.context_today, index=True)
    start_date = fields.Date(string="计划开始日期", index=True)
    end_date = fields.Date(string="计划结束日期", index=True)
    subcontract_scope = fields.Char(string="分包范围", required=True, index=True, tracking=True)
    subcontractor_id = fields.Many2one("res.partner", string="建议分包单位", index=True)
    owner_id = fields.Many2one("res.users", string="负责人", default=lambda self: self.env.user, index=True)
    currency_id = fields.Many2one("res.currency", string="币种", required=True, default=lambda self: self.env.company.currency_id.id)
    estimated_amount = fields.Monetary(string="预计金额", currency_field="currency_id", compute="_compute_estimated_amount", store=True)
    state = fields.Selection(
        [("draft", "草稿"), ("submitted", "已提交"), ("approved", "已确认"), ("cancel", "已取消")],
        string="状态",
        default="draft",
        index=True,
        tracking=True,
    )
    line_ids = fields.One2many("sc.subcontract.plan.line", "plan_id", string="计划明细")
    note = fields.Text(string="计划说明")
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    _sql_constraints = [
        ("legacy_subcontract_plan_unique", "unique(legacy_fact_model, legacy_fact_id)", "来源通用分包计划已迁移为专业分包计划。"),
    ]

    @api.depends("line_ids.estimated_amount")
    def _compute_estimated_amount(self):
        for record in self:
            record.estimated_amount = sum(record.line_ids.mapped("estimated_amount"))

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.subcontract.plan") or _("分包计划")
        return super().create(vals_list)

    def action_submit(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("只有草稿状态的分包计划可以提交。"))
            record._check_business_anchor()
            if not record.line_ids:
                raise ValidationError(_("提交分包计划前必须维护计划明细。"))
            record.line_ids._check_values()
        self.write({"state": "submitted"})
        return True

    def action_approve(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("只有已提交状态的分包计划可以确认。"))
            record._check_business_anchor()
            record.line_ids._check_values()
        self.write({"state": "approved"})
        return True

    def action_cancel(self):
        for record in self:
            if record.state not in ("draft", "submitted"):
                raise UserError(_("只有草稿或已提交状态的分包计划可以取消。"))
        self.write({"state": "cancel"})
        return True

    def action_reset_draft(self):
        for record in self:
            if record.state != "cancel":
                raise UserError(_("只有已取消状态的分包计划可以重置为草稿。"))
        self.write({"state": "draft"})
        return True

    def _check_business_anchor(self):
        for record in self:
            if record.contract_id:
                if record.contract_id.project_id != record.project_id:
                    raise UserError(_("分包计划关联合同必须属于当前项目。"))
                if record.subcontractor_id and record.contract_id.partner_id and record.subcontractor_id != record.contract_id.partner_id:
                    raise UserError(_("分包计划建议分包单位必须与关联合同相对方一致。"))

    @api.constrains("start_date", "end_date")
    def _check_date_order(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_("计划开始日期不能晚于计划结束日期。"))


class ScSubcontractPlanLine(models.Model):
    _name = "sc.subcontract.plan.line"
    _description = "分包计划明细"
    _order = "plan_id, sequence, id"

    plan_id = fields.Many2one("sc.subcontract.plan", string="计划单", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one("project.project", string="项目", related="plan_id.project_id", store=True, index=True)
    work_scope = fields.Char(string="分包工作范围", required=True)
    work_content = fields.Char(string="工作内容")
    planned_qty = fields.Float(string="计划数量", default=1)
    unit_name = fields.Char(string="单位")
    currency_id = fields.Many2one("res.currency", string="币种", related="plan_id.currency_id", store=True)
    estimated_amount = fields.Monetary(string="预计金额", currency_field="currency_id")
    note = fields.Char(string="备注")

    @api.constrains("planned_qty", "estimated_amount")
    def _check_values(self):
        for record in self:
            if record.planned_qty < 0:
                raise ValidationError(_("计划数量不能为负数。"))
            if record.estimated_amount < 0:
                raise ValidationError(_("预计金额不能为负数。"))


class ScSubcontractRequest(models.Model):
    _name = "sc.subcontract.request"
    _description = "分包申请"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(string="申请单号", required=True, default="新建", tracking=True)
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, tracking=True)
    plan_id = fields.Many2one("sc.subcontract.plan", string="来源分包计划", index=True)
    contract_id = fields.Many2one("construction.contract", string="关联合同", index=True)
    request_date = fields.Date(string="申请日期", required=True, default=fields.Date.context_today, index=True)
    need_start_date = fields.Date(string="需用开始日期", index=True)
    need_end_date = fields.Date(string="需用结束日期", index=True)
    subcontract_scope = fields.Char(string="申请分包范围", required=True, index=True, tracking=True)
    suggested_subcontractor_id = fields.Many2one("res.partner", string="建议分包单位", index=True)
    applicant_id = fields.Many2one("res.users", string="申请人", default=lambda self: self.env.user, index=True, tracking=True)
    department_id = fields.Many2one("hr.department", string="申请部门", index=True)
    priority = fields.Selection(
        [("normal", "普通"), ("urgent", "紧急")],
        string="需求优先级",
        default="normal",
        required=True,
        index=True,
    )
    currency_id = fields.Many2one("res.currency", string="币种", required=True, default=lambda self: self.env.company.currency_id.id)
    estimated_amount = fields.Monetary(string="申请预计金额", currency_field="currency_id", compute="_compute_estimated_amount", store=True)
    subcontract_type_text = fields.Char(
        string="分包类型",
        compute="_compute_request_formal_amount_fields",
        store=True,
        readonly=True,
    )
    quantity_total = fields.Float(
        string="数量",
        compute="_compute_request_formal_amount_fields",
        store=True,
        readonly=True,
    )
    price_unit = fields.Monetary(
        string="单价",
        currency_field="currency_id",
        compute="_compute_request_formal_amount_fields",
        store=True,
        readonly=True,
    )
    amount_total = fields.Monetary(
        string="金额",
        currency_field="currency_id",
        compute="_compute_request_formal_amount_fields",
        store=True,
        readonly=True,
    )
    monthly_amount_total = fields.Monetary(
        string="本月合价",
        currency_field="currency_id",
        compute="_compute_request_formal_amount_fields",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "草稿"), ("submitted", "已提交"), ("approved", "已确认"), ("cancel", "已取消")],
        string="状态",
        default="draft",
        index=True,
        tracking=True,
    )
    line_ids = fields.One2many("sc.subcontract.request.line", "request_id", string="申请明细")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_subcontract_request_attachment_rel",
        "request_id",
        "attachment_id",
        string="附件",
    )
    request_reason = fields.Text(string="申请原因")
    note = fields.Text(string="备注")
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    _sql_constraints = [
        ("legacy_subcontract_request_unique", "unique(legacy_fact_model, legacy_fact_id)", "来源通用分包申请已迁移为专业分包申请。"),
    ]

    @api.depends("line_ids.estimated_amount")
    def _compute_estimated_amount(self):
        for record in self:
            record.estimated_amount = sum(record.line_ids.mapped("estimated_amount"))

    @api.depends("line_ids.required_qty", "estimated_amount")
    def _compute_request_formal_amount_fields(self):
        for record in self:
            quantity = sum(record.line_ids.mapped("required_qty"))
            amount = record.estimated_amount or 0.0
            record.subcontract_type_text = False
            record.quantity_total = quantity
            record.price_unit = amount / quantity if quantity else 0.0
            record.amount_total = amount
            record.monthly_amount_total = amount

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.subcontract.request") or _("分包申请")
        return super().create(vals_list)

    def action_submit(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("只有草稿状态的分包申请可以提交。"))
            record._check_business_anchor()
            if not record.line_ids:
                raise ValidationError(_("提交分包申请前必须维护申请明细。"))
            record.line_ids._check_values()
        self.write({"state": "submitted"})
        return True

    def action_approve(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("只有已提交状态的分包申请可以确认。"))
            record._check_business_anchor()
            record.line_ids._check_values()
        self.write({"state": "approved"})
        return True

    def action_cancel(self):
        for record in self:
            if record.state not in ("draft", "submitted"):
                raise UserError(_("只有草稿或已提交状态的分包申请可以取消。"))
        self.write({"state": "cancel"})
        return True

    def action_reset_draft(self):
        for record in self:
            if record.state != "cancel":
                raise UserError(_("只有已取消状态的分包申请可以重置为草稿。"))
        self.write({"state": "draft"})
        return True

    def _check_business_anchor(self):
        for record in self:
            if record.plan_id:
                if record.plan_id.project_id != record.project_id:
                    raise UserError(_("分包申请来源计划必须属于当前项目。"))
                if record.plan_id.state != "approved":
                    raise UserError(_("分包申请只能引用已确认的分包计划。"))
                if (
                    record.suggested_subcontractor_id
                    and record.plan_id.subcontractor_id
                    and record.suggested_subcontractor_id != record.plan_id.subcontractor_id
                ):
                    raise UserError(_("分包申请建议分包单位必须与来源计划一致。"))
            if record.contract_id:
                if record.contract_id.project_id != record.project_id:
                    raise UserError(_("分包申请关联合同必须属于当前项目。"))
                if (
                    record.suggested_subcontractor_id
                    and record.contract_id.partner_id
                    and record.suggested_subcontractor_id != record.contract_id.partner_id
                ):
                    raise UserError(_("分包申请建议分包单位必须与关联合同相对方一致。"))

    def init(self):
        self.env.cr.execute(
            """
            UPDATE sc_subcontract_request request
               SET contract_id = matched.contract_id
              FROM (
                    SELECT r.id AS request_id,
                           MIN(c.id) AS contract_id
                      FROM sc_subcontract_request r
                      JOIN construction_contract c
                        ON c.type = 'in'
                       AND c.project_id = r.project_id
                       AND c.partner_id = r.suggested_subcontractor_id
                     WHERE r.contract_id IS NULL
                       AND r.legacy_fact_type = 'direct_acceptance:分包方单'
                       AND r.project_id IS NOT NULL
                       AND r.suggested_subcontractor_id IS NOT NULL
                     GROUP BY r.id
                    HAVING COUNT(c.id) = 1
              ) matched
             WHERE request.id = matched.request_id
            """
        )

    @api.constrains("need_start_date", "need_end_date")
    def _check_need_date_order(self):
        for record in self:
            if record.need_start_date and record.need_end_date and record.need_start_date > record.need_end_date:
                raise ValidationError(_("需用开始日期不能晚于需用结束日期。"))


class ScSubcontractRequestLine(models.Model):
    _name = "sc.subcontract.request.line"
    _description = "分包申请明细"
    _order = "request_id, sequence, id"

    request_id = fields.Many2one("sc.subcontract.request", string="申请单", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one("project.project", string="项目", related="request_id.project_id", store=True, index=True)
    work_scope = fields.Char(string="申请分包工作范围", required=True)
    work_content = fields.Char(string="工作内容")
    required_qty = fields.Float(string="申请数量", default=1)
    unit_name = fields.Char(string="单位")
    required_date = fields.Date(string="需用日期")
    currency_id = fields.Many2one("res.currency", string="币种", related="request_id.currency_id", store=True)
    estimated_amount = fields.Monetary(string="预计金额", currency_field="currency_id")
    note = fields.Char(string="备注")

    @api.constrains("required_qty", "estimated_amount")
    def _check_values(self):
        for record in self:
            if record.required_qty < 0:
                raise ValidationError(_("申请数量不能为负数。"))
            if record.estimated_amount < 0:
                raise ValidationError(_("预计金额不能为负数。"))


class ScSubcontractRegister(models.Model):
    _name = "sc.subcontract.register"
    _description = "分包登记"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "register_date desc, id desc"

    name = fields.Char(string="登记单号", required=True, default="新建", tracking=True)
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, tracking=True)
    request_id = fields.Many2one("sc.subcontract.request", string="来源分包申请", index=True)
    contract_id = fields.Many2one("construction.contract", string="分包合同", index=True)
    register_date = fields.Date(string="登记日期", required=True, default=fields.Date.context_today, index=True)
    start_date = fields.Date(string="履约开始日期", index=True)
    end_date = fields.Date(string="履约结束日期", index=True)
    subcontract_scope = fields.Char(string="登记分包范围", required=True, index=True, tracking=True)
    subcontractor_id = fields.Many2one("res.partner", string="分包单位", index=True, tracking=True)
    responsible_id = fields.Many2one("res.users", string="现场负责人", default=lambda self: self.env.user, index=True)
    currency_id = fields.Many2one("res.currency", string="币种", required=True, default=lambda self: self.env.company.currency_id.id)
    registered_amount = fields.Monetary(string="登记合同金额", currency_field="currency_id", compute="_compute_registered_amount", store=True)
    sign_date = fields.Date(string="签订时间", compute="_compute_register_boundary_fields", store=True, readonly=True)
    quantity_total = fields.Float(string="总数量", compute="_compute_register_boundary_fields", store=True, readonly=True)
    amount_total = fields.Monetary(
        string="金额",
        currency_field="currency_id",
        compute="_compute_register_boundary_fields",
        store=True,
        readonly=True,
    )
    invoice_amount = fields.Monetary(
        string="已开票金额",
        currency_field="currency_id",
        compute="_compute_register_boundary_fields",
        store=True,
        readonly=True,
    )
    paid_amount = fields.Monetary(
        string="已付款金额",
        currency_field="currency_id",
        compute="_compute_register_boundary_fields",
        store=True,
        readonly=True,
    )
    unpaid_amount = fields.Monetary(
        string="未付款金额",
        currency_field="currency_id",
        compute="_compute_register_boundary_fields",
        store=True,
        readonly=True,
    )
    uninvoiced_amount = fields.Monetary(
        string="未开票金额",
        currency_field="currency_id",
        compute="_compute_register_boundary_fields",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "草稿"), ("active", "已登记"), ("closed", "已关闭"), ("cancel", "已取消")],
        string="状态",
        default="draft",
        index=True,
        tracking=True,
    )
    line_ids = fields.One2many("sc.subcontract.register.line", "register_id", string="登记明细")
    management_note = fields.Text(string="管理要求")
    note = fields.Text(string="备注")
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    _sql_constraints = [
        ("legacy_subcontract_register_unique", "unique(legacy_fact_model, legacy_fact_id)", "来源通用分包登记已迁移为专业分包登记。"),
    ]

    @api.depends("line_ids.registered_amount")
    def _compute_registered_amount(self):
        for record in self:
            record.registered_amount = sum(record.line_ids.mapped("registered_amount"))

    @api.depends("register_date", "registered_amount", "line_ids.contract_qty")
    def _compute_register_boundary_fields(self):
        for record in self:
            amount = record.registered_amount or 0.0
            record.sign_date = record.register_date or False
            record.quantity_total = sum(record.line_ids.mapped("contract_qty"))
            record.amount_total = amount
            record.invoice_amount = 0.0
            record.paid_amount = 0.0
            record.unpaid_amount = amount
            record.uninvoiced_amount = amount

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        explicit_fields_by_vals = []
        for vals in vals_list:
            explicit_fields = {
                name
                for name in (
                    "project_id",
                    "contract_id",
                    "subcontractor_id",
                    "currency_id",
                )
                if vals.get(name)
            }
            explicit_fields_by_vals.append(explicit_fields)
            if vals.get("contract_id"):
                contract = self._sc_caller_visible_relation(
                    "construction.contract", vals["contract_id"]
                )
                vals.setdefault("project_id", contract.project_id.id)
                vals.setdefault("subcontractor_id", contract.partner_id.id)
                vals.setdefault("currency_id", contract.currency_id.id)
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.subcontract.register") or _("分包登记")
        records = super().create(vals_list)
        for record, explicit_fields in zip(records, explicit_fields_by_vals):
            record._sc_validate_subcontract_contract_authority(
                explicit_fields=explicit_fields
            )
        records._sc_validate_cumulative_registered_amounts(
            records.mapped("contract_id").ids
        )
        return records

    def write(self, vals):
        if self.env.context.get("sc_skip_subcontract_contract_authority"):
            return super().write(vals)
        explicit_fields = {
            name
            for name in (
                "project_id",
                "contract_id",
                "subcontractor_id",
                "currency_id",
            )
            if vals.get(name)
        }
        previous_contract_ids = set(self.mapped("contract_id").ids)
        if vals.get("contract_id"):
            self._sc_caller_visible_relation(
                "construction.contract", vals["contract_id"]
            )
        authority_changed = bool(
            {"project_id", "contract_id", "subcontractor_id", "currency_id"}
            & set(vals)
        )
        settlements = (
            self.line_ids.mapped("settlement_line_ids.settlement_id")
            if authority_changed
            else self.env["sc.subcontract.settlement"]
        )
        result = super().write(vals)
        self._sc_validate_subcontract_contract_authority(
            explicit_fields=explicit_fields
        )
        if authority_changed:
            settlements |= self.line_ids.mapped(
                "settlement_line_ids.settlement_id"
            )
        if settlements:
            settlements._sc_validate_register_settlement_authority()
        self._sc_validate_cumulative_registered_amounts(
            previous_contract_ids | set(self.mapped("contract_id").ids)
        )
        return result

    def unlink(self):
        if self.line_ids.mapped("settlement_line_ids"):
            raise UserError(_("已有分包结算引用的分包登记不能删除，请保留审计关系。"))
        return super().unlink()

    @api.model
    def _sc_caller_visible_relation(self, model_name, record_id):
        try:
            relation_id = int(record_id)
        except (TypeError, ValueError):
            relation_id = 0
        record = self.env[model_name].search([("id", "=", relation_id)], limit=1)
        if not record:
            raise AccessError(_("分包关系记录不存在或当前用户无权访问。"))
        return record

    def _sc_validate_subcontract_contract_authority(self, explicit_fields=None):
        explicit_fields = set(explicit_fields or ())
        for register in self:
            contract = register.contract_id
            if not contract:
                continue
            if contract.project_id.company_id != contract.company_id:
                raise ValidationError(_("分包合同项目与合同公司必须一致。"))
            targets = {
                "project_id": contract.project_id,
                "subcontractor_id": contract.partner_id,
                "currency_id": contract.currency_id,
            }
            for field_name, target in targets.items():
                if (
                    field_name in explicit_fields
                    and register[field_name]
                    and register[field_name] != target
                ):
                    raise ValidationError(
                        _("分包登记显式字段与权威分包合同范围冲突。")
                    )
            updates = {
                field_name: target.id
                for field_name, target in targets.items()
                if register[field_name] != target
            }
            if updates:
                register.with_context(
                    sc_skip_subcontract_contract_authority=True
                ).write(updates)

    @api.model
    def _sc_lock_cumulative_amount_contracts(self, contract_ids):
        contract_ids = tuple(
            sorted({int(contract_id) for contract_id in contract_ids if contract_id})
        )
        if not contract_ids:
            return self.env["construction.contract"]
        contract_model = self.env["construction.contract"]
        contract_model.flush_model(["amount_total", "currency_id"])
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute(
                    f"""
                        SELECT id
                          FROM {contract_model._table}
                         WHERE id IN %s
                         ORDER BY id
                           FOR UPDATE
                    """,
                    [contract_ids],
                )
                locked_ids = {row[0] for row in self.env.cr.fetchall()}
                if locked_ids == set(contract_ids):
                    self.env.cr.execute(
                        f"""
                            UPDATE {contract_model._table}
                               SET id = id
                             WHERE id IN %s
                        """,
                        [contract_ids],
                    )
        except OperationalError as error:
            if error.pgcode == "40001":
                raise ValidationError(
                    _(
                        "同一分包合同正在形成其他有效金额事实，"
                        "请刷新后按最新合同余额重试。"
                    )
                ) from error
            raise
        contracts = contract_model.search([("id", "in", contract_ids)])
        if (
            locked_ids != set(contract_ids)
            or set(contracts.ids) != locked_ids
        ):
            raise AccessError(_("分包合同不存在或当前用户无权访问。"))
        return contracts

    @api.model
    def _sc_validate_cumulative_registered_amounts(self, contract_ids):
        contracts = self._sc_lock_cumulative_amount_contracts(contract_ids)
        if not contracts:
            return
        self.flush_model(
            ["contract_id", "currency_id", "registered_amount", "state"]
        )
        self.env.cr.execute(
            f"""
                SELECT contract_id,
                       currency_id,
                       COALESCE(SUM(registered_amount), 0.0)
                  FROM {self._table}
                 WHERE contract_id IN %s
                   AND state IN %s
                 GROUP BY contract_id, currency_id
            """,
            [tuple(contracts.ids), ("active", "closed")],
        )
        amounts_by_contract = {}
        for contract_id, currency_id, amount in self.env.cr.fetchall():
            amounts_by_contract.setdefault(contract_id, []).append(
                (currency_id, amount)
            )
        for contract in contracts:
            total = 0.0
            for currency_id, amount in amounts_by_contract.get(
                contract.id, ()
            ):
                if currency_id != contract.currency_id.id:
                    raise ValidationError(
                        _("有效分包登记币种必须与分包合同币种一致。")
                    )
                total += amount
            if contract.currency_id.compare_amounts(
                total, contract.amount_total
            ) > 0:
                raise ValidationError(
                    _("有效分包登记累计含税金额不能超过分包合同含税金额。")
                )

    def action_register(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("只有草稿状态的分包登记可以确认登记。"))
            record._check_business_anchor()
            if not record.subcontractor_id:
                raise ValidationError(_("确认分包登记前必须维护分包单位。"))
            if not record.line_ids:
                raise ValidationError(_("确认分包登记前必须维护登记明细。"))
            record.line_ids._check_values()
        self.write({"state": "active"})
        return True

    def action_close(self):
        for record in self:
            if record.state != "active":
                raise UserError(_("只有已登记状态的分包登记可以关闭。"))
            record._check_business_anchor()
            record.line_ids._check_values()
        self.write({"state": "closed"})
        return True

    def action_cancel(self):
        for record in self:
            if record.state not in ("draft", "active"):
                raise UserError(_("只有草稿或已登记状态的分包登记可以取消。"))
        self.write({"state": "cancel"})
        return True

    def action_reset_draft(self):
        for record in self:
            if record.state != "cancel":
                raise UserError(_("只有已取消状态的分包登记可以重置为草稿。"))
        self.write({"state": "draft"})
        return True

    def _check_business_anchor(self):
        for record in self:
            if record.request_id:
                if record.request_id.project_id != record.project_id:
                    raise UserError(_("分包登记来源申请必须属于当前项目。"))
                if record.request_id.state != "approved":
                    raise UserError(_("分包登记只能引用已确认的分包申请。"))
                if (
                    record.subcontractor_id
                    and record.request_id.suggested_subcontractor_id
                    and record.subcontractor_id != record.request_id.suggested_subcontractor_id
                ):
                    raise UserError(_("分包登记单位必须与来源申请建议分包单位一致。"))
            if record.contract_id:
                if record.contract_id.project_id != record.project_id:
                    raise UserError(_("分包登记合同必须属于当前项目。"))
                if record.subcontractor_id and record.contract_id.partner_id and record.subcontractor_id != record.contract_id.partner_id:
                    raise UserError(_("分包登记单位必须与合同相对方一致。"))

    @api.constrains("start_date", "end_date")
    def _check_date_order(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_("履约开始日期不能晚于履约结束日期。"))


class ScSubcontractRegisterLine(models.Model):
    _name = "sc.subcontract.register.line"
    _description = "分包登记明细"
    _order = "register_id, sequence, id"

    register_id = fields.Many2one("sc.subcontract.register", string="登记单", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one("project.project", string="项目", related="register_id.project_id", store=True, index=True)
    work_scope = fields.Char(string="登记分包工作范围", required=True)
    work_content = fields.Char(string="工作内容")
    contract_qty = fields.Float(
        string="合同数量",
        default=1,
        digits="Product Unit of Measure",
    )
    unit_name = fields.Char(string="单位")
    currency_id = fields.Many2one("res.currency", string="币种", related="register_id.currency_id", store=True)
    registered_amount = fields.Monetary(string="登记金额", currency_field="currency_id")
    settlement_line_ids = fields.One2many(
        "sc.subcontract.settlement.line",
        "register_line_id",
        string="分包结算明细",
        copy=False,
    )
    note = fields.Char(string="备注")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        registers = records.mapped("register_id")
        registers._sc_validate_cumulative_registered_amounts(
            registers.mapped("contract_id").ids
        )
        return records

    def write(self, vals):
        if vals.get("register_id"):
            self.env["sc.subcontract.register"]._sc_caller_visible_relation(
                "sc.subcontract.register", vals["register_id"]
            )
        registers = self.mapped("register_id")
        previous_contract_ids = set(registers.mapped("contract_id").ids)
        settlements = self.mapped("settlement_line_ids.settlement_id")
        result = super().write(vals)
        self.mapped("register_id")._sc_validate_subcontract_contract_authority()
        settlements |= self.mapped("settlement_line_ids.settlement_id")
        if settlements:
            settlements._sc_validate_register_settlement_authority()
        if {"contract_qty", "unit_name"} & set(vals):
            self.env[
                "sc.subcontract.settlement"
            ]._sc_validate_cumulative_registered_quantities(self.ids)
        registers |= self.mapped("register_id")
        registers._sc_validate_cumulative_registered_amounts(
            previous_contract_ids | set(registers.mapped("contract_id").ids)
        )
        settlements._sc_validate_cumulative_settlement_amounts(
            settlements.mapped("contract_id").ids,
            self.ids,
        )
        return result

    def unlink(self):
        if self.settlement_line_ids:
            raise UserError(_("已有分包结算引用的登记明细不能删除，请保留审计关系。"))
        registers = self.mapped("register_id")
        contract_ids = registers.mapped("contract_id").ids
        result = super().unlink()
        registers._sc_validate_cumulative_registered_amounts(contract_ids)
        return result

    @api.constrains("contract_qty", "registered_amount")
    def _check_values(self):
        for record in self:
            if record.contract_qty < 0:
                raise ValidationError(_("合同数量不能为负数。"))
            if record.registered_amount < 0:
                raise ValidationError(_("登记金额不能为负数。"))


class ScSubcontractSettlement(models.Model):
    _name = "sc.subcontract.settlement"
    _description = "分包结算"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "settlement_date desc, id desc"

    name = fields.Char(string="结算单号", required=True, default="新建", tracking=True)
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, tracking=True)
    register_id = fields.Many2one("sc.subcontract.register", string="来源分包登记", index=True)
    contract_id = fields.Many2one("construction.contract", string="分包合同", index=True)
    subcontractor_id = fields.Many2one("res.partner", string="分包单位", required=True, index=True, tracking=True)
    settlement_date = fields.Date(string="结算日期", required=True, default=fields.Date.context_today, index=True)
    owner_id = fields.Many2one("res.users", string="经办人", default=lambda self: self.env.user, index=True)
    currency_id = fields.Many2one("res.currency", string="币种", required=True, default=lambda self: self.env.company.currency_id.id)
    amount_untaxed = fields.Monetary(string="未税金额", currency_field="currency_id", compute="_compute_amounts", store=True)
    tax_amount = fields.Monetary(string="税额", currency_field="currency_id", compute="_compute_amounts", store=True)
    amount_total = fields.Monetary(string="结算金额", currency_field="currency_id", compute="_compute_amounts", store=True)
    payment_paid_amount = fields.Monetary(
        string="已付款金额",
        currency_field="currency_id",
        compute="_compute_payment_boundary_amounts",
        store=True,
        readonly=True,
    )
    payment_unpaid_amount = fields.Monetary(
        string="未付款金额",
        currency_field="currency_id",
        compute="_compute_payment_boundary_amounts",
        store=True,
        readonly=True,
    )
    payment_requested_amount = fields.Monetary(
        string="已申请金额",
        currency_field="currency_id",
        compute="_compute_payment_boundary_amounts",
        store=True,
        readonly=True,
    )
    payment_unrequested_amount = fields.Monetary(
        string="未申请金额",
        currency_field="currency_id",
        compute="_compute_payment_boundary_amounts",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "草稿"), ("submitted", "已提交"), ("confirmed", "已确认"), ("cancel", "已取消")],
        string="状态",
        default="draft",
        index=True,
        tracking=True,
    )
    line_ids = fields.One2many("sc.subcontract.settlement.line", "settlement_id", string="结算明细")
    note = fields.Text(string="结算说明")
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    _sql_constraints = [
        ("legacy_subcontract_settlement_unique", "unique(legacy_fact_model, legacy_fact_id)", "来源通用分包结算已迁移为专业分包结算。"),
    ]

    @api.depends("line_ids.amount_untaxed", "line_ids.tax_amount", "line_ids.amount_total")
    def _compute_amounts(self):
        for record in self:
            record.amount_untaxed = sum(record.line_ids.mapped("amount_untaxed"))
            record.tax_amount = sum(record.line_ids.mapped("tax_amount"))
            record.amount_total = sum(record.line_ids.mapped("amount_total"))

    @api.depends("amount_total")
    def _compute_payment_boundary_amounts(self):
        for record in self:
            amount = record.amount_total or 0.0
            record.payment_paid_amount = 0.0
            record.payment_unpaid_amount = amount
            record.payment_requested_amount = 0.0
            record.payment_unrequested_amount = amount

    @api.model
    def _sc_validate_cumulative_registered_quantities(
        self, register_line_ids
    ):
        register_line_ids = tuple(
            sorted({int(line_id) for line_id in register_line_ids if line_id})
        )
        if not register_line_ids:
            return

        register_model = self.env["sc.subcontract.register.line"]
        settlement_line_model = self.env["sc.subcontract.settlement.line"]
        register_model.flush_model(["contract_qty", "unit_name"])
        self.flush_model(["state"])
        settlement_line_model.flush_model(
            ["settlement_id", "register_line_id", "qty", "unit_name"]
        )
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute(
                    f"""
                        SELECT id
                          FROM {register_model._table}
                         WHERE id IN %s
                         ORDER BY id
                           FOR UPDATE
                    """,
                    [register_line_ids],
                )
                locked_ids = {
                    row[0] for row in self.env.cr.fetchall()
                }
                if locked_ids == set(register_line_ids):
                    self.env.cr.execute(
                        f"""
                            UPDATE {register_model._table}
                               SET id = id
                             WHERE id IN %s
                        """,
                        [register_line_ids],
                    )
        except OperationalError as error:
            if error.pgcode == "40001":
                raise ValidationError(
                    _(
                        "同一分包登记正在形成其他有效结算，"
                        "请刷新后按最新剩余数量重试。"
                    )
                ) from error
            raise
        register_lines = register_model.search(
            [("id", "in", register_line_ids)]
        )
        if (
            locked_ids != set(register_line_ids)
            or set(register_lines.ids) != locked_ids
        ):
            raise AccessError(
                _("分包关系记录不存在或当前用户无权访问。")
            )

        self.env.cr.execute(
            f"""
                SELECT line.register_line_id,
                       line.unit_name,
                       COALESCE(SUM(line.qty), 0.0)
                  FROM {settlement_line_model._table} AS line
                  JOIN {self._table} AS settlement
                    ON settlement.id = line.settlement_id
                 WHERE line.register_line_id IN %s
                   AND settlement.state = %s
                 GROUP BY line.register_line_id, line.unit_name
            """,
            [register_line_ids, "confirmed"],
        )
        quantities_by_register = {}
        for register_line_id, unit_name, quantity in self.env.cr.fetchall():
            quantities_by_register.setdefault(register_line_id, []).append(
                (unit_name, quantity)
            )

        precision_digits = self.env[
            "decimal.precision"
        ].precision_get("Product Unit of Measure")
        for register_line in register_lines:
            groups = quantities_by_register.get(register_line.id, ())
            if not groups:
                continue
            if not register_line.unit_name:
                raise ValidationError(
                    _("有效分包结算要求登记明细具有明确且可比的数量单位。")
                )
            total_quantity = 0.0
            for settlement_unit, quantity in groups:
                if (
                    not settlement_unit
                    or settlement_unit != register_line.unit_name
                ):
                    raise ValidationError(
                        _(
                            "登记与结算数量单位缺失或不一致，"
                            "当前模型没有正式单位换算关系。"
                        )
                    )
                total_quantity += quantity
            if (
                float_compare(
                    total_quantity,
                    register_line.contract_qty,
                    precision_digits=precision_digits,
                )
                > 0
            ):
                raise ValidationError(
                    _("分包登记明细的有效累计结算数量不能超过登记数量。")
                )

    def _sc_validate_cumulative_settlement_quantities(self):
        register_line_ids = self.filtered(
            lambda settlement: settlement.state == "confirmed"
        ).line_ids.mapped("register_line_id").ids
        self._sc_validate_cumulative_registered_quantities(
            register_line_ids
        )

    @api.model
    def _sc_validate_cumulative_settlement_amounts(
        self, contract_ids, register_line_ids=()
    ):
        register_model = self.env["sc.subcontract.register"]
        contracts = register_model._sc_lock_cumulative_amount_contracts(
            contract_ids
        )
        if not contracts:
            return
        register_model._sc_validate_cumulative_registered_amounts(
            contracts.ids
        )
        self.flush_model(
            ["contract_id", "currency_id", "amount_total", "state"]
        )
        self.env.cr.execute(
            f"""
                SELECT contract_id,
                       currency_id,
                       COALESCE(SUM(amount_total), 0.0)
                  FROM {self._table}
                 WHERE contract_id IN %s
                   AND state = %s
                 GROUP BY contract_id, currency_id
            """,
            [tuple(contracts.ids), "confirmed"],
        )
        amounts_by_contract = {}
        for contract_id, currency_id, amount in self.env.cr.fetchall():
            amounts_by_contract.setdefault(contract_id, []).append(
                (currency_id, amount)
            )
        for contract in contracts:
            total = 0.0
            for currency_id, amount in amounts_by_contract.get(
                contract.id, ()
            ):
                if currency_id != contract.currency_id.id:
                    raise ValidationError(
                        _("有效分包结算币种必须与分包合同币种一致。")
                    )
                total += amount
            if contract.currency_id.compare_amounts(
                total, contract.amount_total
            ) > 0:
                raise ValidationError(
                    _("有效分包结算累计含税金额不能超过分包合同含税金额。")
                )

        register_line_ids = tuple(
            sorted({int(line_id) for line_id in register_line_ids if line_id})
        )
        if not register_line_ids:
            return
        register_line_model = self.env["sc.subcontract.register.line"]
        settlement_line_model = self.env["sc.subcontract.settlement.line"]
        register_line_model.flush_model(
            ["registered_amount", "currency_id", "register_id"]
        )
        settlement_line_model.flush_model(
            ["register_line_id", "settlement_id", "amount_total", "currency_id"]
        )
        register_lines = register_line_model.search(
            [("id", "in", register_line_ids)]
        )
        if set(register_lines.ids) != set(register_line_ids):
            raise AccessError(
                _("分包关系记录不存在或当前用户无权访问。")
            )
        self.env.cr.execute(
            f"""
                SELECT line.register_line_id,
                       line.currency_id,
                       COALESCE(SUM(line.amount_total), 0.0)
                  FROM {settlement_line_model._table} AS line
                  JOIN {self._table} AS settlement
                    ON settlement.id = line.settlement_id
                 WHERE line.register_line_id IN %s
                   AND settlement.state = %s
                 GROUP BY line.register_line_id, line.currency_id
            """,
            [register_line_ids, "confirmed"],
        )
        amounts_by_register_line = {}
        for line_id, currency_id, amount in self.env.cr.fetchall():
            amounts_by_register_line.setdefault(line_id, []).append(
                (currency_id, amount)
            )
        for register_line in register_lines:
            contract = register_line.register_id.contract_id
            if not contract:
                continue
            total = 0.0
            for currency_id, amount in amounts_by_register_line.get(
                register_line.id, ()
            ):
                if currency_id != contract.currency_id.id:
                    raise ValidationError(
                        _("有效分包结算币种必须与来源登记合同币种一致。")
                    )
                total += amount
            if contract.currency_id.compare_amounts(
                total, register_line.registered_amount
            ) > 0:
                raise ValidationError(
                    _("有效分包结算累计含税金额不能超过来源登记明细金额。")
                )

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        explicit_fields_by_vals = []
        for vals in vals_list:
            explicit_fields_by_vals.append(
                {
                    name
                    for name in (
                        "project_id",
                        "register_id",
                        "contract_id",
                        "subcontractor_id",
                        "currency_id",
                    )
                    if vals.get(name)
                }
            )
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.subcontract.settlement") or _("分包结算")
        batched_records = super(
            ScSubcontractSettlement,
            self.with_context(sc_subcontract_register_authority_batch=True),
        ).create(vals_list)
        records = batched_records.with_env(self.env)
        for record, explicit_fields in zip(records, explicit_fields_by_vals):
            record._sc_validate_register_settlement_authority(
                explicit_fields=explicit_fields,
                relation_changed=True,
            )
        records._sc_validate_cumulative_settlement_quantities()
        records._sc_validate_cumulative_settlement_amounts(
            records.mapped("contract_id").ids,
            records.line_ids.mapped("register_line_id").ids,
        )
        return records

    def write(self, vals):
        if self.env.context.get("sc_skip_subcontract_register_authority"):
            return super().write(vals)
        affected_register_line_ids = set(
            self.line_ids.mapped("register_line_id").ids
        )
        explicit_fields = {
            name
            for name in (
                "project_id",
                "register_id",
                "contract_id",
                "subcontractor_id",
                "currency_id",
            )
            if vals.get(name)
        }
        batched = self.with_context(
            sc_subcontract_register_authority_batch=True
        )
        result = super(ScSubcontractSettlement, batched).write(vals)
        self._sc_validate_register_settlement_authority(
            explicit_fields=explicit_fields,
            relation_changed="line_ids" in vals,
        )
        affected_register_line_ids.update(
            self.line_ids.mapped("register_line_id").ids
        )
        self._sc_validate_cumulative_registered_quantities(
            affected_register_line_ids
        )
        self._sc_validate_cumulative_settlement_amounts(
            self.mapped("contract_id").ids,
            affected_register_line_ids,
        )
        return result

    def unlink(self):
        if self.line_ids.mapped("register_line_id"):
            raise UserError(_("已有正式登记范围的分包结算不能删除，请保留审计关系。"))
        return super().unlink()

    def _sc_validate_register_settlement_authority(
        self, explicit_fields=None, relation_changed=False
    ):
        explicit_fields = set(explicit_fields or ())
        for settlement in self:
            lines = settlement.line_ids
            scoped_lines = lines.filtered("register_line_id")
            if not scoped_lines:
                if "register_id" in explicit_fields and settlement.register_id:
                    raise ValidationError(
                        _("分包结算头部登记只能投影自正式登记明细关系。")
                    )
                if relation_changed and (
                    settlement.register_id or settlement.contract_id
                ):
                    settlement.with_context(
                        sc_skip_subcontract_register_authority=True
                    ).write(
                        {
                            "register_id": False,
                            "contract_id": False,
                        }
                    )
                continue
            if len(scoped_lines) != len(lines):
                raise ValidationError(
                    _("关联分包登记时，每条结算明细都必须显式引用登记明细。")
                )
            scoped_lines._sc_validate_register_relation_state()
            register_lines = scoped_lines.mapped("register_line_id")
            registers = register_lines.mapped("register_id")
            contracts = registers.mapped("contract_id")
            if (
                len(contracts) != 1
                or registers.filtered(lambda register: not register.contract_id)
            ):
                raise ValidationError(
                    _("分包结算完整登记集合必须收敛到唯一分包合同。")
                )
            contract = contracts[0]
            if contract.project_id.company_id != contract.company_id:
                raise ValidationError(_("分包合同项目与合同公司必须一致。"))
            for register in registers:
                if register.project_id != contract.project_id:
                    raise ValidationError(_("分包登记项目与权威合同项目冲突。"))
                if register.subcontractor_id != contract.partner_id:
                    raise ValidationError(_("分包登记单位与权威合同相对方冲突。"))
                if register.currency_id != contract.currency_id:
                    raise ValidationError(_("分包登记币种与权威合同币种冲突。"))
            targets = {
                "project_id": contract.project_id,
                "contract_id": contract,
                "subcontractor_id": contract.partner_id,
                "currency_id": contract.currency_id,
                "register_id": registers if len(registers) == 1 else False,
            }
            for field_name, target in targets.items():
                if (
                    field_name in explicit_fields
                    and settlement[field_name]
                    and settlement[field_name] != target
                ):
                    raise ValidationError(
                        _("分包结算显式头部字段与完整登记合同范围冲突。")
                    )
            updates = {}
            for field_name, target in targets.items():
                if settlement[field_name] != target:
                    updates[field_name] = target.id if target else False
            if updates:
                settlement.with_context(
                    sc_skip_subcontract_register_authority=True
                ).write(updates)

    def action_submit(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("只有草稿状态的分包结算可以提交。"))
            record._check_business_anchor()
            if not record.line_ids:
                raise ValidationError(_("提交分包结算前必须维护结算明细。"))
            record.line_ids._check_values()
        self.write({"state": "submitted"})
        return True

    def action_confirm(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("只有已提交状态的分包结算可以确认。"))
            record._check_business_anchor()
            record.line_ids._check_values()
        self.write({"state": "confirmed"})
        return True

    def action_cancel(self):
        for record in self:
            if record.state not in ("draft", "submitted"):
                raise UserError(_("只有草稿或已提交状态的分包结算可以取消。"))
        self.write({"state": "cancel"})
        return True

    def action_reset_draft(self):
        for record in self:
            if record.state != "cancel":
                raise UserError(_("只有已取消状态的分包结算可以重置为草稿。"))
        self.write({"state": "draft"})
        return True

    def _check_business_anchor(self):
        for record in self:
            record._sc_validate_register_settlement_authority()
            scoped_registers = record.line_ids.mapped(
                "register_line_id.register_id"
            )
            if scoped_registers.filtered(
                lambda register: register.state not in ("active", "closed")
            ):
                raise UserError(_("分包结算只能引用已登记或已关闭的分包登记。"))
            if record.register_id:
                if record.register_id.project_id != record.project_id:
                    raise UserError(_("分包结算来源登记必须属于当前项目。"))
                if record.register_id.state not in ("active", "closed"):
                    raise UserError(_("分包结算只能引用已登记或已关闭的分包登记。"))
                if record.register_id.subcontractor_id and record.register_id.subcontractor_id != record.subcontractor_id:
                    raise UserError(_("分包结算单位必须与来源登记一致。"))
            if record.contract_id:
                if record.contract_id.project_id != record.project_id:
                    raise UserError(_("分包结算合同必须属于当前项目。"))
                if record.contract_id.partner_id and record.contract_id.partner_id != record.subcontractor_id:
                    raise UserError(_("分包结算单位必须与合同相对方一致。"))


class ScSubcontractSettlementLine(models.Model):
    _name = "sc.subcontract.settlement.line"
    _description = "分包结算明细"
    _order = "settlement_id, sequence, id"

    settlement_id = fields.Many2one("sc.subcontract.settlement", string="结算单", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one("project.project", string="项目", related="settlement_id.project_id", store=True, index=True)
    register_id = fields.Many2one("sc.subcontract.register", string="分包登记", related="settlement_id.register_id", store=True, index=True)
    register_line_id = fields.Many2one(
        "sc.subcontract.register.line",
        string="来源登记明细",
        index=True,
        ondelete="restrict",
        copy=False,
    )
    work_scope = fields.Char(string="结算分包工作范围", required=True)
    work_content = fields.Char(string="工作内容")
    qty = fields.Float(
        string="结算数量",
        required=True,
        default=1,
        digits="Product Unit of Measure",
    )
    unit_name = fields.Char(string="单位")
    currency_id = fields.Many2one("res.currency", string="币种", related="settlement_id.currency_id", store=True)
    unit_price = fields.Monetary(string="结算单价", currency_field="currency_id", required=True)
    tax_rate = fields.Float(string="税率%")
    amount_untaxed = fields.Monetary(string="未税金额", currency_field="currency_id", compute="_compute_amounts", store=True)
    tax_amount = fields.Monetary(string="税额", currency_field="currency_id", compute="_compute_amounts", store=True)
    amount_total = fields.Monetary(string="含税金额", currency_field="currency_id", compute="_compute_amounts", store=True)
    note = fields.Char(string="备注")

    @api.model
    def _sc_resolve_register_relations(self, vals, current=None):
        resolver = self.env[
            "sc.subcontract.register"
        ]._sc_caller_visible_relation
        settlement = resolver(
            "sc.subcontract.settlement",
            vals.get(
                "settlement_id",
                current.settlement_id.id if current else False,
            ),
        )
        register_line_id = vals.get(
            "register_line_id",
            current.register_line_id.id if current else False,
        )
        register_line = (
            resolver("sc.subcontract.register.line", register_line_id)
            if register_line_id
            else self.env["sc.subcontract.register.line"]
        )
        if register_line:
            resolver("sc.subcontract.register", register_line.register_id.id)
            if register_line.register_id.contract_id:
                resolver(
                    "construction.contract",
                    register_line.register_id.contract_id.id,
                )
        return settlement, register_line

    @api.model
    def _sc_validate_register_pair(self, settlement, register_line):
        if not register_line:
            return
        register = register_line.register_id
        if not register.contract_id:
            raise ValidationError(
                _("登记明细必须具有正式分包合同后才能进入结算关系。")
            )
        register._sc_validate_subcontract_contract_authority()

    def _sc_validate_register_relation_state(self):
        for line in self:
            self._sc_validate_register_pair(
                line.settlement_id,
                line.register_line_id,
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sc_validate_register_pair(
                *self._sc_resolve_register_relations(vals)
            )
        records = super().create(vals_list)
        records._sc_validate_register_relation_state()
        if not self.env.context.get(
            "sc_subcontract_register_authority_batch"
        ):
            settlements = records.mapped("settlement_id")
            settlements._sc_validate_register_settlement_authority(
                relation_changed=True
            )
            settlements._sc_validate_cumulative_registered_quantities(
                records.mapped("register_line_id").ids
            )
            settlements._sc_validate_cumulative_settlement_amounts(
                settlements.mapped("contract_id").ids,
                records.mapped("register_line_id").ids,
            )
        return records

    def write(self, vals):
        settlements = self.mapped("settlement_id")
        affected_register_line_ids = set(
            self.mapped("register_line_id").ids
        )
        for line in self:
            self._sc_validate_register_pair(
                *self._sc_resolve_register_relations(vals, current=line)
            )
        result = super().write(vals)
        self._sc_validate_register_relation_state()
        settlements |= self.mapped("settlement_id")
        if not self.env.context.get(
            "sc_subcontract_register_authority_batch"
        ):
            settlements._sc_validate_register_settlement_authority(
                relation_changed="register_line_id" in vals
            )
            affected_register_line_ids.update(
                self.mapped("register_line_id").ids
            )
            settlements._sc_validate_cumulative_registered_quantities(
                affected_register_line_ids
            )
            settlements._sc_validate_cumulative_settlement_amounts(
                settlements.mapped("contract_id").ids,
                affected_register_line_ids,
            )
        return result

    def unlink(self):
        if self.mapped("register_line_id"):
            raise UserError(_("已有正式登记来源的分包结算明细不能删除，请先保留或解除关系。"))
        settlements = self.mapped("settlement_id")
        result = super().unlink()
        if not self.env.context.get(
            "sc_subcontract_register_authority_batch"
        ):
            settlements._sc_validate_register_settlement_authority(
                relation_changed=True
            )
        return result

    @api.depends("qty", "unit_price", "tax_rate")
    def _compute_amounts(self):
        for record in self:
            amount_untaxed = record.qty * record.unit_price
            tax_amount = amount_untaxed * record.tax_rate / 100
            record.amount_untaxed = amount_untaxed
            record.tax_amount = tax_amount
            record.amount_total = amount_untaxed + tax_amount

    @api.constrains("qty", "unit_price", "tax_rate")
    def _check_values(self):
        for record in self:
            if record.qty <= 0:
                raise ValidationError(_("结算数量必须大于0。"))
            if record.unit_price < 0:
                raise ValidationError(_("结算单价不能为负数。"))
            if record.tax_rate < 0:
                raise ValidationError(_("税率不能为负数。"))


class ConstructionContractSubcontractAuthority(models.Model):
    _inherit = "construction.contract"

    subcontract_register_ids = fields.One2many(
        "sc.subcontract.register",
        "contract_id",
        string="分包履约登记",
        copy=False,
    )

    def write(self, vals):
        authority_changed = bool(
            {
                "project_id",
                "partner_id",
                "company_id",
                "currency_id",
                "amount_total",
            }
            & set(vals)
        )
        registers = (
            self.mapped("subcontract_register_ids")
            if authority_changed
            else self.env["sc.subcontract.register"]
        )
        settlements = registers.line_ids.mapped(
            "settlement_line_ids.settlement_id"
        )
        result = super().write(vals)
        if authority_changed:
            registers |= self.mapped("subcontract_register_ids")
            registers._sc_validate_subcontract_contract_authority()
            settlements |= registers.line_ids.mapped(
                "settlement_line_ids.settlement_id"
            )
            settlements._sc_validate_register_settlement_authority()
            registers._sc_validate_cumulative_registered_amounts(self.ids)
            self.env[
                "sc.subcontract.settlement"
            ]._sc_validate_cumulative_settlement_amounts(
                self.ids,
                registers.line_ids.ids,
            )
        return result


class ConstructionContractLineSubcontractAmountAuthority(models.Model):
    _inherit = "construction.contract.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        contracts = lines.mapped("contract_id")
        contracts.flush_recordset(["amount_total"])
        registers = contracts.mapped("subcontract_register_ids")
        registers._sc_validate_cumulative_registered_amounts(contracts.ids)
        self.env[
            "sc.subcontract.settlement"
        ]._sc_validate_cumulative_settlement_amounts(
            contracts.ids,
            registers.line_ids.ids,
        )
        return lines

    def write(self, vals):
        contracts = self.mapped("contract_id")
        result = super().write(vals)
        contracts |= self.mapped("contract_id")
        contracts.flush_recordset(["amount_total"])
        registers = contracts.mapped("subcontract_register_ids")
        registers._sc_validate_cumulative_registered_amounts(contracts.ids)
        self.env[
            "sc.subcontract.settlement"
        ]._sc_validate_cumulative_settlement_amounts(
            contracts.ids,
            registers.line_ids.ids,
        )
        return result

    def unlink(self):
        contracts = self.mapped("contract_id")
        result = super().unlink()
        contracts.flush_recordset(["amount_total"])
        registers = contracts.mapped("subcontract_register_ids")
        registers._sc_validate_cumulative_registered_amounts(contracts.ids)
        self.env[
            "sc.subcontract.settlement"
        ]._sc_validate_cumulative_settlement_amounts(
            contracts.ids,
            registers.line_ids.ids,
        )
        return result


class ScSubcontractPrice(models.Model):
    _name = "sc.subcontract.price"
    _description = "分包价格库"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "effective_date desc, id desc"

    name = fields.Char(string="价格编号", required=True, default="新建", tracking=True)
    project_id = fields.Many2one("project.project", string="适用项目", index=True, tracking=True)
    subcontractor_id = fields.Many2one("res.partner", string="分包单位", index=True)
    work_scope = fields.Char(string="分包工作范围", required=True, index=True, tracking=True)
    work_content = fields.Char(string="工作内容")
    unit_name = fields.Char(string="计价单位", required=True, default="项")
    currency_id = fields.Many2one("res.currency", string="币种", required=True, default=lambda self: self.env.company.currency_id.id)
    unit_price = fields.Monetary(string="单价", currency_field="currency_id", required=True, tracking=True)
    tax_rate = fields.Float(string="税率%")
    effective_date = fields.Date(string="生效日期", required=True, default=fields.Date.context_today, index=True)
    expire_date = fields.Date(string="失效日期", index=True)
    state = fields.Selection(
        [("draft", "草稿"), ("active", "生效"), ("inactive", "停用")],
        string="状态",
        default="draft",
        index=True,
        tracking=True,
    )
    note = fields.Text(string="价格说明")
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    _sql_constraints = [
        ("legacy_subcontract_price_unique", "unique(legacy_fact_model, legacy_fact_id)", "来源通用分包价格已迁移为专业分包价格。"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.subcontract.price") or _("分包价格")
        return super().create(vals_list)

    def action_activate(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("只有草稿状态的分包价格可以生效。"))
        self._check_values()
        self.write({"state": "active"})
        return True

    def action_deactivate(self):
        for record in self:
            if record.state != "active":
                raise UserError(_("只有生效状态的分包价格可以停用。"))
        self.write({"state": "inactive"})
        return True

    def action_reset_draft(self):
        for record in self:
            if record.state != "inactive":
                raise UserError(_("只有停用状态的分包价格可以重置为草稿。"))
        self.write({"state": "draft"})
        return True

    @api.constrains("unit_price", "tax_rate", "effective_date", "expire_date")
    def _check_values(self):
        for record in self:
            if record.unit_price < 0:
                raise ValidationError(_("分包单价不能为负数。"))
            if record.tax_rate < 0:
                raise ValidationError(_("税率不能为负数。"))
            if record.effective_date and record.expire_date and record.effective_date > record.expire_date:
                raise ValidationError(_("生效日期不能晚于失效日期。"))

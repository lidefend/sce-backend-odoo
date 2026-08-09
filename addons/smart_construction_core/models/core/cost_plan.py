# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProjectCostPlan(models.Model):
    """Versioned management target generated from one published BOQ snapshot."""

    _name = "project.cost.plan"
    _description = "项目目标成本计划"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "project_id, version_date desc, id desc"

    name = fields.Char("计划名称", required=True, tracking=True)
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, tracking=True)
    boq_version_id = fields.Many2one(
        "project.boq.version",
        string="来源清单版本",
        required=True,
        domain="[('project_id', '=', project_id), ('state', '=', 'published')]",
        tracking=True,
    )
    version_code = fields.Char("版本号", required=True, index=True, tracking=True)
    version_date = fields.Date("版本日期", default=fields.Date.context_today, required=True)
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("validated", "已校验"),
            ("published", "已发布"),
            ("adjusting", "调整中"),
            ("archived", "已归档"),
        ],
        string="状态",
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    source_plan_id = fields.Many2one("project.cost.plan", string="调整来源", readonly=True)
    line_ids = fields.One2many("project.cost.plan.line", "plan_id", string="计划明细")
    currency_id = fields.Many2one(
        "res.currency", related="project_id.company_id.currency_id", store=True, readonly=True
    )
    budget_amount = fields.Monetary(
        "预算成本", compute="_compute_totals", store=True, currency_field="currency_id"
    )
    target_amount = fields.Monetary(
        "目标成本", compute="_compute_totals", store=True, currency_field="currency_id"
    )
    saving_amount = fields.Monetary(
        "计划节余", compute="_compute_totals", store=True, currency_field="currency_id"
    )
    line_count = fields.Integer("明细数", compute="_compute_totals", store=True)
    validated_at = fields.Datetime("校验时间", readonly=True)
    validated_by_id = fields.Many2one("res.users", string="校验人", readonly=True)
    published_at = fields.Datetime("发布时间", readonly=True)
    published_by_id = fields.Many2one("res.users", string="发布人", readonly=True)
    note = fields.Text("说明")

    _sql_constraints = [
        ("project_version_unique", "unique(project_id, version_code)", "同一项目的成本计划版本号必须唯一。"),
    ]

    @api.depends("line_ids.budget_amount", "line_ids.target_amount")
    def _compute_totals(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.budget_amount = sum(rec.line_ids.mapped("budget_amount"))
            rec.target_amount = sum(rec.line_ids.mapped("target_amount"))
            rec.saving_amount = rec.budget_amount - rec.target_amount

    @api.constrains("project_id", "boq_version_id")
    def _check_source_scope(self):
        for rec in self:
            if rec.boq_version_id.project_id != rec.project_id:
                raise ValidationError(_("成本计划与来源清单必须属于同一项目。"))

    def action_generate_from_boq(self):
        """Generate a deterministic editable draft from the imported analysis snapshot."""
        for plan in self:
            if plan.state not in ("draft", "adjusting"):
                raise UserError(_("只有草稿或调整中的成本计划可以生成明细。"))
            if plan.boq_version_id.state != "published":
                raise UserError(_("成本计划只能基于已发布清单版本生成。"))
            if plan.line_ids:
                raise UserError(_("成本计划已有明细，不能重复生成。"))
            vals_list = []
            for analysis in plan.boq_version_id.line_ids.mapped("analysis_id"):
                boq_qty = analysis.boq_line_id.quantity or 0.0
                detailed_material_amount = 0.0
                for resource in analysis.resource_line_ids:
                    detailed_material_amount += (
                        resource.budget_consumption * resource.budget_unit_price
                    )
                    vals_list.append(
                        {
                            "plan_id": plan.id,
                            "boq_line_id": analysis.boq_line_id.id,
                            "analysis_id": analysis.id,
                            "cost_type": resource.resource_type,
                            "line_role": (
                                "deduction"
                                if resource.budget_consumption < 0
                                or resource.budget_unit_price < 0
                                else "cost"
                            ),
                            "name": resource.name,
                            "unit_raw": resource.unit_raw,
                            "boq_quantity": boq_qty,
                            "budget_unit_consumption": resource.budget_consumption,
                            "budget_unit_price": resource.budget_unit_price,
                            "target_unit_consumption": resource.budget_consumption,
                            "target_unit_price": resource.budget_unit_price,
                            "adjustment_ratio": 100.0,
                            "source_resource_line_id": resource.id,
                        }
                    )
                material_residual = analysis.material_unit_amount - detailed_material_amount
                if abs(material_residual) > 0.000001:
                    vals_list.append(
                        {
                            "plan_id": plan.id,
                            "boq_line_id": analysis.boq_line_id.id,
                            "analysis_id": analysis.id,
                            "cost_type": "material",
                            "line_role": "adjustment",
                            "name": _("其他材料费（分析差额）"),
                            "unit_raw": analysis.uom_raw,
                            "boq_quantity": boq_qty,
                            "budget_unit_consumption": 1.0,
                            "budget_unit_price": material_residual,
                            "target_unit_consumption": 1.0,
                            "target_unit_price": material_residual,
                            "adjustment_ratio": 100.0,
                            "calculation_mode": "amount",
                        }
                    )
                for cost_type, label, amount in (
                    ("labor", _("人工费"), analysis.labor_unit_amount),
                    ("machine", _("机械费"), analysis.machine_unit_amount),
                    ("overhead", _("管理费"), analysis.overhead_unit_amount),
                ):
                    if amount:
                        vals_list.append(
                            {
                                "plan_id": plan.id,
                                "boq_line_id": analysis.boq_line_id.id,
                                "analysis_id": analysis.id,
                                "cost_type": cost_type,
                                "line_role": "adjustment" if amount < 0 else "cost",
                                "name": label,
                                "unit_raw": analysis.uom_raw,
                                "boq_quantity": boq_qty,
                                "budget_unit_consumption": 1.0,
                                "budget_unit_price": amount,
                                "target_unit_consumption": 1.0,
                                "target_unit_price": amount,
                                "adjustment_ratio": 100.0,
                                "calculation_mode": "amount",
                            }
                        )
            analysed_lines = plan.boq_version_id.analysis_ids.mapped("boq_line_id")
            supplemental_lines = plan.boq_version_id.line_ids.filtered(
                lambda line: line.line_type == "item"
                and not line.is_calculation_detail
                and line not in analysed_lines
                and line.boq_category in {"total_measure", "fee", "tax", "other"}
            )
            for source in supplemental_lines:
                cost_type = {
                    "total_measure": "measure",
                    "fee": "fee",
                    "tax": "tax",
                    "other": "other",
                }[source.boq_category]
                source_amount = source.imported_amount if source.has_imported_amount else source.amount_leaf
                vals_list.append(
                    {
                        "plan_id": plan.id,
                        "boq_line_id": source.id,
                        "cost_type": cost_type,
                        "line_role": "deduction" if source_amount < 0 else "cost",
                        "name": source.name,
                        "unit_raw": source.uom_id.name,
                        "boq_quantity": 1.0,
                        "budget_unit_consumption": 1.0,
                        "budget_unit_price": source_amount,
                        "target_unit_consumption": 1.0,
                        "target_unit_price": source_amount,
                        "adjustment_ratio": 100.0,
                        "calculation_mode": "rate" if source.has_source_rate else "amount",
                        "source_calc_base": source.source_calc_base,
                        "budget_rate": source.source_rate,
                        "target_rate": source.source_rate,
                    }
                )
            for source in plan.boq_version_id.summary_component_ids.filtered(
                lambda row: row.component_type in {"fee", "tax"} and row.amount
            ):
                vals_list.append(
                    {
                        "plan_id": plan.id,
                        "source_summary_component_id": source.id,
                        "cost_type": source.component_type,
                        "line_role": "deduction" if source.amount < 0 else "cost",
                        "name": source.name,
                        "unit_raw": "项",
                        "boq_quantity": 1.0,
                        "budget_unit_consumption": 1.0,
                        "budget_unit_price": source.amount,
                        "target_unit_consumption": 1.0,
                        "target_unit_price": source.amount,
                        "adjustment_ratio": 100.0,
                        "calculation_mode": "rate" if source.source_rate else "amount",
                        "source_calc_base": source.calc_base or source.source_sheet_name,
                        "budget_rate": source.source_rate,
                        "target_rate": source.source_rate,
                    }
                )
            if not vals_list:
                raise UserError(_("来源清单没有可用于成本计划的综合单价分析。"))
            self.env["project.cost.plan.line"].create(vals_list)
        return True

    def action_open_lines(self):
        """Open the scalable, paged compilation ledger for this plan."""
        self.ensure_one()
        action = self.env.ref(
            "smart_construction_core.action_project_cost_plan_line"
        ).read()[0]
        action.update(
            {
                "name": _("%s · 成本明细") % self.display_name,
                "domain": [("plan_id", "=", self.id)],
                "context": {
                    "default_plan_id": self.id,
                    "default_project_id": self.project_id.id,
                },
            }
        )
        return action

    def action_validate(self):
        for plan in self:
            if plan.state not in ("draft", "adjusting"):
                raise UserError(_("只有草稿或调整中的成本计划可以校验。"))
            if not plan.line_ids:
                raise UserError(_("成本计划没有明细。"))
            invalid_cost_lines = plan.line_ids.filtered(
                lambda line: line.line_role == "cost"
                and (
                    line.target_unit_consumption < 0
                    or line.target_unit_price < 0
                    or line.adjustment_ratio < 0
                    or (line.calculation_mode == "rate" and line.target_rate < 0)
                )
            )
            if invalid_cost_lines:
                sample = "、".join(invalid_cost_lines[:3].mapped("name"))
                raise UserError(
                    _("普通成本项不能使用负单耗、负单价、负费率或负调整比例。请检查：%s")
                    % sample
                )
            invalid_deductions = plan.line_ids.filtered(
                lambda line: line.line_role == "deduction" and line.target_amount > 0.000001
            )
            if invalid_deductions:
                sample = "、".join(invalid_deductions[:3].mapped("name"))
                raise UserError(_("扣减项的目标金额不能为正数。请检查：%s") % sample)
            plan.write(
                {
                    "state": "validated",
                    "validated_at": fields.Datetime.now(),
                    "validated_by_id": self.env.user.id,
                }
            )
        return True

    def action_publish(self):
        for plan in self:
            if plan.state != "validated":
                raise UserError(_("只有已校验成本计划可以发布。"))
            siblings = self.search(
                [("project_id", "=", plan.project_id.id), ("state", "=", "published"), ("id", "!=", plan.id)]
            )
            siblings.write({"state": "archived"})
            plan.write(
                {
                    "state": "published",
                    "published_at": fields.Datetime.now(),
                    "published_by_id": self.env.user.id,
                }
            )
        return True

    def action_start_adjustment(self):
        self.ensure_one()
        if self.state != "published":
            raise UserError(_("只有已发布成本计划可以发起调整版本。"))
        suffix = fields.Date.context_today(self).strftime("%Y%m%d")
        base_code = "%s-A%s" % (self.version_code, suffix)
        existing = self.search_count(
            [("project_id", "=", self.project_id.id), ("version_code", "like", base_code + "%")]
        )
        new_code = "%s-%02d" % (base_code, existing + 1)
        line_commands = []
        copy_fields = [
            "sequence",
            "boq_line_id",
            "analysis_id",
            "source_resource_line_id",
            "source_summary_component_id",
            "cost_type",
            "line_role",
            "name",
            "calculation_mode",
            "source_calc_base",
            "budget_rate",
            "target_rate",
            "unit_raw",
            "boq_quantity",
            "budget_unit_consumption",
            "budget_unit_price",
            "target_unit_consumption",
            "target_unit_price",
            "adjustment_ratio",
        ]
        for line in self.line_ids:
            values = {}
            for field_name in copy_fields:
                value = line[field_name]
                values[field_name] = value.id if line._fields[field_name].type == "many2one" else value
            line_commands.append((0, 0, values))
        revision = self.create(
            {
                "name": _("%s 调整") % self.name,
                "project_id": self.project_id.id,
                "boq_version_id": self.boq_version_id.id,
                "version_code": new_code,
                "version_date": fields.Date.context_today(self),
                "state": "adjusting",
                "source_plan_id": self.id,
                "line_ids": line_commands,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": revision.id,
            "view_mode": "form",
            "target": "current",
        }

    def write(self, vals):
        protected = {"project_id", "boq_version_id", "version_code", "line_ids"}
        if protected.intersection(vals) and self.filtered(lambda rec: rec.state in ("published", "archived")):
            raise UserError(_("已发布或已归档成本计划不可修改。"))
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda rec: rec.state not in ("draft", "adjusting")):
            raise UserError(_("只有草稿或调整中的成本计划可以删除。"))
        return super().unlink()


class ProjectCostPlanLine(models.Model):
    _name = "project.cost.plan.line"
    _description = "目标成本计划明细"
    _order = "plan_id, boq_line_id, cost_type, sequence, id"

    plan_id = fields.Many2one("project.cost.plan", string="成本计划", required=True, ondelete="cascade", index=True)
    project_id = fields.Many2one(
        "project.project", related="plan_id.project_id", store=True, readonly=True, index=True
    )
    plan_state = fields.Selection(
        related="plan_id.state", string="计划状态", store=True, readonly=True, index=True
    )
    sequence = fields.Integer("序号", default=10)
    boq_line_id = fields.Many2one("project.boq.line", string="清单项", index=True)
    analysis_id = fields.Many2one("project.boq.analysis", string="综合单价分析", index=True)
    source_resource_line_id = fields.Many2one(
        "project.boq.analysis.resource.line", string="来源资源行", readonly=True, ondelete="restrict"
    )
    source_summary_component_id = fields.Many2one(
        "project.boq.summary.component", string="来源单位工程汇总", readonly=True, ondelete="restrict"
    )
    cost_type = fields.Selection(
        [
            ("labor", "人工"),
            ("material", "材料"),
            ("machine", "机械"),
            ("overhead", "管理费"),
            ("profit", "利润"),
            ("measure", "措施费"),
            ("fee", "规费"),
            ("tax", "税金"),
            ("other", "其他"),
        ],
        string="成本口径",
        required=True,
        index=True,
    )
    line_role = fields.Selection(
        [
            ("cost", "普通成本"),
            ("deduction", "扣减项"),
            ("adjustment", "差额调整"),
        ],
        string="明细性质",
        required=True,
        default="cost",
        readonly=True,
        index=True,
        help="由来源业务事实确定。普通成本禁止负数；扣减项和差额调整保留来源的正负语义。",
    )
    name = fields.Char("成本资源/费用", required=True)
    calculation_mode = fields.Selection(
        [
            ("consumption_price", "单耗×单价"),
            ("amount", "金额调整"),
            ("rate", "费率调整"),
        ],
        string="编制方式",
        required=True,
        default="consumption_price",
    )
    source_calc_base = fields.Char("来源计算基础", readonly=True)
    budget_rate = fields.Float("预算费率(%)", readonly=True, digits=(16, 6))
    target_rate = fields.Float("目标费率(%)", digits=(16, 6))
    unit_raw = fields.Char("单位")
    boq_quantity = fields.Float("清单工程量", readonly=True)
    budget_unit_consumption = fields.Float("预算单耗", readonly=True, digits=(16, 8))
    budget_unit_price = fields.Float("预算单价", readonly=True, digits=(16, 6))
    budget_quantity = fields.Float("预算数量", compute="_compute_amounts", store=True, digits=(16, 8))
    budget_amount = fields.Monetary(
        "预算金额", compute="_compute_amounts", store=True, currency_field="currency_id"
    )
    target_unit_consumption = fields.Float("目标单耗", digits=(16, 8))
    target_unit_price = fields.Float("目标单价", digits=(16, 6))
    adjustment_ratio = fields.Float("调整比例(%)", default=100.0, digits=(16, 6))
    target_quantity = fields.Float("目标数量", compute="_compute_amounts", store=True, digits=(16, 8))
    target_amount = fields.Monetary(
        "目标金额", compute="_compute_amounts", store=True, currency_field="currency_id"
    )
    variance_amount = fields.Monetary(
        "目标差异", compute="_compute_amounts", store=True, currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        "res.currency", related="plan_id.currency_id", store=True, readonly=True
    )

    @api.depends(
        "boq_quantity",
        "budget_unit_consumption",
        "budget_unit_price",
        "target_unit_consumption",
        "target_unit_price",
        "adjustment_ratio",
        "calculation_mode",
        "budget_rate",
        "target_rate",
    )
    def _compute_amounts(self):
        for rec in self:
            rec.budget_quantity = rec.boq_quantity * rec.budget_unit_consumption
            rec.budget_amount = rec.budget_quantity * rec.budget_unit_price
            rec.target_quantity = rec.boq_quantity * rec.target_unit_consumption
            base_target = rec.target_quantity * rec.target_unit_price
            if rec.calculation_mode == "rate" and rec.budget_rate:
                rec.target_amount = rec.budget_amount * rec.target_rate / rec.budget_rate
            else:
                rec.target_amount = base_target * rec.adjustment_ratio / 100.0
            rec.variance_amount = rec.target_amount - rec.budget_amount

    @api.constrains(
        "plan_id", "boq_line_id", "analysis_id", "source_summary_component_id"
    )
    def _check_scope(self):
        for rec in self:
            if rec.boq_line_id and rec.boq_line_id.version_id != rec.plan_id.boq_version_id:
                raise ValidationError(_("成本计划明细必须引用来源清单版本中的清单项。"))
            if rec.analysis_id and rec.analysis_id.boq_line_id != rec.boq_line_id:
                raise ValidationError(_("成本计划明细的综合单价分析与清单项不一致。"))
            if (
                rec.source_summary_component_id
                and rec.source_summary_component_id.version_id != rec.plan_id.boq_version_id
            ):
                raise ValidationError(_("成本计划明细的单位工程汇总来源不属于当前清单版本。"))

    def _assert_editable(self):
        if self.filtered(lambda rec: rec.plan_id.state not in ("draft", "adjusting")):
            raise UserError(_("只有草稿或调整中的成本计划明细可以修改。"))

    def write(self, vals):
        self._assert_editable()
        return super().write(vals)

    def unlink(self):
        self._assert_editable()
        return super().unlink()

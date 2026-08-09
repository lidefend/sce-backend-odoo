# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProjectBoqAnalysis(models.Model):
    """Immutable unit-price analysis snapshot owned by one BOQ item/version."""

    _name = "project.boq.analysis"
    _description = "清单综合单价分析"
    _order = "version_id, source_sheet_index, source_sequence, id"

    name = fields.Char("分析名称", required=True)
    project_id = fields.Many2one(
        "project.project", related="boq_line_id.project_id", store=True, readonly=True, index=True
    )
    version_id = fields.Many2one(
        "project.boq.version", related="boq_line_id.version_id", store=True, readonly=True, index=True
    )
    boq_line_id = fields.Many2one(
        "project.boq.line", string="清单项", required=True, ondelete="cascade", index=True
    )
    boq_code = fields.Char(related="boq_line_id.code", string="清单编码", store=True, readonly=True)
    uom_raw = fields.Char("来源计量单位", readonly=True)
    source_quantity = fields.Float("来源工程量", readonly=True)
    source_unit_price = fields.Monetary(
        "来源综合单价", currency_field="currency_id", readonly=True
    )
    currency_id = fields.Many2one(
        "res.currency", related="boq_line_id.currency_id", store=True, readonly=True
    )
    source_sheet_index = fields.Integer("来源表序号", readonly=True)
    source_sheet_name = fields.Char("来源工作表", readonly=True)
    source_sequence = fields.Integer("来源分析序号", readonly=True)
    single_name = fields.Char("单项工程", readonly=True, index=True)
    unit_name = fields.Char("单位工程", readonly=True, index=True)
    major_name = fields.Char("专业名称", readonly=True, index=True)

    norm_line_ids = fields.One2many(
        "project.boq.analysis.norm.line", "analysis_id", string="定额组成", readonly=True
    )
    resource_line_ids = fields.One2many(
        "project.boq.analysis.resource.line", "analysis_id", string="资源消耗", readonly=True
    )
    labor_unit_amount = fields.Monetary(
        "人工费单价", compute="_compute_component_totals", store=True, currency_field="currency_id"
    )
    material_unit_amount = fields.Monetary(
        "材料费单价", compute="_compute_component_totals", store=True, currency_field="currency_id"
    )
    machine_unit_amount = fields.Monetary(
        "机械费单价", compute="_compute_component_totals", store=True, currency_field="currency_id"
    )
    overhead_unit_amount = fields.Monetary(
        "管理费单价", compute="_compute_component_totals", store=True, currency_field="currency_id"
    )
    profit_unit_amount = fields.Monetary(
        "利润单价", compute="_compute_component_totals", store=True, currency_field="currency_id"
    )
    component_unit_total = fields.Monetary(
        "组成单价合计", compute="_compute_component_totals", store=True, currency_field="currency_id"
    )
    unit_price_variance = fields.Monetary(
        "单价组成差异", compute="_compute_component_totals", store=True, currency_field="currency_id"
    )

    _sql_constraints = [
        ("boq_line_unique", "unique(boq_line_id)", "同一清单项只能有一份综合单价分析。"),
    ]

    @api.depends(
        "norm_line_ids.amount_labor",
        "norm_line_ids.amount_material",
        "norm_line_ids.amount_machine",
        "norm_line_ids.amount_overhead",
        "norm_line_ids.amount_profit",
        "source_unit_price",
    )
    def _compute_component_totals(self):
        for rec in self:
            rec.labor_unit_amount = sum(rec.norm_line_ids.mapped("amount_labor"))
            rec.material_unit_amount = sum(rec.norm_line_ids.mapped("amount_material"))
            rec.machine_unit_amount = sum(rec.norm_line_ids.mapped("amount_machine"))
            rec.overhead_unit_amount = sum(rec.norm_line_ids.mapped("amount_overhead"))
            rec.profit_unit_amount = sum(rec.norm_line_ids.mapped("amount_profit"))
            rec.component_unit_total = (
                rec.labor_unit_amount
                + rec.material_unit_amount
                + rec.machine_unit_amount
                + rec.overhead_unit_amount
                + rec.profit_unit_amount
            )
            rec.unit_price_variance = rec.source_unit_price - rec.component_unit_total

    @api.constrains("boq_line_id")
    def _check_item_line(self):
        for rec in self:
            if rec.boq_line_id.line_type != "item":
                raise ValidationError(_("综合单价分析只能关联清单明细。"))

    def _assert_draft(self):
        if self.filtered(lambda rec: rec.version_id.state != "draft"):
            raise UserError(_("已校验或已发布清单版本的综合单价分析不可修改。"))

    def write(self, vals):
        self._assert_draft()
        return super().write(vals)

    def unlink(self):
        self._assert_draft()
        return super().unlink()

    def _resolve_norm_links(self):
        """Optional sc_norm_engine extension hook; snapshots remain valid without it."""
        return True


class ProjectBoqAnalysisNormLine(models.Model):
    _name = "project.boq.analysis.norm.line"
    _description = "清单分析定额组成"
    _order = "analysis_id, sequence, id"

    analysis_id = fields.Many2one(
        "project.boq.analysis", string="综合单价分析", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer("序号", default=10)
    norm_code = fields.Char("定额编号", required=True, index=True)
    name = fields.Char("定额项目名称", required=True)
    unit_raw = fields.Char("定额单位")
    budget_consumption = fields.Float("预算消耗系数", digits=(16, 8))
    unit_labor = fields.Float("人工费单价", digits=(16, 6))
    unit_material = fields.Float("材料费单价", digits=(16, 6))
    unit_machine = fields.Float("机械费单价", digits=(16, 6))
    unit_overhead = fields.Float("管理费单价", digits=(16, 6))
    unit_profit = fields.Float("利润单价", digits=(16, 6))
    amount_labor = fields.Float("人工费合价", digits=(16, 6))
    amount_material = fields.Float("材料费合价", digits=(16, 6))
    amount_machine = fields.Float("机械费合价", digits=(16, 6))
    amount_overhead = fields.Float("管理费合价", digits=(16, 6))
    amount_profit = fields.Float("利润合价", digits=(16, 6))
    source_row = fields.Integer("来源行号", readonly=True)

    def write(self, vals):
        self.mapped("analysis_id")._assert_draft()
        return super().write(vals)

    def unlink(self):
        self.mapped("analysis_id")._assert_draft()
        return super().unlink()


class ProjectBoqAnalysisResourceLine(models.Model):
    _name = "project.boq.analysis.resource.line"
    _description = "清单分析资源消耗"
    _order = "analysis_id, sequence, id"

    analysis_id = fields.Many2one(
        "project.boq.analysis", string="综合单价分析", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer("序号", default=10)
    resource_type = fields.Selection(
        [("labor", "人工"), ("material", "材料"), ("machine", "机械"), ("other", "其他")],
        string="资源类别",
        required=True,
        default="material",
        index=True,
    )
    name = fields.Char("资源名称", required=True, index=True)
    specification = fields.Char("规格型号")
    unit_raw = fields.Char("资源单位")
    budget_consumption = fields.Float("预算单耗", digits=(16, 8))
    budget_unit_price = fields.Float("预算单价", digits=(16, 6))
    budget_unit_amount = fields.Float("预算单位合价", digits=(16, 6))
    provisional_unit_price = fields.Float("暂估单价", digits=(16, 6))
    provisional_unit_amount = fields.Float("暂估合价", digits=(16, 6))
    source_row = fields.Integer("来源行号", readonly=True)

    def write(self, vals):
        self.mapped("analysis_id")._assert_draft()
        return super().write(vals)

    def unlink(self):
        self.mapped("analysis_id")._assert_draft()
        return super().unlink()


class ProjectBoqSummaryComponent(models.Model):
    """Source-faithful unit-project summary facts; never counted as BOQ leaves."""

    _name = "project.boq.summary.component"
    _description = "单位工程造价汇总快照"
    _order = "version_id, source_sheet_index, sequence, id"

    version_id = fields.Many2one(
        "project.boq.version", string="清单版本", required=True, ondelete="cascade", index=True
    )
    project_id = fields.Many2one(
        "project.project", related="version_id.project_id", store=True, readonly=True, index=True
    )
    sequence = fields.Integer("序号")
    code = fields.Char("来源序号", index=True)
    name = fields.Char("汇总内容", required=True)
    component_type = fields.Selection(
        [
            ("direct", "分部分项及单价措施"),
            ("measure", "总价措施"),
            ("other", "其他项目"),
            ("fee", "规费"),
            ("pre_tax", "税前造价"),
            ("tax", "税金"),
            ("total", "含税总价"),
            ("detail", "汇总明细"),
        ],
        string="汇总口径",
        required=True,
        default="detail",
        index=True,
    )
    amount = fields.Monetary("来源金额", currency_field="currency_id", readonly=True)
    provisional_amount = fields.Monetary("其中暂估价", currency_field="currency_id", readonly=True)
    calc_base = fields.Char("来源计算基础", readonly=True)
    source_rate = fields.Float("来源费率(%)", readonly=True, digits=(16, 6))
    currency_id = fields.Many2one(
        "res.currency", related="version_id.currency_id", store=True, readonly=True
    )
    single_name = fields.Char("单项工程", readonly=True, index=True)
    unit_name = fields.Char("单位工程", readonly=True, index=True)
    major_name = fields.Char("专业名称", readonly=True, index=True)
    source_sheet_index = fields.Integer("来源表序号", readonly=True)
    source_sheet_name = fields.Char("来源工作表", readonly=True)
    source_row = fields.Integer("来源行号", readonly=True)

    def _assert_draft(self):
        if self.filtered(lambda rec: rec.version_id.state != "draft"):
            raise UserError(_("已校验或已发布清单版本的单位工程汇总快照不可修改。"))

    def write(self, vals):
        self._assert_draft()
        return super().write(vals)

    def unlink(self):
        self._assert_draft()
        return super().unlink()


class ProjectBoqLineAnalysisLink(models.Model):
    _inherit = "project.boq.line"

    analysis_id = fields.One2many(
        "project.boq.analysis", "boq_line_id", string="综合单价分析", readonly=True
    )


class ProjectBoqVersionAnalysisLink(models.Model):
    _inherit = "project.boq.version"

    analysis_ids = fields.One2many(
        "project.boq.analysis", "version_id", string="综合单价分析", readonly=True
    )
    analysis_count = fields.Integer(
        "综合单价分析数", compute="_compute_analysis_count", store=True
    )
    summary_component_ids = fields.One2many(
        "project.boq.summary.component", "version_id", string="单位工程汇总快照", readonly=True
    )
    summary_component_count = fields.Integer(
        "单位工程汇总行数", compute="_compute_analysis_count", store=True
    )

    @api.depends("analysis_ids", "summary_component_ids")
    def _compute_analysis_count(self):
        for rec in self:
            rec.analysis_count = len(rec.analysis_ids)
            rec.summary_component_count = len(rec.summary_component_ids)

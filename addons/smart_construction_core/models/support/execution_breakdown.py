# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_round


class ConstructionLocationBreakdown(models.Model):
    """Independent physical Location Breakdown Structure (LBS)."""

    _name = "construction.location.breakdown"
    _description = "项目空间位置结构"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "project_id, parent_path, sequence, id"

    name = fields.Char("位置名称", required=True, index=True)
    code = fields.Char("位置编码", index=True)
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        "res.company", related="project_id.company_id", store=True, readonly=True
    )
    parent_id = fields.Many2one(
        "construction.location.breakdown", string="上级位置", index=True, ondelete="cascade"
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        "construction.location.breakdown", "parent_id", string="下级位置"
    )
    location_type = fields.Selection(
        [
            ("site", "场区"),
            ("building", "单体/楼栋"),
            ("floor", "楼层"),
            ("zone", "施工区域"),
            ("room", "房间"),
            ("other", "其他位置"),
        ],
        string="位置类型",
        default="zone",
        required=True,
        index=True,
    )
    sequence = fields.Integer("序号", default=10)
    active = fields.Boolean("有效", default=True)
    scope_ids = fields.One2many(
        "construction.execution.scope", "location_id", string="执行范围"
    )

    @api.constrains("parent_id", "project_id")
    def _check_parent_project(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.project_id != rec.project_id:
                raise ValidationError(_("空间位置的父子节点必须属于同一项目。"))

    _sql_constraints = [
        (
            "project_parent_code_unique",
            "unique(project_id, parent_id, code)",
            "同一项目、同一上级位置下的位置编码不能重复。",
        ),
    ]


class ConstructionContractSection(models.Model):
    """Contract/package scope independent from both WBS and LBS."""

    _name = "construction.contract.section"
    _description = "项目标段结构"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "project_id, parent_path, sequence, id"

    name = fields.Char("标段名称", required=True, index=True)
    code = fields.Char("标段编码", required=True, index=True)
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        "res.company", related="project_id.company_id", store=True, readonly=True
    )
    parent_id = fields.Many2one(
        "construction.contract.section", string="上级标段", index=True, ondelete="cascade"
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        "construction.contract.section", "parent_id", string="下级标段"
    )
    sequence = fields.Integer("序号", default=10)
    active = fields.Boolean("有效", default=True)
    scope_ids = fields.One2many(
        "construction.execution.scope", "contract_section_id", string="执行范围"
    )

    @api.constrains("parent_id", "project_id")
    def _check_parent_project(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.project_id != rec.project_id:
                raise ValidationError(_("标段的父子节点必须属于同一项目。"))

    _sql_constraints = [
        (
            "project_code_unique",
            "unique(project_id, code)",
            "同一项目下的标段编码不能重复。",
        ),
    ]


class ConstructionExecutionScope(models.Model):
    """Management object at the intersection of WBS, LBS and contract scope."""

    _name = "construction.execution.scope"
    _description = "施工执行范围"
    _order = "project_id, wbs_id, contract_section_id, location_id, id"

    name = fields.Char("执行范围", compute="_compute_name", store=True)
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        "res.company", related="project_id.company_id", store=True, readonly=True
    )
    wbs_id = fields.Many2one(
        "construction.work.breakdown",
        string="WBS 工作包",
        required=True,
        index=True,
        ondelete="cascade",
    )
    location_id = fields.Many2one(
        "construction.location.breakdown",
        string="空间位置",
        index=True,
        ondelete="restrict",
    )
    contract_section_id = fields.Many2one(
        "construction.contract.section",
        string="标段",
        index=True,
        ondelete="restrict",
    )
    state = fields.Selection(
        [("draft", "规划中"), ("baselined", "已基线"), ("archived", "已归档")],
        string="状态",
        default="draft",
        required=True,
        index=True,
    )
    source_type = fields.Selection(
        [("boq", "清单草案"), ("manual", "人工规划")],
        string="来源",
        default="manual",
        required=True,
        index=True,
    )
    source_key = fields.Char("来源稳定键", index=True, readonly=True)
    active = fields.Boolean("有效", default=True)
    allocation_ids = fields.One2many(
        "project.boq.allocation", "execution_scope_id", string="清单分配"
    )
    boq_line_count = fields.Integer("清单项数", compute="_compute_totals", store=True)
    allocated_quantity = fields.Float("分配工程量", compute="_compute_totals", store=True)
    allocated_amount = fields.Monetary(
        "分配金额", compute="_compute_totals", store=True, currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        "res.currency", related="project_id.company_id.currency_id", store=True, readonly=True
    )

    @api.depends("wbs_id.name", "location_id.name", "contract_section_id.name")
    def _compute_name(self):
        for rec in self:
            rec.name = " / ".join(
                part
                for part in [
                    rec.contract_section_id.name,
                    rec.location_id.name,
                    rec.wbs_id.name,
                ]
                if part
            ) or _("未命名执行范围")

    @api.depends(
        "allocation_ids.boq_line_id",
        "allocation_ids.allocated_quantity",
        "allocation_ids.allocated_amount",
    )
    def _compute_totals(self):
        for rec in self:
            allocations = rec.allocation_ids.filtered("active")
            rec.boq_line_count = len(allocations.mapped("boq_line_id"))
            rec.allocated_quantity = sum(allocations.mapped("allocated_quantity"))
            rec.allocated_amount = sum(allocations.mapped("allocated_amount"))

    @api.constrains("project_id", "wbs_id", "location_id", "contract_section_id")
    def _check_dimensions(self):
        for rec in self:
            dimensions = rec.wbs_id.project_id | rec.location_id.project_id | rec.contract_section_id.project_id
            if dimensions and any(project != rec.project_id for project in dimensions):
                raise ValidationError(_("执行范围的 WBS、空间位置和标段必须属于同一项目。"))
            duplicate = self.search_count(
                [
                    ("id", "!=", rec.id),
                    ("project_id", "=", rec.project_id.id),
                    ("wbs_id", "=", rec.wbs_id.id),
                    ("location_id", "=", rec.location_id.id or False),
                    ("contract_section_id", "=", rec.contract_section_id.id or False),
                    ("active", "=", True),
                ]
            )
            if duplicate:
                raise ValidationError(_("相同 WBS、空间位置和标段只能形成一个有效执行范围。"))

    _sql_constraints = [
        (
            "project_source_key_unique",
            "unique(project_id, source_key)",
            "同一项目下的清单草案执行范围稳定键不能重复。",
        ),
    ]

    def action_baseline(self):
        projects = self.mapped("project_id")
        for project in projects:
            versions = self.env["project.boq.version"].search(
                [("project_id", "=", project.id), ("state", "=", "published")],
                order="published_at desc, id desc",
            )
            version = versions.filtered(lambda rec: rec.source_type == "contract")[:1] or versions[:1]
            lines = version.line_ids.filtered(lambda line: line.line_type == "item")
            invalid = lines.filtered(lambda line: not line.allocation_balanced)
            if invalid:
                raise UserError(_("仍有 %s 条清单未完成数量和金额守恒分配，不能建立执行基线。") % len(invalid))
            project_scopes = self.search([("project_id", "=", project.id), ("state", "=", "draft")])
            project_scopes.write({"state": "baselined"})
        return True


class ProjectBoqAllocation(models.Model):
    """Auditable quantity/amount allocation from BOQ fact to execution scope."""

    _name = "project.boq.allocation"
    _description = "清单执行范围分配"
    _order = "boq_line_id, execution_scope_id, id"

    boq_line_id = fields.Many2one(
        "project.boq.line", string="清单项", required=True, index=True, ondelete="cascade"
    )
    execution_scope_id = fields.Many2one(
        "construction.execution.scope",
        string="执行范围",
        required=True,
        index=True,
        ondelete="cascade",
    )
    project_id = fields.Many2one(
        "project.project", related="boq_line_id.project_id", store=True, readonly=True, index=True
    )
    version_id = fields.Many2one(
        "project.boq.version", related="boq_line_id.version_id", store=True, readonly=True, index=True
    )
    uom_id = fields.Many2one(
        "uom.uom", related="boq_line_id.uom_id", store=True, readonly=True
    )
    allocated_quantity = fields.Float("分配工程量", required=True, default=0.0)
    allocated_amount = fields.Monetary(
        "分配金额", required=True, default=0.0, currency_field="currency_id"
    )
    allocation_basis = fields.Selection(
        [
            ("quantity", "按工程量"),
            ("amount", "按金额"),
            ("ratio", "按比例"),
        ],
        string="分配方式",
        default="ratio",
        required=True,
        help="选择本次录入依据；系统按来源清单同步换算另外两项。",
    )
    allocation_ratio = fields.Float("分配比例(%)", default=0.0, required=True)
    currency_id = fields.Many2one(
        "res.currency", related="boq_line_id.currency_id", store=True, readonly=True
    )
    source_type = fields.Selection(
        [("generated", "自动草案"), ("manual", "人工调整")],
        string="来源",
        default="manual",
        required=True,
    )
    active = fields.Boolean("当前有效", default=True, index=True)

    def _values_from_basis(self, basis, quantity, amount, ratio):
        self.ensure_one()
        source_quantity = self.boq_line_id.quantity or 0.0
        source_amount = self.boq_line_id.amount_leaf or 0.0
        qty_rounding = self.uom_id.rounding or 0.0001
        amount_rounding = self.currency_id.rounding or 0.01
        if basis == "quantity":
            ratio = quantity / source_quantity * 100.0 if source_quantity else 0.0
            amount = float_round(source_amount * ratio / 100.0, precision_rounding=amount_rounding)
        elif basis == "amount":
            ratio = amount / source_amount * 100.0 if source_amount else 0.0
            quantity = float_round(source_quantity * ratio / 100.0, precision_rounding=qty_rounding)
        else:
            quantity = float_round(source_quantity * ratio / 100.0, precision_rounding=qty_rounding)
            amount = float_round(source_amount * ratio / 100.0, precision_rounding=amount_rounding)
        return quantity, amount, ratio

    @api.onchange("allocation_basis", "allocated_quantity", "allocated_amount", "allocation_ratio")
    def _onchange_allocation_basis_values(self):
        for rec in self.filtered("boq_line_id"):
            quantity, amount, ratio = rec._values_from_basis(
                rec.allocation_basis,
                rec.allocated_quantity,
                rec.allocated_amount,
                rec.allocation_ratio,
            )
            rec.allocated_quantity = quantity
            rec.allocated_amount = amount
            rec.allocation_ratio = ratio

    @api.constrains("boq_line_id", "execution_scope_id")
    def _check_scope_project(self):
        for rec in self:
            if rec.boq_line_id.project_id != rec.execution_scope_id.project_id:
                raise ValidationError(_("清单项与执行范围必须属于同一项目。"))

    @api.constrains("allocated_quantity", "allocated_amount", "allocation_ratio", "boq_line_id", "active")
    def _check_allocation_bounds(self):
        for rec in self:
            if rec.allocated_quantity < 0 or rec.allocated_amount < 0 or rec.allocation_ratio < 0:
                raise ValidationError(_("分配工程量、金额和比例不能为负数。"))
            if float_compare(rec.allocation_ratio, 100.0, precision_digits=6) > 0:
                raise ValidationError(_("单条分配比例不能超过 100%。"))
            siblings = self.search([("boq_line_id", "=", rec.boq_line_id.id), ("active", "=", True)])
            qty_rounding = rec.uom_id.rounding or 0.0001
            currency_rounding = rec.currency_id.rounding or 0.01
            if float_compare(sum(siblings.mapped("allocated_quantity")), rec.boq_line_id.quantity, precision_rounding=qty_rounding) > 0:
                raise ValidationError(_("清单项的累计分配工程量不能超过来源工程量。"))
            if float_compare(sum(siblings.mapped("allocated_amount")), rec.boq_line_id.amount_leaf, precision_rounding=currency_rounding) > 0:
                raise ValidationError(_("清单项的累计分配金额不能超过来源合价。"))

    _sql_constraints = [
        (
            "boq_scope_unique",
            "unique(boq_line_id, execution_scope_id)",
            "同一清单项在同一执行范围中只能有一条分配记录。",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec, vals in zip(records, vals_list):
            # 导入/自动草案可同时给出数量和金额；此时只补齐审计比例，不改来源精度。
            if "allocated_quantity" in vals and "allocated_amount" in vals and "allocation_ratio" not in vals:
                source_amount = rec.boq_line_id.amount_leaf or 0.0
                ratio = rec.allocated_amount / source_amount * 100.0 if source_amount else 0.0
                super(ProjectBoqAllocation, rec).write({"allocation_ratio": ratio})
            elif {"allocated_quantity", "allocated_amount", "allocation_ratio"}.intersection(vals):
                quantity, amount, ratio = rec._values_from_basis(
                    rec.allocation_basis,
                    rec.allocated_quantity,
                    rec.allocated_amount,
                    rec.allocation_ratio,
                )
                super(ProjectBoqAllocation, rec).write(
                    {"allocated_quantity": quantity, "allocated_amount": amount, "allocation_ratio": ratio}
                )
        return records

    def write(self, vals):
        if self.filtered(lambda rec: rec.execution_scope_id.state == "baselined"):
            raise UserError(_("已建立执行基线的清单分配不可修改。"))
        values = dict(vals)
        if {"allocated_quantity", "allocated_amount", "allocation_ratio", "execution_scope_id"}.intersection(values):
            values.setdefault("source_type", "manual")
        result = super().write(values)
        changed_inputs = {"allocated_quantity", "allocated_amount", "allocation_ratio", "allocation_basis"}.intersection(vals)
        if changed_inputs:
            for rec in self:
                basis_field = {
                    "quantity": "allocated_quantity",
                    "amount": "allocated_amount",
                    "ratio": "allocation_ratio",
                }[rec.allocation_basis]
                if basis_field not in vals and "allocation_basis" not in vals:
                    continue
                quantity, amount, ratio = rec._values_from_basis(
                    rec.allocation_basis,
                    rec.allocated_quantity,
                    rec.allocated_amount,
                    rec.allocation_ratio,
                )
                super(ProjectBoqAllocation, rec).write(
                    {"allocated_quantity": quantity, "allocated_amount": amount, "allocation_ratio": ratio}
                )
        return result

    def unlink(self):
        if self.filtered(lambda rec: rec.execution_scope_id.state == "baselined"):
            raise UserError(_("已建立执行基线的清单分配不可删除。"))
        return super().unlink()

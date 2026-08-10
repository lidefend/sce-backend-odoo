from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ScNormSpecialty(models.Model):
    _name = "sc.norm.specialty"
    _description = "定额专业"
    _order = "catalog_id, sequence, code"

    catalog_id = fields.Many2one(
        "sc.norm.catalog",
        string="所属定额库",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: self.env.ref(
            "sc_norm_engine.catalog_sc_2015", raise_if_not_found=False
        ),
    )

    code = fields.Char("专业代码", required=True, index=True)
    name = fields.Char("专业名称", required=True)
    sheet_name = fields.Char("来源工作表")
    sequence = fields.Integer("排序", default=10)
    active = fields.Boolean("启用", default=True)

    chapter_ids = fields.One2many("sc.norm.chapter", "specialty_id", string="章节")
    item_ids = fields.One2many("sc.norm.item", "specialty_id", string="定额子目")

    _sql_constraints = [
        (
            "catalog_code_uniq",
            "unique(catalog_id, code)",
            "同一定额库内专业代码必须唯一！",
        ),
    ]


class ScNormChapter(models.Model):
    _name = "sc.norm.chapter"
    _description = "定额章节"
    _parent_store = True
    _parent_name = "parent_id"
    _order = "specialty_id, sequence, code"

    code = fields.Char("章节代码", required=True, index=True)
    name = fields.Char("章节名称", required=True)
    specialty_id = fields.Many2one(
        "sc.norm.specialty",
        string="所属专业",
        required=True,
        ondelete="cascade",
    )
    parent_id = fields.Many2one(
        "sc.norm.chapter",
        string="上级章节",
        index=True,
        ondelete="cascade",
        domain="[('specialty_id', '=', specialty_id)]",
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many("sc.norm.chapter", "parent_id", string="下级章节")
    level = fields.Integer("层级", default=1, required=True, index=True)
    sequence = fields.Integer("排序", default=10)

    norm_code_start = fields.Char("开始定额号", index=True)
    norm_code_end = fields.Char("结束定额号")
    source_row = fields.Integer("目录来源行号")

    item_ids = fields.One2many("sc.norm.item", "chapter_id", string="定额子目")

    _sql_constraints = [
        (
            "chapter_uniq",
            "unique(specialty_id, code)",
            "同一专业下章节代码不能重复！",
        ),
    ]

    @api.constrains("specialty_id", "parent_id")
    def _check_parent_specialty_consistency(self):
        for record in self:
            if not record._check_recursion():
                raise ValidationError("章节层级不能形成循环。")
            if record.parent_id and record.parent_id.specialty_id != record.specialty_id:
                raise ValidationError("上级章节必须归属于同一专业。")


class ScNormItem(models.Model):
    _name = "sc.norm.item"
    _description = "定额子目"
    _order = "specialty_id, code"

    code = fields.Char("定额编号", required=True, index=True)
    name = fields.Char("项目名称", required=True, index=True)

    catalog_id = fields.Many2one(
        "sc.norm.catalog",
        string="所属定额库",
        related="specialty_id.catalog_id",
        store=True,
        readonly=True,
        index=True,
    )

    specialty_id = fields.Many2one(
        "sc.norm.specialty",
        string="所属专业",
        required=True,
        ondelete="cascade",
    )
    chapter_id = fields.Many2one(
        "sc.norm.chapter",
        string="所属章节",
        ondelete="set null",
    )

    unit_raw = fields.Char("计量单位")
    uom_id = fields.Many2one("uom.uom", string="标准单位")

    price_total = fields.Float("综合单价")
    cost_direct = fields.Float("直接费")
    cost_labor = fields.Float("人工费")
    cost_material = fields.Float("材料费")
    cost_machine = fields.Float("机械费")
    fee_rate = fields.Float("费率", help="机械费率或配合比费率等")
    cost_misc = fields.Float("综合费")

    direct_share = fields.Float("直接费占比", compute="_compute_cost_shares", store=True, digits=(16, 6))
    labor_share = fields.Float("人工费占比", compute="_compute_cost_shares", store=True, digits=(16, 6))
    material_share = fields.Float("材料费占比", compute="_compute_cost_shares", store=True, digits=(16, 6))
    machine_share = fields.Float("机械费占比", compute="_compute_cost_shares", store=True, digits=(16, 6))
    misc_share = fields.Float("综合费占比", compute="_compute_cost_shares", store=True, digits=(16, 6))

    work_desc = fields.Text("工作内容")
    source_sheet = fields.Char("来源工作表", index=True)
    line_no = fields.Integer("来源行号")

    _sql_constraints = [
        (
            "item_code_uniq",
            "unique(specialty_id, code)",
            "同一专业下定额编号不能重复！",
        ),
    ]

    @api.constrains("specialty_id", "chapter_id")
    def _check_chapter_specialty_consistency(self):
        for record in self:
            if (
                record.chapter_id
                and record.specialty_id
                and record.chapter_id.specialty_id != record.specialty_id
            ):
                raise ValidationError("定额项所属章节必须归属于同一专业。")

    @api.onchange("unit_raw")
    def _onchange_unit_raw(self):
        """单位别名映射可后续实现。"""
        return

    @api.depends(
        "price_total",
        "cost_direct",
        "cost_labor",
        "cost_material",
        "cost_machine",
        "cost_misc",
    )
    def _compute_cost_shares(self):
        for record in self:
            denominator = record.price_total or 0.0
            record.direct_share = record.cost_direct / denominator if denominator else 0.0
            record.labor_share = record.cost_labor / denominator if denominator else 0.0
            record.material_share = record.cost_material / denominator if denominator else 0.0
            record.machine_share = record.cost_machine / denominator if denominator else 0.0
            record.misc_share = record.cost_misc / denominator if denominator else 0.0

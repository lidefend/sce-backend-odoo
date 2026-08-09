from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ScNormRegion(models.Model):
    _name = "sc.norm.region"
    _description = "定额适用地区"
    _parent_store = True
    _parent_name = "parent_id"
    _order = "sequence, code"

    code = fields.Char("地区代码", required=True, index=True)
    name = fields.Char("地区名称", required=True, index=True)
    country_id = fields.Many2one("res.country", string="国家/地区")
    parent_id = fields.Many2one(
        "sc.norm.region", string="上级地区", index=True, ondelete="restrict"
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many("sc.norm.region", "parent_id", string="下级地区")
    sequence = fields.Integer("排序", default=10)
    active = fields.Boolean("启用", default=True)

    _sql_constraints = [
        ("region_code_uniq", "unique(code)", "地区代码必须唯一！"),
    ]

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError("地区层级不能形成循环。")


class ScNormCatalog(models.Model):
    _name = "sc.norm.catalog"
    _description = "定额库版本"
    _order = "region_id, edition_year desc, version desc, code"

    code = fields.Char("定额库编码", required=True, index=True)
    name = fields.Char("定额库名称", required=True, index=True)
    region_id = fields.Many2one(
        "sc.norm.region", string="适用地区", required=True, ondelete="restrict", index=True
    )
    edition_year = fields.Char("发布年份", required=True, index=True)
    version = fields.Char("版本号", required=True, default="1.0", index=True)
    catalog_type = fields.Selection(
        [
            ("budget", "预算定额"),
            ("consumption", "消耗量定额"),
            ("valuation", "计价定额"),
            ("supplement", "补充定额"),
            ("enterprise", "企业定额"),
            ("other", "其他"),
        ],
        string="定额类型",
        required=True,
        default="budget",
        index=True,
    )
    state = fields.Selection(
        [("draft", "草稿"), ("active", "启用"), ("archived", "归档")],
        string="状态",
        required=True,
        default="draft",
        index=True,
    )
    effective_date = fields.Date("生效日期")
    expiry_date = fields.Date("失效日期")
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        required=True,
        default=lambda self: self.env.ref("base.CNY", raise_if_not_found=False)
        or self.env.company.currency_id,
    )
    note = fields.Text("说明")
    specialty_ids = fields.One2many("sc.norm.specialty", "catalog_id", string="专业")
    specialty_count = fields.Integer("专业数", compute="_compute_data_counts")
    chapter_count = fields.Integer("章节数", compute="_compute_data_counts")
    item_count = fields.Integer("定额项数", compute="_compute_data_counts")

    _sql_constraints = [
        ("catalog_code_uniq", "unique(code)", "定额库编码必须唯一！"),
        (
            "catalog_region_edition_version_uniq",
            "unique(region_id, edition_year, version, catalog_type)",
            "同一地区、年份、版本和类型的定额库不能重复！",
        ),
    ]

    @api.constrains("effective_date", "expiry_date")
    def _check_effective_dates(self):
        for record in self:
            if record.effective_date and record.expiry_date and record.expiry_date < record.effective_date:
                raise ValidationError("失效日期不能早于生效日期。")

    def _compute_data_counts(self):
        Specialty = self.env["sc.norm.specialty"]
        Chapter = self.env["sc.norm.chapter"]
        Item = self.env["sc.norm.item"]
        for record in self:
            specialties = Specialty.with_context(active_test=False).search(
                [("catalog_id", "=", record.id)]
            )
            record.specialty_count = len(specialties)
            record.chapter_count = Chapter.search_count(
                [("specialty_id", "in", specialties.ids)]
            )
            record.item_count = Item.search_count([("catalog_id", "=", record.id)])

    @api.onchange("region_id")
    def _onchange_region_currency(self):
        for record in self:
            country_currency = record.region_id.country_id.currency_id
            if country_currency:
                record.currency_id = country_currency

    def action_activate(self):
        self.write({"state": "active"})
        return True

    def action_archive(self):
        self.write({"state": "archived"})
        return True

    def action_reset_draft(self):
        self.write({"state": "draft"})
        return True

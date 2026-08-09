# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

from ..support.state_machine import ScStateMachine
from ..support.state_guard import raise_guard


class ProjectBoqVersion(models.Model):
    """Auditable BOQ snapshot owned by one project and one business source."""

    _name = "project.boq.version"
    _description = "工程量清单版本"
    _order = "project_id, source_type, create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("版本名称", required=True, tracking=True)
    code = fields.Char("版本号", required=True, index=True, tracking=True)
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, index=True, ondelete="cascade", tracking=True
    )
    source_type = fields.Selection(
        ScStateMachine.BOQ_SOURCE_TYPES,
        string="清单来源",
        required=True,
        default="contract",
        index=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("validated", "已校验"),
            ("published", "已发布"),
            ("superseded", "已被替代"),
            ("cancelled", "已取消"),
        ],
        string="状态",
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    previous_version_id = fields.Many2one(
        "project.boq.version", string="上一版本", readonly=True, ondelete="set null"
    )
    replaced_by_id = fields.Many2one(
        "project.boq.version", string="替代版本", readonly=True, ondelete="set null"
    )
    line_ids = fields.One2many("project.boq.line", "version_id", string="清单明细", readonly=True)
    batch_ids = fields.One2many("project.boq.import.batch", "version_id", string="导入批次", readonly=True)
    line_count = fields.Integer("清单行数", compute="_compute_totals", store=True)
    item_count = fields.Integer("清单项数", compute="_compute_totals", store=True)
    total_amount = fields.Monetary(
        "清单合价", compute="_compute_totals", store=True, currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        "res.currency", related="project_id.company_id.currency_id", store=True, readonly=True
    )
    published_at = fields.Datetime("发布时间", readonly=True)
    published_by = fields.Many2one("res.users", string="发布人", readonly=True)
    note = fields.Text("版本说明")

    _sql_constraints = [
        (
            "project_boq_version_scope_uniq",
            "unique(project_id, source_type, code)",
            "同一项目、清单来源下的版本号必须唯一。",
        ),
    ]

    @api.depends("line_ids.amount_leaf", "line_ids.line_type")
    def _compute_totals(self):
        for version in self:
            version.line_count = len(version.line_ids)
            version.item_count = len(version.line_ids.filtered(lambda line: line.line_type == "item"))
            version.total_amount = sum(version.line_ids.mapped("amount_leaf"))

    def action_validate(self):
        for version in self:
            if version.state != "draft":
                raise UserError(_("只有草稿清单版本可以校验。"))
            if not version.line_ids:
                raise UserError(_("清单版本没有明细，不能通过校验。"))
            version.with_context(allow_boq_version_transition=True).write({"state": "validated"})
        return True

    def action_publish(self):
        """Publish atomically; only one current version exists per project/source."""
        for version in self.sorted("id"):
            if version.state not in ("validated", "superseded"):
                raise UserError(_("只有已校验或已被替代的清单版本可以发布。"))
            if not version.line_ids:
                raise UserError(_("清单版本没有明细，不能发布。"))
            self.env.cr.execute("SELECT id FROM project_project WHERE id = %s FOR UPDATE", [version.project_id.id])
            current = self.search(
                [
                    ("project_id", "=", version.project_id.id),
                    ("source_type", "=", version.source_type),
                    ("state", "=", "published"),
                    ("id", "!=", version.id),
                ]
            )
            previous = current[:1]
            if current:
                current.with_context(allow_boq_version_transition=True).write(
                    {"state": "superseded", "replaced_by_id": version.id}
                )
            version.with_context(allow_boq_version_transition=True).write(
                {
                    "state": "published",
                    "previous_version_id": previous.id or version.previous_version_id.id,
                    "replaced_by_id": False,
                    "published_at": fields.Datetime.now(),
                    "published_by": self.env.user.id,
                }
            )
            version.batch_ids.filtered(lambda batch: batch.state == "imported").write({"state": "published"})
        return True

    def action_generate_wbs_draft(self):
        """Explicitly derive an editable management draft from this BOQ snapshot."""
        self.ensure_one()
        if self.state != "published":
            raise UserError(_("只有当前已发布的清单版本可以形成 WBS 草案。"))
        return self.project_id.with_context(boq_version_id=self.id).action_generate_wbs_from_boq()

    def action_restore(self):
        self.ensure_one()
        if self.state != "superseded":
            raise UserError(_("只有已被替代的清单版本可以恢复。"))
        return self.action_publish()

    def write(self, vals):
        protected = {"name", "code", "project_id", "source_type", "note"}
        if protected.intersection(vals) and self.filtered(
            lambda version: version.state in ("published", "superseded")
        ):
            raise UserError(_("已发布清单版本的业务属性不可修改，请创建新版本。"))
        if "state" in vals and not self.env.context.get("allow_boq_version_transition"):
            illegal = self.filtered(lambda version: version.state in ("published", "superseded"))
            if illegal:
                raise UserError(_("已发布的清单版本只能通过发布或恢复动作转换状态。"))
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda version: version.state in ("published", "superseded")):
            raise UserError(_("已发布或已被替代的清单版本属于审计事实，不能删除。"))
        return super().unlink()


class ProjectBoqImportBatch(models.Model):
    """Persistent evidence for one parsed and committed import file."""

    _name = "project.boq.import.batch"
    _description = "工程量清单导入批次"
    _order = "create_date desc, id desc"

    name = fields.Char("批次", required=True, default=lambda self: _("清单导入"))
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, ondelete="cascade")
    version_id = fields.Many2one(
        "project.boq.version", string="目标版本", required=True, index=True, ondelete="restrict"
    )
    source_type = fields.Selection(related="version_id.source_type", store=True, readonly=True)
    state = fields.Selection(
        [
            ("preflight", "已预检"),
            ("imported", "已导入"),
            ("published", "已发布"),
            ("failed", "失败"),
        ],
        string="状态",
        required=True,
        default="preflight",
        index=True,
    )
    filename = fields.Char("文件名", required=True)
    file_digest = fields.Char("文件摘要", required=True, index=True)
    parser_schema = fields.Char("解析契约", required=True, default="sc.boq.import.v1")
    row_count = fields.Integer("解析行数")
    item_count = fields.Integer("清单项数")
    skipped_count = fields.Integer("跳过行数")
    warning_count = fields.Integer("警告数")
    preview_payload = fields.Json("预检摘要", readonly=True)
    log = fields.Text("导入日志", readonly=True)
    imported_at = fields.Datetime("导入时间", readonly=True)
    imported_by = fields.Many2one("res.users", string="导入人", readonly=True)
    line_ids = fields.One2many("project.boq.line", "import_batch_id", string="导入明细", readonly=True)

    @api.constrains("project_id", "version_id")
    def _check_project_scope(self):
        for batch in self:
            if batch.version_id and batch.project_id != batch.version_id.project_id:
                raise ValidationError(_("导入批次与清单版本必须属于同一项目。"))

    def unlink(self):
        if self.filtered(lambda batch: batch.state in ("imported", "published")):
            raise UserError(_("已导入批次属于审计证据，不能删除。"))
        return super().unlink()


class ProjectBoqLine(models.Model):
    """工程量清单（平铺）
    同一项目下允许重复清单编码，用编码 + 项目特征/备注等区分不同位置/部位。
    """

    _name = "project.boq.line"
    _description = "工程量清单"
    _order = "project_id, section_type, parent_path, sequence, id"
    _parent_store = True
    _parent_name = "parent_id"

    allocation_ids = fields.One2many(
        "project.boq.allocation", "boq_line_id", string="执行范围分配", readonly=True
    )
    allocated_quantity = fields.Float("已分配工程量", compute="_compute_allocation_totals", store=True)
    allocated_amount = fields.Monetary(
        "已分配金额", compute="_compute_allocation_totals", store=True, currency_field="currency_id"
    )
    unallocated_quantity = fields.Float("未分配工程量", compute="_compute_allocation_totals", store=True)
    unallocated_amount = fields.Monetary(
        "未分配金额", compute="_compute_allocation_totals", store=True, currency_field="currency_id"
    )
    allocation_balanced = fields.Boolean("分配守恒", compute="_compute_allocation_totals", store=True)

    project_id = fields.Many2one(
        "project.project",
        string="项目",
        required=True,
        index=True,
        ondelete="cascade",
    )

    # 树状层级结构（章/节/子目/清单项等）
    parent_id = fields.Many2one(
        "project.boq.line",
        string="上级清单",
        index=True,
        ondelete="cascade",
    )
    child_ids = fields.One2many(
        "project.boq.line",
        "parent_id",
        string="下级清单",
    )
    parent_path = fields.Char(index=True, unaccent=False)
    level = fields.Integer(
        "层级",
        compute="_compute_level",
        store=True,
        help="1=顶级（专业清单），2=分部清单，3=清单项，以此类推。",
    )
    is_group = fields.Boolean(
        "章节/标题行",
        help="用于标识本行是否为章节/汇总标题行，由导入引擎和层级算法统一维护。",
        index=True,
    )
    hierarchy_code = fields.Char(
        "层级编号",
        help="与清单表中章节编号对应，如 1, 1.1, 1.1.2；用于保存导入解析结果。",
        index=True,
    )
    display_order = fields.Char(
        "展示顺序",
        help="用于树/列表视图的稳定排序，例如 001.001.005；由导入引擎维护。",
        index=True,
    )

    sequence = fields.Integer("序号", default=10)
    section_type = fields.Selection(
        [
            ("building", "建筑"),
            ("installation", "安装/机电"),
            ("decoration", "装饰"),
            ("landscape", "景观"),
            ("municipal", "市政"),
            ("other", "其他"),
        ],
        string="工程类别",
        help="按专业大类归类清单，用于统计。",
    )
    code = fields.Char("清单编码", required=True, index=True)
    source_code = fields.Char(
        "源文件编码",
        readonly=True,
        help="源文件单元格中的原始项目编码；结构标题和汇总行为空。",
    )
    name = fields.Char("清单名称", required=True)
    spec = fields.Char("规格/项目特征")
    division_name = fields.Char("分部工程名称", index=True)
    single_name = fields.Char(
        "单项工程",
        help="工程下的单项工程名称；来源于清单表头或导入模板。",
        index=True,
    )
    unit_name = fields.Char(
        "单位工程",
        help="单项工程下的单位工程/单体/标段名称；来源于清单表头或导入模板。",
        index=True,
    )
    major_name = fields.Char(
        "专业名称",
        help="如：建筑与装饰工程、消防站给排水工程等；来源于清单表头【】内的内容。",
        index=True,
    )
    uom_id = fields.Many2one("uom.uom", string="单位", required=True)
    quantity = fields.Float("工程量", default=0.0, group_operator="sum")
    qty_planned = fields.Float(
        "计划工程量",
        related="quantity",
        store=True,
        readonly=True,
        help="P0 口径：清单计划量（与工程量字段保持一致）。",
    )
    qty_done = fields.Float(
        "累计完成量",
        default=0.0,
        help="P0 口径：执行完成量，默认不允许超出计划量。",
    )
    qty_remain = fields.Float(
        "剩余工程量",
        compute="_compute_qty_remain",
        store=True,
        readonly=True,
    )
    price = fields.Monetary("单价", currency_field="currency_id", group_operator=False)
    imported_amount = fields.Monetary(
        "来源合价",
        currency_field="currency_id",
        group_operator=False,
        readonly=True,
        help="导入文件明确给出的权威合价；缺失时才按工程量乘单价计算。",
    )
    has_imported_amount = fields.Boolean("存在来源合价", readonly=True)
    source_row_type = fields.Selection(
        [
            ("item", "清单明细"),
            ("heading", "源文件标题"),
            ("subtotal", "页内小计"),
            ("total", "合计"),
        ],
        string="源文件行类型",
        default="item",
        required=True,
        index=True,
        readonly=True,
    )
    calculated_amount = fields.Monetary(
        "系统计算合价", currency_field="currency_id", readonly=True, group_operator=False
    )
    amount_variance = fields.Monetary(
        "源值差异",
        currency_field="currency_id",
        compute="_compute_amount_variance",
        store=True,
        group_operator=False,
    )
    calculation_scope_item_count = fields.Integer("计算范围清单项数", readonly=True)
    calculation_scope_start_sequence = fields.Integer("计算范围起始序号", readonly=True)
    calculation_scope_end_sequence = fields.Integer("计算范围结束序号", readonly=True)
    amount = fields.Monetary(
        "合价",
        currency_field="currency_id",
        compute="_compute_amount",
        store=True,
        recursive=True,
        group_operator=False,
        help="树形展示口径：清单项=工程量*单价，父项=子项合价之和；不参与统计汇总。",
    )
    amount_leaf = fields.Monetary(
        "合价(叶子)",
        currency_field="currency_id",
        compute="_compute_amount_leaf",
        store=True,
        group_operator="sum",
        help="仅清单项计入汇总，章节/父项不计入，避免分组/透视重复统计。",
    )

    @api.depends("has_imported_amount", "imported_amount", "calculated_amount")
    def _compute_amount_variance(self):
        for rec in self:
            rec.amount_variance = (
                (rec.imported_amount or 0.0) - (rec.calculated_amount or 0.0)
                if rec.has_imported_amount
                else 0.0
            )
    # 单价分析表基价（人工/机械），导入时回写，便于对账和分析
    base_labor_unit = fields.Float("人工基价")
    base_machine_unit = fields.Float("机械基价")
    has_warning = fields.Boolean("有警告", readonly=True)
    warning_message = fields.Char("警告信息", readonly=True)

    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="project_id.company_id.currency_id",
        store=True,
        readonly=True,
    )

    cost_item_id = fields.Many2one(
        "sc.dictionary",
        string="成本项",
        domain=[("type", "=", "cost_item")],
    )
    task_id = fields.Many2one(
        "project.task",
        string="关联任务",
        ondelete="set null",
        index=True,
    )
    work_id = fields.Many2one(
        "construction.work.breakdown",
        string="施工工序结构",
        ondelete="set null",
        index=True,
    )

    remark = fields.Char("备注")
    is_provisional = fields.Boolean("暂列/暂估")
    category = fields.Selection(
        [
            ("subitem", "分部分项"),
            ("measure", "措施项目"),
            ("other", "其他项目"),
        ],
        string="项目类别",
        index=True,
    )
    boq_category = fields.Selection(
        [
            ("boq", "分部分项清单"),
            ("unit_measure", "单价措施清单"),
            ("total_measure", "总价措施清单"),
            ("fee", "规费"),
            ("tax", "税金"),
            ("other", "其他费用"),
        ],
        string="清单类别",
        default="boq",
        index=True,
        help="用于区分分部分项/措施/规费/税金，避免不同类别清单在汇总时混淆。",
    )
    fee_type_id = fields.Many2one(
        "sc.dictionary",
        string="规费类别",
        domain=[("type", "=", "fee_type")],
    )
    tax_type_id = fields.Many2one(
        "sc.dictionary",
        string="税种",
        domain=[("type", "=", "tax_type")],
    )
    # 编码分段（按清单规范 12 位编码拆分）
    code_cat = fields.Char("工程分类码", compute="_compute_code_segments", store=True, index=True)
    code_prof = fields.Char("专业工程码", compute="_compute_code_segments", store=True, index=True)
    code_division = fields.Char("分部工程码", compute="_compute_code_segments", store=True, index=True)
    code_subdivision = fields.Char("分项工程码", compute="_compute_code_segments", store=True, index=True)
    code_item = fields.Char("清单项目码", compute="_compute_code_segments", store=True, index=True)

    version_id = fields.Many2one(
        "project.boq.version", string="清单版本", required=True, index=True, ondelete="restrict"
    )
    source_type = fields.Selection(
        related="version_id.source_type", string="清单来源", store=True, readonly=True, index=True
    )
    import_batch_id = fields.Many2one(
        "project.boq.import.batch", string="导入批次", index=True, ondelete="restrict", readonly=True
    )
    sheet_index = fields.Integer("来源表序号")
    sheet_name = fields.Char("来源表名称")

    @api.depends(
        "line_type", "quantity", "price", "imported_amount", "has_imported_amount",
        "child_ids.amount", "child_ids.amount_leaf"
    )
    def _compute_amount(self):
        for rec in self:
            qty = rec.quantity or 0.0
            price = rec.price or 0.0
            # 有子节点时优先使用子节点合计；否则回退到自身数量*单价
            if rec.line_type != "item" and rec.child_ids:
                rec.amount = sum(rec.child_ids.mapped("amount"))
            elif rec.has_imported_amount:
                rec.amount = rec.imported_amount
            else:
                rec.amount = qty * price

    @api.depends("line_type", "quantity", "price", "imported_amount", "has_imported_amount")
    def _compute_amount_leaf(self):
        for rec in self:
            if rec.line_type == "item":
                rec.amount_leaf = (
                    rec.imported_amount
                    if rec.has_imported_amount
                    else (rec.quantity or 0.0) * (rec.price or 0.0)
                )

    @api.depends("line_type", "quantity", "qty_done")
    def _compute_qty_remain(self):
        for rec in self:
            if rec.line_type and rec.line_type != "item":
                rec.qty_remain = 0.0
                continue
            rec.qty_remain = (rec.quantity or 0.0) - (rec.qty_done or 0.0)

    @api.depends(
        "quantity",
        "amount_leaf",
        "allocation_ids.active",
        "allocation_ids.allocated_quantity",
        "allocation_ids.allocated_amount",
    )
    def _compute_allocation_totals(self):
        for rec in self:
            allocations = rec.allocation_ids.filtered("active")
            allocated_qty = sum(allocations.mapped("allocated_quantity"))
            allocated_amount = sum(allocations.mapped("allocated_amount"))
            rec.allocated_quantity = allocated_qty
            rec.allocated_amount = allocated_amount
            rec.unallocated_quantity = (rec.quantity or 0.0) - allocated_qty
            rec.unallocated_amount = (rec.amount_leaf or 0.0) - allocated_amount
            qty_rounding = rec.uom_id.rounding if rec.uom_id else 0.0001
            amount_rounding = rec.currency_id.rounding if rec.currency_id else 0.01
            rec.allocation_balanced = bool(allocations) and (
                float_compare(allocated_qty, rec.quantity or 0.0, precision_rounding=qty_rounding) == 0
                and float_compare(
                    allocated_amount,
                    rec.amount_leaf or 0.0,
                    precision_rounding=amount_rounding,
                ) == 0
            )

    @api.constrains("quantity", "qty_done", "line_type", "uom_id")
    def _check_qty_done_range(self):
        for rec in self:
            if rec.line_type and rec.line_type != "item":
                continue
            planned = rec.quantity or 0.0
            done = rec.qty_done or 0.0
            rounding = rec.uom_id.rounding if rec.uom_id else 0.0001
            if float_compare(done, 0.0, precision_rounding=rounding) == -1:
                raise UserError("累计完成量不能为负数。")
            if float_compare(done, planned, precision_rounding=rounding) == 1:
                raise UserError("累计完成量不能超过计划工程量。")

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure project_id is set, inheriting from parent when missing."""
        for vals in vals_list:
            if not vals.get("project_id") and vals.get("parent_id"):
                parent = self.browse(vals["parent_id"])
                if parent.exists():
                    vals["project_id"] = parent.project_id.id
            if vals.get("version_id"):
                version = self.env["project.boq.version"].browse(vals["version_id"])
                vals.setdefault("project_id", version.project_id.id)
        return super().create(vals_list)

    def write(self, vals):
        snapshot_fields = {
            "project_id", "parent_id", "sequence", "section_type", "code", "name", "spec",
            "division_name", "single_name", "unit_name", "major_name", "uom_id", "quantity",
            "price", "imported_amount", "has_imported_amount", "cost_item_id", "remark",
            "is_provisional", "category", "boq_category",
            "fee_type_id", "tax_type_id", "version_id", "sheet_index",
            "sheet_name", "line_type",
            "source_code", "source_row_type", "calculated_amount", "calculation_scope_item_count",
            "calculation_scope_start_sequence", "calculation_scope_end_sequence",
        }
        if snapshot_fields.intersection(vals) and self.filtered(
            lambda line: line.version_id.state in ("published", "superseded")
        ):
            raise UserError(_("已发布清单版本的业务字段不可修改，请创建新版本。"))
        return super().write(vals)

    @api.depends("code")
    def _compute_code_segments(self):
        for rec in self:
            code = (rec.code or "").strip()
            if code.isdigit() and len(code) == 12:
                rec.code_cat = code[:2]
                rec.code_prof = code[:4]
                rec.code_division = code[:6]
                rec.code_subdivision = code[:9]
                rec.code_item = code[:12]
            else:
                rec.code_cat = False
                rec.code_prof = False
                rec.code_division = False
                rec.code_subdivision = False
                rec.code_item = False

    _sql_constraints = []

    @api.constrains("project_id", "parent_id", "version_id", "import_batch_id", "work_id")
    def _check_structure_binding(self):
        """All projections and audit ownership must remain inside one project/version."""
        for rec in self:
            if rec.parent_id and rec.parent_id.project_id != rec.project_id:
                raise ValidationError(_("上下级清单必须属于同一项目。"))
            if rec.parent_id and rec.parent_id.version_id != rec.version_id:
                raise ValidationError(_("上下级清单必须属于同一清单版本。"))
            if rec.version_id and rec.version_id.project_id != rec.project_id:
                raise ValidationError(_("清单行与清单版本必须属于同一项目。"))
            if rec.import_batch_id and rec.import_batch_id.version_id != rec.version_id:
                raise ValidationError(_("清单行与导入批次必须属于同一清单版本。"))
            if rec.work_id and rec.work_id.project_id != rec.project_id:
                raise ValidationError(_("成本 WBS 与清单行必须属于同一项目。"))

    def unlink(self):
        if self.filtered(lambda line: line.version_id.state in ("published", "superseded")):
            raise UserError(_("已发布清单版本的明细属于审计事实，不能删除。"))
        frozen_projects = set()
        for rec in self:
            project = rec.project_id
            if project and project.id not in frozen_projects and project.is_boq_frozen():
                frozen_projects.add(project.id)
        if frozen_projects:
            raise_guard(
                "P0_BOQ_FROZEN",
                "BOQ",
                "删除清单行",
                reasons=[f"涉及已冻结项目数：{len(frozen_projects)}"],
                hints=["请先完成/撤销结算或付款流程后再调整 BOQ"],
            )
        return super().unlink()

    line_type = fields.Selection(
        [
            ("major", "专业工程"),
            ("division", "分部工程"),
            ("group", "标题/汇总行"),
            ("item", "清单项"),
        ],
        string="行类型",
        default="item",
        index=True,
        help="major/division 为系统生成的节点；item 为实际清单行；group 为历史汇总行。",
    )

    @api.depends("parent_path")
    def _compute_level(self):
        """根据 parent_path 计算 BOQ 树中的层级深度：
        - parent_path 形如 '12/', '12/45/', '12/45/78/' 或不带尾斜杠都能兼容
        - 顶级节点 level=1，子节点依次 +1
            """
        for rec in self:
            path = (rec.parent_path or "").strip("/")  # 去掉首尾 '/'
            if not path:
                rec.level = 1  # 没有路径，当作顶级
            else:
                rec.level = len(path.split("/"))

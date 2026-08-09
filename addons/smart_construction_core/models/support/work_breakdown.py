# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ConstructionWorkBreakdown(models.Model):
    """
    项目管理 WBS：
    - 由用户按管理目标建立，不复制 BOQ/CBS 的分部分项层级；
    - 清单通过执行范围分配到 WBS，可跨分部、分项组合为工作包；
    - 任务、空间和标段围绕 WBS 工作包形成执行管理对象。
    """

    _name = "construction.work.breakdown"
    _description = "项目管理 WBS"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _parent_name = "parent_id"
    _parent_store = True
    _order = "project_id, parent_path, sequence, id"

    name = fields.Char("WBS 名称", required=True, tracking=True)
    code = fields.Char("WBS 编码", tracking=True)
    active = fields.Boolean("有效", default=True)
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        required=True,
        index=True,
        ondelete="cascade",
        domain=[],
        check_company=False,  # 避免自动生成 company_id 依赖域
    )
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        related="project_id.company_id",
        store=True,
        readonly=True,
    )

    parent_id = fields.Many2one(
        "construction.work.breakdown",
        string="上级 WBS",
        index=True,
        ondelete="cascade",
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        "construction.work.breakdown",
        "parent_id",
        string="下级 WBS",
    )
    sequence = fields.Integer("序号", default=10)
    # 便于调试/报表的层级深度，根=0
    level = fields.Integer("层级", compute="_compute_level", store=True, recursive=True)
    level_type = fields.Selection(
        [
            ("phase", "管理阶段"),
            ("control_account", "控制账户"),
            ("work_package", "工作包"),
            ("summary", "汇总节点"),
            ("other", "其他"),
        ],
        string="节点角色",
        help="可选管理属性，不决定 WBS 层级；层级由上级 WBS 和缩进操作形成。",
    )
    source_type = fields.Selection(
        [("manual", "用户规划"), ("template", "模板生成")],
        string="来源",
        required=True,
        default="manual",
        index=True,
    )
    source_key = fields.Char(
        "来源稳定键",
        index=True,
        readonly=True,
        help="清单生成节点的稳定业务键，用于跨版本幂等同步。",
    )
    placement_mode = fields.Selection(
        [("planned", "用户规划")],
        string="位置管理",
        default="planned",
        required=True,
        help="WBS 的层级位置由用户管理，不受清单同步影响。",
    )
    boq_version_id = fields.Many2one(
        "project.boq.version",
        string="同步清单版本",
        index=True,
        ondelete="set null",
        readonly=True,
    )
    status = fields.Selection(
        [
            ("planned", "规划中"),
            ("active", "生效"),
            ("inactive", "停用"),
            ("what_if", "假设方案"),
        ],
        string="WBS 状态",
        default="planned",
        required=True,
        tracking=True,
    )
    manager_id = fields.Many2one(
        "res.users", string="责任经理", tracking=True, domain=[("share", "=", False)]
    )
    description = fields.Text("范围说明")

    boq_line_ids = fields.One2many(
        "project.boq.line", "work_id",
        string="关联清单"
    )
    task_ids = fields.One2many(
        "project.task", "work_id",
        string="关联任务"
    )
    execution_scope_ids = fields.One2many(
        "construction.execution.scope", "wbs_id", string="执行范围"
    )

    boq_quantity_total = fields.Float(
        "兼容工程量合计",
        compute="_compute_totals",
        store=True,
        recursive=True,
    )
    boq_amount_total = fields.Monetary(
        "分配金额合计",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
        recursive=True,
    )
    boq_line_count = fields.Integer(
        "分配清单项数",
        compute="_compute_totals",
        store=True,
        recursive=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="project_id.company_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.depends("parent_id.level")
    def _compute_level(self):
        """父层级+1，根节点为0。"""
        for rec in self:
            rec.level = rec.parent_id.level + 1 if rec.parent_id else 0


    @api.depends(
        "execution_scope_ids.allocation_ids.active",
        "execution_scope_ids.allocation_ids.boq_line_id",
        "execution_scope_ids.allocation_ids.allocated_amount",
        "child_ids.boq_quantity_total",
        "child_ids.boq_amount_total",
        "child_ids.boq_line_count",
    )
    def _compute_totals(self):
        """按执行分配自底向上汇总；不同计量单位不在 WBS 中相加。"""
        for rec in self:
            allocations = rec.execution_scope_ids.mapped("allocation_ids").filtered("active")
            self_amt = sum(allocations.mapped("allocated_amount"))
            child_amt = sum(rec.child_ids.mapped("boq_amount_total"))
            rec.boq_quantity_total = 0.0
            rec.boq_amount_total = self_amt + child_amt
            rec.boq_line_count = len(allocations) + sum(rec.child_ids.mapped("boq_line_count"))

    @api.constrains("parent_id", "project_id")
    def _check_parent_project(self):
        """父子节点必须同一项目，避免跨项目串树。"""
        for rec in self:
            if rec.parent_id and rec.parent_id.project_id != rec.project_id:
                raise ValidationError("工程结构的父节点与子节点必须属于同一项目。")

    def _ordered_siblings(self):
        self.ensure_one()
        domain = [("project_id", "=", self.project_id.id)]
        domain.append(("parent_id", "=", self.parent_id.id or False))
        return self.search(domain, order="sequence,id")

    def _create_planned_wbs(self, parent):
        self.ensure_one()
        siblings = self.search(
            [
                ("project_id", "=", self.project_id.id),
                ("parent_id", "=", parent.id or False),
            ],
            order="sequence,id",
        )
        ordinal = len(siblings) + 1
        prefix = parent.code if parent and parent.code else self.project_id.code
        code = f"{prefix}.{ordinal}" if prefix else False
        return self.create(
            {
                "project_id": self.project_id.id,
                "parent_id": parent.id or False,
                "code": code,
                "name": "新增 WBS",
                "sequence": ordinal * 10,
                "status": "planned",
                "source_type": "manual",
                "placement_mode": "planned",
            }
        )

    def action_wbs_add_child(self):
        for rec in self:
            rec._create_planned_wbs(rec)
        return True

    def action_wbs_add_sibling(self):
        for rec in self:
            rec._create_planned_wbs(rec.parent_id)
        return True

    def action_wbs_move_up(self):
        for rec in self:
            siblings = rec._ordered_siblings()
            index = siblings.ids.index(rec.id)
            if index <= 0:
                continue
            previous = siblings[index - 1]
            previous_sequence, current_sequence = previous.sequence, rec.sequence
            if previous_sequence == current_sequence:
                previous_sequence = index * 10
                current_sequence = (index + 1) * 10
            previous.sequence, rec.sequence = current_sequence, previous_sequence
        return True

    def action_wbs_move_down(self):
        for rec in self:
            siblings = rec._ordered_siblings()
            index = siblings.ids.index(rec.id)
            if index >= len(siblings) - 1:
                continue
            following = siblings[index + 1]
            current_sequence, following_sequence = rec.sequence, following.sequence
            if current_sequence == following_sequence:
                current_sequence = (index + 1) * 10
                following_sequence = (index + 2) * 10
            rec.sequence, following.sequence = following_sequence, current_sequence
        return True

    def action_wbs_indent(self):
        for rec in self:
            siblings = rec._ordered_siblings()
            index = siblings.ids.index(rec.id)
            if index <= 0:
                raise UserError("首个同级 WBS 无法缩进，请先将目标上级移动到它之前。")
            rec.parent_id = siblings[index - 1].id
        return True

    def action_wbs_outdent(self):
        for rec in self:
            if not rec.parent_id:
                raise UserError("顶层 WBS 无法继续提升。")
            rec.parent_id = rec.parent_id.parent_id.id or False
        return True

    def unlink(self):
        protected = self.filtered(
            lambda rec: rec.task_ids
            or rec.execution_scope_ids.mapped("allocation_ids").filtered("active")
        )
        if protected:
            raise UserError("已关联计划作业或清单分配的 WBS 不可删除，请先完成重新分配。")
        if self.mapped("child_ids") - self:
            raise UserError("包含下级 WBS 的节点不可直接删除，请先提升或移动下级节点。")
        return super().unlink()

    _sql_constraints = [
        (
            "project_source_key_unique",
            "unique(project_id, source_key)",
            "同一项目下的 WBS 模板节点稳定键不能重复。",
        ),
    ]

    def _exec_structure_action(self):
        ctx = dict(self.env.context or {})
        project_id = False
        if self and self[0].project_id:
            project_id = self[0].project_id.id
        project_id = project_id or ctx.get("default_project_id") or ctx.get("project_id") or ctx.get("active_id")
        if not project_id:
            next_action = {
                "type": "ir.actions.act_window",
                "name": "项目列表",
                "res_model": "project.project",
                "view_mode": "kanban,tree,form",
                "views": [(False, "kanban"), (False, "tree"), (False, "form")],
                "target": "current",
                "context": ctx,
            }
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "执行结构",
                    "message": "请先选择项目，将跳转到项目列表。",
                    "type": "warning",
                    "sticky": False,
                    "next": next_action,
                },
            }

        ctx.setdefault("default_project_id", project_id)
        ctx.setdefault("search_default_project_id", project_id)
        ctx["sc_exec_view"] = "wbs"
        view = self.env.ref("smart_construction_core.view_exec_structure_wbs_tree")
        search_view = self.env.ref("smart_construction_core.view_project_wbs_search")
        return {
            "type": "ir.actions.act_window",
            "name": "执行结构",
            "res_model": "construction.work.breakdown",
            "view_mode": "tree,form",
            "views": [(view.id, "tree"), (False, "form")],
            "search_view_id": search_view.id,
            "domain": [("project_id", "=", project_id)],
            "context": ctx,
            "target": "current",
        }

    def action_open_exec_wbs(self):
        return self._exec_structure_action()

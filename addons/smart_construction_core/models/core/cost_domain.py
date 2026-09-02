# -*- coding: utf-8 -*-
"""
成本域聚合工具 / 领域服务。

历史模型门面 project.budget.line 已移动至 budget_compat.py，
避免 cost_domain.py 里同时承担“领域服务 + 历史模型门面”的职责。
"""
from psycopg2.extras import execute_values

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..support.state_guard import raise_guard


class ProjectBudget(models.Model):
    """Budget header scoped to a single project/contract version."""

    _name = "project.budget"
    _description = "项目预算头"
    _order = "project_id, version_date desc, id desc"

    name = fields.Char("预算名称", required=True)
    budget_kind = fields.Selection(
        [
            ("general", "综合预算"),
            ("material", "物资预算"),
            ("labor", "人工预算"),
            ("machine", "机械预算"),
            ("subcontract", "分包预算"),
            ("measure", "措施费"),
            ("tax", "税费"),
        ],
        string="预算业务分类",
        default="general",
        required=True,
        index=True,
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        related="project_id.company_id",
        store=True,
        readonly=True,
    )
    contract_id = fields.Many2one(
        "account.analytic.account",
        string="关联合同",
        domain="[('project_ids', 'in', project_id)]",
        help="可选：用于映射主合同或成本中心。",
    )
    origin_budget_id = fields.Many2one(
        "project.budget",
        string="复制来源",
        readonly=True,
        help="若该预算由复制生成，记录源预算版本以便审计追踪。",
    )

    version = fields.Char(
        "版本号",
        help="投标版/控制版/调整版，若未填写系统会按项目自动生成。",
        copy=False,
    )
    version_date = fields.Date("版本日期", default=fields.Date.context_today)
    is_active = fields.Boolean("当前生效", default=True)

    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        default=lambda self: self.env.company.currency_id.id,
    )

    amount_revenue_target = fields.Monetary("目标收入", currency_field="currency_id")
    amount_cost_target = fields.Monetary("目标成本", currency_field="currency_id")
    margin_target = fields.Monetary(
        "目标毛利", currency_field="currency_id", compute="_compute_margin", store=True
    )
    margin_rate_target = fields.Float(
        "目标毛利率(%)", compute="_compute_margin", store=True
    )

    note = fields.Text("说明")
    legacy_source_model = fields.Char("历史来源模型", index=True, readonly=True)
    legacy_record_id = fields.Char("历史记录ID", index=True, readonly=True)
    legacy_document_state = fields.Char("历史状态", index=True, readonly=True)

    line_ids = fields.One2many(
        "project.budget.boq.line",
        "budget_id",
        string="预算清单",
    )

    _sql_constraints = [
        (
            "project_version_unique",
            "unique(project_id, version)",
            "同一项目的预算版本号必须唯一。",
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """在创建预算时自动填充版本号。"""
        for vals in vals_list:
            project_id = vals.get("project_id")
            if project_id and not vals.get("version"):
                vals["version"] = self._generate_version_label(project_id)
        return super().create(vals_list)

    def _generate_version_label(self, project_id):
        """返回形如 V001 的连续版本号。"""
        count = self.search_count([("project_id", "=", project_id)])
        return f"V{count + 1:03d}"

    @api.depends("amount_revenue_target", "amount_cost_target")
    def _compute_margin(self):
        """Compute target margin/margin rate for reporting."""
        for rec in self:
            revenue = rec.amount_revenue_target or 0.0
            cost = rec.amount_cost_target or 0.0
            margin = revenue - cost
            rec.margin_target = margin
            rec.margin_rate_target = revenue and (margin / revenue) * 100.0 or 0.0

    def action_set_active(self):
        """Mark current budget as active and archive siblings."""
        for budget in self:
            if budget.is_active:
                continue
            others = self.search(
                [
                    ("project_id", "=", budget.project_id.id),
                    ("is_active", "=", True),
                    ("id", "!=", budget.id),
                ]
            )
            others.write({"is_active": False})
            budget.is_active = True
        return True

    def action_archive_version(self):
        """Archive the selected budget versions."""
        self.write({"is_active": False})
        return True

    def action_copy_version(self):
        """Duplicate budget; copy_allocations=False drops BoQ→科目映射."""
        self.ensure_one()
        copy_vals = {
            "name": f"{self.name} - 复制",
            "version": self._generate_version_label(self.project_id.id),
            "is_active": False,
            "version_date": fields.Date.context_today(self),
            "origin_budget_id": self.id,
        }
        new_budget = self.copy(copy_vals)
        if not self.env.context.get("copy_allocations", True):
            new_budget.line_ids.mapped("alloc_ids").unlink()
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.budget",
            "res_id": new_budget.id,
            "view_mode": "form",
            "target": "current",
            "context": {"default_project_id": new_budget.project_id.id},
        }


class ProjectBudgetBoqLine(models.Model):
    _name = "project.budget.boq.line"
    _description = "项目预算 / 中标清单行"
    _order = "budget_id, sequence, id"
    _rec_name = "name"

    budget_id = fields.Many2one(
        "project.budget",
        string="预算",
        required=True,
        ondelete="cascade",
        index=True,
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="budget_id.project_id",
        store=True,
        readonly=True,
    )

    sequence = fields.Integer("序号", default=10)
    boq_code = fields.Char("清单编码")
    name = fields.Char("清单名称", required=True)

    wbs_id = fields.Many2one(
        "construction.work.breakdown",
        string="对应工程结构",
        help="绑定工程结构以便在统计中核对预算与成本",
    )

    qty_bidded = fields.Float(
        "中标工程量",
        digits="Product Unit of Measure",
    )
    uom_id = fields.Many2one("uom.uom", string="计量单位")
    price_bidded = fields.Monetary(
        "中标单价",
        currency_field="currency_id",
    )
    amount_bidded = fields.Monetary(
        "中标合价",
        compute="_compute_bidded_amount",
        store=True,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="budget_id.currency_id",
        store=True,
        readonly=True,
    )

    measure_rule = fields.Selection(
        [
            ("qty", "按工程量计价"),
            ("stage", "按阶段计价"),
            ("lump", "总价计价"),
        ],
        string="计价规则",
        default="qty",
    )
    cost_collection_method = fields.Selection(
        [
            ("contract", "合同归集"),
            ("non_contract", "无合同归集"),
            ("adjustment", "事后调整"),
        ],
        string="成本归集方式",
        index=True,
    )
    cost_allocation_method = fields.Selection(
        [
            ("direct", "直接分摊"),
            ("ratio", "按比例分摊"),
            ("area", "按面积分摊"),
            ("manual", "手工分摊"),
        ],
        string="成本分摊方式",
        index=True,
    )

    revenue_recognition = fields.Selection(
        [
            ("progress", "按进度确认收入"),
            ("milestone", "按里程碑确认收入"),
            ("completion", "竣工一次性确认"),
        ],
        string="收入确认方式",
        default="progress",
    )

    def unlink(self):
        """防御：若已有合同明细引用该预算清单行，禁止删除并给出友好提示。

        之前用户在界面操作时直接触发数据库外键报错（construction_contract_line_boq_line_id_fkey），
        这里提前拦截，避免出现难以理解的错误弹窗，并明确提示需要先处理合同明细或取消关联。
        """
        ContractLine = self.env["construction.contract.line"]
        for rec in self:
            ref_lines = ContractLine.search([("boq_line_id", "=", rec.id)], limit=1)
            if ref_lines:
                raise UserError(
                    "清单行已被合同明细引用，不能删除。\n"
                    "清单：%s\n"
                    "请先在合同中调整或解除关联，再删除清单。"
                    % (rec.display_name or rec.id)
                )
        return super().unlink()

    note = fields.Char("备注")
    alloc_ids = fields.One2many(
        "project.budget.cost.alloc",
        "budget_boq_line_id",
        string="成本分摊",
        help="记录该清单行如何拆值到不同成本科目",
    )

    @api.depends("qty_bidded", "price_bidded")
    def _compute_bidded_amount(self):
        for line in self:
            qty = line.qty_bidded or 0.0
            price = line.price_bidded or 0.0
            line.amount_bidded = qty * price
class ProjectCostCode(models.Model):
    _name = "project.cost.code"
    _description = "项目成本科目"
    _inherit = ["sc.delete.guard.mixin"]
    _parent_name = "parent_id"
    _parent_store = True
    _order = "code, id"
    _sc_delete_guard_blocker_models = (
        "project.budget.cost.alloc",
        "project.cost.code",
        "project.cost.ledger",
        "sc.contract.event",
    )

    name = fields.Char("名称", required=True)
    code = fields.Char("编码", required=True, index=True)
    parent_id = fields.Many2one("project.cost.code", string="上级科目", index=True)
    parent_path = fields.Char(index=True, unaccent=False)

    type = fields.Selection(
        [
            ("labor", "人工"),
            ("material", "材料"),
            ("machine", "机械"),
            ("subcontract", "分包"),
            ("measure", "措施费"),
            ("overhead", "管理费"),
            ("tax", "税金"),
            ("other", "其他"),
        ],
        string="成本类别",
        required=True,
    )

    level = fields.Integer("层级", compute="_compute_hierarchy", store=True, recursive=True)
    active = fields.Boolean("有效", default=True)
    path_display = fields.Char("路径", compute="_compute_hierarchy", store=True, recursive=True)

    note = fields.Char("说明")

    _sql_constraints = [
        ("code_unique", "unique(code)", "成本科目编码必须唯一。"),
    ]

    @api.model
    def _get_or_create_standard_code(self, code, name, cost_type, note):
        """Concurrency-safe authority for standard industry cost codes."""
        self.env["project.cost.ledger"]._lock_generated_source_headers(
            [("project.cost.code", code)]
        )
        cost_code = self.sudo().with_context(active_test=False).search(
            [("code", "=", code)], limit=1
        )
        if cost_code and cost_code.type != cost_type:
            raise ValidationError(
                _("标准成本科目 %(code)s 已存在但类别不是 %(type)s，禁止静默复用。")
                % {"code": code, "type": cost_type}
            )
        if cost_code:
            if not cost_code.active:
                cost_code.active = True
            return cost_code
        return self.sudo().create({"code": code, "name": name, "type": cost_type, "note": note})

    @api.depends("parent_id", "parent_id.level", "parent_id.path_display", "code", "name")
    def _compute_hierarchy(self):
        for rec in self:
            if rec.parent_id:
                rec.level = (rec.parent_id.level or 0) + 1
                rec.path_display = f"{rec.parent_id.path_display or rec.parent_id.display_name} / {rec.code} {rec.name}"
            else:
                rec.level = 1
                rec.path_display = f"{rec.code} {rec.name}" if rec.code else rec.name

    def unlink(self):
        self._sc_raise_delete_blockers(action_label="删除成本科目")
        return super().unlink()

class ProjectCostLedger(models.Model):
    _name = "project.cost.ledger"
    _description = "项目成本台账"
    _order = "date desc, id desc"

    project_id = fields.Many2one(
        "project.project",
        string="项目",
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        related="project_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )

    wbs_id = fields.Many2one(
        "construction.work.breakdown",
        string="工程结构",
        index=True,
    )

    cost_code_id = fields.Many2one(
        "project.cost.code",
        string="成本科目",
        required=True,
        index=True,
    )

    date = fields.Date("发生日期", index=True, default=fields.Date.context_today)
    period = fields.Char("期间文本", index=True)
    period_id = fields.Many2one(
        "project.cost.period",
        string="成本期间",
        required=True,
        index=True,
    )

    qty = fields.Float("数量")
    uom_id = fields.Many2one("uom.uom", string="单位")
    amount = fields.Monetary(
        "项目公司币种金额",
        currency_field="currency_id",
        help="进入项目报表的标准金额，始终使用项目所属公司的本位币。",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="项目公司币种",
        index=True,
        help=(
            "标准化事实必须使用项目所属公司的本位币；仅无法确定归属的历史隔离事实允许为空，"
            "禁止使用当前环境公司猜测补值。"
        ),
    )
    source_amount = fields.Monetary(
        "来源原币金额",
        currency_field="source_currency_id",
        readonly=True,
        help="生成事实保留的来源金额；项目报表不直接聚合此字段。",
    )
    source_currency_id = fields.Many2one(
        "res.currency",
        string="来源币种",
        readonly=True,
        index=True,
    )
    normalization_state = fields.Selection(
        [
            ("normalized", "已标准化"),
            ("legacy_unresolved_owner", "历史归属待认领"),
            ("legacy_unresolved_currency", "历史币种待换算"),
        ],
        string="标准化状态",
        required=True,
        default="normalized",
        readonly=True,
        index=True,
        help="历史事实只有在公司归属和公司币种金额均可确定时才进入标准口径。",
    )

    partner_id = fields.Many2one("res.partner", string="往来单位/人员")
    cost_flow_label = fields.Char(string="成本来源", compute="_compute_cost_flow_label")
    source_model = fields.Char("来源模型", index=True, readonly=True)
    source_id = fields.Integer("来源记录ID", index=True, readonly=True)
    source_line_id = fields.Integer("来源行ID", index=True, readonly=True)
    is_generated = fields.Boolean(
        "系统生成",
        compute="_compute_recognition_metadata",
        store=True,
        index=True,
    )
    recognition_stage = fields.Selection(
        [
            ("manual_adjustment", "人工调整"),
            ("commitment", "采购承诺"),
            ("receipt_accrual", "收货/库存取得暂估"),
            ("consumption", "现场消耗"),
            ("settlement", "商业结算/应付依据"),
            ("accounting_actual", "会计确认"),
            ("legacy_unresolved", "历史来源待认领"),
        ],
        string="确认阶段",
        compute="_compute_recognition_metadata",
        store=True,
        index=True,
        help="描述成本事实的经济阶段；不同阶段禁止直接混加。",
    )
    reporting_treatment = fields.Selection(
        [
            ("financial_actual", "财务实际"),
            ("operational_actual", "运营实际"),
            ("manual_actual", "人工实际调整"),
            ("memorandum", "阶段备忘（不计实际）"),
        ],
        string="报表口径",
        compute="_compute_recognition_metadata",
        store=True,
        index=True,
        help="现有“实际成本”报表仅汇总财务实际和人工实际调整。",
    )
    recognition_state = fields.Selection(
        [("active", "有效"), ("withdrawn", "已撤回")],
        string="事实状态",
        required=True,
        default="active",
        index=True,
        readonly=True,
    )

    note = fields.Char("备注/摘要")

    _GENERATED_CONTEXT_KEY = "sc_cost_generated_service"
    # A plain context boolean is an RPC input, not an authority boundary.  The
    # object identity below cannot be reconstructed by a JSON-RPC caller and is
    # only injected by the service methods in this Python process.
    _GENERATED_SERVICE_TOKEN = object()
    _GENERATED_IMMUTABLE_FIELDS = {
        "project_id", "wbs_id", "cost_code_id", "date", "period", "period_id",
        "qty", "uom_id", "amount", "currency_id", "source_amount",
        "source_currency_id", "partner_id", "source_model", "source_id",
        "source_line_id", "recognition_state", "normalization_state", "note",
    }
    _SOURCE_STAGE_POLICY = {
        "purchase.order.line": ("commitment", "memorandum"),
        "stock.move": ("receipt_accrual", "memorandum"),
        "sc.material.outbound": ("consumption", "operational_actual"),
        "sc.equipment.usage": ("consumption", "operational_actual"),
        "sc.material.settlement": ("settlement", "memorandum"),
        "account.move.line": ("accounting_actual", "financial_actual"),
    }

    @api.depends(
        "source_model", "source_id", "source_line_id", "project_id", "company_id",
        "normalization_state",
    )
    def _compute_recognition_metadata(self):
        for rec in self:
            rec.is_generated = bool(rec.source_model)
            complete_line = rec.source_line_id > 0 or (
                rec.source_model == "sc.equipment.usage" and rec.source_line_id == 0
            )
            complete_identity = bool(rec.source_model and rec.source_id and complete_line)
            if rec.normalization_state != "normalized" or not rec.project_id or not rec.company_id:
                policy = ("legacy_unresolved", "memorandum")
            elif not rec.source_model:
                policy = ("manual_adjustment", "manual_actual")
            elif not complete_identity or rec.source_model not in self._SOURCE_STAGE_POLICY:
                policy = ("legacy_unresolved", "memorandum")
            else:
                policy = self._SOURCE_STAGE_POLICY[rec.source_model]
            rec.recognition_stage, rec.reporting_treatment = policy

    @api.constrains("project_id", "company_id", "currency_id", "normalization_state")
    def _check_normalized_currency_authority(self):
        for rec in self.filtered(lambda item: item.normalization_state == "normalized"):
            if not rec.project_id or not rec.company_id or not rec.currency_id:
                raise ValidationError(_("标准化成本事实必须明确项目、公司和项目公司币种。"))
            if rec.currency_id != rec.company_id.currency_id:
                raise ValidationError(_("标准化成本事实必须使用项目所属公司的本位币。"))

    def _is_generated_service_call(self):
        return self.env.context.get(self._GENERATED_CONTEXT_KEY) is self._GENERATED_SERVICE_TOKEN

    @api.model
    def _lock_generated_source_headers(self, source_pairs):
        """Serialize every mutation belonging to the same source document."""
        lock_keys = sorted({
            "%s:%s" % (source_model, source_id)
            for source_model, source_id in source_pairs
            if source_model and source_id
        })
        if lock_keys:
            self._cr.execute(
                """
                SELECT pg_advisory_xact_lock(hashtextextended(source_key, 0))
                  FROM unnest(%s::text[]) AS source_key
                 ORDER BY source_key
                """,
                [lock_keys],
            )

    @api.model
    def _lock_existing_generated_source_rows(self, source_pairs):
        """Force stale repeatable-read snapshots into the standard retry path."""
        pairs = sorted({
            (source_model, int(source_id))
            for source_model, source_id in source_pairs
            if source_model and source_id
        })
        if pairs:
            self._cr.execute(
                """
                SELECT ledger.id
                  FROM project_cost_ledger AS ledger
                  JOIN unnest(%s::text[], %s::integer[]) AS source(source_model, source_id)
                    ON source.source_model = ledger.source_model
                   AND source.source_id = ledger.source_id
                 ORDER BY ledger.id
                   FOR UPDATE OF ledger
                """,
                [[pair[0] for pair in pairs], [pair[1] for pair in pairs]],
            )

    def init(self):
        """Make the registered generated-fact identity a database invariant."""
        self._cr.execute(
            """
            SELECT source_model, source_id, source_line_id, count(*)
              FROM project_cost_ledger
             WHERE source_model IS NOT NULL AND source_model <> ''
               AND source_id > 0 AND source_line_id IS NOT NULL
             GROUP BY source_model, source_id, source_line_id
            HAVING count(*) > 1
             LIMIT 1
            """
        )
        duplicate = self._cr.fetchone()
        if duplicate:
            raise ValidationError(
                _("成本台账存在重复生成事实 %(identity)s（%(count)s 条），升级已停止；请先走受控数据修复。")
                % {"identity": duplicate[:3], "count": duplicate[3]}
            )
        self._cr.execute(
            """
            SELECT idx.indisunique,
                   ARRAY(
                       SELECT attr.attname
                         FROM unnest(idx.indkey) WITH ORDINALITY AS key(attnum, ord)
                         JOIN pg_attribute AS attr
                           ON attr.attrelid = idx.indrelid
                          AND attr.attnum = key.attnum
                        WHERE key.ord <= idx.indnkeyatts
                        ORDER BY key.ord
                   ),
                   pg_get_expr(idx.indpred, idx.indrelid)
              FROM pg_index AS idx
              JOIN pg_class AS index_class ON index_class.oid = idx.indexrelid
              JOIN pg_class AS table_class ON table_class.oid = idx.indrelid
              JOIN pg_namespace AS table_namespace ON table_namespace.oid = table_class.relnamespace
             WHERE index_class.relname = 'project_cost_ledger_generated_source_uniq'
               AND table_class.relname = 'project_cost_ledger'
               AND table_namespace.nspname = current_schema()
            """
        )
        index_shape = self._cr.fetchone()
        if index_shape:
            predicate = "".join((index_shape[2] or "").lower().split())
            predicate = predicate.replace("(", "").replace(")", "").replace("::text", "")
            expected_predicate = (
                "source_modelisnotnullandsource_model<>''and"
                "source_id>0andsource_line_idisnotnull"
            )
            if (
                not index_shape[0]
                or index_shape[1] != ["source_model", "source_id", "source_line_id"]
                or predicate != expected_predicate
            ):
                raise ValidationError(
                    _("成本事实唯一索引结构与受治理定义不一致，升级已停止；请先走 P4 索引修复。")
                )
        self._cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS project_cost_ledger_generated_source_uniq
                ON project_cost_ledger (source_model, source_id, source_line_id)
             WHERE source_model IS NOT NULL AND source_model <> ''
               AND source_id > 0 AND source_line_id IS NOT NULL
            """
        )

    @api.depends("source_model", "note", "cost_code_id.name")
    def _compute_cost_flow_label(self):
        source_labels = {
            "purchase.order": _("采购成本"),
            "purchase.order.line": _("采购成本"),
            "stock.picking": _("入库成本"),
            "stock.move": _("入库成本"),
            "stock.move.line": _("入库成本"),
            "account.move": _("凭证成本"),
            "account.move.line": _("凭证成本"),
            "payment.request": _("付款成本"),
            "sc.payment.execution": _("付款成本"),
            "sc.expense.claim": _("费用成本"),
            "sc.invoice.registration": _("发票税务成本"),
            "sc.tax.deduction.registration": _("抵扣税务成本"),
            "sc.settlement.order": _("合同结算成本"),
            "sc.settlement.order.line": _("合同结算成本"),
            "sc.material.acceptance": _("材料成本"),
            "sc.material.outbound": _("材料出库成本"),
            "sc.material.settlement": _("材料结算成本"),
            "sc.labor.settlement": _("劳务结算成本"),
            "sc.equipment.settlement": _("机械结算成本"),
            "sc.equipment.usage": _("机械台班成本"),
            "sc.subcontract.settlement": _("分包结算成本"),
        }
        for rec in self:
            source_model = rec.source_model or ""
            if source_model in source_labels:
                rec.cost_flow_label = source_labels[source_model]
            elif rec.cost_code_id:
                rec.cost_flow_label = rec.cost_code_id.name
            else:
                rec.cost_flow_label = _("成本归集")

    @staticmethod
    def _compute_period_value(date_value):
        if not date_value:
            return False
        date_obj = fields.Date.to_date(date_value)
        return date_obj.strftime("%Y-%m") if date_obj else False

    def _require_visible_project_scope(self, project_ids):
        normalized_ids = {
            int(project_id)
            for project_id in project_ids
            if project_id
        }
        if not normalized_ids:
            return
        Project = self.env["project.project"]
        if self.env.su:
            visible_projects = Project.search([("id", "in", list(normalized_ids))])
        else:
            visible_projects = Project.search(
                [
                    ("id", "in", list(normalized_ids)),
                    ("company_id", "in", self.env.companies.ids),
                    "|",
                    ("user_id", "=", self.env.uid),
                    ("message_is_follower", "=", True),
                ]
            )
        if set(visible_projects.ids) != normalized_ids:
            raise AccessError(_("项目不存在或当前用户无权访问。"))

    def _resolve_periods(self, vals_list):
        """Resolve all periods with one lookup and deterministic project locking."""
        project_ids = sorted({
            int(vals["project_id"])
            for vals in vals_list
            if vals.get("project_id")
        })
        self._lock_cost_projects(project_ids)
        keys = {
            (int(vals["project_id"]), vals["period"])
            for vals in vals_list
            if vals.get("project_id") and vals.get("period") and not vals.get("period_id")
        }
        if not keys:
            return
        Period = self.env["project.cost.period"].sudo()
        periods = Period.search(
            [("project_id", "in", project_ids), ("period", "in", sorted({key[1] for key in keys}))]
        )
        by_key = {(period.project_id.id, period.period): period for period in periods}
        missing = [
            {"project_id": project_id, "period": period_value}
            for project_id, period_value in sorted(keys)
            if (project_id, period_value) not in by_key
        ]
        if missing:
            for period in Period.create(missing):
                by_key[(period.project_id.id, period.period)] = period
        for vals in vals_list:
            key = (int(vals.get("project_id") or 0), vals.get("period"))
            if not vals.get("period_id") and key in by_key:
                vals["period_id"] = by_key[key].id

    @api.model
    def _lock_cost_projects(self, project_ids):
        project_ids = sorted({int(project_id) for project_id in project_ids if project_id})
        if project_ids:
            self._cr.execute(
                "SELECT id FROM project_project WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                [project_ids],
            )

    @api.model
    def _lock_cost_periods(self, periods):
        """Close the period-lock check/write race with deterministic row locks."""
        period_ids = sorted(set(periods.ids))
        if period_ids:
            self._cr.execute(
                "SELECT id FROM project_cost_period WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                [period_ids],
            )
            periods.invalidate_recordset(["locked"])
        return periods

    @api.model
    def _validate_source_identity(self, vals):
        values = (vals.get("source_model"), vals.get("source_id"), vals.get("source_line_id"))
        populated = (bool(values[0]), bool(values[1]), values[2] is not None and values[2] is not False)
        if any(populated) and not all(populated):
            raise ValidationError(_("生成成本事实必须完整填写来源模型、来源记录和来源行。"))
        if populated[1] and int(values[1]) <= 0:
            raise ValidationError(_("来源记录 ID 必须大于 0。"))
        if populated[2] and int(values[2]) < 0:
            raise ValidationError(_("来源行 ID 不能小于 0。"))
        if all(populated) and int(values[2]) == 0 and values[0] != "sc.equipment.usage":
            raise ValidationError(_("只有机械台班这种无明细行来源可以使用来源行 ID 0。"))
        return all(populated)

    @api.model
    def _normalize_generated_values(self, vals_list):
        normalized = [dict(vals) for vals in vals_list]
        project_ids = {int(vals["project_id"]) for vals in normalized if vals.get("project_id")}
        projects = {project.id: project for project in self.env["project.project"].browse(project_ids).exists()}
        for vals in normalized:
            if not self._validate_source_identity(vals):
                raise ValidationError(_("生成成本事实不能使用人工台账身份。"))
            if vals["source_model"] not in self._SOURCE_STAGE_POLICY:
                raise ValidationError(_("当前来源模型未登记成本确认阶段，禁止生成成本事实。"))
            project = projects.get(int(vals.get("project_id") or 0))
            if not project:
                raise ValidationError(_("生成成本事实必须关联有效项目。"))
            if not project.company_id:
                raise ValidationError(_("成本事实项目必须明确所属公司，禁止使用当前用户公司隐式兜底。"))
            fact_date = vals.get("date") or fields.Date.context_today(self)
            source_currency = self.env["res.currency"].browse(
                vals.get("source_currency_id") or vals.get("currency_id") or project.company_id.currency_id.id
            )
            source_amount = vals.get("source_amount", vals.get("amount", 0.0))
            company_amount = vals.pop("company_amount", None)
            vals.update(
                {
                    "date": fact_date,
                    "period": self._compute_period_value(fact_date),
                    "source_amount": source_amount,
                    "source_currency_id": source_currency.id,
                    "amount": company_amount if company_amount is not None else source_currency._convert(
                        source_amount, project.company_id.currency_id,
                        project.company_id, fact_date,
                    ),
                    "currency_id": project.company_id.currency_id.id,
                    "recognition_state": vals.get("recognition_state", "active"),
                    "normalization_state": "normalized",
                }
            )
        self._resolve_periods(normalized)
        return normalized

    @api.model
    def _upsert_generated_cost_rows(self, vals_list):
        """Only supported mutation boundary for source-backed cost facts."""
        identities = [
            (vals.get("source_model"), int(vals.get("source_id") or 0), int(vals.get("source_line_id") or 0))
            for vals in vals_list
            if self._validate_source_identity(vals)
        ]
        if len(identities) != len(vals_list):
            raise ValidationError(_("生成成本事实不能使用人工台账身份。"))
        if len(identities) != len(set(identities)):
            raise ValidationError(_("同一批次包含重复成本事实来源。"))
        # Header serialization must precede normalization: period resolution
        # locks the project row, so taking that lock first would invert the
        # withdraw/replay lock order and permit an advisory/FK deadlock.
        self._lock_generated_source_headers((identity[0], identity[1]) for identity in identities)
        normalized = self._normalize_generated_values(vals_list)
        identity_set = set(identities)
        periods = self.env["project.cost.period"].browse(
            sorted({vals["period_id"] for vals in normalized})
        )
        self._lock_cost_periods(periods)
        for period in periods:
            self._ensure_period_unlocked(period, "Write")
        self._lock_existing_generated_source_rows(
            (identity[0], identity[1]) for identity in identities
        )
        existing = self.sudo().search(
            [
                ("source_model", "in", sorted({key[0] for key in identities})),
                ("source_id", "in", sorted({key[1] for key in identities})),
                ("source_line_id", "in", sorted({key[2] for key in identities})),
            ]
        ) if identities else self.browse()
        by_identity = {
            (row.source_model, row.source_id, row.source_line_id): row
            for row in existing
            if (row.source_model, row.source_id, row.source_line_id) in identity_set
        }
        service = self.sudo().with_context(
            **{self._GENERATED_CONTEXT_KEY: self._GENERATED_SERVICE_TOKEN}
        )
        create_values = []
        update_values = []
        result = self.browse()
        for vals, identity in zip(normalized, identities):
            row = by_identity.get(identity)
            if row:
                changed = {}
                for field_name, value in vals.items():
                    field = row._fields.get(field_name)
                    current = row[field_name]
                    if field and field.type == "many2one":
                        current = current.id
                    elif field and field.type == "date" and current:
                        current = fields.Date.to_string(current)
                        value = fields.Date.to_string(fields.Date.to_date(value)) if value else value
                    if current != value:
                        changed[field_name] = value
                if changed:
                    update_values.append((row, vals))
                result |= row
            else:
                create_values.append(vals)
        if create_values:
            result |= service.create(create_values)
        if update_values:
            self._batch_update_generated_rows(update_values)
            result.invalidate_recordset()
        return result

    @api.model
    def _batch_update_generated_rows(self, updates):
        """Apply heterogeneous generated-fact corrections in one SQL write."""
        columns = (
            "project_id", "wbs_id", "cost_code_id", "date", "period", "period_id",
            "qty", "uom_id", "amount", "currency_id", "source_amount",
            "source_currency_id", "partner_id", "recognition_state", "note",
            "normalization_state",
        )
        records = self.browse([row.id for row, _vals in updates]).sudo()
        records.read(list(columns))
        project_ids = set()
        payload = []
        for row, vals in updates:
            self._ensure_period_unlocked(row.period_id, "Write")
            project = self.env["project.project"].browse(
                vals.get("project_id") or row.project_id.id
            )
            period = self.env["project.cost.period"].browse(
                vals.get("period_id") or row.period_id.id
            )
            wbs = self.env["construction.work.breakdown"].browse(
                vals.get("wbs_id") or row.wbs_id.id
            )
            if period and (period.project_id != project or period.period != vals.get("period")):
                raise ValidationError(_("成本期间必须与成本事实的项目和月份一致。"))
            if wbs and wbs.project_id != project:
                raise ValidationError(_("工程结构必须与成本台账属于同一项目。"))
            if vals.get("currency_id") != project.company_id.currency_id.id:
                raise ValidationError(_("成本台账金额必须使用项目所属公司的本位币。"))
            self._ensure_period_unlocked(period, "Write")
            project_ids.add(project.id)
            row_values = []
            for field_name in columns:
                value = vals[field_name] if field_name in vals else row[field_name]
                field = row._fields[field_name]
                if field.type == "many2one":
                    value = (value.id or None) if hasattr(value, "id") else (value or None)
                elif field.type == "date" and value:
                    value = fields.Date.to_date(value)
                row_values.append(value)
            payload.append((row.id, *row_values, self.env.uid))
        self.env["project.project"].browse(project_ids)._ensure_operation_allowed(
            operation_label="记载成本台账", blocked_states=("paused", "closed")
        )
        integer_columns = {
            "project_id", "wbs_id", "cost_code_id", "period_id", "uom_id",
            "currency_id", "source_currency_id", "partner_id",
        }
        assignments = ", ".join(
            "%s = data.%s%s" % (
                column,
                column,
                "::integer" if column in integer_columns else "",
            )
            for column in columns
        )
        records.flush_recordset()
        execute_values(
            self._cr,
            """
            UPDATE project_cost_ledger AS ledger
               SET %s, write_uid = data.write_uid, write_date = NOW()
              FROM (VALUES %%s) AS data(id, %s, write_uid)
             WHERE ledger.id = data.id
            """ % (assignments, ", ".join(columns)),
            payload,
        )
        records.invalidate_recordset(
            list(columns) + ["write_uid", "write_date"], flush=False
        )
        records.modified(list(columns))
        self.env.invalidate_all(flush=False)
        return records

    @api.model
    def _withdraw_generated_cost_rows(self, source_model, source_ids):
        source_ids = sorted({int(source_id) for source_id in source_ids if source_id})
        self._lock_generated_source_headers((source_model, source_id) for source_id in source_ids)
        rows = self.sudo().search(
            [("source_model", "=", source_model), ("source_id", "in", source_ids)]
        )
        if rows:
            self._lock_cost_projects(rows.mapped("project_id").ids)
            periods = self._lock_cost_periods(rows.mapped("period_id"))
            for period in periods:
                self._ensure_period_unlocked(period, "Write")
            self._lock_existing_generated_source_rows(
                (source_model, source_id) for source_id in source_ids
            )
            rows.invalidate_recordset()
            active_rows = rows.filtered(lambda row: row.recognition_state != "withdrawn")
            if active_rows:
                active_rows.flush_recordset()
                self._cr.execute(
                    """
                    UPDATE project_cost_ledger
                       SET recognition_state = 'withdrawn', write_uid = %s, write_date = NOW()
                     WHERE id = ANY(%s)
                    """,
                    [self.env.uid, active_rows.ids],
                )
                active_rows.invalidate_recordset(
                    ["recognition_state", "write_uid", "write_date"], flush=False
                )
                active_rows.modified(["recognition_state"])
                self.env.invalidate_all(flush=False)
        return rows

    def action_open_source(self):
        """Open the registered source while preserving its native ACL/rules."""
        self.ensure_one()
        if not self.is_generated or self.source_model not in self._SOURCE_STAGE_POLICY:
            raise UserError(_("当前成本事实没有可导航的受支持来源。"))
        source_record_id = (
            self.source_line_id
            if self.source_model in ("purchase.order.line", "account.move.line", "stock.move")
            else self.source_id
        )
        source = self.env[self.source_model].browse(source_record_id).exists()
        if not source:
            raise UserError(_("来源记录不存在或已被移除。"))
        source.check_access_rights("read")
        source.check_access_rule("read")
        return {
            "type": "ir.actions.act_window",
            "name": _("成本事实来源"),
            "res_model": self.source_model,
            "res_id": source.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _automatic_source_enabled(self, parameter_key, company=None):
        """Read the single automatic acquisition authority and fail closed on drift."""
        company = company or self.env.company
        source_fields = {
            "smart_construction_core.sc_cost_from_account_move": "sc_cost_from_account_move",
            "smart_construction_core.sc_cost_from_purchase": "sc_cost_from_purchase",
            "smart_construction_core.sc_cost_from_stock": "sc_cost_from_stock",
        }
        enabled = [key for key, field_name in source_fields.items() if company[field_name]]
        if len(enabled) > 1:
            raise ValidationError(
                _("成本台账自动来源配置冲突：当前公司只能启用凭证、采购或入库中的一个来源。")
            )
        return enabled == [parameter_key]

    def _ensure_period_unlocked(self, period_rec, operation_label):
        if period_rec and period_rec.locked:
            raise_guard(
                "PERIOD_LOCKED",
                period_rec.display_name or "Period",
                operation_label,
                reasons=["period is locked"],
            )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            install_legacy = (
                self.env.su
                and self.env.context.get("install_mode")
                and bool(vals.get("source_model"))
            )
            generated = bool(vals.get("source_model")) if install_legacy else self._validate_source_identity(vals)
            if generated and not install_legacy and not self._is_generated_service_call():
                raise AccessError(_("生成成本事实只能由受控成本事实服务写入。"))
            if (
                vals.get("normalization_state", "normalized") != "normalized"
                and not install_legacy
                and not self._is_generated_service_call()
            ):
                raise AccessError(_("成本事实标准化状态只能由受控迁移或认领服务维护。"))
        self._require_visible_project_scope(
            vals.get("project_id") for vals in vals_list
        )
        project_ids = {vals.get("project_id") for vals in vals_list if vals.get("project_id")}
        projects = {project.id: project for project in self.env["project.project"].browse(project_ids).exists()}
        for vals in vals_list:
            if not vals.get("date"):
                vals["date"] = fields.Date.context_today(self)
            expected_period = self._compute_period_value(vals["date"])
            if vals.get("period") and vals["period"] != expected_period:
                raise ValidationError(_("成本期间必须与事实日期所属月份一致。"))
            vals["period"] = expected_period
            project = projects.get(vals.get("project_id"))
            if project:
                if not project.company_id:
                    raise ValidationError(_("成本事实项目必须明确所属公司，禁止使用当前用户公司隐式兜底。"))
                vals.setdefault("currency_id", project.company_id.currency_id.id)
                if vals.get("currency_id") != project.company_id.currency_id.id:
                    raise ValidationError(_("成本台账金额必须使用项目所属公司的本位币。"))
            if vals.get("period_id"):
                period_rec = self.env["project.cost.period"].browse(vals["period_id"])
                if period_rec.project_id.id != vals.get("project_id"):
                    raise ValidationError(_("成本期间必须与成本台账属于同一项目。"))
                if period_rec.period != expected_period:
                    raise ValidationError(_("成本期间记录必须与事实日期所属月份一致。"))
            elif not vals.get("project_id") or not vals.get("period"):
                raise_guard(
                    "PERIOD_LOCKED",
                    "Period",
                    "Create",
                    reasons=["period is required"],
                )
            if vals.get("wbs_id"):
                wbs = self.env["construction.work.breakdown"].browse(vals["wbs_id"])
                if wbs.project_id.id != vals.get("project_id"):
                    raise ValidationError(_("工程结构必须与成本台账属于同一项目。"))
        self._resolve_periods(vals_list)
        periods = self._lock_cost_periods(
            self.env["project.cost.period"].browse(
                sorted({vals["period_id"] for vals in vals_list if vals.get("period_id")})
            )
        )
        for period in periods:
            self._ensure_period_unlocked(period, "Create")
        if project_ids:
            projects = self.env["project.project"].browse(project_ids)
            projects._ensure_operation_allowed(
                operation_label="记载成本台账",
                blocked_states=("paused", "closed"),
            )
        return super().create(vals_list)

    def write(self, vals):
        install_legacy = self.env.su and self.env.context.get("install_mode")
        service_call = self._is_generated_service_call()
        if "normalization_state" in vals and not install_legacy and not service_call:
            raise AccessError(_("成本事实标准化状态只能由受控迁移或认领服务维护。"))
        if self.filtered("is_generated") and not install_legacy and not service_call:
            if self._GENERATED_IMMUTABLE_FIELDS & set(vals):
                raise AccessError(_("生成成本事实只能由受控成本事实服务更新或撤回。"))
        if {"source_model", "source_id", "source_line_id"} & set(vals):
            for rec in self:
                identity = {
                    "source_model": vals.get("source_model", rec.source_model),
                    "source_id": vals.get("source_id", rec.source_id),
                    "source_line_id": vals.get("source_line_id", rec.source_line_id),
                }
                if not install_legacy:
                    self._validate_source_identity(identity)
                if not rec.is_generated and any(identity.values()) and not service_call:
                    raise AccessError(_("人工成本事实不得提升为系统生成事实。"))
                if rec.is_generated and identity != {
                    "source_model": rec.source_model,
                    "source_id": rec.source_id,
                    "source_line_id": rec.source_line_id,
                }:
                    raise ValidationError(_("生成成本事实的来源身份不可变更。"))
        if vals.get("project_id"):
            self._require_visible_project_scope([vals["project_id"]])
        self._lock_cost_projects(
            self.mapped("project_id").ids + ([vals["project_id"]] if vals.get("project_id") else [])
        )
        Period = self.env["project.cost.period"]
        for rec in self:
            rec_vals = dict(vals)
            target_date = rec_vals.get("date") or rec.date
            expected_period = self._compute_period_value(target_date)
            if rec_vals.get("period") and rec_vals["period"] != expected_period:
                raise ValidationError(_("成本期间必须与事实日期所属月份一致。"))
            rec_vals["period"] = expected_period
            if "period_id" in rec_vals:
                period_rec = Period.browse(rec_vals.get("period_id"))
                if period_rec and period_rec.period != expected_period:
                    raise ValidationError(_("成本期间记录必须与事实日期所属月份一致。"))
            else:
                project_id = rec_vals.get("project_id") or rec.project_id.id
                pending = {"project_id": project_id, "period": expected_period}
                self._resolve_periods([pending]) if project_id and expected_period else None
                period_rec = Period.browse(pending.get("period_id"))
                if period_rec:
                    rec_vals = dict(rec_vals)
                    rec_vals.setdefault("period_id", period_rec.id)
                    rec_vals.setdefault("period", period_rec.period)
            self._lock_cost_periods(rec.period_id | period_rec)
            self._ensure_period_unlocked(rec.period_id, "Write")
            self._ensure_period_unlocked(period_rec, "Write")
            target_project = self.env["project.project"].browse(
                rec_vals.get("project_id") or rec.project_id.id
            )
            if rec_vals.get("currency_id", rec.currency_id.id) != target_project.company_id.currency_id.id:
                raise ValidationError(_("成本台账金额必须使用项目所属公司的本位币。"))
            target_period = period_rec or rec.period_id
            if target_period and target_period.project_id != target_project:
                raise ValidationError(_("成本期间必须与成本台账属于同一项目。"))
            target_wbs = self.env["construction.work.breakdown"].browse(
                rec_vals.get("wbs_id", rec.wbs_id.id)
            )
            if target_wbs and target_wbs.project_id != target_project:
                raise ValidationError(_("工程结构必须与成本台账属于同一项目。"))
            super(ProjectCostLedger, rec).write(rec_vals)
        return True

    def unlink(self):
        if self.filtered("is_generated") and not self._is_generated_service_call():
            raise AccessError(_("生成成本事实不得直接删除；请通过来源业务撤回。"))
        self._lock_cost_projects(self.mapped("project_id").ids)
        self._lock_cost_periods(self.mapped("period_id"))
        for rec in self:
            self._ensure_period_unlocked(rec.period_id, "Delete")
        return super().unlink()


class ProjectBudgetCostAlloc(models.Model):
    _name = "project.budget.cost.alloc"
    _description = "预算清单与成本科目分摊"
    _order = "budget_boq_line_id, cost_code_id, id"

    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="budget_boq_line_id.project_id",
        store=True,
        readonly=True,
        index=True,
    )

    budget_boq_line_id = fields.Many2one(
        "project.budget.boq.line",
        string="预算清单行",
        required=True,
        ondelete="cascade",
        index=True,
    )

    cost_code_id = fields.Many2one(
        "project.cost.code",
        string="成本科目",
        required=True,
        index=True,
    )

    ratio = fields.Float("分摊比例(0-1)", help="建议值，可不强制合计=1")
    amount_budget = fields.Monetary("对应预算金额", currency_field="currency_id")

    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="budget_boq_line_id.currency_id",
        store=True,
        readonly=True,
    )

    note = fields.Char("说明")

# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


_PAYROLL_STATE_TOKEN = object()
_SALARY_PAYMENT_STATE_TOKEN = object()
_SALARY_PAYMENT_SUMMARY_TOKEN = object()


class ScHrPayrollDocument(models.Model):
    _name = "sc.hr.payroll.document"
    _description = "人事薪酬办理单"
    _inherit = ["sc.business.fact.mixin", "mail.thread", "mail.activity.mixin", "sc.delete.guard.mixin"]
    _order = "period_year desc, period_month desc, business_date desc, id desc"

    def _selection_fact_type(self):
        return [
            ("social_person_registration", "社保人员登记"),
            ("social_registration", "社保登记"),
            ("provident_fund_registration", "公积金登记"),
            ("salary_registration", "工资登记"),
            ("subsidy", "补助"),
            ("bonus", "奖金"),
        ]

    employee_user_id = fields.Many2one("res.users", string="人员", index=True, tracking=True, help='公积金登记建议补充缴存人员')
    company_id = fields.Many2one(
        "res.company", readonly=True, string="所属公司", index=True, ondelete="restrict",
        help="薪酬事实的公司归属；项目为可选业务范围，不能代替公司归属。",
    )
    employee_name = fields.Char(string="人员姓名", index=True, tracking=True, help='公积金登记建议补充缴存人员')
    employee_status = fields.Char(string="人员状态", index=True)
    employee_type = fields.Char(string="人员类型", index=True)
    id_number = fields.Char(string="身份证号", index=True)
    contact_phone = fields.Char(string="联系方式", index=True)
    period_year = fields.Integer(string="年度", index=True, help='公积金登记建议补充缴存期间')
    period_month = fields.Integer(string="月份", index=True, help='公积金登记建议补充缴存期间')
    payer_unit = fields.Char(string="缴纳单位", index=True, help='建议补充缴存单位')
    payout_unit = fields.Char(string="发放单位", index=True, help='建议补充发放单位')
    people_count = fields.Integer(string="人数")
    social_security_base = fields.Monetary(string="社保基数", currency_field="currency_id")
    provident_fund_account = fields.Char(string="公积金账号", index=True, tracking=True, help='建议补充公积金账号')
    provident_fund_base = fields.Monetary(string="公积金基数", currency_field="currency_id", help='建议补充公积金基数')
    company_contribution_rate = fields.Float(string="单位缴存比例(%)", digits=(8, 4))
    individual_contribution_rate = fields.Float(string="个人缴存比例(%)", digits=(8, 4))
    company_amount = fields.Monetary(string="公司承担", currency_field="currency_id")
    individual_amount = fields.Monetary(string="个人承担", currency_field="currency_id")
    salary_base = fields.Monetary(string="薪资基数", currency_field="currency_id")
    gross_amount = fields.Monetary(string="应发工资", currency_field="currency_id")
    deduction_amount = fields.Monetary(string="扣款合计", currency_field="currency_id")
    net_salary = fields.Monetary(string="实发工资", currency_field="currency_id")
    paid_amount = fields.Monetary(string="已付款金额", currency_field="currency_id", tracking=True)
    payment_opening_amount = fields.Monetary(
        string="历史已付款承接金额",
        currency_field="currency_id",
        default=0,
        readonly=True,
        copy=False,
    )
    payment_detail_initialized = fields.Boolean(
        string="发放明细已接管", default=False, readonly=True, copy=False
    )
    payment_ids = fields.One2many(
        "sc.hr.salary.payment", "payroll_document_id", string="薪资发放登记", readonly=True
    )
    unpaid_amount = fields.Monetary(
        string="未付款金额",
        currency_field="currency_id",
        compute="_compute_payment_summary",
        store=True,
        readonly=True,
    )
    payment_state = fields.Selection(
        [("unpaid", "未付款"), ("partial", "部分付款"), ("paid", "已付款")],
        string="付款状态",
        compute="_compute_payment_summary",
        store=True,
        readonly=True,
        index=True,
    )
    item_type = fields.Char(string="事项类型", tracking=True)
    amount = fields.Monetary(string="金额", currency_field="currency_id", tracking=True)
    certificate_fee = fields.Monetary(string="证书费用", currency_field="currency_id")
    occurrence_date = fields.Date(string="发生日期", index=True)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_hr_payroll_document_attachment_rel",
        "document_id",
        "attachment_id",
        string="附件",
        help='建议上传薪资核算依据',
    )
    legacy_document_no = fields.Char(string="历史单号", index=True, readonly=True)
    legacy_document_state = fields.Char(string="历史状态", index=True, readonly=True)
    legacy_source_table = fields.Char(string="历史来源表", index=True, readonly=True)
    legacy_source_id = fields.Char(string="历史来源ID", index=True, readonly=True)
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory", sc_ui_usage="interaction")

    _sql_constraints = [
        (
            "hr_payroll_legacy_source_unique",
            "unique(legacy_source_table, legacy_source_id)",
            "同一历史人事薪酬单据只能投影一次。",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get([
            "company_id", "project_id", "fact_type", "state", "paid_amount",
            "payment_opening_amount", "payment_detail_initialized",
        ])
        for values in vals_list:
            project_id = values.get("project_id", defaults.get("project_id"))
            company_id = values.get("company_id", defaults.get("company_id"))
            if project_id:
                project = self.env["project.project"].browse(project_id)
                project.check_access_rights("read")
                project.check_access_rule("read")
                if not project.exists() or not project.company_id:
                    raise ValidationError(_("薪酬项目必须具有明确公司归属。"))
                if company_id and company_id != project.company_id.id:
                    raise ValidationError(_("薪酬公司必须与项目公司一致。"))
                company_id = project.company_id.id
            elif "company_id" not in values and not company_id:
                company_id = self.env.company.id
            if not company_id:
                raise ValidationError(_("薪酬事实必须声明公司归属。"))
            if not self.env.su and company_id not in self.env.companies.ids:
                raise AccessError(_("无权在该公司创建薪酬事实。"))
            values["company_id"] = company_id
            fact_type = values.get("fact_type", defaults.get("fact_type"))
            is_salary = fact_type == "salary_registration"
            is_legacy = bool(
                values.get("legacy_source_table") or values.get("legacy_source_id")
            )
            if not is_salary:
                continue
            maintenance_import = is_legacy and self.env.su and self.env.uid == SUPERUSER_ID
            state = values.get("state", defaults.get("state", "draft"))
            paid_amount = values.get("paid_amount", defaults.get("paid_amount", 0))
            if not maintenance_import and state != "draft":
                raise UserError(_("新建薪资核算单必须从草稿开始。"))
            if not maintenance_import and paid_amount:
                raise UserError(_("新建薪资已付款金额必须由薪资发放登记形成。"))
            if not maintenance_import and any(
                values.get(field, defaults.get(field))
                for field in ("payment_opening_amount", "payment_detail_initialized")
            ):
                raise UserError(_("薪资历史付款承接只能由受管导入生成。"))
            if maintenance_import and paid_amount:
                values.setdefault("payment_opening_amount", paid_amount)
                values.setdefault("payment_detail_initialized", True)
        return super().create(vals_list)

    @api.constrains("company_id", "project_id", "department_id")
    def _check_payroll_ownership(self):
        for record in self:
            if not record.company_id:
                raise ValidationError(_("薪酬事实必须声明公司归属。"))
            if record.project_id:
                record.project_id.check_access_rights("read")
                record.project_id.check_access_rule("read")
                if record.project_id.company_id != record.company_id:
                    raise ValidationError(_("薪酬公司必须与项目公司一致。"))
            if record.department_id and record.department_id.company_id != record.company_id:
                raise ValidationError(_("薪酬部门必须属于同一公司。"))

    def _business_specific_fields(self):
        return [
            "employee_user_id",
            "company_id",
            "employee_name",
            "employee_status",
            "employee_type",
            "id_number",
            "contact_phone",
            "period_year",
            "period_month",
            "payer_unit",
            "payout_unit",
            "people_count",
            "social_security_base",
            "provident_fund_account",
            "provident_fund_base",
            "company_contribution_rate",
            "individual_contribution_rate",
            "company_amount",
            "individual_amount",
            "salary_base",
            "gross_amount",
            "deduction_amount",
            "net_salary",
            "paid_amount",
            "payment_opening_amount",
            "payment_detail_initialized",
            "payment_ids",
            "unpaid_amount",
            "payment_state",
            "item_type",
            "amount",
            "certificate_fee",
            "occurrence_date",
            "attachment_ids",
            "legacy_document_no",
            "legacy_document_state",
            "legacy_source_table",
            "legacy_source_id",
            "processing_advisory",
        ]

    @api.depends(
        "fact_type",
        "project_id",
        "department_id",
        "payout_unit",
        "period_year",
        "period_month",
        "payer_unit",
        "provident_fund_account",
        "provident_fund_base",
        "company_contribution_rate",
        "individual_contribution_rate",
        "description",
        "attachment_ids",
    )
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if record.fact_type == "salary_registration":
                if not record.project_id:
                    suggestions.append("建议关联所属项目")
                if not record.department_id:
                    suggestions.append("建议补充所属部门")
                if not record.payout_unit:
                    suggestions.append("建议补充发放单位")
                if not record.description:
                    suggestions.append("建议补充核算说明")
                if not record.attachment_ids:
                    suggestions.append("建议上传薪资核算依据")
            elif record.fact_type == "provident_fund_registration":
                if not record.employee_user_id and not record.employee_name:
                    suggestions.append("建议补充缴存人员")
                if not record.period_year or not record.period_month:
                    suggestions.append("建议补充缴存期间")
                if not record.payer_unit:
                    suggestions.append("建议补充缴存单位")
                if not record.provident_fund_account:
                    suggestions.append("建议补充公积金账号")
                if not record.provident_fund_base:
                    suggestions.append("建议补充公积金基数")
            record.processing_advisory = (
                "；".join(suggestions) if suggestions else ""
            )

    @api.depends("net_salary", "paid_amount")
    def _compute_payment_summary(self):
        for record in self:
            payable = max(record.net_salary or 0.0, 0.0)
            paid = max(record.paid_amount or 0.0, 0.0)
            record.unpaid_amount = max(payable - paid, 0.0)
            if payable and paid >= payable:
                record.payment_state = "paid"
            elif paid:
                record.payment_state = "partial"
            else:
                record.payment_state = "unpaid"

    def _check_submit_requirements(self):
        super()._check_submit_requirements()
        for record in self:
            if record.fact_type in ("social_person_registration", "social_registration"):
                record._require_fields(["department_id", "period_year", "period_month", "payer_unit"])
                if record.fact_type == "social_person_registration":
                    if not record.employee_user_id and not record.employee_name:
                        raise ValidationError(_("请补齐人员后再办理。"))
                    record._require_fields(["id_number", "social_security_base"])
                else:
                    record._require_fields(["company_amount", "individual_amount"])
            elif record.fact_type == "salary_registration":
                if not record.employee_user_id and not record.employee_name:
                    raise ValidationError(_("请补齐人员后再办理。"))
                record._require_fields(["period_year", "period_month", "gross_amount", "net_salary"])
            elif record.fact_type in ("subsidy", "bonus"):
                if not record.employee_user_id and not record.employee_name:
                    raise ValidationError(_("请补齐人员后再办理。"))
                record._require_fields(["department_id", "item_type", "amount", "occurrence_date"])

            elif record.fact_type == "provident_fund_registration":
                for field_name in ("provident_fund_base", "company_amount", "individual_amount"):
                    if record[field_name] < 0:
                        raise ValidationError(_("%s不能为负数。") % record._fields[field_name].string)
                for field_name in ("company_contribution_rate", "individual_contribution_rate"):
                    if record[field_name] < 0 or record[field_name] > 100:
                        raise ValidationError(_("%s必须在 0 到 100 之间。") % record._fields[field_name].string)

            if record.period_month and (record.period_month < 1 or record.period_month > 12):
                raise ValidationError(_("月份必须在 1 到 12 之间。"))

    def _check_payroll_operator(self):
        for record in self:
            if record.fact_type == "salary_registration" and record.project_id:
                allowed = self.env.su or self.env.user.has_group(
                    "smart_construction_core.group_sc_cap_project_user"
                ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin")
            else:
                allowed = self.env.su or self.env.user.has_group(
                    "smart_construction_core.group_sc_cap_business_initiator"
                ) or self.env.user.has_group(
                    "smart_construction_core.group_sc_cap_business_config_admin"
                ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin")
            if not allowed:
                raise UserError(_("你没有权限办理该薪酬单据。"))

    def _check_payroll_manager(self):
        for record in self:
            if record.fact_type == "salary_registration" and record.project_id:
                allowed = self.env.su or self.env.user.has_group(
                    "smart_construction_core.group_sc_cap_project_manager"
                ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin")
            else:
                allowed = self.env.su or self.env.user.has_group(
                    "smart_construction_core.group_sc_cap_business_config_admin"
                ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin")
            if not allowed:
                raise UserError(_("只有对应审批人员可以完成该薪酬单据。"))

    def action_submit(self):
        self._check_payroll_operator()
        if self.filtered(lambda record: record.state != "draft"):
            raise UserError(_("只有草稿状态的薪酬单据可以提交。"))
        return super(
            ScHrPayrollDocument,
            self.with_context(sc_payroll_state_transition=_PAYROLL_STATE_TOKEN),
        ).action_submit()

    def action_done(self):
        self._check_payroll_manager()
        if self.filtered(lambda record: record.state != "in_progress"):
            raise UserError(_("只有办理中的薪酬单据可以完成。"))
        return super(
            ScHrPayrollDocument,
            self.with_context(sc_payroll_state_transition=_PAYROLL_STATE_TOKEN),
        ).action_done()

    def action_cancel(self):
        for record in self:
            if record.state == "draft":
                record._check_payroll_operator()
            elif record.state == "in_progress":
                record._check_payroll_manager()
            else:
                raise UserError(_("只有草稿或办理中的薪酬单据可以取消。"))
        return super(
            ScHrPayrollDocument,
            self.with_context(sc_payroll_state_transition=_PAYROLL_STATE_TOKEN),
        ).action_cancel()

    def action_reset_draft(self):
        self._check_payroll_manager()
        if self.filtered(lambda record: record.state != "cancel"):
            raise UserError(_("只有已取消的薪酬单据可以重置为草稿。"))
        return super(
            ScHrPayrollDocument,
            self.with_context(sc_payroll_state_transition=_PAYROLL_STATE_TOKEN),
        ).action_reset_draft()

    def write(self, vals):
        # Ownership is not a editable label. In particular, changing project
        # must never silently reclassify a salary into another company's realm.
        if "company_id" in vals and any(
            record.company_id.id != vals["company_id"] for record in self
        ):
            raise ValidationError(_("薪酬事实公司归属不能直接修改；历史归属须通过受管迁移核实。"))
        if any(not record.company_id for record in self):
            raise ValidationError(_("历史薪酬归属未核实，禁止继续办理。"))
        if vals.get("fact_type") == "salary_registration" and any(
            record.fact_type != "salary_registration" and (
                record.state != "draft" or record.paid_amount
                or record.payment_opening_amount or record.payment_detail_initialized
                or record.payment_ids
            ) for record in self
        ):
            raise UserError(_("仅无付款事实的草稿可以转为工资核算。"))
        salary_records = self.filtered(
            lambda record: record.fact_type == "salary_registration"
            or vals.get("fact_type") == "salary_registration"
        )
        if (
            "state" in vals
            and salary_records
            and self.env.context.get("sc_payroll_state_transition") is not _PAYROLL_STATE_TOKEN
        ):
            raise UserError(_("项目薪资状态必须通过正式办理动作变更。"))
        immutable_after_done = {
            "fact_type",
            "project_id",
            "employee_user_id",
            "employee_name",
            "period_year",
            "period_month",
            "currency_id",
            "gross_amount",
            "deduction_amount",
            "net_salary",
        }
        if immutable_after_done.intersection(vals) and salary_records.filtered(
            lambda record: record.state == "done"
        ):
            raise UserError(_("已完成的薪资核算核心数据不能直接修改。"))
        if (
            {"paid_amount", "payment_opening_amount", "payment_detail_initialized"}.intersection(vals)
            and self.env.context.get("sc_salary_payment_summary_sync") is not _SALARY_PAYMENT_SUMMARY_TOKEN
            and salary_records
        ):
            raise UserError(_("项目薪资已付款金额必须由薪资发放登记汇总，不能直接修改。"))
        return super().write(vals)

    def init(self):
        self.env.cr.execute(
            """
            UPDATE sc_hr_payroll_document
               SET employee_status = COALESCE(NULLIF(employee_status, ''), NULLIF(legacy_document_state, '')),
                   employee_type = COALESCE(NULLIF(employee_type, ''), NULLIF(item_type, '')),
                   contact_phone = COALESCE(
                       NULLIF(contact_phone, ''),
                       NULLIF(substring(COALESCE(description, '') from '联系方式[：:]\\s*([^\\n\\r]+)'), '')
                   ),
                   payout_unit = COALESCE(NULLIF(payout_unit, ''), NULLIF(payer_unit, ''))
             WHERE legacy_source_table IS NOT NULL
            """
        )

    department_id = fields.Many2one(ondelete="restrict", help='薪资核算建议补充所属部门')

    description = fields.Text(help='薪资核算建议补充核算说明')

    project_id = fields.Many2one(ondelete="restrict", help='薪资核算建议关联所属项目')

    def unlink(self):
        locked = self.filtered(lambda rec: rec.state not in ("draft", "cancel"))
        if locked:
            raise UserError("仅草稿或已取消的人事薪酬办理单允许删除。")
        self._sc_raise_delete_blockers(action_label="删除人事薪酬办理单")
        return super().unlink()


class ScPayrollProjectOwnership(models.Model):
    _inherit = "project.project"

    def write(self, vals):
        if "company_id" in vals:
            changed = self.filtered(lambda record: record.company_id.id != vals["company_id"])
            if changed and self.env["sc.hr.payroll.document"].sudo().with_context(active_test=False).search_count(
                [("project_id", "in", changed.ids)], limit=1
            ):
                raise ValidationError(_("项目已有薪酬事实，不允许改变公司归属。"))
        return super().write(vals)


class ScPayrollDepartmentOwnership(models.Model):
    _inherit = "hr.department"

    def write(self, vals):
        if "company_id" in vals:
            changed = self.filtered(lambda record: record.company_id.id != vals["company_id"])
            if changed and self.env["sc.hr.payroll.document"].sudo().with_context(active_test=False).search_count(
                [("department_id", "in", changed.ids)], limit=1
            ):
                raise ValidationError(_("部门已有薪酬事实，不允许改变公司归属。"))
        return super().write(vals)


class ScHrSalaryPayment(models.Model):
    _name = "sc.hr.salary.payment"
    _description = "薪资发放登记"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "payment_date desc, id desc"

    name = fields.Char("发放单号", required=True, default="新建", copy=False, tracking=True)
    payroll_document_id = fields.Many2one(
        "sc.hr.payroll.document",
        string="薪资核算单",
        required=True,
        index=True,
        ondelete="restrict",
        domain="[('fact_type', '=', 'salary_registration'), ('company_id', '!=', False), ('state', '=', 'done')]",
    )
    project_id = fields.Many2one(
        related="payroll_document_id.project_id", store=True, readonly=True, string="项目", index=True
    )
    company_id = fields.Many2one(
        related="payroll_document_id.company_id", store=True, readonly=True, string="所属公司"
    )
    employee_user_id = fields.Many2one(
        related="payroll_document_id.employee_user_id", store=True, readonly=True, string="人员"
    )
    employee_name = fields.Char(
        related="payroll_document_id.employee_name", store=True, readonly=True, string="人员姓名"
    )
    period_year = fields.Integer(
        related="payroll_document_id.period_year", store=True, readonly=True, string="年度"
    )
    period_month = fields.Integer(
        related="payroll_document_id.period_month", store=True, readonly=True, string="月份"
    )
    currency_id = fields.Many2one(
        related="payroll_document_id.currency_id", store=True, readonly=True, string="币种"
    )
    payable_amount = fields.Monetary(
        related="payroll_document_id.net_salary", readonly=True, string="应发净额"
    )
    payment_date = fields.Date("发放日期", required=True, default=fields.Date.context_today, index=True)
    payment_amount = fields.Monetary("本次发放金额", required=True, currency_field="currency_id", tracking=True)
    payment_method = fields.Selection(
        [("bank", "银行转账"), ("cash", "现金"), ("other", "其他")],
        string="发放方式",
        default="bank",
        required=True,
    )
    payment_reference = fields.Char("支付凭证号", index=True, help='建议补充支付凭证号')
    responsible_id = fields.Many2one(
        "res.users", string="经办人", default=lambda self: self.env.user, index=True
    )
    state = fields.Selection(
        [("draft", "草稿"), ("submitted", "待确认"), ("confirmed", "已确认"), ("cancel", "已取消")],
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_hr_salary_payment_attachment_rel",
        "payment_id",
        "attachment_id",
        string="附件",
        help='建议上传发放依据',
    )
    note = fields.Text("发放说明", help='建议补充发放说明')
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory", sc_ui_usage="interaction")

    @api.model_create_multi
    def create(self, vals_list):
        default_state = self.default_get(["state"]).get("state", "draft")
        if any(values.get("state", default_state) != "draft" for values in vals_list):
            raise UserError(_("新建薪资发放登记必须从草稿开始。"))
        records = super().create(vals_list)
        sequence = self.env["ir.sequence"].sudo()
        for record in records:
            if record.name == "新建":
                record.name = "SALPAY-%s" % (
                    sequence.next_by_code("sc.business.fact") or record.id
                )
            payroll = record.payroll_document_id
            if not payroll.payment_detail_initialized:
                payroll.sudo().with_context(sc_salary_payment_summary_sync=_SALARY_PAYMENT_SUMMARY_TOKEN).write(
                    {
                        "payment_opening_amount": payroll.paid_amount,
                        "payment_detail_initialized": True,
                    }
                )
        return records

    @api.constrains("payment_amount")
    def _check_payment_amount(self):
        for record in self:
            if record.payment_amount <= 0:
                raise ValidationError(_("本次发放金额必须大于0。"))

    @api.constrains("payroll_document_id")
    def _check_payroll_parent_ownership(self):
        for record in self:
            payroll = record.payroll_document_id
            payroll.check_access_rights("read")
            payroll.check_access_rule("read")
            if payroll.fact_type != "salary_registration" or not payroll.company_id:
                raise ValidationError(_("薪资发放必须关联归属明确的工资核算单。"))

    @api.depends("payment_reference", "attachment_ids", "note")
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if not record.payment_reference:
                suggestions.append("建议补充支付凭证号")
            if not record.note:
                suggestions.append("建议补充发放说明")
            if not record.attachment_ids:
                suggestions.append("建议上传发放依据")
            record.processing_advisory = (
                "；".join(suggestions) if suggestions else ""
            )

    def _check_project_manager(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_project_manager"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("只有项目审批人员可以办理薪资发放登记。"))

    def _check_payroll_ready(self):
        for record in self:
            if record.payroll_document_id.state != "done":
                raise UserError(_("薪资发放只能关联已完成的薪资核算单。"))

    def _sync_payroll_payment_summary(self):
        payrolls = self.mapped("payroll_document_id")
        if not payrolls:
            return
        self.env.cr.execute(
            "SELECT id FROM sc_hr_payroll_document WHERE id IN %s ORDER BY id FOR UPDATE",
            [tuple(payrolls.ids)],
        )
        Payment = self.env["sc.hr.salary.payment"].sudo()
        for payroll in payrolls:
            confirmed_total = sum(
                Payment.search(
                    [
                        ("payroll_document_id", "=", payroll.id),
                        ("state", "=", "confirmed"),
                    ]
                ).mapped("payment_amount")
            )
            paid_total = (payroll.payment_opening_amount or 0.0) + confirmed_total
            if payroll.currency_id.compare_amounts(paid_total, payroll.net_salary) > 0:
                raise ValidationError(_("累计薪资发放金额不能超过薪资核算单实发工资。"))
            payroll.sudo().with_context(sc_salary_payment_summary_sync=_SALARY_PAYMENT_SUMMARY_TOKEN).write(
                {"paid_amount": paid_total}
            )

    def action_submit(self):
        self._check_project_manager()
        self._check_payroll_ready()
        if self.filtered(lambda record: record.state != "draft"):
            raise UserError(_("只有草稿状态的薪资发放登记可以提交。"))
        self.with_context(sc_salary_payment_state_transition=_SALARY_PAYMENT_STATE_TOKEN).write(
            {"state": "submitted"}
        )
        return True

    def action_confirm(self):
        self._check_project_manager()
        self._check_payroll_ready()
        if self.filtered(lambda record: record.state != "submitted"):
            raise UserError(_("只有待确认状态的薪资发放登记可以确认。"))
        self.with_context(sc_salary_payment_state_transition=_SALARY_PAYMENT_STATE_TOKEN).write(
            {"state": "confirmed"}
        )
        self._sync_payroll_payment_summary()
        return True

    def action_cancel(self):
        self._check_project_manager()
        if self.filtered(lambda record: record.state not in ("draft", "submitted", "confirmed")):
            raise UserError(_("当前薪资发放登记不能取消。"))
        self.with_context(sc_salary_payment_state_transition=_SALARY_PAYMENT_STATE_TOKEN).write(
            {"state": "cancel"}
        )
        self._sync_payroll_payment_summary()
        return True

    def action_reset_draft(self):
        self._check_project_manager()
        if self.filtered(lambda record: record.state != "cancel"):
            raise UserError(_("只有已取消的薪资发放登记可以重置为草稿。"))
        self.with_context(sc_salary_payment_state_transition=_SALARY_PAYMENT_STATE_TOKEN).write(
            {"state": "draft"}
        )
        return True

    def write(self, vals):
        if vals.get("payroll_document_id"):
            target = self.env["sc.hr.payroll.document"].browse(vals["payroll_document_id"])
            target.check_access_rights("read")
            target.check_access_rule("read")
            if any(record.company_id != target.company_id for record in self):
                raise ValidationError(_("薪资发放不能跨公司更换核算单。"))
        if "state" in vals and self.env.context.get(
            "sc_salary_payment_state_transition"
        ) is not _SALARY_PAYMENT_STATE_TOKEN:
            raise UserError(_("薪资发放状态必须通过正式办理动作变更。"))
        protected_fields = {
            "payroll_document_id",
            "payment_date",
            "payment_amount",
            "currency_id",
            "payment_method",
        }
        if protected_fields.intersection(vals) and self.filtered(
            lambda record: record.state != "draft"
        ):
            raise UserError(_("已提交的薪资发放核心数据不能直接修改。"))
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda record: record.state not in ("draft", "cancel")):
            raise UserError(_("只有草稿或已取消的薪资发放登记可以删除。"))
        return super().unlink()

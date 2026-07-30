# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.float_utils import float_compare


DECISION_VERSION = "BAOSHENG-HISTORICAL-PAYMENT-MIGRATION-V1"
IMPORTER_GROUP = "smart_core.group_smart_core_tenant_payload_importer"


class ScHistoricalPaymentFact(models.Model):
    """Read-only migration fact; deliberately outside the live payment workflow."""

    _name = "sc.historical.payment.fact"
    _description = "历史付款承接事实"
    _order = "id desc"
    _rec_name = "source_external_id"

    _sql_constraints = [
        (
            "source_identity_uniq",
            "unique(company_id, source_system, source_external_id, source_snapshot_identity)",
            "同一来源快照中的历史付款事实不得重复导入。",
        ),
    ]

    company_id = fields.Many2one(
        "res.company", string="公司", required=True, readonly=True, index=True, ondelete="restrict"
    )
    contract_id = fields.Many2one(
        "construction.contract",
        string="历史关联合同",
        required=True,
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="contract_id.project_id",
        store=True,
        readonly=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="contract_id.currency_id",
        store=True,
        readonly=True,
    )
    source_system = fields.Char(string="来源系统", required=True, readonly=True, index=True)
    source_external_id = fields.Char(string="来源记录标识", required=True, readonly=True, index=True)
    source_status = fields.Char(string="来源状态", required=True, readonly=True, index=True)
    source_contract_external_id = fields.Char(
        string="来源合同标识", required=True, readonly=True, index=True
    )
    source_application_amount = fields.Monetary(
        string="历史申请金额", currency_field="currency_id", readonly=True
    )
    historical_confirmed_paid_amount = fields.Monetary(
        string="历史确认已付", currency_field="currency_id", readonly=True
    )
    historical_amount_pending_confirmation = fields.Monetary(
        string="历史金额待确认", currency_field="currency_id", readonly=True
    )
    migration_disposition = fields.Selection(
        [
            ("historical_completed_payment_fact", "历史已完成付款事实"),
            ("historical_pending_review", "历史待确认事项"),
            ("historical_draft_reference", "历史草稿参考"),
        ],
        string="承接类型",
        required=True,
        readonly=True,
        index=True,
    )
    has_authoritative_settlement_basis = fields.Boolean(
        string="具有新系统结算依据", default=False, required=True, readonly=True
    )
    execution_blocked = fields.Boolean(
        string="禁止付款执行", default=True, required=True, readonly=True
    )
    decision_version = fields.Char(
        string="裁决规则版本", required=True, readonly=True, default=DECISION_VERSION
    )
    migration_batch_id = fields.Many2one(
        "sc.tenant.payload.import.batch",
        string="导入批次",
        required=True,
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    source_snapshot_identity = fields.Char(
        string="来源快照", required=True, readonly=True, index=True
    )
    source_record_digest = fields.Char(
        string="来源记录摘要", required=True, readonly=True
    )
    source_execution_count = fields.Integer(
        string="来源执行记录数", default=0, required=True, readonly=True
    )
    source_ledger_external_id = fields.Char(string="来源付款台账标识", readonly=True)
    source_paid_at = fields.Datetime(string="历史付款时间", readonly=True)
    migration_notice = fields.Char(
        string="承接说明",
        compute="_compute_migration_notice",
        readonly=True,
    )

    @api.depends("migration_disposition")
    def _compute_migration_notice(self):
        for record in self:
            record.migration_notice = _("历史承接，无新系统结算依据；只读且不可再次执行。")

    @api.model
    def _assert_import_context(self):
        if not (
            self.env.context.get("sc_tenant_payload_import")
            and self.env.user.has_group(IMPORTER_GROUP)
        ):
            raise AccessError(_("历史付款事实只能由已审计的租户数据导入器创建。"))

    @api.model_create_multi
    def create(self, vals_list):
        self._assert_import_context()
        for vals in vals_list:
            vals["has_authoritative_settlement_basis"] = False
            vals["execution_blocked"] = True
            vals["decision_version"] = DECISION_VERSION
        records = super().create(vals_list)
        records._validate_historical_fact()
        return records

    def write(self, vals):
        self._assert_import_context()
        immutable = set(vals) - {"migration_batch_id"}
        if immutable:
            raise AccessError(_("历史付款事实为只读审计记录，禁止修改业务内容。"))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("历史付款事实不得通过业务界面删除。"))

    @api.constrains(
        "company_id",
        "contract_id",
        "source_status",
        "migration_disposition",
        "source_application_amount",
        "historical_confirmed_paid_amount",
        "historical_amount_pending_confirmation",
        "has_authoritative_settlement_basis",
        "execution_blocked",
        "source_record_digest",
        "source_ledger_external_id",
    )
    def _validate_historical_fact(self):
        for record in self:
            if record.contract_id.company_id != record.company_id:
                raise ValidationError(_("历史付款事实与合同必须属于同一公司。"))
            registration = self.env["sc.tenant.company.registration"].sudo().search(
                [("company_id", "=", record.company_id.id), ("active", "=", True)],
                limit=1,
            )
            if (
                record.company_id.is_platform_bootstrap_company
                or not registration
            ):
                raise ValidationError(_("历史付款事实只能绑定已显式注册的业务公司。"))
            if record.has_authoritative_settlement_basis:
                raise ValidationError(_("历史承接事实不得声明新系统结算依据。"))
            if not record.execution_blocked:
                raise ValidationError(_("历史承接事实必须禁止付款执行。"))
            if len(record.source_record_digest or "") != 64:
                raise ValidationError(_("来源记录摘要必须是64位SHA-256。"))
            rounding = record.currency_id.rounding or 0.01
            confirmed = record.historical_confirmed_paid_amount or 0.0
            pending = record.historical_amount_pending_confirmation or 0.0
            if float_compare(confirmed, 0.0, precision_rounding=rounding) < 0:
                raise ValidationError(_("历史确认已付金额不得为负数。"))
            if float_compare(pending, 0.0, precision_rounding=rounding) < 0:
                raise ValidationError(_("历史待确认金额不得为负数。"))
            completed = record.migration_disposition == "historical_completed_payment_fact"
            if completed:
                if record.source_status != "done" or not record.source_ledger_external_id:
                    raise ValidationError(_("历史完成事实必须具有done状态及权威付款台账。"))
            elif float_compare(confirmed, 0.0, precision_rounding=rounding):
                raise ValidationError(_("非历史完成事项不得计入历史确认已付。"))


class ConstructionContractHistoricalPayment(models.Model):
    _inherit = "construction.contract"

    historical_payment_fact_ids = fields.One2many(
        "sc.historical.payment.fact",
        "contract_id",
        string="历史付款承接事实",
        readonly=True,
    )
    historical_confirmed_paid_amount = fields.Monetary(
        string="历史确认已付",
        currency_field="currency_id",
        compute="_compute_historical_payment_amounts",
        compute_sudo=True,
    )
    historical_amount_pending_confirmation = fields.Monetary(
        string="历史金额待确认",
        currency_field="currency_id",
        compute="_compute_historical_payment_amounts",
        compute_sudo=True,
    )
    new_system_flow_paid_amount = fields.Monetary(
        string="新系统流程已付",
        currency_field="currency_id",
        compute="_compute_historical_payment_amounts",
        compute_sudo=True,
    )
    cumulative_paid_amount = fields.Monetary(
        string="合同累计已付",
        currency_field="currency_id",
        compute="_compute_historical_payment_amounts",
        compute_sudo=True,
    )

    def _compute_historical_payment_amounts(self):
        historical = {}
        if self.ids:
            rows = self.env["sc.historical.payment.fact"].sudo().read_group(
                [("contract_id", "in", self.ids)],
                ["historical_confirmed_paid_amount:sum", "historical_amount_pending_confirmation:sum"],
                ["contract_id"],
            )
            historical = {
                row["contract_id"][0]: (
                    row.get("historical_confirmed_paid_amount_sum", 0.0) or 0.0,
                    row.get("historical_amount_pending_confirmation_sum", 0.0) or 0.0,
                )
                for row in rows
                if row.get("contract_id")
            }
        for contract in self:
            confirmed, pending = historical.get(contract.id, (0.0, 0.0))
            new_system_paid = contract.paid_amount or 0.0
            contract.historical_confirmed_paid_amount = confirmed
            contract.historical_amount_pending_confirmation = pending
            contract.new_system_flow_paid_amount = new_system_paid
            contract.cumulative_paid_amount = confirmed + new_system_paid

# -*- coding: utf-8 -*-
from datetime import date, datetime
import re

from odoo import api, fields, models


def _parse_legacy_amount(value):
    text = str(value or "").replace(",", "").replace("￥", "").replace("¥", "").strip()
    if not text:
        return 0.0
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return 0.0
    return float(match.group(0))


def _parse_legacy_date(value):
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return False
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[: len(fmt)], fmt).date()
        except ValueError:
            continue
    return False


def _parse_legacy_datetime(value):
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return False
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[: len(fmt)], fmt)
        except ValueError:
            continue
    return False


def _normalize_legacy_settlement_state(value):
    text = str(value or "").strip()
    if text == "已结算":
        return "settled"
    if text == "未结算":
        return "unsettled"
    return "unknown" if text else False


def _add_legacy_visible_fields(namespace):
    namespace["legacy_acceptance_label"] = fields.Char(string="验收菜单", readonly=True, index=True)
    namespace["legacy_acceptance_sort_id"] = fields.Integer(string="验收排序锚点", readonly=True, index=True)
    for index in range(1, 61):
        namespace[f"legacy_visible_{index:02d}"] = fields.Char(
            string=f"历史验收可见字段{index:02d}",
            readonly=True,
        )


def _lv(index):
    return "legacy" + "_visible_" + f"{index:02d}"


class MaterialRentalOrderDirectAcceptanceVisible(models.Model):
    _inherit = "sc.material.rental.order"

    _add_legacy_visible_fields(locals())
    invoiced_amount_text = fields.Char(string="已开票金额", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    paid_amount_text = fields.Char(string="已付款金额", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    unpaid_amount_text = fields.Char(string="未付款金额", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    uninvoiced_amount_text = fields.Char(string="未开票金额", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    contract_sign_date_text = fields.Char(string="签订时间", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_material_name = fields.Char(string="材料名称", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_material_spec = fields.Char(string="规格型号", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_quantity_text = fields.Char(string="数量", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_unit_price_text = fields.Char(string="单价", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_deposit_amount_text = fields.Char(string="租赁押金", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_status_display = fields.Char(string="单据状态", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_document_no = fields.Char(string="单据编号", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_document_date = fields.Char(string="单据日期", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_partner_name = fields.Char(string="租赁单位", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_use_unit_name = fields.Char(string="使用单位", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_material_name = fields.Char(string="材料名称", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_material_spec = fields.Char(string="规格型号", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_quantity = fields.Char(string="数量", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_unit_price = fields.Char(string="单价", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_deposit_amount = fields.Char(string="租赁押金", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_settlement_status = fields.Char(string="结算状态", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_settlement_amount = fields.Char(string="单据结算金额", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_compensation_fee = fields.Char(string="赔偿费", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_repair_fee = fields.Char(string="维修费", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_transport_fee = fields.Char(string="进出场费", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_deposit_deduction = fields.Char(string="抵扣押金", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_note = fields.Char(string="备注", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_attachment_text = fields.Char(string="附件", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_project_name = fields.Char(string="项目名称", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_source_created_by = fields.Char(string="录入人", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)
    rental_order_source_created_at = fields.Char(string="录入时间", compute="_compute_rental_order_formal_visible_fields", store=True, readonly=True)

    @api.depends(
        "legacy_acceptance_label",
        "state",
        "name",
        "rental_date",
        "supplier_id",
        "project_id",
        "note",
        "source_created_by",
        "source_created_at",
        *[_lv(index) for index in range(1, 17)],
    )
    def _compute_rental_order_formal_visible_fields(self):
        contract_map = {
            "invoiced_amount_text": _lv(9),
            "paid_amount_text": _lv(10),
            "unpaid_amount_text": _lv(11),
            "uninvoiced_amount_text": _lv(12),
            "contract_sign_date_text": _lv(14),
        }
        rental_in_map = {
            "rental_material_name": _lv(6),
            "rental_material_spec": _lv(7),
            "rental_quantity_text": _lv(8),
            "rental_unit_price_text": _lv(9),
            "rental_deposit_amount_text": _lv(10),
        }
        fields_to_clear = set(contract_map) | set(rental_in_map)
        fields_to_clear |= {
            "rental_order_status_display",
            "rental_order_document_no",
            "rental_order_document_date",
            "rental_order_partner_name",
            "rental_order_use_unit_name",
            "rental_order_material_name",
            "rental_order_material_spec",
            "rental_order_quantity",
            "rental_order_unit_price",
            "rental_order_deposit_amount",
            "rental_order_settlement_status",
            "rental_order_settlement_amount",
            "rental_order_compensation_fee",
            "rental_order_repair_fee",
            "rental_order_transport_fee",
            "rental_order_deposit_deduction",
            "rental_order_note",
            "rental_order_attachment_text",
            "rental_order_project_name",
            "rental_order_source_created_by",
            "rental_order_source_created_at",
        }
        state_labels = dict(self._fields["state"].selection)
        for record in self:
            for field_name in fields_to_clear:
                record[field_name] = False
            if record.legacy_acceptance_label == "租赁合同":
                source_map = contract_map
            elif record.legacy_acceptance_label == "租入":
                source_map = rental_in_map
            else:
                source_map = {}
            for target_field, source_field in source_map.items():
                record[target_field] = getattr(record, source_field, False)
            if record.legacy_acceptance_label == "租入":
                record.rental_order_status_display = record[_lv(1)] or state_labels.get(record.state) or ""
                record.rental_order_document_no = record[_lv(2)] or record.name or ""
                record.rental_order_document_date = record[_lv(3)] or (record.rental_date.isoformat() if record.rental_date else "")
                record.rental_order_partner_name = record[_lv(4)] or (record.supplier_id.display_name if record.supplier_id else "")
                record.rental_order_use_unit_name = record[_lv(5)] or ""
                record.rental_order_material_name = record[_lv(6)] or record.rental_material_name or ""
                record.rental_order_material_spec = record[_lv(7)] or record.rental_material_spec or ""
                record.rental_order_quantity = record[_lv(8)] or record.rental_quantity_text or ""
                record.rental_order_unit_price = record[_lv(9)] or record.rental_unit_price_text or ""
                record.rental_order_deposit_amount = record[_lv(10)] or record.rental_deposit_amount_text or ""
                record.rental_order_note = record[_lv(11)] or (record.note or "")
                record.rental_order_attachment_text = record[_lv(12)] or ""
                record.rental_order_source_created_by = record[_lv(13)] or record.source_created_by or ""
                record.rental_order_source_created_at = record[_lv(14)] or (record.source_created_at and fields.Datetime.to_string(record.source_created_at)) or ""
                record.rental_order_project_name = record[_lv(15)] or (record.project_id.display_name if record.project_id else "")
            elif record.legacy_acceptance_label == "还租":
                record.rental_order_status_display = record[_lv(1)] or state_labels.get(record.state) or ""
                record.rental_order_project_name = record[_lv(2)] or (record.project_id.display_name if record.project_id else "")
                record.rental_order_settlement_status = record[_lv(3)] or ""
                record.rental_order_document_no = record[_lv(4)] or record.name or ""
                record.rental_order_document_date = record[_lv(5)] or (record.rental_date.isoformat() if record.rental_date else "")
                record.rental_order_partner_name = record[_lv(6)] or (record.supplier_id.display_name if record.supplier_id else "")
                record.rental_order_settlement_amount = record[_lv(7)] or ""
                record.rental_order_compensation_fee = record[_lv(8)] or ""
                record.rental_order_repair_fee = record[_lv(9)] or ""
                record.rental_order_transport_fee = record[_lv(10)] or ""
                record.rental_order_attachment_text = record[_lv(11)] or ""
                record.rental_order_note = record[_lv(12)] or (record.note or "")
                record.rental_order_source_created_by = record[_lv(13)] or record.source_created_by or ""
                record.rental_order_source_created_at = record[_lv(14)] or (record.source_created_at and fields.Datetime.to_string(record.source_created_at)) or ""
                record.rental_order_deposit_deduction = record[_lv(15)] or ""
                record.rental_order_use_unit_name = record[_lv(16)] or ""
            else:
                record.rental_order_status_display = state_labels.get(record.state) or ""
                record.rental_order_document_no = record.name or ""
                record.rental_order_document_date = record.rental_date.isoformat() if record.rental_date else ""
                record.rental_order_partner_name = record.supplier_id.display_name if record.supplier_id else ""
                record.rental_order_project_name = record.project_id.display_name if record.project_id else ""
                record.rental_order_note = record.note or ""
                record.rental_order_source_created_by = record.source_created_by or ""
                record.rental_order_source_created_at = (
                    fields.Datetime.to_string(record.source_created_at) if record.source_created_at else ""
                )


class HrPayrollDocumentDirectAcceptanceVisible(models.Model):
    _inherit = "sc.hr.payroll.document"

    _add_legacy_visible_fields(locals())
    payroll_document_status_display = fields.Char(
        string="单据状态",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_project_name = fields.Char(
        string="项目名称",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_no = fields.Char(
        string="单据编号",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_date = fields.Char(
        string="单据日期",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_salary_month = fields.Char(
        string="工资月份",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_net_salary = fields.Char(
        string="本次实发工资总额",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_gross_salary = fields.Char(
        string="本次应发工资总额",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_payment_status = fields.Char(
        string="付款状态",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_paid_amount = fields.Char(
        string="已付款金额",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_unpaid_amount = fields.Char(
        string="未付款金额",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_note = fields.Char(
        string="备注",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_attachment_text = fields.Char(
        string="附件",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_source_created_by = fields.Char(
        string="录入人",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payroll_document_source_created_at = fields.Char(
        string="录入时间",
        compute="_compute_payroll_document_formal_visible_fields",
        store=True,
        readonly=True,
    )

    @api.depends(
        "legacy_acceptance_label",
        "legacy_source_table",
        "state",
        "project_id",
        "name",
        "period_year",
        "period_month",
        "gross_amount",
        "net_salary",
        "attachment_ids",
        "source_created_by",
        "source_created_at",
        *[_lv(index) for index in range(1, 15)],
    )
    def _compute_payroll_document_formal_visible_fields(self):
        state_labels = dict(self._fields["state"].selection)
        for record in self:
            for field_name in (
                "payroll_document_status_display",
                "payroll_document_project_name",
                "payroll_document_no",
                "payroll_document_date",
                "payroll_document_salary_month",
                "payroll_document_net_salary",
                "payroll_document_gross_salary",
                "payroll_document_payment_status",
                "payroll_document_paid_amount",
                "payroll_document_unpaid_amount",
                "payroll_document_note",
                "payroll_document_attachment_text",
                "payroll_document_source_created_by",
                "payroll_document_source_created_at",
            ):
                record[field_name] = False

            is_manager_salary = (
                record.legacy_acceptance_label == "管理人员工资表"
                or record.legacy_source_table == "direct_acceptance:管理人员工资表"
            )
            if is_manager_salary:
                record.payroll_document_status_display = record[_lv(1)] or state_labels.get(record.state) or ""
                record.payroll_document_project_name = record[_lv(2)] or (record.project_id.display_name if record.project_id else "")
                record.payroll_document_no = record[_lv(3)] or record.name or ""
                record.payroll_document_date = record[_lv(4)] or ""
                record.payroll_document_salary_month = record[_lv(5)] or ""
                record.payroll_document_net_salary = record[_lv(6)] or ""
                record.payroll_document_gross_salary = record[_lv(7)] or ""
                record.payroll_document_payment_status = record[_lv(8)] or ""
                record.payroll_document_paid_amount = record[_lv(9)] or ""
                record.payroll_document_unpaid_amount = record[_lv(10)] or ""
                record.payroll_document_note = record[_lv(11)] or ""
                record.payroll_document_attachment_text = record[_lv(12)] or (
                    "附件(%s)" % len(record.attachment_ids) if record.attachment_ids else ""
                )
                record.payroll_document_source_created_by = record[_lv(13)] or record.source_created_by or ""
                record.payroll_document_source_created_at = record[_lv(14)] or (
                    fields.Datetime.to_string(record.source_created_at) if record.source_created_at else ""
                )
                continue

            record.payroll_document_status_display = state_labels.get(record.state) or ""
            record.payroll_document_project_name = record.project_id.display_name if record.project_id else ""
            record.payroll_document_no = record.name or ""
            if record.period_year and record.period_month:
                record.payroll_document_salary_month = "%04d-%02d" % (record.period_year, record.period_month)
            record.payroll_document_net_salary = str(record.net_salary or "") if record.net_salary else ""
            record.payroll_document_gross_salary = str(record.gross_amount or "") if record.gross_amount else ""
            record.payroll_document_attachment_text = "附件(%s)" % len(record.attachment_ids) if record.attachment_ids else ""
            record.payroll_document_source_created_by = record.source_created_by or ""
            record.payroll_document_source_created_at = (
                fields.Datetime.to_string(record.source_created_at) if record.source_created_at else ""
            )

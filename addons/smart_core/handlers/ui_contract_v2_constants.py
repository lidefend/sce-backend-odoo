# -*- coding: utf-8 -*-
"""Static vocabulary used by the UI contract v2 projection handler."""

BUSINESS_OPERATION_FIELD_PRIORITY = (
    "name", "document_no", "legacy_document_no", "invoice_no", "invoice_code",
    "subject", "type", "source_kind", "direction", "project_id",
    "operation_strategy", "partner_id", "contract_id", "settlement_id",
    "payment_request_id", "date_request", "date_receipt", "document_date",
    "invoice_date", "date_contract", "amount", "amount_no_tax", "tax_amount",
    "amount_total", "visible_contract_amount", "settlement_amount",
    "settlement_amount_payable", "paid_amount", "unpaid_amount", "state",
    "document_status", "handler_id", "handler_name", "creator_name",
    "created_time", "note",
)
BUSINESS_OPERATION_TECHNICAL_PREFIXES = ("message_", "activity_", "website_", "rating_")
BUSINESS_OPERATION_TECHNICAL_FIELDS = {
    "id", "display_name", "create_uid", "create_date", "write_uid", "write_date",
    "__last_update",
}
BUSINESS_FORM_STRUCTURE_ALLOWED_LEGACY_FIELDS = {
    "legacy_document_no", "legacy_contract_no", "legacy_status",
}
BUSINESS_FORM_STRUCTURE_HISTORY_LABEL_TOKENS = ("历史", "旧系统", "旧库", "来源", "导入", "原始")
BUSINESS_FORM_STRUCTURE_HISTORY_NAME_PREFIXES = ("legacy_source_",)
BUSINESS_FORM_STRUCTURE_HISTORY_NAME_TOKENS = (
    "_record_id", "_source_", "_batch", "_deleted", "_attachment_ref", "_pid",
    "_parent_id",
)
BUSINESS_FORM_STRUCTURE_HISTORY_NAME_SUFFIXES = ("_id", "_sort")
BUSINESS_FORM_STRUCTURE_INTERNAL_FIELDS = {
    "active", "archived", "color", "can_review", "entry_data", "has_comment",
    "has_message", "hide_reviews", "is_favorite", "is_locked",
    "my_activity_date_deadline", "name_short", "need_validation", "next_review",
    "sequence", "source_origin", "task_properties", "reject_reason", "rejected",
    "rejected_message", "review_ids", "reviewer_ids", "to_validate_message",
    "validated", "validated_message", "validation_status",
}
BUSINESS_FORM_STRUCTURE_INTERNAL_PREFIXES = (
    "access_", "alias_", "allow_", "dashboard_", "favorite_", "last_update_",
    "privacy_",
)
BUSINESS_FORM_STRUCTURE_INTERNAL_TOKENS = (
    "_delta", "_source", "_source_", "_visible", "legacy_deleted", "legacy_",
    "source_created", "validation",
)
BUSINESS_FORM_STRUCTURE_INTERNAL_SUFFIXES = ("_count", "_rate")
LEGACY_VISIBLE_BUSINESS_COLUMN_LABELS_BY_MODEL = {
    "project.material.plan": {
        "legacy_visible_01": "单据状态",
        "legacy_visible_02": "单据编号",
        "legacy_visible_05": "采购材料名称",
    },
    "sc.material.inbound": {
        "legacy_visible_01": "单据状态",
        "legacy_visible_02": "入库单号",
        "legacy_visible_05": "材料名称",
    },
}
STANDARD_LOWCODE_COLUMN_LABELS = {
    "source_created_by": "录入人",
    "source_created_at": "录入时间",
}

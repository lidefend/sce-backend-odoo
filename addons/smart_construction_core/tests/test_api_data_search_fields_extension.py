# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.smart_construction_core.core_extension import smart_core_api_data_search_fields


@tagged("api_data_search_fields_extension")
class TestApiDataSearchFieldsExtension(TransactionCase):
    def test_tender_guarantee_projection_search_fields_include_remark(self):
        fields = smart_core_api_data_search_fields(self.env, "tender.guarantee")

        self.assertIn("remark", fields)
        self.assertIn("project_id", fields)

    def test_settlement_acceptance_visible_fields_contribute_source_fields(self):
        fields = smart_core_api_data_search_fields(self.env, "sc.settlement.order")

        self.assertIn("settlement_unit_id", fields)
        self.assertIn("source_created_by", fields)

    def test_search_fields_are_driven_by_explicit_contract_not_field_strings(self):
        fields = smart_core_api_data_search_fields(None, "payment.request")

        self.assertIn("accepted_amount_uppercase", fields)
        self.assertIn("amount_uppercase", fields)
        self.assertEqual(
            self.env["payment.request"]._fields["accepted_amount_uppercase"].string,
            "用户确认金额大写",
        )

    def test_customer_history_carrier_does_not_extend_product_search_policy(self):
        fields = smart_core_api_data_search_fields(None, "sc.legacy.direct.acceptance.fact")

        self.assertEqual(fields, [])

    def test_runtime_search_fields_are_existing_model_fields(self):
        for model_name in (
            "payment.request",
            "tender.guarantee",
            "sc.settlement.order",
        ):
            fields = smart_core_api_data_search_fields(self.env, model_name)
            model_fields = self.env[model_name]._fields

            self.assertTrue(fields)
            self.assertFalse([field_name for field_name in fields if field_name not in model_fields])

    def test_contract_formal_labels_are_not_taken_by_projection_fields(self):
        contract_fields = self.env["construction.contract"]._fields
        projection_fields = [
            name
            for name in contract_fields
            if name.startswith("legacy_visible_")
        ]
        reserved_labels = {"单据状态", "单据编号", "项目名称", "合同金额", "录入人", "录入时间", "附件"}
        duplicate_projection_labels = {
            contract_fields[name].string
            for name in projection_fields
            if contract_fields[name].string in reserved_labels
        }

        self.assertFalse(duplicate_projection_labels)

    def test_known_duplicate_model_labels_are_namespaced(self):
        expectations = {
            "project.project": {
                "sc_partner_display_name": "关联单位显示名称",
            },
            "res.partner": {
                "sc_supplier_type_label": "供应商类型汇总",
            },
            "res.users": {
                "sc_supplier_type_label": "供应商类型汇总",
            },
            "sc.material.settlement": {
                "payment_request_ids": "关联付款申请",
            },
            "sc.settlement.order": {
                "settlement_category_display": "结算分类显示",
                "settlement_stage": "结算阶段编码",
                "payment_request_ids": "关联付款申请",
            },
            "payment.request": {
                "accepted_amount_uppercase": "用户确认金额大写",
            },
        }
        for model_name, expected_fields in expectations.items():
            fields = self.env[model_name]._fields
            for field_name, expected_label in expected_fields.items():
                self.assertEqual(fields[field_name].string, expected_label)

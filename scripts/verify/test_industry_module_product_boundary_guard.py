#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import industry_module_product_boundary_guard as guard


class IndustryModuleProductBoundaryGuardTests(unittest.TestCase):
    def _module_root(self, source: str, *, manifest: str = "{}") -> tuple[tempfile.TemporaryDirectory, Path]:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        (module / "models").mkdir(parents=True)
        (module / "__manifest__.py").write_text(manifest, encoding="utf-8")
        (module / "models" / "sample.py").write_text(source, encoding="utf-8")
        return tmp, root / "addons"

    def test_runtime_bare_pass_boundary_rejects_runtime_pass(self):
        tmp, addons = self._module_root(
            "def sample():\n"
            "    try:\n"
            "        return 1\n"
            "    except Exception:\n"
            "        pass\n"
        )
        with tmp, patch.object(guard, "ROOT", addons.parent), patch.object(guard, "ADDONS", addons):
            errors = guard.verify_runtime_bare_pass_boundary()
        self.assertEqual(len(errors), 1)
        self.assertIn("bare pass", errors[0])
        self.assertIn("models/sample.py:5", errors[0])

    def test_runtime_abstract_boundary_rejects_bare_not_implemented(self):
        tmp, addons = self._module_root(
            "class Sample:\n"
            "    def run(self):\n"
            "        raise NotImplementedError\n"
        )
        with tmp, patch.object(guard, "ROOT", addons.parent), patch.object(guard, "ADDONS", addons):
            errors = guard.verify_runtime_abstract_method_boundary()
        self.assertEqual(len(errors), 1)
        self.assertIn("NotImplementedError", errors[0])
        self.assertIn("models/sample.py", errors[0])

    def test_manifest_shape_rejects_demo_key(self):
        tmp, addons = self._module_root("VALUE = 1\n", manifest="{'data': [], 'demo': []}")
        with (
            tmp,
            patch.object(guard, "ROOT", addons.parent),
            patch.object(guard, "ADDONS", addons),
            patch.object(guard, "INDUSTRY_MODULES", ("smart_construction_core",)),
            patch.object(guard, "ALLOWED_UNDECLARED_XML", {}),
        ):
            errors = guard.verify_manifest_shape()
        self.assertEqual(errors, ["smart_construction_core: production manifest must not declare demo data entries"])

    def test_customer_specific_runtime_view_boundary_rejects_loaded_user_confirmation_section(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        (module / "views").mkdir(parents=True)
        (module / "__manifest__.py").write_text(
            "{'data': ['views/customer_form.xml']}",
            encoding="utf-8",
        )
        (module / "views" / "customer_form.xml").write_text(
            '<odoo><group string="用户确认数据"/></odoo>',
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ROOT", root), patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_customer_specific_runtime_view_boundary()
        self.assertEqual(len(errors), 1)
        self.assertIn("customer-specific runtime view token", errors[0])

    def test_material_plan_customer_field_boundary_rejects_legacy_model_extension(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        view_dir = module / "views" / "support"
        migration_dir = module / "migrations" / "17.0.0.113"
        model_dir.mkdir(parents=True)
        view_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            'class Legacy:\n    _inherit = "project.material.plan"\n',
            encoding="utf-8",
        )
        (view_dir / "user_confirmed_formal_list_views.xml").write_text(
            '<odoo><field name="state"/><field name="name"/><field name="date_plan"/>'
            '<field name="material_name_summary"/><field name="project_id"/>'
            '<field name="material_plan_status_display"/></odoo>',
            encoding="utf-8",
        )
        (migration_dir / "pre-migration.py").write_text(
            "project_material_plan information_schema.columns legacy_visible_%02d "
            "MATERIAL_PLAN_P2_HISTORY_NOT_EXTRACTED raise RuntimeError",
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_material_plan_customer_field_boundary()
        self.assertTrue(any("must not register P2" in error for error in errors))
        self.assertTrue(any("material_plan_status_display" in error for error in errors))

    def test_material_rfq_customer_field_boundary_rejects_legacy_projection(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        view_dir = module / "views" / "support"
        migration_dir = module / "migrations" / "17.0.0.114"
        model_dir.mkdir(parents=True)
        view_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            'class Legacy:\n    _inherit = "sc.material.rfq"\n',
            encoding="utf-8",
        )
        (view_dir / "user_confirmed_formal_list_views.xml").write_text(
            '<odoo><field name="state"/><field name="name"/>'
            '<field name="selected_supplier_id"/><field name="rfq_date"/>'
            '<field name="project_id"/><field name="owner_id"/>'
            '<field name="quote_status_display"/></odoo>',
            encoding="utf-8",
        )
        (migration_dir / "pre-migration.py").write_text(
            "sc_material_rfq information_schema.columns legacy_visible_%02d "
            "MATERIAL_RFQ_P2_HISTORY_NOT_EXTRACTED raise RuntimeError",
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_material_rfq_customer_field_boundary()
        self.assertTrue(any("must not register P2" in error for error in errors))
        self.assertTrue(any("quote_status_display" in error for error in errors))

    def test_material_inbound_customer_field_boundary_rejects_legacy_extension(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        view_dir = module / "views" / "support"
        migration_dir = module / "migrations" / "17.0.0.115"
        model_dir.mkdir(parents=True)
        view_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            '_inherit = "sc.material.inbound"', encoding="utf-8"
        )
        (view_dir / "user_confirmed_formal_list_views.xml").write_text(
            '<field name="document_status"/><field name="name"/><field name="inbound_date"/>'
            '<field name="supplier_id"/><field name="material_name_summary"/>'
            '<field name="project_name_display"/>'
            "<field name=\"domain\">[('legacy_acceptance_label', '=', '入库')]</field>",
            encoding="utf-8",
        )
        (migration_dir / "pre-migration.py").write_text(
            "sc_material_inbound information_schema.columns legacy_visible_%02d "
            "MATERIAL_INBOUND_P2_HISTORY_NOT_EXTRACTED raise RuntimeError", encoding="utf-8"
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_material_inbound_customer_field_boundary()
        self.assertTrue(any("must not register P2" in error for error in errors))
        self.assertTrue(any("must not filter on removed P2 label" in error for error in errors))

    def test_pass_through_customer_field_boundary_rejects_legacy_extension(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        migration_dir = module / "migrations" / "17.0.0.116"
        model_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            '_inherit = "sc.receipt.income"', encoding="utf-8"
        )
        (migration_dir / "pre-migration.py").write_text(
            "sc_fund_account_operation sc_receipt_income sc_invoice_registration "
            "construction_contract_expense PASS_THROUGH_P2_HISTORY_NOT_EXTRACTED raise RuntimeError",
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_pass_through_customer_field_boundary()
        self.assertTrue(any("sc.receipt.income" in error for error in errors))

    def test_subcontract_request_customer_field_boundary_rejects_legacy_extension(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        core_model_dir = module / "models" / "core"
        view_dir = module / "views" / "support"
        migration_dir = module / "migrations" / "17.0.0.117"
        model_dir.mkdir(parents=True)
        core_model_dir.mkdir(parents=True)
        view_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            '_inherit = "sc.subcontract.request"', encoding="utf-8"
        )
        (core_model_dir / "formal_config_contract_fields.py").write_text(
            "class SubcontractRequestFormalConfigContractFields: pass", encoding="utf-8"
        )
        (view_dir / "user_confirmed_formal_list_views.xml").write_text(
            '<field name="state"/><field name="name"/><field name="project_id"/>'
            '<field name="subcontract_scope"/><field name="amount_total"/><field name="attachment_ids"/>',
            encoding="utf-8",
        )
        (migration_dir / "pre-migration.py").write_text(
            "sc_subcontract_request information_schema.columns legacy_visible_%02d "
            "SUBCONTRACT_REQUEST_P2_HISTORY_NOT_EXTRACTED raise RuntimeError",
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_subcontract_request_customer_field_boundary()
        self.assertTrue(any("must not register P2" in error for error in errors))
        self.assertTrue(any("without display aliases" in error for error in errors))

    def test_construction_diary_customer_field_boundary_rejects_legacy_extension(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        core_model_dir = module / "models" / "core"
        migration_dir = module / "migrations" / "17.0.0.118"
        model_dir.mkdir(parents=True)
        core_model_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            '_inherit = "sc.construction.diary"', encoding="utf-8"
        )
        (core_model_dir / "formal_config_contract_fields.py").write_text(
            "class ConstructionDiaryFormalConfigContractFields: pass", encoding="utf-8"
        )
        (migration_dir / "pre-migration.py").write_text(
            "sc_construction_diary legacy_visible_%02d "
            "CONSTRUCTION_DIARY_P2_HISTORY_NOT_EXTRACTED raise RuntimeError",
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_construction_diary_customer_field_boundary()
        self.assertTrue(any("must not register P2" in error for error in errors))
        self.assertTrue(any("without display aliases" in error for error in errors))

    def test_settlement_order_customer_field_boundary_rejects_legacy_extension(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        view_dir = module / "views" / "support"
        migration_dir = module / "migrations" / "17.0.0.119"
        model_dir.mkdir(parents=True)
        view_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            '_inherit = "sc.settlement.order"', encoding="utf-8"
        )
        (view_dir / "user_confirmed_formal_list_views.xml").write_text(
            ''.join(f'<field name="{name}"/>' for name in (
                "state", "name", "project_id", "settlement_amount", "paid_amount", "unpaid_amount", "attachment_ids"
            )), encoding="utf-8"
        )
        (migration_dir / "pre-migration.py").write_text(
            "sc_settlement_order legacy_visible_%02d SETTLEMENT_ORDER_P2_HISTORY_NOT_EXTRACTED raise RuntimeError",
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_settlement_order_customer_field_boundary()
        self.assertTrue(any("must not register P2" in error for error in errors))

    def test_equipment_usage_customer_field_boundary_rejects_legacy_extension(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        core_model_dir = module / "models" / "core"
        migration_dir = module / "migrations" / "17.0.0.120"
        model_dir.mkdir(parents=True)
        core_model_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            '_inherit = "sc.equipment.usage"', encoding="utf-8"
        )
        (core_model_dir / "equipment_management.py").write_text(
            "specification uom_text currency_id price_unit amount", encoding="utf-8"
        )
        (migration_dir / "pre-migration.py").write_text(
            "sc_equipment_usage legacy_visible_%02d EQUIPMENT_USAGE_P2_HISTORY_NOT_EXTRACTED raise RuntimeError",
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_equipment_usage_customer_field_boundary()
        self.assertTrue(any("must not register P2" in error for error in errors))

    def test_labor_usage_customer_field_boundary_rejects_legacy_extension(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        core_model_dir = module / "models" / "core"
        migration_dir = module / "migrations" / "17.0.0.121"
        model_dir.mkdir(parents=True)
        core_model_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text('_inherit = "sc.labor.usage"', encoding="utf-8")
        (core_model_dir / "labor_management.py").write_text("usage_type work_type construction_part price_unit amount_total settlement_state", encoding="utf-8")
        (migration_dir / "pre-migration.py").write_text("sc_labor_usage legacy_visible_%02d LABOR_USAGE_P2_HISTORY_NOT_EXTRACTED raise RuntimeError", encoding="utf-8")
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_labor_usage_customer_field_boundary()
        self.assertTrue(any("must not register P2" in error for error in errors))

    def test_material_rental_order_customer_field_boundary_rejects_legacy_extension(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        core_model_dir = module / "models" / "core"
        migration_dir = module / "migrations" / "17.0.0.122"
        model_dir.mkdir(parents=True)
        core_model_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            '_inherit = "sc.material.rental.order"', encoding="utf-8"
        )
        (core_model_dir / "material_rental.py").write_text(
            "actual_return_date use_unit_name deposit_amount settlement_amount compensation_fee "
            "repair_fee transport_fee deposit_deduction material_summary specification_summary "
            "quantity_total attachment_ids",
            encoding="utf-8",
        )
        (migration_dir / "pre-migration.py").write_text(
            "sc_material_rental_order legacy_visible_%02d "
            "MATERIAL_RENTAL_ORDER_P2_HISTORY_NOT_EXTRACTED raise RuntimeError",
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_material_rental_order_customer_field_boundary()
        self.assertTrue(any("must not register P2" in error for error in errors))

    def test_hr_payroll_document_customer_field_boundary_rejects_obsolete_module(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "addons" / "smart_construction_core"
        model_dir = module / "models" / "support"
        core_model_dir = module / "models" / "core"
        migration_dir = module / "migrations" / "17.0.0.123"
        model_dir.mkdir(parents=True)
        core_model_dir.mkdir(parents=True)
        migration_dir.mkdir(parents=True)
        (module / "models" / "__init__.py").write_text(
            "from .support import direct_acceptance_formal_visible_fields", encoding="utf-8"
        )
        (model_dir / "direct_acceptance_formal_visible_fields.py").write_text(
            '_inherit = "sc.hr.payroll.document"', encoding="utf-8"
        )
        (core_model_dir / "hr_payroll_document.py").write_text(
            "gross_amount net_salary payment_state paid_amount unpaid_amount attachment_ids", encoding="utf-8"
        )
        (migration_dir / "pre-migration.py").write_text(
            "sc_hr_payroll_document legacy_visible_%02d "
            "HR_PAYROLL_DOCUMENT_P2_HISTORY_NOT_EXTRACTED raise RuntimeError",
            encoding="utf-8",
        )
        with tmp, patch.object(guard, "ADDONS", root / "addons"):
            errors = guard.verify_hr_payroll_document_customer_field_boundary()
        self.assertTrue(any("obsolete direct acceptance" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""
smart_core tests package

Keep package import side effects minimal so isolated pure-Python unittest
modules can be executed without a live Odoo runtime. Odoo transaction-style
tests remain discoverable by explicit module import in Odoo test execution.
"""

from . import test_permission_contract_runtime_uid
from . import test_native_action_selection_alignment
from . import test_action_dispatcher_server_mapping
from . import test_menu_delivery_convergence_service
from . import test_odoo_native_alignment_boundaries
from . import test_release_gate_category_options
from . import test_usage_backend
from . import test_business_config_change_set
from . import test_runtime_view_contract_fail_closed
from . import test_admin_vis_p3_project_record_rule_orm
from . import test_chatter_timeline_authorization_orm
from . import test_um_p1_ownership_visibility_contract_orm
from . import test_um_p1_payment_visibility_contract_orm
from . import test_um_p1_invoice_deduction_visibility_contract_orm
from . import test_um_p1_interfund_financing_visibility_contract_orm
from . import test_um_p1_contract_settlement_visibility_contract_orm
from . import test_um_p1_cost_ledger_visibility_contract_orm
from . import test_um_p2_receipt_relation_aggregation_orm
from . import test_um_p2_payment_relation_aggregation_orm
from . import test_um_p2_interfund_relation_aggregation_orm
from . import test_um_p2_invoice_relation_aggregation_orm
from . import test_um_p2_settlement_relation_aggregation_orm
from . import test_um_p3_fund_plan_actual_event_allocation_orm
from . import test_um_p3_material_settlement_purchase_authority_orm
from . import test_um_p3_subcontract_register_settlement_authority_orm
from . import test_um_p3_subcontract_cumulative_settlement_orm
from . import test_um_p3_payment_ledger_request_permission_orm
from . import test_um_p3_subcontract_cumulative_amount_orm
from . import test_tenant_extension_storage
from . import test_narrow_tenant_payload_importer
from . import test_localized_display
from . import test_user_activation
from . import test_authentication_compatibility

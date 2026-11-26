# -*- coding: utf-8 -*-
"""
smart_core tests package

Keep package import side effects minimal so isolated pure-Python unittest
modules can be executed without a live Odoo runtime. Odoo transaction-style
tests remain discoverable by explicit module import in Odoo test execution.
"""

from . import test_native_action_selection_alignment
from . import test_action_dispatcher_server_mapping
from . import test_native_action_view_set_integration
from . import test_native_action_search_view_integration
from . import test_native_action_contract_integration
from . import test_native_occurrence_contract_integration
from . import test_menu_delivery_convergence_service
from . import test_odoo_native_alignment_boundaries
from . import test_native_tree_presentation_semantic
from . import test_release_gate_category_options
from . import test_usage_backend
from . import test_business_config_change_set
from . import test_lowcode_config_contract_write_authority
from . import test_runtime_view_contract_fail_closed
from . import test_tenant_extension_storage
from . import test_narrow_tenant_payload_importer
from . import test_localized_display
from . import test_api_data_mutation_failure_atomicity_orm
from . import test_user_activation
from . import test_authentication_compatibility
from . import test_auth_credential_framework
from . import test_intent_smoke
from . import test_scene_runtime_contract_chain
from . import test_scene_nav_contract_builder
from . import test_canonical_navigation_projection
from . import test_user_view_preference_runtime_orm
from . import test_res_users_audience_group_boundary
from . import test_intent_permission_menu_visibility
from . import test_smart_core_model_init_table_recovery
from . import test_data_space_boundary
from . import test_data_space_identity_enrollment
from . import test_data_space_uncached_membership
from . import test_platform_database_governance_orm
from . import test_principal_group_signature_request_scope_orm
from . import test_tenant_payload_operator_lifecycle
from . import test_platform_maintenance_access_http
from . import test_contract_assembly_determinism
from . import test_submission_readiness_notice_suppression
from . import test_extension_runtime_context
from . import test_extension_registry_lifecycle
from . import test_workflow_contract_platform
from . import test_platform_multi_company

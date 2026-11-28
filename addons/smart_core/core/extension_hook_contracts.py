# -*- coding: utf-8 -*-
"""Explicit invocation contracts for smart_core extension hooks."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HookContract:
    mode: str
    providers: tuple[str, ...] = ()
    final_providers: tuple[str, ...] = ()
    merge: str = ""
    allow_undeclared: bool = False


SINGLE_OWNER_HOOKS = frozenset({
    "smart_core_add_catalog_entry_to_product_policy",
    "smart_core_api_data_create_execution_policy",
    "smart_core_api_data_mutation_policy",
    "smart_core_api_data_search_fields",
    "smart_core_api_data_unlink_allowed_models",
    "smart_core_api_data_write_allowlist",
    "smart_core_app_shell_contract",
    "smart_core_authorize_work_item_origin",
    "smart_core_build_default_product_policy",
    "smart_core_build_cost_tracking_service",
    "smart_core_build_payment_slice_service",
    "smart_core_build_project_dashboard_service",
    "smart_core_build_project_execution_service",
    "smart_core_build_project_plan_bootstrap_service",
    "smart_core_build_settlement_slice_service",
    "smart_core_business_category_policy_bindings",
    "smart_core_business_config_admin_group_xmlids",
    "smart_core_business_config_approval_policy_refs",
    "smart_core_business_config_approval_targets",
    "smart_core_business_config_form_settings_refs",
    "smart_core_business_list_default_visibility",
    "smart_core_business_nav_group_display_order",
    "smart_core_business_root_menu_xmlid",
    "smart_core_business_scenario_maintenance",
    "smart_core_capability_groups",
    "smart_core_create_default_skip_fields",
    "smart_core_create_field_fallbacks",
    "smart_core_default_product_policy_specs",
    "smart_core_default_release_snapshot_role_code",
    "smart_core_delivery_scene_declarations",
    "smart_core_file_download_allowed_models",
    "smart_core_file_download_auth_subject",
    "smart_core_file_upload_allowed_models",
    "smart_core_finalize_projected_contract_data",
    "smart_core_finalize_unified_page_contract_v2",
    "smart_core_form_business_actions",
    "smart_core_form_field_aliases",
    "smart_core_form_structure_surface_policy",
    "smart_core_get_scene_version",
    "smart_core_get_schema_version",
    "smart_core_has_db_scenes",
    "smart_core_identity_profile",
    "smart_core_industry_extension_module_names",
    "smart_core_intent_permission_model_acl_policy",
    "smart_core_legacy_visible_business_column_labels",
    "smart_core_list_capabilities_for_user",
    "smart_core_list_capabilities_for_user_with_timings",
    "smart_core_load_scene_configs",
    "smart_core_lowcode_config_recovery_parent_menu_xmlids",
    "smart_core_menu_config_recovery_menu_xmlids",
    "smart_core_lowcode_system_config_menu_xmlids",
    "smart_core_menu_config_only_exempt_group_xmlids",
    "smart_core_menu_delivery_token_policy",
    "smart_core_model_code_mapping",
    "smart_core_model_specific_form_contract_policy",
    "smart_core_native_config_delivery_excluded_menu_xmlids",
    "smart_core_native_config_action_entry_target",
    "smart_core_native_config_root_menu_xmlid",
    "smart_core_native_view_widget_payload",
    "smart_core_navigation_authority_filter",
    "smart_core_normalize_product_policy",
    "smart_core_normalize_projected_contract_data",
    "smart_core_normalize_unified_page_contract_v2",
    "smart_core_platform_legacy_ownership_module",
    "smart_core_product_policy_catalog_base_keys",
    "smart_core_product_policy_catalog_label",
    "smart_core_product_policy_catalog_source",
    "smart_core_product_scene_composition",
    "smart_core_relation_entry_policy",
    "smart_core_resolve_record_context_config",
    "smart_core_resolve_release_actor_role_codes",
    "smart_core_resolve_startup_delivery_identity",
    "smart_core_resolve_usage_actor_role_codes",
    "smart_core_runtime_business_config_productization_sources",
    "smart_core_scenario_surface_projection",
    "smart_core_scene_entry_orchestrator_specs",
    "smart_core_scene_governance_service_class",
    "smart_core_scene_package_service_class",
    "smart_core_server_action_window_map",
    "smart_core_surface_aliases",
    "smart_core_surface_deep_link_allowlist",
    "smart_core_surface_nav_allowlist",
    "smart_core_surface_policy_default_name",
    "smart_core_surface_policy_file_default",
    "smart_core_surface_unregistered_bypass",
    "smart_core_user_data_acceptance_nav_contract",
    "smart_core_workflow_contract_profiles",
    "smart_core_workflow_contract_evidence",
    "smart_core_workflow_approval_required",
})


ORDERED_MERGE_HOOKS = {
    "smart_core_critical_scene_target_overrides": HookContract(
        mode="ordered_merge",
        providers=(
            "smart_construction_core",
            "smart_construction_scene",
        ),
        merge="set_union",
    ),
    "smart_core_critical_scene_target_route_overrides": HookContract(
        mode="ordered_merge",
        providers=(
            "smart_construction_core",
            "smart_construction_scene",
        ),
        merge="dict_update",
    ),
    "smart_core_nav_scene_maps": HookContract(
        mode="ordered_merge",
        providers=(
            "smart_construction_core",
            "smart_construction_scene",
        ),
        merge="deep_dict",
    ),
}


RUN_ALL_HOOKS = {
    "get_intent_handler_contributions": HookContract(
        mode="run_all",
        providers=(
            "smart_construction_core", "smart_construction_scene", "smart_owner_core",
            "smart_construction_bundle", "smart_owner_bundle", "smart_license_core",
        ),
        allow_undeclared=True,
    ),
    "get_system_init_fact_contributions": HookContract(
        mode="run_all",
        providers=("smart_construction_core", "smart_construction_bundle", "smart_license_core"),
        final_providers=("smart_license_core",),
        allow_undeclared=True,
    ),
    # Domain contributions precede product overlays; licensing filters the final
    # capability set. This order is independent of installation/config ordering.
    "smart_core_extend_system_init": HookContract(
        mode="run_all",
        providers=(
            "smart_construction_core",
            "smart_construction_scene",
            "smart_owner_core",
            "smart_construction_bundle",
            "smart_owner_bundle",
            "smart_license_core",
        ),
        final_providers=("smart_license_core",),
        allow_undeclared=True,
    ),
    # Registration is order independent: _build_handlers rejects replacements
    # and removals, and accepts repeated registration only of the same class.
    "smart_core_register": HookContract(mode="run_all"),
}


def contract_for(hook_name: str) -> HookContract:
    if hook_name in SINGLE_OWNER_HOOKS:
        return HookContract(mode="single_owner")
    contract = ORDERED_MERGE_HOOKS.get(hook_name)
    if contract is not None:
        return contract
    run_all_contract = RUN_ALL_HOOKS.get(hook_name)
    if run_all_contract is not None:
        return run_all_contract
    raise KeyError(hook_name)


def registered_hook_names() -> frozenset[str]:
    return frozenset(SINGLE_OWNER_HOOKS) | frozenset(ORDERED_MERGE_HOOKS) | frozenset(RUN_ALL_HOOKS)

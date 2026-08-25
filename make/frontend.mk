# ======================================================
# ==================== Frontend ========================
# ======================================================
include make/frontend_professional_extensions.mk

.PHONY: fe.install fe.dev fe.gate verify.frontend.build prod.frontend.build verify.frontend.typecheck.strict verify.frontend.lint.src verify.frontend.page_width_contract.guard verify.frontend.quick.gate verify.frontend.contract_header_action.unit verify.frontend.relation_entry.contract_guard verify.frontend.relation_read_closure.guard verify.frontend.modifiers_runtime.guard verify.frontend.onchange_roundtrip.guard verify.frontend.onchange_contract_schema.guard verify.frontend.onchange_line_patch.guard verify.frontend.x2many_command_semantic.guard verify.frontend.x2many_inline_edit.guard verify.contract.subviews.guard verify.frontend.view_type_render_coverage.guard verify.frontend.view_type_contract_semantic.guard verify.frontend.search_groupby_savedfilters.guard verify.frontend.group_summary_runtime.guard verify.frontend.grouped_rows_runtime.guard verify.frontend.grouped_pagination_semantic.guard verify.frontend.grouped_pagination_semantic_drift.guard verify.contract.operation_gateway.guard verify.frontend.suggested_action.contract_guard verify.frontend.suggested_action.catalog verify.frontend.suggested_action.parser_guard verify.frontend.suggested_action.runtime_guard verify.frontend.suggested_action.import_boundary_guard verify.frontend.suggested_action.usage_guard verify.frontend.suggested_action.trace_export_guard verify.frontend.suggested_action.topk_guard verify.frontend.suggested_action.since_filter_guard verify.frontend.suggested_action.hud_export_guard verify.frontend.cross_stack_smoke verify.frontend.no_new_any_guard verify.frontend.suggested_action.all verify.portal.scene_observability.structure_guard verify.portal.scene_observability.structure_guard.update
.PHONY: fe.install.cached confirm.frontend.release.audit verify.frontend.release.local verify.frontend.ui5_scene_spike verify.frontend.scene_component_drivers verify.frontend.scene_component_bridge.unit verify.frontend.scene_component_bridge.guard verify.frontend.scene_component_bridge.browser verify.frontend.primitive_adapter.unit

fe.install:
	@scripts/dev/pnpm_exec.sh -C frontend install

fe.install.cached: guard.prod.forbid
	@bash scripts/dev/frontend_cached_dependencies_restore.sh

confirm.frontend.release.audit: guard.prod.forbid
	@test "$(CONFIRM_FRONTEND_RELEASE_AUDIT)" = "RUN_FROZEN_FRONTEND_RELEASE_AUDIT" || { \
	  echo "[frontend.release.lane] DENY formal release audit is not a daily-development target" >&2; \
	  echo "[frontend.release.lane] use local.dev.* and targeted verification until final acceptance is explicitly opened" >&2; \
	  exit 2; \
	}

verify.frontend.release.local: guard.prod.forbid confirm.frontend.release.audit
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh release-preflight
	@$(MAKE) --no-print-directory fe.install.cached
	@SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" bash scripts/dev/frontend_acceptance_operation_entry.sh release-audit

fe.dev:
	@scripts/dev/pnpm_exec.sh -C frontend dev

fe.dev.reset: guard.prod.forbid
	@bash scripts/dev/frontend_dev_reset.sh

fe.dev.daily: guard.prod.forbid
	@FRONTEND_PROFILE=daily bash scripts/dev/frontend_dev_reset.sh

fe.dev.test: guard.prod.forbid
	@FRONTEND_PROFILE=test bash scripts/dev/frontend_dev_reset.sh

fe.dev.uat: guard.prod.forbid
	@FRONTEND_PROFILE=uat bash scripts/dev/frontend_dev_reset.sh

fe.gate:
	@scripts/dev/pnpm_exec.sh -C frontend gate

verify.frontend.build: guard.prod.forbid
	@ENV="$(ENV)" ENV_FILE="$(ENV_FILE)" ROOT_DIR="$(ROOT_DIR)" \
	  bash scripts/dev/frontend_static_build.sh

prod.frontend.build: guard.prod.danger check-compose-project check-compose-env
	@bash scripts/dev/frontend_static_build.sh

verify.frontend.typecheck.strict: guard.prod.forbid
	@scripts/dev/pnpm_exec.sh -C frontend/apps/web typecheck:strict

verify.frontend.scene_component_drivers: guard.prod.forbid
	@python3 scripts/verify/frontend_ui5_scene_spike_guard.py
	@$(MAKE) --no-print-directory verify.frontend.scene_component_bridge.unit
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/scene-ui5-spike/scripts/normalizedCollectionAdapter.test.ts --bundle --platform=node --format=esm --outfile=/tmp/normalized-collection-adapter-test.mjs >/dev/null
	@node /tmp/normalized-collection-adapter-test.mjs
	@VITE_FEATURE_FLAGS=scene_collection_pilot scripts/dev/pnpm_exec.sh -C frontend/apps/scene-ui5-spike build
	@bash scripts/verify/frontend_ui5_scene_spike_browser.sh

verify.frontend.ui5_scene_spike: verify.frontend.scene_component_drivers

verify.frontend.scene_component_bridge.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/scene_component_driver_bridge_test.ts --bundle --platform=node --format=esm --outfile=/tmp/scene-component-driver-bridge-test.mjs >/dev/null
	@node /tmp/scene-component-driver-bridge-test.mjs
	@$(MAKE) --no-print-directory verify.frontend.canonical_form_presenter.unit
	@python3 addons/smart_core/tests/test_user_view_preference_boundaries.py
	@python3 addons/smart_core/tests/test_scene_component_driver_feature_flags.py

verify.frontend.scene_component_bridge.guard: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_scene_audit_disclosure_guard
	@python3 -m unittest scripts.verify.test_contract_form_semantic_identity_guard
	@python3 scripts/verify/frontend_scene_component_bridge_guard.py

verify.frontend.scene_component_bridge.browser: guard.prod.forbid check-compose-project check-compose-env
	@set -eu; \
	password="$$(python3 -c 'import secrets; print(secrets.token_hex(24))')"; export SC_ACCEPTANCE_FIXTURE_PASSWORD="$$password"; \
	$(MAKE) --no-print-directory db.frontend.acceptance.ensure DB_NAME=sc_frontend_acceptance; \
	$(MAKE) --no-print-directory frontend.acceptance.release.build DB_NAME=sc_frontend_acceptance; \
	cleanup() { \
	  $(MAKE) --no-print-directory frontend.acceptance.down DB_NAME=sc_frontend_acceptance || true; \
	  $(MAKE) --no-print-directory backend.acceptance.down DB_NAME=sc_frontend_acceptance || true; \
	  SC_ACCEPTANCE_COMPONENT_DRIVER_PROBE_MODE=cleanup $(MAKE) --no-print-directory acceptance.frontend.fixture DB_NAME=sc_frontend_acceptance || true; \
	}; \
	trap cleanup EXIT; \
	target_output="$$(SC_ACCEPTANCE_COMPONENT_DRIVER_PROBE_MODE=setup $(MAKE) --no-print-directory acceptance.frontend.fixture DB_NAME=sc_frontend_acceptance)"; \
	targets_json="$$(printf '%s\n' "$$target_output" | sed -n 's/^SCENE_COMPONENT_DRIVER_TARGETS_JSON=//p' | tail -n 1)"; \
	test -n "$$targets_json" || { printf '%s\n' "$$target_output"; exit 2; }; \
	$(MAKE) --no-print-directory backend.acceptance.up DB_NAME=sc_frontend_acceptance; \
	FRONTEND_ACCEPTANCE_MODE=production FRONTEND_ACCEPTANCE_STATIC_DIST="$$(pwd)/frontend/apps/web/dist-release" $(MAKE) --no-print-directory frontend.acceptance.up DB_NAME=sc_frontend_acceptance; \
	SCENE_COMPONENT_DRIVER_TARGETS_JSON="$$targets_json" DB_NAME=sc_frontend_acceptance FRONTEND_URL=http://127.0.0.1:5175 ODOO_URL=http://127.0.0.1:18082 GIT_SHA="$$(git rev-parse HEAD)" \
	  node scripts/verify/frontend_scene_component_driver_readonly_browser.mjs

verify.frontend.primitive_adapter.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/primitive_adapter_contract_test.ts --bundle --platform=node --format=esm --outfile=/tmp/primitive-adapter-contract-test.mjs >/dev/null
	@node /tmp/primitive-adapter-contract-test.mjs
	@python3 -m unittest scripts.verify.test_frontend_primitive_adapter_guard
	@python3 scripts/verify/frontend_primitive_adapter_guard.py

.PHONY: verify.frontend.navigation_shell.unit
verify.frontend.navigation_shell.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/canonical_navigation_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/canonical-navigation-model-test.mjs >/dev/null
	@node /tmp/canonical-navigation-model-test.mjs
	@python3 addons/smart_core/tests/test_delivery_menu_entry_target.py
	@python3 -m unittest scripts/verify/test_frontend_navigation_shell_guard.py
	@python3 scripts/verify/frontend_navigation_shell_guard.py

.PHONY: verify.frontend.product_page_header.unit verify.frontend.collection_action_toolbar.unit verify.frontend.collection_aggregate_footer.unit verify.frontend.collection_group_header.unit verify.frontend.collection_summary_strip.unit verify.frontend.collection_navigation_controls.unit verify.frontend.collection_row_cell.unit verify.frontend.collection_selection_control.unit
verify.frontend.product_page_header.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/product-page-header-model-test.mjs >/dev/null
	@node /tmp/product-page-header-model-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_product_page_header_guard.py
	@python3 scripts/verify/frontend_product_page_header_guard.py

verify.frontend.collection_action_toolbar.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/collection_action_settlement_test.ts --bundle --platform=node --format=esm --outfile=/tmp/collection-action-settlement-test.mjs >/dev/null
	@node /tmp/collection-action-settlement-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_collection_action_toolbar_guard.py
	@python3 scripts/verify/frontend_collection_action_toolbar_guard.py

verify.frontend.collection_aggregate_footer.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/collection_aggregate_presentation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/collection-aggregate-presentation-test.mjs >/dev/null
	@node /tmp/collection-aggregate-presentation-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_collection_aggregate_footer_guard.py
	@python3 scripts/verify/frontend_collection_aggregate_footer_guard.py

verify.frontend.collection_group_header.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_collection_group_header_guard.py
	@python3 scripts/verify/frontend_collection_group_header_guard.py

verify.frontend.collection_summary_strip.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/collection_summary_presentation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/collection-summary-presentation-test.mjs >/dev/null
	@node /tmp/collection-summary-presentation-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_collection_summary_strip_guard.py
	@python3 scripts/verify/frontend_collection_summary_strip_guard.py

verify.frontend.collection_navigation_controls.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/collection_pagination_presentation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/collection-pagination-presentation-test.mjs >/dev/null
	@node /tmp/collection-pagination-presentation-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_collection_navigation_controls_guard.py
	@python3 scripts/verify/frontend_collection_navigation_controls_guard.py

verify.frontend.collection_row_cell.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_collection_row_cell_guard.py
	@python3 scripts/verify/frontend_collection_row_cell_guard.py

verify.frontend.collection_selection_control.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/collection_selection_presentation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/collection-selection-presentation-test.mjs >/dev/null
	@node /tmp/collection-selection-presentation-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_collection_selection_control_guard.py
	@python3 scripts/verify/frontend_collection_selection_control_guard.py

.PHONY: verify.frontend.product_page_header.browser
verify.frontend.product_page_header.browser: guard.prod.forbid
	@node scripts/verify/frontend_product_page_header_browser.mjs

.PHONY: verify.frontend.product_page_pattern.unit verify.frontend.professional_component_registry.unit verify.frontend.professional_base_field.unit
verify.frontend.product_page_pattern.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_pattern_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/product-page-pattern-model-test.mjs >/dev/null
	@node /tmp/product-page-pattern-model-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_product_page_pattern_guard.py
	@python3 scripts/verify/frontend_product_page_pattern_guard.py

verify.frontend.professional_component_registry.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_component_registry_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-component-registry-test.mjs >/dev/null
	@node /tmp/professional-component-registry-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_professional_component_registry_guard.py
	@python3 scripts/verify/frontend_professional_component_registry_guard.py

verify.frontend.professional_base_field.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_base_field_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-base-field-model-test.mjs >/dev/null
	@node /tmp/professional-base-field-model-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_professional_base_field_guard.py
	@python3 scripts/verify/frontend_professional_base_field_guard.py

.PHONY: verify.frontend.professional_business_value.unit
verify.frontend.professional_business_value.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_business_value_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-business-value-model-test.mjs >/dev/null
	@node /tmp/professional-business-value-model-test.mjs
	@python3 addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py
	@python3 -m unittest scripts/verify/test_frontend_professional_business_value_guard.py
	@python3 scripts/verify/frontend_professional_business_value_guard.py

.PHONY: verify.frontend.professional_relation_field.unit
verify.frontend.professional_relation_field.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_relation_field_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-relation-field-model-test.mjs >/dev/null
	@node /tmp/professional-relation-field-model-test.mjs
	@python3 addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py
	@python3 -m unittest scripts/verify/test_frontend_professional_relation_field_guard.py
	@python3 scripts/verify/frontend_professional_relation_field_guard.py

.PHONY: verify.frontend.professional_detail_collection.unit
verify.frontend.professional_detail_collection.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_detail_collection_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-detail-collection-model-test.mjs >/dev/null
	@node /tmp/professional-detail-collection-model-test.mjs
	@python3 addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py
	@python3 -m unittest scripts/verify/test_frontend_professional_detail_collection_guard.py
	@python3 scripts/verify/frontend_professional_detail_collection_guard.py

.PHONY: verify.frontend.professional_workflow.unit
verify.frontend.professional_workflow.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_workflow_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-workflow-model-test.mjs >/dev/null
	@node /tmp/professional-workflow-model-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_professional_workflow_guard.py
	@python3 scripts/verify/frontend_professional_workflow_guard.py

.PHONY: verify.frontend.professional_audit.unit
verify.frontend.professional_audit.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_audit_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-audit-model-test.mjs >/dev/null
	@node /tmp/professional-audit-model-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_professional_audit_guard.py
	@python3 scripts/verify/frontend_professional_audit_guard.py

.PHONY: verify.frontend.professional_collaboration.unit
verify.frontend.professional_collaboration.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_collaboration_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-collaboration-model-test.mjs >/dev/null
	@node /tmp/professional-collaboration-model-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_professional_collaboration_guard.py
	@python3 scripts/verify/frontend_professional_collaboration_guard.py

.PHONY: verify.frontend.professional_relation_lifecycle.unit
verify.frontend.professional_relation_lifecycle.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_relation_lifecycle_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-relation-lifecycle-model-test.mjs >/dev/null
	@node /tmp/professional-relation-lifecycle-model-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_professional_relation_lifecycle_guard.py
	@python3 scripts/verify/frontend_professional_relation_lifecycle_guard.py

.PHONY: verify.frontend.hierarchical_worksheet.unit
verify.frontend.hierarchical_worksheet.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/hierarchical_worksheet_interaction_test.ts --bundle --platform=node --format=esm --outfile=/tmp/hierarchical-worksheet-interaction-test.mjs >/dev/null
	@node /tmp/hierarchical-worksheet-interaction-test.mjs

verify.frontend.quick.gate: verify.frontend.scene_component_bridge.unit verify.frontend.scene_component_bridge.guard verify.frontend.scene_contract.consumption.guard verify.frontend.primitive_adapter.unit verify.frontend.navigation_shell.unit verify.frontend.product_page_header.unit verify.frontend.collection_action_toolbar.unit verify.frontend.collection_aggregate_footer.unit verify.frontend.collection_group_header.unit verify.frontend.collection_summary_strip.unit verify.frontend.collection_navigation_controls.unit verify.frontend.collection_row_cell.unit verify.frontend.collection_selection_control.unit verify.frontend.product_page_pattern.unit verify.frontend.professional_component_registry.unit verify.frontend.professional_base_field.unit verify.frontend.professional_business_value.unit verify.frontend.professional_relation_field.unit verify.frontend.professional_detail_collection.unit verify.frontend.professional_workflow.unit verify.frontend.professional_audit.unit verify.frontend.professional_collaboration.unit verify.frontend.professional_relation_lifecycle.unit verify.frontend.hierarchical_worksheet.unit verify.frontend.professional.extensions.unit

verify.frontend.release.unit: verify.frontend.scene_component_bridge.unit verify.frontend.scene_component_bridge.guard verify.frontend.primitive_adapter.unit verify.frontend.navigation_shell.unit verify.frontend.product_page_header.unit verify.frontend.product_page_pattern.unit verify.frontend.professional_component_registry.unit verify.frontend.professional_base_field.unit verify.frontend.professional_business_value.unit verify.frontend.professional_relation_field.unit verify.frontend.professional_detail_collection.unit verify.frontend.professional_workflow.unit verify.frontend.professional_audit.unit verify.frontend.professional_collaboration.unit verify.frontend.professional_relation_lifecycle.unit verify.frontend.professional.extensions.unit

verify.frontend.lint.src: guard.prod.forbid
	@scripts/dev/pnpm_exec.sh -C frontend/apps/web lint:src

.PHONY: verify.frontend.page_width_contract.guard verify.frontend.workspace_content_alignment.guard verify.frontend.workspace_layout_contract.unit verify.frontend.form_canvas_layout.guard verify.frontend.form_canvas_layout.unit verify.frontend.form_grid_span.browser verify.frontend.localized_display.unit verify.frontend.list_optional_columns.unit verify.frontend.collection_view_semantics.unit verify.frontend.action_surface_renderer_registry.unit verify.frontend.auth_credential.guard verify.frontend.all_list_visual.audit verify.frontend.runtime_environment.unit audit.frontend.industry_agnostic verify.frontend.industry_agnostic.guard

verify.frontend.auth_credential.guard: guard.prod.forbid
	@python3 scripts/verify/auth_credential_frontend_guard.py
	@node scripts/verify/frontend_evidence_capture_guard.test.mjs

audit.frontend.industry_agnostic: guard.prod.forbid
	@python3 scripts/verify/frontend_industry_agnostic_audit.py

verify.frontend.industry_agnostic.guard: guard.prod.forbid
	@FRONTEND_INDUSTRY_AGNOSTIC_ENFORCE=1 python3 scripts/verify/frontend_industry_agnostic_audit.py

verify.frontend.localized_display.unit: guard.prod.forbid
	@node --experimental-strip-types scripts/verify/frontend_localized_display_contract_test.ts

verify.frontend.list_optional_columns.unit: guard.prod.forbid
	@node --experimental-strip-types scripts/verify/frontend_list_optional_columns_contract_test.ts

verify.frontend.collection_view_semantics.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/record_entry_contract_test.ts --bundle --platform=node --format=esm --outfile=/tmp/record-entry-contract-test.mjs >/dev/null
	@node /tmp/record-entry-contract-test.mjs
	@python3 addons/smart_core/tests/test_navigation_entry_target.py
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/collection_view_semantics_test.ts --bundle --platform=node --format=esm --outfile=/tmp/collection-view-semantics-test.mjs >/dev/null
	@node /tmp/collection-view-semantics-test.mjs
	@python3 addons/smart_core/tests/test_native_view_parser_surfaces.py
	@python3 scripts/verify/collection_view_semantics_guard.py

verify.frontend.action_surface_renderer_registry.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/action_surface_renderer_registry_test.ts --bundle --platform=node --format=esm --outfile=/tmp/action-surface-renderer-registry-test.mjs >/dev/null
	@node /tmp/action-surface-renderer-registry-test.mjs
	@python3 scripts/verify/action_surface_renderer_architecture_guard.py

verify.frontend.all_list_visual.audit: guard.prod.forbid
	@E2E_PASSWORD="$${E2E_PASSWORD:?E2E_PASSWORD is required}" \
		DB_NAME="$(DB_NAME)" \
		FRONTEND_URL="$${FRONTEND_URL:-http://127.0.0.1:18081}" \
		REQUIRE_ACTIVITY_SURFACE="$${REQUIRE_ACTIVITY_SURFACE:-0}" \
		CONCURRENCY="$${CONCURRENCY:-1}" \
		ARTIFACT_DIR="$${ARTIFACT_DIR:-/tmp/frontend-all-list-visual-audit}" \
		node scripts/verify/frontend_all_list_visual_audit.mjs

verify.frontend.runtime_environment.unit: guard.prod.forbid
	@python3 scripts/verify/test_common_env_explicit_path.py
	@python3 scripts/verify/frontend_dev_process_isolation_guard.py

.PHONY: verify.frontend.detail_form_productization.guard
verify.frontend.detail_form_productization.guard: guard.prod.forbid
	@python3 scripts/verify/frontend_detail_form_productization_guard.py
verify.frontend.workspace_layout_contract.unit: guard.prod.forbid
	@node --experimental-strip-types scripts/verify/frontend_workspace_layout_contract_compatibility_test.ts

verify.frontend.workspace_content_alignment.guard: guard.prod.forbid verify.frontend.workspace_layout_contract.unit verify.frontend.form_canvas_layout.guard
	@python3 scripts/verify/frontend_workspace_content_alignment_guard.py

verify.frontend.page_width_contract.guard: verify.frontend.workspace_content_alignment.guard
	@echo "[verify.frontend.page_width_contract.guard] compatibility alias PASS"

verify.frontend.form_canvas_layout.unit: guard.prod.forbid
	@node --experimental-strip-types scripts/verify/frontend_form_canvas_layout_contract_test.ts

verify.frontend.form_canvas_layout.guard: guard.prod.forbid verify.frontend.form_canvas_layout.unit
	@python3 scripts/verify/frontend_form_canvas_wide_grid_guard.py

verify.frontend.form_grid_span.browser: guard.prod.forbid
	@FE_PRO_04WR3_PHASE=$${FE_PRO_04WR3_PHASE:-final} GIT_SHA=$$(git rev-parse HEAD) FORM_SECTION_BLOB=$$(git hash-object frontend/apps/web/src/components/template/FormSection.vue) node scripts/verify/frontend_form_grid_span_browser.mjs

.PHONY: verify.frontend.page_identity
verify.frontend.page_identity: guard.prod.forbid
	@node scripts/verify/frontend_page_identity_smoke.js
	@node scripts/verify/frontend_page_identity_lifecycle_smoke.js
	@python3 scripts/verify/frontend_page_identity_guard.py

.PHONY: verify.frontend.my_work_approval.guard
verify.frontend.my_work_approval.guard: guard.prod.forbid
	@python3 scripts/verify/frontend_my_work_approval_guard.py

.PHONY: verify.frontend.style_system.guard
verify.frontend.style_system.guard: guard.prod.forbid
	@python3 scripts/verify/frontend_style_system_guard.py

.PHONY: verify.frontend.standard_list_scroll_contract.guard
verify.frontend.standard_list_scroll_contract.guard: guard.prod.forbid
	@python3 scripts/verify/frontend_standard_list_scroll_contract_guard.py

.PHONY: verify.frontend.delivery_hardening.guard verify.frontend.delivery_hardening.inventory verify.frontend.release_navigation_policy.guard
verify.frontend.delivery_hardening.guard: guard.prod.forbid
	@python3 scripts/verify/frontend_delivery_hardening_guard.py

verify.frontend.delivery_hardening.inventory: guard.prod.forbid
	@python3 scripts/verify/frontend_delivery_ui_inventory.py

verify.frontend.release_navigation_policy.guard: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_release_navigation_policy_guard.py
	@python3 scripts/verify/frontend_release_navigation_policy_guard.py

verify.frontend.relation_entry.contract_guard: guard.prod.forbid
	@python3 scripts/verify/relation_entry_contract_guard.py

verify.frontend.relation_read_closure.guard: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/relation_read_closure_test.ts --bundle --platform=node --format=esm --outfile=/tmp/relation-read-closure-test.mjs >/dev/null
	@node /tmp/relation-read-closure-test.mjs
	@python3 scripts/verify/relation_read_closure_guard.py

verify.frontend.modifiers_runtime.guard: guard.prod.forbid
	@python3 scripts/verify/modifiers_runtime_guard.py

verify.frontend.onchange_roundtrip.guard: guard.prod.forbid
	@python3 scripts/verify/onchange_roundtrip_guard.py

verify.frontend.onchange_contract_schema.guard: guard.prod.forbid
	@python3 scripts/verify/onchange_contract_schema_guard.py

verify.frontend.onchange_line_patch.guard: guard.prod.forbid
	@python3 scripts/verify/onchange_line_patch_guard.py

.PHONY: verify.scene.maturity.guard
verify.scene.maturity.guard: guard.prod.forbid
	@python3 scripts/verify/scene_maturity_guard.py

.PHONY: verify.scene.coverage.dashboard
verify.scene.coverage.dashboard: guard.prod.forbid
	@python3 scripts/verify/scene_coverage_dashboard_report.py

.PHONY: verify.scene.inventory.freeze.guard
verify.scene.inventory.freeze.guard: guard.prod.forbid
	@python3 scripts/verify/scene_inventory_freeze_guard.py

.PHONY: verify.scene.role.policy.consistency.guard
verify.scene.role.policy.consistency.guard: guard.prod.forbid
	@python3 scripts/verify/scene_role_policy_consistency_guard.py

.PHONY: verify.scene.data_source.schema.guard
verify.scene.data_source.schema.guard: guard.prod.forbid
	@python3 scripts/verify/scene_data_source_schema_guard.py

.PHONY: verify.scene.r3.runtime.guard
verify.scene.r3.runtime.guard: guard.prod.forbid
	@python3 scripts/verify/scene_r3_runtime_guard.py

.PHONY: verify.scene.r3.runtime.strict
verify.scene.r3.runtime.strict: guard.prod.forbid
	@python3 scripts/verify/scene_r3_runtime_guard.py \
		--max-action-chain-fail-count 0 \
		--min-pass-rate 1.0 \
		--min-action-chain-success-rate 0.50 \
		--max-action-chain-fallback-rate 0.50 \
		--fail-on-warning

.PHONY: gate.scene.r3.runtime.strict
gate.scene.r3.runtime.strict: verify.scene.r3.runtime.strict
	@echo "[gate.scene.r3.runtime.strict] PASS"

.PHONY: verify.scene.r3.runtime.quick
verify.scene.r3.runtime.quick: guard.prod.forbid gate.scene.r3.runtime.strict
	@echo "[verify.scene.r3.runtime.quick] summary"
	@sed -n '/^## Summary/,/^## Gate Thresholds/p' docs/audit/scene_r3_runtime_dashboard.md | sed '$$d'
	@sed -n '/^## Gate Result/,/^## Checks/p' docs/audit/scene_r3_runtime_dashboard.md | sed '$$d'

.PHONY: verify.scene.role.surface.consistency.guard
verify.scene.role.surface.consistency.guard: guard.prod.forbid
	@python3 scripts/verify/scene_role_surface_consistency_guard.py

.PHONY: verify.scene.inventory.draft.diff.report
verify.scene.inventory.draft.diff.report: guard.prod.forbid
	@python3 scripts/verify/scene_inventory_draft_diff_report.py

.PHONY: verify.scene.r1_r2.upgrade.queue.report
verify.scene.r1_r2.upgrade.queue.report: guard.prod.forbid
	@python3 scripts/verify/scene_r1_r2_upgrade_queue_report.py

.PHONY: verify.scene.r2_r3.upgrade.queue.report
verify.scene.r2_r3.upgrade.queue.report: guard.prod.forbid
	@python3 scripts/verify/scene_r2_r3_upgrade_queue_report.py

verify.frontend.x2many_command_semantic.guard: guard.prod.forbid
	@python3 scripts/verify/x2many_command_semantic_guard.py

verify.frontend.x2many_inline_edit.guard: guard.prod.forbid
	@python3 scripts/verify/x2many_inline_edit_guard.py

verify.contract.subviews.guard: guard.prod.forbid
	@python3 scripts/verify/subviews_contract_guard.py

verify.frontend.view_type_render_coverage.guard: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_view_type_render_coverage_guard
	@python3 scripts/verify/view_type_render_coverage_guard.py

verify.frontend.view_type_contract_semantic.guard: guard.prod.forbid
	@python3 scripts/verify/view_type_contract_semantic_guard.py

.PHONY: verify.frontend.widget_richness.post_ga.guard
verify.frontend.widget_richness.post_ga.guard: guard.prod.forbid verify.frontend.x2many_command_semantic.guard verify.frontend.x2many_inline_edit.guard verify.contract.subviews.guard verify.frontend.view_type_render_coverage.guard verify.frontend.view_type_contract_semantic.guard verify.unified_page_contract.v2.web_consumer
	@echo "[OK] verify.frontend.widget_richness.post_ga.guard done"

verify.frontend.search_groupby_savedfilters.guard: guard.prod.forbid
	@python3 scripts/verify/search_groupby_savedfilters_guard.py

verify.frontend.group_summary_runtime.guard: guard.prod.forbid
	@python3 scripts/verify/group_summary_runtime_guard.py

verify.frontend.grouped_rows_runtime.guard: guard.prod.forbid
	@python3 scripts/verify/grouped_rows_runtime_guard.py

verify.payment_request_receipt_type.browser_group_smoke: guard.prod.forbid
	@node scripts/verify/payment_request_receipt_type_browser_group_smoke.js

verify.invoice_entry_fact.contract_guard: guard.prod.forbid
	@python3 scripts/verify/invoice_entry_fact_contract_guard.py

verify.invoice_entry_fact.runtime_smoke: guard.prod.forbid
	@node scripts/verify/invoice_entry_fact_runtime_smoke.js

verify.invoice_entry_fact.browser_smoke: guard.prod.forbid
	@node scripts/verify/invoice_entry_fact_browser_smoke.js

verify.frontend.grouped_pagination_semantic.guard: guard.prod.forbid
	@python3 scripts/verify/grouped_pagination_semantic_guard.py

verify.frontend.grouped_pagination_semantic_drift.guard: guard.prod.forbid
	@python3 scripts/verify/grouped_pagination_semantic_drift_guard.py

.PHONY: verify.frontend.grouped_contract_consistency.guard
verify.frontend.grouped_contract_consistency.guard: guard.prod.forbid
	@python3 scripts/verify/grouped_contract_consistency_guard.py

.PHONY: verify.frontend.grouped_drift_summary.guard
verify.frontend.grouped_drift_summary.guard: guard.prod.forbid
	@python3 scripts/verify/grouped_drift_summary_guard.py

.PHONY: verify.frontend.grouped_drift_summary.schema.guard
verify.frontend.grouped_drift_summary.schema.guard: guard.prod.forbid verify.frontend.grouped_drift_summary.guard
	@python3 scripts/verify/grouped_drift_summary_schema_guard.py

.PHONY: verify.frontend.grouped_drift_summary.baseline.guard
verify.frontend.grouped_drift_summary.baseline.guard: guard.prod.forbid verify.frontend.grouped_drift_summary.schema.guard
	@python3 scripts/verify/grouped_drift_summary_baseline_guard.py

.PHONY: verify.frontend.grouped_governance_brief.guard
verify.frontend.grouped_governance_brief.guard: guard.prod.forbid verify.frontend.grouped_drift_summary.baseline.guard verify.contract.governance.coverage
	@python3 scripts/verify/grouped_governance_brief_guard.py

.PHONY: verify.frontend.grouped_governance_brief.schema.guard
verify.frontend.grouped_governance_brief.schema.guard: guard.prod.forbid verify.frontend.grouped_governance_brief.guard
	@python3 scripts/verify/grouped_governance_brief_schema_guard.py

.PHONY: verify.frontend.grouped_governance_brief.baseline.guard
verify.frontend.grouped_governance_brief.baseline.guard: guard.prod.forbid verify.frontend.grouped_governance_brief.schema.guard
	@python3 scripts/verify/grouped_governance_brief_baseline_guard.py

.PHONY: verify.frontend.grouped_governance_policy_matrix
verify.frontend.grouped_governance_policy_matrix: guard.prod.forbid verify.frontend.grouped_governance_brief.baseline.guard
	@python3 scripts/verify/grouped_governance_policy_matrix.py

.PHONY: verify.frontend.grouped_governance_policy_matrix.schema.guard
verify.frontend.grouped_governance_policy_matrix.schema.guard: guard.prod.forbid verify.frontend.grouped_governance_policy_matrix
	@python3 scripts/verify/grouped_governance_policy_matrix_schema_guard.py

.PHONY: verify.frontend.grouped_governance_trend_consistency.guard
verify.frontend.grouped_governance_trend_consistency.guard: guard.prod.forbid verify.frontend.grouped_governance_policy_matrix.schema.guard
	@python3 scripts/verify/grouped_governance_trend_consistency_guard.py

.PHONY: verify.frontend.grouped_governance_trend_consistency.schema.guard
verify.frontend.grouped_governance_trend_consistency.schema.guard: guard.prod.forbid verify.frontend.grouped_governance_trend_consistency.guard
	@python3 scripts/verify/grouped_governance_trend_consistency_schema_guard.py

.PHONY: verify.frontend.grouped_governance_trend_consistency.baseline.guard
verify.frontend.grouped_governance_trend_consistency.baseline.guard: guard.prod.forbid verify.frontend.grouped_governance_trend_consistency.schema.guard
	@python3 scripts/verify/grouped_governance_trend_consistency_baseline_guard.py

.PHONY: verify.grouped.governance.bundle
verify.grouped.governance.bundle: guard.prod.forbid verify.frontend.grouped_rows_runtime.guard verify.frontend.grouped_pagination_semantic.guard verify.frontend.grouped_pagination_semantic_drift.guard verify.frontend.grouped_contract_consistency.guard verify.frontend.grouped_drift_summary.baseline.guard verify.frontend.grouped_governance_brief.baseline.guard verify.frontend.grouped_governance_policy_matrix.schema.guard verify.frontend.grouped_governance_trend_consistency.baseline.guard
	@python3 scripts/contract/export_evidence.py
	@python3 scripts/verify/contract_evidence_schema_guard.py
	@python3 scripts/verify/contract_evidence_guard.py
	@echo "[OK] verify.grouped.governance.bundle done"

verify.contract.operation_gateway.guard: guard.prod.forbid
	@python3 scripts/verify/operation_gateway_contract_guard.py

verify.frontend.contract_header_action.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/contract_header_action_presentation_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/contract-header-action-presentation-test.mjs >/dev/null
	@node /tmp/contract-header-action-presentation-test.mjs

.PHONY: verify.frontend.canonical_form_presenter.unit verify.frontend.hierarchy_command_authority.unit verify.frontend.readonly_main_data_coverage.unit verify.frontend.create_default_hydration.unit verify.frontend.create_record_user_journey.unit
verify.frontend.canonical_form_presenter.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/canonical_form_presenter_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/canonical-form-presenter-test.mjs >/dev/null
	@node /tmp/canonical-form-presenter-test.mjs

verify.frontend.hierarchy_command_authority.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/hierarchy_command_authority_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/hierarchy-command-authority-test.mjs >/dev/null
	@node /tmp/hierarchy-command-authority-test.mjs

verify.frontend.readonly_main_data_coverage.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/readonly_main_data_coverage_test.ts --bundle --platform=node --format=esm --outfile=/tmp/readonly-main-data-coverage-test.mjs >/dev/null
	@node /tmp/readonly-main-data-coverage-test.mjs

verify.frontend.create_default_hydration.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/create_default_hydration_test.ts --bundle --platform=node --format=esm --outfile=/tmp/create-default-hydration-test.mjs >/dev/null
	@node /tmp/create-default-hydration-test.mjs

verify.frontend.create_record_user_journey.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/create_record_user_journey_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/create-record-user-journey-test.mjs >/dev/null
	@node /tmp/create-record-user-journey-test.mjs

.PHONY: verify.frontend.native_section_navigation.unit verify.frontend.native_collaboration_presentation.unit
verify.frontend.native_section_navigation.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/native_section_navigation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/native-section-navigation-test.mjs >/dev/null
	@node /tmp/native-section-navigation-test.mjs

verify.frontend.native_collaboration_presentation.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/native_collaboration_presentation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/native-collaboration-presentation-test.mjs >/dev/null
	@node /tmp/native-collaboration-presentation-test.mjs

.PHONY: verify.frontend.cross_model_action_navigation.unit
verify.frontend.cross_model_action_navigation.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/cross_model_action_navigation_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/cross-model-action-navigation-test.mjs >/dev/null
	@node /tmp/cross-model-action-navigation-test.mjs

verify.frontend.quick.gate: verify.frontend.canonical_form_presenter.unit verify.frontend.hierarchy_command_authority.unit verify.frontend.create_default_hydration.unit verify.frontend.create_record_user_journey.unit verify.frontend.native_collaboration_presentation.unit verify.frontend.cross_model_action_navigation.unit verify.frontend.contract_render_profile.unit
verify.frontend.quick.gate: guard.prod.forbid verify.frontend.workspace_content_alignment.guard verify.frontend.page_identity verify.frontend.contract_header_action.unit verify.frontend.readonly_main_data_coverage.unit verify.frontend.relation_entry.contract_guard verify.frontend.relation_read_closure.guard verify.frontend.modifiers_runtime.guard verify.frontend.onchange_roundtrip.guard verify.frontend.onchange_contract_schema.guard verify.frontend.onchange_line_patch.guard verify.frontend.x2many_command_semantic.guard verify.frontend.x2many_inline_edit.guard verify.contract.subviews.guard verify.frontend.view_type_render_coverage.guard verify.frontend.view_type_contract_semantic.guard verify.frontend.search_groupby_savedfilters.guard verify.frontend.group_summary_runtime.guard verify.frontend.grouped_rows_runtime.guard verify.frontend.grouped_pagination_semantic.guard verify.frontend.grouped_pagination_semantic_drift.guard verify.frontend.grouped_contract_consistency.guard verify.frontend.grouped_drift_summary.baseline.guard verify.frontend.typecheck.strict verify.frontend.build
	@echo "[OK] verify.frontend.quick.gate done"

verify.frontend.suggested_action.contract_guard: guard.prod.forbid
	@python3 scripts/verify/suggested_action_contract_guard.py

verify.frontend.suggested_action.catalog: guard.prod.forbid
	@python3 scripts/verify/suggested_action_catalog_export.py

verify.frontend.suggested_action.parser_guard: guard.prod.forbid
	@python3 scripts/verify/suggested_action_parser_guard.py

verify.frontend.suggested_action.runtime_guard: guard.prod.forbid
	@python3 scripts/verify/suggested_action_runtime_guard.py

verify.frontend.suggested_action.import_boundary_guard: guard.prod.forbid
	@python3 scripts/verify/suggested_action_import_boundary_guard.py

verify.frontend.suggested_action.usage_guard: guard.prod.forbid
	@python3 scripts/verify/suggested_action_usage_guard.py

verify.frontend.suggested_action.trace_export_guard: guard.prod.forbid
	@python3 scripts/verify/suggested_action_trace_export_guard.py

verify.frontend.suggested_action.topk_guard: guard.prod.forbid
	@python3 scripts/verify/suggested_action_topk_guard.py

verify.frontend.suggested_action.since_filter_guard: guard.prod.forbid
	@python3 scripts/verify/suggested_action_since_filter_guard.py

verify.frontend.suggested_action.hud_export_guard: guard.prod.forbid
	@python3 scripts/verify/suggested_action_hud_export_guard.py

verify.frontend.cross_stack_smoke: guard.prod.forbid
	@python3 scripts/verify/cross_stack_suggested_action_smoke.py

verify.frontend.no_new_any_guard: guard.prod.forbid
	@python3 scripts/verify/no_new_any_guard.py

verify.portal.scene_observability.structure_guard: guard.prod.forbid
	@python3 scripts/verify/scene_observability_structure_guard.py

verify.portal.scene_observability.structure_guard.update: guard.prod.forbid
	@python3 scripts/verify/scene_observability_structure_guard.py --update

verify.frontend.suggested_action.all: guard.prod.forbid verify.frontend.suggested_action.contract_guard verify.frontend.suggested_action.parser_guard verify.frontend.suggested_action.runtime_guard verify.frontend.suggested_action.import_boundary_guard verify.frontend.suggested_action.usage_guard verify.frontend.suggested_action.trace_export_guard verify.frontend.suggested_action.topk_guard verify.frontend.suggested_action.since_filter_guard verify.frontend.suggested_action.hud_export_guard verify.frontend.cross_stack_smoke verify.frontend.no_new_any_guard verify.frontend.suggested_action.catalog verify.frontend.typecheck.strict verify.frontend.build
	@echo "[OK] verify.frontend.suggested_action.all done"

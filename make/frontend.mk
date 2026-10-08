# ======================================================
# ==================== Frontend ========================
# ======================================================
include make/frontend_professional_extensions.mk

.PHONY: fe.install fe.dev fe.gate verify.frontend.build prod.frontend.build verify.frontend.typecheck.strict verify.frontend.lint.src verify.frontend.page_width_contract.guard verify.frontend.quick.gate verify.frontend.contract_header_action.unit verify.frontend.relation_entry.contract_guard verify.frontend.relation_read_closure.guard verify.frontend.modifiers_runtime.guard verify.frontend.onchange_roundtrip.guard verify.frontend.onchange_contract_schema.guard verify.frontend.onchange_line_patch.guard verify.frontend.x2many_command_semantic.guard verify.frontend.x2many_inline_edit.guard verify.contract.subviews.guard verify.frontend.view_type_render_coverage.guard verify.frontend.view_type_contract_semantic.guard verify.frontend.search_groupby_savedfilters.guard verify.frontend.saved_search_capability.unit verify.frontend.record_denied_reason.unit verify.frontend.contract_record_action_state.unit verify.frontend.group_summary_runtime.guard verify.frontend.grouped_rows_runtime.guard verify.frontend.grouped_pagination_semantic.guard verify.frontend.grouped_pagination_semantic_drift.guard verify.contract.operation_gateway.guard verify.frontend.suggested_action.contract_guard verify.frontend.suggested_action.catalog verify.frontend.suggested_action.parser_guard verify.frontend.suggested_action.runtime_guard verify.frontend.suggested_action.import_boundary_guard verify.frontend.suggested_action.usage_guard verify.frontend.suggested_action.trace_export_guard verify.frontend.suggested_action.topk_guard verify.frontend.suggested_action.since_filter_guard verify.frontend.suggested_action.hud_export_guard verify.frontend.cross_stack_smoke verify.frontend.no_new_any_guard verify.frontend.suggested_action.all verify.portal.scene_observability.structure_guard verify.portal.scene_observability.structure_guard.update
.PHONY: fe.install.cached confirm.frontend.release.audit verify.frontend.release.local verify.frontend.scene_component_bridge.unit verify.frontend.scene_component_bridge.guard verify.frontend.scene_component_bridge.browser verify.frontend.primitive_adapter.unit

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
	@FRONTEND_PROFILE=$${FRONTEND_PROFILE:-local-dev} \
	  FRONTEND_DEV_PIDFILE="$${FRONTEND_DEV_PIDFILE:-/tmp/sc-frontend-dev.pid}" \
	  FRONTEND_DEV_LOGFILE="$${FRONTEND_DEV_LOGFILE:-/tmp/sc-frontend-dev.log}" \
	  bash scripts/dev/frontend_dev_reset.sh

fe.dev.reset: guard.prod.forbid
	@bash scripts/dev/frontend_dev_reset.sh

fe.dev.daily: guard.prod.forbid
	@FRONTEND_PROFILE=local-dev bash scripts/dev/frontend_dev_reset.sh

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

verify.frontend.chart_engine.guard: guard.prod.forbid
	@python3 -m py_compile scripts/verify/frontend_chart_engine_guard.py
	@python3 -m unittest scripts.verify.test_frontend_chart_engine_guard
	@python3 scripts/verify/frontend_chart_engine_guard.py


verify.frontend.scene_component_bridge.unit: guard.prod.forbid verify.frontend.contract_form_collaboration_authority.unit
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
	SC_ACCEPTANCE_FIXTURE_PASSWORD="$${SC_ACCEPTANCE_FIXTURE_PASSWORD:-$(SC_ACCEPTANCE_FIXTURE_PASSWORD)}"; export SC_ACCEPTANCE_FIXTURE_PASSWORD; \
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

# Concurrent-read coalescing identity. The request key must cover every
# result-affecting parameter, so a new keyword, page or ordering is a real
# request and only genuinely identical in-flight reads are merged.
.PHONY: verify.frontend.intent_request_identity.unit verify.frontend.intent_request_coalescing.unit
verify.frontend.intent_request_identity.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/intent_request_identity_test.ts --bundle --platform=node --format=esm --outfile=/tmp/intent-request-identity-test.mjs >/dev/null
	@node /tmp/intent-request-identity-test.mjs

verify.frontend.intent_request_coalescing.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/intent_request_coalescing_test.ts --bundle --platform=node --format=esm --define:import.meta.env={} --alias:vue=$(ROOT_DIR)/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js --outfile=/tmp/intent-request-coalescing-test.mjs >/dev/null
	@node /tmp/intent-request-coalescing-test.mjs

.PHONY: verify.frontend.official_icon.unit
verify.frontend.official_icon.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/official_icon_adapter_test.ts --bundle --platform=node --format=esm --loader:.css=empty --outfile=/tmp/official-icon-adapter-test.mjs >/dev/null
	@node /tmp/official-icon-adapter-test.mjs
	@python3 -m unittest scripts.verify.test_frontend_official_icon_resource_guard
	@python3 scripts/verify/frontend_official_icon_resource_guard.py

.PHONY: verify.frontend.global_component_capability.unit
verify.frontend.global_component_capability.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/global_component_capability_test.ts --bundle --platform=node --format=esm --loader:.css=empty --resolve-extensions=.tsx,.ts,.jsx,.js,.css,.json,.mjs --alias:vue=./frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js --alias:tdesign-vue-next=$(ROOT_DIR)/frontend/packages/ui/node_modules/tdesign-vue-next --outfile=/tmp/global-component-capability-test.mjs >/dev/null
	@node /tmp/global-component-capability-test.mjs

.PHONY: verify.frontend.system_state_recovery.unit
verify.frontend.system_state_recovery.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/session_expired_recovery_test.ts --bundle --platform=node --format=esm --outfile=/tmp/session-expired-recovery-test.mjs >/dev/null
	@node /tmp/session-expired-recovery-test.mjs
	@python3 -m unittest scripts.verify.test_frontend_system_state_recovery_guard
	@python3 scripts/verify/frontend_system_state_recovery_guard.py

.PHONY: verify.frontend.scene_entry_contract.unit
verify.frontend.scene_entry_contract.unit: guard.prod.forbid
	@node frontend/apps/web/scripts/readonly_block_component_test.mjs --kind grid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/scene_entry_contract_test.ts --bundle --platform=node --format=esm --outfile=/tmp/scene-entry-contract-test.mjs >/dev/null
	@node /tmp/scene-entry-contract-test.mjs
	@python3 addons/smart_core/tests/test_scene_ready_contract_builder_semantic_consumption.py
	@python3 addons/smart_core/tests/test_system_init_scene_runtime_surface_builder.py
	@python3 addons/smart_core/tests/test_scene_provider_target_identity_merge.py

.PHONY: verify.frontend.navigation_shell.unit
verify.frontend.navigation_shell.unit: guard.prod.forbid verify.frontend.scene_entry_contract.unit
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/canonical_navigation_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/canonical-navigation-model-test.mjs >/dev/null
	@node /tmp/canonical-navigation-model-test.mjs
	@python3 addons/smart_core/tests/test_delivery_menu_entry_target.py
	@python3 addons/smart_construction_core/tests/test_business_category_entry_policy.py
	@python3 -m unittest scripts/verify/test_frontend_navigation_shell_guard.py
	@python3 scripts/verify/frontend_navigation_shell_guard.py

.PHONY: verify.frontend.record_form_return.unit
verify.frontend.record_form_return.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/record_form_return_navigation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/record-form-return-navigation-test.mjs >/dev/null
	@node /tmp/record-form-return-navigation-test.mjs

.PHONY: verify.frontend.boq_import_preview.unit
verify.frontend.boq_import_preview.unit: guard.prod.forbid
	@node frontend/apps/web/scripts/readonly_block_component_test.mjs --kind boq
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/boq_import_preview_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/boq-import-preview-model-test.mjs >/dev/null
	@node /tmp/boq-import-preview-model-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_boq_import_preview_guard.py
	@python3 scripts/verify/frontend_boq_import_preview_guard.py

.PHONY: verify.frontend.chart_dataset.unit
verify.frontend.chart_dataset.unit: guard.prod.forbid
	@node frontend/apps/web/scripts/readonly_block_component_test.mjs --kind chart
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/chart_dataset_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/chart-dataset-model-test.mjs >/dev/null
	@node /tmp/chart-dataset-model-test.mjs
	@python3 scripts/verify/frontend_chart_engine_guard.py

.PHONY: verify.frontend.boq_line_patch.unit
verify.frontend.boq_line_patch.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/boq_line_patch_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/boq-line-patch-model-test.mjs >/dev/null
	@node /tmp/boq-line-patch-model-test.mjs

.PHONY: verify.frontend.overview_rich_text.unit
verify.frontend.overview_rich_text.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/overview_rich_text_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/overview-rich-text-model-test.mjs >/dev/null
	@node /tmp/overview-rich-text-model-test.mjs

.PHONY: verify.frontend.product_page_header.unit verify.frontend.collection_action_toolbar.unit verify.frontend.collection_aggregate_footer.unit verify.frontend.collection_group_header.unit verify.frontend.collection_summary_strip.unit verify.frontend.collection_mobile_record_row.unit verify.frontend.collection_kanban_record_card.unit verify.frontend.collection_navigation_controls.unit verify.frontend.collection_row_action_identity.unit verify.frontend.collection_row_cell.unit verify.frontend.collection_selection_control.unit
verify.frontend.product_page_header.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/product-page-header-model-test.mjs >/dev/null
	@node /tmp/product-page-header-model-test.mjs
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts --bundle --platform=node --format=esm --outfile=/tmp/product-page-header-adapter-contract-test.mjs >/dev/null
	@node /tmp/product-page-header-adapter-contract-test.mjs
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

verify.frontend.collection_mobile_record_row.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_collection_mobile_record_row_guard.py
	@python3 scripts/verify/frontend_collection_mobile_record_row_guard.py

verify.frontend.collection_kanban_record_card.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_collection_kanban_record_card_guard.py
	@python3 scripts/verify/frontend_collection_kanban_record_card_guard.py

verify.frontend.collection_navigation_controls.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/collection_pagination_presentation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/collection-pagination-presentation-test.mjs >/dev/null
	@node /tmp/collection-pagination-presentation-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_collection_navigation_controls_guard.py
	@python3 scripts/verify/frontend_collection_navigation_controls_guard.py

verify.frontend.collection_row_action_identity.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/collection_row_action_identity_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/collection-row-action-identity-test.mjs >/dev/null
	@node /tmp/collection-row-action-identity-test.mjs

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

.PHONY: verify.frontend.product_page_pattern.unit verify.frontend.professional_component_registry.unit verify.frontend.professional_base_field.unit verify.frontend.component_driver_takeover.unit refresh.frontend.component_driver_takeover.inventory
verify.frontend.component_driver_takeover.unit: guard.prod.forbid
	@python3 -m unittest scripts.audit.test_generate_frontend_component_driver_takeover_inventory
	@python3 scripts/audit/generate_frontend_component_driver_takeover_inventory.py --check

refresh.frontend.component_driver_takeover.inventory: guard.prod.forbid
	@python3 scripts/audit/generate_frontend_component_driver_takeover_inventory.py

.PHONY: verify.frontend.theme_profile.unit verify.frontend.boq_import_preview.unit
verify.frontend.theme_profile.unit: guard.prod.forbid
	@python3 scripts/verify/frontend_theme_profile_guard.py

.PHONY: verify.frontend.mobile_viewport.unit
verify.frontend.mobile_viewport.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_mobile_viewport_guard.py
	@python3 scripts/verify/frontend_mobile_viewport_guard.py

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
	@node frontend/apps/web/scripts/readonly_block_component_test.mjs --kind attachment
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_relation_field_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-relation-field-model-test.mjs >/dev/null
	@node /tmp/professional-relation-field-model-test.mjs
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/relation_column_descriptor_authority_test.ts --bundle --platform=node --format=esm --outfile=/tmp/relation-column-descriptor-authority-test.mjs >/dev/null
	@node /tmp/relation-column-descriptor-authority-test.mjs
	@python3 addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py
	@python3 -m unittest scripts/verify/test_frontend_professional_relation_field_guard.py
	@python3 scripts/verify/frontend_professional_relation_field_guard.py

.PHONY: verify.frontend.professional_detail_collection.unit
verify.frontend.professional_detail_collection.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_detail_collection_model_test.ts --bundle --platform=node --format=esm --outfile=/tmp/professional-detail-collection-model-test.mjs >/dev/null
	@node /tmp/professional-detail-collection-model-test.mjs
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/payment_settlement_introduce_dialog_contract_test.ts --bundle --platform=node --format=esm --outfile=/tmp/payment-settlement-introduce-dialog-contract-test.mjs >/dev/null
	@node /tmp/payment-settlement-introduce-dialog-contract-test.mjs
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

.PHONY: verify.frontend.capability_policy.unit
verify.frontend.capability_policy.unit: guard.prod.forbid
	@node scripts/verify/fe_capability_policy_smoke.js

.PHONY: verify.frontend.decision_authority.unit verify.frontend.decision_authority.guard verify.frontend.decision_authority.export
verify.frontend.decision_authority.export: guard.prod.forbid
	@python3 scripts/verify/frontend_decision_authority.py --export

verify.frontend.decision_authority.guard: guard.prod.forbid
	@python3 scripts/verify/frontend_decision_authority_guard.py

verify.frontend.decision_authority.unit: guard.prod.forbid
	@python3 -m py_compile scripts/verify/frontend_decision_authority.py scripts/verify/frontend_decision_authority_guard.py scripts/verify/test_frontend_decision_authority_guard.py
	@python3 -m unittest scripts.verify.test_frontend_decision_authority_guard
	@python3 scripts/verify/frontend_decision_authority_guard.py

.PHONY: verify.frontend.professional_relation_lifecycle.unit verify.frontend.contract_prompt_action_presentation.unit verify.frontend.contract_prompt_action_presentation.browser verify.frontend.low_code_field_create_dialog.unit verify.frontend.low_code_field_create_dialog.browser verify.frontend.overlay_lifecycle.unit verify.frontend.overlay_lifecycle.browser verify.frontend.collaboration_primitives.browser verify.frontend.state_dashboard.unit verify.frontend.state_dashboard.browser verify.frontend.rendering_detail_state.unit verify.frontend.rendering_detail_state.browser
verify.frontend.professional_relation_lifecycle.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/professional_relation_lifecycle_model_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/professional-relation-lifecycle-model-test.mjs >/dev/null
	@node /tmp/professional-relation-lifecycle-model-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_professional_relation_lifecycle_guard.py
	@python3 scripts/verify/frontend_professional_relation_lifecycle_guard.py

verify.frontend.contract_prompt_action_presentation.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_contract_prompt_action_presentation_guard.py
	@python3 scripts/verify/frontend_contract_prompt_action_presentation_guard.py

verify.frontend.contract_prompt_action_presentation.browser: guard.prod.forbid
	@node scripts/verify/frontend_contract_prompt_action_presentation_browser.mjs

verify.frontend.low_code_field_create_dialog.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_low_code_field_create_dialog_guard.py
	@python3 scripts/verify/frontend_low_code_field_create_dialog_guard.py

verify.frontend.low_code_field_create_dialog.browser: guard.prod.forbid
	@node scripts/verify/frontend_low_code_field_create_dialog_browser.mjs

verify.frontend.overlay_lifecycle.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/modal_lifecycle_runtime_test.ts --bundle --platform=node --format=esm --outfile=/tmp/modal-lifecycle-runtime-test.mjs >/dev/null
	@node /tmp/modal-lifecycle-runtime-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_overlay_lifecycle_guard.py
	@python3 scripts/verify/frontend_overlay_lifecycle_guard.py

verify.frontend.overlay_lifecycle.browser: guard.prod.forbid
	@node scripts/verify/frontend_overlay_lifecycle_browser.mjs

.PHONY: verify.frontend.page_renderer.browser
verify.frontend.page_renderer.browser: guard.prod.forbid
	@OVERLAY_LIFECYCLE_SCOPE=page-renderer node scripts/verify/frontend_overlay_lifecycle_browser.mjs

verify.frontend.collaboration_primitives.browser: guard.prod.forbid
	@node scripts/verify/frontend_collaboration_primitives_browser.mjs

verify.frontend.state_dashboard.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_my_work_presentation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/product-my-work-presentation-test.mjs >/dev/null
	@node /tmp/product-my-work-presentation-test.mjs
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/activity_page_tab_keyboard_test.ts --bundle --platform=node --format=esm --outfile=/tmp/activity-page-tab-keyboard-test.mjs >/dev/null
	@node /tmp/activity-page-tab-keyboard-test.mjs
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/form_route_instance_identity_test.ts --bundle --platform=node --format=esm --outfile=/tmp/form-route-instance-identity-test.mjs >/dev/null
	@node /tmp/form-route-instance-identity-test.mjs
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/activity_page_retention_test.ts --bundle --platform=node --format=esm --outfile=/tmp/activity-page-retention-test.mjs >/dev/null
	@node /tmp/activity-page-retention-test.mjs
	@python3 -m unittest scripts/verify/test_frontend_state_presentation_guard.py scripts/verify/test_frontend_dashboard_state_guard.py
	@python3 scripts/verify/frontend_state_presentation_guard.py
	@python3 scripts/verify/frontend_dashboard_state_guard.py

verify.frontend.state_dashboard.browser: guard.prod.forbid
	@node scripts/verify/frontend_state_dashboard_browser.mjs

.PHONY: verify.frontend.rendering_detail_state.unit refresh.frontend.rendering_detail.inventory
verify.frontend.rendering_detail_state.unit: guard.prod.forbid
	@python3 -m unittest scripts.audit.test_generate_frontend_rendering_detail_inventory scripts.audit.test_generate_frontend_visual_projection_inventory scripts.audit.test_generate_frontend_official_design_alignment_inventory scripts.verify.test_frontend_inline_state_guard scripts.verify.test_frontend_rendering_detail_state_guard
	@python3 scripts/verify/frontend_inline_state_guard.py
	@python3 scripts/verify/frontend_rendering_detail_state_guard.py
	@python3 scripts/audit/generate_frontend_rendering_detail_inventory.py --check
	@python3 scripts/audit/generate_frontend_visual_projection_inventory.py --check
	@python3 scripts/audit/generate_frontend_official_design_alignment_inventory.py --check

refresh.frontend.rendering_detail.inventory: guard.prod.forbid
	@python3 scripts/audit/generate_frontend_rendering_detail_inventory.py
	@python3 scripts/audit/generate_frontend_visual_projection_inventory.py
	@python3 scripts/audit/generate_frontend_official_design_alignment_inventory.py

verify.frontend.rendering_detail_state.browser: guard.prod.forbid
	@node scripts/verify/frontend_rendering_detail_state_browser.mjs

.PHONY: verify.frontend.contract_basis.unit verify.frontend.contract_basis.enforce
verify.frontend.contract_basis.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_frontend_contract_basis_guard
	@python3 scripts/verify/frontend_contract_basis_guard.py

# 机制（交付车道）：出现前端判断即停机，回契约要结果。只要还有未闭合的契约缺陷
# （openContractDefects 或 verdict=contract_defect_open 的站点），就禁止冻结/放行。
verify.frontend.contract_basis.enforce: guard.prod.forbid
	@python3 scripts/verify/frontend_contract_basis_guard.py --enforce

.PHONY: verify.frontend.action_view_page_size_runtime.unit
# Behavioural lock for the list page-size declaration surface. It drives the
# production resolver with the production contract store, so a consumption-shape
# regression (reading a key the carrier does not expose) fails here instead of on
# the deployed surface. It asserts declaration-driven output plus fail-closed stop
# on a missing declaration, not the presence of literal strings.
verify.frontend.action_view_page_size_runtime.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/action_view_list_page_size_runtime_test.ts --bundle --platform=node --format=esm --outfile=/tmp/action-view-list-page-size-runtime-test.mjs >/dev/null
	@node /tmp/action-view-list-page-size-runtime-test.mjs

.PHONY: verify.frontend.dev.incremental verify.frontend.dev.incremental.unit verify.frontend.action_view_page_size_runtime.unit verify.frontend.dev.watch verify.frontend.form_structure_contract_projection.unit verify.frontend.native_form_structure_responsibility.unit verify.frontend.form_header_action_primitives.unit verify.frontend.action_view_page_actions.unit verify.frontend.relational_action_primitives.unit verify.frontend.native_form_action_presentation.unit verify.frontend.native_text_presentation.unit verify.frontend.native_form_action_presentation.browser verify.frontend.hierarchical_worksheet.unit verify.frontend.page_pattern_reference_parity.unit verify.frontend.collection_status_presentation.unit

verify.frontend.form_structure_contract_projection.unit: guard.prod.forbid
	@python3 scripts/verify/form_structure_contract_projection_matrix.py --check

# Shared form-structure responsibility behaviour: container pruning, layout
# wrapper decoration, body/navigation tree identity and the action-placeholder
# carrier gate.  Executes the production helpers, not a text scan.
verify.frontend.native_form_structure_responsibility.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/native_form_structure_responsibility_test.ts --bundle --platform=node --format=esm --outfile=/tmp/native-form-structure-responsibility-test.mjs >/dev/null
	@node /tmp/native-form-structure-responsibility-test.mjs

.PHONY: verify.frontend.contract_form_collaboration_authority.unit
verify.frontend.contract_form_collaboration_authority.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/contract_form_collaboration_authority_test.ts --bundle --platform=node --format=esm --outfile=/tmp/contract-form-collaboration-authority-test.mjs >/dev/null
	@node /tmp/contract-form-collaboration-authority-test.mjs

# Declared form surfaces: a non-field page region is visible only when the
# contract declares it, and a role-gated sub-region only on an explicit allow.
# Negative-first: the withheld-authorization and empty-declaration cases must
# stay hidden before the allowed case is proven to render.
.PHONY: verify.frontend.form_structure_surface_contract.unit
verify.frontend.form_structure_surface_contract.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/form_structure_surface_contract_test.ts --bundle --platform=node --format=esm --outfile=/tmp/form-structure-surface-contract-test.mjs >/dev/null
	@node /tmp/form-structure-surface-contract-test.mjs

.PHONY: verify.frontend.contract_v2_render_authority.unit
verify.frontend.contract_v2_render_authority.unit: guard.prod.forbid
	@python3 scripts/verify/contract_v2_render_authority_matrix.py --check

.PHONY: verify.frontend.contract_v2_runtime_policy.unit
verify.frontend.contract_v2_runtime_policy.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts --bundle --platform=node --format=esm --outfile=/tmp/contract-v2-runtime-policy-test.mjs >/dev/null
	@node /tmp/contract-v2-runtime-policy-test.mjs

# Development feedback only: these entries never build, capture browser
# evidence, refresh reports, or freeze a candidate fingerprint.
verify.frontend.dev.incremental.unit: guard.prod.forbid
	@python3 -m py_compile scripts/verify/frontend_dev_incremental.py scripts/verify/test_frontend_dev_incremental.py
	@python3 -m unittest scripts.verify.test_frontend_dev_incremental

verify.frontend.dev.incremental: guard.prod.forbid
	@python3 scripts/verify/frontend_dev_incremental.py $(foreach path,$(FRONTEND_DEV_CHANGED_PATHS),--path $(path))

verify.frontend.dev.watch: guard.prod.forbid
	@python3 scripts/verify/frontend_dev_incremental.py --watch
verify.frontend.form_header_action_primitives.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_form_header_action_primitives_guard.py
	@python3 scripts/verify/frontend_form_header_action_primitives_guard.py

verify.frontend.action_view_page_actions.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_action_view_page_actions_guard.py
	@python3 scripts/verify/frontend_action_view_page_actions_guard.py

verify.frontend.relational_action_primitives.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_relational_action_primitives_guard.py
	@python3 scripts/verify/frontend_relational_action_primitives_guard.py

verify.frontend.native_form_action_presentation.unit: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_frontend_native_form_action_presentation_guard.py
	@python3 scripts/verify/frontend_native_form_action_presentation_guard.py

verify.frontend.native_text_presentation.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/native_text_presentation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/native-text-presentation-test.mjs >/dev/null
	@node /tmp/native-text-presentation-test.mjs

verify.frontend.native_form_action_presentation.browser: guard.prod.forbid
	@node scripts/verify/frontend_native_form_action_presentation_browser.mjs

verify.frontend.hierarchical_worksheet.unit: guard.prod.forbid
	@python3 addons/smart_core/tests/test_page_assembler_view_orchestration_versions.py
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/hierarchical_worksheet_interaction_test.ts --bundle --platform=node --format=esm --outfile=/tmp/hierarchical-worksheet-interaction-test.mjs >/dev/null
	@node /tmp/hierarchical-worksheet-interaction-test.mjs
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/hierarchical_worksheet_domain_tab_test.ts --bundle --platform=node --format=esm --outfile=/tmp/hierarchical-worksheet-domain-tab-test.mjs >/dev/null
	@node /tmp/hierarchical-worksheet-domain-tab-test.mjs
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/hierarchical_worksheet_load_stage_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/hierarchical-worksheet-load-stage-test.mjs >/dev/null
	@node /tmp/hierarchical-worksheet-load-stage-test.mjs

verify.frontend.page_pattern_reference_parity.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_frontend_page_pattern_reference_parity_guard
	@python3 scripts/verify/frontend_page_pattern_reference_parity_guard.py
	@python3 scripts/verify/test_page_pattern_reference_ledger_guard.py
	@python3 scripts/verify/page_pattern_reference_ledger_guard.py

.PHONY: verify.frontend.collection_status_presentation.unit
verify.frontend.collection_status_presentation.unit: guard.prod.forbid
	@node scripts/verify/frontend_collection_status_presentation.test.mjs

verify.frontend.quick.gate: verify.frontend.official_icon.unit verify.frontend.global_component_capability.unit verify.frontend.component_driver_takeover.unit verify.frontend.scene_component_bridge.unit verify.frontend.scene_component_bridge.guard verify.frontend.scene_contract.consumption.guard verify.frontend.primitive_adapter.unit verify.frontend.navigation_shell.unit verify.frontend.product_page_header.unit verify.frontend.collection_action_toolbar.unit verify.frontend.collection_aggregate_footer.unit verify.frontend.collection_group_header.unit verify.frontend.collection_summary_strip.unit verify.frontend.collection_mobile_record_row.unit verify.frontend.collection_kanban_record_card.unit verify.frontend.collection_navigation_controls.unit verify.frontend.collection_row_action_identity.unit verify.frontend.collection_row_cell.unit verify.frontend.collection_selection_control.unit verify.frontend.product_page_pattern.unit verify.frontend.professional_component_registry.unit verify.frontend.professional_base_field.unit verify.frontend.professional_business_value.unit verify.frontend.professional_relation_field.unit verify.frontend.professional_detail_collection.unit verify.frontend.professional_workflow.unit verify.frontend.professional_audit.unit verify.frontend.professional_collaboration.unit verify.frontend.professional_relation_lifecycle.unit verify.frontend.contract_prompt_action_presentation.unit verify.frontend.low_code_field_create_dialog.unit verify.frontend.form_header_action_primitives.unit verify.frontend.action_view_page_actions.unit verify.frontend.relational_action_primitives.unit verify.frontend.native_form_action_presentation.unit verify.frontend.native_text_presentation.unit verify.frontend.native_form_structure_responsibility.unit verify.frontend.overlay_lifecycle.unit verify.frontend.state_dashboard.unit verify.frontend.rendering_detail_state.unit verify.frontend.hierarchical_worksheet.unit verify.frontend.page_pattern_reference_parity.unit verify.frontend.professional.extensions.unit verify.frontend.theme_profile.unit verify.frontend.intent_request_identity.unit verify.frontend.intent_request_coalescing.unit verify.frontend.decision_authority.unit verify.frontend.capability_policy.unit verify.frontend.contract_basis.unit verify.frontend.action_view_page_size_runtime.unit

verify.frontend.pr.unit: verify.frontend.official_icon.unit verify.frontend.global_component_capability.unit verify.frontend.component_driver_takeover.unit verify.frontend.primitive_adapter.unit verify.frontend.navigation_shell.unit verify.frontend.state_dashboard.unit verify.frontend.professional.extensions.unit verify.frontend.boq_import_preview.unit verify.frontend.chart_dataset.unit verify.frontend.mobile_viewport.unit verify.frontend.intent_request_identity.unit verify.frontend.intent_request_coalescing.unit verify.frontend.collection_row_action_identity.unit verify.frontend.action_view_page_size_runtime.unit

verify.frontend.release.unit: verify.frontend.official_icon.unit verify.frontend.global_component_capability.unit verify.frontend.component_driver_takeover.unit verify.frontend.scene_component_bridge.unit verify.frontend.scene_component_bridge.guard verify.frontend.primitive_adapter.unit verify.frontend.navigation_shell.unit verify.frontend.product_page_header.unit verify.frontend.product_page_pattern.unit verify.frontend.professional_component_registry.unit verify.frontend.professional_base_field.unit verify.frontend.professional_business_value.unit verify.frontend.professional_relation_field.unit verify.frontend.professional_detail_collection.unit verify.frontend.professional_workflow.unit verify.frontend.professional_audit.unit verify.frontend.professional_collaboration.unit verify.frontend.professional_relation_lifecycle.unit verify.frontend.contract_prompt_action_presentation.unit verify.frontend.low_code_field_create_dialog.unit verify.frontend.form_header_action_primitives.unit verify.frontend.action_view_page_actions.unit verify.frontend.relational_action_primitives.unit verify.frontend.state_dashboard.unit verify.frontend.professional.extensions.unit verify.frontend.boq_import_preview.unit verify.frontend.chart_dataset.unit verify.frontend.mobile_viewport.unit verify.frontend.intent_request_identity.unit verify.frontend.intent_request_coalescing.unit verify.frontend.collection_row_action_identity.unit verify.frontend.action_view_page_size_runtime.unit

verify.frontend.lint.src: guard.prod.forbid
	@scripts/dev/pnpm_exec.sh -C frontend/apps/web lint:src

.PHONY: verify.frontend.lint
verify.frontend.lint: guard.prod.forbid
	@scripts/dev/pnpm_exec.sh -C frontend/apps/web lint

.PHONY: verify.frontend.page_width_contract.guard verify.frontend.workspace_content_alignment.guard verify.frontend.workspace_layout_contract.unit verify.frontend.form_canvas_layout.guard verify.frontend.form_canvas_layout.unit verify.frontend.form_grid_span.browser verify.frontend.localized_display.unit verify.frontend.list_optional_columns.unit verify.frontend.collection_view_semantics.unit verify.frontend.action_surface_renderer_registry.unit verify.frontend.auth_credential.guard verify.frontend.auth_surface.guard verify.frontend.all_list_visual.audit verify.frontend.density.baseline verify.frontend.runtime_environment.unit audit.frontend.industry_agnostic verify.frontend.industry_agnostic.guard verify.frontend.industry_agnostic.audit.unit

verify.frontend.auth_credential.guard: guard.prod.forbid
	@python3 scripts/verify/auth_credential_frontend_guard.py
	@node scripts/verify/frontend_evidence_capture_guard.test.mjs

verify.frontend.auth_surface.guard: guard.prod.forbid
	@python3 scripts/verify/frontend_auth_surface_guard.py

audit.frontend.industry_agnostic: guard.prod.forbid
	@python3 scripts/verify/frontend_industry_agnostic_audit.py

verify.frontend.industry_agnostic.audit.unit: guard.prod.forbid
	@python3 scripts/verify/test_frontend_industry_agnostic_audit.py

verify.frontend.industry_agnostic.guard: guard.prod.forbid verify.frontend.industry_agnostic.audit.unit
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

# Visual density baseline gate: asserts rendered list/form metrics match the
# product density token contract (list th 42px / row 46px / query-bar 46px;
# form control 36px / readonly 14px). Requires a reachable frontend (dev server
# or acceptance stack) at FRONTEND_URL. Contract reference:
# docs/audit/visual_density_baseline_v1.md
verify.frontend.density.baseline: guard.prod.forbid
	@E2E_PASSWORD="$${E2E_PASSWORD:?E2E_PASSWORD is required}" \
		FRONTEND_URL="$${FRONTEND_URL:-http://127.0.0.1:5175}" \
		E2E_LOGIN="$${E2E_LOGIN:-fixture_role_activity_accounting}" \
		node scripts/verify/frontend_density_baseline_audit.mjs

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
	@python3 -m unittest scripts.verify.test_frontend_form_canvas_wide_grid_guard
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

.PHONY: verify.frontend.delivery_hardening.guard verify.frontend.delivery_hardening.inventory verify.frontend.release_navigation_policy.guard verify.frontend.role_surface_exposure_declaration.guard
verify.frontend.delivery_hardening.guard: guard.prod.forbid
	@python3 scripts/verify/frontend_delivery_hardening_guard.py

verify.frontend.delivery_hardening.inventory: guard.prod.forbid
	@python3 scripts/verify/frontend_delivery_ui_inventory.py

verify.frontend.role_surface_exposure_declaration.guard: guard.prod.forbid
	@python3 -m unittest scripts/verify/test_role_surface_exposure_declaration_guard.py
	@python3 scripts/verify/role_surface_exposure_declaration_guard.py

verify.frontend.release_navigation_policy.guard: guard.prod.forbid verify.frontend.role_surface_exposure_declaration.guard
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
	@node frontend/apps/web/scripts/onchange_roundtrip_race_test.mjs

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
	@python3 scripts/verify/test_scene_inventory_freeze_guard.py
	@python3 scripts/verify/scene_inventory_freeze_guard.py

.PHONY: verify.scene.inventory.test_boundary.guard
verify.scene.inventory.test_boundary.guard: guard.prod.forbid
	@python3 scripts/verify/test_scene_inventory_test_boundary_guard.py
	@python3 scripts/verify/scene_inventory_test_boundary_guard.py

.PHONY: verify.scene.inventory.hygiene.guard
verify.scene.inventory.hygiene.guard: \
		verify.scene.inventory.freeze.guard \
		verify.scene.inventory.test_boundary.guard
	@echo "[verify.scene.inventory.hygiene.guard] PASS"

.PHONY: gate.scene.inventory.hygiene.strict
gate.scene.inventory.hygiene.strict: verify.scene.inventory.hygiene.guard
	@echo "[gate.scene.inventory.hygiene.strict] PASS"

.PHONY: verify.scene.role.policy.consistency.guard
verify.scene.role.policy.consistency.guard: guard.prod.forbid
	@python3 scripts/verify/scene_role_policy_consistency_guard.py

.PHONY: verify.scene.data_source.schema.guard
verify.scene.data_source.schema.guard: guard.prod.forbid
	@python3 scripts/verify/scene_data_source_schema_guard.py

.PHONY: verify.scene.r3.runtime.guard
verify.scene.r3.runtime.guard: guard.prod.forbid
	@python3 scripts/verify/test_scene_r3_action_target_scene_resolution.py
	@python3 scripts/verify/scene_r3_runtime_guard.py

.PHONY: verify.scene.r3.runtime.strict
verify.scene.r3.runtime.strict: guard.prod.forbid
	@python3 scripts/verify/test_scene_r3_action_target_scene_resolution.py
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

.PHONY: verify.frontend.saved_search_capability.unit
verify.frontend.saved_search_capability.unit: guard.prod.forbid
	@python3 -m py_compile addons/smart_core/app_config_engine/models/app_search_config.py addons/smart_core/tests/test_saved_search_capability_projection.py
	@python3 addons/smart_core/tests/test_saved_search_capability_projection.py
	@python3 addons/smart_core/tests/test_search_favorite_handler_boundaries.py

.PHONY: verify.frontend.record_denied_reason.unit
verify.frontend.record_denied_reason.unit: guard.prod.forbid
	@python3 -m py_compile addons/smart_core/utils/delete_policy.py addons/smart_core/tests/test_delete_policy_denied_reason.py addons/smart_core/tests/test_record_denied_reason_projection.py
	@python3 addons/smart_core/tests/test_delete_policy_denied_reason.py
	@python3 addons/smart_core/tests/test_record_denied_reason_projection.py

.PHONY: verify.frontend.contract_record_action_state.unit
verify.frontend.contract_record_action_state.unit: guard.prod.forbid
	@node scripts/verify/frontend_contract_record_action_state.test.mjs

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

.PHONY: verify.frontend.canonical_form_presenter.unit verify.frontend.hierarchy_command_authority.unit verify.frontend.readonly_main_data_coverage.unit verify.frontend.create_default_hydration.unit verify.frontend.create_record_user_journey.unit verify.frontend.j13_required_value_semantics.unit
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
	@node --test frontend/apps/web/scripts/native_attachment_partial_failure_test.mjs

.PHONY: verify.frontend.contract_field_occurrence_identity.unit
verify.frontend.contract_field_occurrence_identity.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/contract_field_occurrence_identity_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/contract-field-occurrence-identity-test.mjs >/dev/null
	@node /tmp/contract-field-occurrence-identity-test.mjs

.PHONY: verify.frontend.contract_error_business_ownership.unit
verify.frontend.contract_error_business_ownership.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/contract_error_business_ownership_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/contract-error-business-ownership-test.mjs >/dev/null
	@node /tmp/contract-error-business-ownership-test.mjs

.PHONY: verify.frontend.contract_form_save_failure_recovery.unit
verify.frontend.contract_form_save_failure_recovery.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/contract_form_save_failure_recovery_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/contract-form-save-failure-recovery-test.mjs >/dev/null
	@node /tmp/contract-form-save-failure-recovery-test.mjs

.PHONY: verify.frontend.contract_form_dirty_semantics.unit
verify.frontend.contract_form_dirty_semantics.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/contract_form_dirty_semantics_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --alias:vue=$(ROOT_DIR)/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js --outfile=/tmp/contract-form-dirty-semantics-test.mjs >/dev/null
	@node /tmp/contract-form-dirty-semantics-test.mjs

.PHONY: verify.frontend.standard_form_composition.unit
verify.frontend.standard_form_composition.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/standard_form_composition_adoption_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/standard-form-composition-adoption-test.mjs >/dev/null
	@node /tmp/standard-form-composition-adoption-test.mjs

.PHONY: verify.frontend.adopted_form_engine_decision.unit
verify.frontend.adopted_form_engine_decision.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/adopted_form_engine_decision_test.ts --bundle --platform=node --format=esm --loader:.css=empty --resolve-extensions=.tsx,.ts,.jsx,.js,.css,.json,.mjs --alias:vue=./frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js --alias:tdesign-vue-next=$(ROOT_DIR)/frontend/packages/ui/node_modules/tdesign-vue-next --outfile=/tmp/adopted-form-engine-decision-test.mjs >/dev/null
	@node /tmp/adopted-form-engine-decision-test.mjs

.PHONY: verify.frontend.standard_collection_composition.unit
verify.frontend.standard_collection_composition.unit: guard.prod.forbid
	@node frontend/apps/web/scripts/list_surface_component_test.mjs
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/standard_collection_composition_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --loader:.css=empty --resolve-extensions=.tsx,.ts,.jsx,.js,.css,.json,.mjs --outfile=/tmp/standard-collection-composition-test.mjs >/dev/null
	@node /tmp/standard-collection-composition-test.mjs

.PHONY: verify.frontend.list_order_field_contract.unit
verify.frontend.list_order_field_contract.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/list_order_field_contract_test.ts --bundle --platform=node --format=esm --outfile=/tmp/list-order-field-contract-test.mjs >/dev/null
	@node /tmp/list-order-field-contract-test.mjs

.PHONY: verify.frontend.standard_shell_composition.unit
verify.frontend.standard_shell_composition.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/standard_shell_composition_test.ts --bundle --platform=node --format=esm --outfile=/tmp/standard-shell-composition-test.mjs >/dev/null
	@node /tmp/standard-shell-composition-test.mjs

.PHONY: verify.frontend.adopted_form_validation_identity.unit
verify.frontend.adopted_form_validation_identity.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/adopted_form_validation_identity_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --loader:.css=empty --resolve-extensions=.tsx,.ts,.jsx,.js,.css,.json,.mjs --alias:vue=./frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js --outfile=/tmp/adopted-form-validation-identity-test.mjs >/dev/null
	@node /tmp/adopted-form-validation-identity-test.mjs

.PHONY: verify.frontend.j13_required_value_semantics.unit
verify.frontend.j13_required_value_semantics.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/j13_required_value_semantics_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/j13-required-value-semantics-test.mjs >/dev/null
	@node /tmp/j13-required-value-semantics-test.mjs

.PHONY: verify.frontend.native_section_navigation.unit verify.frontend.native_collaboration_presentation.unit
verify.frontend.native_section_navigation.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/native_section_navigation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/native-section-navigation-test.mjs >/dev/null
	@node /tmp/native-section-navigation-test.mjs

verify.frontend.native_collaboration_presentation.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/native_collaboration_presentation_test.ts --bundle --platform=node --format=esm --outfile=/tmp/native-collaboration-presentation-test.mjs >/dev/null
	@node /tmp/native-collaboration-presentation-test.mjs

.PHONY: verify.form_structure_authority_unification.unit
verify.form_structure_authority_unification.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_form_structure_authority_unification

.PHONY: verify.frontend.cross_model_action_navigation.unit
verify.frontend.cross_model_action_navigation.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/cross_model_action_navigation_test.ts --bundle --platform=node --format=esm --define:import.meta.env='{}' --outfile=/tmp/cross-model-action-navigation-test.mjs >/dev/null
	@node /tmp/cross-model-action-navigation-test.mjs

.PHONY: verify.frontend.playwright_vendor_coupling.guard
verify.frontend.playwright_vendor_coupling.guard: guard.prod.forbid
	@python3 scripts/verify/playwright_vendor_coupling_guard.py
	@python3 -m unittest scripts.verify.test_playwright_vendor_coupling_guard

verify.frontend.quick.gate: verify.frontend.j13_required_value_semantics.unit verify.frontend.canonical_form_presenter.unit verify.frontend.hierarchy_command_authority.unit verify.frontend.create_default_hydration.unit verify.frontend.create_record_user_journey.unit verify.frontend.contract_field_occurrence_identity.unit verify.frontend.contract_form_save_failure_recovery.unit verify.frontend.contract_error_business_ownership.unit verify.frontend.standard_form_composition.unit verify.frontend.adopted_form_engine_decision.unit verify.frontend.adopted_form_validation_identity.unit verify.frontend.standard_collection_composition.unit verify.frontend.standard_shell_composition.unit verify.frontend.native_section_navigation.unit verify.frontend.native_collaboration_presentation.unit verify.frontend.cross_model_action_navigation.unit verify.frontend.contract_render_profile.unit verify.frontend.collection_status_presentation.unit
verify.frontend.quick.gate: verify.frontend.playwright_vendor_coupling.guard
verify.frontend.quick.gate: verify.frontend.business_entry.evidence_scope.unit
verify.frontend.quick.gate: guard.prod.forbid verify.frontend.workspace_content_alignment.guard verify.frontend.page_identity verify.frontend.contract_header_action.unit verify.frontend.readonly_main_data_coverage.unit verify.frontend.relation_entry.contract_guard verify.frontend.relation_read_closure.guard verify.frontend.modifiers_runtime.guard verify.frontend.onchange_roundtrip.guard verify.frontend.onchange_contract_schema.guard verify.frontend.onchange_line_patch.guard verify.frontend.x2many_command_semantic.guard verify.frontend.x2many_inline_edit.guard verify.contract.subviews.guard verify.frontend.view_type_render_coverage.guard verify.frontend.view_type_contract_semantic.guard verify.frontend.search_groupby_savedfilters.guard verify.frontend.saved_search_capability.unit verify.frontend.record_denied_reason.unit verify.frontend.contract_record_action_state.unit verify.frontend.group_summary_runtime.guard verify.frontend.grouped_rows_runtime.guard verify.frontend.grouped_pagination_semantic.guard verify.frontend.grouped_pagination_semantic_drift.guard verify.frontend.grouped_contract_consistency.guard verify.frontend.grouped_drift_summary.baseline.guard verify.frontend.typecheck.strict verify.frontend.build
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

.PHONY: verify.frontend.bound_form_configuration.unit
verify.frontend.bound_form_configuration.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/bound_form_configuration_test.ts --bundle --platform=node --format=esm --outfile=/tmp/bound-form-configuration-test.mjs >/dev/null
	@node /tmp/bound-form-configuration-test.mjs

.PHONY: verify.frontend.explicit_any.unit verify.frontend.typed_dependencies.unit
verify.frontend.explicit_any.unit: guard.prod.forbid
	@node --test scripts/verify/frontend_explicit_any_test.mjs
verify.frontend.typed_dependencies.unit: guard.prod.forbid
	@node scripts/verify/typed_dependency_contract_test.mjs

.PHONY: verify.frontend.form_designer_actions.unit
verify.frontend.form_designer_actions.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/form_designer_actions_test.ts --bundle --platform=node --format=esm --outfile=/tmp/form-designer-actions-test.mjs >/dev/null
	@node /tmp/form-designer-actions-test.mjs

.PHONY: verify.frontend.workspace_composition.unit
verify.frontend.workspace_composition.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_workspace_composition_wiring
	@python3 scripts/verify/frontend_home_layout_section_coverage_guard.py

.PHONY: verify.frontend.activation_form_engine.unit
verify.frontend.activation_form_engine.unit: guard.prod.forbid
	@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/activation_form_engine_test.ts --bundle --platform=node --format=esm --loader:.css=empty --resolve-extensions=.tsx,.ts,.jsx,.js,.css,.json,.mjs --alias:vue=./frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js --alias:tdesign-vue-next=$(ROOT_DIR)/frontend/packages/ui/node_modules/tdesign-vue-next --outfile=/tmp/activation-form-engine-test.mjs >/dev/null
	@node /tmp/activation-form-engine-test.mjs

.PHONY: verify.frontend.public_auth_bootstrap.unit
verify.frontend.public_auth_bootstrap.unit: guard.prod.forbid
	@python3 addons/smart_core/tests/test_page_contracts_builder_boundaries.py
	@node --test frontend/apps/web/scripts/public_auth_bootstrap_test.mjs

.PHONY: verify.frontend.field_configuration_component.unit
verify.frontend.field_configuration_component.unit: guard.prod.forbid
	@node frontend/apps/web/scripts/field_configuration_component_test.mjs

.PHONY: verify.contract.form_field_policy.unit
verify.contract.form_field_policy.unit: guard.prod.forbid
	@python3 scripts/verify/test_form_field_policy.py

# This target uses the registered preview, not exported .env.dev defaults.
# Validate invocation origins before replacing defaults. DB origins were captured
# by Makefile before the env include; never wash an explicit conflicting input.
SC_LIST_PREVIEW_URL_KEYS := SC_ACCEPTANCE_FRONTEND_URL FRONTEND_URL ACCEPTANCE_BASE_URL BASE_URL SC_ACCEPTANCE_API_URL
SC_LIST_PREVIEW_DB_KEYS := SC_ACCEPTANCE_DATABASE E2E_DB FRONTEND_ACCEPTANCE_DB
# Arguments: diagnostic name, origin, value, exact registered value.
define sc_list_preview_explicit_input
$(if $(filter command line environment override,$(2)),$(if $(strip $(3)),$(if $(filter-out $(4),$(strip $(3))),$(error DENY standard list explicit $(1) mismatch),$(if $(filter-out 1,$(words $(3))),$(error DENY standard list explicit $(1) mismatch)))))
endef

.PHONY: verify.frontend.list_surface_search_contract.unit verify.frontend.list_surface_structure.browser
# The list/detail browser probe consumes the backend exact-instance contract
# receipt: the approved record, target route and sealed semantics come from the
# live ui.contract.v2 read, never from the first rendered row or a selector.
SC_ACCEPTANCE_CONTRACT_RECEIPT ?= artifacts/backend/dev_acceptance_release_probe.json
SC_ACCEPTANCE_CONTRACT_DECLARATION ?= config/acceptance/backend_contract_instance_v1.json
SC_ACCEPTANCE_REQUIRED_SHA ?= $(if $(ACCEPTANCE_TARGET_SHA),$(ACCEPTANCE_TARGET_SHA),$(shell git rev-parse HEAD))
verify.frontend.list_surface_search_contract.unit: guard.prod.forbid
	@python3 -m unittest scripts.verify.test_frontend_list_surface_search_contract
	@node scripts/verify/acceptance_contract_receipt_test.mjs
verify.frontend.list_surface_structure.browser: guard.prod.forbid verify.frontend.list_surface_search_contract.unit
	$(foreach key,$(SC_LIST_PREVIEW_URL_KEYS),$(call sc_list_preview_explicit_input,$(key),$(origin $(key)),$($(key)),http://127.0.0.1:5180))
	$(foreach key,$(SC_LIST_PREVIEW_DB_KEYS),$(call sc_list_preview_explicit_input,$(key),$(origin $(key)),$($(key)),sc_frontend_acceptance))
	$(foreach key,DB_NAME DB BD,$(call sc_list_preview_explicit_input,$(key),$(REQUESTED_$(key)_ORIGIN),$(REQUESTED_$(key)),sc_frontend_acceptance))
	@$(foreach key,$(SC_LIST_PREVIEW_URL_KEYS),$(key)=http://127.0.0.1:5180) $(foreach key,$(SC_LIST_PREVIEW_DB_KEYS) DB_NAME DB BD,$(key)=sc_frontend_acceptance) SC_FRONTEND_RELEASE_CI_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="$(SC_ACCEPTANCE_RUNTIME_PROFILE)" SC_ACCEPTANCE_REQUIRE_CONTRACT=1 SC_ACCEPTANCE_EXPECTED_SHA="$(SC_ACCEPTANCE_REQUIRED_SHA)" SC_ACCEPTANCE_CONTRACT_RECEIPT="$(SC_ACCEPTANCE_CONTRACT_RECEIPT)" SC_ACCEPTANCE_CONTRACT_DECLARATION="$(SC_ACCEPTANCE_CONTRACT_DECLARATION)" bash scripts/dev/frontend_acceptance_operation_entry.sh standard-list-surface-browser

.PHONY: verify.daily_dev.list_surface.readonly.browser
# The declared instance receipt names one exact runtime (config/acceptance/
# backend_contract_instance_v1.json). This lane resolves the daily profile
# (config/frontend/acceptance_environments_v1.json profiles.daily), which is a
# different declared environment, so the instance contract is enforced only when
# the caller explicitly requires it:
#   SC_ACCEPTANCE_REQUIRE_CONTRACT=1 [DB_NAME=<receipt runtime>] make <this target>
# A receipt supplied for another runtime still fails closed on the database
# binding; this lane never silently skips a declared prerequisite.
verify.daily_dev.list_surface.readonly.browser: guard.prod.forbid
	@test -n "$(ACCEPTANCE_TARGET_SHA)" || (echo "explicit ACCEPTANCE_TARGET_SHA is required"; exit 2)
	@SC_ACCEPTANCE_PROFILE=daily SC_ACCEPTANCE_OPERATION=readonly SC_ACCEPTANCE_EXPECTED_SHA="$(ACCEPTANCE_TARGET_SHA)" SC_ACCEPTANCE_FRONTEND_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_API_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_DATABASE="$(DB_NAME)" SC_ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" SC_ACCEPTANCE_REQUIRE_CONTRACT="$(SC_ACCEPTANCE_REQUIRE_CONTRACT)" SC_ACCEPTANCE_CONTRACT_RECEIPT="$(if $(filter command line environment override,$(origin SC_ACCEPTANCE_REQUIRE_CONTRACT)),$(SC_ACCEPTANCE_CONTRACT_RECEIPT),)" SC_ACCEPTANCE_CONTRACT_DECLARATION="$(SC_ACCEPTANCE_CONTRACT_DECLARATION)" LIST_SURFACE_VIEWPORTS=1440,390 node scripts/verify/frontend_list_surface_structure_browser.mjs

.PHONY: verify.frontend.business_entry.lifecycle.browser
# Owner-authorized product acceptance for the 项目启停管理 formal business entry
# (project.project lifecycle) on the external daily development server. This lane
# MUTATES the declared record, and the owner explicitly authorized mutating the
# sc_demo semi-production dataset, so it is deliberately NOT bound to the readonly
# daily profile. Its write authority is the explicit SC_ENTRY_WRITE_CONFIRM token
# plus the run-declared environment authority; the served revision must equal
# ACCEPTANCE_TARGET_SHA and the served database must equal DB_NAME before any
# action runs.
verify.frontend.business_entry.lifecycle.browser: guard.prod.forbid
	@test -n "$(ACCEPTANCE_TARGET_SHA)" || (echo "explicit ACCEPTANCE_TARGET_SHA is required"; exit 2)
	@test -n "$(ACCEPTANCE_LOGIN)" -a -n "$(ACCEPTANCE_PASSWORD)" || (echo "ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD must be supplied through the environment"; exit 2)
	@test -n "$(ACCEPTANCE_RECORD_RESOLUTION)" -a -f "$(ACCEPTANCE_RECORD_RESOLUTION)" || (echo "ACCEPTANCE_RECORD_RESOLUTION must point at the managed resolution body"; exit 2)
	@test "$(SC_ENTRY_WRITE_CONFIRM)" = "DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE" || (echo "SC_ENTRY_WRITE_CONFIRM=DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE is required"; exit 2)
	@SC_ACCEPTANCE_FRONTEND_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_DATABASE="$(DB_NAME)" SC_ACCEPTANCE_TARGET_SHA="$(ACCEPTANCE_TARGET_SHA)" ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" ACCEPTANCE_RECORD_RESOLUTION="$(ACCEPTANCE_RECORD_RESOLUTION)" SC_ENTRY_RECORD_XMLID="$(SC_ENTRY_RECORD_XMLID)" SC_ENTRY_WRITE_CONFIRM="$(SC_ENTRY_WRITE_CONFIRM)" SC_ENTRY_DRY_RUN="$(SC_ENTRY_DRY_RUN)" SC_ACCEPTANCE_OUTPUT_DIR="$(SC_ACCEPTANCE_OUTPUT_DIR)" node scripts/verify/frontend_business_entry_lifecycle_browser.mjs

.PHONY: verify.frontend.business_entry.payment_request.browser
# Owner-authorized product acceptance for the 付款申请 formal business entry
# (payment.request) detail collection on the external daily development server.
# It reproduces the recorded gap "edit an existing imported detail row, then save
# is refused as a duplicate row" and locks the observed behaviour to the runtime
# contract and the persisted result. Like the lifecycle lane it MUTATES the
# declared fixture carrier inside the owner-authorized sc_demo acceptance fixture
# and restores its declared empty start state before returning, so it is
# deliberately NOT bound to the readonly daily profile. Its write authority is the
# explicit SC_ENTRY_WRITE_CONFIRM token; the served revision must equal
# ACCEPTANCE_TARGET_SHA and the served database must equal DB_NAME before any
# action runs.
verify.frontend.business_entry.payment_request.browser: guard.prod.forbid
	@test -n "$(ACCEPTANCE_TARGET_SHA)" || (echo "explicit ACCEPTANCE_TARGET_SHA is required"; exit 2)
	@test -n "$(ACCEPTANCE_LOGIN)" -a -n "$(ACCEPTANCE_PASSWORD)" || (echo "ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD must be supplied through the environment"; exit 2)
	@test -n "$(ACCEPTANCE_RECORD_RESOLUTION)" -a -f "$(ACCEPTANCE_RECORD_RESOLUTION)" || (echo "ACCEPTANCE_RECORD_RESOLUTION must point at the managed resolution body"; exit 2)
	@test "$(SC_ENTRY_WRITE_CONFIRM)" = "DRIVE_DAILY_SC_DEMO_PAYMENT_REQUEST_ONE2MANY" || (echo "SC_ENTRY_WRITE_CONFIRM=DRIVE_DAILY_SC_DEMO_PAYMENT_REQUEST_ONE2MANY is required"; exit 2)
	@SC_ACCEPTANCE_FRONTEND_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_DATABASE="$(DB_NAME)" SC_ACCEPTANCE_TARGET_SHA="$(ACCEPTANCE_TARGET_SHA)" ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" ACCEPTANCE_RECORD_RESOLUTION="$(ACCEPTANCE_RECORD_RESOLUTION)" SC_ENTRY_WRITE_CONFIRM="$(SC_ENTRY_WRITE_CONFIRM)" SC_ACCEPTANCE_OUTPUT_DIR="$(SC_ACCEPTANCE_OUTPUT_DIR)" node scripts/verify/business_entry_payment_request_one2many_browser.mjs

.PHONY: verify.frontend.business_entry.general_contract.browser
# Owner-authorized product acceptance for the 日常合同 formal business entry
# (sc.general.contract) on the external daily development server. It drives the
# declared record ladder (submit -> confirmed, complete -> signed) and the declared
# terminal rung from the runtime ui.contract.v2 workflowContract, walks the declared
# list query/filter/paging surface with its detail-return context, and proves the
# negative authority case for a role holding none of the entry's declared groups.
# Like the lifecycle lane it MUTATES the declared fixture carrier inside the
# owner-authorized sc_demo acceptance fixture, so it is deliberately NOT bound to
# the readonly daily profile. Its write authority is the explicit
# SC_ENTRY_WRITE_CONFIRM token; the served revision must equal ACCEPTANCE_TARGET_SHA
# and the served database must equal DB_NAME before any action runs.
verify.frontend.business_entry.general_contract.browser: guard.prod.forbid
	@test -n "$(ACCEPTANCE_TARGET_SHA)" || (echo "explicit ACCEPTANCE_TARGET_SHA is required"; exit 2)
	@test -n "$(ACCEPTANCE_LOGIN)" -a -n "$(ACCEPTANCE_PASSWORD)" || (echo "ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD must be supplied through the environment"; exit 2)
	@test -n "$(ACCEPTANCE_RECORD_RESOLUTION)" -a -f "$(ACCEPTANCE_RECORD_RESOLUTION)" || (echo "ACCEPTANCE_RECORD_RESOLUTION must point at the managed resolution body"; exit 2)
	@test "$(SC_ENTRY_WRITE_CONFIRM)" = "DRIVE_DAILY_SC_DEMO_GENERAL_CONTRACT" || (echo "SC_ENTRY_WRITE_CONFIRM=DRIVE_DAILY_SC_DEMO_GENERAL_CONTRACT is required"; exit 2)
	@SC_ACCEPTANCE_FRONTEND_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_DATABASE="$(DB_NAME)" SC_ACCEPTANCE_TARGET_SHA="$(ACCEPTANCE_TARGET_SHA)" ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" ACCEPTANCE_RECORD_RESOLUTION="$(ACCEPTANCE_RECORD_RESOLUTION)" SC_ENTRY_RECORD_XMLID="$(SC_ENTRY_RECORD_XMLID)" SC_ENTRY_ENTRY_MODE="$(SC_ENTRY_ENTRY_MODE)" SC_ENTRY_DENIED_ROLE_LOGIN="$(SC_ENTRY_DENIED_ROLE_LOGIN)" SC_ENTRY_WRITE_CONFIRM="$(SC_ENTRY_WRITE_CONFIRM)" SC_ENTRY_DRY_RUN="$(SC_ENTRY_DRY_RUN)" SC_ACCEPTANCE_OUTPUT_DIR="$(SC_ACCEPTANCE_OUTPUT_DIR)" node scripts/verify/business_entry_general_contract_browser.mjs

.PHONY: verify.frontend.business_entry.matrix.browser
# Declaration-driven read-only product-surface acceptance over the formal business
# entry matrix (docs/product/frontend_business_entry_acceptance_v1.csv). It selects
# one declared batch (SC_ENTRY_MATRIX_DOMAIN and/or SC_ENTRY_MATRIX_KEYS), resolves
# every entry inside the acting role's RELEASED navigation (not merely the raw
# route), walks the declared list lifecycle, the search filter built from a
# rendered row identity, the first-row detail read-back and the declared
# pagination surface, then proves the negative authority case for a role holding
# none of the entry's declared groups. It is read-only: an entry whose overlay
# declares a mutating expectation fails closed unless SC_ENTRY_WRITE_CONFIRM
# carries the explicit token, so the lane never slips a write into a read batch.
verify.frontend.business_entry.matrix.browser: guard.prod.forbid
	@test -n "$(ACCEPTANCE_TARGET_SHA)" || (echo "explicit ACCEPTANCE_TARGET_SHA is required"; exit 2)
	@test -n "$(ACCEPTANCE_LOGIN)" -a -n "$(ACCEPTANCE_PASSWORD)" || (echo "ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD must be supplied through the environment"; exit 2)
	@SC_ACCEPTANCE_FRONTEND_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_DATABASE="$(DB_NAME)" SC_ACCEPTANCE_TARGET_SHA="$(ACCEPTANCE_TARGET_SHA)" ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" SC_ENTRY_MATRIX_DOMAIN="$(SC_ENTRY_MATRIX_DOMAIN)" SC_ENTRY_MATRIX_KEYS="$(SC_ENTRY_MATRIX_KEYS)" SC_ENTRY_MATRIX_INCLUDE_PASSED="$(SC_ENTRY_MATRIX_INCLUDE_PASSED)" SC_ENTRY_MATRIX_CSV="$(SC_ENTRY_MATRIX_CSV)" SC_ENTRY_MATRIX_OVERLAY="$(SC_ENTRY_MATRIX_OVERLAY)" SC_ENTRY_WRITE_CONFIRM="$(SC_ENTRY_WRITE_CONFIRM)" SC_ACCEPTANCE_OUTPUT_DIR="$(SC_ACCEPTANCE_OUTPUT_DIR)" node scripts/verify/business_entry_matrix_browser.mjs

# Reuse-first entry for the same declaration-driven surface. It declares the
# matrix as evidence units, asks scripts/ops/evidence_scope.py what is still
# affected under the current inputs, executes exactly that key set through the
# existing probe, then records the outcome. An unchanged passing entry is reused
# instead of re-collected; a targeted rerun of a covered entry is refused unless
# SC_ENTRY_SCOPE_REVERIFY_REASON states why; re-walking every entry needs
# SC_ENTRY_SCOPE_FULL=1 together with SC_ENTRY_SCOPE_FULL_REASON. The plan this
# entry consumes is the negative-closure snapshot below, so refresh that first
# when the principal closures could have moved. When only the mapping from an
# observation to a recorded status was wrong, set SC_ENTRY_SCOPE_RECORD_EXISTING
# to the bound summary.json together with SC_ENTRY_SCOPE_RECORD_EXISTING_REASON
# and SC_ENTRY_SCOPE_PLAN=the original selection.json: the entry then re-folds
# that observation instead of re-walking the surface.
SC_ENTRY_MATRIX_CLOSURES ?= artifacts/frontend-business-entry-matrix/negative_closures.json
SC_ENTRY_SCOPE_LEDGER ?= .runtime/evidence-scope/verify.frontend.business_entry.matrix.browser.json
SC_ENTRY_SCOPE_REVERIFY_REASON ?=
SC_ENTRY_SCOPE_FULL ?=
SC_ENTRY_SCOPE_FULL_REASON ?=
SC_ENTRY_SCOPE_RECORD_EXISTING ?=
SC_ENTRY_SCOPE_RECORD_EXISTING_REASON ?=
SC_ENTRY_SCOPE_PLAN ?=

.PHONY: verify.frontend.business_entry.negative_closures verify.frontend.business_entry.matrix.incremental verify.frontend.business_entry.matrix.evidence_scope.status verify.frontend.business_entry.evidence_scope.unit

# Bounded read-only diagnostic: observe each declared denied-role candidate's
# capability closure and released navigation count. Set SC_ENTRY_MATRIX_CLOSURES_FROM
# to an already-recorded observation to adopt it instead of re-walking the logins.
verify.frontend.business_entry.negative_closures: guard.prod.forbid
	@test -n "$(ACCEPTANCE_BASE_URL)" || (echo "ACCEPTANCE_BASE_URL is required"; exit 2)
	@test -n "$(ACCEPTANCE_PASSWORD)" || (echo "ACCEPTANCE_PASSWORD is required"; exit 2)
	@SC_ACCEPTANCE_FRONTEND_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_DATABASE="$(DB_NAME)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" SC_ENTRY_MATRIX_OVERLAY="$(SC_ENTRY_MATRIX_OVERLAY)" SC_ENTRY_MATRIX_CLOSURES_OUT="$(SC_ENTRY_MATRIX_CLOSURES)" SC_ENTRY_MATRIX_CLOSURES_FROM="$(SC_ENTRY_MATRIX_CLOSURES_FROM)" node scripts/verify/business_entry_negative_closures.mjs

verify.frontend.business_entry.matrix.incremental: guard.prod.forbid
	@test -n "$(ACCEPTANCE_TARGET_SHA)" || (echo "explicit ACCEPTANCE_TARGET_SHA is required"; exit 2)
	@test -n "$(ACCEPTANCE_LOGIN)" -a -n "$(ACCEPTANCE_PASSWORD)" || (echo "ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD must be supplied through the environment"; exit 2)
	@SC_ACCEPTANCE_FRONTEND_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_DATABASE="$(DB_NAME)" SC_ACCEPTANCE_TARGET_SHA="$(ACCEPTANCE_TARGET_SHA)" ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" SC_ENTRY_MATRIX_CSV="$(SC_ENTRY_MATRIX_CSV)" SC_ENTRY_MATRIX_OVERLAY="$(SC_ENTRY_MATRIX_OVERLAY)" SC_ENTRY_MATRIX_CLOSURES="$(SC_ENTRY_MATRIX_CLOSURES)" SC_ENTRY_MATRIX_KEYS="$(SC_ENTRY_MATRIX_KEYS)" SC_ENTRY_SCOPE_LEDGER="$(SC_ENTRY_SCOPE_LEDGER)" SC_ENTRY_SCOPE_REVERIFY_REASON="$(SC_ENTRY_SCOPE_REVERIFY_REASON)" SC_ENTRY_SCOPE_FULL="$(SC_ENTRY_SCOPE_FULL)" SC_ENTRY_SCOPE_FULL_REASON="$(SC_ENTRY_SCOPE_FULL_REASON)" SC_ENTRY_SCOPE_RECORD_EXISTING="$(SC_ENTRY_SCOPE_RECORD_EXISTING)" SC_ENTRY_SCOPE_RECORD_EXISTING_REASON="$(SC_ENTRY_SCOPE_RECORD_EXISTING_REASON)" SC_ENTRY_SCOPE_PLAN="$(SC_ENTRY_SCOPE_PLAN)" SC_ENTRY_WRITE_CONFIRM="$(SC_ENTRY_WRITE_CONFIRM)" SC_ACCEPTANCE_OUTPUT_DIR="$(SC_ACCEPTANCE_OUTPUT_DIR)" python3 scripts/verify/business_entry_matrix_incremental.py

# Read-only coverage report for the same surface. It executes nothing: it prints
# how many declared entries are covered, stale, never recorded or blocked.
verify.frontend.business_entry.matrix.evidence_scope.status: guard.prod.forbid
	@test -n "$(ACCEPTANCE_TARGET_SHA)" || (echo "explicit ACCEPTANCE_TARGET_SHA is required"; exit 2)
	@test -n "$(ACCEPTANCE_LOGIN)" -a -n "$(ACCEPTANCE_PASSWORD)" || (echo "ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD must be supplied through the environment"; exit 2)
	@mkdir -p .runtime/evidence-scope
	@SC_ACCEPTANCE_FRONTEND_URL="$(ACCEPTANCE_BASE_URL)" SC_ACCEPTANCE_DATABASE="$(DB_NAME)" SC_ACCEPTANCE_TARGET_SHA="$(ACCEPTANCE_TARGET_SHA)" ACCEPTANCE_LOGIN="$(ACCEPTANCE_LOGIN)" ACCEPTANCE_PASSWORD="$(ACCEPTANCE_PASSWORD)" SC_ENTRY_MATRIX_CSV="$(SC_ENTRY_MATRIX_CSV)" SC_ENTRY_MATRIX_OVERLAY="$(SC_ENTRY_MATRIX_OVERLAY)" SC_ENTRY_MATRIX_CLOSURES="$(SC_ENTRY_MATRIX_CLOSURES)" node scripts/verify/business_entry_matrix_scope.mjs --emit-units .runtime/evidence-scope/units.status.json
	@python3 scripts/ops/evidence_scope.py status --units .runtime/evidence-scope/units.status.json --ledger "$(SC_ENTRY_SCOPE_LEDGER)"

verify.frontend.business_entry.evidence_scope.unit: guard.prod.forbid
	@python3 -m py_compile scripts/ops/evidence_scope.py scripts/verify/business_entry_matrix_incremental.py scripts/verify/business_entry_matrix_scope_seed.py
	@python3 -m unittest scripts.ops.test_evidence_scope scripts.verify.test_business_entry_matrix_incremental

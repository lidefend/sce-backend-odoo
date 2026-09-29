import { computed, ref, type ComputedRef } from 'vue';
import type { RouteLocationNormalizedLoaded } from 'vue-router';
import type { NavNode } from '@sc/schema';
import { BUSINESS_CONFIG_ROUTE_FLAGS, isBusinessConfigRuntimeModel } from '../../app/businessConfigBoundaries';
import { findActionMeta } from '../../app/menu';

type UseBusinessConfigSurfaceScopeParamsOptions = {
  route: RouteLocationNormalizedLoaded;
  menuTree: NavNode[];
};

/**
 * Route query -> business scope. The workbench URL carries the target model,
 * action, view, role and page label; this module owns that translation so the
 * route assembly file does not re-derive business identity inline.
 */
export function useBusinessConfigSurfaceScopeParams(options: UseBusinessConfigSurfaceScopeParamsOptions) {
  const { route } = options;

  function numericQuery(name: string) {
    const parsed = Number(route.query[name] || 0);
    return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : undefined;
  }

  const entryModel = findActionMeta(options.menuTree, numericQuery('action_id') || 0)?.model || '';
  const requestedBusinessModel = String(route.query.model || entryModel).trim();
  const scopeModel = ref(isBusinessConfigRuntimeModel(requestedBusinessModel) ? '' : requestedBusinessModel);
  const scopeActionId = ref(scopeModel.value ? (numericQuery('action_id') || 0) : 0);
  const scopeViewId = ref(scopeModel.value ? (numericQuery('view_id') || 0) : 0);
  const scopeRoleKey = ref(String(route.query.role_key || '').trim());
  const selectedPageLabel = ref(scopeModel.value ? String(route.query.page_label || '').trim() : '');
  const rootMenuXmlid = computed(() => String(route.query.root_menu_xmlid || '').trim());
  const shouldOpenPageList = computed(() => String(route.query[BUSINESS_CONFIG_ROUTE_FLAGS.openPages] || '').trim() === '1');
  const shouldOpenListSearch = computed(() => String(route.query.open_list_search || '').trim() === '1');
  const shouldOpenAnalysis = computed(() => String(route.query.open_analysis || '').trim() === '1');
  const shouldOpenFormConfig = computed(() => String(route.query.open_form_config || '').trim() === '1');
  const currentModel: ComputedRef<string> = computed(() => String(scopeModel.value || '').trim());
  const scopeAction: ComputedRef<number | undefined> = computed(() => {
    const parsed = Number(scopeActionId.value || 0);
    return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : undefined;
  });
  const scopeView: ComputedRef<number | undefined> = computed(() => {
    const parsed = Number(scopeViewId.value || 0);
    return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : undefined;
  });
  const scopeRole: ComputedRef<string | undefined> = computed(() => String(scopeRoleKey.value || '').trim() || undefined);
  const currentModelIsRuntimeConfig = computed(() => isBusinessConfigRuntimeModel(currentModel.value));

  return {
    numericQuery,
    entryModel,
    scopeModel,
    scopeActionId,
    scopeViewId,
    scopeRoleKey,
    selectedPageLabel,
    rootMenuXmlid,
    shouldOpenPageList,
    shouldOpenListSearch,
    shouldOpenAnalysis,
    shouldOpenFormConfig,
    currentModel,
    scopeAction,
    scopeView,
    scopeRole,
    currentModelIsRuntimeConfig,
  };
}

/* eslint-disable @typescript-eslint/no-unused-vars */
import { computed, type ComputedRef, type Ref } from 'vue';
import type { RouteLocationNormalizedLoaded } from 'vue-router';
import { resolveContractV2SurfacePolicies } from '../contracts/v2/store';
import type { ContractV2NormalizedStore } from '../contracts/v2/types';

type UseActionViewPageDisplayStateRuntimeOptions = {
  routeSceneLabel: Ref<string>;
  menuTitle?: ComputedRef<string>;
  actionContract: Ref<ContractV2NormalizedStore | null>;
  injectedTitle: ComputedRef<string>;
  actionMetaName: ComputedRef<string>;
  t: (key: string, fallback?: string) => string;
  searchTerm: Ref<string>;
  activeContractFilterKey: Ref<string>;
  errorMessage: ComputedRef<string>;
  route: RouteLocationNormalizedLoaded;
  isHudEnabled: (route: RouteLocationNormalizedLoaded) => boolean;
};

function isTechnicalViewTitle(value: string) {
  const normalized = String(value || '').trim();
  return /^[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*){1,}\.(?:tree|list|form|kanban|search|graph|pivot|calendar|activity|gantt)$/i.test(normalized);
}

export function useActionViewPageDisplayStateRuntime(options: UseActionViewPageDisplayStateRuntimeOptions) {
  const pageTitle = computed(() => {
    if (options.routeSceneLabel.value) return options.routeSceneLabel.value;
    const menuTitle = String(options.menuTitle?.value || '').trim();
    if (menuTitle) return menuTitle;
    const contractTitle = String(options.actionContract.value?.snapshot.pageInfo.pageName || '').trim();
    if (contractTitle && !isTechnicalViewTitle(contractTitle)) return contractTitle;
    return options.injectedTitle.value || options.actionMetaName.value || options.t('page_title_fallback', '角色首页');
  });

  const emptyReasonText = computed(() => {
    if (options.searchTerm.value.trim() || options.activeContractFilterKey.value) {
      return options.t('empty_reason_filter', '可能由当前筛选条件导致无数据，建议先清除筛选后重试。');
    }
    const surfacePolicies = resolveContractV2SurfacePolicies(options.actionContract.value);
    const fromSurfacePolicy = String(surfacePolicies.empty_reason || '').trim();
    if (fromSurfacePolicy) return fromSurfacePolicy;
    return options.t('empty_reason_default', '');
  });

  const showHud = computed(() => options.isHudEnabled(options.route));

  return {
    pageTitle,
    emptyReasonText,
    showHud,
    errorMessage: options.errorMessage,
  };
}

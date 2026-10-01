import { nextTick, onMounted } from 'vue';

export type BusinessConfigWorkbenchBootstrapDependencies = {
  shouldOpenPageList: Readonly<import('vue').Ref<boolean>>;
  shouldOpenFormConfig: Readonly<import('vue').Ref<boolean>>;
  shouldOpenListSearch: Readonly<import('vue').Ref<boolean>>;
  shouldOpenAnalysis: Readonly<import('vue').Ref<boolean>>;
  loadSurface: ReturnType<typeof import('./useBusinessConfigScopeLifecycle').useBusinessConfigScopeLifecycle>['loadSurface'];
  surface: import('vue').Ref<import('../../api/businessConfig').BusinessConfigSurfacePayload | null>;
  route: import('vue-router').RouteLocationNormalizedLoaded;
  loadChangeSetSafely: () => Promise<void>;
  coverageScan: import('vue').Ref<import('../../api/businessConfig').BusinessConfigCoverageScanPayload | null>;
  scanSystemRootCoverage: ReturnType<typeof import('./useBusinessConfigScopeLifecycle').useBusinessConfigScopeLifecycle>['scanSystemRootCoverage'];
  currentModel: Readonly<import('vue').Ref<string>>;
  scopeAction: Readonly<import('vue').Ref<number | undefined>>;
  clearConsumedOpenIntent: (keys: string[]) => Promise<void>;
  coverageRowMatchesScope: ReturnType<typeof import('./useBusinessConfigScopeLifecycle').useBusinessConfigScopeLifecycle>['coverageRowMatchesScope'];
  focusScanRow: ReturnType<typeof import('./useBusinessConfigScopeLifecycle').useBusinessConfigScopeLifecycle>['focusScanRow'];
  loadListSearchConfig: ReturnType<typeof import('./useBusinessConfigPublishLifecycle').useBusinessConfigPublishLifecycle>['loadListSearchConfig'];
  loadAnalysisConfig: ReturnType<typeof import('./useBusinessConfigPublishLifecycle').useBusinessConfigPublishLifecycle>['loadAnalysisConfig'];
};

export function useBusinessConfigWorkbenchBootstrap(deps: BusinessConfigWorkbenchBootstrapDependencies) {
  const {
    shouldOpenPageList,
    shouldOpenFormConfig,
    shouldOpenListSearch,
    shouldOpenAnalysis,
    loadSurface,
    surface,
    route,
    loadChangeSetSafely,
    coverageScan,
    scanSystemRootCoverage,
    currentModel,
    scopeAction,
    clearConsumedOpenIntent,
    coverageRowMatchesScope,
    focusScanRow,
    loadListSearchConfig,
    loadAnalysisConfig,
  } = deps;

  onMounted(() => {
    void (async () => {
      const openPageListOnMount = shouldOpenPageList.value;
      const openFormConfigOnMount = shouldOpenFormConfig.value;
      const openListSearchOnMount = shouldOpenListSearch.value;
      const openAnalysisOnMount = shouldOpenAnalysis.value;
      await loadSurface();
      if (!surface.value || route.path !== '/admin/business-config') return;
      await loadChangeSetSafely();
      if (openPageListOnMount || !coverageScan.value) await scanSystemRootCoverage();
      if (openFormConfigOnMount && currentModel.value && scopeAction.value) {
        await clearConsumedOpenIntent(['open_form_config']);
        const matched = (coverageScan.value?.items || []).find(coverageRowMatchesScope);
        if (matched) await focusScanRow(matched);
        else await loadSurface();
      }
      if (openListSearchOnMount && currentModel.value) {
        await clearConsumedOpenIntent(['open_list_search']);
        await loadListSearchConfig();
      }
      if (openAnalysisOnMount && currentModel.value) {
        await clearConsumedOpenIntent(['open_analysis']);
        await loadAnalysisConfig();
      }
      const returnScroll = Number(route.query.workbench_scroll || 0);
      if (Number.isFinite(returnScroll) && returnScroll > 0) {
        await nextTick();
        window.scrollTo({ top: returnScroll, behavior: 'auto' });
      }
    })();
  });
}

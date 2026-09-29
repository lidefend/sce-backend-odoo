import { computed, type ComputedRef, type Ref } from 'vue';
import type { Router } from 'vue-router';
import type { BusinessConfigCoverageScanItem } from '../../api/businessConfig';

type RuntimeTarget = { path: string; query: Record<string, string> };

type UseBusinessConfigSurfaceRuntimeRouteOptions = {
  router: Router;
  selectedRuntimeRoute: Ref<BusinessConfigCoverageScanItem['runtime_route'] | null>;
  selectedCoverageRow: ComputedRef<BusinessConfigCoverageScanItem | undefined>;
  scopeAction: ComputedRef<number | undefined>;
};

/**
 * The "open the real page" target. The workbench only ever links to the
 * record's own route; when the scan has no runtime route it falls back to the
 * scope action, never to a page the operator did not select.
 */
export function useBusinessConfigSurfaceRuntimeRoute(options: UseBusinessConfigSurfaceRuntimeRouteOptions) {
  const runtimeRouteTarget: ComputedRef<RuntimeTarget> = computed(() => {
    const runtimeRoute = options.selectedRuntimeRoute.value || {};
    const runtimePath = String(runtimeRoute.path || '').trim();
    if (runtimePath && !runtimePath.startsWith('/admin/business-config')) {
      return { path: runtimePath, query: runtimeRoute.query || {} };
    }
    if (options.scopeAction.value) {
      const query: Record<string, string> = {};
      const menuId = String(options.selectedCoverageRow.value?.runtime_route?.query?.menu_id || '').trim();
      if (menuId) query.menu_id = menuId;
      return { path: `/a/${options.scopeAction.value}`, query };
    }
    return { path: '', query: {} };
  });
  const runtimeRouteHref = computed(() => (
    runtimeRouteTarget.value.path
      ? options.router.resolve({ path: runtimeRouteTarget.value.path, query: runtimeRouteTarget.value.query }).href
      : ''
  ));

  return { runtimeRouteTarget, runtimeRouteHref };
}

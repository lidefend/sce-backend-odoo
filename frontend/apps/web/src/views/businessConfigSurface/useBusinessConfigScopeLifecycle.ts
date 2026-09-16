/* eslint-disable @typescript-eslint/no-explicit-any */
import type { BusinessConfigCoverageScanItem } from '../../api/businessConfig';
import { isBusinessConfigRuntimeModel } from '../../app/businessConfigBoundaries';
import { onBeforeRouteUpdate } from 'vue-router';
import { findActionMeta } from '../../app/menu';
import { ApiError } from '../../api/client';

export function useBusinessConfigScopeLifecycle(deps: Record<string, any>) {
  const { scopeAction, currentModel, scopeView, message, surfaceLoadSeq, loading, error, surfaceError, withSurfaceLoadTimeout, loadBusinessConfigSurface, SURFACE_LOAD_TIMEOUT_MS, scopeRole, session, router, route, surface, scanLoading, coverageScan, scanBusinessConfigCoverage, rootMenuXmlid, selectedPageLabel, scopeModel, scopeActionId, scopeViewId, selectedRuntimeRoute, replaceWorkbenchQuerySilently, focusSelectedConfigPanelOnMobile, resetEditorPanels, runtimeReturnQuery, confirmScopeChange, hasUnsavedEdits, resetScopeDrafts } = deps;
  onBeforeRouteUpdate(async (to) => {
    const actionId = Number(to.query.action_id || 0);
    const model = String(to.query.model || findActionMeta(session.menuTree, actionId)?.model || '').trim();
    const targetModel = isBusinessConfigRuntimeModel(model) ? '' : model;
    const targetAction = targetModel ? actionId : 0;
    const targetView = targetModel ? Number(to.query.view_id || 0) : 0;
    const targetRole = String(to.query.role_key || '').trim();
    if (String(to.query.company_id || '') !== String(route.query.company_id || '')) {
      setMessage('请通过全局公司选择切换公司；不能通过页面参数改变配置作用域。');
      return false;
    }
    if (targetModel === scopeModel.value && targetAction === scopeActionId.value && targetView === scopeViewId.value && targetRole === deps.scopeRoleKey.value) return true;
    if (deps.scopeBusy()) return false;
    if (hasUnsavedEdits() && !(await confirmScopeChange())) return false;
    resetScopeDrafts(); resetEditorPanels(); surface.value = null; selectedRuntimeRoute.value = null;
    scopeModel.value = targetModel; scopeActionId.value = targetAction; scopeViewId.value = targetView; deps.scopeRoleKey.value = targetRole;
    selectedPageLabel.value = String(to.query.page_label || '');
    hydrateSelectedCoverageRowFromScan();
    await loadSurface();
    return true;
  });
  function coverageRowKey(row: Pick<BusinessConfigCoverageScanItem, 'model' | 'action_id' | 'view_id'>) {
    return [
      String(row.model || '').trim(),
      Number(row.action_id || 0),
      Number(row.view_id || 0),
    ].join(':');
  }

  function coverageRowMatchesScope(row: Pick<BusinessConfigCoverageScanItem, 'model' | 'action_id' | 'view_id'>) {
    const actionId = Number(scopeAction.value || 0);
    if (!actionId || Number(row.action_id || 0) !== actionId) return false;
    const rowModel = String(row.model || '').trim();
    const model = String(currentModel.value || '').trim();
    if (model && rowModel && rowModel !== model) return false;
    return !row.view_id || !scopeView.value || Number(row.view_id) === Number(scopeView.value);
  }

  function coverageRowActionId(row: Pick<BusinessConfigCoverageScanItem, 'action_id'>) {
    return Number(row.action_id || 0) || undefined;
  }

  function coverageRowViewId(row: Pick<BusinessConfigCoverageScanItem, 'view_id'>) {
    return Number(row.view_id || 0) || undefined;
  }

  function clearMessage() {
    message.value = { text: '', detail: '' };
  }

  function setMessage(text: string, detail = '') {
    message.value = { text, detail };
  }

  async function loadSurface() {
    const seq = ++surfaceLoadSeq.value;
    loading.value = true;
    surfaceError.value = '';
    clearMessage();
    try {
      const nextSurface = await withSurfaceLoadTimeout(
        loadBusinessConfigSurface({
          business_catalog: true,
          company_id: Number(route.query.company_id || session.recordContext?.company_id || 0) || undefined,
          model: currentModel.value || undefined,
          action_id: scopeAction.value,
          view_id: scopeView.value,
          role_key: scopeRole.value || session.roleSurface?.role_code || undefined,
        }),
        SURFACE_LOAD_TIMEOUT_MS,
      );
      if (seq !== surfaceLoadSeq.value) return;
      surface.value = nextSurface;
    } catch (err) {
      if (seq !== surfaceLoadSeq.value) return;
      if (err instanceof ApiError && err.status === 401) { await session.logout(); await router.replace({ path: '/login', query: { next: route.fullPath } }); return; }
      if (err instanceof ApiError && err.status === 403 && !String(err.message).includes('CONFIG_SCOPE_CONFLICT')) { await router.replace({ path: '/access-denied', query: { from: route.fullPath, reason: err.reasonCode || 'PERMISSION_DENIED' } }); return; }
      surface.value = null;
      surfaceError.value = err instanceof Error ? err.message : '业务配置工作台加载失败';
    } finally {
      if (seq === surfaceLoadSeq.value) {
        loading.value = false;
      }
    }
  }

  async function scanCoverage() {
    scanLoading.value = true;
    error.value = '';
    clearMessage();
    try {
      coverageScan.value = await scanBusinessConfigCoverage({
        business_catalog: true,
        exclude_configuration_models: true,
        model: currentModel.value || undefined,
        view_id: scopeView.value,
        role_key: scopeRole.value || session.roleSurface?.role_code || undefined,
        root_menu_xmlid: rootMenuXmlid.value || undefined,
        include_all_root_menu_actions: false,
        limit: 1000,
      });
      hydrateSelectedCoverageRowFromScan();
    } catch (err) {
      error.value = err instanceof Error ? err.message : '业务配置覆盖检查失败';
    } finally {
      scanLoading.value = false;
    }
  }

  async function scanSystemRootCoverage() {
    if (!surface.value && currentModel.value) { await loadSurface(); if (!surface.value) return; }
    scanLoading.value = true;
    error.value = '';
    clearMessage();
    try {
      coverageScan.value = await scanBusinessConfigCoverage({
        business_catalog: true,
        exclude_configuration_models: true,
        model: undefined,
        view_id: undefined,
        role_key: scopeRole.value || session.roleSurface?.role_code || undefined,
        root_menu_xmlid: rootMenuXmlid.value || undefined,
        include_all_root_menu_actions: true,
        limit: 1000,
      });
      hydrateSelectedCoverageRowFromScan();
    } catch (err) {
      error.value = err instanceof Error ? err.message : '系统根菜单覆盖检查失败';
    } finally {
      scanLoading.value = false;
    }
  }

  async function scanCurrentModel() {
    if (!currentModel.value) return;
    scanLoading.value = true;
    error.value = '';
    clearMessage();
    try {
      coverageScan.value = await scanBusinessConfigCoverage({
        business_catalog: true,
        exclude_configuration_models: true,
        model: currentModel.value,
        view_id: scopeView.value,
        role_key: scopeRole.value || session.roleSurface?.role_code || undefined,
        root_menu_xmlid: rootMenuXmlid.value || undefined,
        include_all_root_menu_actions: Boolean(coverageScan.value?.include_all_root_menu_actions),
        limit: 1000,
      });
      hydrateSelectedCoverageRowFromScan();
    } catch (err) {
      error.value = err instanceof Error ? err.message : '当前业务对象覆盖检查失败';
    } finally {
      scanLoading.value = false;
    }
  }

  async function rescanCoverageAfterBootstrap() {
    if (coverageScan.value?.include_all_root_menu_actions) {
      await scanSystemRootCoverage();
      return;
    }
    if (coverageScan.value?.model) {
      await scanCurrentModel();
      return;
    }
    await scanCoverage();
  }

  async function applyScopeAndLoad() {
    if (deps.scopeBusy()) { setMessage('配置操作处理中，请完成后再切换对象'); return; }
    if (hasUnsavedEdits() && !(await confirmScopeChange())) return;
    resetScopeDrafts();
    resetEditorPanels();
    coverageScan.value = null;
    selectedPageLabel.value = '';
    await router.replace({
      path: route.path,
      query: {
        ...route.query,
        model: currentModel.value || undefined,
        action_id: scopeAction.value ? String(scopeAction.value) : undefined,
        view_id: scopeView.value ? String(scopeView.value) : undefined,
        role_key: scopeRole.value || undefined,
        page_label: undefined,
      },
    });
    await loadSurface();
  }

  async function focusScanRow(row: BusinessConfigCoverageScanItem) {
    if (isBusinessConfigRuntimeModel(row.model)) return;
    if (coverageRowMatchesScope(row)) { await focusSelectedConfigPanelOnMobile(); return; }
    if (deps.scopeBusy()) { setMessage('配置操作处理中，请完成后再切换对象'); return; }
    if (hasUnsavedEdits() && !(await confirmScopeChange())) return;
    resetScopeDrafts();
    surface.value = null;
    scopeModel.value = row.model;
    scopeActionId.value = row.action_id;
    scopeViewId.value = Number(row.view_id || 0);
    selectedPageLabel.value = row.name || row.model;
    selectedRuntimeRoute.value = row.runtime_route || null;
    resetEditorPanels();
    await router.replace({ path: route.path, query: {
      ...route.query,
      model: row.model || undefined,
      action_id: row.action_id ? String(row.action_id) : undefined,
      view_id: row.view_id ? String(row.view_id) : undefined,
      role_key: scopeRole.value || undefined,
      page_label: row.name || undefined,
      open_list_search: undefined,
      change_set_token: undefined,
    } });
    await loadSurface();
    await focusSelectedConfigPanelOnMobile();
  }

  function hydrateSelectedCoverageRowFromScan() {
    const matched = (coverageScan.value?.items || []).find(coverageRowMatchesScope);
    if (!matched || isBusinessConfigRuntimeModel(matched.model)) return;
    scopeModel.value = matched.model || scopeModel.value;
    scopeActionId.value = matched.action_id || scopeActionId.value;
    scopeViewId.value = Number(matched.view_id || scopeViewId.value || 0);
    selectedPageLabel.value = matched.name || selectedPageLabel.value || matched.model;
    selectedRuntimeRoute.value = matched.runtime_route || selectedRuntimeRoute.value;
  }

  async function openRuntimeRoute(row: BusinessConfigCoverageScanItem) {
    const runtimeRoute = row.runtime_route || {};
    const path = String(runtimeRoute.path || '').trim();
    if (!path) return;
    await router.push({
      path,
      query: runtimeReturnQuery(runtimeRoute.query || {}, {
        model: row.model,
        actionId: row.action_id,
        viewId: row.view_id,
        pageLabel: row.name || row.model,
      }),
    });
  }

  return { coverageRowKey, coverageRowMatchesScope, coverageRowActionId, coverageRowViewId, clearMessage, setMessage, loadSurface, scanCoverage, scanSystemRootCoverage, scanCurrentModel, rescanCoverageAfterBootstrap, applyScopeAndLoad, focusScanRow, hydrateSelectedCoverageRowFromScan, openRuntimeRoute };
}

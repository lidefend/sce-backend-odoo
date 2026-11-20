import { onScopeDispose } from 'vue';
import {
  beginBooleanActivity,
  createContextRequestOwner,
  type ContextRequestIdentity,
} from '../../app/contextEpoch';

export type BusinessConfigPublishLifecycleDependencies = {
  currentModel: Readonly<import('vue').Ref<string>>;
  listSearchBusy: import('vue').Ref<boolean>;
  error: import('vue').Ref<string>;
  clearMessage: () => void;
  auditBusinessListSearchConfig: typeof import('../../api/businessConfig').auditBusinessListSearchConfig;
  scopeAction: Readonly<import('vue').Ref<number | undefined>>;
  scopeView: Readonly<import('vue').Ref<number | undefined>>;
  scopeRole: Readonly<import('vue').Ref<string | undefined>>;
  listSearchAudit: import('vue').Ref<import('../../api/businessConfig').BusinessConfigListSearchAuditPayload | null>;
  namesToText: typeof import('./formatters').namesToText;
  normalizeNamesText: typeof import('./formatters').normalizeNamesText;
  listColumnsText: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['listColumnsText'];
  searchFiltersText: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['searchFiltersText'];
  searchGroupByText: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['searchGroupByText'];
  listSearchBase: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['listSearchBase'];
  activeListSearchEditor: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['activeListSearchEditor'];
  requestedListSearchTab: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['requestedListSearchTab'];
  analysisPanelOpen: import('vue').Ref<boolean>;
  approvalPanelOpen: import('vue').Ref<boolean>;
  listSearchPanelOpen: import('vue').Ref<boolean>;
  focusActiveEditorPanel: () => Promise<void>;
  setMessage: (text: string, detail?: string) => void;
  auditBusinessAnalysisConfig: typeof import('../../api/businessConfig').auditBusinessAnalysisConfig;
  analysisAudit: import('vue').Ref<import('../../api/businessConfig').BusinessConfigAnalysisAuditPayload | null>;
  pivotMeasuresText: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['pivotMeasuresText'];
  pivotDimensionsText: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['pivotDimensionsText'];
  graphMeasuresText: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['graphMeasuresText'];
  graphDimensionsText: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['graphDimensionsText'];
  graphType: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['graphType'];
  analysisBase: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['analysisBase'];
  activeAnalysisEditor: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['activeAnalysisEditor'];
  requestedAnalysisTab: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['requestedAnalysisTab'];
  listSearchSaving: import('vue').Ref<boolean>;
  hasListSearchDraftChanges: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['hasListSearchDraftChanges'];
  parseNames: typeof import('./formatters').parseNames;
  stageUnifiedDraftItem: ReturnType<typeof import('./useBusinessConfigDraftSession').useBusinessConfigDraftSession>['stageItem'];
  contractTargetKey: typeof import('./changeSetPayloads').contractTargetKey;
  listContractPayload: typeof import('./changeSetPayloads').listContractPayload;
  searchContractPayload: typeof import('./changeSetPayloads').searchContractPayload;
  hasAnalysisDraftChanges: ReturnType<typeof import('./useBusinessConfigFieldEditors').useBusinessConfigFieldEditors>['hasAnalysisDraftChanges'];
  analysisContractPayload: typeof import('./changeSetPayloads').analysisContractPayload;
  previewDraft: ReturnType<typeof import('./useBusinessConfigDraftSession').useBusinessConfigDraftSession>['previewDraft'];
  openImpactDialog: ReturnType<typeof import('./useBusinessConfigImpactDialog').useBusinessConfigImpactDialog>['openImpactDialog'];
  changeSet: ReturnType<typeof import('./useBusinessConfigDraftSession').useBusinessConfigDraftSession>['changeSet'];
  publishDraft: ReturnType<typeof import('./useBusinessConfigDraftSession').useBusinessConfigDraftSession>['publishDraft'];
  loadSurface: ReturnType<typeof import('./useBusinessConfigScopeLifecycle').useBusinessConfigScopeLifecycle>['loadSurface'];
  rollbackPublished: ReturnType<typeof import('./useBusinessConfigDraftSession').useBusinessConfigDraftSession>['rollbackPublished'];
  discardDraft: ReturnType<typeof import('./useBusinessConfigDraftSession').useBusinessConfigDraftSession>['discardDraft'];
  requestIdentity: () => ContextRequestIdentity;
};

export function useBusinessConfigPublishLifecycle(deps: BusinessConfigPublishLifecycleDependencies) {
  const { currentModel, listSearchBusy, error, clearMessage, auditBusinessListSearchConfig, scopeAction, scopeView, scopeRole, listSearchAudit, namesToText, normalizeNamesText, listColumnsText, searchFiltersText, searchGroupByText, listSearchBase, activeListSearchEditor, requestedListSearchTab, analysisPanelOpen, approvalPanelOpen, listSearchPanelOpen, focusActiveEditorPanel, setMessage, auditBusinessAnalysisConfig, analysisAudit, pivotMeasuresText, pivotDimensionsText, graphMeasuresText, graphDimensionsText, graphType, analysisBase, activeAnalysisEditor, requestedAnalysisTab, listSearchSaving, hasListSearchDraftChanges, parseNames, stageUnifiedDraftItem, contractTargetKey, listContractPayload, searchContractPayload, hasAnalysisDraftChanges, analysisContractPayload, previewDraft, openImpactDialog, changeSet, publishDraft, loadSurface, rollbackPublished, discardDraft } = deps;
  const requestOwner = createContextRequestOwner(deps.requestIdentity);
  let loadedListSearchIdentity = '';
  let loadedAnalysisIdentity = '';
  onScopeDispose(() => requestOwner.dispose());

  function listSearchIdentityKey() {
    return requestOwner.currentIdentityKey({ viewType: 'tree+search' });
  }

  function analysisIdentityKey() {
    return requestOwner.currentIdentityKey({ viewType: 'pivot+graph+calendar+dashboard' });
  }

  function hasCurrentListSearchRead() {
    return Boolean(loadedListSearchIdentity) && loadedListSearchIdentity === listSearchIdentityKey();
  }

  function hasCurrentAnalysisRead() {
    return Boolean(loadedAnalysisIdentity) && loadedAnalysisIdentity === analysisIdentityKey();
  }

  async function loadListSearchConfig() {
    if (!currentModel.value) return;
    const request = requestOwner.begin('editor-read', { viewType: 'tree+search' });
    const releaseBusy = beginBooleanActivity(listSearchBusy);
    loadedListSearchIdentity = '';
    error.value = '';
    clearMessage();
    try {
      const result = await auditBusinessListSearchConfig({
        model: currentModel.value,
        action_id: scopeAction.value,
        view_id: scopeView.value,
        role_key: scopeRole.value,
      });
      if (!requestOwner.isCurrent(request)) return;
      listSearchAudit.value = result;
      const configuredListColumns = result.business_config_list_columns || [];
      const configuredSearchFilters = result.business_config_search_filters || [];
      const configuredSearchGroupBy = result.business_config_search_group_by || [];
      const hasListConfig = result.has_business_list_config === true;
      const hasSearchConfig = result.has_business_search_config === true;
      const suggestedListColumns = hasListConfig ? [] : result.suggested_list_columns || [];
      const suggestedSearchFilters = hasSearchConfig ? [] : result.suggested_search_filters || [];
      const suggestedSearchGroupBy = hasSearchConfig ? [] : result.suggested_search_group_by || [];
      const displayedListColumns = hasListConfig ? configuredListColumns : suggestedListColumns;
      const displayedSearchFilters = hasSearchConfig ? configuredSearchFilters : suggestedSearchFilters;
      const displayedSearchGroupBy = hasSearchConfig ? configuredSearchGroupBy : suggestedSearchGroupBy;
      listColumnsText.value = namesToText(displayedListColumns);
      searchFiltersText.value = namesToText(displayedSearchFilters);
      searchGroupByText.value = namesToText(displayedSearchGroupBy);
      listSearchBase.value = {
        list: normalizeNamesText(namesToText(displayedListColumns)),
        filter: normalizeNamesText(namesToText(displayedSearchFilters)),
        group: normalizeNamesText(namesToText(displayedSearchGroupBy)),
      };
      activeListSearchEditor.value = requestedListSearchTab.value;
      analysisPanelOpen.value = false;
      approvalPanelOpen.value = false;
      listSearchPanelOpen.value = true;
      await focusActiveEditorPanel();
      if (!requestOwner.isCurrent(request)) return;
      loadedListSearchIdentity = request.identityKey;
      if ((!hasListConfig && suggestedListColumns.length) || (!hasSearchConfig && (suggestedSearchFilters.length || suggestedSearchGroupBy.length))) {
        setMessage('建议配置，尚未保存', '采用或调整建议后点击保存，才会加入待发布变更');
      }
    } catch (err) {
      if (!requestOwner.isCurrent(request)) return;
      error.value = err instanceof Error ? err.message : '列表与搜索设置读取失败';
    } finally {
      releaseBusy();
    }
  }

  async function loadAnalysisConfig() {
    if (!currentModel.value) return;
    const request = requestOwner.begin('editor-read', { viewType: 'pivot+graph+calendar+dashboard' });
    const releaseBusy = beginBooleanActivity(listSearchBusy);
    loadedAnalysisIdentity = '';
    error.value = '';
    clearMessage();
    try {
      const result = await auditBusinessAnalysisConfig({
        model: currentModel.value,
        action_id: scopeAction.value,
        view_id: scopeView.value,
        role_key: scopeRole.value,
      });
      if (!requestOwner.isCurrent(request)) return;
      analysisAudit.value = result;
      const configuredPivotMeasures = result.pivot_measures || [];
      const configuredPivotDimensions = result.pivot_dimensions || [];
      const configuredGraphMeasures = result.graph_measures || [];
      const configuredGraphDimensions = result.graph_dimensions || [];
      const hasPivotConfig = result.has_business_pivot_config === true;
      const hasGraphConfig = result.has_business_graph_config === true;
      const suggestedPivotMeasures = hasPivotConfig ? [] : result.suggested_pivot_measures || [];
      const suggestedPivotDimensions = hasPivotConfig ? [] : result.suggested_pivot_dimensions || [];
      const suggestedGraphMeasures = hasGraphConfig ? [] : result.suggested_graph_measures || [];
      const suggestedGraphDimensions = hasGraphConfig ? [] : result.suggested_graph_dimensions || [];
      const configuredGraphType = hasGraphConfig ? result.graph_type || 'bar' : '';
      const displayedPivotMeasures = hasPivotConfig ? configuredPivotMeasures : suggestedPivotMeasures;
      const displayedPivotDimensions = hasPivotConfig ? configuredPivotDimensions : suggestedPivotDimensions;
      const displayedGraphMeasures = hasGraphConfig ? configuredGraphMeasures : suggestedGraphMeasures;
      const displayedGraphDimensions = hasGraphConfig ? configuredGraphDimensions : suggestedGraphDimensions;
      const displayedGraphType = configuredGraphType || result.suggested_graph_type || result.graph_type || 'bar';
      pivotMeasuresText.value = namesToText(displayedPivotMeasures);
      pivotDimensionsText.value = namesToText(displayedPivotDimensions);
      graphMeasuresText.value = namesToText(displayedGraphMeasures);
      graphDimensionsText.value = namesToText(displayedGraphDimensions);
      graphType.value = displayedGraphType;
      analysisBase.value = {
        pivotMeasures: normalizeNamesText(namesToText(displayedPivotMeasures)),
        pivotDimensions: normalizeNamesText(namesToText(displayedPivotDimensions)),
        graphMeasures: normalizeNamesText(namesToText(displayedGraphMeasures)),
        graphDimensions: normalizeNamesText(namesToText(displayedGraphDimensions)),
        graphType: displayedGraphType,
      };
      listSearchPanelOpen.value = false;
      approvalPanelOpen.value = false;
      analysisPanelOpen.value = true;
      activeAnalysisEditor.value = requestedAnalysisTab.value;
      await focusActiveEditorPanel();
      if (!requestOwner.isCurrent(request)) return;
      loadedAnalysisIdentity = request.identityKey;
      if (
        (!hasPivotConfig && (suggestedPivotMeasures.length || suggestedPivotDimensions.length))
        || (!hasGraphConfig && (suggestedGraphMeasures.length || suggestedGraphDimensions.length))
      ) {
        setMessage('建议配置，尚未保存', '采用或调整建议后点击保存，才会加入待发布变更');
      }
    } catch (err) {
      if (!requestOwner.isCurrent(request)) return;
      error.value = err instanceof Error ? err.message : '分析视图设置读取失败';
    } finally {
      releaseBusy();
    }
  }

  async function saveListSearchConfig() {
    if (!currentModel.value || !hasListSearchDraftChanges.value) return false;
    if (!hasCurrentListSearchRead()) {
      error.value = '当前配置对象尚未完成有效读取，请重新读取后再保存。';
      return false;
    }
    const request = requestOwner.begin('editor-save', { viewType: 'tree+search' });
    const releaseSaving = beginBooleanActivity(listSearchSaving);
    error.value = '';
    clearMessage();
    try {
      const listColumns = parseNames(listColumnsText.value);
      const searchFilters = parseNames(searchFiltersText.value);
      const searchGroupBy = parseNames(searchGroupByText.value);
      const listChanged = normalizeNamesText(listColumnsText.value) !== listSearchBase.value.list;
      const searchChanged = normalizeNamesText(searchFiltersText.value) !== listSearchBase.value.filter
        || normalizeNamesText(searchGroupByText.value) !== listSearchBase.value.group;
      if (listChanged) await stageUnifiedDraftItem({
        config_type: 'list', model: currentModel.value, view_type: 'tree', action_id: scopeAction.value, view_id: scopeView.value,
        role_key: scopeRole.value, target_key: contractTargetKey(currentModel.value, 'tree', scopeAction.value, scopeView.value),
        draft_payload: listContractPayload(listColumns), diff_summary: { summary: `列表列调整为 ${listColumns.length} 项` }, risk_level: 'low',
      });
      if (!requestOwner.isCurrent(request)) return false;
      if (searchChanged) await stageUnifiedDraftItem({
        config_type: 'search', model: currentModel.value, view_type: 'search', action_id: scopeAction.value, view_id: scopeView.value,
        role_key: scopeRole.value, target_key: contractTargetKey(currentModel.value, 'search', scopeAction.value, scopeView.value),
        draft_payload: searchContractPayload(searchFilters, searchGroupBy), diff_summary: { summary: `搜索项 ${searchFilters.length}，分组项 ${searchGroupBy.length}` }, risk_level: 'low',
      });
      if (!requestOwner.isCurrent(request)) return false;
      listSearchBase.value = {
        list: normalizeNamesText(listColumnsText.value),
        filter: normalizeNamesText(searchFiltersText.value),
        group: normalizeNamesText(searchGroupByText.value),
      };
      setMessage('列表与搜索修改已加入待发布变更', '正式运行页面尚未改变，可继续编辑其他配置后统一预览和发布');
      loadedListSearchIdentity = request.identityKey;
      return true;
    } catch (err) {
      if (!requestOwner.isCurrent(request)) return false;
      error.value = err instanceof Error ? err.message : '列表与搜索设置保存失败';
      return false;
    } finally {
      releaseSaving();
    }
  }

  async function saveAnalysisConfig() {
    if (!currentModel.value || !hasAnalysisDraftChanges.value) return false;
    if (!hasCurrentAnalysisRead()) {
      error.value = '当前配置对象尚未完成有效读取，请重新读取后再保存。';
      return false;
    }
    const request = requestOwner.begin('editor-save', { viewType: 'pivot+graph+calendar+dashboard' });
    const releaseSaving = beginBooleanActivity(listSearchSaving);
    error.value = '';
    clearMessage();
    try {
      const pivotMeasures = parseNames(pivotMeasuresText.value);
      const pivotDimensions = parseNames(pivotDimensionsText.value);
      const graphMeasures = parseNames(graphMeasuresText.value);
      const graphDimensions = parseNames(graphDimensionsText.value);
      const pivotChanged = normalizeNamesText(pivotMeasuresText.value) !== analysisBase.value.pivotMeasures
        || normalizeNamesText(pivotDimensionsText.value) !== analysisBase.value.pivotDimensions;
      const graphChanged = normalizeNamesText(graphMeasuresText.value) !== analysisBase.value.graphMeasures
        || normalizeNamesText(graphDimensionsText.value) !== analysisBase.value.graphDimensions
        || graphType.value !== analysisBase.value.graphType;
      if (pivotChanged) await stageUnifiedDraftItem({
        config_type: 'analysis', model: currentModel.value, view_type: 'pivot', action_id: scopeAction.value, view_id: scopeView.value,
        role_key: scopeRole.value, target_key: contractTargetKey(currentModel.value, 'pivot', scopeAction.value, scopeView.value),
        draft_payload: analysisContractPayload('pivot', pivotMeasures, pivotDimensions, graphType.value),
        diff_summary: { summary: `透视指标 ${pivotMeasures.length}，维度 ${pivotDimensions.length}` }, risk_level: 'medium',
      });
      if (!requestOwner.isCurrent(request)) return false;
      if (graphChanged) await stageUnifiedDraftItem({
        config_type: 'analysis', model: currentModel.value, view_type: 'graph', action_id: scopeAction.value, view_id: scopeView.value,
        role_key: scopeRole.value, target_key: contractTargetKey(currentModel.value, 'graph', scopeAction.value, scopeView.value),
        draft_payload: analysisContractPayload('graph', graphMeasures, graphDimensions, graphType.value),
        diff_summary: { summary: `图表指标 ${graphMeasures.length}，维度 ${graphDimensions.length}` }, risk_level: 'medium',
      });
      if (!requestOwner.isCurrent(request)) return false;
      analysisBase.value = {
        pivotMeasures: normalizeNamesText(pivotMeasuresText.value),
        pivotDimensions: normalizeNamesText(pivotDimensionsText.value),
        graphMeasures: normalizeNamesText(graphMeasuresText.value),
        graphDimensions: normalizeNamesText(graphDimensionsText.value),
        graphType: graphType.value,
      };
      setMessage('分析修改已加入待发布变更', '正式分析页面尚未改变，可在统一变更集中检查和预览');
      loadedAnalysisIdentity = request.identityKey;
      return true;
    } catch (err) {
      if (!requestOwner.isCurrent(request)) return false;
      error.value = err instanceof Error ? err.message : '分析视图设置保存失败';
      return false;
    } finally {
      releaseSaving();
    }
  }

  async function previewUnifiedDraft(device: 'desktop' | 'tablet' | 'mobile' = 'desktop') {
    const request = requestOwner.begin('preview', { viewType: 'change-set-preview' });
    try {
      const result = await previewDraft(device);
      if (!requestOwner.isCurrent(request)) return;
      setMessage('草稿预览已生成', `预览令牌仅对当前管理员有效，正式配置写入 ${result.preview?.formal_contract_write_count || 0}`);
    } catch (err) {
      if (requestOwner.isCurrent(request)) error.value = err instanceof Error ? err.message : '草稿预览失败';
    }
  }

  async function publishUnifiedDraft() {
    const request = requestOwner.begin('publish', { viewType: 'change-set-publish' });
    try {
      const confirmed = await openImpactDialog({ summary: `发布 ${changeSet.value?.item_count || 0} 项可逆配置`, immediate: true, rollbackText: '发布将生成一个变更批次，可按批次回滚。' });
      if (!confirmed || !requestOwner.isCurrent(request)) return;
      const result = await publishDraft();
      if (!requestOwner.isCurrent(request)) return;
      await loadSurface();
      if (!requestOwner.isCurrent(request)) return;
      setMessage('统一变更集已发布', `发布批次包含 ${result.item_count} 项配置，已完成权威重读`);
    } catch (err) {
      if (requestOwner.isCurrent(request)) error.value = err instanceof Error ? err.message : '统一发布失败';
    }
  }

  async function rollbackUnifiedDraft() {
    const request = requestOwner.begin('rollback', { viewType: 'change-set-rollback' });
    try {
      const result = await rollbackPublished();
      if (!requestOwner.isCurrent(request)) return;
      await loadSurface();
      if (!requestOwner.isCurrent(request)) return;
      setMessage('已按发布批次回滚', `回滚批次 ${result?.id || ''} 已完成运行态验证`);
    } catch (err) {
      if (requestOwner.isCurrent(request)) error.value = err instanceof Error ? err.message : '批次回滚失败';
    }
  }

  async function discardUnifiedDraft() {
    const request = requestOwner.begin('discard', { viewType: 'change-set-discard' });
    try {
      await discardDraft();
      if (requestOwner.isCurrent(request)) setMessage('未发布修改已放弃');
    } catch (err) {
      if (requestOwner.isCurrent(request)) error.value = err instanceof Error ? err.message : '放弃草稿失败';
    }
  }
  return { loadListSearchConfig, loadAnalysisConfig, saveListSearchConfig, saveAnalysisConfig, previewUnifiedDraft, publishUnifiedDraft, rollbackUnifiedDraft, discardUnifiedDraft };
}

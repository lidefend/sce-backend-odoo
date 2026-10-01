<template src="./businessConfigSurface/template.html"></template>
<script setup lang="ts">
/* eslint-disable @typescript-eslint/no-unused-vars */
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import BusinessConfigAdvancedAuditPanels from './businessConfigSurface/BusinessConfigAdvancedAuditPanels.vue';
import BusinessConfigApprovalPanel from './businessConfigSurface/BusinessConfigApprovalPanel.vue';
import BusinessConfigContextBar from './businessConfigSurface/BusinessConfigContextBar.vue';
import BusinessConfigChangeSetPanel from './businessConfigSurface/BusinessConfigChangeSetPanel.vue';
import BusinessConfigOverviewTable from './businessConfigSurface/BusinessConfigOverviewTable.vue';
import BusinessConfigCoverageWorkspace from './businessConfigSurface/BusinessConfigCoverageWorkspace.vue';
import BusinessConfigEditorPanels from './businessConfigSurface/BusinessConfigEditorPanels.vue';
import BusinessConfigImpactDialog from './businessConfigSurface/BusinessConfigImpactDialog.vue';
import BusinessConfigStartPanel from './businessConfigSurface/BusinessConfigStartPanel.vue';
import BusinessConfigVersionPanel from './businessConfigSurface/BusinessConfigVersionPanel.vue';
import ScInput from '../components/design-system/ScInput.vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScErrorState from '../components/design-system/ScErrorState.vue';
import ScInlineState from '../components/design-system/ScInlineState.vue';
import {
  auditBusinessAnalysisConfig,
  auditBusinessListSearchConfig,
  bootstrapBusinessAnalysisConfig,
  bootstrapBusinessFormConfig,
  bootstrapBusinessListSearchConfig,
  bootstrapCoverageMissingConfig,
  loadBusinessConfigSurface,
  scanBusinessConfigCoverage,
  type BusinessConfigAnalysisAuditPayload,
  type BusinessConfigCoverageScanItem,
  type BusinessConfigCoverageScanPayload,
  type BusinessConfigListSearchAuditPayload,
  type BusinessConfigSurfacePayload,
} from '../api/businessConfig';
import { BUSINESS_CONFIG_INTENTS } from '../app/businessConfigBoundaries';
import { useSessionStore } from '../stores/session';
import {
  analysisItemLabel,
  createBoundaryLabel,
  deliveryReadinessItemStatusText,
  namesToText,
  normalizeNamesText,
  overallStatusLabel,
  pageDesignStatus,
  pageViewModeText,
  parseNames,
  rowActionHintText,
  rowBootstrapMissingViewTypes,
  rowCoverageProgressText,
  rowHasAnalysisConfig,
  rowHasFormConfig,
  rowHasListSearchConfig,
  runtimeEvidenceText,
  runtimeReasonText,
  sectionHelpLabel,
  sectionPrimaryActionLabel,
  sectionPrimaryCopy,
  sectionTaskKindLabel,
  severityLabel,
  versionStatusLabel, viewTypeLabel,
  visibleRowRemediationActions,
} from './businessConfigSurface/formatters';
import { useBusinessConfigApprovalEditor } from './businessConfigSurface/useBusinessConfigApprovalEditor';
import { useBusinessConfigCoverage } from './businessConfigSurface/useBusinessConfigCoverage';
import { useBusinessConfigFieldEditors } from './businessConfigSurface/useBusinessConfigFieldEditors';
import { useBusinessConfigSnapshots } from './businessConfigSurface/useBusinessConfigSnapshots';
import { useBusinessConfigVersions } from './businessConfigSurface/useBusinessConfigVersions';
import { useBusinessConfigWorkbenchMeta } from './businessConfigSurface/useBusinessConfigWorkbenchMeta';
import { useBusinessConfigProductExperience } from './businessConfigSurface/useBusinessConfigProductExperience';
import { useBusinessConfigNavigation } from './businessConfigSurface/useBusinessConfigNavigation';
import { useBusinessConfigImpactDialog } from './businessConfigSurface/useBusinessConfigImpactDialog';
import { useBusinessConfigDraftSession } from './businessConfigSurface/useBusinessConfigDraftSession';
import { useBusinessConfigScopeLifecycle } from './businessConfigSurface/useBusinessConfigScopeLifecycle';
import { useBusinessConfigWorkbenchBootstrap } from './businessConfigSurface/useBusinessConfigWorkbenchBootstrap';
import { useBusinessConfigSurfacePageContract } from './businessConfigSurface/useBusinessConfigSurfacePageContract';
import { useBusinessConfigSurfaceRuntimeRoute } from './businessConfigSurface/useBusinessConfigSurfaceRuntimeRoute';
import { useBusinessConfigSurfaceScopeParams } from './businessConfigSurface/useBusinessConfigSurfaceScopeParams';
import { useBusinessConfigPublishLifecycle } from './businessConfigSurface/useBusinessConfigPublishLifecycle';
import { useBusinessConfigRemediationLifecycle } from './businessConfigSurface/useBusinessConfigRemediationLifecycle';
import { analysisContractPayload, contractTargetKey, listContractPayload, searchContractPayload } from './businessConfigSurface/changeSetPayloads';
import { clearConsumedOpenIntent, replaceWorkbenchQuerySilently, withSurfaceLoadTimeout } from './businessConfigSurface/workbenchUtils';
import { focusActiveEditorPanel, focusSelectedConfigPanelOnMobile } from './businessConfigSurface/workbenchFocus';
const SURFACE_LOAD_TIMEOUT_MS = 20000;
const CORE_DELIVERY_READINESS_SECTIONS = new Set(['form', 'list_search', 'menu', 'approval']);
const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const {
  pageSectionStyle,
  pageGlobalActions,
  pageSectionsReady,
  pageSectionsFingerprint,
  executeGlobalPageAction,
} = useBusinessConfigSurfacePageContract({
  router,
  route,
  refresh: () => loadSurface(),
});
const loading = ref(false);
const scanLoading = ref(false);
const listSearchBusy = ref(false);
const listSearchSaving = ref(false);
const error = ref('');
const surfaceError = ref('');
const message = ref({ text: '', detail: '' });
const { impactDialog, openImpactDialog, resolveImpactDialog, rollbackConfirm } = useBusinessConfigImpactDialog();
const surface = ref<BusinessConfigSurfacePayload | null>(null);
const boundaryLabels = () => surface.value?.boundary_labels || {};
const boundaryLabel = createBoundaryLabel(boundaryLabels);
const coverageScan = ref<BusinessConfigCoverageScanPayload | null>(null);
const listSearchAudit = ref<BusinessConfigListSearchAuditPayload | null>(null);
const analysisAudit = ref<BusinessConfigAnalysisAuditPayload | null>(null);
const listSearchPanelOpen = ref(false);
const analysisPanelOpen = ref(false);
const selectedRuntimeRoute = ref<BusinessConfigCoverageScanItem['runtime_route'] | null>(null);
const advancedPanelOpen = ref(false);
const surfaceLoadSeq = ref(0);
const {
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
} = useBusinessConfigSurfaceScopeParams({ route, menuTree: session.menuTree });

const sections = computed(() => surface.value?.sections || []);
const visibleSections = computed(() => sections.value.filter((section) => {
  if (advancedPanelOpen.value) return true;
  return section.key === 'form'
    || section.key === 'list_search'
    || section.key === 'analysis'
    || section.key === 'menu'
    || section.key === 'approval';
}));
const selectedCoverageRow = computed(() => (coverageScan.value?.items || []).find(coverageRowMatchesScope));
const selectedPageHasFormConfig = computed(() => {
  const row = selectedCoverageRow.value;
  return row ? rowHasFormConfig(row) : true;
});
const selectedPageHasListSearchConfig = computed(() => {
  const row = selectedCoverageRow.value;
  return row ? rowHasListSearchConfig(row) : true;
});
const selectedPageHasAnalysisConfig = computed(() => {
  const row = selectedCoverageRow.value;
  return row ? rowHasAnalysisConfig(row) : false;
});
const visibleConfigSections = computed(() => {
  const result = visibleSections.value.filter((section) => {
    if (section.key === 'form' && currentModelIsRuntimeConfig.value) return false;
    if (section.key === 'form') return selectedPageHasFormConfig.value;
    if (section.key === 'list_search') return selectedPageHasListSearchConfig.value;
    return true;
  });
  if (
    !advancedPanelOpen.value
    && selectedPageHasAnalysisConfig.value
    && !result.some((section) => section.key === 'analysis')
  ) {
    result.push({
      key: 'analysis',
      label: '分析视图配置',
      contract_count: 0,
      intent: BUSINESS_CONFIG_INTENTS.analysisAudit,
      boundary: 'business_contract',
    });
  }
  return result;
});
const approvalSection = computed(() => visibleConfigSections.value.find((section) => section.key === 'approval') || null);
const {
  changeSet,
  loading: changeSetLoading, busy: changeSetBusy,
  error: changeSetError,
  publishing: changeSetPublishing,
  previewing: changeSetPreviewing,
  stageItem: stageUnifiedDraftItem,
  validateDraft: validateUnifiedDraft,
  previewDraft,
  publishDraft,
  rollbackPublished,
  discardDraft,
  ensureChangeSet,
  resumeScope,
  hasUnifiedDraft,
  resetScope: resetUnifiedDraftScope,
} = useBusinessConfigDraftSession(() => scopeRole.value || '', () => ({ model: currentModel.value, actionId: scopeAction.value, companyId: Number(session.recordContext?.company_id || 0) }));
async function loadChangeSetSafely() {
  try { await resumeScope(); } catch { /* rendered by the change-set panel */ }
}
function resetEditorPanels() {
  listSearchPanelOpen.value = false; listSearchAudit.value = null;
  analysisPanelOpen.value = false; analysisAudit.value = null;
  versionsPanelOpen.value = false; versionContracts.value = [];
}
function runtimeReturnQuery(baseQuery: Record<string, string>, options: Record<string, unknown>) { return buildRuntimeReturnQuery(baseQuery, options); }
const {
  coverageRowKey, coverageRowMatchesScope, coverageRowActionId, coverageRowViewId,
  clearMessage, setMessage, loadSurface, scanCoverage, scanSystemRootCoverage, scanCurrentModel,
  rescanCoverageAfterBootstrap, applyScopeAndLoad, focusScanRow, hydrateSelectedCoverageRowFromScan, openRuntimeRoute,
} = useBusinessConfigScopeLifecycle({ scopeRoleKey, scopeAction, currentModel, scopeView, message, surfaceLoadSeq, loading, error, surfaceError, withSurfaceLoadTimeout, loadBusinessConfigSurface, SURFACE_LOAD_TIMEOUT_MS, scopeRole, session, router, route, surface, scanLoading, coverageScan, scanBusinessConfigCoverage, rootMenuXmlid, selectedPageLabel, scopeModel, scopeActionId, scopeViewId, selectedRuntimeRoute, focusSelectedConfigPanelOnMobile, resetEditorPanels, runtimeReturnQuery,
  scopeBusy: () => changeSetBusy.value || changeSetLoading.value || changeSetPublishing.value || changeSetPreviewing.value || listSearchSaving.value || listSearchBusy.value || approvalLoading.value,
  hasUnsavedEdits: () => hasListSearchDraftChanges.value || hasAnalysisDraftChanges.value || hasApprovalDraftChanges.value,
  confirmScopeChange: () => openImpactDialog({ summary: '切换业务页面会丢弃未保存的编辑，已保存草稿保留。', immediate: false, rollbackText: '选择取消可留在当前页面保存配置草稿。' }),
  resetScopeDrafts: () => { resetListSearchDraft(); resetAnalysisDraft(); resetApprovalDraft(); resetUnifiedDraftScope(); },
});

async function retryBusinessConfigSurface() {
  await loadSurface();
  if (!surface.value) return;
  await loadChangeSetSafely();
  if (!coverageScan.value) await scanSystemRootCoverage();
}
const {
  approvalLoading,
  approvalTargetModel,
  approvalAudit,
  approvalPanelOpen,
  approvalForm,
  approvalSteps,
  approvalStepDragIndex,
  approvalStepDropIndex,
  approvalModeOptions,
  approvalScopeOptions,
  approvalPolicyLabel,
  approvalRuntimeText,
  approvalEffectGuideText,
  approvalImpactSummaryText,
  hasApprovalDraftChanges,
  activeApprovalStepCount,
  approvalValidationMessage,
  canSaveApprovalDraft,
  resetApprovalDraft,
  updateApprovalFormField,
  onApprovalRequiredChange,
  enableApprovalWithDefaultStep,
  loadApprovalConfig,
  saveApprovalConfig,
  addApprovalStep,
  removeApprovalStep,
  moveApprovalStep,
  startApprovalStepDrag,
  dropApprovalStep,
  clearApprovalStepDrag,
} = useBusinessConfigApprovalEditor({
  currentModel,
  targetOptions: computed(() => approvalSection.value?.target_options || []),
  selectedPageLabel,
  error,
  setMessage,
  clearMessage,
  loadSurface,
  focusActiveEditorPanel,
  onOpenPanel: () => {
    listSearchPanelOpen.value = false;
    analysisPanelOpen.value = false;
  },
});
const canOpenDesigner = computed(() => Boolean(surface.value && selectedCoverageRow.value && currentModel.value && scopeAction.value && !currentModelIsRuntimeConfig.value));
const startScopeSummary = computed(() => {
  if (selectedPageLabel.value) return '当前页面配置，只影响这个业务页面';
  if (currentModel.value) return '已选择业务页面，可配置表单、列表、菜单和审批';
  return '先从业务页面目录选择配置对象';
});
const {
  showOnlyIssues,
  pageSearch,
  pageTypeFilter,
  pageTypeOptions,
  configStatusFilter,
  configStatusOptions,
  coverageIssueRows,
  coverageBatchBootstrapRows,
  coverageScopeLabel,
  visibleCoverageRows,
  remediationSummaryItems,
  copyCoverageSummary,
} = useBusinessConfigCoverage({
  coverageScan,
  advancedPanelOpen,
  setMessage,
});
const activeConfigSectionKey = ref(String(route.query.workbench_section || 'form'));
pageSearch.value = String(route.query.workbench_search || '').trim();
const initialPageType = String(route.query.workbench_page_type || '').trim();
if (pageTypeOptions.some((option) => option.key === initialPageType)) {
  pageTypeFilter.value = initialPageType as typeof pageTypeFilter.value;
}
const initialConfigStatus = String(route.query.workbench_config_status || '').trim();
if (configStatusOptions.some((option) => option.key === initialConfigStatus)) configStatusFilter.value = initialConfigStatus as typeof configStatusFilter.value;
const {
  snapshotCompareText,
  snapshotCompareLoading,
  snapshotExportLoading,
  snapshotCompareResult,
  snapshotSummary,
  snapshotSummaryText,
  snapshotCompareSummary,
  snapshotCompareChangedRows,
  snapshotCompareAddedRows,
  snapshotCompareRemovedRows,
  snapshotRemediationSummary,
  downloadSnapshot,
  downloadSnapshotRemediationPlan,
  compareSnapshot,
} = useBusinessConfigSnapshots({
  surface,
  error,
  setMessage,
  clearMessage,
});
const deliveryReadiness = computed(() => surface.value?.delivery_readiness || null);
const deliveryReadinessItems = computed(() => deliveryReadiness.value?.items || []);
const visibleDeliveryReadinessItems = computed(() => {
  const items = deliveryReadinessItems.value;
  if (advancedPanelOpen.value) return items;
  return items.filter((item) => CORE_DELIVERY_READINESS_SECTIONS.has(String(item.section_key || '')));
});
const deliveryReadinessStatusText = computed(() => {
  const items = visibleDeliveryReadinessItems.value;
  if (!deliveryReadiness.value || !items.length) return '读取中';
  return items.every((item) => item.status === 'ready') ? '已配置' : '待检查';
});
const visibleDeliveryReadinessProgressText = computed(() => {
  const items = visibleDeliveryReadinessItems.value;
  if (!deliveryReadiness.value || !items.length) return snapshotSummary.value ? `配置 ${snapshotSummary.value.contract_count}` : '';
  const readyCount = items.filter((item) => item.status === 'ready').length;
  return `${readyCount}/${items.length} 项已有配置`;
});
const listSearchPanelDescription = computed(() => (
  advancedPanelOpen.value
    ? '这些配置写入正式业务配置，不写入个人列偏好。'
    : '保存为这个页面的默认列表、搜索和分组设置，不覆盖个人列宽和排序偏好。'
));
const {
  listColumnsText,
  searchFiltersText,
  searchGroupByText,
  pivotMeasuresText,
  pivotDimensionsText,
  graphMeasuresText,
  graphDimensionsText,
  graphType,
  listSearchBase,
  analysisBase,
  listColumnDraft,
  searchFilterDraft,
  searchGroupDraft,
  activeListSearchEditor,
  activeAnalysisEditor,
  listFieldOptionSearch,
  filterFieldOptionSearch,
  groupFieldOptionSearch,
  analysisFieldOptionSearch,
  requestedListSearchTab,
  requestedAnalysisTab,
  listSearchEditorTabs,
  analysisEditorTabs,
  availableListFieldOptions,
  availableFilterFieldOptions,
  availableGroupFieldOptions,
  availableAnalysisFieldOptions,
  hasListSearchDraftChanges,
  hasAnalysisDraftChanges,
  listSearchEditorCount,
  updateListSearchFieldSearch,
  updateListSearchDraft,
  setActiveListSearchEditor,
  setActiveAnalysisEditor,
  resetListSearchDraft,
  fieldOptionAvailableCount,
  analysisEditorState,
  analysisEditorLabel,
  setAnalysisDraft,
  analysisEditorCount, analysisFieldOptionCandidates,
  fieldDisplayLabel,
  fieldOptionHelpText,
  fieldOptionLabel,
  fieldHelpText,
  addListSearchName,
  addVisibleListSearchOptions,
  removeListSearchName,
  moveListSearchName,
  clearChipDrag,
  startListSearchChipDrag,
  hoverListSearchChipDrop,
  dropListSearchChip,
  isListSearchChipDragging,
  isListSearchChipDropTarget,
  addAnalysisName,
  addVisibleAnalysisOptions,
  removeAnalysisName,
  moveAnalysisName,
  startAnalysisChipDrag,
  hoverAnalysisChipDrop,
  dropAnalysisChip,
  isAnalysisChipDragging,
  isAnalysisChipDropTarget,
  resetAnalysisDraft,
} = useBusinessConfigFieldEditors({
  route,
  router,
  listSearchAudit,
  analysisAudit,
  listSearchPanelOpen,
  analysisPanelOpen,
  advancedPanelOpen,
  setMessage,
  clearMessage,
});
const { runtimeRouteTarget, runtimeRouteHref } = useBusinessConfigSurfaceRuntimeRoute({
  router,
  selectedRuntimeRoute,
  selectedCoverageRow,
  scopeAction,
});

const {
  buildRuntimeReturnQuery,
  openCurrentEffectivePage,
  openMenuConfig,
  openCreateMenuConfig,
  openApprovalConfig,
  openFormConfig,
} = useBusinessConfigNavigation({
  route,
  router,
  session,
  runtimeRouteTarget,
  currentModel,
  selectedPageLabel,
  scopeAction,
  scopeView,
  scopeRole,
  pageSearch,
  pageTypeFilter,
  configStatusFilter,
  activeConfigSectionKey,
  listSearchPanelOpen,
  analysisPanelOpen,
  activeListSearchEditor,
  activeAnalysisEditor,
  canOpenDesigner,
  ensureChangeSetToken: async () => (await ensureChangeSet()).token,
});

const {
  versionsLoading,
  versionsPanelOpen,
  versionTitle,
  activeVersionSection,
  versionContracts,
  versionPanelDescription,
  versionPanelGuide,
  versionEmptyText,
  loadVersions,
  rollbackContractFromWorkbench,
  versionContractDisplayName,
  versionContractImpactText,
  versionRollbackButtonLabel,
  versionContractDecisionText,
  versionDeltaText,
  versionSummaryText,
} = useBusinessConfigVersions({
  currentModel,
  scopeAction,
  scopeView,
  scopeRole,
  selectedPageLabel,
  surface,
  advancedPanelOpen,
  listSearchSaving,
  coverageScan,
  error,
  setMessage,
  clearMessage,
  loadSurface,
  rescanCoverageAfterBootstrap,
  rollbackConfirm,
});
const {
  workbenchCompanyLabel,
  workbenchRoleLabel,
  hasWorkbenchDraftChanges,
  currentEffectiveVersionLabel,
  inspectListSearchDraft,
  inspectAnalysisDraft,
} = useBusinessConfigProductExperience({
  session,
  currentModel, scopeAction, scopeView, scopeRole, surface,
  selectedViewType: computed(() => selectedCoverageRow.value?.target_view_types?.includes('form') ? 'form' : (selectedCoverageRow.value?.view_mode?.split(',')[0] || 'form')),
  versionContracts,
  listSearchAudit,
  analysisAudit,
  snapshotSummary,
  hasListSearchDraftChanges,
  hasAnalysisDraftChanges,
  hasApprovalDraftChanges,
  hasUnifiedDraft,
  activeChangeSetToken: computed(() => String(changeSet.value?.token || '')),
  listColumnsText,
  searchFiltersText,
  searchGroupByText,
  listSearchBase,
  listSearchPanelOpen,
  analysisPanelOpen,
  approvalPanelOpen,
  versionsPanelOpen,
  resetListSearchDraft,
  resetAnalysisDraft,
  resetApprovalDraft,
  resetUnifiedDraftScope,
  loadSurface,
  scanSystemRootCoverage,
  setMessage,
  openImpactDialog,
});
const { loadListSearchConfig, loadAnalysisConfig, saveListSearchConfig, saveAnalysisConfig, previewUnifiedDraft, publishUnifiedDraft, rollbackUnifiedDraft, discardUnifiedDraft } = useBusinessConfigPublishLifecycle({ currentModel, listSearchBusy, error, clearMessage, auditBusinessListSearchConfig, scopeAction, scopeView, scopeRole, listSearchAudit, namesToText, normalizeNamesText, listColumnsText, searchFiltersText, searchGroupByText, listSearchBase, activeListSearchEditor, requestedListSearchTab, analysisPanelOpen, approvalPanelOpen, listSearchPanelOpen, focusActiveEditorPanel, setMessage, auditBusinessAnalysisConfig, analysisAudit, pivotMeasuresText, pivotDimensionsText, graphMeasuresText, graphDimensionsText, graphType, analysisBase, activeAnalysisEditor, requestedAnalysisTab, listSearchSaving, hasListSearchDraftChanges, parseNames, stageUnifiedDraftItem, contractTargetKey, listContractPayload, searchContractPayload, hasAnalysisDraftChanges, analysisContractPayload, previewDraft, openImpactDialog, changeSet, publishDraft, loadSurface, rollbackPublished, discardDraft });
const {
  sectionImpactText,
  sectionStatusLabel,
  sectionTaskCoverageText,
  deliveryReadinessItemMetaText,
  runDeliveryReadinessAction,
} = useBusinessConfigWorkbenchMeta({
  selectedCoverageRow,
  selectedPageLabel,
  advancedPanelOpen,
  boundaryLabels,
  scanSystemRootCoverage,
  openMenuConfig,
  loadApprovalConfig,
  loadListSearchConfig,
  openFormConfig,
});
const { runRemediationAction, openVersionsForRuntimeGaps, bootstrapMissingContracts, bootstrapCoverageMissing, confirmAndSaveApprovalConfig } = useBusinessConfigRemediationLifecycle({ focusScanRow, loadAnalysisConfig, loadVersions, setMessage, openMenuConfig, loadListSearchConfig, rowBootstrapMissingViewTypes, listSearchSaving, error, clearMessage, bootstrapBusinessFormConfig, coverageRowActionId, coverageRowViewId, scopeRole, bootstrapBusinessListSearchConfig, bootstrapBusinessAnalysisConfig, loadSurface, scanCurrentModel, openFormConfig, coverageBatchBootstrapRows, openImpactDialog, bootstrapCoverageMissingConfig, currentModel, scopeView, rootMenuXmlid, coverageScan, rescanCoverageAfterBootstrap, approvalImpactSummaryText, saveApprovalConfig });

useBusinessConfigWorkbenchBootstrap({
  shouldOpenPageList, shouldOpenFormConfig, shouldOpenListSearch, shouldOpenAnalysis,
  loadSurface, surface, route, loadChangeSetSafely, coverageScan, scanSystemRootCoverage,
  currentModel, scopeAction, clearConsumedOpenIntent, coverageRowMatchesScope, focusScanRow,
  loadListSearchConfig, loadAnalysisConfig,
});
</script>

<style src="./businessConfigSurface/style.css"></style>

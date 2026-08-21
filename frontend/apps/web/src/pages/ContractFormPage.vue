/* eslint-disable @typescript-eslint/no-unused-vars, no-extra-boolean-cast, vue/attributes-order */
<template>
  <LayoutShell
    :content-layout="recordContentLayoutMode"
    :class="['sc-page', { 'contract-form-native-shell': useNativeFormTree }]"
    data-product-page-mode="form"
    :data-v2-shadow-store="String(v2ShadowStoreReady)" :data-v2-shadow-widgets="String(v2ShadowWidgetCount)"
    :data-v2-shadow-actions="String(v2ShadowActionCount)" :data-v2-shadow-button-statuses="String(v2ShadowButtonStatusCount)"
    :data-v2-shadow-field-codes="String(v2ShadowFieldCodeCount)" :data-v2-shadow-field-overlap="String(v2ShadowLegacyFieldOverlapCount)"
    :data-v2-shadow-field-missing="v2ShadowLegacyFieldMissingPreview" :data-v2-shadow-layout-source="v2ShadowLayoutSourceKind"
    :data-v2-shadow-global-source="v2ShadowGlobalSourceKind" :data-v2-shadow-source-context="v2ShadowSourceContextKind"
    :data-v2-shadow-status-fields="String(v2ShadowStatusFieldCount)" :data-v2-shadow-value-fields="String(v2ShadowValueFieldCount)"
    :data-v2-shadow-main-data-fields="String(v2ShadowMainDataFieldCount)"
    :data-v2-shadow-readonly-values="String(v2ShadowReadonlyValueCount)"
    :data-v2-shadow-value-source="v2ShadowValueSourceKind"
    :data-v2-shadow-error="v2ContractDecodeError || '-'"
  >
    <h1 class="sc-visually-hidden">{{ pageDisplayTitle }}</h1>
    <ContractFormProductHeader
      v-if="!initialFormLoading"
      :title="pageDisplayTitle" :subtitle="pageDisplaySubtitle" :hide-title="suppressPageHeaderTitle" :show-hud="showHud"
      :model="model" :record-id-display="recordIdDisplay" :action-id="actionId" :contract-meta-line="contractMetaLine"
      :intake-mode="isIntakeCreateMode" :intake-required-summary="intakeRequiredSummary" :intake-missing-summary="intakeMissingSummary" :statusbar="nativeStatusbar"
      :mode="renderProfile" :mode-label="currentRenderProfileLabel" :dirty="hasChanges" :changed-field-count="changedFieldCount"
      :show-continue-processing="showContinueProcessing"
      :busy="busy || status === 'loading'" :busy-kind="busyKind" :show-return="showReturnToBusinessConfigAction" :show-draft-save="!canonicalProductRendererActive && showDraftSaveAction" :draft-save-disabled="draftSaveDisabled" :draft-save-label="draftSaveButtonLabel"
      :show-primary-form-action="!canonicalProductRendererActive && showPrimaryBusinessFormAction" :primary-form-action-disabled="primaryFormActionDisabled" :primary-form-action-hint="primaryFormActionHint" :submit-label="submitButtonLabel" :primary-action="primaryBusinessFormAction"
      :direct-actions="canonicalProductRendererActive ? [] : headerBusinessDirectActions" :overflow-actions="canonicalProductRendererActive ? [] : headerBusinessOverflowActions" :config-actions="canonicalProductRendererActive ? [] : headerConfigActionsVisible"
      :show-discard="showDiscardAction" :show-debug="showDebugActionsVisible" :contract-present="Boolean(contract)" :discard-label="formUiLabel('discard')" :reload-label="formUiLabel('reload')"
      @back="returnToPreviousPage" @continue-processing="continueProcessing" @set-status="setStatusbarValue" @return-workbench="returnToBusinessConfigDesigner" @save-draft="saveRecord()"
      @run-primary="runPrimaryFormAction" @run-action="runAction" @discard="discardChanges" @copy="copyContractJson" @export="exportContractJson" @reload="reload"
    />
    <ProductFormLoadingSkeleton v-if="initialFormLoading" :loading-label="`正在载入${pageDisplayTitle || '表单'}`" />
    <StatusPanel v-else-if="renderErrorMessage" :title="pageDisplayTitle" :message="renderErrorMessage" variant="error" :on-retry="reload" />
    <StatusPanel v-else-if="status === 'error'" :title="pageDisplayTitle" :message="errorMessage" :error-code="loadError.status" :reason-code="loadError.reason" :trace-id="loadError.trace" variant="error" :on-retry="reload" />
    <StatusPanel v-else-if="recordMissing" :title="pageDisplayTitle" message="该记录不存在，可能已被删除或当前链接已经失效。" :error-code="404" variant="error" retry-label="返回安全页面" :on-retry="() => router.push('/')" />
    <section v-else :class="['card', 'sc-panel', 'sc-product-main-surface', { 'card--flow': isIntakeCreateMode, 'is-refreshing': status === 'loading' }]"
      :aria-busy="status === 'loading' || undefined" data-workspace-primary-content>
      <ContractFormActionBlocks
        v-if="(pageSectionEnabled('next_actions', true) && pageSectionTagIs('next_actions', 'section')) || (pageSectionEnabled('stat_buttons', true) && pageSectionTagIs('stat_buttons', 'div'))"
        :style="[pageSectionStyle('next_actions'), pageSectionStyle('stat_buttons')]"
        :active-filter-key="activeFilterKey"
        :body-actions="bodyActions"
        :busy="busy"
        :is-intake-create-mode="isIntakeCreateMode"
        :search-filters="searchFilters"
        :show-hud="showHud"
        :show-search-filters="showSearchFilters"
        :strict-contract-defaults-summary="strictContractDefaultsSummary"
        :strict-contract-missing-summary="strictContractMissingSummary"
        :use-native-form-tree="useNativeFormTree"
        :warnings="warnings"
        :workflow-evidence-gate-rows="workflowEvidenceGateRows"
        :workflow-transitions="workflowTransitions"
        @open-filter="openFilter"
        @run-action="runAction"
      />
      <section v-if="pageSectionEnabled('details_fallback', true) && pageSectionTagIs('details_fallback', 'section')" class="form-grid" :class="{ 'form-grid--designer-workspace': showCurrentFormFieldConfigScope }" :style="pageSectionStyle('details_fallback')">
        <StatusPanel
          v-if="sceneValidationPanel"
          title="表单校验失败"
          :message="sceneValidationPanel.message"
          :error-code="sceneValidationPanel.code"
          :reason-code="sceneValidationPanel.code"
          :hint="sceneValidationPanel.hint"
          :suggested-action="sceneValidationPanel.suggestedAction"
          variant="error"
        />
        <ProductFormErrorSummary
          :errors="nonSceneValidationErrors"
          :conflict="formConflict"
          @focus-error="focusValidationError"
          @reload-latest="reloadLatestRecord"
        />
        <p v-if="onchangeWarnings.length" class="validation-warn">
          {{ onchangeWarnings.map((item) => item.message || item.title || '').filter(Boolean).join('；') }}
        </p>
        <p v-if="submissionFeedback" class="submission-feedback" :class="`submission-feedback--${submissionFeedback.kind}`">
          {{ submissionFeedback.message }}
        </p>
        <SceneBlocksRenderer
          v-if="showSceneBlocksDebug && sceneReadyFormSurface.sceneBlocks.length"
          :blocks="sceneReadyFormSurface.sceneBlocks"
          @action="handleSceneBlockAction"
        />
        <CurrentFormFieldSettingsPanel
          v-if="showCurrentFormFieldConfigScope"
          v-model:field-search-text="formDesignerFieldSearchText"
          v-model:order-placement="selectedFormSettingsOrderPlacement"
          v-model:order-target-key="selectedFormSettingsOrderTargetKey"
          v-model:selected-field-group-title-edit="selectedFormSettingsFieldGroupTitleEdit"
          :active-tab="formSettingsActiveTab"
          :audit-busy="formConfigAuditBusy"
          :audit-result="formConfigAuditResult"
          :audit-summary="formConfigAuditSummary"
          :busy="busy"
          :field-count="currentFormDesignFieldCount"
          :filtered-field-rows="formDesignerFilteredFieldRows"
          :format-operation-summary="formatFormConfigOperationSummary"
          :format-operation-time="formatFormConfigOperationTime"
          :group-navigator-items="formDesignerGroupNavigatorItems"
          :group-options="currentFormGroupOptions"
          :has-draft-changes="hasCurrentFormFieldDraftChanges"
          :layout-columns="formLayoutColumnsDraft"
          :operation-log="formConfigOperationLog"
          :operation-status-label="formConfigOperationStatusLabel"
          :operator-name="formConfigOperatorName"
          :order-target-options="selectedFormSettingsOrderTargetOptions"
          :scope="formFieldConfigScope"
          :selected-field-group-title="selectedFormSettingsFieldGroupTitle"
          :selected-field-key="selectedFormSettingsFieldKey"
          :selected-field-row="selectedFormSettingsFieldRow"
          :selected-field-size="selectedFormSettingsFieldSize"
          :selected-group-columns="selectedFormSettingsGroupColumns"
          :selected-group-visible="selectedFormSettingsGroupVisible"
          :suggested-hidden-count="suggestedHiddenFieldRows.length"
          @audit="auditCurrentFormConfiguration"
          @clear-operation-log="clearFormConfigOperationLog"
          @hide-suggested-internal-fields="hideSuggestedInternalFields"
          @layout-columns-change="onFormLayoutColumnsChange"
          @move-selected-field="moveSelectedFormSettingsFieldToOrderTarget"
          @open-custom-field-create="openCentralCustomFieldCreate"
          @preview="previewCurrentFormConfiguration"
          @reset="resetContractFieldOrder"
          @return-to-workbench="returnToBusinessConfigDesigner"
          @save="saveContractFieldOrder"
          @select-field="selectFormDesignerField"
          @select-group="selectFormDesignerGroup"
          @selected-field-group-move-change="onSelectedFormSettingsFieldGroupMoveChange"
          @selected-field-label-change="onSelectedFormSettingsFieldLabelChange"
          @selected-field-size-change="onSelectedFormSettingsFieldSizeChange"
          @selected-field-visibility-change="onSelectedFormSettingsFieldVisibilityChange"
          @selected-group-columns-change="onSelectedFormSettingsGroupColumnsChange"
          @selected-group-title-change="onSelectedFormSettingsGroupTitleChange"
          @selected-group-visibility-change="onSelectedFormSettingsGroupVisibilityChange"
        />
        <ContractFormDriverHost v-if="!showCurrentFormFieldConfigScope" :render-model="canonicalFormRenderState.model" :error="canonicalFormDriverError" :driver-config="contractFormDriverConfig"
          :collaboration-panel-listeners="nativeCollaborationPanelListeners"
          :collaboration-panel-props="nativeCollaborationPanelProps"
          :relation-adapter="relationFieldAdapter"
          :show-collaboration-panel="showNativeCollaborationPanel"
          @driver-change="changeContractFormDriver"
          @field-change="onTemplateFieldChange"
          @action-ref="runCanonicalFormAction"
        />
        <ContractFormNativeCanvas v-else
          :button-label-resolver="resolveNativeButtonLabel"
          :collaboration-panel-listeners="nativeCollaborationPanelListeners"
          :collaboration-panel-props="nativeCollaborationPanelProps"
          :designer-mode="true"
          :dirty="hasChanges"
          :field-actions="formSettingsFieldActions"
          :field-config-editable="isContractFieldOrderEditable"
          :field-order-count="fieldOrderDraft.length"
          :field-order-dragging-key="draggingFieldKey"
          :field-order-drop-placement="dropTargetPlacement"
          :field-order-drop-target-key="dropTargetFieldKey"
          :field-order-editable="isContractFieldOrderEditable"
          :field-order-index="contractInlineFieldOrderIndex"
          :field-schemas-for-nodes="nativeFieldSchemasForNodes"
          :field-selection-mode="isContractFieldOrderEditable"
          :is-node-visible="isNativeLayoutNodeVisible"
          :layout-nodes="nativeCanvasFormLayoutNodes"
          :layout-visibility-revision="nativeLayoutVisibilityRevision"
          :mode="renderProfile"
          :native-action-handler="runNativeLayoutAction"
          :native-action-state-resolver="resolveNativeActionState"
          :relation-adapter="relationFieldAdapter"
          :root-columns="nativeFormRootColumns"
          :selected-field-key="selectedFormSettingsFieldKey"
          :selected-field-row-label="selectedFormSettingsFieldRow?.label || ''"
          :show-collaboration-panel="showNativeCollaborationPanel"
          :show-default-section-title="showNativeDefaultSectionTitle"
          :use-native-form-tree="useNativeFormTree"
          @field-action="onContractFieldAction"
          @field-add-after="onContractInlineFieldAddAfter"
          @field-change="onTemplateFieldChange"
          @field-label-change="onContractInlineFieldLabelChange"
          @field-order-drag-end="onContractInlineFieldOrderDragEnd"
          @field-order-drag-leave="onContractInlineFieldOrderDragLeave"
          @field-order-drag-over="onContractInlineFieldOrderDragOver"
          @field-order-drag-start="onContractInlineFieldOrderDragStart"
          @field-order-drop="onContractInlineFieldOrderDrop"
          @field-order-group-drop="onContractInlineFieldOrderGroupDrop"
          @field-order-move="onContractInlineFieldOrderMove"
          @field-select="onFormSettingsFieldSelect"
          @group-add-field="onContractInlineGroupAddField"
          @group-rename="onContractInlineGroupRename"
          @native-action="runNativeLayoutAction"
        />
        <ContractModeSupportPanel
          v-if="!canonicalProductRendererActive"
          :active-actions="activeContractModeActions"
          :advanced-expanded="advancedExpanded"
          :busy="busy"
          :low-code-field-create-dialog="lowCodeFieldCreateDialog"
          :low-code-precheck-warnings="lowCodePrecheckWarnings"
          :mode-feedback="contractModeFeedback"
          :prompt-fields="contractPromptFields"
          :prompt-values="contractPromptValues"
          :prompt-visible="Boolean(contractPromptRule)"
          :show-advanced-toggle="hasAdvancedFields && !isIntakeCreateMode && !useNativeFormTree"
          @cancel-prompt="closeContractPromptAction"
          @close-field-create="closeInlineCustomFieldCreate"
          @field-create-label-change="setFieldCreateLabel"
          @field-create-type-change="setFieldCreateType"
          @open-mode-action="openContractModeAction"
          @prompt-value-change="setContractPromptValue($event.fieldName, $event.value)"
          @submit-field-create="submitInlineCustomFieldCreate"
          @submit-prompt="submitContractPromptAction"
          @toggle-advanced="advancedExpanded = !advancedExpanded"
        />
      </section>
      <PageFooterTemplate v-if="!canonicalProductRendererActive && isIntakeCreateMode" :hint="formUiLabel('create_hint')">
        <template #default>
          <button class="ghost" :disabled="busy" @click="cancelIntake">取消</button>
          <button class="primary" :disabled="isIntakeCreateDisabled" @click="() => saveRecord()">
            {{ intakeCreateButtonLabel }}
          </button>
        </template>
      </PageFooterTemplate>
      <NativeCollaborationPanel
        v-if="!canonicalProductRendererActive && showNativeCollaborationPanel && !hasNativeChatterNode && pageSectionEnabled('chatter', true) && pageSectionTagIs('chatter', 'section')"
        :style="pageSectionStyle('chatter')"
        v-bind="nativeCollaborationPanelProps"
        v-on="nativeCollaborationPanelListeners"
      />
    </section>
    <DevContextPanel
      :visible="showHud && pageSectionEnabled('dev_context', true) && pageSectionTagIs('dev_context', 'div')"
      :style="pageSectionStyle('dev_context')"
      title="表单上下文"
      :entries="hudEntries"
    />
    <RelationSearchDialog
      :busy="busy"
      :dialog="relationSearchDialog"
      :record-count-label="relationRecordCountLabel"
      @close="closeRelationSearchDialog"
      @confirm="confirmRelationSearchSelection"
      @create="createRelationFromSearchDialog"
      @keyword-change="setRelationSearchKeyword"
      @search="runRelationSearch"
      @select-row="selectRelationSearchRow"
    />
    <IntentConfirmationDialog ref="intentConfirmationRef" />
    <AttachmentViewer ref="attachmentViewerRef" />
  </LayoutShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onErrorCaptured, reactive, ref, watch } from 'vue';
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router';
import StatusPanel from '../components/StatusPanel.vue';
import DevContextPanel from '../components/DevContextPanel.vue';
import ProductFormErrorSummary from '../components/product-record/ProductFormErrorSummary.vue';
import IntentConfirmationDialog from '../components/business/IntentConfirmationDialog.vue';
import AttachmentViewer from '../components/attachment/AttachmentViewer.vue';
import LayoutShell from '../components/template/LayoutShell.vue';
import ProductFormLoadingSkeleton from '../components/product-record/ProductFormLoadingSkeleton.vue';
import { contractContentLayoutMode, resolveContentLayoutMode } from '../components/design-system/pageWidth';
import { type NativeFormLayoutNode } from '../components/template/NativeFormTreeRenderer.vue';
import SceneBlocksRenderer from '../components/scene/SceneBlocksRenderer.vue';
import PageFooterTemplate from '../components/template/PageFooter.vue';
import NativeCollaborationPanel, {
  type NativeCollaborationPanelListeners,
  type NativeCollaborationPanelProps,
} from './contractForm/NativeCollaborationPanel.vue';
import ContractFormDriverHost from './contractForm/ContractFormDriverHost.vue';
import ContractFormNativeCanvas from './contractForm/ContractFormNativeCanvas.vue';
import {
  collectCanonicalFormActions,
  resolveCanonicalFormActionExecution,
  validateCanonicalFormActionExecutors,
} from './contractForm/canonicalFormActionExecutor';
import { shouldShowNativeCollaborationPanel } from './contractForm/collaborationPresentation';
import RelationSearchDialog from './contractForm/RelationSearchDialog.vue';
import ContractModeSupportPanel from './contractForm/ContractModeSupportPanel.vue';
import CurrentFormFieldSettingsPanel from './contractForm/CurrentFormFieldSettingsPanel.vue';
import ContractFormActionBlocks from './contractForm/ContractFormActionBlocks.vue';
import ContractFormProductHeader from './contractForm/ContractFormProductHeader.vue';
import type {
  FormSectionFieldActionPayload,
  FormSectionFieldSchema,
  FormSectionFieldChange,
} from '../components/template/formSection.types';
import type { RelationFieldAdapter } from '../components/template/relationField.types';
import { createFormSectionFieldSchemaBuilder } from '../components/template/formSection.adapter';
import { resolveInputPlaceholder, resolveSelectPlaceholder } from '../components/template/placeholder.mapper';
import { resolveFieldSpanClass } from '../components/template/fieldSpan.mapper';
import { mapDescriptorSelectionOptions, mapRelationOptions } from '../components/template/option.mapper';
import { dispatchTemplateFieldChange } from '../components/template/fieldChange.dispatcher';
import { isHudEnabled, isSceneBlocksDebugEnabled } from '../config/debug';
import { config } from '../config';
import { intentRequest } from '../api/intents';
import { ApiError } from '../api/client';
import { executeButton } from '../api/executeButton';
import { triggerOnchange } from '../api/onchange';
import type { OnchangeLinePatch } from '../api/onchange';
import type { FieldDescriptor } from '@sc/schema';
import { useSessionStore } from '../stores/session';
import { ErrorCodes } from '../app/error_codes';
import {
  detectObjectMethodFromActionKey,
  normalizeActionKind,
  parseMaybeJsonRecord,
  toPositiveInt,
} from '../app/contractRuntime';
import { resolveActionIdFromContext } from '../app/actionContext';
import { findActionMeta, findActionMetaByMenu, findMenuNode } from '../app/menu';
import { pickContractNavQuery } from '../app/navigationContext';
import { buildModelFormRouteTarget } from '../app/runtime/actionViewRouteRuntime';
import { readWorkspaceContext } from '../app/workspaceContext';
import { buildRuntimeFieldStates } from '../app/modifierEngine';
import { resolveSceneValidationSuggestedAction } from '../app/sceneValidationRecoveryStrategy';
import { findSceneReadyEntry, resolveFormSceneReady } from '../app/resolvers/sceneReadyResolver';
import { normalizeSceneActionProtocol } from '../app/sceneActionProtocol';
import { executeProjectionRefresh } from '../app/projectionRefreshRuntime';
import {
  createContractFormRecord,
  defaultContractFormRecord,
  listContractFormRecords,
  readContractFormRecord,
  writeContractFormRecord,
} from '../app/runtime/contractFormDataRuntime';
import {
  collectContractV2ButtonStatusById,
  ContractV2DecodeError,
  createContractV2Store,
  decodeContractV2Snapshot,
  resolveContractV2ContainerTree,
  resolveContractV2EffectiveFormCapabilities,
  resolveContractV2GlobalStatus,
  resolveContractV2MainData,
  resolveContractV2ActionRules,
  resolveContractV2FormFieldMap,
  resolveContractV2RuntimeContract,
  resolveContractV2SearchContract,
  resolveContractV2WorkflowContract,
  loadActionContractV2,
  loadModelContractV2,
  type ContractV2NormalizedStore,
} from '../app/contracts/v2';
import type { ContractV2ActionRule } from '../app/contracts/v2/types';
import { executeSceneMutation } from '../app/sceneMutationRuntime';
import { isCoreSceneStrictMode } from '../app/contractStrictMode';
import {
  BUSINESS_CONFIG_ACTION_KEYS,
  BUSINESS_CONFIG_INTENTS,
  BUSINESS_CONFIG_MODES,
  BUSINESS_CONFIG_ROUTE_FLAGS,
  FORM_FIELD_CONFIG_INTENTS,
  isBusinessConfigMode,
  isBusinessConfigRuntimeModel,
} from '../app/businessConfigBoundaries';
import {
  buildActiveContractModeActions,
  buildContractFieldActionsFromRules,
  buildFormSettingsFieldActions as buildFormSettingsFieldActionsFromRules,
  contractActionConfirmationPrompt,
  contractActionRuleClientMode,
  contractActionRuleControl,
  contractActionRuleKey,
  isTierValidationActionHidden as isTierValidationActionHiddenFromState,
  normalizeActionSafety,
  normalizeActionLabel,
  normalizeRequiredParams,
  resolvePrimaryCreateFooterAction,
  resolveV2ButtonStatus,
} from './contractForm/actionContract';
import { normalizeContractAccessPolicy } from './contractForm/accessPolicy';
import {
  fieldInputType,
  fieldType,
  normalizeRelationIds,
  sanitizeUiErrorMessage,
  toDateInputValue,
  toDatetimeInputValue,
} from './contractForm/fieldUtils';
import {
  buildFormConfigFieldLabelReplacementEntries,
  buildFormFieldConfigScope,
  buildCurrentFormGroupOptions,
  buildFormDesignerGroupNavigatorItems,
  buildFormDesignerSearchableFieldRows,
  buildLowCodeApplyBaseParams,
  buildLowCodePreviewQuery,
  buildLowCodeReturnQuery,
  buildLowCodeViewOrchestration as buildLowCodeViewOrchestrationFromDraft,
  changedFieldGroupFromDrafts,
  changedFieldVisibilityFromDrafts,
  collectLowCodeLayoutFromViewOrchestration,
  collectNativeFieldStructureGroups,
  effectiveFieldGroupTitleFromDrafts,
  extractLowCodeFormFieldDraftState,
  extractLowCodeLayoutDraftState,
  filterFormDesignerFieldRows,
  formConfigOperationStatusLabel,
  fieldGroupTitleMatches,
  formatFormConfigAuditSummary,
  formatFormConfigOperationSummary as formatFormConfigOperationSummaryText,
  formatFormConfigOperationTime,
  collectNativeLayoutGroupTitles,
  fieldStructureTitle,
  inferLowCodeLayoutColumns,
  isReadableFieldGroupTitle,
  isSuggestedInternalFormField,
  layoutHasReadableFieldGroups,
  lowCodeFormSpecFromViews,
  lowCodeLayoutFieldLabelFromNodes,
  lowCodeLayoutFromFormSpec,
  lowCodeScopedContractName,
  lowCodeViewsFromContractResponse,
  mergeLowCodeLayoutWithRuntimeGroupShells,
  normalizeConfigPageLabel,
  normalizeFieldGroupTitle,
  normalizeFormConfigAuditResult,
  normalizeLowCodeContractListRows,
  contractFieldSequenceFromOrder,
  readableFallbackFieldLabel,
  routeQueryText as readRouteQueryText,
  resolveFormDesignFieldLabel,
  resolveSelectedFormSettingsFieldGroupTitle,
  type LowCodeLayoutDraftRow,
} from './contractForm/formConfigHelpers';
import { useFormConfigOperationLog } from './contractForm/useFormConfigOperationLog';
import {
  isMissingRequiredValue,
    normalizeContractFieldValue,
  normalizeComparable,
  normalizeRouteDefault,
  resolveNavigationUrl as resolveNavigationUrlFromOrigin,
} from './contractForm/valueUtils';
import {
  buildOnchangeRequestPayload,
  normalizeOnchangeFieldPatch,
  normalizeOnchangeResponse,
} from './contractForm/onchangeNormalization';
import { fieldRequiresServerOnchange } from './contractForm/contractActionRules';
import { dictOrEmpty } from './contractForm/recordUtils';
import {
  collectFormDataFieldNames,
  collectNativeFormDesignFields,
  collectNativeFavoriteFieldNames,
  collectNativeVisibleFieldNames,
  collectNativeVisibleFieldOrder,
  collectNativeVisibleSectionTitles,
  countNativeNodesByType,
  evaluateNativeModifierValue as evaluateNativeModifierValueWithResolver,
  findNativeFieldNode as findNativeFieldNodeInTree,
  isNativeFieldLayoutNode,
  isStaticTruthyModifier,
  nativeModifierValue,
  nativeFieldSubview as nativeFieldSubviewFromTree,
  nativeFieldPresentation,
  isCreateWorkflowStateField,
  nativeLayoutNodeType,
  nativeNodeFieldDescriptor as nativeNodeFieldDescriptorFromNode,
  nativeNodeWidget,
  nativeNodeWidgetSemantics,
  normalizeContractFieldSemantics,
  normalizeSemanticFieldGroups,
  isNativeActionVisible,
  resolveNativeButtonLabel as resolveNativeButtonLabelFromNode,
  resolveFieldSemanticMeta,
  resolveNativeFormRootColumns,
  semanticFieldNamesBySurfaceRole,
  buildLegacyLayoutNodes,
  buildNativeFieldSchemas,
  applyReadonlyFieldValues,
  applyNativeFieldOrderPreview as applyNativeFieldOrderPreviewFromTree,
  normalizeContractV2ContainersForNativeForm as normalizeContractV2ContainersForNativeFormFromTree,
  shouldShowRequiredMark as shouldShowRequiredMarkFromNativeLayout,
  isNativeFieldVisible as isNativeFieldVisibleFromNativeLayout,
  isNativeLayoutNodeVisible as isNativeLayoutNodeVisibleFromNativeLayout,
  filterVisibleNativeLayoutNodes as filterVisibleNativeLayoutNodesFromTree,
  type FieldSemanticMeta,
  type NativeLayoutLikeNode,
  type SemanticFieldGroup,
} from './contractForm/nativeLayoutUtils';
import {
  formRuntimeCommandHintLabel,
  formRuntimeReasonLabel,
  formRuntimeRowStateLabel,
  one2manyCanCreateFromPolicies,
  one2manyColumnDisplayValue,
  one2manyColumnInputType,
  one2manyCreateLabelFromPolicies,
  one2manyColumnsFromSubview,
  one2manyDraftSummary,
  one2manyPrimaryColumnFromColumns,
  one2manyRowLabelFromPrimary,
  one2manyRowStateLabel,
  selectOne2manySubview,
  one2manySubviewPolicies,
} from './contractForm/one2manyUtils';
import { useOne2manyRuntime } from './contractForm/useOne2manyRuntime';
import {
  dynamicRelationDomainFromDescriptor,
  relationEntry,
  dynamicDomainDependencyFields,
  fallbackRelationSearchColumns,
  hasAmbiguousRelationMatches,
  isBlockAllDomain,
  mergeRelationDomains,
  normalizeRouteQueryValues,
  relationDomainFromDescriptor,
  relationCreateMode,
  relationInlineCreate,
  relationModel as relationModelFromDescriptor,
  relationOptionsFromRecords,
  relationOrder,
  relationReadFields,
  relationSearchColumnsFromContract,
  relationSearchDialogContract,
  relationSearchLimit,
  relationSearchOrder,
  relationSearchReadFields,
  relationSearchRowsFromRecords,
  relationUiLabel,
  relationUiLabels,
  runtimeRelationDomainFromModifiers,
  resolveRelationQuickFillOption,
  singleContainingRelationOption,
} from './contractForm/relationDescriptor';
import { useRelationRuntime } from './contractForm/useRelationRuntime';
import {
  buildSceneValidationPanel,
  collectSceneValidationPrecheckErrors as collectSceneValidationPrecheckErrorsFromRules,
  sceneValidationErrorPrefix,
  strictContractDefaultsSummary as strictContractDefaultsSummaryFromGuard,
  strictContractGuardFromSceneReadyEntry,
  strictContractMissingSummary as strictContractMissingSummaryFromGuard,
} from './contractForm/sceneValidation';
import {
  isWorkflowTransitionMethod,
  normalizeWorkflowActionRows,
  normalizeWorkflowEvidenceGateRows,
  normalizeNativeFormStatusbar,
  normalizeWorkflowPhaseStatusbar,
  resolveStatusbarSelectionValue,
  resolveWorkflowContractFromStore,
  applyWorkflowAvailability,
  shouldShowWorkflowAction,
  workflowActionMethodAliases,
  workflowActionRowForMethod,
} from './contractForm/workflowContract';
import {
  formUiLabelFromLabels,
  formUiLabelsFromFormView,
  renderProfileLabel,
  resolveSubmitButtonLabel,
  layoutContainsType,
} from './contractForm/uiLabels';
import { presentContractHeaderActions } from './contractForm/headerActionPresentation';
import { buildContractFormPageIdentity } from '../app/pageIdentityAdapters';
import { usePageContract } from '../app/pageContract';
import { resolveRoutePageIdentity } from '../app/pageIdentityRoute';
import { usePublishedPageIdentity } from '../app/usePublishedPageIdentity';
import {
  activeChatterPlaceholder as activeChatterPlaceholderFromMode,
  activeChatterPostingLabel as activeChatterPostingLabelFromMode,
  activeChatterSubmitLabel as activeChatterSubmitLabelFromMode,
  nativeActivityFieldLabel,
  nativeAttachmentContractOrNull,
  nativeAttachmentLabel,
  nativeAttachmentLabelsFromContract,
  nativeAttachmentMaxBytes as nativeAttachmentMaxBytesFromContract,
  nativeChatterActionsFromContract,
  nativeCollaborationUnavailableMessage as nativeCollaborationUnavailableMessageFromState,
  resolveNativeAttachmentContract,
  resolveNativeChatterContract,
  resolveRuntimeCollaborationContract,
} from './contractForm/collaborationContract';
import {
  MANY2ONE_CREATE_OPTION,
  MANY2ONE_OPEN_RECORD_OPTION,
  MANY2ONE_SEARCH_MORE_OPTION,
  RECORD_CONTEXT_CHANGED_EVENT,
  ContractAccessPolicyError,
  type ContractAccessPolicy,
  type ContractAction,
  type ContractFieldGovernanceAction,
  type ContractFieldGovernanceRow,
  type FormRuntimeStateEvent,
  type LayoutNode,
  type LowCodeFieldSize,
  type NativeChatterAction,
  type NativeStatusbarVm,
  type One2ManyColumn,
  type One2ManyInlineRow,
  type RelationOption,
  type RelationSearchColumn,
  type RelationSearchRow,
  type RelationUiLabels,
} from './contractForm/types';
import { useIntakeAutosaveRuntime } from './contractForm/useIntakeAutosaveRuntime';
import {
  applyIncomingFormFieldValue,
  snapshotOriginalFormValues,
  type FormRecordHydrationTarget,
} from './contractForm/recordHydration';
import {
  useNativeAttachmentRuntime,
  type NativeAttachmentViewerLike,
} from './contractForm/useNativeAttachmentRuntime';
import { useNativeChatterRuntime } from './contractForm/useNativeChatterRuntime';
import { useFieldOrderDragRuntime } from './contractForm/useFieldOrderDragRuntime';
import { useLowCodeFieldCreateRuntime } from './contractForm/useLowCodeFieldCreateRuntime';
import { useFormSettingsLayoutRuntime } from './contractForm/useFormSettingsLayoutRuntime';
import { useFormSettingsGroupRuntime } from './contractForm/useFormSettingsGroupRuntime';
import { useFieldOrderMutationRuntime } from './contractForm/useFieldOrderMutationRuntime';
import { useFieldVisibilityDraftRuntime } from './contractForm/useFieldVisibilityDraftRuntime';
import { useInlineFieldPolicyRuntime } from './contractForm/useInlineFieldPolicyRuntime';
import { useContractModeActionRuntime } from './contractForm/useContractModeActionRuntime';
import { useActionResponseNavigation } from './contractForm/useActionResponseNavigation';
import { usePrimaryFormActionRuntime } from './contractForm/usePrimaryFormActionRuntime';
import { useFormActionRuntime } from './contractForm/useFormActionRuntime';
import { useFormConfigSaveRuntime } from './contractForm/useFormConfigSaveRuntime';
import { applyFormRuntimeStatusEvent } from './contractForm/runtimeStateApplier';
import { useContractDebugExportRuntime } from './contractForm/useContractDebugExportRuntime';
import { useRecordContextChangeRuntime } from './contractForm/useRecordContextChangeRuntime';
import { selectAuthoritativeBusinessActionRows } from './contractForm/authoritativeBusinessActionRows';
import { isFormPageRouteOwner, useFormPageLifecycleRuntime } from './contractForm/useFormPageLifecycleRuntime';
import { useFormAuxiliaryWatchersRuntime } from './contractForm/useFormAuxiliaryWatchersRuntime';
import { useUnsavedFormGuard } from './contractForm/useUnsavedFormGuard';
import { buildContractFormActions } from './contractForm/contractActionPresentation';
import { focusProductFormValidationError } from './contractForm/formValidationFocus';
import { groupContractHeaderActions, resolvePrimaryBusinessActionState } from './contractForm/contractHeaderActionPresentation';
import { resolveContractFormFieldLabels } from './contractForm/formFieldLabels';
import { buildSaveRecordPayload, validateBeforeSaveRecord } from './contractForm/saveRecordHelpers';
import { useCreatedRecordNavigationRuntime } from './contractForm/useCreatedRecordNavigationRuntime';
import { useRecordCollaborationPresentation } from './contractForm/useRecordCollaborationPresentation';
import { useRecordContractSemantics } from './contractForm/useRecordContractSemantics';
import { useRecordFormLayout } from './contractForm/useRecordFormLayout';
import { useRecordFormFieldSchemas } from './contractForm/useRecordFormFieldSchemas';
import { useRecordFormState } from './contractForm/useRecordFormState';
import { useRecordFormDesigner } from './contractForm/useRecordFormDesigner';
import { useRecordRelationships } from './contractForm/useRecordRelationships';
import { useRecordPageLifecycle } from './contractForm/useRecordPageLifecycle';
import {
  resolveEffectiveContractRenderProfile,
  resolveRequestedContractRenderProfile,
} from './contractForm/contractRenderProfile';
import { useRecordActionPresentation } from './contractForm/useRecordActionPresentation';
import { useRecordFormActions } from './contractForm/useRecordFormActions';
import { resolveCanonicalFormRenderState, useContractFormComponentDriverRuntime } from './contractForm/useContractFormComponentDriverRuntime';
import { useFormNavigationActionsRuntime } from './contractForm/useFormNavigationActionsRuntime';
import { useContractV2ShadowDiagnostics } from './contractForm/useContractV2ShadowDiagnostics';
import { useContractFormPageState } from './contractForm/useContractFormPageState';
import { buildFormRequestContext } from './contractForm/formRequestContext';
import { collectActionParams as collectActionParamsFromPlan } from './contractForm/actionExecutionPlan';
import {
  createRouteDefaultsFingerprint,
  formCreateContext as formCreateContextFromState,
  resolveCreateDefaults as resolveCreateDefaultsFromState,
} from './contractForm/createDefaults';
import {
  buildWorkflowTransitions,
  buildRouteContractContext,
  collectRuntimeCapabilities,
  normalizeContractWarnings,
  normalizeSearchFilters,
  resolveBusinessCategoryContext,
  type FormContractReadiness,
} from './contractForm/contractRuntimeVm';
const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const recordPageContract = usePageContract('record');
const pageSectionEnabled = recordPageContract.sectionEnabled;
const pageSectionTagIs = recordPageContract.sectionTagIs;
const pageSectionStyle = recordPageContract.sectionStyle;
const {
  actionResponseNavQuery,
  actionResponseRouteTarget,
  navigateActionResponseResult,
} = useActionResponseNavigation({
  router,
  currentQuery: () => route.query,
  currentModel: () => String(route.params.model || v2ContractStore.value?.snapshot.pageInfo.model || ''),
});
const designerRouteQueryText = (key: string) => readRouteQueryText(route.query as Record<string, unknown>, key);
const {
  status, isComponentActive, instanceRouteIdentity, retainedRouteIdentity, renderErrorMessage,
  recordMissing, errorMessage, loadError, validationErrors, submissionFeedback, formConflict,
  showOne2manyErrors, busyKind, activeContractMode, formSettingsActiveTab, contractModeFeedback,
  contract, contractMeta,
} = useContractFormPageState();
const intentConfirmationRef = ref<InstanceType<typeof IntentConfirmationDialog> | null>(null);
const initialFormLoading = computed(() => status.value === 'loading' && !contract.value);
type PageStatusEvent = Extract<FormRuntimeStateEvent, { kind: 'status' }>;
const applyPageStatusEvent = (event: PageStatusEvent) => applyFormRuntimeStatusEvent({ status, errorMessage }, event);
const {
  copyContractJson,
  exportContractJson,
} = useContractDebugExportRuntime({
  actionId: () => actionId.value || 0,
  contract,
  contractMeta,
  modelName: () => model.value,
});
const {
  handleRecordContextChanged,
} = useRecordContextChangeRuntime({
  isActive: () => isComponentActive.value,
  reload: () => reload(),
});
const v2ContractStore = ref<ContractV2NormalizedStore | null>(null);
const canonicalFormFields = computed(() => resolveContractV2FormFieldMap(v2ContractStore.value));
const v2ContractDecodeError = ref('');
function formRouteIdentity() {
  const query = route.query as Record<string, unknown>;
  return [
    String(route.params.model || ''),
    String(route.params.id || ''),
    String(query.action_id || ''),
    String(query.menu_id || ''),
    String(recordId.value ? '' : (query.view_id || query.viewId || '')),
    String(recordId.value ? '' : (query.current_business_category_code || query.default_business_category_code || '')),
    String(recordId.value ? '' : (query.allowed_business_category_codes || '')),
    String(recordId.value ? '' : createRouteDefaultsFingerprint(query)),
  ].join('|');
}
const {
  v2ShadowStoreReady, v2ShadowWidgetCount, v2ShadowActionCount, v2ShadowButtonStatusCount,
  v2ShadowFieldCodeCount, v2ShadowLegacyFieldOverlapCount, v2ShadowLegacyFieldMissingPreview,
  v2ShadowFormStructureContract, v2ShadowFormStructureSlotCount, v2ShadowLayoutSourceKind,
  v2ShadowGlobalSourceKind, v2ShadowSourceContextKind, v2ShadowStatusFieldCount,
  v2ShadowValueSourceKind, v2ShadowValueFieldCount, v2ShadowMainDataFieldCount,
  v2ShadowReadonlyValueCount,
} = useContractV2ShadowDiagnostics({
  store: v2ContractStore,
  legacyFields: () => canonicalFormFields.value,
  nativeLayoutCount: () => nativeFormLayoutNodes.value.length,
  layoutNodes: () => layoutNodes.value,
});
const activeFilterKey = ref('');
const originalValues = ref<Record<string, unknown>>({});
const recordVersionToken = ref('');
const formData = reactive<Record<string, unknown>>({});
const canonicalFormRenderState = computed(() => resolveCanonicalFormRenderState(
  v2ContractStore.value,
  v2ContractDecodeError.value,
  renderProfile.value,
  formData,
));
// Product routes have one rendering authority. Contract/driver failures stay in
// the canonical host and must never reactivate the legacy product pipeline.
const canonicalProductRendererActive = computed(() => !showCurrentFormFieldConfigScope.value);
const nativeLayoutVisibilityRevision = ref(0);
const advancedExpanded = ref(false);
const {
  relationOptions,
  relationFieldDescriptors,
  relationKeywords,
  invalidatedRelationKeywords,
  clearedDynamicRelationFields,
  relationSearchDialog,
  deniedRelationModels,
  relationQueryTimers,
  relationKeyword,
  relationOptionsForField: relationOptionsForFieldFromRuntime,
  selectedRelationOptions: selectedRelationOptionsFromRuntime,
  setRelationKeywordValue,
  filteredRelationOptions: filteredRelationOptionsFromRuntime,
  upsertRelationOption,
  mergeRelationOptions,
  closeRelationSearchDialog,
  setRelationSearchKeyword,
  selectRelationSearchRow,
  openRelationSearch: openRelationSearchFromRuntime,
  runRelationSearch: runRelationSearchFromRuntime,
  confirmRelationSearchSelection: confirmRelationSearchSelectionFromRuntime,
  selectRelationSearchOption: selectRelationSearchOptionFromRuntime,
  queryRelationOptions: queryRelationOptionsFromRuntime,
  fetchRelationOptions: fetchRelationOptionsFromRuntime,
} = useRelationRuntime();
const onchangeModifiersPatch = ref<Record<string, Record<string, unknown>>>({});
const onchangeWarnings = ref<Array<{ title?: string; message?: string; reason_code?: string }>>([]);
const onchangeLinePatches = ref<OnchangeLinePatch[]>([]);
const {
  rowsByField: one2manyRows,
  fieldRows: one2manyFieldRows,
  visibleRows: visibleOne2manyRows,
  removedRows: removedOne2manyRows,
  ensureRows: ensureOne2manyRows,
  clearRows: clearOne2manyRows,
  addRow: addOne2manyRow,
  setRowField: setOne2manyRowField,
  removeRow: removeOne2manyRow,
  restoreRow: restoreOne2manyRow,
  initRows: initOne2manyRows,
  mergeHydratedRecords: mergeHydratedOne2manyRecords,
  buildCommandValue: buildOne2manyCommandValue,
  collectValidation: collectOne2manyDraftValidation,
  rowHints: one2manyRowHints,
  applyLinePatches: applyOnchangeLinePatches,
} = useOne2manyRuntime({
  recordId: () => recordId.value,
  originalValues: () => originalValues.value,
  parentValues: () => formData,
  onchangeLinePatches: () => onchangeLinePatches.value as Array<Record<string, unknown>>,
  resolveColumns: (fieldName) => one2manyColumns(fieldName),
  resolvePrimaryColumn: (fieldName) => one2manyPrimaryColumn(fieldName),
  resolveRelationOptions: (fieldName) => relationOptionsForField(fieldName),
  markFieldChanged,
});
const changedFieldSet = new Set<string>();
const dirtyFieldSet = new Set<string>();
let onchangeTimer: ReturnType<typeof setTimeout> | null = null;
const applyingOnchangePatch = ref(false);
const {
  activeMode: activeChatterMode,
  activeLabel: activeChatterLabel,
  draft: chatterDraft,
  activitySummary,
  activityDeadline,
  activityNote,
  userQuery: collaborationUserQuery,
  userOptions: collaborationUserOptions,
  usersLoading: collaborationUsersLoading,
  selectedMentionUserIds,
  selectedMentionUsers,
  userChoices: collaborationUserChoices,
  activityAssigneeId,
  posting: chatterPosting,
  loading: chatterLoading,
  error: chatterError,
  timeline: chatterTimeline,
  timelineHasMore: chatterTimelineHasMore,
  activityUpdatingIds,
  clearForRecordLoad: clearNativeChatterForRecordLoad,
  closeComposer: closeNativeChatterComposer,
  loadTimeline: loadNativeChatterTimeline,
  loadMoreTimeline: loadMoreNativeChatterTimeline,
  loadUsers: loadCollaborationUsers,
  selectMentionUser,
  removeMentionUser,
  openAction: openNativeChatterAction,
  send: sendNativeChatter,
  updateActivity: updateNativeActivity,
} = useNativeChatterRuntime({
  model: () => model.value,
  recordId: () => recordId.value,
  activeActivityAction: () => activeActivityAction.value,
});
const attachmentViewerRef = ref<NativeAttachmentViewerLike | null>(null);
const chatterTimelineLoading = chatterLoading;
const {
  uploading: attachmentUploading,
  error: attachmentError,
  pendingAttachments: pendingNativeAttachments,
  clearError: clearNativeAttachmentError,
  clearPendingAttachments: clearPendingNativeAttachments,
  onAttachmentSelected: onNativeAttachmentSelected,
  removePendingAttachment: removePendingNativeAttachment,
  uploadPendingAttachments: uploadPendingNativeAttachments,
  openAttachment: openNativeAttachment,
} = useNativeAttachmentRuntime({
  model: () => model.value,
  recordId: () => recordId.value,
  maxBytes: () => nativeAttachmentMaxBytes.value,
  resolveLabel: (key, fallback) => resolveNativeAttachmentLabel(key, fallback),
  reloadTimeline: loadNativeChatterTimeline,
  viewerRef: attachmentViewerRef,
  onPendingUploadFailed: (message) => {
    validationErrors.value = [message];
    submissionFeedback.value = { kind: 'error', message };
    applyPageStatusEvent({ kind: 'status', transaction: 'primaryAction', status: 'error' });
  },
});
const nativeChatterAutoLoadKey = ref('');
const model = computed(() => String(route.params.model || v2ContractStore.value?.snapshot.pageInfo.model || ''));
const menuId = computed(() => Number(route.query.menu_id || 0) || 0);
const actionId = computed(() => {
  const rawRecordId = String(route.params.id || '').trim();
  const isCreateRoute = !rawRecordId || rawRecordId === 'new';
  const menuAction = findActionMetaByMenu(session.menuTree, menuId.value);
  return resolveActionIdFromContext({
    routeQuery: route.query as Record<string, unknown>,
    menuActionId: menuAction?.action_id,
    menuActionModel: menuAction?.model,
    currentActionId: isCreateRoute ? session.currentAction?.action_id : null,
    currentActionModel: session.currentAction?.model,
    model: model.value,
  });
});
const currentMenuTitle = computed(() => {
  const node = findMenuNode(session.menuTree, menuId.value);
  return String(node?.label || node?.name || node?.title || '').trim();
});
const recordId = computed(() => {
  const raw = String(route.params.id || '').trim();
  if (!raw || raw === 'new') return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
});
const recordIdDisplay = computed(() => (recordId.value ? String(recordId.value) : 'new'));
const recordContentLayoutMode = computed(() => showCurrentFormFieldConfigScope.value ? 'data-grid' : resolveContentLayoutMode({ contractContentLayout: contractContentLayoutMode(contract.value), pageKind: recordId.value ? (route.name === 'model-form' ? 'edit' : 'detail') : 'create' }));
const showHud = computed(() => isHudEnabled(route));
const showSceneBlocksDebug = computed(() => isSceneBlocksDebugEnabled(route));
const requestedSurface = computed<'user' | 'native' | 'hud'>(() => {
  const raw = String(route.query.surface || '').trim().toLowerCase();
  if (raw === 'native' || raw === 'hud' || raw === 'user') return raw;
  if (showHud.value) return 'hud';
  return 'user';
});
const requestedSourceMode = computed(() => (
  requestedSurface.value === 'native' ? 'native_parser' : 'governance_pipeline'
));
const busy = computed(() => busyKind.value !== null);
const {
  runPrimaryFormAction,
} = usePrimaryFormActionRuntime({
  actionId: () => actionId.value || 0,
  applyProjectionRefreshPolicy: (policy) => applyProjectionRefreshPolicy(policy),
  busyKind,
  confirmActionSafety: (action) => confirmActionSafety(action),
  errorMessage, hasChanges: () => hasChanges.value,
  modelName: () => model.value,
  navigateActionResponseResult: (result) => navigateActionResponseResult(result),
  primaryCreateFooterAction: () => primaryCreateFooterAction.value,
  primarySubmitAction: () => primarySubmitAction.value,
  recordId,
  reload: () => reload(),
  routeMenuId: () => route.query.menu_id,
  saveRecord: (refreshPolicy, options) => saveRecord(refreshPolicy, options),
  status,
  submissionFeedback,
  validationErrors,
});
const {
  runAction,
} = useFormActionRuntime({
  actionId: () => actionId.value || 0,
  applyClientMode: (mode, toggle) => applyClientMode(mode, toggle),
  applyProjectionRefreshPolicy: (policy) => applyProjectionRefreshPolicy(policy),
  busyKind,
  collectActionParams: (action) => collectActionParamsFromPlan(action, () => applyPageStatusEvent({ kind: 'status', transaction: 'runAction', status: 'error', errorMessage: '请填写操作原因' })),
  confirmActionSafety: (action) => confirmActionSafety(action),
  currentQuery: () => route.query,
  ensureSavedBeforeRecordAction: () => ensureSavedBeforeRecordAction(),
  errorMessage,
  executeSceneMutation: (input) => executeSceneMutation(input),
  modelName: () => model.value,
  navigateActionResponseResult: (result) => navigateActionResponseResult(result),
  recordId: () => recordId.value,
  reload: () => reload(),
  resolveNavigationUrl: (url) => resolveNavigationUrl(url),
  routeMenuId: () => route.query.menu_id,
  router,
  saveRecord: (refreshPolicy) => saveRecord(refreshPolicy),
  status,
  submissionFeedback,
});
const {
  navigateCreatedRecord,
} = useCreatedRecordNavigationRuntime({
  applyProjectionRefreshPolicy: (policy) => applyProjectionRefreshPolicy(policy),
  currentQuery: () => route.query as Record<string, unknown>,
  isQuickIntakeMode: () => isQuickIntakeMode.value,
  isStandardIntakeMode: () => isStandardIntakeMode.value,
  modelName: () => model.value,
  resolveWorkspaceContextQuery: () => readWorkspaceContext(route.query as Record<string, unknown>),
  returnToIntakeList: (createdId) => returnToIntakeList(createdId),
  router,
});
const {
  cancelIntake,
  openFilter,
  returnToIntakeList,
} = useFormNavigationActionsRuntime({
  actionId: () => actionId.value || 0,
  currentQuery: () => route.query as Record<string, unknown>,
  isIntakeCreateMode: () => isIntakeCreateMode.value,
  resolveLandingPath: (fallback) => session.resolveLandingPath(fallback),
  resolveWorkspaceContextQuery: () => readWorkspaceContext(route.query as Record<string, unknown>),
  router,
  searchFilters: () => searchFilters.value,
  setActiveFilterKey: (key) => {
    activeFilterKey.value = key;
  },
});
function recordVersionPolicy() {
  const raw = (contract.value as Record<string, unknown> | null)?.record_version;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const policy = raw as Record<string, unknown>;
  if (policy.enabled !== true) return null;
  const tokenField = String(policy.token_field || '').trim();
  const requestParam = String(policy.request_param || '').trim();
  if (!tokenField || requestParam !== 'if_match') return null;
  return { tokenField };
}
const requestedRenderProfile = computed<'create' | 'edit' | 'readonly'>(() => (
  resolveRequestedContractRenderProfile({ routeName: route.name, recordId: recordId.value })
));
const renderProfile = computed<'create' | 'edit' | 'readonly'>(() => {
  const globalStatus = resolveContractV2GlobalStatus(v2ContractStore.value);
  return resolveEffectiveContractRenderProfile({
    backendProfile: globalStatus?.effectiveRenderProfile,
    normalizedReady: Boolean(v2ContractStore.value),
    requestedProfile: requestedRenderProfile.value,
  });
});
const rights = computed(() => {
  const globalStatus = resolveContractV2GlobalStatus(v2ContractStore.value);
  const pageAuth = String(globalStatus?.pageAuth || '').trim().toLowerCase();
  if (globalStatus?.pageVisible === false || pageAuth === 'none') {
    return { read: false, write: false, create: false, unlink: false, duplicate: false };
  }
  const authoritative = resolveContractV2EffectiveFormCapabilities(v2ContractStore.value);
  if (authoritative) {
    return authoritative;
  }
  return { read: false, write: false, create: false, unlink: false, duplicate: false };
});
const canSave = computed(() => (
  renderProfile.value === 'edit'
    ? rights.value.write
    : renderProfile.value === 'create' && rights.value.create
));
const { driverConfig: contractFormDriverConfig, changeDriver: changeContractFormDriver } = useContractFormComponentDriverRuntime({
  actionId: () => actionId.value || 0, model: () => model.value, renderMode: () => renderProfile.value,
  featureFlag: () => session.featureFlags.scene_component_drivers_v1, previewKit: () => typeof route.query.scene_ui_kit === 'string' ? route.query.scene_ui_kit : '', isActive: () => isComponentActive.value && isFormPageRouteOwner(route.name),
});
const relationRecordCountLabel = computed(() => {
  const template = relationSearchDialog.labels.record_count || '%s 条记录';
  const count = String(relationSearchDialog.rows.length);
  return template.includes('%s') ? template.replace('%s', count) : `${count} ${template}`.trim();
});
const isQuickIntakeMode = computed(() => {
  if (recordId.value) return false;
  return String(route.query.intake_mode || '').trim().toLowerCase() === 'quick';
});
const isStandardIntakeMode = computed(() => {
  if (recordId.value) return false;
  if (isQuickIntakeMode.value) return false;
  return String(route.query.intake_mode || '').trim().toLowerCase() === 'standard';
});
const isIntakeCreateMode = computed(() => isQuickIntakeMode.value || isStandardIntakeMode.value);
const showNativeCollaborationPanel = computed(() => shouldShowNativeCollaborationPanel({
  hasChatterActions: nativeChatterActions.value.length > 0,
  hasAttachments: Boolean(nativeAttachments.value),
  isIntakeCreateMode: isIntakeCreateMode.value,
}));
const intakeAutosaveKey = computed(() => {
  if (!isIntakeCreateMode.value) return '';
  const mode = isQuickIntakeMode.value ? 'quick' : 'standard';
  const userId = Number(session.user?.id || 0) || 0;
  return `sc:intake:autosave:${String(model.value || 'record')}:${mode}:u${userId}`;
});
const intakeAutosaveFields = computed(() => [] as string[]);
const quickRequiredReady = computed(() => {
  if (!isQuickIntakeMode.value) return true;
  return intakeRequiredReadyCount.value >= intakeRequiredFields.value.length;
});
const standardCreateReady = computed(() => {
  if (!isStandardIntakeMode.value) return true;
  return intakeRequiredReadyCount.value >= intakeRequiredFields.value.length;
});
function hasPendingInlineRelationChange() {
  return layoutNodes.value.some((node) => {
    if (node.kind !== 'field' || node.readonly) return false;
    const descriptor = canonicalFormFields.value[node.name];
    if (fieldType(descriptor) !== 'many2one') return false;
    const inline = relationInlineCreate(descriptor);
    if (!inline.enabled || !inline.createOnNoMatch) return false;
    const currentId = Number(formData[node.name] || 0);
    if (Number.isFinite(currentId) && currentId > 0) return false;
    return Boolean(relationKeyword(node.name).trim());
  });
}
function hasPendingMany2manyTagCreate() {
  return Object.entries(relationKeywords).some(([name, keyword]) => {
    if (!String(keyword || '').trim()) return false;
    if (!isFieldWritable(name)) return false;
    if (!Array.isArray(formData[name])) return false;
    const descriptor = canonicalFormFields.value[name];
    const inline = relationInlineCreate(descriptor);
    if (!inline.enabled || !inline.createOnNoMatch) return false;
    return Boolean(relationModel(name));
  });
}
function hasOne2manyDraftChanges() {
  return layoutNodes.value.some((node) => {
    if (node.kind !== 'field' || node.readonly) return false;
    const descriptor = canonicalFormFields.value[node.name];
    if (fieldType(descriptor) !== 'one2many') return false;
    return one2manyFieldRows(node.name).some((row) => row.isNew || row.dirty || row.removed);
  });
}
const hasChanges = computed(() => {
  if (hasPendingInlineRelationChange()) return true;
  if (hasPendingMany2manyTagCreate()) return true;
  if (hasOne2manyDraftChanges()) return true;
  const statusField = nativeStatusbar.value.field;
  if (
    statusField
    && !nativeStatusbar.value.readonly
    && comparableFieldValue(statusField, formData[statusField]) !== comparableFieldValue(statusField, originalValues.value[statusField])
  ) {
    return true;
  }
  const keys = Object.keys(formData);
  return keys.some((key) => {
    if (!isFieldWritable(key)) return false;
    return comparableFieldValue(key, formData[key]) !== comparableFieldValue(key, originalValues.value[key]);
  });
});
const writableFieldCount = computed(() =>
  layoutNodes.value.filter((node) => node.kind === 'field' && !node.readonly).length,
);
const changedFieldCount = computed(() =>
  Object.keys(formData).filter((key) => isFieldWritable(key) && comparableFieldValue(key, formData[key]) !== comparableFieldValue(key, originalValues.value[key])).length
    + (hasOne2manyDraftChanges() ? 1 : 0),
);
const intakeRequiredFields = computed(() => {
  if (!isIntakeCreateMode.value) return [];
  return layoutNodes.value
    .filter((node) => node.kind === 'field' && node.required && isFieldVisible(node.name))
    .map((node) => ({ name: node.name, label: node.label || node.name }));
});
const intakeRequiredReadyCount = computed(() => {
  if (!isIntakeCreateMode.value) return 0;
  return intakeRequiredFields.value.filter((field) => {
    const value = formData[field.name];
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return value.trim().length > 0;
    if (typeof value === 'number') return Number.isFinite(value) && value > 0;
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === 'boolean') return true;
    return Boolean(value);
  }).length;
});
const intakeMissingRequiredLabels = computed(() => {
  if (!isIntakeCreateMode.value) return [];
  return intakeRequiredFields.value
    .filter((field) => {
      const value = formData[field.name];
      if (value === null || value === undefined) return true;
      if (typeof value === 'string') return value.trim().length === 0;
      if (typeof value === 'number') return !Number.isFinite(value) || value <= 0;
      if (Array.isArray(value)) return value.length === 0;
      return false;
    })
    .map((field) => String(field.label || '').trim())
    .slice(0, 5);
});
const intakeRequiredSummary = computed(() => {
  if (!isIntakeCreateMode.value) return '';
  const total = intakeRequiredFields.value.length;
  const done = intakeRequiredReadyCount.value;
  if (total <= 0) return '当前页面未提供必填字段约束。';
  return `${done}/${total}`;
});
const intakeMissingSummary = computed(() => {
  if (!isIntakeCreateMode.value) return '';
  if (!intakeMissingRequiredLabels.value.length) return '无';
  return intakeMissingRequiredLabels.value.join('、');
});
const one2manyValidation = computed(() => collectOne2manyDraftValidation());
const currentActionMeta = computed(() => findActionMetaByMenu(session.menuTree, menuId.value, actionId.value || undefined));
const currentBusinessCategoryContext = computed(() => resolveBusinessCategoryContext({
  contractRecord: contract.value,
  routeQuery: route.query as Record<string, unknown>,
  relationBusinessCategoryLabel: relationKeywords.business_category_id,
}));
const currentBusinessCategoryLabel = computed(() => currentBusinessCategoryContext.value.label);
const currentBusinessCategoryCode = computed(() => currentBusinessCategoryContext.value.code);
const pageIdentityInput = computed(() => buildContractFormPageIdentity({
  action: currentActionMeta.value, breadcrumbs: resolveRoutePageIdentity(route, session.menuTree).breadcrumbs,
  businessCategoryLabel: currentBusinessCategoryLabel.value, contract: contract.value, formData,
  entryTitle: route.query.entry_title,
  isCreate: !recordId.value, isEdit: route.name === 'model-form',
  menuName: currentMenuTitle.value, modelName: model.value, recordMissing: recordMissing.value,
  renderError: Boolean(renderErrorMessage.value), status: status.value,
}));
const pageIdentity = usePublishedPageIdentity(pageIdentityInput, { routeKey: () => route.fullPath,
  active: () => isComponentActive.value && isFormPageRouteOwner(route.name), onTitle: (title) => session.updateActiveActivityTitle(title) });
const pageDisplayTitle = computed(() => pageIdentity.value.title);
const pageDisplaySubtitle = computed(() => pageIdentity.value.subtitle || '');
const suppressPageHeaderTitle = computed(() => true);
const currentRenderProfileLabel = computed(() => renderProfileLabel(renderProfile.value));
const intakeCreateButtonLabel = computed(() => {
  return busy.value && busyKind.value === 'save' ? formUiLabel('saving') : formUiLabel('save');
});
const submitButtonLabel = computed(() => resolveSubmitButtonLabel({
  busy: busy.value,
  busyKind: busyKind.value,
  footerActionLabel: primaryCreateFooterAction.value?.label || primarySubmitAction.value?.label || '',
  hasFooterAction: Boolean(primaryCreateFooterAction.value),
  hasPrimarySubmitAction: Boolean(primarySubmitAction.value),
  recordId: recordId.value,
  saveLabel: formUiLabel('save'),
  savingLabel: formUiLabel('saving'),
}));
const primaryBusinessActionState = computed(() => resolvePrimaryBusinessActionState({
  busy: busy.value, canSave: canSave.value,
  configurationMode: showCurrentFormFieldConfigScope.value, intakeMode: isIntakeCreateMode.value,
  hasChanges: hasChanges.value, hasRecord: Boolean(recordId.value),
  primaryCreateAction: primaryCreateFooterAction.value, primarySubmitAction: primarySubmitAction.value,
  quickSubmitDisabled: isQuickSubmitDisabled.value,
}));
const showPrimaryBusinessFormAction = computed(() => primaryBusinessActionState.value.show);
const showContinueProcessing = computed(() => (
  route.name === 'record'
  && Boolean(recordId.value)
  && rights.value.write
));
function continueProcessing() {
  if (!showContinueProcessing.value || !recordId.value) return;
  void router.push(buildModelFormRouteTarget({
    model: model.value,
    id: String(recordId.value),
    query: normalizeRouteQueryValues(route.query as Record<string, unknown>) as LocationQueryRaw,
  }) as Parameters<typeof router.push>[0]);
}
const showDraftSaveAction = computed(() => {
  if (!showPrimaryBusinessFormAction.value || !canSave.value || primaryCreateFooterAction.value) return false;
  if (!recordId.value) return true;
  return Boolean(primarySubmitAction.value) && hasChanges.value;
});
const draftSaveButtonLabel = computed(() => {
  if (busy.value && busyKind.value === 'save') return formUiLabel('saving');
  return recordId.value ? '保存修改' : '保存草稿';
});
const showDiscardAction = computed(() => !isIntakeCreateMode.value && Boolean(recordId.value) && hasChanges.value);
const groupedHeaderActions = computed(() => groupContractHeaderActions({
  actions: headerActions.value, intakeMode: isIntakeCreateMode.value, nativeTree: useNativeFormTree.value,
  configurationMode: showCurrentFormFieldConfigScope.value,
  isSubmitAction: isUnifiedSubmitAction,
}));
const headerBusinessActionPresentation = computed(() => presentContractHeaderActions({
  direct: groupedHeaderActions.value.direct, overflow: groupedHeaderActions.value.overflow,
  excludedKeys: new Set([
    primaryCreateFooterAction.value?.key,
    primarySubmitAction.value?.key,
  ].filter((key): key is string => Boolean(key))),
}));
const headerBusinessDirectActions = computed(() => headerBusinessActionPresentation.value.direct);
const headerBusinessOverflowActions = computed(() => headerBusinessActionPresentation.value.overflow);
const headerConfigActionsVisible = computed(() => groupedHeaderActions.value.configuration);
const nativeCanvasFormLayoutNodes = computed<NativeFormLayoutNode[]>(() => {
  const primaryMethod = String(
    (!recordId.value ? primaryCreateFooterAction.value : primarySubmitAction.value)?.methodName || '',
  ).trim();
  const filterNodes = (nodes: NativeFormLayoutNode[]): NativeFormLayoutNode[] => nodes.flatMap((node) => {
    if (node.type === 'header' && !showCurrentFormFieldConfigScope.value) return [];
    const actionMethod = String(node.name || node.action?.name || '').trim();
    if (primaryMethod && node.type === 'button' && actionMethod === primaryMethod) return [];
    const children = Array.isArray(node.children) ? filterNodes(node.children) : node.children;
    if (node.type === 'header' && Array.isArray(children) && !children.length) return [];
    return [{ ...node, ...(Array.isArray(children) ? { children } : {}) }];
  });
  return filterNodes(nativeFormLayoutNodes.value);
});
const contractV2ActionRules = computed(() => resolveContractV2ActionRules(v2ContractStore.value) as unknown as Array<Record<string, unknown>>);
function contractFieldActions(field: FormSectionFieldSchema) {
  return buildContractFieldActionsFromRules({
    rules: contractV2ActionRules.value,
    fieldName: field.name,
    mode: activeContractMode.value,
    visibilityDraft: fieldVisibilityDraft,
    busy: busy.value,
  });
}
function formSettingsFieldActions(field: FormSectionFieldSchema) {
  const fieldKey = String(field.name || '').trim();
  const existingRow = activeContractModeFieldRows.value.find((row) => row.fieldKey === fieldKey);
  return buildFormSettingsFieldActionsFromRules({
    fieldName: fieldKey,
    existingActions: existingRow?.actions,
    visibilityDraft: fieldVisibilityDraft,
    busy: busy.value,
  });
}
const activeContractModeActions = computed(() => {
  return buildActiveContractModeActions({
    rules: contractV2ActionRules.value,
    mode: activeContractMode.value,
    excludedKeys: [BUSINESS_CONFIG_ACTION_KEYS.currentFormFieldOrderSave],
  });
});
const {
  fieldOrderDraft, fieldOrderPreviewActive, nativeFormDesignFieldKeys, nativeFormDesignFieldLabels, formConfigFieldLabelCache,
  fieldGroupBase, fieldGroupSavedBase, fieldGroupDraft, formLayoutColumnsBase, formLayoutColumnsDraft,
  formLayoutColumnsConfigured, groupVisibilityBase, groupVisibilityDraft, groupColumnsBase, groupColumnsDraft,
  fieldSizeBase, fieldSizeDraft, formLayoutDirty, groupLayoutDirtyKeys, fieldLayoutDirtyKeys,
  fieldMoveTargetDraft, draggingFieldKey, draggingFieldLabel, dropTargetFieldKey, dropTargetPlacement,
  onFieldOrderDragStart, onFieldOrderDragOver, onFieldOrderDragLeave, onFieldOrderDragEnd, onFieldOrderWindowDragOver,
  onFieldOrderWindowDragStop, resetFieldOrderDropTarget, selectedFormSettingsFieldKey, selectedFormSettingsFieldLabel, selectedFormSettingsFieldGroupTitleDraft,
  selectedFormSettingsFieldGroupTitleEdit, formDesignerFieldSearchText, selectedFormSettingsOrderTargetKey, selectedFormSettingsOrderPlacement, isContractFieldOrderEditable,
  showReturnToBusinessConfigAction, fieldVisibilityBase, fieldVisibilityDirty, fieldVisibilityDraft, fieldVisibilityDirtyKeys,
  formConfigAuditBusy, formConfigAuditResult, formConfigOperationLog, formConfigOperatorName, appendFormConfigOperation,
  markPendingFormConfigOperations, clearFormConfigOperationLog, onFormLayoutColumnsChange, onSelectedFormSettingsGroupVisibilityChange, onSelectedFormSettingsGroupColumnsChange,
  onSelectedFormSettingsFieldSizeChange, resetContractFieldOrder, onContractInlineGroupRename, moveFieldOrder, moveSelectedFormSettingsFieldToOrderTarget,
  onSelectedFormSettingsFieldGroupMoveChange, onFieldOrderDrop, onFieldOrderGroupDrop, hideSuggestedInternalFields, onFieldVisibilityDraftChange,
  onSelectedFormSettingsFieldVisibilityChange, onContractInlineFieldLabelChange, setInlineFieldPolicy, closeContractPromptAction, contractPromptFields,
  contractPromptRule, contractPromptValues, openContractModeAction, runContractRuleAction, setContractPromptValue,
  submitContractPromptAction, lowCodeFieldCreateDialog, openCentralCustomFieldCreate, onContractInlineFieldAddAfter, onContractInlineGroupAddField,
  closeInlineCustomFieldCreate, setFieldCreateLabel, setFieldCreateType, submitInlineCustomFieldCreate, lowCodeContractLoaded,
  lowCodeContractHydrating, lowCodePrecheckWarnings, lowCodeContractList, lowCodeSelectedContractName, lowCodeFormLayoutBase,
  lowCodeLayoutDraft, saveContractFieldOrder, contractModeBaseFieldRows, activeContractModeFieldRows, currentFormDesignFieldKeys,
  currentFormOrderedFieldKeys, selectedFormSettingsOrderTargetOptions, syncFieldOrderDraftWithDesignKeys, hasFieldOrderChanges, formVisibilityDraftFieldKeys,
  hasFieldVisibilityChanges, hasFieldGroupChanges, effectiveGroupVisible, effectiveGroupColumns, effectiveFieldSize,
  hasFormLayoutChanges, hasGroupLayoutChanges, hasFieldLayoutChanges, hasCurrentFormFieldDraftChanges, formConfigFieldLabelReplacementEntries,
  formatFormConfigOperationSummary, formDesignFieldLabel, rememberFormConfigFieldLabel, suggestedHiddenFieldRows, changedFieldVisibilityDraft,
  changedFieldGroupDraft, effectiveFieldGroupTitleForDraft, auditCurrentFormConfiguration, showCurrentFormFieldConfigScope, showLowCodeTechnicalDetails,
  currentFormConfigPageLabel, formFieldConfigScope, formConfigAuditSummary, selectedFormSettingsFieldRow, nativeFieldStructureGroups,
  currentFormDesignFieldCount, currentFormGroupOptions, formDesignerGroupNavigatorItems, formDesignerFieldSearchQuery, formDesignerSearchableFieldRows,
  formDesignerFilteredFieldRows, selectedFormSettingsFieldGroupTitle, selectedFormSettingsGroupVisible, selectedFormSettingsGroupColumns, selectedFormSettingsFieldSize,
  syncLayoutDraftFromFormSpec, syncFieldDraftFromFormSpec, applyRuntimeInferredFormColumns, hydrateLowCodeDraftFromContract, refreshLowCodeFormLayoutBase,
  loadLowCodeContractList, switchLowCodeContractByName, publishSelectedLowCodeContract, rollbackSelectedLowCodeContract, buildLowCodeViewOrchestration,
  lowCodeLayoutFieldLabel, effectiveLowCodeFieldLabel,
} = useRecordFormDesigner({
  BUSINESS_CONFIG_INTENTS, BUSINESS_CONFIG_MODES, BUSINESS_CONFIG_ROUTE_FLAGS,
  FORM_FIELD_CONFIG_INTENTS, actionId, activeContractMode,
  applyClientMode: (mode: string, toggle?: boolean) => applyClientMode(mode, toggle), applyPageStatusEvent, buildCurrentFormGroupOptions,
  buildFormConfigFieldLabelReplacementEntries, buildFormDesignerGroupNavigatorItems, buildFormDesignerSearchableFieldRows,
  buildFormFieldConfigScope, buildLowCodeViewOrchestrationFromDraft, busy,
  busyKind, changedFieldGroupFromDrafts, changedFieldVisibilityFromDrafts,
  collectLowCodeLayoutFromViewOrchestration, collectNativeFieldStructureGroups, collectNativeLayoutGroupTitles,
  contract, contractActionRuleClientMode, contractActionRuleControl,
  contractActionRuleKey, contractFieldLabel: (...args: [string]) => contractFieldLabel(...args), contractFieldSequence: (fieldKey: string, fallback?: number) => contractFieldSequence(fieldKey, fallback),
  contractModeFeedback, contractV2ActionRules, currentBusinessCategoryLabel,
  effectiveFieldGroupTitleFromDrafts, ensureFieldOrderDraftStartsFromCurrentLayout: (...args: []) => ensureFieldOrderDraftStartsFromCurrentLayout(...args), errorMessage,
  extractLowCodeFormFieldDraftState, extractLowCodeLayoutDraftState, filterFormDesignerFieldRows,
  formSettingsActiveTab, formatFormConfigAuditSummary, formatFormConfigOperationSummaryText,
  inferLowCodeLayoutColumns, intentRequest, isBusinessConfigRuntimeModel,
  isReadableFieldGroupTitle, isSuggestedInternalFormField, layoutHasReadableFieldGroups,
  lowCodeApplyBaseParams: () => lowCodeApplyBaseParams(), lowCodeFormSpecFromViews, lowCodeLayoutFieldLabelFromNodes,
  lowCodeLayoutFromFormSpec, lowCodeScopedContractName, lowCodeViewsFromContractResponse,
  mergeLowCodeLayoutWithRuntimeGroupShells, model, nativeFormLayoutNodes: computed(() => nativeFormLayoutNodes.value),
  normalizeConfigPageLabel, normalizeContractV2ContainersForNativeFormFromTree, normalizeFieldGroupTitle,
  normalizeFormConfigAuditResult, normalizeLowCodeContractListRows, pageDisplayTitle,
  parseMaybeJsonRecord, rawNativeFormLayoutNodes: computed(() => rawNativeFormLayoutNodes.value), readableFallbackFieldLabel,
  reload: (...args: []) => reload(...args), resolveContractV2ContainerTree, resolveFormDesignFieldLabel,
  resolveSelectedFormSettingsFieldGroupTitle, route,
  routeQueryText: designerRouteQueryText, runtimeNativeFormLayoutNodes: (...args: []) => runtimeNativeFormLayoutNodes(...args), session,
  showHud, status, useContractModeActionRuntime,
  useFieldOrderDragRuntime, useFieldOrderMutationRuntime, useFieldVisibilityDraftRuntime,
  useFormConfigOperationLog, useFormConfigSaveRuntime, useFormSettingsGroupRuntime,
  useFormSettingsLayoutRuntime, useInlineFieldPolicyRuntime, useLowCodeFieldCreateRuntime,
  v2ContractStore,
});
const isQuickSubmitDisabled = computed(() => {
  if (busy.value) return true;
  if (!canSave.value) return true;
  if (isQuickIntakeMode.value) return !quickRequiredReady.value;
  return Boolean(recordId.value) && !hasChanges.value;
});
const primaryFormActionDisabled = computed(() => primaryBusinessActionState.value.disabled);
const primaryFormActionHint = computed(() => {
  if (primarySubmitAction.value && !primarySubmitAction.value.enabled) return primarySubmitAction.value.hint;
  return primarySubmitAction.value && recordId.value && hasChanges.value ? '请先保存修改，再提交审批' : '';
});
const primaryBusinessFormAction = computed(() => (
  !recordId.value ? primaryCreateFooterAction.value : primarySubmitAction.value
));
const draftSaveDisabled = computed(() => {
  if (busy.value) return true;
  if (!canSave.value) return true;
  return Boolean(recordId.value) && !hasChanges.value;
});
const isStandardCreateDisabled = computed(() => {
  if (busy.value) return true;
  if (!canSave.value) return true;
  if (isStandardIntakeMode.value) return !standardCreateReady.value;
  return false;
});
const isIntakeCreateDisabled = computed(() => {
  if (!isIntakeCreateMode.value) return false;
  if (isQuickIntakeMode.value) return isQuickSubmitDisabled.value;
  return isStandardCreateDisabled.value;
});
const {
  persist: persistIntakeAutosave, restore: restoreIntakeAutosave, clear: clearIntakeAutosave,
} = useIntakeAutosaveRuntime({
  key: intakeAutosaveKey, hasRecord: recordId, formData, fields: intakeAutosaveFields,
});
const contractMetaLine = computed(() => {
  if (!v2ContractStore.value) return '';
  const mode = String(contractMeta.value?.contract_mode || '-');
  const surface = String(contractMeta.value?.contract_surface || '-');
  const viewType = String(v2ContractStore.value.snapshot.pageInfo.viewType || '-');
  const filters = Array.isArray(resolveContractV2SearchContract(v2ContractStore.value).filters) ? (resolveContractV2SearchContract(v2ContractStore.value).filters as unknown[]).length : 0;
  const transitions = Array.isArray(resolveContractV2WorkflowContract(v2ContractStore.value).transitions) ? (resolveContractV2WorkflowContract(v2ContractStore.value).transitions as unknown[]).length : 0;
  const profileLabels: Record<string, string> = {
    create: '新建',
    edit: '编辑',
    readonly: '只读',
  };
  const permissionLabels = [
    rights.value.read ? '可查看' : '',
    rights.value.write ? '可编辑' : '',
    rights.value.create ? '可新建' : '',
    rights.value.unlink ? '可删除' : '',
  ].filter(Boolean);
  const valueLabel = (value: string, labels: Record<string, string>) => {
    const normalized = String(value || '').trim().toLowerCase();
    if (!normalized || normalized === '-') return '未配置';
    return labels[normalized] || value;
  };
  const modeLabel = valueLabel(mode, {
    native: '标准表单',
    governed: '受控表单',
    action: '操作页面',
    legacy: '历史承载',
  });
  const surfaceLabel = valueLabel(surface, {
    native: '标准界面',
    governed: '受控界面',
    business_config: '配置界面',
    lowcode_config: '低代码配置',
  });
  const viewTypeLabel = valueLabel(viewType, {
    form: '表单',
    tree: '列表',
    list: '列表',
    kanban: '看板',
    search: '搜索',
    calendar: '日历',
    pivot: '透视',
    graph: '图表',
  });
  return `配置模式：${modeLabel} · 承载界面：${surfaceLabel} · 视图类型：${viewTypeLabel} · 页面状态：${profileLabels[renderProfile.value] || renderProfile.value} · 筛选项：${filters} · 流转项：${transitions} · 操作权限：${permissionLabels.join('、') || '无可用权限'}`;
});
const showDebugActions = computed(() => renderProfile.value !== 'create');
const showDebugActionsVisible = computed(() => showHud.value && showDebugActions.value);
const runtimeRoleCode = computed(() => String(session.roleSurface?.role_code || '').trim().toLowerCase());
const runtimeRoleCodes = computed(() => {
  const configured = session.roleSurface?.role_codes || [];
  const roles = configured.length ? configured : [runtimeRoleCode.value];
  return roles.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean);
});
const runtimeCapabilities = computed(() => collectRuntimeCapabilities(session));
const policyContext = computed(() => ({
  profile: renderProfile.value,
  formData: formData as Record<string, unknown>,
  capabilities: runtimeCapabilities.value,
  roleCode: runtimeRoleCode.value,
  roleCodes: runtimeRoleCodes.value,
}));
const warnings = computed(() => normalizeContractWarnings(undefined));

const contractAccessPolicy = computed<ContractAccessPolicy>(() => {
  return normalizeContractAccessPolicy(undefined);
});

const workflowTransitions = computed(() => buildWorkflowTransitions({
  rows: resolveContractV2WorkflowContract(v2ContractStore.value).transitions,
  actions: contractActions.value,
  profile: renderProfile.value,
  showHud: showHud.value,
}));
const searchFilters = computed(() => normalizeSearchFilters(resolveContractV2SearchContract(v2ContractStore.value).filters));

const showSearchFilters = computed(() => {
  if (useNativeFormTree.value) return false;
  if (!v2ContractStore.value) return true;
  if (renderProfile.value !== 'create') return true;
  return true;
});

const {
  relationIds, selectedRelationOptions, many2oneValue, relationOptionsForField, hydrateSelectedRelationOptions,
  one2manyRelationModel, one2manyRelationFieldDescriptor, nativeNodeFieldDescriptor, findNativeFieldNode, effectiveFieldDescriptor,
  nativeFieldSubview, one2manyColumns, one2manyPolicies, one2manyCanCreate,
  one2manyCreateLabel, one2manyPrimaryColumn, one2manyRowLabel, one2manySummary, hydrateOne2manyRows,
  hydrateVisibleOne2manyRows, one2manyRowErrors, setRelationKeyword, filteredRelationOptions, relationModel,
  formUiLabels, formUiLabel, dynamicDomainFromDescriptor, resolveDynamicDomainDependencyValue, clearDynamicRelationDependents,
  relationDomain, runtimeRelationDomain, mergedRelationDomain, queryRelationOptions, fetchRelationOptions,
  loadRelationSearchColumns, fetchRelationSearchRows, onRelationDialogDocumentKeydown, openRelationSearchDialog, runRelationSearch,
  confirmRelationSearchSelection, selectRelationSearchOption, setMany2oneOption, switchFormByRelationOption, createRelationFromSearchDialog,
  ensureRelationFieldDescriptors, openRelationCreateForm, currentRelationRecordId, canOpenRelationRecordForm, openRelationRecordForm,
  quickCreateRelation,
} = useRecordRelationships({
  ApiError, actionId, clearedDynamicRelationFields,
  closeRelationSearchDialog, confirmRelationSearchSelectionFromRuntime, contract,
  contractFieldLabel: (...args: [string]) => contractFieldLabel(...args), createContractFormRecord, deniedRelationModels,
  dynamicDomainDependencyFields, dynamicRelationDomainFromDescriptor, ensureOne2manyRows,
  fallbackRelationSearchColumns, fetchRelationOptionsFromRuntime, fieldModifierMap: computed(() => fieldModifierMap.value),
  fieldType, filteredRelationOptionsFromRuntime, findNativeFieldNodeInTree,
  formData, formUiLabelFromLabels, formUiLabelsFromFormView,
  invalidatedRelationKeywords, isWritableFieldVisible: (...args: [string]) => isWritableFieldVisible(...args), layoutNodes: computed(() => layoutNodes.value),
  listContractFormRecords, loadModelContractV2, markFieldChanged,
  menuId, mergeHydratedOne2manyRecords, mergeRelationDomains,
  mergeRelationOptions, model, nativeFieldSubviewFromTree,
  nativeFormLayoutNodes: computed(() => nativeFormLayoutNodes.value), nativeNodeFieldDescriptorFromNode, normalizeFieldValue: (...args: [string, unknown]) => normalizeFieldValue(...args),
  normalizeRelationIds, normalizeRouteQueryValues,
  onchangeModifiersPatch, one2manyCanCreateFromPolicies, one2manyColumnsFromSubview,
  one2manyCreateLabelFromPolicies, one2manyDraftSummary, one2manyFieldRows,
  one2manyPrimaryColumnFromColumns, one2manyRowLabelFromPrimary, one2manySubviewPolicies,
  one2manyValidation, openRelationSearchFromRuntime, pickContractNavQuery,
  queryRelationOptionsFromRuntime, rawNativeFormLayoutNodes: computed(() => rawNativeFormLayoutNodes.value), readContractFormRecord,
  recordId, relationCreateMode, relationDomainFromDescriptor,
  relationEntry, relationFieldDescriptors, relationInlineCreate,
  relationKeyword, relationKeywords, relationModelFromDescriptor,
  relationOptions, relationOptionsForFieldFromRuntime, relationOptionsFromRecords,
  relationOrder, relationQueryTimers, relationReadFields, renderProfile,
  relationSearchColumnsFromContract, relationSearchDialog, relationSearchDialogContract,
  relationSearchLimit, relationSearchOrder, relationSearchReadFields,
  relationSearchRowsFromRecords, relationUiLabel, relationUiLabels,
  reload: (...args: []) => reload(...args), route, router,
  runRelationSearchFromRuntime, runtimeRelationDomainFromModifiers, sanitizeUiErrorMessage,
  selectOne2manySubview, selectRelationSearchOptionFromRuntime, selectedRelationOptionsFromRuntime,
  setRelationKeywordValue, v2ContractStore, validationErrors,
});
const {
  currentWorkflowContract, workflowContractActionRows, blockingWorkflowEvidenceMessage, applyWorkflowContractToAction, shouldShowWorkflowNativeAction,
  workflowEvidenceGateRows, contractActions, headerActions, bodyActions, contractFieldLabels,
  contractFieldLabel, activeActivityAction, nativeAttachmentMaxBytes, nativeChatterActions, nativeAttachments,
  nativeCollaborationPanelProps, nativeCollaborationPanelListeners, resolveNativeAttachmentLabel, hasNativeChatterNode, nativeLayoutContainsType,
  contractActionFromNativeRow, resolveNativeActionState, isUnifiedSubmitMethod, isUnifiedSubmitAction,
  primarySubmitAction, primaryCreateFooterAction, runNativeLayoutAction, advancedFieldNames, contractVisibleFields,
  coreFieldNames, fieldSemanticMeta, focusFirstValidationError, focusValidationError, hasAdvancedFields,
  nonSceneValidationErrors, policyRequiredFields, reloadLatestRecord, sceneReadyFormSurface, sceneValidationPanel,
  sceneValidationRequiredFields, strictContractDefaultsSummary, strictContractGuard, strictContractMissingSummary, strictContractMode,
  useSceneFormAugmentations, validationRequiredFields, baseNativeFormLayoutNodes, currentNativeFieldOrder, ensureFieldOrderDraftStartsFromCurrentLayout,
  evaluateNativeActionVisibility, evaluateNativeModifierValue, fieldModifierMap, formDataFieldNames, isFieldVisible,
  isNativeFavoriteField, isNativeFieldVisible, isNativeLayoutNodeVisible, isWritableFieldVisible, nativeFormLayoutNodes,
  nativeFormRootColumns, nativeGroupCount, nativeNotebookPageCount, nativeStatusbar, nativeVisibleFieldNames,
  nativeVisibleSectionTitles, rawNativeFormLayoutNodes, resolveNativeButtonLabel, runtimeFieldStates, runtimeNativeFormLayoutNodes,
  runtimeState, setStatusbarValue, showNativeDefaultSectionTitle, useNativeFormTree, layoutNodes,
  nativeFieldSchemasForNodes, collectSceneValidationPrecheckErrors, onTemplateFieldChange, relationFieldAdapter,
} = useRecordActionPresentation({
  ErrorCodes, actionId, activeChatterLabel,
  activeChatterMode, activityAssigneeId, activityDeadline,
  activityNote, activitySummary, activityUpdatingIds,
  addOne2manyRow, advancedExpanded, applyPageStatusEvent,
  applyWorkflowAvailability, attachmentError, attachmentUploading,
  buildContractFormActions, busy, busyKind,
  canOpenRelationRecordForm, changedFieldGroupDraft, chatterDraft,
  chatterError, chatterPosting, chatterTimeline, chatterTimelineHasMore, chatterTimelineLoading,
  closeNativeChatterComposer, collaborationUserChoices, collaborationUserOptions,
  collaborationUserQuery, collaborationUsersLoading, collectContractV2ButtonStatusById,
  collectSceneValidationPrecheckErrorsFromRules, commitMany2oneInline: (...args: Parameters<typeof commitMany2oneInline>) => commitMany2oneInline(...args),
  confirmActionSafety: (action: ContractAction) => confirmActionSafety(action), contract, detectObjectMethodFromActionKey,
  dispatchTemplateFieldChange, effectiveFieldSize, effectiveGroupVisible,
  ensureSavedBeforeRecordAction: () => ensureSavedBeforeRecordAction(), executeButton, fieldGroupBase,
  fieldGroupDraft, fieldInputType, fieldMoveTargetDraft,
  fieldOrderDraft, fieldOrderPreviewActive, fieldVisibilityDraft,
  filteredRelationOptions, focusProductFormValidationError, formConflict,
  formData, formLayoutColumnsDraft, inputFieldValue,
  intentConfirmationRef, isContractFieldOrderEditable, isMissingRequiredValue,
  isIntakeCreateMode, isQuickIntakeMode, isTierValidationActionHidden: (methodName: string) => isTierValidationActionHidden(methodName),
  layoutContainsType, loadCollaborationUsers, loadMoreNativeChatterTimeline, lowCodeFormLayoutBase,
  many2oneValue, markFieldChanged, model,
  nativeFormDesignFieldKeys, nativeFormDesignFieldLabels, nativeLayoutVisibilityRevision,
  navigateActionResponseResult, normalizeActionKind, normalizeActionSafety,
  normalizeRequiredParams, normalizeWorkflowActionRows, normalizeWorkflowEvidenceGateRows,
  onNativeAttachmentSelected, onchangeModifiersPatch, one2manyCanCreate,
  one2manyColumnDisplayValue, one2manyColumnInputType, one2manyColumns,
  one2manyCreateLabel, one2manyRowErrors, one2manyRowHints,
  one2manyRowLabel, one2manyRowStateLabel, one2manySummary,
  openNativeAttachment, openNativeChatterAction, openRelationCreateForm,
  parseMaybeJsonRecord, pendingNativeAttachments, policyContext,
  queryMany2oneInline: (...args: Parameters<typeof queryMany2oneInline>) => queryMany2oneInline(...args), recordId, relationCreateMode,
  relationIds, relationInlineCreate, relationKeyword,
  relationOptionsForField, relationUiLabel, reload: (...args: Parameters<typeof reload>) => reload(...args),
  rememberFormConfigFieldLabel, removeMentionUser, removeOne2manyRow,
  removePendingNativeAttachment, removedOne2manyRows, renderProfile,
  resolveContractFormFieldLabels, resolveContractV2ActionRules, resolveContractV2RuntimeContract,
  resolveInputPlaceholder, resolvePrimaryCreateFooterAction,
  resolveSelectPlaceholder, resolveWorkflowContractFromStore,
  restoreOne2manyRow, rights, route,
  runAction, runtimeRoleCode, selectMentionUser,
  selectedMentionUsers, selectedRelationOptions, sendNativeChatter,
  session, setBooleanField: (...args: Parameters<typeof setBooleanField>) => setBooleanField(...args), setMany2oneField: (...args: Parameters<typeof setMany2oneField>) => setMany2oneField(...args),
  setOne2manyRowField, setRelationIds: (...args: Parameters<typeof setRelationIds>) => setRelationIds(...args), setRelationKeyword,
  setRelationMultiField: (...args: Parameters<typeof setRelationMultiField>) => setRelationMultiField(...args), setSelectionField: (...args: Parameters<typeof setSelectionField>) => setSelectionField(...args), setTextField: (...args: Parameters<typeof setTextField>) => setTextField(...args),
  shouldShowWorkflowAction, showHud, showOne2manyErrors,
  toDateInputValue, toDatetimeInputValue, toPositiveInt,
  updateNativeActivity, useRecordCollaborationPresentation, useRecordContractSemantics,
  useRecordFormFieldSchemas, useRecordFormLayout, v2ContractStore,
  validationErrors, visibleOne2manyRows,
});

// Cutover is allowed only when every executable canonical action has one exact
// adapter into the existing unified executor. Disabled actions remain visible
// with their server reason and do not require an execution adapter.
const canonicalActionExecutionError = computed(() => {
  const model = canonicalFormRenderState.value.model;
  if (!model) return '';
  const failure = validateCanonicalFormActionExecutors(collectCanonicalFormActions(model), contractActions.value);
  return failure ? `${failure.reasonCode}:${failure.actionId}:${failure.backendIdentity}` : '';
});
const canonicalFormDriverError = computed(() => (
  canonicalFormRenderState.value.error || canonicalActionExecutionError.value
));

async function runCanonicalFormAction(actionRef: ContractV2ActionRule) {
  const resolution = resolveCanonicalFormActionExecution(actionRef, contractActions.value);
  if (resolution.kind === 'error') {
    renderErrorMessage.value = resolution.reasonCode;
    return;
  }
  if (resolution.kind === 'save') {
    await saveRecord();
    return;
  }
  const action = resolution.action;
  const primary = primaryBusinessFormAction.value;
  if (primary && String(primary.backendIdentity || '').trim() === String(action.backendIdentity || '').trim()) {
    await runPrimaryFormAction();
    return;
  }
  await runAction(action);
}
const contractReadiness = computed<FormContractReadiness>(() => {
  if (!v2ContractStore.value) {
    return { usable: false, issues: ['contract not loaded'], fieldCount: 0, layoutFieldCount: 0, visibleCandidateCount: 0 };
  }
  const fieldCount = Object.keys(canonicalFormFields.value).length;
  const layoutFieldCount = layoutNodes.value.filter((node) => node.kind === 'field').length;
  const viewType = v2ContractStore.value.snapshot.pageInfo.viewType;
  return {
    usable: viewType === 'form' && fieldCount > 0,
    issues: viewType === 'form' && fieldCount > 0 ? [] : ['canonical form contract is incomplete'],
    fieldCount,
    layoutFieldCount,
    visibleCandidateCount: layoutFieldCount,
  };
});

let recordFormStateRuntime: ReturnType<typeof useRecordFormState>;
function markFieldChanged(name: string) { recordFormStateRuntime.markFieldChanged(name); }
function inputFieldValue(name: string) { return recordFormStateRuntime.inputFieldValue(name); }
recordFormStateRuntime = useRecordFormState({
  formFields: canonicalFormFields, model, recordId, rights, formData, originalValues, submissionFeedback, relationKeywords,
  invalidatedRelationKeywords, clearedDynamicRelationFields, relationQueryTimers, relationOptions,
  validationErrors, onchangeModifiersPatch, onchangeWarnings, onchangeLinePatches, applyingOnchangePatch,
  changedFieldSet, dirtyFieldSet, getOnchangeTimer: () => onchangeTimer,
  setOnchangeTimer: (timer) => { onchangeTimer = timer; }, contractV2ActionRules, layoutNodes,
  nativeStatusbar, route, isNativeFavoriteField, clearDynamicRelationDependents,
  openRelationCreateForm, openRelationSearchDialog, openRelationRecordForm, relationOptionsForField,
  switchFormByRelationOption, queryRelationOptions, setRelationKeyword, setMany2oneOption,
  relationKeyword, quickCreateRelation, relationUiLabel, relationModel, relationIds, upsertRelationOption,
  buildOne2manyCommandValue, one2manyFieldRows, initOne2manyRows, applyOnchangeLinePatches,
  isWritableFieldVisible,
});
const {
  addRelationId, collectWritableValues, commitMany2oneInline, comparableFieldValue, isFieldWritable,
  normalizeFieldValue, queryMany2oneInline, quickCreateMany2manyTag, resolvePendingInlineRelationCreates,
  resolvePendingMany2manyTagCreates, setBooleanField, setMany2oneField, setRelationIds,
  setRelationMultiField, setSelectionField, setTextField,
} = recordFormStateRuntime;

const {
  resolveNavigationUrl, viewOrchestrationHudSummary, hudEntries, loadContract,
  loadRecord, handleSceneBlockAction, reload, ensureFormInitialReload, preloadFormAuxiliaryData,
} = useRecordPageLifecycle({
  ApiError, ContractAccessPolicyError, ContractV2DecodeError,
  ErrorCodes, actionId, advancedExpanded,
  applyIncomingFormFieldValue, applyPageStatusEvent,
  buildRouteContractContext, changedFieldCount,
  changedFieldSet, chatterLoading, clearNativeAttachmentError,
  clearNativeChatterForRecordLoad, clearOne2manyRows, clearPendingNativeAttachments,
  closeNativeChatterComposer, contract, contractAccessPolicy,
  contractActions, contractMeta,
  contractReadiness, coreFieldNames, createContractV2Store,
  decodeContractV2Snapshot, dirtyFieldSet, fieldType,
  formData, formDataFieldNames,
  formRouteIdentity, hydrateSelectedRelationOptions, hydrateVisibleOne2manyRows,
  initOne2manyRows, isComponentActive, layoutNodes,
  loadActionContractV2, loadError, loadModelContractV2,
  loadNativeChatterTimeline, menuId,
  model, nativeAttachments,
  nativeChatterActions, nativeChatterAutoLoadKey, nativeLayoutVisibilityRevision,
  onchangeLinePatches, onchangeModifiersPatch, getOnchangeTimer: () => onchangeTimer,
  setOnchangeTimer: (timer: ReturnType<typeof setTimeout> | null) => { onchangeTimer = timer; }, onchangeWarnings, originalValues,
  pickContractNavQuery, defaultContractFormRecord, readContractFormRecord, recordId,
  recordIdDisplay, recordMissing, recordVersionPolicy,
  recordVersionToken, relationKeywords, relationOptions,
  renderErrorMessage, renderProfile: requestedRenderProfile, requestedSourceMode,
  requestedSurface, resolveContractV2MainData, resolveCreateDefaultsFromState,
  resolveNavigationUrlFromOrigin,
  restoreIntakeAutosave, retainedRouteIdentity, rights,
  route, router, session,
  setStatusbarValue, showHud, showOne2manyErrors,
  snapshotOriginalFormValues, status, toPositiveInt,
  upsertRelationOption, v2ContractDecodeError, v2ContractStore,
  v2ShadowActionCount, v2ShadowButtonStatusCount, v2ShadowFieldCodeCount,
  v2ShadowGlobalSourceKind, v2ShadowLayoutSourceKind, v2ShadowLegacyFieldMissingPreview,
  v2ShadowLegacyFieldOverlapCount, v2ShadowMainDataFieldCount, v2ShadowReadonlyValueCount,
  v2ShadowSourceContextKind, v2ShadowStatusFieldCount, v2ShadowStoreReady,
  v2ShadowValueFieldCount, v2ShadowValueSourceKind, v2ShadowWidgetCount,
  validationErrors, writableFieldCount,
});
const {
  discardChanges, confirmActionSafety, ensureSavedBeforeRecordAction, applyClientMode, applyRouteConfigMode,
  onContractFieldAction, onFormSettingsFieldSelect, selectFormDesignerGroup, selectFormDesignerField, onSelectedFormSettingsGroupTitleChange,
  onSelectedFormSettingsFieldLabelChange, contractInlineFieldOrderIndex, onContractInlineFieldOrderMove, onContractInlineFieldOrderDragStart, onContractInlineFieldOrderDragOver,
  onContractInlineFieldOrderDragLeave, onContractInlineFieldOrderDrop, onContractInlineFieldOrderGroupDrop, onContractInlineFieldOrderDragEnd, lowCodeApplyBaseParams,
  contractFieldSequence, fieldGroupTitleForDraft, routeQueryText, lowCodeReturnQuery, previewLowCodeConfiguredPage,
  previewCurrentFormConfiguration, returnToBusinessConfigDesigner, isTierValidationActionHidden, applyProjectionRefreshPolicy, saveRecord,
} = useRecordFormActions({
  ApiError, BUSINESS_CONFIG_ACTION_KEYS, BUSINESS_CONFIG_MODES,
  BUSINESS_CONFIG_ROUTE_FLAGS, RECORD_CONTEXT_CHANGED_EVENT, actionId,
  activeContractMode, activeContractModeFieldRows, appendFormConfigOperation,
  buildLowCodeApplyBaseParams, buildLowCodePreviewQuery, buildLowCodeReturnQuery,
  buildSaveRecordPayload, busy, busyKind,
  canSave, clearIntakeAutosave, closeContractPromptAction,
  collectSceneValidationPrecheckErrors, collectWritableValues,
  comparableFieldValue, contract, contractActionConfirmationPrompt, contractActionRuleKey,
  contractFieldSequenceFromOrder, contractModeFeedback, contractV2ActionRules,
  createContractFormRecord, currentFormDesignFieldKeys, currentFormOrderedFieldKeys,
  dirtyFieldSet, draggingFieldLabel, effectiveFieldGroupTitleForDraft,
  ensureFormInitialReload, executeProjectionRefresh, fieldGroupTitleMatches,
  fieldOrderDraft, fieldVisibilityBase, fieldVisibilityDirtyKeys,
  fieldVisibilityDraft, focusFirstValidationError, formConfigAuditResult,
  formConflict, formCreateContextFromState, formData, formFields: canonicalFormFields,
  formDesignFieldLabel, formDesignerGroupNavigatorItems, formRouteIdentity,
  formSettingsActiveTab, formUiLabel, handleRecordContextChanged,
  hasChanges, hasCurrentFormFieldDraftChanges, instanceRouteIdentity,
  intentConfirmationRef, isBusinessConfigMode, isBusinessConfigRuntimeModel,
  isComponentActive, isContractFieldOrderEditable, isFormPageRouteOwner,
  isStandardIntakeMode, isTierValidationActionHiddenFromState, isWritableFieldVisible,
  layoutNodes, model, moveFieldOrder,
  navigateCreatedRecord, normalizeFieldGroupTitle, normalizeFieldValue,
  onContractInlineGroupRename, onErrorCaptured, onFieldOrderDragEnd,
  onFieldOrderDragLeave, onFieldOrderDragOver, onFieldOrderDragStart,
  onFieldOrderDrop, onFieldOrderGroupDrop, onFieldOrderWindowDragOver,
  onFieldOrderWindowDragStop, onRelationDialogDocumentKeydown, one2manyValidation,
  originalValues, parseMaybeJsonRecord, policyContext,
  recordId, recordVersionPolicy, recordVersionToken,
  reload, rememberFormConfigFieldLabel, renderErrorMessage,
  resolvePendingInlineRelationCreates, resolvePendingMany2manyTagCreates, retainedRouteIdentity,
  route, router, runContractRuleAction,
  sanitizeUiErrorMessage, saveContractFieldOrder, sceneReadyFormSurface,
  buildFormRequestContext, selectedFormSettingsFieldGroupTitle, selectedFormSettingsFieldGroupTitleDraft,
  selectedFormSettingsFieldGroupTitleEdit, selectedFormSettingsFieldKey, selectedFormSettingsFieldLabel,
  selectedFormSettingsFieldRow, session, setInlineFieldPolicy,
  showOne2manyErrors, status, submissionFeedback,
  uploadPendingNativeAttachments, useFormPageLifecycleRuntime, v2ContractStore,
  validateBeforeSaveRecord, validationErrors,
  writeContractFormRecord,
});
const unsavedFormGuard = useUnsavedFormGuard({
  dirty: () => hasChanges.value,
  busy,
  confirmLeave: async () => intentConfirmationRef.value?.confirm({
    actionLabel: '离开页面',
    message: '当前修改尚未保存。离开后这些修改将丢失，是否继续？',
  }) ?? false,
});
async function returnToPreviousPage() {
  await unsavedFormGuard.navigateAfterConfirm(() => router.back());
}
useFormAuxiliaryWatchersRuntime({
  autosaveSource: () => [
    intakeAutosaveKey.value,
    ...Object.keys(formData).sort().map((key) => comparableFieldValue(key, formData[key])),
  ],
  businessCategoryCode: () => currentBusinessCategoryCode.value,
  businessCategoryLabel: () => currentBusinessCategoryLabel.value,
  chatterLoading: () => chatterLoading.value,
  collaborationReady: () => Boolean(nativeChatterActions.value.length || nativeAttachments.value),
  currentQuery: () => route.query as Record<string, unknown>,
  isActive: () => isComponentActive.value,
  isIntake: () => isIntakeCreateMode.value,
  loadNativeChatterTimeline: () => loadNativeChatterTimeline(),
  modelName: () => model.value,
  nativeChatterAutoLoadKey,
  persistIntakeAutosave: () => persistIntakeAutosave(),
  primaryReady: () => status.value === 'ok',
  recordId: () => recordId.value,
  router,
});
watch(() => route.query.config_mode, (mode) => applyRouteConfigMode(mode), { immediate: true });
</script>

<style scoped src="./contractForm/ContractFormPage.css"></style>

/* eslint-disable @typescript-eslint/no-explicit-any */
import { computed } from 'vue';
import type { FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import type { NativeFormLayoutNode } from '../../components/template/NativeFormTreeRenderer.vue';
import type { ContractAction } from './types';

type PresentationDependencies = Record<string, any>;

/** Owns authoritative action presentation and field interaction adapters. */
export function useRecordActionPresentation(dependencies: PresentationDependencies) {
  const { ErrorCodes, actionId, activeChatterLabel, activeChatterMode, activityAssigneeId, activityDeadline, activityNote, activitySummary, activityUpdatingIds, addOne2manyRow, advancedExpanded, applyPageStatusEvent, applyWorkflowAvailability, attachmentError, attachmentUploading, buildContractFormActions, busy, busyKind, canOpenRelationRecordForm, changedFieldGroupDraft, chatterDraft, chatterError, chatterPosting, chatterTimeline, closeNativeChatterComposer, collaborationUserChoices, collaborationUserOptions, collaborationUserQuery, collaborationUsersLoading, collectContractV2ButtonStatusById, commitMany2oneInline, confirmActionSafety, detectObjectMethodFromActionKey, dispatchTemplateFieldChange, effectiveFieldSize, effectiveGroupVisible, ensureSavedBeforeRecordAction, executeButton, fieldGroupBase, fieldGroupDraft, fieldInputType, fieldMoveTargetDraft, fieldOrderDraft, fieldOrderPreviewActive, fieldVisibilityDraft, filteredRelationOptions, focusProductFormValidationError, formConflict, formData, formLayoutColumnsDraft, inputFieldValue, intentConfirmationRef, isContractFieldOrderEditable, isMissingRequiredValue, isIntakeCreateMode, isQuickIntakeMode, isTierValidationActionHidden, layoutContainsType, loadCollaborationUsers, lowCodeFormLayoutBase, many2oneValue, markFieldChanged, model, nativeFormDesignFieldKeys, nativeFormDesignFieldLabels, nativeLayoutVisibilityRevision, navigateActionResponseResult, normalizeActionKind, normalizeActionSafety, normalizeRequiredParams, normalizeWorkflowActionRows, normalizeWorkflowEvidenceGateRows, onNativeAttachmentSelected, onchangeModifiersPatch, one2manyCanCreate, one2manyColumnDisplayValue, one2manyColumnInputType, one2manyColumns, one2manyCreateLabel, one2manyRowActions, one2manyRowColumnBehavior, one2manyRowErrors, one2manyRowHints, one2manyRowLabel, one2manyRowStateLabel, one2manySummary, openNativeAttachment, openNativeChatterAction, openRelationCreateForm, parseMaybeJsonRecord, pendingNativeAttachments, policyContext, queryMany2oneInline, recordId, relationCreateMode, relationIds, relationInlineCreate, relationKeyword, relationModel, relationOptionsForField, relationUiLabel, reload, rememberFormConfigFieldLabel, removeMentionUser, removeOne2manyRow, removePendingNativeAttachment, removedOne2manyRows, renderProfile, resolveContractFormFieldLabels, resolveInputPlaceholder, resolvePrimaryCreateFooterAction, resolveSelectPlaceholder, resolveWorkflowContractFromSources, restoreOne2manyRow, rights, route, runAction, runtimeRoleCode, selectMentionUser, selectedMentionUsers, selectedRelationOptions, sendNativeChatter, session, setBooleanField, setMany2oneField, setOne2manyRowField, setRelationIds, setRelationKeyword, setRelationMultiField, setSelectionField, setTextField, shouldShowWorkflowAction, showHud, showOne2manyErrors, toDateInputValue, toDatetimeInputValue, toPositiveInt, updateNativeActivity, useRecordCollaborationPresentation, useRecordContractSemantics, useRecordFormFieldSchemas, useRecordFormLayout, v2ContractStore, validationErrors, visibleOne2manyColumns, visibleOne2manyRows } = dependencies;
  const chatterTimelineHasMore = dependencies.chatterTimelineHasMore;
  const chatterTimelineLoading = dependencies.chatterTimelineLoading;
  const loadMoreNativeChatterTimeline = dependencies.loadMoreNativeChatterTimeline;
  function currentWorkflowContract(): Record<string, unknown> {
    return resolveWorkflowContractFromSources(null, v2ContractStore.value?.snapshot);
  }

  function workflowContractActionRows(): Array<Record<string, unknown>> {
    if (!recordId.value) return [];
    return normalizeWorkflowActionRows(currentWorkflowContract(), model.value);
  }

  function blockingWorkflowEvidenceMessage() {
    const row = workflowEvidenceGateRows.value.find((item) => item.blocking);
    return row?.message || '';
  }

  function applyWorkflowContractToAction(action: ContractAction): ContractAction {
    return applyWorkflowAvailability({ action, workflow: currentWorkflowContract(), recordId: recordId.value, blockingMessage: blockingWorkflowEvidenceMessage() });
  }

  function shouldShowWorkflowNativeAction(methodName: string) {
    return shouldShowWorkflowAction(currentWorkflowContract(), recordId.value, methodName);
  }

  const workflowEvidenceGateRows = computed(() => normalizeWorkflowEvidenceGateRows(currentWorkflowContract()));

  const contractActions = computed<ContractAction[]>(() => {
    const storeButtonStatus = collectContractV2ButtonStatusById(v2ContractStore.value);
    return buildContractFormActions({
      model: model.value,
      recordId: recordId.value,
      renderProfile: renderProfile.value,
      v2ButtonStatus: storeButtonStatus,
      v2ActionRuleList: v2ContractStore.value?.snapshot.actionContract.actionRuleList as Array<Record<string, unknown>> | undefined,
      policyContext: policyContext.value,
      evaluateNativeActionVisibility,
      isTierValidationActionHidden,
    });
  });

  const headerActions = computed(() => contractActions.value.filter((item) => item.level === 'header' || item.level === 'toolbar'));
  const bodyActions = computed(() => contractActions.value.filter((item) => item.level !== 'header' && item.level !== 'toolbar'));

  const contractFieldLabels = computed<Record<string, string>>(() => resolveContractFormFieldLabels(null, v2ContractStore.value?.snapshot));

  function contractFieldLabel(name: string) {
    return contractFieldLabels.value[String(name || '').trim()] || '';
  }
  const {
    activeActivityAction,
    nativeAttachmentMaxBytes,
    nativeChatterActions,
    nativeAttachments,
    nativeCollaborationPanelProps,
    nativeCollaborationPanelListeners,
    resolveNativeAttachmentLabel,
  } = useRecordCollaborationPresentation({
    v2ContractStore, recordId, model, renderProfile, busy,
    activeChatterMode, activeChatterLabel, chatterDraft, activitySummary, activityDeadline, activityNote,
    collaborationUserQuery, collaborationUserOptions, collaborationUserChoices, collaborationUsersLoading,
    selectedMentionUsers, activityAssigneeId, chatterPosting, chatterError, chatterTimeline,
    chatterTimelineHasMore, chatterTimelineLoading, activityUpdatingIds,
    attachmentError, attachmentUploading, pendingNativeAttachments, onNativeAttachmentSelected,
    closeNativeChatterComposer, loadCollaborationUsers, openNativeChatterAction, openNativeAttachment,
    removeMentionUser, removePendingNativeAttachment, selectMentionUser, sendNativeChatter, updateNativeActivity,
    loadMoreNativeChatterTimeline,
  });

  const hasNativeChatterNode = computed(() => nativeLayoutContainsType(nativeFormLayoutNodes.value, 'chatter'));

  function nativeLayoutContainsType(nodes: NativeFormLayoutNode[], type: string): boolean {
    return layoutContainsType(nodes as Array<Record<string, unknown>>, type);
  }

  function contractActionFromNativeRow(row: Record<string, unknown>): ContractAction | null {
    const nativeAction = row.action && typeof row.action === 'object' && !Array.isArray(row.action)
      ? row.action as Record<string, unknown>
      : {};
    const payload = parseMaybeJsonRecord(nativeAction.payload || row.payload);
    const rowName = String(nativeAction.name || row.name || payload.method || payload.ref || '').trim();
    const rowLabel = String(nativeAction.label || row.label || '').trim();
    const key = String(nativeAction.key || row.key || rowName || rowLabel || '').trim();
    if (!key) return null;
    const kind = normalizeActionKind(
      nativeAction.kind || row.kind || row.buttonType || payload.type || row.type || (rowName ? 'object' : ''),
    );
    const level = String(nativeAction.level || row.level || 'body').trim().toLowerCase();
    const actionId = toPositiveInt(payload.action_id) ?? toPositiveInt(payload.ref) ?? toPositiveInt(row.action_id) ?? toPositiveInt(row.ref);
    const methodName = detectObjectMethodFromActionKey(
      key,
      String(payload.method || row.method || (kind === 'object' || kind === 'server' ? rowName : '') || '').trim(),
    );
    if (!shouldShowWorkflowNativeAction(methodName)) return null;
    const needRecord = kind === 'object' || kind === 'server' || level === 'row' || level === 'smart';
    return applyWorkflowContractToAction({
      key,
      label: rowLabel || key,
      kind,
      level,
      selection: 'none',
      actionId,
      methodName,
      targetModel: String(row.target_model || row.model || payload.model || model.value || '').trim(),
      context: parseMaybeJsonRecord(payload.context_raw || row.context),
      domainRaw: String(payload.domain_raw || row.domain_raw || '').trim(),
      target: String(payload.target || row.target || '').trim(),
      url: String(payload.url || row.url || '').trim(),
      enabled: !needRecord || Boolean(recordId.value),
      hint: needRecord && !recordId.value ? 'requires record id' : '',
      intent: String(nativeAction.intent || row.intent || '').trim(),
      semantic: '',
      sourceWidgetId: String(row.sourceWidgetId || row.source_widget_id || '').trim(),
      clientMode: '',
      visibleProfiles: ['create', 'edit', 'readonly'],
      requiredParams: normalizeRequiredParams(nativeAction.required_params || row.required_params),
      requiresReason: nativeAction.requires_reason === true || row.requires_reason === true,
      actionSafety: normalizeActionSafety(nativeAction.action_safety || row.action_safety),
    });
  }

  function resolveNativeActionState(row: Record<string, unknown>) {
    const action = contractActionFromNativeRow(row);
    if (!action) return {};
    return {
      disabled: busy.value || !action.enabled,
      title: action.hint || '',
    };
  }

  function isUnifiedSubmitMethod(methodName: string) {
    const method = String(methodName || '').trim();
    return method === 'action_submit'
      || method === 'action_submit_progress'
      || method === 'action_confirm'
      || method === 'button_confirm';
  }

  function isUnifiedSubmitAction(action: ContractAction | null | undefined) {
    return Boolean(action && isUnifiedSubmitMethod(action.methodName));
  }

  const primarySubmitAction = computed<ContractAction | null>(() => {
    if (isIntakeCreateMode.value) return null;
    if (!model.value) return null;
    if (!recordId.value) return null;
    const runtime = parseMaybeJsonRecord(v2ContractStore.value?.snapshot.runtimeContract);
    if (String(runtime.interactionMode || '').trim() === 'wizard') {
      const wizardAction = contractActions.value.find((action) => (
        action.level === 'footer'
        && action.presentationTier === 'primary'
        && action.enabled
      ));
      if (wizardAction) return wizardAction;
    }
    const visibleAction = headerActions.value.find((action) => isUnifiedSubmitAction(action));
    return visibleAction || null;
  });

  const primaryCreateFooterAction = computed<ContractAction | null>(() => {
    if (isIntakeCreateMode.value) return null;
    if (!model.value || recordId.value) return null;
    if (primarySubmitAction.value) return null;
    return resolvePrimaryCreateFooterAction({
      actions: contractActions.value,
    });
  });

  async function runNativeLayoutAction(row: Record<string, unknown>) {
    const action = contractActionFromNativeRow(row);
    if (!action) return;
    if ((action.kind === 'object' || action.kind === 'server') && action.methodName && recordId.value) {
      if (!action.enabled || !await confirmActionSafety(action)) return;
      if (!await ensureSavedBeforeRecordAction()) return;
      busyKind.value = 'action';
      try {
        const response = await executeButton({
          model: action.targetModel || model.value,
          res_id: recordId.value,
          button: { name: action.methodName, type: action.kind === 'server' ? 'server' : 'object' },
          context: action.context,
          meta: {
            menu_id: Number(route.query.menu_id || 0) || undefined,
            action_id: actionId.value || undefined,
          },
        });
        const result = response?.result;
        if (await navigateActionResponseResult(result)) {
          return;
        }
        await reload();
        return;
      } catch (err) {
        applyPageStatusEvent({ kind: 'status', transaction: 'runAction', status: 'error', errorMessage: err instanceof Error ? err.message : '操作执行失败' });
        return;
      } finally {
        busyKind.value = null;
      }
    }
    await runAction(action);
  }

  const {
    advancedFieldNames, contractVisibleFields, coreFieldNames, fieldSemanticMeta, focusFirstValidationError,
    focusValidationError, hasAdvancedFields, nonSceneValidationErrors, policyRequiredFields, reloadLatestRecord, sceneReadyFormSurface,
    sceneValidationPanel, sceneValidationRequiredFields, strictContractDefaultsSummary, strictContractGuard,
    strictContractMissingSummary, strictContractMode, useSceneFormAugmentations, validationRequiredFields,
  } = useRecordContractSemantics({
    v2ContractStore, route, session, actionId, recordId, model, renderProfile, runtimeRoleCode,
    validationErrors, isIntakeCreateMode, intentConfirmationRef, formConflict,
    layoutNodes: () => layoutNodes.value,
    reload: () => reload(),
    focusValidationError: focusProductFormValidationError,
  });

  const {
    baseNativeFormLayoutNodes, currentNativeFieldOrder, ensureFieldOrderDraftStartsFromCurrentLayout,
    evaluateNativeActionVisibility, evaluateNativeModifierValue, fieldModifierMap, formDataFieldNames, isFieldVisible,
    isNativeFavoriteField, isNativeFieldVisible, isNativeLayoutNodeVisible, isNativeOccurrenceEditable, isWritableFieldVisible, nativeFieldAccess,
    nativeFormLayoutNodes, nativeFormRootColumns, nativeGroupCount, nativeNotebookPageCount, nativeStatusbar,
    nativeVisibleFieldNames, nativeVisibleSectionTitles, rawNativeFormLayoutNodes, resolveNativeButtonLabel,
    runtimeFieldStates, runtimeNativeFormLayoutNodes, runtimeOccurrenceState, runtimeState, setStatusbarValue, showNativeDefaultSectionTitle, useNativeFormTree,
  } = useRecordFormLayout({
    v2ContractStore, contractVisibleFields, onchangeModifiersPatch, formData,
    isQuickIntakeMode, contractFieldLabel, fieldSemanticMeta, showHud, advancedExpanded,
    coreFieldNames, advancedFieldNames, renderProfile, recordId, isContractFieldOrderEditable,
    fieldOrderDraft, fieldOrderPreviewActive, changedFieldGroupDraft, fieldMoveTargetDraft,
    fieldGroupBase, fieldGroupDraft, effectiveGroupVisible, lowCodeFormLayoutBase,
    nativeLayoutVisibilityRevision, nativeFormDesignFieldKeys, nativeFormDesignFieldLabels,
    formLayoutColumnsDraft, fieldVisibilityDraft, contractActionFromNativeRow, policyContext, rights,
    markFieldChanged, layoutNodes: () => layoutNodes.value,
  });

  const { layoutNodes, nativeFieldSchemasForNodes } = useRecordFormFieldSchemas({
    v2ContractStore, nativeFormLayoutNodes, isNativeFieldVisible, isNativeLayoutNodeVisible,
    runtimeState, runtimeOccurrenceState, recordId, rights, contractFieldLabel, isContractFieldOrderEditable, effectiveFieldSize,
    rememberFormConfigFieldLabel, fieldOrderPreviewActive, fieldOrderDraft, formData, isFieldVisible,
    contractVisibleFields, coreFieldNames, advancedFieldNames, evaluatePolicyContext: policyContext,
    runtimeFieldStates, validationErrors,
    relationOptionsForField, relationCreateMode, relationInlineCreate, relationKeyword,
    canOpenRelationRecordForm, relationUiLabel, inputFieldValue, many2oneValue,
    toDateInputValue, toDatetimeInputValue,
    evaluateNativeModifierValue,
  });

  function onTemplateFieldChange(payload: FormSectionFieldChange) {
    if (useNativeFormTree.value && !isNativeOccurrenceEditable(String(payload.occurrenceKey || ''))) return;
    if (String(payload.type || '').trim().toLowerCase() === 'many2one' && payload.action === 'query') {
      queryMany2oneInline(payload.name, payload.descriptor, String(payload.value ?? ''));
      return;
    }
    if (String(payload.type || '').trim().toLowerCase() === 'many2one' && payload.action === 'commit') {
      void commitMany2oneInline(payload.name, payload.descriptor, String(payload.value ?? ''));
      return;
    }
    dispatchTemplateFieldChange(payload, {
      onBoolean: (name, value) => setBooleanField(name, value),
      onSelection: (name, value) => setSelectionField(name, value),
      onMany2one: (name, descriptor, value) => setMany2oneField(name, descriptor, value),
      onText: (name, value) => setTextField(name, value),
    });
    const filenameField = String(payload.descriptor?.filename || '').trim();
    if (String(payload.type || '').trim().toLowerCase() === 'binary' && filenameField && payload.fileName) {
      setTextField(filenameField, payload.fileName);
    }
  }

  async function runOne2manyRowAction(
    fieldName: string,
    row: { id?: number | null; isNew?: boolean; removed?: boolean; dirty?: boolean },
    action: { enabled?: boolean; kind?: string; methodName?: string },
  ) {
    const childId = Number(row.id || 0);
    const childModel = String(relationModel(fieldName) || '').trim();
    const methodName = String(action.methodName || '').trim();
    if (
      !action.enabled
      || action.kind !== 'object'
      || !childModel
      || !Number.isInteger(childId)
      || childId <= 0
      || !methodName
      || row.isNew
      || row.removed
      || busy.value
    ) return;
    if (!await ensureSavedBeforeRecordAction()) return;
    busyKind.value = 'action';
    try {
      const response = await executeButton({
        model: childModel,
        res_id: childId,
        button: { name: methodName, type: 'object' },
        context: {},
        meta: {
          menu_id: Number(route.query.menu_id || 0) || undefined,
          action_id: actionId.value || undefined,
        },
      });
      if (!await navigateActionResponseResult(response?.result)) await reload();
    } catch (err) {
      applyPageStatusEvent({
        kind: 'status',
        transaction: 'runAction',
        status: 'error',
        errorMessage: err instanceof Error ? err.message : '子记录操作执行失败',
      });
    } finally {
      busyKind.value = null;
    }
  }

  const strictFieldDescriptor=(fieldName:string)=>{const widgets=v2ContractStore.value?.widgetsByFieldCodeAll.get(String(fieldName||'').trim())||[];return widgets.find((widget)=>widget.fieldDescriptor)?.fieldDescriptor as any;};
  const relationFieldAdapter = computed<RelationFieldAdapter>(() => ({
    busy: busy.value,
    showOne2manyErrors: showOne2manyErrors.value,
    relationKeyword,
    setRelationKeyword,
    relationIds,
    selectedRelationOptions,
    filteredRelationOptions,
    setRelationMultiField,
    setRelationIds,
    relationCreateMode: (fieldName: string) => relationCreateMode(strictFieldDescriptor(fieldName)),
    relationCreateLabel: (fieldName: string) => {
      const descriptor = strictFieldDescriptor(fieldName);
      const mode = relationCreateMode(descriptor);
      if (mode === 'page') return relationUiLabel(descriptor, 'create_and_edit');
      if (mode === 'quick') return relationUiLabel(descriptor, 'quick_create');
      return '';
    },
    relationInlineCreateLabel: (fieldName: string) => {
      const descriptor = strictFieldDescriptor(fieldName);
      const template = relationUiLabel(descriptor, 'inline_create');
      const label = relationKeyword(fieldName).trim();
      return template.includes('%s') ? template.replace('%s', label) : template || label;
    },
    canInlineCreateRelation: (fieldName: string) => {
      const descriptor = strictFieldDescriptor(fieldName);
      const inline = relationInlineCreate(descriptor);
      const keyword = relationKeyword(fieldName).trim();
      if (!keyword || !inline.enabled || !inline.createOnNoMatch) return false;
      return !relationOptionsForField(fieldName).some((option) => option.label.trim().toLowerCase() === keyword.toLowerCase());
    },
    openRelationCreate: (fieldName: string) => {
      const descriptor = strictFieldDescriptor(fieldName);
      if (!descriptor) return;
      void openRelationCreateForm(fieldName, descriptor);
    },
    one2manyCanCreate,
    one2manyCreateLabel,
    addOne2manyRow,
    one2manySummary,
    visibleOne2manyRows,
    one2manyRowStateLabel,
    one2manyColumns,
    visibleOne2manyColumns,
    one2manyRowColumnBehavior,
    one2manyRowActions,
    runOne2manyRowAction: (fieldName, row, action) => { void runOne2manyRowAction(fieldName, row, action); },
    setOne2manyRowField,
    removeOne2manyRow,
    one2manyRowErrors,
    one2manyRowHints,
    removedOne2manyRows,
    restoreOne2manyRow,
    one2manyRowLabel,
    selectPlaceholder: resolveSelectPlaceholder,
    one2manyColumnInputType,
    one2manyColumnDisplayValue,
    inputFieldValue,
    fieldInputType,
    inputPlaceholder: resolveInputPlaceholder,
    setTextField,
  }));


  return {
    currentWorkflowContract,
    workflowContractActionRows,
    blockingWorkflowEvidenceMessage,
    applyWorkflowContractToAction,
    shouldShowWorkflowNativeAction,
    workflowEvidenceGateRows,
    contractActions,
    headerActions,
    bodyActions,
    contractFieldLabels,
    contractFieldLabel,
    activeActivityAction,
    nativeAttachmentMaxBytes,
    nativeChatterActions,
    nativeAttachments,
    nativeCollaborationPanelProps,
    nativeCollaborationPanelListeners,
    resolveNativeAttachmentLabel,
    hasNativeChatterNode,
    nativeLayoutContainsType,
    contractActionFromNativeRow,
    resolveNativeActionState,
    isUnifiedSubmitMethod,
    isUnifiedSubmitAction,
    primarySubmitAction,
    primaryCreateFooterAction,
    runNativeLayoutAction,
    advancedFieldNames,
    contractVisibleFields,
    coreFieldNames,
    fieldSemanticMeta,
    focusFirstValidationError,
    focusValidationError,
    hasAdvancedFields,
    nonSceneValidationErrors,
    policyRequiredFields,
    reloadLatestRecord,
    sceneReadyFormSurface,
    sceneValidationPanel,
    sceneValidationRequiredFields,
    strictContractDefaultsSummary,
    strictContractGuard,
    strictContractMissingSummary,
    strictContractMode,
    useSceneFormAugmentations,
    validationRequiredFields,
    baseNativeFormLayoutNodes,
    currentNativeFieldOrder,
    ensureFieldOrderDraftStartsFromCurrentLayout,
    evaluateNativeActionVisibility,
    evaluateNativeModifierValue,
    fieldModifierMap,
    formDataFieldNames,
    isFieldVisible,
    isNativeFavoriteField,
    isNativeFieldVisible,
    isNativeLayoutNodeVisible,
    isWritableFieldVisible,
    nativeFieldAccess,
    nativeFormLayoutNodes,
    nativeFormRootColumns,
    nativeGroupCount,
    nativeNotebookPageCount,
    nativeStatusbar,
    nativeVisibleFieldNames,
    nativeVisibleSectionTitles,
    rawNativeFormLayoutNodes,
    resolveNativeButtonLabel,
    runtimeFieldStates,
    runtimeNativeFormLayoutNodes,
    runtimeState,
    setStatusbarValue,
    showNativeDefaultSectionTitle,
    useNativeFormTree,
    layoutNodes,
    nativeFieldSchemasForNodes,
    onTemplateFieldChange,
    relationFieldAdapter,
  };
}

/* eslint-disable @typescript-eslint/no-explicit-any */
import { computed } from 'vue';
import { resolveContractV2FormFieldMap } from '../../app/contracts/v2';
import { routeAuthorityEntries } from '../../app/routeAuthority';
import type { FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter, RelationFieldColumn } from '../../components/template/relationField.types';
import type { NativeFormLayoutNode } from '../../components/template/NativeFormTreeRenderer.vue';
import type { ContractAction } from './types';
import { resolveAuthorizedWindowActionTarget, resolveContractActionForNativeOccurrence } from './contractActionPresentation';

type PresentationDependencies = Record<string, any>;

/** Owns authoritative action presentation and field interaction adapters. */
export function useRecordActionPresentation(dependencies: PresentationDependencies) {
  const { ErrorCodes, actionId, activeChatterLabel, activeChatterMode, activityAssigneeId, activityDeadline, activityNote, activitySummary, activityUpdatingIds, addOne2manyRow, advancedExpanded, applyPageStatusEvent, attachmentError, attachmentUploading, buildContractFormActions, busy, busyKind, canOpenRelationRecordForm, changedFieldGroupDraft, chatterDraft, chatterError, chatterPosting, chatterTimeline, closeNativeChatterComposer, collaborationUserChoices, collaborationUserOptions, collaborationUserQuery, collaborationUsersLoading, collectContractV2ButtonStatusById, collectSceneValidationPrecheckErrorsFromRules, commitMany2oneInline, confirmActionSafety, contract, dispatchTemplateFieldChange, effectiveFieldSize, effectiveGroupVisible, ensureSavedBeforeRecordAction, executeButton, fieldGroupBase, fieldGroupDraft, fieldInputType, fieldMoveTargetDraft, fieldOrderDraft, fieldOrderPreviewActive, fieldVisibilityDraft, filteredRelationOptions, focusProductFormValidationError, formConflict, formData, formLayoutColumnsDraft, inputFieldValue, intentConfirmationRef, isContractFieldOrderEditable, isMissingRequiredValue, isIntakeCreateMode, isQuickIntakeMode, isOne2manyHydrating, layoutContainsType, loadCollaborationUsers, lowCodeFormLayoutBase, many2oneValue, markFieldChanged, model, nativeFormDesignFieldKeys, nativeFormDesignFieldLabels, nativeLayoutVisibilityRevision, navigateActionResponseResult, normalizeWorkflowEvidenceGateRows, onNativeAttachmentSelected, onchangeModifiersPatch, one2manyCanCreate, one2manyCanInlineEdit, one2manyCanUnlink, one2manyColumnDisplayValue, one2manyColumnInputType, one2manyColumns, one2manyCreateLabel, one2manyRowErrors, one2manyRowHints, one2manyRowLabel, one2manyRowStateLabel, one2manySummary, openNativeAttachment, openNativeChatterAction, openRelationCreateForm, pendingNativeAttachments, policyContext, queryMany2oneInline, recordId, relationCreateMode, relationIds, relationInlineCreate, relationKeyword, relationOptionsForField, relationUiLabel, reload, rememberFormConfigFieldLabel, removeMentionUser, removeOne2manyRow, removePendingNativeAttachment, removedOne2manyRows, renderProfile, resolveContractFormFieldLabels, resolveContractV2ActionRules, resolveContractV2RuntimeContract, resolveInputPlaceholder, resolvePrimaryCreateFooterAction, resolveSelectPlaceholder, resolveWorkflowContractFromStore, restoreOne2manyRow, rights, route, runAction, runtimeRoleCode, selectMentionUser, selectedMentionUsers, selectedRelationOptions, sendNativeChatter, session, setBooleanField, setMany2oneField, setOne2manyRowField, createContractFormRecord, setRelationIds, setRelationKeyword, setRelationMultiField, setSelectionField, setTextField, showHud, showOne2manyErrors, toDateInputValue, toDatetimeInputValue, updateNativeActivity, useRecordCollaborationPresentation, useRecordContractSemantics, useRecordFormFieldSchemas, useRecordFormLayout, v2ContractStore, validationErrors, visibleOne2manyRows } = dependencies;
  const chatterTimelineHasMore = dependencies.chatterTimelineHasMore;
  const chatterTimelineLoading = dependencies.chatterTimelineLoading;
  const loadMoreNativeChatterTimeline = dependencies.loadMoreNativeChatterTimeline;
  const setTechnicalCompanionTextField = dependencies.setTechnicalCompanionTextField;
  const formFields = computed(() => resolveContractV2FormFieldMap(v2ContractStore.value));

  // Workflow evidence is display-only. Executable availability is already
  // joined into Contract V2 action authority and must not be recomputed here.
  const workflowEvidenceGateRows = computed(() => normalizeWorkflowEvidenceGateRows(
    resolveWorkflowContractFromStore(v2ContractStore.value),
  ));

  const contractActions = computed<ContractAction[]>(() => {
    const sceneReadyActions = useSceneFormAugmentations.value && Array.isArray(sceneReadyFormSurface.value.actions)
      ? sceneReadyFormSurface.value.actions as Array<Record<string, unknown>>
      : [];
    const v2ButtonStatus = collectContractV2ButtonStatusById(v2ContractStore.value);
    return buildContractFormActions({
      model: model.value,
      recordId: recordId.value,
      renderProfile: renderProfile.value,
      sceneReadyActions,
      v2ButtonStatus,
      v2ActionRuleList: resolveContractV2ActionRules(v2ContractStore.value) as Array<Record<string, unknown>>,
      resolveActionReference: (requested) => resolveAuthorizedWindowActionTarget(
        routeAuthorityEntries(session.routeAuthority),
        requested,
        {
          query: route.query as Record<string, unknown>,
          companyId: Number(session.recordContext?.company_id || session.recordContext?.selected?.company_id || 0) || null,
          selectedRecordId: Number(session.recordContext?.selected?.id || 0) || null,
        },
      ),
    });
  });

  const headerActions = computed(() => contractActions.value.filter((item) => item.level === 'header' || item.level === 'toolbar'));
  const bodyActions = computed(() => contractActions.value.filter((item) => item.level !== 'header' && item.level !== 'toolbar'));

  const contractFieldLabels = computed<Record<string, string>>(() => resolveContractFormFieldLabels(contract.value, v2ContractStore.value?.snapshot));

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
    return resolveContractActionForNativeOccurrence(contractActions.value, row);
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
    const runtime = resolveContractV2RuntimeContract(v2ContractStore.value);
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
    if ((action.kind === 'object' || action.kind === 'action' || action.kind === 'server') && action.methodName && recordId.value) {
      if (!action.enabled || !await confirmActionSafety(action)) return;
      if (!await ensureSavedBeforeRecordAction()) return;
      busyKind.value = 'action';
      try {
        const response = await executeButton({
          model: action.targetModel || model.value,
          res_id: recordId.value,
          button: {
            name: action.methodName,
            type: action.kind === 'server' ? 'server' : action.kind === 'action' ? 'action' : 'object',
            action_id: String(action.authorityActionId || '').trim(),
            backend_identity: String(action.backendIdentity || '').trim(),
            source_widget_id: String(action.sourceWidgetId || '').trim(),
            server_action_id: action.serverActionId || undefined,
            xml_id: action.serverActionXmlId || undefined,
          },
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
    contract, v2ContractStore, route, session, actionId, recordId, model, renderProfile, runtimeRoleCode,
    validationErrors, isIntakeCreateMode, intentConfirmationRef, formConflict,
    layoutNodes: () => layoutNodes.value,
    reload: () => reload(),
    focusValidationError: focusProductFormValidationError,
  });

  const {
    baseNativeFormLayoutNodes, currentNativeFieldOrder, ensureFieldOrderDraftStartsFromCurrentLayout,
    evaluateNativeActionVisibility, evaluateNativeModifierValue, fieldModifierMap, formDataFieldNames, isFieldVisible,
    isNativeFavoriteField, isNativeFieldVisible, isNativeLayoutNodeVisible, isWritableFieldVisible,
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
    contract, v2ContractStore, nativeFormLayoutNodes, isNativeFieldVisible, isNativeLayoutNodeVisible,
    runtimeState, recordId, rights, contractFieldLabel, isContractFieldOrderEditable, effectiveFieldSize,
    rememberFormConfigFieldLabel, fieldOrderPreviewActive, fieldOrderDraft, formData, isFieldVisible,
    contractVisibleFields, coreFieldNames, advancedFieldNames, evaluatePolicyContext: policyContext,
    runtimeFieldStates, validationErrors,
    relationOptionsForField, relationCreateMode, relationInlineCreate, relationKeyword,
    canOpenRelationRecordForm, relationUiLabel, inputFieldValue, many2oneValue,
    toDateInputValue, toDatetimeInputValue, evaluateNativeModifierValue, runtimeOccurrenceState,
  });

  function collectSceneValidationPrecheckErrors(fieldLabels: Record<string, string>): string[] {
    return collectSceneValidationPrecheckErrorsFromRules({
      requiredFields: sceneValidationRequiredFields.value,
      fieldLabels,
      isFieldVisible,
      fieldValue: (field) => formData[field],
      isMissingValue: isMissingRequiredValue,
      errorCode: ErrorCodes.SCENE_VALIDATION_REQUIRED,
    });
  }

  function onTemplateFieldChange(payload: FormSectionFieldChange) {
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
      setTechnicalCompanionTextField(filenameField, payload.fileName);
    }
  }

  const relationFieldAdapter = computed<RelationFieldAdapter>(() => ({
    busy: busy.value,
    showOne2manyErrors: showOne2manyErrors.value,
    currentModel: model.value,
    currentRecordId: recordId.value,
    relationModelOf: (fieldName: string) => {
      const descriptor = formFields.value[fieldName]?.descriptor;
      return String((descriptor as { relation?: string } | undefined)?.relation || '');
    },
    relationKeyword,
    setRelationKeyword,
    relationIds,
    selectedRelationOptions,
    filteredRelationOptions,
    setRelationMultiField,
    setRelationIds,
    relationCreateMode: (fieldName: string) => relationCreateMode(formFields.value[fieldName]),
    relationInlineCreate: (fieldName: string) => relationInlineCreate(formFields.value[fieldName]),
    relationCreateLabel: (fieldName: string) => {
      const descriptor = formFields.value[fieldName];
      const mode = relationCreateMode(descriptor);
      if (mode === 'page' || mode === 'dialog') return relationUiLabel(descriptor, 'create_and_edit');
      if (mode === 'quick') return relationUiLabel(descriptor, 'quick_create');
      return '';
    },
    relationInlineCreateLabel: (fieldName: string) => {
      const descriptor = formFields.value[fieldName];
      const template = relationUiLabel(descriptor, 'inline_create');
      const label = relationKeyword(fieldName).trim();
      return template.includes('%s') ? template.replace('%s', label) : template || label;
    },
    canOpenRelationRecord: (fieldName: string) => canOpenRelationRecordForm(fieldName, formFields.value[fieldName]),
    relationOpenLabel: (fieldName: string) => relationUiLabel(formFields.value[fieldName], 'open_existing', '维护当前项'),
    relationSearchLabel: (fieldName: string) => relationUiLabel(formFields.value[fieldName], 'search_more'),
    canInlineCreateRelation: (fieldName: string) => {
      const descriptor = formFields.value[fieldName];
      const inline = relationInlineCreate(descriptor);
      const keyword = relationKeyword(fieldName).trim();
      if (!keyword || !inline.enabled || !inline.createOnNoMatch) return false;
      return !relationOptionsForField(fieldName).some((option) => option.label.trim().toLowerCase() === keyword.toLowerCase());
    },
    openRelationCreate: (fieldName: string) => {
      const descriptor = formFields.value[fieldName];
      if (!descriptor) return;
      void openRelationCreateForm(fieldName, descriptor);
    },
    // 级联维护：many2many 按当前关键词快速创建字典记录并勾选关联。
    quickCreateRelationMany: async (fieldName: string) => {
      const descriptor = formFields.value[fieldName];
      if (!descriptor) return;
      const keyword = relationKeyword(fieldName).trim();
      if (!keyword) return;
      const entry = dependencies.relationEntry(descriptor);
      const inline = relationInlineCreate(descriptor);
      const relation = String((descriptor as Record<string, unknown> | undefined)?.relation || '').trim();
      if (entry?.canCreate !== true || !inline.enabled || !inline.createOnNoMatch || !relation) return;
      try {
        const existing = relationOptionsForField(fieldName);
        if (existing.some((item) => String(item.label).trim().toLowerCase() === keyword.toLowerCase())) {
          setRelationKeyword(fieldName, '');
          return;
        }
        const nameField = inline.nameField || 'name';
        const created = await createContractFormRecord({
          model: relation,
          vals: { ...(entry.defaultVals || {}), [nameField]: keyword },
        });
        const id = Number(created?.id || 0);
        if (Number.isFinite(id) && id > 0) {
          const current = relationIds(fieldName) || [];
          setRelationIds(fieldName, Array.from(new Set([...current, Math.trunc(id)])));
          setRelationKeyword(fieldName, '');
          markFieldChanged(fieldName);
        }
      } catch (err) {
        validationErrors.value = [
          err instanceof Error ? err.message : relationUiLabel(descriptor, 'quick_create_failed'),
        ];
      }
    },
    one2manyCanCreate,
    one2manyCanInlineEdit,
    one2manyCanUnlink,
    one2manyCanOpenRow: (fieldName: string, row: RelationFieldRow) => {
      const recordId = dependencies.one2manyRowRecordId(row);
      return recordId > 0 && dependencies.canOpenRelationRecord(
        fieldName,
        recordId,
        dependencies.effectiveFieldDescriptor(fieldName),
      );
    },
    openOne2manyRow: (fieldName: string, row: RelationFieldRow) => {
      const recordId = dependencies.one2manyRowRecordId(row);
      if (recordId <= 0 || !dependencies.canOpenRelationRecord(
        fieldName,
        recordId,
        dependencies.effectiveFieldDescriptor(fieldName),
      )) return;
      void dependencies.openRelationRecord(
        fieldName,
        recordId,
        dependencies.effectiveFieldDescriptor(fieldName),
      );
    },
    one2manyCreateLabel,
    addOne2manyRow: (fieldName: string) => {
      if (!one2manyCanCreate(fieldName)) return;
      addOne2manyRow(fieldName);
    },
    one2manySummary,
    isOne2manyHydrating,
    visibleOne2manyRows,
    one2manyRowStateLabel,
    one2manyColumns,
    setOne2manyRowField: (fieldName: string, rowKey: string, column: RelationFieldColumn, value: unknown) => {
      if (!one2manyCanInlineEdit(fieldName)) return;
      setOne2manyRowField(fieldName, rowKey, column, value);
    },
    removeOne2manyRow: (fieldName: string, rowKey: string) => {
      if (!one2manyCanUnlink(fieldName)) return;
      removeOne2manyRow(fieldName, rowKey);
    },
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
    collectSceneValidationPrecheckErrors,
    onTemplateFieldChange,
    relationFieldAdapter,
  };
}

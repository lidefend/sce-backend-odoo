/* eslint-disable @typescript-eslint/no-explicit-any */
import { ref, watch } from 'vue';
import type {
  FormSectionFieldActionPayload,
  FormSectionFieldSchema,
} from '../../components/template/formSection.types';
import type { ContractAction, LayoutNode } from './types';
import {
  decodeServerFieldErrors,
  indexBusinessFieldErrors,
} from '../../app/businessValidationError';
import {
  buildRequiredFieldErrorPayload,
  canonicalizeSubmissionValues,
  createSingleFlightSave,
} from './saveRecordHelpers';
import { resolveStandardFormComposition } from '../../app/presentation/standardFormComposition';

type ActionDependencies = Record<string, any>;

/** Owns save, conflict recovery, form configuration, and projection refresh actions. */
export function useRecordFormActions(dependencies: ActionDependencies) {
  const {
    ApiError,
    BUSINESS_CONFIG_ACTION_KEYS,
    BUSINESS_CONFIG_MODES,
    BUSINESS_CONFIG_ROUTE_FLAGS,
    RECORD_CONTEXT_CHANGED_EVENT,
    actionId,
    activeContractMode,
    activeContractModeFieldRows,
    appendFormConfigOperation,
    buildFormRequestContext,
    buildLowCodeApplyBaseParams,
    buildLowCodePreviewQuery,
    buildLowCodeReturnQuery,
    buildSaveRecordPayload,
    busy,
    busyKind,
    canSave,
    clearIntakeAutosave,
    closeContractPromptAction,
    collectSceneValidationPrecheckErrors,
    collectWritableValues,
    comparableFieldValue,
    contract,
    contractActionRuleKey,
    contractActionConfirmationPrompt,
    contractFieldSequenceFromOrder,
    contractModeFeedback,
    contractV2ActionRules,
    createContractFormRecord,
    currentFormDesignFieldKeys,
    currentFormOrderedFieldKeys,
    dirtyFieldSet,
    draggingFieldLabel,
    effectiveFieldGroupTitleForDraft,
    ensureFormInitialReload,
    executeProjectionRefresh,
    fieldGroupTitleMatches,
    fieldOrderDraft,
    fieldVisibilityBase,
    fieldVisibilityDirtyKeys,
    fieldVisibilityDraft,
    focusFirstValidationError,
    formConfigAuditResult,
    formConflict,
    formCreateContextFromState,
    formData,
    formFields,
    formDesignFieldLabel,
    formDesignerGroupNavigatorItems,
    formRouteIdentity,
    formRouteOwnerIdentity,
    formSettingsActiveTab,
    formUiLabel,
    handleRecordContextChanged,
    hasChanges,
    hasCurrentFormFieldDraftChanges,
    instanceRouteIdentity,
    intentConfirmationRef,
    isBusinessConfigMode,
    isBusinessConfigRuntimeModel,
    isComponentActive,
    isContractFieldOrderEditable,
    isFormPageRouteOwner,
    isWritableFieldVisible,
    layoutNodes,
    model,
    moveFieldOrder,
    navigateCreatedRecord,
    normalizeFieldGroupTitle,
    normalizeFieldValue,
    onContractInlineGroupRename,
    onErrorCaptured,
    onFieldOrderDragEnd,
    onFieldOrderDragLeave,
    onFieldOrderDragOver,
    onFieldOrderDragStart,
    onFieldOrderDrop,
    onFieldOrderGroupDrop,
    onFieldOrderWindowDragOver,
    onFieldOrderWindowDragStop,
    onRelationDialogDocumentKeydown,
    one2manyValidation,
    originalValues,
    parseMaybeJsonRecord,
    recordId,
    recordVersionPolicy,
    recordVersionToken,
    reload,
    rememberFormConfigFieldLabel,
    renderErrorMessage,
    resolvePendingInlineRelationCreates,
    resolvePendingMany2manyTagCreates,
    retainedRouteIdentity,
    route,
    routeQueryText,
    router,
    runContractRuleAction,
    sanitizeUiErrorMessage,
    saveContractFieldOrder,
    sceneReadyFormSurface,
    snapshotOriginalFormValues,
    selectedFormSettingsFieldGroupTitle,
    selectedFormSettingsFieldGroupTitleDraft,
    selectedFormSettingsFieldGroupTitleEdit,
    selectedFormSettingsFieldKey,
    selectedFormSettingsFieldLabel,
    selectedFormSettingsFieldRow,
    session,
    setInlineFieldPolicy,
    showOne2manyErrors,
    status,
    submissionFeedback,
    uploadPendingNativeAttachments,
    useFormPageLifecycleRuntime,
    v2ContractStore,
    validateAdoptedFormSections,
    validateBeforeSaveRecord,
    validationErrors,
    validationFieldErrors,
    writeContractFormRecord,
  } = dependencies;

  // ---------------------------------------------------------------------------
  // Save-operation ownership across awaits
  // ---------------------------------------------------------------------------
  // An adopted save awaits the official engine, and may await relation creates
  // and the write itself. The record the page is bound to can move during any
  // of those waits - including back to a record it showed before - so "same
  // model, same record id" is not an identity: the id comes back but the draft
  // session does not. This epoch advances on every change to the bound surface,
  // and every save takes an operation id, so a resumed operation can prove it
  // still owns the surface before it writes an error, moves focus, sends a
  // write, paints feedback, or clears the busy flag.
  const boundSurfaceKey = () => `${String(model.value ?? '')}\u0000${recordId.value ?? 'new'}`;
  const surfaceEpoch = ref(0);
  let observedSurfaceKey = boundSurfaceKey();
  watch(boundSurfaceKey, (next) => {
    if (next === observedSurfaceKey) return;
    observedSurfaceKey = next;
    surfaceEpoch.value += 1;
  }, { flush: 'sync' });

  type SaveOperation = { id: number; epoch: number; model: string; recordId: number | null };
  let saveOperationSequence = 0;
  let activeSaveOperation: SaveOperation = { id: 0, epoch: -1, model: '', recordId: null };
  let busyOwnerOperationId = 0;

  const beginSaveOperation = (): SaveOperation => {
    saveOperationSequence += 1;
    activeSaveOperation = {
      id: saveOperationSequence,
      epoch: surfaceEpoch.value,
      model: String(model.value ?? ''),
      recordId: recordId.value ?? null,
    };
    return activeSaveOperation;
  };

  const saveOperationOwnsSurface = (operation: SaveOperation) =>
    activeSaveOperation.id === operation.id
    && surfaceEpoch.value === operation.epoch
    && String(model.value ?? '') === operation.model
    && (recordId.value ?? null) === operation.recordId;

  async function discardChanges() {
    if (!hasChanges.value || busy.value) return;
    await reload();
  }
  onErrorCaptured((err) => {
    const message = err instanceof Error ? err.message : String(err || '系统处理问题');
    renderErrorMessage.value = `表单页面打开失败：${message}`;
    return false;
  });
  async function confirmActionSafety(action: ContractAction) {
    const prompt = contractActionConfirmationPrompt(action);
    if (!prompt) return true;
    return intentConfirmationRef.value?.confirm(prompt) ?? false;
  }

  async function ensureSavedBeforeRecordAction() {
    if (!hasChanges.value) return true;
    return Boolean(await saveRecord({ on_success: ['scene_projection'] }));
  }

  function applyClientMode(mode: string, toggle = true) {
    const next = String(mode || '').trim();
    if (!next) return false;
    activeContractMode.value = toggle && activeContractMode.value === next ? '' : next;
    contractModeFeedback.value = '';
    if (!activeContractMode.value) closeContractPromptAction();
    return true;
  }

  function applyRouteConfigMode(rawMode: unknown) {
    const mode = String(rawMode || '').trim();
    if (isBusinessConfigRuntimeModel(model.value)) {
      if (
        activeContractMode.value === BUSINESS_CONFIG_MODES.formFieldConfiguration ||
        activeContractMode.value === BUSINESS_CONFIG_MODES.lowCode
      ) {
        activeContractMode.value = '';
      }
      return;
    }
    if (isBusinessConfigMode(mode)) {
      applyClientMode(mode, false);
    }
  }

  async function onContractFieldAction(payload: FormSectionFieldActionPayload) {
    const fieldKey = String(payload.field.name || '').trim();
    const actionValue = String(payload.action.value || '').trim();
    if (isContractFieldOrderEditable.value && fieldKey && ['show', 'hide'].includes(actionValue)) {
      fieldVisibilityDraft[fieldKey] = actionValue === 'show';
      fieldVisibilityDirtyKeys[fieldKey] = true;
      formConfigAuditResult.value = null;
      appendFormConfigOperation(
        actionValue === 'show' ? '显示字段' : '隐藏字段',
        `${formDesignFieldLabel(fieldKey)} 设置为${actionValue === 'show' ? '显示' : '隐藏'}`,
      );
      contractModeFeedback.value = '字段显示设置已调整，保存后生效';
      return;
    }
    if (actionValue === 'reload-requested') {
      await reload();
      return;
    }
    const raw = payload.action.raw;
    if (!raw) return;
    await runContractRuleAction(raw);
  }

  function onFormSettingsFieldSelect(payload: {
    field: FormSectionFieldSchema;
    groupTitle: string;
  }) {
    if (!isContractFieldOrderEditable.value) return;
    const fieldKey = String(payload.field.name || payload.field.key || '').trim();
    if (!fieldKey) return;
    rememberFormConfigFieldLabel(fieldKey, payload.field.label);
    if (!Object.prototype.hasOwnProperty.call(fieldVisibilityBase.value, fieldKey)) {
      const row = activeContractModeFieldRows.value.find((item) => item.fieldKey === fieldKey);
      const checkedAction = row?.actions.find((action) => Boolean(action.checked));
      fieldVisibilityBase.value = {
        ...fieldVisibilityBase.value,
        [fieldKey]: checkedAction ? checkedAction.value === 'show' : true,
      };
      if (!Object.prototype.hasOwnProperty.call(fieldVisibilityDraft, fieldKey)) {
        fieldVisibilityDraft[fieldKey] = checkedAction ? checkedAction.value === 'show' : true;
      }
    }
    selectedFormSettingsFieldKey.value = fieldKey;
    selectedFormSettingsFieldLabel.value = String(payload.field.label || fieldKey).trim();
    selectedFormSettingsFieldGroupTitleDraft.value =
      effectiveFieldGroupTitleForDraft(fieldKey) || normalizeFieldGroupTitle(payload.groupTitle);
    selectedFormSettingsFieldGroupTitleEdit.value = selectedFormSettingsFieldGroupTitleDraft.value;
    formSettingsActiveTab.value = 'fields';
  }

  function selectFormDesignerGroup(title: string) {
    const normalizedTitle = normalizeFieldGroupTitle(title);
    if (!normalizedTitle) return;
    const group = formDesignerGroupNavigatorItems.value.find((item) =>
      fieldGroupTitleMatches(item.title, normalizedTitle),
    );
    const orderedKeys = currentFormOrderedFieldKeys.value.length
      ? currentFormOrderedFieldKeys.value
      : currentFormDesignFieldKeys.value;
    const fieldKey =
      orderedKeys.find((key) => group?.fieldKeys.includes(key)) || group?.fieldKeys[0] || '';
    if (!fieldKey) return;
    onFormSettingsFieldSelect({
      field: {
        name: fieldKey,
        key: fieldKey,
        label: formDesignFieldLabel(fieldKey),
      } as FormSectionFieldSchema,
      groupTitle: normalizedTitle,
    });
  }

  function selectFormDesignerField(fieldKey: string) {
    const key = String(fieldKey || '').trim();
    if (!key) return;
    onFormSettingsFieldSelect({
      field: {
        name: key,
        key,
        label: formDesignFieldLabel(key),
      } as FormSectionFieldSchema,
      groupTitle: effectiveFieldGroupTitleForDraft(key) || '业务配置字段',
    });
  }

  async function onSelectedFormSettingsGroupTitleChange(value: string) {
    const oldTitle = selectedFormSettingsFieldGroupTitle.value;
    const newTitle = String(
      selectedFormSettingsFieldGroupTitleEdit.value || value || '',
    ).trim();
    if (!oldTitle || !newTitle || oldTitle === newTitle) {
      selectedFormSettingsFieldGroupTitleEdit.value = oldTitle;
      return;
    }
    await onContractInlineGroupRename({ oldTitle, newTitle });
  }

  async function onSelectedFormSettingsFieldLabelChange(value: string) {
    const fieldKey = selectedFormSettingsFieldKey.value;
    const label = String(value || '').trim();
    if (!fieldKey || !label || label === selectedFormSettingsFieldRow.value?.label) return;
    selectedFormSettingsFieldLabel.value = label;
    await setInlineFieldPolicy(fieldKey, { label });
  }

  function contractInlineFieldOrderIndex(field: FormSectionFieldSchema) {
    const fieldKey = String(field.name || '').trim();
    if (!fieldKey) return -1;
    return fieldOrderDraft.value.indexOf(fieldKey);
  }

  function onContractInlineFieldOrderMove(payload: {
    field: FormSectionFieldSchema;
    delta: number;
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    moveFieldOrder(fieldKey, payload.delta);
  }

  function onContractInlineFieldOrderDragStart(payload: {
    field: FormSectionFieldSchema;
    event: DragEvent;
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    rememberFormConfigFieldLabel(fieldKey, payload.field.label);
    const fieldLabel = String(payload.field.label || '').trim();
    draggingFieldLabel.value =
      fieldLabel && fieldLabel !== fieldKey ? fieldLabel : formDesignFieldLabel(fieldKey);
    onFieldOrderDragStart(fieldKey, payload.event);
  }

  function onContractInlineFieldOrderDragOver(payload: {
    field: FormSectionFieldSchema;
    groupTitle?: string;
    placement?: 'before' | 'after' | '';
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    rememberFormConfigFieldLabel(fieldKey, payload.field.label);
    onFieldOrderDragOver(fieldKey, payload.placement);
  }

  function onContractInlineFieldOrderDragLeave(payload: {
    field: FormSectionFieldSchema;
    groupTitle?: string;
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    onFieldOrderDragLeave(fieldKey);
  }

  function onContractInlineFieldOrderDrop(payload: {
    field: FormSectionFieldSchema;
    groupTitle?: string;
    placement?: 'before' | 'after' | '';
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    rememberFormConfigFieldLabel(fieldKey, payload.field.label);
    onFieldOrderDrop(fieldKey, payload.groupTitle, payload.placement);
  }

  function onContractInlineFieldOrderGroupDrop(payload: {
    groupTitle: string;
    groupIndex?: number;
  }) {
    onFieldOrderGroupDrop(payload.groupTitle);
  }

  function onContractInlineFieldOrderDragEnd() {
    onFieldOrderDragEnd();
  }

  function lowCodeApplyBaseParams() {
    const configAction = contractV2ActionRules.value.find(
      (rule) =>
        contractActionRuleKey(rule) === BUSINESS_CONFIG_ACTION_KEYS.currentFormFieldOrderSave,
    );
    const target = parseMaybeJsonRecord(configAction?.target);
    return buildLowCodeApplyBaseParams({
      actionId: actionId.value || route.query.action_id,
      viewId: routeQueryText('view_id') || routeQueryText('viewId'),
      targetParams: parseMaybeJsonRecord(target.params),
      modelName: String(model.value || ''),
    });
  }

  function contractFieldSequence(fieldKey: string, fallback = 100) {
    return contractFieldSequenceFromOrder(fieldOrderDraft.value, fieldKey, fallback);
  }

  function fieldGroupTitleForDraft(fieldKey: string) {
    return effectiveFieldGroupTitleForDraft(fieldKey);
  }

  function lowCodeReturnQuery() {
    return buildLowCodeReturnQuery({
      routeQuery: route.query as Record<string, unknown>,
      modelName: model.value,
      actionId: actionId.value,
      openPagesFlag: BUSINESS_CONFIG_ROUTE_FLAGS.openPages,
    });
  }

  function previewLowCodeConfiguredPage() {
    const query = buildLowCodePreviewQuery({
      routeQuery: route.query as Record<string, unknown>,
      returnToBusinessConfigFlag: BUSINESS_CONFIG_ROUTE_FLAGS.returnToBusinessConfig,
      openPagesFlag: BUSINESS_CONFIG_ROUTE_FLAGS.openPages,
    });
    router.push({ path: route.path, query });
  }

  async function previewCurrentFormConfiguration() {
    if (hasCurrentFormFieldDraftChanges.value) {
      const saved = await saveContractFieldOrder();
      if (!saved) return;
    }
    previewLowCodeConfiguredPage();
  }

  function returnToBusinessConfigDesigner() {
    router.push({
      path: '/admin/business-config',
      query: lowCodeReturnQuery(),
    });
  }

  async function applyProjectionRefreshPolicy(policy?: ContractAction['refreshPolicy']) {
    if (!policy || !Array.isArray(policy.on_success) || !policy.on_success.length) {
      return;
    }
    await executeProjectionRefresh({
      policy,
      refreshScene: async () => {
        await reload();
      },
      refreshWorkbench: async () => {
        await session.loadAppInit();
      },
      refreshRoleSurface: async () => {
        await session.loadAppInit();
      },
      recordTrace: ({ intent, writeMode, latencyMs }) => {
        session.recordIntentTrace({ intent, writeMode, latencyMs });
      },
    });
  }

  /**
   * Required editable positions the contract declares for this page.
   *
   * Used only to tell "the composition has nothing to validate" apart from
   * "the composition should have validated but had nothing registered".
   */
  function adoptedExpectedRequiredFieldNames(): string[] {
    return (layoutNodes.value as LayoutNode[])
      .filter((node) => node.kind === 'field' && !node.readonly && Boolean(node.descriptor?.required))
      .filter((node) => isWritableFieldVisible(node.name))
      .map((node) => node.name);
  }

  /**
   * Ask the adopted form sections to validate before anything is written.
   *
   * Three boundaries are kept apart:
   *  - a surface outside the pilot scope adopts nothing and needs no runtime;
   *  - an adopted surface whose runtime or section registration is missing,
   *    while the contract still declares required editable positions, fails
   *    closed and keeps the draft instead of passing silently;
   *  - an adopted surface whose contract genuinely has no required editable
   *    position is a legal empty set, not a runtime failure.
   *
   * `coveredFieldNames` is what the official engine really evaluated. The save
   * chain excludes exactly those positions from the page-level generic precheck,
   * so one save is never decided twice by two generic authorities. Positions the
   * engine did not cover keep their pre-existing precheck, so an applicable but
   * unmounted position can never be auto-passed.
   *
   * The rejected codes join the same error store the rest of the save chain
   * uses, so there is one summary, one per-field message and one focus entry.
   */
  async function runAdoptedFormValidation(): Promise<{ ok: boolean; coveredFieldNames: string[]; superseded: boolean }> {
    // The operation this run belongs to. `saveRecord` opens one before calling
    // here, so the await below is bound to a surface the caller can re-verify.
    const operation = activeSaveOperation;
    if (!resolveStandardFormComposition({ model: model.value }).adopted) {
      return { ok: true, coveredFieldNames: [], superseded: false };
    }
    const validate = typeof validateAdoptedFormSections === 'function' ? validateAdoptedFormSections : null;
    const outcome = validate ? await validate() : null;
    // The engine can take a while, and the page can move on while it runs. A
    // stale answer must not enter the error store, focus a field, or announce
    // "validation could not finish" on a page it never validated: the guard is
    // here, at the write, not only at the caller's return value.
    if (!saveOperationOwnsSurface(operation)) {
      return { ok: false, coveredFieldNames: [], superseded: true };
    }
    const coveredFieldNames = outcome?.ok && Array.isArray(outcome.coveredFieldNames)
      ? outcome.coveredFieldNames
      : [];
    const coverageMissing = adoptedExpectedRequiredFieldNames().length > 0 && coveredFieldNames.length === 0;
    if (!outcome?.ok || coverageMissing) {
      const message = '表单校验未能完成，请重试。';
      submissionFeedback.value = { kind: 'warn', message };
      validationErrors.value = [message];
      validationFieldErrors.value = {};
      return { ok: false, coveredFieldNames: [], superseded: false };
    }
    const fieldNames: string[] = Array.isArray(outcome.fieldNames) ? outcome.fieldNames : [];
    if (!fieldNames.length) return { ok: true, coveredFieldNames, superseded: false };
    const labels = (layoutNodes.value as LayoutNode[]).reduce<Record<string, string>>((acc, node) => {
      if (node.kind === 'field') acc[node.name] = node.label || node.name;
      return acc;
    }, {});
    const payload = buildRequiredFieldErrorPayload(
      fieldNames.map((name) => ({ name, label: labels[name] || name })),
      { model: model.value, recordId: recordId.value },
    );
    validationErrors.value = payload.messages;
    validationFieldErrors.value = payload.fieldErrors;
    submissionFeedback.value = { kind: 'warn', message: '请先补充必填信息，再保存草稿或提交。' };
    await focusFirstValidationError();
    return { ok: false, coveredFieldNames: [], superseded: false };
  }

  async function saveRecord(
    refreshPolicy?: ContractAction['refreshPolicy'],
    options: { navigateAfterCreate?: boolean } = {},
  ): Promise<boolean | number> {
    if (!canSave.value || !model.value) return false;
    const operation = beginSaveOperation();
    submissionFeedback.value = null;
    validationErrors.value = [];
    validationFieldErrors.value = {};
    formConflict.value = false;
    // The draft as it stands before the official engine looks at it. If it
    // changes while the engine is deciding, the value about to be written was
    // never validated: keep the draft, stop this save, and let the user save
    // again. Nothing here retries or writes the newer draft on the older answer.
    const validatedDraftSnapshot = canonicalizeSubmissionValues(collectWritableValues());
    const adoptedValidation = await runAdoptedFormValidation();
    if (adoptedValidation.superseded) return false;
    if (!adoptedValidation.ok) return false;
    if (!saveOperationOwnsSurface(operation)) return false;
    if (canonicalizeSubmissionValues(collectWritableValues()) !== validatedDraftSnapshot) {
      submissionFeedback.value = { kind: 'warn', message: '表单内容已变化，请重新保存。' };
      return false;
    }
    const validation = await validateBeforeSaveRecord({
      excludedRequiredFieldNames: adoptedValidation.coveredFieldNames,
      collectSceneValidationPrecheckErrors: (fieldLabels) =>
        collectSceneValidationPrecheckErrors(fieldLabels),
      collectWritableValues: () => collectWritableValues(),
      formData,
      isWritableFieldVisible: (name) => isWritableFieldVisible(name),
      layoutNodes: layoutNodes.value,
      layoutFieldLabels: () =>
        (layoutNodes.value as LayoutNode[]).reduce<Record<string, string>>((acc, node) => {
          if (node.kind === 'field') acc[node.name] = node.label || node.name;
          return acc;
        }, {}),
      normalizeFieldValue: (name, value) => normalizeFieldValue(name, value),
      one2manyFieldErrors: one2manyValidation.value.cellErrors,
      one2manyIssues: one2manyValidation.value.issues,
      model: operation.model,
      recordId: operation.recordId,
      resolvePendingInlineRelationCreates: () => resolvePendingInlineRelationCreates(),
      resolvePendingMany2manyTagCreates: () => resolvePendingMany2manyTagCreates(),
    });
    // The precheck awaited the network for relation creates too, so the same
    // ownership and same-draft rules hold before anything is written.
    if (!saveOperationOwnsSurface(operation)) return false;
    showOne2manyErrors.value = Boolean(validation.showOne2manyErrors);
    if (!validation.ok || !validation.editableMap) {
      validationErrors.value = validation.validationErrors || [];
      validationFieldErrors.value = validation.fieldErrors || {};
      submissionFeedback.value = validation.submissionFeedback || null;
      await focusFirstValidationError();
      return false;
    }
    const editableMap = validation.editableMap;
    if (canonicalizeSubmissionValues(collectWritableValues()) !== canonicalizeSubmissionValues(editableMap)) {
      submissionFeedback.value = { kind: 'warn', message: '表单内容已变化，请重新保存。' };
      return false;
    }
    busyKind.value = 'save';
    busyOwnerOperationId = operation.id;
    try {
      const values = buildSaveRecordPayload({
        comparableFieldValue: (name, value) => comparableFieldValue(name, value),
        formFields: formFields.value,
        dirtyFieldSet,
        editableMap,
        formData,
        originalValues: originalValues.value,
        recordId: operation.recordId,
      });
      if (operation.recordId && !Object.keys(values).length) {
        if (busyOwnerOperationId === operation.id) busyKind.value = null;
        dirtyFieldSet.clear();
        return true;
      }
      if (operation.recordId) {
        // The write targets the record this operation started for, never
        // whatever the page happens to show by the time the request is built.
        await writeContractFormRecord({
          model: operation.model,
          ids: [operation.recordId],
          vals: values,
          ifMatch: recordVersionPolicy() ? recordVersionToken.value : undefined,
        });
        // The write has already been sent. A response for a surface the user
        // has left is dropped as-is: it is not a rollback, it is not retried,
        // and it must not repaint, navigate or clear the page that owns the
        // screen now. The record is read back the next time it is opened.
        if (!saveOperationOwnsSurface(operation)) return false;
        formConflict.value = false;
        originalValues.value = snapshotOriginalFormValues(Object.keys(formData), formData);
        dirtyFieldSet.clear();
        const appliedRefreshPolicy = refreshPolicy || { on_success: ['scene_projection'] };
        await applyProjectionRefreshPolicy(appliedRefreshPolicy);
        if (!saveOperationOwnsSurface(operation)) return false;
        if (!appliedRefreshPolicy.on_success?.includes('scene_projection')) {
          await reload();
          if (!saveOperationOwnsSurface(operation)) return false;
        }
        if (status.value !== 'ok') {
          submissionFeedback.value = {
            kind: 'error',
            message: '修改已写入，但未能读取服务端最新结果，请重新加载页面。',
          };
          return true;
        }
        submissionFeedback.value = { kind: 'success', message: formUiLabel('save_success') };
        return true;
      }
      const context = buildFormRequestContext(
        route.query,
        formCreateContextFromState({
          contract: contract.value,
          v2ContractStore: v2ContractStore.value,
        }),
      );
      const created = await createContractFormRecord({ model: operation.model, vals: values, context });
      if (!saveOperationOwnsSurface(operation)) return false;
      if (created?.id) {
        const attachmentsUploaded = await uploadPendingNativeAttachments(Number(created.id));
        if (!saveOperationOwnsSurface(operation)) return false;
        if (!attachmentsUploaded) {
          return false;
        }
        const title = String(v2ContractStore.value?.snapshot.pageInfo.pageName || '').trim();
        submissionFeedback.value = { kind: 'success', message: `${title || '记录'}已创建` };
        clearIntakeAutosave();
        if (options.navigateAfterCreate === false) {
          return Number(created.id);
        }
        return await navigateCreatedRecord({
          createdId: created.id,
          createdLabel: String(formData.display_name || formData.name || title || '').trim(),
          nextSceneKey: String(sceneReadyFormSurface.value.nextSceneKey || '').trim(),
          nextSceneRoute: String(sceneReadyFormSurface.value.nextSceneRoute || '').trim(),
          refreshPolicy,
        });
      }
    } catch (err) {
      // A rejection that names a page the user has left must not mark the
      // current record, steal its focus, or drive it to login/denied.
      if (!saveOperationOwnsSurface(operation)) return false;
      const fallback = operation.recordId ? '保存失败，请检查填写内容' : '创建失败，请检查填写内容';
      if (err instanceof ApiError && err.status === 401) {
        await session.logout();
        await router.replace('/login');
        return false;
      }
      if (err instanceof ApiError && err.status === 403) {
        await router.replace({ name: 'access-denied' });
        return false;
      }
      if (err instanceof ApiError && err.status === 409) {
        formConflict.value = true;
        validationErrors.value = ['当前记录已发生变化，请加载最新数据后重新核对本次修改。'];
        validationFieldErrors.value = {};
        submissionFeedback.value = {
          kind: 'error',
          message: '记录已被其他操作更新，当前输入尚未写入。',
        };
        await focusFirstValidationError();
        return false;
      }
      // A business rejection that names its owning field is presented against
      // that field. A rejection that only carries a message stays an
      // operation-level error: the field is never recovered from the text.
      const serverFieldErrors = err instanceof ApiError && err.status === 422
        ? decodeServerFieldErrors(err.details, { model: operation.model, recordId: operation.recordId })
        : [];
      const message = sanitizeUiErrorMessage(err instanceof Error ? err.message : err, fallback);
      validationErrors.value = [message];
      validationFieldErrors.value = indexBusinessFieldErrors(serverFieldErrors);
      submissionFeedback.value = { kind: 'error', message: message && message !== fallback ? message : fallback };
      await focusFirstValidationError();
      return false;
    } finally {
      // Only the operation that took the busy flag may release it, so a
      // superseded save cannot switch off a newer save's loading state.
      if (busyOwnerOperationId === operation.id) {
        busyKind.value = null;
        busyOwnerOperationId = 0;
      }
    }
    return false;
  }
  // Collapse repeated clicks onto one save, but only inside one surface: a save
  // that belongs to another record or draft is never joined.
  const singleFlightSaveRecord = createSingleFlightSave(
    saveRecord,
    () => `${surfaceEpoch.value}\u0000${boundSurfaceKey()}`,
  );

  useFormPageLifecycleRuntime({
    formRouteIdentity: () => formRouteIdentity(),
    formRouteOwnerIdentity: () => formRouteOwnerIdentity(),
    handleRecordContextChanged,
    instanceRouteIdentity,
    isComponentActive,
    onFieldOrderDragEnd,
    onFieldOrderWindowDragOver,
    onFieldOrderWindowDragStop,
    onRelationDialogDocumentKeydown,
    recordContextChangedEvent: RECORD_CONTEXT_CHANGED_EVENT,
    routeIsOwned: () => isFormPageRouteOwner(route.name),
    reload: () => reload(),
    retainedRouteIdentity,
    status,
    ensureFormInitialReload: () => ensureFormInitialReload(),
  });

  return {
    discardChanges,
    confirmActionSafety,
    ensureSavedBeforeRecordAction,
    applyClientMode,
    applyRouteConfigMode,
    onContractFieldAction,
    onFormSettingsFieldSelect,
    selectFormDesignerGroup,
    selectFormDesignerField,
    onSelectedFormSettingsGroupTitleChange,
    onSelectedFormSettingsFieldLabelChange,
    contractInlineFieldOrderIndex,
    onContractInlineFieldOrderMove,
    onContractInlineFieldOrderDragStart,
    onContractInlineFieldOrderDragOver,
    onContractInlineFieldOrderDragLeave,
    onContractInlineFieldOrderDrop,
    onContractInlineFieldOrderGroupDrop,
    onContractInlineFieldOrderDragEnd,
    lowCodeApplyBaseParams,
    contractFieldSequence,
    fieldGroupTitleForDraft,
    routeQueryText,
    lowCodeReturnQuery,
    previewLowCodeConfiguredPage,
    previewCurrentFormConfiguration,
    returnToBusinessConfigDesigner,
    applyProjectionRefreshPolicy,
    saveRecord: singleFlightSaveRecord,
  };
}

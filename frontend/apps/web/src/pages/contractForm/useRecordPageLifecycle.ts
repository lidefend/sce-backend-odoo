/* eslint-disable @typescript-eslint/no-explicit-any */
import { computed } from 'vue';
import type { FormRecordHydrationTarget } from './recordHydration';
import { readonlyMainDataCoversFields } from './readonlyMainDataCoverage';
import { contractLoadProfileOptions } from './contractRenderProfile';
import {
  loadAuthoritativeCreateDefaults,
  resolveCreateRouteRelationLabels,
  shouldHydrateCreateDefaults,
} from './createDefaults';

type LifecycleDependencies = Record<string, any>;

/** Owns authoritative contract loading, record hydration, and stale-response isolation. */
export function useRecordPageLifecycle(dependencies: LifecycleDependencies) {
  const { ApiError, ContractAccessPolicyError, ContractV2DecodeError, ErrorCodes, actionId, advancedExpanded, analyzeFormContractReadiness, applyIncomingFormFieldValue, applyPageStatusEvent, buildRouteContractContext, changedFieldCount, changedFieldSet, clearNativeAttachmentError, clearNativeChatterForRecordLoad, clearOne2manyRows, clearPendingNativeAttachments, closeNativeChatterComposer, contractAccessPolicy, contractActions, contractModelName, contractReadiness, coreFieldNames, createContractV2Store, decodeContractV2Snapshot, defaultContractFormRecord, dirtyFieldSet, formData, formDataFieldNames, formRouteIdentity, hydrateSelectedRelationOptions, hydrateVisibleOne2manyRows, initOne2manyRows, isComponentActive, layoutNodes, loadError, menuId, model, nativeChatterAutoLoadKey, nativeLayoutVisibilityRevision, onchangeLinePatches, onchangeModifiersPatch, getOnchangeTimer, setOnchangeTimer, onchangeWarnings, originalValues, pickContractNavQuery, readContractFormRecord, recordId, recordIdDisplay, recordMissing, recordVersionPolicy, recordVersionToken, relationKeywords, relationOptions, renderErrorMessage, renderProfile, requestedSourceMode, requestedSurface, resolveContractV2MainData, resolveCreateDefaultsFromState, resolveNavigationUrlFromOrigin, restoreIntakeAutosave, retainedRouteIdentity, rights, route, router, setStatusbarValue, showHud, showOne2manyErrors, snapshotOriginalFormValues, status, toPositiveInt, upsertRelationOption, v2ContractDecodeError, v2ContractStore, formV2ActionCount, formV2ButtonStatusCount, formV2FieldCodeCount, formV2GlobalSourceKind, formV2LayoutSourceKind, formV2AuthorityIssuePreview, formV2DescriptorCount, formV2MainDataFieldCount, formV2ReadonlyValueCount, formV2SourceContextKind, formV2StatusFieldCount, formV2StoreReady, formV2ValueFieldCount, formV2ValueSourceKind, formV2WidgetCount, validateSurfaceMarkers, validationErrors, writableFieldCount } = dependencies;
  let activeReloadToken = 0;
  let activeReloadIdentity = '';
  let activeReloadPromise: Promise<void> | null = null;

  function resolveNavigationUrl(url: string) {
    return resolveNavigationUrlFromOrigin(url, window.location.origin);
  }

  function syncContractV2Store(snapshot: unknown) {
    v2ContractStore.value = null;
    v2ContractDecodeError.value = '';
    try {
      v2ContractStore.value = createContractV2Store(decodeContractV2Snapshot(snapshot));
    } catch (err) {
      if (err instanceof ContractV2DecodeError) {
        v2ContractDecodeError.value = err.issues.slice(0, 4).map((issue) => `${issue.path} ${issue.message}`).join(' | ');
        throw err;
      }
      v2ContractDecodeError.value = err instanceof Error ? err.message : '表单配置解析失败';
      throw err;
    }
  }
  const strictFieldDescriptor=(name:string)=>{const key=String(name||'').trim();if(!key)return undefined;const widgets=v2ContractStore.value?.widgetsByFieldCodeAll.get(key)||[];return widgets.find((widget)=>widget.fieldDescriptor)?.fieldDescriptor;};

  const viewOrchestrationHudSummary = computed(() => {
    const rootGovernance = (v2ContractStore.value?.snapshot.runtimeContract as Record<string, unknown> | undefined)?.governance;
    const governance = rootGovernance && typeof rootGovernance === 'object' && !Array.isArray(rootGovernance)
      ? rootGovernance as Record<string, unknown>
      : {};
    const orchestration = governance.view_orchestration && typeof governance.view_orchestration === 'object' && !Array.isArray(governance.view_orchestration)
      ? governance.view_orchestration as Record<string, unknown>
      : {};
    const views = orchestration.views && typeof orchestration.views === 'object' && !Array.isArray(orchestration.views)
      ? orchestration.views as Record<string, unknown>
      : {};
    const current = (views.form || {}) as Record<string, unknown>;
    const contracts = Array.isArray(current.business_config_contracts)
      ? current.business_config_contracts as Array<Record<string, unknown>>
      : [];
    const businessConfigFormFields = Array.isArray(current.business_config_form_fields)
      ? current.business_config_form_fields.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    const skippedLegacyPolicyFields = Array.isArray(current.skipped_legacy_policy_fields)
      ? current.skipped_legacy_policy_fields.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    return {
      applied: Boolean(orchestration.applied || current.applied || contracts.length),
      owner: String(orchestration.owner_layer || current.owner_layer || '-'),
      contractCount: contracts.length,
      contractNames: contracts.map((row) => String(row.name || row.id || '').trim()).filter(Boolean).join(',') || '-',
      legacyOverlay: Boolean(current.legacy_field_policy_overlay),
      businessConfigFieldCount: businessConfigFormFields.length,
      skippedLegacyPolicyFields: skippedLegacyPolicyFields.join(',') || '-',
    };
  });

  const hudEntries = computed(() => [
    { label: '业务对象', value: model.value || '-' },
    { label: '操作编号', value: actionId.value || '-' },
    { label: '记录编号', value: recordIdDisplay.value },
    { label: '配置已加载', value: Boolean(v2ContractStore.value) },
    { label: '配置可用', value: contractReadiness.value.usable },
    { label: '配置问题数', value: contractReadiness.value.issues.length },
    { label: 'V2配置可用', value: formV2StoreReady.value },
    { label: 'V2组件数', value: formV2WidgetCount.value },
    { label: 'V2操作数', value: formV2ActionCount.value },
    { label: 'V2按钮状态数', value: formV2ButtonStatusCount.value },
    { label: 'V2字段描述数', value: formV2FieldCodeCount.value },
    { label: 'V2字段描述数', value: formV2DescriptorCount.value },
    { label: 'V2权威问题', value: formV2AuthorityIssuePreview.value },
    { label: 'V2布局来源', value: formV2LayoutSourceKind.value },
    { label: 'V2全局来源', value: formV2GlobalSourceKind.value },
    { label: 'V2上下文来源', value: formV2SourceContextKind.value },
    { label: 'V2状态字段数', value: formV2StatusFieldCount.value },
    { label: 'V2值字段数', value: formV2ValueFieldCount.value },
    { label: 'V2主数据字段数', value: formV2MainDataFieldCount.value },
    { label: 'V2只读值数', value: formV2ReadonlyValueCount.value },
    { label: 'V2值来源', value: formV2ValueSourceKind.value },
    { label: '配置解析问题', value: v2ContractDecodeError.value || '-' },
    { label: '配置视图类型', value: v2ContractStore.value?.snapshot.pageInfo.viewType || '-' },
    { label: '页面编排已应用', value: viewOrchestrationHudSummary.value.applied },
    { label: '页面编排责任层', value: viewOrchestrationHudSummary.value.owner },
    { label: '页面编排配置数', value: viewOrchestrationHudSummary.value.contractCount },
    { label: '页面编排名称', value: viewOrchestrationHudSummary.value.contractNames },
    { label: '表单配置字段数', value: viewOrchestrationHudSummary.value.businessConfigFieldCount },
    { label: '跳过策略字段', value: viewOrchestrationHudSummary.value.skippedLegacyPolicyFields },
    { label: '历史策略覆盖', value: viewOrchestrationHudSummary.value.legacyOverlay },
    { label: '渲染档位', value: renderProfile.value },
    { label: '字段数', value: v2ContractStore.value?.widgetsByFieldCode.size || 0 },
    { label: '布局节点数', value: layoutNodes.value.length },
    { label: '可写字段数', value: writableFieldCount.value },
    { label: '已变更字段数', value: changedFieldCount.value },
    { label: '操作数', value: contractActions.value.length },
    { label: '权限', value: `${rights.value.read ? 'R' : '-'}${rights.value.write ? 'W' : '-'}${rights.value.create ? 'C' : '-'}${rights.value.unlink ? 'D' : '-'}` },
    { label: '联动提醒数', value: onchangeWarnings.value.length },
    { label: '明细联动补丁数', value: onchangeLinePatches.value.length },
  ]);
  async function loadContract() {
    v2ContractStore.value = null;
    v2ContractDecodeError.value = '';
    const profileOptions = contractLoadProfileOptions(renderProfile.value);
    const currentModel = String(model.value || '').trim();
    const contractContext = buildRouteContractContext(route.query as Record<string, unknown>);
    const contextRaw = String(route.query.context_raw || '').trim();
    const sceneKey = String(route.query.scene_key || route.query.scene || '').trim();
    const requestedViewId = toPositiveInt(route.query.view_id) || toPositiveInt(route.query.viewId) || 0;
    let strictSnapshot: unknown = null;
    if (actionId.value && recordId.value) {
      try {
        const bundle = await dependencies.loadActionFormContractV2Bundle(actionId.value, {
          sceneKey: sceneKey || undefined,
          menuId: menuId.value || undefined,
          viewType: 'form',
          viewId: requestedViewId || undefined,
          recordId: recordId.value,
          ...profileOptions,
          surface: requestedSurface.value,
          sourceMode: requestedSourceMode.value,
          context: contractContext,
          contextRaw,
          previewToken: String(route.query.preview_token || '').trim() || undefined,
          previewRoleKey: String(route.query.preview_role_key || '').trim() || undefined,
        });
        strictSnapshot = bundle.snapshot;
        const actionModel = String(bundle.snapshot.pageInfo.model || '').trim();
        if (currentModel && actionModel !== currentModel) throw new Error('strict V2 action model authority mismatch');
      } catch (error) {
        // Strict V2 authority failures must not silently switch from the
        // requested action/view to a second model-scoped contract.
        throw error;
      }
    }
    if (!strictSnapshot && currentModel) {
      const bundle = await dependencies.loadModelFormContractV2Bundle(currentModel, {
        sceneKey: sceneKey || undefined,
        actionId: actionId.value || undefined,
        menuId: menuId.value || undefined,
        viewType: 'form',
        viewId: requestedViewId || undefined,
        recordId: recordId.value,
        ...profileOptions,
        surface: requestedSurface.value,
        sourceMode: requestedSourceMode.value,
        context: contractContext,
        contextRaw,
        previewToken: String(route.query.preview_token || '').trim() || undefined,
        previewRoleKey: String(route.query.preview_role_key || '').trim() || undefined,
      });
      strictSnapshot = bundle.snapshot;
    }
    syncContractV2Store(strictSnapshot);
    if (!v2ContractStore.value || v2ContractStore.value.snapshot.pageInfo.viewType !== 'form') {
      throw new Error('strict V2 form contract is required');
    }
    const policy = contractAccessPolicy.value;
    if (policy.mode === 'block') {
      const message = policy.message || 'contract access policy blocked this page';
      throw new ContractAccessPolicyError(message, policy.reasonCode || 'CONTRACT_ACCESS_BLOCKED');
    }
    const hasCore = coreFieldNames.value.length > 0;
    advancedExpanded.value = renderProfile.value !== 'create' || !hasCore;
  }

  async function loadRecord() {
    const versionPolicy = recordVersionPolicy();
    const fieldNames = formDataFieldNames();
    if (!fieldNames.includes('display_name')) fieldNames.push('display_name');
    if (versionPolicy?.tokenField && !fieldNames.includes(versionPolicy.tokenField)) {
      fieldNames.push(versionPolicy.tokenField);
    }
    recordVersionToken.value = '';
    closeNativeChatterComposer();
    clearNativeChatterForRecordLoad();
    clearNativeAttachmentError();
    if (!recordId.value) {
      clearPendingNativeAttachments();
      nativeChatterAutoLoadKey.value = '';
    }
    Object.keys(formData).forEach((key) => {
      delete formData[key];
    });
    Object.keys(relationKeywords).forEach((key) => {
      delete relationKeywords[key];
    });
    relationOptions.value = {};
    clearOne2manyRows();
    onchangeModifiersPatch.value = {};
    onchangeWarnings.value = [];
    onchangeLinePatches.value = [];
    changedFieldSet.clear();
    dirtyFieldSet.clear();
    const pendingOnchangeTimer = getOnchangeTimer();
    if (pendingOnchangeTimer) {
      clearTimeout(pendingOnchangeTimer);
      setOnchangeTimer(null);
    }
    const hydrationTarget: FormRecordHydrationTarget = {
      formData,
      relationOptions: relationOptions.value,
      relationKeywords,
      upsertRelationOption,
      initOne2manyRows,
    };
    if (shouldHydrateCreateDefaults(recordId.value, renderProfile.value)) {
      const baseDefaults = resolveCreateDefaultsFromState({ routeQuery: route.query as Record<string, unknown>, v2ContractStore: v2ContractStore.value });
      const defaults = await loadAuthoritativeCreateDefaults({
        primaryDataSource: v2ContractStore.value?.primaryDataSource || null,
        model: model.value,
        fieldNames,
        baseDefaults,
        fetchDefaults: defaultContractFormRecord,
      });
      fieldNames.forEach((name) => {
        const descriptor = strictFieldDescriptor(name);
        applyIncomingFormFieldValue({
          fieldName: name,
          descriptor,
          incoming: name in defaults ? defaults[name] : '',
          target: hydrationTarget,
        });
      });
      Object.entries(resolveCreateRouteRelationLabels(v2ContractStore.value, route.query as Record<string, unknown>, defaults)).forEach(([name, label]) => {
        if (!fieldNames.includes(name)) return;
        const id = Number(formData[name] || 0);
        if (!Number.isFinite(id) || id <= 0) return;
        upsertRelationOption(name, { id, label });
        relationKeywords[name] = label;
      });
      originalValues.value = snapshotOriginalFormValues(fieldNames, formData);
      nativeLayoutVisibilityRevision.value += 1;
      restoreIntakeAutosave();
      return;
    }
    const contractMainData = resolveContractV2MainData(v2ContractStore.value);
    const canUseReadonlyMainData = readonlyMainDataCoversFields({
      renderProfile: renderProfile.value,
      fieldNames,
      mainData: contractMainData,
    });
    let row: Record<string, unknown> | undefined;
    if (canUseReadonlyMainData) {
      row = contractMainData;
    } else {
      const read = await readContractFormRecord({
        model: model.value,
        ids: [recordId.value],
        fields: fieldNames.length ? fieldNames : '*',
      });
      row = read.records?.[0];
    }
    if (!row) {
      recordMissing.value = true;
      return;
    }
    recordMissing.value = false;
    if (versionPolicy?.tokenField) {
      recordVersionToken.value = String((row as Record<string, unknown>)[versionPolicy.tokenField] || '').trim();
    }
    fieldNames.forEach((name) => {
      if (name === versionPolicy?.tokenField && !strictFieldDescriptor(name)) return;
      const incoming = Object.prototype.hasOwnProperty.call(row, name)
        ? (row as Record<string, unknown>)[name]
        : (contractMainData[name] ?? '');
      applyIncomingFormFieldValue({
        fieldName: name,
        descriptor: strictFieldDescriptor(name),
        incoming,
        target: hydrationTarget,
      });
    });
    originalValues.value = snapshotOriginalFormValues(fieldNames, formData);
    nativeLayoutVisibilityRevision.value += 1;
  }
  function handleSceneBlockAction(payload: { action?: { target?: Record<string, unknown> } }) {
    const target = payload?.action?.target && typeof payload.action.target === 'object'
      ? payload.action.target
      : {};
    const targetKind = String(target.kind || '').trim();
    if (targetKind === 'statusbar_value') {
      const value = String(target.value || '').trim();
      if (value) {
        setStatusbarValue(value);
        return;
      }
    }
    const route = String(target.route || '').trim();
    if (route) {
      void router.push(route);
      return;
    }
    const sceneKey = String(target.scene_key || '').trim();
    if (sceneKey) {
      void router.push({ name: 'scene', params: { sceneKey } });
    }
  }
  async function reload() {
    const reloadIdentity = formRouteIdentity();
    if (activeReloadPromise && reloadIdentity && reloadIdentity === activeReloadIdentity) {
      return activeReloadPromise;
    }
    const run = (async () => {
      const reloadToken = activeReloadToken + 1;
      activeReloadToken = reloadToken;
      renderErrorMessage.value = '';
      Object.assign(loadError, { status: null, reason: '', trace: '' });
      recordMissing.value = false;
      applyPageStatusEvent({ kind: 'status', transaction: 'formReload', status: 'loading' });
      validationErrors.value = [];
      showOne2manyErrors.value = false;
      try {
        await loadContract();
        if (reloadToken !== activeReloadToken) return;
        await loadRecord();
        if (reloadToken !== activeReloadToken) return;
        applyPageStatusEvent({ kind: 'status', transaction: 'formReload', status: 'ok' });
        retainedRouteIdentity.value = formRouteIdentity();
        void preloadFormAuxiliaryData(reloadToken);
      } catch (err) {
        if (reloadToken !== activeReloadToken) return;
        if (err instanceof ApiError) {
          Object.assign(loadError, { status: err.status, reason: String(err.reasonCode || ''), trace: String(err.traceId || '') });
        }
        if (err instanceof ApiError && err.status === 403) {
          await router.replace({
            name: 'access-denied',
            query: { from: route.fullPath, reason: err.reasonCode || 'PERMISSION_DENIED' },
          });
          return;
        }
        if (err instanceof ApiError && err.status === 404) {
          recordMissing.value = true;
          renderErrorMessage.value = '';
          // The status protocol clears any prior loading error without a direct ref write.
          applyPageStatusEvent({ kind: 'status', transaction: 'formReload', status: 'ok' });
          return;
        }
        if (err instanceof ContractAccessPolicyError) {
          await router.push({
            name: 'workbench',
            query: pickContractNavQuery(route.query as Record<string, unknown>, {
              reason: ErrorCodes.CAPABILITY_MISSING,
              action_id: actionId.value || undefined,
              menu_id: Number(route.query.menu_id || 0) || undefined,
              diag: showHud.value ? (err.reasonCode || 'CONTRACT_ACCESS_BLOCKED') : undefined,
            }),
          });
          return;
        }
        applyPageStatusEvent({ kind: 'status', transaction: 'formReload', status: 'error', errorMessage: err instanceof Error ? err.message : '表单加载失败' });
      } finally {
        if (activeReloadIdentity === reloadIdentity) {
          activeReloadPromise = null;
          activeReloadIdentity = '';
        }
      }
    })();
    activeReloadIdentity = reloadIdentity;
    activeReloadPromise = run;
    return run;
  }

  function ensureFormInitialReload() {
    const identity = formRouteIdentity();
    if (!identity) return;
    if (identity === retainedRouteIdentity.value && status.value === 'ok') return;
    if (status.value === 'loading' || !v2ContractStore.value) {
      void reload();
    }
  }

  async function preloadFormAuxiliaryData(reloadToken: number) {
    try {
      if (!isComponentActive.value || reloadToken !== activeReloadToken) return;
      // Relation candidates are interaction-time data. Eagerly enumerating all
      // writable relations here leaves requests in flight across route/actor
      // changes and probes models the user never opened. Create defaults only
      // need their already-selected identities hydrated.
      if (!recordId.value) {
        if (renderProfile.value !== 'readonly') {
          await hydrateSelectedRelationOptions();
          if (!isComponentActive.value || reloadToken !== activeReloadToken) return;
        }
      }
      await hydrateVisibleOne2manyRows();
    } catch {
      // Auxiliary data can be completed by explicit field interactions after the form renders.
    }
  }


  return {
    resolveNavigationUrl,
    syncContractV2Store,
    viewOrchestrationHudSummary,
    hudEntries,
    loadContract,
    loadRecord,
    handleSceneBlockAction,
    reload,
    ensureFormInitialReload,
    preloadFormAuxiliaryData,
  };
}

/* eslint-disable @typescript-eslint/no-explicit-any */
import { computed, nextTick, type ComputedRef, type Ref } from 'vue';
import type { ContractV2NormalizedStore } from '../../app/contracts/v2';
import { ErrorCodes } from '../../app/error_codes';
import { findActionMeta } from '../../app/menu';
import { resolveSceneValidationSuggestedAction } from '../../app/sceneValidationRecoveryStrategy';
import { resolveFormSceneReady } from '../../app/resolvers/sceneReadyResolver';
import { isCoreSceneStrictMode } from '../../app/contractStrictMode';
import { resolveUnifiedPageContractV2FieldGroups, resolveUnifiedPageContractV2VisibleFields } from '../../app/contracts/unifiedPageContractV2';
import { collectPrimaryActionRequiredFields } from './contractRuntimeVm';
import { dictOrEmpty } from './recordUtils';
import {
  normalizeContractFieldSemantics,
  normalizeSemanticFieldGroups,
  resolveFieldSemanticMeta,
  semanticFieldNamesBySurfaceRole,
  type FieldSemanticMeta,
  type SemanticFieldGroup,
} from './nativeLayoutUtils';
import {
  buildSceneValidationPanel,
  sceneValidationErrorPrefix,
  strictContractDefaultsSummary as strictContractDefaultsSummaryFromGuard,
  strictContractGuardFromSceneReadyEntry,
  strictContractMissingSummary as strictContractMissingSummaryFromGuard,
} from './sceneValidation';

export function useRecordContractSemantics(context: {
  v2ContractStore: Ref<ContractV2NormalizedStore | null>;
  route: any;
  session: any;
  actionId: ComputedRef<number | null>;
  recordId: ComputedRef<number | null>;
  model: ComputedRef<string>;
  renderProfile: ComputedRef<string>;
  runtimeRoleCode: ComputedRef<string>;
  validationErrors: Ref<string[]>;
  isIntakeCreateMode: ComputedRef<boolean>;
  intentConfirmationRef: Ref<{ confirm: (input: { actionLabel: string; message: string }) => Promise<boolean> } | null>;
  formConflict: Ref<boolean>;
  layoutNodes: () => Array<{ kind: string; name: string; label: string }>;
  reload: () => Promise<unknown>;
  focusValidationError: (message: string, fields: Array<{ kind: string; name: string; label: string }>) => void;
}) {
  const strictFieldDescriptors = () => Array.from(context.v2ContractStore.value?.widgetsById.values() || [])
    .reduce<Record<string, any>>((output, widget) => {
      if (widget.fieldCode && widget.fieldDescriptor && !output[widget.fieldCode]) output[widget.fieldCode] = widget.fieldDescriptor;
      return output;
    }, {});
  const strictSnapshot = () => dictOrEmpty(context.v2ContractStore.value?.snapshot);
  const semanticFieldGroups = computed<Record<string, SemanticFieldGroup>>(() => {
    const raw = resolveUnifiedPageContractV2FieldGroups(strictSnapshot());
    return normalizeSemanticFieldGroups(raw, undefined);
  });
  const contractFieldSemantics = computed<Record<string, FieldSemanticMeta>>(() => normalizeContractFieldSemantics(
    dictOrEmpty(strictSnapshot().runtimeContract).fieldSemantics,
  ));
  const fieldSemanticMeta = (name: string) => resolveFieldSemanticMeta(
    name,
    contractFieldSemantics.value,
    strictFieldDescriptors()[name],
  );
  const coreFieldNames = computed(() => semanticFieldNamesBySurfaceRole(
    strictFieldDescriptors(), contractFieldSemantics.value, semanticFieldGroups.value, 'core',
  ));
  const advancedFieldNames = computed(() => semanticFieldNamesBySurfaceRole(
    strictFieldDescriptors(), contractFieldSemantics.value, semanticFieldGroups.value, 'advanced',
  ));
  const hasAdvancedFields = computed(() => advancedFieldNames.value.length > 0);
  const policyRequiredFields = computed(() => collectPrimaryActionRequiredFields(
    dictOrEmpty(strictSnapshot().actionContract).actionPolicies,
  ));
  const sceneReadySceneKey = computed(() => String(
    context.route.query.scene_key || context.route.params.sceneKey
    || findActionMeta(context.session.menuTree, context.actionId.value)?.scene_key
    || findActionMeta(context.session.menuTree, context.actionId.value)?.sceneKey
    || context.session.currentAction?.scene_key || context.session.currentAction?.sceneKey || '',
  ).trim());
  const sceneReadyEntry = computed<Record<string, unknown> | null>(() => {
    const entry = dictOrEmpty(strictSnapshot().runtimeContract).sceneFormAugmentations;
    return entry && typeof entry === 'object' && !Array.isArray(entry)
      ? entry as Record<string, unknown>
      : null;
  });
  const useSceneFormAugmentations = computed(() => Boolean(sceneReadyEntry.value));
  const strictContractMode = computed(() => isCoreSceneStrictMode(sceneReadySceneKey.value, sceneReadyEntry.value));
  const strictContractGuard = computed<Record<string, unknown>>(() => strictContractGuardFromSceneReadyEntry(sceneReadyEntry.value));
  const strictContractMissingSummary = computed(() => strictContractMissingSummaryFromGuard(strictContractMode.value, strictContractGuard.value));
  const strictContractDefaultsSummary = computed(() => strictContractDefaultsSummaryFromGuard(strictContractMode.value, strictContractGuard.value));
  const sceneValidationRequiredFields = computed(() => useSceneFormAugmentations.value
    ? resolveFormSceneReady(sceneReadyEntry.value).requiredFields : []);
  const sceneReadyFormSurface = computed(() => resolveFormSceneReady(useSceneFormAugmentations.value ? sceneReadyEntry.value : null));
  const validationRequiredFields = computed(() => {
    const fields = new Set<string>();
    const runtime = dictOrEmpty(strictSnapshot().runtimeContract);
    const rules = Array.isArray(runtime.validationRules) ? runtime.validationRules : [];
    rules.forEach((rule) => {
      if (!rule || typeof rule !== 'object') return;
      const item = rule as Record<string, unknown>;
      if (String(item.code || '').trim().toUpperCase() !== 'REQUIRED') return;
      const field = String(item.field || '').trim();
      const profiles = Array.isArray(item.when_profiles) ? item.when_profiles.map((value) => String(value || '').trim().toLowerCase()) : [];
      if (field && (!profiles.length || profiles.includes(context.renderProfile.value))) fields.add(field);
    });
    sceneValidationRequiredFields.value.forEach((field) => fields.add(field));
    return fields;
  });
  const sceneValidationRequiredErrorPrefix = sceneValidationErrorPrefix(ErrorCodes.SCENE_VALIDATION_REQUIRED);
  const sceneValidationPanel = computed(() => buildSceneValidationPanel({
    enabled: useSceneFormAugmentations.value, validationErrors: context.validationErrors.value,
    errorCode: ErrorCodes.SCENE_VALIDATION_REQUIRED,
    suggestedAction: resolveSceneValidationSuggestedAction({
      modelName: context.model.value, recordId: context.recordId.value, actionId: context.actionId.value,
      sceneKey: String(context.route.query.scene_key || context.route.params.sceneKey || '').trim(), roleCode: context.runtimeRoleCode.value,
    }),
  }));
  const nonSceneValidationErrors = computed(() => context.validationErrors.value.filter(
    (item) => !String(item || '').trim().startsWith(sceneValidationRequiredErrorPrefix),
  ));
  const focusValidationError = (message: string) => context.focusValidationError(message, context.layoutNodes());
  const focusFirstValidationError = async () => {
    await nextTick();
    const message = nonSceneValidationErrors.value[0] || context.validationErrors.value[0] || '';
    if (message) focusValidationError(message);
  };
  const reloadLatestRecord = async () => {
    const confirmed = await context.intentConfirmationRef.value?.confirm({
      actionLabel: '加载最新数据', message: '加载最新数据会放弃当前页面尚未保存的修改，是否继续？',
    });
    if (!confirmed) return;
    context.formConflict.value = false;
    await context.reload();
  };
  const contractVisibleFields = computed(() => {
    return resolveUnifiedPageContractV2VisibleFields(strictSnapshot());
  });
  return {
    advancedFieldNames, contractVisibleFields, coreFieldNames, fieldSemanticMeta, focusFirstValidationError,
    focusValidationError, hasAdvancedFields, nonSceneValidationErrors, policyRequiredFields, reloadLatestRecord, sceneReadyFormSurface,
    sceneValidationPanel, sceneValidationRequiredFields, strictContractDefaultsSummary, strictContractGuard,
    strictContractMissingSummary, strictContractMode, useSceneFormAugmentations, validationRequiredFields,
  };
}

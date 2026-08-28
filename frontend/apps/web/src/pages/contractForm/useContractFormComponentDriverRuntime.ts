import { computed, ref, watch } from 'vue';
import { SCENE_UI_KITS, type SceneUiKitId } from '@sc/ui/form';
import { getUserViewPreference, setUserViewPreference } from '../../api/preferences';
import { resolveContractFormComponentDriverDecision } from '../../app/renderers/sceneComponentDriverPolicy';
import { recordSceneComponentDriverEvent } from '../../app/renderers/sceneComponentDriverTelemetry';
import { sceneUiKitRef } from '../../app/renderers/globalSceneKit';
export { resolveCanonicalFormRenderState } from './canonicalFormRenderState';

export type ContractFormComponentDriverRuntimeOptions = {
  actionId: () => number;
  model: () => string;
  renderMode: () => 'create' | 'edit' | 'readonly';
  featureFlag: () => unknown;
  previewKit: () => string;
  isActive: () => boolean;
};

export function useContractFormComponentDriverRuntime(options: ContractFormComponentDriverRuntimeOptions) {
  const userKit = ref('');
  let preferenceLoadSeq = 0;
  let loadedPreferenceKey = '';
  const preferenceScope = computed(() => ({
    action_id: options.actionId() || undefined,
    model: options.model(),
    view_type: 'form',
    preference_key: 'scene_ui_driver',
  }));
  const decision = computed(() => resolveContractFormComponentDriverDecision({
    featureFlag: options.featureFlag(),
    actionId: options.actionId(),
    model: options.model(),
    renderMode: options.renderMode(),
    userKit: userKit.value,
    previewKit: options.previewKit(),
  }));
  const driverConfig = computed(() => {
    const flagEligible = options.isActive() && decision.value.eligible;
    const allowedKits: SceneUiKitId[] = flagEligible
      ? [...decision.value.policy.allowedKits]
      : ['tdesign-modern', 'sc-native'];
    const allowOverride = options.isActive()
      && (flagEligible ? (decision.value.allowUserOverride && !decision.value.policy.lockedKit) : true)
      && allowedKits.length > 1;
    const activeKit: SceneUiKitId = (() => {
      if (!options.isActive()) return sceneUiKitRef.value;
      if (flagEligible) return decision.value.resolution.kit;
      const preferred = userKit.value as SceneUiKitId;
      return preferred && allowedKits.includes(preferred) ? preferred : sceneUiKitRef.value;
    })();
    return {
      activeKit,
      allowedKits,
      allowUserOverride: allowOverride,
      showUserDriverChooser: allowOverride,
      resolutionSource: flagEligible ? decision.value.resolution.source : 'user-preference',
      reasonCode: flagEligible ? decision.value.reasonCode : 'SCENE_DRIVER_FEATURE_DISABLED_FALLBACK',
    };
  });

  async function loadPreference(): Promise<void> {
    const seq = ++preferenceLoadSeq;
    const scope = preferenceScope.value;
    if (!options.isActive() || !driverConfig.value.allowUserOverride || !scope.action_id || !scope.model) {
      userKit.value = '';
      return;
    }
    const preferenceKey = `${scope.action_id}|${scope.model}|${scope.view_type}|${scope.preference_key}`;
    if (preferenceKey === loadedPreferenceKey) return;
    loadedPreferenceKey = preferenceKey;
    userKit.value = '';
    try {
      const result = await getUserViewPreference(scope);
      if (seq === preferenceLoadSeq) userKit.value = String(result.preference?.kit || '').trim();
    } catch (error) {
      if (seq === preferenceLoadSeq) {
        userKit.value = '';
        loadedPreferenceKey = '';
      }
      console.warn('[contract-form-driver] failed to load preference', error);
    }
  }

  async function changeDriver(kit: SceneUiKitId): Promise<void> {
    const cfg = driverConfig.value;
    if (!cfg.allowUserOverride || !cfg.allowedKits.includes(kit)) return;
    userKit.value = kit;
    try {
      await setUserViewPreference(preferenceScope.value, { kit });
      recordSceneComponentDriverEvent({
        timestamp: Date.now(), actionId: options.actionId(), model: options.model(), requestedKit: kit,
        resolvedKit: driverConfig.value.activeKit, source: driverConfig.value.resolutionSource, reasonCode: driverConfig.value.reasonCode,
      });
    } catch (error) {
      userKit.value = '';
      console.warn('[contract-form-driver] failed to save preference', error);
    }
  }

  watch(
    () => [options.isActive(), options.renderMode(), preferenceScope.value.action_id || 0, preferenceScope.value.model || '', JSON.stringify(options.featureFlag() || {})].join('|'),
    () => { void loadPreference(); },
    { immediate: true },
  );
  watch(
    () => [options.actionId(), options.model(), options.renderMode(), decision.value.eligible, decision.value.resolution.kit, decision.value.reasonCode].join('|'),
    () => {
      if (!options.isActive()) return;
      recordSceneComponentDriverEvent({
        timestamp: Date.now(), actionId: options.actionId(), model: options.model(),
        requestedKit: userKit.value || options.previewKit(), resolvedKit: driverConfig.value.activeKit,
        source: decision.value.resolution.source, reasonCode: decision.value.reasonCode,
      });
    },
    { immediate: true },
  );

  return { driverConfig, changeDriver, kitLabel: (kit: SceneUiKitId) => SCENE_UI_KITS[kit]?.label || kit };
}

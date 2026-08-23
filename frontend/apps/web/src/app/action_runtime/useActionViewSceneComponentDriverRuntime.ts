import { computed, ref, watch } from 'vue';
import type { SceneUiKitId } from '@sc/ui';
import { getUserViewPreference, setUserViewPreference, type UserViewPreferenceScope } from '../../api/preferences';
import type { ActionCollectionPresentation } from '../contracts/actionViewSurfaceContract';
import { resolveActionSurfaceRenderer } from '../renderers/actionSurfaceRendererRegistry';
import { resolveSceneComponentDriverDecision } from '../renderers/sceneComponentDriverPolicy';
import { recordSceneComponentDriverEvent } from '../renderers/sceneComponentDriverTelemetry';
import { resolveSceneReadonlyCollectionBridge } from '../renderers/sceneReadonlyCollectionBridge';

type Dict = Record<string, unknown>;

export type ActionViewSceneComponentDriverRuntimeOptions = {
  actionContract: () => unknown;
  records: () => Dict[];
  columnLabels: () => Record<string, string>;
  totalCount: () => number;
  actionId: () => number;
  model: () => string;
  sceneKey: () => string;
  viewMode: () => string;
  menuTitle: () => string;
  actionName: () => string;
  companyName: () => string;
  roleName: () => string;
  featureFlag: () => unknown;
  previewKit: () => string;
  preferenceScope: () => UserViewPreferenceScope;
  collectionPresentation: () => ActionCollectionPresentation;
};

export function useActionViewSceneComponentDriverRuntime(
  options: ActionViewSceneComponentDriverRuntimeOptions,
) {
  const userKit = ref('');
  let preferenceLoadSeq = 0;

  const preferenceScope = computed<UserViewPreferenceScope>(() => ({
    ...options.preferenceScope(),
    preference_key: 'scene_ui_driver',
  }));
  const bridge = computed(() => resolveSceneReadonlyCollectionBridge({
    actionContract: options.actionContract(),
    records: options.records(),
    columnLabels: options.columnLabels(),
    totalCount: options.totalCount(),
    identity: {
      productName: '企业业务管理平台',
      companyName: options.companyName(),
      roleName: options.roleName(),
      breadcrumbs: [options.menuTitle()].filter(Boolean),
      workTabs: [],
    },
    description: options.menuTitle() || options.actionName(),
  }));
  const decision = computed(() => resolveSceneComponentDriverDecision({
    featureFlag: options.featureFlag(),
    actionId: options.actionId(),
    model: options.model(),
    sceneKey: options.sceneKey() || bridge.value.sceneKey,
    viewMode: options.viewMode(),
    pageAuth: bridge.value.pageAuth,
    hasMutationActions: bridge.value.hasMutationActions,
    selectionEnabled: bridge.value.selectionEnabled,
    userKit: userKit.value,
    previewKit: options.previewKit(),
  }));
  const surfaceRendererDescriptor = computed(() => {
    const currentBridge = bridge.value;
    const currentDecision = decision.value;
    const contractError = Boolean(options.actionContract()) && currentDecision.targeted && (
      currentBridge.reasonCode === 'SCENE_DRIVER_NORMALIZED_V2_MISSING'
      || (
        currentBridge.reasonCode === 'SCENE_DRIVER_NORMALIZED_ADAPTER_REJECTED'
        && !currentBridge.hasMutationActions
        && !currentBridge.selectionEnabled
      )
    );
    return resolveActionSurfaceRenderer(options.collectionPresentation(), options.viewMode(), {
      eligible: currentBridge.ok && currentDecision.eligible,
      contractError,
      reasonCode: currentBridge.ok ? currentDecision.reasonCode : currentBridge.reasonCode,
      config: currentBridge.contract ? {
        contract: currentBridge.contract,
        activeKit: currentDecision.resolution.kit,
        allowedKits: currentDecision.policy.allowedKits,
        allowUserOverride: false,
        resolutionSource: currentDecision.resolution.source,
      } : {},
    });
  });

  async function loadPreference(): Promise<void> {
    const seq = ++preferenceLoadSeq;
    const scope = preferenceScope.value;
    if (!decision.value.allowUserOverride || (!scope.action_id && !scope.model)) {
      userKit.value = '';
      return;
    }
    try {
      const result = await getUserViewPreference(scope);
      if (seq === preferenceLoadSeq) userKit.value = String(result.preference?.kit || '').trim();
    } catch (err) {
      if (seq === preferenceLoadSeq) userKit.value = '';
      console.warn('[scene-driver] failed to load preference', err);
    }
  }

  async function handleSceneDriverChange(kitRaw: string): Promise<void> {
    const kit = String(kitRaw || '').trim() as SceneUiKitId;
    const before = decision.value;
    if (!before.allowUserOverride || !before.policy.allowedKits.includes(kit)) return;
    userKit.value = kit;
    try {
      await setUserViewPreference(preferenceScope.value, { kit });
      const after = decision.value;
      recordSceneComponentDriverEvent({
        timestamp: Date.now(), actionId: options.actionId(), model: options.model(), requestedKit: kit,
        resolvedKit: after.resolution.kit, source: after.resolution.source, reasonCode: after.reasonCode,
      });
    } catch (err) {
      userKit.value = '';
      console.warn('[scene-driver] failed to save preference', err);
    }
  }

  watch(
    () => [preferenceScope.value.action_id || 0, preferenceScope.value.model || '', JSON.stringify(options.featureFlag() || {})].join('|'),
    () => { void loadPreference(); },
    { immediate: true },
  );
  watch(
    () => [options.actionId(), options.model(), bridge.value.ok ? 'bridge-ok' : bridge.value.reasonCode,
      decision.value.eligible ? 'eligible' : decision.value.reasonCode, decision.value.resolution.kit,
      decision.value.resolution.source].join('|'),
    () => {
      const currentBridge = bridge.value;
      const currentDecision = decision.value;
      recordSceneComponentDriverEvent({
        timestamp: Date.now(), actionId: options.actionId(), model: options.model(),
        requestedKit: userKit.value || options.previewKit(), resolvedKit: currentDecision.resolution.kit,
        source: currentDecision.resolution.source,
        reasonCode: currentBridge.ok ? currentDecision.reasonCode : currentBridge.reasonCode,
      });
    },
    { immediate: true },
  );

  return { surfaceRendererDescriptor, handleSceneDriverChange };
}

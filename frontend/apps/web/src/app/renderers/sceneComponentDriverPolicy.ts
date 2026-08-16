import {
  isSceneUiKitAllowed,
  resolveSceneUiPreference,
  type SceneUiKitId,
  type SceneUiPreferencePolicy,
  type SceneUiPreferenceResolution,
} from '@sc/ui/bridge';

type Dict = Record<string, unknown>;

export type SceneComponentDriverDecision = {
  eligible: boolean;
  targeted: boolean;
  reasonCode: string;
  policy: SceneUiPreferencePolicy;
  resolution: SceneUiPreferenceResolution;
  allowUserOverride: boolean;
};

export type SceneComponentDriverContext = {
  featureFlag: unknown;
  actionId: number;
  model: string;
  sceneKey: string;
  viewMode: string;
  pageAuth: string;
  hasMutationActions: boolean;
  selectionEnabled: boolean;
  userKit?: string | null;
  previewKit?: string | null;
};

const SAFE_POLICY: SceneUiPreferencePolicy = Object.freeze({
  allowedKits: ['sc-native'],
  systemDefaultKit: 'sc-native',
  allowUserOverride: false,
  allowPreviewOverride: false,
});

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Dict : {};
}

function textList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.map((item) => String(item || '').trim()).filter(Boolean))];
}

function positiveIntegerList(value: unknown): number[] {
  return textList(value)
    .map((item) => Number(item))
    .filter((item) => Number.isInteger(item) && item > 0);
}

function sceneKitList(value: unknown): SceneUiKitId[] {
  const candidatePolicy: SceneUiPreferencePolicy = {
    allowedKits: ['sc-native', 'tdesign-modern', 'ui5-horizon'],
    systemDefaultKit: 'sc-native',
  };
  return textList(value).filter((item): item is SceneUiKitId => isSceneUiKitAllowed(candidatePolicy, item));
}

function denied(reasonCode: string, targeted = false): SceneComponentDriverDecision {
  return {
    eligible: false,
    targeted,
    reasonCode,
    policy: SAFE_POLICY,
    resolution: { kit: 'sc-native', source: 'safe-default' },
    allowUserOverride: false,
  };
}

export function resolveSceneComponentDriverDecision(
  context: SceneComponentDriverContext,
): SceneComponentDriverDecision {
  const flag = asDict(context.featureFlag);
  if (flag.enabled !== true) return denied('SCENE_DRIVER_POLICY_DISABLED');
  if (flag.read_only_only !== true) return denied('SCENE_DRIVER_POLICY_NOT_READONLY_ONLY');
  if (!['tree', 'list'].includes(String(context.viewMode || '').trim().toLowerCase())) {
    return denied('SCENE_DRIVER_VIEW_UNSUPPORTED');
  }
  const actionIds = positiveIntegerList(flag.action_ids);
  const models = textList(flag.models);
  const sceneKeys = textList(flag.scene_keys);
  if (!actionIds.length && !models.length && !sceneKeys.length) {
    return denied('SCENE_DRIVER_SCOPE_EMPTY');
  }
  const scopeMatched = (
    (context.actionId > 0 && actionIds.includes(context.actionId))
    || (Boolean(context.model) && models.includes(context.model))
    || (Boolean(context.sceneKey) && sceneKeys.includes(context.sceneKey))
  );
  if (!scopeMatched) return denied('SCENE_DRIVER_SCOPE_MISMATCH');

  const allowedKits = sceneKitList(flag.allowed_kits);
  if (!allowedKits.length || !allowedKits.includes('sc-native')) {
    return denied('SCENE_DRIVER_ALLOWED_KITS_INVALID', true);
  }
  if (!['read', 'readonly'].includes(String(context.pageAuth || '').trim().toLowerCase())) {
    return denied('SCENE_DRIVER_PAGE_NOT_READONLY', true);
  }
  if (context.hasMutationActions) return denied('SCENE_DRIVER_MUTATION_ACTION_PRESENT', true);
  if (context.selectionEnabled) return denied('SCENE_DRIVER_SELECTION_PRESENT', true);
  const policy: SceneUiPreferencePolicy = {
    allowedKits,
    systemDefaultKit: String(flag.system_default_kit || 'sc-native') as SceneUiKitId,
    organizationDefaultKit: String(flag.organization_default_kit || '') as SceneUiKitId || undefined,
    lockedKit: String(flag.locked_kit || '') as SceneUiKitId || undefined,
    allowUserOverride: flag.allow_user_override === true,
    allowPreviewOverride: flag.allow_preview_override === true,
  };
  const resolution = resolveSceneUiPreference({
    policy,
    userKit: context.userKit,
    previewKit: context.previewKit,
  });
  return {
    eligible: true,
    targeted: true,
    reasonCode: '',
    policy,
    resolution,
    allowUserOverride: policy.allowUserOverride === true && !policy.lockedKit,
  };
}

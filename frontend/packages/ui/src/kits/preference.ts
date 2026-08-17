import { SCENE_UI_KITS, type SceneUiKitId } from './types';

export interface SceneUiPreferencePolicy {
  allowedKits: readonly SceneUiKitId[];
  systemDefaultKit: SceneUiKitId;
  organizationDefaultKit?: SceneUiKitId;
  lockedKit?: SceneUiKitId;
  allowUserOverride?: boolean;
  allowPreviewOverride?: boolean;
}

export interface SceneUiPreferenceInput {
  policy: SceneUiPreferencePolicy;
  previewKit?: string | null;
  userKit?: string | null;
}

export interface SceneUiPreferenceResolution {
  kit: SceneUiKitId;
  source:
    | 'organization-lock'
    | 'preview'
    | 'user'
    | 'organization-default'
    | 'system-default'
    | 'safe-default';
}

export function isSceneUiKitId(value: string | null | undefined): value is SceneUiKitId {
  return Boolean(value && Object.prototype.hasOwnProperty.call(SCENE_UI_KITS, value));
}

export function isSceneUiKitAllowed(policy: SceneUiPreferencePolicy, value: string | null | undefined): value is SceneUiKitId {
  return isSceneUiKitId(value) && policy.allowedKits.includes(value);
}

export function resolveSceneUiPreference(input: SceneUiPreferenceInput): SceneUiPreferenceResolution {
  const { policy } = input;
  if (isSceneUiKitAllowed(policy, policy.lockedKit)) {
    return { kit: policy.lockedKit, source: 'organization-lock' };
  }
  if (policy.allowPreviewOverride && isSceneUiKitAllowed(policy, input.previewKit)) {
    return { kit: input.previewKit, source: 'preview' };
  }
  if (policy.allowUserOverride !== false && isSceneUiKitAllowed(policy, input.userKit)) {
    return { kit: input.userKit, source: 'user' };
  }
  if (isSceneUiKitAllowed(policy, policy.organizationDefaultKit)) {
    return { kit: policy.organizationDefaultKit, source: 'organization-default' };
  }
  if (isSceneUiKitAllowed(policy, policy.systemDefaultKit)) {
    return { kit: policy.systemDefaultKit, source: 'system-default' };
  }
  return { kit: 'sc-native', source: 'safe-default' };
}

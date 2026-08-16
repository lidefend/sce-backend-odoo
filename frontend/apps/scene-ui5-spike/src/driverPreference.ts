import {
  isSceneUiKitAllowed,
  isSceneDesignTokenProfileId,
  resolveSceneUiPreference,
  type SceneDesignTokenProfileId,
  type SceneUiKitId,
  type SceneUiPreferencePolicy,
  type SceneUiPreferenceResolution,
} from '@sc/ui';

const STORAGE_KEY = 'sc.scene.ui.driver';
const TOKEN_STORAGE_KEY = 'sc.scene.ui.tokens';
export const LAB_DRIVER_POLICY: SceneUiPreferencePolicy = {
  allowedKits: ['sc-native', 'tdesign-modern', 'ui5-horizon'],
  systemDefaultKit: 'sc-native',
  allowPreviewOverride: true,
  allowUserOverride: true,
};

export function readDriverPreference(): SceneUiPreferenceResolution {
  const query = new URLSearchParams(window.location.search);
  const organizationKit = query.get('organizationKit') || undefined;
  const systemKit = query.get('systemKit') || LAB_DRIVER_POLICY.systemDefaultKit;
  const lockedKit = query.get('lockedKit') || undefined;
  const policy: SceneUiPreferencePolicy = {
    ...LAB_DRIVER_POLICY,
    organizationDefaultKit: organizationKit as SceneUiKitId | undefined,
    systemDefaultKit: systemKit as SceneUiKitId,
    lockedKit: lockedKit as SceneUiKitId | undefined,
  };
  return resolveSceneUiPreference({
    policy,
    previewKit: query.get('kit'),
    userKit: window.localStorage.getItem(STORAGE_KEY),
  });
}

export function writeDriverPreference(value: SceneUiKitId): void {
  if (!isSceneUiKitAllowed(LAB_DRIVER_POLICY, value) || LAB_DRIVER_POLICY.lockedKit) return;
  window.localStorage.setItem(STORAGE_KEY, value);
  const url = new URL(window.location.href);
  url.searchParams.set('kit', value);
  window.history.replaceState(null, '', url);
}

export function readTokenProfile(): SceneDesignTokenProfileId {
  const preview = new URLSearchParams(window.location.search).get('tokens');
  if (isSceneDesignTokenProfileId(preview)) return preview;
  const stored = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  return isSceneDesignTokenProfileId(stored) ? stored : 'enterprise-neutral';
}

export function writeTokenProfile(value: SceneDesignTokenProfileId): void {
  if (!isSceneDesignTokenProfileId(value)) return;
  window.localStorage.setItem(TOKEN_STORAGE_KEY, value);
  const url = new URL(window.location.href);
  url.searchParams.set('tokens', value);
  window.history.replaceState(null, '', url);
}

import { computed, readonly, ref } from 'vue';
import type { TDesignGlobalConfigProvider } from '../components/design-system/tdesignPrimitiveBridge';

const THEME_KEY = 'sc_theme';
const THEME_PROFILE_KEY = 'sc_theme_profile';
const SYSTEM_DARK_QUERY = '(prefers-color-scheme: dark)';
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
const TD_ANIMATIONS = ['ripple', 'expand', 'fade'] as const;

const reducedMotionState = ref(false);
let stopThemeRuntimeWatch: (() => void) | null = null;

export const reducedMotion = readonly(reducedMotionState);
export const tdesignGlobalConfig = computed<TDesignGlobalConfigProvider>(() => reducedMotionState.value
  ? { animation: { include: [], exclude: [...TD_ANIMATIONS] } }
  : {});

export type ScTheme = 'light' | 'dark' | 'system';

/** Orthogonal, runtime-switchable style profile. Drives semantic brand /
 * emphasis / border / radius tokens; independent of the light/dark mode. */
export type ScThemeProfile = 'enterprise-neutral' | 'business-soft' | 'accessible-contrast';

export const SCENE_THEME_PROFILES: ReadonlyArray<{ id: ScThemeProfile; label: string; description: string }> = [
  { id: 'enterprise-neutral', label: '企业中性', description: '清晰、克制的企业业务默认主题。' },
  { id: 'business-soft', label: '柔和商务', description: '降低边界锐度，适合长时间数据办理。' },
  { id: 'accessible-contrast', label: '高对比', description: '强化文字、边界和焦点，服务低视力与键盘用户。' },
];

export function isSceneThemeProfile(value: string | null | undefined): value is ScThemeProfile {
  return value === 'enterprise-neutral' || value === 'business-soft' || value === 'accessible-contrast';
}

function resolveSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light';
  return window.matchMedia(SYSTEM_DARK_QUERY).matches ? 'dark' : 'light';
}

export function applyTheme(theme: ScTheme): void {
  const root = document.documentElement;
  const resolved = theme === 'system' ? resolveSystemTheme() : theme;
  root.setAttribute('data-sc-theme-mode', theme);
  root.setAttribute('data-sc-theme-resolved', resolved);
  root.setAttribute('data-sc-theme', resolved);
  root.style.colorScheme = resolved;
}

function applyReducedMotion(reduced: boolean): void {
  reducedMotionState.value = reduced;
  document.documentElement.setAttribute('data-sc-reduced-motion', reduced ? 'reduce' : 'no-preference');
}

/** Register the application-lifetime media listeners exactly once.
 * App.vue is the common root for login, shell and embedded routes, so route
 * changes must never own or duplicate these listeners. */
export function ensureThemeRuntimeWatch(): () => void {
  if (stopThemeRuntimeWatch) return stopThemeRuntimeWatch;
  if (typeof window === 'undefined' || !window.matchMedia) return () => {};
  const darkMedia = window.matchMedia(SYSTEM_DARK_QUERY);
  const motionMedia = window.matchMedia(REDUCED_MOTION_QUERY);
  const syncTheme = () => {
    if (document.documentElement.getAttribute('data-sc-theme-mode') === 'system') applyTheme('system');
  };
  const syncMotion = () => applyReducedMotion(motionMedia.matches);
  darkMedia.addEventListener('change', syncTheme);
  motionMedia.addEventListener('change', syncMotion);
  syncMotion();
  stopThemeRuntimeWatch = () => {
    darkMedia.removeEventListener('change', syncTheme);
    motionMedia.removeEventListener('change', syncMotion);
    stopThemeRuntimeWatch = null;
  };
  return stopThemeRuntimeWatch;
}

export function stopThemeRuntime(): void {
  stopThemeRuntimeWatch?.();
}

export function bootTheme(): void {
  let theme: ScTheme = 'system';
  try {
    const stored = localStorage.getItem(THEME_KEY) as ScTheme | null;
    if (stored === 'light' || stored === 'dark' || stored === 'system') theme = stored;
  } catch {
    theme = 'system';
  }
  applyTheme(theme);
  ensureThemeRuntimeWatch();
}

export function nextTheme(current: ScTheme): ScTheme {
  if (current === 'system') return 'light';
  if (current === 'light') return 'dark';
  return 'system';
}

export function persistTheme(theme: ScTheme): void {
  try { localStorage.setItem(THEME_KEY, theme); } catch { /* ignore storage failures */ }
  applyTheme(theme);
}

export function applyThemeProfile(profile: ScThemeProfile): void {
  document.documentElement.setAttribute('data-sc-theme-profile', profile);
}

export function bootThemeProfile(): ScThemeProfile {
  let profile: ScThemeProfile = 'enterprise-neutral';
  try {
    const stored = localStorage.getItem(THEME_PROFILE_KEY);
    if (isSceneThemeProfile(stored)) profile = stored;
  } catch {
    profile = 'enterprise-neutral';
  }
  applyThemeProfile(profile);
  return profile;
}

export function nextThemeProfile(current: ScThemeProfile): ScThemeProfile {
  const ids = SCENE_THEME_PROFILES.map((p) => p.id);
  const index = ids.indexOf(current);
  return ids[(index + 1) % ids.length];
}

export function persistThemeProfile(profile: ScThemeProfile): void {
  try { localStorage.setItem(THEME_PROFILE_KEY, profile); } catch { /* ignore storage failures */ }
  applyThemeProfile(profile);
}

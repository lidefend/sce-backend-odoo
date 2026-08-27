const THEME_KEY = 'sc_theme';
const THEME_PROFILE_KEY = 'sc_theme_profile';

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
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function applyTheme(theme: ScTheme): void {
  const root = document.documentElement;
  const resolved = theme === 'system' ? resolveSystemTheme() : theme;
  root.setAttribute('data-sc-theme-mode', theme);
  root.setAttribute('data-sc-theme-resolved', resolved);
  root.setAttribute('data-sc-theme', resolved);
  root.style.colorScheme = resolved;
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

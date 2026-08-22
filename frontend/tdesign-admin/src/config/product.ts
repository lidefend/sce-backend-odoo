import { reactive, readonly } from 'vue';

export interface ProductBrandConfig {
  appName: string;
  subtitle: string;
}

interface RuntimeAppConfig {
  appName?: string;
  subtitle?: string;
}

declare global {
  interface Window {
    __APP_CONFIG__?: RuntimeAppConfig;
  }
}

export const DEFAULT_APP_NAME = '智能施工管理系统';

const initialRuntimeConfig = typeof window === 'undefined' ? undefined : window.__APP_CONFIG__;
const state = reactive<ProductBrandConfig>({
  appName:
    normalizeText(initialRuntimeConfig?.appName) || normalizeText(import.meta.env.VITE_APP_NAME) || DEFAULT_APP_NAME,
  subtitle: normalizeText(initialRuntimeConfig?.subtitle),
});

export const productBrand = readonly(state);

export function updateProductBrand(config: Partial<ProductBrandConfig>) {
  state.appName = normalizeText(config.appName) || state.appName || DEFAULT_APP_NAME;
  state.subtitle = normalizeText(config.subtitle) || state.subtitle;
  syncDocumentTitle();
}

export function applyProductBrandFromSystemInit(payload: Record<string, unknown>) {
  const extFacts = asRecord(payload.ext_facts);
  const pageProfile = asRecord(extFacts.page_profile_overrides);
  const pageTexts = asRecord(pageProfile.page_texts);
  const loginTexts = asRecord(pageTexts.login);
  const startupBrand = asRecord(extFacts.branding);
  const runtimeBrand = asRecord(payload.brand);

  updateProductBrand({
    appName:
      normalizeText(runtimeBrand.name) ||
      normalizeText(startupBrand.app_name) ||
      normalizeText(loginTexts.brand_name),
    subtitle:
      normalizeText(runtimeBrand.subtitle) ||
      normalizeText(startupBrand.subtitle) ||
      normalizeText(loginTexts.brand_subtitle),
  });
}

export function syncDocumentTitle(pageTitle = '') {
  if (typeof document === 'undefined') return;
  const normalizedPageTitle = normalizeText(pageTitle);
  document.title = normalizedPageTitle ? `${normalizedPageTitle} - ${state.appName}` : state.appName;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function normalizeText(value: unknown) {
  return typeof value === 'string' ? value.trim() : '';
}

syncDocumentTitle();

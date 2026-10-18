import { runtimeOdooDb, runtimeOdooDbLocked } from './runtimeConfig';

const DB_SCOPE = String(import.meta.env.VITE_APP_ENV || 'default').trim() || 'default';
const ACTIVE_DB_STORAGE_KEY = `sc_active_db:${DB_SCOPE}`;
// Batch C: the entry contract (runtime-config.js) is the only build-external
// source that may name a database, and even that is display/local state.  A
// build-time database variable is not an authority.
const ENV_DB = runtimeOdooDb;
const ENV_DB_LOCKED = runtimeOdooDbLocked;

function normalizeDb(value: unknown): string {
  const db = String(value || '').trim();
  return db;
}

export function isPlatformAdminEntryRuntime(): boolean {
  if (typeof window === 'undefined') return false;
  const params = new URLSearchParams(window.location.search);
  return window.location.pathname.startsWith('/platform-admin') || params.get('platform_admin') === '1';
}

function readDbFromStorage(): string {
  if (typeof window === 'undefined') return '';
  const sessionDb = normalizeDb(sessionStorage.getItem(ACTIVE_DB_STORAGE_KEY));
  if (sessionDb) {
    return sessionDb;
  }
  const localDb = normalizeDb(localStorage.getItem(ACTIVE_DB_STORAGE_KEY));
  return localDb;
}

export function resolveActiveDb(fallbackDb = ''): string {
  // Batch C: a database query parameter is never a selector.  Only a value the server
  // already confirmed in this tab (or a build-time local default) is used, and
  // it never travels back to the server as a hint.
  return readDbFromStorage() || normalizeDb(fallbackDb);
}

export function resolveConfiguredDb(fallbackDb = ''): string {
  const envDb = ENV_DB;
  if (ENV_DB_LOCKED) {
    return envDb;
  }
  return resolveActiveDb(envDb || fallbackDb);
}

export function isConfiguredDbPinned(): boolean {
  return ENV_DB_LOCKED;
}

export function setActiveDb(db: string): void {
  const normalized = normalizeDb(db);
  if (!normalized || typeof window === 'undefined') return;
  sessionStorage.setItem(ACTIVE_DB_STORAGE_KEY, normalized);
  localStorage.setItem(ACTIVE_DB_STORAGE_KEY, normalized);
}

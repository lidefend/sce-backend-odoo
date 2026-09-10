import { normalizeLegacyWorkbenchPath } from './routeQuery';

const SESSION_EXPIRED_RETURN_PATH_KEY = 'sc.session_expired.return_path.v1';
const MAX_RETURN_PATH_LENGTH = 4096;
const AUTH_ENTRY_PATHS = new Set([
  '/login',
  '/platform-admin/login',
  '/activate-account',
  '/password-recovery',
]);

type SessionStorageLike = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;
type SessionExpiredNavigationRuntime = {
  location: Pick<Location, 'pathname' | 'search' | 'hash'> & { assign: (url: string) => void };
  sessionStorage: SessionStorageLike;
};

let sessionExpiredRedirectScheduled = false;

function browserRuntime(): SessionExpiredNavigationRuntime | null {
  if (typeof window === 'undefined') return null;
  return {
    location: window.location,
    sessionStorage: window.sessionStorage,
  };
}

function containsUnsafeEncoding(path: string): boolean {
  if (path.includes('\\') || /[\u0000-\u001f\u007f]/.test(path)) return true;
  try {
    const decoded = decodeURIComponent(path);
    return decoded.startsWith('//') || decoded.includes('\\') || /[\u0000-\u001f\u007f]/.test(decoded);
  } catch {
    return true;
  }
}

function isAuthEntryPath(pathname: string): boolean {
  return AUTH_ENTRY_PATHS.has(String(pathname || '').replace(/\/+$/, '') || '/');
}

export function normalizeSafeLoginReturnPath(rawPath: unknown): string {
  const candidate = String(rawPath || '').trim();
  if (!candidate || candidate.length > MAX_RETURN_PATH_LENGTH) return '';
  if (!candidate.startsWith('/') || candidate.startsWith('//') || containsUnsafeEncoding(candidate)) return '';

  let parsed: URL;
  try {
    parsed = new URL(candidate, 'https://sce.invalid');
  } catch {
    return '';
  }
  if (parsed.origin !== 'https://sce.invalid' || isAuthEntryPath(parsed.pathname)) return '';

  const normalized = normalizeLegacyWorkbenchPath(`${parsed.pathname}${parsed.search}${parsed.hash}`);
  const isUnboundActionRoute = /^\/(f|a|r)\//.test(normalized)
    && !/[?&](action_id|menu_id|scene_key|scene)=/.test(normalized);
  return isUnboundActionRoute ? '' : normalized;
}

export function rememberSessionExpiredReturnPath(
  rawPath: unknown,
  storage: SessionStorageLike | null = browserRuntime()?.sessionStorage || null,
): boolean {
  const returnPath = normalizeSafeLoginReturnPath(rawPath);
  if (!returnPath || !storage) return false;
  try {
    storage.setItem(SESSION_EXPIRED_RETURN_PATH_KEY, returnPath);
    return true;
  } catch {
    return false;
  }
}

export function readSessionExpiredReturnPath(
  storage: SessionStorageLike | null = browserRuntime()?.sessionStorage || null,
): string {
  if (!storage) return '';
  try {
    return normalizeSafeLoginReturnPath(storage.getItem(SESSION_EXPIRED_RETURN_PATH_KEY));
  } catch {
    return '';
  }
}

export function clearSessionExpiredReturnPath(
  storage: SessionStorageLike | null = browserRuntime()?.sessionStorage || null,
): void {
  if (!storage) return;
  try {
    storage.removeItem(SESSION_EXPIRED_RETURN_PATH_KEY);
  } catch {
    // Storage denial must not block a successful login or its safe fallback.
  }
}

export function redirectForExpiredSession(
  runtime: SessionExpiredNavigationRuntime | null = browserRuntime(),
): boolean {
  if (!runtime || sessionExpiredRedirectScheduled || isAuthEntryPath(runtime.location.pathname)) return false;
  sessionExpiredRedirectScheduled = true;
  rememberSessionExpiredReturnPath(
    `${runtime.location.pathname}${runtime.location.search}${runtime.location.hash}`,
    runtime.sessionStorage,
  );
  runtime.location.assign('/login?reason=session_expired');
  return true;
}

export function resetSessionExpiredRedirectForTest(): void {
  sessionExpiredRedirectScheduled = false;
}

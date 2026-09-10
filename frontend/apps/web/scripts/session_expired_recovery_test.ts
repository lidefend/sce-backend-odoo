import assert from 'node:assert/strict';
import {
  clearSessionExpiredReturnPath,
  normalizeSafeLoginReturnPath,
  readSessionExpiredReturnPath,
  redirectForExpiredSession,
  rememberSessionExpiredReturnPath,
  resetSessionExpiredRedirectForTest,
} from '../src/app/sessionExpiredRecovery';

class MemoryStorage {
  readonly values = new Map<string, string>();
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
  removeItem(key: string) { this.values.delete(key); }
}

let assertions = 0;
function equal(actual: unknown, expected: unknown, message?: string) {
  assertions += 1;
  assert.equal(actual, expected, message);
}

function doesNotThrow(callback: () => void, message?: string) {
  assertions += 1;
  assert.doesNotThrow(callback, message);
}

equal(normalizeSafeLoginReturnPath('/a/42?menu_id=9&search=abc#details'), '/a/42?menu_id=9&search=abc#details');
equal(normalizeSafeLoginReturnPath('/workbench?scene=workspace.home&tab=todo'), '/s/workspace.home?tab=todo');
equal(normalizeSafeLoginReturnPath('/r/payment.request/7?action_id=42'), '/r/payment.request/7?action_id=42');
equal(normalizeSafeLoginReturnPath('/r/payment.request/7'), '', 'unbound record routes must not bypass route authority');
equal(normalizeSafeLoginReturnPath('https://outside.invalid/a/42'), '');
equal(normalizeSafeLoginReturnPath('//outside.invalid/a/42'), '');
equal(normalizeSafeLoginReturnPath('/%2foutside.invalid'), '');
equal(normalizeSafeLoginReturnPath('/login?redirect=/a/42'), '');
equal(normalizeSafeLoginReturnPath('/platform-admin/login'), '');
equal(normalizeSafeLoginReturnPath(`/${'x'.repeat(4096)}`), '');

const storage = new MemoryStorage();
equal(rememberSessionExpiredReturnPath('/a/42?menu_id=9', storage), true);
equal(readSessionExpiredReturnPath(storage), '/a/42?menu_id=9');
clearSessionExpiredReturnPath(storage);
equal(readSessionExpiredReturnPath(storage), '');
equal(rememberSessionExpiredReturnPath('javascript:alert(1)', storage), false);

const assigned: string[] = [];
const runtime = {
  location: {
    pathname: '/a/42',
    search: '?menu_id=9&search=abc',
    hash: '#details',
    assign: (url: string) => assigned.push(url),
  },
  sessionStorage: storage,
};
resetSessionExpiredRedirectForTest();
equal(redirectForExpiredSession(runtime), true);
equal(redirectForExpiredSession(runtime), false, 'parallel 401 responses must schedule one redirect');
equal(assigned.length, 1);
equal(assigned[0], '/login?reason=session_expired');
equal(readSessionExpiredReturnPath(storage), '/a/42?menu_id=9&search=abc#details');

resetSessionExpiredRedirectForTest();
runtime.location.pathname = '/login';
equal(redirectForExpiredSession(runtime), false, 'login requests must not redirect recursively');
resetSessionExpiredRedirectForTest();
runtime.location.pathname = '/platform-admin/login';
equal(redirectForExpiredSession(runtime), false, 'platform administrator login must not redirect to the regular login');

for (const authEntry of ['/activate-account', '/password-recovery']) {
  resetSessionExpiredRedirectForTest();
  runtime.location.pathname = authEntry;
  equal(redirectForExpiredSession(runtime), false, `${authEntry} must not redirect recursively`);
}

const deniedStorage = {
  getItem: () => { throw new Error('storage read denied'); },
  setItem: () => { throw new Error('storage write denied'); },
  removeItem: () => { throw new Error('storage removal denied'); },
};
equal(rememberSessionExpiredReturnPath('/my-work', deniedStorage), false, 'storage write denial must degrade safely');
equal(readSessionExpiredReturnPath(deniedStorage), '', 'storage read denial must produce no recovery target');
doesNotThrow(() => clearSessionExpiredReturnPath(deniedStorage), 'storage removal denial must not block login completion');

const deniedStorageAssigned: string[] = [];
resetSessionExpiredRedirectForTest();
equal(redirectForExpiredSession({
  location: {
    pathname: '/my-work',
    search: '',
    hash: '',
    assign: (url: string) => deniedStorageAssigned.push(url),
  },
  sessionStorage: deniedStorage,
}), true, 'storage method denial must not block login navigation');
equal(deniedStorageAssigned[0], '/login?reason=session_expired');

const originalWindowDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'window');
const deniedPropertyAssigned: string[] = [];
Object.defineProperty(globalThis, 'window', {
  configurable: true,
  value: {
    location: {
      pathname: '/my-work',
      search: '?tab=todo',
      hash: '',
      assign: (url: string) => deniedPropertyAssigned.push(url),
    },
    get sessionStorage() { throw new Error('storage property denied'); },
  },
});
try {
  resetSessionExpiredRedirectForTest();
  equal(redirectForExpiredSession(), true, 'sessionStorage property denial must not block login navigation');
  equal(deniedPropertyAssigned[0], '/login?reason=session_expired');
} finally {
  if (originalWindowDescriptor) Object.defineProperty(globalThis, 'window', originalWindowDescriptor);
  else delete (globalThis as { window?: unknown }).window;
}

console.log(`[session-expired-recovery] PASS assertions=${assertions}`);

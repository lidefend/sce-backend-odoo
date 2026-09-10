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

console.log(`[session-expired-recovery] PASS assertions=${assertions}`);

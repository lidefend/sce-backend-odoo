import assert from 'node:assert/strict';
import { resolveCreateFormActivityRedirect } from '../src/app/recordFormActivityRoute.ts';
import {
  executeRecordFormReturn,
  hasInAppReturnHistory,
  resolveRecordFormReturnFallbackRoute,
} from '../src/pages/contractForm/useCreatedRecordNavigationRuntime.ts';

const cases: Array<{ name: string; run: () => void | Promise<void> }> = [];
let passed = 0;

function check(name: string, run: () => void | Promise<void>) {
  cases.push({ name, run });
}

// --- create-form activity identity must preserve the navigation mode --------

check('create form gains an activity identity without forcing replace', () => {
  const redirect = resolveCreateFormActivityRedirect({
    routeName: 'model-form',
    routeParams: { model: 'sc.receipt.income', id: 'new' },
    query: { menu_id: '338' },
    hash: '',
    createActivityInstanceId: () => 'ap_abc',
  });
  assert.deepEqual(redirect, {
    name: 'model-form',
    params: { model: 'sc.receipt.income', id: 'new' },
    query: { menu_id: '338', activity_page_id: 'ap_abc' },
    hash: '',
  });
  assert.equal(Object.prototype.hasOwnProperty.call(redirect as object, 'replace'), false);
});

check('an existing activity identity is left untouched', () => {
  assert.equal(resolveCreateFormActivityRedirect({
    routeName: 'model-form',
    routeParams: { model: 'sc.receipt.income', id: 'new' },
    query: { menu_id: '338', activity_page_id: 'ap_existing' },
    hash: '',
    createActivityInstanceId: () => 'ap_new',
  }), null);
});

check('activity identity redirect only applies to create routes', () => {
  assert.equal(resolveCreateFormActivityRedirect({
    routeName: 'model-form',
    routeParams: { model: 'sc.receipt.income', id: '7' },
    query: { menu_id: '338' },
    hash: '',
    createActivityInstanceId: () => 'ap_new',
  }), null);
  assert.equal(resolveCreateFormActivityRedirect({
    routeName: 'action',
    routeParams: { actionId: '637' },
    query: { menu_id: '338' },
    hash: '',
    createActivityInstanceId: () => 'ap_new',
  }), null);
});

check('record route name is treated as a create form too', () => {
  const redirect = resolveCreateFormActivityRedirect({
    routeName: 'record',
    routeParams: { model: 'sc.receipt.income', id: 'new' },
    query: { menu_id: '338' },
    hash: '#top',
    createActivityInstanceId: () => 'ap_record',
  });
  assert.ok(redirect);
  assert.equal(redirect?.hash, '#top');
  assert.equal(redirect?.query.activity_page_id, 'ap_record');
});

// --- record form return ----------------------------------------------------

check('in-app history entry is detected from router history state', () => {
  assert.equal(hasInAppReturnHistory({ back: '/a/637?menu_id=338', current: '/f/sc.receipt.income/new' }), true);
  assert.equal(hasInAppReturnHistory({ back: null, current: '/f/sc.receipt.income/new' }), false);
  assert.equal(hasInAppReturnHistory({ back: '', current: '/f/x/new' }), false);
  assert.equal(hasInAppReturnHistory(null), false);
  assert.equal(hasInAppReturnHistory(undefined), false);
});

check('fallback entry comes from the declared contract route only', () => {
  assert.equal(resolveRecordFormReturnFallbackRoute('/a/637?menu_id=338'), '/a/637?menu_id=338');
  assert.equal(resolveRecordFormReturnFallbackRoute('  /a/637?menu_id=338 '), '/a/637?menu_id=338');
  assert.equal(resolveRecordFormReturnFallbackRoute(''), '');
  assert.equal(resolveRecordFormReturnFallbackRoute(undefined), '');
  assert.equal(resolveRecordFormReturnFallbackRoute('sc.receipt.income'), '');
});

check('direct create link returns to the contract entry route', async () => {
  const calls: string[] = [];
  const mode = await executeRecordFormReturn({
    query: { menu_id: '338' },
    relationModel: 'sc.receipt.income',
    embedded: false,
    postCancel: () => calls.push('cancel'),
    navigateBack: () => calls.push('back'),
    hasInAppHistoryEntry: () => false,
    fallbackRoute: () => '/a/637?menu_id=338',
    navigateFallback: (route) => calls.push(`fallback:${route}`),
  });
  assert.equal(mode, 'fallback');
  assert.deepEqual(calls, ['fallback:/a/637?menu_id=338']);
});

check('in-app create returns through browser history', async () => {
  const calls: string[] = [];
  const mode = await executeRecordFormReturn({
    query: { menu_id: '338' },
    relationModel: 'sc.receipt.income',
    embedded: false,
    postCancel: () => calls.push('cancel'),
    navigateBack: () => calls.push('back'),
    hasInAppHistoryEntry: () => true,
    fallbackRoute: () => '/a/637?menu_id=338',
    navigateFallback: (route) => calls.push(`fallback:${route}`),
  });
  assert.equal(mode, 'history');
  assert.deepEqual(calls, ['back']);
});

check('embedded relation dialog still cancels without navigating', async () => {
  const calls: string[] = [];
  const mode = await executeRecordFormReturn({
    query: {
      relation_create_mode: 'dialog',
      relation_dialog_nonce: 'dialog-nonce-0001',
      relation_return_field: 'partner_id',
      relation_return_model: 'res.partner',
      activity_page_id: 'ap_1',
    },
    relationModel: 'res.partner',
    embedded: true,
    postCancel: (message) => calls.push(`cancel:${String((message as { type?: string }).type || '')}`),
    navigateBack: () => calls.push('back'),
    hasInAppHistoryEntry: () => false,
    fallbackRoute: () => '/a/637?menu_id=338',
    navigateFallback: (route) => calls.push(`fallback:${route}`),
  });
  assert.equal(mode, 'dialog_cancel');
  assert.deepEqual(calls, ['cancel:sc.relation_record_cancelled.v1']);
});

check('no contract entry route keeps the plain history return', async () => {
  const calls: string[] = [];
  const mode = await executeRecordFormReturn({
    query: {},
    relationModel: 'sc.receipt.income',
    embedded: false,
    postCancel: () => calls.push('cancel'),
    navigateBack: () => calls.push('back'),
    hasInAppHistoryEntry: () => false,
    fallbackRoute: () => '',
    navigateFallback: (route) => calls.push(`fallback:${route}`),
  });
  assert.equal(mode, 'history');
  assert.deepEqual(calls, ['back']);
});

check('fallback is not used when no fallback handler is supplied', async () => {
  const calls: string[] = [];
  const mode = await executeRecordFormReturn({
    query: {},
    relationModel: 'sc.receipt.income',
    embedded: false,
    postCancel: () => calls.push('cancel'),
    navigateBack: () => calls.push('back'),
    hasInAppHistoryEntry: () => false,
    fallbackRoute: () => '/a/637?menu_id=338',
  });
  assert.equal(mode, 'history');
  assert.deepEqual(calls, ['back']);
});

for (const testCase of cases) {
  await testCase.run();
  passed += 1;
  console.log(`ok ${passed} - ${testCase.name}`);
}
assert.ok(passed >= 11, `expected at least 11 cases, ran ${passed}`);
console.log(`record_form_return_navigation_test cases=${passed}`);

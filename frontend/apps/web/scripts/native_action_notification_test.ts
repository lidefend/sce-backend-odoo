import assert from 'node:assert/strict';
import { effectScope, ref } from 'vue';
import { beginContextTransition } from '../src/app/contextEpoch';
import { decodeNativeActionNotification } from '../src/app/contract/nativeActionNotification';
import { useNativeActionFeedback } from '../src/pages/contractForm/useNativeActionFeedback';
import { usePrimaryFormActionRuntime } from '../src/pages/contractForm/usePrimaryFormActionRuntime';

const result = { raw_action: { type: 'ir.actions.client', tag: 'display_notification', params: {
  title: 'Native title', message: 'Native advisory', type: 'warning', sticky: true,
} } };
assert.deepEqual(decodeNativeActionNotification(result), result.raw_action.params);
for (const invalid of [{ type: ['info'] }, { type: {} }, { type: 'other' }, { message: '' }, { message: false }, { sticky: 1 }, { title: null }]) {
  assert.throws(() => decodeNativeActionNotification({ raw_action: { ...result.raw_action, params: { ...result.raw_action.params, ...invalid } } }), { name: 'ContractGapError' });
}
assert.equal(decodeNativeActionNotification({ raw_action: { tag: 'other' } }), null);
const scope = effectScope();
const identity = ref('record-1');
const active = ref(true);
const shown: unknown[] = [];
let closed = 0;
const feedback = scope.run(() => useNativeActionFeedback({ identity: () => identity.value,
  active: () => active.value, show: async value => { shown.push(value); return () => { closed += 1; }; } }))!;
const owner = feedback.begin();
await owner.publish(result);
assert.equal(shown.length, 1);
identity.value = 'record-2'; identity.value = 'record-1';
await owner.publish(result);
assert.equal(shown.length, 1);
assert.equal(closed, 1);
const contextOwner = feedback.begin();
await contextOwner.publish(result);
const beforeContext = closed;
beginContextTransition();
assert.equal(closed, beforeContext + 1, 'already visible notification closes on context abort');
await contextOwner.publish(result);
assert.equal(shown.length, 2, 'epoch-only stale result cannot publish');
shown.pop();
const superseded = feedback.begin(); feedback.begin();
await superseded.publish(result); assert.equal(shown.length, 1);
const deactivated = feedback.begin(); active.value = false; active.value = true;
await deactivated.publish(result); assert.equal(shown.length, 1);

let writes = 0; let reloads = 0; let confirm = true;
let pending: (() => void) | undefined;
const runtime = usePrimaryFormActionRuntime({
  beginActionFeedback: feedback.begin, confirmActionSafety: async () => confirm,
  busyKind: ref(null), recordId: ref(1), modelName: () => 'declared.model', actionId: () => 2,
  routeMenuId: () => 3, currentQuery: () => ({}),
  executeButtonRequest: async () => { writes += 1; return { result }; },
  navigateActionResponseResult: async () => false,
  applyProjectionRefreshPolicy: async () => {},
  reload: async () => { reloads += 1; await new Promise<void>(resolve => { pending = resolve; }); },
  submissionFeedback: ref(null), validationErrors: ref([]), status: ref('ok'), errorMessage: ref(''),
} as never);
const action = { enabled: true, methodName: 'native_action', kind: 'object' } as never;
const first = runtime.executePrimarySubmitAction(action, 1);
while (!pending) await Promise.resolve();
assert.equal(shown.length, 1, 'notification waits for refresh'); pending!(); await first;
assert.equal(shown.length, 2, 'real action chain publishes after refresh');
assert.equal(reloads, 1);
pending = undefined;
const stale = runtime.executePrimarySubmitAction(action, 1);
while (!pending) await Promise.resolve();
identity.value = 'record-2'; pending!(); await stale;
assert.equal(shown.length, 2, 'refreshed old record never notifies new page');
confirm = false; await runtime.executePrimarySubmitAction(action, 1);
assert.equal(writes, 2, 'cancel sends no request');
const disposed = feedback.begin(); scope.stop(); await disposed.publish(result);
assert.equal(shown.length, 2);
console.log('[native_action_notification] PASS checks=22 real_primary_chain=true');

// Actual router navigation and owner handoff, independent of the vendor plugin.
const { createRouter, createMemoryHistory } = await import('vue-router');
const { useActionResponseNavigation } = await import('../src/pages/contractForm/useActionResponseNavigation');
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/source', component: {} }, { path: '/other', component: {} },
  { path: '/a/:actionId', name: 'action', component: {} },
] });
await router.push('/source');
const principal = ref('actor/company');
let navigationShown = 0; let navigationClosed = 0;
let delayShow: (() => void) | undefined;
let delayPlugin = false;
const navigation = useActionResponseNavigation({ router, currentQuery: () => ({}), currentModel: () => 'declared.model',
  notificationIdentity: () => principal.value,
  showNotification: async () => {
    navigationShown += 1;
    if (delayPlugin) await new Promise<void>(resolve => { delayShow = resolve; });
    return () => { navigationClosed += 1; };
  },
});
function navigationOwner() {
  const sourceScope = effectScope();
  const state = sourceScope.run(() => useNativeActionFeedback({ identity: () => router.currentRoute.value.fullPath,
    active: () => true, show: async () => () => {} }))!;
  return { sourceScope, owner: state.begin() };
}
const nextResult = { ...result, action_id: 2 };
let fixture = navigationOwner();
const disposeAfter = router.afterEach(() => fixture.sourceScope.stop());
assert.equal(await navigation.navigateActionResponseResult(nextResult, fixture.owner), true);
assert.equal(router.currentRoute.value.path, '/a/2');
assert.equal(navigationShown, 1, 'declared navigation notification survives source scope disposal');
disposeAfter();
await router.push('/other');
assert.equal(navigationClosed, 1, 'subsequent user navigation closes handed-off notification');
await router.push('/source');
fixture = navigationOwner();
const cancelNavigation = router.beforeEach(to => to.path === '/a/2' ? false : undefined);
assert.equal(await navigation.navigateActionResponseResult(nextResult, fixture.owner), 'invalidated');
assert.equal(navigationShown, 1, 'cancelled navigation never publishes');
cancelNavigation(); fixture.sourceScope.stop();
fixture = navigationOwner(); delayPlugin = true;
const lateNavigation = navigation.navigateActionResponseResult(nextResult, fixture.owner);
while (!delayShow) await Promise.resolve();
await router.push('/other'); delayShow!();
assert.equal(await lateNavigation, 'invalidated');
assert.equal(navigationClosed, 2, 'late plugin instance closes after user navigation');
fixture.sourceScope.stop(); delayPlugin = false;
await router.push('/source'); fixture = navigationOwner();
await navigation.navigateActionResponseResult(nextResult, fixture.owner);
beginContextTransition();
assert.equal(navigationClosed, 3, 'context abort closes destination notification');
fixture.sourceScope.stop();
console.log('[native_action_notification_navigation] PASS checks=9 actual_router=true');

const { useCreatedRecordNavigationRuntime } = await import('../src/pages/contractForm/useCreatedRecordNavigationRuntime');
const { useFormNavigationActionsRuntime } = await import('../src/pages/contractForm/useFormNavigationActionsRuntime');
const { resolveProfessionalRelationLifecycleEvent } = await import('../src/pages/contractForm/professionalRelationLifecycleModel');
router.addRoute({ path: '/f/:model/:id', name: 'model-form', component: {} });
const previousWindow = (globalThis as any).window;
let hardNavigations = 0;
const testWindow: any = { location: { origin: 'http://fixture.local', replace: () => { hardNavigations += 1; } } };
testWindow.parent = testWindow;
(globalThis as any).window = testWindow;
const createQuery = ref<Record<string, unknown>>({});
let intake = false;
const intakeNavigation = useFormNavigationActionsRuntime({ router, actionId: () => 2,
  currentQuery: () => createQuery.value, isIntakeCreateMode: () => intake,
  resolveLandingPath: () => '/source', resolveWorkspaceContextQuery: () => ({}),
});
const createdNavigation = useCreatedRecordNavigationRuntime({ router, currentQuery: () => createQuery.value,
  modelName: () => 'declared.model', isQuickIntakeMode: () => intake, isStandardIntakeMode: () => false,
  resolveWorkspaceContextQuery: () => ({}), applyProjectionRefreshPolicy: async () => {},
  returnToIntakeList: intakeNavigation.returnToIntakeList,
  navigateNotificationTarget: navigation.navigateNotificationTarget,
});
const createdOptions = { createdId: 7, nextSceneKey: '', nextSceneRoute: '' };
await router.push('/source'); fixture = navigationOwner();
const beforeCreated = navigationShown;
assert.equal(await createdNavigation.navigateCreatedRecord({ ...createdOptions, feedback: { result, owner: fixture.owner } }), true);
assert.equal(router.currentRoute.value.path, '/f/declared.model/7');
assert.equal(navigationShown, beforeCreated + 1);
assert.equal(hardNavigations, 0, 'notification create uses owner-bound replace, not hard reload');
fixture.sourceScope.stop();
await router.push('/source'); fixture = navigationOwner();
const rejectCreated = router.beforeEach(to => to.name === 'model-form' ? false : undefined);
assert.equal(await createdNavigation.navigateCreatedRecord({ ...createdOptions, feedback: { result, owner: fixture.owner } }), false);
assert.equal(navigationShown, beforeCreated + 1);
rejectCreated(); fixture.sourceScope.stop();
intake = true; fixture = navigationOwner();
await createdNavigation.navigateCreatedRecord({ ...createdOptions, feedback: { result, owner: fixture.owner } });
assert.equal(router.currentRoute.value.path, '/a/2');
assert.equal(navigationShown, beforeCreated + 2, 'intake list receives the same native notification');
fixture.sourceScope.stop();
intake = false;
createQuery.value = { relation_create_mode: 'dialog', relation_dialog_nonce: 'nonce-123456',
  relation_return_field: 'partner_id', relation_return_model: 'parent.model' };
let posted: unknown;
testWindow.parent = { postMessage: (message: unknown) => { posted = message; } };
fixture = navigationOwner();
await createdNavigation.navigateCreatedRecord({ ...createdOptions, feedback: { result, owner: fixture.owner } });
const eventParams = { active: true, context: { nonce: 'nonce-123456', fieldName: 'partner_id',
  parentModel: 'parent.model', relationModel: 'declared.model' },
  eventOrigin: testWindow.location.origin, expectedOrigin: testWindow.location.origin, sourceMatches: true, payload: posted };
const resolved = resolveProfessionalRelationLifecycleEvent(eventParams);
assert.equal(resolved?.kind, 'created');
if (resolved?.kind === 'created') assert.deepEqual(resolved.result.notification, result.raw_action.params);
assert.equal(resolveProfessionalRelationLifecycleEvent({ ...eventParams, sourceMatches: false }), null);
assert.equal(resolveProfessionalRelationLifecycleEvent({ ...eventParams, active: false }), null);
assert.throws(() => resolveProfessionalRelationLifecycleEvent({ ...eventParams,
  payload: { ...(posted as object), notification: { ...result.raw_action.params, sticky: 'true' } } }), { name: 'ContractGapError' });
posted = undefined; beginContextTransition();
assert.equal(await createdNavigation.navigateCreatedRecord({ ...createdOptions, feedback: { result, owner: fixture.owner } }), false);
assert.equal(posted, undefined, 'old context cannot complete dialog handoff');
fixture.sourceScope.stop();
(globalThis as any).window = previousWindow;
console.log('[native_action_notification_created] PASS checks=15 ordinary_intake_dialog=true');

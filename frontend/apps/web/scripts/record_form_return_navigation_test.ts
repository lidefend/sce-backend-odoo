import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { relationReadRouteRequest, validateRelationReadRoute } from '../src/app/relationReadRouteAuthority.ts';
import { resolveCreateFormActivityRedirect } from '../src/app/recordFormActivityRoute.ts';
import {
  createRecordFormReturnHandler,
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

check('activity identity injection never carries a navigation mode of its own', () => {
  // The caller decides push vs replace. The redirect must expose no mode key at
  // all, so a caller that replaces keeps replacing (no extra history entry) and
  // a caller that pushes keeps pushing. Asserting the exact key set catches a
  // future `push`/`replace` flag being reintroduced.
  const redirect = resolveCreateFormActivityRedirect({
    routeName: 'model-form',
    routeParams: { model: 'sc.receipt.income', id: 'new' },
    query: { menu_id: '338' },
    hash: '',
    createActivityInstanceId: () => 'ap_mode',
  });
  assert.ok(redirect);
  assert.deepEqual(Object.keys(redirect as object).sort(), ['hash', 'name', 'params', 'query']);
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

check('return handler consumes live authority only after unsaved confirmation', async () => {
  const previousWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');
  const view = { parent: null as unknown, location: { origin: 'http://localhost' } };
  view.parent = view;
  Object.defineProperty(globalThis, 'window', { configurable: true, value: view });
  try {
    let allow = false;
    let authority = '/m/one';
    const visits: string[] = [];
    const params = {
      route: { query: {} },
      router: { options: { history: { state: {} } }, back: () => { visits.push('back'); },
        replace: async (target: string) => { visits.push(target); } },
      model: () => 'x.document', authorityRoute: () => authority,
      navigateAfterConfirm: async (navigate: () => Promise<void>) => {
        if (!allow) return false;
        await navigate();
        return true;
      },
    };
    const navigate = createRecordFormReturnHandler(params as unknown as Parameters<typeof createRecordFormReturnHandler>[0]);
    await navigate();
    assert.deepEqual(visits, [], 'rejected confirmation must not navigate');
    allow = true;
    authority = '/m/two';
    await navigate();
    assert.deepEqual(visits, ['/m/two'], 'use current authority, not factory-time authority');
  } finally {
    if (previousWindow) Object.defineProperty(globalThis, 'window', previousWindow);
    else Reflect.deleteProperty(globalThis, 'window');
  }
});

const relationRoute = () => ({ name:'record', path:'/r/x.partner/56', params:{model:'x.partner',id:'56'},
  query:{action_id:'324',menu_id:'164',return_model:'x.payment',return_record_id:'1813',return_field:'partner_id',return_action_id:'775',return_menu_id:'545'} });
check('relation read navigation transports exact provenance without trusting can_open or return URL', async () => {
  const route = relationRoute();
  const params = relationReadRouteRequest(route)!;
  assert.equal(params.access_mode, 'read'); assert.equal(params.render_profile, 'readonly');
  assert.equal(params.relation_origin.record_id,1813);
  assert.equal(await validateRelationReadRoute(route,()=> 'actor30/company8/epoch1',async request => ({...request,allowed:true})),true);
  assert.deepEqual(route,relationRoute());
});
check('relation read receipt requires every target identity field and read mode', async () => {
  const route = relationRoute();
  for (const [key,value] of Object.entries({model:'x.other',record_id:57,action_id:325,menu_id:165,route_path:'/f/x.partner/56',access_mode:'write',render_profile:'edit',allowed:false})) {
    assert.equal(await validateRelationReadRoute(route,()=> 'stable',async request=>({...request,allowed:true,[key]:value})),false,key);
  }
  assert.equal(await validateRelationReadRoute(route,()=> 'stable',async()=>({allowed:true})),false);
  assert.equal(await validateRelationReadRoute(route,()=> 'stable',async()=>{throw new Error('revoked');}),false);
});
check('relation origin cannot authorize edit/list/create or coerced IDs', async () => {
  const route=relationRoute();
  for (const [name,path] of [['model-form','/f/x.partner/56'],['action','/a/324'],['record','/r/x.partner/new'],['record','/r/x.partner/57']]) {
    let called=false;
    assert.equal(await validateRelationReadRoute({...route,name,path},()=> 'stable',async()=>{called=true;return {allowed:true};}),false);
    assert.equal(called,false);
  }
  for (const value of [true,56.5,[],{},'56.0','056','9007199254740992']) {
    assert.equal(relationReadRouteRequest({...route,params:{...route.params,id:value}}),null);
    assert.equal(relationReadRouteRequest({...route,query:{...route.query,return_record_id:value}}),null);
  }
});
check('late relation receipt cannot cross actor/company/context lifetime', async () => {
  for (const changed of ['actor31/company8/epoch1','actor30/company9/epoch1','actor30/company8/epoch2']) {
    let scope='actor30/company8/epoch1';
    let resolve!: (value:Record<string,unknown>)=>void;
    const pending=validateRelationReadRoute(relationRoute(),()=>scope,()=>new Promise(done=>{resolve=done;}));
    scope=changed; resolve({...relationReadRouteRequest(relationRoute()),allowed:true});
    assert.equal(await pending,false);
  }
});
check('router uses bounded read validator without mutating session authority; loader retains action and readonly', () => {
  const router=readFileSync('frontend/apps/web/src/router/index.ts','utf8');
  assert.match(router,/if \(!routeAuthority && to.name === 'record'\) \{[\s\S]*?validateRelationReadRoute\(to,[\s\S]*?currentContextEpoch\(\)/);
  const bridge=router.split("if (!routeAuthority && to.name === 'record') {")[1].split("if (to.name === 'action'")[0];
  assert.doesNotMatch(bridge,/setActionMeta|routeAuthority\s*=/);
  const loader=readFileSync('frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts','utf8');
  assert.match(loader,/loadActionContractV2\(actionId.value/);
  assert.match(loader,/loadModelContractV2\(currentModel,[\s\S]*?actionId: actionId.value[\s\S]*?menuId: menuId.value[\s\S]*?\.\.\.profileOptions/);
});

for (const testCase of cases) {
  await testCase.run();
  passed += 1;
  console.log(`ok ${passed} - ${testCase.name}`);
}
assert.ok(passed >= 11, `expected at least 11 cases, ran ${passed}`);
console.log(`record_form_return_navigation_test cases=${passed}`);

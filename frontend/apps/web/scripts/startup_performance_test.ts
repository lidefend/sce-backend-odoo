import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  STARTUP_PHASES,
  canPublishRecordReady,
  markStartupPhase,
  readStartupTimingMarks,
  shouldPreloadWorkspaceHomeAtStartup,
  startupTimingOrderIssues,
} from '../src/app/performance/startupTiming';
import {
  ASSET_LOAD_TIMEOUT_MS,
  createContractFormRouteLoader,
} from '../src/pages/contractFormRouteLoader';
import { validateRecordDeepLinkEvidence } from './record_deep_link_evidence.mjs';

let cases = 0;
for (const phase of STARTUP_PHASES) performance.clearMarks(phase);

assert.equal(markStartupPhase('boot_start', 'test'), true);
assert.equal(markStartupPhase('session_ready', 'test'), true);
assert.equal(markStartupPhase('skeleton_shown', 'test'), true);
assert.equal(markStartupPhase('contract_loaded', 'test'), true);
assert.equal(markStartupPhase('record_ready', 'test'), true);
cases += 5;

assert.equal(markStartupPhase('record_ready', 'duplicate'), false);
cases += 1;

const marks = readStartupTimingMarks();
assert.deepEqual(Object.keys(marks).sort(), [...STARTUP_PHASES].sort());
assert.deepEqual(startupTimingOrderIssues(marks), []);
cases += 2;

const missing = startupTimingOrderIssues({ boot_start: 1, session_ready: 2 });
assert(missing.includes('record_ready_missing'));
cases += 1;

assert.equal(shouldPreloadWorkspaceHomeAtStartup('record'), false);
assert.equal(shouldPreloadWorkspaceHomeAtStartup('model-form'), false);
assert.equal(shouldPreloadWorkspaceHomeAtStartup('home'), true);
assert.equal(shouldPreloadWorkspaceHomeAtStartup('not-found', '/t/demo/r/project.project/26'), false);
assert.equal(shouldPreloadWorkspaceHomeAtStartup('not-found', '/t/demo/f/project.project/new'), false);
assert.equal(shouldPreloadWorkspaceHomeAtStartup('scene', '/t/demo/s/workspace.home'), true);
cases += 6;

assert.equal(canPublishRecordReady({
  routeCurrent: true,
  recordMissing: false,
  hasContract: true,
  status: 'ok',
}), true);
for (const input of [
  { routeCurrent: false, recordMissing: false, hasContract: true, status: 'ok' },
  { routeCurrent: true, recordMissing: true, hasContract: true, status: 'ok' },
  { routeCurrent: true, recordMissing: false, hasContract: false, status: 'ok' },
  { routeCurrent: true, recordMissing: false, hasContract: true, status: 'error' },
]) {
  assert.equal(canPublishRecordReady(input), false);
}
cases += 5;

assert.equal(ASSET_LOAD_TIMEOUT_MS, 15_000);
cases += 1;
let staleResolve!: (value: string) => void;
let loadCalls = 0;
const routeLoader = createContractFormRouteLoader(() => {
  loadCalls += 1;
  if (loadCalls === 1) {
    return new Promise<string>((resolve) => {
      staleResolve = resolve;
    });
  }
  return Promise.resolve('current-page');
}, 100);
const staleLoad = routeLoader.load();
assert.equal(routeLoader.load(), staleLoad, 'same activation must share one in-flight request');
routeLoader.invalidate();
const resumedLoad = routeLoader.load();
assert.deepEqual(await resumedLoad, { module: 'current-page' });
staleResolve('stale-page');
assert.deepEqual(await staleLoad, { cancelled: true });
assert.equal(loadCalls, 2, 'cache reactivation must restart a cancelled load');
cases += 5;

let activeResolve!: (value: string) => void;
const activeLoader = createContractFormRouteLoader(
  () => new Promise<string>((resolve) => {
    activeResolve = resolve;
  }),
  100,
);
const activeLoad = activeLoader.load();
activeResolve('active-page');
assert.deepEqual(await activeLoad, { module: 'active-page' });
cases += 1;

const timedOutLoad = await createContractFormRouteLoader(
  () => new Promise<string>(() => undefined),
  5,
).load();
assert.ok('error' in timedOutLoad);
cases += 1;

const expectedBuildSha = 'a'.repeat(40);
const bundleSha256 = 'b'.repeat(64);
const validBundleAssets = [
  {
    resource_url: 'http://127.0.0.1/assets/index-AbCdEf12.js',
    decoded_body_size: 100,
    resource_sha256: bundleSha256,
  },
  {
    resource_url: 'http://127.0.0.1/assets/ContractFormRoute-XyZ12345.js',
    decoded_body_size: 20,
    resource_sha256: bundleSha256,
  },
  {
    resource_url: 'http://127.0.0.1/assets/ContractFormPage-QwErTy78.js',
    decoded_body_size: 200,
    resource_sha256: bundleSha256,
  },
];
const validEvidence = {
  expectedBuildSha,
  servedBuildInfo: { sha: expectedBuildSha },
  bundleAssets: validBundleAssets,
};
assert.deepEqual(validateRecordDeepLinkEvidence(validEvidence), []);
assert(validateRecordDeepLinkEvidence({
  ...validEvidence,
  expectedBuildSha: '',
}).includes('served_build_sha_expected_missing'));
assert(validateRecordDeepLinkEvidence({
  ...validEvidence,
  servedBuildInfo: null,
}).includes('served_build_info_missing'));
assert(validateRecordDeepLinkEvidence({
  ...validEvidence,
  servedBuildInfo: { sha: 'c'.repeat(40) },
}).includes('served_build_sha_mismatch'));
assert(validateRecordDeepLinkEvidence({
  ...validEvidence,
  bundleAssets: validBundleAssets.slice(0, 2),
}).includes('bundle_asset_missing:form'));
assert(validateRecordDeepLinkEvidence({
  ...validEvidence,
  bundleAssets: validBundleAssets.map((asset, index) => (
    index === 0 ? { ...asset, resource_sha256: '' } : asset
  )),
}).includes('bundle_asset_hash_missing:entry'));
cases += 6;

const indexHtml = readFileSync('frontend/apps/web/index.html', 'utf8');
assert.match(indexHtml, /performance\.mark\('boot_start'\)/);
cases += 1;

const sessionStore = readFileSync('frontend/apps/web/src/stores/session.ts', 'utf8');
assert.match(sessionStore, /markStartupPhase\('session_ready'/);
cases += 1;

const recordLifecycle = readFileSync(
  'frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts',
  'utf8',
);
assert.match(recordLifecycle, /markStartupPhase\('contract_loaded'/);
assert.match(recordLifecycle, /markStartupPhase\('record_ready'/);
cases += 2;
assert(
  recordLifecycle.indexOf('await nextTick()') < recordLifecycle.indexOf("markStartupPhase('record_ready'"),
  'record_ready must follow the Vue DOM patch',
);
assert.match(recordLifecycle, /if \(recordMissing\.value\) return;/);
cases += 2;

const skeleton = readFileSync(
  'frontend/apps/web/src/components/product-record/ProductFormLoadingSkeleton.vue',
  'utf8',
);
assert.match(skeleton, /markStartupPhase\('skeleton_shown'/);
cases += 1;

const recordRoute = readFileSync('frontend/apps/web/src/pages/ContractFormRoute.vue', 'utf8');
assert.match(recordRoute, /import\('\.\/ContractFormPage\.vue'\)/);
assert.doesNotMatch(recordRoute, /import ContractFormPage from '\.\/ContractFormPage\.vue'/);
assert.match(recordRoute, /ProductFormLoadingSkeleton/);
cases += 3;
assert.match(recordRoute, /createContractFormRouteLoader/);
assert.match(recordRoute, /window\.location\.reload\(\)/);
assert.match(recordRoute, /onDeactivated/);
assert.doesNotMatch(recordRoute, /onBeforeRouteLeave/);
assert.match(recordRoute, /onActivated/);
assert.match(recordRoute, /pageLoader\.invalidate\(\)/);
cases += 6;

const sessionRequest = readFileSync('frontend/apps/web/src/stores/session.ts', 'utf8');
assert.match(sessionRequest, /includeWorkspaceHome === false \? \[\] : \['workspace_home'\]/);
assert.match(
  readFileSync('frontend/apps/web/src/main.ts', 'utf8'),
  /bootstrapApp\(\{ initialRouteName: initialRoute\.name, initialPath: window\.location\.pathname \}\)/,
);
cases += 2;

const browserProbe = readFileSync(
  'scripts/verify/local_dev_dev_acceptance_remediation_browser.mjs',
  'utf8',
);
assert.match(browserProbe, /served_build_info/);
assert.match(browserProbe, /resource_sha256/);
assert.match(browserProbe, /startup_mark_missing/);
cases += 3;

console.log(`[startup_performance_test] PASS cases=${cases}`);

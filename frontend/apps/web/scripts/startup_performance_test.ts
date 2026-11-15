import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  STARTUP_PHASES,
  markStartupPhase,
  readStartupTimingMarks,
  shouldPreloadWorkspaceHomeAtStartup,
  startupTimingOrderIssues,
} from '../src/app/performance/startupTiming';

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

const sessionRequest = readFileSync('frontend/apps/web/src/stores/session.ts', 'utf8');
assert.match(sessionRequest, /includeWorkspaceHome === false \? \[\] : \['workspace_home'\]/);
assert.match(
  readFileSync('frontend/apps/web/src/main.ts', 'utf8'),
  /bootstrapApp\(\{ initialRouteName: initialRoute\.name, initialPath: window\.location\.pathname \}\)/,
);
cases += 2;

console.log(`[startup_performance_test] PASS cases=${cases}`);

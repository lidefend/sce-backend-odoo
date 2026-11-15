import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  resolveSceneActivityTitle,
  shouldRenderScenePageHeading,
} from '../src/app/activityPageTitle';
import { formatLoadingProgress } from '../src/app/presentation/loadingProgress';
import { resolveListColumnPreferenceScope } from '../src/app/runtime/listPreferenceScope';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

// N-02: the action owns the model while a new list contract is converging.
check(
  resolveListColumnPreferenceScope({ actionId: 940, model: 'sc.labor.usage' }),
  {
    action_id: 940,
    model: '',
    view_type: 'list',
    preference_key: 'list_columns',
  },
  'a new action must not inherit the previous list model',
);
check(
  resolveListColumnPreferenceScope({ actionId: 639, model: 'sc.labor.deduction' }),
  {
    action_id: 639,
    model: '',
    view_type: 'list',
    preference_key: 'list_columns',
  },
  'rapid switches use action-resolved identity instead of a stale page projection',
);
check(
  resolveListColumnPreferenceScope({ actionId: 0, model: ' sc.equipment.usage ' }),
  {
    action_id: undefined,
    model: 'sc.equipment.usage',
    view_type: 'list',
    preference_key: 'list_columns',
  },
  'model-only consumers keep their declared model identity',
);

// M-01: business labels come from declared scene projections, not a frontend
// key-to-label dictionary.
check(
  resolveSceneActivityTitle({
    sceneKey: 'enterprise.department',
    runtimeLabel: '部门管理',
    queryLabel: 'enterprise.department',
  }),
  '部门管理',
  'runtime scene projection owns the enterprise tab title',
);
check(
  resolveSceneActivityTitle({
    sceneKey: 'portal.notifications',
    registeredLabel: '消息中心',
  }),
  '消息中心',
  'registered scene label owns the portal tab title',
);
check(
  resolveSceneActivityTitle({
    sceneKey: 'projects.ledger',
    queryLabel: '项目台账',
  }),
  '项目台账',
  'a distinct route-carried business label is consumed',
);

// N-03: scene pages always expose one semantic heading. Handling surfaces that
// already render their own h1 do not receive a duplicate.
check(
  shouldRenderScenePageHeading({ hasSceneIdentity: 'safety.issue.list' }),
  true,
  'a rendered scene page receives its generic semantic heading',
);
check(
  shouldRenderScenePageHeading({
    hasSceneIdentity: 'project.management',
    hasExplicitHeading: true,
  }),
  false,
  'an explicit handling-surface heading is not duplicated',
);
check(
  shouldRenderScenePageHeading({ hasSceneIdentity: '' }),
  false,
  'a page without scene identity does not invent a heading',
);
check(
  formatLoadingProgress(14_700),
  {
    elapsedLabel: '已等待 14 秒',
    hint: '业务数据仍在加载，请稍候',
  },
  'long record loading exposes elapsed progress without inventing a completion percentage',
);

const actionView = readFileSync('frontend/apps/web/src/views/ActionView.vue', 'utf8');
assert.match(
  actionView,
  /resolveListColumnPreferenceScope/,
  'ActionView must consume the action-owned preference scope helper',
);
cases += 1;

const router = readFileSync('frontend/apps/web/src/router/index.ts', 'utf8');
assert.match(
  router,
  /resolveSceneActivityTitle/,
  'activity tab title projection must consume the declared scene-title helper',
);
cases += 1;

const sceneView = readFileSync('frontend/apps/web/src/views/SceneView.vue', 'utf8');
assert.match(
  sceneView,
  /data-scene-page-heading/,
  'SceneView must render a stable semantic page heading hook',
);
cases += 1;

const formLoading = readFileSync('frontend/apps/web/src/components/product-record/ProductFormLoadingSkeleton.vue', 'utf8');
assert.match(
  formLoading,
  /data-loading-progress/,
  'record form loading exposes a visible progress surface',
);
cases += 1;

console.log(`[dev_acceptance_remediation_test] PASS cases=${cases}`);

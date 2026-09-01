import assert from 'node:assert/strict';
import {
  isSupersededEntryActionActivityPage,
  retainIndependentActivityPages,
  trimRetainedActivityPages,
  type RetainedActivityPageLike,
} from '../src/app/activityPageRetention';
import { resolveBusinessActivityTitle } from '../src/app/activityPageTitle';

function createPage(overrides: Partial<RetainedActivityPageLike> = {}): RetainedActivityPageLike {
  return {
    key: 'new:project.project:first',
    kind: 'record_form',
    model: 'project.project',
    menu_id: 378,
    record_id: 'new',
    record_context: { company_id: 1, selected: null },
    dirty: false,
    ...overrides,
  };
}

const previous = createPage();
const incoming = createPage({ key: 'new:project.project:second', action_id: 722 });
const otherModelLoading = createPage({
  key: 'record:payment.request:157',
  kind: 'record_form',
  model: 'payment.request',
  menu_id: 558,
  action_id: 807,
  record_id: '157',
});

assert.notEqual(previous.key, incoming.key, 'different activity instances remain independently addressable');
assert.deepEqual(
  retainIndependentActivityPages([previous, otherModelLoading], incoming, false).map((page) => page.key),
  [previous.key, otherModelLoading.key],
  'same-carrier instances and pages from other models remain available',
);

const entryAction = createPage({
  key: 'action:722:menu:378',
  kind: 'menu_action',
  record_id: undefined,
});
assert.equal(isSupersededEntryActionActivityPage(entryAction, incoming), true);
assert.equal(isSupersededEntryActionActivityPage({ ...entryAction, menu_id: 379 }, incoming), false);
assert.equal(isSupersededEntryActionActivityPage({ ...entryAction, dirty: true }, incoming), false);
assert.deepEqual(
  retainIndependentActivityPages([entryAction, previous], incoming, true).map((page) => page.key),
  [previous.key],
  'only the entry action intermediate is removed when the form replaces it',
);

console.log('[activity_page_retention_test] PASS cases=6');

const capacityPages = Array.from({ length: 7 }, (_, index) => createPage({
  key: `page:${index + 1}`,
  dirty: index === 0,
  last_active_at: index + 1,
}));
assert.deepEqual(
  trimRetainedActivityPages(capacityPages, 'page:7', 6).map((page) => page.key),
  ['page:1', 'page:3', 'page:4', 'page:5', 'page:6', 'page:7'],
  'capacity eviction preserves the active page and dirty pages while removing the least-recent clean page',
);
assert.equal(
  trimRetainedActivityPages(capacityPages.map((page) => ({ ...page, dirty: true })), 'page:7', 6).length,
  7,
  'capacity remains soft when every inactive page contains unsaved work',
);

console.log('[activity_page_capacity_test] PASS cases=2');

assert.equal(resolveBusinessActivityTitle({
  authorityName: '项目立项',
  actionTitle: '新项目立项',
  modelLabel: '项目',
}), '项目立项', 'route authority owns the stable activity name');
assert.equal(resolveBusinessActivityTitle({
  actionTitle: '新项目立项',
  modelLabel: '项目',
}), '新项目立项', 'fallback activity names are not decorated with a page mode');

console.log('[activity_page_title_test] PASS cases=2');

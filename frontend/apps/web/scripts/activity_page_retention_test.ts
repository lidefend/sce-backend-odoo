import assert from 'node:assert/strict';
import {
  dedupeCleanCreateActivityPages,
  isSupersededCleanCreateActivityPage,
  isSupersededEntryActionActivityPage,
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

assert.equal(isSupersededCleanCreateActivityPage(previous, incoming), true);
assert.deepEqual(dedupeCleanCreateActivityPages([previous, incoming]).map((page) => page.key), [incoming.key]);
assert.equal(isSupersededCleanCreateActivityPage(createPage({ dirty: true }), incoming), false);
assert.equal(isSupersededCleanCreateActivityPage(createPage({ menu_id: 379 }), incoming), false);
assert.equal(isSupersededCleanCreateActivityPage(createPage({ model: 'sale.order' }), incoming), false);
assert.equal(isSupersededCleanCreateActivityPage(createPage({ record_context: { company_id: 2 } }), incoming), false);
assert.equal(isSupersededCleanCreateActivityPage(createPage({ record_id: '42' }), incoming), false);
assert.equal(isSupersededCleanCreateActivityPage(
  createPage({ menu_id: undefined, action_id: 722 }),
  createPage({ key: 'new:project.project:third', menu_id: undefined, action_id: 722 }),
), true);

const dirty = createPage({ key: 'new:project.project:dirty', dirty: true });
assert.deepEqual(
  dedupeCleanCreateActivityPages([previous, dirty, incoming]).map((page) => page.key),
  [dirty.key, incoming.key],
);

const entryAction = createPage({
  key: 'action:722:menu:378',
  kind: 'menu_action',
  record_id: undefined,
});
assert.equal(isSupersededEntryActionActivityPage(entryAction, incoming), true);
assert.equal(isSupersededEntryActionActivityPage({ ...entryAction, menu_id: 379 }, incoming), false);
assert.equal(isSupersededEntryActionActivityPage({ ...entryAction, dirty: true }, incoming), false);

console.log('[activity_page_retention_test] PASS cases=12');

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

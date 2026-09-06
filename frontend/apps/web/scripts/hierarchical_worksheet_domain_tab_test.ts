import { strict as assert } from 'node:assert';
import {
  applyWorksheetDomainTab,
  resolveWorksheetDomainTabs,
} from '../src/app/action_runtime/hierarchicalWorksheetDomainTabs';

type SheetLike = {
  domain: unknown[];
  domain_tabs?: unknown;
};

function makeSheet(overrides: Partial<SheetLike> & Record<string, unknown> = {}): SheetLike {
  return {
    model: 'project.boq.line',
    fields: ['id', 'name'],
    presentation_mode: 'source_order',
    domain: [['version_id.state', '=', 'published']],
    ...overrides,
  } as SheetLike;
}

// ── resolveWorksheetDomainTabs：规范化与容错 ──────────────
assert.deepEqual(resolveWorksheetDomainTabs(makeSheet()), []);
assert.deepEqual(resolveWorksheetDomainTabs(makeSheet({ domain_tabs: [] })), []);

const tabs = resolveWorksheetDomainTabs(makeSheet({
  domain_tabs: [
    { key: 'published', label: '已发布版本', domain: [['version_id.state', '=', 'published']] },
    { key: 'editing', label: '', domain: [['version_id.state', 'in', ['draft', 'validated']]] },
  ],
}));
assert.equal(tabs.length, 2);
assert.equal(tabs[0].key, 'published');
assert.equal(tabs[0].label, '已发布版本');
assert.equal(tabs[0].domain.length, 1);
// label 缺省回退 key
assert.equal(tabs[1].label, 'editing');

// key 缺失 / 重复 / domain 非数组 → 剔除或容错
assert.deepEqual(
  resolveWorksheetDomainTabs(makeSheet({
    domain_tabs: [
      { key: '', label: '无 key', domain: [] },
      { key: 'a', label: 'A', domain: 'not-a-list' },
      { key: 'a', label: 'A 重复', domain: [] },
      null,
      'garbage',
    ],
  })),
  [{ key: 'a', label: 'A', domain: [] }],
);

// ── applyWorksheetDomainTab：tab domain 合成 ──────────────
const sheet = makeSheet({
  domain_tabs: [
    { key: 'published', label: '已发布版本', domain: [['version_id.state', '=', 'published'], ['source_row_type', 'in', ['item']]] },
    { key: 'editing', label: '编制中版本', domain: [['version_id.state', 'in', ['draft', 'validated']]] },
  ],
});

const editing = applyWorksheetDomainTab(sheet, 'editing');
assert.equal(editing.domain.length, 1);
assert.deepEqual(editing.domain[0], ['version_id.state', 'in', ['draft', 'validated']]);
// 原 config 不被变异（domain 引用替换而非原地修改）
assert.equal(sheet.domain.length, 1);
assert.deepEqual(sheet.domain[0], ['version_id.state', '=', 'published']);
// 其余字段原样保留
assert.equal(editing.model, 'project.boq.line');
assert.equal(editing.presentation_mode, 'source_order');

// 未知 key → 返回原 config（默认 domain 兜底）
assert.equal(applyWorksheetDomainTab(sheet, 'unknown'), sheet);
// 无 tabs config → 原样返回（旧契约兼容）
const legacy = makeSheet();
assert.equal(applyWorksheetDomainTab(legacy, 'published'), legacy);

console.log('hierarchical_worksheet_domain_tab_test: all assertions passed');

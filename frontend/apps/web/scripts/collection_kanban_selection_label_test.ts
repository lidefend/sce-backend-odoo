import assert from 'node:assert/strict';
import { FIELD_VALUE_EMPTY_TEXT } from '../src/utils/fieldSemantics';
import {
  resolveSelectionLabel,
  resolveCollectionCell,
  collectColumnSelections,
  resolveCollectionStatusPresentation,
} from '../src/app/presentation/collectionStatusPresentation';

// F03：项目台账卡片「经营方式」消费已声明选择项（公司直营/联营项目）。
const operationStrategy = [
  { value: 'direct', label: '公司直营' },
  { value: 'joint', label: '联营项目' },
];

assert.equal(resolveSelectionLabel('direct', operationStrategy), '公司直营');
assert.equal(resolveSelectionLabel('joint', operationStrategy), '联营项目');
assert.equal(resolveSelectionLabel(['direct', '公司直营'], operationStrategy), '公司直营');
// 声明选项存在但值不在选择集：返回 null，KanbanPage 据此走 ContractGapError，不静默兜底英文。
assert.equal(resolveSelectionLabel('self_run', operationStrategy), null);
// 普通非 selection 字段无声明选择项：保持原行为（null → semanticValueByField）。
assert.equal(resolveSelectionLabel('direct'), null);
assert.equal(resolveSelectionLabel('unknown', operationStrategy), null);

// F02：项目看板「状态」消费已声明生命周期选择项。
const lifecycle = [
  { value: 'draft', label: '草稿' },
  { value: 'in_progress', label: '在建' },
  { value: 'paused', label: '停工' },
  { value: 'done', label: '竣工' },
  { value: 'closing', label: '结算中' },
  { value: 'warranty', label: '保修期' },
  { value: 'closed', label: '关闭' },
];

assert.deepEqual(resolveCollectionStatusPresentation({ value: 'in_progress', selection: lifecycle }), {
  value: 'in_progress',
  label: '在建',
  tone: 'info',
});
assert.deepEqual(resolveCollectionStatusPresentation({ value: ['closing', '结算中'], selection: lifecycle }), {
  value: 'closing',
  label: '结算中',
  tone: 'warning',
});
assert.equal(resolveSelectionLabel('closed', lifecycle), '关闭');

const ordinary = (field: string, value: unknown) => ({ text: `${field}:${value}`, tone: 'neutral' as const });
for (const status of [true, false]) {
  const input = { field: 'generic_selection', selection: lifecycle, status };
  assert.equal(resolveCollectionCell({ ...input, value: 'closing' }, ordinary).text, '结算中');
  assert.throws(() => resolveCollectionCell({ ...input, value: 'unknown' }, ordinary), { name: 'ContractGapError' });
  assert.throws(() => resolveCollectionCell({ ...input, value: 'closing', selection: [{ value: 'closing', label: ' ' }] }, ordinary), { name: 'ContractGapError' });
  assert.throws(() => resolveCollectionCell({ ...input, value: 'closing', selection: [] }, ordinary), { name: 'ContractGapError' });
  assert.equal(resolveCollectionCell({ ...input, value: null }, ordinary).text, FIELD_VALUE_EMPTY_TEXT);
}
assert.deepEqual(resolveCollectionCell({ field: 'plain', value: 'hello', status: false }, ordinary), ordinary('plain', 'hello'));
assert.equal(resolveCollectionCell({ field: 'operation_strategy', value: 'joint', selection: operationStrategy, status: false }, ordinary).text, '联营项目');
for (const status of [true, false]) {
  assert.equal(resolveCollectionCell({ field: 'empty', value: false, selection: lifecycle, status }, ordinary).text, FIELD_VALUE_EMPTY_TEXT);
}
const projected = collectColumnSelections([{ name: 'state', selection: [] }, { name: 'plain' }]);
assert.deepEqual(projected, { state: [] });
assert.throws(() => resolveCollectionCell({ field: 'state', value: 'unknown', selection: projected.state, status: true }, ordinary), { name: 'ContractGapError' });
console.log('[collection_kanban_selection_label_test] PASS assertions=25');

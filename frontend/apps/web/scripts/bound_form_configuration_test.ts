import { summarizeBoundPatches } from '../src/pages/contractForm/boundFormConfiguration';
import assert from 'node:assert/strict';
import { bindNode, boundNodes, editBoundField, groupBoundField, orderBoundField } from '../src/pages/contractForm/boundFormConfiguration';
import type { ContractV2Container } from '../src/app/contracts/v2/types';
import { nativeChildSegments } from '../src/components/template/nativeChildSequence';
const field = (position: number) => ({ type: 'field', containerType: 'field', name: 'same_name', label: 'Name',
  nativeLocator: `/form/group/field[${position}]`, occurrenceIndex: position, children: [] }) as unknown as ContractV2Container;
const parent = { type: 'group', containerType: 'group', name: '', nativeLocator: '/form/group', occurrenceIndex: 1,
  children: [field(1), field(2)] } as unknown as ContractV2Container;
const rows = boundNodes([parent]);
assert.equal(rows.length, 3);
const patch = editBoundField([], parent.children[1], { label: 'Second', visible: false });
assert.equal(patch[0].target, '/form/group/field[2]');
assert.equal(patch[0].expected.occurrence_index, 2);
assert.equal(bindNode(parent).expected.name, '');
const ordered = orderBoundField(patch, parent, parent.children[1], -1);
assert.deepEqual(ordered[1].order, ['/form/group/field[2]', '/form/group/field[1]']);
const grouped = groupBoundField(ordered, parent, parent.children[1], 'Contacts');
assert.deepEqual(grouped[1].group?.members, ['/form/group/field[2]']);
assert.deepEqual(grouped[0], patch[0]);
assert.equal(ordered[1].group, undefined, 'draft input must remain immutable');
assert.throws(() => groupBoundField(grouped, parent, parent.children[0], 'Other'), /同一区域/);
assert.throws(() => bindNode({ ...parent, nativeLocator: undefined }), /稳定身份/);
console.log('[bound_form_configuration_test] PASS cases=7');
for (const types of [['field', 'group', 'field'], ['field', 'field', 'group'], ['group', 'field', 'field'], ['field', 'button', 'widget', 'group']]) {
  const segments = nativeChildSegments(types, (type) => type);
  assert.deepEqual(segments.flatMap((segment) => segment.nodes), types);
  assert(segments.every((segment, index) => index === 0 || segment.kind !== segments[index - 1].kind));
}
assert.deepEqual(nativeChildSegments(['group', 'field', 'field'], (type) => type), [
  { kind: 'container', nodes: ['group'] }, { kind: 'field', nodes: ['field', 'field'] },
]);
console.log('[bound_form_configuration_test] PASS ordered adjacent-field batches cases=5');

const summary = summarizeBoundPatches([parent], grouped);
assert.equal(summary.length, 4);
assert(summary.some((line) => line.startsWith('标签：') && line.includes('Second')));
assert(summary.some((line) => line.startsWith('显隐：') && line.endsWith('隐藏')));
assert(summary.some((line) => line.startsWith('顺序：') && line.includes(' → ')));
assert(summary.some((line) => line.startsWith('分组：Contacts')));
console.log('[bound_form_configuration_test] PASS summary categories=4');

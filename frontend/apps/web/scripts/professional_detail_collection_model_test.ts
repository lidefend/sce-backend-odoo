import assert from 'node:assert/strict';
import {
  detailCollectionAuthority,
  isProfessionalDetailCollectionField,
} from '../src/components/professional-fields/professionalDetailCollectionModel';
import {
  createOne2manyRelationPopupAuthority,
  createOne2manyRelationRequestAuthority,
  isExplicitOne2manyRelationPopupClose,
  isExplicitOne2manyRelationPopupOpen,
  one2manyRelationDependencyKey,
  preserveSelectedOne2manyRelationOption,
} from '../src/components/template/one2manyRelationQuery';
import {
  analyzeDynamicRelationDomain,
  dynamicRelationDomainFromDescriptor,
} from '../src/pages/contractForm/relationDescriptor';

const modes = ['task', 'workspace'] as const;
const profiles = ['create', 'edit', 'readonly'] as const;
let matrix = 0;
for (const presentationMode of modes) {
  for (const renderProfile of profiles) {
    const field = {
      componentKey: 'sc.relation.table', type: 'one2many', name: 'line_ids',
      presentationMode, renderProfile, descriptor: { relation: 'x.line' },
    } as never;
    const adapter = {
      visibleOne2manyRows: () => [{ key: '1', values: {} }],
      one2manyColumns: () => [{ name: 'name', label: 'Name', ttype: 'char', required: true }],
      one2manyCanCreate: () => renderProfile !== 'readonly',
      one2manyCanInlineEdit: () => renderProfile === 'edit',
      removedOne2manyRows: () => [],
      showOne2manyErrors: renderProfile !== 'readonly',
      one2manySummary: () => '1 line',
    } as never;
    assert.equal(isProfessionalDetailCollectionField(field), true);
    const authority = detailCollectionAuthority(field, adapter);
    assert.equal(authority.relationModel, 'x.line');
    assert.equal(authority.rowCount, 1);
    assert.equal(authority.columnCount, 1);
    assert.equal(authority.canCreate, renderProfile !== 'readonly');
    assert.equal(authority.canInlineEdit, renderProfile === 'edit');
    matrix += 1;
  }
}
assert.equal(matrix, 6);
assert.equal(isProfessionalDetailCollectionField({ componentKey: 'sc.relation.table', type: 'many2many' } as never), false);
assert.throws(() => detailCollectionAuthority({ componentKey: 'sc.table.data', type: 'one2many' } as never, {} as never), /PROFESSIONAL_DETAIL_COLLECTION_UNSUPPORTED/);

const requestAuthority = createOne2manyRelationRequestAuthority();
const firstRequest = requestAuthority.begin('line:1:partner_id');
const secondRequest = requestAuthority.begin('line:1:partner_id');
assert.equal(requestAuthority.isCurrent('line:1:partner_id', firstRequest), false);
assert.equal(requestAuthority.isCurrent('line:1:partner_id', secondRequest), true);
requestAuthority.invalidate('line:1:partner_id');
assert.equal(requestAuthority.isCurrent('line:1:partner_id', secondRequest), false);
const pendingSearchRequest = requestAuthority.begin('line:2:partner_id');
const clearSearchRequest = requestAuthority.begin('line:2:partner_id');
assert.equal(requestAuthority.isCurrent('line:2:partner_id', pendingSearchRequest), false);
assert.equal(requestAuthority.isCurrent('line:2:partner_id', clearSearchRequest), true);
const pendingClosedRequest = requestAuthority.begin('line:3:partner_id');
requestAuthority.invalidate('line:3:partner_id');
const reopenedRequest = requestAuthority.begin('line:3:partner_id');
assert.equal(requestAuthority.isCurrent('line:3:partner_id', pendingClosedRequest), false);
assert.equal(requestAuthority.isCurrent('line:3:partner_id', reopenedRequest), true);

const popupAuthority = createOne2manyRelationPopupAuthority();
assert.equal(popupAuthority.update('line:1:partner_id', 'desktop-primary', true), 'opened');
assert.equal(popupAuthority.update('line:1:partner_id', 'desktop-primary', true), 'unchanged');
assert.equal(popupAuthority.update('line:1:partner_id', 'desktop-clone', false), 'unchanged');
assert.equal(popupAuthority.update('line:1:partner_id', 'desktop-clone', true), 'unchanged');
assert.equal(popupAuthority.update('line:1:partner_id', 'desktop-primary', false), 'unchanged');
assert.equal(popupAuthority.update('line:1:partner_id', 'desktop-clone', false), 'closed');
assert.equal(popupAuthority.isOpen('line:1:partner_id'), false);
assert.equal(popupAuthority.update('line:1:partner_id', 'desktop-replacement', true), 'opened');
assert.equal(popupAuthority.isOpen('line:1:partner_id'), true);
assert.equal(isExplicitOne2manyRelationPopupClose('keydown-esc'), true);
assert.equal(isExplicitOne2manyRelationPopupClose('document'), false);
assert.equal(isExplicitOne2manyRelationPopupClose('trigger-element-click'), false);
assert.equal(isExplicitOne2manyRelationPopupClose('trigger-element-blur'), false);
assert.equal(isExplicitOne2manyRelationPopupClose('owner-unmount'), false);
assert.equal(isExplicitOne2manyRelationPopupClose('component-sync'), false);
assert.equal(isExplicitOne2manyRelationPopupOpen('trigger-element-click'), true);
assert.equal(isExplicitOne2manyRelationPopupOpen('component-sync'), false);
popupAuthority.clear();
assert.equal(popupAuthority.update('line:1:partner_id', 'mobile', true), 'opened');
assert.equal(popupAuthority.isOpen('line:1:partner_id'), true);

assert.deepEqual(preserveSelectedOne2manyRelationOption({
  incoming: [],
  previous: [{ value: 7, label: '已选择记录' }],
  currentValue: 7,
}), [{ value: 7, label: '已选择记录' }]);

const values = { project_id: 9, note: '初始备注' };
const dependencyKey = () => one2manyRelationDependencyKey({
  relation: 'x.catalog',
  canRead: true,
  domainSupported: true,
  dependencies: ['parent.project_id'],
  resolveValue: (dependency) => values[dependency.replace('parent.', '') as keyof typeof values],
});
const initialDependencyKey = dependencyKey();
values.note = '修改备注';
assert.equal(dependencyKey(), initialDependencyKey);
values.project_id = 10;
assert.notEqual(dependencyKey(), initialDependencyKey);

const supportedDomain = { type: 'many2one', domain: "[('project_id', '=', parent.project_id)]" } as never;
assert.deepEqual(analyzeDynamicRelationDomain(supportedDomain), {
  supported: true,
  dependencies: ['parent.project_id'],
});
const unsupportedDomain = { type: 'many2one', domain: "['|', ('project_id', '=', parent.project_id)]" } as never;
assert.equal(analyzeDynamicRelationDomain(unsupportedDomain).supported, false);
assert.deepEqual(dynamicRelationDomainFromDescriptor({
  descriptor: unsupportedDomain,
  resolveDependencyValue: () => 9,
  normalizeDependencyValue: (_field, value) => value,
  currentFieldValue: () => false,
}), [['id', '=', -1]]);

console.log(`[professional_detail_collection_model_test] PASS matrix=${matrix} counterexamples=7`);

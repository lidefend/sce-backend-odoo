import { strict as assert } from 'node:assert';
import { resolveProductPageHeaderModel, type ProductPageHeaderAction } from '../src/app/presentation/productPageHeader';
import { resolveCanonicalHeaderActionPresentation } from '../src/pages/contractForm/contractFormHeaderCanonicalActions';
import type { CanonicalFormAction } from '../src/app/presentation/canonicalFormRenderModel';
import type { CanonicalFormFloorplan } from '../src/app/presentation/canonicalFormFloorplan';

const save: ProductPageHeaderAction = { key: 'save', label: '保存', semantic: 'save', enabled: true };
const submit: ProductPageHeaderAction = { key: 'submit', label: '提交', semantic: 'submit', enabled: true };
const base = {
  title: '项目', subtitle: '', breadcrumb: ['项目中心'], presentationMode: 'workspace' as const,
  renderProfile: 'edit' as const, dirtyState: 'clean' as const, statusbar: false,
  overflowActions: [], exitAction: null, variant: 'standalone' as const,
};

assert.equal(resolveProductPageHeaderModel({ ...base, primaryActions: [save] }).primaryAction?.key, 'save');
assert.equal(resolveProductPageHeaderModel({ ...base, renderProfile: 'readonly', primaryActions: [submit] }).primaryAction?.key, 'submit');
assert.throws(() => resolveProductPageHeaderModel({ ...base, primaryActions: [save, submit] }), /PRIMARY_ACTION_MULTIPLE/);
assert.throws(() => resolveProductPageHeaderModel({ ...base, renderProfile: 'readonly', primaryActions: [save] }), /READONLY_SAVE_FORBIDDEN/);
assert.throws(() => resolveProductPageHeaderModel({ ...base, title: ' ', primaryActions: [] }), /TITLE_REQUIRED/);
assert.deepEqual(resolveProductPageHeaderModel({ ...base, breadcrumb: [' 项目 ', ''], primaryActions: [] }).breadcrumb, ['项目']);
for (const presentationMode of ['task', 'workspace'] as const) {
  for (const renderProfile of ['create', 'edit', 'readonly'] as const) {
    const result = resolveProductPageHeaderModel({ ...base, presentationMode, renderProfile, primaryActions: [] });
    assert.equal(result.presentationMode, presentationMode);
    assert.equal(result.renderProfile, renderProfile);
  }
}

const saveAction = {
  key: 'form.save', label: '保存草稿', visible: true, enabled: true, tier: 'secondary',
  actionRef: { actionId: 'form.save' },
} as CanonicalFormAction;
const submitAction = {
  key: 'submit', label: '提交', visible: true, enabled: true, tier: 'primary',
  actionRef: { actionId: 'submit' },
} as CanonicalFormAction;
const taskFloorplan = {
  decisionMode: true,
  directActions: [saveAction, submitAction],
  overflowActions: [saveAction],
} as CanonicalFormFloorplan;
const createHeader = resolveCanonicalHeaderActionPresentation({
  floorplan: taskFloorplan, actions: [saveAction, submitAction], renderProfile: 'create', rendererActive: true, dirty: false,
});
assert.equal(createHeader.localSavePrimary, true);
assert.deepEqual(createHeader.direct.map((action) => action.actionRef.actionId), ['submit']);
assert.deepEqual(createHeader.overflow, []);
const readonlyHeader = resolveCanonicalHeaderActionPresentation({
  floorplan: taskFloorplan, actions: [saveAction, submitAction], renderProfile: 'readonly', rendererActive: true, dirty: false,
});
assert.equal(readonlyHeader.localSavePrimary, false);
assert.deepEqual(readonlyHeader.direct.map((action) => action.actionRef.actionId), ['form.save', 'submit']);
const deniedSaveAction = { ...saveAction, enabled: false } as CanonicalFormAction;
const blockedHeader = resolveCanonicalHeaderActionPresentation({
  floorplan: { ...taskFloorplan, directActions: [deniedSaveAction] },
  actions: [deniedSaveAction], renderProfile: 'edit', rendererActive: true, dirty: true,
});
assert.equal(blockedHeader.localSavePrimary, false);
assert.deepEqual(blockedHeader.direct.map((action) => action.actionRef.actionId), ['form.save']);
const dirtyEditHeader = resolveCanonicalHeaderActionPresentation({
  floorplan: taskFloorplan, actions: [saveAction, submitAction], renderProfile: 'edit', rendererActive: true, dirty: true,
});
assert.equal(dirtyEditHeader.localSavePrimary, true);
assert.deepEqual(dirtyEditHeader.direct.map((action) => action.actionRef.actionId), ['submit']);
const cleanEditHeader = resolveCanonicalHeaderActionPresentation({
  floorplan: taskFloorplan, actions: [saveAction, submitAction], renderProfile: 'edit', rendererActive: true, dirty: false,
});
assert.equal(cleanEditHeader.localSavePrimary, true);
assert.deepEqual(cleanEditHeader.direct.map((action) => action.actionRef.actionId), ['submit']);
console.log('[product_page_header_model_test] PASS cases=24');

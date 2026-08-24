import { strict as assert } from 'node:assert';
import { resolveProductPageHeaderModel, type ProductPageHeaderAction } from '../src/app/presentation/productPageHeader';

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
console.log('[product_page_header_model_test] PASS cases=12');

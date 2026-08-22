import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { formatDisplayValue, resolveLocalizedDisplayValue, stripInternalMigrationMetadata } from '../../frontend/apps/web/src/utils/display.ts';
import {
  mergeWorkspaceNavigationLinks,
  resolveWorkspaceNavigationLink,
} from '../../frontend/apps/web/src/app/workspaceHomeNavigation.ts';

const localized = { zh_CN: '项目甲', en_US: 'Project A' };
assert.equal(resolveLocalizedDisplayValue(localized, { locale: 'zh-CN' }), '项目甲');
assert.equal(resolveLocalizedDisplayValue(localized, { locale: 'en-US' }), 'Project A');
assert.equal(resolveLocalizedDisplayValue({ fr_FR: 'Projet' }, { locale: 'de-DE' }), 'Projet');
assert.equal(resolveLocalizedDisplayValue("{'zh_CN': '合同甲', 'en_US': 'Contract A'}", { locale: 'zh_CN' }), '合同甲');
assert.equal(
  resolveLocalizedDisplayValue("HT-001 / {'zh_CN': '合同甲', 'en_US': 'Contract A'}", { locale: 'zh_CN' }),
  'HT-001 / 合同甲',
);
assert.equal(resolveLocalizedDisplayValue('普通文本', { locale: 'zh_CN' }), '普通文本');
assert.equal(resolveLocalizedDisplayValue('{broken}', { locale: 'zh_CN', emptyText: '--' }), '--');
assert.equal(resolveLocalizedDisplayValue({}, { locale: 'zh_CN', emptyText: '--' }), '--');
assert.equal(formatDisplayValue([7, localized], { type: 'many2one' }, { locale: 'zh_CN' }), '项目甲');
assert.equal(formatDisplayValue([7, localized], undefined, { locale: 'zh_CN' }), '项目甲');
assert.equal(formatDisplayValue([1, 2, 3], undefined, { locale: 'zh_CN' }), '1, 2, 3');
assert.equal(
  stripInternalMigrationMetadata('[migration:general_contract] legacy_record_id=e431f445\n公司综合平台\n业务备注'),
  '公司综合平台\n业务备注',
);
assert.equal(
  stripInternalMigrationMetadata('[migration:direct_payment_apply_formal]\n真实付款办理备注'),
  '真实付款办理备注',
  'a leading migration marker without a legacy id must not leak into product display',
);
assert.equal(
  formatDisplayValue('[migration:general_contract] legacy_record_id=e431f445\n公司综合平台\n业务备注'),
  '公司综合平台\n业务备注',
);
assert.equal(
  stripInternalMigrationMetadata('业务备注\n[migration:general_contract] legacy_record_id=e431f445'),
  '业务备注\n[migration:general_contract] legacy_record_id=e431f445',
  'only an authoritative leading internal marker may be removed',
);
assert.deepEqual(
  resolveWorkspaceNavigationLink({
    key: 'workspace',
    label: '工作台',
    children: [{ key: 'overview', label: '数据总览', route: '/a/42?menu_id=7' }],
  }),
  {
    key: 'overview:/a/42?menu_id=7',
    label: '数据总览',
    detail: '工作台',
    route: '/a/42?menu_id=7',
  },
  'a directory label must not be paired with a descendant route',
);
assert.deepEqual(
  mergeWorkspaceNavigationLinks(
    [{ key: 'overview', label: '数据总览', detail: '工作台', route: '/a/42?menu_id=7' }],
    [{ key: 'legacy-shortcut', label: '工作台', detail: '数据总览', route: '/a/42?menu_id=7' }],
  ),
  [{ key: 'overview', label: '数据总览', detail: '工作台', route: '/a/42?menu_id=7' }],
  'a shortcut cannot override the menu-authoritative identity for the same route',
);

const formSource = readFileSync(
  new URL('../../frontend/apps/web/src/pages/ContractFormPage.vue', import.meta.url),
  'utf8',
);
assert.match(formSource, /resolvePrimaryBusinessActionState\(\{/);
assert.doesNotMatch(
  formSource,
  /showPrimaryBusinessFormAction = computed\(\(\) => canSave\.value/,
  'normalized business actions must not be hidden merely because the readonly form cannot save',
);

const listPageSource = readFileSync(
  new URL('../../frontend/apps/web/src/pages/ListPage.vue', import.meta.url),
  'utf8',
);
assert.match(
  listPageSource,
  /return resolveListDisplayField\(field, columnOption\(field\)\);/,
  'list cells must consume the API display field rather than the underlying sort/filter/aggregate value field',
);

for (const relativePath of [
  '../../frontend/apps/web/src/pages/listPage/listCellPresentation.ts',
  '../../frontend/apps/web/src/pages/listPage/listColumnWidth.ts',
  '../../frontend/apps/web/src/app/pageIdentity.ts',
]) {
  const source = readFileSync(new URL(relativePath, import.meta.url), 'utf8');
  assert.match(source, /resolveLocalizedDisplayValue/);
}

console.log('FRONTEND_LOCALIZED_DISPLAY_CONTRACT=PASS');

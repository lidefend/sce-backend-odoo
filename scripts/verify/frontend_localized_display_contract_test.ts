import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { formatDisplayValue, resolveLocalizedDisplayValue } from '../../frontend/apps/web/src/utils/display.ts';

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

const formSource = readFileSync(
  new URL('../../frontend/apps/web/src/pages/ContractFormPage.vue', import.meta.url),
  'utf8',
);
assert.match(formSource, /showPrimaryBusinessFormAction = computed\(\(\) => canSave\.value/);

for (const relativePath of [
  '../../frontend/apps/web/src/pages/listPage/listCellPresentation.ts',
  '../../frontend/apps/web/src/pages/listPage/listColumnWidth.ts',
  '../../frontend/apps/web/src/app/pageIdentity.ts',
]) {
  const source = readFileSync(new URL(relativePath, import.meta.url), 'utf8');
  assert.match(source, /resolveLocalizedDisplayValue/);
}

console.log('FRONTEND_LOCALIZED_DISPLAY_CONTRACT=PASS');

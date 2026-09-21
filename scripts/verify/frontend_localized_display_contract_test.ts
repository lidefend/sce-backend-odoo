import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';

import { formatDisplayValue, resolveLocalizedDisplayValue, stripInternalMigrationMetadata } from '../../frontend/apps/web/src/utils/display.ts';
import {
  COLLECTION_NUMERIC_EMPTY_TEXT,
  FIELD_VALUE_EMPTY_TEXT,
  FIELD_VALUE_FALSE_TEXT,
  FIELD_VALUE_TRUE_TEXT,
  containsAttachmentReference,
  formatNumericFieldValue,
} from '../../frontend/apps/web/src/utils/fieldSemantics.ts';
import { presentListCell } from '../../frontend/apps/web/src/pages/listPage/listCellPresentation.ts';
import { semanticBoolean } from '../../frontend/apps/web/src/utils/semantic.ts';
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

const listColumn = (type: string) => ({ field: 'f', label: 'F', type });

// 字段语义单一权威：集合（列表）与记录／表单必须给出同一空值、布尔与数值口径。
assert.equal(formatDisplayValue('', { type: 'char' }), FIELD_VALUE_EMPTY_TEXT);
assert.equal(presentListCell({ raw: '', column: listColumn('char') }).text, FIELD_VALUE_EMPTY_TEXT);
assert.equal(semanticBoolean(null), FIELD_VALUE_EMPTY_TEXT);
assert.equal(formatDisplayValue(null, { type: 'char' }), FIELD_VALUE_EMPTY_TEXT);

assert.equal(formatDisplayValue(true, { type: 'boolean' }), FIELD_VALUE_TRUE_TEXT);
assert.equal(presentListCell({ raw: true, column: listColumn('boolean') }).text, FIELD_VALUE_TRUE_TEXT);
assert.equal(semanticBoolean(false), FIELD_VALUE_FALSE_TEXT);

assert.equal(formatNumericFieldValue('1234.5', 'float'), '1,234.50');
assert.equal(formatNumericFieldValue('1234', 'integer'), '1,234');
assert.equal(formatDisplayValue(1234.5, { type: 'float' }), '1,234.50');

// 日期在两路径一致；datetime 是声明式档位差异（集合 compact、记录／表单 full），不是各写一套规则。
assert.equal(formatDisplayValue('2026-09-21', { type: 'date' }), '2026-09-21');
assert.equal(presentListCell({ raw: '2026-09-21', column: listColumn('date') }).text, '2026-09-21');
assert.equal(formatDisplayValue('2026-09-21T10:17:01Z', { type: 'datetime' }), '2026-09-21 10:17:01');
assert.equal(presentListCell({ raw: '2026-09-21T10:17:01Z', column: listColumn('datetime') }).text, '2026-09-21 10:17');
assert.doesNotMatch(
  formatDisplayValue('2026-09-21T10:17:01Z', { type: 'datetime' }),
  /T\d{2}:\d{2}:\d{2}Z/,
  '机器格式的 ISO 时间戳不得泄漏到记录／表单取值呈现',
);

// 集合数值列缺少取值是已登记的集合密度策略，不是每条路径各自的分支。
assert.equal(
  presentListCell({ raw: '', column: listColumn('float'), numeric: true }).text,
  COLLECTION_NUMERIC_EMPTY_TEXT,
);
assert.equal(formatDisplayValue('', { type: 'float' }), FIELD_VALUE_EMPTY_TEXT);

assert.equal(containsAttachmentReference('合同.pdf | /web/content/123'), true);
assert.equal(formatDisplayValue('合同.pdf | /web/content/123', { type: 'char' }), '合同.pdf');

// 权威模块之外不得再出现空值／布尔文案字面量或各自一套的日期、附件检测正则。
const frontendSrc = new URL('../../frontend/apps/web/src/', import.meta.url);
const authorityRelativePath = 'utils/fieldSemantics.ts';
const walk = (directory: URL): string[] => readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
  const child = new URL(entry.name, directory);
  if (entry.isDirectory()) return walk(new URL(`${entry.name}/`, directory));
  return /\.(?:ts|vue|js)$/.test(entry.name) ? [child] : [];
});
const presentationSources = walk(frontendSrc);
assert.ok(presentationSources.length > 200, '前端源码盘点不得退化为空集合');
for (const source of presentationSources) {
  const relativePath = decodeURIComponent(source.pathname.split('/src/')[1] || '');
  if (relativePath === authorityRelativePath) continue;
  const text = readFileSync(source, 'utf8');
  assert.doesNotMatch(text, /'--'|"--"/, `${relativePath} 不得自行定义空值文案`);
  assert.doesNotMatch(text, /'是'|'否'|"是"|"否"/, `${relativePath} 不得自行定义布尔文案`);
  assert.doesNotMatch(
    text,
    /legacy-file-id\|legacy-file|legacy-file\|https\?\|file/,
    `${relativePath} 不得自行重写附件引用检测`,
  );
  assert.doesNotMatch(text, /\^\(\\d\{4\}-\\d\{2\}-\\d\{2\}\)/, `${relativePath} 不得自行重写日期解析`);
}

console.log(`FRONTEND_FIELD_SEMANTICS_AUTHORITY=PASS sources=${presentationSources.length}`);
console.log('FRONTEND_LOCALIZED_DISPLAY_CONTRACT=PASS');

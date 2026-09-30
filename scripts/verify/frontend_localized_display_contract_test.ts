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
import { resolveReadonlyEmptyText } from '../../frontend/apps/web/src/components/professional-fields/professionalBaseFieldModel.ts';
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

// JSON 字段没有客户端编辑控件，只读展示必须给出真实 JSON 文本与空值口径，
// 不得退化为空文本，也不得把对象字符串化后冒充可编辑输入。
assert.equal(
  formatDisplayValue({ seq: 'A-1', level: 2 }, { type: 'json' }),
  '{"seq":"A-1","level":2}',
);
assert.equal(formatDisplayValue({ seq: 'A-1' }, { ttype: 'json' }), '{"seq":"A-1"}');
assert.equal(formatDisplayValue([1, 2], { type: 'json' }), '[1,2]');
assert.equal(formatDisplayValue('{"a":1}', { type: 'json' }), '{"a":1}');
assert.equal(formatDisplayValue({}, { type: 'json' }), FIELD_VALUE_EMPTY_TEXT);
assert.equal(formatDisplayValue([], { type: 'json' }), FIELD_VALUE_EMPTY_TEXT);
assert.equal(formatDisplayValue(false, { type: 'json' }), FIELD_VALUE_EMPTY_TEXT);
assert.equal(formatDisplayValue(null, { type: 'json' }), FIELD_VALUE_EMPTY_TEXT);
assert.equal(formatDisplayValue('   ', { type: 'json' }), FIELD_VALUE_EMPTY_TEXT);
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

// 权威模块之外不得再出现空值／布尔文案字面量（含转义、拼接、repeat、模板等等价写法），
// 也不得在已收口的消费方里自行重写数值／时间格式化或日期、附件检测正则。
const frontendSrc = new URL('../../frontend/apps/web/src/', import.meta.url);
const authorityRelativePath = 'utils/fieldSemantics.ts';
const walk = (directory: URL): string[] => readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
  const child = new URL(entry.name, directory);
  if (entry.isDirectory()) return walk(new URL(`${entry.name}/`, directory));
  return /\.(?:ts|vue|js)$/.test(entry.name) ? [child] : [];
});
const presentationSources = walk(frontendSrc);
assert.ok(presentationSources.length > 200, '前端源码盘点不得退化为空集合');

const sourceText = (relativePath: string) => readFileSync(new URL(relativePath, frontendSrc), 'utf8');
const readPresentationSource = (source: URL) => decodeURIComponent(source.pathname.split('/src/')[1] || '');
const decodeEscapes = (text: string) => text.replace(/\\u([0-9a-fA-F]{4})/g, (_, hex: string) => String.fromCharCode(parseInt(hex, 16)));
const flatten = (text: string) => decodeEscapes(text).replace(/\s+/g, '');

// 字面量、转义、拼接与 repeat 的等价写法都必须被抓到；仅带引号/反引号的纯文案才算文案字面量。
const EMPTY_TEXT_LITERAL_PATTERNS = [/['"`]--['"`]/, /['"`]-['"`]\+['"`]-['"`]/, /['"`]-['"`]\.repeat\(2\)/];
const BOOLEAN_TEXT_LITERAL_PATTERNS = [/['"`]是['"`]/, /['"`]否['"`]/];

for (const source of presentationSources) {
  const relativePath = readPresentationSource(source);
  if (relativePath === authorityRelativePath) continue;
  const text = readFileSync(source, 'utf8');
  const flat = flatten(text);
  for (const pattern of EMPTY_TEXT_LITERAL_PATTERNS) {
    assert.doesNotMatch(flat, pattern, `${relativePath} 不得自行定义空值文案`);
  }
  for (const pattern of BOOLEAN_TEXT_LITERAL_PATTERNS) {
    assert.doesNotMatch(flat, pattern, `${relativePath} 不得自行定义布尔文案`);
  }
  assert.doesNotMatch(
    text,
    /legacy-file-id\|legacy-file|legacy-file\|https\?\|file/,
    `${relativePath} 不得自行重写附件引用检测`,
  );
  assert.doesNotMatch(text, /\^\(\\d\{4\}-\\d\{2\}-\\d\{2\}\)/, `${relativePath} 不得自行重写日期解析`);
}

// 附件引用与日期解析的等价重写可能不再带引号字面量或逐字正则，因此按「谁可以拥有该解析规则」
// 登记：命中即必须显式登记，否则说明新增了第二处权威。登记项即下一批的收口清单。
const ATTACHMENT_SOURCE_REGISTRY: Record<string, string> = {
  'utils/fieldSemantics.ts': 'authority',
  'utils/filePreview.ts': 'registered: attachment URL parsing / download entry, not a value-presentation authority',
  'components/attachment/AttachmentViewer.vue': 'registered: attachment viewer URL handling, not a value-presentation authority',
  'components/template/X2ManyRelationRenderer.vue':
    'registered: relation collection renderer attachment links consumed as already-resolved values',
};
const TEMPORAL_PARSE_REGISTRY: Record<string, string> = {
  'utils/fieldSemantics.ts': 'authority',
  'pages/contractForm/professionalCollaborationModel.ts':
    'registered: collaboration audit timestamp formatting, unconverted; needs its own batch decision',
};
for (const source of presentationSources) {
  const relativePath = readPresentationSource(source);
  const text = readFileSync(source, 'utf8');
  const withoutBackslashes = decodeEscapes(text).replace(/\\/g, '');
  if (withoutBackslashes.includes('web/content') || withoutBackslashes.includes('legacy-file')) {
    assert.ok(
      relativePath in ATTACHMENT_SOURCE_REGISTRY,
      `${relativePath} 出现了附件引用解析来源；必须走权威或在该守卫中登记理由`,
    );
  }
  if (/\\d\{4\}/.test(text)) {
    assert.ok(
      relativePath in TEMPORAL_PARSE_REGISTRY,
      `${relativePath} 出现了日期解析规则；必须走权威或在该守卫中登记理由`,
    );
  }
}

// 复核点名「尚未收口」的取值呈现消费方：逐条锁定其本地回退与格式化事实。
// 锁定即「已知、有意保留、需单独决策」；任何漂移都必须先更新登记，不得静默变化。
const PENDING_VALUE_PRESENTATION_CONSUMERS: Record<string, readonly string[]> = {
  'app/presentation/productMyWorkPresentation.ts': ["'未填写'", "'未知'", '.slice(0, 16)'],
  'views/ApiKeyManagementView.vue': ["'—'", 'toISOString().slice(0, 19)'],
  'components/professional-fields/PaymentSettlementIntroduceDialog.vue': ["'—'"],
  'components/boq/BoqImportPreviewPanel.vue': ["'—'"],
  'pages/contractForm/RelationSearchDialog.vue': ["'未填写'"],
};
for (const [relativePath, markers] of Object.entries(PENDING_VALUE_PRESENTATION_CONSUMERS)) {
  const text = sourceText(relativePath);
  for (const marker of markers) {
    assert.ok(
      text.includes(marker),
      `${relativePath} 的未收口取值呈现事实已变化（缺少 ${marker}）；必须重新决策，不得静默漂移`,
    );
  }
}

// 已收口消费方必须 import 权威，且不得自行重写数值／时间格式化；
// 例外必须登记在此（含理由），登记即意味着「已知、有意保留、需另行决策」，不是静默放过。
const AUTHORITY_CONSUMERS = [
  'utils/display.ts',
  'utils/semantic.ts',
  'pages/listPage/listCellPresentation.ts',
  'pages/listPage/listColumnWidth.ts',
  'pages/ListPage.vue',
  'app/contracts/actionViewActivityContract.ts',
  'app/contracts/actionViewAnalysisContract.ts',
  'app/presentation/collectionStatusPresentation.ts',
  'pages/contractForm/one2manyUtils.ts',
  'pages/contractForm/RelationSearchDialog.vue',
  'views/ActionView.vue',
  'components/action/ActionSurfaceToolbar.vue',
  'components/page/blocks/BlockRecordTable.vue',
  'components/page/blocks/BlockMetricRow.vue',
  'components/page/blocks/BlockRecordSummary.vue',
  'components/page/blocks/BlockAccordionGroup.vue',
  'components/scene/SceneBlocksRenderer.vue',
  'views/SceneContractBlockGridView.vue',
];
const LOCAL_FORMATTER_PATTERNS = [/toISOString\(/, /Intl\.DateTimeFormat\(/, /toLocaleString\(/, /new Date\(/];
const REGISTERED_LOCAL_FORMATTERS: Record<string, Array<{ pattern: RegExp; reason: string }>> = {
  // one2manyColumnDisplayValue 同时充当内联单元格输入框的 model-value，并入权威记录／表单档位会改变
  // 可编辑行取值显示（且其 datetime 分支产出并非 datetime-local 输入可接受格式），需单独决策后另批处理。
  'pages/contractForm/one2manyUtils.ts': LOCAL_FORMATTER_PATTERNS.map((pattern) => ({
    pattern,
    reason: 'registered: inline cell input model-value shares one function; needs its own batch decision',
  })),
};
let registeredFormatterAllowances = 0;
for (const relativePath of AUTHORITY_CONSUMERS) {
  const text = sourceText(relativePath);
  assert.match(text, /fieldSemantics\.ts/, `${relativePath} 必须消费字段语义权威`);
  const registered = REGISTERED_LOCAL_FORMATTERS[relativePath] || [];
  for (const pattern of LOCAL_FORMATTER_PATTERNS) {
    if (registered.some((entry) => entry.pattern.source === pattern.source)) {
      registeredFormatterAllowances += 1;
      continue;
    }
    assert.doesNotMatch(text, pattern, `${relativePath} 不得自行重写数值／时间格式化（应走权威或登记例外）`);
  }
}

// 表单只读事实的空值文案由契约字段声明（`readonly_empty_text`）决定，未声明的既有页面保持既有回退
// （2026-09-14 受管决定）。该路径是本批已登记的**契约权威例外**：必须保持显式声明，
// 任何改动都会在这里失败并要求同步更新登记，不允许静默改口径。
const FORM_READONLY_EMPTY_TEXT_REGISTRY = [
  { path: 'components/template/FormSection.vue', token: "resolveReadonlyEmptyText(field, '-')", occurrences: 2 },
  { path: 'components/professional-fields/ProfessionalBaseFieldControl.vue', token: "resolveReadonlyEmptyText(props.field, '-')" },
  { path: 'components/template/formSection.mapper.ts', token: "emptyText = '-'" },
  { path: 'pages/contractForm/ContractFormNativeCanvas.vue', token: "resolveReadonlyEmptyText(field, '未填写')" },
];
for (const entry of FORM_READONLY_EMPTY_TEXT_REGISTRY) {
  const matches = sourceText(entry.path).split(entry.token).length - 1;
  assert.equal(
    matches,
    entry.occurrences ?? 1,
    `${entry.path} 的表单只读空值回退已变化：契约权威例外必须显式登记（当前 token=${entry.token}）`,
  );
}
assert.equal(resolveReadonlyEmptyText({ readonlyEmptyText: '尚未生成' }), '尚未生成');
assert.equal(resolveReadonlyEmptyText({}), '—');
assert.equal(resolveReadonlyEmptyText({ readonlyEmptyText: '   ' }, '-'), '-');

// 权威消费方与例外规模必须可被读取者核对，避免「登记」退化为隐藏白名单。
assert.equal(AUTHORITY_CONSUMERS.length, 18);
assert.ok(registeredFormatterAllowances > 0, '登记例外必须非空且逐条对应真实文件，否则应删除登记');

console.log(`FRONTEND_FIELD_SEMANTICS_AUTHORITY=PASS sources=${presentationSources.length} consumers=${AUTHORITY_CONSUMERS.length} registered_formatter_allowances=${registeredFormatterAllowances}`);
console.log('FRONTEND_LOCALIZED_DISPLAY_CONTRACT=PASS');

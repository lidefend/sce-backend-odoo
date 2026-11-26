import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createServer } from 'node:http';
import path from 'node:path';
import { build } from 'esbuild';
import { compileScript, parse } from 'vue/compiler-sfc';

const root = process.cwd();
const controlFile = `${root}/frontend/apps/web/src/components/professional-fields/ProfessionalBusinessValueControl.vue`;
const baseControlFile = `${root}/frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue`;
const fieldValueFile = `${root}/frontend/apps/web/src/components/FieldValue.vue`;
const formSectionFile = `${root}/frontend/apps/web/src/components/template/FormSection.vue`;
const presentationFile = `${root}/frontend/apps/web/src/app/presentation/businessValuePresentation.ts`;
const listFile = `${root}/frontend/apps/web/src/pages/listPage/listCellPresentation.ts`;
const kanbanFile = `${root}/frontend/apps/web/src/app/presentation/collectionKanbanPresentation.ts`;

const output = await build({
  stdin: {
    contents: `
import { createApp, h } from 'vue';
import BusinessValue from ${JSON.stringify(controlFile)};
import BaseField from ${JSON.stringify(baseControlFile)};
import FieldValue from ${JSON.stringify(fieldValueFile)};
import FormSection from ${JSON.stringify(formSectionFile)};
import { presentDeclaredBusinessValue } from ${JSON.stringify(presentationFile)};
import { presentListCell } from ${JSON.stringify(listFile)};
import { presentCollectionKanbanCell } from ${JSON.stringify(kanbanFile)};
import { formatNumericFieldValue } from ${JSON.stringify(`${root}/frontend/apps/web/src/utils/fieldSemantics.ts`)};
import { formatDisplayValue } from ${JSON.stringify(`${root}/frontend/apps/web/src/utils/display.ts`)};

const cases = [
  ['null', null, '--'],
  ['undefined', undefined, '--'],
  ['false', false, '--'],
  ['zero', 0, '0.000 小时'],
  ['one', 1, '1.000 小时'],
  ['one-half', 1.5, '1.500 小时'],
  ['carry', 1.999, '1.999 小时'],
  ['negative', -0.5, '-0.500 小时'],
];
window.durationCases = cases;
window.listOutputs = [];
window.kanbanOutputs = [];
const field = (value, readonly = true, inputValue = value) => ({
  key: 'duration',
  name: 'opaque_hours',
  label: 'Hours',
  type: 'float',
  widget: 'float_time',
  componentKey: 'sc.value.duration',
  digits: [16, 3],
  unit: { kind: 'duration', code: 'hour', label: '小时' },
  value,
  inputValue,
  readonly,
  presentationMode: 'workspace',
  renderProfile: 'readonly',
});
const localizedRelationLabel = { zh_CN: '项目甲', en_US: 'Project A' };
const Host = {
  setup() {
    const durationNodes = cases.flatMap(([key, value]) => [
      h(BusinessValue, {
        key: 'form-' + key,
        field: field(value),
        controlId: 'form-' + key,
        'data-duration-case': key,
      }),
      h('output', {
        key: 'list-' + key,
        'data-list-duration': key,
      }, presentListCell({
        raw: value,
        column: {
          field: 'opaque_hours',
          label: 'Hours',
          type: 'float',
          widget: 'float_time',
          componentKey: 'sc.value.duration',
          digits: [16, 3],
          unit: { kind: 'duration', code: 'hour', label: '小时' },
        },
      }).text),
      h('output', {
        key: 'kanban-' + key,
        'data-kanban-duration': key,
      }, presentCollectionKanbanCell({
        field: 'opaque_hours',
        value,
        columnOptions: [{
          name: 'opaque_hours',
          type: 'float',
          widget: 'float_time',
          componentKey: 'sc.value.duration',
          digits: [16, 3],
          unit: { kind: 'duration', code: 'hour', label: '小时' },
        }],
      }).text),
      ...(key === 'false' ? [
        h(BusinessValue, {
          key: 'edit-false',
          field: {
            ...field(false, false, false),
            presentationMode: 'task',
            renderProfile: 'edit',
          },
          controlId: 'edit-false',
          'data-edit-duration': 'false',
        }),
      ] : []),
      ...(key === 'one-half' ? [
        h(BusinessValue, {
          key: 'edit-one-half',
          field: {
            ...field(1.5, false, 1.5),
            presentationMode: 'task',
            renderProfile: 'edit',
          },
          controlId: 'edit-one-half',
          'data-edit-duration': 'one-half',
        }),
      ] : []),
    ]);
    const percentageField = {
      name: 'completion_ratio',
      label: 'Completion',
      type: 'float',
      componentKey: 'sc.value.percentage',
      digits: [16, 4],
      unit: { kind: 'percent', code: 'percent', label: '%' },
    };
    const quantityField = {
      name: 'declared_quantity',
      label: 'Quantity',
      type: 'float',
      componentKey: 'sc.input.number',
      digits: [16, 6],
    };
    return () => h('main', [
      ...durationNodes,
      h(BusinessValue, {
        field: {
          ...percentageField,
          key: 'percentage',
          value: 12.5,
          inputValue: 12.5,
          readonly: true,
          presentationMode: 'workspace',
          renderProfile: 'readonly',
        },
        controlId: 'percentage',
        'data-percentage-value': 'form',
      }),
      h('output', { 'data-percentage-value': 'list' }, presentListCell({
        raw: 12.5,
        column: { field: percentageField.name, label: 'Completion', ...percentageField },
      }).text),
      h('output', { 'data-percentage-value': 'kanban' }, presentCollectionKanbanCell({
        field: percentageField.name,
        value: 12.5,
        columnOptions: [{ name: percentageField.name, ...percentageField }],
      }).text),
      h('output', { 'data-precision-value': 'form' }, formatDisplayValue(12.5, {
        type: 'float',
        digits: quantityField.digits,
      })),
      h('output', { 'data-precision-value': 'list' }, presentListCell({
        raw: 12.5,
        numericText: formatNumericFieldValue(12.5, 'float', { digits: quantityField.digits }) || '',
        numeric: true,
        column: {
          field: quantityField.name,
          label: 'Quantity',
          type: 'float',
          componentKey: 'sc.input.number',
          digits: quantityField.digits,
        },
      }).text),
      h('output', { 'data-precision-value': 'kanban' }, presentCollectionKanbanCell({
        field: quantityField.name,
        value: 12.5,
        columnOptions: [{ name: quantityField.name, ...quantityField }],
      }).text),
      h('section', { 'data-authority-browser': 'readonly' }, [
        h('div', { 'data-authority-case': 'field-status' }, [
          h(FieldValue, {
            value: 'pending',
            field: {
              type: 'selection',
              componentKey: 'sc.display.status',
              selection: [['pending', '待处理']],
            },
          }),
        ]),
        h('div', { 'data-authority-case': 'field-relation' }, [
          h(FieldValue, {
            value: [7, localizedRelationLabel],
            field: { type: 'many2one' },
          }),
        ]),
        h('div', { 'data-authority-case': 'field-relation-object' }, [
          h(FieldValue, {
            value: { id: 7, display_name: localizedRelationLabel },
            field: { type: 'many2one' },
          }),
        ]),
        h('div', { 'data-authority-case': 'base-status' }, [
          h(BaseField, {
            field: {
              key: 'state',
              name: 'state',
              label: '状态',
              type: 'selection',
              componentKey: 'sc.display.status',
              value: 'pending',
              inputValue: 'pending',
              readonly: true,
              required: false,
              descriptor: {
                type: 'selection',
                selection: [['pending', '待处理']],
              },
            },
            controlId: 'base-state',
            placeholder: '请选择',
          }),
        ]),
        h('div', { 'data-authority-case': 'base-percentage' }, [
          h(BaseField, {
            field: {
              key: 'ratio',
              name: 'ratio',
              label: '比例',
              type: 'float',
              componentKey: 'sc.value.percentage',
              value: 12.5,
              inputValue: 12.5,
              digits: [16, 4],
              unit: { kind: 'percent', code: 'percent', label: '%' },
              readonly: true,
              required: false,
            },
            controlId: 'base-ratio',
            placeholder: '请输入',
          }),
        ]),
        h('div', { 'data-authority-case': 'form-section-relation' }, [
          h(FormSection, {
            title: '关系',
            columns: 1,
            fields: [{
              key: 'project_id',
              name: 'project_id',
              label: '项目',
              type: 'many2one',
              componentKey: 'sc.relation.many2one',
              componentRenderer: 'ProfessionalRelationFieldControl',
              span: 24,
              value: { id: 7, display_name: localizedRelationLabel },
              inputValue: 7,
              readonly: true,
              required: false,
              descriptor: { type: 'many2one' },
            }],
            preferReadonlyFacts: true,
            fillOrphanRows: false,
          }),
        ]),
      ]),
    ]);
  },
};
createApp(Host).mount('#app');
`,
    resolveDir: `${root}/frontend/apps/web`,
    loader: 'js',
  },
  bundle: true,
  write: false,
  platform: 'browser',
  format: 'iife',
  define: {
    __VUE_OPTIONS_API__: 'true',
    __VUE_PROD_DEVTOOLS__: 'false',
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
    'process.env.NODE_ENV': '"production"',
    'import.meta.env': JSON.stringify({ VITE_APP_ENV: 'test' }),
  },
  resolveExtensions: ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.mjs'],
  loader: { '.css': 'empty' },
  alias: {
    vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,
    'tdesign-vue-next': `${root}/frontend/packages/ui/node_modules/tdesign-vue-next`,
  },
  plugins: [{
    name: 'actual-duration-sfc',
    setup(builder) {
      builder.onLoad({ filter: /\.vue$/ }, (args) => {
        const { descriptor } = parse(fs.readFileSync(args.path, 'utf8'), { filename: args.path });
        return {
          contents: compileScript(descriptor, { id: args.path, inlineTemplate: true }).content,
          loader: 'ts',
          resolveDir: path.dirname(args.path),
        };
      });
    },
  }],
  logLevel: 'error',
});

const { launchChromium } = await import('../../../../scripts/verify/playwright_runtime.mjs');
const server = createServer((request, response) => {
  const requestUrl = new URL(request.url || '/', 'http://127.0.0.1');
  if (requestUrl.pathname === '/bundle.js') {
    response.setHeader('content-type', 'text/javascript; charset=utf-8');
    response.end(output.outputFiles[0].text);
    return;
  }
  const locale = requestUrl.searchParams.get('lang') === 'en_US' ? 'en_US' : 'zh_CN';
  response.setHeader('content-type', 'text/html; charset=utf-8');
  response.end(`<!doctype html><html lang="${locale}"><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module" src="/bundle.js"></script></body></html>`);
});
await new Promise((resolve, reject) => {
  server.once('error', reject);
  server.listen(0, '127.0.0.1', resolve);
});
const address = server.address();
assert(address && typeof address !== 'string');
const browser = await launchChromium();
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  let caseCount = 0;
  let authorityCaseCount = 0;
  let assertionCount = 0;
  for (const [locale, expectedRelation] of [['zh_CN', '项目甲'], ['en_US', 'Project A']]) {
    await page.goto(`http://127.0.0.1:${address.port}/?lang=${locale}`);
    await page.setViewportSize({ width: 1440, height: 900 });
    const booted = await page.evaluate(() => Array.isArray(window.durationCases));
    assert.equal(booted, true, `${locale}: browser fixture failed to boot: ${errors.join(' | ')}`);
    const cases = await page.evaluate(() => window.durationCases);
    caseCount = cases.length;
    for (const [key, , expected] of cases) {
      const form = page.locator(`[data-duration-case="${key}"]`);
      try {
        await form.waitFor({ state: 'visible' });
      } catch (error) {
        throw new Error(`${locale}: duration node ${key} did not render: ${errors.join(' | ') || String(error)}`);
      }
      assert.equal(String(await form.innerText()).trim(), expected, `${locale}: Form duration ${key}`);
      assert.equal(await page.locator(`[data-list-duration="${key}"]`).innerText(), expected, `${locale}: List duration ${key}`);
      assert.equal(await page.locator(`[data-kanban-duration="${key}"]`).innerText(), expected, `${locale}: Kanban duration ${key}`);
      assertionCount += 3;
    }
    const falseEdit = page.locator('[data-edit-duration="false"]');
    assert.equal(await falseEdit.locator('input').inputValue(), '', `${locale}: false input is empty, not false or zero`);
    assert.equal(await falseEdit.getByText('小时', { exact: true }).count(), 1, `${locale}: duration suffix remains declared`);
    assert.equal(await page.locator('[data-edit-duration="one-half"] input').inputValue(), '1.5', `${locale}: editable duration keeps decimal-hours mutation shape`);
    assertionCount += 3;
    for (const consumer of ['form', 'list', 'kanban']) {
      assert.equal(
        String(await page.locator(`[data-percentage-value="${consumer}"]`).innerText()).trim(),
        '12.5000%',
        `${locale}: percentage ${consumer} consumes declared identity and precision`,
      );
      assert.equal(
        String(await page.locator(`[data-precision-value="${consumer}"]`).innerText()).trim(),
        '12.500000',
        `${locale}: plain float ${consumer} consumes declared precision`,
      );
      assertionCount += 2;
    }
    const authorityExpected = {
      'field-status': '待处理',
      'field-relation': expectedRelation,
      'field-relation-object': expectedRelation,
      'base-status': '待处理',
      'base-percentage': '12.5000%',
      'form-section-relation': expectedRelation,
    };
    authorityCaseCount = Object.keys(authorityExpected).length;
    for (const [key, expected] of Object.entries(authorityExpected)) {
      const target = key === 'form-section-relation'
        ? page.locator('[data-authority-case="form-section-relation"] .readonly-value')
        : page.locator(`[data-authority-case="${key}"]`);
      assert.equal(
        String(await target.innerText()).trim(),
        expected,
        `${locale}: ${key} consumes the shared authority`,
      );
      assertionCount += 1;
    }
    assert.equal(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      true,
      `${locale}: desktop authority surface has no horizontal overflow`,
    );
    assertionCount += 1;

    await page.setViewportSize({ width: 390, height: 844 });
    for (const [key, expected] of Object.entries(authorityExpected)) {
      const target = key === 'form-section-relation'
        ? page.locator('[data-authority-case="form-section-relation"] .readonly-value')
        : page.locator(`[data-authority-case="${key}"]`);
      assert.equal(
        String(await target.innerText()).trim(),
        expected,
        `${locale}: mobile ${key} preserves the shared semantic authority`,
      );
      assertionCount += 1;
    }
    assert.equal(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      true,
      `${locale}: mobile authority surface has no horizontal overflow`,
    );
    assertionCount += 1;
  }
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({
    browser: browser.version(),
    cases: caseCount,
    consumers: 3,
    declaredValueCases: 2,
    readonlyAuthorityCases: authorityCaseCount,
    locales: ['zh_CN', 'en_US'],
    viewports: [1440, 390],
    assertions: assertionCount,
    consoleErrors: 0,
    editInputs: 'PASS',
    pass: true,
  }));
} finally {
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

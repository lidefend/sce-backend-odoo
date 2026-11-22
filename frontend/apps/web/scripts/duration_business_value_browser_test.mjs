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
import { presentDeclaredBusinessValue } from ${JSON.stringify(presentationFile)};
import { presentListCell } from ${JSON.stringify(listFile)};
import { presentCollectionKanbanCell } from ${JSON.stringify(kanbanFile)};
import { formatNumericFieldValue } from ${JSON.stringify(`${root}/frontend/apps/web/src/utils/fieldSemantics.ts`)};
import { formatDisplayValue } from ${JSON.stringify(`${root}/frontend/apps/web/src/utils/display.ts`)};

const cases = [
  ['null', null, '--'],
  ['undefined', undefined, '--'],
  ['false', false, '--'],
  ['zero', 0, '0 小时'],
  ['one', 1, '1 小时'],
  ['one-half', 1.5, '1 小时 30 分钟'],
  ['carry', 1.999, '2 小时'],
  ['negative', -0.5, '-30 分钟'],
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
  value,
  inputValue,
  readonly,
  presentationMode: 'workspace',
  renderProfile: 'readonly',
});
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
            value: [7, '项目甲'],
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
              readonly: true,
              required: false,
            },
            controlId: 'base-ratio',
            placeholder: '请输入',
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
  if (request.url === '/bundle.js') {
    response.setHeader('content-type', 'text/javascript; charset=utf-8');
    response.end(output.outputFiles[0].text);
    return;
  }
  response.setHeader('content-type', 'text/html; charset=utf-8');
  response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module" src="/bundle.js"></script></body></html>');
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
  await page.goto(`http://127.0.0.1:${address.port}/`);
  await page.setViewportSize({ width: 1440, height: 900 });
  const booted = await page.evaluate(() => Array.isArray(window.durationCases));
  assert.equal(booted, true, `browser fixture failed to boot: ${errors.join(' | ')}`);
  const cases = await page.evaluate(() => window.durationCases);
  for (const [key, , expected] of cases) {
    const form = page.locator(`[data-duration-case="${key}"]`);
    await form.waitFor({ state: 'visible' });
    assert.equal(String(await form.innerText()).trim(), expected, `Form duration ${key}`);
    assert.equal(await page.locator(`[data-list-duration="${key}"]`).innerText(), expected, `List duration ${key}`);
    assert.equal(await page.locator(`[data-kanban-duration="${key}"]`).innerText(), expected, `Kanban duration ${key}`);
  }
  const falseEdit = page.locator('[data-edit-duration="false"]');
  assert.equal(await falseEdit.locator('input').inputValue(), '', 'false input is empty, not false or zero');
  assert.equal(await falseEdit.getByText('小时', { exact: true }).count(), 1, 'duration suffix remains declared');
  assert.equal(await page.locator('[data-edit-duration="one-half"] input').inputValue(), '1.5', 'editable duration keeps decimal-hours mutation shape');
  for (const consumer of ['form', 'list', 'kanban']) {
    assert.equal(
      String(await page.locator(`[data-percentage-value="${consumer}"]`).innerText()).trim(),
      '12.5000%',
      `percentage ${consumer} consumes declared identity and precision`,
    );
    assert.equal(
      String(await page.locator(`[data-precision-value="${consumer}"]`).innerText()).trim(),
      '12.500000',
      `plain float ${consumer} consumes declared precision`,
    );
  }
  const authorityExpected = {
    'field-status': '待处理',
    'field-relation': '项目甲',
    'base-status': '待处理',
    'base-percentage': '12.5000%',
  };
  for (const [key, expected] of Object.entries(authorityExpected)) {
    assert.equal(
      String(await page.locator(`[data-authority-case="${key}"]`).innerText()).trim(),
      expected,
      `${key} consumes the shared authority`,
    );
  }
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    'desktop authority surface has no horizontal overflow',
  );

  await page.setViewportSize({ width: 390, height: 844 });
  for (const [key, expected] of Object.entries(authorityExpected)) {
    assert.equal(
      String(await page.locator(`[data-authority-case="${key}"]`).innerText()).trim(),
      expected,
      `mobile ${key} preserves the shared semantic authority`,
    );
  }
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    'mobile authority surface has no horizontal overflow',
  );
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({
    browser: browser.version(),
    cases: cases.length,
    consumers: 3,
    declaredValueCases: 2,
    readonlyAuthorityCases: Object.keys(authorityExpected).length,
    viewports: [1440, 390],
    assertions: cases.length * 3 + 10 + Object.keys(authorityExpected).length * 2 + 2,
    consoleErrors: 0,
    editInputs: 'PASS',
    pass: true,
  }));
} finally {
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

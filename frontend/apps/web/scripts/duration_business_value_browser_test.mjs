import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { build } from 'esbuild';
import { compileScript, parse } from 'vue/compiler-sfc';

const root = process.cwd();
const controlFile = `${root}/frontend/apps/web/src/components/professional-fields/ProfessionalBusinessValueControl.vue`;
const presentationFile = `${root}/frontend/apps/web/src/app/presentation/businessValuePresentation.ts`;
const listFile = `${root}/frontend/apps/web/src/pages/listPage/listCellPresentation.ts`;
const kanbanFile = `${root}/frontend/apps/web/src/app/presentation/collectionKanbanPresentation.ts`;

const output = await build({
  stdin: {
    contents: `
import { createApp, h } from 'vue';
import BusinessValue from ${JSON.stringify(controlFile)};
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
const browser = await launchChromium();
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.setContent('<div id="app"></div>');
  await page.addScriptTag({ content: output.outputFiles[0].text });
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
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({
    browser: browser.version(),
    cases: cases.length,
    consumers: 3,
    declaredValueCases: 2,
    assertions: cases.length * 3 + 10,
    consoleErrors: 0,
    editInputs: 'PASS',
    pass: true,
  }));
} finally {
  await browser.close();
}

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
    return () => h('main', cases.flatMap(([key, value]) => [
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
    ]));
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
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({
    browser: browser.version(),
    cases: cases.length,
    consumers: 3,
    assertions: cases.length * 3 + 4,
    consoleErrors: 0,
    editInputs: 'PASS',
    pass: true,
  }));
} finally {
  await browser.close();
}

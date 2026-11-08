import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import { compileScript, parse, registerTS } from 'vue/compiler-sfc';

const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));

const root = process.cwd();
const components = [
  'ScInput',
  'ScTextarea',
  'ScSelect',
  'ScDateField',
  'ScNumberInput',
  'ScCheckbox',
].map((name) => `${root}/frontend/apps/web/src/components/design-system/${name}.vue`);

const output = await build({
  stdin: {
    contents: `
import { createApp, h, ref } from 'vue';
import ScInput from ${JSON.stringify(components[0])};
import ScTextarea from ${JSON.stringify(components[1])};
import ScSelect from ${JSON.stringify(components[2])};
import ScDateField from ${JSON.stringify(components[3])};
import ScNumberInput from ${JSON.stringify(components[4])};
import ScCheckbox from ${JSON.stringify(components[5])};
import ProfessionalBaseFieldControl from ${JSON.stringify(`${root}/frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue`)};

window.componentLog = [];
const record = (kind, value, event) => window.componentLog.push({
  kind,
  value: value === undefined ? null : value,
  eventType: event?.type || null,
  trusted: event?.isTrusted ?? null,
});
const contractField = (overrides) => ({
  key: overrides.name,
  name: overrides.name,
  label: overrides.name,
  type: 'char',
  required: false,
  readonly: false,
  componentRenderer: 'ProfessionalBaseFieldControl',
  presentationMode: 'task',
  renderProfile: 'edit',
  inputValue: '',
  value: '',
  selectionOptions: [],
  ...overrides,
});
const contractFields = [
  contractField({ name: 'contract-text', componentKey: 'sc.input.text', inputValue: 'text' }),
  contractField({ name: 'contract-area', componentKey: 'sc.input.textarea', type: 'text', inputValue: 'area' }),
  contractField({ name: 'contract-html', componentKey: 'sc.input.textarea', type: 'html', inputValue: '<p>html</p>' }),
  contractField({ name: 'contract-number', componentKey: 'sc.input.number', type: 'integer', inputValue: 3 }),
  contractField({ name: 'contract-select', componentKey: 'sc.select.remote', type: 'selection', inputValue: 'A', selectionOptions: [{ value: 'A', label: 'A' }] }),
  contractField({ name: 'contract-boolean', componentKey: 'sc.input.boolean', type: 'boolean', value: true, inputValue: true }),
  contractField({ name: 'contract-date', componentKey: 'sc.input.date', type: 'date', inputValue: '2026-11-08' }),
  contractField({ name: 'contract-datetime', componentKey: 'sc.input.datetime', type: 'datetime', inputValue: '2026-11-08 10:30:00' }),
  contractField({ name: 'contract-unknown', componentKey: 'sc.unknown' }),
];
const Host = {
  setup() {
    const text = ref('');
    const area = ref('');
    const choice = ref('A');
    const date = ref('2026-11-08');
    const number = ref(1);
    const checked = ref(false);
    return () => h('div', [
      h(ScInput, {
        id: 'text-input',
        modelValue: text.value,
        name: 'title',
        inputMode: 'text',
        required: true,
        describedBy: 'title-help',
        ariaLabel: '标题',
        'onUpdate:modelValue': value => { text.value = value; record('text-update', value); },
        onInput: (value, event) => record('text-input', value, event),
        onChange: (value, event) => record('text-change', value, event),
        onFocus: (value, event) => record('text-focus', value, event),
        onBlur: (value, event) => record('text-blur', value, event),
        onKeydown: event => record('text-keydown', text.value, event),
        onKeyup: event => record('text-keyup', text.value, event),
      }),
      h(ScTextarea, {
        id: 'area-input',
        modelValue: area.value,
        name: 'summary',
        rows: 2,
        maxRows: 5,
        required: true,
        describedBy: 'summary-help',
        ariaLabel: '摘要',
        'onUpdate:modelValue': value => { area.value = value; record('area-update', value); },
        onInput: (value, event) => record('area-input', value, event),
        onChange: (value, event) => record('area-change', value, event),
        onFocus: (value, event) => record('area-focus', value, event),
        onBlur: (value, event) => record('area-blur', value, event),
        onKeydown: event => record('area-keydown', area.value, event),
        onKeyup: event => record('area-keyup', area.value, event),
      }),
      h(ScSelect, {
        id: 'choice-input',
        modelValue: choice.value,
        name: 'choice',
        options: [{ value: 'A', label: 'A' }, { value: 'B', label: 'B' }],
        filterable: true,
        required: true,
        describedBy: 'choice-help',
        ariaLabel: '选择',
        'onUpdate:modelValue': value => { choice.value = value; record('choice-update', value); },
        onChange: (value, event) => record('choice-change', value, event),
        onSearch: (value, event) => record('choice-search', value, event),
        onFocus: (value, event) => record('choice-focus', value, event),
        onBlur: (value, event) => record('choice-blur', value, event),
        onKeydown: event => record('choice-keydown', choice.value, event),
        onKeyup: event => record('choice-keyup', choice.value, event),
        onPopupVisibleChange: (state, event) => record('choice-popup', state.visible, event),
      }),
      h(ScDateField, {
        id: 'date-input',
        modelValue: date.value,
        name: 'start_date',
        clearable: true,
        required: true,
        describedBy: 'date-help',
        ariaLabel: '开始日期',
        'onUpdate:modelValue': value => { date.value = value; record('date-update', value); },
        onChange: (value, event) => record('date-change', value, event),
        onFocus: (value, event) => record('date-focus', value, event),
        onBlur: (value, event) => record('date-blur', value, event),
        onKeydown: event => record('date-keydown', date.value, event),
        onKeyup: event => record('date-keyup', date.value, event),
      }),
      h(ScNumberInput, {
        id: 'number-input',
        modelValue: number.value,
        required: true,
        invalid: true,
        describedBy: 'number-help',
        ariaLabel: '数量',
        'onUpdate:modelValue': value => { number.value = value; record('number-update', value); },
      }),
      h(ScCheckbox, {
        id: 'checkbox-input',
        checked: checked.value,
        label: '启用',
        required: true,
        describedBy: 'checkbox-help',
        'onUpdate:checked': value => { checked.value = value; record('checkbox-update', value); },
        onChange: (value, event) => record('checkbox-change', value, event),
      }),
      ...contractFields.map((field) => h(ProfessionalBaseFieldControl, {
        field,
        controlId: 'bound-' + field.name,
        describedBy: field.name + '-help',
        placeholder: field.label + ' placeholder',
        'onUpdate:value': value => record('bound-update:' + field.name, value),
      })),
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
  },
  resolveExtensions: ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.mjs'],
  loader: { '.css': 'empty' },
  alias: {
    vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,
    'tdesign-vue-next': `${root}/frontend/packages/ui/node_modules/tdesign-vue-next`,
  },
  plugins: [{
    name: 'actual-vue-sfc',
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
let checks = 0;
const check = (condition, message) => {
  assert.ok(condition, message);
  checks += 1;
};

try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.setContent('<div id="app"></div>');
  await page.addScriptTag({ content: output.outputFiles[0].text });
  await page.locator('#text-input').waitFor({ state: 'visible' });

  check(await page.locator('#text-input').getAttribute('name') === 'title', 'input name projects to the native input');
  check(await page.locator('#text-input').getAttribute('inputmode') === 'text', 'input mode projects');
  check(await page.locator('#text-input').getAttribute('aria-label') === '标题', 'input accessible name projects');
  check(await page.locator('#text-input').getAttribute('aria-describedby') === 'title-help', 'input help identity projects');
  check(await page.locator('#text-input').getAttribute('required') === '', 'input required projects');

  await page.locator('#text-input').focus();
  await page.locator('#text-input').pressSequentially('abc');
  await page.locator('#area-input').focus();
  await page.locator('#area-input').pressSequentially('第一行第二行');
  await page.locator('#area-input').press('ArrowRight');
  await page.locator('#choice-input').focus();
  let events = await page.evaluate(() => window.componentLog);
  check(events.some((event) => event.kind === 'text-update' && event.value === 'abc'), 'input updates controlled value');
  check(events.some((event) => event.kind === 'text-input' && event.eventType === 'input' && event.trusted === true), 'input forwards the real native input event');
  check(events.some((event) => event.kind === 'text-change' && event.value === 'abc'), 'input change is emitted on commit');
  check(events.filter((event) => event.kind === 'text-update').length === 3, 'input update occurs once per typed character');
  check(events.filter((event) => event.kind === 'text-input').length === 3, 'input event occurs once per typed character');
  check(events.filter((event) => event.kind === 'text-change').length === 1, 'input change occurs once on blur');
  check(events.some((event) => event.kind === 'text-focus'), 'input focus is forwarded');
  check(events.some((event) => event.kind === 'text-blur'), 'input blur is forwarded');
  check(events.some((event) => event.kind === 'text-keydown'), 'input keydown is forwarded');
  check(events.some((event) => event.kind === 'text-keyup'), 'input keyup is forwarded');

  check(await page.locator('#area-input').getAttribute('name') === 'summary', 'textarea name projects');
  check(await page.locator('#area-input').evaluate((element) => element.tagName) === 'TEXTAREA', 'textarea renders a native textarea');
  check(events.some((event) => event.kind === 'area-update' && event.value.includes('第二行')), 'textarea updates controlled value');
  check(events.some((event) => event.kind === 'area-input' && event.eventType === 'input' && event.trusted === true), 'textarea input is forwarded from the real input event');
  check(events.some((event) => event.kind === 'area-change' && event.value.includes('第二行')), 'textarea change is forwarded once the area loses focus');
  check(events.filter((event) => event.kind === 'area-change').length === 1, 'textarea change occurs once on blur');
  check(events.some((event) => event.kind === 'area-focus'), 'textarea focus is forwarded');
  check(events.some((event) => event.kind === 'area-blur'), 'textarea blur is forwarded');
  check(events.some((event) => event.kind === 'area-keydown'), 'textarea keydown is forwarded');
  check(events.some((event) => event.kind === 'area-keyup'), 'textarea keyup is forwarded');

  check(await page.locator('#choice-input').getAttribute('name') === 'choice', 'select name projects');
  check(await page.locator('#choice-input').getAttribute('aria-label') === '选择', 'select accessible name projects');
  await page.locator('#choice-input').fill('B');
  await page.getByText('B', { exact: true }).last().click();
  events = await page.evaluate(() => window.componentLog);
  check(events.some((event) => event.kind === 'choice-search' && event.value.includes('B')), 'select search is forwarded');
  check(events.some((event) => event.kind === 'choice-popup'), 'select popup visibility is forwarded');
  check(events.some((event) => event.kind === 'choice-update' && event.value === 'B'), 'select updates controlled value');
  check(events.some((event) => event.kind === 'choice-change' && event.value === 'B'), 'select change is forwarded');
  check(events.some((event) => event.kind === 'choice-focus'), 'select focus is forwarded');

  check(await page.locator('#date-input').getAttribute('name') === 'start_date', 'date name projects');
  check(await page.locator('#date-input').getAttribute('aria-label') === '开始日期', 'date accessible name projects');

  await page.locator('#date-input').hover();
  await page.locator('span.t-input__clear').last().click();
  events = await page.evaluate(() => window.componentLog);
  check(events.some((event) => event.kind === 'date-update' && event.value === ''), 'initial non-empty date clears without prior focus');
  check(events.filter((event) => event.kind === 'date-change' && event.value === '').length === 1, 'initial direct clear emits one real change');

  await page.locator('#date-input').focus();
  await page.locator('#date-input').click();
  const datePanel = page.locator('.t-date-picker__panel').last();
  await datePanel.waitFor({ state: 'visible' });
  const dateCell = datePanel.locator('td.t-date-picker__cell').filter({ hasText: /^9$/ }).first();
  await dateCell.click();
  await page.locator('#date-input').press('Tab');
  events = await page.evaluate(() => window.componentLog);
  check(events.some((event) => event.kind === 'date-update' && event.value === '2026-11-09'), 'date updates controlled value through real input/change');
  check(events.some((event) => event.kind === 'date-change' && event.value === '2026-11-09' && event.trusted === true), 'date change is forwarded from the real native change event');
  check(events.filter((event) => event.kind === 'date-change').length === 2, 'initial clear and date selection each emit one change');
  check(events.some((event) => event.kind === 'date-focus'), 'date focus is forwarded');
  check(events.some((event) => event.kind === 'date-blur'), 'date blur is forwarded');
  check(events.some((event) => event.kind === 'date-keydown'), 'date keydown is forwarded');

  await page.locator('#date-input').hover();
  await page.locator('span.t-input__clear').last().click();
  events = await page.evaluate(() => window.componentLog);
  check(events.some((event) => event.kind === 'date-update' && event.value === ''), 'unfocused date clear updates controlled value');
  check(events.filter((event) => event.kind === 'date-change' && event.value === '').length === 2, 'initial and post-selection unfocused clear each emit one real change');

  await page.locator('#date-input').click();
  const secondPanel = page.locator('.t-date-picker__panel').last();
  await secondPanel.waitFor({ state: 'visible' });
  await secondPanel.locator('td.t-date-picker__cell').filter({ hasText: /^10$/ }).first().click();
  await page.locator('#date-input').hover();
  await page.locator('span.t-input__clear').last().click();
  events = await page.evaluate(() => window.componentLog);
  check(events.filter((event) => event.kind === 'date-change').length === 5, 'initial, selected and focused/unfocused clear paths each emit exactly one date change');

  check(await page.locator('#number-input').getAttribute('aria-label') === '数量', 'number accessible name projects');
  check(await page.locator('#number-input').getAttribute('aria-invalid') === 'true', 'number invalid ARIA projects');
  check(await page.locator('#checkbox-input').getAttribute('aria-describedby') === 'checkbox-help', 'checkbox help identity projects');
  await page.locator('#checkbox-input').click();
  events = await page.evaluate(() => window.componentLog);
  check(events.some((event) => event.kind === 'checkbox-update' && event.value === true), 'checkbox updates checked state');
  check(events.some((event) => event.kind === 'checkbox-change' && event.value === true), 'checkbox change is forwarded');

  const bindingCases = [
    ['contract-text', 'sc.input.text', 'ScInput'],
    ['contract-area', 'sc.input.textarea', 'ScTextarea'],
    ['contract-html', 'sc.input.textarea', 'RestrictedHtmlEditor'],
    ['contract-number', 'sc.input.number', 'ScNumberInput'],
    ['contract-select', 'sc.select.remote', 'ScSelect'],
    ['contract-boolean', 'sc.input.boolean', 'ScCheckbox'],
    ['contract-date', 'sc.input.date', 'ScDateField'],
    ['contract-datetime', 'sc.input.datetime', 'ScDateField'],
  ];
  for (const [name, componentKey, implementation] of bindingCases) {
    const root = page.locator(`[data-field-name="${name}"]`);
    check(await root.getAttribute('data-component-key') === componentKey, `${name} exposes its Contract component key`);
    check((await root.getAttribute('data-component-binding'))?.startsWith(`${componentKey}:`) === true, `${name} resolves an authoritative binding`);
    if (implementation === 'RestrictedHtmlEditor') {
      check(await root.locator('[role="textbox"]').count() === 1, `${name} renders the declared HTML editor variant`);
    } else {
      check(await root.locator(`[data-semantic-component="${implementation}"]`).count() === 1, `${name} renders ${implementation}`);
    }
  }
  const unknown = page.locator('[data-field-name="contract-unknown"]');
  check(await unknown.locator('[data-field-component-binding-error="sc.unknown"]').count() === 1, 'unknown componentKey renders a visible binding error');
  check(await unknown.locator('[data-semantic-component]').count() === 0, 'unknown componentKey does not fall back to a component');

  check(errors.length === 0, `unexpected browser errors: ${errors.join('; ')}`);
  console.log(JSON.stringify({ browser: browser.version(), checks, consoleErrors: errors.length }));
} finally {
  await browser.close();
}

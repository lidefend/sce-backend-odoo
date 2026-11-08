import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import { compileScript, parse, registerTS } from 'vue/compiler-sfc';

const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));
const root = process.cwd();
const inputFile = `${root}/frontend/apps/web/src/components/design-system/scene-adapter/ScSceneInput.vue`;
const textareaFile = `${root}/frontend/apps/web/src/components/design-system/scene-adapter/ScSceneTextarea.vue`;

const output = await build({
  stdin: {
    contents: `
import { createApp, h, ref } from 'vue';
import ScSceneInput from ${JSON.stringify(inputFile)};
import ScSceneTextarea from ${JSON.stringify(textareaFile)};

window.textLog = [];
const record = (kind, value, event) => window.textLog.push({
  kind, value, source: event?.source, eventType: event?.nativeEvent?.type || null,
  trusted: event?.nativeEvent?.isTrusted ?? null,
});
const Host = {
  setup() {
    const inputValue = ref('');
    const areaValue = ref('');
    return () => h('div', [
      h(ScSceneInput, {
        id: 'text-input', modelValue: inputValue.value, name: 'title', inputMode: 'text',
        required: true, describedBy: 'input-help', ariaLabel: '标题',
        'onUpdate:modelValue': value => { inputValue.value = value; record('update', value); },
        onInput: (value, event) => record('input', value, event),
        onChange: (value, event) => record('change', value, event),
        onFocus: (value, event) => record('focus', value, event),
        onBlur: (value, event) => record('blur', value, event),
        onKeydown: event => record('keydown', inputValue.value, event),
        onKeyup: event => record('keyup', inputValue.value, event),
        onCompositionstart: event => record('compositionstart', inputValue.value, event),
        onCompositionend: event => record('compositionend', inputValue.value, event),
      }),
      h(ScSceneInput, {
        id: 'disabled-input', modelValue: 'fixed', disabled: true,
        'onUpdate:modelValue': value => record('disabled-update', value),
      }),
      h(ScSceneInput, {
        id: 'readonly-input', modelValue: 'fixed', readonly: true,
        'onUpdate:modelValue': value => record('readonly-update', value),
      }),
      h(ScSceneInput, {
        id: 'error-input', modelValue: '', status: 'error', describedBy: 'error-help',
      }),
      h(ScSceneTextarea, {
        id: 'text-area', modelValue: areaValue.value, rows: 2, maxRows: 5,
        'onUpdate:modelValue': value => { areaValue.value = value; record('area-update', value); },
        onInput: (value, event) => record('area-input', value, event),
        onChange: (value, event) => record('area-change', value, event),
        onFocus: (value, event) => record('area-focus', value, event),
        onBlur: (value, event) => record('area-blur', value, event),
        onKeydown: event => record('area-keydown', areaValue.value, event),
        onKeyup: event => record('area-keyup', areaValue.value, event),
        onCompositionstart: event => record('area-compositionstart', areaValue.value, event),
        onCompositionend: event => record('area-compositionend', areaValue.value, event),
      }),
    ]);
  },
};
createApp(Host).mount('#app');
`,
    resolveDir: `${root}/frontend/apps/web`,
    loader: 'js',
  },
  bundle: true, write: false, platform: 'browser', format: 'iife',
  define: {
    __VUE_OPTIONS_API__: 'true', __VUE_PROD_DEVTOOLS__: 'false',
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false', 'process.env.NODE_ENV': '"production"',
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
  await page.evaluate(() => {
    for (const [id, prefix] of [['text-input', 'input'], ['text-area', 'area']]) {
      document.querySelector(`#${id}`).addEventListener('compositionupdate', (event) => {
        window.textLog.push({
          kind: `${prefix}-native-compositionupdate`,
          value: event.target.value,
          trusted: event.isTrusted,
        });
      });
    }
  });

  assert.equal(await page.locator('#text-input').getAttribute('name'), 'title');
  assert.equal(await page.locator('#text-input').getAttribute('inputmode'), 'text');
  assert.equal(await page.locator('#text-input').getAttribute('aria-label'), '标题');
  assert.equal(await page.locator('#text-input').getAttribute('aria-describedby'), 'input-help');
  assert.equal(await page.locator('#text-input').getAttribute('required'), '');
  assert.equal(await page.locator('#error-input').getAttribute('aria-invalid'), 'true');
  assert.equal(await page.locator('#disabled-input').isDisabled(), true);
  assert.equal(await page.locator('#readonly-input').getAttribute('readonly'), '');

  let events;
  await page.evaluate(() => {
    window.textLog = [];
    for (const id of ['disabled-input', 'readonly-input']) {
      const input = document.querySelector(`#${id}`);
      input.value = 'attempted-change';
      input.dispatchEvent(new InputEvent('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  events = await page.evaluate(() => window.textLog);
  assert.equal(events.filter((event) => event.kind === 'disabled-update').length, 0);
  assert.equal(events.filter((event) => event.kind === 'readonly-update').length, 0);

  await page.locator('#text-input').focus();
  await page.locator('#text-input').pressSequentially('abc');
  events = await page.evaluate(() => window.textLog);
  assert.ok(
    events.some((event) => event.kind === 'update' && event.value === 'abc'),
    JSON.stringify(events),
  );
  assert.ok(events.some((event) => event.kind === 'input' && event.value === 'abc' && event.source === 'keyboard'));
  assert.ok(events.some((event) => event.kind === 'keydown'));
  assert.ok(events.some((event) => event.kind === 'keyup'));
  await page.locator('#text-area').focus();
  events = await page.evaluate(() => window.textLog);
  assert.equal(events.filter((event) => event.kind === 'update').length, 3);
  assert.equal(events.filter((event) => event.kind === 'input').length, 3);
  assert.equal(events.filter((event) => event.kind === 'change' && event.value === 'abc').length, 1);
  assert.ok(events.some((event) => event.kind === 'change' && event.value === 'abc'));
  assert.ok(events.some((event) => event.kind === 'blur'));
  assert.ok(events.some((event) => event.kind === 'focus'));

  await page.evaluate(() => {
    const input = document.querySelector('#text-input');
    input.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true, data: '' }));
    input.dispatchEvent(new CompositionEvent('compositionupdate', { bubbles: true, data: '你' }));
    input.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true, data: '你' }));
  });
  events = await page.evaluate(() => window.textLog);
  assert.ok(events.some((event) => event.kind === 'compositionstart'));
  assert.ok(events.some((event) => event.kind === 'input-native-compositionupdate'));
  assert.ok(events.some((event) => event.kind === 'compositionend'));

  await page.evaluate(() => { window.textLog = []; });
  await page.locator('#text-area').fill('第一行\n第二行');
  await page.evaluate(() => {
    const area = document.querySelector('#text-area');
    area.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true, data: '' }));
    area.dispatchEvent(new CompositionEvent('compositionupdate', { bubbles: true, data: '完成' }));
    area.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true, data: '完成' }));
  });
  await page.locator('#text-input').focus();
  events = await page.evaluate(() => window.textLog);
  assert.equal(
    events.filter((event) => event.kind === 'area-update' && event.value.includes('第二行')).length,
    1,
    JSON.stringify(events),
  );
  assert.equal(
    events.filter((event) => event.kind === 'area-input').length,
    1,
    JSON.stringify(events),
  );
  assert.equal(
    events.filter((event) => event.kind === 'area-change').length,
    1,
    JSON.stringify(events),
  );
  assert.equal(events.filter((event) => event.kind === 'area-native-compositionupdate').length, 1);
  const areaUpdateIndex = events.findIndex((event) => event.kind === 'area-update' && event.value.includes('第二行'));
  const areaChangeIndex = events.findIndex((event) => event.kind === 'area-change');
  assert.ok(areaUpdateIndex >= 0 && areaChangeIndex > areaUpdateIndex, JSON.stringify(events));
  assert.ok(events.some((event) => event.kind === 'area-update' && event.value.includes('第二行')));
  assert.ok(events.some((event) => event.kind === 'area-input'));
  assert.ok(events.some((event) => event.kind === 'area-change'));
  assert.ok(events.some((event) => event.kind === 'area-compositionstart'));
  assert.ok(events.some((event) => event.kind === 'area-compositionend'));
  assert.equal(await page.locator('#text-area').evaluate((element) => element.tagName), 'TEXTAREA');
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ browser: browser.version(), checks: 31, consoleErrors: 0 }));
} finally {
  await browser.close();
}

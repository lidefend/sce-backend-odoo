import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import { compileScript, parse, registerTS } from 'vue/compiler-sfc';

const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));

const root = process.cwd();
const behaviorMode = process.argv.includes('--behavior');
const runtimeFile = path.join(root, '.runtime/scene-primitive-adapter-test.mjs');
const buttonFile = `${root}/frontend/apps/web/src/components/design-system/scene-adapter/ScSceneButton.vue`;

const harness = behaviorMode ? `
import { createApp, h, nextTick, ref } from 'vue';
import { ScenePrimitiveProvider } from '@sc/ui/primitive-port/provider';
import ScSceneButton from ${JSON.stringify(buttonFile)};

const component = () => null;
const contract = (primitive, capabilities) => ({ primitive, portVersion: 1, capabilities });
const primitives = {
  Button: { component, contract: contract('Button', ['activate', 'focus', 'blur', 'keyboard', 'loading']) },
  Input: { component, contract: contract('Input', ['value', 'change', 'focus', 'blur', 'keyboard', 'ime']) },
  Select: { component, contract: contract('Select', ['value', 'change', 'search', 'popup', 'focus', 'blur', 'keyboard']) },
  DateField: { component, contract: contract('DateField', ['value', 'change', 'focus', 'blur', 'keyboard']) },
  Textarea: { component, contract: contract('Textarea', ['value', 'change', 'focus', 'blur', 'keyboard', 'ime']) },
  Table: { component, contract: contract('Table', ['row-activate', 'focus', 'keyboard']) },
  Icon: { component, contract: contract('Icon', ['semantic-icon']) },
};
const invalidPrimitives = {
  ...primitives,
  Input: { ...primitives.Input, contract: contract('Input', ['value', 'change', 'focus', 'blur', 'keyboard']) },
};

window.scenePrimitiveLog = [];
const record = (kind, event) => window.scenePrimitiveLog.push({
  kind,
  source: event.source,
  eventType: event.nativeEvent?.type || null,
  trusted: event.nativeEvent?.isTrusted ?? null,
});

const Host = {
  setup() {
    const primitivesBroken = ref(false);
    const pointerButton = ref(null);
    window.breakPrimitiveAdapter = async () => {
      primitivesBroken.value = true;
      await nextTick();
    };
    window.callSceneButtonFocus = async (options) => {
      pointerButton.value.focus(options);
      await nextTick();
    };
    return () => h(ScenePrimitiveProvider, { primitives, density: 'cozy' }, {
      default: () => h('div', [
        h(ScSceneButton, {
          id: 'pointer-button',
          ref: pointerButton,
          onActivate: event => record('activate', event),
          onFocus: event => record('focus', event),
          onBlur: event => record('blur', event),
        }, () => 'Pointer'),
        h(ScSceneButton, {
          id: 'enter-button',
          onActivate: event => record('activate', event),
        }, () => 'Enter'),
        h(ScSceneButton, {
          id: 'space-button',
          onActivate: event => record('activate', event),
        }, () => 'Space'),
        h(ScSceneButton, {
          id: 'programmatic-button',
          onActivate: event => record('activate', event),
        }, () => 'Programmatic'),
        h(ScSceneButton, {
          id: 'disabled-button',
          disabled: true,
          onActivate: event => record('activate', event),
        }, () => 'Disabled'),
        h(ScSceneButton, {
          id: 'loading-button',
          loading: true,
          loadingLabel: '加载中',
          onActivate: event => record('activate', event),
        }, () => 'Loading'),
        h(ScSceneButton, {
          id: 'labelled-button',
          accessibleLabel: '保存合同',
          onActivate: event => record('activate', event),
        }, () => ''),
        h(ScenePrimitiveProvider, {
          primitives: primitivesBroken.value ? invalidPrimitives : primitives,
        }, {
          default: () => h('div', { id: 'dynamic-consumer' }, 'Dynamic'),
        }),
      ]),
    });
  },
};

createApp(Host).mount('#app');
` : `
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import {
  ScenePrimitiveProvider,
  useScenePrimitiveContext,
} from '@sc/ui/primitive-port/provider';

const component = () => null;
const contract = (primitive, capabilities) => ({ primitive, portVersion: 1, capabilities });
const validAdapter = {
  Button: { component, contract: contract('Button', ['activate', 'focus', 'blur', 'keyboard', 'loading']) },
  Input: { component, contract: contract('Input', ['value', 'change', 'focus', 'blur', 'keyboard', 'ime']) },
  Select: { component, contract: contract('Select', ['value', 'change', 'search', 'popup', 'focus', 'blur', 'keyboard']) },
  DateField: { component, contract: contract('DateField', ['value', 'change', 'focus', 'blur', 'keyboard']) },
  Textarea: { component, contract: contract('Textarea', ['value', 'change', 'focus', 'blur', 'keyboard', 'ime']) },
  Table: { component, contract: contract('Table', ['row-activate', 'focus', 'keyboard']) },
  Icon: { component, contract: contract('Icon', ['semantic-icon']) },
};
const invalidAdapter = {
  ...validAdapter,
  Input: { ...validAdapter.Input, contract: contract('Input', ['value', 'change', 'focus', 'blur', 'keyboard']) },
};

let renderedChildren = 0;
const Consumer = {
  setup() {
    const context = useScenePrimitiveContext();
    return () => {
      renderedChildren += 1;
      return h('div', { id: 'consumer' }, \`\${context.primitives.Button.contract.primitive}:\${context.density}\`);
    };
  },
};

export async function renderValid() {
  renderedChildren = 0;
  const html = await renderToString(createSSRApp({
    render: () => h(ScenePrimitiveProvider, { primitives: validAdapter, density: 'cozy' }, {
      default: () => h(Consumer),
    }),
  }));
  return { html, renderedChildren };
}

export async function renderInvalid() {
  renderedChildren = 0;
  const html = await renderToString(createSSRApp({
    render: () => h(ScenePrimitiveProvider, { primitives: invalidAdapter }, {
      default: () => h(Consumer),
    }),
  }));
  return { html, renderedChildren };
}

export async function renderOutsideProvider() {
  return renderToString(createSSRApp({
    setup() {
      try {
        useScenePrimitiveContext();
        return () => h('div', { id: 'outside-provider-unexpected' });
      } catch (error) {
        return () => h('div', { id: 'outside-provider-error' }, error.name);
      }
    },
  }));
}
`;

const output = await build({
  stdin: {
    contents: harness,
    resolveDir: `${root}/frontend/apps/web`,
    loader: 'js',
  },
  bundle: true,
  write: false,
  platform: behaviorMode ? 'browser' : 'node',
  format: behaviorMode ? 'iife' : 'esm',
  define: {
    __VUE_OPTIONS_API__: 'true',
    __VUE_PROD_DEVTOOLS__: 'false',
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
    'process.env.NODE_ENV': '"production"',
  },
  resolveExtensions: ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.mjs'],
  banner: behaviorMode
    ? undefined
    : { js: "import { createRequire } from 'node:module'; const require = createRequire(import.meta.url);" },
  loader: { '.css': 'empty' },
  alias: {
    'vue/server-renderer': require.resolve('vue/server-renderer'),
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
          resolveDir: args.path.slice(0, args.path.lastIndexOf('/')),
        };
      });
    },
  }],
  logLevel: 'error',
});

const code = output.outputFiles[0].text;

if (behaviorMode) {
  const { launchChromium } = await import('../../../../scripts/verify/playwright_runtime.mjs');
  const browser = await launchChromium();
  try {
    const page = await browser.newPage();
    const errors = [];
    const requests = [];
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text());
    });
    await page.route('**/*', (route) => {
      requests.push(route.request().url());
      return route.abort();
    });
    await page.setContent('<div id="app"></div>');
    await page.addScriptTag({ content: code });
    await page.locator('#pointer-button').waitFor({ state: 'visible' });

    let checks = 0;
    const equal = (actual, expected, message) => {
      checks += 1;
      assert.equal(actual, expected, message);
    };
    const deepEqual = (actual, expected, message) => {
      checks += 1;
      assert.deepEqual(actual, expected, message);
    };
    const match = (actual, expected, message) => {
      checks += 1;
      assert.match(actual, expected, message);
    };
    const reset = () => page.evaluate(() => { window.scenePrimitiveLog = []; });
    const log = () => page.evaluate(() => window.scenePrimitiveLog);

    await reset();
    await page.locator('#pointer-button').click();
    const pointerActivations = (await log()).filter((event) => event.kind === 'activate');
    equal(pointerActivations.length, 1);
    deepEqual(pointerActivations[0], {
      kind: 'activate',
      source: 'pointer',
      eventType: 'click',
      trusted: true,
    });

    await reset();
    await page.locator('#enter-button').focus();
    await page.locator('#enter-button').press('Enter');
    const enterEvents = await log();
    equal(enterEvents.filter((event) => event.kind === 'activate').length, 1);
    equal(enterEvents.find((event) => event.kind === 'activate')?.source, 'keyboard');

    await reset();
    await page.locator('#space-button').focus();
    await page.locator('#space-button').press('Space');
    const spaceEvents = await log();
    equal(spaceEvents.filter((event) => event.kind === 'activate').length, 1);
    equal(spaceEvents.find((event) => event.kind === 'activate')?.source, 'keyboard');

    await reset();
    await page.evaluate(() => document.querySelector('#programmatic-button').click());
    const programmaticEvents = await log();
    equal(programmaticEvents.length, 1);
    equal(programmaticEvents[0].source, 'programmatic');
    equal(programmaticEvents[0].trusted, false);

    await reset();
    await page.evaluate(() => document.querySelector('#disabled-button').dispatchEvent(
      new MouseEvent('click', { bubbles: true }),
    ));
    await page.evaluate(() => document.querySelector('#loading-button').dispatchEvent(
      new MouseEvent('click', { bubbles: true }),
    ));
    deepEqual(await log(), []);
    equal(await page.locator('#loading-button').getAttribute('aria-busy'), 'true');
    equal(await page.locator('#loading-button').getByText('加载中').count(), 1);

    await page.evaluate(() => {
      const originalFocus = HTMLElement.prototype.focus;
      window.focusOptions = [];
      HTMLElement.prototype.focus = function focus(options) {
        window.focusOptions.push(options ?? null);
        return originalFocus.call(this, options);
      };
    });
    await page.evaluate(() => window.callSceneButtonFocus({ preventScroll: true }));
    deepEqual(await page.evaluate(() => window.focusOptions.at(-1)), { preventScroll: true });

    await page.locator('#pointer-button').blur();
    await reset();
    await page.locator('#pointer-button').focus();
    await page.locator('#pointer-button').blur();
    const focusEvents = await log();
    deepEqual(focusEvents.map((event) => event.kind), ['focus', 'blur']);

    equal(await page.locator('#labelled-button').getAttribute('aria-label'), '保存合同');
    equal(await page.locator('#dynamic-consumer').count(), 1);
    await page.evaluate(() => window.breakPrimitiveAdapter());
    await page.locator('[data-scene-primitive-contract-error]').waitFor({ state: 'visible' });
    equal(await page.locator('#dynamic-consumer').count(), 0);
    match(await page.locator('[data-scene-primitive-contract-error]').innerText(), /Input:ime/);
    deepEqual(requests, []);
    deepEqual(errors, []);
    console.log(JSON.stringify({
      browser: browser.version(),
      checks,
      consoleErrors: errors.length,
      networkRequests: requests.length,
    }));
  } finally {
    await browser.close();
  }
} else {
  fs.mkdirSync(path.dirname(runtimeFile), { recursive: true });
  fs.writeFileSync(runtimeFile, code);
  const runtime = await import(`${runtimeFile}?v=${Date.now()}`);
  const valid = await runtime.renderValid();
  assert.match(valid.html, /id="consumer"/);
  assert.match(valid.html, /Button:cozy/);
  assert.ok(valid.renderedChildren > 0);

  const invalid = await runtime.renderInvalid();
  assert.match(invalid.html, /role="alert"/);
  assert.match(invalid.html, /Scene Primitive 契约错误/);
  assert.match(invalid.html, /Input:ime/);
  assert.equal(invalid.renderedChildren, 0);

  const outsideProvider = await runtime.renderOutsideProvider();
  assert.match(outsideProvider, /id="outside-provider-error"/);
  assert.match(outsideProvider, /ScenePrimitiveProviderError/);
  assert.doesNotMatch(outsideProvider, /outside-provider-unexpected/);
  console.log('[scene-primitive-adapter-test] PASS provider=3 button-contract=real');
}

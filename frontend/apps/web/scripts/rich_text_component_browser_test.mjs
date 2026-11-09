import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { build } from 'esbuild';
import { compileScript, parse } from 'vue/compiler-sfc';

const root = process.cwd();
const component = path.join(root, 'frontend/apps/web/src/components/content/ScRichText.vue');
const output = await build({
  stdin: {
    contents: `
import { createApp, h } from 'vue';
import ScRichText from ${JSON.stringify(component)};
createApp({
  render: () => h('main', [
    h(ScRichText, { id: 'readonly', policy: 'readonly', content: '<p onclick="bad()">说明<strong>加粗</strong><script>bad()</script><a href="javascript:bad()">坏链接</a><a href="https://example.com/x" title="x">好链接</a></p>' }),
    h(ScRichText, { id: 'restricted', policy: 'restricted', content: '<h2>标题</h2><table><tr><td colspan="2">单元</td></tr></table><iframe>bad</iframe>' }),
  ]),
}).mount('#app');
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
  alias: {
    vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,
  },
  plugins: [{
    name: 'actual-rich-text-sfc',
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
  await page.route('http://app.local/', (route) => route.fulfill({
    status: 200,
    contentType: 'text/html',
    body: '<div id="app"></div>',
  }));
  await page.goto('http://app.local/');
  await page.addScriptTag({ content: output.outputFiles[0].text });
  assert.equal(await page.locator('[data-semantic-component="ScRichText"]').count(), 2);
  assert.equal(await page.locator('#readonly').getAttribute('data-policy'), 'readonly');
  assert.equal(await page.locator('#restricted').getAttribute('data-policy'), 'restricted');
  assert.equal(await page.locator('#readonly p').getAttribute('onclick'), null);
  assert.equal(await page.locator('#readonly script').count(), 0);
  assert.equal(await page.locator('#readonly a', { hasText: '坏链接' }).getAttribute('href'), null);
  assert.equal(
    await page.locator('#readonly a', { hasText: '好链接' }).getAttribute('href'),
    'https://example.com/x',
  );
  assert.equal(
    await page.locator('#readonly a', { hasText: '好链接' }).getAttribute('rel'),
    'noopener noreferrer',
  );
  assert.equal(await page.locator('#restricted h2').innerText(), '标题');
  assert.equal(await page.locator('#restricted td').getAttribute('colspan'), '2');
  assert.equal(await page.locator('#restricted iframe').count(), 0);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({
    browser: browser.version(),
    checks: 10,
    consoleErrors: 0,
    readonlyPolicy: 'PASS',
    restrictedPolicy: 'PASS',
    unsafeMarkup: 'removed',
  }));
} finally {
  await browser.close();
}

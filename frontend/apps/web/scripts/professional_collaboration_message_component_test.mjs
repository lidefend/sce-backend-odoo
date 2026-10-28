import assert from 'node:assert/strict';
import fs from 'node:fs';
import { build } from 'esbuild';
import { parse, compileScript, registerTS } from 'vue/compiler-sfc';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));
const root = process.cwd();
const browserMode = process.argv.includes('--browser');
// Four observed author/body pairs (FEPC-09); IDs, title, meta and permissions are synthetic.
const pairs = [
  ['OdooBot', ''],
  ['项目审批岗', '项目立项已通过，尚未启动。'],
  ['项目审批岗', '项目初始化已完成：已建立项目管理对象；任务根节点已就绪；成本/资金/风险承载采用按业务事件驱动补充。'],
  ['项目审批岗', '项目 创建'],
  ['服务端作者', '前缀: 保留·中点：以及\n多行'],
  [undefined, '不得猜作者：正文完整'],
  ['服务端作者', '<b>正文：</b>不能作为 HTML 执行'],
];
const entries = pairs.map(([author_name, body], i) => ({ key: `m${i}`, type: 'message', typeLabel: '备注',
  title: '标题不得替代正文', meta: '元信息不得替代作者', body, at: '2026-10-28T03:40:21',
  message: { id: i + 1, author_name, can_reply: i !== 5, reply_intent: 'chatter.post' } }));
const props = { entries, activityUpdatingIds: [], attachmentDeletingIds: [], messageDeletingIds: [],
  attachmentViewLabel: '查看', timelineHasMore: false, timelineLoading: false };
const harness = `
import { ${browserMode ? 'createApp' : 'createSSRApp'}, h } from 'vue';
${browserMode ? '' : "import { renderToString } from 'vue/server-renderer';"}
import Timeline from ${JSON.stringify(`${root}/frontend/apps/web/src/pages/contractForm/ProfessionalCollaborationTimeline.vue`)};
import { formatCollaborationTimelineMeta } from ${JSON.stringify(`${root}/frontend/apps/web/src/pages/contractForm/professionalCollaborationModel.ts`)};
const props = ${JSON.stringify(props)};
${browserMode ? `window.replyKeys = []; props.onReply = entry => window.replyKeys.push(entry.key);
window.expectedTime = formatCollaborationTimelineMeta(props.entries[0].at);
createApp({render:()=>h(Timeline,props)}).mount('#app');` : `export const expectedTime = formatCollaborationTimelineMeta(props.entries[0].at);
export const render = () => renderToString(createSSRApp({render:()=>h(Timeline,props)}));`}
`;
const output = await build({ stdin: { contents: harness, resolveDir: `${root}/frontend/apps/web`, loader: 'js' },
  bundle: true, write: false, platform: browserMode ? 'browser' : 'node', format: browserMode ? 'iife' : 'esm',
  define: { __VUE_OPTIONS_API__: 'true', __VUE_PROD_DEVTOOLS__: 'false', __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false', 'process.env.NODE_ENV': '"production"' },
  resolveExtensions: ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.mjs'],
  banner: browserMode ? undefined : { js: "import { createRequire } from 'node:module'; const require = createRequire(import.meta.url);" },
  loader: { '.css': 'empty' },
  alias: { 'vue/server-renderer': require.resolve('vue/server-renderer'), vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`, 'tdesign-vue-next': `${root}/frontend/packages/ui/node_modules/tdesign-vue-next` },
  plugins: [{ name: 'actual-vue-sfc', setup(builder) { builder.onLoad({ filter: /\.vue$/ }, args => {
    const { descriptor } = parse(fs.readFileSync(args.path, 'utf8'), { filename: args.path });
    return { contents: compileScript(descriptor, { id: args.path, inlineTemplate: true }).content, loader: 'ts', resolveDir: args.path.slice(0, args.path.lastIndexOf('/')) };
  }); } }], logLevel: 'error' });
const code = output.outputFiles[0].text;
let checks = 0;
const equal = (actual, expected) => { assert.deepEqual(actual, expected); checks++; };
if (browserMode) {
  const { launchChromium } = await import('../../../../scripts/verify/playwright_runtime.mjs');
  const browser = await launchChromium();
  try {
    const page = await browser.newPage();
    const errors = [];
    const requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.route('**/*', route => { requests.push(route.request().url()); return route.abort(); });
    await page.setContent('<div id="app"></div>');
    await page.addScriptTag({ content: code });
    await page.locator('.native-chatter-message-body').first().waitFor({ state: 'attached' });
    equal(await page.locator('.native-chatter-message-author').allTextContents(), pairs.map(([author]) => author ?? ''));
    equal(await page.locator('.native-chatter-message-body').allTextContents(), pairs.map(([, body]) => body));
    const expectedTime = await page.evaluate(() => window.expectedTime);
    equal(await page.locator('.native-chatter-message-time').allTextContents(), pairs.map(() => expectedTime));
    equal(await page.locator('.native-chatter-message-reply').count(), 6);
    equal(await page.locator('.native-chatter-message-delete').count(), 0);
    equal(await page.locator('.native-chatter-message-body b').count(), 0);
    await page.locator('.native-chatter-message-reply').first().click();
    equal(await page.evaluate(() => window.replyKeys), ['m0']);
    equal(await page.locator('.native-chatter-message-body').allTextContents(), pairs.map(([, body]) => body));
    equal(requests, []);
    equal(errors, []);
    console.log(JSON.stringify({ browser: browser.version(), consoleErrors: errors, networkRequests: requests.length, replyKeys: ['m0'] }));
  } finally { await browser.close(); }
} else {
  const file = `${root}/.runtime/fepc10-message-component.mjs`;
  fs.mkdirSync(`${root}/.runtime`, { recursive: true }); fs.writeFileSync(file, code);
  const { render, expectedTime } = await import(file);
  const html = await render();
  const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  const content = name => [...html.matchAll(new RegExp(`<span class="${name}">([\\s\\S]*?)</span>`, 'g'))].map(match => match[1]);
  equal(content('native-chatter-message-author'), pairs.map(([author]) => escape(author ?? '')));
  equal(content('native-chatter-message-body'), pairs.map(([, body]) => escape(body)));
  equal(content('native-chatter-message-time'), pairs.map(() => escape(expectedTime)));
  equal((html.match(/native-chatter-message-reply/g) || []).length, 6);
  equal((html.match(/native-chatter-message-delete/g) || []).length, 0);
  equal((html.match(/data-collaboration-entry-type="message"/g) || []).length, 7);
}
console.log(`[collaboration-message-component] PASS mode=${browserMode ? 'browser' : 'SSR'} checks=${checks} messages=${entries.length}`);

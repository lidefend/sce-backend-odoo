import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import { compileScript, parse } from 'vue/compiler-sfc';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

const require = createRequire(import.meta.url);
const root = process.cwd();
const fixturePath = path.join(
  root,
  'frontend/apps/web/scripts/fixtures/native_embedded_widget_contract_v2.json',
);
const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
const harness = `
import { createApp, h } from 'vue';
import NativeFormTreeRenderer from ${JSON.stringify(path.join(root, 'frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue'))};
import CanonicalFormNodeRenderer from ${JSON.stringify(path.join(root, 'frontend/apps/web/src/pages/contractForm/CanonicalFormNodeRenderer.vue'))};
import { buildCanonicalNativeFormBridge } from ${JSON.stringify(path.join(root, 'frontend/apps/web/src/pages/contractForm/canonicalNativeFormBridge.ts'))};
import { decodeContractV2Snapshot } from ${JSON.stringify(path.join(root, 'frontend/apps/web/src/app/contracts/v2/schema.ts'))};
import { createContractV2Store } from ${JSON.stringify(path.join(root, 'frontend/apps/web/src/app/contracts/v2/store.ts'))};
import { presentContractV2Form } from ${JSON.stringify(path.join(root, 'frontend/apps/web/src/app/presentation/contractFormPresenter.ts'))};

const producer = ${JSON.stringify(fixture)};
const supported = structuredClone(producer);
supported.layoutContract.containerTree = supported.layoutContract.containerTree.slice(0, 2);
supported.statusContract.containerStatus = supported.statusContract.containerStatus.slice(0, 2);
delete supported.layoutContract.componentRegistry['sc.unsupported.native_node'];

const bridge = buildCanonicalNativeFormBridge(
  presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(supported)), 'readonly'),
);
createApp({
  render: () => h(NativeFormTreeRenderer, {
    nodes: bridge.primaryNodes,
    fieldSchemasForNodes: bridge.fieldSchemasForNodes,
    isNodeVisible: bridge.nodeVisible,
  }),
}).mount('#native');

const store = createContractV2Store(decodeContractV2Snapshot(supported));
const model = presentContractV2Form(store, 'readonly');
createApp({
  render: () => h(CanonicalFormNodeRenderer, {
    node: model.zones.primary[0],
    preferReadonlyFacts: true,
  }),
}).mount('#canonical');

const hidden = structuredClone(supported);
hidden.statusContract.containerStatus[0].visible = false;
const hiddenStore = createContractV2Store(decodeContractV2Snapshot(hidden));
const hiddenModel = presentContractV2Form(hiddenStore, 'readonly');
createApp({
  render: () => h(CanonicalFormNodeRenderer, {
    node: hiddenModel.zones.primary[0],
    preferReadonlyFacts: true,
  }),
}).mount('#hidden');

const hiddenNative = structuredClone(supported);
hiddenNative.statusContract.containerStatus[0].visible = false;
const hiddenNativeBridge = buildCanonicalNativeFormBridge(
  presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(hiddenNative)), 'readonly'),
);
createApp({
  render: () => h(NativeFormTreeRenderer, {
    nodes: hiddenNativeBridge.primaryNodes,
    fieldSchemasForNodes: hiddenNativeBridge.fieldSchemasForNodes,
    isNodeVisible: hiddenNativeBridge.nodeVisible,
  }),
}).mount('#hidden-native');

const parentHidden = structuredClone(supported);
const hiddenWidget = parentHidden.layoutContract.containerTree[0];
parentHidden.layoutContract.containerTree = [{
  containerId: 'hidden-parent',
  containerType: 'group',
  type: 'group',
  title: 'Hidden parent',
  span: 24,
  columns: 1,
  children: [hiddenWidget],
  widgetList: [],
}];
parentHidden.statusContract.containerStatus = [
  { containerId: 'hidden-parent', visible: false, disabled: false },
  ...parentHidden.statusContract.containerStatus,
];
const parentHiddenBridge = buildCanonicalNativeFormBridge(
  presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(parentHidden)), 'readonly'),
);
createApp({
  render: () => h(NativeFormTreeRenderer, {
    nodes: parentHiddenBridge.primaryNodes,
    fieldSchemasForNodes: parentHiddenBridge.fieldSchemasForNodes,
    isNodeVisible: parentHiddenBridge.nodeVisible,
  }),
}).mount('#parent-hidden');

let unsupported = '';
try {
  decodeContractV2Snapshot(producer);
} catch (error) {
  unsupported = String(error?.message || error);
}
document.documentElement.dataset.unsupported = unsupported;
document.documentElement.dataset.ready = 'true';
`;

const bundled = await build({
  stdin: {
    contents: harness,
    resolveDir: path.join(root, 'frontend/apps/web'),
    loader: 'js',
  },
  bundle: true,
  write: false,
  platform: 'browser',
  format: 'esm',
  define: {
    'import.meta.env': '{}',
    'process.env.NODE_ENV': '"production"',
  },
  resolveExtensions: ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.mjs', '.vue'],
  loader: { '.css': 'empty' },
  alias: {
    vue: path.join(root, 'frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js'),
  },
  plugins: [{
    name: 'native-widget-browser-vue',
    setup(builder) {
      builder.onLoad({ filter: /\.vue$/ }, (args) => {
        const { descriptor } = parse(fs.readFileSync(args.path, 'utf8'), { filename: args.path });
        const compiled = compileScript(descriptor, { id: args.path, inlineTemplate: true });
        return {
          contents: compiled.content,
          loader: 'ts',
          resolveDir: path.dirname(args.path),
        };
      });
    },
  }],
  logLevel: 'error',
});
const bundle = bundled.outputFiles[0].text;
const server = http.createServer((request, response) => {
  if (request.url === '/app.mjs') {
    response.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8' });
    response.end(bundle);
    return;
  }
  response.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
  response.end('<!doctype html><html><body><div id="native"></div><div id="canonical"></div><div id="hidden"></div><div id="hidden-native"></div><div id="parent-hidden"></div><script type="module" src="/app.mjs"></script></body></html>');
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const address = server.address();
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage();
  const businessRequests = [];
  page.on('request', (request) => {
    if (!['document', 'script'].includes(request.resourceType())) {
      businessRequests.push(request.url());
    }
  });
  await page.goto(`http://127.0.0.1:${address.port}/`, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true');

  const nativeRibbons = page.locator('#native [data-native-widget="web_ribbon"]');
  assert.equal(await nativeRibbons.count(), 2);
  assert.deepEqual(await nativeRibbons.allInnerTexts(), ['Paid', 'Draft']);
  const canonicalRibbons = page.locator('#canonical [data-native-widget="web_ribbon"]');
  assert.equal(await canonicalRibbons.count(), 1);
  assert.equal((await canonicalRibbons.innerText()).trim(), 'Paid');
  assert.equal(await canonicalRibbons.getAttribute('class'), 'native-ribbon text-bg-success');
  assert.equal(await page.locator('#hidden [data-native-widget="web_ribbon"]').count(), 0);
  assert.equal(await page.locator('#hidden-native [data-native-widget="web_ribbon"]').count(), 1);
  assert.equal(
    await page.locator('#hidden-native [data-contract-container-id="web_ribbon..form1.widget1.1"]').count(),
    0,
  );
  assert.equal(await page.locator('#parent-hidden [data-native-widget="web_ribbon"]').count(), 0);
  const unsupported = await page.evaluate(() => document.documentElement.dataset.unsupported || '');
  assert.match(unsupported, /NATIVE_VIEW_WIDGET_UNSUPPORTED/);
  assert.deepEqual(businessRequests, []);
  console.log('[native-embedded-widget-browser] PASS paths=2 occurrences=2 canonical=1 self_hidden=0 parent_hidden=0 unsupported=fail_closed business_requests=0');
} finally {
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

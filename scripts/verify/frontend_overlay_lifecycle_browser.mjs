import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';

const entryId = '\0overlay-lifecycle-browser-entry';
const server = await createServer({
  root: new URL('../../frontend/apps/web', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, hmr: false },
  plugins: [{
    name: 'overlay-lifecycle-browser-harness',
    configureServer(vite) {
      vite.middlewares.use('/__overlay_lifecycle.html', (_request, response) => {
        response.setHeader('content-type', 'text/html; charset=utf-8');
        response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body><button id="opener">打开</button><div id="app"></div><script type="module" src="/__overlay_lifecycle.js"></script></body></html>');
      });
    },
    resolveId(id) { return id === '/__overlay_lifecycle.js' ? entryId : undefined; },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h, reactive } from 'vue';
        import Dialog from '/src/components/design-system/ScDialog.vue';
        import Drawer from '/src/components/design-system/ScDrawer.vue';
        import '/src/styles/design-system.css';
        const state = reactive({ dialog: false, drawer: false, locked: false, empty: false, closes: 0 });
        window.overlayState = state;
        document.querySelector('#opener').addEventListener('click', () => { state.dialog = true; });
        createApp({ render() { return h('div', [
          h(Dialog, { open: state.dialog, title: '详情', description: '对话说明', size: 'wide', onClose: () => { state.dialog = false; state.closes += 1; } }, {
            default: () => [h('button', { id: 'dialog-first', 'data-dialog-primary': '' }, '第一项'), h('button', { id: 'open-drawer', onClick: () => { state.drawer = true; } }, '打开抽屉')],
          }),
          h(Drawer, { open: state.drawer, title: '抽屉', description: '抽屉说明', onClose: () => { state.drawer = false; state.closes += 1; } }, {
            default: () => h('button', { id: 'drawer-action', 'data-dialog-primary': '' }, '抽屉动作'),
          }),
          h(Dialog, { open: state.locked, title: '不可关闭', dismissible: false, onClose: () => { state.locked = false; state.closes += 1; } }, { default: () => h('p', '处理中') }),
          h(Dialog, { open: state.empty, title: '无控件', dismissible: false, onClose: () => { state.empty = false; } }, { default: () => h('p', '只读内容') }),
        ]); } }).mount('#app');
      `;
    },
  }],
});

await server.listen();
const address = server.httpServer?.address();
if (!address || typeof address === 'string') throw new Error('overlay harness did not expose a TCP port');
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  await page.goto(`http://127.0.0.1:${address.port}/__overlay_lifecycle.html`);
  const visibleOverlayResidueCount = async () => page.locator('.t-drawer:visible, .t-drawer__mask:visible, .t-dialog:visible, .t-dialog__mask:visible, [data-overlay-kind]:visible').count();
  const initialOverlayResidueCount = await visibleOverlayResidueCount();
  const waitForActiveWithin = async (selector) => {
    await page.waitForFunction((target) => {
      const node = document.querySelector(target);
      return Boolean(node && document.activeElement && node.contains(document.activeElement));
    }, selector);
  };
  await page.locator('#opener').click();
  const dialog = page.locator('[data-overlay-kind="dialog"][data-state="open"]');
  try {
    await dialog.waitFor();
  } catch (error) {
    throw new Error(`overlay dialog did not open: ${JSON.stringify({ errors, body: (await page.locator('body').innerText()).slice(0, 500) })}`, { cause: error });
  }
  await waitForActiveWithin('[data-overlay-kind="dialog"][data-state="open"]');
  const initialFocus = await dialog.evaluate((node) => node.contains(document.activeElement));
  const bodyLocked = await page.evaluate(() => getComputedStyle(document.body).overflow === 'hidden');
  const labelled = await dialog.evaluate((node) => ({ labelledby: node.getAttribute('aria-labelledby'), describedby: node.getAttribute('aria-describedby') }));
  await page.locator('#open-drawer').click();
  const drawer = page.locator('[data-overlay-kind="drawer"][data-state="open"]');
  await drawer.waitFor();
  await waitForActiveWithin('[data-overlay-kind="drawer"][data-state="open"]');
  const nestedFocus = await drawer.evaluate((node) => node.contains(document.activeElement));
  await page.keyboard.press('Escape');
  await drawer.waitFor({ state: 'hidden' });
  await page.waitForFunction(() => !document.querySelector('.t-drawer, .t-drawer__mask, [data-overlay-kind="drawer"]'));
  const closedDrawerResidueCount = await page.locator('.t-drawer, .t-drawer__mask, [data-overlay-kind="drawer"]').count();
  await page.waitForFunction(() => document.activeElement?.id === 'open-drawer');
  const nestedRestore = await page.evaluate(() => document.activeElement?.id === 'open-drawer');
  const nestedBodyLocked = await page.evaluate(() => getComputedStyle(document.body).overflow === 'hidden');
  await page.keyboard.press('Escape');
  await dialog.waitFor({ state: 'hidden' });
  await page.waitForFunction(() => document.activeElement?.id === 'opener');
  const openerRestored = await page.evaluate(() => document.activeElement?.id === 'opener');
  const bodyReleased = await page.evaluate(() => getComputedStyle(document.body).overflow !== 'hidden');

  await page.evaluate(() => { window.overlayState.locked = true; });
  const locked = page.locator('[data-overlay-kind="dialog"][data-state="open"][data-dismissible="false"]');
  await locked.waitFor();
  await page.keyboard.press('Escape');
  await locked.dispatchEvent('mousedown', { bubbles: true });
  const lockedRemains = await locked.count() === 1;
  await page.evaluate(() => { window.overlayState.locked = false; });
  await locked.waitFor({ state: 'hidden' });
  await page.evaluate(() => { window.overlayState.empty = true; });
  const emptySurface = page.locator('[data-overlay-kind="dialog"][data-state="open"]');
  await emptySurface.waitFor();
  await waitForActiveWithin('[data-overlay-kind="dialog"][data-state="open"]');
  const emptyInitialFocus = await emptySurface.evaluate((node) => node.contains(document.activeElement));
  await page.keyboard.press('Tab');
  const emptyTabContained = await emptySurface.evaluate((node) => node.contains(document.activeElement));
  await page.evaluate(() => { window.overlayState.empty = false; });

  const pass = initialOverlayResidueCount === 0 && closedDrawerResidueCount === 0
    && initialFocus && nestedFocus
    && nestedRestore && openerRestored
    && bodyLocked && nestedBodyLocked && bodyReleased && lockedRemains
    && emptyInitialFocus && emptyTabContained
    && Boolean(labelled.labelledby) && Boolean(labelled.describedby)
    && errors.length === 0;
  console.log(JSON.stringify({ pass, initialOverlayResidueCount, closedDrawerResidueCount, initialFocus, nestedFocus, nestedRestore, openerRestored, bodyLocked, nestedBodyLocked, bodyReleased, lockedRemains, emptyInitialFocus, emptyTabContained, labelled, errors }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}

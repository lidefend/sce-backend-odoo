import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';

const entryId = '\0native-form-action-presentation-browser-entry';
const server = await createServer({
  root: new URL('../../frontend/apps/web', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0 },
  plugins: [{
    name: 'native-form-action-presentation-browser-harness',
    configureServer(vite) {
      vite.middlewares.use('/__native_action_overflow.html', (_request, response) => {
        response.setHeader('content-type', 'text/html');
        response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><div id="outside" tabindex="0">outside</div><script type="module" src="/__native_action_overflow.js"></script></body></html>');
      });
    },
    resolveId(id) { return id === '/__native_action_overflow.js' ? entryId : undefined; },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h } from 'vue';
        import Menu from '/src/components/template/NativeActionOverflowMenu.vue';
        import '/src/styles/design-system.css';
        const actions = [
          { key: 'one', label: '动作一' },
          { key: 'disabled', label: '禁用动作', disabled: true },
          { key: 'two', label: '动作二' },
          { key: 'three', label: '动作三' },
        ];
        const props = {
          actions, identity: 'same-identity', keyResolver: (a) => a.key,
          evidenceResolver: (a) => ({ 'data-action-key': a.key }),
          labelResolver: (a) => a.label, iconResolver: () => '',
          disabledResolver: (a) => Boolean(a.disabled), titleResolver: (a) => a.label,
        };
        window.nativeActionEvidence = { selected: [] };
        createApp({ render() { return h('div', [
          h(Menu, { ...props, label: '更多一', onSelect: (a) => window.nativeActionEvidence.selected.push(a.key) }),
          h(Menu, { ...props, actions: actions.map((action) => ({ ...action, disabled: true })), label: '更多二', onSelect: (a) => window.nativeActionEvidence.selected.push(a.key) }),
        ]); } }).mount('#app');
      `;
    },
  }],
});

await server.listen();
const address = server.httpServer?.address();
if (!address || typeof address === 'string') throw new Error('Vite browser harness did not expose a TCP port');
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  await page.goto(`http://127.0.0.1:${address.port}/__native_action_overflow.html`);
  const triggers = page.getByRole('button', { name: /更多/ });
  const firstTrigger = triggers.nth(0);
  await firstTrigger.focus();
  await firstTrigger.press('ArrowDown');
  const ids = await page.locator('[role="menu"]').evaluateAll((nodes) => nodes.map((node) => node.id));
  const focusSequence = [await page.evaluate(() => document.activeElement?.textContent?.trim())];
  await page.keyboard.press('ArrowDown'); focusSequence.push(await page.evaluate(() => document.activeElement?.textContent?.trim()));
  await page.keyboard.press('End'); focusSequence.push(await page.evaluate(() => document.activeElement?.textContent?.trim()));
  await page.keyboard.press('Home'); focusSequence.push(await page.evaluate(() => document.activeElement?.textContent?.trim()));
  await page.keyboard.press('ArrowUp'); focusSequence.push(await page.evaluate(() => document.activeElement?.textContent?.trim()));
  await page.keyboard.press('Escape');
  const escapeRestored = await firstTrigger.evaluate((node) => document.activeElement === node);
  await firstTrigger.press('ArrowUp');
  const arrowUpInitial = await page.evaluate(() => document.activeElement?.textContent?.trim());
  await page.keyboard.press('Enter');
  const selected = await page.evaluate(() => window.nativeActionEvidence.selected);
  const selectionRestored = await firstTrigger.evaluate((node) => document.activeElement === node);
  await triggers.nth(1).press('ArrowDown');
  const secondId = await page.locator('[role="menu"]').getAttribute('id');
  await triggers.nth(1).press('Escape');
  const allDisabledEscapeClosed = await page.locator('[role="menu"]').count() === 0;
  await triggers.nth(1).click();
  await triggers.nth(1).press('Tab');
  const allDisabledTabClosed = await page.locator('[role="menu"]').count() === 0;
  await firstTrigger.click();
  await page.locator('#outside').click();
  const outsideClosed = await page.locator('[role="menu"]').count() === 0;
  const pass = JSON.stringify(focusSequence) === JSON.stringify(['动作一', '动作二', '动作三', '动作一', '动作三'])
    && arrowUpInitial === '动作三'
    && JSON.stringify(selected) === JSON.stringify(['three'])
    && escapeRestored && selectionRestored && outsideClosed && allDisabledEscapeClosed && allDisabledTabClosed
    && ids.length === 1 && Boolean(ids[0]) && Boolean(secondId) && ids[0] !== secondId
    && errors.length === 0;
  console.log(JSON.stringify({ pass, focusSequence, arrowUpInitial, selected, escapeRestored, selectionRestored, outsideClosed, allDisabledEscapeClosed, allDisabledTabClosed, ids: [ids[0], secondId], errors }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}

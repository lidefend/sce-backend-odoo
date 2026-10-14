import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';

const denialScope = process.env.SC_NATIVE_ACTION_SCOPE === 'denial';
const entryId = '\0native-form-action-presentation-browser-entry';
const server = await createServer({
  root: new URL('../../frontend/apps/web', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, hmr: false },
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
        import Dropdown from '/src/components/design-system/ScDropdown.vue';
        import Button from '/src/components/design-system/ScButton.vue';
        import Renderer from '/src/components/template/NativeFormTreeRenderer.vue';
        import '/src/styles/design-system.css';
        const actions = Array.from({ length: 7 }, (_, index) => ({
          type: 'button', name: 'action_' + index, visible: index !== 2,
          label: '完整声明的较长操作名称 ' + index,
          action: { actionKey: 'action_' + index, level: 'smart', kind: 'object' },
        }));
        window.nativeActionEvidence = { selected: [], declared: actions.filter(a => a.visible).map(a => a.action.actionKey) };
        if (${denialScope}) {
          window.denialEvents = [];
          createApp({ render: () => h(Dropdown, { items: [{value:'blocked',label:'办理',disabled:true,reasonMessage:'先补齐依据'}],
            onSelect: value => window.denialEvents.push(value) }, { trigger: () => h(Button, {}, () => '操作') }) }).mount('#app');
        } else createApp({ render() { return h(Renderer, {
          nodes: [{ type: 'div', span: 24, class: 'oe_button_box', children: actions }],
          fieldSchemasForNodes: () => [], isNodeVisible: node => node.visible !== false,
          nativeActionStateResolver: node => ({ disabled: node.name === 'action_4' }),
          onNativeAction: action => window.nativeActionEvidence.selected.push(action.actionKey),
        }); } }).mount('#app');
      `;
    },
  }],
});

await server.listen();
const address = server.httpServer?.address();
if (!address || typeof address === 'string') throw new Error('Vite browser harness did not expose a TCP port');
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage({ hasTouch: denialScope });
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  const results = [];
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`http://127.0.0.1:${address.port}/__native_action_overflow.html`);
    if (denialScope) {
      await page.getByRole('button', { name: '操作', exact: true }).click();
      const explanation = page.getByRole('button', { name: '办理: 先补齐依据', exact: true });
      await explanation.waitFor({ state: 'visible' });
      await explanation.focus();
      await explanation.press('Enter');
      await page.getByText('先补齐依据', { exact: true }).waitFor({ state: 'visible' });
      const keyboardVisible = await page.getByText('先补齐依据', { exact: true }).isVisible();
      const pointer = () => width === 390 ? explanation.tap() : explanation.click();
      await pointer();
      await page.getByText('先补齐依据', { exact: true }).waitFor({ state: 'hidden' });
      const clickClosed = !(await page.getByText('先补齐依据', { exact: true }).isVisible());
      await pointer();
      await page.getByText('先补齐依据', { exact: true }).waitFor({ state: 'visible' });
      const events = await page.evaluate(() => window.denialEvents);
      const clickVisible = await page.getByText('先补齐依据', { exact: true }).isVisible();
      results.push({ width, pointer: width === 390 ? 'touch' : 'mouse', keyboardVisible, clickClosed, clickVisible, events, pass: keyboardVisible && clickClosed && clickVisible && events.length === 0 });
      continue;
    }
    const buttons = page.locator('.native-actions--smart [data-action-key]');
    await buttons.first().waitFor({ state: 'visible' });
    const declared = await page.evaluate(() => window.nativeActionEvidence.declared);
    const actual = await buttons.evaluateAll(nodes => nodes.map(node => node.dataset.actionKey));
    const geometry = await buttons.evaluateAll(nodes => nodes.map(node => {
      const rect = node.getBoundingClientRect();
      const label = node.querySelector('.native-smart-action__label');
      return { key: node.dataset.actionKey, fits: rect.width > 0 && rect.left >= 0 && rect.right <= innerWidth + 1,
        labelUnclipped: Boolean(label && label.scrollWidth <= label.clientWidth + 1 && label.scrollHeight <= label.clientHeight + 1) };
    }));
    const disabled = page.locator('[data-action-key="action_4"]');
    const disabledDeclared = await disabled.isDisabled();
    await disabled.dispatchEvent('click');
    const deniedEvents = await page.evaluate(() => window.nativeActionEvidence.selected.length);
    await page.locator('[data-action-key="action_6"]').click();
    const selected = await page.evaluate(() => window.nativeActionEvidence.selected);
    const autoMenus = await page.locator('[data-semantic-component="NativeActionOverflowMenu"]').count();
    const pass = JSON.stringify(actual) === JSON.stringify(declared) && actual.length === 6
      && geometry.every(item => item.fits && item.labelUnclipped) && disabledDeclared && deniedEvents === 0
      && JSON.stringify(selected) === JSON.stringify(['action_6']) && autoMenus === 0;
    results.push({ width, declared, actual, geometry, disabledDeclared, deniedEvents, selected, autoMenus, pass });
  }
  const pass = results.every(item => item.pass) && errors.length === 0;
  console.log(JSON.stringify({ pass, renderer: denialScope ? 'ScDropdown+ScPopover' : 'NativeFormTreeRenderer', driver: 'real', results, errors }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}

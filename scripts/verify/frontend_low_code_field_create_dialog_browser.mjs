import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';

const expectedTypes = ['char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime', 'html'];
const entryId = '\0low-code-field-dialog-browser-entry';
const server = await createServer({
  root: new URL('../../frontend/apps/web', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0 },
  plugins: [{
    name: 'low-code-field-dialog-browser-harness',
    configureServer(vite) {
      vite.middlewares.use('/__low_code_field_dialog.html', (_request, response) => {
        response.setHeader('content-type', 'text/html');
        response.end('<!doctype html><html><body><div id="app"></div><script type="module" src="/__low_code_field_dialog.js"></script></body></html>');
      });
    },
    resolveId(id) {
      return id === '/__low_code_field_dialog.js' ? entryId : undefined;
    },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h, reactive } from 'vue';
        import Dialog from '/src/pages/contractForm/LowCodeFieldCreateDialog.vue';
        import '/src/styles/design-system.css';
        import '/src/styles/product-patterns.css';
        const state = reactive({ open: true, afterFieldKey: '', groupTitle: '', sequence: 1, label: '', ttype: 'char' });
        window.fieldCreateEvidence = { submits: 0, closes: 0, labelUpdates: [], typeUpdates: [] };
        createApp({ render() { return h(Dialog, {
          dialog: state,
          busy: false,
          onClose: () => { window.fieldCreateEvidence.closes += 1; },
          onSubmit: () => { window.fieldCreateEvidence.submits += 1; },
          'onUpdate:label': (value) => { state.label = value; window.fieldCreateEvidence.labelUpdates.push(value); },
          'onUpdate:ttype': (value) => { state.ttype = value; window.fieldCreateEvidence.typeUpdates.push(value); },
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
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${address.port}/__low_code_field_dialog.html`);
  const form = page.locator('[data-semantic-component="LowCodeFieldCreateForm"]');
  await form.waitFor();
  const label = form.locator('input');
  const type = form.locator('select');
  const submit = form.getByRole('button', { name: '创建字段' });
  const cancel = form.getByRole('button', { name: '取消' });
  const initialFocus = await page.evaluate(() => document.activeElement?.id || '');
  await submit.click();
  const emptySubmits = await page.evaluate(() => window.fieldCreateEvidence.submits);
  await label.fill('专业字段');
  await type.selectOption('datetime');
  await submit.click();
  await cancel.click();
  const evidence = await page.evaluate(() => window.fieldCreateEvidence);
  const options = await type.locator('option').evaluateAll((nodes) => nodes.map((node) => node.value));
  const labels = await form.locator('label').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('for')));
  const controlIds = [await label.getAttribute('id'), await type.getAttribute('id')];
  const pass = emptySubmits === 0
    && evidence.submits === 1
    && evidence.closes === 1
    && evidence.labelUpdates.at(-1) === '专业字段'
    && evidence.typeUpdates.at(-1) === 'datetime'
    && JSON.stringify(options) === JSON.stringify(expectedTypes)
    && JSON.stringify(labels) === JSON.stringify(controlIds)
    && initialFocus === controlIds[0]
    && await label.getAttribute('required') === ''
    && await type.getAttribute('required') === ''
    && await submit.count() === 1
    && await cancel.count() === 1;
  console.log(JSON.stringify({ pass, emptySubmits, evidence, options, labels, controlIds, initialFocus }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}

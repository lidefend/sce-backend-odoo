import assert from 'node:assert/strict';
import { createServer } from '../node_modules/vite/dist/node/index.js';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

// Real browser component fixture. No backend, router authority, or business writes.
const entryId = '\0list-composition-browser-entry';
const server = await createServer({
  root: new URL('..', import.meta.url).pathname,
  logLevel: 'error', server: { host: '127.0.0.1', port: 0, hmr: false },
  plugins: [{
    name: 'list-composition-browser-harness',
    configureServer(vite) {
      vite.middlewares.use('/__list_composition.html', (_request, response) => {
        response.setHeader('content-type', 'text/html; charset=utf-8');
        response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module" src="/__list_composition.js"></script></body></html>');
      });
    },
    resolveId(id) { return id === '/__list_composition.js' ? entryId : undefined; },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h, reactive, nextTick } from 'vue';
        import ListPage from '/src/pages/ListPage.vue';
        import Toolbar from '/src/components/action/ActionSurfaceToolbar.vue';
        import '/src/styles/design-system.css';
        const probe = reactive({ state: 'normal', queryMode: 'fallback' });
        window.setListProbe = async (value) => { Object.assign(probe, value); await nextTick(); };
        createApp({ render() {
          const { state, queryMode } = probe;
          return h(ListPage, {
      key: queryMode + ':' + state, title: 'Authorized collection', model: 'x.fixture', status: state === 'empty' ? 'empty' : 'ok', loading: false,
      columns: ['name'], records: state === 'empty' ? [] : [{ id: 1, name: 'Record' }],
      subtitle: '', statusLabel: '', columnLabels: { name: 'Name' },
      selectedIds: state === 'selected' ? [1] : [],
      selectionActions: [{ key: 'batch:read', label: 'Batch probe', enabled: false }],
      selectionEnabled: true, showPlainSearch: true, showFallbackCreate: true,
      onReload() {}, onRowClick() {}, onSearch() {}, onSort() {}, onFilter() {}, onToggleSelection() {}, onToggleSelectionAll() {},
      contractPageType: { pageType: 'query-list', reason: 'contract-collection-view' },
    }, {
      ...(queryMode === 'declared' ? { toolbar: () => h(Toolbar, {
        loading: false, showViewSwitch: false, viewLabel: 'View', viewModes: ['list'], currentViewMode: 'list', viewModeLabels: { list: 'List' },
        searchValue: '', searchPlaceholder: 'Query probe', clearLabel: 'Clear', showFilter: false, filterLabel: 'Filter', filterPrimary: [], filterOverflow: [], activeFilterKey: '',
        showSavedFilter: false, savedFilterLabel: 'Saved', savedFilterPrimary: [], savedFilterOverflow: [], activeSavedFilterKey: '',
        sortLabel: 'Sort', sortOptions: [], sortValue: '', showGroup: false, groupLabel: 'Group', groupPrimary: [], groupOverflow: [],
        customFilterEnabled: false, customFilterLabel: '', customFilterFields: [], customGroupEnabled: false, customGroupLabel: '', customGroupFields: [],
        favoriteSaveEnabled: false, favoriteContextKey: '', submitFavorite: async () => ({ ok: false }), favoriteSaveLabel: '',
        activeCustomFilterLabel: '', activeGroupLabel: '', activeGroupKey: '', canCreateRecord: false, createLabel: 'Create',
      }) } : {}),
      leading: () => [h('button', { 'data-probe-operation': 'create' }, 'Create probe'), h('button', { 'data-probe-operation': 'reload' }, 'Reload probe')],
    });
        } }).mount('#app');
      `;
    },
  }],
});
let browser;
let checks = 0;
const check = (actual, expected, message) => { assert.deepEqual(actual, expected, message); checks += 1; };
try {
  await server.listen();
  const address = server.httpServer?.address();
  assert(address && typeof address !== 'string', 'component host must expose loopback TCP port');
  const hostOrigin = `http://127.0.0.1:${address.port}`;
  browser = await launchChromium({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  const forbiddenRequests = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() !== 'GET' || url.pathname.startsWith('/api/') || url.origin !== hostOrigin) {
      forbiddenRequests.push(`${request.method()} ${url.pathname}`);
      await route.abort();
    } else await route.continue();
  });
  await page.goto(`${hostOrigin}/__list_composition.html`);
  await page.waitForFunction(() => typeof window.setListProbe === 'function');
  for (const queryMode of ['fallback', 'declared']) for (const state of ['normal', 'selected', 'empty']) {
    await page.evaluate((value) => window.setListProbe(value), { state, queryMode });
    await page.locator('[data-list-query-action-bar]').waitFor();
    const html = await page.locator('#app').innerHTML();
    check((html.match(/data-probe-operation="create"/g) || []).length, 1, `${state}: create appears once`);
    check((html.match(/data-probe-operation="reload"/g) || []).length, 1, `${state}: reload appears once`);
    check((html.match(/type="search"/g) || []).length, 1, `${state}: query remains unique`);
    check((html.match(/data-list-query-action-bar/g) || []).length, 1, `${state}: one shared header`);
    check((html.match(/data-list-card-container="official"/g) || []).length, 1, `${state}: one card`);
    check(/data-workspace-frame=|sc-page-frame/.test(html), false, `${state}: embedded list cannot own canvas`);
    check(html.includes('t-card'), true, `${state}: actual TDesign card rendered`);
    check(html.includes('t-input'), true, `${state}: actual TDesign query input rendered`);
    check(html.includes('list-surface-column-button'), true, `${state}: column settings retained`);
    check(html.includes('list-surface-contextual-toolbar'), state === 'selected', `${state}: batch and query coexist only when selected`);
    check(html.includes('Batch probe'), state === 'selected', `${state}: actual selection props drive batch capability`);
    if (state === 'selected') {
      const action = html.match(/<button[^>]*data-action-key="batch:read"[^>]*>/)?.[0] || '';
      check(action.includes('disabled'), true, `${queryMode}: denied batch action remains disabled`);
    }
    check(html.includes('data-semantic-component="CollectionActionToolbar"'), queryMode === 'declared', `${state}: declared query uses actual toolbar`);
  }
  check(forbiddenRequests, [], 'fixture performs no backend or external requests');
  check(errors, [], 'real components produce no console or page errors');
  console.log(`[list_surface_component_test] PASS checks=${checks} combinations=6 real_sfc=true real_tdesign=true attachment_viewer=real render=browser_component_fixture backend_acceptance=false actionview_permission_chain=not_tested browser_geometry=not_tested`);
} finally {
  try { await browser?.close(); } finally { await server.close(); }
}

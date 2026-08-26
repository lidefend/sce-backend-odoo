import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';

const entryId = '\0state-dashboard-browser-entry';
const server = await createServer({
  root: new URL('../../frontend/apps/web', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0 },
  plugins: [{
    name: 'state-dashboard-browser-harness',
    configureServer(vite) {
      vite.middlewares.use('/__state_dashboard.html', (_request, response) => {
        response.setHeader('content-type', 'text/html');
        response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module" src="/__state_dashboard.js"></script></body></html>');
      });
    },
    resolveId(id) { return id === '/__state_dashboard.js' ? entryId : undefined; },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h, reactive } from 'vue';
        import { createMemoryHistory, createRouter } from 'vue-router';
        import ActivityPage from '/src/pages/ActivityPage.vue';
        import StatusPanel from '/src/components/StatusPanel.vue';
        import ActivityPageTabs from '/src/components/product-shell/ActivityPageTabs.vue';
        import DashboardPattern from '/src/components/product-page-patterns/DashboardPattern.vue';
        import AlertPanel from '/src/components/page/blocks/BlockAlertPanel.vue';
        import TodoList from '/src/components/page/blocks/BlockTodoList.vue';
        import RecordTable from '/src/components/page/blocks/BlockRecordTable.vue';
        import '/src/styles/design-system.css';
        const state = reactive({ mode: 'loading', opened: '', retries: 0, activeTab: 'one', closedTabs: [], focusExits: 0, dashboardActions: [] });
        window.stateDashboard = state;
        const labels = { eyebrow: '动态', countSuffix: '条', loading: '正在加载', unavailable: '动态不可用', record: '记录', emptyTitle: '暂无动态', emptyHint: '当前范围没有动态' };
        const model = () => state.mode === 'error'
          ? { ok: false, reasonCode: 'ACTIVITY_UNAVAILABLE', fields: [], requestedFields: [], records: [], templateNames: [], templateNodes: [], sourceAuthority: {} }
          : { ok: true, reasonCode: '', fields: [], requestedFields: [], records: state.mode === 'records' ? [{ id: 7 }] : [], templateNames: [], templateNodes: [], sourceAuthority: {} };
        const block = (key, title) => ({ key, title, actions: [{ key: 'refresh', label: '刷新' }], payload: {} });
        const onAction = (payload) => state.dashboardActions.push(payload.actionKey);
        const pages = reactive([
          { key: 'one', title: '第一个页面', route: '/one', kind: 'custom', created_at: 1, last_active_at: 1 },
          { key: 'two', title: '第二个页面', route: '/two', kind: 'custom', created_at: 2, last_active_at: 2 },
        ]);
        const closePage = (page) => {
          const index = pages.findIndex((item) => item.key === page.key);
          if (index < 0) return;
          pages.splice(index, 1);
          state.closedTabs.push(page.key);
          if (state.activeTab === page.key) state.activeTab = pages[Math.min(index, pages.length - 1)]?.key || '';
        };
        const focusExit = () => {
          state.focusExits += 1;
          document.querySelector('#activity-focus-exit')?.focus();
        };
        const app = createApp({ render() { return h('main', [
          h('button', { id: 'activity-focus-exit', tabindex: -1 }, '活动页签关闭后焦点'),
          h(ActivityPageTabs, { pages, activeKey: state.activeTab, onActivate: (page) => { state.activeTab = page.key; }, onClose: closePage, onFocusExit: focusExit }),
          h(ActivityPage, { title: '业务动态', loading: state.mode === 'loading', model: model(), labels, onOpenRecord: (record) => { state.opened = String(record.id); } }),
          h(StatusPanel, { title: '加载失败', message: '请重试', variant: 'error', onRetry: async () => { state.retries += 1; } }),
          h(DashboardPattern, {}, { default: () => [
            h(AlertPanel, { block: block('alerts', '风险'), zoneKey: 'main', dataset: [], onAction }),
            h(TodoList, { block: block('todos', '待办'), zoneKey: 'main', dataset: [{ id: 1, title: '审核合同', action_key: 'open_todo' }], onAction }),
            h(RecordTable, { block: block('table', '明细'), zoneKey: 'main', dataset: { columns: [], rows: [], empty_message: '暂无明细' }, onAction }),
          ] }),
        ]); } });
        const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] });
        app.use(router);
        await router.push('/');
        await router.isReady();
        app.mount('#app');
      `;
    },
  }],
});

await server.listen();
const address = server.httpServer?.address();
if (!address || typeof address === 'string') throw new Error('state dashboard harness did not expose a TCP port');
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  await page.goto(`http://127.0.0.1:${address.port}/__state_dashboard.html`);
  await page.waitForFunction(() => Boolean(window.stateDashboard));

  const loading = await page.locator('[data-activity-surface] [data-semantic-component="ScLoading"][data-state="loading"]').count() === 1;
  await page.evaluate(() => { window.stateDashboard.mode = 'error'; });
  const error = await page.locator('[data-activity-surface] [data-semantic-component="ScErrorState"][data-state="error"]').count() === 1;
  await page.evaluate(() => { window.stateDashboard.mode = 'empty'; });
  const empty = await page.locator('[data-activity-surface] [data-semantic-component="ScEmptyState"][data-state="empty"]').count() === 1;
  await page.evaluate(() => { window.stateDashboard.mode = 'records'; });
  const card = page.locator('.activity-card');
  await card.focus();
  const focusVisible = await card.evaluate((node) => getComputedStyle(node).outlineStyle !== 'none');
  await card.click();

  const firstTab = page.locator('[role="tab"]').first();
  await firstTab.focus();
  await firstTab.press('ArrowRight');
  const selectedTab = await page.locator('[role="tab"][aria-selected="true"]').textContent();
  const focusedTab = await page.evaluate(() => document.activeElement?.textContent?.trim() || '');
  const tablistUnexpectedButtonCount = await page.locator('[role="tablist"] button:not([role="tab"])').count();
  await page.locator('[role="tab"][aria-selected="true"]').press('Delete');
  await page.locator('#activity-focus-exit').waitFor();
  const singlePageTablistHidden = await page.locator('[role="tablist"]').count() === 0;
  const emptyTabFocusSettled = await page.locator('#activity-focus-exit').evaluate((node) => document.activeElement === node);

  const retry = page.locator('.sc-state-panel [data-semantic-component="ScButton"]').filter({ hasText: '重试' });
  await retry.click();
  const dashboardEmptyCount = await page.locator('[data-product-page-pattern="dashboard"] [data-semantic-component="ScEmptyState"][data-density="compact"]').count();
  const dashboardEmptyHeadingCount = await page.locator('[data-product-page-pattern="dashboard"] [data-semantic-component="ScEmptyState"] h5').count();
  const dashboardUnexpectedH2Count = await page.locator('[data-product-page-pattern="dashboard"] [data-semantic-component="ScEmptyState"] h2').count();
  await page.locator('.block-todo-list [data-semantic-component="ScButton"]').filter({ hasText: '进入处理' }).click();
  const state = await page.evaluate(() => ({ ...window.stateDashboard }));
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);

  const pass = loading && error && empty && focusVisible && state.opened === '7' && state.retries === 1
    && selectedTab?.includes('第二个页面') && focusedTab === '第二个页面'
    && tablistUnexpectedButtonCount === 0 && singlePageTablistHidden
    && state.closedTabs.includes('two') && state.focusExits === 1 && emptyTabFocusSettled
    && dashboardEmptyCount === 2 && dashboardEmptyHeadingCount === 2 && dashboardUnexpectedH2Count === 0
    && state.dashboardActions.includes('open_todo')
    && !overflow && errors.length === 0;
  console.log(JSON.stringify({ pass, loading, error, empty, focusVisible, selectedTab, focusedTab, tablistUnexpectedButtonCount, singlePageTablistHidden, emptyTabFocusSettled, dashboardEmptyCount, dashboardEmptyHeadingCount, dashboardUnexpectedH2Count, state, overflow, errors }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}

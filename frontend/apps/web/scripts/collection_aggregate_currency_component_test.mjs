import assert from 'node:assert/strict';
import { createServer } from '../node_modules/vite/dist/node/index.js';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

const entryId = '\0collection-aggregate-currency-browser-entry';
const server = await createServer({
  root: new URL('..', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, hmr: false },
  plugins: [{
    name: 'collection-aggregate-currency-harness',
    configureServer(vite) {
      vite.middlewares.use('/__aggregate_currency.html', (_request, response) => {
        response.setHeader('content-type', 'text/html; charset=utf-8');
        response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module" src="/__aggregate_currency.js"></script></body></html>');
      });
    },
    resolveId(id) {
      return id === '/__aggregate_currency.js' ? entryId : undefined;
    },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h, reactive, nextTick } from 'vue';
        import ListPage from '/src/pages/ListPage.vue';
        import '/src/styles/design-system.css';

        const currency = (id, name, symbol) => ({ id, name, symbol, decimal_places: 2, rounding: 0.01 });
        const columnOptions = [{
          name: 'name',
          label: 'Name',
          type: 'char',
        }, {
          name: 'amount',
          label: 'Amount',
          type: 'monetary',
          dataType: 'monetary',
          aggregate: 'sum',
          aggregationField: 'amount',
          currencyField: 'currency_id',
          digits: [16, 2],
        }, {
          name: 'quantity',
          label: 'Quantity',
          type: 'integer',
          dataType: 'integer',
          aggregate: 'sum',
          aggregationField: 'quantity',
        }];
        const base = {
          records: [{ id: 1, name: 'CNY record', amount: 100, quantity: 7, currency_id: [1, 'CNY'] }],
          listProfile: { row_primary: 'name', columns: ['name', 'amount', 'quantity'] },
          listAggregates: {
            amount: {
              aggregate: 'sum',
              data_type: 'monetary',
              aggregation_field: 'amount',
              page_sum: 100,
              sum: 300,
              currency_field: 'currency_id',
              currency_id: 1,
            },
            quantity: {
              aggregate: 'sum',
              data_type: 'integer',
              aggregation_field: 'quantity',
              page_sum: 7,
              sum: 9,
            },
          },
        };
        const scenarios = {
          same: base,
          missing_id: {
            ...base,
            listAggregates: { amount: { ...base.listAggregates.amount, currency_id: undefined } },
          },
          missing_label: {
            ...base,
            records: [{ id: 1, name: 'Bare currency', amount: 100, currency_id: 1 }],
          },
          label_mismatch: {
            ...base,
            records: [{ id: 1, name: 'USD page row', amount: 100, currency_id: [2, 'USD'] }],
          },
          mixed_scope: {
            ...base,
            records: [
              { id: 1, name: 'CNY record', amount: 100, quantity: 1, currency_id: [1, 'CNY'] },
              { id: 2, name: 'USD record', amount: 200, quantity: 2, currency_id: [2, 'USD'] },
            ],
            listAggregates: {
              ...base.listAggregates,
              amount: {
                aggregate: 'none',
                data_type: 'monetary',
                currency_field: 'currency_id',
                reason_code: 'AGGREGATE_MULTI_CURRENCY_PROHIBITED',
              },
            },
          },
          out_of_page_currency_mismatch: {
            ...base,
            records: [
              { id: 1, name: 'CNY page row', amount: 100, quantity: 7, currency_id: [1, 'CNY'] },
            ],
            listAggregates: {
              ...base.listAggregates,
              amount: {
                aggregate: 'none',
                data_type: 'monetary',
                currency_field: 'currency_id',
                reason_code: 'AGGREGATE_CURRENCY_SCOPE_UNVERIFIED',
              },
            },
          },
          aggregate_type_mismatch: {
            ...base,
            listAggregates: {
              ...base.listAggregates,
              amount: {
                ...base.listAggregates.amount,
                data_type: 'float',
              },
            },
          },
          non_monetary: {
            ...base,
            listAggregates: {
              ...base.listAggregates,
              amount: {
                aggregate: 'none',
                data_type: 'monetary',
                currency_field: 'currency_id',
                reason_code: 'AGGREGATE_MULTI_CURRENCY_PROHIBITED',
              },
            },
          },
          grouped: {
            records: [{ id: 1, name: 'CNY parent row', amount: 100, quantity: 7, currency_id: [1, 'CNY'] }],
            enableGroupedRows: true,
            groupedRows: [
              {
                key: 'state:group-cny',
                label: 'CNY group',
                count: 1,
                sampleRows: [{ id: 1, name: 'CNY group row', amount: 100, quantity: 7, currency_id: [1, 'CNY'] }],
                pageOffset: 0,
                pageLimit: 3,
                aggregates: {
                  amount: {
                    aggregate: 'sum', data_type: 'monetary', aggregation_field: 'amount',
                    page_sum: 100, sum: 100, currency_field: 'currency_id', currency_id: 1,
                  },
                  quantity: {
                    aggregate: 'sum', data_type: 'integer', aggregation_field: 'quantity',
                    page_sum: 7, sum: 7,
                  },
                },
              },
              {
                key: 'state:group-usd',
                label: 'USD group',
                count: 1,
                sampleRows: [{ id: 2, name: 'USD group row', amount: 200, quantity: 8, currency_id: [2, 'USD'] }],
                pageOffset: 0,
                pageLimit: 3,
                aggregates: {
                  amount: {
                    aggregate: 'sum', data_type: 'monetary', aggregation_field: 'amount',
                    page_sum: 200, sum: 200, currency_field: 'currency_id', currency_id: 2,
                  },
                  quantity: {
                    aggregate: 'sum', data_type: 'integer', aggregation_field: 'quantity',
                    page_sum: 8, sum: 8,
                  },
                },
              },
            ],
            listProfile: {
              row_primary: 'name',
              columns: ['name', 'amount', 'quantity'],
              grouping: { default_sample_limit: 3, sample_limits: [3] },
            },
            groupSampleLimit: 3,
          },
        };
        const probe = reactive({ name: 'same' });
        window.setAggregateScenario = async (name) => {
          probe.name = name;
          await nextTick();
        };
        createApp({
          render() {
            const scenario = scenarios[probe.name];
            return h(ListPage, {
              title: 'Aggregate currency probe',
              model: 'x.aggregate_fixture',
              status: 'ok',
              loading: false,
              columns: ['name', 'amount', 'quantity'],
              records: scenario.records,
              subtitle: '',
              statusLabel: '',
              columnLabels: { name: 'Name', amount: 'Amount', quantity: 'Quantity' },
              columnOptions,
              listAggregates: scenario.listAggregates,
              enableGroupedRows: scenario.enableGroupedRows === true,
              groupedRows: scenario.groupedRows || [],
              listProfile: scenario.listProfile,
              groupSampleLimit: scenario.groupSampleLimit,
              listLimit: 20,
              listTotalCount: scenario.enableGroupedRows ? 2 : 1,
              pageSizeOptions: [10, 20, 50],
              pageSizeRange: { min: 1, max: 200 },
              contractPageType: { pageType: 'query-list', reason: 'aggregate-currency-contract' },
              onReload() {}, onRowClick() {}, onSearch() {}, onSort() {}, onFilter() {}, onToggleSelection() {}, onToggleSelectionAll() {},
            });
          },
        }).mount('#app');
      `;
    },
  }],
});

let browser;
let checks = 0;
const check = (condition, message) => {
  assert.ok(condition, message);
  checks += 1;
};
try {
  await server.listen();
  const address = server.httpServer?.address();
  assert(address && typeof address !== 'string');
  const origin = `http://127.0.0.1:${address.port}`;
  browser = await launchChromium({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  const forbiddenRequests = [];
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console:${message.text()}`);
  });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() !== 'GET' || url.pathname.startsWith('/api/') || url.origin !== origin) {
      forbiddenRequests.push(`${request.method()} ${url.pathname}`);
      await route.abort();
    } else {
      await route.continue();
    }
  });
  await page.goto(`${origin}/__aggregate_currency.html`);
  await page.waitForFunction(() => typeof window.setAggregateScenario === 'function');

  await page.evaluate(() => window.setAggregateScenario('same'));
  let footerText = (await page.locator('.flat-table tfoot').allInnerTexts()).join(' ');
  if (process.env.DEBUG_AGGREGATE_HTML === '1') {
    console.log(await page.locator('#app').innerHTML());
  }
  check(footerText.includes('¥100.00'), `same-currency page aggregate renders with declared currency: ${footerText}`);
  check(footerText.includes('¥300.00'), `same-currency complete aggregate renders with declared currency: ${footerText}`);
  let footerCells = await page.locator('.flat-table tfoot tr').first().locator('td').allInnerTexts();
  check(footerCells.some((text) => text.trim() === '7'), `same-currency non-monetary page aggregate remains visible: ${footerCells.join(' | ')}`);
  footerCells = await page.locator('.flat-table tfoot tr').nth(1).locator('td').allInnerTexts();
  check(footerCells.some((text) => text.trim() === '9'), `same-currency non-monetary total aggregate remains visible: ${footerCells.join(' | ')}`);

  for (const scenario of ['missing_id', 'missing_label', 'label_mismatch', 'mixed_scope', 'out_of_page_currency_mismatch', 'aggregate_type_mismatch']) {
    await page.evaluate((name) => window.setAggregateScenario(name), scenario);
    footerText = (await page.locator('.flat-table tfoot').allInnerTexts()).join(' ');
    check(!footerText.includes('100.00') && !footerText.includes('300.00'), `${scenario}: unproven monetary aggregate stays hidden: ${footerText}`);
  }

  await page.evaluate(() => window.setAggregateScenario('non_monetary'));
  footerText = (await page.locator('.flat-table tfoot').allInnerTexts()).join(' ');
  check(!footerText.includes('100.00') && !footerText.includes('300.00'), `non_monetary: unavailable monetary aggregate stays hidden: ${footerText}`);
  check(/\b7\b/.test(footerText) && /\b9\b/.test(footerText), `non_monetary: valid integer aggregate remains visible: ${footerText}`);

  await page.evaluate(() => window.setAggregateScenario('grouped'));
  const groupBlocks = page.locator('.group-block');
  check(await groupBlocks.count() === 2, 'two real grouped list sections render');
  const cnyGroupText = String(await groupBlocks.nth(0).locator('tfoot').innerText());
  const usdGroupText = String(await groupBlocks.nth(1).locator('tfoot').innerText());
  check(cnyGroupText.includes('¥100.00'), 'CNY group uses its own aggregate currency id');
  check(usdGroupText.includes('$200.00'), 'USD group uses its own aggregate currency id');

  await page.evaluate(() => window.setAggregateScenario('same'));
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileSummary = page.locator('[data-semantic-component="CollectionAggregateFooter"][data-aggregate-context="flat"]');
  await mobileSummary.waitFor();
  const mobileText = String(await mobileSummary.innerText());
  check(mobileText.includes('¥100.00') && mobileText.includes('¥300.00'), 'mobile summary preserves aggregate currency identity');
  check(/\b7\b/.test(mobileText) && /\b9\b/.test(mobileText), 'mobile summary preserves non-monetary aggregates');
  check(forbiddenRequests.length === 0, 'aggregate component fixture performs no backend or external requests');
  check(errors.length === 0, `aggregate component fixture has no browser errors: ${errors.join(' | ')}`);

  console.log(`[collection_aggregate_currency_component_test] PASS checks=${checks} scenarios=9 viewports=1440,390 backend_acceptance=false`);
} finally {
  try { await browser?.close(); } finally { await server.close(); }
}

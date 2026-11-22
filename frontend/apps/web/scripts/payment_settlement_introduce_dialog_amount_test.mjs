import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { build } from 'esbuild';
import { compileScript, parse } from 'vue/compiler-sfc';

const root = process.cwd();
const dialogFile = `${root}/frontend/apps/web/src/components/professional-fields/PaymentSettlementIntroduceDialog.vue`;

const output = await build({
  stdin: {
    contents: `
import { createApp, h, ref } from 'vue';
import { createPinia } from 'pinia';
import PaymentSettlementIntroduceDialog from ${JSON.stringify(dialogFile)};

const contract = {
  buttonLabel: '从结算单引入',
  purpose: 'settlement-introduce',
  title: '从结算单引入',
  description: '选择结算明细并确认引入。',
  searchPlaceholder: '搜索结算单',
  searchActionLabel: '搜索',
  searchLoadingLabel: '正在搜索',
  searchEmptyLabel: '没有可引入的结算单',
  resultContractLabel: '合同',
  resultAmountLabel: '结算金额',
  resultLineCountLabel: '明细',
  resultLineCountSuffix: '项',
  switchSourceLabel: '更换结算单',
  selectAllLabel: '全选',
  summarySelectedPrefix: '已选',
  summaryLineCountSuffix: '项',
  summarySettlementAmountLabel: '结算金额',
  summaryApplicableAmountLabel: '可申请金额',
  columnLabels: {
    name: '明细',
    contract: '合同',
    settlementAmount: '结算金额',
    applied: '已申请',
    remaining: '剩余',
    state: '状态',
  },
  stateAppliedLabel: '已完成',
  stateApplicableLabel: '可申请',
  allAppliedLabel: '全部明细已申请',
  historyTitle: '历史付款申请',
  historyCountSuffix: '条',
  historyExpandLabel: '展开',
  historyCollapseLabel: '收起',
  ratioModeLabel: '比例',
  amountModeLabel: '金额',
  ratioPlaceholder: '比例',
  totalPlaceholder: '金额',
  ratioHint: '按比例应用',
  amountHint: '按金额应用',
  applyTotalLabel: '本次引入',
  cancelLabel: '取消',
  confirmLabel: '确认引入',
  recordRequiredMessage: '请先保存付款申请',
  actions: {
    search: 'payment.request.settlement.search',
    preview: 'payment.request.settlement.preview',
    introduce: 'payment.request.add.settlement.lines',
  },
  payloadFields: {
    record: 'payment_request_id',
    source: 'settlement_id',
    sourceLines: 'source_line_ids',
    applyMode: 'apply_mode',
    ratio: 'ratio',
    totalAmount: 'total_amount',
    searchKeyword: 'keyword',
  },
};

const adapter = { currentRecordId: 701 };
const open = ref(false);
const app = createApp({
  render: () => h(PaymentSettlementIntroduceDialog, {
    contract,
    adapter,
    open: open.value,
  }),
});
app.use(createPinia());
app.mount('#app');
setTimeout(() => {
  open.value = true;
}, 0);
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
    'import.meta.env': '{}',
  },
  resolveExtensions: ['.tsx', '.ts', '.jsx', '.js', '.css', '.json', '.mjs'],
  loader: { '.css': 'empty' },
  alias: {
    vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,
    pinia: `${root}/frontend/apps/web/node_modules/pinia/dist/pinia.mjs`,
  },
  plugins: [{
    name: 'actual-vue-sfc',
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

const currency = {
  id: 7,
  name: 'CNY',
  symbol: '¥',
  decimal_places: 2,
  rounding: 0.01,
};

const preview = {
  currency,
  settlement: {
    id: 91,
    name: 'SET/001',
    display_name: 'SET/001',
    contract_name: '测试合同',
    amount_total: 0,
  },
  lines: [{
    id: 1,
    name: '零金额明细',
    contract_name: '测试合同',
    amount: 0,
    applied: 0,
    remaining: 0,
    is_fully_applied: false,
  }],
  related_payment_requests: [
    {
      id: 1,
      name: 'PAY/000',
      state: 'draft',
      state_label: '草稿',
      amount: 999.99,
      applied_to_settlement: 0,
      date_request: '2026-11-22',
    },
    {
      id: 2,
      name: 'PAY/NULL',
      state: 'draft',
      state_label: '草稿',
      amount: 77.7,
      applied_to_settlement: null,
      date_request: '2026-11-22',
    },
    {
      id: 3,
      name: 'PAY/MISSING',
      state: 'draft',
      state_label: '草稿',
      amount: 0,
      date_request: '2026-11-22',
    },
    {
      id: 4,
      name: 'PAY/POS',
      state: 'draft',
      state_label: '草稿',
      amount: 1,
      applied_to_settlement: 1234.5,
      date_request: '2026-11-22',
    },
    {
      id: 5,
      name: 'PAY/NEG',
      state: 'draft',
      state_label: '草稿',
      amount: 1,
      applied_to_settlement: -12.34,
      date_request: '2026-11-22',
    },
  ],
  totals: {
    settlement_amount: 0,
    line_amount_total: 0,
    applied_total: 0,
    remaining_total: 0,
  },
};

const { launchChromium } = await import('../../../../scripts/verify/playwright_runtime.mjs');
const browser = await launchChromium();
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  const requestIntents = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.route('**/api/v1/intent', async (route) => {
    const payload = JSON.parse(route.request().postData() || '{}');
    requestIntents.push(String(payload.intent || ''));
    let data;
    if (payload.intent === 'payment.request.settlement.search') {
      data = {
        settlements: [{
          id: 91,
          name: 'SET/001',
          display_name: 'SET/001',
          amount_total: 0,
          currency,
          contract_name: '测试合同',
          partner_name: '测试单位',
          line_count: 1,
        }],
      };
    } else if (payload.intent === 'payment.request.settlement.preview') {
      data = preview;
    } else {
      throw new Error(`unexpected intent ${payload.intent}`);
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, data, meta: { trace_id: 'trace-dialog-amount' } }),
    });
  });
  await page.route('http://dialog.test/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<!doctype html><html><body><div id="app"></div></body></html>',
    });
  });

  await page.goto('http://dialog.test/');
  await page.addScriptTag({ content: output.outputFiles[0].text });
  await page.waitForTimeout(250);
  if (errors.length) {
    throw new Error(`dialog mount failed: ${JSON.stringify(errors)} html=${(await page.content()).slice(0, 2000)}`);
  }

  const results = page.locator('[data-settle-results]');
  try {
    await results.locator('.settle-option').waitFor({ state: 'visible', timeout: 5000 });
  } catch (error) {
    throw new Error(`settlement search did not render: ${JSON.stringify({
      requestIntents,
      errors,
      text: String(await page.locator('body').innerText()).slice(0, 1000),
    })}`, { cause: error });
  }
  const searchText = String(await results.textContent() || '').replace(/\s+/g, ' ').trim();
  assert.ok(searchText.includes('0.00'), searchText);

  await results.locator('.settle-option').click();
  const previewRoot = page.locator('[data-settle-preview]');
  await previewRoot.waitFor({ state: 'visible' });
  const lineAmount = String(await page.locator('.settle-line .settle-col-amount').first().innerText());
  assert.ok(lineAmount.includes('0.00'), lineAmount);

  const history = page.locator('[data-settle-history]');
  await history.locator('.settle-history-head').click();
  const historyAmounts = await history.locator('.settle-history-amount').allInnerTexts();
  assert.equal(historyAmounts.length, 5);
  assert.ok(historyAmounts[0].includes('0.00'), historyAmounts[0]);
  assert.equal(historyAmounts[1].trim(), '--');
  assert.equal(historyAmounts[2].trim(), '--');
  assert.ok(historyAmounts[3].includes('1,234.50'), historyAmounts[3]);
  assert.ok(historyAmounts[4].trim().startsWith('-'), historyAmounts[4]);
  assert.ok(historyAmounts[4].includes('12.34'), historyAmounts[4]);
  assert.ok(!historyAmounts[0].includes('999.99'), historyAmounts[0]);

  assert.equal(requestIntents.filter((intent) => intent === 'payment.request.add.settlement.lines').length, 0);
  assert.deepEqual(errors, []);

  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(String(await page.locator('.settle-history-amount').first().innerText()).includes('0.00'));
  assert.ok(String(await page.locator('.settle-line .settle-col-amount').first().innerText()).includes('0.00'));

  console.log(JSON.stringify({
    browser: browser.version(),
    cases: 12,
    viewports: [1440, 390],
    zeroPreserved: 'PASS',
    missingPreserved: 'PASS',
    positiveAndNegative: 'PASS',
    writeRequests: 0,
    consoleErrors: 0,
  }));
} finally {
  await browser.close();
}

#!/usr/bin/env node
/**
 * Visual density baseline audit for TDesign product surfaces.
 *
 * Verifies that rendered component metrics match the product density token
 * contract on the list and form surfaces:
 *
 *   list  surface (t-table)   : header 42px / row 46px / query-bar 46px
 *   form  surface (t-input …) : control height = --sc-component-input-form-height (36px)
 *                                readonly values = 14px in readonly sections
 *
 * Fails (non-zero exit) when any asserted metric drifts from its token value,
 * so it can be wired into a CI gate. Mirrors the token contract documented in
 * docs/audit/visual_density_baseline_v1.md.
 *
 * Usage:
 *   E2E_PASSWORD=... \
 *   FRONTEND_URL=http://127.0.0.1:5175 \
 *   E2E_LOGIN=fixture_role_activity_accounting \
 *   node scripts/verify/frontend_density_baseline_audit.mjs
 *
 * Env:
 *   FRONTEND_URL  base URL (default http://127.0.0.1:5175)
 *   E2E_LOGIN     login (default fixture_role_activity_accounting)
 *   E2E_PASSWORD  password (required)
 *   TARGET_LIST_URL / TARGET_FORM_URL  override target pages (defaults to
 *     payment request list 775/545 and form /f/payment.request/1709)
 *   TOLERANCE_PX  metric tolerance (default 1)
 */
import { launchChromium } from './playwright_runtime.mjs';

const baseUrl = String(process.env.FRONTEND_URL || 'http://127.0.0.1:5175').replace(/\/$/, '');
const loginName = process.env.E2E_LOGIN || 'fixture_role_activity_accounting';
const password = process.env.E2E_PASSWORD || '';
const tolerance = Math.max(0, Number(process.env.TOLERANCE_PX || 1));

const listUrl = process.env.TARGET_LIST_URL || `${baseUrl}/a/775?menu_id=545`;
const formUrl = process.env.TARGET_FORM_URL || `${baseUrl}/f/payment.request/1709?menu_id=545&action_id=775`;
// Worksheet surface: the 89px row height is a KNOWN CHARACTERISTIC of TDesign
// 1.20.5 fixed-layout tree-table (see docs/audit/visual_density_baseline_v1.md
// section 1). This audit enforces an UPPER bound so the row height cannot
// regress further; a future component-layer fix should lower the baseline.
const worksheetUrl = process.env.TARGET_WORKSHEET_URL || `${baseUrl}/a/748?menu_id=664`;
const worksheetRowMax = Math.max(46, Number(process.env.WORKSHEET_ROW_MAX_BASELINE || 89));

if (!password) {
  console.error('[density-baseline] E2E_PASSWORD is required');
  process.exit(2);
}

function diff(name, actual, expected, checks) {
  const ok = Math.abs(actual - expected) <= tolerance;
  checks.push({ name, actual, expected, ok });
  return ok;
}

function diffMax(name, actual, max, checks) {
  const ok = actual <= max;
  checks.push({ name, actual, expected: `<= ${max}`, ok });
  return ok;
}

async function login(page) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(2000);
  await page.locator('input').nth(0).fill(loginName);
  await page.locator('input').nth(1).fill(password);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
}

async function auditList(page) {
  await page.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 25000 });
  await page.waitForSelector('table tbody tr', { timeout: 20000 });
  await page.waitForTimeout(2500);
  return page.evaluate(() => {
    const th = document.querySelector('.t-table thead th, .t-table__header th');
    const tr = document.querySelector('table tbody tr');
    const qb = document.querySelector('.product-list-query-bar');
    // Cell presentation contracts. ListPage.css declares these scoped, so they
    // never reach the TDesign-rendered td; the global list-surface rules in
    // product-patterns.css must restore them (see visual_density_baseline_v1.md
    // section "cell presentation").
    const longTextTd = document.querySelector('.t-table td.column-long-text');
    const longTextCell = longTextTd && longTextTd.firstElementChild;
    const moneyTd = document.querySelector('.t-table td.column-layout-money, .t-table td.column-numeric');
    const dateTd = document.querySelector('.t-table td.column-layout-date');
    const textTd = document.querySelector('.t-table td.column-layout-text');
    const styleOf = (el, prop) => el ? getComputedStyle(el)[prop] : null;
    // Pagination must render the record count exactly once: the custom
    // .pagination-total owns "共 N 条" and ScPagination disables the TDesign
    // built-in total through its public totalContent prop.
    const pagFooter = document.querySelector('.pagination-footer');
    const pagVisible = pagFooter ? pagFooter.innerText.replace(/\s+/g, ' ') : '';
    const paginationCountMatches = (pagVisible.match(/共\s*\d+\s*条/g) || []).length;
    return {
      th: th ? Math.round(th.getBoundingClientRect().height) : null,
      row: tr ? Math.round(tr.getBoundingClientRect().height) : null,
      queryBar: qb ? Math.round(qb.getBoundingClientRect().height) : null,
      longTextEllipsis: longTextCell ? styleOf(longTextCell, 'textOverflow') : null,
      longTextOverflow: longTextCell ? styleOf(longTextCell, 'overflow') : null,
      moneyAlign: moneyTd ? styleOf(moneyTd, 'textAlign') : null,
      dateColor: dateTd ? styleOf(dateTd, 'color') : null,
      textColor: textTd ? styleOf(textTd, 'color') : null,
      paginationCountMatches,
    };
  });
}

async function auditForm(page) {
  await page.goto(formUrl, { waitUntil: 'domcontentloaded', timeout: 25000 });
  await page.waitForSelector('.t-input', { timeout: 20000 });
  await page.waitForTimeout(3500);
  return page.evaluate(() => {
    const inputs = [...document.querySelectorAll('.t-input, .t-select, .t-date-picker')]
      .filter((e) => e.getBoundingClientRect().height > 0 && e.offsetParent !== null);
    // main form controls only: exclude the .sc-input t-input--prefix search box
    const main = inputs.filter((e) => !(e.classList.contains('t-input--prefix') && e.closest('.sc-input')));
    const heights = main.map((e) => Math.round(e.getBoundingClientRect().height));
    const input = heights.length ? heights[0] : null;
    const uniform = heights.every((h) => h === heights[0]);

    const ro = [...document.querySelectorAll('.readonly-value, .professional-base-field-control__readonly')]
      .filter((e) => e.getBoundingClientRect().height > 0 && (e.innerText || '').trim().length > 0);
    const roSizes = ro.map((e) => Math.round(parseFloat(getComputedStyle(e).fontSize) * 100) / 100);
    const roWeights = ro.map((e) => getComputedStyle(e).fontWeight);

    // Form-structure contract (canonical render detail, v1):
    //  - the canonical sheet must span the full task-section card (grid-column
    //    1 / -1) so its interior reaches the width that triggers the two-column
    //    form grid
    //  - fields in the core-input card must occupy at least two columns (the
    //    two-column canonical layout landed as part of the form-structure work)
    //  - readonly facts must stay compact (their height collapsed from
    //    line-height-inflated 90-111px to content-height 49-69px)
    const sheet = document.querySelector('.object-task-page__core-input .canonical-form-node--sheet');
    const sheetGridCol = sheet ? getComputedStyle(sheet).gridColumn : null;
    const coreFields = [...document.querySelectorAll('.object-task-page__core-input .field')]
      .filter((e) => e.getBoundingClientRect().height > 0 && e.offsetParent !== null);
    const fieldXs = coreFields.map((e) => Math.round(e.getBoundingClientRect().x));
    const fieldColumnCount = [...new Set(fieldXs)].length;
    const facts = [...document.querySelectorAll('.canonical-form-node--readonly-fact')]
      .filter((e) => e.getBoundingClientRect().height > 0);
    const factHeights = facts.map((e) => Math.round(e.getBoundingClientRect().height));
    const factMaxHeight = factHeights.length ? Math.max(...factHeights) : null;

    return {
      inputCount: heights.length,
      inputHeight: input,
      inputsUniform: uniform,
      readonlyCount: ro.length,
      readonlySizes: [...new Set(roSizes)],
      readonlyUniform: new Set(roSizes).size <= 1,
      readonlyWeights: [...new Set(roWeights)],
      readonlyWeightUniform: new Set(roWeights).size <= 1,
      sheetGridCol,
      fieldColumnCount,
      factCount: factHeights.length,
      factMaxHeight,
    };
  });
}

async function auditWorksheet(page) {
  await page.goto(worksheetUrl, { waitUntil: 'domcontentloaded', timeout: 25000 });
  await page.waitForSelector('table tbody tr', { timeout: 20000 });
  await page.waitForTimeout(3000);
  return page.evaluate(() => {
    const trs = [...document.querySelectorAll('table tbody tr')];
    const heights = trs.map((tr) => Math.round(tr.getBoundingClientRect().height));
    return {
      rows: trs.length,
      rowHeights: [...new Set(heights)],
      firstRowHeight: heights.length ? heights[0] : null,
    };
  });
}

const browser = await launchChromium({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
const checks = [];
const results = {};

try {
  await login(page);
  console.log(`[density-baseline] auditing list ${listUrl}`);
  results.list = await auditList(page);
  console.log(`[density-baseline] list -> th=${results.list.th} row=${results.list.row} queryBar=${results.list.queryBar}`);

  console.log(`[density-baseline] auditing form ${formUrl}`);
  results.form = await auditForm(page);
  console.log(`[density-baseline] form -> input=${results.form.inputHeight} (x${results.form.inputCount}, uniform=${results.form.inputsUniform}) readonly=${JSON.stringify(results.form.readonlySizes)}`);

  console.log(`[density-baseline] auditing worksheet ${worksheetUrl}`);
  results.worksheet = await auditWorksheet(page);
  console.log(`[density-baseline] worksheet -> rows=${results.worksheet.rows} heights=${JSON.stringify(results.worksheet.rowHeights)} (max baseline ${worksheetRowMax})`);

  if (results.list.th == null || results.list.row == null) {
    console.error('[density-baseline] FAIL list table not rendered');
    process.exitCode = 1;
  } else {
    diff('list.header-height', results.list.th, 42, checks);
    diff('list.row-height', results.list.row, 46, checks);
    if (results.list.queryBar != null) diff('list.query-bar-height', results.list.queryBar, 46, checks);
  }

  // Cell presentation contracts (scoped ListPage.css never reaches TDesign td;
  // the global product-patterns rules restore them).
  if (results.list.longTextEllipsis !== 'ellipsis') {
    console.error(`[density-baseline] FAIL long-text cell not truncated: overflow=${results.list.longTextOverflow} text-overflow=${results.list.longTextEllipsis}`);
    checks.push({ name: 'list.long-text-ellipsis', actual: results.list.longTextEllipsis, expected: 'ellipsis', ok: false });
  } else {
    checks.push({ name: 'list.long-text-ellipsis', actual: results.list.longTextEllipsis, expected: 'ellipsis', ok: true });
  }
  if (results.list.moneyAlign !== 'right') {
    console.error(`[density-baseline] FAIL monetary/numeric cell not right-aligned: ${results.list.moneyAlign}`);
    checks.push({ name: 'list.money-right-align', actual: results.list.moneyAlign, expected: 'right', ok: false });
  } else {
    checks.push({ name: 'list.money-right-align', actual: results.list.moneyAlign, expected: 'right', ok: true });
  }
  if (results.list.dateColor != null && results.list.textColor != null && results.list.dateColor === results.list.textColor) {
    console.error(`[density-baseline] FAIL date cell uses primary color (${results.list.dateColor}) instead of secondary token`);
    checks.push({ name: 'list.date-secondary-color', actual: results.list.dateColor, expected: '!= text primary', ok: false });
  } else if (results.list.dateColor == null || results.list.textColor == null) {
    console.warn('[density-baseline] WARN date/text cells not found, skipping date-color check');
  } else {
    checks.push({ name: 'list.date-secondary-color', actual: results.list.dateColor, expected: `!= ${results.list.textColor}`, ok: true });
  }
  // Record count must be rendered exactly once in the pagination footer.
  if (results.list.paginationCountMatches != null && results.list.paginationCountMatches > 1) {
    console.error(`[density-baseline] FAIL record count rendered ${results.list.paginationCountMatches} times in pagination footer (custom + TDesign built-in duplicate)`);
    checks.push({ name: 'list.pagination-count-single', actual: results.list.paginationCountMatches, expected: '<= 1', ok: false });
  } else {
    checks.push({ name: 'list.pagination-count-single', actual: results.list.paginationCountMatches, expected: '<= 1', ok: true });
  }

  if (results.worksheet.firstRowHeight == null) {
    console.error('[density-baseline] FAIL worksheet table not rendered');
    process.exitCode = 1;
  } else {
    diffMax('worksheet.row-height-upper-bound', results.worksheet.firstRowHeight, worksheetRowMax, checks);
  }

  if (results.form.inputHeight == null) {
    console.error('[density-baseline] FAIL form controls not rendered');
    process.exitCode = 1;
  } else {
    diff('form.control-height', results.form.inputHeight, 36, checks);
    if (!results.form.inputsUniform) {
      console.warn('[density-baseline] WARN form controls not uniform (mixed heights)');
    }
    if (results.form.readonlyCount > 0) {
      if (!results.form.readonlyUniform) {
        console.error(`[density-baseline] FAIL readonly sizes not uniform: ${JSON.stringify(results.form.readonlySizes)}`);
        checks.push({ name: 'form.readonly-uniform', actual: results.form.readonlySizes, expected: 'single 14px', ok: false });
      } else {
        const roSize = results.form.readonlySizes[0];
        if (Math.abs(roSize - 14) > 0.5) {
          console.error(`[density-baseline] FAIL readonly size ${roSize} != 14`);
          checks.push({ name: 'form.readonly-size', actual: roSize, expected: 14, ok: false });
        } else {
          checks.push({ name: 'form.readonly-size', actual: roSize, expected: 14, ok: true });
        }
      }
      if (!results.form.readonlyWeightUniform) {
        console.error(`[density-baseline] FAIL readonly weights not uniform: ${JSON.stringify(results.form.readonlyWeights)}`);
        checks.push({ name: 'form.readonly-weight-uniform', actual: results.form.readonlyWeights, expected: 'single 400', ok: false });
      } else if (results.form.readonlyWeights[0] !== '400') {
        console.error(`[density-baseline] FAIL readonly weight ${results.form.readonlyWeights[0]} != 400`);
        checks.push({ name: 'form.readonly-weight', actual: results.form.readonlyWeights[0], expected: '400', ok: false });
      } else {
        checks.push({ name: 'form.readonly-weight', actual: results.form.readonlyWeights[0], expected: '400', ok: true });
      }
    }
    // Form structure: the canonical sheet spans the full task-section card.
    if (results.form.sheetGridCol == null) {
      console.warn('[density-baseline] WARN canonical sheet not found, skipping sheet-span check');
    } else if (!String(results.form.sheetGridCol).includes('-1')) {
      console.error(`[density-baseline] FAIL canonical sheet grid-column ${results.form.sheetGridCol} != 1 / -1 (right half of the task-section card stays empty)`);
      checks.push({ name: 'form.sheet-spans-card', actual: results.form.sheetGridCol, expected: '1 / -1', ok: false });
    } else {
      checks.push({ name: 'form.sheet-spans-card', actual: results.form.sheetGridCol, expected: '1 / -1', ok: true });
    }
    // Form structure: core-input fields occupy at least two columns.
    if (results.form.fieldColumnCount == null || results.form.fieldColumnCount < 1) {
      console.warn('[density-baseline] WARN no core-input fields found, skipping field-column check');
    } else if (results.form.fieldColumnCount < 2) {
      console.error(`[density-baseline] FAIL core-input fields occupy ${results.form.fieldColumnCount} column(s), expected >= 2 (two-column canonical layout regressed to single column)`);
      checks.push({ name: 'form.field-two-column', actual: results.form.fieldColumnCount, expected: '>= 2', ok: false });
    } else {
      checks.push({ name: 'form.field-two-column', actual: results.form.fieldColumnCount, expected: '>= 2', ok: true });
    }
    // Form structure: readonly facts stay compact (content height, not
    // line-height-inflated ~90-111px). Baseline max is 69px; allow headroom.
    const factMaxBaseline = Math.max(80, Number(process.env.FACT_HEIGHT_MAX_BASELINE || 80));
    if (results.form.factCount == null || results.form.factCount === 0) {
      console.warn('[density-baseline] WARN no readonly facts found, skipping fact-height check');
    } else if (results.form.factMaxHeight > factMaxBaseline) {
      console.error(`[density-baseline] FAIL readonly fact max height ${results.form.factMaxHeight} > ${factMaxBaseline} (facts line-height inflated again)`);
      checks.push({ name: 'form.fact-height-compact', actual: results.form.factMaxHeight, expected: `<= ${factMaxBaseline}`, ok: false });
    } else {
      checks.push({ name: 'form.fact-height-compact', actual: results.form.factMaxHeight, expected: `<= ${factMaxBaseline}`, ok: true });
    }
  }
} finally {
  await browser.close();
}

console.log('[density-baseline] checks:');
for (const c of checks) {
  console.log(`  ${c.ok ? 'PASS' : 'FAIL'}  ${c.name}  actual=${JSON.stringify(c.actual)} expected=${JSON.stringify(c.expected)}`);
  if (!c.ok) process.exitCode = 1;
}
if (process.exitCode) {
  console.error('[density-baseline] DENSITY BASELINE VIOLATION');
} else {
  console.log('[density-baseline] density baseline OK');
}

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

if (!password) {
  console.error('[density-baseline] E2E_PASSWORD is required');
  process.exit(2);
}

function diff(name, actual, expected, checks) {
  const ok = Math.abs(actual - expected) <= tolerance;
  checks.push({ name, actual, expected, ok });
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
    return {
      th: th ? Math.round(th.getBoundingClientRect().height) : null,
      row: tr ? Math.round(tr.getBoundingClientRect().height) : null,
      queryBar: qb ? Math.round(qb.getBoundingClientRect().height) : null,
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
    return {
      inputCount: heights.length,
      inputHeight: input,
      inputsUniform: uniform,
      readonlyCount: ro.length,
      readonlySizes: [...new Set(roSizes)],
      readonlyUniform: new Set(roSizes).size <= 1,
      readonlyWeights: [...new Set(roWeights)],
      readonlyWeightUniform: new Set(roWeights).size <= 1,
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

  if (results.list.th == null || results.list.row == null) {
    console.error('[density-baseline] FAIL list table not rendered');
    process.exitCode = 1;
  } else {
    diff('list.header-height', results.list.th, 42, checks);
    diff('list.row-height', results.list.row, 46, checks);
    if (results.list.queryBar != null) diff('list.query-bar-height', results.list.queryBar, 46, checks);
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

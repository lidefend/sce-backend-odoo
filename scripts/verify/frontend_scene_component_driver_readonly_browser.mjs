#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5175';
const DB_NAME = process.env.DB_NAME || 'sc_frontend_acceptance';
const PASSWORD = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const TARGET = JSON.parse(process.env.SCENE_COMPONENT_DRIVER_TARGETS_JSON || '{}');
const OUTPUT = process.env.SCENE_COMPONENT_DRIVER_ARTIFACTS || 'artifacts/frontend-scene-component-driver';

function check(value, message) {
  if (!value) throw new Error(message);
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function requestIntent(request) {
  if (request.method() !== 'POST') return '';
  try {
    const body = request.postDataJSON();
    return String(body?.intent || body?.params?.intent || '');
  } catch {
    return '';
  }
}

function isBusinessMutation(request) {
  const intent = requestIntent(request);
  if (['execute_button', 'api.data.create', 'api.data.write', 'api.data.unlink'].includes(intent)) return true;
  if (intent !== 'api.data') return false;
  try {
    const body = request.postDataJSON();
    return ['create', 'write', 'unlink'].includes(String(body?.params?.op || body?.params?.payload?.op || ''));
  } catch {
    return true;
  }
}

async function main() {
  check(PASSWORD, 'SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
  check(TARGET.model && !String(TARGET.model).includes('payment') && TARGET.record_id > 0 && TARGET.action_id > 0 && TARGET.menu_id > 0, 'invalid non-payment target');
  fs.mkdirSync(OUTPUT, { recursive: true });
  const browser = await launchChromium();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const evidence = { console: [], pageerror: [], failed: [], mutations: [], systemInitPolicy: null, contractLayoutShape: null, contractSha256: '' };
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) evidence.console.push(message.text());
  });
  page.on('pageerror', (error) => evidence.pageerror.push(error.message));
  page.on('request', (request) => {
    if (isBusinessMutation(request)) evidence.mutations.push({ intent: requestIntent(request), url: request.url() });
  });
  page.on('response', async (response) => {
    if (response.status() >= 400 && !/favicon/i.test(response.url())) evidence.failed.push({ status: response.status(), url: response.url() });
    const request = response.request();
    const intent = requestIntent(request);
    if (request.method() === 'POST' && /json/i.test(response.headers()['content-type'] || '')) {
      try {
        const body = await response.json();
        const findContract = (value, depth = 0) => {
          if (!value || typeof value !== 'object' || depth > 5) return null;
          if (value.layoutContract?.containerTree) return value;
          for (const nested of Object.values(value)) {
            const found = findContract(nested, depth + 1);
            if (found) return found;
          }
          return null;
        };
        const contract = findContract(body);
        const summarize = (nodes) => (Array.isArray(nodes) ? nodes : []).map((node) => ({
          keys: node && typeof node === 'object' ? Object.keys(node).sort() : [],
          containerId: String(node?.containerId || ''),
          containerType: String(node?.containerType || ''),
          type: String(node?.type || ''),
          name: String(node?.name || ''),
          children: summarize(node?.children),
        }));
        if (contract) {
          evidence.contractLayoutShape = { intent, nodes: summarize(contract.layoutContract.containerTree) };
          evidence.contractSha256 = String(contract?.meta?.lifecycle?.integrity?.contractSha256 || '');
        }
      } catch { /* shape evidence remains unavailable */ }
    }
    if (intent !== 'system.init') return;
    try {
      const body = await response.json();
      const data = body?.data || body?.result?.data || body?.result || {};
      evidence.systemInitPolicy = data?.feature_flags?.scene_component_drivers_v1 || null;
    } catch { /* evidence remains fail-closed below */ }
  });
  try {
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.locator('#login-username, input[autocomplete="username"]').first().fill(TARGET.login);
    await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
    const database = page.locator('input').nth(2);
    if (await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
    await page.locator('.layout-shell').waitFor({ timeout: 45000 });

    const route = `/r/${encodeURIComponent(TARGET.model)}/${TARGET.record_id}?action_id=${TARGET.action_id}&menu_id=${TARGET.menu_id}`;
    await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const anyHost = page.locator('[data-contract-form-driver]').first();
    try {
      await anyHost.waitFor({ state: 'visible', timeout: 8000 });
    } catch (error) {
      const failureScreenshot = path.join(OUTPUT, 'failure-before-driver-host.png');
      await page.screenshot({ path: failureScreenshot, fullPage: true });
      const diagnostic = await page.evaluate(() => ({
        url: location.href,
        title: document.title,
        text: String(document.body?.innerText || '').slice(0, 1200),
        pageMode: document.querySelector('[data-product-page-mode]')?.getAttribute('data-product-page-mode') || '',
        contractError: document.querySelector('[data-contract-form-driver-error]')?.textContent || '',
      }));
      const failureReport = path.join(OUTPUT, 'failure-before-driver-host.json');
      fs.writeFileSync(failureReport, `${JSON.stringify({ ...diagnostic, systemInitPolicy: evidence.systemInitPolicy, contractLayoutShape: evidence.contractLayoutShape, screenshot: failureScreenshot }, null, 2)}\n`);
      throw new Error(`ContractForm driver host missing: ${JSON.stringify({ ...diagnostic, systemInitPolicy: evidence.systemInitPolicy, contractLayoutShape: evidence.contractLayoutShape, screenshot: failureScreenshot, report: failureReport })}`, { cause: error });
    }
    const hostDiagnostic = {
      activeKit: await anyHost.getAttribute('data-contract-form-driver'),
      source: await anyHost.getAttribute('data-contract-form-driver-source'),
      reason: await anyHost.getAttribute('data-contract-form-driver-reason'),
      systemInitPolicy: evidence.systemInitPolicy,
      route,
    };
    check(hostDiagnostic.activeKit === 'tdesign-modern', `TDesign policy was not selected: ${JSON.stringify(hostDiagnostic)}`);
    const host = page.locator('[data-contract-form-driver="tdesign-modern"]');
    await page.locator('[data-scene-ui-kit="tdesign-modern"]').waitFor({ state: 'visible', timeout: 45000 });
    await page.locator('[data-control-driver="tdesign-modern"] [data-scene-driver-control]').first().waitFor({ state: 'visible', timeout: 45000 });
    await page.waitForTimeout(500);

    const result = await page.evaluate(() => {
      const host = document.querySelector('[data-contract-form-driver="tdesign-modern"]');
      const fields = [...document.querySelectorAll('[data-product-page-mode="form"] [data-field-name]')];
      const driverFields = [...document.querySelectorAll('[data-control-driver="tdesign-modern"]')];
      const editableDriverControls = driverFields.filter((node) => {
        const control = node.querySelector('input, textarea, select, [contenteditable="true"]');
        return control && !control.hasAttribute('readonly') && !control.hasAttribute('disabled');
      });
      return {
        sourceContractSha256: host?.getAttribute('data-source-contract-sha') || '',
        renderModelFields: Number(host?.getAttribute('data-render-model-fields') || 0),
        renderModelActions: Number(host?.getAttribute('data-render-model-actions') || 0),
        fieldCount: fields.length,
        uniqueFieldCount: new Set(fields.map((node) => node.getAttribute('data-field-name'))).size,
        driverFieldCount: driverFields.length,
        editableDriverControlCount: editableDriverControls.length,
        horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
        fallback: document.querySelector('[data-scene-driver-fallback="true"]') !== null,
      };
    });
    check(evidence.systemInitPolicy?.locked_kit === 'tdesign-modern', 'system.init entitlement policy was not authoritative');
    check(result.sourceContractSha256, 'normalized source contract identity missing');
    check(evidence.contractSha256 === result.sourceContractSha256, 'network and canvas contract identities differ');
    check(result.fieldCount > 0 && result.fieldCount === result.uniqueFieldCount, 'readonly fields are missing or duplicated');
    check(result.renderModelFields === result.uniqueFieldCount, 'render model and DOM field sets differ');
    check(result.driverFieldCount > 0, 'TDesign did not render any supported readonly field');
    check(result.editableDriverControlCount === 0, 'readonly driver exposed an editable control');
    check(result.horizontalOverflow === 0, 'readonly driver caused horizontal overflow');
    check(result.fallback === false, 'TDesign load unexpectedly fell back to Native');
    check(evidence.mutations.length === 0, 'readonly journey issued a business mutation');
    check(evidence.console.length === 0 && evidence.pageerror.length === 0 && evidence.failed.length === 0, 'runtime errors detected');

    const screenshot = path.join(OUTPUT, 'tdesign-readonly-project.png');
    await page.screenshot({ path: screenshot, fullPage: true });
    const report = {
      schema_version: 'frontend_scene_component_driver_readonly.v1',
      result: 'PASS',
      git_sha: process.env.GIT_SHA || '',
      database: DB_NAME,
      target: { ...TARGET, login: TARGET.login },
      driver: 'tdesign-modern',
      ...result,
      runtime_errors: {
        console: evidence.console,
        pageerror: evidence.pageerror,
        failed: evidence.failed,
        mutations: evidence.mutations,
        systemInitPolicy: evidence.systemInitPolicy,
      },
      screenshot: { path: screenshot, sha256: sha256(screenshot) },
    };
    const reportPath = path.join(OUTPUT, 'report.json');
    fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
    console.log(`[frontend_scene_component_driver_readonly_browser] PASS report=${reportPath}`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`[frontend_scene_component_driver_readonly_browser] FAIL ${error.stack || error.message}`);
  process.exit(2);
});

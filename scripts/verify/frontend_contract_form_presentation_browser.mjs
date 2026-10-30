#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';
import { resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'native-form-presentation', operation: 'readonly' });
const target = JSON.parse(process.env.CONTRACT_FORM_PRESENTATION_TARGET || '{}');
const output = path.resolve(process.env.CONTRACT_FORM_PRESENTATION_OUTPUT || 'artifacts/frontend-contract-form-presentation/summary.json');

function check(value, message) { if (!value) throw new Error(message); }

check(target && typeof target.route === 'string' && target.route.startsWith('/'), 'target route is required');
check(
  ['construction.contract', 'construction.contract.income', 'construction.contract.expense', 'sc.general.contract'].includes(target.model),
  'target model must be a construction contract model',
);
check(acceptance.login && acceptance.password, 'governed acceptance credentials are required');
fs.mkdirSync(path.dirname(output), { recursive: true });

const identityByModel = {
  'sc.general.contract': {
    title: 'contract_name',
    fields: ['contract_name', 'contract_no', 'contract_direction', 'contract_type', 'name'],
    status: ['state', 'validation_status'],
  },
  'construction.contract': {
    title: 'subject',
    fields: ['subject', 'name', 'type', 'document_status', 'business_category_id'],
    status: ['state', 'document_status', 'validation_status'],
  },
};
const identity = identityByModel[target.model];
check(identity, `no identity assertion declared for model ${target.model}`);
const viewports = [
  { key: '1440', width: 1440, height: 900 },
  { key: '1024', width: 1024, height: 800 },
  { key: '768', width: 768, height: 900 },
  { key: '390', width: 390, height: 844 },
];

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const evidence = {
  schema: 'frontend_contract_form_presentation_browser.v1',
  passed: false,
  provenance: {
    profile: acceptance.profile,
    base_url: acceptance.baseUrl,
    database: acceptance.database,
    login: acceptance.login,
    expected_sha: acceptance.provenance.expectedSha,
    route: target.route,
    model: target.model,
  },
  console: [],
  pageerror: [],
  http: [],
  viewports: [],
};

page.on('console', (message) => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) evidence.console.push(message.text()); });
page.on('pageerror', (error) => evidence.pageerror.push(error.message));
page.on('response', (response) => { if (response.status() >= 500) evidence.http.push({ status: response.status(), url: response.url() }); });

await page.goto(`${acceptance.baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
await page.locator('#login-username, input[autocomplete="username"]').first().fill(acceptance.login);
await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(acceptance.password);
const database = page.locator('input').nth(2);
if (await database.isEnabled().catch(() => false)) await database.fill(acceptance.database);
await page.getByRole('button', { name: /^登录$/ }).click();
await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });

await page.goto(`${acceptance.baseUrl}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
await page.waitForFunction(() => !/正在载入|正在加载|正在初始化/.test(document.body.innerText || ''), null, { timeout: 45_000 });
await page.locator(`[data-field-name="${identity.title}"]`).first().waitFor({ state: 'visible', timeout: 45_000 });

// Native form fields carry data-field-name; assert the identity fields render.
check(await page.locator(`[data-field-name="${identity.title}"]`).count() >= 1, `${identity.title} title field must render`);

for (const field of identity.fields) {
  const present = await page.locator(`[data-field-name="${field}"]`).count();
  check(present >= 1, `identity field ${field} is missing from the rendered form`);
}

// The lifecycle statusbar lives in the header, not the sheet; assert it renders
// through the status surface the native form publishes.
check(await page.locator('[data-status]').count() >= 1, 'state lifecycle status surface is missing');

for (const vp of viewports) {
  await page.setViewportSize({ width: vp.width, height: vp.height });
  await page.waitForTimeout(250);
  const geometry = await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    const title = document.querySelector(`[data-field-name="${identity.title}"]`);
    return {
      scrollWidth: Math.max(doc.scrollWidth, body ? body.scrollWidth : 0),
      clientWidth: doc.clientWidth,
      horizontalOverflow: Math.max(doc.scrollWidth, body ? body.scrollWidth : 0) > doc.clientWidth + 1,
      bandRect: title ? { x: title.getBoundingClientRect().x, width: title.getBoundingClientRect().width } : null,
      titleRect: title ? { width: title.getBoundingClientRect().width, height: title.getBoundingClientRect().height } : null,
    };
  });
  evidence.viewports.push({ key: vp.key, width: vp.width, ...geometry });
  const shot = path.join(path.dirname(output), `viewport-${vp.key}.png`);
  await page.screenshot({ path: shot, fullPage: true });
}

evidence.passed = (
  evidence.console.length === 0
  && evidence.pageerror.length === 0
  && evidence.http.length === 0
  && evidence.viewports.every((vp) => !vp.horizontalOverflow && vp.bandRect && vp.bandRect.width > 0)
);
fs.writeFileSync(output, JSON.stringify(evidence, null, 2) + '\n');
await browser.close();

if (!evidence.passed) {
  console.error('[contract-form-presentation] FAIL', JSON.stringify({ console: evidence.console.length, pageerror: evidence.pageerror.length, http: evidence.http.length, viewports: evidence.viewports.map((v) => v.key) }));
  process.exit(1);
}
console.log(`[contract-form-presentation] PASS route=${target.route} viewports=${evidence.viewports.length} overflow=0 errors=0`);

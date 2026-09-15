#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const EXPECTED_DB = 'sc_dev_demo';
const EXPECTED_URL = 'http://127.0.0.1:5176';
const NAMESPACE = 'codex_p4_tender_award';
const batch = String(process.env.P4_TENDER_AWARD_BATCH || '').trim();
const productSha = String(process.env.PRODUCT_CANDIDATE_SHA || '').trim();
const toolSha = String(process.env.P4_TOOL_CANDIDATE_SHA || '').trim();
const frontendUrl = String(process.env.FRONTEND_URL || EXPECTED_URL).replace(/\/$/, '');
const database = String(process.env.DB_NAME || '');
const password = String(process.env.SC_DEMO_USER_PASSWORD || '');
const outputDir = path.resolve(process.env.ARTIFACT_DIR || `artifacts/p4-tender-award/${Date.now()}`);

function deny(message) { throw new Error(`[DENY] ${message}`); }
function fullSha(value, label) {
  if (!/^[0-9a-f]{40}$/.test(value)) deny(`${label} must be a full SHA`);
}
function normalize(value) { return String(value ?? '').replace(/\s+/g, ' ').trim(); }
function check(condition, message, facts = undefined) {
  if (!condition) throw new Error(`${message}${facts ? `: ${JSON.stringify(facts)}` : ''}`);
}

if (!/^[a-z0-9][a-z0-9-]{2,31}$/.test(batch)) deny('P4_TENDER_AWARD_BATCH is invalid');
fullSha(productSha, 'PRODUCT_CANDIDATE_SHA');
fullSha(toolSha, 'P4_TOOL_CANDIDATE_SHA');
if (database !== EXPECTED_DB) deny(`DB_NAME must be ${EXPECTED_DB}`);
if (String(process.env.SC_ENVIRONMENT || '') !== 'dev') deny('SC_ENVIRONMENT must be dev');
if (String(process.env.ODOO_DBFILTER || '') !== '^sc_dev_demo$') deny('ODOO_DBFILTER must be exact');
if (frontendUrl !== EXPECTED_URL) deny(`FRONTEND_URL must be ${EXPECTED_URL}`);
if (!password) deny('SC_DEMO_USER_PASSWORD is required');

const actualTool = spawnSync('git', ['-C', ROOT, 'rev-parse', 'HEAD'], { encoding: 'utf8' });
if (actualTool.status !== 0 || normalize(actualTool.stdout) !== toolSha) deny('tool SHA does not match worktree HEAD');
let pid = {};
try { pid = JSON.parse(fs.readFileSync('/tmp/sc-local-dev-candidate-frontend.pid', 'utf8')); }
catch { deny('candidate frontend pidfile is missing or invalid'); }
if (String(pid.head || '') !== productSha || path.resolve(String(pid.root || '')) !== ROOT) {
  deny('served product candidate identity mismatch');
}

function authorityRead() {
  const result = spawnSync('bash', [path.join(ROOT, 'scripts/verify/local_dev_tender_award_fixture.sh')], {
    cwd: ROOT,
    encoding: 'utf8',
    maxBuffer: 4 * 1024 * 1024,
    env: {
      ...process.env,
      P4_TENDER_AWARD_MODE: 'inspect',
      P4_TENDER_AWARD_CONFIRM: 'INSPECT',
      CANDIDATE_GIT_HEAD: toolSha,
    },
  });
  if (result.status !== 0) deny(`fixture authority inspect failed: ${normalize(result.stderr).slice(0, 600)}`);
  const prefix = 'LOCAL_DEV_TENDER_AWARD_FIXTURE_JSON=';
  const rows = String(result.stdout || '').split(/\r?\n/).filter((line) => line.startsWith(prefix));
  if (rows.length !== 1) deny('fixture authority did not return exactly one result');
  return JSON.parse(rows[0].slice(prefix.length));
}

const authority = authorityRead();
check(authority.existing_batch === true, 'fixture batch must exist before browser journey');
check(authority.namespace === NAMESPACE && authority.batch === batch, 'fixture namespace/batch mismatch');
check(authority.candidate_sha === toolSha, 'fixture authority tool SHA mismatch');
check(authority.fixture?.writer_read_allowed && authority.fixture?.writer_write_allowed, 'fixture writer lacks authority');
check(authority.fixture?.state === 'waiting', 'fixture must start in waiting state', authority.fixture);
check(Number(authority.fixture?.bid_amount) === 1200, 'fixture quote mismatch');
check(Number(authority.fixture?.line_total) === 1000, 'fixture BOQ total mismatch');
check(Number(authority.fixture?.opening_amount) === 900, 'fixture opening amount mismatch');

const require = createRequire(path.join(ROOT, 'frontend/apps/web/package.json'));
const { chromium } = require('playwright');
fs.mkdirSync(outputDir, { recursive: true });
const report = {
  pass: false,
  batch,
  database,
  product_candidate_sha: productSha,
  tool_candidate_sha: toolSha,
  formal_entry: authority.formal_entry,
  fixture_before: authority.fixture,
  mutations: [],
  errors: [],
  output_dir: outputDir,
};

async function token(page) {
  return page.evaluate((db) => sessionStorage.getItem(`sc_auth_token:${db}`) || '', database);
}
async function intent(page, name, params, allowError = false) {
  const bearer = await token(page);
  return page.evaluate(async ({ database, bearer, name, params, allowError }) => {
    const response = await fetch(`/api/v1/intent?db=${encodeURIComponent(database)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: bearer ? `Bearer ${bearer}` : '' },
      body: JSON.stringify({ intent: name, params }),
    });
    const body = await response.json().catch(() => ({}));
    if (!allowError && (!response.ok || body?.ok === false)) throw new Error(JSON.stringify(body?.error || body));
    return { status: response.status, body };
  }, { database, bearer, name, params, allowError });
}
async function login(page) {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(authority.writer.login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).isEnabled().catch(() => false)) await inputs.nth(2).fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30_000 });
}
async function waitForForm(page) {
  const surface = page.locator(
    `[data-form-model="tender.bid"][data-form-record="${authority.fixture.bid_id}"]`,
  ).first();
  await surface.waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => !/正在加载页面|正在加载表单/.test(document.body.innerText || ''), null, { timeout: 30_000 });
  return surface;
}
async function chooseRelation(page, fieldName, rowText) {
  const root = page.locator(`[data-field-name="${fieldName}"]:visible`).first();
  await root.scrollIntoViewIfNeeded();
  const input = root.locator('input:visible').first();
  await input.click();
  await page.waitForTimeout(300);
  const inline = page.getByRole('option').filter({ hasText: rowText }).first();
  if (await inline.count() && await inline.isVisible().catch(() => false)) {
    await inline.click();
    return 'inline';
  }
  const searchMore = root.getByRole('button', { name: /搜索更多/ }).first();
  await searchMore.waitFor({ state: 'visible', timeout: 10_000 });
  await searchMore.click();
  const dialog = page.locator('.relation-dialog:visible').first();
  await dialog.waitFor({ state: 'visible', timeout: 10_000 });
  const row = dialog.locator('tbody tr:visible, .relation-dialog-result-card:visible').filter({ hasText: rowText }).first();
  await row.waitFor({ state: 'visible', timeout: 10_000 });
  await row.click();
  await dialog.getByRole('button', { name: /^选择$/ }).click();
  await dialog.waitFor({ state: 'hidden', timeout: 10_000 });
  return 'search-more';
}
async function chooseSelection(page, fieldName, label) {
  const root = page.locator(`[data-field-name="${fieldName}"]:visible`).first();
  await root.scrollIntoViewIfNeeded();
  await root.locator('input:visible').first().click();
  const option = page.getByRole('option', { name: label, exact: true }).last();
  await option.waitFor({ state: 'visible', timeout: 10_000 });
  await option.click();
}
async function saveDraft(page) {
  const response = page.waitForResponse((candidate) => {
    if (!candidate.url().includes('/api/v1/intent')) return false;
    try {
      const body = candidate.request().postDataJSON();
      return body?.intent === 'api.data' && body?.params?.op === 'write'
        && body?.params?.model === 'tender.bid'
        && (body?.params?.ids || []).map(Number).includes(Number(authority.fixture.bid_id));
    } catch { return false; }
  }, { timeout: 30_000 });
  await page.getByRole('button', { name: /^保存(?:修改)?$/ }).first().click();
  const result = await response;
  const body = await result.json().catch(() => ({}));
  check(result.status() === 200 && body?.ok === true, 'award inputs save failed', body);
  report.mutations.push({ intent: 'api.data.write', status: result.status(), fields: ['award_opening_id', 'award_source_kind', 'award_source_reference', 'award_tax_basis'] });
  await page.waitForTimeout(500);
}
async function executeFromPage(page) {
  let button = page.locator('[data-action-method="action_mark_won"]:visible').first();
  if (!(await button.count())) {
    const more = page.getByRole('button', { name: /更多操作/ }).first();
    await more.click();
    button = page.locator('[data-action-method="action_mark_won"]:visible').first();
  }
  await button.waitFor({ state: 'visible', timeout: 10_000 });
  const response = page.waitForResponse((candidate) => {
    if (!candidate.url().includes('/api/v1/intent')) return false;
    try {
      const body = candidate.request().postDataJSON();
      return body?.intent === 'execute_button' && body?.params?.button?.name === 'action_mark_won';
    } catch { return false; }
  }, { timeout: 30_000 });
  await button.click();
  const dialog = page.locator('[role="dialog"]:visible').first();
  if (await dialog.count() && await dialog.isVisible().catch(() => false)) {
    const confirm = dialog.getByRole('button', { name: /确认中标事实|确认/ }).last();
    if (await confirm.count()) await confirm.click();
  }
  const result = await response;
  const body = await result.json().catch(() => ({}));
  check(result.status() === 200 && body?.ok === true, 'award confirmation failed', body);
  report.mutations.push({ intent: 'execute_button', method: 'action_mark_won', status: result.status() });
}
async function readBid(page) {
  const response = await intent(page, 'api.data', {
    op: 'read',
    model: 'tender.bid',
    ids: [authority.fixture.bid_id],
    fields: [
      'id', 'state', 'bid_amount', 'amount_total', 'award_opening_id',
      'award_amount', 'award_currency_id', 'award_tax_basis', 'award_source_kind',
      'award_source_reference', 'award_confirmed_by_id', 'award_confirmed_at',
      'award_confirmation_state', 'award_contract_handoff_message', 'contract_id',
    ],
    context: {},
  });
  return response.body?.data?.records?.[0] || {};
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1088, height: 791 }, locale: 'zh-CN' });
page.on('console', (message) => { if (message.type() === 'error' && !message.text().includes('favicon')) report.errors.push(message.text()); });
page.on('pageerror', (error) => report.errors.push(String(error.message || error)));

try {
  await login(page);
  const entry = authority.formal_entry;
  const route = `${frontendUrl}/f/tender.bid/${authority.fixture.bid_id}?menu_id=${entry.menu_id}&action_id=${entry.action_id}`;
  await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForForm(page);
  check(new URL(page.url()).searchParams.get('menu_id') === String(entry.menu_id), 'formal menu identity was lost');
  check(new URL(page.url()).searchParams.get('action_id') === String(entry.action_id), 'formal action identity was lost');
  report.opening_selection_path = await chooseRelation(page, 'award_opening_id', /900|受管中标/);
  await chooseSelection(page, 'award_source_kind', '最终报价资料');
  await page.locator('[data-field-name="award_source_reference"] input:visible').first().fill(authority.expected.source_reference);
  await chooseSelection(page, 'award_tax_basis', '未知');
  await page.screenshot({ path: path.join(outputDir, 'before-confirmation.png'), fullPage: true });
  await saveDraft(page);
  const prepared = await readBid(page);
  check(Number(Array.isArray(prepared.award_opening_id) ? prepared.award_opening_id[0] : prepared.award_opening_id) === Number(authority.fixture.opening_id), 'saved opening selection mismatch', prepared);
  check(prepared.award_source_kind === 'final_quote' && prepared.award_tax_basis === 'unknown', 'saved source/tax facts mismatch', prepared);
  check(prepared.award_source_reference === authority.expected.source_reference, 'saved source reference mismatch', prepared);

  await executeFromPage(page);
  const confirmed = await readBid(page);
  check(confirmed.state === 'won', 'award state was not confirmed', confirmed);
  check(Number(confirmed.bid_amount) === 1200 && Number(confirmed.amount_total) === 1000 && Number(confirmed.award_amount) === 900, '1200/1000/900 facts mismatch', confirmed);
  check(Boolean(confirmed.award_confirmed_by_id) && Boolean(confirmed.award_confirmed_at), 'confirmer/time missing', confirmed);
  check(!confirmed.contract_id, 'contract was created unexpectedly', confirmed);
  report.authoritative_after_confirm = confirmed;

  const repeat = await intent(page, 'execute_button', {
    model: 'tender.bid',
    res_id: authority.fixture.bid_id,
    button: { name: 'action_mark_won', type: 'object' },
  });
  report.mutations.push({ intent: 'execute_button', method: 'action_mark_won', repeat: true, status: repeat.status });
  const repeated = await readBid(page);
  check(repeated.award_confirmed_at === confirmed.award_confirmed_at, 'repeat request changed confirmation time', { confirmed, repeated });
  check(Number(repeated.award_amount) === 900 && !repeated.contract_id, 'repeat request changed snapshot or created contract', repeated);
  report.authoritative_after_repeat = repeated;

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForForm(page);
  const readonly = await page.evaluate(() => {
    const text = (value) => String(value ?? '').replace(/\s+/g, ' ').trim();
    return {
      state: text(document.querySelector('[data-field-name="award_confirmation_state"]')?.textContent),
      amount: text(document.querySelector('[data-field-name="award_amount"]')?.textContent),
      confirmer: text(document.querySelector('[data-field-name="award_confirmed_by_id"]')?.textContent),
      confirmedAt: text(document.querySelector('[data-field-name="award_confirmed_at"]')?.textContent),
      editableInputs: ['award_opening_id', 'award_source_kind', 'award_source_reference', 'award_tax_basis']
        .flatMap((name) => [...document.querySelectorAll(`[data-field-name="${name}"] input:not([disabled]), [data-field-name="${name}"] textarea:not([disabled])`)])
        .filter((node) => node.offsetParent !== null).length,
      actionCount: document.querySelectorAll('[data-action-method="action_mark_won"]:not([disabled])').length,
    };
  });
  check(readonly.state.includes('已确认'), 'refreshed confirmation state is not readonly/confirmed', readonly);
  check(readonly.amount.includes('900'), 'refreshed award amount missing', readonly);
  check(readonly.confirmer && readonly.confirmedAt, 'refreshed confirmer/time missing', readonly);
  check(readonly.editableInputs === 0, 'confirmed award inputs remain editable', readonly);
  check(readonly.actionCount === 0, 'confirmation action remains executable after confirmation', readonly);
  report.refreshed_readonly = readonly;
  await page.screenshot({ path: path.join(outputDir, 'after-confirmation-refresh.png'), fullPage: true });
  report.pass = report.errors.length === 0;
} catch (error) {
  report.error = error instanceof Error ? error.stack || error.message : String(error);
} finally {
  await browser.close().catch(() => {});
  fs.writeFileSync(path.join(outputDir, 'summary.json'), JSON.stringify(report, null, 2));
}

console.log(`LOCAL_DEV_TENDER_AWARD_BROWSER_JSON=${JSON.stringify({ pass: report.pass, output_dir: outputDir, mutations: report.mutations.length, error: report.error || null })}`);
if (!report.pass) process.exit(1);

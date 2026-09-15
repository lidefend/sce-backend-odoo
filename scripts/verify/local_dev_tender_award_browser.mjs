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
function collectAwardOpeningDescriptors(value, pathName = '$', out = []) {
  if (!value || typeof value !== 'object') return out;
  if (!Array.isArray(value)) {
    const name = String(value.name || value.field || value.field_name || '').trim();
    if (name === 'award_opening_id') {
      out.push({
        path: pathName,
        name,
        type: value.type || value.ttype,
        domain: value.domain,
        modifiers: value.modifiers,
        relation_entry: value.relation_entry,
      });
    }
  }
  for (const [key, child] of Object.entries(value)) {
    if (child && typeof child === 'object') {
      collectAwardOpeningDescriptors(child, `${pathName}.${key}`, out);
    }
  }
  return out;
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
  selection_chain: [],
  relation_requests: [],
  contract_requests: [],
  award_opening_descriptors: [],
  expected_errors: [],
  errors: [],
  output_dir: outputDir,
};

async function token(page) {
  return page.evaluate((db) => sessionStorage.getItem(`sc_auth_token:${db}`) || '', database);
}
async function postIntent(page, requestBody, allowError = false) {
  const bearer = await token(page);
  return page.evaluate(async ({ database, bearer, requestBody, allowError }) => {
    const response = await fetch(`/api/v1/intent?db=${encodeURIComponent(database)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: bearer ? `Bearer ${bearer}` : '' },
      body: JSON.stringify(requestBody),
    });
    const body = await response.json().catch(() => ({}));
    if (!allowError && (!response.ok || body?.ok === false)) throw new Error(JSON.stringify(body?.error || body));
    return { status: response.status, body };
  }, { database, bearer, requestBody, allowError });
}
async function intent(page, name, params, allowError = false) {
  return postIntent(page, { intent: name, params }, allowError);
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
  await page.waitForFunction(
    () => !/加载中/.test(document.title) && !/正在加载页面|正在加载表单/.test(document.body.innerText || ''),
    null,
    { timeout: 45_000 },
  );
  const surface = page.locator(
    `[data-form-model="tender.bid"][data-form-record="${authority.fixture.bid_id}"]`,
  ).first();
  await surface.waitFor({ state: 'visible', timeout: 45_000 });
  return surface;
}
function waitForCurrentRecordContract(page) {
  return page.waitForResponse((candidate) => {
    if (!candidate.url().includes('/api/v1/intent')) return false;
    try {
      const body = candidate.request().postDataJSON();
      return body?.intent === 'ui.contract.v2'
        && body?.params?.op === 'action_open'
        && Number(body?.params?.record_id) === Number(authority.fixture.bid_id);
    } catch { return false; }
  }, { timeout: 45_000 });
}
async function chooseRelation(page, fieldName, expectedId) {
  const root = page.locator(`[data-field-name="${fieldName}"]:visible`).first();
  await root.scrollIntoViewIfNeeded();
  await root.locator('input:visible').first().click();
  const searchMore = root.getByRole('button', { name: /搜索更多/ }).first();
  await searchMore.waitFor({ state: 'visible', timeout: 10_000 });
  await searchMore.click();
  const dialog = page.locator('.relation-dialog:visible').first();
  const row = dialog.locator(`[data-record-id="${expectedId}"]:visible`);
  await row.waitFor({ state: 'visible', timeout: 10_000 });
  check(await row.count() === 1, 'opening option identity is ambiguous');
  await row.click();
  check(await row.getAttribute('aria-selected') === 'true', 'opening option is not selected');
  report.selection_chain.push({ stage: 'option_selected', at: new Date().toISOString(), id: expectedId, selected: true });
  await dialog.getByRole('button', { name: /^选择$/ }).click();
  await dialog.waitFor({ state: 'hidden', timeout: 10_000 });
  return 'search-more-exact-id';
}
async function openingValueEvidence(page, stage) {
  const display = await page.locator('[data-field-name="award_opening_id"] input:visible').first().inputValue();
  const draft = report.selection_chain.filter((row) => row.stage === 'onchange_draft').at(-1);
  const evidence = { stage, at: new Date().toISOString(), display, draftId: draft?.openingId };
  report.selection_chain.push(evidence);
  check(display.trim() && Number(evidence.draftId) === Number(authority.fixture.opening_id), 'opening ID not bound in control/draft; confirmation forbidden', evidence);
}
async function chooseSelection(page, fieldName, label) {
  const root = page.locator(`[data-field-name="${fieldName}"]:visible`).first();
  await root.scrollIntoViewIfNeeded();
  await root.locator('input:visible').first().click();
  const semanticOption = page.getByRole('option', { name: label, exact: true }).last();
  const option = await semanticOption.count()
    ? semanticOption
    : page.getByText(label, { exact: true }).last();
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
  report.mutations.push({ intent: 'api.data.write', status: result.status(), vals: result.request().postDataJSON().params.vals, traceId: result.headers()['x-trace-id'] || body.meta?.trace_id });
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
  const requestBody = result.request().postDataJSON();
  check(requestBody?.intent === 'execute_button' && requestBody?.meta?.menu_id && requestBody?.meta?.action_id, 'confirmed action request authority is missing', requestBody);
  return requestBody;
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
const contractResponseCaptures = [];
await page.route('**/api/v1/intent?**', async (route) => {
  let body; try { body = route.request().postDataJSON(); } catch { return route.continue(); }
  if (body?.intent === 'api.data' && body.params?.op === 'write' && body.params?.model === 'tender.bid') {
    const valid = Number.isSafeInteger(body.params.vals?.award_opening_id)
      && body.params.vals.award_opening_id === authority.fixture.opening_id
      && Array.isArray(body.params.ids) && body.params.ids.length === 1
      && Number.isSafeInteger(body.params.ids[0]) && body.params.ids[0] === authority.fixture.bid_id;
    report.selection_chain.push({ stage: 'submit_parameters', at: new Date().toISOString(), ids: body.params.ids, vals: body.params.vals, forwarded: valid });
    if (!valid) { report.errors.push('opening submit ID mismatch; write blocked'); return route.abort('blockedbyclient'); }
  }
  await route.continue();
});
page.on('request', (request) => {
  if (!request.url().includes('/api/v1/intent')) return;
  try {
    const body = request.postDataJSON();
    if (body?.intent === 'api.data' && body?.params?.model === 'tender.opening') {
      report.relation_requests.push({
        op: body.params.op,
        domain: body.params.domain,
        context: body.params.context,
        search_term: body.params.search_term,
      });
    }
    if (body?.intent === 'ui.contract.v2') report.contract_requests.push(body.params);
    if (body?.intent === 'api.onchange' && body.params?.model === 'tender.bid') {
      report.selection_chain.push({ stage: 'onchange_draft', at: new Date().toISOString(), changedFields: body.params.changed_fields, openingId: body.params.values?.award_opening_id });
    }
  } catch { /* failure evidence must not change the journey */ }
});
page.on('response', (response) => {
  if (!response.url().includes('/api/v1/intent')) return;
  let requestBody;
  try { requestBody = response.request().postDataJSON(); } catch { return; }
  if (requestBody?.intent === 'api.onchange' && requestBody.params?.model === 'tender.bid') {
    contractResponseCaptures.push(response.json().then((body) => report.selection_chain.push({ stage: 'onchange_result', at: new Date().toISOString(), patch: body.data?.patch, traceId: response.headers()['x-trace-id'] || body.meta?.trace_id })));
  }
  if (requestBody?.intent !== 'ui.contract.v2') return;
  const capture = response.json().then((body) => {
    report.award_opening_descriptors.push(...collectAwardOpeningDescriptors(body));
  }).catch(() => {});
  contractResponseCaptures.push(capture);
});
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
  const openingRead = await intent(page, 'api.data', { op: 'read', model: 'tender.opening', ids: [authority.fixture.opening_id], fields: ['id', 'bid_id', 'result'], context: { company_id: authority.writer.company_id } });
  const opening = openingRead.body?.data?.records?.[0];
  check(Number(opening?.id) === Number(authority.fixture.opening_id) && Number(opening?.bid_id?.[0]) === Number(authority.fixture.bid_id) && opening?.result === 'won', 'opening eligibility/ownership mismatch', opening);
  report.option_eligibility = { ...opening, companyId: authority.writer.company_id, status: openingRead.status, traceId: openingRead.body?.meta?.trace_id };
  const selectedDraftResponse = page.waitForResponse((response) => {
    try { const b = response.request().postDataJSON(); return b?.intent === 'api.onchange' && b.params?.model === 'tender.bid' && Number(b.params?.values?.award_opening_id) === Number(authority.fixture.opening_id); } catch { return false; }
  }, { timeout: 15_000 });
  report.opening_selection_path = await chooseRelation(page, 'award_opening_id', Number(authority.fixture.opening_id));
  await selectedDraftResponse;
  await openingValueEvidence(page, 'control_and_draft_after_selection');
  await chooseSelection(page, 'award_source_kind', '最终报价资料');
  await page.locator('[data-field-name="award_source_reference"] input:visible').first().fill(authority.expected.source_reference);
  await chooseSelection(page, 'award_tax_basis', '未知');
  await page.screenshot({ path: path.join(outputDir, 'before-confirmation.png'), fullPage: true });
  await page.waitForTimeout(600); // Allow the existing debounced onchange to settle after focus leaves the relation.
  await openingValueEvidence(page, 'control_and_draft_before_save');
  await saveDraft(page);
  const prepared = await readBid(page);
  check(Number(Array.isArray(prepared.award_opening_id) ? prepared.award_opening_id[0] : prepared.award_opening_id) === Number(authority.fixture.opening_id), 'saved opening selection mismatch', prepared);
  check(prepared.award_source_kind === 'final_quote' && prepared.award_tax_basis === 'unknown', 'saved source/tax facts mismatch', prepared);
  check(prepared.award_source_reference === authority.expected.source_reference, 'saved source reference mismatch', prepared);

  report.authoritative_before_confirm = prepared;
  const repeatRequest = await executeFromPage(page);
  const confirmed = await readBid(page);
  check(confirmed.state === 'won', 'award state was not confirmed', confirmed);
  check(Number(confirmed.bid_amount) === 1200 && Number(confirmed.amount_total) === 1000 && Number(confirmed.award_amount) === 900, '1200/1000/900 facts mismatch', confirmed);
  check(Boolean(confirmed.award_confirmed_by_id) && Boolean(confirmed.award_confirmed_at), 'confirmer/time missing', confirmed);
  check(!confirmed.contract_id, 'contract was created unexpectedly', confirmed);
  report.authoritative_after_confirm = confirmed;

  const repeat = await postIntent(page, repeatRequest, true);
  const repeatDenied = repeat.body?.error?.code === 'PERMISSION_DENIED'
    && repeat.body?.error?.message === 'ACTION_CONTRACT_NOT_AUTHORIZED';
  check(
    (repeat.status === 200 && repeat.body?.ok === true) || repeatDenied,
    'repeat request was neither idempotent nor rejected by the updated action contract',
    repeat,
  );
  report.mutations.push({
    intent: 'execute_button',
    method: 'action_mark_won',
    repeat: true,
    status: repeat.status,
    outcome: repeatDenied ? 'rejected_by_action_contract' : 'idempotent_success',
  });
  if (repeatDenied) {
    const consoleError = 'Failed to load resource: the server responded with a status of 403 (Forbidden)';
    const consoleErrorIndex = report.errors.indexOf(consoleError);
    check(consoleErrorIndex >= 0, 'contract-rejected repeat did not produce the expected browser response evidence', report.errors);
    report.expected_errors.push({
      intent: 'execute_button',
      method: 'action_mark_won',
      status: repeat.status,
      console: report.errors.splice(consoleErrorIndex, 1)[0],
    });
  }
  const repeated = await readBid(page);
  check(repeated.award_confirmed_at === confirmed.award_confirmed_at, 'repeat request changed confirmation time', { confirmed, repeated });
  check(Number(repeated.award_amount) === 900 && !repeated.contract_id, 'repeat request changed snapshot or created contract', repeated);
  report.authoritative_after_repeat = repeated;

  const refreshedContractPromise = waitForCurrentRecordContract(page);
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45_000 });
  const refreshedContractResponse = await refreshedContractPromise;
  const refreshedContractBody = await refreshedContractResponse.json().catch(() => ({}));
  check(
    refreshedContractResponse.status() === 200 && refreshedContractBody?.ok === true,
    'refreshed contract request failed',
    refreshedContractBody,
  );
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
  await Promise.allSettled(contractResponseCaptures);
  report.error = error instanceof Error ? error.stack || error.message : String(error);
  report.failure_page = {
    url: page.url(),
    title: await page.title().catch(() => ''),
    body_text: await page.locator('body').innerText().then((value) => value.replace(/\s+/g, ' ').trim().slice(0, 2000)).catch(() => ''),
  };
  await page.screenshot({ path: path.join(outputDir, 'failure.png'), fullPage: true }).catch(() => {});
} finally {
  await Promise.allSettled(contractResponseCaptures);
  await browser.close().catch(() => {});
  fs.writeFileSync(path.join(outputDir, 'summary.json'), JSON.stringify(report, null, 2));
}

console.log(`LOCAL_DEV_TENDER_AWARD_BROWSER_JSON=${JSON.stringify({ pass: report.pass, output_dir: outputDir, mutations: report.mutations.length, error: report.error || null })}`);
if (!report.pass) process.exit(1);

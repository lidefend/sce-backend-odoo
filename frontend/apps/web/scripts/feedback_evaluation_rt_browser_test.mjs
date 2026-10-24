import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const CANDIDATE = process.env.FEEDBACK_RT_CASE === 'company_project_refund';
const RUN = String(process.env.FEEDBACK_RT_RUN || 'FE-GATE-03B1-R6-3-RT');
const EVIDENCE = path.join(ROOT, '.runtime/agent-runs', RUN, 'http-evidence.json');
const OUTPUT = path.join(ROOT, '.runtime/agent-runs', RUN, 'frontend-evidence.json');
const BUNDLE = path.join(ROOT, '.runtime/agent-runs', RUN, 'feedback-evaluation-rt-harness.js');
const FRONTEND_URL = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18081/t/demo').replace(/\/+$/, '');
const LOGIN = String(process.env.E2E_LOGIN || 'wutao');
const PASSWORD = String(process.env.E2E_PASSWORD || '');
const FULL_ADVICE = CANDIDATE
  ? '建议选择退款方/收款方，便于责任与资金台账归集；建议补充办理日期；建议补充退款原因或办理说明'
  : '建议补充办理日期；建议补充办理说明';
const SELECTED_PARTNER_ADVICE = '建议补充办理日期；建议补充退款原因或办理说明';
const INITIAL_DATA = CANDIDATE
  ? { partner_id: false, business_date: false, note: '' }
  : { business_date: false, note: '' };
const FILLED_DATA = CANDIDATE
  ? { partner_id: [731, 'Sensitive Partner'], business_date: '2026-10-23', note: '已填写' }
  : { business_date: '2026-10-23', note: '已填写' };
const START_OPTIONS = CANDIDATE ? {
  sourceField: 'processing_advisory',
  sourceType: 'char',
  conditionField: 'processing_advisory',
  initialData: INITIAL_DATA,
  presence: ['partner_id', 'business_date', 'note'],
  advice: FULL_ADVICE,
} : {};
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

if (!PASSWORD) throw new Error('E2E_PASSWORD is required');
if (!fs.existsSync(EVIDENCE)) throw new Error(`HTTP evidence is missing: ${EVIDENCE}`);
if (!fs.existsSync(BUNDLE)) throw new Error(`browser harness bundle is missing: ${BUNDLE}`);
const httpEvidence = JSON.parse(fs.readFileSync(EVIDENCE, 'utf8')).evidence;
const candidateSha = execFileSync('git', ['-C', ROOT, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
const bundleSha256 = createHash('sha256').update(fs.readFileSync(BUNDLE)).digest('hex');
const binding = httpEvidence.cases.find((row) => row.case === 'describe')?.binding;
assert.ok(binding?.etag, 'real HTTP describe binding is missing');

const observations = [];
const consoleErrors = [];
const pageErrors = [];
let evaluationCount = 0;
let descriptionCount = 0;
let holdEvaluation = false;
const held = [];
const feedbackRequests = [];

function feedbackResponse(request) {
  const values = Object.fromEntries((request.inputs || []).map((row) => [row.field, row.value]));
  if (CANDIDATE) {
    const parts = [];
    if (values.partner_id !== true) parts.push('建议选择退款方/收款方，便于责任与资金台账归集');
    if (values.business_date === false) parts.push('建议补充办理日期');
    if (values.note === false || values.note === '') parts.push('建议补充退款原因或办理说明');
    return {
      version: '1.0.0',
      request_id: request.request_id,
      status: 'ready',
      binding_etag: request.binding_etag,
      container_id: request.container_id,
      result: { content: parts.join('；'), visible: Boolean(parts.length) },
    };
  }
  const visible = values.business_date === false && (values.note === false || values.note === '');
  return {
    version: '1.0.0',
    request_id: request.request_id,
    status: 'ready',
    binding_etag: request.binding_etag,
    container_id: request.container_id,
    result: { content: visible ? FULL_ADVICE : '', visible },
  };
}

function envelope(data) {
  return {
    ok: true,
    data: {
      schema_version: 'v1',
      patch: {},
      modifiers_patch: {},
      line_patches: [],
      warnings: [],
      applied_fields: [],
      feedback_evaluation: data,
    },
    meta: { intent: 'api.onchange', contract_version: '1.1.0' },
  };
}

function failureEnvelope(request, reasonCode, pathValue, status) {
  return {
    status,
    body: {
      ok: false,
      code: status,
      error: {
        code: status,
        reason_code: reasonCode,
        message: 'feedback evaluation rejected',
        details: {
          feedback_evaluation: {
            version: '1.0.0',
            request_id: request.request_id,
            status: 'failed',
            diagnostic: { code: reasonCode, path: pathValue },
          },
        },
      },
      meta: { intent: 'api.onchange' },
    },
  };
}

async function fulfill(route, status, body) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    headers: { 'X-Trace-Id': 'r6-3-rt-browser' },
    body: JSON.stringify(body),
  });
}

async function installFeedbackRoute(page) {
  await page.route('**/api/v1/intent*', async (route) => {
    const request = route.request();
    let payload = {};
    try { payload = JSON.parse(request.postData() || '{}'); } catch { /* leave empty */ }
    const block = payload?.params?.feedback_evaluation;
    if (payload?.intent !== 'api.onchange' || !block) {
      await route.continue();
      return;
    }
    feedbackRequests.push(block);
    if (block.operation === 'describe') {
      descriptionCount += 1;
      await fulfill(route, 200, envelope({
        version: '1.0.0',
        request_id: block.request_id,
        status: 'described',
        binding,
      }));
      return;
    }
    evaluationCount += 1;
    if (holdEvaluation) {
      held.push({ route, request: block, count: evaluationCount });
      return;
    }
    await fulfill(route, 200, envelope(feedbackResponse(block)));
  });
}

async function waitFor(predicate, timeout = 10000, interval = 50) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const value = await predicate();
    if (value) return value;
    await sleep(interval);
  }
  throw new Error('browser condition timeout');
}

async function pageState(page) {
  return page.evaluate(() => window.__SC_FEEDBACK_RT__.state());
}

async function record(page, name) {
  const state = await pageState(page);
  observations.push({ case: name, ...state });
  return state;
}

async function login(page) {
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(LOGIN);
  await inputs.nth(1).fill(PASSWORD);
  if (await inputs.nth(2).isEnabled().catch(() => false)) await inputs.nth(2).fill('sc_dev_demo');
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => url.pathname !== '/login', { timeout: 30000 });
  await page.waitForFunction(() => Boolean(sessionStorage.getItem('sc_auth_token:sc_dev_demo')
    || Object.keys(sessionStorage).some((key) => key.startsWith('sc_auth_token:'))), null, { timeout: 30000 });
}

const browser = await launchChromium({ headless: true });
const page = await browser.newPage();
page.on('console', (message) => {
  if (message.type() === 'error') consoleErrors.push(message.text());
});
page.on('pageerror', (error) => pageErrors.push(String(error?.message || error)));

try {
  await login(page);
  await installFeedbackRoute(page);
  await page.addScriptTag({ path: BUNDLE });
  await page.evaluate(
    ([value, options]) => window.__SC_FEEDBACK_RT__.start(value, options),
    [binding, START_OPTIONS],
  );
  try {
    await waitFor(async () => Boolean((await pageState(page))?.state?.binding?.etag));
  } catch (error) {
    throw new Error(`${error.message}; state=${JSON.stringify(await pageState(page))} descriptions=${descriptionCount} console=${JSON.stringify(consoleErrors)} page=${JSON.stringify(pageErrors)}`);
  }
  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), INITIAL_DATA);
  await waitFor(async () => {
    const state = await pageState(page);
    return state?.state?.status === 'ready' && state.visible === true && state.content === FULL_ADVICE;
  });
  const initial = await record(page, 'initial_ready_visible');
  assert.equal(initial.visible, true, JSON.stringify(initial));
  assert.equal(initial.content, FULL_ADVICE, JSON.stringify(initial));

  if (CANDIDATE) {
    await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), {
      partner_id: [731, 'Sensitive Partner'],
      business_date: false,
      note: '',
    });
    await waitFor(async () => {
      const state = await pageState(page);
      return state?.state?.status === 'ready' && state.content === SELECTED_PARTNER_ADVICE;
    });
    const partnerSelected = await record(page, 'partner_presence_visible');
    assert.equal(partnerSelected.content, SELECTED_PARTNER_ADVICE);
    await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), INITIAL_DATA);
    await waitFor(async () => (await pageState(page))?.content === FULL_ADVICE);
  }

  const beforeDebounce = evaluationCount;
  await page.evaluate(([filled, initial]) => {
    window.__SC_FEEDBACK_RT__.setDraft(filled);
    window.__SC_FEEDBACK_RT__.setDraft(initial);
  }, [FILLED_DATA, INITIAL_DATA]);
  await sleep(120);
  assert.equal(evaluationCount, beforeDebounce, 'debounce window must not send an intermediate request');
  await sleep(260);
  assert.equal(evaluationCount, beforeDebounce + 1, 'debounce window must collapse edits to one request');
  const collapsed = await record(page, 'debounce_collapsed');
  assert.equal(collapsed.content, FULL_ADVICE);

  holdEvaluation = true;
  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), FILLED_DATA);
  await waitFor(() => Promise.resolve(held.length === 1));
  holdEvaluation = false;
  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), INITIAL_DATA);
  await waitFor(async () => (await pageState(page))?.state?.status === 'ready');
  const oldSuccess = held.shift();
  await fulfill(oldSuccess.route, 200, envelope(feedbackResponse(oldSuccess.request)));
  await sleep(100);
  const afterOldSuccess = await record(page, 'old_success_dropped');
  assert.equal(afterOldSuccess.content, FULL_ADVICE);

  holdEvaluation = true;
  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), FILLED_DATA);
  await waitFor(() => Promise.resolve(held.length === 1));
  holdEvaluation = false;
  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), INITIAL_DATA);
  await waitFor(async () => (await pageState(page))?.state?.status === 'ready');
  const oldFailure = held.shift();
  const failure = failureEnvelope(oldFailure.request, 'FEEDBACK_INPUT_INVALID', 'feedback_evaluation.inputs', 422);
  await fulfill(oldFailure.route, failure.status, failure.body);
  await sleep(100);
  const afterOldFailure = await record(page, 'old_failure_dropped');
  assert.equal(afterOldFailure.content, FULL_ADVICE);

  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), FILLED_DATA);
  await waitFor(async () => {
    const state = await pageState(page);
    return state?.state?.status === 'ready' && state.visible === false;
  });
  const hidden = await record(page, 'visible_to_hidden');
  assert.equal(hidden.content, '');
  assert.equal(hidden.visible, false);
  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), INITIAL_DATA);
  await waitFor(async () => {
    const state = await pageState(page);
    return state?.state?.status === 'ready' && state.visible === true && state.content === FULL_ADVICE;
  });
  const recovered = await record(page, 'hidden_to_visible_recovered');
  assert.equal(recovered.content, FULL_ADVICE);
  assert.equal(recovered.visible, true);

  holdEvaluation = true;
  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), INITIAL_DATA);
  await waitFor(() => Promise.resolve(held.length === 1));
  const recordOld = held.shift();
  holdEvaluation = false;
  await page.evaluate(() => window.__SC_FEEDBACK_RT__.changeRecord(123));
  await waitFor(async () => (await pageState(page))?.state?.status === 'unavailable');
  await fulfill(recordOld.route, 200, envelope(feedbackResponse(recordOld.request)));
  await sleep(100);
  const switched = await record(page, 'record_switch_rejects_old');
  assert.equal(switched.content, '');
  assert.equal(switched.visible, false);

  await page.evaluate(() => window.__SC_FEEDBACK_RT__.changeRecord(null));
  await waitFor(async () => Boolean((await pageState(page))?.state?.binding?.etag));
  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), FILLED_DATA);
  await waitFor(async () => {
    const state = await pageState(page);
    return state?.state?.status === 'ready' && state.visible === false;
  });

  holdEvaluation = true;
  await page.evaluate((value) => window.__SC_FEEDBACK_RT__.setDraft(value), INITIAL_DATA);
  await waitFor(() => Promise.resolve(held.length === 1));
  const saveOld = held.shift();
  holdEvaluation = false;
  await page.evaluate(() => {
    window.__SC_FEEDBACK_RT__.beginSave();
    window.__SC_FEEDBACK_RT__.clearPresence();
    window.__SC_FEEDBACK_RT__.finishSave();
  });
  await sleep(100);
  await fulfill(saveOld.route, 200, envelope(feedbackResponse(saveOld.request)));
  await sleep(100);
  const saved = await record(page, 'save_epoch_rejects_old');
  assert.equal(saved.content, '');
  assert.equal(saved.visible, false);

  assert.deepEqual(pageErrors, [], 'browser page errors are not allowed');
  const relevantConsoleErrors = consoleErrors.filter((message) => !/Failed to load resource/.test(message));
  assert.deepEqual(relevantConsoleErrors, [], 'browser console errors are not allowed');
  if (CANDIDATE) {
    const serialized = JSON.stringify(feedbackRequests);
    assert.ok(!serialized.includes('731'), 'partner id leaked in feedback request');
    assert.ok(!serialized.includes('Sensitive Partner'), 'partner name leaked in feedback request');
  }
  const result = {
    schema_version: 1,
    run: RUN,
    candidate_sha: candidateSha,
    frontend_url: FRONTEND_URL,
    harness_sha256: bundleSha256,
    http_binding_etag: binding.etag,
    case: CANDIDATE ? 'company_project_refund' : 'team_loan_deduction',
    evaluation_count: evaluationCount,
    cases: observations,
    console_errors: relevantConsoleErrors,
    page_errors: pageErrors,
  };
  fs.writeFileSync(OUTPUT, `${JSON.stringify(result, null, 2)}\n`, { mode: 0o600 });
  console.log(`[feedback_evaluation_rt_browser] PASS cases=${observations.length} evidence=${path.relative(ROOT, OUTPUT)}`);
} finally {
  await page.close();
  await browser.close();
}

// P4 user-journey probe: approve one payment request through the user-defined
// finance, project, finance-review and executive chain using My Work.
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from '../verify/playwright_runtime.mjs';
import { matrixLoginUrl } from '../verify/business_entry_matrix_model.mjs';
import { fillLoginCredentials } from '../verify/frontend_authenticated_intent.mjs';

const BASE = String(
  process.env.SC_ACCEPTANCE_FRONTEND_URL || 'http://127.0.0.1:18083/t/clean',
).replace(/\/$/, '');
const PASSWORD = String(process.env.ACCEPTANCE_PASSWORD || '');
const REQUEST_ID = Number(process.env.PAYMENT_REQUEST_ID || 0);
const COMPANY_ID = Number(process.env.SC_ACCEPTANCE_COMPANY_ID || 0);
const TARGET_SHA = String(process.env.SC_ACCEPTANCE_TARGET_SHA || '');
const BUILD_SHA256 = String(process.env.SC_ACCEPTANCE_BUILD_SHA256 || '');
const OUTPUT_DIR = path.resolve(
  process.env.SC_ACCEPTANCE_OUTPUT_DIR
    || '.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/local-clean-finance-approval-journey',
);
const REVIEWER_LOGINS = [
  process.env.FINANCE_CLERK_APPROVER_LOGIN || 'fixture_role_finance_reviewer',
  process.env.PROJECT_MANAGER_LOGIN || 'fixture_role_project_manager',
  process.env.FINANCE_MANAGER_LOGIN || 'fixture_role_finance_manager',
  process.env.EXECUTIVE_APPROVER_LOGIN || 'fixture_role_executive',
];

if (!PASSWORD || REQUEST_ID <= 0 || COMPANY_ID <= 0) {
  throw new Error(
    'ACCEPTANCE_PASSWORD, PAYMENT_REQUEST_ID and SC_ACCEPTANCE_COMPANY_ID are required',
  );
}
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const report = {
  schema: 'local_clean.finance_approval_journey.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  runtime: {
    base: BASE,
    request_id: REQUEST_ID,
    company_id: COMPANY_ID,
    source_revision: TARGET_SHA,
    frontend_build_sha256: BUILD_SHA256,
    reviewer_logins: REVIEWER_LOGINS,
  },
  before: null,
  transitions: [],
  after: null,
  screenshots: [],
  assertions: [],
  console_errors: [],
  failed_requests: [],
};

function check(condition, assertion, facts = {}) {
  report.assertions.push({ assertion, pass: Boolean(condition), ...facts });
  if (!condition) throw new Error(`${assertion}: ${JSON.stringify(facts)}`);
}

function envelopeData(body) {
  return body?.data || body?.result?.data || body?.result || {};
}

function requestOf(response) {
  try {
    return JSON.parse(response.request().postData() || '{}');
  } catch {
    return {};
  }
}

async function shot(page, name) {
  const file = path.join(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  report.screenshots.push({ name, file, url: page.url() });
}

async function api(page, intent, params) {
  const token = await page.evaluate(() => {
    const entryBase = (
      window.location.pathname.match(/^\/(?:t\/[a-z0-9][a-z0-9-]*|platform-admin)/) || ['']
    )[0];
    const audience = entryBase === '/platform-admin'
      ? 'platform-admin'
      : (entryBase ? 'tenant' : 'unscoped');
    return sessionStorage.getItem(`sc_auth_token:${audience}:${entryBase || 'root'}`) || '';
  });
  return page.evaluate(async ({ tokenValue, intentValue, paramsValue }) => {
    const entryBase = (
      window.location.pathname.match(/^\/(?:t\/[a-z0-9][a-z0-9-]*|platform-admin)/) || ['']
    )[0];
    const response = await fetch(`${entryBase}/api/v1/intent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: tokenValue ? `Bearer ${tokenValue}` : '',
        'X-Trace-Id': `clean-payment-approval-${Date.now()}`,
      },
      body: JSON.stringify({ intent: intentValue, params: paramsValue }),
    });
    return { status: response.status, body: await response.json().catch(() => ({})) };
  }, { tokenValue: token, intentValue: intent, paramsValue: params });
}

async function readJourney(page) {
  const paymentResponse = await api(page, 'api.data', {
    op: 'list',
    model: 'payment.request',
    fields: ['id', 'name', 'state', 'validation_status', 'review_ids', 'amount', 'currency_id'],
    domain: [['id', '=', REQUEST_ID]],
    limit: 1,
    context: { allowed_company_ids: [COMPANY_ID] },
  });
  const payment = envelopeData(paymentResponse.body)?.records?.[0] || null;
  check(paymentResponse.status === 200 && payment, 'payment request is readable by the reviewer', {
    request_id: REQUEST_ID,
    status: paymentResponse.status,
    payment,
  });
  const reviewIds = Array.isArray(payment.review_ids) ? payment.review_ids : [];
  const reviewsResponse = await api(page, 'api.data', {
    op: 'list',
    model: 'tier.review',
    fields: ['id', 'name', 'sequence', 'status', 'reviewer_ids', 'done_by'],
    domain: [['id', 'in', reviewIds], ['model', '=', 'payment.request'], ['res_id', '=', REQUEST_ID]],
    order: 'sequence asc, id asc',
    limit: Math.max(reviewIds.length, 1),
    context: { allowed_company_ids: [COMPANY_ID] },
  });
  const reviews = envelopeData(reviewsResponse.body)?.records || [];
  check(reviewsResponse.status === 200 && reviews.length === reviewIds.length,
    'the exact payment approval instance is readable', {
      review_ids: reviewIds,
      status: reviewsResponse.status,
      reviews,
    });
  return { payment, reviews };
}

async function login(page, loginName) {
  await page.goto(matrixLoginUrl(BASE), { waitUntil: 'networkidle' });
  await fillLoginCredentials(page, loginName, PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  const deadline = Date.now() + 45000;
  while (new URL(page.url()).pathname.includes('/login') && Date.now() < deadline) {
    await page.waitForTimeout(250);
  }
  check(!new URL(page.url()).pathname.includes('/login'), `reviewer ${loginName} logs in`, {
    url: page.url(),
  });
  await page.locator('.nav-shell[data-navigation-state="ready"]')
    .waitFor({ state: 'visible', timeout: 45000 });
}

async function approveFromMyWork(page, loginName, requestName, reviewId, stepIndex) {
  await page.goto(`${BASE}/s/my_work.workspace`, { waitUntil: 'networkidle' });
  await page.locator('.product-work').waitFor({ state: 'visible', timeout: 45000 });
  const todo = page.locator('.count-card[data-section-key="todo"]');
  if (await todo.count()) await todo.click();
  const section = page.locator('.work-section[data-section-key="todo"]');
  await section.waitFor({ state: 'visible', timeout: 45000 });
  const card = section.locator('.work-card').filter({ hasText: requestName }).first();
  await card.waitFor({ state: 'visible', timeout: 45000 });
  await shot(page, `step-${stepIndex + 1}-${loginName}-todo`);

  const responsePromise = page.waitForResponse((response) => {
    const request = requestOf(response);
    return request.intent === 'payment.request.execute'
      && Number(request.params?.id || request.params?.res_id || 0) === REQUEST_ID
      && String(request.params?.action || '') === 'approve';
  }, { timeout: 45000 });
  await card.getByRole('button', { name: '审批', exact: true }).click();
  const dialog = page.getByRole('dialog').last();
  await dialog.waitFor({ state: 'visible', timeout: 15000 });
  await dialog.getByRole('button', { name: '确认审批', exact: true }).click();
  const response = await responsePromise;
  const body = await response.json().catch(() => ({}));
  check(response.status() === 200 && body?.ok === true, `step ${stepIndex + 1} approval succeeds`, {
    status: response.status(),
    body,
  });
  await dialog.waitFor({ state: 'hidden', timeout: 45000 });
  const after = await readJourney(page);
  const review = after.reviews.find((row) => Number(row.id) === reviewId);
  check(review?.status === 'approved', `step ${stepIndex + 1} records the reviewer decision`, {
    review,
  });
  report.transitions.push({
    step: stepIndex + 1,
    login: loginName,
    review_id: reviewId,
    state: after.payment.state,
    validation_status: after.payment.validation_status,
    review,
  });
  await shot(page, `step-${stepIndex + 1}-${loginName}-approved`);
}

const browser = await launchChromium({ headless: true });
try {
  const contexts = [];
  const pages = [];
  for (let index = 0; index < REVIEWER_LOGINS.length; index += 1) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 960 },
      locale: 'zh-CN',
    });
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    page.on('pageerror', (error) => report.console_errors.push(`pageerror: ${error.message}`));
    page.on('console', (message) => {
      if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) {
        report.console_errors.push(`console.error: ${message.text()}`.slice(0, 500));
      }
    });
    page.on('response', (response) => {
      if (response.status() < 400) return;
      const request = requestOf(response);
      report.failed_requests.push({
        status: response.status(),
        intent: request.intent || '',
        model: request.params?.model || '',
      });
    });
    contexts.push(context);
    pages.push(page);
  }

  await login(pages[0], REVIEWER_LOGINS[0]);
  report.before = await readJourney(pages[0]);
  const reviews = [...report.before.reviews].sort((left, right) => (
    Number(left.sequence || 0) - Number(right.sequence || 0)
  ));
  check(reviews.length === REVIEWER_LOGINS.length,
    'the request has one review instance per configured approval role', {
      expected: REVIEWER_LOGINS.length,
      reviews,
    });
  check(reviews[0].status === 'pending', 'the first approval step is pending', {
    review: reviews[0],
  });
  check(reviews.slice(1).every((review) => review.status === 'waiting'),
    'later approval steps wait for their sequence', { reviews });

  for (let index = 0; index < REVIEWER_LOGINS.length; index += 1) {
    const loginName = REVIEWER_LOGINS[index];
    const page = pages[index];
    if (index > 0) await login(page, loginName);
    const current = await readJourney(page);
    const review = current.reviews.find((row) => Number(row.id) === Number(reviews[index].id));
    check(review?.status === 'pending', `step ${index + 1} is pending for its reviewer`, {
      review,
    });
    check(Array.isArray(review.reviewer_ids) && review.reviewer_ids.length > 0,
      `step ${index + 1} has at least one assigned reviewer`, { review });
    await approveFromMyWork(page, loginName, current.payment.name, review.id, index);
  }

  await login(pages[0], REVIEWER_LOGINS[0]);
  report.after = await readJourney(pages[0]);
  check(report.after.payment.state === 'approved', 'all approvals move the payment request to approved', {
    payment: report.after.payment,
  });
  check(report.after.payment.validation_status === 'validated',
    'all approvals complete tier validation', { payment: report.after.payment });
  check(report.after.reviews.every((review) => review.status === 'approved'),
    'every configured review records an approved decision', {
      reviews: report.after.reviews,
    });
  check(report.console_errors.length === 0, 'approval journey has no browser errors', {
    errors: report.console_errors,
  });
  check(report.failed_requests.length === 0, 'approval journey has no failed HTTP responses', {
    failed_requests: report.failed_requests,
  });
  report.pass = true;

  for (const context of contexts) await context.close();
} catch (error) {
  report.error = {
    type: error instanceof Error ? error.name : typeof error,
    message: error instanceof Error ? error.message : String(error),
  };
} finally {
  const output = path.join(OUTPUT_DIR, 'receipt.json');
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    pass: report.pass,
    output,
    error: report.error || null,
    request_id: REQUEST_ID,
    transitions: report.transitions,
    before: report.before,
    after: report.after,
    assertions: report.assertions,
    console_errors: report.console_errors,
    failed_requests: report.failed_requests,
  }, null, 2));
  await browser.close();
  if (!report.pass) process.exitCode = 1;
}

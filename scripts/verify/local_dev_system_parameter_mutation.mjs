import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { execFileSync, spawn } from 'node:child_process';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.FRONTEND_BASE_CONFIGURATION_DOMAIN_TARGET || '{}');
const base = process.env.FRONTEND_URL;
const scenario = process.env.SC_PARAMETER_SCENARIO || 'payment_terms';
assert.ok(['payment_terms', 'approval', 'approval_chain', 'recovery'].includes(scenario));
const output = path.resolve(`.runtime/agent-runs/PRODUCT-ITERATION-V2-20261020/parameter-mutation-${scenario}`);
const isApproval = ['approval', 'approval_chain'].includes(scenario);
const key = isApproval ? 'approval_mode' : 'default_payment_terms';
const injectedFailure = 'INJECTED_AFTER_PUBLISH';
assert.equal(target.database, 'sc_dev_demo');
assert.equal(new URL(base).origin, 'http://127.0.0.1:18081');
assert.ok(target.parameter_facts && target.user?.id && process.env.E2E_PASSWORD);
if (scenario === 'approval_chain') {
  assert.match(process.env.SOURCE_SHA || '', /^[a-f0-9]{40}$/);
  assert.equal(process.env.SOURCE_SHA, process.env.CANDIDATE_HEAD);
  assert.match(process.env.CANDIDATE_FINGERPRINT || '', /^[a-f0-9]{64}$/);
}
fs.mkdirSync(output, { recursive: true });
const report = { status: 'failed', head: process.env.CANDIDATE_HEAD, database: target.database,
  principal: target.user.xmlid, scenario, cases: [], recovery: [], errors: [] };
const browser = await launchChromium();
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
let proposed;
let publication;
function params(request) { try { return request.postDataJSON() || {}; } catch { return {}; } }
function find(value, name) {
  if (!value || typeof value !== 'object') return undefined;
  if (Object.hasOwn(value, name)) return value[name];
  for (const child of Object.values(value)) { const hit = find(child, name); if (hit !== undefined) return hit; }
}
function readback(label) {
  const result = JSON.parse(execFileSync('bash', ['scripts/verify/local_dev_system_parameter_browser.sh', '--readback'],
    { encoding: 'utf8', timeout: 60000 }));
  assert.equal(result.database, target.database);
  assert.equal(result.user.id, target.user.id);
  fs.writeFileSync(path.join(output, `${label}.json`), JSON.stringify(result, null, 2));
  return result.parameter_facts;
}
function responseFor(intent) {
  return page.waitForResponse(response => params(response.request()).intent === `sc.product.system_parameter.${intent}`, { timeout: 30000 });
}
page.on('pageerror', error => report.errors.push(error.message));
page.on('request', request => {
  if (params(request).intent === 'sc.product.system_parameter.publish') publication = request;
});
try {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username').fill(target.user.login);
  await page.locator('#login-password').fill(process.env.E2E_PASSWORD);
  const db = page.getByLabel(/数据库/);
  if (await db.count() === 1 && await db.isVisible() && await db.isEnabled()) await db.fill(target.database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 45000 });
  const loaded = responseFor('catalog');
  await page.goto(`${base}/admin/system-parameters`, { waitUntil: 'domcontentloaded' });
  const declaration = find(await (await loaded).json(), 'parameters').find(row => row.key === key);
  assert.equal(declaration.available, true);
  assert.equal(declaration.current_value, target.parameter_facts.values[key]);
  if (isApproval) {
    assert.equal(target.parameter_facts.approval_configuration.policy.length, 1, 'existing policy required for reversible probe');
    assert.ok(target.parameter_facts.approval_configuration.definitions.length > 0, 'existing synchronized definitions required');
    proposed = scenario === 'approval_chain' ? 'single' : (declaration.current_value === 'disabled' ? 'multi' : 'disabled');
    assert.notEqual(proposed, declaration.current_value, 'consumer journey requires a changed mode');
    assert.ok(declaration.allowed_values.includes(proposed));
  } else {
    proposed = declaration.allowed_values.find(value => value !== declaration.current_value && target.parameter_facts.payment_terms[value]);
  }
  assert.ok(proposed, 'a different declared and backed value is required');
  const card = page.locator(`[data-parameter-key="${key}"]`);
  await card.locator('[data-semantic-component="ScSelect"]').click();
  await page.getByText(proposed, { exact: true }).last().click();
  const preview = responseFor('preview');
  await card.getByRole('button', { name: '预览影响', exact: true }).click();
  const previewResponse = await preview;
  assert.equal(params(previewResponse.request()).params.proposed_value, proposed);
  assert.ok(find(await previewResponse.json(), 'impact'));
  // A changed selection invalidates the old preview, even when changed back.
  await card.locator('[data-semantic-component="ScSelect"]').click();
  await page.getByText(declaration.current_value, { exact: true }).last().click();
  assert.equal(await card.getByRole('button', { name: /^发布$/ }).isDisabled(), true);
  await card.locator('[data-semantic-component="ScSelect"]').click();
  await page.getByText(proposed, { exact: true }).last().click();
  assert.equal(await card.getByRole('button', { name: /^发布$/ }).isDisabled(), true);
  const revisedPreview = responseFor('preview');
  await card.getByRole('button', { name: '预览影响', exact: true }).click();
  assert.equal(params((await revisedPreview).request()).params.proposed_value, proposed);
  const published = responseFor('publish');
  await card.getByRole('button', { name: /^发布$/ }).click();
  const result = await (await published).json();
  const change = find(result, 'change');
  assert.equal(change?.state, 'published', JSON.stringify(result));
  assert.equal(change.parameter_key, key);
  assert.equal(change.previous_value, declaration.current_value);
  const active = readback('published');
  assert.equal(active.values[key], proposed);
  if (isApproval) {
    assert.equal(active.approval_required, proposed !== 'disabled');
    if (scenario !== 'approval_chain') assert.notEqual(active.approval_required, target.parameter_facts.approval_required);
    if (scenario === 'approval_chain') {
      assert.ok(active.approval_configuration.definitions.every(row => row.active && !row.approve_sequence));
    }
    if (proposed === 'disabled') assert.ok(active.approval_configuration.definitions.every(row => !row.active));
  } else {
    assert.equal(active.purchase_default, active.payment_terms[proposed]);
  }
  assert.ok(active.changes.some(row => row.id === change.id && row.state === 'published'));
  report.cases.push({ key, publish: 'passed', consumer: isApproval ? 'approval_routing_decision' : 'purchase_default', change_id: change.id });
  if (scenario === 'approval_chain') {
    const log = fs.openSync(path.join(output, 'payment-full-chain.log'), 'w');
    try {
      const status = await new Promise((resolve, reject) => {
        const child = spawn('make', ['--no-print-directory', 'verify.local.dev.payment_request.full_chain'],
          { env: process.env, stdio: ['ignore', log, log] });
        child.on('error', reject);
        child.on('exit', (code, signal) => resolve({ code, signal }));
      });
      assert.equal(status.code, 0, `payment full chain failed: ${JSON.stringify(status)}`);
      const chain = JSON.parse(fs.readFileSync('artifacts/playwright/local-dev-payment-request-full-chain/summary.json', 'utf8'));
      assert.equal(chain.pass, true);
      assert.ok(chain.roles.approval_chain.length > 1, "multiple configured review instances required");
      assert.ok(chain.roles.approval_chain.every(row => row.status === "pending"),
        "single mode must release all configured reviews without sequential waiting");
      assert.equal(chain.source.head_sha, process.env.SOURCE_SHA);
      assert.equal(chain.source.candidate_fingerprint, process.env.CANDIDATE_FINGERPRINT);
      fs.writeFileSync(path.join(output, 'payment-full-chain-report.json'), JSON.stringify(chain, null, 2));
      report.cases[0].consumer = 'payment_request_execution_posted_ledger';
      report.cases[0].payment_request_id = chain.runtime.request_id;
      assert.equal(readback('after-payment-chain').values[key], proposed);
    } finally { fs.closeSync(log); }
  }
  if (scenario === 'recovery') throw new Error(injectedFailure);
  const rolledBack = responseFor('rollback');
  await page.locator('[data-semantic-component="SystemParameterChangeHistory"] [data-change-state="published"]')
    .filter({ hasText: key }).getByRole('button', { name: '回滚', exact: true }).click();
  const rollbackResponse = await rolledBack;
  assert.equal(params(rollbackResponse.request()).params.change_id, change.id);
  assert.equal(find(await rollbackResponse.json(), 'change')?.state, 'rolled_back');
  const restored = readback('restored');
  assert.deepEqual(restored.values, target.parameter_facts.values);
  assert.equal(restored.purchase_default, target.parameter_facts.purchase_default);
  await page.waitForFunction(({ key, expected }) => {
    const card = document.querySelector(`[data-parameter-key="${key}"]`);
    return card && Array.from(card.querySelectorAll('input')).some(input => input.value === expected);
  }, { key, expected: declaration.current_value }, { timeout: 15000 });
  report.cases[0].rollback = 'passed';
  report.cases[0].visible_restored_value = 'passed';
  report.cases[0].edit_invalidates_preview = 'passed';
  assert.deepEqual(report.errors, []);
  report.status = 'passed';
} catch (error) {
  report.failure = error.message;
  if (scenario !== 'recovery' || error.message !== injectedFailure) process.exitCode = 1;
  await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
} finally {
  try {
    const current = readback('recovery-before');
    const baseline = new Set(target.parameter_facts.changes.map(row => row.id));
    const newChanges = current.changes.filter(row => !baseline.has(row.id));
    for (const row of newChanges.filter(row => row.state === 'published').reverse()) {
      assert.ok(publication, 'no authenticated publication request available for recovery');
      assert.equal(row.parameter_key, key);
      assert.equal(row.user_id[0], target.user.id);
      assert.equal(row.proposed_value, proposed);
      const response = await context.request.post(publication.url(), {
        headers: await publication.allHeaders(),
        data: { ...params(publication), intent: 'sc.product.system_parameter.rollback', params: { change_id: row.id } },
      });
      assert.equal(find(await response.json(), 'change')?.state, 'rolled_back');
      report.recovery.push({ change_id: row.id, status: 'rolled_back' });
    }
    const final = readback('recovery-after');
    assert.deepEqual(final.values, target.parameter_facts.values);
    assert.equal(final.purchase_default, target.parameter_facts.purchase_default);
    assert.deepEqual(final.approval_configuration, target.parameter_facts.approval_configuration);
    assert.equal(final.approval_required, target.parameter_facts.approval_required);
    if (scenario === 'recovery') {
      assert.equal(report.failure, injectedFailure);
      assert.equal(report.recovery.length, 1);
      assert.deepEqual(report.errors, []);
      report.status = 'passed';
      report.cases[0].injected_failure_recovery = 'passed';
    }
    report.restoration = 'passed';
  } catch (error) {
    report.restoration = 'failed';
    report.recoveryFailure = error.message;
    report.status = 'failed';
    process.exitCode = 1;
  }
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
  console.log(`[system-parameter.mutation] ${report.status} cases=${report.cases.length} restoration=${report.restoration}${report.failure ? ` reason=${report.failure}` : ''}`);
}

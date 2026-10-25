// P4 daily demo UI adapter. Runtime contracts remain the product authority.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { launchChromium } from './playwright_runtime.mjs';
import { matrixLoginUrl } from './business_entry_matrix_model.mjs';
import { captureReleasedNavigation } from './released_navigation_target.mjs';
import { permitsInventoryRequest } from '../../frontend/apps/web/scripts/bootstrap_inventory_policy.mjs';
import { permitsContractWrite, isExactSignedReadback } from './daily_demo_contract_ui_policy.mjs';

const base = (process.env.ACCEPTANCE_BASE_URL || '').replace(/\/$/, '');
const output = process.env.SC_ACCEPTANCE_OUTPUT_DIR;
const resume = process.env.SC_DEMO_UI_MODE === 'resume';
const finalReadback = process.env.SC_DEMO_UI_MODE === 'final_readback';
const execute = resume || process.env.SC_DEMO_UI_MODE === 'execute';
const key = process.env.SC_DEMO_CONTRACT_KEY;
let recordId = 0;
let checkpoint;
if (resume) {
  checkpoint = JSON.parse(fs.readFileSync(process.env.SC_DEMO_UI_CHECKPOINT, 'utf8'));
  assert.equal(checkpoint.key, key);
  recordId = Number(checkpoint.recordId);
  assert(recordId > 0);
}
if (finalReadback) {
  const signed = JSON.parse(fs.readFileSync(process.env.SC_DEMO_API_SIGN_RECEIPT, 'utf8'));
  assert.equal(signed.status, 'API_SIGN_EXECUTED');
  assert.equal(signed.business_key, key);
  assert.equal(signed.record_id, 6);
  assert.equal(signed.completed_api_actions[0].readback.state, 'signed');
  recordId = signed.record_id;
}
if (execute) {
  assert.equal(process.env.SC_DEMO_WRITE_CONFIRM, 'CREATE_AND_SUBMIT_DEMO_ACCEPTANCE_CONTRACT');
  assert.match(key || '', /^DEMO-DELIVERY-[A-Z0-9-]+$/);
}
assert(base && output && process.env.ACCEPTANCE_TARGET_SHA && process.env.ACCEPTANCE_PASSWORD);
const runtime = await (await fetch(`${base}/api/runtime-version`)).json();
assert.equal(runtime.source_revision || runtime.git_sha, process.env.ACCEPTANCE_TARGET_SHA);
assert.equal(runtime.database, 'sc_demo');
fs.mkdirSync(output, { recursive: true });
if (execute) assert(!fs.existsSync(path.join(output, 'created-checkpoint.json')), 'Existing created checkpoint: read back instead of replaying');
const report = { status: 'RUNNING', runtime, observations: [], errors: [], blocked: [], contracts: [] };
const browser = await launchChromium({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' });
page.setDefaultTimeout(30000);
const navigation = captureReleasedNavigation(page);
const prefix = new URL(base).pathname;
page.on('pageerror', error => report.errors.push(error.message));
page.on('response', async response => {
  try {
    const body = response.request().postDataJSON();
    if (body?.intent === 'ui.contract.v2' && response.ok()) report.contracts.push(await response.json());
  } catch {}
});
await page.route('**/api/**', async route => {
  const req = route.request();
  let body;
  try { body = req.postDataJSON(); } catch {}
  const pathname = new URL(req.url()).pathname.replace(prefix, '');
  if (!permitsInventoryRequest(req.method(), pathname, body, true) &&
      !(req.method() === 'POST' && pathname === '/api/v1/intent' &&
        permitsContractWrite(body, { enabled: execute, key, recordId, readOnly: finalReadback }))) {
    report.blocked.push({ method: req.method(), pathname, intent: body?.intent, params: body?.params });
    return route.abort();
  }
  return route.continue();
});
try {
  await page.goto(matrixLoginUrl(base));
  await page.locator('input').nth(0).fill(process.env.ACCEPTANCE_LOGIN);
  await page.locator('input').nth(1).fill(process.env.ACCEPTANCE_PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL(url => !url.pathname.endsWith('/login'));
  const target = await navigation.targetByMenuXmlid('smart_construction_core.menu_sc_p1_daily_contract');
  report.target = target;
  report.startup = navigation.payload();
  assert.equal(report.startup.user?.company_id, 1);
  assert.notEqual(report.startup.user?.id, 1);
  if (finalReadback) {
    report.record_id = recordId;
    report.business_key = key;
    report.reused_api_sign_receipt = process.env.SC_DEMO_API_SIGN_RECEIPT;
    await page.goto(`${base}/a/${target.action_id}?menu_id=${target.menu_id}`, { waitUntil: 'networkidle' });
    await page.locator('button[data-semantic-cell-kind="primary"]').first().waitFor();
    await page.locator('input[placeholder*="搜索关键字"]:visible').first().fill(key);
    await page.getByRole('button', { name: /^搜索$/ }).first().click();
    await page.waitForFunction(() => document.querySelectorAll('button[data-semantic-cell-kind="primary"]').length === 1);
    const link = page.locator('button[data-semantic-cell-kind="primary"]');
    await link.waitFor();
    assert.equal(await link.count(), 1);
    await link.click();
    for (const stage of ['open', 'reload']) {
      if (stage === 'reload') await page.reload({ waitUntil: 'networkidle' });
      const form = page.locator('[data-semantic-component="ContractFormPage"][data-form-model="sc.general.contract"][data-form-record="6"]').filter({ visible: true });
      await form.waitFor();
      assert.equal(await form.count(), 1);
      const status = form.locator('[data-professional-workflow-component="statusbar"][data-workflow-current="signed"]');
      await status.waitFor();
      const fieldText = async name => {
        const field = form.locator(`[data-field-name="${name}"] .readonly-value`).filter({ visible: true });
        await field.waitFor();
        assert.equal(await field.count(), 1);
        return (await field.innerText()).trim();
      };
      const money = form.locator('[data-field-name="amount_total"] [data-money-display]').filter({ visible: true });
      await money.waitFor();
      assert.equal(await money.count(), 1);
      const amount = (await money.evaluate(n => [...n.childNodes].filter(c => c.nodeType === Node.TEXT_NODE).map(c => c.textContent).join(''))).trim();
      assert.equal(amount, await money.getAttribute('data-money-display'));
      const observed = { pathname: new URL(page.url()).pathname, basePath: new URL(base).pathname,
        recordId: Number(await form.getAttribute('data-form-record')), key,
        name: await fieldText('contract_name'), amount,
        state: await status.getAttribute('data-workflow-current'), stateLabel: await status.innerText() };
      assert(isExactSignedReadback(observed), JSON.stringify(observed));
      report.observations.push({ stage: `signed_${stage}`, ...observed });
      await page.screenshot({ path: path.join(output, `signed-${stage}.png`), fullPage: true });
    }
    assert.equal(report.blocked.length, 0, JSON.stringify(report.blocked));
    assert.equal(report.errors.length, 0, JSON.stringify(report.errors));
    report.status = 'UI_SIGNED_RECORD_OPEN_RELOAD_PASS';
  } else if (resume) {
    assert.deepEqual(target, checkpoint.target);
    report.record_id = recordId;
    report.business_key = key;
    report.reused_create_checkpoint = process.env.SC_DEMO_UI_CHECKPOINT;
    await page.goto(`${base}/f/sc.general.contract/${recordId}?menu_id=${target.menu_id}&action_id=${target.action_id}`, { waitUntil: 'networkidle' });
    await page.locator('input[id*="contract_name"]').first().waitFor({ state: 'visible', timeout: 45000 });
    assert.equal(await page.locator('input[id*="contract_name"]').first().inputValue(), key);
  } else {
  await page.goto(`${base}/a/${target.action_id}?menu_id=${target.menu_id}`, { waitUntil: 'networkidle' });
  await page.locator('button[data-semantic-cell-kind="primary"]').first().waitFor();
  report.observations.push({ stage: 'list', buttons: await page.getByRole('button').allTextContents() });
  if (execute) {
    await page.locator('input[placeholder*="搜索关键字"]:visible').first().fill(key);
    await page.getByRole('button', { name: /^搜索$/ }).first().click();
    await page.waitForTimeout(3500);
    assert.equal(await page.locator('button[data-semantic-cell-kind="primary"]').count(), 0, 'Business key already visible; refuse duplicate creation');
  }
  await page.getByRole('button', { name: /^(新建|新增|创建)$/ }).first().click();
  await page.locator('input[id*="contract_name"]').first().waitFor({ state: 'visible', timeout: 45000 });
  report.observations.push({ stage: 'create_form', url: page.url(), controls: await page.evaluate(() =>
    [...document.querySelectorAll('input,textarea,select,button')].filter(n => n.getClientRects().length).map(n =>
      ({ tag: n.tagName, id: n.id, type: n.type, name: n.name, placeholder: n.getAttribute('placeholder'),
        label: n.getAttribute('aria-label'), text: n.tagName === 'BUTTON' ? n.innerText : '',
        value: n.tagName === 'BUTTON' ? undefined : n.value, disabled: n.disabled, readonly: n.readOnly }))) });
  await page.screenshot({ path: path.join(output, 'create-form.png'), fullPage: true });
  report.status = 'INSPECTED_NOT_ACCEPTED';
  }
  if (execute) {
    const input = name => page.locator(`input[id*="-field-${name}-occ"]`).first();
    const waitSave = operation => page.waitForResponse(response => {
      try {
        const body = response.request().postDataJSON();
        return body.params?.model === 'sc.general.contract' &&
          ((body.intent === 'api.data' && body.params?.op === operation) || (operation === 'write' && body.intent === 'api.data.write'));
      } catch { return false; }
    }, { timeout: 45000 });
    const dataOf = body => body?.data || body?.result?.data || body?.result || body;
    if (!resume) {
    await input('contract_name').fill(key);
    await input('partner_name_text').fill('德阳中联商砼有限公司');
    await input('contract_type').fill('现场服务');
    await input('amount_total').fill('12300');
    await input('amount_total').blur();
    const created = waitSave('create');
    await page.getByRole('button', { name: /^保存草稿$/ }).first().click();
    const createResponse = await created;
    const createBody = await createResponse.json();
    assert(createResponse.ok(), JSON.stringify(createBody));
    recordId = Number(dataOf(createBody).id);
    assert(recordId > 0, JSON.stringify(createBody));
    report.record_id = recordId;
    report.business_key = key;
    fs.writeFileSync(path.join(output, 'created-checkpoint.json'), JSON.stringify({ recordId, key, target, createBody }, null, 2));
    await page.goto(`${base}/f/sc.general.contract/${recordId}?menu_id=${target.menu_id}&action_id=${target.action_id}`, { waitUntil: 'networkidle' });
    await input('contract_name').waitFor({ state: 'visible', timeout: 45000 });
    assert.equal(await input('contract_name').inputValue(), key);
    assert.equal(Number(await input('amount_total').inputValue()), 12300);
    report.observations.push({ stage: 'ui_create_refresh_readback', recordId, key, amount: 12300 });
    }
    const editedAmount = resume ? 12600 : 12500;
    await input('amount_total').fill(String(editedAmount));
    await input('amount_total').blur();
    const edited = waitSave('write');
    await page.getByRole('button', { name: /^保存草稿$/ }).first().click();
    const editResponse = await edited;
    assert(editResponse.ok(), await editResponse.text());
    await page.reload({ waitUntil: 'networkidle' });
    await input('amount_total').waitFor({ state: 'visible', timeout: 45000 });
    assert.equal(Number(await input('amount_total').inputValue()), editedAmount);
    report.observations.push({ stage: 'ui_edit_refresh_readback', recordId, amount: editedAmount });
    await page.screenshot({ path: path.join(output, 'edited.png'), fullPage: true });
    const submitted = page.waitForResponse(response => {
      try { const body = response.request().postDataJSON(); return body.intent === 'execute_button' && Number(body.params?.res_id) === recordId && body.params?.button?.name === 'action_confirm'; } catch { return false; }
    }, { timeout: 45000 });
    await page.getByRole('button', { name: /^提交审批$/ }).first().click();
    await page.waitForTimeout(500);
    const dialog = page.getByRole('dialog');
    if (await dialog.count()) await dialog.getByRole('button', { name: /^(确认|确定|提交)$/ }).first().click();
    const submitResponse = await submitted;
    assert(submitResponse.ok(), await submitResponse.text());
    report.observations.push({ stage: 'ui_formal_submit', recordId, response: await submitResponse.json() });
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(output, 'submitted.png'), fullPage: true });
    report.status = 'UI_CREATE_EDIT_SUBMIT_EXECUTED_PENDING_BACKEND_READBACK';
  }
} catch (error) {
  report.status = 'FAIL';
  report.errors.push(error.message);
  report.visible_dom = await page.locator('[data-semantic-component="ContractFormPage"]').filter({ visible: true }).evaluateAll(nodes => nodes.map(n => n.outerHTML)).catch(() => []);
  await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
} finally {
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close();
}
console.log(JSON.stringify({ status: report.status, errors: report.errors, blocked: report.blocked, output }));
if (report.status === 'FAIL') process.exitCode = 1;

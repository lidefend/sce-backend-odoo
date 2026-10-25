// P4: fixed affected forms, draft interaction only; never save or dispatch.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {launchChromium} from './playwright_runtime.mjs';
import {permitsInventoryRequest} from '../../frontend/apps/web/scripts/bootstrap_inventory_policy.mjs';
// The existing nginx owns the namespace stamp; the preview server does not.
const base = 'http://127.0.0.1:18081/t/demo';
const scope = process.env.SC_FEEDBACK_SCOPE || 'workspace';
assert(['workspace', 'cost'].includes(scope));
const root = `.runtime/product-user-gap-closeout-20261026/${scope}-browser/${process.env.CANDIDATE_GIT_HEAD}`;
fs.mkdirSync(root, {recursive: true});
const availableCases = scope === 'workspace' ? [
  {model: 'sc.team.loan.deduction.workspace', field: 'note', hint: '建议补充办理说明'},
  {model: 'sc.current.account.workspace', field: 'note', hint: '建议补充办理说明', retained: '办理承包人借还款前请选择承包人/往来单位'},
] : [
  {model: 'sc.equipment.usage', field: 'equipment_code', hint: '建议补充设备编号', retained: '建议上传台班依据', create: true},
  {model: 'sc.subcontract.register', field: 'management_note', tab: '管理要求', hint: '建议补充管理要求', retained: '建议上传分包成本依据', create: true},
  {model: 'sc.hr.salary.payment', field: 'note', tab: '发放说明', hint: '建议补充发放说明', retained: '建议上传发放依据', create: true},
];
const selected = process.env.SC_FEEDBACK_MODELS?.split(',').filter(Boolean);
if (selected) {
  assert(selected.length && new Set(selected).size === selected.length);
  assert(selected.every(model => availableCases.some(item => item.model === model)), 'model outside fixed scope');
}
const cases = selected ? availableCases.filter(item => selected.includes(item.model)) : availableCases;
const models = cases.map(item => item.model);
const report = {head: process.env.CANDIDATE_GIT_HEAD, cases: [], blocked: [], errors: [], feedback: [], passed: false};
assert(/^[a-f0-9]{40}$/.test(report.head || ''));
const browser = await launchChromium({headless: true});
let page;
try {
  page = await browser.newPage({viewport: {width: 1440, height: 960}, locale: 'zh-CN'});
  page.setDefaultTimeout(20000);
  let init;
  page.on('pageerror', error => report.errors.push(error.message));
  await page.route('**/api/**', async route => {
    const req = route.request();
    let body; try { body = req.postDataJSON(); } catch {}
    const request = body?.params?.intent ? body.params : body;
    const pathname = new URL(req.url()).pathname.replace(/^\/t\/demo/, '');
    const draft = req.method() === 'POST' && pathname === '/api/v1/intent' &&
      request?.intent === 'api.onchange' && models.includes(request.params?.model);
    if (!draft && !permitsInventoryRequest(req.method(), pathname, body, false)) {
      report.blocked.push({intent: request?.intent || pathname});
      return route.abort();
    }
    await route.continue();
  });
  page.on('response', async response => {
    let request; try { const body = response.request().postDataJSON(); request = body?.params?.intent ? body.params : body; } catch {}
    if (!['system.init', 'api.onchange'].includes(request?.intent)) return;
    try {
      const payload = await response.json();
      if (request.intent === 'system.init') init = payload.data;
      else if (request.params.feedback_evaluation) report.feedback.push({model: request.params.model, ok: payload.ok, data: payload.data});
    } catch {}
  });
  await page.goto(base + '/login', {waitUntil: 'domcontentloaded'});
  await page.locator('#login-username').fill('demo_full');
  await page.locator('#login-password').fill(process.env.E2E_PASSWORD);
  const database = page.getByLabel(/数据库/);
  assert(await database.count() <= 1, 'database selector must be unique');
  if (await database.count() && await database.isVisible() && await database.isEnabled()) {
    await database.fill('sc_dev_demo');
  }
  await page.getByRole('button', {name: /^登录$/}).click();
  await page.waitForURL(url => !url.pathname.includes('/login'), {timeout: 45000});
  await page.waitForTimeout(1200);
  assert(init?.navigation?.nav, 'authoritative navigation missing');
  const leaves = [];
  function walk(nodes) { for (const node of nodes) { if (node.children?.length) walk(node.children); else leaves.push(node); } }
  walk(init.navigation.nav);
  report.actor = {uid: init.user?.id, login: 'demo_full', company: init.user?.company_id};
  for (const plan of cases) {
    const {model} = plan;
    const node = leaves.find(n => n.meta?.model === model);
    assert(node?.meta?.route?.startsWith('/'), 'workspace navigation declaration missing: ' + model);
    const item = {model, route: node.meta.route}; report.cases.push(item);
    await page.goto(base + node.meta.route, {waitUntil: 'domcontentloaded'});
    if (plan.create) await page.getByRole('button', {name: /^(新建|新增|创建)$/}).first().click();
    if (plan.tab) await page.locator(`[data-section-tab="${plan.tab}"]`).click();
    const note = page.locator(`[data-field-name="${plan.field}"]`).locator('textarea, input:not([type="hidden"])').first();
    await note.waitFor({state: 'visible', timeout: 45000});
    await page.getByText(plan.hint, {exact: false}).last().waitFor({state: 'visible'});
    item.before = await page.locator('body').innerText();
    const refreshed = page.waitForResponse(async response => {
      let body; try { body = response.request().postDataJSON(); } catch { return false; }
      const request = body?.params?.intent ? body.params : body;
      if (request?.intent !== 'api.onchange' || request.params?.model !== model ||
          request.params?.feedback_evaluation?.operation !== 'evaluate') return false;
      const payload = await response.json();
      const result = payload.data?.feedback_evaluation;
      return payload.ok === true && result?.status === 'ready' &&
        !result.result.content.includes(plan.hint);
    });
    await note.fill('本次仅验证草稿提示，未保存或办理业务');
    await note.blur();
    await refreshed;
    await page.waitForFunction(hint => !document.body.innerText.includes(hint), plan.hint);
    if (plan.retained) await page.getByText(plan.retained, {exact: false}).last().waitFor({state: 'visible'});
    item.after = await page.locator('body').innerText();
    item.actions = await page.getByRole('button').allTextContents();
    assert(!/页面加载失败|ContractGapError/.test(item.after));
    await page.screenshot({path: `${root}/${model}-desktop.png`});
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: `${root}/${model}-mobile.png`});
    await page.setViewportSize({width: 1440, height: 960});
    item.passed = true;
  }
  assert.equal(report.errors.length, 0);
  for (const model of models) assert(report.feedback.some(r => r.model === model && r.ok), 'feedback transport missing');
  report.passed = true;
} finally {
  report.lastPage = page ? {url: page.url(), text: await page.locator('body').innerText().catch(() => '')} : null;
  await browser.close();
  fs.writeFileSync(`${root}/report.json`, JSON.stringify(report, null, 2));
}
console.log(`feedback browser: PASS (${cases.length} ${scope} forms, no save/dispatch)`);

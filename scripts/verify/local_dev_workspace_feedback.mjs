// P4: two existing workspaces, draft interaction only; never save or dispatch.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {launchChromium} from './playwright_runtime.mjs';
import {permitsInventoryRequest} from '../../frontend/apps/web/scripts/bootstrap_inventory_policy.mjs';
const base = 'http://127.0.0.1:5176';
const root = '.runtime/product-user-gap-closeout-20261026/workspace-browser';
fs.mkdirSync(root, {recursive: true});
const models = ['sc.team.loan.deduction.workspace', 'sc.current.account.workspace'];
const report = {head: process.env.CANDIDATE_GIT_HEAD, cases: [], blocked: [], errors: [], feedback: [], passed: false};
assert(/^[a-f0-9]{40}$/.test(report.head || ''));
const browser = await launchChromium({headless: true});
try {
  const page = await browser.newPage({viewport: {width: 1440, height: 960}, locale: 'zh-CN'});
  page.setDefaultTimeout(20000);
  let init;
  page.on('pageerror', error => report.errors.push(error.message));
  await page.route('**/api/**', async route => {
    const req = route.request();
    let body; try { body = req.postDataJSON(); } catch {}
    const request = body?.params?.intent ? body.params : body;
    const pathname = new URL(req.url()).pathname;
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
  await page.getByRole('button', {name: /^登录$/}).click();
  await page.waitForURL(url => !url.pathname.includes('/login'), {timeout: 45000});
  await page.waitForTimeout(1200);
  assert(init?.navigation?.nav, 'authoritative navigation missing');
  const leaves = [];
  function walk(nodes) { for (const node of nodes) { if (node.children?.length) walk(node.children); else leaves.push(node); } }
  walk(init.navigation.nav);
  report.actor = {uid: init.user?.id, login: 'demo_full', company: init.user?.company_id};
  for (const model of models) {
    const node = leaves.find(n => n.meta?.model === model);
    assert(node?.meta?.route?.startsWith('/'), 'workspace navigation declaration missing: ' + model);
    const item = {model, route: node.meta.route}; report.cases.push(item);
    await page.goto(base + node.meta.route, {waitUntil: 'domcontentloaded'});
    const note = page.locator('[data-field-name="note"] textarea');
    await note.waitFor({state: 'visible', timeout: 45000});
    await page.getByText('建议补充办理说明', {exact: false}).last().waitFor({state: 'visible'});
    item.before = await page.locator('body').innerText();
    await note.fill('本次仅验证草稿提示，未保存或办理业务');
    await note.blur();
    await page.waitForFunction(() => !document.body.innerText.includes('建议补充办理说明'));
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
  await browser.close();
  fs.writeFileSync(`${root}/report.json`, JSON.stringify(report, null, 2));
}
console.log('workspace feedback browser: PASS (2 workspaces, no save/dispatch)');

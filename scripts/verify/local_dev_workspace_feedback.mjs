// P4: fixed affected forms, draft interaction only; never save or dispatch.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {launchChromium} from './playwright_runtime.mjs';
import {permitsInventoryRequest} from '../../frontend/apps/web/scripts/bootstrap_inventory_policy.mjs';
// The existing nginx owns the namespace stamp; the preview server does not.
const base = 'http://127.0.0.1:18081/t/demo';
const scope = process.env.SC_FEEDBACK_SCOPE || 'workspace';
assert(['workspace', 'cost', 'conditioned', 'approval', 'usability'].includes(scope));
const root = `.runtime/product-user-gap-closeout-20261026/${scope}-browser/${process.env.CANDIDATE_GIT_HEAD}`;
fs.mkdirSync(root, {recursive: true});
const actor = scope === 'usability' ? (process.env.SC_FEEDBACK_ACTOR || 'demo_full') : 'demo_full';
assert(['demo_full', 'demo_role_pm', 'demo_role_finance', 'demo_role_project_read'].includes(actor));
const availableCases = scope === 'usability' ? [] : scope === 'workspace' ? [
  {model: 'sc.team.loan.deduction.workspace', field: 'note', hint: '建议补充办理说明'},
  {model: 'sc.current.account.workspace', field: 'note', hint: '建议补充办理说明', retained: '办理承包人借还款前请选择承包人/往来单位'},
] : scope === 'cost' ? [
  {model: 'sc.equipment.usage', field: 'equipment_code', hint: '建议补充设备编号', retained: '建议上传台班依据', create: true},
  {model: 'sc.subcontract.register', field: 'management_note', tab: '管理要求', hint: '建议补充管理要求', retained: '建议上传分包成本依据', create: true},
  {model: 'sc.hr.salary.payment', field: 'note', tab: '发放说明', hint: '建议补充发放说明', retained: '建议上传发放依据', create: true},
] : scope === 'conditioned' ? [
  {model: 'sc.quality.acceptance', field: 'location', hint: '建议补充验收部位', retained: '建议上传验收资料', create: true},
  {model: 'sc.labor.usage', field: 'work_type', hint: '建议补充工种', retained: '建议上传用工依据', create: true},
  {model: 'sc.hr.payroll.document', menu: '695', selection: '工资登记', field: 'payout_unit', hint: '建议补充发放单位', retained: '建议上传薪资核算依据', create: true},
  {model: 'sc.hr.payroll.document', menu: '706', selection: '公积金登记', field: 'payer_unit', hint: '建议补充缴存单位', retained: '建议补充公积金账号', create: true},
  {model: 'sc.hr.payroll.document', menu: '673', selection: '工资登记', field: 'payout_unit', hint: '建议补充发放单位', retained: '建议上传薪资核算依据', create: true},
] : [
  {model: 'sc.approval.policy', menu: '424', key: 'approval-general', approval: true, selection: '项目立项',
    target: 'project.project', expectedVisible: false, field: 'name', create: true},
  {model: 'sc.approval.policy', menu: '424', key: 'approval-payment', approval: true, selection: '付款/收款申请',
    target: 'payment.request', expectedVisible: true, field: 'name', create: true},
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
  await page.locator('#login-username').fill(actor);
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
  report.actor = {uid: init.user?.id, login: actor, company: init.user?.company_id};
  if (scope === 'usability') {
    await page.goto(base + '/s/workspace.home', {waitUntil: 'domcontentloaded'});
    const capability = page.locator('[data-login-home-block="capability_map"]');
    await capability.waitFor({state: 'visible', timeout: 45000});
    await page.waitForFunction(() => ['ready', 'empty'].includes(document.querySelector('[data-login-home-block="capability_map"]')?.getAttribute('data-state')));
    assert((await capability.innerText()).includes('工作入口'));
    const state = await capability.getAttribute('data-state');
    if (actor !== 'demo_full') assert.equal(state, 'empty', 'ordinary-role empty-state sample missing');
    if (state === 'empty') assert((await capability.innerText()).includes('暂无首页快捷入口。请从导航菜单选择业务；如需调整权限，请联系管理员。'));
    const risks = await page.locator('[data-login-home-block="risks"]').innerText();
    if (actor === 'demo_full') assert(/风险状态[：:]/.test(risks), 'actual risk state sample missing');
    assert(!/风险状态[：:]\s*(open|claimed|escalated)\b/.test(risks));
    report.cases.push({key: 'home', state, risks, text: await capability.innerText(), passed: true});
    await page.screenshot({path: `${root}/${actor}-home-desktop.png`});
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: `${root}/${actor}-home-mobile.png`});
    if (actor === 'demo_full') {
      const node = leaves.find(n => n.meta?.route && new URL(n.meta.route, base).searchParams.get('menu_id') === '431');
      assert(node?.meta?.route?.startsWith('/'), 'config navigation declaration missing');
      await page.goto(base + node.meta.route, {waitUntil: 'domcontentloaded'});
      const header = page.locator('.business-config-context .product-page-header');
      await header.waitFor({state: 'visible', timeout: 45000});
      const choosePage = page.getByRole('button', {name: '选择业务页面', exact: true}).first();
      await choosePage.waitFor({state: 'visible', timeout: 45000});
      assert(await choosePage.isEnabled(), 'page selection unavailable after loading');
      for (const width of [390, 1440]) {
        await page.setViewportSize({width, height: width === 390 ? 844 : 960});
        const layout = await header.evaluate(el => ({
          columns: getComputedStyle(el).gridTemplateColumns,
          identityColumn: getComputedStyle(el.querySelector('.product-page-header__identity')).gridColumn,
          actionsColumn: getComputedStyle(el.querySelector('.product-page-header__actions')).gridColumn,
        }));
        if (width === 390) {
          assert.equal(layout.columns.split(' ').length, 1, 'mobile header must use one column');
          assert.equal(layout.identityColumn, '1 / -1');
          assert.equal(layout.actionsColumn, '1 / -1');
        } else assert(layout.columns.split(' ').length > 1, 'desktop header must retain multiple columns');
        report.cases.push({key: 'config-' + width, route: node.meta.route, layout, passed: true});
        await page.screenshot({path: `${root}/${actor}-config-${width}.png`});
      }
    }
    assert.equal(report.blocked.length, 0, 'read-only observer blocked requests');
  }
  for (const plan of cases) {
    const {model} = plan;
    const node = leaves.find(n => n.meta?.model === model && (!plan.menu ||
      new URL(n.meta.route, base).searchParams.get('menu_id') === plan.menu));
    assert(node?.meta?.route?.startsWith('/'), 'workspace navigation declaration missing: ' + model);
    const key = plan.key || (plan.menu ? model + '-' + plan.menu : model);
    const item = {key, model, menu: plan.menu, target: plan.target, route: node.meta.route}; report.cases.push(item);
    await page.goto(base + node.meta.route, {waitUntil: 'domcontentloaded'});
    if (plan.create) await page.getByRole('button', {name: /^(新建|新增|创建)$/}).first().click();
    const approvalText = '付款申请的启用审批和审批方式请在“系统参数”中发布或回滚。';
    const approvalReady = plan.approval ? page.waitForResponse(async response => {
      let body; try { body = response.request().postDataJSON(); } catch { return false; }
      const request = body?.params?.intent ? body.params : body;
      const evaluation = request?.params?.feedback_evaluation;
      if (request?.intent !== 'api.onchange' || request.params.model !== model ||
          evaluation?.operation !== 'evaluate' ||
          !evaluation.inputs?.some(row => row.field === 'target_model' && row.value === plan.target)) return false;
      const payload = await response.json();
      const result = payload.data?.feedback_evaluation;
      return payload.ok === true && result?.status === 'ready' &&
        result.result.visible === plan.expectedVisible &&
        result.result.content === (plan.expectedVisible ? approvalText : '');
    }) : null;
    if (plan.selection) {
      const select = page.locator(`[data-field-name="${plan.approval ? 'target_model' : 'fact_type'}"] [data-semantic-component="ScSelect"]`);
      await select.waitFor({state: 'visible', timeout: 45000});
      await select.click();
      await page.getByText(plan.selection, {exact: true}).last().click();
    }
    if (plan.tab) await page.locator(`[data-section-tab="${plan.tab}"]`).click();
    const note = page.locator(`[data-field-name="${plan.field}"]`).locator('textarea:visible, input:not([type="hidden"]):visible').first();
    await note.waitFor({state: 'visible', timeout: 45000});
    if (plan.approval) {
      await approvalReady;
      await page.waitForFunction(({text, visible}) => document.body.innerText.includes(text) === visible,
        {text: approvalText, visible: plan.expectedVisible});
      item.before = await page.locator('body').innerText();
      await note.fill('草稿提示验证，未保存规则');
      assert.equal(await note.inputValue(), '草稿提示验证，未保存规则');
      assert.equal((await page.locator('body').innerText()).includes(approvalText), plan.expectedVisible);
    } else {
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
    }
    item.after = await page.locator('body').innerText();
    item.actions = await page.getByRole('button').allTextContents();
    assert(!/页面加载失败|ContractGapError/.test(item.after));
    await page.screenshot({path: `${root}/${key}-desktop.png`});
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: `${root}/${key}-mobile.png`});
    await page.setViewportSize({width: 1440, height: 960});
    item.passed = true;
  }
  assert.equal(report.errors.length, 0);
  for (const model of models) assert(report.feedback.some(r => r.model === model && r.ok), 'feedback transport missing');
  report.passed = true;
} finally {
  report.lastPage = page ? {url: page.url(), text: await page.locator('body').innerText().catch(() => '')} : null;
  await browser.close();
  fs.writeFileSync(`${root}/${scope === 'usability' ? actor + '-' : ''}report.json`, JSON.stringify(report, null, 2));
}
console.log(`browser: PASS (${report.cases.length} ${scope} cases, no save/dispatch)`);

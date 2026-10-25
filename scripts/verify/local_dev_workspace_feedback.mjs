// P4: fixed affected forms, draft interaction only; never save or dispatch.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {launchChromium} from './playwright_runtime.mjs';
import {permitsInventoryRequest} from '../../frontend/apps/web/scripts/bootstrap_inventory_policy.mjs';
// The existing nginx owns the namespace stamp; the preview server does not.
const base = 'http://127.0.0.1:18081/t/demo';
const scope = process.env.SC_FEEDBACK_SCOPE || 'workspace';
assert(['workspace', 'cost', 'conditioned', 'approval', 'usability', 'create-authority', 'certificate', 'analysis'].includes(scope));
const root = `.runtime/product-user-gap-closeout-20261026/${scope}-browser/${process.env.CANDIDATE_GIT_HEAD}`;
fs.mkdirSync(root, {recursive: true});
const actor = scope === 'usability' ? (process.env.SC_FEEDBACK_ACTOR || 'demo_full') : 'demo_full';
assert(['demo_full', 'demo_role_pm', 'demo_role_finance', 'demo_role_project_read'].includes(actor));
const availableCases = ['usability', 'create-authority', 'certificate', 'analysis'].includes(scope) ? [] : scope === 'workspace' ? [
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
let certificateRecordId = null;
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
    const certificateRead = scope === 'certificate' && certificateRecordId !== null &&
      req.method() === 'POST' && pathname === '/api/v1/intent' && ['chatter.timeline', 'chatter.followers.list'].includes(request?.intent) &&
      request.params?.model === 'sc.document.admin.document' &&
      Number(request.params.res_id ?? request.params.record_id) === certificateRecordId;
    if (!draft && !certificateRead && !permitsInventoryRequest(req.method(), pathname, body, false)) {
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
  if (scope === 'analysis') {
    const views = (process.env.SC_ANALYSIS_VIEWS || 'pivot,graph').split(',');
    assert(views.length && new Set(views).size === views.length && views.every(view => ['pivot', 'graph'].includes(view)));
    for (const plan of [
      {menu: '703', model: 'sc.tax.filing', view: 'pivot'},
      {menu: '704', model: 'sc.labor.subcontract.report', view: 'pivot'},
      {menu: '704', model: 'sc.labor.subcontract.report', view: 'graph'},
    ].filter(plan => views.includes(plan.view))) {
      const node = leaves.find(n => n.meta?.model === plan.model && new URL(n.meta.route, base).searchParams.get('menu_id') === plan.menu);
      assert(node?.meta?.route?.startsWith('/'), 'analysis entry missing');
      const responseFor = (intent, operation) => page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === intent && request.params?.op === operation &&
          (intent === 'ui.contract.v2' ? String(request.params.menu_id) === plan.menu : request.params.model === plan.model);
      }, {timeout: 45000});
      const contractResponse = responseFor('ui.contract.v2', 'action_open');
      const dataResponse = responseFor('api.data', 'list');
      const url = new URL(base + node.meta.route);
      url.searchParams.set('view_mode', plan.view);
      await page.goto(url.href, {waitUntil: 'domcontentloaded'});
      const contract = await (await contractResponse).json();
      const data = await (await dataResponse).json();
      assert.equal(contract.ok, true); assert.equal(data.ok, true);
      const profile = contract.data.layoutContract[plan.view + 'Profile'];
      assert(profile?.dimensions?.length && profile?.measures?.length, 'analysis declaration absent');
      const records = data.data.records;
      assert(records?.length, 'demo analysis sample absent');
      const groups = new Map();
      for (const record of records) {
        const raw = profile.dimensions.map(field => Array.isArray(record[field.name]) ? record[field.name][0] : record[field.name] ?? null);
        const key = JSON.stringify(raw);
        const labels = profile.dimensions.map(field => {
          const value = record[field.name];
          if (value === false || value == null || value === '') return '--';
          if (field.fieldType === 'selection') {
            const choice = field.selection.find(pair => pair[0] === value);
            assert(choice?.[1] && choice[1] !== value, 'untranslated selection declaration');
            return choice[1];
          }
          return Array.isArray(value) ? String(value[1]) : String(value);
        });
        const group = groups.get(key) || {labels, totals: profile.measures.map(() => 0)};
        profile.measures.forEach((field, index) => { group.totals[index] += Number(record[field.name] || 0); });
        groups.set(key, group);
      }
      const expected = [...groups.values()];
      const surface = page.locator(`[data-analysis-view="${plan.view}"][data-analysis-state="ready"]`);
      await surface.waitFor({state: 'visible', timeout: 45000});
      const item = {...plan, route: url.href, fields: profile, loadedRecords: records.length,
        reportedTotal: data.data.total, expected, viewports: [], passed: false};
      report.cases.push(item);
      for (const width of [1440, 390]) {
        await page.setViewportSize({width, height: width === 390 ? 844 : 960});
        if (plan.view === 'pivot') {
          const headers = await surface.getByRole('columnheader').allTextContents();
          for (const field of [...profile.dimensions, ...profile.measures]) {
            assert(field.label && field.label !== field.name, 'technical analysis label');
            assert(headers.some(header => header.trim() === field.label), 'native header not rendered: ' + field.label);
          }
          const rows = await surface.getByRole('row').all();
          const actual = [];
          for (const row of rows) {
            const cells = await row.getByRole('cell').allTextContents();
            if (cells.length) actual.push(cells.map(cell => cell.trim()));
          }
          assert.deepEqual(actual, expected.map(group => [...group.labels, ...group.totals.map(String)]), 'analysis labels/group totals differ from loaded API records');
        } else {
          const rows = surface.getByRole('article');
          assert.equal(await rows.count(), expected.length);
          for (let index = 0; index < expected.length; index++) {
            const paragraphs = await rows.nth(index).getByRole('paragraph').allTextContents();
            assert.deepEqual(paragraphs.map(value => value.trim()), [expected[index].labels.join(' / '), String(expected[index].totals[0])]);
          }
        }
        await page.screenshot({path: `${root}/${plan.menu}-${plan.view}-${width}.png`});
        item.viewports.push(width);
      }
      item.passed = true;
    }
    assert.equal(report.blocked.length, 0);
  }
  if (scope === 'certificate') {
    const model = 'sc.document.admin.document';
    const fields = ['certificate_name', 'certificate_no', 'holder_name', 'valid_until'];
    const menus = (process.env.SC_CERTIFICATE_MENUS || '356,708').split(',');
    assert(menus.length && new Set(menus).size === menus.length && menus.every(menu => ['356', '708'].includes(menu)));
    for (const menu of menus) {
      const node = leaves.find(n => n.meta?.model === model && new URL(n.meta.route, base).searchParams.get('menu_id') === menu);
      assert(node?.meta?.route?.startsWith('/'), 'document entry missing');
      const responseFor = (intent, operation) => page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === intent && request.params?.op === operation &&
          (intent === 'ui.contract.v2' ? String(request.params.menu_id) === menu : request.params.model === model);
      }, {timeout: 45000});
      const contractResponse = responseFor('ui.contract.v2', 'action_open');
      const dataResponse = responseFor('api.data', 'list');
      await page.goto(base + node.meta.route, {waitUntil: 'domcontentloaded'});
      const contract = await (await contractResponse).json();
      const data = await (await dataResponse).json();
      assert.equal(contract.ok, true); assert.equal(data.ok, true);
      const profile = contract.data.layoutContract.listProfile;
      const columns = profile.fact_columns || profile.columns;
      const records = data.data.records;
      assert(Array.isArray(records), 'document list response missing');
      await page.waitForFunction(() => ['ok', 'empty'].includes(document.querySelector('[data-semantic-component="ActionView"]')?.getAttribute('data-collection-state')));
      const item = {menu, route: node.meta.route, columns}; report.cases.push(item);
      if (menu === '356') {
        for (const field of fields) assert(columns.includes(field), 'certificate column missing: ' + field);
        assert(!columns.includes('document_title'));
        const record = records.find(row => fields.every(field => row[field]));
        assert(record, 'certificate name/number/holder/expiry data sample missing');
        item.record = {id: record.id, ...Object.fromEntries(fields.map(field => [field, record[field]]))};
        for (const width of [1440, 390]) {
          await page.setViewportSize({width, height: width === 390 ? 844 : 960});
          const text = await page.locator('[data-semantic-component="ActionView"]').innerText();
          assert(text.includes(record.certificate_name), 'certificate name not rendered');
          assert(text.includes(record.certificate_no), 'certificate number not rendered');
          assert(text.includes(record.valid_until), 'expiry not rendered');
          if (record.holder_name) assert(text.includes(record.holder_name), 'holder not rendered');
          await page.screenshot({path: `${root}/certificate-${width}.png`});
        }
        await page.setViewportSize({width: 1440, height: 960});
        certificateRecordId = Number(record.id);
        const collaborationResponses = ['chatter.timeline', 'chatter.followers.list'].map(intent => page.waitForResponse(response => {
          let body; try { body = response.request().postDataJSON(); } catch { return false; }
          const request = body?.params?.intent ? body.params : body;
          return request?.intent === intent && request.params?.model === model &&
            Number(request.params.res_id ?? request.params.record_id) === certificateRecordId;
        }, {timeout: 45000}));
        await page.goto(base + '/r/' + model + '/' + record.id + '?menu_id=' + menu, {waitUntil: 'domcontentloaded'});
        await page.locator('[data-field-name="certificate_name"]').first().waitFor({state: 'visible', timeout: 45000});
        for (const field of fields) {
          const container = page.locator(`[data-field-name="${field}"]`).first();
          const value = await container.evaluate(el => el.textContent + ' ' + Array.from(el.querySelectorAll('input,textarea')).map(input => input.value).join(' '));
          if (record[field]) assert(value.includes(record[field]), 'detail differs from list: ' + field);
        }
        item.collaboration = [];
        for (const response of await Promise.all(collaborationResponses)) {
          const result = {http: response.status(), ok: (await response.json()).ok};
          assert.equal(result.http, 200, 'certificate collaboration HTTP failed');
          assert.equal(result.ok, true, 'certificate collaboration read failed');
          item.collaboration.push(result);
        }
        await page.screenshot({path: `${root}/certificate-detail.png`});
      } else {
        assert(columns.includes('document_title') && columns.includes('policy_version'));
        for (const field of fields) assert(!columns.includes(field), 'certificate field leaked to policies');
        await page.screenshot({path: `${root}/policy-list.png`});
      }
      item.passed = true;
    }
    assert.equal(report.blocked.length, 0);
  }
  if (scope === 'create-authority') {
    for (const plan of [
      {model: 'account.move.line', menu: '176', allowed: false},
      {model: 'sc.tax.filing', menu: '703', allowed: false},
      {model: 'sc.tax.filing', menu: '702', allowed: true},
    ]) {
      const node = leaves.find(n => n.meta?.model === plan.model && new URL(n.meta.route, base).searchParams.get('menu_id') === plan.menu);
      assert(node?.meta?.route?.startsWith('/'), 'declared entry missing');
      const responseFor = operation => page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === 'ui.contract.v2' && request.params?.op === operation &&
          String(request.params.menu_id) === plan.menu;
      }, {timeout: 45000});
      const collectionResponse = responseFor('action_open');
      await page.goto(base + node.meta.route, {waitUntil: 'domcontentloaded'});
      const collectionPayload = await (await collectionResponse).json();
      assert.equal(collectionPayload.ok, true);
      const collectionStatus = collectionPayload.data.statusContract.globalStatus;
      assert.equal(collectionStatus.effectiveRecordCapabilities.create, plan.allowed);
      await page.waitForFunction(() => ['ok', 'empty'].includes(document.querySelector('[data-semantic-component="ActionView"]')?.getAttribute('data-collection-state')));
      const surface = page.locator('[data-semantic-component="ActionView"]');
      assert.equal(await surface.getAttribute('data-can-create'), String(plan.allowed));
      const create = page.getByRole('button', {name: /^(新建|新增|创建)$/});
      if (plan.allowed) { assert.equal(await create.count(), 1); assert(await create.isEnabled()); }
      else for (const button of await create.all()) assert(!await button.isEnabled(), 'forbidden create offered');
      const item = {...plan, collectionStatus, route: node.meta.route}; report.cases.push(item);
      await page.screenshot({path: `${root}/${plan.menu}-list.png`});
      const formResponse = responseFor('model');
      if (plan.allowed) await create.click();
      else await page.goto(base + '/f/' + plan.model + '/new?menu_id=' + plan.menu, {waitUntil: 'domcontentloaded'});
      const formPayload = await (await formResponse).json();
      assert.equal(formPayload.ok, true);
      item.formStatus = formPayload.data.statusContract.globalStatus;
      assert.equal(item.formStatus.effectiveRecordCapabilities.create, plan.allowed);
      if (!plan.allowed) {
        assert.equal(item.formStatus.pageVisible, false);
        assert.equal(item.formStatus.reasonCode, 'FORM_CREATE_NOT_ALLOWED');
      } else {
        await page.locator('[data-field-name="period_start"]').first().waitFor({state: 'visible', timeout: 45000});
        assert(new URL(page.url()).pathname.endsWith('/f/sc.tax.filing/new'));
        assert(!(await page.locator('body').innerText()).includes('页面加载失败'));
        await page.screenshot({path: `${root}/${plan.menu}-create.png`});
      }
      item.passed = true;
    }
    assert.equal(report.blocked.length, 0);
  }
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

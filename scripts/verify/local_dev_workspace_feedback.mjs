// P4: fixed affected forms. journal-save permits one owned draft and exact cleanup; no posting.
import fs from 'node:fs';
import { saveClerkJournal } from './local_dev_journal_clerk_save.mjs';
import { inspectMobileAccounting, inspectMobileJournalRoots } from './local_dev_journal_mobile.mjs';
import { permitsJournalSaveMutation, permitsJournalRoleRead, permitsJournalDetailRead, journalFormWidgets, journalLineColumns } from './local_dev_journal_save_policy.mjs';
import assert from 'node:assert/strict';
import {launchChromium} from './playwright_runtime.mjs';
import {permitsInventoryRequest} from '../../frontend/apps/web/scripts/bootstrap_inventory_policy.mjs';
// The existing nginx owns the namespace stamp; the preview server does not.
const base = 'http://127.0.0.1:18081/t/demo';
const scope = process.env.SC_FEEDBACK_SCOPE || 'workspace';
assert(['workspace', 'cost', 'conditioned', 'approval', 'usability', 'create-authority', 'certificate', 'analysis', 'payroll', 'native-child', 'journal-draft', 'journal-save', 'journal-role'].includes(scope));
const mobileRoot = process.env.SC_FEEDBACK_VIEWPORT === 'mobile-root';
const mobile = mobileRoot || process.env.SC_FEEDBACK_VIEWPORT === 'mobile';
assert(['', 'desktop', 'mobile', 'mobile-root'].includes(process.env.SC_FEEDBACK_VIEWPORT || ''));
assert(!mobile || scope === 'journal-role');
const root = scope === 'journal-save' ? process.env.SC_RUNTIME_JOURNAL_EVIDENCE
  : `.runtime/product-user-gap-closeout-20261026/${scope}-browser/${process.env.CANDIDATE_GIT_HEAD}${mobileRoot ? '/mobile-root' : mobile ? '/mobile' : ''}`;
if (scope === 'journal-save') assert.equal(root, `.runtime/product-user-gap-closeout-20261026/journal-save-browser/${process.env.CANDIDATE_GIT_HEAD}/${process.env.SC_RUNTIME_JOURNAL_REF}`);
fs.mkdirSync(root, {recursive: true});
const actor = ['usability', 'journal-role', 'journal-save'].includes(scope) ? (process.env.SC_FEEDBACK_ACTOR || 'demo_full') : 'demo_full';
assert(['demo_full', 'demo_role_pm', 'demo_role_finance', 'demo_role_project_read', 'sc_demo_accounting_manager', 'sc_demo_accounting_read', 'sc_demo_accounting_user'].includes(actor));
const accountingActor = ['sc_demo_accounting_manager','sc_demo_accounting_read','sc_demo_accounting_user'].includes(actor);
const accountingReadonly = actor === 'sc_demo_accounting_read';
const availableCases = ['usability', 'create-authority', 'certificate', 'analysis', 'payroll', 'native-child', 'journal-draft', 'journal-save', 'journal-role'].includes(scope) ? [] : scope === 'workspace' ? [
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
const models = ['journal-draft', 'journal-save'].includes(scope) ? ['account.move', 'account.move.line'] : scope === 'native-child' ? ['res.partner'] : cases.map(item => item.model);
const report = {head: process.env.CANDIDATE_GIT_HEAD, cases: [], blocked: [], errors: [], feedback: [], onchanges: [], childInitializations: [], passed: false};
assert(/^[a-f0-9]{40}$/.test(report.head || ''));
const browser = await launchChromium({headless: true});
let page;
let certificateRecordId = null;
let journalDetailId = null;
const journalRolePairs = new Set(accountingActor ? [] : ['292/175']);
const journalSave = { enabled: scope === 'journal-save', ready: false, createAttempted: false, cleanupVerified: false,
  ref: process.env.SC_RUNTIME_JOURNAL_REF, createdId: null, accounts: [], rowKeys: [] };
if (journalSave.enabled) {
  assert(['demo_full','sc_demo_accounting_user'].includes(actor));
  assert.equal(Number(process.env.SC_FEEDBACK_EXPECTED_UID || 40), actor === 'demo_full' ? 40 : 1988);
  assert(new RegExp(`^P4-JOURNAL-${report.head}-[a-f0-9]{32}$`).test(journalSave.ref));
  report.ownedRef = journalSave.ref;
  assert.equal(process.env.CONFIRM_LOCAL_DEV_JOURNAL_SAVE, 'CREATE_READBACK_CLEANUP_ONE_DRAFT');
  assert(process.env.SC_LOCAL_DEV_WRITE_LEASE_TOKEN, 'governed write lease required');
  assert.equal(process.env.DB_NAME, 'sc_dev_demo');
  assert.equal(process.env.ODOO_DBFILTER, '^sc_dev_demo$');
}
let journalTransport;
async function journalApi(intent, params) {
  assert(journalTransport, 'existing authenticated transport required');
  return page.evaluate(async ({url, headers, body}) => {
    const response = await fetch(url, {method: 'POST', headers, body: JSON.stringify(body)});
    return {status: response.status, payload: await response.json()};
  }, {...journalTransport, body: {intent, params}});
}
async function ownedJournalRows() {
  const result = await journalApi('api.data', {op:'list',model:'account.move',domain:[['ref','=',journalSave.ref]],
    fields:['id','ref','state','company_id','journal_id','currency_id','line_ids'],limit:2});
  assert.equal(result.payload.ok,true); assert.equal(result.status,200);
  return result.payload.data.records;
}
try {
  page = await browser.newPage({viewport: mobile ? {width: 390, height: 844} : {width: 1440, height: 960}, hasTouch: mobile, isMobile: mobile, locale: 'zh-CN'});
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
    const roleAuthorityRead = scope === 'journal-role'
      && permitsJournalRoleRead(request, journalRolePairs, {method:req.method(),path:pathname});
    const detailRead = scope === 'journal-role' && accountingActor
      && permitsJournalDetailRead(request,journalDetailId,{method:req.method(),path:pathname});
    const ownedMutation = permitsJournalSaveMutation(request, journalSave, {method:req.method(),path:pathname});
    const ownedRead = journalSave.enabled && Number.isSafeInteger(journalSave.createdId) && req.method()==='POST' && pathname==='/api/v1/intent'
      && ['chatter.timeline','chatter.followers.list'].includes(request?.intent) && request.params?.model==='account.move'
      && (request.params.res_id ?? request.params.record_id)===journalSave.createdId;
    if (ownedMutation && request.intent === 'api.data') journalSave.createAttempted = true;
    if (!draft && !roleAuthorityRead && !detailRead && !certificateRead && !ownedMutation && !ownedRead && !permitsInventoryRequest(req.method(), pathname, body, false)) {
      report.blocked.push({intent: request?.intent || pathname, ...(journalSave.enabled && request?.params?.model==='account.move' ? {params:request.params} : {})});
      return route.abort();
    }
    await route.continue();
  });
  page.on('response', async response => {
    let request; try { const body = response.request().postDataJSON(); request = body?.params?.intent ? body.params : body; } catch {}
    if (['journal-role','journal-save'].includes(scope) && request?.intent === 'api.data'
      && request.params?.op === 'read' && request.params?.model === 'account.move.line') {
      try {
        const payload = await response.json();
        (report.childReads ||= []).push({params:request.params,httpStatus:response.status(),ok:payload.ok,error:payload.error,
          records:(payload.data?.records || []).map(row=>({id:row.id,fields:Object.keys(row)}))});
      } catch { report.childReadCaptureIncomplete = true; }
    }
    if (!['system.init', 'api.onchange'].includes(request?.intent)) return;
    try {
      const payload = await response.json();
      if (request.intent === 'system.init') {
        init = payload.data;
        if (['journal-role','journal-save'].includes(scope)) journalTransport = {url:response.url(), headers:Object.fromEntries(
          Object.entries(await response.request().allHeaders()).filter(([key])=>/^(authorization|content-type)$|^x-/i.test(key)))};
      }
      else if (request.params.feedback_evaluation) report.feedback.push({model: request.params.model, ok: payload.ok, data: payload.data});
      else if (request.params.child_initialization) report.childInitializations.push({params: request.params, httpStatus: response.status(), ok: payload.ok, data: payload.data, error: payload.error});

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
  if (journalSave.enabled) {
    assert.equal(init.user.id,Number(process.env.SC_FEEDBACK_EXPECTED_UID || 40));
    assert.equal(init.user.company_id,1);
    report.actor.identityVerified=true;
  }
  if (scope === 'native-child') {
    const model = 'res.partner';
    const candidateIndex = fs.readFileSync('frontend/apps/web/dist-dev/index.html', 'utf8');
    const expectedEntries = [...candidateIndex.matchAll(/<script[^>]*src="([^"]*assets\/[^"]+)"/g)].map(match => new URL(match[1], base).pathname);
    const servedEntries = await page.locator('script[src]').evaluateAll(nodes => nodes.map(node => new URL(node.src).pathname).filter(path => path.includes('/assets/')));
    assert(expectedEntries.length > 0 && expectedEntries.every(path => servedEntries.includes(path)), 'namespace frontend differs from candidate build');
    report.frontendEntries = servedEntries;
    const node = leaves.find(item => item.meta?.model === model && item.meta?.route?.startsWith('/'));
    assert(node, 'native contact entry missing');
    const item = { model, field: 'child_ids', route: node.meta.route, passed: false };
    report.cases.push(item);
    await page.goto(base + node.meta.route, {waitUntil: 'domcontentloaded'});
    await page.getByRole('button', {name: /^(新建|新增|创建)$/}).first().click();
    const name = page.locator('[data-field-name="name"] input:visible').first();
    await name.waitFor({state: 'visible', timeout: 45000});
    const [onchangeResponse] = await Promise.all([
      page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === 'api.onchange' && request.params?.model === model && !request.params?.feedback_evaluation
          && !request.params?.res_id && request.params?.changed_fields?.includes('name')
          && request.params?.values?.name === '原生子表草稿验证（不保存）';
      }, {timeout: 20000}),
      (async () => { await name.fill('原生子表草稿验证（不保存）'); await name.blur(); })(),
    ]);
    const onchange = await onchangeResponse.json();
    report.onchanges.push({httpStatus: onchangeResponse.status(), ok: onchange.ok, error: onchange.error});
    assert(onchangeResponse.ok() && onchange.ok === true, 'native onchange did not succeed');
    item.before = await page.locator('body').innerText();
    await page.screenshot({path: `${root}/before-child.png`});
    assert(!/页面加载失败|ContractGapError|字段联动失败|字段联动声明不完整/.test(item.before));
    const collection = page.locator('[data-field-name="child_ids"]').first();
    await collection.waitFor({state: 'visible', timeout: 20000});
    item.collection = await collection.innerText();
    const counter = collection.locator('[data-row-count]').first();
    const beforeCount = Number(await counter.getAttribute('data-row-count'));
    assert(Number.isSafeInteger(beforeCount) && beforeCount >= 0);
    await collection.getByRole('button', {name: /新增|添加/}).first().click();
    await page.waitForFunction(({selector, expected}) => {
      const node = document.querySelector(selector)?.querySelector('[data-row-count]');
      return Number(node?.getAttribute('data-row-count')) === expected;
    }, {selector: '[data-field-name="child_ids"]', expected: beforeCount + 1});
    item.beforeCount = beforeCount;
    item.afterCount = Number(await counter.getAttribute('data-row-count'));
    item.after = await page.locator('body').innerText();
    item.inputs = await collection.locator('input:visible, textarea:visible').count();
    await page.screenshot({path: `${root}/after-child.png`});
    assert(item.inputs > 0, 'native child draft has no editable input');
    assert(!/页面加载失败|ContractGapError|字段联动失败|字段联动声明不完整/.test(item.after));
    assert.equal(report.blocked.length, 0);
    assert(report.onchanges.length > 0 && report.onchanges.every(result => result.ok === true), 'native onchange evidence missing or failed');
    item.passed = true;
  }
  if (journalSave.enabled && actor==='sc_demo_accounting_user') {
    await saveClerkJournal({page,base,root,report,leaves,state:journalSave,api:journalApi});
  } else if (['journal-draft', 'journal-save'].includes(scope)) {
    const model = 'account.move';
    const candidateIndex = fs.readFileSync('frontend/apps/web/dist-dev/index.html', 'utf8');
    const expectedEntries = [...candidateIndex.matchAll(/<script[^>]*src="([^"]*assets\/[^"]+)"/g)].map(match => new URL(match[1], base).pathname);
    const servedEntries = await page.locator('script[src]').evaluateAll(nodes => nodes.map(node => new URL(node.src).pathname).filter(path => path.includes('/assets/')));
    assert(expectedEntries.length && expectedEntries.every(path => servedEntries.includes(path)), 'namespace frontend differs from candidate build');
    report.frontendEntries = servedEntries;
    const node = leaves.find(item => item.meta?.model === model && item.meta?.route?.startsWith('/')
      && new URL(item.meta.route, base).searchParams.get('menu_id') === '175');
    assert(node, 'fixed journal entry missing');
    const item = {model, field: 'line_ids', route: node.meta.route, passed: false};
    report.cases.push(item);
    const capture = async (response) => {
      let body; try { body = response.request().postDataJSON(); } catch { return; }
      const request = body?.params?.intent ? body.params : body;
      const accountRead = request?.intent === 'api.data' && request.params?.model === 'account.account' && request.params?.op === 'list';
      if (!accountRead && (request?.intent !== 'api.onchange' || !models.includes(request.params?.model) || request.params?.feedback_evaluation)) return;
      const payload = await response.json();
      return {httpStatus: response.status(), ok: payload.ok, params: request.params, data: payload.data, error: payload.error};
    };
    await page.goto(base + node.meta.route, {waitUntil: 'domcontentloaded'});
    const [initialResponse] = await Promise.all([
      page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === 'api.onchange' && request.params?.model === model && !request.params?.res_id && !request.params?.feedback_evaluation;
      }),
      page.getByRole('button', {name: /^(新建|新增|创建)$/}).first().click(),
    ]);
    const initial = await capture(initialResponse);
    report.onchanges.push(initial);
    assert(initial?.httpStatus === 200 && initial.ok === true, 'root initialization failed');
    const collection = page.locator('[data-field-name="line_ids"]').first();
    await collection.waitFor({state: 'visible', timeout: 45000});
    const counter = collection.locator('[data-row-count]').first();
    const beforeCount = Number(await counter.getAttribute('data-row-count'));
    assert(Number.isSafeInteger(beforeCount) && beforeCount >= 0);
    await page.screenshot({path: `${root}/before-line.png`});
    const [childResponse, lineResponse] = await Promise.all([
      page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === 'api.onchange' && request.params?.model === model && !request.params?.res_id
          && request.params?.child_initialization?.field === 'line_ids';
      }),
      page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === 'api.onchange' && request.params?.model === model && !request.params?.res_id
          && request.params?.changed_fields?.includes('line_ids') && Array.isArray(request.params?.values?.line_ids)
          && request.params.values.line_ids.some(command => Array.isArray(command) && command[0] === 0);
      }),
      collection.getByRole('button', {name: /新增|添加/}).first().click(),
    ]);
    const childInitialization = await capture(childResponse);
    report.onchanges.push(childInitialization);
    assert(childInitialization?.httpStatus === 200 && childInitialization.ok === true, 'native child initialization failed');
    const currency = childInitialization.data?.patch?.currency_id;
    assert(Array.isArray(currency) && Number.isSafeInteger(currency[0]) && currency[0] > 0, 'native child currency missing');
    const line = await capture(lineResponse);
    report.onchanges.push(line);
    const created = line.params.values.line_ids.filter(command => command[0] === 0);
    assert.equal(created.length, 1, 'fixed journal probe must contain exactly one new row');
    assert.deepEqual(created[0][2].currency_id, currency, 'next parent request must carry initialized child currency');
    item.initializedCurrencyId = currency[0];
    item.virtualKey = created[0][1];
    assert(line?.httpStatus === 200 && line.ok === true, 'new-line onchange failed');
    await page.waitForFunction(({expected}) => Number(document.querySelector('[data-field-name="line_ids"] [data-row-count]')?.getAttribute('data-row-count')) === expected,
      {expected: beforeCount + 1});
    item.beforeCount = beforeCount;
    item.afterCount = Number(await counter.getAttribute('data-row-count'));
    item.collection = await collection.innerText();
    item.inputs = await collection.locator('input:visible').count();
    await page.screenshot({path: `${root}/after-line.png`});
    assert(item.inputs > 0, 'journal line has no editable input');
    assert(!/页面加载失败|ContractGapError|字段联动失败|字段联动声明不完整/.test(await page.locator('body').innerText()));
    assert.equal(report.blocked.length, 0);
    // Query the actual selector; an unopened selector's placeholder is not data evidence.
    const accountInput = collection.locator('input[aria-label="科目"]:visible');
    const [accountResponse] = await Promise.all([
      page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === 'api.data' && request.params?.model === 'account.account' && request.params?.op === 'list';
      }),
      accountInput.click(),
    ]);
    const accountResult = await capture(accountResponse);
    item.accountQuery = accountResult;
    assert(accountResult.httpStatus === 200 && accountResult.ok === true, 'account selector query failed');
    const childCompany = childInitialization.data?.patch?.company_id;
    assert(Array.isArray(childCompany) && Number.isSafeInteger(childCompany[0]) && childCompany[0] > 0);
    assert.deepEqual(accountResult.params.domain, ['|', ['company_id', '=', false], ['company_id', 'parent_of', [childCompany[0]]],
      ['deprecated', '=', false], ['account_type', '!=', 'off_balance']], 'native account restrictions must reach actual query');
    // Inline cells use ScSelect (official TDesign rows), not ScRelationField's ARIA adapter.
    const options = page.locator('li.t-select-option:visible:not(.t-is-disabled)');
    const option = options.first();
    await option.waitFor({state: 'visible'});
    item.accountOptionLabel = (await option.innerText()).trim();
    const matchedAccounts = accountResult.data?.records?.filter(record => [record.display_name, record.name].includes(item.accountOptionLabel)) || [];
    assert.equal(matchedAccounts.length, 1, 'visible option must uniquely identify a returned account');
    const expectedAccountId = matchedAccounts[0].id;
    const [selectedResponse] = await Promise.all([
      page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === 'api.onchange' && request.params?.model === model
          && !request.params?.res_id && request.params?.changed_fields?.includes('line_ids')
          && request.params?.values?.line_ids?.some(command => command[0] === 0 && command[1] === item.virtualKey
            && (Array.isArray(command[2]?.account_id) ? command[2].account_id[0] : command[2]?.account_id) === expectedAccountId);
      }),
      option.click(),
    ]);
    item.accountSelection = await capture(selectedResponse);
    const selectedAccount = item.accountSelection.params.values.line_ids.find(command => command[0] === 0 && command[2]?.account_id)?.[2].account_id;
    item.selectedAccountId = Array.isArray(selectedAccount) ? selectedAccount[0] : selectedAccount;
    assert(accountResult.data?.records?.some(record => record.id === item.selectedAccountId), 'selected account must belong to returned options');
    assert(item.accountSelection.httpStatus === 200 && item.accountSelection.ok === true, 'selected account onchange failed');
    assert.equal(report.blocked.length, 0);
    await page.screenshot({path: `${root}/after-account-selection.png`});
    if (journalSave.enabled) {
      journalSave.companyId = childCompany[0]; journalSave.currencyId = currency[0];
      journalSave.userId=init.user.id; journalSave.date=initial.data?.patch?.date || initial.params.values.date;
      const journal = initial.data?.patch?.journal_id;
      assert(Array.isArray(journal) && journal[0] > 0); journalSave.journalId = journal[0];
      journalSave.accounts = accountResult.data.records.map(record => record.id);
      journalSave.rowKeys = [item.virtualKey];
      journalTransport = {url: accountResponse.url(), headers: Object.fromEntries(Object.entries(await accountResponse.request().allHeaders())
        .filter(([key]) => /^(authorization|content-type)$|^x-/i.test(key)))};
      assert.equal((await ownedJournalRows()).length, 0, 'marker already exists');
      const ref = page.locator('[data-field-name="ref"] input:visible').first();
      await ref.fill(journalSave.ref); await ref.blur();
      const waitLine = (predicate) => page.waitForResponse(response => {
        let body; try { body=response.request().postDataJSON(); } catch { return false; }
        const request=body?.params?.intent ? body.params : body;
        return request?.intent==='api.onchange' && request.params?.model===model && !request.params.res_id
          && request.params.changed_fields?.includes('line_ids') && predicate(request.params.values?.line_ids || []);
      });
      const setAmount = async (field, index, amount) => {
        const [response] = await Promise.all([
          waitLine(commands => Number(commands[index]?.[2]?.[field])===amount),
          (async () => { const input=collection.locator(`input[id$="-${field}-desktop"]`).nth(index);
            await input.fill(String(amount)); await input.blur(); })(),
        ]);
        const result=await capture(response); report.onchanges.push(result);
        assert.equal(result.ok,true, 'amount onchange failed');
      };
      await setAmount('debit',0,100);
      const [secondResponse] = await Promise.all([
        waitLine(commands => commands.filter(command => command[0]===0).length===2),
        collection.getByRole('button', {name:/新增|添加/}).first().click(),
      ]);
      const second=await capture(secondResponse); assert.equal(second.ok,true);
      const secondKey=second.params.values.line_ids[1][1]; journalSave.rowKeys.push(secondKey);
      const secondInput=collection.locator('input[aria-label="科目"]:visible').nth(1);
      const secondQuery=page.waitForResponse(response => {
        let body; try { body=response.request().postDataJSON(); } catch { return false; }
        const request=body?.params?.intent ? body.params : body;
        return request?.intent==='api.data' && request.params?.model==='account.account' && request.params?.op==='list';
      });
      await secondInput.click(); const secondOptions=await capture(await secondQuery); assert.equal(secondOptions.ok,true);
      const nextOption=page.locator('li.t-select-option:visible:not(.t-is-disabled)').nth(1);
      await nextOption.waitFor({state:'visible'});
      const nextLabel=(await nextOption.innerText()).trim();
      const nextRecords=secondOptions.data.records.filter(record => [record.name,record.display_name].includes(nextLabel));
      assert.equal(nextRecords.length,1); const nextId=nextRecords[0].id;
      assert.notEqual(nextId,item.selectedAccountId);
      const selected=waitLine(commands => commands.some(command => command[1]===secondKey &&
        (Array.isArray(command[2].account_id) ? command[2].account_id[0] : command[2].account_id)===nextId));
      await nextOption.click(); assert.equal((await capture(await selected)).ok,true);
      await setAmount('credit',1,100);
      journalSave.accounts=[item.selectedAccountId,nextId];
      assert.deepEqual({user:journalSave.userId,company:journalSave.companyId,journal:journalSave.journalId,
        currency:journalSave.currencyId,accounts:journalSave.accounts}, {user:Number(process.env.SC_FEEDBACK_EXPECTED_UID || 40),company:1,journal:3,currency:6,accounts:[49,48]}, 'recovery scope mismatch');
      journalSave.ready=true;
      const createResponse=page.waitForResponse(response => {
        let body; try { body=response.request().postDataJSON(); } catch { return false; }
        const request=body?.params?.intent ? body.params : body;
        return request?.intent==='api.data' && request.params?.op==='create' && request.params?.model===model;
      }, {timeout:20000});
      await page.getByRole('button',{name:'保存',exact:true}).click();
      const saved=await createResponse; const savedBody=await saved.json();
      report.saved={httpStatus:saved.status(),ok:savedBody.ok,data:savedBody.data,error:savedBody.error};
      assert.equal(savedBody.ok,true,'draft save failed');
      journalSave.createdId=savedBody.data.id; assert(Number.isSafeInteger(journalSave.createdId) && journalSave.createdId>0);
      fs.writeFileSync(`${root}/created-receipt.json`, JSON.stringify({head:report.head,ref:journalSave.ref,actor,uid:init.user.id,
        record_id:journalSave.createdId,line_ids:[]}));
      await page.waitForURL(url => url.pathname.endsWith('/'+journalSave.createdId),{timeout:20000});
      await page.reload({waitUntil:'domcontentloaded'});
      const reloadedRef = page.locator('[data-field-name="ref"] input:visible').first();
      await reloadedRef.waitFor({state:'visible'});
      await page.waitForFunction(ref => document.querySelector('[data-field-name="ref"] input')?.value === ref,journalSave.ref);
      item.reloadedRef = await reloadedRef.inputValue();
      assert.equal(item.reloadedRef,journalSave.ref,'reloaded field must contain saved reference');
      const rows=await ownedJournalRows(); assert.equal(rows.length,1);
      assert.equal(rows[0].id,journalSave.createdId); assert.equal(rows[0].state,'draft');
      const relationId = value => Array.isArray(value) ? value[0] : value;
      assert.equal(relationId(rows[0].company_id),journalSave.companyId);
      assert.equal(relationId(rows[0].journal_id),journalSave.journalId);
      assert.equal(relationId(rows[0].currency_id),journalSave.currencyId);
      const lines=await journalApi('api.data',{op:'read',model:'account.move.line',ids:rows[0].line_ids,
        fields:['id','move_id','account_id','currency_id','debit','credit','balance']});
      assert.equal(lines.payload.ok,true); assert.equal(lines.payload.data.records.length,2);
      assert.equal(lines.payload.data.records.reduce((sum,row)=>sum+row.balance,0),0);
      assert.equal(lines.payload.data.records.reduce((sum,row)=>sum+row.debit,0),100);
      assert.equal(lines.payload.data.records.reduce((sum,row)=>sum+row.credit,0),100);
      for (const row of lines.payload.data.records) {
        assert.equal(relationId(row.move_id),journalSave.createdId);
        assert.equal(relationId(row.currency_id),journalSave.currencyId);
        const debit=row.debit===100; assert.equal(row.debit,debit?100:0); assert.equal(row.credit,debit?0:100);
        assert.equal(relationId(row.account_id),journalSave.accounts[debit?0:1]);
      }
      assert.equal(report.blocked.length,0);
      report.readback={record:rows[0],lines:lines.payload.data.records};
      fs.writeFileSync(`${root}/created-receipt.json`, JSON.stringify({head:report.head,ref:journalSave.ref,actor,uid:init.user.id,
        record_id:journalSave.createdId,line_ids:lines.payload.data.records.map(row=>row.id)}));
      await page.screenshot({path:`${root}/saved-reloaded.png`});
    }
    item.passed = true;


  }
  if (scope === 'payroll') {
    const model = 'sc.hr.payroll.document';
    for (const menu of ['673', '695', '706']) {
      const node = leaves.find(n => n.meta?.model === model && new URL(n.meta.route, base).searchParams.get('menu_id') === menu);
      assert(node?.meta?.route?.startsWith('/'), 'payroll entry missing');
      const responseFor = (intent, op) => page.waitForResponse(response => {
        let body; try { body = response.request().postDataJSON(); } catch { return false; }
        const request = body?.params?.intent ? body.params : body;
        return request?.intent === intent && request.params?.op === op &&
          (intent === 'ui.contract.v2' ? String(request.params.menu_id) === menu : request.params.model === model);
      }, {timeout: 45000});
      const contractResponse = responseFor('ui.contract.v2', 'action_open');
      const dataResponse = responseFor('api.data', 'list');
      await page.goto(base + node.meta.route, {waitUntil: 'domcontentloaded'});
      const contract = await (await contractResponse).json();
      const transport = await dataResponse;
      const data = await transport.json();
      assert.equal(contract.ok, true); assert.equal(data.ok, true);
      const profile = contract.data.layoutContract.listProfile;
      const columns = profile.fact_columns || profile.columns;
      const records = data.data.records;
      assert(Array.isArray(records));
      await page.waitForFunction(() => ['ok', 'empty'].includes(document.querySelector('[data-semantic-component="ActionView"]')?.getAttribute('data-collection-state')));
      const item = {menu, columns, recordCount: records.length, passed: false}; report.cases.push(item);
      if (menu === '673') {
        for (const field of ['fact_type', 'payroll_display_period', 'payroll_display_amount']) assert(columns.includes(field));
        for (const field of ['period_year', 'period_month', 'net_salary']) assert(!columns.includes(field));
        assert(records.length, 'mixed payroll demo sample missing');
        const original = transport.request().postDataJSON();
        const request = original?.params?.intent ? original.params : original;
        const sourceRequest = {...request, params: {...request.params, op: 'read', ids: records.map(row => row.id),
          fields: ['id', 'document_no', 'fact_type', 'period_year', 'period_month', 'net_salary', 'occurrence_date', 'amount', 'currency_id', 'payroll_display_period', 'payroll_display_amount']}};
        const headers = Object.fromEntries(Object.entries(await transport.request().allHeaders()).filter(([key]) => /^(authorization|content-type)$|^x-/i.test(key)));
        const source = await page.evaluate(async ({url, headers, body}) => {
          const response = await fetch(url, {method: 'POST', headers, body: JSON.stringify(body)});
          return {status: response.status, payload: await response.json()};
        }, {url: transport.url(), headers, body: original?.params?.intent ? {...original, params: sourceRequest} : sourceRequest});
        assert.equal(source.status, 200); assert.equal(source.payload.ok, true);
        const sourceRows = source.payload.data.records;
        assert.equal(sourceRows.length, records.length);
        item.facts = sourceRows.map(row => {
          assert(['salary_registration', 'subsidy', 'bonus'].includes(row.fact_type));
          const amount = row.fact_type === 'salary_registration' ? row.net_salary : row.amount;
          const period = row.fact_type === 'salary_registration'
            ? (row.period_year && row.period_month ? `${String(row.period_year).padStart(4, '0')}-${String(row.period_month).padStart(2, '0')}` : false)
            : row.occurrence_date;
          assert.equal(row.payroll_display_amount, amount);
          assert.equal(row.payroll_display_period, period);
          const listed = records.find(record => record.id === row.id);
          assert.equal(listed.payroll_display_amount, amount);
          assert.equal(listed.payroll_display_period, period);
          return {id: row.id, documentNo: row.document_no, type: row.fact_type, amount, period, currency: row.currency_id};
        });
        item.missingDemoTypes = ['salary_registration', 'subsidy', 'bonus'].filter(type => !item.facts.some(row => row.type === type));
        assert(item.facts.some(row => row.type === 'bonus' && row.amount > 0), 'original nonzero bonus regression sample required');
        for (const width of [1440, 390]) {
          await page.setViewportSize({width, height: width === 390 ? 844 : 960});
          const body = await page.locator('body').innerText();
          assert(!body.includes('实发工资') && !body.includes('年度') && !body.includes('月份'), 'salary-only columns leak into mixed overview');
          for (const fact of item.facts) {
            const row = page.locator(`[data-record-key="${fact.id}"]`).filter({visible: true});
            assert.equal(await row.count(), 1, 'visible payroll row/card must be unique');
            const content = await row.innerText();
            assert(content.includes({'salary_registration': '工资登记', 'subsidy': '补助', 'bonus': '奖金'}[fact.type]));
            if (fact.period) assert(content.includes(fact.period), 'period missing from row/card');
            assert(content.includes(Number(fact.amount).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})), 'source amount missing from row/card');
          }
          await page.screenshot({path: `${root}/673-${width}.png`});
        }
      } else {
        assert(!columns.includes('payroll_display_amount'), 'mixed display leaked to sibling entry');
        await page.setViewportSize({width: 1440, height: 960});
        await page.screenshot({path: `${root}/${menu}-desktop.png`});
      }
      item.passed = true;
    }
    assert.equal(report.blocked.length, 0);
  }
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
  if (scope === 'journal-role') {
      const expectedUid = {demo_role_finance:47,demo_role_project_read:41,sc_demo_accounting_manager:7}[actor]
        ?? (['sc_demo_accounting_read','sc_demo_accounting_user'].includes(actor) ? Number(process.env.SC_FEEDBACK_EXPECTED_UID) : undefined);
      assert(Number.isSafeInteger(expectedUid) && expectedUid > 0, 'undeclared actor or missing seed identity receipt');
      assert.equal(init.user.id,expectedUid,'authenticated actor differs from registered demo identity');
      assert.equal(init.user.company_id,1,'unexpected actor company');
      report.actor.identityVerified = true;
      const candidateIndex = fs.readFileSync('frontend/apps/web/dist-dev/index.html','utf8');
      const expectedEntries = [...candidateIndex.matchAll(/<script[^>]*src="([^"]*assets\/[^"]+)"/g)].map(match=>new URL(match[1],base).pathname);
      const servedEntries = await page.locator('script[src]').evaluateAll(nodes=>nodes.map(node=>new URL(node.src).pathname).filter(path=>path.includes('/assets/')));
      assert(expectedEntries.length && expectedEntries.every(path=>servedEntries.includes(path)),'namespace frontend differs from candidate build');
      report.frontendEntries = servedEntries;
      if (accountingActor) {
        const models = ['account.move','account.move.line','account.account','account.journal',
          'account.analytic.account','account.analytic.distribution.model'];
        const entries = leaves.filter(n=>models.includes(n.meta?.model) && n.meta?.route?.startsWith('/a/'));
        assert.equal(entries.length,6,'accounting must expose exactly six declared entries');
        assert.deepEqual([...new Set(entries.map(n=>n.meta.model))].sort(),[...models].sort());
        for (const entry of entries) {
          const route = new URL(entry.meta.route,base);
          journalRolePairs.add(`${Number(route.pathname.split('/').at(-1))}/${Number(route.searchParams.get('menu_id'))}`);
        }
        assert.equal(journalRolePairs.size,6);
        if (mobile) {
          await (mobileRoot ? inspectMobileJournalRoots : inspectMobileAccounting)({page, base, root, actor, accountingReadonly, entries, report, journalApi,
            setDetailId: id => { journalDetailId = id; }});
        } else {
        for (const entry of entries) {
          const route = new URL(entry.meta.route,base);
          const menu = route.searchParams.get('menu_id');
          const action = Number(route.pathname.split('/').at(-1));
          const allowed = await journalApi('route.authority.validate',{action_id:action,menu_id:Number(menu)});
          assert.equal(allowed.status,200); assert.equal(allowed.payload.ok,true);
          assert.equal(allowed.payload.data.allowed,true);
          const pending = page.waitForResponse(response=>{
            let body; try {body=response.request().postDataJSON();} catch {return false;}
            const request=body?.params?.intent ? body.params : body;
            return request?.intent==='ui.contract.v2' && request.params?.op==='action_open'
              && String(request.params.menu_id)===menu;
          });
          await page.goto(base+entry.meta.route,{waitUntil:'domcontentloaded'});
          const response = await pending;
          assert.equal(response.status(),200); const payload = await response.json();
          assert.equal(payload.ok,true);
          await page.waitForFunction(()=>['ok','empty'].includes(document.querySelector('[data-semantic-component="ActionView"]')?.getAttribute('data-collection-state')));
          if (entry.meta.model === 'account.move') {
            const headers = page.locator('[data-semantic-component="ActionView"] thead th');
            report.journalHeaders = (await headers.allTextContents()).map(text=>text.trim());
            assert.equal(report.journalHeaders.filter(text=>text==='凭证编号').length,1);
            assert(!report.journalHeaders.includes('数量'));
            await headers.getByText('凭证编号',{exact:true}).waitFor({state:'visible'});
            report.journalNumberLabel = '凭证编号';
          }
          report.cases.push({model:entry.meta.model,menu,route:entry.meta.route,navigationPublished:true,
            collectionState:await page.locator('[data-semantic-component="ActionView"]').getAttribute('data-collection-state'),passed:true});
          await page.screenshot({path:`${root}/${actor}-${menu}.png`});
          if (entry.meta.model === 'account.move') {
            report.journalStates=[];
            for (const journalState of ['draft','posted']) {
            const selected = await journalApi('api.data',{op:'list',model:'account.move',
              domain:[['state','=',journalState],['move_type','=','entry'],['name','!=','/'],['name','!=',false]],
              fields:['id','name','ref','state','move_type','company_id','journal_id','line_ids','write_date'],limit:5});
            assert.equal(selected.status,200); assert.equal(selected.payload.ok,true);
            const record = selected.payload.data.records.find(row=>row.name && row.name !== '/');
            if (!record && journalState === 'posted') {
              report.journalStates.push({state:journalState,outcome:'demo_gap',reason:'No named posted journal entry available to the accounting manager',passed:false});
              continue;
            }
            assert(record,'demo gap: no named saved draft journal entry');
            assert.equal(record.state,journalState);
            assert.equal(record.move_type,'entry');
            journalDetailId = record.id;
            assert(Number.isSafeInteger(journalDetailId) && journalDetailId>0);
            const relationId = value=>Array.isArray(value) ? value[0] : value;
            assert.equal(relationId(record.company_id),1);
            assert(record.line_ids.length>0,'demo draft must have journal lines');
            const waitForm = ()=>page.waitForResponse(response=>{
              let body; try {body=response.request().postDataJSON();} catch {return false;}
              const request=body?.params?.intent ? body.params : body;
              return request?.intent==='ui.contract.v2' && request.params?.op==='action_open'
                && request.params?.view_type==='form' && Number(request.params?.action_id)===action
                && Number(request.params?.menu_id)===Number(menu) && Number(request.params?.record_id)===record.id;
            });
            const open = waitForm();
            if (journalState === 'draft') {
              await page.locator('[data-semantic-component="ActionView"]').getByRole('button',{name:record.name,exact:true}).click();
            } else {
              await page.goto(`${base}/f/account.move/${record.id}?menu_id=${menu}&action_id=${action}`,{waitUntil:'domcontentloaded'});
            }
            let detailContract;
            const validateForm = async pending=>{
              const response=await pending; assert.equal(response.status(),200);
              const payload=await response.json(); assert.equal(payload.ok,true);
              await page.waitForFunction(id=>{
                const form=document.querySelector('[data-semantic-component="ContractFormPage"]');
                return form?.getAttribute('data-state')==='ok' && form?.getAttribute('data-form-model')==='account.move'
                  && form?.getAttribute('data-form-record')===String(id)
                  && form?.getAttribute('data-v2-shadow-error')==='-';
              },record.id);
              await page.locator('[data-field-name="line_ids"]').first().waitFor({state:'visible'});
              await page.waitForFunction(expected=>Number(document.querySelector('[data-field-name="line_ids"] [data-row-count]')?.getAttribute('data-row-count'))===expected,record.line_ids.length);
              detailContract=payload.data;
              return payload.data.statusContract.globalStatus;
            };
            const status = await validateForm(open);
            const reload=waitForm(); await page.reload({waitUntil:'domcontentloaded'});
            const reloadedStatus=await validateForm(reload);
            assert.equal(status.effectiveRecordCapabilities.write,!accountingReadonly);
            assert.equal(reloadedStatus.effectiveRecordCapabilities.write,!accountingReadonly);
            const lineRead=await journalApi('api.data',{op:'read',model:'account.move.line',ids:record.line_ids,
              fields:['id','move_id','name','account_id','debit','credit','analytic_distribution','write_date']});
            assert.equal(lineRead.status,200); assert.equal(lineRead.payload.ok,true);
            const lines=lineRead.payload.data.records;
            assert.deepEqual(lines.map(line=>line.id).sort((a,b)=>a-b),[...record.line_ids].sort((a,b)=>a-b));
            const lineComparisons=[];
            const readonlyTable=page.locator('[data-field-name="line_ids"] [data-readonly-relation] [data-detail-collection-content="desktop-table"]');
            let readonlyHeaders=[];
            if (journalState === 'posted' || accountingReadonly) {
              await readonlyTable.waitFor({state:'visible'});
              readonlyHeaders=(await readonlyTable.locator('thead th').allTextContents()).map(text=>text.trim());
              for (const label of ['科目','借项','贷项']) assert.equal(readonlyHeaders.filter(text=>text===label).length,1);
              assert.equal(new Set(lines.map(line=>line.account_id[1])).size,lines.length,'readonly sample needs unique account labels for row binding');
              assert.equal(await readonlyTable.locator('tbody tr').count(),lines.length);
            }
            for (const line of lines) {
              assert.equal(relationId(line.move_id),record.id);
              const cell=field=>page.locator(`#o2m-control-line_ids-o2m_id_${line.id}-${field}-desktop`);
              const values={};
              const readonlyRow=journalState === 'posted' || accountingReadonly
                ? readonlyTable.locator('tbody tr').filter({has:page.getByText(line.account_id[1],{exact:true})}) : null;
              if (readonlyRow) assert.equal(await readonlyRow.count(),1,'readonly line account must identify one actual row');
              for (const field of ['debit','credit']) {
                values[field]=readonlyRow
                  ? (await readonlyRow.locator('td').nth(readonlyHeaders.indexOf(field==='debit' ? '借项' : '贷项')).innerText()).trim()
                  : await cell(field).inputValue();
                assert.match(values[field],/^-?\d+(?:\.\d+)?$/,'amount must be an explicit numeric UI value');
                assert.equal(Number(values[field]),line[field],`line ${line.id} ${field} differs from ORM`);
              }
              values.account=readonlyRow
                ? (await readonlyRow.locator('td').nth(readonlyHeaders.indexOf('科目')).innerText()).trim()
                : await cell('account_id').inputValue();
              assert.equal(values.account,line.account_id[1],`line ${line.id} account label differs from ORM`);
              if (readonlyRow) {
                values.expansions=[];
                for (const [field,label,expected] of [['account_id','科目',line.account_id[1]],['name','标签',line.name]]) {
                  if (typeof expected !== 'string' || !expected) continue;
                  const trigger=readonlyRow.getByRole('button',{name:`查看完整${label}：${expected}`,exact:true});
                  const style=await trigger.evaluate(button=>{
                    const css=getComputedStyle(button), rect=button.getBoundingClientRect();
                    const content=button.querySelector('.sc-btn__content');
                    return {border:css.borderTopWidth,background:css.backgroundColor,whiteSpace:css.whiteSpace,
                      height:rect.height,width:rect.width,cellWidth:button.closest('td').getBoundingClientRect().width,
                      contentWhiteSpace:content && getComputedStyle(content).whiteSpace,type:button.type};
                  });
                  assert.equal(style.border,'0px'); assert.equal(style.background,'rgba(0, 0, 0, 0)');
                  assert.equal(style.whiteSpace,'nowrap'); assert.equal(style.contentWhiteSpace,'nowrap');
                  assert.equal(style.type,'button'); assert(style.height>0 && style.height<60 && style.width<=style.cellWidth);
                  assert.equal(await trigger.getAttribute('title'),null,'explicit popup should not compete with a tooltip');
                  await trigger.focus(); await trigger.press('Enter');
                  const full=page.locator('.o2m-readonly-full-value:visible');
                  await full.waitFor({state:'visible'}); assert.equal(await full.innerText(),expected);
                  await page.waitForFunction(()=>{
                    let element=document.querySelector('.o2m-readonly-full-value');
                    if (!element) return false;
                    for (;element;element=element.parentElement) if (Number(getComputedStyle(element).opacity)<1) return false;
                    return true;
                  });
                  await page.screenshot({path:`${root}/${actor}-${journalState}-${line.id}-${field}-expanded.png`});
                  await trigger.click(); await full.waitFor({state:'hidden'});
                  values.expansions.push({field,text:expected,style,keyboardOpened:true,closed:true});
                }
              }
              lineComparisons.push({id:line.id,account:line.account_id,debit:line.debit,credit:line.credit,ui:values,passed:true});
            }
            const linesAfter=await journalApi('api.data',{op:'read',model:'account.move.line',ids:record.line_ids,
              fields:['id','move_id','name','account_id','debit','credit','analytic_distribution','write_date']});
            assert.equal(linesAfter.status,200); assert.equal(linesAfter.payload.ok,true);
            assert.deepEqual(linesAfter.payload.data.records,lines,'readonly inspection must preserve journal lines');
            const readback=await journalApi('api.data',{op:'read',model:'account.move',ids:[record.id],
              fields:['id','name','ref','state','move_type','company_id','journal_id','line_ids','write_date']});
            assert.equal(readback.payload.ok,true);
            assert.equal(readback.payload.data.records.length,1);
            const savedFields=['id','name','ref','state','move_type','company_id','journal_id','line_ids','write_date'];
            const facts=row=>Object.fromEntries(savedFields.map(key=>[key,row[key]]));
            assert.deepEqual(facts(readback.payload.data.records[0]),facts(record),'readonly detail must preserve saved record');
            const detail={record,status,reloadedStatus,lineComparisons,readback:facts(readback.payload.data.records[0]),comparisonPassed:true,
              visibleLineCount:Number(await page.locator('[data-field-name="line_ids"] [data-row-count]').first().getAttribute('data-row-count')),
              lineRegionText:await page.locator('[data-field-name="line_ids"]').first().innerText(),route:page.url(),
              visibleButtons:await page.locator('[data-semantic-component="ContractFormPage"] button:visible').allTextContents(),passed:true};
            const form=page.locator('[data-semantic-component="ContractFormPage"]');
            if (accountingReadonly) {
              assert.equal(await form.getByRole('button',{name:'保存',exact:true}).count(),0);
              assert.equal(await form.getByRole('button',{name:'过账',exact:true}).count(),0);
            } else await form.getByRole('button',{name:'保存',exact:true}).waitFor({state:'visible'});
            assert.equal(await form.getByRole('button',{name:'保存草稿',exact:true}).count(),0);
            const publishedColumns=journalLineColumns(detailContract);
            const analyticDeclared=publishedColumns.includes('analytic_distribution');
            assert.equal(analyticDeclared,!accountingReadonly,'native role column membership differs from declared role baseline');
            detail.analyticPresentation={declared:analyticDeclared,publishedColumns};
            if (!analyticDeclared) assert(!readonlyHeaders.includes('分析分配'),'undeclared allocation must not leak through a generic column');
            const nativeCells=page.locator('[data-field-name="line_ids"] [data-detail-collection-content="desktop-table"] [data-semantic-component="NativeWeightedRelationDisplay"]');
            assert.equal(await nativeCells.count(),analyticDeclared ? lines.length : 0);
            if (analyticDeclared) await page.waitForFunction(() => {
              const cells=[...document.querySelectorAll('[data-field-name="line_ids"] [data-detail-collection-content="desktop-table"] [data-semantic-component="NativeWeightedRelationDisplay"]')];
              return cells.length>0 && cells.every(cell=>cell.getAttribute('data-display-state')==='ready');
            });
            assert.equal(await page.locator('input[id$="-analytic_distribution-desktop"]').count(),0);
            if (journalState === 'posted' && analyticDeclared) {
              assert.equal(readonlyHeaders.filter(text=>text==='分析分配').length,1);
              for (const line of lines) {
                const distribution=line.analytic_distribution;
                assert(distribution===false || distribution===null || (typeof distribution==='object' && !Array.isArray(distribution)), 'expected native distribution object');
                assert(distribution && Object.keys(distribution).length===1,'demo should retain one native analytic allocation');
                const [key,percentage]=Object.entries(distribution)[0];
                assert.match(key,/^[1-9]\d*$/); assert.equal(percentage,100);
                const accountId=Number(key);
                const named=await journalApi('api.data',{op:'read',model:'account.analytic.account',ids:[accountId],fields:['id','display_name'],context:{allowed_company_ids:[1]}});
                assert.equal(named.status,200); assert.equal(named.payload.ok,true);
                assert.equal(named.payload.data.records.length,1); assert.equal(named.payload.data.records[0].id,accountId);
                const expected=`${named.payload.data.records[0].display_name}：100%`;
                const row=readonlyTable.locator('tbody tr').filter({has:page.getByText(line.account_id[1],{exact:true})});
                const cell=row.locator('td').nth(readonlyHeaders.indexOf('分析分配'));
                await cell.locator('[data-semantic-component="NativeWeightedRelationDisplay"][data-display-state="ready"]').waitFor({state:'visible'});
                const actual=(await cell.innerText()).trim();
                assert.equal(actual,expected); assert.equal(await cell.locator('input').count(),0);
                const expand=cell.getByRole('button',{name:`查看完整内容：${expected}`,exact:true});
                const compact = await expand.evaluate((button) => {
                  const content = button.querySelector('.sc-btn__content');
                  return { whiteSpace: getComputedStyle(button).whiteSpace,
                    height: button.getBoundingClientRect().height,
                    contentHeight: content?.getBoundingClientRect().height };
                });
                assert(compact.whiteSpace === 'nowrap' && compact.height < 60 && compact.contentHeight < 60,
                  `native allocation must remain compact: ${JSON.stringify(compact)}`);
                await expand.click();
                const full=page.locator('[data-native-weighted-full-value]').filter({hasText:expected});
                await full.waitFor({state:'visible'}); assert.equal((await full.innerText()).trim(),expected);
                await page.screenshot({path:`${root}/${actor}-analytic-full-value.png`});
                await expand.click();
                await full.waitFor({state:'hidden'});

                (detail.structuredValues ??= []).push({lineId:line.id,raw:distribution,display:actual,
                  compact,representation:'native_weighted_relation',nativeAnalyticReadonlyAccepted:true,nativeAnalyticEditingAccepted:false});
              }
              assert(!(await readonlyTable.innerText()).includes('[object Object]'));
              const right=readonlyTable.getByRole('button',{name:'查看右侧列',exact:true});
              if (await right.count() && await right.isEnabled()) await right.click();

              assert.equal(await page.locator('[data-semantic-component="ContractFormPage"]').getByRole('button',{name:'过账',exact:true}).count(),0,'posted journal must not expose posting again');
            }
            detail.lineRegionText=await page.locator('[data-field-name="line_ids"]').first().innerText();
            report.journalStates.push({state:journalState,outcome:'verified',...detail});
            if (journalState === 'draft') report.journalDetail=detail;
            await page.screenshot({path:`${root}/${actor}-saved-${journalState}-detail.png`});
            }
            report.journalStateCoverageComplete=report.journalStates.length===2 && report.journalStates.every(item=>item.outcome==='verified' && item.passed);
          }
        }
        const lineEntry=entries.find(entry=>entry.meta.model==='account.move.line');
        const lineRoute=new URL(lineEntry.meta.route,base);
        report.lineRootStates=[];
        for (const source of report.journalStates) {
        const lineId=source.record.line_ids[0];
        const sample=source.structuredValues?.find(item=>item.lineId===lineId);
        if (source.state==='posted' && source.analyticPresentation.declared) assert(sample,'posted root must retain authorized allocation comparison');
        const lineFields=['id','move_id','parent_state','analytic_distribution','write_date'];
        const before=await journalApi('api.data',{op:'read',model:'account.move.line',ids:[lineId],fields:lineFields});
        assert.equal(before.status,200); assert.equal(before.payload.ok,true);
        assert.equal(before.payload.data.records.length,1); assert.equal(before.payload.data.records[0].id,lineId);
        assert.equal(before.payload.data.records[0].parent_state,source.state);
        assert.equal(before.payload.data.records[0].move_id[0],source.record.id);
        const rootResponse=page.waitForResponse(response=>{
          let body; try {body=response.request().postDataJSON();} catch {return false;}
          const request=body?.params?.intent ? body.params : body;
          return request?.intent==='ui.contract.v2' && request.params?.op==='action_open' && request.params?.view_type==='form'
            && Number(request.params?.action_id)===Number(lineRoute.pathname.split('/').at(-1))
            && Number(request.params?.record_id)===lineId && Number(request.params?.menu_id)===Number(lineRoute.searchParams.get('menu_id'));
        });
        await page.goto(`${base}/f/account.move.line/${lineId}?menu_id=${lineRoute.searchParams.get('menu_id')}&action_id=${lineRoute.pathname.split('/').at(-1)}`,{waitUntil:'domcontentloaded'});
        await page.waitForFunction(id=>{
          const form=document.querySelector('[data-semantic-component="ContractFormPage"]');
          return form?.getAttribute('data-state')==='ok' && form?.getAttribute('data-form-model')==='account.move.line'
            && form?.getAttribute('data-form-record')===String(id);
        },lineId);
        const rootTransport=await rootResponse; assert.equal(rootTransport.status(),200);
        const rootPayload=await rootTransport.json(); assert.equal(rootPayload.ok,true);
        const rootAnalyticDeclared=journalFormWidgets(rootPayload.data).some(widget=>widget.fieldCode==='analytic_distribution');
        assert.equal(rootAnalyticDeclared,!accountingReadonly);
        const lineForm=page.locator('[data-semantic-component="ContractFormPage"]');
        if (accountingReadonly) assert.equal(await lineForm.getByRole('button',{name:'保存',exact:true}).count(),0);
        else await lineForm.getByRole('button',{name:'保存',exact:true}).waitFor({state:'visible'});
        assert.equal(await lineForm.getByRole('button',{name:'保存草稿',exact:true}).count(),0);
        const rootTitle=(await lineForm.locator('h1').first().innerText()).trim();
        assert(rootTitle && rootTitle !== 'false','empty record name must not render a boolean title');
        assert(!(await page.title()).startsWith('false'),'document title must not expose boolean name');
        const rootField=page.locator('[data-field-name="analytic_distribution"]');
        const rootDisplay=rootField.locator('[data-semantic-component="NativeWeightedRelationDisplay"]');
        if (rootAnalyticDeclared) await rootDisplay.waitFor({state:'visible'});
        else assert.equal(await rootField.count(),0,'undeclared analytic field must stay absent');
        if (rootAnalyticDeclared) await page.waitForFunction(()=>document.querySelector('[data-field-name="analytic_distribution"] [data-semantic-component="NativeWeightedRelationDisplay"]')?.getAttribute('data-display-state')==='ready');
        const rootText=rootAnalyticDeclared ? (await rootDisplay.innerText()).trim() : null;
        if (sample) assert.equal(rootText,sample.display);
        assert.equal(await rootField.locator('input,textarea').count(),0);
        const after=await journalApi('api.data',{op:'read',model:'account.move.line',ids:[lineId],fields:lineFields});
        assert.equal(after.status,200); assert.equal(after.payload.ok,true);
        assert.equal(after.payload.data.records.length,1); assert.equal(after.payload.data.records[0].id,lineId);
        assert.deepEqual(after.payload.data.records,before.payload.data.records);
        const rootResult={model:'account.move.line',recordId:lineId,state:source.state,title:rootTitle,documentTitle:await page.title(),display:rootText,analyticDeclared:rootAnalyticDeclared,displayValueCompared:Boolean(sample),saveLabel:accountingReadonly ? null : '保存',
          raw:before.payload.data.records[0].analytic_distribution,
          before:before.payload.data.records[0],after:after.payload.data.records[0],unchanged:true,noEditor:true,passed:true};
        report.lineRootStates.push(rootResult);
        if (source.state==='posted' && rootAnalyticDeclared) report.rootAnalyticReadonly=rootResult;
        if (rootAnalyticDeclared) await rootDisplay.scrollIntoViewIfNeeded();
        await page.screenshot({path:`${root}/${actor}-root-${source.state}-analytic.png`});
        }
        }
      } else {
      assert(!leaves.some(n=>n.meta?.model==='account.move' && new URL(n.meta.route,base).searchParams.get('menu_id')==='175'),
        'role policy must not publish undeclared journal route');
      const positive = leaves.find(n=>n.meta?.route?.startsWith('/a/') && n.meta?.model !== 'account.move');
      assert(positive,'role must publish a positive business route');
      const positiveMenu = new URL(positive.meta.route,base).searchParams.get('menu_id');
      const positiveResponse = page.waitForResponse(response=>{
        let body; try {body=response.request().postDataJSON();} catch {return false;}
        const request=body?.params?.intent ? body.params : body;
        return request?.intent==='ui.contract.v2' && request.params?.op==='action_open'
          && String(request.params.menu_id)===positiveMenu;
      });
      await page.goto(base+positive.meta.route,{waitUntil:'domcontentloaded'});
      const positiveTransport=await positiveResponse;
      assert.equal(positiveTransport.status(),200); assert.equal((await positiveTransport.json()).ok,true);
      await page.waitForFunction(()=>['ok','empty'].includes(document.querySelector('[data-semantic-component="ActionView"]')?.getAttribute('data-collection-state')));
      report.positiveRoute={route:positive.meta.route,model:positive.meta.model,passed:true};
      const denied=await journalApi('route.authority.validate',{action_id:292,menu_id:175});
      assert.equal(denied.status,403); assert.equal(denied.payload.ok,false);
      report.routeValidation = denied;
      // Public dispatch checks published menus before invoking the route handler.
      assert.equal(denied.payload.error.reason_code,'PERMISSION_DENIED');
      assert.equal(denied.payload.error.details.intent,'route.authority.validate');
      assert.match(denied.payload.error.details.cause,/^用户无权访问菜单 /);
      await page.goto(base+'/a/292?menu_id=175',{waitUntil:'domcontentloaded'});
      await page.waitForURL(url=>url.pathname.endsWith('/access-denied'));
      await page.locator('[data-semantic-component="AccessDeniedView"]').waitFor({state:'visible'});
      report.cases.push({model:'account.move',menu:'175',route:'/a/292?menu_id=175',navigationPublished:false,
        authority:{status:denied.status,reason:denied.payload.error.reason_code},pageDenied:true,passed:true});
      await page.screenshot({path:`${root}/${actor}-journal-denied.png`});
      }
      assert.equal(report.blocked.length,0);
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
      await page.screenshot({path: `${root}/${actor}-${plan.menu}-list.png`});
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
  if (!['native-child', 'journal-draft', 'journal-save', 'journal-role'].includes(scope)) for (const model of models) assert(report.feedback.some(r => r.model === model && r.ok), 'feedback transport missing');
  report.passed = true;
} finally {
  if (journalSave.enabled && !report.passed && page) {
    report.validationDiagnostic = await page.evaluate(async () => {
      for (const element of document.querySelectorAll('*')) {
        let component = element.__vueParentComponent;
        while (component) {
          if (component.type?.__name === 'ContractFormPage') {
            const state = component.setupState;
            return { expectedRequired: state.nativeRequiredEditableFieldNames?.(),
              outcome: await state.standardFormComposition?.validateAdoptedFields() };
          }
          component = component.parent;
        }
      }
      return { unavailable: true };
    }).catch(error => ({ error: error.message }));
  }
  if (journalSave.enabled) report.cleanup = {passed: false, pending: 'governed ordinary-user ORM and independent readback',
    createdId: journalSave.createdId, ref: journalSave.ref};
  if (page && ['native-child', 'journal-draft', 'journal-save', 'journal-role'].includes(scope)) await page.screenshot({path: `${root}/${scope === 'journal-role' ? actor + '-' : ''}final.png`}).catch(() => {});
  report.lastPage = page ? {url: page.url(), text: await page.locator('body').innerText().catch(() => '')} : null;
  await browser.close();
  if (journalSave.enabled) { report.browserPassed = report.passed; report.passed = false; }
  fs.writeFileSync(`${root}/${['usability','journal-role'].includes(scope) ? actor + '-' : ''}report.json`, JSON.stringify(report, null, 2));
}
assert(journalSave.enabled ? report.browserPassed : report.passed, 'browser acceptance failed; governed wrapper must still clean up');
console.log(`browser: PASS (${report.cases.length} ${scope} cases${journalSave.enabled ? ', draft save/readback; ORM cleanup pending' : ', no save/dispatch'})`);

if (report.journalStates) console.log(`journal state coverage: ${report.journalStateCoverageComplete ? 'COMPLETE' : 'INCOMPLETE'} (${report.journalStates.map(item=>`${item.state}:${item.outcome}`).join(', ')})`);

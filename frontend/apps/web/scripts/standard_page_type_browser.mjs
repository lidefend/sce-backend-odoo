import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { paymentSourceReceiptValid, paymentSourceDraftWriteKind, documentFlowWriteKind, paymentReviewOriginalSteps, paymentReviewFlowSteps, paymentReviewWriteKind, versionReviewWriteKind, planExecutionWriteKind, reportProbeWriteKind, eventProbeWriteKind, diaryProbeWriteKind, expenseProbeWriteKind, permitsExpensePolicyWrite } from './standard_expense_success_scope.mjs';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';
import { permitsProjectNameWrite } from './standard_project_save_scope.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const base = 'http://127.0.0.1:5180';
const out = path.join(root, 'artifacts/frontend-web-fix-20260928', `tpl07-${Date.now()}`);
const report = { startup: [], status: 'not_run', assertions: [], calls: [], errors: [], forbiddenWrites: [], introduceContract: null };
// The introduce entry and dialog are contract driven: the probe reads the
// declared vocabulary from the effective contract response, so it can assert
// that the page renders the declared terms instead of a local rebuild.
function findIntroduceConfig(node, depth = 0) {
  if (!node || typeof node !== 'object' || depth > 14) return null;
  if (Array.isArray(node)) {
    for (const item of node) {
      const hit = findIntroduceConfig(item, depth + 1);
      if (hit) return hit;
    }
    return null;
  }
  if (node.componentKey === 'sc.payment.settlement_detail_collection' && node.componentConfig?.introduceDialog) {
    return { introduceLabel: node.componentConfig.introduceLabel, dialog: node.componentConfig.introduceDialog };
  }
  for (const value of Object.values(node)) {
    const hit = findIntroduceConfig(value, depth + 1);
    if (hit) return hit;
  }
  return null;
}
function findSavedSearchAuthority(node, depth = 0) {
  if (!node || typeof node !== 'object' || depth > 14) return null;
  if (node.custom?.favorites && typeof node.custom.favorites.save_enabled === 'boolean') return node.custom.favorites;
  for (const value of Object.values(node)) {
    const found = findSavedSearchAuthority(value, depth + 1);
    if (found) return found;
  }
  return null;
}
// Bounded detail-style verification helpers (pure; exercised by preview tests).
function detailStyleScopeIsolated(env) {
  return env.TPL07_SCOPE === 'style' && env.TPL52_FAMILY === 'detail'
    && !Object.entries(env).some(([key, value]) => /^(TPL07_|TPL52_)/.test(key)
      && !['TPL07_SCOPE', 'TPL52_FAMILY'].includes(key) && value && value !== '0');
}
const DETAIL_ORIGIN_FIXTURE = Object.freeze({ name: 'FE-DELIVERY-HARDENING-001', companyId: 8, state: 'draft' });
function detailOriginDomain(fixture) {
  return [['name', '=', fixture.name], ['company_id', '=', fixture.companyId], ['state', '=', fixture.state]];
}
function detailOriginRecord(records) {
  return Array.isArray(records) && records.length === 1 ? records[0] : null;
}
function detailRelationCandidates(authority) {
  const found = [];
  const walk = (nodes) => { for (const node of nodes || []) {
    const entry = node.fieldInfo?.relation_entry, value = authority.mainData?.[node.name];
    if (node.type === 'field' && entry?.can_read === true && entry.can_open === true
      && typeof entry.model === 'string' && /^[a-zA-Z0-9_.]+$/.test(entry.model)
      && Number.isSafeInteger(entry.menu_id) && entry.menu_id > 0
      && Number.isSafeInteger(entry.action_id) && entry.action_id > 0
      && Array.isArray(value) && Number.isSafeInteger(value[0]) && value[0] > 0
      && typeof value[1] === 'string' && value[1].trim()
      && !found.some(row => row.field === node.name)) found.push({ field: node.name, entry, id: value[0], label: value[1] });
    walk(node.children);
  } };
  walk(authority.layout?.containerTree);
  return found;
}
function detailExpectedSections(authority) {
  const expected = [], unknown = [];
  const statuses = new Map((authority.containers || []).map(row => [row.containerId, row]));
  const walk = nodes => { for (const node of nodes || []) {
    if (node.type === 'field') continue;
    const status = statuses.get(node.containerId);
    if (node.visible === false || status?.visible === false) continue;
    const raw = String(node.title || node.string || node.label || node.semanticTitle || '').trim();
    const title = raw && !['group','page','notebook','sheet','container','header','footer'].includes(raw.toLowerCase())
      && !(/^[a-z][a-z0-9_:. -]*$/i.test(raw) && /[_:.]/.test(raw)) ? raw : '';
    if ((node.type === 'group' && title) || node.type === 'notebook') {
      if (status?.visible !== true) unknown.push(node.containerId || node.type);
      expected.push({id:node.containerId,title:node.type === 'notebook' ? '' : title,type:node.type,locator:node.nativeLocator});
    } else walk(node.children);
  } };
  walk(authority.layout?.containerTree);
  return {expected,unknown};
}
function detailGeometryFailures(metrics) {
  const failures = [];
  if (metrics.unknownVisibility?.length) failures.push('section visibility authority');
  if (metrics.cards.length < 2 || metrics.expectedCount !== metrics.cards.length || !metrics.expectedMatched) failures.push('independent section/card coverage');
  if (metrics.cards.some(card => !card.official || card.nested)) failures.push('official nonnested Cards');
  if (metrics.cards.some(card => card.bodyCount > 1 || (!card.collapsed && (card.bodyCount !== 1 || !card.body || !Number.isFinite(card.body.height) || card.body.height <= 0)))) failures.push('expanded Card owned body geometry');
  if (metrics.cards.some(card => !card.collapsed && card.header && (!Number.isFinite(card.header.height) || card.header.height <= 0 || !Number.isFinite(card.headerBodyGap)))) failures.push('expanded Card header/body geometry');
  if (metrics.cards.some(card => ['grid','inline-grid'].includes(card.display) || (card.rowGap !== 'normal' && Number.parseFloat(card.rowGap) !== 0)
    || (card.headerBodyGap !== null && (!Number.isFinite(card.headerBodyGap) || Math.abs(card.headerBodyGap) > 1)))) failures.push('Card root spacing owned by official driver');
  for (let i=0; i<metrics.cards.length; i+=1) for (let j=i+1; j<metrics.cards.length; j+=1) {
    const a=metrics.cards[i].rect, b=metrics.cards[j].rect;
    if (Math.max(b.top-a.bottom,a.top-b.bottom,b.left-a.right,a.left-b.right) <= 0) failures.push('positive card spacing');
  }
  if (!metrics.descriptions.length || metrics.descriptions.some(row => !row.official || !row.owned)) failures.push('official Descriptions owner');
  if (!metrics.facts.length || metrics.facts.some(row => !row.label || !row.value
    || row.label.right > row.value.left + 1 || Math.min(row.label.bottom,row.value.bottom) <= Math.max(row.label.top,row.value.top))) failures.push('horizontal label/value cells');
  if (metrics.collectionInsideFacts) failures.push('collection outside Descriptions');
  if (!metrics.contained) failures.push('page containment');
  return [...new Set(failures)];
}
// The create/edit review inspects the declared create and edit surfaces of one
// published model, plus reload retention. It reads only and never saves, so it
// must not be combined with a probe or scope that writes.
function createEditScopeIsolated(env) {
  return env.TPL07_SCOPE === 'create-edit'
    && !Object.entries(env).some(([key, value]) => /^(TPL07_|TPL52_)/.test(key)
      && key !== 'TPL07_SCOPE' && value && value !== '0');
}
let governedOrigin = null;
// Shared governed origin resolver: every scope that must open the representative
// published record resolves it from the fixture declaration (name bound to owning
// company and expected business state, unique match required) instead of a literal
// record id. A recorded id stops matching as soon as the acceptance fixture is
// rebuilt, which silently turns a real page failure into a "record not found".
async function resolveGovernedOrigin(page) {
  if (governedOrigin) return governedOrigin;
  const records = await page.evaluate(async (domain) => {
    const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
    const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
      body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model: 'payment.request', domain, fields: ['id', 'name', 'company_id', 'state'], limit: 2 } }),
    });
    const payload = await response.json();
    return payload.ok === true ? (payload.data?.records || []) : null;
  }, detailOriginDomain(DETAIL_ORIGIN_FIXTURE));
  check('governed origin: declared fixture read', Array.isArray(records));
  const record = detailOriginRecord(records || []);
  check('governed origin: unique declared fixture identity', Boolean(record)
    && record.company_id?.[0] === DETAIL_ORIGIN_FIXTURE.companyId && record.state === DETAIL_ORIGIN_FIXTURE.state,
    { count: (records || []).length });
  if (!record) throw new Error('governed origin fixture did not resolve to a unique declared record');
  governedOrigin = { id: record.id, name: record.name, company_id: record.company_id?.[0], state: record.state, match_count: (records || []).length };
  return governedOrigin;
}
// Transient TDesign tooltips/popups are absolutely-positioned overlays left by
// the probe's own theme-switch clicks. They are not page content, but a leftover
// tooltip keeps its pre-resize coordinates and inflates documentElement.scrollWidth
// during a later narrow-viewport measurement. Dismiss them before measuring so the
// containment assertion still bounds the real document layout.
async function dismissTransientOverlays(page) {
  await page.evaluate(() => { const el = document.activeElement; if (el && typeof el.blur === 'function') el.blur(); });
  await page.mouse.move(0, 0);
  await page.locator('.t-popup.t-tooltip').first().waitFor({ state: 'hidden', timeout: 2000 }).catch(() => {});
}
// Bind ownership when the request starts; response-time URLs are not authority.
function sceneRequestOwner(body, startedUrl) {
  if (body?.intent === 'my.work.summary' && body.params?.product_workspace === true) {
    const p = body.params;
    if (p.limit === 12 && p.limit_each === 4 && p.page_size === 12 && p.sort_by === 'priority') return 'workspace.home';
    if (p.limit === 80 && p.limit_each === 80 && p.page_size === 80 && p.sort_by === 'write_date') return 'my-work';
    return new URL(startedUrl).pathname === '/s/workspace.home' ? 'workspace.home-unclassified' : 'summary-unclassified';
  }
  return ({ 'workspace.home.enter': 'workspace.home', 'dashboard.company.enter': 'dashboard.company',
    'project.dashboard.enter': 'project.management' })[body?.intent] || null;
}
function retainedRelationValue(before, after) {
  return typeof before === 'string' && before.trim().length > 0 && before === after;
}
// End bounded detail-style verification helpers.
function findRecordAuthority(node, depth = 0) {
  if (!node || typeof node !== 'object' || depth > 14) return null;
  if (node.statusContract?.globalStatus?.effectiveRecordCapabilities && node.pageInfo?.model) {
    return { model: node.pageInfo.model, status: node.statusContract.globalStatus,
      deletePolicy: node.actionContract?.deletePolicy, mainData: node.dataContract?.mainData,
      ...(['task-authority', 'approval-actions', 'expense-policy', 'style', 'create-edit'].includes(process.env.TPL07_SCOPE) ? { structure: node.formStructureContract, layout: node.layoutContract, actions: node.actionContract, containers: node.statusContract.containerStatus } : {}) };
  }
  for (const value of Object.values(node)) {
    const found = findRecordAuthority(value, depth + 1);
    if (found) return found;
  }
  return null;
}
if (process.env.TPL07_SCOPE === 'style' && process.env.TPL52_FAMILY === 'detail') assert.ok(detailStyleScopeIsolated(process.env), 'detail style scope cannot combine probes or writes');
if (process.env.TPL07_SCOPE === 'create-edit') assert.ok(createEditScopeIsolated(process.env), 'create/edit scope cannot combine probes or writes');
const check = (name, passed, detail = {}) => { report.assertions.push({ name, passed, ...detail }); assert.ok(passed, name); };
await fs.mkdir(out, { recursive: true });
const build = JSON.parse(await fs.readFile(path.resolve(root, '../sce-offrepo/artifacts/config05-20260929/build-identity.json')));
const entry = Buffer.from(await fetch(`${base}${build.entry}`).then((res) => res.arrayBuffer()));
assert.equal(createHash('sha256').update(entry).digest('hex'), build.entry_sha256);
report.build = build;
const browser = await launchChromium({ headless: true });
const pendingProbeAborts = new Set();
let favoriteWritePermit = null;
let projectWritePermit = null;
let expenseCreateCapture = false;
const redFlushDenialInspect = process.env.TPL07_RED_FLUSH_DENIAL_INSPECT === '1';
assert.ok(!redFlushDenialInspect || (process.env.TPL07_SCOPE === 'approval-actions'
  && process.env.TPL07_APPROVAL_MODEL === 'sc.output.invoice.adjustment' && !process.env.TPL07_APPROVAL_VIEW));
assert.ok(!redFlushDenialInspect || !Object.entries(process.env).some(([key, value]) => key.startsWith('TPL07_')
  && !['TPL07_RED_FLUSH_DENIAL_INSPECT', 'TPL07_SCOPE', 'TPL07_APPROVAL_MODEL'].includes(key) && value && value !== '0'),
'red-flush denial inspection cannot combine with other probes');
const documentFlow = process.env.TPL07_DOCUMENT_FLOW === '1';
assert.ok(!documentFlow || (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_MODEL === 'sc.project.document' && process.env.TPL07_APPROVAL_VIEW === 'create'));
assert.ok(!documentFlow || !Object.entries(process.env).some(([key, value]) => key.startsWith('TPL07_')
  && !['TPL07_DOCUMENT_FLOW', 'TPL07_SCOPE', 'TPL07_APPROVAL_MODEL', 'TPL07_APPROVAL_VIEW'].includes(key) && value && value !== '0'),
  'document flow must not combine another probe or write scope');
const paymentSourceFlow = process.env.TPL07_PAYMENT_SOURCE_FLOW || '';
assert.ok(!paymentSourceFlow || (['subcontract', 'rental'].includes(paymentSourceFlow)
  && process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_MODEL === 'payment.request'
  && process.env.TPL07_APPROVAL_VIEW === 'create' && process.env.TPL07_PAYMENT_SOURCE_REPORT));
assert.ok(!paymentSourceFlow || !Object.entries(process.env).some(([key, value]) => key.startsWith('TPL07_')
  && !['TPL07_PAYMENT_SOURCE_FLOW', 'TPL07_PAYMENT_SOURCE_REPORT', 'TPL07_SCOPE', 'TPL07_APPROVAL_MODEL', 'TPL07_APPROVAL_VIEW'].includes(key)
  && value && value !== '0'), 'payment source scope must be isolated');
let paymentSourceSuccess = null;
let paymentSourceCapture = false;
let documentSuccess = null;
let documentCreateCapture = false;
const diarySaveProbe = process.env.TPL07_DIARY_SAVE_PROBE === '1';
assert.ok(!diarySaveProbe || (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_MODEL === 'sc.construction.diary' && process.env.TPL07_APPROVAL_VIEW === 'create'));
const eventSaveProbe = process.env.TPL07_EVENT_SAVE_PROBE === '1';
assert.ok(!eventSaveProbe || (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_MODEL === 'sc.contract.event' && process.env.TPL07_APPROVAL_VIEW === 'create'));
const eventSaveSuccess = process.env.TPL07_EVENT_SAVE_SUCCESS === '1';
assert.ok(!eventSaveSuccess || (eventSaveProbe && process.env.TPL07_EXPENSE_SAVE_SUCCESS !== '1' && process.env.TPL07_DIARY_SAVE_SUCCESS !== '1'));
const reportSaveSuccess = process.env.TPL07_REPORT_SAVE_SUCCESS === '1';
assert.ok(!reportSaveSuccess || (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_MODEL === 'sc.plan.report'
  && process.env.TPL07_APPROVAL_VIEW === 'create' && !eventSaveSuccess && process.env.TPL07_DIARY_SAVE_SUCCESS !== '1' && process.env.TPL07_EXPENSE_SAVE_SUCCESS !== '1'));
const planVersionInspect = process.env.TPL07_PLAN_VERSION_INSPECT === '1';
assert.ok(!planVersionInspect || reportSaveSuccess);
const planVersionSave = process.env.TPL07_PLAN_VERSION_SAVE === '1';
assert.ok(!planVersionSave || planVersionInspect);
const planVersionSubmit = process.env.TPL07_PLAN_VERSION_SUBMIT === '1';
assert.ok(!planVersionSubmit || planVersionSave);
const planVersionReview = process.env.TPL07_PLAN_VERSION_REVIEW === '1';
assert.ok(!planVersionReview || planVersionSubmit);
const planExecution = process.env.TPL07_PLAN_EXECUTION === '1';
assert.ok(!planExecution || (reportSaveSuccess && !planVersionInspect));
let planSaveCapture = false;
let planNodeReadGate = null;
let versionSaveCapture = false;
let reportSuccess = null;
let reportCreateCapture = false;
let eventSuccess = null;
let eventCreateCapture = false;
let diaryCreateCapture = false;
const diarySaveSuccess = process.env.TPL07_DIARY_SAVE_SUCCESS === '1';
assert.ok(!diarySaveSuccess || (diarySaveProbe && process.env.TPL07_EXPENSE_SAVE_SUCCESS !== '1'));
let diarySuccess = null;
const expenseSaveProbe = process.env.TPL07_EXPENSE_SAVE_PROBE === '1';
const expenseSaveSuccess = process.env.TPL07_EXPENSE_SAVE_SUCCESS === '1';
const expenseFailureStage = process.env.TPL07_EXPENSE_FAILURE_STAGE || '';
assert.ok(['', 'upload', 'submit'].includes(expenseFailureStage));
const expensePartialUpload = process.env.TPL07_EXPENSE_PARTIAL_UPLOAD === '1';
assert.ok(!expensePartialUpload || (expenseSaveSuccess && expenseSaveProbe && expenseFailureStage === 'upload'));
let expenseSuccess = null;
let paymentReview = null;
let expensePolicyPermit = null;
const expenseRecoveryPath = path.join(out, 'expense-success-recovery.json');
async function expenseCleanup(stage) {
  const output = execFileSync('make', ['verify.business_config.approval_runtime', 'SC_ACCEPTANCE_RUNTIME_PROFILE=local'], {
    cwd: root, encoding: 'utf8', timeout: 60000,
    env: { ...process.env, SC_APPROVAL_RUNTIME_SCOPE: 'expense-browser-cleanup', SC_EXPENSE_CREATE_REPORT: expenseRecoveryPath },
  });
  await fs.writeFile(path.join(out, `expense-cleanup-${stage}.log`), output);
  const receipt = JSON.parse(output.split('\n').find(line => line.startsWith('EXPENSE_BROWSER_CLEANUP=')).slice('EXPENSE_BROWSER_CLEANUP='.length));
  const expected = stage === 'preflight' && paymentReview?.phase === 'prepare' ? 'preflight' : 'restored';
  check(`expense cleanup: ${stage} authoritative ${expected}`, receipt.status === expected);
  return receipt;
}
const lifecycleName = 'FE-TPL53-私有收藏闭环';

async function login(role) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  page.on('pageerror', (error) => report.errors.push(error.message));
  const sceneRequests = new WeakMap();
  page.on('request', (request) => {
    if (process.env.TPL07_SCOPE !== 'scene-entry') return;
    let body;
    try { body = request.postDataJSON(); } catch { return; }
    const startedUrl = page.url();
    const owner = sceneRequestOwner(body, startedUrl);
    if (!owner) return;
    report.sceneEntryCalls ??= [];
    const row = { id: report.sceneEntryCalls.length + 1, role, owner, intent: body.intent,
      startedUrl, params: body.params, success: null };
    report.sceneEntryCalls.push(row);
    sceneRequests.set(request, row);
  });
  await page.route('**/api/v1/intent*', async (route) => {
    const body = route.request().postDataJSON();
    if ((process.env.TPL07_SCOPE === 'scene-entry' || detailStyleScopeIsolated(process.env)) && ['execute_button', 'contract.action', 'file.upload'].includes(body?.intent)) {
      report.forbiddenWrites.push({ intent: body.intent, reason: 'scene entry scope is read-only' });
      return route.abort();
    }
    // The create/edit review inspects the declared surfaces and never saves, so
    // any business write it would have triggered is recorded and refused here.
    if (createEditScopeIsolated(process.env) && body?.intent === 'api.data'
      && ['create', 'write', 'unlink'].includes(body?.params?.op) && body?.params?.model === 'payment.request') {
      report.forbiddenWrites.push({ intent: body.intent, op: body.params.op, reason: 'create/edit review scope is read-only' });
      return route.abort();
    }

    const paymentKind = paymentReviewWriteKind(role, body, paymentReview);
    if (paymentKind) {
      paymentReview.phase = `${paymentKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.paymentReviewWrites ??= [];
      report.paymentReviewWrites.push({ kind: paymentKind, request: body, result });
      if (result.ok === true) {
        if (paymentKind === 'open') paymentReview.continuation = result.data?.result?.raw_action;
        if (paymentKind === 'create') paymentReview.id = Number(result.data?.id || result.data?.record?.id);
        paymentReview.phase = { config_disable: 'config_disabled', flow_config: 'flow_steps', flow_steps: 'flow_configured', restore_steps: 'flow_restored', open: 'opened', create: 'created', submit: 'submitted', approve: paymentReview.approvalFlow && paymentReview.reviewStage === 1 ? 'first_approved' : 'done' }[paymentKind];
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
      return route.fulfill({ response });
    }
    if (paymentReview?.phase === 'capture' && role === 'fixture_role_pfl035_finance_user'
      && body?.intent === 'api.data' && body.params?.op === 'create' && body.params.model === paymentReview.model) {
      report.paymentReviewCreateCapture = body;
      paymentReview.phase = 'captured';
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
      return route.fulfill({ status: 503, contentType: 'application/json',
        body: JSON.stringify({ ok: false, error: { code: 'TPL53_CAPTURE_ONLY', message: '验收只读捕获：未创建记录' } }) });
    }
    const reviewKind = versionReviewWriteKind(role, body, reportSuccess);
    if (reviewKind) {
      reportSuccess.phase = `${reviewKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.versionReviewWrites ??= [];
      report.versionReviewWrites.push({ kind: reviewKind, request: body, result });
      if (result.ok === true) {
        if (reviewKind === 'version-config') reportSuccess.approvalPolicyId = result.data?.policy?.id;
        reportSuccess.phase = reviewKind === 'version-config' ? 'version-steps' : 'done';
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
      return route.fulfill({ response });
    }
    if (planNodeReadGate && role === 'fixture_role_pm' && body?.intent === 'api.data'
      && body.params?.op === 'read' && body.params.model === 'sc.plan.line'
      && body.params.ids?.length === 1 && body.params.ids[0] === reportSuccess?.nodeId
      && body.params.fields?.includes('name')) await planNodeReadGate;
    if (permitsExpensePolicyWrite(role, body, expensePolicyPermit)) {
      report.expensePolicyWrites ??= [];
      report.expensePolicyWrites.push({ ...expensePolicyPermit });
      expensePolicyPermit = null;
      return route.continue();
    }
    const planKind = planExecutionWriteKind(role, body, reportSuccess);
    if (planKind) {
      reportSuccess.phase = `${planKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.planExecutionWrites ??= [];
      report.planExecutionWrites.push({ kind: planKind, request: body, result });
      if (result.ok === true) reportSuccess.phase = 'done';
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
      return route.fulfill({ response });
    }
    if (planExecution && planSaveCapture && role === 'fixture_role_pm' && body?.intent === 'api.data'
      && body.params?.op === 'write' && body.params.model === 'sc.plan') {
      report.planSaveAttempts ??= [];
      report.planSaveAttempts.push(body.params);
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ ok: false, error: { code: 'TPL53_PLAN_CAPTURE', message: '计划执行定向保存失败验证' } }) });
    }
    const reportKind = reportProbeWriteKind(role, body, reportSuccess);
    if (reportKind) {
      reportSuccess.phase = `${reportKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.reportSuccessWrites ??= [];
      report.reportSuccessWrites.push({ kind: reportKind, result });
      if (result.ok === true) {
        if (reportKind === 'parent') reportSuccess.parentId = result.data?.id;
        if (reportKind === 'create') reportSuccess.id = result.data?.id;
        reportSuccess.phase = reportKind === 'parent' ? 'prepare' : reportKind === 'create' ? 'submit' : 'done';
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
      return route.fulfill({ response });
    }
    if (planVersionSave && versionSaveCapture && role === 'fixture_role_pm' && body?.intent === 'api.data'
      && body.params?.op === 'write' && body.params.model === 'sc.plan') {
      report.versionSaveAttempts ??= [];
      report.versionSaveAttempts.push(body.params);
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ ok: false, error: { code: 'TPL53_VERSION_CAPTURE', message: '计划版本定向保存失败验证' } }) });
    }
    if (reportSaveSuccess && reportCreateCapture && role === 'fixture_role_pm' && body?.intent === 'api.data'
      && body.params?.op === 'create' && body.params.model === 'sc.plan.report') {
      report.reportSaveAttempts ??= [];
      report.reportSaveAttempts.push(body.params);
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ ok: false, error: { code: 'TPL53_REPORT_CAPTURE', message: '计划汇报定向保存失败验证' } }) });
    }
    if (paymentSourceFlow && paymentSourceDraftWriteKind(role, body, paymentSourceSuccess)) {
      paymentSourceSuccess.phase = 'create_in_flight';
      const recovery = path.join(out, 'payment-source-recovery.json');
      await fs.writeFile(recovery, JSON.stringify(paymentSourceSuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.paymentSourceWrite = result;
      if (result.ok === true) { paymentSourceSuccess.id = result.data?.id; paymentSourceSuccess.phase = 'readback'; }
      await fs.writeFile(recovery, JSON.stringify(paymentSourceSuccess, null, 2));
      return route.fulfill({ response });
    }
    if (paymentSourceFlow && paymentSourceCapture && role === 'fixture_role_finance' && body?.intent === 'api.data'
      && body.params?.op === 'create' && body.params.model === 'payment.request') {
      paymentSourceCapture = false;
      report.paymentSourceAttempt = body.params;
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ ok: false,
        error: { code: 'TPL53_PAYMENT_SOURCE_CAPTURE', message: '付款来源定向载荷捕获，请重试保存' } }) });
    }
    const documentKind = documentFlowWriteKind(role, body, documentSuccess);
    if (documentFlow && documentKind) {
      documentSuccess.phase = `${documentKind}_in_flight`;
      await fs.writeFile(path.join(out, 'document-flow-recovery.json'), JSON.stringify(documentSuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.documentWrites ??= [];
      report.documentWrites.push({ kind: documentKind, result });
      if (result.ok === true) {
        if (documentKind === 'create') documentSuccess.id = result.data?.id;
        documentSuccess.phase = 'readback';
      }
      await fs.writeFile(path.join(out, 'document-flow-recovery.json'), JSON.stringify(documentSuccess, null, 2));
      return route.fulfill({ response });
    }
    if (documentFlow && documentCreateCapture && role === 'fixture_role_pm' && body?.intent === 'api.data'
      && body.params?.op === 'create' && body.params.model === 'sc.project.document') {
      documentCreateCapture = false;
      report.documentCreateAttempt = body.params;
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ ok: false,
        error: { code: 'TPL53_DOCUMENT_CAPTURE', message: '工程资料定向载荷捕获，请重试保存' } }) });
    }
    const eventKind = eventProbeWriteKind(role, body, eventSuccess);
    if (eventKind) {
      eventSuccess.phase = `${eventKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(eventSuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.eventSuccessWrites ??= [];
      report.eventSuccessWrites.push({ kind: eventKind, result });
      if (result.ok === true) {
        if (eventKind === 'create') eventSuccess.id = result.data?.id;
        eventSuccess.phase = eventKind === 'create' ? 'submit' : 'done';
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(eventSuccess, null, 2));
      return route.fulfill({ response });
    }
    if (eventSaveProbe && eventCreateCapture && role === 'fixture_role_contract_operator' && body?.intent === 'api.data'
      && body.params?.op === 'create' && body.params.model === 'sc.contract.event') {
      report.eventSaveAttempts ??= [];
      report.eventSaveAttempts.push(body.params);
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({
        ok: false, error: { code: 'TPL53_EVENT_SAVE_UNAVAILABLE', message: '验收注入：事件保存暂不可用，请重试' },
      }) });
    }
    if (eventSaveProbe && ['contract.action', 'execute_button', 'file.upload'].includes(body?.intent)) {
      report.forbiddenWrites.push({ intent: body.intent, reason: 'event save failure probe cannot execute business actions' });
      return route.abort();
    }
    const diaryKind = diaryProbeWriteKind(role, body, diarySuccess);
    if (diaryKind) {
      diarySuccess.phase = `${diaryKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(diarySuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.diarySuccessWrites ??= [];
      report.diarySuccessWrites.push({ kind: diaryKind, result });
      if (result.ok === true) {
        if (diaryKind === 'create') diarySuccess.id = result.data?.id;
        diarySuccess.phase = diaryKind === 'create' ? 'submit' : 'done';
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(diarySuccess, null, 2));
      return route.fulfill({ response });
    }
    if (diarySaveProbe && diaryCreateCapture && role === 'fixture_role_pm' && body?.intent === 'api.data'
      && body.params?.op === 'create' && body.params.model === 'sc.construction.diary') {
      report.diarySaveAttempts ??= [];
      report.diarySaveAttempts.push(body.params);
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({
        ok: false, error: { code: 'TPL53_DIARY_SAVE_UNAVAILABLE', message: '验收注入：日志保存暂不可用，请重试' },
      }) });
    }
    if (diarySaveProbe && ['contract.action', 'execute_button', 'file.upload'].includes(body?.intent)) {
      report.forbiddenWrites.push({ intent: body.intent, reason: 'diary save failure probe cannot execute business actions' });
      return route.abort();
    }
    const expenseWriteKind = expenseProbeWriteKind(role, body, expenseSuccess);
    if (expenseWriteKind) {
      if (expenseFailureStage === expenseWriteKind && !expenseSuccess.failureInjected
        && (!expensePartialUpload || expenseSuccess.uploadIndex === 1)) {
        expenseSuccess.failureInjected = true;
        report.expenseInjectedFailure = { kind: expenseWriteKind, id: expenseSuccess.id };
        await fs.writeFile(expenseRecoveryPath, JSON.stringify(expenseSuccess, null, 2));
        return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({
          ok: false, error: { code: 'TPL53_LATER_STAGE_UNAVAILABLE', message: '验收注入：后续操作暂不可用，请重试' },
        }) });
      }
      expenseSuccess.phase = `${expenseWriteKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(expenseSuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.expenseSuccessWrites ??= [];
      report.expenseSuccessWrites.push({ kind: expenseWriteKind, intent: body.intent, filename: body.params?.name, result });
      if (result.ok === true) {
        if (expenseWriteKind === 'create') expenseSuccess.id = result.data?.id;
        expenseSuccess.phase = ({ create: 'upload', upload: 'submit', submit: 'done' })[expenseWriteKind];
        if (expenseWriteKind === 'upload' && expenseSuccess.files) {
          expenseSuccess.uploadIndex += 1;
          if (expenseSuccess.uploadIndex < expenseSuccess.files.length) expenseSuccess.phase = 'upload';
        }
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(expenseSuccess, null, 2));
      return route.fulfill({ response });
    }
    if ((expenseSaveProbe || process.env.TPL07_SCOPE === 'expense-policy') && ['contract.action', 'execute_button', 'file.upload'].includes(body?.intent)) {
      report.forbiddenWrites.push({ intent: body.intent, reason: 'save-failure probe cannot execute business actions' });
      return route.abort();
    }
    if (expenseCreateCapture && role === 'fixture_role_finance' && body?.intent === 'api.data'
      && body.params?.op === 'create' && body.params.model === 'sc.expense.claim') {
      report.expenseSaveAttempts ??= [];
      report.expenseSaveAttempts.push(body.params);
      return route.fulfill({ status: 503, contentType: 'application/json',
        body: JSON.stringify({ ok: false, error: { code: 'TPL53_SAVE_UNAVAILABLE', message: '验收注入：保存暂不可用，请重试' } }) });
    }
    if (permitsProjectNameWrite(role, body, projectWritePermit)) {
        report.projectWriteAttempts ??= [];
        report.projectWriteAttempts.push({ id: 10, name: projectWritePermit.name });
        projectWritePermit = null;
        return route.continue();
    }
    if (favoriteWritePermit && body?.intent === favoriteWritePermit.intent) {
      const permit = favoriteWritePermit;
      const params = body.params || {};
      const exact = params.model === 'payment.request' && Number(params.action_id) === 775
        && (body.intent === 'search.favorite.set'
          ? params.name === lifecycleName && params.is_default === false && params.is_shared === false
          : params.filter_id === permit.id);
      if (exact) {
        favoriteWritePermit = null;
        report.configurationAttempts ??= [];
        report.configurationAttempts.push({ intent: body.intent, id: params.filter_id, injectedFailure: permit.abort === true });
        return permit.abort ? route.abort('failed') : route.continue();
      }
    }
    if (((reportSaveSuccess || documentFlow || paymentSourceFlow) && ['execute_button', 'contract.action', 'file.upload'].includes(body?.intent))
      || (/^sc\.approval_policy\..*\.set$/.test(body?.intent || ''))
      || (body?.intent === 'api.data' && !['list', 'read', 'default_get'].includes(body.params?.op))
      || ['search.favorite.set', 'search.favorite.delete', 'api.data.create', 'api.data.write', 'api.data.unlink'].includes(body?.intent)) {
      report.forbiddenWrites.push({ intent: body.intent, op: body.params?.op, params: /^sc\.approval_policy\./.test(body.intent || '') ? body.params : undefined });
      return route.abort();
    }
    return route.continue();
  });
  page.on('response', async (response) => {
    try {
      if (new URL(response.url()).pathname === '/api/v1/auth/page-contracts') report.publicAuthContract = await response.json();
      const body = response.request().postDataJSON();
      if (process.env.TPL07_PLAN_EXECUTION === '1' && body?.intent === 'api.data' && body.params?.op === 'read' && body.params?.model === 'sc.plan.line') {
        report.planNodeReads ??= [];
        report.planNodeReads.push({ request: body.params, result: await response.json() });
      }
      const sceneRequest = sceneRequests.get(response.request());
      if (sceneRequest) {
        const result = await response.json();
        sceneRequest.success = result.ok !== false && Boolean(result.data);
      }
      if (['system.init', 'ui.contract', 'ui.contract.get'].includes(body?.intent)) {
        const result = await response.json();
        report.startup.push({ role, intent: body.intent, success: result.ok !== false && Boolean(result.data), ...(process.env.TPL07_SCOPE === 'scene-entry' ? { workspaceHome: Boolean(result.data?.workspace_home), scenes: (result.data?.scene_ready_contract?.scenes || []).filter(row => ['workspace.home', 'dashboard.company', 'project.management'].includes(row.scene?.key)).map(row => ({ scene: row.scene, target: row.meta?.target })) } : {}) });
        if (body.intent === 'system.init') {
          report.productVersion = result.data?.product_version;
          if (process.env.TPL07_APPROVAL_CONFIG_SCOPE_INSPECT === '1') {
            const nav = result.data?.navigation?.nav;
            const matches = [];
            const visit = (node) => {
              if (!node || typeof node !== 'object') return;
              if (Number(node.menu_id || node.meta?.menu_id) === 507 || Number(node.meta?.action_id || node.action_id) === 655) matches.push(node);
              for (const child of node.children || []) visit(child);
            };
            if (Array.isArray(nav)) nav.forEach(visit);
            report.planConfigurationNavigation = { type: Array.isArray(nav) ? 'array' : typeof nav, matches };
          }
          if (['approval-actions', 'expense-policy', 'style'].includes(process.env.TPL07_SCOPE)) report.routeAuthority = result.data?.navigation?.route_authority;
        }
      }
      if (body?.intent === 'api.data' && body.params?.op === 'list') {
        const result = await response.json();
        report.calls.push({ role, model: body.params.model, domain: body.params.domain, domainRaw: body.params.domain_raw, order: body.params.order, offset: body.params.offset || 0, limit: body.params.limit, ids: result.data?.records?.map((row) => row.id) || [] });
      }
      if (typeof body?.intent === 'string' && body.intent.startsWith('ui.contract')) {
        const contract = await response.json();
        if (['approval-actions', 'expense-policy', 'style', 'create-edit'].includes(process.env.TPL07_SCOPE)) {
          report.contractResponses ??= [];
          report.contractResponses.push({ intent: body.intent, model: body.params?.model, contract, ...(process.env.TPL07_SCOPE === 'style' ? {role,request:body.params} : {}) });
        }
        if (contract.meta?.projection_cache) {
          report.projectionCaches ??= [];
          report.projectionCaches.push(contract.meta.projection_cache);
        }
        const recordAuthority = findRecordAuthority(contract);
        if (recordAuthority) {
          report.recordAuthority = recordAuthority;
          if (process.env.TPL07_SCOPE === 'task-authority') {
            report.taskAuthorities ??= {};
            report.taskAuthorities[recordAuthority.model] = recordAuthority;
          }
        }
        const savedSearch = findSavedSearchAuthority(contract);
        if (savedSearch) report.savedSearchAuthority = savedSearch;
        const found = findIntroduceConfig(contract);
        if (found) report.introduceContract = found;
      }
    } catch { /* only JSON list responses are observations */ }
  });
  await page.goto(`${base}/login`);
  const inputs = page.locator('input');
  if (process.env.TPL07_SCOPE === 'navigation') {
    await page.getByRole('button', { name: '激活账号', exact: true }).waitFor();
    const actions = report.publicAuthContract?.data?.pages?.login?.page_orchestration?.action_schema?.actions;
    check('login: activation has public execution target', actions?.open_account_activation?.target?.path === '/activate-account');
    check('login: declared recovery entry is present', await page.getByRole('button', { name: '忘记密码', exact: true }).count() === 1);
    check('login: heading consumes public brand identity', (await page.getByRole('heading', { level: 1 }).innerText()).includes(report.publicAuthContract.data.pages.login.texts.brand_name));
    await page.screenshot({ animations: 'disabled', path: path.join(out, 'login-public-authority.png') });
  }
  await inputs.nth(0).fill(role);
  await inputs.nth(1).fill(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD);
  if (await inputs.count() > 2 && await inputs.nth(2).isEnabled()) await inputs.nth(2).fill('sc_frontend_acceptance');
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 60000 });
  await page.locator('.layout-shell').waitFor();
  return { page, ctx };
}

async function list(page, menu, name) {
  await page.goto(`${base}/m/${menu}`);
  await page.locator('[data-list-card-container="official"]').waitFor();
  check(`${name}: standard type`, await page.locator('[data-list-composition-reason="contract-collection-view"]').count() === 1);
  check(`${name}: one container`, await page.locator('[data-list-card-container="official"]').count() === 1);
  await page.screenshot({ animations: 'disabled', path: path.join(out, `${name}.png`) });
}

async function form(page, url, name, profile = 'form') {
  await page.goto(`${base}${url}`);
  // Readiness follows the mode the contract declared for this page, never one
  // assumed composition. An editable record waits for the adopted form engine;
  // a readonly record waits for the page to publish the readonly detail
  // composition the contract declared. Demanding the editable engine on a
  // readonly record would require a mode the same contract cannot declare at
  // the same time, so the probe would hang on a page that is behaving correctly.
  await page.locator(profile === 'readonly'
    ? '[data-product-page-mode="form"][data-state="ok"][data-detail-composition="official-standard-detail"][data-detail-composition-reason="contract-readonly-record-view"]'
    : '[data-form-composition="official-standard-form"][data-state="ok"]').waitFor();
  check(`${name}: no unknown renderer`, await page.locator('[data-field-fail-closed]').count() === 0);
  if (profile === 'readonly') {
    check(`${name}: readonly mode published`, await page.locator('[data-semantic-component="ContractFormProductHeader"][data-state="readonly"]').count() === 1);
    check(`${name}: no editable form composition`, await page.locator('[data-form-composition="official-standard-form"]').count() === 0);
    // "The form engine is not mounted" is not the same claim as "no part of the
    // record is presented as editable": a readonly record could still be framed
    // by an editable section without ever mounting the engine. Assert the
    // sections themselves, so the readonly profile cannot hide an edit surface
    // behind the facts layout.
    check(`${name}: no editable record section`, await page.locator('[data-detail-section-reason][data-state="editable"]').count() === 0);
    check(`${name}: nonzero official facts`, await page.locator('[data-detail-facts="official-standard-detail"]').count() > 0);
    check(`${name}: readonly detail adopted`, await page.locator('[data-detail-composition="official-standard-detail"]').count() === 1);
    const collections = page.locator('[data-field-type="one2many"], [data-field-type="many2many"], [data-field-type="binary"]');
    const count = await collections.count();
    if (name === 'payment-readonly') check('payment readonly: nonzero detail collection', await page.locator('[data-field-type="one2many"]').count() > 0);
    for (let index = 0; index < count; index += 1) {
      check(`${name}: collection remains outside descriptions`, await collections.nth(index).locator('xpath=ancestor::*[@data-detail-facts="official-standard-detail"]').count() === 0);
    }
    report.detailSections ??= {};
    report.detailSections[name] = await page.locator('[data-detail-section-reason]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-detail-section-reason')));
  } else {
    check(`${name}: official form engine mounted`, await page.locator('[data-semantic-component="ScForm"]').count() > 0);
  }
  await page.screenshot({ animations: 'disabled', path: path.join(out, `${name}.png`) });
}

async function favoritesScope() {
  const finance = await login('fixture_role_finance');
  const page = finance.page;
  const failureProbe = process.env.TPL07_SCOPE === 'favorites-failure';
  let signalRequest;
  let releaseRequest;
  let requestStarted;
  if (failureProbe) {
    report.injectedFavoriteFailures = [];
    await page.route('**/api/v1/intent*', async (route) => {
      const body = route.request().postDataJSON();
      if (body?.intent !== 'search.favorite.set') return route.fallback();
      report.injectedFavoriteFailures.push({ model: body.params.model, shared: body.params.is_shared });
      let settled = false;
      let resume;
      const abort = async () => {
        if (settled) return;
        settled = true;
        try { await route.abort('failed'); }
        finally { resume?.(); pendingProbeAborts.delete(abort); }
      };
      pendingProbeAborts.add(abort);
      const waiting = new Promise((resolve) => { resume = resolve; releaseRequest = resolve; });
      signalRequest();
      await waiting;
      return abort();
    });
  }
  await list(page, 545, 'favorites-list');
  const authority = report.savedSearchAuthority;
  check('favorites: effective contract declares capability', typeof authority?.save_enabled === 'boolean');
  check('favorites: authorized fixture can exercise save form', authority.save_enabled === true && authority.intent === 'search.favorite.set');
  const menu = page.getByRole('button', { name: '展开搜索菜单', exact: true });
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
    await menu.click();
    const entry = page.getByRole('button', { name: authority.label, exact: true });
    check(`favorites-${width}: declared save entry is available`, await entry.isEnabled());
    await entry.click();
    const name = page.getByPlaceholder('收藏名称', { exact: true });
    await name.waitFor();
    check(`favorites-${width}: sharing follows declared capability`, await page.getByRole('checkbox', { name: '共享给所有用户', exact: true }).count() === (authority.shared_enabled === true ? 1 : 0));
    await name.fill('仅检查表单，不保存');
    const save = page.getByRole('button', { name: /^保存/ });
    await save.scrollIntoViewIfNeeded();
    check(`favorites-${width}: named save form is usable`, await save.isEnabled());
    check(`favorites-${width}: save action can enter viewport`, await save.evaluate((el) => { const box = el.getBoundingClientRect(); return box.top >= 0 && box.bottom <= innerHeight; }));
    if (failureProbe) {
      requestStarted = new Promise((resolve) => { signalRequest = resolve; });
      await save.click();
      let requestDeadline;
      try {
        await Promise.race([requestStarted, new Promise((_, reject) => { requestDeadline = setTimeout(() => reject(new Error('favorite request did not start')), 15000); })]);
      } finally { clearTimeout(requestDeadline); }
      check(`favorites-${width}: saving prevents duplicate submission`, await save.isDisabled());
      check(`favorites-${width}: pending input is stable`, await name.isDisabled());
      releaseRequest();
      await page.getByRole('alert').filter({ hasText: '收藏保存未完成' }).waitFor();
      check(`favorites-${width}: failure retains input`, await name.inputValue() === '仅检查表单，不保存');
      check(`favorites-${width}: failure permits retry`, await save.isEnabled());
      check(`favorites-${width}: no sharing escalation`, report.injectedFavoriteFailures.at(-1).shared === false);
    }
    await page.screenshot({ animations: 'disabled', path: path.join(out, `favorites-${width}.png`) });
    await page.getByRole('button', { name: '取消', exact: true }).click();
    await name.waitFor({ state: 'detached' });
    await page.keyboard.press('Escape');
    check(`favorites-${width}: escape restores search control`, await menu.evaluate((el) => el === document.activeElement));
    check(`favorites-${width}: no page overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  }
  check('favorites: real startup authority present', report.startup.some((r) => r.intent === 'system.init' && r.success));
  await finance.ctx.close();
}

async function navigationScope() {
  const finance = await login('fixture_role_finance');
  const page = finance.page;
  await list(page, 545, 'navigation-desktop');
  check('navigation: desktop keeps one official aside', await page.locator('[data-navigation-driver="official-aside"]').count() === 1);
  check('navigation: runtime product version is declared', typeof report.productVersion === 'string' && report.productVersion.length > 0);
  check('navigation: expanded footer consumes runtime version', (await page.locator('[data-product-version]').innerText()).trim() === `版本 ${report.productVersion}`);
  const before = new URL(page.url()).pathname;
  await page.setViewportSize({ width: 390, height: 844 });
  const toggle = page.getByRole('button', { name: '菜单', exact: true });
  await toggle.click();
  const dialog = page.getByRole('dialog', { name: '主导航', exact: true });
  await dialog.waitFor();
  check('navigation: mobile footer preserves runtime version', (await dialog.locator('[data-product-version]').innerText()).trim() === `版本 ${report.productVersion}`);
  check('navigation: mobile version fits drawer', await dialog.locator('[data-product-version]').evaluate((el) => { const box = el.getBoundingClientRect(); return box.right <= innerWidth && box.bottom <= innerHeight; }));
  check('navigation: exactly one dialog', await page.getByRole('dialog').count() === 1);
  check('navigation: official drawer owns the navigation', await dialog.locator('[data-navigation-driver="official-drawer"]').count() === 1);
  check('navigation: private mask exited', await page.locator('.mobile-sidebar-backdrop').count() === 0);
  check('navigation: authorized current menu retained', await dialog.getByText('付款申请', { exact: true }).count() > 0);
  await page.keyboard.press('Tab');
  check('navigation: focus remains in drawer', await dialog.evaluate((el) => el.contains(document.activeElement)));
  await page.screenshot({ animations: 'disabled', path: path.join(out, 'navigation-mobile-open.png') });
  await page.keyboard.press('Escape');
  await dialog.waitFor({ state: 'detached' });
  check('navigation: escape restores opener', await toggle.evaluate((el) => el === document.activeElement));
  check('navigation: closing preserves route', new URL(page.url()).pathname === before);
  check('navigation: scroll lock released', await page.evaluate(() => document.body.style.overflow !== 'hidden'));
  await toggle.click();
  await dialog.waitFor();
  await page.mouse.click(385, 420);
  await dialog.waitFor({ state: 'detached' });
  check('navigation: official backdrop dismisses', await page.getByRole('dialog').count() === 0);
  await page.setViewportSize({ width: 1440, height: 900 });
  check('navigation: desktop restored without duplicate navigation', await page.locator('[data-navigation-driver="official-aside"]').count() === 1 && await page.locator('#primary-sidebar').count() === 1);
  check('navigation: real startup authority present', report.startup.some((r) => r.intent === 'system.init' && r.success));
  await finance.ctx.close();
}

async function detailStyleVisualScope(session, inspect) {
  const page = session.page;
  let originId = null;
  let sourcePath = null;
  const themeState = () => page.evaluate(() => ({ mode: document.documentElement.getAttribute('data-sc-theme-mode'),
    resolved: document.documentElement.getAttribute('data-sc-theme-resolved'), stored: localStorage.getItem('sc_theme') }));
  const initialTheme = await themeState();
  report.detailVisual = { initialTheme, samples: [], relations: [] };
  async function setTheme(mode) {
    await page.setViewportSize({ width: 1440, height: 900 });
    for (let attempt=0; attempt<3; attempt+=1) {
      if ((await themeState()).mode === mode && (await themeState()).stored === mode) break;
      await page.locator('.theme-switch:visible').click();
    }
    await page.waitForFunction(mode => document.documentElement.getAttribute('data-sc-theme-mode') === mode
      && localStorage.getItem('sc_theme') === mode && document.documentElement.getAttribute('data-sc-theme-resolved')
        === (mode === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : mode), mode);
  }
  async function resolveOrigin() {
    const records = await page.evaluate(async (domain) => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
        body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model: 'payment.request', domain, fields: ['id', 'name', 'company_id', 'state'], limit: 2 } }),
      });
      const payload = await response.json();
      return payload.ok === true ? (payload.data?.records || []) : null;
    }, detailOriginDomain(DETAIL_ORIGIN_FIXTURE));
    check('detail origin: governed fixture read', Array.isArray(records));
    const record = detailOriginRecord(records || []);
    check('detail origin: unique declared fixture identity', Boolean(record)
      && record.company_id?.[0] === DETAIL_ORIGIN_FIXTURE.companyId && record.state === DETAIL_ORIGIN_FIXTURE.state,
      { count: (records || []).length });
    return { id: record.id, name: record.name, company_id: record.company_id?.[0], state: record.state, match_count: (records || []).length };
  }
  async function relationRoundTrip(authority, name) {
    const source = page.locator(`[data-detail-composition="official-standard-detail"][data-form-model="payment.request"][data-form-record="${originId}"][data-state="ok"]`);
    const actionsSnapshot = () => source.locator('[data-action-key]').evaluateAll(nodes => nodes.map(node => ({
      key: node.getAttribute('data-action-key'), label: node.textContent.trim(), enabled: node.getAttribute('data-action-enabled'),
      allowed: node.getAttribute('data-action-allowed'), disabled: node.hasAttribute('disabled'),
    })));
    const beforeActions = await actionsSnapshot();
    check(`${name}: source action identity available`, beforeActions.length > 0);
    const candidates = detailRelationCandidates(authority);
    let chosen;
    for (const candidate of candidates) {
      const controls = source.locator(`[data-field-name="${candidate.field}"] button:visible`).filter({ hasText: candidate.label });
      if (await controls.count() === 1 && await controls.isEnabled()) { chosen = { ...candidate, control: controls }; break; }
    }
    if (!chosen) report.detailVisual.relations.push({ name, status: 'not_run', reason: 'no visible nonempty declared can_read/can_open relation' });
    check(`${name}: qualified relation entry prerequisite`, Boolean(chosen));
    const originUrl = page.url(), origin = new URL(originUrl);
    const responseStart = (report.contractResponses || []).length;
    await chosen.control.click();
    await page.waitForURL(url => url.pathname.endsWith(`/${chosen.entry.model}/${chosen.id}`), {timeout:30000});
    await page.locator(`[data-form-model="${chosen.entry.model}"][data-form-record="${chosen.id}"][data-state="ok"]`).waitFor();
    // Navigation may reuse an already observed ui.contract for this exact identity.
    // DOM must still enter that target; direct API reads cannot satisfy this check.
    const contracts = report.contractResponses || [];
    const matches = row => {const current=findRecordAuthority(row.contract);return row.role==='fixture_role_finance'&&current?.model===chosen.entry.model&&current.mainData?.id===chosen.id;};
    let contractResponseIndex = contracts.findLastIndex((row,index)=>index>=responseStart&&matches(row));
    const contractObservation = contractResponseIndex >= 0 ? 'navigation-response' : 'same-session-cache';
    if (contractResponseIndex < 0) {
      const previous=report.detailVisual.relations.find(row=>row.status==='passed'&&row.target.model===chosen.entry.model&&row.target.id===chosen.id
        &&row.target.entry.menu_id===chosen.entry.menu_id&&row.target.entry.action_id===chosen.entry.action_id);
      contractResponseIndex=previous?.target.contractResponseIndex ?? -1;
    }
    const target = contractResponseIndex >= 0 && matches(contracts[contractResponseIndex]) ? findRecordAuthority(contracts[contractResponseIndex].contract) : null;
    check(`${name}: clicked target has exact same-session ui.contract authority`, Boolean(target));
    const targetUrl = new URL(page.url());
    check(`${name}: relation declared menu/action`, Number(targetUrl.searchParams.get('menu_id')) === chosen.entry.menu_id
      && Number(targetUrl.searchParams.get('action_id')) === chosen.entry.action_id);
    check(`${name}: relation exact return context`, decodeURIComponent(targetUrl.searchParams.get('return_url') || '') === `${origin.pathname}${origin.search}`
      && targetUrl.searchParams.get('return_model') === 'payment.request' && targetUrl.searchParams.get('return_field') === chosen.field);
    const targetProfile = target.status?.effectiveRenderProfile;
    check(`${name}: relation target authoritative identity/profile`, target.model === chosen.entry.model && target.mainData.id === chosen.id
      && ['readonly', 'edit', 'form'].includes(targetProfile));
    await page.locator(targetProfile === 'readonly' ? '[data-detail-composition="official-standard-detail"][data-state="ok"]'
      : '[data-form-composition="official-standard-form"][data-state="ok"]').waitFor();
    check(`${name}: relation target renders declared fields`, await page.locator('[data-field-fail-closed]').count() === 0);
    await page.goBack();
    await page.waitForURL(originUrl);
    await source.waitFor();
    await source.locator(`[data-field-name="${chosen.field}"] button:visible`).filter({hasText: chosen.label}).waitFor();
    check(`${name}: exact readonly source restored`, page.url() === originUrl && await source.count() === 1
      && await source.locator('[data-semantic-component="ContractFormProductHeader"][data-state="readonly"]').count() === 1);
    check(`${name}: source action/label restoration`, JSON.stringify(await actionsSnapshot()) === JSON.stringify(beforeActions));
    report.detailVisual.relations.push({name,status:'passed',field:chosen.field,label:chosen.label,source:{url:originUrl,model:'payment.request',id:originId,profile:'readonly',actions:beforeActions},
      target:{contractObservation,contractResponseIndex,url:targetUrl.href,model:target.model,id:target.mainData.id,profile:targetProfile,entry:chosen.entry}});
  }
  try {
    const resolvedOrigin = await resolveOrigin();
    originId = resolvedOrigin.id;
    sourcePath = `/r/payment.request/${originId}?menu_id=545&action_id=775`;
    report.detailVisual.origin = resolvedOrigin;
    const routeAuthority = report.routeAuthority;
    check('detail visual: exact ordinary finance/company authority', routeAuthority?.principal_scope?.user_id === 30 && routeAuthority.principal_scope.company_id === 8);
    const entries = ['primary_actions','contextual_actions','role_home_actions'].flatMap(key => routeAuthority[key] || []);
    check('detail visual: published source menu/action authority', entries.some(entry => Number(entry.menu_id) === 545 && Number(entry.action_id) === 775));
    for (const theme of ['light','dark']) {
      await setTheme(theme);
      for (const viewport of [{width:1440,height:900},{width:390,height:844}]) {
        await page.setViewportSize(viewport);
        const name = `detail-${theme}-${viewport.width}`;
        await list(page, 545, `style-list-${theme}-${viewport.width}`);
        await inspect(`shell-${theme}-${viewport.width}`, '.product-page-header h1', ['24px','600','32px']);
        await form(page, sourcePath, `style-${name}`, 'readonly');
        const authority = report.recordAuthority;
        check(`${name}: record/company identity`, authority?.model === 'payment.request' && authority.mainData?.id === originId && authority.mainData.company_id?.[0] === 8);
        check(`${name}: real theme persisted through navigation`, JSON.stringify(await themeState()) === JSON.stringify({mode:theme,resolved:theme,stored:theme}));
        const sections = detailExpectedSections(authority);
        const metrics = await page.evaluate(sections => {
          const root = document.querySelector('[data-detail-composition="official-standard-detail"]');
          const visible = node => node.getClientRects().length > 0 && getComputedStyle(node).visibility !== 'hidden';
          const rect = node => { const r=node.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,height:r.height}; };
          const containers = [...root.querySelectorAll('.native-container')].filter(visible);
          const expectedMatches = sections.expected.map(section => {
            const typed = containers.filter(node => (section.type === 'notebook' ? node.classList.contains('native-container--notebook') : node.classList.contains('native-container--group'))
              && !node.parentElement.closest('[data-detail-card="native-section"]'));
            const byIdentity=typed.filter(node=>node.getAttribute('data-section-source-identity')===section.id);
            if (byIdentity.length) return byIdentity;
            const byTitle=typed.filter(node=>section.type === 'notebook' || node.getAttribute('data-group-title')===section.title);
            return byTitle.every(node=>!node.getAttribute('data-section-source-identity')) ? byTitle : [];
          });
          const sectionMatches=sections.expected.map((section,index)=>({expectedId:section.id,title:section.title,
            matching:expectedMatches[index].map(node=>({sourceIdentity:node.getAttribute('data-section-source-identity')||null,
              basis:node.getAttribute('data-section-source-identity') ? 'contract-container-identity' : 'unique-title-and-type-fallback'}))}));
          const cards = [...root.querySelectorAll('[data-detail-card="native-section"]')].filter(visible);
          const descriptions = [...root.querySelectorAll('[data-detail-facts="official-standard-detail"]')].filter(visible);
          const facts = descriptions.flatMap(node => [...node.querySelectorAll('.detail-fact-value')].filter(value => visible(value)
            && value.textContent.trim() && !['one2many','many2many','binary','html'].includes(value.getAttribute('data-field-type'))).map(value => {
              const content = value.closest('.t-descriptions__content'), label = content?.previousElementSibling;
              return {field:value.getAttribute('data-field-name'),text:value.textContent.trim(),labelText:label?.textContent.trim(),
                label:label?.classList.contains('t-descriptions__label') ? rect(label) : null,value:content ? rect(content) : null};
            }));
          const probe=document.createElement('span');probe.style.backgroundColor='var(--td-bg-color-container)';probe.style.color='var(--td-text-color-primary)';document.body.append(probe);
          const themeTokens={surface:getComputedStyle(probe).backgroundColor,text:getComputedStyle(probe).color};probe.remove();
          return {expectedCount:sections.expected.length, unknownVisibility:sections.unknown, expectedMatched:expectedMatches.every(nodes => nodes.length === 1 && cards.includes(nodes[0])) && new Set(expectedMatches.flat()).size === sections.expected.length,
            expectedSections:sections.expected,sectionMatches,themeTokens,
            cards:cards.map(node=>{const style=getComputedStyle(node),header=node.querySelector(':scope > .t-card__header'),bodies=[...node.querySelectorAll('.native-detail-card-body')].filter(body=>body.closest('[data-detail-card="native-section"]')===node),body=bodies.length===1 ? bodies[0] : null;return {bodyCount:bodies.length,collapsed:node.getAttribute('data-collapsed')==='true',display:style.display,rowGap:style.rowGap,header:header ? rect(header) : null,body:body ? rect(body) : null,headerBodyGap:header&&body ? rect(body).top-rect(header).bottom : null,title:node.getAttribute('data-group-title'),official:node.classList.contains('t-card') && node.getAttribute('data-semantic-component')==='ScCard',
              nested:Boolean(node.parentElement.closest('[data-detail-card="native-section"]')),rect:rect(node),background:style.backgroundColor,color:style.color};}),
            descriptions:descriptions.map(node=>({official:node.classList.contains('t-descriptions')&&node.getAttribute('data-semantic-component')==='ScDescriptions',owned:Boolean(node.closest('[data-detail-card="native-section"]'))})),
            facts, collectionInsideFacts:descriptions.some(node=>node.querySelector('[data-field-type="one2many"],[data-field-type="many2many"],[data-field-type="binary"]')),
            contained:document.documentElement.scrollWidth<=innerWidth+1, bodyBackground:getComputedStyle(document.body).backgroundColor,bodyColor:getComputedStyle(document.body).color};
        }, sections);
        report.detailVisual.samples.push({name,theme,width:viewport.width,metrics});
        check(`${name}: official independent cards and horizontal facts`, detailGeometryFailures(metrics).length === 0, {failures:detailGeometryFailures(metrics)});
        check(`${name}: actual Card surface/text follow active theme tokens`, metrics.cards.every(card=>card.background===metrics.themeTokens.surface&&card.color===metrics.themeTokens.text));
        await inspect(name, '.product-page-header h1', ['24px','600','32px']);
        await relationRoundTrip(authority,name);
        await page.screenshot({animations:'disabled',path:path.join(out,`${name}-relation-return.png`),fullPage:true});
      }
    }
    for (const width of [1440,390]) {
      const [light,dark]=['light','dark'].map(theme=>report.detailVisual.samples.find(row=>row.theme===theme&&row.width===width).metrics.cards[0]);
      check(`detail-${width}: actual dark surface and text differ from light`,light.background!==dark.background&&light.color!==dark.color);
    }
    check('detail visual: no write or page errors', report.forbiddenWrites.length === 0 && report.errors.length === 0);
  } catch (error) {
    report.detailVisual.failure={url:page.url(),message:error.message,text:(await page.locator('body').innerText()).slice(0,8000)};
    await page.screenshot({animations:'disabled',path:path.join(out,'detail-visual-failure.png'),fullPage:true});
    throw error;
  } finally {
    try {
      await setTheme(initialTheme.mode);
      if (initialTheme.stored === null) await page.evaluate(() => localStorage.removeItem('sc_theme'));
      const restored = await themeState(); report.detailVisual.restoredTheme = restored;
      check('detail visual: original theme restored', restored.mode === initialTheme.mode && restored.resolved === initialTheme.resolved && restored.stored === initialTheme.stored);
    } finally { await session.ctx.close(); }
  }
}

async function styleScope() {
  const family = process.env.TPL52_FAMILY || 'all';
  assert.ok(['all', 'shell', 'collection', 'detail', 'form', 'overlay'].includes(family), 'known style family');
  report.styleFamily = family;
  const finance = await login('fixture_role_finance');
  const page = finance.page;
  const tokenSources = await Promise.all([
    'frontend/apps/web/src/styles/tokens/semantic.css',
    'frontend/apps/web/src/styles/tokens/component.css',
    'frontend/apps/web/src/styles/tokens/pattern.css',
  ].map((file) => fs.readFile(path.join(root, file), 'utf8')));
  const tokenNames = [...new Set(tokenSources.flatMap((text) => [...text.matchAll(/(--sc-[\w-]+)\s*:/g)].map((m) => m[1])))];
  tokenNames.push('--sc-semantic-text-disabled', '--sc-font-title-large', '--sc-font-title-medium');
  report.styles = [];
  const titleRole = await page.evaluate(() => {
    const probe = document.createElement('span');
    probe.style.font = 'var(--sc-font-title-large)';
    document.body.append(probe);
    const style = getComputedStyle(probe);
    const result = [style.fontSize, style.fontWeight, style.lineHeight];
    probe.remove();
    return result;
  });
  check('shell: official title-large role resolves', JSON.stringify(titleRole) === JSON.stringify(['18px', '600', '26px']), { titleRole });
  async function inspect(name, headingSelector, expected) {
    const result = await page.evaluate(({ tokenNames, headingSelector }) => {
      const rootStyle = getComputedStyle(document.documentElement);
      const missing = tokenNames.filter((name) => !rootStyle.getPropertyValue(name).trim());
      const headings = [...document.querySelectorAll(headingSelector)].filter((el) => el.getClientRects().length).map((el) => {
        const s = getComputedStyle(el);
        return { text: el.textContent.trim(), size: s.fontSize, weight: s.fontWeight, line: s.lineHeight };
      });
      return { missing, headings, placeholder: rootStyle.getPropertyValue('--td-text-color-placeholder').trim(),
        muted: rootStyle.getPropertyValue('--sc-semantic-text-muted').trim(),
        contained: document.documentElement.scrollWidth <= innerWidth + 1 };
    }, { tokenNames, headingSelector });
    report.styles.push({ name, ...result });
    check(`${name}: shared token chains resolve`, result.missing.length === 0, { missing: result.missing });
    check(`${name}: placeholder uses muted role`, result.placeholder === result.muted && Boolean(result.muted));
    check(`${name}: heading rendered`, result.headings.length > 0);
    if (expected) check(`${name}: official typography`, result.headings.every((h) => h.size === expected[0] && h.weight === expected[1] && h.line === expected[2]), { headings: result.headings });
    check(`${name}: page contained`, result.contained);
    await page.screenshot({ animations: 'disabled', path: path.join(out, `${name}.png`), fullPage: true });
  }
  if (family === 'detail') return detailStyleVisualScope(finance, inspect);
  // The record-opening families read the representative published record from the
  // governed declaration, so a rebuilt acceptance fixture cannot turn a real page
  // failure into a "record not found" on a frozen id.
  const originId = ['form', 'overlay', 'all'].includes(family) ? (await resolveGovernedOrigin(page)).id : null;
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    if (family !== 'overlay') {
    await list(page, 545, `style-list-${viewport.width}`);
    // This standard list intentionally suppresses the outer headline; its record
    // header keeps the pinned official headline-small ladder.
    await inspect(`shell-${viewport.width}`, '.product-page-header h1', ['24px', '600', '32px']);
    }
    if (['all', 'collection'].includes(family)) {
      const selector = viewport.width > 600 ? '.flat-table .column-sort-btn' : '.collection-mobile-record-row__identity';
      await page.locator(selector).first().waitFor();
      await inspect(`collection-cells-${viewport.width}`, selector, viewport.width > 600 ? ['14px', '600', '22px'] : ['16px', '600', '24px']);
    }
    if (['shell', 'collection'].includes(family)) continue;
    if (family === 'detail') {
      await form(page, `/r/payment.request/${originId}?menu_id=545&action_id=775`, `style-detail-${viewport.width}`, 'readonly');
      await inspect(`detail-${viewport.width}`, '.product-page-header h1', ['24px', '600', '32px']);
      continue;
    }
    await form(page, `/f/payment.request/${originId}?menu_id=545&action_id=775`, `style-form-${viewport.width}`);
    if (family === 'form') {
      await inspect(`form-${viewport.width}`, '.product-page-header h1', ['24px', '600', '32px']);
      continue;
    }
    await inspect(`form-text-${viewport.width}`, '.template-form-section .readonly-value:not(.readonly-value--action)', ['14px', '400', '22px']);
    const introduce = page.locator('[data-contract-entry-label]');
    check(`form-${viewport.width}: contract supplies introduce label`, Boolean(report.introduceContract?.introduceLabel));
    // The settlement collection is a declared optional presentation. With no rows
    // the declaration renders it collapsed with destroy-on-collapse, so the
    // declared introduce entry is only mounted once its own disclosure is
    // expanded. Expand the declared disclosure instead of assuming the entry is
    // unconditionally mounted.
    const settlementDisclosure = page.locator(
      '[data-semantic-component="PaymentSettlementDetailCollectionControl"] [data-disclosure-trigger]');
    const disclosureCount = await settlementDisclosure.count();
    let disclosureExpanded = false;
    if (disclosureCount === 1) {
      if (await settlementDisclosure.getAttribute('data-state') === 'collapsed') {
        await settlementDisclosure.click();
        await page.locator('[data-semantic-component="PaymentSettlementDetailCollectionControl"] [data-disclosure-trigger][data-state="expanded"]').waitFor();
      }
      disclosureExpanded = true;
    }
    const settlementEntry = await page.evaluate(() => ({
      entryButtons: document.querySelectorAll('[data-contract-entry-label]').length,
      gapMissing: document.querySelector('[data-contract-semantic-gap]')?.getAttribute('data-contract-semantic-missing') ?? null,
    }));
    report.settlementEntry = { ...settlementEntry, disclosureCount, disclosureExpanded };
    check(`form-${viewport.width}: declared entry is consumed or the gap is explicit`,
      settlementEntry.entryButtons > 0 || settlementEntry.gapMissing !== null, report.settlementEntry);
    await introduce.click();
    await page.locator('[data-dialog-purpose="payment-settlement-introduce"]').waitFor();
    await page.getByText('正在搜索结算单', { exact: false }).waitFor({ state: 'hidden' });
    await inspect(`dialog-${viewport.width}`, '.sc-design-dialog__heading h2', ['16px', '600', '24px']);
    await page.keyboard.press('Escape');
    await page.locator('[data-dialog-purpose="payment-settlement-introduce"]').waitFor({ state: 'detached' });
    if (family === 'overlay') continue;
    await form(page, `/r/payment.request/${originId}?menu_id=545&action_id=775`, `style-detail-${viewport.width}`, 'readonly');
    await inspect(`detail-${viewport.width}`, '.product-page-header h1', ['24px', '600', '32px']);
    await inspect(`detail-text-${viewport.width}`, '.template-form-section-descriptions .readonly-value:not(.readonly-value--action)', ['14px', '400', '22px']);
  }
  if (family === 'all') {
    const variants = await page.evaluate((names) => {
      const el = document.documentElement;
      const original = el.getAttribute('data-sc-theme');
      try {
        return ['light', 'dark'].map((theme) => {
          el.setAttribute('data-sc-theme', theme);
          const s = getComputedStyle(el);
          return { theme, missing: names.filter((name) => !s.getPropertyValue(name).trim()), disabled: s.getPropertyValue('--td-text-color-disabled').trim() };
        });
      } finally {
        if (original === null) el.removeAttribute('data-sc-theme'); else el.setAttribute('data-sc-theme', original);
      }
    }, tokenNames);
    check('style: both token variants resolve including disabled text', variants.every((v) => !v.missing.length && v.disabled), { variants });
  }
  check('style: real startup contract loaded', report.startup.some((r) => r.intent === 'system.init' && r.success));
  await finance.ctx.close();
}

// Bounded create/edit representative review: one published existing model, its
// declared create and edit surfaces, the declared relation field and child
// collection, and reload retention. The record identity comes from the governed
// declaration; the scope reads only and never saves.
async function createEditScope() {
  const finance = await login('fixture_role_finance');
  const page = finance.page;
  const origin = await resolveGovernedOrigin(page);
  const surface = '[data-form-composition="official-standard-form"][data-state="ok"]';
  report.createEdit = { origin, surfaces: [] };
  const themeState = () => page.evaluate(() => ({ mode: document.documentElement.getAttribute('data-sc-theme-mode'),
    resolved: document.documentElement.getAttribute('data-sc-theme-resolved'), stored: localStorage.getItem('sc_theme') }));
  async function setTheme(mode) {
    await page.setViewportSize({ width: 1440, height: 900 });
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const state = await themeState();
      if (state.mode === mode && state.stored === mode) break;
      await page.locator('.theme-switch:visible').click();
    }
    await page.waitForFunction((expected) => document.documentElement.getAttribute('data-sc-theme-mode') === expected
      && localStorage.getItem('sc_theme') === expected, mode);
    check(`create-edit: ${mode} theme applied`, (await themeState()).mode === mode);
  }
  async function inspectSurface(name, recordId) {
    await page.locator(surface).waitFor();
    check(`${name}: one declared official form composition`, await page.locator('[data-form-composition="official-standard-form"]').count() === 1);
    check(`${name}: composition follows the contract declaration`, await page.locator('[data-form-composition-reason="contract-record-view"]').count() === 1);
    check(`${name}: not an unclassified fallback`, await page.locator('[data-form-composition-reason="contract-view-not-classified"]').count() === 0);
    check(`${name}: no unknown renderer`, await page.locator('[data-field-fail-closed]').count() === 0);
    check(`${name}: declared editable sections`, await page.locator('[data-component="FormSection"][data-state="editable"]').count() > 0);
    check(`${name}: declared child collection rendered`, await page.locator('[data-field-type="one2many"]').count() > 0);
    const rendered = {
      record: await page.locator('[data-form-record]').first().getAttribute('data-form-record'),
      sections: await page.locator('[data-component="FormSection"]').count(),
      one2many: await page.locator('[data-field-type="one2many"]').count(),
      fields: await page.locator('[data-field-name]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-field-name')).sort()),
    };
    check(`${name}: bound to the declared ${recordId === null ? 'create' : 'record'} identity`,
      rendered.record === String(recordId === null ? 'new' : recordId), { rendered: rendered.record, recordId });
    report.createEdit.surfaces.push({ name, ...rendered });
    return rendered;
  }
  async function reviewBothThemes(name) {
    for (const theme of ['light', 'dark']) {
      await setTheme(theme);
      for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
        await page.setViewportSize(viewport);
        await dismissTransientOverlays(page);
        const geometry = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
        check(`${name}-${theme}-${viewport.width}: page contained`, geometry.scrollWidth <= geometry.innerWidth + 1, geometry);
        await page.screenshot({ animations: 'disabled', path: path.join(out, `${name}-${theme}-${viewport.width}.png`), fullPage: true });
      }
    }
  }

  // Create surface: the same declared composition must be adopted for a new
  // record. The probe inspects it and leaves without saving anything.
  await page.goto(`${base}/f/payment.request/new?menu_id=545&action_id=775`);
  await inspectSurface('create-surface', null);
  await reviewBothThemes('create-surface');

  // Edit surface: the declared editable composition for the published record,
  // its declared relation field and declared child collection.
  const editResponseStart = report.contractResponses?.length || 0;
  await page.goto(`${base}/f/payment.request/${origin.id}?menu_id=545&action_id=775`);
  const editSurface = await inspectSurface('edit-surface', origin.id);
  const relation = page.locator('[data-field-name="partner_id"]').first();
  check('edit-surface: declared relation field rendered', await page.locator('[data-field-name="partner_id"]').count() >= 1);
  check('edit-surface: declared relation field is visible', await relation.isVisible());
  check('edit-surface: relation field keeps its declared write state',
    await relation.getAttribute('data-field-state') !== 'readonly');
  check('edit-surface: relation field is not replaced by readonly facts',
    await relation.locator('[data-detail-facts="official-standard-detail"]').count() === 0);

  // Reload retention: re-entering the same declared route must re-render the same
  // bound record, composition and rendered field membership, not a stale draft.
  const selectedPartner = (start) => (report.contractResponses || []).slice(start)
    .map(row => findRecordAuthority(row.contract))
    .filter(row => row?.model === 'payment.request' && row.mainData?.id === origin.id).at(-1)?.mainData?.partner_id;
  const partnerBefore = selectedPartner(editResponseStart);
  check('edit-surface: exact source contract declares selected relation', Array.isArray(partnerBefore)
    && Number.isSafeInteger(partnerBefore[0]) && partnerBefore[0] > 0 && typeof partnerBefore[1] === 'string' && Boolean(partnerBefore[1].trim()), { partnerBefore });
  const relationBefore = await relation.locator('input').first().inputValue();
  check('edit-surface: input matches declared relation label', retainedRelationValue(partnerBefore[1], relationBefore));
  check('edit-surface: relation has a nonempty selected value before reload', retainedRelationValue(relationBefore, relationBefore), { value: relationBefore });
  const reloadResponseStart = report.contractResponses?.length || 0;
  await page.reload();
  const reloaded = await inspectSurface('edit-surface-reload', origin.id);
  check('edit-surface: reload keeps the declared field membership',
    JSON.stringify(reloaded.fields) === JSON.stringify(editSurface.fields), { before: editSurface.fields, after: reloaded.fields });
  check('edit-surface: reload keeps exact declared relation identity', JSON.stringify(selectedPartner(reloadResponseStart)) === JSON.stringify(partnerBefore));
  check('edit-surface: reload keeps the relation value',
    retainedRelationValue(relationBefore, await page.locator('[data-field-name="partner_id"]').first().locator('input').first().inputValue()));
  await reviewBothThemes('edit-surface');

  check('create-edit: real startup authority present', report.startup.some((row) => row.role === 'fixture_role_finance' && row.intent === 'system.init' && row.success));
  await finance.ctx.close();
}

try {
  if (process.env.TPL07_SCOPE === 'scene-entry') {
    // Bounded home selection: the published workspace home is reviewed on its own
    // so the explicitly unpublished company/project scenes never gate it.
    const sceneSelection = process.env.TPL07_SCENE_SELECTION || 'all';
    assert.ok(['all', 'home'].includes(sceneSelection), 'known scene selection');
    const sceneTargets = [
      ['fixture_role_finance', [['workspace.home', 'workspace.home.enter']]],
      ['fixture_role_executive', [['dashboard.company', 'dashboard.company.enter'], ['project.management', 'project.dashboard.enter']]],
    ];
    for (const [role, entries] of (sceneSelection === 'home' ? sceneTargets.slice(0, 1) : sceneTargets)) {
      const { page, ctx } = await login(role);
      for (const [scene, intent] of entries) {
        const before = report.sceneEntryCalls?.length || 0;
        const entryResponse = page.waitForResponse(response => response.request().postDataJSON()?.intent === (scene === 'workspace.home' ? 'my.work.summary' : intent), { timeout: 60000 }).then(response => ({ response }), error => ({ error }));
        await page.goto(`${base}/s/${scene}${scene === 'project.management' ? '?project_id=10' : ''}`);
        const home = scene === 'workspace.home';
        const surface = page.locator(`[data-semantic-component="${home ? 'HomeView' : 'SceneContractBlockGridView'}"]`);
        const entryResult = await entryResponse;
        if (entryResult.error) throw entryResult.error;
        await surface.waitFor({ timeout: 60000 });
        if (home) {
          const response = entryResult.response;
          const payload = await response.json();
          check(`${scene}: workspace summary contract loaded`, payload.ok !== false && Boolean(payload.data?.product_workspace));
          const workspace = payload.data?.product_workspace;
          const sections = Array.isArray(workspace?.sections) ? workspace.sections : [];
          report.workspaceHome = { sections: sections.map((row) => ({ key: row.key, label: row.label, count: row.count })),
            total: workspace?.total ?? null, quick_links: (workspace?.presentation?.quick_links || []).length };
          const root = page.locator('[data-role-home][data-role-home-renderer="workspace-contract"]');
          await root.waitFor({ timeout: 60000 });
          await page.waitForFunction(() => ['ready', 'error'].includes(document.querySelector('[data-role-home]')?.getAttribute('data-state')), undefined, { timeout: 60000 });
          check(`${scene}: declared workspace composition rendered`, await page.locator('[data-workspace-composition="official-dashboard-workspace"]').count() === 1);
          check(`${scene}: declared workspace state is usable`, await root.getAttribute('data-state') === 'ready');
          const summaries = page.locator('[data-role-home] .role-home-surface__summary-list article');
          check(`${scene}: declared sections render as summaries`, await summaries.count() === Math.min(sections.length, 4),
            { rendered: await summaries.count(), declared: sections.length });
          check(`${scene}: declared entries render as usable actions`, await page.locator('[data-role-home] .role-home-surface__link-list--quick button:enabled').count() > 0);
          check(`${scene}: declared main action available`, await page.getByRole('button', { name: '查看全部', exact: true }).isEnabled());
          const themeState = () => page.evaluate(() => ({ mode: document.documentElement.getAttribute('data-sc-theme-mode'), stored: localStorage.getItem('sc_theme') }));
          for (const theme of ['light', 'dark']) {
            await page.setViewportSize({ width: 1440, height: 900 });
            for (let attempt = 0; attempt < 3; attempt += 1) {
              const state = await themeState();
              if (state.mode === theme && state.stored === theme) break;
              await page.locator('.theme-switch:visible').click();
            }
            await page.waitForFunction((expected) => document.documentElement.getAttribute('data-sc-theme-mode') === expected
              && localStorage.getItem('sc_theme') === expected, theme);
            check(`${scene}: ${theme} theme applied`, (await themeState()).mode === theme);
            for (const width of [1440, 390]) {
              await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
              await dismissTransientOverlays(page);
              const geometry = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth,
                widest: [...document.querySelectorAll('body *')].map((node) => ({ tag: node.tagName, cls: String(node.className || '').slice(0, 80), right: Math.round(node.getBoundingClientRect().right) }))
                  .filter((row) => row.right > window.innerWidth + 1).sort((a, b) => b.right - a.right).slice(0, 5) }));
              check(`${scene}-${theme}-${width}: page contained`, geometry.scrollWidth <= geometry.innerWidth + 1, geometry);
              await page.screenshot({ animations: 'disabled', path: path.join(out, `scene-${scene}-${theme}-${width}.png`), fullPage: true });
            }
          }
          await page.setViewportSize({ width: 1440, height: 900 });
        } else {
          await page.waitForFunction(() => document.querySelector('[data-semantic-component="SceneContractBlockGridView"]')?.getAttribute('data-state') === 'idle', undefined, { timeout: 60000 });
          check(`${scene}: declared entry succeeded`, (report.sceneEntryCalls || []).slice(before).some(row => row.role === role && row.intent === intent && row.success));
        }
        check(`${scene}: one shared contract block renderer`, await surface.count() === 1);
        for (const width of [1440, 390]) {
          await page.setViewportSize({ width, height: 900 });
          const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
          check(`${scene}: usable viewport ${width}`, !overflow);
          await page.screenshot({ animations: 'disabled', path: path.join(out, `scene-${scene}-${width}.png`), fullPage: true });
        }
        const ownedCalls = () => (report.sceneEntryCalls || []).filter(row => row.role === role && row.owner === scene);
        check(`${scene}: actual owned request observed`, ownedCalls().some(row => row.success === true
          && (!home || row.intent === 'my.work.summary')), ownedCalls());
        const after = ownedCalls().length;
        await page.getByRole('button', { name: '我的工作', exact: true }).click();
        await page.waitForURL(url => url.pathname === '/my-work');
        await surface.waitFor({ state: 'hidden' });
        await page.waitForTimeout(700);
        check(`${scene}: cached scene stops after leaving route`, ownedCalls().length === after, { before: after, after: ownedCalls().length });
      }
      check(`${role}: real startup loaded`, report.startup.some(row => row.role === role && row.intent === 'system.init' && row.success));
      await ctx.close();
    }
  } else if (process.env.TPL07_SCOPE === 'expense-policy') {
    const admin = await login('fixture_role_config_admin');
    const resolveEntry = (xmlid) => {
      const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
        .flatMap((key) => report.routeAuthority?.[key] || []).filter((row) => row.menu_xmlid === xmlid);
      assert.equal(entries.length, 1, `one authorized entry: ${xmlid}`);
      assert.ok(Number(entries[0].menu_id) > 0 && Number(entries[0].action_id) > 0);
      return entries[0];
    };
    const categoryEntry = resolveEntry('smart_construction_core.menu_sc_business_category');
    const request = (params) => admin.page.evaluate(async (params) => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
        body: JSON.stringify({ intent: 'api.data', params }),
      });
      return response.json();
    }, params);
    const found = await request({ op: 'list', model: 'sc.business.category',
      domain: [['code', '=', 'finance.expense.reimbursement'], ['active', '=', true]],
      fields: ['id', 'code', 'attachment_policy'], limit: 2 });
    assert.equal(found.ok, true);
    assert.equal(found.data?.records?.length, 1);
    const baseline = found.data.records[0];
    assert.equal(baseline.attachment_policy, 'required');
    const read = async () => {
      const result = await request({ op: 'read', model: 'sc.business.category', ids: [baseline.id], fields: ['id', 'code', 'attachment_policy'] });
      assert.equal(result.ok, true);
      assert.equal(result.data?.records?.length, 1);
      return result.data.records[0];
    };
    const recovery = { database: 'sc_frontend_acceptance', role: 'fixture_role_config_admin', baseline, restored: false };
    const recoveryPath = path.join(out, 'expense-policy-recovery.json');
    await fs.writeFile(recoveryPath, JSON.stringify(recovery, null, 2));
    report.expensePolicy = recovery;
    const finance = await login('fixture_role_finance');
    const expenseEntry = resolveEntry('smart_construction_core.menu_sc_reimbursement_request');
    const observe = async (value, stage) => {
      const start = report.contractResponses?.length || 0;
      await form(finance.page, `/f/sc.expense.claim/new?menu_id=${expenseEntry.menu_id}&action_id=${expenseEntry.action_id}`, `expense-policy-${stage}`);
      const authority = (report.contractResponses || []).slice(start).map((row) => findRecordAuthority(row.contract))
        .findLast((row) => row?.model === 'sc.expense.claim' && !Number(row.mainData?.id));
      check(`policy ${stage}: effective contract value`, authority?.mainData?.submission_attachment_policy === value);
      await finance.page.getByRole('button', { name: '提交审批', exact: true }).click();
      const message = value === 'required' ? '当前业务分类要求上传附件后才能提交、批准或完成。' : '请先补充必填信息，再保存草稿或提交。';
      await finance.page.getByText(message, { exact: true }).first().waitFor();
      check(`policy ${stage}: submission feedback`, true);
      await finance.page.screenshot({ path: path.join(out, `expense-policy-${stage}-feedback.png`) });
    };
    const change = async (value, label) => {
      const start = report.contractResponses?.length || 0;
      await form(admin.page, `/f/sc.business.category/${baseline.id}?menu_id=${categoryEntry.menu_id}&action_id=${categoryEntry.action_id}`, `expense-policy-admin-${value}`);
      const authority = (report.contractResponses || []).slice(start).map((row) => findRecordAuthority(row.contract))
        .findLast((row) => row?.model === 'sc.business.category' && Number(row.mainData?.id) === baseline.id);
      const save = authority?.actions?.actionRuleList?.find((row) => row.actionSemantics?.purpose === 'save_draft');
      check('policy: authorized save action', save?.enabled === true && save.target?.operation === 'write');
      await admin.page.locator('[data-field-name="attachment_policy"] input').click();
      // Select options carry their text as the standard `title` attribute; the
      // vendor class is not part of the declared public surface here.
      await admin.page.locator('li[title]:visible').filter({ hasText: label }).click();
      expensePolicyPermit = { id: baseline.id, value };
      const response = admin.page.waitForResponse((res) => {
        try { const body = res.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'write'; } catch { return false; }
      });
      const [saved] = await Promise.all([response, admin.page.getByRole('button', { name: save.label, exact: true }).click()]);
      assert.equal((await saved.json()).ok, true);
      check(`policy ${value}: authoritative readback`, (await read()).attachment_policy === value);
    };
    try {
      await observe('required', 'before');
      await change('recommended', '建议上传');
      await observe('recommended', 'changed');
      await change('required', '必须上传');
      await observe('required', 'restored');
    } finally {
      expensePolicyPermit = null;
      const current = await read();
      assert.equal(current.code, baseline.code);
      assert.ok(['required', 'recommended'].includes(current.attachment_policy), 'external configuration change; refuse overwrite');
      if (current.attachment_policy !== baseline.attachment_policy) {
        expensePolicyPermit = { id: baseline.id, value: baseline.attachment_policy };
        const restored = await request({ op: 'write', model: 'sc.business.category', ids: [baseline.id], vals: { attachment_policy: baseline.attachment_policy } });
        assert.equal(restored.ok, true);
      }
      expensePolicyPermit = null;
      assert.deepEqual(await read(), baseline);
      recovery.restored = true;
      await fs.writeFile(recoveryPath, JSON.stringify(recovery, null, 2));
      check('policy: baseline restored', true);
    }
    await finance.ctx.close();
    await admin.ctx.close();
  } else if (['favorite-lifecycle', 'favorite-lifecycle-resume', 'favorite-active-delete', 'favorite-active-delete-resume'].includes(process.env.TPL07_SCOPE)) {
    const finance = await login('fixture_role_finance');
    const page = finance.page;
    await list(page, 545, 'favorite-lifecycle-list');
    async function readFavorite() {
      const response = await page.evaluate(async (name) => {
        const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
        return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
          method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
          body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model: 'ir.filters', fields: ['id', 'name', 'user_id', 'model_id', 'action_id', 'is_default'], domain: [['name','=',name],['user_id','=',30],['model_id','=','payment.request'],['action_id','=',775]], limit: 2 } }),
        })).json();
      }, lifecycleName);
      check('favorite lifecycle: authoritative query succeeds', response.ok === true && Array.isArray(response.data?.records));
      return response.data.records;
    }
    const baseline = await readFavorite();
    const resuming = ['favorite-lifecycle-resume', 'favorite-active-delete-resume'].includes(process.env.TPL07_SCOPE);
    if (resuming) {
      const originalPath = process.env.TPL07_SCOPE === 'favorite-active-delete-resume'
        ? 'artifacts/frontend-web-fix-20260928/tpl07-1790769721849/report.json'
        : 'artifacts/frontend-web-fix-20260928/tpl07-1790769469765/report.json';
      const original = JSON.parse(await fs.readFile(path.join(root, originalPath)));
      const created = original.favoriteCreated?.[0];
      check('favorite lifecycle: resume exact previously observed private record', original.favoriteSaved?.ok === true
        && created?.id === original.favoriteSaved?.data?.id && baseline.length === 1 && JSON.stringify(baseline[0]) === JSON.stringify(created));
      report.carriedForwardSave = originalPath;
    } else check('favorite lifecycle: named private configuration initially absent', baseline.length === 0);
    check('favorite lifecycle: explicit save authority', report.savedSearchAuthority?.save_enabled === true);
    const menu = page.getByRole('button', { name: '展开搜索菜单', exact: true });
    let id = baseline[0]?.id;
    await menu.click();
    if (!resuming) {
    await page.getByRole('button', { name: report.savedSearchAuthority.label, exact: true }).click();
    const name = page.getByPlaceholder('收藏名称', { exact: true });
    await name.fill(lifecycleName);
    favoriteWritePermit = { intent: 'search.favorite.set' };
    const saveResponse = page.waitForResponse((response) => response.request().postData()?.includes('search.favorite.set'), { timeout: 15000 });
    await page.getByRole('button', { name: /^保存/ }).click();
    const saved = await (await saveResponse).json();
    report.favoriteSaved = saved;
    check('favorite lifecycle: server accepted save', saved.ok === true && Number(saved.data?.id) > 0);
    const rows = await readFavorite();
    report.favoriteCreated = rows;
    check('favorite lifecycle: exact private nondefault record read back', rows.length === 1 && rows[0].id === saved.data.id && rows[0].is_default === false);
    id = rows[0].id;
    await name.waitFor({ state: 'detached' });
    }
    // The menu stays open after saving; the refreshed contract supplies deletion.
    const deleteButton = page.getByRole('button', { name: `删除收藏：${lifecycleName}`, exact: true });
    await deleteButton.waitFor();
    check('favorite lifecycle: refreshed menu supplies product delete action', await deleteButton.isEnabled());
    await page.reload();
    await page.locator('[data-list-card-container="official"]').waitFor();
    await menu.click();
    await deleteButton.waitFor();
    check('favorite lifecycle: reload retains saved item and deletion grant', await deleteButton.isEnabled());
    const activeDeletion = process.env.TPL07_SCOPE.startsWith('favorite-active-delete');
    if (activeDeletion) {
      await page.getByRole('button', { name: lifecycleName, exact: true }).click();
      await page.waitForURL((url) => url.searchParams.get('saved_filter') === lifecycleName);
      await menu.click();
      check('favorite lifecycle: saved filter can be applied', await page.locator('[aria-pressed]').filter({ hasText: lifecycleName }).evaluateAll((nodes) => nodes.length > 0 && nodes.every((node) => node.getAttribute('aria-pressed') === 'true')));
    }
    for (const width of activeDeletion ? [390] : [1440, 390]) {
      await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
      if (!(await deleteButton.isVisible())) await menu.click();
      await deleteButton.click();
      const dialog = page.getByRole('dialog', { name: '删除收藏', exact: true });
      await dialog.waitFor();
      check(`favorite-${width}: official confirmation`, await dialog.getAttribute('data-semantic-driver') === 'tdesign-dialog');
      check(`favorite-${width}: deletion scope explained`, (await dialog.innerText()).includes('不删除业务记录'));
      check(`favorite-${width}: confirmation fits viewport`, await dialog.evaluate((el) => { const r = el.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; }));
      await page.screenshot({ animations: 'disabled', path: path.join(out, `favorite-delete-${width}.png`) });
      await dialog.getByRole('button', { name: '取消', exact: true }).click();
      await dialog.waitFor({ state: 'detached' });
    }
    check('favorite lifecycle: cancel preserved exact record', (await readFavorite())[0]?.id === id);
    await menu.click();
    await deleteButton.click();
    const dialog = page.getByRole('dialog', { name: '删除收藏', exact: true });
    favoriteWritePermit = { intent: 'search.favorite.delete', id, abort: true };
    await dialog.getByRole('button', { name: '确认删除', exact: true }).click();
    await dialog.getByRole('alert').waitFor();
    check('favorite lifecycle: failed deletion retains confirmation', await dialog.isVisible());
    check('favorite lifecycle: failed deletion preserved record', (await readFavorite())[0]?.id === id);
    favoriteWritePermit = { intent: 'search.favorite.delete', id };
    const deleteResponse = page.waitForResponse((response) => response.request().postData()?.includes('search.favorite.delete'), { timeout: 15000 });
    await dialog.getByRole('button', { name: '确认删除', exact: true }).click();
    const deleted = await (await deleteResponse).json();
    report.favoriteDeleted = deleted;
    check('favorite lifecycle: server confirms exact deletion', deleted.ok === true && deleted.data?.deleted === true && deleted.data?.id === id);
    await dialog.waitFor({ state: 'detached' });
    check('favorite lifecycle: authoritative state restored', (await readFavorite()).length === 0);
    if (activeDeletion) {
      await page.waitForURL((url) => !url.searchParams.get('saved_filter'));
      check('favorite lifecycle: deleting selected filter clears route state', !new URL(page.url()).searchParams.get('saved_filter'));
    }
    check('favorite lifecycle: refreshed menu removed deleted entry', await deleteButton.count() === 0);
    await page.reload();
    await page.locator('[data-list-card-container="official"]').waitFor();
    await menu.click();
    check('favorite lifecycle: reload retains restoration', await page.getByText(lifecycleName, { exact: true }).count() === 0);
    await finance.ctx.close();
  } else if (process.env.TPL07_SCOPE === 'task-authority') {
    const finance = await login('fixture_role_finance');
    const taskOriginId = (await resolveGovernedOrigin(finance.page)).id;
    await form(finance.page, `/f/payment.request/${taskOriginId}?menu_id=545&action_id=775`, 'task-authority');
    const authority = report.taskAuthorities?.['payment.request'];
    check('task: actual payment authority received', authority?.model === 'payment.request');
    check('task: native tree is sole layout authority', authority.structure?.layoutPolicy === 'container_tree_authority');
    check('task: retired slots remain empty', Array.isArray(authority.structure?.slots) && authority.structure.slots.length === 0);
    check('task: effective native tree is present', Boolean(authority.layout?.containerTree));
    const matrix = JSON.parse(await fs.readFile(path.join(root, 'config/p1_payment_request_field_completeness_v1.json')));
    const rules = matrix.field_rules.filter((row) => row.model === 'payment.request' && row.surfaces.some((surface) => ['edit', 'create_edit'].includes(surface)));
    check('task: existing P1 field responsibilities are nonempty', rules.length > 0);
    const fieldReferences = new Set(Object.keys(authority.mainData || {}));
    function collectFieldReferences(node) {
      if (!node || typeof node !== 'object') return;
      if (node.fieldCode) fieldReferences.add(node.fieldCode);
      if (node.type === 'field' && node.name) fieldReferences.add(node.name);
      for (const child of Object.values(node)) collectFieldReferences(child);
    }
    collectFieldReferences(authority.layout.containerTree);
    for (const field of Object.keys(authority.structure.sourceAuthority?.governance_source?.fieldSemanticRoles || {})) fieldReferences.add(field);
    // The P1 native payment view explicitly removes this duplicate heading
    // field; business_category_id remains the authoritative handling input.
    const retiredDuplicateFields = ['payment_flow_label'];
    const missingDeclarations = rules.filter((row) => !fieldReferences.has(row.field) && !retiredDuplicateFields.includes(row.field)).map((row) => row.field);
    report.taskFieldCoverage = { ruleCount: rules.length, missingDeclarations, retiredDuplicateFields };
    check('task: P1 handling fields declared by contract', missingDeclarations.length === 0, { missingDeclarations });
    // Only unconditional required user inputs are asserted unconditionally.
    // Conditional facts keep their backend modifiers; no inferred applicability.
    for (const row of rules.filter((row) => row.classification === 'required' && row.applicability === 'always')) {
      check(`task: required ${row.field} visible`, await finance.page.locator(`[data-field-name="${row.field}"]`).first().isVisible());
    }
    check('task: attachment input retained', await finance.page.locator('[data-field-name="attachment_ids"]').first().isVisible());
    const trace = finance.page.locator('[data-group-title="履约与追溯"]').first();
    await trace.getByRole('button', { name: '履约与追溯', exact: true }).click();
    check('task: declared trace section can expand', await trace.getAttribute('data-collapsed') === 'false');
    check('task: existing record supplies conditional contract and settlement', Boolean(authority.mainData.contract_id && authority.mainData.settlement_id));
    const applicableFacts = rules.filter((row) => ['contract_selected', 'settlement_selected'].includes(row.applicability));
    check('task: conditional fact scope is nonempty', applicableFacts.length > 0);
    for (const row of applicableFacts) {
      check(`task: applicable ${row.field} visible`, await finance.page.locator(`[data-field-name="${row.field}"]`).first().isVisible());
    }
    check('task: pay record does not expose receipt-only notebook', await trace.getByText('收款发票明细', { exact: true }).count() === 0);
    report.traceControls = await trace.evaluate((el) => ({ text: el.innerText, controls: [...el.querySelectorAll('[role],button')].map((node) => ({ tag: node.tagName, role: node.getAttribute('role'), text: node.textContent?.trim() })) }));
    await finance.page.screenshot({ animations: 'disabled', path: path.join(out, 'trace-before-tabs.png') });
    await trace.getByText('付款记录', { exact: true }).click();
    check('task: declared payment relation is reachable', await trace.locator('[data-field-name="ledger_line_ids"]').isVisible());
    await trace.getByText('历史金额确认', { exact: true }).click();
    const historical = trace.locator('[data-field-name="accepted_amount_uppercase"]');
    check('task: historical fact is reachable', await historical.isVisible());
    check('task: historical fact remains readonly', await historical.locator('input, textarea').count() === 0);
    check('task: historical empty text follows declared semantics', (await historical.innerText()).includes('无历史确认记录'));
    await trace.getByText('结算与来源匹配', { exact: true }).click();
    check('task: trace return restores settlement facts', await trace.locator('[data-field-name="paid_amount_total"]').isVisible());
    report.taskPresentation = [];
    for (const width of [1440, 390]) {
      await finance.page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
      report.taskPresentation.push(await finance.page.evaluate(() => ({
        width: innerWidth,
        fields: [...document.querySelectorAll('[data-field-name]')].map((el) => ({
          name: el.getAttribute('data-field-name'), visible: Boolean(el.getClientRects().length),
        })),
        groups: [...document.querySelectorAll('[data-group-title]')].map((el) => ({
          title: el.getAttribute('data-group-title'), columns: getComputedStyle(el).gridTemplateColumns,
        })),
      })));
      const geometry = await finance.page.evaluate(() => {
        const first = document.querySelector('[data-field-name="project_id"]')?.getBoundingClientRect();
        const second = document.querySelector('[data-field-name="partner_id"]')?.getBoundingClientRect();
        return first && second ? { first: { x: first.x, y: first.y }, second: { x: second.x, y: second.y } } : null;
      });
      check(`task-${width}: responsive field geometry`, Boolean(geometry) && (width > 600
        ? Math.abs(geometry.first.y - geometry.second.y) < 2 && geometry.second.x > geometry.first.x
        : Math.abs(geometry.first.x - geometry.second.x) < 2 && geometry.second.y > geometry.first.y), { geometry });
      check(`task-${width}: one official form composition`, await finance.page.locator('[data-form-composition="official-standard-form"]').count() === 1);
      check(`task-${width}: no page overflow`, await finance.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await finance.page.screenshot({ animations: 'disabled', path: path.join(out, `task-authority-${width}.png`), fullPage: true });
    }
    check('task: startup authority loaded', report.startup.some((row) => row.intent === 'system.init' && row.success));
    await finance.ctx.close();
  } else if (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_PAYMENT_REVIEW_RESUME === '201') {
    const original = JSON.parse(await fs.readFile(path.join(root, 'artifacts/frontend-web-fix-20260928/tpl07-1790824095790/expense-success-recovery.json'), 'utf8'));
    check('payment resume: retained record identity', original.id === 201 && original.source.id === 1710
      && original.source.company_id === 8 && original.marker === 'TPL53-PAYMENT-REVIEW-1790824096177');
    paymentReview = { model: original.model, source: original.source, marker: original.marker,
      baseline: original.baseline, id: 201, approvalFlow: true, reviewStage: 2, phase: 'observe' };
    const executive = await login('fixture_role_executive');
    const invoke = (intent, params) => executive.page.evaluate(async ({ intent, params }) => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
        body: JSON.stringify({ intent, params }),
      })).json();
    }, { intent, params });
    const read = () => invoke('api.data', { op: 'read', model: paymentReview.model, ids: [201],
      fields: ['id', 'name', 'state', 'validation_status', 'company_id', 'payment_request_id', 'note'], context: { company_id: 8 } });
    const before = await read();
    report.paymentResumeBefore = before;
    const record = before.data?.records?.[0];
    check('payment resume: current user reads pending owned-scope record', before.ok === true && record?.id === 201
      && record.company_id?.[0] === 8 && record.payment_request_id?.[0] === 1710 && record.note === original.marker
      && record.state === 'draft' && record.validation_status === 'pending');
    const [workspaceResponse] = await Promise.all([
      executive.page.waitForResponse(response => {
        try { const b = response.request().postDataJSON(); return b?.intent === 'my.work.summary' && b.params?.product_workspace === true; } catch { return false; }
      }), executive.page.goto(`${base}/my-work`),
    ]);
    const workspace = await workspaceResponse.json();
    report.paymentResumeWorkspace = workspace;
    const item = workspace.data?.product_workspace?.sections?.flatMap(section => section.items || [])
      .find(item => item.target?.model === paymentReview.model && item.target.record_id === 201);
    check('payment resume: actual assigned second-stage task', item?.target?.work_item_origin?.source === 'tier.review'
      && item.target.work_item_origin.id === 505);
    paymentReview.origin = item.target.work_item_origin;
    await executive.page.locator('[data-work-item-key]').filter({ hasText: record.name })
      .getByRole('button', { name: '打开详情', exact: true }).click();
    await executive.page.getByRole('button', { name: '审批通过', exact: true }).waitFor();
    paymentReview.phase = 'approve';
    await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
    const [approvalResponse] = await Promise.all([
      executive.page.waitForResponse(response => {
        try { const b = response.request().postDataJSON(); return b?.intent === 'execute_button' && b.params?.model === paymentReview.model && b.params?.res_id === 201; } catch { return false; }
      }), executive.page.getByRole('button', { name: '审批通过', exact: true }).click(),
    ]);
    report.paymentResumeApproval = await approvalResponse.json();
    check('payment resume: second reviewer approval succeeds', report.paymentResumeApproval.ok === true && paymentReview.phase === 'done');
    report.paymentResumeAfter = await read();
    const after = report.paymentResumeAfter.data?.records?.[0];
    check('payment resume: final state confirmed and validated', after?.state === 'confirmed' && after.validation_status === 'validated');
    const finalWorkspace = await invoke('my.work.summary', { product_workspace: true });
    check('payment resume: completed task removed', finalWorkspace.ok === true && !(finalWorkspace.data?.product_workspace?.sections || [])
      .flatMap(section => section.items || []).some(item => item.target?.model === paymentReview.model && item.target.record_id === 201));
    const detail = executive.page.locator('[data-form-model="sc.payment.execution"][data-form-record="201"][data-detail-composition="official-standard-detail"][data-state="ok"]');
    await detail.getByText(/状态[：:]\s*已确认/).first().waitFor();
    for (const width of [1440, 390]) {
      await executive.page.setViewportSize({ width, height: 950 });
      check(`payment resume ${width}: no page overflow`, await executive.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
      await executive.page.screenshot({ path: path.join(out, `payment-resume-${width}.png`), fullPage: true });
    }
    await executive.ctx.close();
  } else if (process.env.TPL07_SCOPE === 'approval-actions' && (process.env.TPL07_PAYMENT_REVIEW_CAPTURE === '1' || process.env.TPL07_PAYMENT_REVIEW_SUCCESS === '1')) {
    paymentReview = { model: 'sc.payment.execution', source: { id: 1710, company_id: 8 },
      marker: `TPL53-PAYMENT-REVIEW-${Date.now()}`, phase: 'prepare' };
    await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
    const preflight = await expenseCleanup('preflight');
    check('payment review: exact current baseline captured', preflight.status === 'preflight' && preflight.baseline.execution_ids.includes(186));
    paymentReview.baseline = preflight.baseline;
    paymentReview.approvalToggle = process.env.TPL07_PAYMENT_APPROVAL_TOGGLE === '1';
    paymentReview.approvalFlow = process.env.TPL07_PAYMENT_APPROVAL_FLOW === '1';
    check('payment configuration: one configuration mode', !(paymentReview.approvalToggle && paymentReview.approvalFlow));
    await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
    if (paymentReview.approvalToggle || paymentReview.approvalFlow) {
      check('payment toggle: complete success journey selected', process.env.TPL07_PAYMENT_REVIEW_SUCCESS === '1');
      const admin = await login('fixture_role_config_admin');
      const entry = report.routeAuthority?.primary_actions?.find(row => row.model === 'payment.request');
      check('payment toggle: published parent authorized', Number.isInteger(entry?.action_id));
      await admin.page.goto(`${base}/admin/business-config?model=payment.request&action_id=${entry.action_id}&menu_id=${entry.menu_id}`);
      await admin.page.getByRole('tab', { name: '审批规则', exact: true }).click();
      await admin.page.getByRole('button', { name: '配置审批规则', exact: true }).click();
      const panel = admin.page.locator('.approval-panel');
      await panel.getByText('保存状态：已同步', { exact: true }).waitFor();
      await panel.getByLabel('审批对象', { exact: true }).click();
      const [loaded] = await Promise.all([
        admin.page.waitForResponse(response => {
          try { const b = response.request().postDataJSON(); return b?.intent === 'sc.approval_policy.config.get' && b.params?.model === paymentReview.model; } catch { return false; }
        }),
        admin.page.getByText('付款执行', { exact: true }).last().click(),
      ]);
      paymentReview.configContext = loaded.request().postDataJSON()?.params?.context;
      check('payment toggle: actual request company context', paymentReview.configContext?.company_id === 8);
      const original = await loaded.json();
      report.paymentToggleOriginal = original;
      check('payment toggle: original policy18 loaded', original.ok === true && original.data?.policy?.id === 18
        && original.data.policy.approval_required === true && original.data.policy.mode === 'single');
      await panel.getByText('保存状态：已同步', { exact: true }).waitFor();
      if (paymentReview.approvalFlow) {
        const steps = paymentReviewFlowSteps(paymentReview);
        check('payment flow: original finance step supports sequential extension', Array.isArray(steps));
        await panel.getByRole('textbox', { name: '第1步名称', exact: true }).fill(steps[0].name);
        await panel.getByRole('button', { name: '添加步骤', exact: true }).click();
        await panel.getByRole('textbox', { name: '第2步名称', exact: true }).fill(steps[1].name);
        await panel.getByLabel('第2步审批岗位', { exact: true }).click();
        await admin.page.getByText('管理层/总经理终审', { exact: true }).last().click();
        paymentReview.phase = 'flow_config';
      } else {
        await panel.getByText('启用审批', { exact: true }).click();
        check('payment toggle: visible control disables approval', !await panel.getByRole('checkbox', { name: '启用审批', exact: true }).isChecked());
        paymentReview.phase = 'config_disable';
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
      await panel.getByRole('button', { name: '保存审批设置', exact: true }).click();
      await admin.page.getByRole('dialog', { name: '确认配置影响', exact: true }).getByRole('button', { name: '确认继续', exact: true }).click();
      await admin.page.getByText('审批设置已保存', { exact: true }).waitFor();
      if (paymentReview.approvalFlow) {
        const saved = report.paymentReviewWrites?.find(row => row.kind === 'flow_steps')?.result;
        check('payment flow: sequential configuration saved', paymentReview.phase === 'flow_configured'
          && saved?.ok === true && saved.data?.policy?.mode === 'linear'
          && saved.data.policy.steps.filter(step => step.active).map(step => step.approval_scope_key).join(',') === 'finance_manager,executive');
      } else {
        const saved = report.paymentReviewWrites?.find(row => row.kind === 'config_disable')?.result;
        check('payment toggle: disabled policy saved without step mutation', paymentReview.phase === 'config_disabled'
          && saved?.ok === true && saved.data?.policy?.approval_required === false && saved.data.policy.mode === 'none');
      }
      await admin.page.screenshot({ path: path.join(out, 'payment-approval-configured.png'), fullPage: true });
      await admin.ctx.close();
    }
    paymentReview.phase = 'open';
    await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
    let manager = await login('fixture_role_pfl035_finance_user');
    await manager.page.goto(`${base}/r/payment.request/1710?action_id=775&menu_id=545`);
    await manager.page.getByRole('button', { name: '生成付款登记', exact: true }).click();
    await manager.page.waitForURL(url => url.pathname === '/f/sc.payment.execution/new');
    check('payment review: native continuation opened', paymentReview.phase === 'opened');
    paymentReview.paymentDate = await manager.page.locator('[data-field-name="date_payment"] input').first().inputValue();
    check('payment review: contract date default is present', /^\d{4}-\d{2}-\d{2}$/.test(paymentReview.paymentDate));
    const values = { paid_amount: '1', payment_account_name: 'FE Company A Operating Account',
      payment_bank_name: 'FE Construction Bank', payment_account_no: 'FE-PAYER-0001', payment_method: '银行转账', note: paymentReview.marker };
    for (const [field, value] of Object.entries(values)) {
      await manager.page.locator(`[data-field-name="${field}"] input, [data-field-name="${field}"] textarea`).first().fill(value);
    }
    paymentReview.phase = 'capture';
    await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
    const [response] = await Promise.all([
      manager.page.waitForResponse(response => {
        try { const b = response.request().postDataJSON(); return b?.intent === 'api.data' && b.params?.op === 'create' && b.params.model === paymentReview.model; } catch { return false; }
      }, { timeout: 15000 }),
      manager.page.getByRole('button', { name: /^保存(?:草稿)?$/ }).first().click(),
    ]);
    check('payment review: create request captured without write', response.status() === 503 && paymentReview.phase === 'captured' && Boolean(report.paymentReviewCreateCapture));
    check('payment review: actual capture satisfies native defaults and source baseline',
      paymentReviewWriteKind('fixture_role_pfl035_finance_user', report.paymentReviewCreateCapture, { ...paymentReview,
        phase: 'create', request: report.paymentReviewCreateCapture?.params }) === 'create');
    await manager.page.screenshot({ path: path.join(out, 'payment-review-create-capture.png') });
    if (process.env.TPL07_PAYMENT_REVIEW_SUCCESS === '1') {
      const persist = () => fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
      const invoke = (page, intent, params) => page.evaluate(async ({ intent, params }) => {
        const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
        return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
          method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
          body: JSON.stringify({ intent, params }),
        })).json();
      }, { intent, params });
      const read = page => invoke(page, 'api.data', { op: 'read', model: paymentReview.model, ids: [paymentReview.id],
        fields: ['id', 'name', 'state', 'validation_status', 'company_id', 'payment_request_id', 'paid_amount', 'note'], context: { company_id: 8 } });
      const clickAction = async (page, label, intent, predicate) => {
        const [response] = await Promise.all([
          page.waitForResponse(response => {
            try { const body = response.request().postDataJSON(); return body?.intent === intent && predicate(body.params); } catch { return false; }
          }, { timeout: 20000 }),
          page.getByRole('button', { name: label, exact: typeof label === 'string' }).first().click(),
        ]);
        return response.json();
      };
      paymentReview.request = report.paymentReviewCreateCapture.params;
      paymentReview.phase = 'create';
      await persist();
      report.paymentReviewSaved = await clickAction(manager.page, /^保存(?:草稿)?$/, 'api.data', p => p?.op === 'create' && p.model === paymentReview.model);
      check('payment review: exact save succeeds once', report.paymentReviewSaved.ok === true && paymentReview.phase === 'created'
        && Number.isInteger(paymentReview.id) && paymentReview.id > 0 && !paymentReview.baseline.execution_ids.includes(paymentReview.id));
      await manager.page.waitForURL(url => ['/r/', '/f/'].some(prefix => url.pathname === `${prefix}sc.payment.execution/${paymentReview.id}`));
      await manager.page.waitForLoadState('domcontentloaded');
      report.paymentReviewCreated = await read(manager.page);
      const created = report.paymentReviewCreated.data?.records?.[0];
      check('payment review: actual created ownership and draft readback', report.paymentReviewCreated.ok === true
        && created?.id === paymentReview.id && created.state === 'draft' && created.company_id?.[0] === 8
        && created.payment_request_id?.[0] === 1710 && created.paid_amount === 1 && created.note === paymentReview.marker);
      const operator = manager;
      await operator.page.goto(`${base}/r/sc.payment.execution/${paymentReview.id}?action_id=803&menu_id=335`);
      await operator.page.getByRole('button', { name: '提交审批', exact: true }).waitFor();
      paymentReview.phase = 'submit';
      await persist();
      report.paymentReviewSubmitted = await clickAction(operator.page, '提交审批', 'execute_button', p => p?.model === paymentReview.model && p.res_id === paymentReview.id);
      check('payment review: ordinary operator submitted', report.paymentReviewSubmitted.ok === true && paymentReview.phase === 'submitted');
      report.paymentReviewWaiting = await read(operator.page);
      const waiting = report.paymentReviewWaiting.data?.records?.[0];
      if (paymentReview.approvalToggle) {
        check('payment toggle: same operator submit automatically confirms', waiting?.state === 'confirmed' && waiting.validation_status === 'no');
        paymentReview.phase = 'done';
        await persist();
        report.paymentReviewFinal = report.paymentReviewWaiting;
        await operator.page.reload();
      } else {
      check('payment review: configured approval waits', waiting?.state === 'draft' && ['waiting', 'pending'].includes(waiting.validation_status));
      check('payment flow: submitting operator has no reviewer action', await operator.page.getByRole('button', { name: '审批通过', exact: true }).count() === 0);
      const reviewers = paymentReview.approvalFlow ? ['fixture_role_finance', 'fixture_role_executive'] : ['fixture_role_finance'];
      for (const [index, reviewer] of reviewers.entries()) {
      await manager.ctx.close();
      manager = await login(reviewer);
      paymentReview.reviewStage = index + 1;
      const [workspaceResponse] = await Promise.all([
        manager.page.waitForResponse(response => {
          try { const b = response.request().postDataJSON(); return b?.intent === 'my.work.summary' && b.params?.product_workspace === true; } catch { return false; }
        }),
        manager.page.goto(`${base}/my-work`),
      ]);
      const workspace = await workspaceResponse.json();
      const items = workspace.data?.product_workspace?.sections?.flatMap(section => section.items) || [];
      const item = items.find(item => item.target?.model === paymentReview.model && item.target.record_id === paymentReview.id);
      check('payment review: actual reviewer workspace contains assigned execution', Boolean(item?.target?.work_item_origin));
      paymentReview.origin = item.target.work_item_origin;
      report.paymentReviewWorkItem = item;
      await persist();
      const card = manager.page.locator('[data-work-item-key]').filter({ hasText: created.name });
      await card.getByRole('button', { name: '打开详情', exact: true }).click();
      await manager.page.waitForURL(url => url.pathname === `/r/sc.payment.execution/${paymentReview.id}`);
      await manager.page.getByRole('button', { name: '审批通过', exact: true }).waitFor();
      paymentReview.phase = 'approve';
      await persist();
      report.paymentReviewApproved = await clickAction(manager.page, '审批通过', 'execute_button', p => p?.model === paymentReview.model && p.res_id === paymentReview.id);
      check('payment review: assigned reviewer approval succeeds', report.paymentReviewApproved.ok === true && ['first_approved', 'done'].includes(paymentReview.phase));
      report.paymentReviewFinal = await read(manager.page);
      const approved = report.paymentReviewFinal.data?.records?.[0];
      if (paymentReview.approvalFlow && index === 0) {
        check('payment flow: first review cannot finalize second stage', approved?.state === 'draft' && ['pending', 'waiting'].includes(approved.validation_status));
      } else {
        check('payment review: confirmed without cash posting', approved?.state === 'confirmed' && approved.validation_status === 'validated');
      }
      const finalWorkspace = await invoke(manager.page, 'my.work.summary', { product_workspace: true });
      report.paymentReviewFinalWorkspace = finalWorkspace;
      check('payment review: completed item exits reviewer workspace', finalWorkspace.ok === true
        && !(finalWorkspace.data?.product_workspace?.sections || []).flatMap(section => section.items || [])
          .some(item => item.target?.model === paymentReview.model && item.target.record_id === paymentReview.id));
      }
      }
      const finalDetail = manager.page.locator(`[data-form-model="sc.payment.execution"][data-form-record="${paymentReview.id}"][data-detail-composition="official-standard-detail"][data-state="ok"]`);
      await finalDetail.waitFor();
      await manager.page.getByRole('heading', { name: created.name, exact: true }).waitFor();
      await finalDetail.getByText(/状态[：:]\s*已确认/).first().waitFor();
      check('payment review: refreshed official detail shows approved state', await finalDetail.count() === 1
        && await manager.page.getByRole('button', { name: '审批通过', exact: true }).count() === 0);
      for (const width of [1440, 390]) {
        await manager.page.setViewportSize({ width, height: 950 });
        check(`payment review ${width}: final detail no page overflow`,
          await manager.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
        await manager.page.screenshot({ path: path.join(out, `payment-review-approved-${width}.png`), fullPage: true });
      }
    }
    await manager.ctx.close();
  } else if (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_AMOUNT_INSPECT === '1') {
    report.amountCapabilityInspection = [];
    for (const spec of [{ model: 'payment.request', supported: true },
      { model: 'project.project', supported: false, menu: 'smart_construction_core.menu_sc_project_initiation' }]) {
      const admin = await login('fixture_role_config_admin');
      const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
        .flatMap(key => report.routeAuthority?.[key] || []);
      const entry = entries.find(row => row.model === spec.model && (!spec.menu || row.menu_xmlid === spec.menu));
      check(`amount ${spec.model}: actual published configuration entry`, Number.isInteger(entry?.action_id) && entry.action_id > 0 && Number(entry.menu_id) > 0);
      const surfaceResponse = admin.page.waitForResponse(response => {
        try { return response.request().postDataJSON()?.intent === 'ui.business_config.surface.get'; } catch { return false; }
      });
      await admin.page.goto(`${base}/admin/business-config?model=${spec.model}&action_id=${entry.action_id}&menu_id=${entry.menu_id}`);
      const surface = await (await surfaceResponse).json();
      check(`amount ${spec.model}: configuration surface available`, surface.ok === true);
      await admin.page.getByRole('tab', { name: '审批规则', exact: true }).click();
      const configResponse = admin.page.waitForResponse(response => {
        try { const body = response.request().postDataJSON(); return body?.intent === 'sc.approval_policy.config.get' && body.params?.model === spec.model; } catch { return false; }
      });
      await admin.page.getByRole('button', { name: '配置审批规则', exact: true }).click();
      const config = await (await configResponse).json();
      const capability = config.data?.amount_condition;
      check(`amount ${spec.model}: authoritative capability`, config.ok === true && config.data?.model === spec.model
        && capability?.supported === spec.supported && Boolean(capability.field) === spec.supported && Boolean(capability.message));
      const panel = admin.page.locator('.approval-panel');
      await panel.getByText('保存状态：已同步', { exact: true }).waitFor();
      await panel.locator('.approval-amount-message').getByText(capability.message, { exact: true }).waitFor();
      // Unsaved local editing demonstrates usable controls; all configuration writes remain intercepted.
      const enabled = panel.getByRole('checkbox', { name: '启用审批', exact: true });
      if (!(await enabled.isChecked())) await panel.locator('.approval-toggle').click();
      if (!(await panel.locator('.approval-step-row').count())) await panel.getByRole('button', { name: '添加步骤', exact: true }).click();
      check(`amount ${spec.model}: reviewer steps remain editable`, await panel.getByLabel('第1步名称', { exact: true }).isEnabled()
        && await panel.getByLabel('第1步审批岗位', { exact: true }).isEnabled());
      check(`amount ${spec.model}: inputs follow capability`, await panel.getByLabel('第1步金额下限', { exact: true }).count() === Number(spec.supported)
        && await panel.getByLabel('第1步金额上限', { exact: true }).count() === Number(spec.supported));
      for (const width of [1440, 390]) {
        await admin.page.setViewportSize({ width, height: 950 });
        await panel.locator('.approval-amount-message').scrollIntoViewIfNeeded();
        check(`amount ${spec.model} ${width}: no page overflow`, await admin.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
        await admin.page.screenshot({ path: path.join(out, `amount-${spec.model}-${width}.png`) });
      }
      report.amountCapabilityInspection.push({ model: spec.model, entry, config: config.data, unsavedOnly: true });
      await admin.ctx.close();
    }
    check('amount capability inspection: no writes', report.forbiddenWrites.length === 0);
  } else if (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_CONFIG_PUBLISHED_INSPECT === '1') {
    // Read-only user observation; existing write interception remains deny-by-default.
    const admin = await login('fixture_role_config_admin');
    const entry = report.routeAuthority?.primary_actions?.find(row => row.model === 'payment.request');
    check('published approval editor: payment entry authorized', Number.isInteger(entry?.action_id) && entry.action_id > 0);
    const surfaceResponse = admin.page.waitForResponse(response => {
      try { return response.request().postDataJSON()?.intent === 'ui.business_config.surface.get'; } catch { return false; }
    });
    await admin.page.goto(`${base}/admin/business-config?model=payment.request&action_id=${entry.action_id}&menu_id=${entry.menu_id}`);
    const surface = await (await surfaceResponse).json();
    check('published approval editor: configuration surface available', surface.ok === true);
    await admin.page.getByRole('tab', { name: '审批规则', exact: true }).click();
    report.publishedApprovalInspection = { entry, surface: surface.data };
    await fs.writeFile(path.join(out, 'published-approval-surface.json'), JSON.stringify(report.publishedApprovalInspection, null, 2));
    await admin.page.screenshot({ path: path.join(out, 'published-approval-before-open.png') });
    const [configResponse] = await Promise.all([
      admin.page.waitForResponse(response => {
        try { return response.request().postDataJSON()?.intent === 'sc.approval_policy.config.get'; } catch { return false; }
      }, { timeout: 15000 }),
      admin.page.getByRole('button', { name: '配置审批规则', exact: true }).click(),
    ]);
    const config = await configResponse.json();
    check('published approval editor: policy loaded', config.ok === true);
    const panel = admin.page.locator('.approval-panel');
    await panel.getByText('保存状态：已同步', { exact: true }).waitFor();
    check('published approval editor: target selector visible', await panel.getByLabel('审批对象', { exact: true }).isVisible());
    check('published approval editor: switch reflects backend', await panel.getByRole('checkbox', { name: '启用审批', exact: true }).isChecked() === Boolean(config.data?.policy?.approval_required));
    report.publishedApprovalInspection = { entry, surface: surface.data, config: config.data };
    for (const [width, height] of [[1440, 900], [390, 844]]) {
      await admin.page.setViewportSize({ width, height });
      await panel.getByLabel('审批对象', { exact: true }).scrollIntoViewIfNeeded();
      check(`published approval editor: target visible at ${width}`, await panel.getByLabel('审批对象', { exact: true }).isVisible());
      const panelBox = await panel.boundingBox();
      const targetBox = await panel.getByLabel('审批对象', { exact: true }).boundingBox();
      const stepsBox = await panel.locator('.approval-steps').boundingBox();
      check(`published approval editor: content uses panel width at ${width}`, Boolean(panelBox && targetBox && targetBox.width > panelBox.width * 0.7));
      check(`published approval editor: steps remain usable at ${width}`, Boolean(panelBox && stepsBox && stepsBox.width > panelBox.width * 0.45));
      const ruleBox = await panel.getByLabel('审批规则设置', { exact: true }).boundingBox();
      const scopeBox = await panel.getByLabel('默认审批岗位', { exact: true }).boundingBox();
      check(`published approval editor: reviewer selector inside rule column at ${width}`, Boolean(ruleBox && scopeBox && scopeBox.x >= ruleBox.x && scopeBox.x + scopeBox.width <= ruleBox.x + ruleBox.width));
      await admin.page.screenshot({ path: path.join(out, `published-approval-editor-${width}.png`) });
      const save = panel.getByRole('button', { name: '保存审批设置', exact: true });
      await save.scrollIntoViewIfNeeded();
      const saveBox = await save.boundingBox();
      check(`published approval editor: save reachable at ${width}`, Boolean(saveBox && saveBox.x >= 0 && saveBox.x + saveBox.width <= width && saveBox.y >= 0 && saveBox.y + saveBox.height <= height));
      check(`published approval editor: unchanged settings cannot save at ${width}`, await save.isDisabled());
    }
    const declaredTargets = surface.data.sections.find(section => section.key === 'approval')?.target_options || [];
    const child = declaredTargets.find(target => target.value === 'sc.payment.execution');
    check('published approval editor: owned target declared', Boolean(child?.relation_field && child?.label));
    await panel.getByLabel('审批对象', { exact: true }).click();
    const [childResponse] = await Promise.all([
      admin.page.waitForResponse(response => {
        try {
          const body = response.request().postDataJSON();
          return body?.intent === 'sc.approval_policy.config.get' && body.params?.model === child.value;
        } catch { return false; }
      }, { timeout: 15000 }),
      admin.page.getByText(child.label, { exact: true }).last().click(),
    ]);
    const childConfig = await childResponse.json();
    check('published approval editor: owned target readback', childConfig.ok === true && childConfig.data?.policy?.target_model === child.value);
    await panel.getByText('保存状态：已同步', { exact: true }).waitFor();
    check('published approval editor: child switch reflects backend', await panel.getByRole('checkbox', { name: '启用审批', exact: true }).isChecked() === Boolean(childConfig.data?.policy?.approval_required));
    report.publishedApprovalInspection.childConfig = childConfig.data;
    await panel.getByLabel('审批对象', { exact: true }).scrollIntoViewIfNeeded();
    await admin.page.screenshot({ path: path.join(out, 'published-approval-child-390.png') });
    await admin.ctx.close();
  } else if (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_CONFIG_INSPECT === '1') {
    // Read only: establish the actual configuration and distinct reviewer entry
    // before extending the existing exact-write/recovery scope.
    report.planApprovalInspection = [];
    const scopeInspect = process.env.TPL07_APPROVAL_CONFIG_SCOPE_INSPECT === '1';
    for (const role of scopeInspect ? ['fixture_role_config_admin'] : ['fixture_role_config_admin', 'fixture_role_pm', 'fixture_role_executive']) {
      const session = await login(role);
      const request = scopeInspect
        ? { intent: 'ui.business_config.surface.get', params: { business_catalog: true, company_id: 8, model: 'sc.plan', action_id: 655 } }
        : role === 'fixture_role_config_admin'
        ? { intent: 'sc.approval_policy.config.get', params: { model: 'sc.plan.version' } }
        : { intent: 'api.data', params: { op: 'list', model: 'sc.plan', domain: [['project_id', '=', 10]], fields: ['id', 'name', 'state'], limit: 1, context: { company_id: 8 } } };
      const result = await session.page.evaluate(async body => {
        const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
        return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
          method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' }, body: JSON.stringify(body),
        })).json();
      }, request);
      report.planApprovalInspection.push({ role, request, result, routeAuthority: report.routeAuthority });
      if (scopeInspect) {
        report.planConfigurationRouteValidation = await session.page.evaluate(async () => {
          const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
          return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
            method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
            body: JSON.stringify({ intent: 'route.authority.validate', params: { action_id: 655 } }),
          })).json();
        });
      }
      check(`plan approval inspection ${role}: authenticated response`, typeof result.ok === 'boolean');
      await session.ctx.close();
    }
  } else if (process.env.TPL07_SCOPE === 'approval-actions') {
    report.approvalPages = [];
    check('approval scope: supported model selection', !process.env.TPL07_APPROVAL_MODEL || ['sc.expense.claim', 'sc.settlement.adjustment', 'sc.receipt.income', 'sc.financing.loan', 'sc.self.funding.registration', 'sc.treasury.reconciliation', 'sc.output.invoice.adjustment', 'tender.guarantee', 'sc.project.document', 'tender.doc.purchase', 'payment.request', 'sc.contract.event', 'sc.payment.execution', 'sc.plan', 'sc.plan.report', 'sc.construction.diary', 'project.task', 'project.project', 'sc.material.inbound', 'sc.material.acceptance', 'sc.material.purchase.request', 'sc.material.rfq', 'sc.material.settlement', 'sc.equipment.plan', 'sc.equipment.request', 'sc.equipment.usage', 'sc.equipment.settlement', 'sc.labor.plan', 'sc.labor.request', 'sc.material.rental.plan', 'sc.material.rental.order', 'sc.material.rental.settlement', 'sc.safety.plan', 'sc.safety.disclosure', 'sc.subcontract.plan', 'sc.subcontract.request', 'sc.subcontract.settlement', 'sc.attendance.checkin', 'sc.labor.usage', 'sc.labor.settlement'].includes(process.env.TPL07_APPROVAL_MODEL));
    for (const spec of [
      { role: 'fixture_role_pm', model: 'sc.material.inbound', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.acceptance', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.purchase.request', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.rfq', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.project.document', domain: [] },
      { role: 'fixture_role_pm', model: 'tender.doc.purchase', domain: [] },
      { role: 'fixture_role_pm', model: 'tender.guarantee', domain: [] },
      { role: 'fixture_role_project_a_member', model: 'sc.settlement.adjustment', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.expense.claim', domain: [['source_origin', '!=', 'legacy']] },
      { role: 'fixture_role_finance', model: 'sc.receipt.income', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.financing.loan', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.self.funding.registration', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.treasury.reconciliation', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.output.invoice.adjustment', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.equipment.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.equipment.request', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.equipment.usage', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.equipment.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.labor.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.labor.request', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.rental.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.rental.order', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.rental.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.safety.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.safety.disclosure', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.subcontract.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.subcontract.request', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.subcontract.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.attendance.checkin', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.labor.usage', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.labor.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'project.project', stateField: 'lifecycle_state', fields: ['sc_approval_state'], domain: [] },
      { role: 'fixture_role_pm', model: 'project.task', stateField: 'sc_state', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.plan.report', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.construction.diary', domain: [] },
      { role: 'fixture_role_contract_operator', model: 'sc.contract.event', domain: [] },
      { role: 'fixture_role_finance', model: 'payment.request', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.payment.execution', domain: [['state', '=', 'paid']] },
    ].filter((spec) => !process.env.TPL07_APPROVAL_MODEL || spec.model === process.env.TPL07_APPROVAL_MODEL)) {
      const executionLabels = {
        'sc.equipment.usage': ['登记单号', '确认台班'],
        'sc.equipment.settlement': ['结算单号', '确认结算'],
        'sc.attendance.checkin': ['考勤单号', '确认考勤'],
        'sc.labor.usage': ['用工单号', '确认用工'],
        'sc.labor.settlement': ['结算单号', '确认结算'],
      }[spec.model];
      const session = await login(spec.role);
      if (process.env.TPL07_APPROVAL_VIEW === 'create') {
        check('approval create scope: explicit supported form', ['sc.contract.event', 'sc.expense.claim', 'sc.settlement.adjustment', 'sc.receipt.income', 'sc.financing.loan', 'sc.self.funding.registration', 'sc.treasury.reconciliation', 'sc.output.invoice.adjustment', 'tender.guarantee', 'sc.project.document', 'tender.doc.purchase', 'payment.request', 'sc.plan', 'sc.plan.report', 'sc.construction.diary', 'project.task', 'project.project', 'sc.material.inbound', 'sc.material.acceptance', 'sc.material.purchase.request', 'sc.material.rfq', 'sc.material.settlement', 'sc.equipment.plan', 'sc.equipment.request', 'sc.equipment.usage', 'sc.equipment.settlement', 'sc.labor.plan', 'sc.labor.request', 'sc.material.rental.plan', 'sc.material.rental.order', 'sc.material.rental.settlement', 'sc.safety.plan', 'sc.safety.disclosure', 'sc.subcontract.plan', 'sc.subcontract.request', 'sc.subcontract.settlement', 'sc.attendance.checkin', 'sc.labor.usage', 'sc.labor.settlement'].includes(spec.model));
        report.recordAuthority = null;
        const createResponseStart = report.contractResponses?.length || 0;
        let createContext = '';
        if (spec.model === 'project.project') {
          const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
            .flatMap((key) => report.routeAuthority?.[key] || []);
          const matches = entries.filter((row) => row.menu_xmlid === 'smart_construction_core.menu_sc_project_initiation');
          report.projectCreateEntryResolution = { role: spec.role, requestedMenuXmlid: 'smart_construction_core.menu_sc_project_initiation', matches, availableProjectEntries: entries.filter((row) => row.model === 'project.project') };

          check('project create: one authorized initiation entry', matches.length === 1 && Number(matches[0].menu_id) > 0 && Number(matches[0].action_id) > 0);
          report.approvalCreateEntry = matches[0];
          createContext = `?menu_id=${Number(matches[0].menu_id)}&action_id=${Number(matches[0].action_id)}`;
        }
        if (spec.model === 'sc.expense.claim') {
          const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
            .flatMap((key) => report.routeAuthority?.[key] || []);
          const matches = entries.filter((row) => row.menu_xmlid === 'smart_construction_core.menu_sc_reimbursement_request');
          check('expense create: one authorized reimbursement entry', matches.length === 1 && Number(matches[0].menu_id) > 0 && Number(matches[0].action_id) > 0);
          report.approvalCreateEntry = matches[0];
          createContext = `?menu_id=${Number(matches[0].menu_id)}&action_id=${Number(matches[0].action_id)}`;
        }
        if (paymentSourceFlow) {
          const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
            .flatMap(key => report.routeAuthority?.[key] || []);
          const matches = entries.filter(row => row.model === 'payment.request' && Number(row.menu_id) === 545 && Number(row.action_id) === 775);
          check('payment source: one published finance payment entry', matches.length === 1);
          report.approvalCreateEntry = matches[0];
          createContext = '?menu_id=545&action_id=775';
        }
        if (documentFlow || diarySaveProbe || eventSaveProbe || ['sc.plan', 'sc.plan.report'].includes(spec.model)) {
          const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
            .flatMap(key => report.routeAuthority?.[key] || []);
          const entryXmlid = documentFlow ? 'smart_construction_core.menu_sc_site_documents' : spec.model === 'sc.plan.report' ? 'smart_construction_core.menu_sc_plan_report'
            : spec.model === 'sc.plan' ? 'smart_construction_core.menu_sc_plan'
            : eventSaveProbe ? 'smart_construction_core.menu_sc_contract_event' : 'smart_construction_core.menu_sc_construction_diary';
          const matches = entries.filter(row => row.menu_xmlid === entryXmlid);
          check(`${spec.model}: one authorized native entry`, matches.length === 1 && Number(matches[0].menu_id) > 0 && Number(matches[0].action_id) > 0);
          report.approvalCreateEntry = matches[0];
          createContext = `?menu_id=${Number(matches[0].menu_id)}&action_id=${Number(matches[0].action_id)}`;
        }
        await form(session.page, `/f/${spec.model}/new${createContext}`, `${spec.model}-create`);
        // Child relation contracts may arrive last; bind the create observation
        // to the requested parent model within this navigation's responses.
        const authority = (report.contractResponses || []).slice(createResponseStart)
          .map((row) => findRecordAuthority(row.contract))
          .findLast((row) => row?.model === spec.model && !(Number(row.mainData?.id) > 0));
        check(`${spec.model}: new form effective contract`, authority?.model === spec.model);
        report.approvalPages.push({ ...spec, view: 'create', authority });
        if (spec.model === 'sc.plan') {
          for (const field of ['company_id', 'owner_id']) {
            const value = authority.mainData?.[field];
            check(`plan create: ${field} default relation label retained`, Array.isArray(value)
              && typeof value[1] === 'string' && value[1].length > 0
              && await session.page.locator(`[data-field-name="${field}"] input`).first().inputValue() === value[1]);
          }
        }
        if (paymentSourceFlow) {
          const receiptLines = (await fs.readFile(process.env.TPL07_PAYMENT_SOURCE_REPORT, 'utf8')).split('\n')
            .filter(line => line.startsWith('PAYMENT_SOURCE_PREP='));
          check('payment source: unique completed preparation receipt', receiptLines.length === 1);
          const receipt = JSON.parse(receiptLines[0].slice('PAYMENT_SOURCE_PREP='.length));
          check('payment source: exact bounded preparation', receipt.kind === paymentSourceFlow && paymentSourceReceiptValid(receipt));
          const api = params => session.page.evaluate(async params => {
            const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
            return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
              method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
              body: JSON.stringify({ intent: 'api.data', params }),
            })).json();
          }, params);
          const sourceResult = await api({ op: 'read', model: receipt.source_model, ids: [receipt.source_id],
            fields: Object.keys(receipt.readback.record), context: { company_id: 8 } });
          const source = sourceResult.data?.records?.[0];
          check('payment source: finance authoritative source identity', sourceResult.ok === true && paymentSourceReceiptValid(receipt, source));
          const relationQuery = async (field, model, search) => {
            const pending = session.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === model && JSON.stringify(body.params).includes(search); } catch { return false; }
            });
            void pending.catch(() => {});
            await session.page.locator(`[data-field-name="${field}"] input`).first().fill(search);
            const response = await pending, result = await response.json();
            (report.paymentSourceQueries ??= []).push({ field, params: response.request().postDataJSON().params, result });
            check(`payment source: ${field} authorized relation query`, result.ok === true);
            return { params: response.request().postDataJSON().params, rows: result.data?.records || [] };
          };
          const select = async (field, model, search, id) => {
            const queried = await relationQuery(field, model, search);
            const row = queried.rows.find(row => row.id === id && String(row.display_name || row.name).includes(search));
            check(`payment source: ${field} exact ID and rendered label`, Boolean(row));
            await session.page.getByRole('option', { name: String(row.display_name || row.name), exact: true }).click();
            return queried;
          };
          const project = receipt.projects.find(row => row.id === receipt.project_id);
          const other = receipt.projects.find(row => row.id === receipt.other_project_id);
          check('payment source: both governed project labels', Boolean(project?.name && other?.name));
          await select('project_id', 'project.project', project.name, project.id);
          const selected = await select(receipt.source_field, receipt.source_model, receipt.marker, receipt.source_id);
          const hasDomain = (params, projectId) => JSON.stringify(params.domain).includes(JSON.stringify(['project_id', '=', projectId]))
            && JSON.stringify(params.domain).includes(JSON.stringify(['state', '=', 'confirmed']));
          check('payment source: nonempty confirmed source domain bound to selected project', hasDomain(selected.params, project.id));
          await select('project_id', 'project.project', other.name, other.id);
          check('payment source: changing project clears previous source',
            await session.page.locator(`[data-field-name="${receipt.source_field}"] input`).first().inputValue() === '');
          const changed = await relationQuery(receipt.source_field, receipt.source_model, receipt.marker);
          check('payment source: changed project excludes old source', hasDomain(changed.params, other.id)
            && !changed.rows.some(row => row.id === receipt.source_id));
          await session.page.keyboard.press('Escape');
          await select('project_id', 'project.project', project.name, project.id);
          await select(receipt.source_field, receipt.source_model, receipt.marker, receipt.source_id);
          const partner = source[paymentSourceFlow === 'rental' ? 'supplier_id' : 'subcontractor_id'];
          const partnerInput = session.page.locator('[data-field-name="partner_id"] input').first();
          if (!(await partnerInput.inputValue())) await select('partner_id', 'res.partner', partner[1], partner[0]);
          await session.page.locator('[data-field-name="amount"] input').first().fill('100');
          const marker = `TPL53-PAYMENT-SOURCE-${paymentSourceFlow.toUpperCase()}-${Date.now()}`;
          await session.page.locator('[data-field-name="note"] textarea, [data-field-name="note"] input').first().fill(marker);
          const waitCreate = () => session.page.waitForResponse(response => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'create'
              && body.params.model === 'payment.request'; } catch { return false; }
          });
          paymentSourceCapture = true;
          const captured = waitCreate();
          void captured.catch(() => {});
          await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
          await captured;
          await session.page.getByText('付款来源定向载荷捕获，请重试保存', { exact: true }).first().waitFor();
          const category = authority.mainData?.business_category_id;
          paymentSourceSuccess = { receipt, source, marker, menuId: 545, actionId: 775, phase: 'create', id: null,
            dateRequest: authority.mainData?.date_request, businessCategoryId: Array.isArray(category) ? category[0] : category,
            request: structuredClone(report.paymentSourceAttempt) };
          check('payment source: captured payload obeys exact bounded save permit', paymentSourceDraftWriteKind(spec.role,
            { intent: 'api.data', params: paymentSourceSuccess.request }, paymentSourceSuccess) === 'create');
          const saved = waitCreate();
          void saved.catch(() => {});
          await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
          check('payment source: actual ordinary finance draft save', (await (await saved).json()).ok === true && Number(paymentSourceSuccess.id) > 0);
          await session.page.waitForURL(url => url.pathname === `/f/payment.request/${paymentSourceSuccess.id}`, { waitUntil: 'domcontentloaded' });
          const readback = async label => {
            const result = await api({ op: 'read', model: 'payment.request', ids: [paymentSourceSuccess.id],
              fields: ['id', 'note', 'state', 'type', 'project_id', 'company_id', 'partner_id', 'currency_id', 'amount', 'create_uid',
                'rental_settlement_id', 'subcontract_settlement_id'], context: { company_id: 8 } });
            const row = result.data?.records?.[0];
            report.paymentSourceReadbacks ??= []; report.paymentSourceReadbacks.push({ label, result });
            check(`payment source ${label}: persisted draft identity and source`, result.ok === true && row?.id === paymentSourceSuccess.id
              && row.note === marker && row.state === 'draft' && row.type === 'pay' && row.amount === 100
              && row.project_id?.[0] === receipt.project_id && row.company_id?.[0] === 8 && row.partner_id?.[0] === receipt.partner_id
              && row.currency_id?.[0] === receipt.currency_id && row.create_uid?.[0] === 30 && row[receipt.source_field]?.[0] === receipt.source_id
              && !row[paymentSourceFlow === 'rental' ? 'subcontract_settlement_id' : 'rental_settlement_id']);
          };
          await readback('saved');
          await form(session.page, `/f/payment.request/${paymentSourceSuccess.id}${createContext}`, 'payment-source-refresh');
          await readback('refreshed');
          report.paymentSourceScope = { ...paymentSourceSuccess, retainedDevelopmentData: true };
          await session.ctx.close();
          continue;
        }
        if (documentFlow) {
          const api = params => session.page.evaluate(async params => {
            const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
            return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
              method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
              body: JSON.stringify({ intent: 'api.data', params }),
            })).json();
          }, params);
          const classification = await api({ op: 'list', model: 'sc.dictionary',
            domain: [['code', '=', 'ITER-DOC-TYPE'], ['type', '=', 'doc_type']],
            fields: ['id', 'name', 'code', 'type'], limit: 2, context: { company_id: 8 } });
          check('document: PM reads one authorized development classification by code', classification.ok === true
            && classification.data?.records?.length === 1 && classification.data.records[0].code === 'ITER-DOC-TYPE');
          const docType = classification.data.records[0];
          const selectRelation = async (field, model, search, expectedId) => {
            const response = session.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === model && JSON.stringify(body.params).includes(search); } catch { return false; }
            });
            await session.page.locator(`[data-field-name="${field}"] input`).first().fill(search);
            const result = await (await response).json();
            const selected = result.data?.records?.find(row => expectedId ? row.id === expectedId : Number(row.id) > 0 && String(row.display_name || row.name).includes(search));
            check(`document: ${field} returned by PM relation query`, result.ok === true && Boolean(selected));
            await session.page.getByRole('option', { name: String(selected.display_name || selected.name), exact: true }).click();
            return selected;
          };
          const project = await selectRelation('project_id', 'project.project', 'FE Project A');
          await selectRelation('doc_type_id', 'sc.dictionary', docType.name, docType.id);
          const marker = `TPL53-DOCUMENT-FLOW-${Date.now()}`;
          await session.page.locator('[data-field-name="name"] input').first().fill(marker);
          documentCreateCapture = true;
          const captured = session.page.waitForResponse(response => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'create'
              && body.params.model === spec.model; } catch { return false; }
          });
          await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
          await captured;
          await session.page.getByText('工程资料定向载荷捕获，请重试保存', { exact: true }).first().waitFor();
          const responsible = authority.mainData?.responsible_id;
          documentSuccess = { model: spec.model, marker, projectId: project.id, docTypeId: docType.id,
            menuId: Number(report.approvalCreateEntry.menu_id), actionId: Number(report.approvalCreateEntry.action_id),
            responsibleId: Array.isArray(responsible) ? responsible[0] : responsible,
            request: structuredClone(report.documentCreateAttempt), phase: 'create', id: null };
          check('document: exact captured request contains only selected values and unchanged defaults',
            documentFlowWriteKind(spec.role, { intent: 'api.data', params: documentSuccess.request }, documentSuccess) === 'create');
          report.documentScope = { marker, projectId: project.id, docTypeId: docType.id, entry: report.approvalCreateEntry,
            retainedDevelopmentData: true, configuredApprovalCoverage: 'only if observed on this document' };
          const saved = session.page.waitForResponse(response => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'create'
              && body.params.model === spec.model; } catch { return false; }
          });
          await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
          check('document: actual PM save succeeds', (await (await saved).json()).ok === true && Number(documentSuccess.id) > 0);
          await session.page.waitForURL(url => url.pathname === `/f/${spec.model}/${documentSuccess.id}`, { waitUntil: 'domcontentloaded' });
          await session.page.locator(`[data-form-record="${documentSuccess.id}"][data-state="ok"]`).waitFor();
          const read = async label => {
            const result = await api({ op: 'read', model: spec.model, ids: [documentSuccess.id],
              fields: ['id', 'name', 'state', 'project_id', 'doc_type_id', 'company_id', 'validation_status'], context: { company_id: 8 } });
            report.documentReadbacks ??= [];
            report.documentReadbacks.push({ label, result });
            const row = result.data?.records?.[0];
            check(`document ${label}: authoritative identity readback`, result.ok === true && row?.id === documentSuccess.id
              && row.name === marker && row.project_id[0] === project.id && row.doc_type_id[0] === docType.id && row.company_id[0] === 8);
            return row;
          };
          check('document: saved separately as draft', (await read('saved')).state === 'draft');
          const perform = async (page, phase, label) => {
            documentSuccess.phase = phase;
            const response = page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'execute_button'
                && body.params?.model === spec.model && body.params.res_id === documentSuccess.id; } catch { return false; }
            }).then(response => ({ response }), error => ({ error }));
            const direct = page.getByRole('button', { name: label, exact: true });
            if (await direct.count() && await direct.isVisible()) await direct.click();
            else {
              await page.getByRole('button', { name: '更多操作', exact: true }).click();
              await page.getByText(label, { exact: true }).last().click();
            }
            const outcome = await response;
            if (outcome.error) throw outcome.error;
            check(`document: ${phase} succeeds through visible action`, (await outcome.response.json()).ok === true
              && report.documentWrites.filter(row => row.kind === phase && row.result.ok === true).length === 1);
          };
          const observeDocument = async (label, state) => {
            await session.page.goto(`${base}/f/${spec.model}/${documentSuccess.id}${createContext}`);
            const surface = session.page.locator(`[data-form-model="${spec.model}"][data-form-record="${documentSuccess.id}"][data-state="ok"]`);
            await surface.waitFor();
            const actual = (report.contractResponses || []).map(row => findRecordAuthority(row.contract))
              .findLast(row => row?.model === spec.model && Number(row.mainData?.id) === documentSuccess.id);
            check(`document ${label}: loaded contract has actual state`, actual?.mainData?.state === state);
            const readonly = actual.status?.effectiveRenderProfile === 'readonly';
            check(`document ${label}: renderer consumes declared profile`, readonly
              ? await surface.getAttribute('data-detail-composition-reason') === 'contract-readonly-record-view'
              : await surface.getAttribute('data-form-composition') === 'official-standard-form');
            check(`document ${label}: no unknown fields`, await surface.locator('[data-field-fail-closed]').count() === 0);
            report.documentViews ??= [];
            report.documentViews.push({ label, state, profile: actual.status?.effectiveRenderProfile });
            await session.page.screenshot({ path: path.join(out, `document-${label}.png`) });
          };
          await observeDocument('saved', 'draft');
          await perform(session.page, 'submit', '提交审批');
          let submitted = await read('submitted');
          if (submitted.state === 'review') {
            const reviewer = await login('fixture_role_executive');
            const summary = reviewer.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'my.work.summary' && body.params?.product_workspace === true; } catch { return false; }
            });
            await reviewer.page.goto(`${base}/my-work`);
            const workspace = await (await summary).json();
            const item = workspace.data?.product_workspace?.sections?.flatMap(section => section.items)
              .find(item => item.target?.model === spec.model && item.target.record_id === documentSuccess.id);
            check('document: actual executive workspace grants this document review', Boolean(item?.target?.work_item_origin));
            documentSuccess.approvalOrigin = item.target.work_item_origin;
            report.documentReviewTarget = item.target;
            await reviewer.page.locator('[data-work-item-key]').filter({ hasText: marker })
              .getByRole('button', { name: '打开详情', exact: true }).click();
            await reviewer.page.waitForURL(url => url.pathname === `/r/${spec.model}/${documentSuccess.id}`);
            await perform(reviewer.page, 'approve', '审批通过');
            await reviewer.ctx.close();
            submitted = await read('reviewed');
          } else {
            report.documentScope.configuredApprovalCoverage = 'not exercised: actual submission auto-approved; backend configured-review evidence is separate';
          }
          check('document: approval precedes explicit archive', submitted.state === 'approved');
          await observeDocument('approved', 'approved');
          await perform(session.page, 'archive', '归档');
          check('document: explicit archive reaches done', (await read('archived')).state === 'done');
          documentSuccess.phase = 'done';
          await observeDocument('archived', 'done');
          for (const width of [1440, 390]) {
            await session.page.setViewportSize({ width, height: 950 });
            check(`document archived ${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
            await session.page.screenshot({ path: path.join(out, `document-archived-${width}.png`) });
          }
          check('document: no out-of-scope mutation', report.forbiddenWrites.length === 0);
          await session.ctx.close();
          continue;
        }
        if (reportSaveSuccess) {
          const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
            .flatMap(key => report.routeAuthority?.[key] || []);
          const parentEntries = entries.filter(row => row.menu_xmlid === 'smart_construction_core.menu_sc_plan');
          check('report handling: one authorized parent entry', parentEntries.length === 1);
          const api = params => session.page.evaluate(async params => {
            const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
            return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
              method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
              body: JSON.stringify({ intent: 'api.data', params }),
            })).json();
          }, params);
          const marker = `TPL53-REPORT-SAVE-${Date.now()}`;
          const parentName = marker.replace('REPORT-SAVE', 'REPORT-PARENT');
          const content = '临时验收计划汇报：核对官方表单提交和详情返回。';
          const parentRequest = { op: 'create', model: 'sc.plan', vals: { name: parentName, project_id: 10 },
            context: { company_id: 8, menu_id: Number(parentEntries[0].menu_id), action_id: Number(parentEntries[0].action_id) } };
          reportSuccess = { model: spec.model, marker, planExecutionProbe: planExecution, versionProbe: planVersionSave, versionSubmitProbe: planVersionSubmit, versionReviewProbe: planVersionReview, parentRequest, parentId: null, id: null, request: null, phase: 'prepare' };
          await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
          const recovery = await expenseCleanup('preflight');
          if (planVersionReview) {
            reportSuccess.approvalBaseline = recovery.approval_baseline;
            check('version review: configuration baseline recorded', Boolean(reportSuccess.approvalBaseline?.reviewer_id));
            await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
            const admin = await login('fixture_role_config_admin');
            await admin.page.goto(`${base}/admin/business-config?model=sc.plan&action_id=${parentRequest.context.action_id}&menu_id=${parentRequest.context.menu_id}`);
            await admin.page.getByRole('tab', { name: '审批规则', exact: true }).click();
            await admin.page.getByRole('button', { name: '配置审批规则', exact: true }).click();
            const panel = admin.page.locator('.approval-panel');
            await panel.getByLabel('审批对象', { exact: true }).click();
            await admin.page.getByText('计划版本', { exact: true }).last().click();
            await panel.getByText(/计划版本：尚未建立审批规则/).waitFor();
            await panel.getByRole('checkbox', { name: '启用审批', exact: true }).check();
            await panel.getByLabel(/默认审批岗位/).click();
            await admin.page.getByText('管理层/总经理终审', { exact: true }).last().click();
            await panel.getByRole('textbox', { name: '第1步名称', exact: true }).fill(`${marker}-审批`);
            reportSuccess.phase = 'version-config';
            await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
            await panel.getByRole('button', { name: '保存审批设置', exact: true }).click();
            await admin.page.getByRole('dialog', { name: '确认配置影响', exact: true }).getByRole('button', { name: '确认继续', exact: true }).click();
            await admin.page.getByText('审批设置已保存', { exact: true }).waitFor();
            check('version review: configuration and steps accepted', reportSuccess.phase === 'done' && report.versionReviewWrites?.length === 2);
            await admin.page.screenshot({ path: path.join(out, 'version-review-configured.png') });
            await admin.ctx.close();
          }
          const projectRead = await api({ op: 'read', model: 'project.project', ids: [10], fields: ['id', 'company_id'], context: { company_id: 8 } });
          check('report handling: parent project authorized', projectRead.ok === true && projectRead.data?.records?.[0]?.company_id?.[0] === 8);
          reportSuccess.phase = 'parent';
          const parent = await api(parentRequest);
          check('report handling: exact temporary parent created', parent.ok === true && Number.isInteger(reportSuccess.parentId) && reportSuccess.parentId > 0);
          if (planExecution) {
            const parentUrl = `/f/sc.plan/${reportSuccess.parentId}?menu_id=${parentRequest.context.menu_id}&action_id=${parentRequest.context.action_id}`;
            const nodeName = marker.replace('REPORT-SAVE', 'PLAN-NODE');
            const collection = session.page.locator('[data-field-name="line_ids"]').first();
            const showNodes = async (label, profile = 'form') => {
              await form(session.page, parentUrl, label, profile);
              await collection.waitFor();
              await collection.scrollIntoViewIfNeeded();
            };
            const saveNode = async phase => {
              const previous = report.planSaveAttempts?.length || 0;
              planSaveCapture = true;
              await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
              await session.page.getByText('计划执行定向保存失败验证', { exact: false }).first().waitFor();
              planSaveCapture = false;
              check(`plan execution ${phase}: one captured attempt`, report.planSaveAttempts.length === previous + 1);
              reportSuccess.planRequest = report.planSaveAttempts.at(-1);
              reportSuccess.phase = phase;
              check(`plan execution ${phase}: exact node write scope`, planExecutionWriteKind('fixture_role_pm', { intent: 'api.data', params: reportSuccess.planRequest }, reportSuccess) === phase);
              await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
              const pending = session.page.waitForResponse(response => {
                try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'write' && body.params.model === 'sc.plan'; } catch { return false; }
              });
              await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
              const result = await (await pending).json();
              check(`plan execution ${phase}: authoritative write accepted`, result.ok === true && reportSuccess.phase === 'done');
            };
            const action = async (phase, label, expected) => {
              const button = session.page.getByRole('button', { name: label, exact: true });
              await button.waitFor();
              reportSuccess.phase = phase;
              await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
              const pending = session.page.waitForResponse(response => {
                try { const body = response.request().postDataJSON(); return body?.intent === 'execute_button' && body.params?.model === 'sc.plan'; } catch { return false; }
              });
              await button.click();
              const result = await (await pending).json();
              check(`plan execution ${phase}: real action succeeds`, result.ok === true && reportSuccess.phase === 'done');
              const read = await api({ op: 'read', model: 'sc.plan', ids: [reportSuccess.parentId], fields: ['id', 'state', 'actual_start', 'actual_finish'], context: { company_id: 8 } });
              report.planExecutionReadbacks ??= [];
              report.planExecutionReadbacks.push(read);
              check(`plan execution ${phase}: state readback`, read.ok === true && read.data.records[0].state === expected);
            };
            await showNodes('plan-execution-draft');
            await collection.getByRole('button').filter({ hasText: /新增|添加/ }).first().click();
            await collection.getByRole('textbox', { name: '节点名称', exact: true }).fill(nodeName);
            await saveNode('node-save');
            const nodes = await api({ op: 'list', model: 'sc.plan.line', domain: [['plan_id', '=', reportSuccess.parentId], ['name', '=', nodeName]], fields: ['id', 'name', 'state', 'progress_rate'], limit: 2, context: { company_id: 8 } });
            check('plan execution: exact saved node', nodes.ok === true && nodes.data.records.length === 1 && nodes.data.records[0].state === 'draft');
            reportSuccess.nodeId = nodes.data.records[0].id;
            await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
            await showNodes('plan-execution-saved');
            await action('plan-confirm', '确认', 'confirmed');
            await showNodes('plan-execution-confirmed', 'readonly');
            await action('plan-start', '开始执行', 'in_progress');
            for (const [phase, percent, stateLabel, state] of [['node-progress', 50, '执行中', 'in_progress'], ['node-done', 100, '已完成', 'done']]) {
              let releaseRead;
              planNodeReadGate = new Promise(resolve => { releaseRead = resolve; });
              try {
                await showNodes(`plan-execution-${phase}`);
                await collection.getByText('正在加载关系记录', { exact: true }).waitFor();
                check(`plan execution ${phase}: pending read cannot be edited`, await collection.getByRole('spinbutton', { name: '完成率(%)', exact: true }).count() === 0);
              } finally {
                planNodeReadGate = null;
                releaseRead();
              }
              await collection.getByRole('textbox', { name: '节点名称', exact: true }).waitFor();
              check(`plan execution ${phase}: baseline hydrated before editing`, await collection.getByRole('textbox', { name: '节点名称', exact: true }).inputValue() === nodeName);
              report.planNodeBeforeEdit ??= [];
              report.planNodeBeforeEdit.push({ phase, values: await collection.locator('input').evaluateAll(nodes => nodes.map(node => ({ label: node.getAttribute('aria-label'), value: node.value, disabled: node.disabled }))) });
              check(`plan execution ${phase}: baseline remains readonly`, await collection.getByRole('textbox', { name: '节点名称', exact: true }).isDisabled());
              await collection.getByRole('spinbutton', { name: '完成率(%)', exact: true }).fill(String(percent));
              await collection.getByRole('textbox', { name: '状态', exact: true }).click();
              await session.page.getByText(stateLabel, { exact: true }).last().click();
              await saveNode(phase);
              const read = await api({ op: 'read', model: 'sc.plan.line', ids: [reportSuccess.nodeId], fields: ['id', 'state', 'progress_rate'], context: { company_id: 8 } });
              check(`plan execution ${phase}: node facts read back`, read.ok === true && read.data.records[0].state === state && read.data.records[0].progress_rate === percent);
            }
            await showNodes('plan-execution-before-complete');
            await action('plan-done', '完成', 'done');
            await showNodes('plan-execution-completed', 'readonly');
            check('plan execution: terminal contract readonly', report.recordAuthority?.status?.effectiveRecordCapabilities?.write === false);
            await collection.getByText(nodeName, { exact: true }).first().waitFor();
            for (const width of [1440, 390]) {
              await session.page.setViewportSize({ width, height: 950 });
              await collection.scrollIntoViewIfNeeded();
              check(`plan execution completed ${width}: no overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
              await session.page.screenshot({ path: path.join(out, `plan-execution-completed-${width}.png`) });
            }
            continue;
          }
          if (planVersionInspect) {
            await form(session.page, `/f/sc.plan/${reportSuccess.parentId}?menu_id=${parentRequest.context.menu_id}&action_id=${parentRequest.context.action_id}`, 'plan-version-parent');
            await session.page.getByText('版本', { exact: true }).click();
            const collection = session.page.locator('[data-field-name="version_ids"]').first();
            await collection.waitFor();
            await collection.scrollIntoViewIfNeeded();
            report.planVersionInspection = {
              parentId: reportSuccess.parentId, url: session.page.url(),
              authority: report.recordAuthority,
              text: await collection.innerText(),
              buttons: await collection.getByRole('button').evaluateAll(nodes => nodes.map(n => ({ text: n.textContent, label: n.getAttribute('aria-label'), disabled: n.disabled }))),
            };
            await session.page.screenshot({ path: path.join(out, 'plan-version-parent-inspection.png') });
            const add = collection.getByRole('button').filter({ hasText: /新增|添加/ }).first();
            check('plan version: shared collection exposes creation', await add.count() === 1 && await add.isEnabled());
            const defaultsResponse = session.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data'
                && body.params?.op === 'default_get' && body.params?.model === 'sc.plan.version'; } catch { return false; }
            });
            await add.click();
            const defaults = await defaultsResponse;
            const defaultsResult = await defaults.json();
            report.planVersionInspection.defaults = { request: defaults.request().postDataJSON(), result: defaultsResult };
            check('plan version: backend default state drives new row', defaultsResult.ok === true && defaultsResult.data?.record?.state === 'draft');
            const versionInput = collection.getByRole('textbox', { name: '版本号', exact: true });
            await versionInput.waitFor();
            const versionNo = planVersionSave ? marker.replace('REPORT-SAVE', 'VERSION-SAVE') : 'TPL53-UNSAVED-VERSION';
            await versionInput.fill(versionNo);
            check('plan version: definition editable after default hydration', await versionInput.inputValue() === versionNo);
            report.planVersionInspection.afterAdd = await collection.innerText();
            report.planVersionInspection.inputs = await collection.locator('input,textarea').evaluateAll(nodes => nodes.map(n => ({ label: n.getAttribute('aria-label'), placeholder: n.getAttribute('placeholder'), value: n.value })));
            check('plan version: draft row has inputs', report.planVersionInspection.inputs.length > 0);
            await session.page.screenshot({ path: path.join(out, 'plan-version-new-row-inspection.png') });
            if (planVersionSave) {
              reportSuccess.versionDefaults = defaultsResult.data.record;
              versionSaveCapture = true;
              await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
              await session.page.getByText('计划版本定向保存失败验证', { exact: false }).first().waitFor();
              check('plan version: failed save preserves input', await versionInput.inputValue() === versionNo && report.versionSaveAttempts?.length === 1);
              versionSaveCapture = false;
              reportSuccess.versionRequest = report.versionSaveAttempts[0];
              reportSuccess.phase = 'version-save';
              check('plan version: captured write belongs to exact temporary parent', reportProbeWriteKind('fixture_role_pm', { intent: 'api.data', params: reportSuccess.versionRequest }, reportSuccess) === 'version-save');
              await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
              const savedResponse = session.page.waitForResponse(response => {
                try { const body = response.request().postDataJSON(); return body?.intent === 'api.data'
                  && body.params?.op === 'write' && body.params.model === 'sc.plan'; } catch { return false; }
              });
              await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
              const savedResult = await (await savedResponse).json();
              check('plan version: real parent save succeeds once', savedResult.ok === true && reportSuccess.phase === 'done'
                && JSON.stringify(report.reportSuccessWrites.map(row => row.kind)) === JSON.stringify(['parent', 'version-save']));
              const saved = await api({ op: 'list', model: 'sc.plan.version', fields: ['id', 'version_no', 'plan_id', 'state', 'revision_type', 'version_date', 'approved_by', 'approved_date'],
                domain: [['plan_id', '=', reportSuccess.parentId], ['version_no', '=', versionNo]], limit: 2, context: { company_id: 8 } });
              report.planVersionSaved = saved;
              const row = saved.data?.records?.[0];
              check('plan version: authoritative draft child readback', saved.ok === true && saved.data.records.length === 1
                && row.state === 'draft' && row.plan_id[0] === reportSuccess.parentId && row.version_no === versionNo
                && row.revision_type === reportSuccess.versionDefaults.revision_type && row.version_date === reportSuccess.versionDefaults.version_date
                && !row.approved_by && !row.approved_date);
              reportSuccess.versionId = row.id;
              await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
              await form(session.page, `/f/sc.plan/${reportSuccess.parentId}?menu_id=${parentRequest.context.menu_id}&action_id=${parentRequest.context.action_id}`, 'plan-version-saved-parent');
              await session.page.getByText('版本', { exact: true }).click();
              await collection.waitFor();
              report.planVersionSavedControls = await collection.getByRole('button').evaluateAll(nodes => nodes.map(n => ({ text: n.textContent, label: n.getAttribute('aria-label') })));
              for (const width of [1440, 390]) {
                await session.page.setViewportSize({ width, height: 950 });
                await collection.scrollIntoViewIfNeeded();
                await collection.getByRole('button', { name: `打开${versionNo}`, exact: true }).scrollIntoViewIfNeeded();
                check(`plan version saved ${width}: open action usable`, await collection.getByRole('button', { name: `打开${versionNo}`, exact: true }).isEnabled());
                check(`plan version saved ${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
                await session.page.screenshot({ path: path.join(out, `plan-version-saved-${width}.png`) });
              }
              if (planVersionSubmit) {
                await session.page.setViewportSize({ width: 1440, height: 950 });
                await collection.getByRole('button', { name: `打开${versionNo}`, exact: true }).click();
                await session.page.waitForURL(url => url.pathname === `/f/sc.plan.version/${row.id}`);
                const submit = session.page.getByRole('button', { name: '提交', exact: true });
                await submit.waitFor();
                report.planVersionOpen = { url: session.page.url(), authority: report.recordAuthority };
                check('plan version: row opens actual child action contract', report.recordAuthority?.model === 'sc.plan.version'
                  && report.recordAuthority.actions?.actionRuleList?.some(action => action.actionSemantics?.purpose === 'submit'));
                const query = new URL(session.page.url()).searchParams;
                reportSuccess.versionActionContext = { menu_id: Number(query.get('menu_id') || 0), action_id: Number(query.get('action_id') || 0) };
                reportSuccess.phase = 'version-submit';
                await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
                const submission = session.page.waitForResponse(response => {
                  try { const body = response.request().postDataJSON(); return body?.intent === 'execute_button'
                    && body.params?.model === 'sc.plan.version' && body.params.res_id === row.id; } catch { return false; }
                });
                await submit.click();
                const submitResult = await (await submission).json();
                report.planVersionSubmitResult = submitResult;
                check('plan version: exact real submit succeeds', submitResult.ok === true && reportSuccess.phase === 'done'
                  && report.reportSuccessWrites.filter(write => write.kind === 'version-submit').length === 1);
                const readback = await api({ op: 'read', model: 'sc.plan.version', ids: [row.id],
                  fields: ['id', 'state', 'plan_id', 'approved_by', 'approved_date'], context: { company_id: 8 } });
                report.planVersionApprovedReadback = readback;
                const approved = readback.data?.records?.[0];
                if (planVersionReview) {
                  check('version review: configured submission waits for reviewer', readback.ok === true && approved?.state === 'draft' && !approved.approved_by && !approved.approved_date);
                  const reviewer = await login('fixture_role_executive');
                  const workspaceResponse = reviewer.page.waitForResponse(response => {
                    try { const body = response.request().postDataJSON(); return body?.intent === 'my.work.summary' && body.params?.product_workspace === true; } catch { return false; }
                  });
                  await reviewer.page.goto(`${base}/my-work`);
                  const workspace = await (await workspaceResponse).json();
                  const item = workspace.data?.product_workspace?.sections?.flatMap(section => section.items).find(item => item.target?.model === 'sc.plan.version' && item.target.record_id === row.id);
                  check('version review: actual current workspace declares assigned version', Boolean(item?.target?.work_item_origin));
                  reportSuccess.approvalOrigin = item.target.work_item_origin;
                  report.versionReviewWorkspace = { target: item.target, counts: workspace.data.product_workspace.counts };
                  await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
                  const card = reviewer.page.locator('[data-work-item-key]').filter({ hasText: versionNo });
                  await card.getByRole('button', { name: '打开详情', exact: true }).click();
                  await reviewer.page.waitForURL(url => url.pathname === `/r/sc.plan.version/${row.id}`);
                  const approve = reviewer.page.getByRole('button', { name: '审批通过', exact: true });
                  await approve.waitFor();
                  await reviewer.page.getByRole('heading', { name: versionNo, exact: true }).waitFor();
                  check('version review: business version title and approval available', await approve.isEnabled());
                  reportSuccess.phase = 'version-approve';
                  await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
                  const approvalResponse = reviewer.page.waitForResponse(response => {
                    try { const body = response.request().postDataJSON(); return body?.intent === 'execute_button' && body.params?.model === 'sc.plan.version'; } catch { return false; }
                  });
                  await approve.click();
                  const result = await (await approvalResponse).json();
                  check('version review: actual executive action succeeds', result.ok === true && reportSuccess.phase === 'done');
                  const final = await api({ op: 'read', model: 'sc.plan.version', ids: [row.id], fields: ['id', 'state', 'approved_by', 'approved_date'], context: { company_id: 8 } });
                  report.versionReviewFinalReadback = final;
                  check('version review: real reviewer and approved state read back', final.ok === true && final.data.records[0].state === 'approved'
                    && final.data.records[0].approved_by[0] === reportSuccess.approvalBaseline.reviewer_id && Boolean(final.data.records[0].approved_date));
                  await reviewer.page.getByText('已确认', { exact: true }).first().waitFor();
                  await reviewer.page.getByRole('heading', { name: versionNo, exact: true }).waitFor();
                  for (const width of [1440, 390]) {
                    await reviewer.page.setViewportSize({ width, height: 950 });
                    check(`version review completed ${width}: no overflow`, await reviewer.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
                    await reviewer.page.screenshot({ path: path.join(out, `version-review-approved-${width}.png`) });
                  }
                  const refreshedResponse = reviewer.page.waitForResponse(response => {
                    try { const body = response.request().postDataJSON(); return body?.intent === 'my.work.summary' && body.params?.product_workspace === true; } catch { return false; }
                  });
                  await reviewer.page.goto(`${base}/my-work`);
                  const refreshed = await (await refreshedResponse).json();
                  check('version review: completed task exits current workspace', !refreshed.data.product_workspace.sections.flatMap(section => section.items)
                    .some(item => item.target?.model === 'sc.plan.version' && item.target.record_id === row.id));
                  await reviewer.ctx.close();
                } else {
                  check('plan version: unconfigured approval auto-passes without fabricated reviewer', readback.ok === true && approved?.state === 'approved'
                    && approved.plan_id[0] === reportSuccess.parentId && !approved.approved_by && Boolean(approved.approved_date));
                  await session.page.screenshot({ path: path.join(out, 'plan-version-approved.png') });
                }
                await session.page.getByRole('button', { name: '返回', exact: true }).click();
                await session.page.waitForURL(url => url.pathname === `/f/sc.plan/${reportSuccess.parentId}`);
                report.planVersionReturnUrl = session.page.url();
                check('plan version: returns to owning parent', new URL(session.page.url()).pathname === `/f/sc.plan/${reportSuccess.parentId}`);
              }
            }
            continue;
          }
          await session.page.locator('[data-field-name="name"] input').first().fill(marker);
          await session.page.locator('[data-field-name="summary"] textarea').first().fill(content);
          const planInput = session.page.locator('[data-field-name="plan_id"] input').first();
          await planInput.fill(parentName);
          await session.page.getByRole('option', { name: parentName, exact: true }).click();
          reportCreateCapture = true;
          await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
          await session.page.getByText('计划汇报定向保存失败验证', { exact: false }).first().waitFor();
          check('report handling: failed save retains input', await session.page.locator('[data-field-name="name"] input').first().inputValue() === marker
            && await session.page.locator('[data-field-name="summary"] textarea').first().inputValue() === content);
          reportSuccess.request = structuredClone(report.reportSaveAttempts.at(-1));
          check('report handling: create request binds selected parent', reportSuccess.request.vals.plan_id === reportSuccess.parentId
            && reportSuccess.request.vals.name === marker && reportSuccess.request.vals.summary === content);
          reportSuccess.phase = 'create';
          await fs.writeFile(expenseRecoveryPath, JSON.stringify(reportSuccess, null, 2));
          await session.page.getByRole('button', { name: '提交', exact: true }).click();
          await session.page.waitForFunction(() => !window.location.pathname.endsWith('/new'));
          check('report handling: one parent, one report, one submit', reportSuccess.phase === 'done'
            && JSON.stringify(report.reportSuccessWrites.map(row => row.kind)) === JSON.stringify(['parent', 'create', 'submit']));
          const saved = await api({ op: 'read', model: spec.model, ids: [reportSuccess.id],
            fields: ['id', 'state', 'plan_id', 'company_id', 'name', 'summary', 'approver_id', 'approved_date'], context: { company_id: 8 } });
          report.reportSavedRecord = saved;
          const row = saved.data?.records?.[0];
          check('report handling: PM authoritative accepted readback', saved.ok === true && row?.id === reportSuccess.id
            && row.state === 'accepted' && row.plan_id[0] === reportSuccess.parentId && row.company_id[0] === 8
            && row.name === marker && row.summary === content && !row.approver_id && Boolean(row.approved_date));
          await form(session.page, `/f/sc.plan.report/${reportSuccess.id}${createContext}`, 'report-success-saved', 'readonly');
          for (const width of [1440, 390]) {
            await session.page.setViewportSize({ width, height: 950 });
            check(`report saved ${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
            await session.page.screenshot({ path: path.join(out, `report-success-${width}.png`) });
          }
          await session.page.setViewportSize({ width: 1440, height: 950 });
          const returnedQuery = session.page.waitForResponse(response => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data'
              && body.params?.op === 'list' && body.params.model === spec.model; } catch { return false; }
          });
          await session.page.getByRole('button', { name: '返回', exact: true }).click();
          const returnedResponse = await returnedQuery;
          const returnedResult = await returnedResponse.json();
          report.reportReturnQuery = { request: returnedResponse.request().postDataJSON(), result: returnedResult };
          await session.page.locator('[data-list-composition-reason="contract-collection-view"]').waitFor();
          await session.page.getByRole('row').filter({ hasText: marker }).first().waitFor();
          check('report handling: return reaches official authorized list', new URL(session.page.url()).pathname === `/m/${report.approvalCreateEntry.menu_id}`
            || new URL(session.page.url()).pathname === `/a/${report.approvalCreateEntry.action_id}`);
          check('report handling: returned query includes saved report', returnedResult.ok === true && returnedResult.data?.records?.some(row => row.id === reportSuccess.id));
          report.reportReturnUrl = session.page.url();
          await session.page.screenshot({ path: path.join(out, 'report-success-return-list.png') });
          continue;
        }
        if (eventSaveProbe) {
          report.eventCreateAuthority = authority;
          for (const field of ['name', 'project_id', 'event_type', 'description']) {
            check(`event create: ${field} has an editable native input`,
              await session.page.locator(`[data-field-name="${field}"]`).locator('input, textarea, [contenteditable="true"]').count() > 0);
          }
          const name = `TPL53-EVENT-SAVE-${Date.now()}`;
          const content = '临时验收合同履约事件：核对官方表单保存与提交恢复。';
          const projectInput = session.page.locator('[data-field-name="project_id"] input').first();
          const projectResponse = session.page.waitForResponse(response => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
              && body.params.model === 'project.project' && JSON.stringify(body.params).includes('FE Project A'); } catch { return false; }
          });
          await projectInput.fill('FE Project A');
          const projectResult = await projectResponse;
          let candidates = await projectResult.json();
          report.eventProjectQuery = { request: projectResult.request().postDataJSON(), result: candidates };
          if (candidates.ok === true && !candidates.data?.records?.length) {
            const availableResponse = session.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'project.project' && !body.params.search_term; } catch { return false; }
            });
            await projectInput.fill('');
            const available = await availableResponse;
            candidates = await available.json();
            report.eventAvailableProjects = { request: available.request().postDataJSON(), result: candidates };
          }
          const project = candidates.data?.records?.find(row => Number(row.id) > 0);
          report.eventSelectedProject = project || null;
          check('event create: project returned in operator authorized query', candidates.ok === true && Boolean(project));
          await session.page.getByRole('option', { name: String(project.display_name || project.name), exact: true }).click();
          const nameInput = session.page.locator('[data-field-name="name"]').locator('input, textarea').first();
          const contentInput = session.page.locator('[data-field-name="description"]').locator('textarea, input').first();
          await nameInput.fill(name);
          await session.page.locator('[data-field-name="event_type"] input').first().click();
          await session.page.getByText('设计变更', { exact: true }).click();
          await contentInput.fill(content);
          eventCreateCapture = true;
          for (const label of ['保存草稿', '提交']) {
            const response = session.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'create'
                && body.params.model === 'sc.contract.event'; } catch { return false; }
            });
            await session.page.getByRole('button', { name: label, exact: true }).click();
            await response;
            await session.page.getByText('验收注入：事件保存暂不可用，请重试', { exact: true }).first().waitFor();
            const payload = report.eventSaveAttempts.at(-1);
            check(`event ${label}: actual fields and relation identity preserved`, payload.vals.project_id === project.id
              && payload.vals.name === name && payload.vals.description === content && payload.vals.event_type === 'design_change');
            check(`event ${label}: authorized context preserved`, String(payload.context?.menu_id) === String(report.approvalCreateEntry.menu_id)
              && String(payload.context?.action_id) === String(report.approvalCreateEntry.action_id) && payload.context.company_id === 8);
            check(`event ${label}: failed create retains draft`, new URL(session.page.url()).pathname === '/f/sc.contract.event/new'
              && await nameInput.inputValue() === name && await contentInput.inputValue() === content);
          }
          eventCreateCapture = false;
          check('event save: two attempts and no follow-up action', report.eventSaveAttempts.length === 2 && report.forbiddenWrites.length === 0);
          await session.page.screenshot({ path: path.join(out, 'event-filled-save-failure.png') });
          if (eventSaveSuccess) {
            eventSuccess = { model: spec.model, request: structuredClone(report.eventSaveAttempts.at(-1)), phase: 'prepare', id: null, projectId: project.id };
            await fs.writeFile(expenseRecoveryPath, JSON.stringify(eventSuccess, null, 2));
            await expenseCleanup('preflight');
            eventSuccess.phase = 'create';
            await session.page.getByRole('button', { name: '提交', exact: true }).click();
            await session.page.waitForFunction(() => !window.location.pathname.endsWith('/new'));
            check('event success: create and confirm each execute once', eventSuccess.phase === 'done'
              && JSON.stringify(report.eventSuccessWrites?.map(row => row.kind)) === JSON.stringify(['create', 'submit']));
            const saved = await session.page.evaluate(async id => {
              const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
              return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
                method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
                body: JSON.stringify({ intent: 'api.data', params: { op: 'read', model: 'sc.contract.event', ids: [id],
                  fields: ['id', 'state', 'project_id', 'company_id', 'name', 'description', 'event_type'], context: { company_id: 8 } } }),
              })).json();
            }, eventSuccess.id);
            report.eventSavedRecord = saved;
            const row = saved.data?.records?.[0];
            check('event success: operator authoritative record readback', saved.ok === true && row?.id === eventSuccess.id
              && row.state === 'approved' && row.project_id[0] === project.id && row.company_id[0] === 8
              && row.name === name && row.description === content && row.event_type === 'design_change');
            await form(session.page, `/f/sc.contract.event/${eventSuccess.id}${createContext}`, 'event-success-saved', 'readonly');
            for (const width of [1440, 390]) {
              await session.page.setViewportSize({ width, height: 950 });
              check(`event saved ${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
              await session.page.screenshot({ path: path.join(out, `event-success-${width}.png`) });
            }
            continue;
          }
        }

        if (diarySaveProbe) {
          const title = `TPL53-DIARY-SAVE-${Date.now()}`;
          const content = '临时验收施工日志：核对官方表单保存与提交失败恢复。';
          report.diaryCreateAuthority = authority;
          for (const field of ['project_id', 'title', 'description']) {
            check(`diary create: ${field} has an editable native input`,
              await session.page.locator(`[data-field-name="${field}"]`).locator('input, textarea, [contenteditable="true"]').count() > 0);
          }
          const projectInput = session.page.locator('[data-field-name="project_id"] input').first();
          const projectResponse = session.page.waitForResponse(response => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
              && body.params.model === 'project.project' && JSON.stringify(body.params).includes('FE Project A'); } catch { return false; }
          });
          await projectInput.fill('FE Project A');
          const candidates = await (await projectResponse).json();
          const project = candidates.data?.records?.find(row => Number(row.id) === 10);
          check('diary create: project returned in PM authorized query', candidates.ok === true && Boolean(project));
          const label = String(project.display_name || project.name);
          await session.page.getByRole('option', { name: label, exact: true }).click();
          const titleInput = session.page.locator('[data-field-name="title"]').locator('input, textarea').first();
          const contentInput = session.page.locator('[data-field-name="description"]').locator('textarea, input').first();
          await titleInput.fill(title);
          await contentInput.fill(content);
          diaryCreateCapture = true;
          for (const label of ['保存草稿', '提交审批']) {
            const response = session.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'create'
                && body.params.model === 'sc.construction.diary'; } catch { return false; }
            });
            await session.page.getByRole('button', { name: label, exact: true }).click();
            await response;
            await session.page.getByText('验收注入：日志保存暂不可用，请重试', { exact: true }).first().waitFor();
            const payload = report.diarySaveAttempts.at(-1);
            check(`diary ${label}: actual values and numeric project preserved`, payload.vals.project_id === project.id
              && payload.vals.title === title && payload.vals.description === content);
            check(`diary ${label}: unchanged date remains an effective backend default`, Boolean(authority.mainData?.date_diary)
              && (!Object.hasOwn(payload.vals, 'date_diary') || payload.vals.date_diary === authority.mainData.date_diary));
            check(`diary ${label}: native entry context preserved`, String(payload.context?.menu_id) === String(report.approvalCreateEntry.menu_id)
              && String(payload.context?.action_id) === String(report.approvalCreateEntry.action_id));
            check(`diary ${label}: failed create preserves editable draft`, new URL(session.page.url()).pathname === '/f/sc.construction.diary/new'
              && await titleInput.inputValue() === title && await contentInput.inputValue() === content);
          }
          diaryCreateCapture = false;
          check('diary save: two explicit attempts and no follow-up business mutation', report.diarySaveAttempts.length === 2 && report.forbiddenWrites.length === 0);
          await session.page.screenshot({ path: path.join(out, 'diary-filled-save-failure.png'), fullPage: true });
          if (diarySaveSuccess) {
            diarySuccess = { model: spec.model, request: structuredClone(report.diarySaveAttempts.at(-1)), phase: 'prepare', id: null };
            await fs.writeFile(expenseRecoveryPath, JSON.stringify(diarySuccess, null, 2));
            await expenseCleanup('preflight');
            diarySuccess.phase = 'create';
            await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
            await session.page.waitForFunction(() => !window.location.pathname.endsWith('/new'));
            check('diary success: create and confirm each execute once', diarySuccess.phase === 'done'
              && JSON.stringify(report.diarySuccessWrites?.map(row => row.kind)) === JSON.stringify(['create', 'submit']));
            const saved = await session.page.evaluate(async id => {
              const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
              return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
                method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
                body: JSON.stringify({ intent: 'api.data', params: { op: 'read', model: 'sc.construction.diary', ids: [id],
                  fields: ['id', 'state', 'project_id', 'company_id', 'title', 'description', 'date_diary', 'diary_type', 'source_origin'], context: { company_id: 8 } } }),
              })).json();
            }, diarySuccess.id);
            report.diarySavedRecord = saved;
            const row = saved.data?.records?.[0];
            check('diary success: PM authoritative record readback', saved.ok === true && row?.id === diarySuccess.id
              && row.state === 'confirmed' && row.project_id[0] === 10 && row.company_id[0] === 8
              && row.title === title && row.description === content && Boolean(row.date_diary)
              && row.diary_type === '施工日志' && row.source_origin === 'manual');
            await form(session.page, `/f/sc.construction.diary/${diarySuccess.id}${createContext}`, 'diary-success-saved', 'readonly');
            for (const width of [1440, 390]) {
              await session.page.setViewportSize({ width, height: 950 });
              check(`diary saved ${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
              await session.page.screenshot({ path: path.join(out, `diary-success-${width}.png`) });
            }
            continue;
          }

        }

        if (spec.model === 'sc.expense.claim') {
          const fields = [];
          const visit = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); visit(node.children); } };
          visit(authority.layout?.containerTree);
          for (const name of ['project_id', 'partner_id', 'payment_request_id', 'amount', 'payee_account', 'payer_account']) {
            check(`expense create: ${name} retained in effective contract`, fields.some((field) => field.name === name));
          }
          for (const name of ['payment_request_id', 'amount', 'payee_account', 'payer_account']) {
            check(`expense create: ${name} has rendered input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
          await session.page.getByText('当前业务分类要求上传附件后才能提交、批准或完成。', { exact: true }).first().waitFor({ state: 'visible' });
          check('expense create: incomplete submission stays on unsaved form', new URL(session.page.url()).pathname === '/f/sc.expense.claim/new');
          check('expense create: required validation sends no business write', report.forbiddenWrites.length === 0);
          const projectInput = session.page.locator('[data-field-name="project_id"] input').first();
          const projectResponse = session.page.waitForResponse((response) => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
              && body.params.model === 'project.project' && JSON.stringify(body.params).includes('FE Project A'); } catch { return false; }
          });
          await projectInput.fill('FE Project A');
          const projectResult = await (await projectResponse).json();
          const project = projectResult.data?.records?.find((row) => row.name === 'FE Project A' || row.display_name === 'FE Project A');
          check('expense relation: existing authorized project returned', projectResult.ok === true && Number(project?.id) > 0);
          await session.page.getByRole('option', { name: String(project.display_name || project.name), exact: true }).click();
          const paymentInput = session.page.locator('[data-field-name="payment_request_id"] input').first();
          const paymentResponse = session.page.waitForResponse((response) => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list' && body.params.model === 'payment.request'; } catch { return false; }
          });
          await paymentInput.click();
          const response = await paymentResponse;
          const query = response.request().postDataJSON().params;
          const result = await response.json();
          report.expenseRelation = { projectId: project.id, query, result };
          const hasProject = (value) => Array.isArray(value) && ((value[0] === 'project_id' && value[1] === '=' && Number(value[2]) === Number(project.id)) || value.some(hasProject));
          check('expense relation: actual request query includes selected project', hasProject(query.domain));
          const hasPayDirection = (value) => Array.isArray(value) && ((value[0] === 'type' && value[1] === 'in'
            && Array.isArray(value[2]) && value[2].length === 1 && value[2][0] === 'pay') || value.some(hasPayDirection));
          check('expense relation: cash-out query restricts request direction', hasPayDirection(query.domain));
          check('expense relation: authorized request candidates returned', result.ok === true && result.data?.records?.length > 0);
          const selected = result.data.records[0];
          const selectedLabel = String(selected.display_name || selected.name);
          await session.page.getByRole('option', { name: selectedLabel, exact: true }).click();
          check('expense relation: selected candidate label retained', await paymentInput.inputValue() === selectedLabel);
          report.expenseRelation.selected = { id: selected.id, label: selectedLabel };
          const otherProjectResponse = session.page.waitForResponse((response) => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
              && body.params.model === 'project.project' && JSON.stringify(body.params).includes('FE Project B'); } catch { return false; }
          });
          await projectInput.fill('FE Project B');
          const otherResult = await (await otherProjectResponse).json();
          const otherProject = otherResult.data?.records?.find((row) => row.name === 'FE Project B' || row.display_name === 'FE Project B');
          check('expense relation: second authorized project returned', otherResult.ok === true && Number(otherProject?.id) > 0 && otherProject.id !== project.id);
          await session.page.getByRole('option', { name: String(otherProject.display_name || otherProject.name), exact: true }).click();
          check('expense relation: changing project clears stale request', await paymentInput.inputValue() === '');
          const otherPaymentResponse = session.page.waitForResponse((response) => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list' && body.params.model === 'payment.request'
              && JSON.stringify(body.params.domain).includes(JSON.stringify(['project_id', '=', otherProject.id])); } catch { return false; }
          });
          await paymentInput.click();
          const otherResponse = await otherPaymentResponse;
          report.expenseRelation.changedProject = { id: otherProject.id, query: otherResponse.request().postDataJSON().params, result: await otherResponse.json() };
          check('expense relation: next query uses changed project', report.expenseRelation.changedProject.result.ok === true);
          check('expense relation: changed project preserves cash-out direction', hasPayDirection(report.expenseRelation.changedProject.query.domain));
          check('expense relation: draft interactions send no business write', report.forbiddenWrites.length === 0);

          if (expenseSaveProbe) {
            const sourceResult = await session.page.evaluate(async ({ id, context }) => {
              const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
              return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
                method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
                body: JSON.stringify({ intent: 'api.data', params: { op: 'read', model: 'payment.request', ids: [id],
                  fields: ['id', 'project_id', 'partner_id', 'company_id', 'currency_id', 'amount', 'type', 'state'], context } }),
              })).json();
            }, { id: selected.id, context: query.context });
            const source = sourceResult.data?.records?.[0];
            check('expense save: selected source authoritatively read', sourceResult.ok === true && source?.id === selected.id && source.type === 'pay');
            report.expenseSaveSource = source;
            await projectInput.fill('FE Project A');
            await session.page.getByRole('option', { name: String(project.display_name || project.name), exact: true }).click();
            const partnerInput = session.page.locator('[data-field-name="partner_id"] input').first();
            await partnerInput.fill(source.partner_id[1]);
            await session.page.getByRole('option', { name: source.partner_id[1], exact: true }).click();
            await paymentInput.click();
            await session.page.getByRole('option', { name: selectedLabel, exact: true }).click();
            const amountInput = session.page.locator('[data-field-name="amount"] input').first();
            await amountInput.fill(String(source.amount));
            for (const [name, value] of [['payee_account', 'EXPENSE-SAVE-PAYEE'], ['payer_account', 'EXPENSE-SAVE-PAYER']]) {
              await session.page.locator(`[data-field-name="${name}"] input`).first().fill(value);
            }
            expenseCreateCapture = true;
            await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
            await session.page.getByText('当前业务分类要求上传附件后才能提交、批准或完成。', { exact: true }).first().waitFor();
            check('expense submit: missing attachment blocks before create', !report.expenseSaveAttempts?.length);
            const draftResponse = session.page.waitForResponse((response) => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data'
                && body.params?.op === 'create' && body.params.model === 'sc.expense.claim'; } catch { return false; }
            });
            await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
            await draftResponse;
            await session.page.getByText('验收注入：保存暂不可用，请重试', { exact: true }).first().waitFor();
            check('expense draft: missing attachment does not prevent save', report.expenseSaveAttempts?.length === 1);
            report.expenseDraftSaveAttempt = report.expenseSaveAttempts[0];
            report.expenseSaveAttempts = [];
            const pendingName = 'tpl53-submission-requirement.txt';
            await session.page.locator('[data-professional-collaboration-component="attachments"] input[type="file"]').setInputFiles({
              name: pendingName, mimeType: 'text/plain', buffer: Buffer.from('Rollback-only submission prerequisite verification'),
            });
            await session.page.getByText(pendingName, { exact: true }).first().waitFor();
            check('expense submit: attachment stays pending before record creation', report.forbiddenWrites.length === 0);
            for (let attempt = 1; attempt <= 2; attempt += 1) {
              const saveResponse = session.page.waitForResponse((response) => {
                try { const body = response.request().postDataJSON(); return body?.intent === 'api.data'
                  && body.params?.op === 'create' && body.params.model === 'sc.expense.claim'; } catch { return false; }
              });
              await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
              await saveResponse;
              await session.page.getByText('验收注入：保存暂不可用，请重试', { exact: true }).first().waitFor();
              check(`expense save: attempt ${attempt} sends exactly one create`, report.expenseSaveAttempts.length === attempt);
              const payload = report.expenseSaveAttempts[attempt - 1];
              check(`expense save: attempt ${attempt} preserves numeric relationship identity`,
                payload.vals.project_id === project.id && payload.vals.partner_id === source.partner_id[0]
                && payload.vals.payment_request_id === selected.id);
              check(`expense save: attempt ${attempt} preserves amount and entry context`,
                Number(payload.vals.amount) === Number(source.amount)
                && String(payload.context?.menu_id) === String(report.approvalCreateEntry.menu_id)
                && String(payload.context?.action_id) === String(report.approvalCreateEntry.action_id));
              check(`expense save: attempt ${attempt} preserves editable draft`, new URL(session.page.url()).pathname === '/f/sc.expense.claim/new'
                && Number(await amountInput.inputValue()) === Number(source.amount) && await paymentInput.inputValue() === selectedLabel);
            }
            expenseCreateCapture = false;
            check('expense save: failed saves do not execute business actions', report.forbiddenWrites.length === 0);
            if (expenseSaveSuccess) {
              const request = structuredClone(report.expenseSaveAttempts[1]);
              request.vals.summary = `TPL53-EXPENSE-SUCCESS-${Date.now()}`;
              expenseSuccess = { request, source, filename: pendingName,
                data: Buffer.from('Rollback-only submission prerequisite verification').toString('base64'), phase: 'prepare', id: null };
              if (expensePartialUpload) {
                expenseSuccess.files = [
                  { name: pendingName, data: expenseSuccess.data },
                  { name: 'tpl53-partial-second.txt', data: Buffer.from('Rollback-only second attachment').toString('base64') },
                ];
                expenseSuccess.uploadIndex = 0;
                const second = expenseSuccess.files[1];
                await session.page.locator('[data-professional-collaboration-component="attachments"] input[type="file"]').setInputFiles({
                  name: second.name, mimeType: 'text/plain', buffer: Buffer.from(second.data, 'base64'),
                });
                await session.page.getByText(second.name, { exact: true }).first().waitFor();
              }
              await fs.writeFile(expenseRecoveryPath, JSON.stringify(expenseSuccess, null, 2));
              await expenseCleanup('preflight');
              await session.page.locator('[data-field-name="summary"]').locator('input, textarea').first().fill(request.vals.summary);
              expenseSuccess.phase = 'create';
              await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
              await session.page.waitForFunction(() => !window.location.pathname.endsWith('/new'));
              if (expenseFailureStage) {
                await session.page.locator('[data-form-composition="official-standard-form"][data-state="ok"]').waitFor();
                const recoveryUrl = new URL(session.page.url());
                check('expense recovery: generated record remains the current identity', recoveryUrl.pathname === `/f/sc.expense.claim/${expenseSuccess.id}`
                  && recoveryUrl.searchParams.get('create_recovery') === expenseFailureStage && report.expenseInjectedFailure?.id === expenseSuccess.id);
                const message = expenseFailureStage === 'upload'
                  ? '单据已保存，附件上传未完成。请在当前单据重新选择附件后提交。'
                  : '单据已保存，提交未完成。请在当前单据核对后重试。';
                await session.page.getByText(message, { exact: true }).waitFor();
                if (expenseFailureStage === 'upload') {
                  if (expensePartialUpload) {
                    check('expense partial: first file confirmed before second failed', expenseSuccess.uploadIndex === 1
                      && report.expenseSuccessWrites.filter(row => row.kind === 'upload').length === 1);
                    await session.page.getByText(pendingName, { exact: true }).first().waitFor();
                  }
                  const retryFile = expenseSuccess.files?.[expenseSuccess.uploadIndex]
                    || { name: pendingName, data: expenseSuccess.data };
                  const uploadResponse = session.page.waitForResponse((response) => {
                    try { return response.request().postDataJSON()?.intent === 'file.upload'; } catch { return false; }
                  });
                  await session.page.locator('[data-professional-collaboration-component="attachments"] input[type="file"]').setInputFiles({
                    name: retryFile.name, mimeType: 'text/plain', buffer: Buffer.from(retryFile.data, 'base64'),
                  });
                  await uploadResponse;
                }
                await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
              }
              const completed = () => report.expenseSuccessWrites?.some((row) => row.kind === 'submit' && row.result.ok === true);
              for (let wait = 0; wait < 100 && !completed(); wait += 1) await session.page.waitForTimeout(100);
              check('expense success: create upload submit occur exactly once',
                JSON.stringify(report.expenseSuccessWrites?.map((row) => row.kind)) === JSON.stringify(expensePartialUpload ? ['create', 'upload', 'upload', 'submit'] : ['create', 'upload', 'submit']) && completed());
              const saved = await session.page.evaluate(async (id) => {
                const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
                return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
                  method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
                  body: JSON.stringify({ intent: 'api.data', params: { op: 'read', model: 'sc.expense.claim', ids: [id],
                    fields: ['id', 'state', 'project_id', 'partner_id', 'payment_request_id', 'amount', 'attachment_ids', 'summary'], context: { company_id: 8 } } }),
                })).json();
              }, expenseSuccess.id);
              report.expenseSuccessRecord = saved;
              const savedRow = saved.data?.records?.[0];
              check('expense success: submitted record and attachment authoritative readback', saved.ok === true && savedRow?.state === 'approved'
                && savedRow.attachment_ids.length === (expensePartialUpload ? 2 : 1) && savedRow.payment_request_id[0] === source.id && savedRow.summary === request.vals.summary);
              await form(session.page, `/f/sc.expense.claim/${expenseSuccess.id}${createContext}`, 'expense-success-saved', 'readonly');
              const savedAuthority = (report.contractResponses || []).map((row) => findRecordAuthority(row.contract))
                .findLast((row) => row?.model === 'sc.expense.claim' && Number(row.mainData?.id) === expenseSuccess.id);
              check('expense success: saved contract is readonly', savedAuthority?.status.effectiveRenderProfile === 'readonly');
              for (const width of [1440, 390]) {
                await session.page.setViewportSize({ width, height: 950 });
                check(`expense success ${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
                await session.page.screenshot({ path: path.join(out, `expense-success-${width}.png`) });
              }
              await session.ctx.close();
              continue;
            }
          }

          await session.page.getByRole('heading', { name: '新建报销申请', exact: true }).click();

        }

        if (['sc.settlement.adjustment', 'sc.receipt.income', 'sc.financing.loan', 'sc.self.funding.registration', 'sc.treasury.reconciliation'].includes(spec.model)) {
          const fields = [];
          const walk = (nodes, pages = []) => { for (const node of nodes || []) { const path = node.type === 'page' ? [...pages, node.label || node.title] : pages; if (node.type === 'field') fields.push({ ...node, probePages: path }); walk(node.children, path); } };
          walk(authority.layout?.containerTree);
          const required = spec.model === 'sc.treasury.reconciliation'
            ? ['project_id', 'treasury_ledger_id', 'system_difference'] : spec.model === 'sc.settlement.adjustment'
              ? ['project_id', 'contract_id', 'item_name', 'amount'] : spec.model === 'sc.receipt.income'
              ? ['project_id', 'payment_request_id', 'partner_id', 'amount'] : ['project_id', 'partner_id', 'amount'];
          for (const name of required) {
            const field = fields.find((node) => node.name === name);
            check(`${spec.model}: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            const input = session.page.locator(`[data-field-name="${name}"] input`).first();
            // Task forms may project native notebook fields into semantic regions.
            // Prefer the actual input; native pages are navigation only when needed.
            if (!(await input.isVisible())) {
              for (const title of field.probePages) {
                const pageLink = session.page.getByText(title, { exact: true });
                if (await pageLink.count() === 1) await pageLink.click();
              }
            }
            await input.waitFor({ state: 'visible' });
            await input.scrollIntoViewIfNeeded();
            check(`${spec.model}: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          for (const label of ['审批通过', spec.model === 'sc.treasury.reconciliation' ? '对账完成' : spec.model === 'sc.receipt.income' ? '已收款' : '完成']) {
            check(`${spec.model}: no ${label} on unsaved document`, await session.page.getByRole('button', { name: label, exact: true }).count() === 0);
          }
        }
        if (spec.model === 'sc.project.document') {
          const fields = [];
          const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
          walk(authority.layout?.containerTree);
          for (const name of ['name', 'project_id', 'doc_type_id']) {
            const field = fields.find((node) => node.name === name);
            check(`project document: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            check(`project document: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          check('project document: no archival before saved approval', await session.page.getByRole('button', { name: '归档', exact: true }).count() === 0);
          check('project document: no approval of unsaved document', await session.page.getByRole('button', { name: '审批通过', exact: true }).count() === 0);
        }
        if (spec.model === 'tender.doc.purchase') {
          const fields = [];
          const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
          walk(authority.layout?.containerTree);
          for (const name of ['bid_id', 'apply_date', 'amount']) {
            const field = fields.find((node) => node.name === name);
            check(`tender purchase: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            check(`tender purchase: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          check('tender purchase: no direct approval on unsaved document', await session.page.getByRole('button', { name: '通过', exact: true }).count() === 0);
        }
        if (spec.model === 'tender.guarantee') {
          const fields = [];
          const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
          walk(authority.layout?.containerTree);
          for (const name of ['bid_id', 'date', 'amount']) {
            const field = fields.find((node) => node.name === name);
            check(`tender guarantee: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            check(`tender guarantee: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          check('tender guarantee: no cash posting before approval', await session.page.getByRole('button', { name: '确认入账', exact: true }).count() === 0);
          check('tender guarantee: no direct approval on unsaved document', await session.page.getByRole('button', { name: '通过', exact: true }).count() === 0);
        }
        if (spec.model === 'sc.output.invoice.adjustment') {
          const fields = [];
          const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
          walk(authority.layout?.containerTree);
          for (const name of ['original_ledger_id', 'adjustment_date', 'red_flush_invoice_no']) {
            const field = fields.find((node) => node.name === name);
            check(`red flush: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            check(`red flush: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          const originalControl = session.page.locator('[data-field-name="original_ledger_id"] input').first();
          const originalResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list' && body.params.model === 'sc.output.invoice.ledger';
            } catch { return false; }
          });
          await originalControl.click();
          const originalQuery = (await originalResponse).request().postDataJSON().params;
          const eligibleDomain = [['active', '=', true], ['adjustment_kind', '=', 'normal'], '|', ['source_model', '!=', 'sc.invoice.registration'], ['invoice_document_state', 'in', ['registered', 'legacy_confirmed']]];
          check('red flush: actual original query preserves eligibility domain', JSON.stringify(originalQuery.domain) === JSON.stringify(eligibleDomain));
          await session.page.getByRole('heading', { name: '新建记录', exact: true }).click();
          check('red flush: no red invoice before approval', await session.page.getByRole('button', { name: '确认红冲', exact: true }).count() === 0);
          check('red flush: no direct approval on unsaved document', await session.page.getByRole('button', { name: '通过', exact: true }).count() === 0);
        }
        if (spec.model === 'payment.request') {
          const nodes = [];
          const visit = (items) => {
            for (const node of items || []) {
              if (node.type === 'field') nodes.push(node);
              visit(node.children);
            }
          };
          visit(authority.layout?.containerTree);
          const basis = nodes.find((node) => node.name === 'subcontract_settlement_id');
          check('payment create: explicit subcontract basis in effective contract', Boolean(basis));
          check('payment create: subcontract basis is editable', basis.readonly !== true && basis.fieldInfo?.readonly !== true && basis.componentConfig?.readonly !== true);
          const control = session.page.getByPlaceholder('请选择分包结算单', { exact: true });
          check('payment create: actual subcontract relation control', await control.count() === 1);
          await control.scrollIntoViewIfNeeded();
          const sourceResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'sc.subcontract.settlement';
            } catch { return false; }
          });
          await control.click();
          const sourceQuery = (await sourceResponse).request().postDataJSON().params;
          check('payment create: unresolved project blocks source query',
            JSON.stringify(sourceQuery.domain) === JSON.stringify([['id', '=', -1]]));
          await session.page.screenshot({ animations: 'disabled', path: path.join(out, 'payment-subcontract-basis-open.png') });
          await session.page.getByRole('heading', { name: '新建记录', exact: true }).click();
          const projectControl = session.page.locator('[data-field-name="project_id"]').locator('input').first();
          const projectResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'project.project';
            } catch { return false; }
          });
          await projectControl.click();
          const projects = (await (await projectResponse).json()).data?.records || [];
          check('payment source: existing authorized project available', projects.length > 0);
          let project = projects[0];
          const projectLabel = String(project.display_name || project.name);
          const matchesScope = (domain) => Array.isArray(domain)
            && domain.some((term) => JSON.stringify(term) === JSON.stringify(['project_id', '=', project.id]))
            && domain.some((term) => JSON.stringify(term) === JSON.stringify(['state', '=', 'confirmed']));
          const scopedResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'sc.subcontract.settlement'
                && matchesScope(body.params.domain);
            } catch { return false; }
          });
          await session.page.getByRole('option', { name: projectLabel, exact: true }).click();
          const scopedQuery = (await scopedResponse).request().postDataJSON().params;
          check('payment source: selected project and confirmed state preserved', matchesScope(scopedQuery.domain));
          report.paymentSourceScope = { projectId: project.id, domain: scopedQuery.domain };
          await control.click();
          const moreResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'sc.subcontract.settlement' && body.params.limit === 120;
            } catch { return false; }
          });
          const [moreResult] = await Promise.all([
            moreResponse,
            session.page.getByRole('button', { name: '搜索更多...', exact: true }).click(),
          ]);
          const moreQuery = moreResult.request().postDataJSON().params;
          check('payment source: search dialog preserves same scope', matchesScope(moreQuery.domain));
          const sourceDialog = session.page.getByRole('dialog');
          await sourceDialog.getByRole('button', { name: '取消', exact: true }).click();
          check('payment source: second existing project available', projects.length > 1);
          project = projects[1];
          await projectControl.click();
          const changedSourceResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'sc.subcontract.settlement' && matchesScope(body.params.domain);
            } catch { return false; }
          });
          const [changedSource] = await Promise.all([
            changedSourceResponse,
            session.page.getByRole('option', { name: String(project.display_name || project.name), exact: true }).click(),
          ]);
          check('payment source: project change replaces query scope', matchesScope(changedSource.request().postDataJSON().params.domain));
          report.paymentSourceScope.changedProjectId = project.id;
          await session.page.getByRole('heading', { name: '新建记录', exact: true }).click();
        }
        if (['sc.material.rental.order', 'sc.material.rental.settlement'].includes(spec.model)) {
          const settlement = spec.model === 'sc.material.rental.settlement';
          const dateField = settlement ? 'settlement_date' : 'rental_date';
          const fields = [];
          const visit = (nodes) => {
            for (const node of nodes || []) {
              if (node.type === 'field') fields.push(node);
              visit(node.children);
            }
          };
          visit(authority.layout?.containerTree);
          for (const name of ['project_id', 'supplier_id', dateField, 'note']) {
            const field = fields.find((node) => node.name === name);
            check(`${spec.model}: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
          }
          for (const label of ['项目', '供应商']) {
            check(`${spec.model}: ${label} input visible`, await session.page.getByPlaceholder(`请选择${label}`, { exact: true }).isVisible());
          }
          check(`${spec.model}: date input visible`, await session.page.locator(`input[value="${authority.mainData[dateField]}"]`).isVisible());
          check(`${spec.model}: note input visible`, await session.page.locator('textarea').first().isVisible());

          check(`${spec.model}: generated number absent on create`, await session.page.getByText(settlement ? '结算单号' : '租赁单号', { exact: true }).count() === 0);
          for (const name of (settlement ? ['确认结算', '确认支付'] : ['确认租赁', '确认退还', '完成结算'])) {
            check(`${spec.model}: unsaved cannot ${name}`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
          }
        }
        if (executionLabels) {
          check(`${spec.model}: generated number absent on create`, await session.page.getByText(executionLabels[0], { exact: true }).count() === 0);
          check(`${spec.model}: unsaved cannot confirm`, await session.page.getByRole('button', { name: executionLabels[1], exact: true }).count() === 0);
        }
        if (['sc.safety.plan', 'sc.safety.disclosure', 'sc.subcontract.plan', 'sc.subcontract.request', 'sc.subcontract.settlement'].includes(spec.model)) {
          const fields = [];
          const visit = (nodes) => {
            for (const node of nodes || []) {
              if (node.type === 'field') fields.push(node);
              visit(node.children);
            }
          };
          visit(authority.layout?.containerTree);
          if (spec.model.startsWith('sc.subcontract.')) {
            const number = fields.find((node) => node.name === 'name');
            const invisible = number?.modifiers?.invisible;
            const hiddenForNewIdentity = invisible?.kind === 'not'
              && invisible.expr?.kind === 'field_truthy' && invisible.expr?.field === 'id'
              && !(Number(authority.mainData?.id) > 0);
            check(`${spec.model}: generated number hidden by effective contract`, !number || number.invisible === true || number.fieldInfo?.invisible === true || number.componentConfig?.invisible === true || hiddenForNewIdentity);
          }
          const inputs = spec.model === 'sc.subcontract.settlement'
            ? ['project_id', 'subcontractor_id', 'settlement_date']
            : spec.model.startsWith('sc.subcontract.')
            ? ['project_id', 'subcontract_scope', spec.model.endsWith('plan') ? 'plan_date' : 'request_date']
            : spec.model === 'sc.safety.plan'
            ? ['name', 'project_id', 'description']
            : ['name', 'project_id', 'participant_note', 'content'];
          for (const name of inputs) {
            const field = fields.find((node) => node.name === name);
            check(`${spec.model}: ${name} editable input contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true && field.componentConfig?.readonly !== true);
          }
        }
        if (['sc.equipment.plan', 'sc.equipment.request', 'sc.labor.plan', 'sc.labor.request', 'sc.material.rental.plan', 'sc.subcontract.plan', 'sc.subcontract.request'].includes(spec.model)) {
          const numberLabel = spec.model.endsWith('plan') ? '计划单号' : '申请单号';
          check(`${spec.model}: generated number absent on create`, await session.page.getByText(new RegExp(numberLabel)).count() === 0);
          check(`${spec.model}: old direct approval absent`, await session.page.getByRole('button', { name: spec.model === 'sc.material.rental.plan' ? '确认' : spec.model.endsWith('plan') ? '确认计划' : '确认申请', exact: true }).count() === 0);
        }
        if (spec.model === 'sc.labor.settlement') {
          const nodes = [];
          const visit = (items) => {
            for (const node of items || []) {
              if (node.type === 'field') nodes.push(node);
              visit(node.children);
            }
          };
          visit(authority.layout?.containerTree);
          for (const [name, label] of [['project_id', '项目'], ['contractor_id', '劳务单位'], ['settlement_date', '结算日期'], ['note', '结算说明']]) {
            const field = nodes.find((node) => node.name === name);
            check(`labor settlement: ${name} input contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true && field.componentConfig?.readonly !== true);
            const input = name === 'project_id' || name === 'contractor_id'
              ? session.page.getByPlaceholder(`请选择${label}`, { exact: true })
              : name === 'settlement_date'
                ? session.page.locator(`input[value="${authority.mainData.settlement_date}"]`)
                : session.page.locator('textarea');
            check(`labor settlement: ${name} input visible`, await input.count() > 0);
          }
        }
        if (spec.model === 'sc.subcontract.settlement') {
          check('subcontract settlement: generated number absent on create', await session.page.getByText(/结算单号/).count() === 0);
          check('subcontract settlement: unsaved has no confirmation', await session.page.getByRole('button', { name: '确认结算', exact: true }).count() === 0);
          for (const name of ['project_id', 'subcontractor_id', 'settlement_date']) {
            const field = session.page.locator(`[data-field-name="${name}"]`);
            check(`subcontract settlement: ${name} has actual input`, await field.locator('input').count() > 0);
          }
        }
        if (spec.model === 'sc.material.settlement') check('material settlement: generated number absent on create', await session.page.getByText('结算单号', { exact: true }).count() === 0);
        if (spec.model === 'sc.material.rfq') check('RFQ: generated number absent on create', await session.page.getByText('询价单号', { exact: true }).count() === 0);
        if (spec.model === 'sc.material.purchase.request') {
          check('purchase request: generated number not exposed for create input', await session.page.getByText('申请单号', { exact: true }).count() === 0);
        }

        for (const name of ['审批通过', '审批驳回', '完成', ...(spec.model === 'sc.material.inbound' ? ['确认入库'] : spec.model === 'sc.material.acceptance' ? ['验收通过', '验收不通过'] : spec.model === 'sc.material.purchase.request' ? ['生成询价单', '生成采购订单'] : spec.model === 'sc.material.rfq' ? ['确定报价', '生成采购订单'] : spec.model === 'sc.material.settlement' ? ['确认结算', '生成剩余付款申请'] : [])]) {
          check(`${spec.model}: unsaved form has no ${name} action`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
        }
        for (const width of [1440, 390]) {
          await session.page.setViewportSize({ width, height: 900 });
          await session.page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          check(`${spec.model}-create-${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
          if (['sc.subcontract.plan', 'sc.subcontract.request'].includes(spec.model)) {
            const names = spec.model.endsWith('plan')
              ? ['project_id', 'subcontract_scope', 'plan_date', 'start_date', 'end_date']
              : ['project_id', 'subcontract_scope', 'request_date'];
            const observation = await session.page.evaluate((fieldNames) => {
              const box = (el) => {
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { x: r.x, y: r.y, width: r.width, height: r.height };
              };
              return fieldNames.map((name) => ({
                name,
                occurrences: [...document.querySelectorAll('[data-field-name]')]
                  .filter((el) => el.getAttribute('data-field-name') === name)
                  .map((el) => ({
                    box: box(el),
                    label: box(el.querySelector('label')),
                    controls: [...el.querySelectorAll('input, textarea')].map((input) => ({
                      box: box(input), id: input.id, placeholder: input.getAttribute('placeholder'),
                      disabled: input.disabled, readonly: input.readOnly,
                    })),
                  })),
              }));
            }, names);
            (report.createInputGeometry ||= []).push({ model: spec.model, width, fields: observation });
            for (const field of observation) {
              const rendered = field.occurrences.filter((row) => row.box?.width > 0 && row.box?.height > 0);
              check(`${spec.model}-${width}: ${field.name} rendered usable input`, rendered.length > 0 && rendered.every((row) =>
                row.controls.some((control) => !control.disabled && control.box?.width > 0 && control.box?.height > 0)));
              check(`${spec.model}-${width}: ${field.name} label separated from input`, rendered.every((row) =>
                row.label && row.controls.every((control) => control.box.y >= row.label.y + row.label.height)));
            }
            const scopeField = observation.find((field) => field.name === 'subcontract_scope');
            const scopeInput = session.page.locator(`[id="${scopeField.occurrences[0].controls[0].id}"]`);
            await scopeInput.fill('本地验收未保存分包范围');
            check(`${spec.model}-${width}: scope accepts draft input`, await scopeInput.inputValue() === '本地验收未保存分包范围');
            await scopeInput.fill('');
            const dateField = observation.find((field) => field.name === (spec.model.endsWith('plan') ? 'start_date' : 'request_date'));
            const dateInput = session.page.locator(`[id="${dateField.occurrences[0].controls[0].id}"]`);
            await dateInput.click();
            await session.page.getByText('一', { exact: true }).waitFor({ state: 'visible' });
            await session.page.getByText('六', { exact: true }).waitFor({ state: 'visible' });
            check(`${spec.model}-${width}: date opens official calendar`, await session.page.getByText('一', { exact: true }).isVisible() && await session.page.getByText('六', { exact: true }).isVisible());
            await session.page.getByRole('heading', { name: '新建记录', exact: true }).click();
            await session.page.getByText('一', { exact: true }).waitFor({ state: 'hidden' });
            check(`${spec.model}-${width}: calendar closes on outside click`, !await session.page.getByText('一', { exact: true }).isVisible());
            await session.page.evaluate(() => window.scrollTo(0, 0));

          }
          await session.page.screenshot({ animations: 'disabled', path: path.join(out, `${spec.model}-create-${width}.png`) });
        }
        await session.ctx.close();
        continue;
      }
      const projectSave = process.env.TPL07_PROJECT_SAVE === '1';
      if (projectSave) {
        check('project save: exact governed scope', spec.model === 'project.project' && spec.role === 'fixture_role_pm'
          && process.env.TPL07_APPROVAL_VIEW === 'information-edit');
        spec.domain = [['id', '=', 10]];
      }
      const candidate = await session.page.evaluate(async ({ model, domain, stateField, fields }) => {
        const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
        const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
          method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
          body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model, fields: ['id', stateField || 'state', ...(fields || [])], domain, limit: 1 } }),
        });
        return response.json();
      }, spec);
      report.approvalPages.push({ ...spec, candidate });
      check(`${spec.model}: existing authorized record available`, candidate.ok === true && candidate.data?.records?.length === 1);
      const record = candidate.data.records[0];
      report.recordAuthority = null;
      const informationEdit = process.env.TPL07_APPROVAL_VIEW === 'information-edit';
      const editing = process.env.TPL07_APPROVAL_VIEW === 'edit' || informationEdit;
      let entryContext = '';
      if (informationEdit) {
        check('information edit: project-only responsibility', spec.model === 'project.project');
        const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
          .flatMap((key) => report.routeAuthority?.[key] || []);
        const matches = entries.filter((row) => row.menu_xmlid === 'smart_construction_core.menu_sc_project_project');
        check('information edit: current principal has one authorized entry', matches.length === 1 && Number(matches[0].menu_id) > 0 && Number(matches[0].action_id) > 0);
        report.approvalPages.at(-1).entry = matches[0];
        entryContext = `?menu_id=${Number(matches[0].menu_id)}&action_id=${Number(matches[0].action_id)}`;
      }
      const responseStart = report.contractResponses?.length || 0;
      await form(session.page, `/${editing ? 'f' : 'r'}/${spec.model}/${record.id}${entryContext}`, spec.model, editing ? 'form' : 'readonly');
      // Embedded relation contracts can finish after the main record. Select
      // this navigation's exact record, never the last unrelated response.
      const authority = (report.contractResponses || []).slice(responseStart)
        .map((row) => findRecordAuthority(row.contract))
        .findLast((row) => row?.model === spec.model && Number(row.mainData?.id) === Number(record.id));
      check(`${spec.model}: matching effective contract`, authority?.model === spec.model && authority.mainData?.[spec.stateField || 'state'] === record[spec.stateField || 'state']);
      report.approvalPages.at(-1).authority = authority;
      if (redFlushDenialInspect) {
        const finalContract = (report.contractResponses || []).slice(responseStart)
          .map(row => row.contract?.data)
          .findLast(contract => contract?.pageInfo?.model === spec.model && contract.dataContract?.mainData?.id === record.id);
        check('red flush: exact final contract observed', Boolean(finalContract));
        const declarations = (finalContract.workflowContract?.availableActions || []).filter(row => row.method === 'action_confirm');
        check('red flush: source already confirmed explicitly denies completion', declarations.length === 1
          && declarations[0].enabled === false && declarations[0].reason_code === 'RED_FLUSH_SOURCE_ALREADY_CONFIRMED');
        const denied = declarations[0];
        const rules = (authority.actions?.actionRuleList || []).filter(row => row.button?.type === 'object' && row.button.name === denied.method);
        check('red flush: workflow denial reaches final rule', rules.length === 1
          && rules[0].allowed === false && rules[0].enabled === false && rules[0].disabled === true);
        const rule = rules[0];
        const status = finalContract.statusContract?.buttonStatus?.find(row => row.backendIdentity === rule.backendIdentity);
        check('red flush: workflow denial reaches visible button status', status?.visible === true && status.disabled === true
          && rule.reasonCode === denied.reason_code && status.reasonCode === denied.reason_code);
        const button = session.page.getByRole('button', { name: rule.label, exact: true });
        check('red flush: visible action exists and is disabled', await button.count() === 1 && await button.isDisabled());
        check('red flush: workflow explanation remains visible',
          Boolean(denied.blocked_message) && await session.page.getByText(denied.blocked_message, { exact: true }).count() > 0);
        check('red flush: source relation displays authoritative invoice number', Boolean(authority.mainData.invoice_no)
          && authority.mainData.original_ledger_id?.[1] === authority.mainData.invoice_no);
      }
      if (spec.model === 'sc.expense.claim') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_done', 'complete']]) {
          check(`expense: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check('expense: completion absent before approval or after execution', await session.page.getByRole('button', { name: '完成', exact: true }).count() === 0);
      }
      if (['sc.plan', 'sc.construction.diary'].includes(spec.model)) {
        const rules = authority.actions?.actionRuleList || [];
        check(`${spec.model}: native approval methods declared`, ['validate_tier', 'reject_tier'].every((method) => rules.some((rule) => rule.button?.name === method)));
        const completeState = spec.model === 'sc.plan' ? 'in_progress' : 'confirmed';
        if (record.state !== completeState) {
          check(`${spec.model}: premature completion absent`, await session.page.getByRole('button', { name: '完成', exact: true }).count() === 0);
        }
        if (spec.model === 'sc.plan' && record.state !== 'cancel') {
          check('plan: reset absent outside cancelled state', await session.page.getByRole('button', { name: '重置草稿', exact: true }).count() === 0);
        }
      }
      if (['sc.equipment.plan', 'sc.equipment.request', 'sc.labor.plan', 'sc.labor.request', 'sc.material.rental.plan', 'sc.subcontract.plan', 'sc.subcontract.request'].includes(spec.model)) {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject']]) {
          check(`${spec.model}: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        check(`${spec.model}: legacy direct approval retired`, !rules.some((rule) => rule.button?.name === 'action_approve'));
      }
      if (spec.model === 'sc.material.rental.order') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_activate', 'start_execution'], ['action_return', 'complete'], ['action_settle', 'complete']]) {
          check(`rental order: ${method} responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        for (const [state, name] of [['approved', '确认租赁'], ['active', '确认退还'], ['returned', '完成结算']]) {
          if (record.state !== state) check(`rental order: ${name} respects state`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
        }
      }
      if (executionLabels) {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_confirm', 'complete']]) {
          check(`${spec.model}: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check(`${spec.model}: confirmation absent outside approved`, await session.page.getByRole('button', { name: executionLabels[1], exact: true }).count() === 0);
      }
      if (spec.model === 'sc.material.settlement') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_confirm', 'complete']]) {
          check(`material settlement: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check('material settlement: confirmation absent outside approved', await session.page.getByRole('button', { name: '确认结算', exact: true }).count() === 0);
        if (record.state !== 'confirmed') check('material settlement: remaining payment absent before confirmation', await session.page.getByRole('button', { name: '生成剩余付款申请', exact: true }).count() === 0);
      }
      if (spec.model === 'sc.material.rfq') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_select', 'complete']]) {
          check(`RFQ: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check('RFQ: quote selection absent before approval or after selection', await session.page.getByRole('button', { name: '确定报价', exact: true }).count() === 0);
        if (record.state !== 'selected') check('RFQ: order generation absent before selection', await session.page.getByRole('button', { name: '生成采购订单', exact: true }).count() === 0);
      }
      if (spec.model === 'sc.material.purchase.request') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject']]) {
          check(`purchase request: ${method} declares its business meaning`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        check('purchase request: old direct approval entry retired', !rules.some((rule) => rule.button?.name === 'action_approve'));
        if (record.state !== 'approved') {
          for (const name of ['生成询价单', '生成采购订单']) check(`purchase request: ${name} absent outside approved`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
        }
      }
      if (spec.model === 'sc.material.acceptance') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_accept', 'complete'], ['action_reject', 'complete']]) {
          check(`acceptance: ${method} has distinct declared responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') {
          for (const name of ['验收通过', '验收不通过']) check(`acceptance: ${name} absent outside approved`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
        }
      }
      if (spec.model === 'sc.material.inbound') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_receive', 'complete']]) {
          check(`inbound: ${method} declares its business meaning`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check('inbound: no receiving before approval or after receipt', await session.page.getByRole('button', { name: '确认入库', exact: true }).count() === 0);
      }
      if (spec.model === 'project.project') {
        const rules = authority.actions?.actionRuleList || [];
        if (informationEdit) {
          check('information edit: submission is the only native workflow action', rules.filter((rule) => rule.button?.type === 'object').every((rule) => rule.button.name === 'action_sc_submit') && rules.some((rule) => rule.button?.name === 'action_sc_submit' && rule.actionSemantics?.purpose === 'submit'));
          check('information edit: effective entry remains editable', authority.status?.effectiveRenderProfile === 'edit' || authority.status?.effectiveRenderProfile === 'editable');
        } else {
          check('project: submit and start are distinct native methods', ['action_sc_submit', 'action_sc_start'].every((method) => rules.some((rule) => rule.button?.name === method)));
          for (const [method, purpose] of [['action_sc_submit', 'submit'], ['action_sc_start', 'start_execution'], ['validate_tier', 'approve'], ['reject_tier', 'reject']]) {
            check(`project: ${method} has declared business meaning`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
          }
        }
        if (editing && record.lifecycle_state === 'draft' && record.sc_approval_state === 'draft') {
          check('project: editable draft exposes submission', await session.page.getByRole('button', { name: '提交立项', exact: true }).first().isVisible());
        }
        if (record.lifecycle_state !== 'draft' || record.sc_approval_state !== 'approved') {
          check('project: start absent before approval or after startup', await session.page.getByRole('button', { name: '启动项目', exact: true }).count() === 0);
        }
        check('project: approval state remains a separate fact', authority.mainData?.sc_approval_state === record.sc_approval_state);
        if (projectSave) {
          const request = (params) => session.page.evaluate(async (params) => {
            const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
            const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
              method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
              body: JSON.stringify({ intent: 'api.data', params }),
            });
            return response.json();
          }, params);
          const read = async () => {
            const result = await request({ op: 'read', model: 'project.project', ids: [10], fields: ['id', 'name', 'company_id', 'lifecycle_state', 'sc_approval_state'] });
            assert.equal(result.ok, true);
            assert.equal(result.data?.records?.length, 1);
            return result.data.records[0];
          };
          const baseline = await read();
          check('project save: exact draft object authority', baseline.id === 10 && baseline.lifecycle_state === 'draft'
            && baseline.sc_approval_state === 'draft' && baseline.name === authority.mainData.name);
          const temporaryName = `${baseline.name} [TPL53保存验证]`;
          report.projectSave = { baseline, temporaryName, restored: false };
          await fs.writeFile(path.join(out, 'project-save-recovery.json'), JSON.stringify(report.projectSave, null, 2));
          try {
            const saveAction = authority.actions.actionRuleList.find((rule) => rule.actionSemantics?.purpose === 'save_draft');
            check('project save: explicit enabled write action', saveAction?.enabled === true && saveAction.target?.operation === 'write');
            await session.page.locator('[data-field-name="name"] input').fill(temporaryName);
            projectWritePermit = { name: temporaryName };
            const response = session.page.waitForResponse((res) => {
              try { const body = res.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'write'; } catch { return false; }
            });
            const [saved] = await Promise.all([response, session.page.getByRole('button', { name: saveAction.label, exact: true }).click()]);
            const result = await saved.json();
            check('project save: write accepted', result.ok === true);
            const observed = await read();
            check('project save: authoritative readback preserves lifecycle', observed.name === temporaryName
              && observed.lifecycle_state === baseline.lifecycle_state && observed.sc_approval_state === baseline.sc_approval_state);
            report.projectSave.saved = observed;
          } finally {
            projectWritePermit = null;
            const current = await read();
            assert.ok(current.name === baseline.name || current.name === temporaryName, 'project changed outside this probe; refuse restoration overwrite');
            if (current.name === temporaryName) {
              projectWritePermit = { name: baseline.name };
              const restored = await request({ op: 'write', model: 'project.project', ids: [10], vals: { name: baseline.name } });
              assert.equal(restored.ok, true, 'project restoration rejected');
            }
            projectWritePermit = null;
            assert.deepEqual(await read(), baseline, 'project baseline not restored');
            report.projectSave.restored = true;
            await fs.writeFile(path.join(out, 'project-save-recovery.json'), JSON.stringify(report.projectSave, null, 2));
            check('project save: original business values restored', true);
          }
          await session.page.reload();
          await session.page.locator('[data-field-name="name"] input').waitFor();
          check('project save: reloaded official form shows restored name', await session.page.locator('[data-field-name="name"] input').inputValue() === baseline.name);
        }
      }
      if (spec.model === 'sc.payment.execution') {
        check('paid execution: unrelated payment prerequisite absent', await session.page.getByText('新系统付款执行必须填写付款账户信息。', { exact: true }).count() === 0);
        check('paid execution: reversal entry is visible', await session.page.getByRole('button', { name: '撤销付款', exact: true }).count() === 1);
        check('paid execution: pre-payment cancellation is absent', await session.page.getByRole('button', { name: '取消', exact: true }).count() === 0);
        check('paid execution: duplicate payment is absent', await session.page.getByRole('button', { name: '已付款', exact: true }).count() === 0);
        const reversal = authority.actions?.actionRuleList?.find((action) => action.button?.name === 'action_reverse_payment');
        check('paid execution: native reversal declares confirmation', reversal?.actionSafety?.requires_confirm === true && reversal.actionSafety.classification === 'danger');
        await session.page.getByRole('button', { name: '撤销付款', exact: true }).click();
        const dialog = session.page.getByRole('dialog');
        await dialog.waitFor();
        check('paid execution: confirmation consumes declared consequence', (await dialog.innerText()).includes(reversal.actionSafety.confirm_message));
        await dialog.getByRole('button', { name: '取消', exact: true }).click();
        await dialog.waitFor({ state: 'hidden' });
        check('paid execution: cancelled confirmation dispatched no write', report.forbiddenWrites.length === 0);

      }
      for (const width of [1440, 390]) {
        await session.page.setViewportSize({ width, height: 900 });
        if (spec.model === 'sc.payment.execution') {
          const relationValue = authority.mainData.payment_request_id;
          check(`paid execution-${width}: declared relation label available`, Array.isArray(relationValue) && Boolean(relationValue[1]));
          const relation = session.page.getByRole('button').filter({ hasText: String(relationValue[1]) });
          check(`paid execution-${width}: one relation action`, await relation.count() === 1);
          const geometry = await relation.evaluate((button) => {
            const bounds = button.getBoundingClientRect();
            const walker = document.createTreeWalker(button, NodeFilter.SHOW_TEXT);
            const lines = [];
            for (let node = walker.nextNode(); node; node = walker.nextNode()) {
              if (!node.textContent?.trim()) continue;
              const range = document.createRange();
              range.selectNodeContents(node);
              for (const rect of range.getClientRects()) lines.push({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom });
            }
            return { bounds: { left: bounds.left, right: bounds.right, top: bounds.top, bottom: bounds.bottom }, lines };
          });
          (report.readonlyRelationGeometry ||= []).push({ model: spec.model, width, ...geometry });
          check(`paid execution-${width}: relation text fits its action`, geometry.lines.length > 0 && geometry.lines.every((line) =>
            line.left >= geometry.bounds.left - 1 && line.right <= geometry.bounds.right + 1
            && line.top >= geometry.bounds.top - 1 && line.bottom <= geometry.bounds.bottom + 1));
        }
        check(`${spec.model}-${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        await session.page.screenshot({ animations: 'disabled', path: path.join(out, `${spec.model}-${width}.png`) });
      }
      if (spec.model === 'sc.payment.execution') {
        const originUrl = session.page.url();
        const relationValue = authority.mainData.payment_request_id;
        const targetId = Number(relationValue[0]);
        const fields = [];
        const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
        walk(authority.layout?.containerTree);
        const entry = fields.find((field) => field.name === 'payment_request_id')?.fieldInfo?.relation_entry;
        check('paid relation: explicit authorized entry', entry?.can_read === true && entry.can_open === true && entry.model === 'payment.request');
        const waitRecordContract = (model, id) => session.page.waitForResponse(async (response) => {
          try {
            const body = response.request().postDataJSON();
            if (!String(body?.intent || '').startsWith('ui.contract')) return false;
            const current = findRecordAuthority(await response.json());
            return current?.model === model && Number(current.mainData?.id) === id;
          } catch { return false; }
        });
        const targetResponse = waitRecordContract(entry.model, targetId);
        await session.page.getByRole('button').filter({ hasText: String(relationValue[1]) }).click();
        const targetAuthority = findRecordAuthority(await (await targetResponse).json());
        await session.page.waitForURL((url) => url.pathname.endsWith(`/payment.request/${targetId}`));
        const targetUrl = new URL(session.page.url());
        check('paid relation: target uses declared menu and action', Number(targetUrl.searchParams.get('menu_id')) === Number(entry.menu_id)
          && Number(targetUrl.searchParams.get('action_id')) === Number(entry.action_id));
        const sourceUrl = new URL(originUrl);
        check('paid relation: return context preserves source', decodeURIComponent(targetUrl.searchParams.get('return_url') || '') === `${sourceUrl.pathname}${sourceUrl.search}`
          && targetUrl.searchParams.get('return_model') === spec.model && targetUrl.searchParams.get('return_field') === 'payment_request_id');
        const targetProfile = targetAuthority.status.effectiveRenderProfile;
        await session.page.locator(targetProfile === 'readonly'
          ? '[data-detail-composition="official-standard-detail"][data-state="ok"]'
          : '[data-form-composition="official-standard-form"][data-state="ok"]').waitFor();
        check('paid relation: target identity and declared renderer', Number(targetAuthority.mainData.id) === targetId
          && await session.page.locator('[data-field-fail-closed]').count() === 0);
        report.paidRelationNavigation = { source: { model: spec.model, id: record.id, url: originUrl }, target: { model: entry.model, id: targetId, url: targetUrl.href, profile: targetProfile } };
        await session.page.goBack();
        await session.page.waitForURL(originUrl);
        const restoredPage = session.page.locator(`[data-form-model="${spec.model}"][data-form-record="${record.id}"][data-detail-composition="official-standard-detail"][data-state="ok"]`);
        await restoredPage.waitFor();
        check('paid relation: browser back restores exact source', session.page.url() === originUrl && await restoredPage.count() === 1);
        await restoredPage.getByRole('button', { name: '撤销付款', exact: true }).waitFor({ state: 'visible' });
        // The status badge includes the accessibility prefix “状态：”; its
        // declared title identifies the label without assuming a bare text node.
        await restoredPage.getByLabel('业务状态', { exact: true }).getByTitle('已付款', { exact: true }).waitFor({ state: 'visible' });
        const terminalActions = {
          reversal: await restoredPage.getByRole('button', { name: '撤销付款', exact: true }).count(),
          duplicatePayment: await restoredPage.getByRole('button', { name: '已付款', exact: true }).count(),
        };
        check('paid relation: cached source keeps terminal actions', terminalActions.reversal === 1 && terminalActions.duplicatePayment === 0, terminalActions);
        await session.page.screenshot({ animations: 'disabled', path: path.join(out, 'paid-relation-return.png') });
        check('paid relation: navigation dispatched no business write', report.forbiddenWrites.length === 0);
      }
      await session.ctx.close();
    }
  } else if (process.env.TPL07_SCOPE === 'detail-state') {
    const finance = await login('fixture_role_finance');
    const stateOriginId = (await resolveGovernedOrigin(finance.page)).id;
    await form(finance.page, `/r/payment.request/${stateOriginId}?menu_id=545&action_id=775`, 'detail-state', 'readonly');
    let authority = report.recordAuthority;
    check('detail state: effective record authority received', authority?.model === 'payment.request');
    check('detail state: allowed draft has no invented denial', await finance.page.locator('[data-record-action-denials]').count() === 0);
    const statePolicy = authority.deletePolicy;
    const candidate = await finance.page.evaluate(async ({ field, allowed, project, company }) => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      const domain = [[field, 'not in', allowed]];
      if (project) domain.push(['project_id', '=', project]);
      if (company) domain.push(['company_id', '=', company]);
      const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
        body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model: 'payment.request', fields: ['id', field], domain, limit: 1 } }),
      });
      return response.json();
    }, { field: statePolicy.state_field, allowed: statePolicy.allowed_states,
      project: Array.isArray(authority.mainData.project_id) ? authority.mainData.project_id[0] : authority.mainData.project_id,
      company: Array.isArray(authority.mainData.company_id) ? authority.mainData.company_id[0] : authority.mainData.company_id });
    check('detail state: existing restricted record available in same scope', candidate.ok === true && candidate.data?.records?.length === 1);
    report.restrictedRecord = candidate.data.records[0];
    await form(finance.page, `/r/payment.request/${report.restrictedRecord.id}?menu_id=545&action_id=775`, 'detail-state-restricted', 'readonly');
    authority = report.recordAuthority;
    const caps = authority.status.effectiveRecordCapabilities;
    const reasons = authority.status.recordDeniedReasons || {};
    const policy = authority.deletePolicy || {};
    const stateBlocked = policy.policy_kind === 'state_limited_business_document'
      && policy.allowed_states?.length && authority.mainData?.[policy.state_field]
      && !policy.allowed_states.includes(authority.mainData[policy.state_field]);
    const declaredDenial = ['write', 'unlink'].some((op) => caps[op] !== true && reasons[op])
      || (policy.allowed === false && policy.reason_code) || (stateBlocked && policy.denied_reason_code);
    check('detail state: restriction explicitly declared', Boolean(declaredDenial));
    for (const width of [1440, 390]) {
      await finance.page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
      const notice = finance.page.locator('[data-record-action-denials]');
      check(`detail-state-${width}: explicit denials drive feedback`, await notice.count() === (declaredDenial ? 1 : 0));
      if (declaredDenial) {
        check(`detail-state-${width}: official alert owns feedback`, await notice.getAttribute('data-semantic-driver') === 'tdesign-alert');
        check(`detail-state-${width}: feedback explains restriction`, /不可编辑|不可删除/.test(await notice.innerText()));
      }
      check(`detail-state-${width}: no page overflow`, await finance.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await finance.page.screenshot({ animations: 'disabled', path: path.join(out, `detail-state-${width}.png`) });
    }
    await finance.ctx.close();
  } else if (process.env.TPL07_SCOPE === 'favorite-recovery') {
    const finance = await login('fixture_role_finance');
    await list(finance.page, 545, 'recovery-list');
    report.recovery = await finance.page.evaluate(async () => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
        body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model: 'ir.filters', fields: ['id', 'name', 'user_id', 'model_id', 'action_id', 'create_date', 'is_default'], domain: [['name', '=', '仅检查表单，不保存'], ['user_id', '=', 30], ['model_id', '=', 'payment.request'], ['action_id', '=', 775]], limit: 2 } }),
      });
      return { status: response.status, body: await response.json() };
    });
    check('recovery: authoritative read succeeded', report.recovery.body.ok === true);
    check('recovery: probe records are absent', report.recovery.body.data.records.length === 0);
    await finance.page.getByRole('button', { name: '展开搜索菜单', exact: true }).click();
    check('recovery: menu reflects removal', await finance.page.getByText('仅检查表单，不保存', { exact: true }).count() === 0);
    await finance.page.reload();
    await finance.page.locator('[data-list-card-container="official"]').waitFor();
    await finance.page.getByRole('button', { name: '展开搜索菜单', exact: true }).click();
    check('recovery: warm contract menu remains restored', await finance.page.getByText('仅检查表单，不保存', { exact: true }).count() === 0);
    check('recovery: cache-hit delivery exercised', report.projectionCaches?.some((entry) => ['hot', 'persisted'].includes(entry.status)));
    await finance.ctx.close();
  } else if (['favorites', 'favorites-failure', 'favorite-recovery'].includes(process.env.TPL07_SCOPE)) {
    await favoritesScope();
  } else if (process.env.TPL07_SCOPE === 'navigation') {
    await navigationScope();
  } else if (process.env.TPL07_SCOPE === 'style') {
    await styleScope();
  } else if (process.env.TPL07_SCOPE === 'create-edit') {
    await createEditScope();
  } else if (process.env.TPL07_SCOPE === 'detail') {
    const finance = await login('fixture_role_finance');
    const detailOriginId = (await resolveGovernedOrigin(finance.page)).id;
    await form(finance.page, `/r/payment.request/${detailOriginId}?menu_id=545&action_id=775`, 'payment-readonly', 'readonly');
    check('payment: existing company fact preserved', await finance.page.getByText('FE Company A', { exact: true }).count() > 0);
    report.paymentFactText = await finance.page.locator('[data-detail-facts]').allTextContents();
    await finance.page.setViewportSize({ width: 390, height: 844 });
    check('payment detail: narrow page contained', await finance.page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    await finance.page.screenshot({ path: path.join(out, 'payment-readonly-narrow.png') });
    await finance.ctx.close();
    const contract = await login('fixture_role_contract_operator');
    await form(contract.page, '/r/sc.general.contract/11?menu_id=662', 'contract-readonly', 'readonly');
    await contract.ctx.close();
  } else if (process.env.TPL07_SCOPE !== 'additional') {
  const finance = await login('fixture_role_finance');
  const p = finance.page;
  await list(p, 545, 'payment-list');
  const pager = p.locator('[data-semantic-component="ScPagination"]');
  // The page-size control is the only input inside the declared pagination
  // component; options carry their text as the standard `title` attribute.
  await pager.locator('input').click();
  await p.locator('li[title]:visible').filter({ hasText: /^10 条\/页$/ }).click();
  await p.waitForTimeout(1500);
  const before = report.calls.filter((call) => call.model === 'payment.request').at(-1);
  // Page numbers are the only list items inside the declared pagination; going
  // to page 2 exercises the same server-side next-page behaviour.
  await pager.locator('li').filter({ hasText: /^2$/ }).click();
  await p.waitForTimeout(1800);
  const next = report.calls.filter((call) => call.model === 'payment.request').at(-1);
  check('payment: server next page', next.offset === 10 && next.ids.length > 0 && JSON.stringify(next.ids) !== JSON.stringify(before.ids), { ids: next.ids });
  // The record a list opens declares its own mode: a closed row is a readonly
  // detail, so the probe binds the opened page to the identity of the row it
  // clicked and to the composition the contract declared for it, instead of
  // assuming an editable draft sits first on the page. What must hold either
  // way is that the page is classified by the contract (never an unclassified
  // fallback) and keeps the list context it was opened from.
  const openedRow = p.locator('.flat-table tbody tr[data-record-key]').filter({ has: p.locator('td') }).first();
  const openedRecordKey = await openedRow.getAttribute('data-record-key');
  await openedRow.click();
  await p.locator(`[data-form-record="${openedRecordKey}"][data-state="ok"]`).waitFor();
  check('payment: opened record identity matches the clicked row', await p.locator(`[data-form-record="${openedRecordKey}"]`).count() === 1, { openedRecordKey });
  check(
    'payment: opened record composition follows the contract declaration',
    await p.locator('[data-form-composition-reason="contract-record-view"], [data-detail-composition-reason="contract-readonly-record-view"]').count() === 1,
  );
  check(
    'payment: opened record is not an unclassified fallback',
    await p.locator('[data-form-composition-reason="contract-view-not-classified"], [data-detail-composition-reason="contract-view-not-classified"]').count() === 0,
  );
  check('payment: return context carried', new URL(p.url()).searchParams.get('list_offset') === '10');
  await p.goBack();
  await p.locator('[data-list-card-container="official"]').waitFor();
  await p.waitForTimeout(1500);
  check('payment: return keeps page and set', JSON.stringify(report.calls.filter((call) => call.model === 'payment.request').at(-1).ids) === JSON.stringify(next.ids));
  const paymentOriginId = (await resolveGovernedOrigin(p)).id;
  await form(p, `/f/payment.request/${paymentOriginId}?menu_id=545&action_id=775`, 'payment-master-detail');
  check('payment: master detail extension preserved', await p.locator('[data-field-type="one2many"]').count() > 0);
  // The introduce action and its dialog must render the terms the effective
  // contract declares, and a contract gap must surface instead of being
  // rebuilt locally from production copy.
  const declaredIntroduce = report.introduceContract;
  check('payment: introduce contract published to the page', Boolean(declaredIntroduce?.dialog?.title && declaredIntroduce?.introduceLabel));
  const introduceEntry = p.locator('[data-contract-entry-label]');
  // The settlement collection is a declared optional presentation: with no
  // rows it renders collapsed with destroy-on-collapse, so the declared
  // introduce entry is only mounted once its own disclosure is expanded —
  // the same declared-contract consumption the form scope applies above.
  const settlementDisclosure = p.locator(
    '[data-semantic-component="PaymentSettlementDetailCollectionControl"] [data-disclosure-trigger]');
  if (await settlementDisclosure.count() === 1
    && await settlementDisclosure.getAttribute('data-state') === 'collapsed') {
    await settlementDisclosure.click();
    await p.locator('[data-semantic-component="PaymentSettlementDetailCollectionControl"] [data-disclosure-trigger][data-state="expanded"]').waitFor();
  }
  check('payment: introduce entry carries the declared label', await introduceEntry.count() === 1);
  check(
    'payment: introduce entry text is the declared label',
    (await introduceEntry.innerText()).trim() === String(declaredIntroduce.introduceLabel).trim(),
  );
  check('payment: no introduce contract gap rendered', await p.locator('[data-contract-semantic-gap]').count() === 0);
  await introduceEntry.click();
  const introduceDialog = p.locator('[data-dialog-purpose="payment-settlement-introduce"]');
  await introduceDialog.waitFor();
  check(
    'payment: introduce dialog uses the declared title',
    await introduceDialog.getByText(String(declaredIntroduce.dialog.title), { exact: false }).count() > 0,
  );
  check(
    'payment: introduce dialog uses the declared confirm label',
    await p.getByRole('button', { name: String(declaredIntroduce.dialog.confirmLabel), exact: true }).count() > 0,
  );
  await p.screenshot({ path: path.join(out, 'payment-introduce-dialog.png') });
  await p.keyboard.press('Escape');
  await p.locator('[data-dialog-purpose="payment-settlement-introduce"]').waitFor({ state: 'detached' });
  await form(p, `/r/payment.request/${paymentOriginId}?menu_id=545&action_id=775`, 'payment-readonly', 'readonly');
  await p.setViewportSize({ width: 390, height: 844 });
  check('payment detail: narrow page contained', await p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
  await p.screenshot({ path: path.join(out, 'payment-readonly-narrow.png') });
  await finance.ctx.close();

  const contract = await login('fixture_role_contract_operator');
  await list(contract.page, 662, 'contract-list');
  await form(contract.page, '/r/sc.general.contract/11?menu_id=662', 'contract-readonly', 'readonly');
  await contract.ctx.close();
  }

  if (!['scene-entry', 'expense-policy', 'favorite-lifecycle', 'favorite-lifecycle-resume', 'favorite-active-delete', 'favorite-active-delete-resume', 'task-authority', 'approval-actions', 'detail', 'detail-state', 'style', 'create-edit', 'navigation', 'favorites', 'favorites-failure', 'favorite-recovery'].includes(process.env.TPL07_SCOPE)) {
  const admin = await login('fixture_role_config_admin');
  // Resolve a non-pilot entry from authorized navigation instead of model IDs.
  await admin.page.getByPlaceholder('搜索菜单...').fill('客户档案');
  await admin.page.getByText('客户档案', { exact: true }).first().click();
  await admin.page.locator('[data-list-card-container="official"]').waitFor();
  check('non-pilot standard list: official default', await admin.page.locator('[data-list-composition-reason="contract-collection-view"]').count() === 1);
  await admin.page.screenshot({ path: path.join(out, 'customer-list.png') });
  await admin.ctx.close();
  }
  check('no page exceptions', report.errors.length === 0);
  check('no undeclared business writes attempted', report.forbiddenWrites.length === 0);
  report.status = 'passed';
} catch (error) {
  report.status = 'failed';
  report.error = error.message;
  if (['approval-actions', 'expense-policy', 'scene-entry', 'style', 'create-edit'].includes(process.env.TPL07_SCOPE)) {
    report.failurePages = [];
    for (const ctx of browser.contexts()) for (const page of ctx.pages()) {
      report.failurePages.push({ url: page.url(), text: (await page.locator('body').innerText()).slice(0, 8000),
        surfaces: await page.locator('[data-product-page-mode], [data-form-composition], [data-detail-composition], [data-semantic-component="ScForm"], [data-component="FormSection"], [data-canonical-node-kind], [data-field-name]').evaluateAll((nodes) => nodes.map((node) => ({ tag: node.tagName, attributes: Object.fromEntries([...node.attributes].filter((attr) => attr.name.startsWith('data-')).map((attr) => [attr.name, attr.value])) }))) });
      await page.screenshot({ path: path.join(out, `failure-${report.failurePages.length}.png`) });
    }
  }
  process.exitCode = 1;
} finally {
  await Promise.allSettled([...pendingProbeAborts].map((abort) => abort()));
  if (paymentReview?.approvalFlow && paymentReview.configContext && paymentReview.baseline) {
    try {
      const admin = await login('fixture_role_config_admin');
      paymentReview.phase = 'restore_steps';
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(paymentReview, null, 2));
      const restored = await admin.page.evaluate(async ({ model, steps, context }) => {
        const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
        return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
          method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
          body: JSON.stringify({ intent: 'sc.approval_policy.steps.set', params: { model, steps, context } }),
        })).json();
      }, { model: paymentReview.model, steps: paymentReviewOriginalSteps(paymentReview), context: paymentReview.configContext });
      const readback = await admin.page.evaluate(async ({ model, context }) => {
        const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
        return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
          method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
          body: JSON.stringify({ intent: 'sc.approval_policy.config.get', params: { model, context } }),
        })).json();
      }, { model: paymentReview.model, context: paymentReview.configContext });
      report.paymentFlowRestoration = { restored, readback, retainedRecordId: paymentReview.id || null };
      check('payment flow: restored configuration authoritative readback', readback.ok === true
        && JSON.stringify(readback.data?.policy) === JSON.stringify(restored.data?.policy));
      const active = readback.data?.policy?.steps?.filter(step => step.active) || [];
      check('payment flow: original active configuration restored; business record retained', restored.ok === true
        && restored.data.policy.mode === 'single' && active.length === 1 && active[0].id === 2187
        && active[0].approval_scope_key === 'finance_manager' && active[0].name === paymentReviewOriginalSteps(paymentReview)[0].name);
      await admin.ctx.close();
    } catch (error) { report.status = 'failed'; report.cleanupError = error.message; process.exitCode = 1; }
  }
  await browser.close();
  if (expenseSuccess || diarySuccess || eventSuccess || reportSuccess || (paymentReview?.baseline && !paymentReview.approvalFlow)) {
    try { await expenseCleanup('final'); }
    catch (error) { report.status = 'failed'; report.cleanupError = error.message; process.exitCode = 1; }
  }
  await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`[standard_page_type_browser] ${report.status} assertions=${report.assertions.length} report=${out}/report.json`);
}

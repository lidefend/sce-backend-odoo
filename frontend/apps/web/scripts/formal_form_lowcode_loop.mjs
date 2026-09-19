import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { resolveChangeSetOpenResponse, resolveDesignerDraftPolicy, resolveCleanupRelease } from './designer_draft_ownership.mjs';

export async function runFormalFormLoop() {
  const scope = JSON.parse(process.env.FORM_LOWCODE_SCOPE || '{}');
  assert.equal(scope.database, 'sc_dev_demo');
  const [entry, outside] = scope.entries;
  const documentTopic = scope.topic === 'document';
  const invoiceTopic = scope.topic === 'invoice';
  const payrollTopic = scope.topic === 'payroll';
  const usagePerformanceTopic = scope.topic === 'usage_performance';
  // The governed role can only navigate the three delivered menus of this topic.  The
  // registered siblings that share a model and form view sit on menus the delivered route
  // authority denies, so the browser-level isolation claim uses the reachable sibling of
  // the same topic; the shared-view siblings keep their contract-level assertion.
  const usagePerformanceIsolation = usagePerformanceTopic
    ? scope.entries.find((item) => item.action_id === 570 && item.menu_id === 692) || null
    : null;
  if (['material', 'document', 'invoice'].includes(scope.topic)) {
    assert.equal(entry.action_id, documentTopic ? 666 : invoiceTopic ? 785 : 546);
    assert.equal(outside.action_id, documentTopic ? 862 : invoiceTopic ? 787 : 547);
  } else {
    // Read-only representative topics carry their own registered identities.
    assert(entry && entry.action_id > 0, `topic ${scope.topic} must register at least one surface`);
  }
  const base = process.env.BASE_URL;
  const configurationEntryOnly = process.env.FORM_LOWCODE_CONFIG_ENTRY === '1';
  const out = path.resolve(configurationEntryOnly ? '../../../artifacts/config-center-entry/browser'
    : documentTopic ? '../../../artifacts/uc3-document-lowcode/browser'
    : invoiceTopic ? '../../../artifacts/uc4-invoice-lowcode/browser'
    : '../../../artifacts/lowcode-form-loop/browser');
  await fs.mkdir(out, { recursive: true });
  // `dirty` was a literal `true`, so a clean frozen candidate still produced a report
  // that claimed an uncommitted worktree and could never be bound to the frozen SHA.
  // The wrapper now measures it; an unset or unknown value stays `dirty` (fail-closed)
  // rather than borrowing a cleanliness the run did not observe.
  const reportDirty = process.env.CANDIDATE_DIRTY !== '0';
  const report = { candidate: process.env.CANDIDATE_GIT_HEAD, dirty: reportDirty, scope, stages: {}, restored: false, ok: false };
  const navigationOnly = process.env.FORM_LOWCODE_NAV_ONLY === '1';
  const observeOnly = process.env.FORM_LOWCODE_PREVIEW_OBSERVE === '1';
  const closureOnly = process.env.FORM_LOWCODE_PREVIEW_CLOSURE === '1' || observeOnly;
  const emptySectionOnly = documentTopic && process.env.FORM_LOWCODE_DOCUMENT_EMPTY === '1';
  const designerOnly = process.env.FORM_LOWCODE_DESIGNER === '1' || documentTopic || invoiceTopic || payrollTopic;
  const replayOnly = process.env.FORM_LOWCODE_REPLAY === '1';
  const representativeOnly = process.env.FORM_LOWCODE_REPRESENTATIVE === '1';
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await context.newPage();
  report.browser_errors = [];
  page.setDefaultTimeout(15000);
  // Bounded failure diagnostics: enough to attribute a break (URL, DOM, console,
  // failed requests, intent envelopes and recovery state) without recording any
  // credential or capability token.
  const diagnostics = { intents: [], console: [], failed_requests: [] };
  const redact = (value) => String(value ?? '')
    .replace(/Bearer\s+[^\s"']+/gi, 'Bearer <redacted>')
    .replace(/(sc_auth_token:)[^"'\s,}]*/g, '$1<redacted>')
    .replace(/((?:session_id|api_key|password|access_token|change_set_token|token)=)[^&\s"']+/gi, '$1<redacted>');
  const pathOnly = (raw) => { try { const parsed = new URL(raw, base); return `${parsed.origin}${parsed.pathname}`; } catch { return redact(raw).slice(0, 300); } };
  const queryKeys = (raw) => { try { return [...new URL(raw, base).searchParams.keys()].sort(); } catch { return []; } };
  // Every product surface the run touches is instrumented, including the preview and
  // business popups: a failure inside a popup must be attributable from its own DOM,
  // console and request evidence instead of being guessed from the opener page.
  const pages = [];
  const pageKind = (target) => (target === page ? 'main' : `popup_${pages.indexOf(target)}`);
  function attachDiagnostics(target) {
    pages.push(target);
    target.on('pageerror', (error) => report.browser_errors.push({ page: pageKind(target), message: error.message }));
    target.on('console', (message) => {
      if (!['error', 'warning'].includes(message.type()) || diagnostics.console.length >= 40) return;
      diagnostics.console.push({ page: pageKind(target), type: message.type(), text: redact(message.text()).slice(0, 400) });
    });
    target.on('requestfailed', (request) => {
      if (diagnostics.failed_requests.length >= 40) return;
      diagnostics.failed_requests.push({ page: pageKind(target), method: request.method(), path: pathOnly(request.url()), error: redact(request.failure()?.errorText).slice(0, 200) });
    });
  }
  context.on('page', attachDiagnostics);
  attachDiagnostics(page);
  async function captureFailurePage() {
    const read = async (target) => {
      const text = await target.locator('body').innerText().catch(() => '');
      return text || '';
    };
    let surface = page;
    let kind = 'main';
    for (const candidate of [...pages].reverse()) {
      const text = await read(candidate);
      if (text) { surface = candidate; kind = pageKind(candidate); break; }
    }
    let dom = '';
    try { dom = redact(await surface.content()); } catch {}
    try { await fs.writeFile(path.join(out, 'failure-dom.html'), redact(await page.content().catch(() => ''))); } catch {}
    try { await fs.writeFile(path.join(out, `failure-dom-${kind}.html`), dom); } catch {}
    const probe = await surface.evaluate(() => {
      const root = document.querySelector('#app') || document.body;
      const fields = [...document.querySelectorAll('[data-field-name]')].map((node) => node.getAttribute('data-field-name'));
      return {
        ready_state: document.readyState,
        body_text_length: (document.body?.innerText || '').length,
        body_text: (document.body?.innerText || '').slice(0, 4000),
        root_child_count: root ? root.children.length : 0,
        root_html_length: root ? root.innerHTML.length : 0,
        field_nodes: fields.length,
        field_names: fields.slice(0, 80),
        section_nav_items: document.querySelectorAll('[data-form-section-navigation] button').length,
      };
    }).catch(() => null);
    return { page_kind: kind, url: pathOnly(surface.url()), url_query_keys: queryKeys(surface.url()), dom_file: `failure-dom-${kind}.html`, dom_length: dom.length, ...(probe || {}) };
  }
  const pending = [];
  // token -> change_set id of every draft this run holds for cleanup. Ownership is
  // proved from the id against the pre-run inventory, never from the token alone.
  const drafts = new Map();
  let baseline;
  const walk = function* (rows) {
    for (const node of rows || []) {
      if (!node || typeof node !== 'object') continue;
      yield node;
      for (const key of ['children', 'tabs', 'pages', 'nodes', 'items']) if (Array.isArray(node[key])) yield* walk(node[key]);
    }
  };
  const tree = (contract) => contract.layoutContract.containerTree;
  const effective = (contract) => ({ layout: contract.layoutContract, policies: contract.statusContract, actions: contract.actionContract });
  async function intent(name, params = {}, ok = true) {
    const started = Date.now();
    let response;
    try {
      response = await page.evaluate(async ({ name, params, db }) => {
        const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
        const res = await fetch('/api/v1/intent', { method: 'POST', headers: { Authorization: `Bearer ${token || ''}`, 'Content-Type': 'application/json', 'X-Odoo-DB': db }, body: JSON.stringify({ intent: name, params }) });
        return { status: res.status, body: await res.json() };
      }, { name, params, db: scope.database });
    } catch (error) {
      diagnostics.intents.push({ intent: name, param_keys: Object.keys(params).sort(), status: null, ok: null, error: redact(error.message).slice(0, 200), ms: Date.now() - started });
      throw error;
    }
    diagnostics.intents.push({ intent: name, param_keys: Object.keys(params).sort(), status: response.status, ok: response.body?.ok ?? null, error: response.body?.ok === false ? redact(String(response.body.error?.code || response.body.error || '')).slice(0, 200) : null, ms: Date.now() - started });
    if (diagnostics.intents.length > 120) diagnostics.intents.splice(0, diagnostics.intents.length - 120);
    if (ok) assert.equal(response.body.ok, true, `${name}: ${JSON.stringify(response.body.error || response.body.message || response.body)}`);
    return response.body;
  }
  const cs = (name, params = {}, ok = true) => intent(`ui.business_config.change_set.${name}`, { role_key: scope.role_key, ...params }, ok);
  const contract = async (surface = entry, extra = {}) => (await intent('ui.contract.v2', { op: 'model', model: surface.model, action_id: surface.action_id, menu_id: surface.menu_id, view_id: surface.view_id, view_type: 'form', render_profile: 'create', ...extra })).data;
  const url = (extra = {}) => `${base}/f/${entry.model}/new?${new URLSearchParams({ menu_id: String(entry.menu_id), action_id: String(entry.action_id), ...extra })}`;
  async function observe(name, expected, extra = {}) {
    await page.goto(url(extra), { waitUntil: 'domcontentloaded', timeout: 30000 });
    if (expected) await page.getByText(expected, { exact: true }).first().waitFor({ state: 'visible' });
    else await page.getByText('入库日期', { exact: true }).first().waitFor({ state: 'visible' });
    await page.evaluate(() => { window.scrollTo(0, 0); for (const node of document.querySelectorAll('*')) if (node.scrollTop) node.scrollTop = 0; });
    await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: true });
    return { url: page.url(), screenshot: `${name}.png`, text: (await page.locator('body').innerText()).slice(0, 6000) };
  }
  const binding = (node, extra) => ({ target: node.nativeLocator, expected: { type: node.type, name: node.name ?? null, occurrence_index: node.occurrenceIndex }, ...extra });
  const transportFailures = () => diagnostics.failed_requests.filter((entry) => /net::ERR_/.test(entry.error || ''));
  const transportRecovery = (stage) => {
    const failures = transportFailures();
    return { stage, classification: failures.length ? 'environment_transport' : 'app_shell_not_mounted', aborted_module_requests: failures.length, examples: failures.slice(0, 3) };
  };
  // A transport abort only explains a failure when the page could not render at all;
  // a partial abort must never excuse a product or locator failure.
  const classifyFailure = (failurePage) => {
    const aborted = transportFailures().length;
    const rendered = (failurePage?.body_text_length || 0) > 0 && (failurePage?.root_child_count || 0) > 0;
    if (aborted && !rendered) return 'environment_transport';
    return aborted ? 'environment_transport_partial' : 'product_or_locator';
  };
  // The application shell must actually mount before any product assertion runs.
  // A broken module transport (host network change aborting in-flight fetches)
  // must be attributed as an environment prerequisite failure, never as a form
  // structure defect, and must fail fast instead of timing out silently.
  async function appShellMounted(timeout = 15000) {
    return page.locator('#app > *').first().waitFor({ state: 'attached', timeout }).then(() => true).catch(() => false);
  }
  // One bounded recovery attempt for a transient host-network abort: re-navigate
  // and re-probe the mount. The recovery fact is recorded; the timeout is not
  // extended and no product assertion is relaxed.
  async function mountOrRecoverOnce() {
    if (await appShellMounted()) return { recovered: false };
    const first = transportRecovery('login_mount');
    await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    const mounted = await appShellMounted();
    report.transport_recovery = { ...first, recovery_attempt: 'remount', recovered: mounted };
    return { recovered: mounted, first };
  }
  // The same transient abort can blank a page in the middle of a journey, not only
  // at login.  Every navigation whose application shell did not mount and whose
  // aborted requests are transport errors (`net::ERR_*`) is retried exactly once
  // and recorded.  A page that still does not mount keeps its original assertion,
  // so the failure stays attributable instead of being masked.
  report.transport_recoveries = [];
  const navigate = page.goto.bind(page);
  page.goto = async (target, options) => {
    const response = await navigate(target, options);
    if (await appShellMounted()) return response;
    if (!transportFailures().length) return response;
    const record = { ...transportRecovery('post_navigation_mount'), url: pathOnly(String(target)) };
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const retried = await navigate(target, options);
    const mounted = await appShellMounted();
    report.transport_recoveries.push({ ...record, recovery_attempt: 'renavigate_once', recovered: mounted });
    return retried;
  };
  async function rollback(token) {
    const result = (await cs('rollback', { change_set_token: token, request_id: `restore-${token}` })).data;
    assert.equal(result.publish_result.runtime_verified, true);
    pending.splice(pending.indexOf(token), 1);
    return result;
  }
  try {
    const health = await page.request.get(`${base}/`, { timeout: 5000 });
    assert(health.ok(), 'frontend health failed');
    await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    const mount = await mountOrRecoverOnce();
    if (!mount.recovered && report.transport_recovery) {
      const failure = report.transport_recovery;
      assert.equal(failure.classification, 'app_shell_not_mounted', `login page did not mount: ${failure.aborted_module_requests} module requests aborted (${failure.examples.map((entry) => entry.error).join(', ')}); environment prerequisite not recovered`);
      assert.fail('login page mounted no application shell');
    }
    const inputs = page.locator('input');
    await inputs.nth(0).fill(process.env.E2E_LOGIN);
    await inputs.nth(1).fill(process.env.E2E_PASSWORD);
    if (await inputs.count() > 2 && await inputs.nth(2).isEnabled()) await inputs.nth(2).fill(scope.database);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL((target) => !target.pathname.includes('/login'), { timeout: 30000 });
    if (process.env.FORM_LOWCODE_READ_FAILURE === '1') {
      const previous = JSON.parse(await fs.readFile(path.join(out, 'designer-report.json'), 'utf8'));
      const token = new URL(previous.failurePage.url).searchParams.get('change_set_token');
      assert(token, 'no failed designer draft to read');
      const result = (await cs('get', { change_set_token: token })).data;
      console.log(JSON.stringify({ id: result.id, state: result.state, failure: result.failure_message, items: result.items }));
      return;
    }
    baseline = await contract();
    const otherBaseline = await contract(outside);
    await fs.writeFile(path.join(out, configurationEntryOnly ? 'entry-baseline-contracts.json' : emptySectionOnly ? 'empty-section-baseline.json' : 'baseline.json'), JSON.stringify({ entry: baseline, outside: otherBaseline }, null, 2));
    if (!navigationOnly && !designerOnly && !closureOnly && !representativeOnly) report.stages.default = await observe('default');
    if (configurationEntryOnly) {
      if (process.env.FORM_LOWCODE_CONFIG_BATCH === '1') {
        const { checkConfigurationCenterBatch } = await import('./configuration_center_batch_journey.mjs');
        await checkConfigurationCenterBatch({ page, scope, intent, out, report });
      } else {
        const { checkConfigurationEntry } = await import('./formal_form_document_journey.mjs');
        await checkConfigurationEntry({ page, scope, intent, out, report });
      }
      report.ok = true;
    } else if (emptySectionOnly) {
      const { checkEmptyDocumentSource } = await import('./formal_form_document_journey.mjs');
      await checkEmptyDocumentSource({ page, entry, out, report });
      report.ok = true;
    } else if (representativeOnly) {
      const { runRepresentativeSurface } = await import('./formal_form_representative_journey.mjs');
      await runRepresentativeSurface({ page, scope, contract, out, report });
      report.ok = true; report.restored = true;
      // A registered fact that could not run is printed with its reason so the
      // operator sees the coverage gap instead of reading a shorter route list.
      for (const row of report.representative_uncovered || []) {
        console.log(`[formal_form_lowcode_loop] UNCOVERED action=${row.action_id} fact=${row.fact} state=${row.state} domain_rows=${row.domain_rows} business_rows=${row.business_row_count}`);
      }
      for (const row of report.representative_blocked || []) {
        console.log(`[formal_form_lowcode_loop] BLOCKED action=${row.action_id} reason=${row.reason}`);
      }
    } else if (observeOnly) {
      const previous = JSON.parse(await fs.readFile(path.join(out, 'closure-report.json'), 'utf8'));
      await page.goto(previous.review.preview_url, { waitUntil: 'domcontentloaded' });
      await page.locator('[data-configuration-preview]').waitFor();
      await page.getByText('设计器保管员', { exact: true }).first().waitFor();
      await page.screenshot({ path: path.join(out, 'closure-preview-desktop.png'), fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      await page.screenshot({ path: path.join(out, 'closure-preview-narrow.png'), fullPage: true });
      await page.locator('[data-section-tab="入库明细"]').last().scrollIntoViewIfNeeded();
      const banner = await page.locator('[data-configuration-preview]').boundingBox();
      assert(banner && banner.y >= 0 && banner.y + banner.height <= 844, 'preview marker is not persistent');
      const unobscured = await page.locator('[data-configuration-preview]').evaluate((node) => {
        const box = node.getBoundingClientRect();
        const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
        return node.contains(hit);
      });
      assert(unobscured, 'preview marker is occluded');
      report.banner_after_scroll = { ...banner, unobscured };
      await page.screenshot({ path: path.join(out, 'closure-preview-narrow-scrolled.png'), fullPage: true });
      await page.goto(previous.review.designer_url, { waitUntil: 'domcontentloaded' });
      const summary = page.locator('[data-bound-change-summary]');
      await summary.getByText(/^顺序：/).waitFor();
      await summary.scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(out, 'closure-summary-narrow.png'), fullPage: true });
      const bounds = await summary.boundingBox();
      assert(bounds && bounds.x >= 0 && bounds.x + bounds.width <= 391, 'summary overflow');
      report.stages.observation = { persistent_preview_marker: 'passed', narrow_summary: 'passed' };
      report.ok = true; report.restored = true;
    } else if (closureOnly) {
      const previous = JSON.parse(await fs.readFile(path.join(out, 'designer-report.json'), 'utf8'));
      await page.goto(previous.review.designer_url, { waitUntil: 'domcontentloaded' });
      const panel = page.locator('[data-bound-form-designer]');
      await panel.getByRole('button', { name: '验证并预览', exact: true }).waitFor();
      assert.equal(await panel.locator('select').count(), 0, 'native select remains');
      assert.equal(await panel.locator('[data-semantic-component="ScSelect"]').count(), 2);
      const summary = panel.locator('[data-bound-change-summary]');
      for (const text of ['标签：', '顺序：', '分组：', '显隐：']) await summary.getByText(new RegExp(text)).waitFor();
      // Exercise the actual design-system selector without saving changes.
      await panel.getByLabel('字段显示', { exact: true }).click();
      await page.getByText('保持原规则', { exact: true }).last().click();
      await panel.getByRole('heading', { name: '当前页面字段配置' }).click();
      await page.screenshot({ path: path.join(out, 'closure-designer-desktop.png'), fullPage: true });
      await panel.getByRole('button', { name: '验证并预览', exact: true }).click();
      await panel.locator('[data-bound-preview-link]').waitFor();
      const popup = page.waitForEvent('popup');
      await panel.locator('[data-bound-preview-link]').click();
      const preview = await popup;
      await preview.locator('[data-configuration-preview]').waitFor();
      try { await preview.getByText('设计器保管员', { exact: true }).first().waitFor(); } catch (error) { report.preview_failure = await preview.locator('body').innerText(); throw error; }
      for (const text of ['保存草稿', '提交', '上传附件']) assert.equal(await preview.getByRole('button', { name: text, exact: true }).filter({ visible: true }).count(), 0, text);
      await preview.getByRole('link', { name: '返回设计器', exact: true }).waitFor();
      const blocked = await preview.evaluate(async () => {
        const { intentRequest } = await import('/src/api/intents.ts');
        try { await intentRequest({ intent: 'api.data', params: { model: 'sc.material.inbound', op: 'create', values: { __preview_invalid_field__: true } } }); return 'unexpected_success'; }
        catch (error) { return `${error.reasonCode}: ${error.message}`; }
      });
      assert(blocked.includes('CONFIG_PREVIEW_READ_ONLY'), blocked);
      await preview.screenshot({ path: path.join(out, 'closure-preview-desktop.png'), fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      await preview.setViewportSize({ width: 390, height: 844 });
      await page.screenshot({ path: path.join(out, 'closure-designer-narrow.png'), fullPage: true });
      await preview.screenshot({ path: path.join(out, 'closure-preview-narrow.png'), fullPage: true });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'designer horizontal overflow');
      assert(await preview.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'preview horizontal overflow');
      report.review = { designer_url: page.url(), preview_url: preview.url(), login: scope.login };
      await preview.getByRole('link', { name: '返回设计器', exact: true }).click();
      await preview.locator('[data-bound-form-designer]').waitFor();
      assert(!new URL(preview.url()).searchParams.has('preview_token'));
      assert(new URL(preview.url()).searchParams.get('change_set_token'));
      assert.deepEqual(effective(await contract()), effective(baseline));
      assert.deepEqual(effective(await contract(outside)), effective(otherBaseline));
      report.stages.closure = { preview_readonly: 'passed', write_rejected: blocked, designer_components: 'passed', summary: 'passed', desktop: 'passed', narrow: 'passed', return_to_designer: 'passed' };
      report.ok = true; report.restored = true;
    } else if (designerOnly) {
      // The product resumes whichever open draft it finds for the designer target.
      // A draft that already existed is somebody else's work: refuse before the
      // first write unless the operator authorized that exact draft id *and*
      // operation. A missing inventory (unknown ownership) is also a refusal.
      const draftPolicy = resolveDesignerDraftPolicy({
        inventory: scope.designer_drafts,
        authorization: process.env.FORM_LOWCODE_AUTHORIZED_DRAFT,
      });
      draftPolicy.inventoryIds = draftPolicy.inventoryIds || [];
      draftPolicy.roleKey = scope.role_key;
      report.designer_draft_policy = { decision: draftPolicy.decision, reason: draftPolicy.reason || null,
        inventory_ids: draftPolicy.inventoryIds, allowed: draftPolicy.allowed };
      if (documentTopic) {
        const { checkDocumentDefaults } = await import('./formal_form_document_journey.mjs');
        await checkDocumentDefaults({ page, entry, outside, contract, out, report });
      }
      if (invoiceTopic) {
        const { checkInvoiceDefaults } = await import('./formal_form_invoice_journey.mjs');
        await checkInvoiceDefaults({ page, scope, contract, out, report });
      }
      if (replayOnly) {
        // Read-only replay: the designer journey (which opens drafts) is skipped
        // on purpose so a failing entry surface can be attributed without writes.
        // It opens no draft and stages nothing, so a *write* authorization must not gate
        // it: refusing here would hide the entry surface behind a draft the run is
        // deliberately leaving untouched. The policy is still reported as an observation.
        report.stages.replay = { mode: 'read_only_entry_surface', designer_journey: 'skipped',
          draft_policy: draftPolicy.decision, draft_policy_reason: draftPolicy.reason || null };
        report.ok = true;
      } else {
        // The write path refuses before the first write, not after it: everything up to
        // this point is read-only (navigation, contract reads, read-only resume probes),
        // so a refusal here proves no draft was staged, previewed, published or discarded.
        if (draftPolicy.decision === 'fail_closed') {
          // Make the refusal attributable instead of vacuous: ask the product read-only
          // which draft it would resume for this designer target. A blank answer alongside
          // a non-empty inventory means the block is stale, not protective.
          const probeParams = { resume_only: true, target_model: entry.model, target_action_id: entry.action_id };
          const refusalProbe = resolveChangeSetOpenResponse({
            body: await cs('open', probeParams),
            intent: 'open:refusal_probe',
          });
          report.designer_draft_refusal = { reason: draftPolicy.reason, inventory_ids: draftPolicy.inventoryIds,
            blocking: draftPolicy.blocking, would_resume: refusalProbe.draft?.id || null, probe_shape: refusalProbe.shape };
          throw new Error(draftPolicy.reason);
        }
        const { runDesignerJourney } = await import('./formal_form_designer_journey.mjs');
        await runDesignerJourney({ page, entry, baseline, outsideBaseline: otherBaseline, outside, contract, effective, out, report, pending, cs, drafts, draftPolicy, documentTopic, invoiceTopic, payrollTopic, usagePerformanceTopic, isolationEntry: usagePerformanceIsolation });
      }
    } else {
    const nodes = [...walk(tree(baseline))];
    const field = nodes.find((node) => node.type === 'field' && node.name === 'keeper_id');
    const hidden = nodes.find((node) => node.type === 'field' && node.name === 'line_note_summary');
    const parent = nodes.find((node) => node.children?.includes(field));
    assert(field?.nativeLocator && hidden?.nativeLocator && parent?.nativeLocator, 'missing authoritative node bindings');
    const key = `view_orchestration:formal_material_loop:${Date.now()}`;
    async function stage(patches, targetKey = key) {
      // The loop asks for a fresh draft explicitly and requires the handler to report
      // that it created one. Resuming a same-named draft and discarding it (the previous
      // behaviour) destroyed a draft this run had no creation credential for.
      const opened = (await cs('open', { name: '正式表单受管配置验证', fresh: true })).data;
      assert.equal(opened.name, '正式表单受管配置验证');
      assert.equal(opened.created, true, 'material loop draft was not created by this run');
      assert.equal(opened.items.length, 0, 'a freshly created draft already carried items');
      drafts.set(opened.token, opened.id);
      await cs('stage', { change_set_token: opened.token, config_type: 'form', target_key: targetKey,
        model: entry.model, view_type: 'form', action_id: entry.action_id, view_id: entry.view_id,
        draft_payload: { view_orchestration: { views: { form: { node_patches: patches } } } } });
      return opened;
    }
    async function publish(label) {
      const opened = await stage([
        binding(field, { set: { label } }), binding(hidden, { set: { visible: false } }),
        binding(parent, { order: [...parent.children].reverse().map((node) => node.nativeLocator),
          group: { key: 'custody', label: '保管配置', members: [field.nativeLocator] } }),
      ]);
      const preview = (await cs('preview', { change_set_token: opened.token })).data;
      const previewParams = { preview_token: preview.preview.token, preview_role_key: scope.role_key };
      const previewContract = await contract(entry, previewParams);
      report.stages[`preview-${label}`] = await observe(`preview-${label}`, label, previewParams);
      const published = (await cs('publish', { change_set_token: opened.token, request_id: `publish-${opened.token}` })).data;
      pending.push(opened.token);
      drafts.delete(opened.token);
      assert.equal(published.publish_result.published_content_verified, true);
      assert.equal(published.publish_result.runtime_verified, true);
      assert.equal(published.publish_result.page_behavior_verification, 'not_run');
      const final = await contract();
      assert.deepEqual(effective(final), effective(previewContract), 'preview and published effective contract differ');
      assert.deepEqual(effective(await contract(outside)), effective(otherBaseline), 'configuration leaked to action 547');
      const observation = await observe(`published-${label}`, label);
      report.stages[label] = { publication: 'passed', final_contract: 'passed', browser: 'passed', ...observation };
      return { opened, final };
    }
    if (navigationOnly) {
      const opened = await stage([
        binding(field, { set: { label: '保管员 A' } }), binding(hidden, { set: { visible: false } }),
        binding(parent, { order: [...parent.children].reverse().map((node) => node.nativeLocator),
          group: { key: 'custody', label: '保管配置', members: [field.nativeLocator] } }),
      ]);
      const preview = (await cs('preview', { change_set_token: opened.token })).data;
      const previewParams = { preview_token: preview.preview.token, preview_role_key: scope.role_key };
      report.stages.preview = await observe('navigation-preview', '保管员 A', previewParams);
      const nav = page.locator('[data-form-section-navigation]');
      await nav.getByRole('button', { name: '保管配置', exact: true }).click();
      await page.getByText('保管员 A', { exact: true }).first().scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(out, 'configured-field.png'), fullPage: true });
      await page.locator('[data-section-tab="说明与附件"]').last().click();
      assert.equal(await page.getByText('备注', { exact: true }).count(), 0, 'hidden optional field remained visible');
      await page.locator('[data-section-tab="来源追溯"]').last().click();
      await nav.getByRole('button', { name: '入库明细', exact: true }).click();
      await page.locator('[data-section-tab="入库明细"].native-tab--active').waitFor({ state: 'visible' });
      await page.getByText('添加入库明细', { exact: true }).waitFor({ state: 'visible' });
      await page.screenshot({ path: path.join(out, 'configured-detail-navigation.png'), fullPage: true });
      report.stages.navigation = { status: 'passed', labels: await nav.locator('[data-section-link]').allTextContents(),
        scroll: await page.evaluate(() => [...document.querySelectorAll('*')].filter((node) => node.scrollTop > 0)
          .map((node) => ({ tag: node.tagName, class: node.className, scrollTop: node.scrollTop }))) };
      assert.deepEqual(effective(await contract()), effective(baseline), 'preview changed published baseline');
      assert.deepEqual(effective(await contract(outside)), effective(otherBaseline), 'preview changed outside scope');
      report.review = { url: url(previewParams), expires_at: preview.preview.expires_at, account: scope.login,
        state: 'saved preview only; published baseline restored', change_set_id: opened.id };
      drafts.delete(opened.token); // Preserve only this expiring, creator-scoped preview for product review.
      report.restored = true;
      report.ok = true;
    } else {
    const a = await publish('保管员 A');
    const b = await publish('保管员 B');
    await rollback(b.opened.token);
    assert.deepEqual(effective(await contract()), effective(a.final), 'rollback B did not restore A');
    report.stages.rollbackA = await observe('rollback-A', '保管员 A');
    const readonly = nodes.find((node) => node.name === 'amount_total');
    const required = nodes.find((node) => node.name === 'project_id');
    report.rejections = {};
    for (const [name, patch, reason] of [
      ['readonly', binding(readonly, { set: { readonly: false } }), 'CONFIG_BUSINESS_CONSTRAINT_RELAXED'],
      ['required', binding(required, { set: { visible: false } }), 'CONFIG_REQUIRED_FIELD_HIDDEN'],
      ['stale', { ...binding(field, { set: { label: '失效目标' } }), target: '/removed/node' }, 'CONFIG_TARGET_STALE'],
    ]) {
      const opened = await stage([patch]);
      const rejected = await cs('preview', { change_set_token: opened.token }, false);
      assert.equal(rejected.ok, false, `${name} should be rejected`);
      assert(JSON.stringify(rejected).includes(reason), `${name} missing explicit diagnostic`);
      report.rejections[name] = reason;
      await cs('discard', { change_set_token: opened.token });
      drafts.delete(opened.token);
    }
    const conflict = await stage([binding(field, { set: { label: '同级冲突' } })], `${key}:conflict`);
    const rejected = await cs('preview', { change_set_token: conflict.token }, false);
    assert.equal(rejected.ok, false);
    assert(JSON.stringify(rejected).includes('CONFIG_SAME_PRIORITY_CONFLICT'));
    report.rejections.conflict = 'CONFIG_SAME_PRIORITY_CONFLICT';
    await cs('discard', { change_set_token: conflict.token });
    drafts.delete(conflict.token);
    await rollback(a.opened.token);
    assert.deepEqual(effective(await contract()), effective(baseline), 'baseline restoration failed');
    report.stages.restoredDefault = await observe('restored-default');
    report.restored = true;
    report.ok = true;
    }
    }
  } catch (error) {
    report.failure = error.stack || String(error);
    report.diagnostics = diagnostics;
    report.failurePage = await captureFailurePage();
    report.failure_class = classifyFailure(report.failurePage);
    await (report.failurePage?.page_kind === 'main' || !report.failurePage
      ? page
      : pages.find((target) => pageKind(target) === report.failurePage.page_kind) || page
    ).screenshot({ path: path.join(out, 'failure.png'), fullPage: true }).catch(() => {});
  } finally {
    report.recovery = [];
    const cleanup = resolveCleanupRelease({ heldIds: [...drafts.values()], inventoryIds: report.designer_draft_policy?.inventory_ids || [] });
    report.cleanup_guard = { decision: cleanup.decision, reason: cleanup.reason || null, foreign: cleanup.foreign };
    if (cleanup.decision === 'fail_closed') {
      // A foreign draft reached the cleanup set: refuse to discard anything and fail
      // the run, because silently skipping it would hide that a boundary was crossed.
      report.recovery.push({ status: 'cleanup_refused_foreign_draft', ids: cleanup.foreign });
      report.recovery_state = { draft_tokens_held: drafts.size, rollback_tokens_pending: pending.length, released: false };
    } else {
      report.recovery_state = { draft_tokens_held: drafts.size, rollback_tokens_pending: pending.length, released: true };
      for (const token of drafts.keys()) {
        try { await cs('discard', { change_set_token: token }); }
        catch (error) { report.recovery.push({ status: 'draft_discard_failed', error: String(error) }); }
      }
    }
    for (const token of [...pending].reverse()) {
      try { await rollback(token); report.recovery.push({ status: 'restored' }); }
      catch (error) { report.recovery.push({ status: 'failed', error: String(error) }); }
    }
    if (baseline && !report.restored) {
      try { assert.deepEqual(effective(await contract()), effective(baseline)); report.restored = true; }
      catch (error) { report.recovery.push({ status: 'baseline_readback_failed', error: String(error) }); }
    }
    // Positive transport evidence: a run that aborted no request and logged no page error
    // has to say so explicitly. Otherwise "this run had no interruption" could only be
    // inferred from an absent field, which is the same shape as a run whose instrumentation
    // never attached.
    if (!report.diagnostics) report.diagnostics = diagnostics;
    if (process.env.FORM_LOWCODE_READ_FAILURE !== '1') await fs.writeFile(path.join(out, configurationEntryOnly ? (process.env.FORM_LOWCODE_CONFIG_BATCH === '1' ? 'batch-report.json' : process.env.FORM_LOWCODE_CONFIG_SUMMARY === '1' ? 'summary-report.json' : 'entry-report.json') : emptySectionOnly ? 'empty-section-report.json' : representativeOnly ? `representative-report-${scope.topic}.json` : observeOnly ? 'closure-observation.json' : closureOnly ? 'closure-report.json' : replayOnly ? 'replay-report.json' : designerOnly ? 'designer-report.json' : navigationOnly ? 'navigation-report.json' : 'report.json'), JSON.stringify(report, null, 2));
    await browser.close();
  }
  assert(report.cleanup_guard?.decision !== 'fail_closed', report.cleanup_guard?.reason || 'cleanup guard refused');
  assert(report.ok && report.restored, report.failure || 'journey/restoration incomplete');
  console.log(configurationEntryOnly ? (process.env.FORM_LOWCODE_CONFIG_BATCH === '1' ? '[formal_form_lowcode_loop] configuration batch complete; inspect separate publication/contract/browser results and baseline restoration' : '[formal_form_lowcode_loop] configuration entry observation complete; inspect report, no publish or business save') : emptySectionOnly ? '[formal_form_lowcode_loop] PASS empty source narrow observation; no publication or business write' : closureOnly ? '[formal_form_lowcode_loop] PASS preview/designer closure; no publication' : replayOnly ? '[formal_form_lowcode_loop] PASS read-only replay; no draft opened, staged or changed' : designerOnly ? '[formal_form_lowcode_loop] PASS formal designer journey' : navigationOnly ? '[formal_form_lowcode_loop] PASS configured navigation; published baseline unchanged' : '[formal_form_lowcode_loop] PASS default -> preview -> A -> B -> A -> default');
}

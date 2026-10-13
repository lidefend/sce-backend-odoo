import fs from 'node:fs';
import { isDeepStrictEqual } from 'node:util';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { launchChromium } from './playwright_runtime.mjs';
import { assertContractPrerequisite, observedContractBinding, readContractReceipt } from './lib/acceptance_contract_receipt.mjs';
import { findReleasedNavigationTargetById } from './released_navigation_target.mjs';

function check(value, message, details) {
  if (!value) throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
}
export function executionKeys(units, plan) {
  const ids = (units.units || []).map(unit => unit.id);
  check(ids.length > 0 && new Set(ids).size === ids.length, 'invalid declared unit keys');
  check(ids.every(key => key === 'entry_click' || /^project_create:(standard|quick):(1440|390)$/.test(key) || /^(list|create|edit|readonly):(1440|390)$/.test(key) || /^(edit|readonly):auth_occurrence:(1440|390)$/.test(key) || /^edit:(span|guidance):(1440|390)$/.test(key)), 'unsupported executor unit');
  check(plan.schema === 'evidence_scope.plan.v1' && plan.check === units.check
    && isDeepStrictEqual(plan.identity, units.identity), 'plan identity mismatch');
  check(Array.isArray(plan.affected) && Array.isArray(plan.reusable) && Array.isArray(plan.blocked)
    && !plan.blocked.length, 'invalid or blocked evidence plan');
  const partition = [...plan.affected, ...plan.reusable];
  check(partition.length === ids.length && new Set(partition).size === ids.length
    && partition.every(key => ids.includes(key)), 'unknown, duplicate or missing planned unit');
  return new Set(plan.affected);
}
export function approvedTarget({ receipt, target, sourceSha, database }) {
  const approved = assertContractPrerequisite({ receipt, expectedSha: sourceSha, database,
    login: target.user.login, roleCode: target.acceptance_authority.role_code, companyName: target.user.company_name });
  check(receipt.request.database === database && approved.identity.uid === target.user.id, 'approved actor/database mismatch');
  check(approved.approved.model === target.contract_resolution.targets.payment_request.model
    && approved.approved.record_id === target.record.id && approved.approved.action_id === target.action.id
    && approved.approved.menu_id === target.menu.id, 'approved target mismatch');
  return approved;
}
export function formDeclaration(contract, expected) {
  const profile = contract?.statusContract?.globalStatus?.effectiveRenderProfile;
  const structure = contract?.formStructureContract;
  check(contract?.pageInfo?.model === expected.model && contract?.pageInfo?.viewType === 'form', 'form identity mismatch');
  check(['create', 'edit', 'readonly'].includes(profile), 'effective profile missing');
  check(expected.record === 'new' ? profile === 'create' : Number(contract?.dataContract?.mainData?.id) === expected.record,
    'form record mismatch');
  check(expected.routeMode !== 'readonly' || profile === 'readonly', 'readonly route granted edit profile');
  check(['task', 'workspace'].includes(structure?.presentationMode), 'form presentation declaration missing');
  check(structure?.structureAuthority === 'container_tree', 'this native observation requires declared container_tree');
  return { profile, bodyStructureAuthority: 'containerTree',
    pattern: `[data-product-page-pattern="${structure.presentationMode}-form"][data-render-profile="${profile}"]`,
    seal: contract?.meta?.lifecycle?.integrity?.contractSha256 };
}

export function consumptionCases(contract) {
  const statuses = new Map((contract.statusContract?.widgetStatus || []).map(item => [item.widgetId, item]));
  const containers = new Map((contract.statusContract?.containerStatus || []).map(item => [item.containerId, item]));
  const fields = [];
  function visit(nodes, visible = true) {
    for (const node of nodes || []) {
      const owner = containers.get(node.containerId);
      check(typeof owner?.visible === 'boolean', 'container visibility declaration missing');
      const ancestorsVisible = visible && owner.visible;
      for (const widget of node.widgetList || []) {
        if (!widget.fieldCode) continue;
        const status = statuses.get(widget.widgetId);
        check(typeof status?.visible === 'boolean' && typeof status.readonly === 'boolean', 'widget status declaration missing');
        fields.push({ id: widget.widgetId, field: widget.fieldCode, locator: widget.nativeLocator,
          position: widget.sourcePosition, span: widget.span, auth: status.auth,
          readonly: status.readonly || status.disabled === true,
          visible: ancestorsVisible && status.visible, ancestorsVisible, ownVisible: status.visible,
          type: widget.componentConfig?.fieldType, nativeWidget: widget.componentConfig?.nativeWidget });
      }
      visit(node.children, ancestorsVisible);
    }
  }
  visit(contract.layoutContract?.containerTree);
  const duplicates = new Set(fields.filter(item => fields.filter(other => other.field === item.field).length > 1).map(item => item.field));
  const hidden = fields.filter(item => !item.visible && duplicates.has(item.field) && item.nativeWidget !== 'statusbar');
  const scalar = fields.filter(item => item.visible && ['char', 'text', 'monetary', 'float', 'integer'].includes(item.type));
  const selected = [...scalar.filter(item => item.auth === 'write' && !item.readonly).slice(0, 2),
    ...scalar.filter(item => item.auth === 'read' || item.readonly).slice(0, 2)];
  check(selected.length > 0 && hidden.length > 0, 'sample lacks discriminating visible/hidden occurrence candidates');
  return { selected, hidden, statusbar: fields.find(item => item.nativeWidget === 'statusbar' && item.visible) || null };
}

export function guidanceDeclaration(contract) {
  const retired = new Set(['legal_next_action_display', 'payment_blocking_reason_display']);
  const visit = value => {
    if (!value || typeof value !== 'object') return;
    check(!retired.has(value.name) && !retired.has(value.fieldName), 'retired guidance declared in form body');
    for (const child of Object.values(value)) if (child && typeof child === 'object') visit(child);
  };
  visit(contract.layoutContract?.containerTree);
  const actions = (contract.actionContract?.actionRuleList || []).filter(action =>
    action.button?.type === 'object' && action.button?.name === 'action_submit'
    && action.allowed === true && action.enabled === true && action.disabled !== true
    && action.presentation?.requires_confirmation === true);
  check(actions.length === 1, 'one enabled declared submit confirmation required');
  const action = actions[0], message = action.presentation.warning_message;
  check(typeof message === 'string' && message.trim(), 'declared confirmation message missing');
  check(typeof action.backendIdentity === 'string' && action.backendIdentity, 'confirmation action identity missing');
  return { backendIdentity: action.backendIdentity, message, actionId: action.actionId };
}

export function projectCreateDeclaration(contract, entry, params) {
  const declaration = formDeclaration(contract, {model:entry.model,record:'new',routeMode:'create'});
  check(Number(params.action_id)===entry.action_id && Number(params.menu_id)===entry.menu_id, 'project create request entry mismatch');
  check(contract.formStructureContract.sourceAuthority?.governance_source?.resolvedViewId===entry.view_id, 'project action view mismatch');
  const statuses=new Map((contract.statusContract?.widgetStatus||[]).map(item=>[item.widgetId,item]));
  const containers=new Map((contract.statusContract?.containerStatus||[]).map(item=>[item.containerId,item]));
  const visible=[];
  const visit=(nodes,parentVisible=true)=>{for(const node of nodes||[]){
    const state=containers.get(node.containerId); check(typeof state?.visible==='boolean','project container authority missing');
    const shown=parentVisible&&state.visible;
    for(const widget of node.widgetList||[]){
      check(!['intake_next_action_display','intake_blocking_reason_display'].includes(widget.fieldCode),'retired project guidance declared');
      const status=statuses.get(widget.widgetId);
      if(shown&&status?.visible===true)visible.push({...widget,status});
    }
    visit(node.children,shown);
  }};
  visit(contract.layoutContract.containerTree);
  const required=visible.filter(widget=>['name','initiation_date','manager_id'].includes(widget.fieldCode));
  check(required.length===3 && new Set(required.map(widget=>widget.fieldCode)).size===3 && required.every(widget=>widget.status.required===true),'project required occurrence declaration missing');
  return {...declaration,required:required.map(widget=>({field:widget.fieldCode,widgetId:widget.widgetId}))};
}

async function main() {
  const scope = process.env.LOCAL_DEV_FLOORPLAN_SCOPE || 'base';
  check(['base', 'consumption', 'project_create'].includes(scope), 'unsupported floorplan scope');
  const target = JSON.parse(process.env.LOCAL_DEV_PAYMENT_FLOORPLAN_JSON || '{}');
  const base = process.env.FRONTEND_URL || '', database = process.env.DB_NAME || '';
  const password = process.env.E2E_PASSWORD || '', sourceSha = process.env.SOURCE_SHA || '';
  const output = path.resolve('artifacts/playwright/local-dev-payment-request-floorplan');
  check(base && database && password && target.user?.login, 'local.dev identity incomplete');
  const approved = {};
  for (const profile of scope === 'project_create' ? [] : ['edit', 'readonly']) {
    const { receipt } = readContractReceipt(path.join(output, `approval-${profile}.json`));
    approved[profile] = approvedTarget({ receipt, target, sourceSha, database });
    check(receipt.request.params.render_profile === profile, 'approval profile mismatch');
  }
  const units = JSON.parse(fs.readFileSync(path.join(output, 'units.json'), 'utf8'));
  const plan = JSON.parse(fs.readFileSync(path.join(output, 'plan.json'), 'utf8'));
  const affected = executionKeys(units, plan);
  if (!affected.size) {
    fs.writeFileSync(path.join(output, 'summary.json'), JSON.stringify({scope,status:'reused',pass:null,executed_keys:[],not_run:['browser:all_keys_reusable']}));
    return;
  }
  const wants = key => affected.has(key);
  // This check deliberately occurs before browser creation or login.
  const { build } = await import('../../frontend/apps/web/node_modules/esbuild/lib/main.js');
  const bundled = await build({ stdin: { contents: 'export { useActionViewNavigationRuntime } from "./frontend/apps/web/src/app/action_runtime/useActionViewNavigationRuntime"; export { decodeContractV2Snapshot } from "./frontend/apps/web/src/app/contracts/v2/schema";', resolveDir: process.cwd() },
    bundle: true, write: false, platform: 'node', format: 'esm', define: { 'import.meta.env': '{}' } });
  const { useActionViewNavigationRuntime, decodeContractV2Snapshot } = await import(`data:text/javascript;base64,${Buffer.from(bundled.outputFiles[0].text).toString('base64')}`);
  const browser = await launchChromium({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const page = await context.newPage();
  const exchanges = [], errors = [], mutations = [];
  const report = { schemaVersion: 'payment_request_floorplan_readonly.v1', sourceSha, target, database, frontendUrl: base,
    scope, observationRunId: `${Date.now()}-${process.pid}`, pass: false, rows: [], executed_keys: [], unit_results: {}, affected_keys: [...affected],
    unit_fingerprints: Object.fromEntries(JSON.parse(fs.readFileSync(path.join(output, 'units.json'), 'utf8')).units.map(unit => [unit.id, unit.fingerprint])), not_run: ['save', 'submit', 'approval', 'upload', 'other_roles', 'search_empty_state', 'audit_disclosure', 'field_occurrence_exhaustiveness',
      'x2many_nondefault_page_size', 'x2many_cross_page_count', 'all_business_value_formats'],
    approval_scope: { edit: 'exact_record_seal', readonly: 'exact_record_seal', list: 'live_contract_only', create: 'live_contract_only' } };
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(message.text()); });
  await page.route('**/api/v1/intent*', async route => {
    const body = route.request().postDataJSON() || {}, params = body.params || {};
    const forbidden = /(^|\.)(create|write|unlink|execute_button|upload)(\.|$)/.test(body.intent || '')
      || (body.intent === 'api.data' && !['list', 'read', 'search', 'search_read', 'name_search', 'fields_get', 'default_get'].includes(params.op))
      || /^(create|write|unlink|web_save|action_)/.test(params.method || '');
    if (forbidden) { mutations.push({ intent: body.intent, op: params.op, method: params.method }); await route.abort(); }
    else await route.continue();
  });
  page.on('response', async response => {
    if (!response.url().includes('/api/v1/intent')) return;
    const request = response.request().postDataJSON() || {};
    if (!['ui.contract.v2', 'system.init', 'api.data'].includes(request.intent)) return;
    try { exchanges.push({ intent: request.intent, params: request.params || {}, context: request.context || {}, response: await response.json() }); } catch {}
  });
  const wait = async (predicate, message) => {
    const until = Date.now() + 45000;
    while (Date.now() < until) { const found = exchanges.find(predicate); if (found) return found; await new Promise(resolve => setTimeout(resolve, 50)); }
    throw new Error(message);
  };
  const snapshot = async (surface, width, details) => {
    if (!wants(`${surface}:${width}`)) return;
    await page.setViewportSize({ width, height: width === 390 ? 844 : 960 });
    await page.waitForFunction(w => document.documentElement.clientWidth === w, width);
    const geometry = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
    check(geometry.scrollWidth <= geometry.width, `${surface} overflow`, geometry);
    const key = `${surface}:${width}`;
    await page.screenshot({ path: path.join(output, `${surface}-${width}.png`), fullPage: true });
    report.rows.push({ key, ...details, geometry }); report.executed_keys.push(key); report.unit_results[key] = 'passed';
  };
  const observeForm = async (surface, routeMode, expectedRecord, start) => {
    const exchange = await wait(item => exchanges.indexOf(item) >= start && item.intent === 'ui.contract.v2'
      && item.response?.ok === true && item.response.data?.pageInfo?.viewType === 'form'
      && item.response.data.pageInfo.model === approved.edit.approved.model
      && (expectedRecord === 'new' ? item.response.data.statusContract?.globalStatus?.effectiveRenderProfile === 'create'
        : Number(item.response.data.dataContract?.mainData?.id) === expectedRecord), 'matching form contract missing');
    const contract = exchange.response.data;
    const declaration = formDeclaration(contract, { model: approved.edit.approved.model, record: expectedRecord, routeMode });
    let binding = null;
    if (expectedRecord !== 'new') {
      const gate = approved[routeMode];
      binding = observedContractBinding({ envelope: exchange.response, requestParams: exchange.params,
        receiptRequest: gate.approvedRequest.params, approved: gate });
      check(binding.ok, 'approved form contract diverged', binding);
    }
    const root = page.locator('[data-product-page-mode="form"][data-form-model]').first();
    await root.locator(declaration.pattern).waitFor({ timeout: 45000 });
    check(await root.getAttribute('data-form-model') === approved.edit.approved.model, 'DOM model mismatch');
    const host = root.locator('[data-contract-form-driver]').first();
    check(await host.getAttribute('data-source-contract-sha') === declaration.seal, 'renderer not bound to observed seal');
    await host.locator('.sc-native-contract-tree').waitFor({ timeout: 45000 });
    check(await host.locator('[data-object-task-page]').count() === 0, 'containerTree used legacy task floorplan');
    check(await host.locator('[data-field-name]').count() > 0, 'native field consumption missing');
    const editable = host.locator('[data-field-name] input:visible:not([readonly]):not([disabled]), [data-field-name] textarea:visible:not([readonly]):not([disabled]), [data-field-name] select:visible:not([disabled])');
    if (declaration.profile === 'readonly') check(await editable.count() === 0, 'readonly fields became editable');
    if (declaration.profile === 'create') check(await editable.count() > 0, 'create form has no editable business fields');
    check(await root.locator('[data-contract-form-driver-error]').count() === 0, 'renderer error');
    if (scope === 'base') {
      for (const width of [1440, 390]) await snapshot(surface, width, { declaration, binding, contract_response_index: exchanges.indexOf(exchange) });
    } else {
      const candidates = consumptionCases(contract);
      for (const width of [1440, 390]) {
        const authKey = `${surface}:auth_occurrence:${width}`, spanKey = `${surface}:span:${width}`, guidanceKey = `${surface}:guidance:${width}`;
        if (!wants(authKey) && !wants(spanKey) && !wants(guidanceKey)) continue;
        await page.setViewportSize({ width, height: width === 390 ? 844 : 960 });
        if (wants(guidanceKey)) {
          const guidance = guidanceDeclaration(contract);
          check(await host.locator('[data-field-name="legal_next_action_display"]:visible, [data-field-name="payment_blocking_reason_display"]:visible').count() === 0, 'retired task guidance rendered');
          check(!(await host.innerText()).includes(guidance.message), 'action guidance rendered as initial body text');
          const button = root.locator(`[data-backend-identity=${JSON.stringify(guidance.backendIdentity)}]:visible`);
          check(await button.count() === 1, 'declared confirmation action not unique');
          check(await button.isEnabled(), 'declared soft action rendered disabled');
          const mutationStart = mutations.length;
          await button.click();
          const dialog = page.locator('[data-dialog-purpose="intent-confirmation"][data-state="open"]');
          await dialog.waitFor();
          check((await dialog.locator('#intent-confirmation-message').innerText()).includes(guidance.message), 'official confirmation omitted native warning');
          const confirmationScreenshot = `${report.observationRunId}-${guidanceKey.replaceAll(':','-')}-confirmation.png`;
          await page.screenshot({ path: path.join(output, confirmationScreenshot), fullPage: true, animations: 'disabled' });
          await dialog.getByRole('button', { name: '取消', exact: true }).click();
          await dialog.waitFor({ state: 'hidden' });
          check(mutations.length === mutationStart, 'cancelled confirmation dispatched business mutation');
          const screenshot = `${report.observationRunId}-${guidanceKey.replaceAll(':','-')}.png`;
          await page.screenshot({ path: path.join(output, screenshot), fullPage: true });
          report.rows.push({ key: guidanceKey, guidance, binding, contract_response_index: exchanges.indexOf(exchange), screenshot, confirmationScreenshot, cancelled: true, mutationCount: mutations.length - mutationStart });
          report.executed_keys.push(guidanceKey); report.unit_results[guidanceKey] = 'passed';
        }
        const observations = [];
        for (const field of wants(authKey) ? candidates.hidden : []) {
          const nodes = root.locator(`[data-field-key="${field.id}"]:visible`);
          check(await nodes.count() === 0, 'hidden occurrence leaked through ancestor/widget visibility', field);
        }
        for (const field of wants(authKey) || wants(spanKey) ? candidates.selected : []) {
          const node = root.locator(`[data-field-key="${field.id}"]:visible`);
          check(await node.count() === 1, 'declared occurrence missing or duplicated', field);
          check(await node.getAttribute('data-native-locator') === field.locator
            && Number(await node.getAttribute('data-source-position')) === field.position, 'occurrence identity diverged', field);
          const controls = node.locator('input:visible:not([readonly]):not([disabled]), textarea:visible:not([readonly]):not([disabled]), select:visible:not([disabled])');
          const writable = declaration.profile !== 'readonly' && field.auth === 'write' && !field.readonly;
          if (wants(authKey)) check(writable ? await controls.count() > 0 : await controls.count() === 0, 'field authority consumption diverged', field);
          const span = await node.getAttribute('data-field-span');
          const facts = await node.evaluate(element => Boolean(element.closest('[data-detail-facts="official-standard-detail"]')));
          if (wants(spanKey) && span === null) check(declaration.profile === 'readonly' && facts, 'grid field lost declared span', field);
          else if (wants(spanKey)) check(Number(span) === field.span, 'field span differs from occurrence declaration', { field, span });
          observations.push({ ...field, writable, observedSpan: span, spanApplicability: span === null ? 'not_applicable_to_readonly_facts' : 'grid' });
        }
        if (wants(authKey) && candidates.statusbar && (candidates.statusbar.auth === 'read' || candidates.statusbar.readonly)) {
          const bar = root.locator('[data-professional-workflow-component="statusbar"]');
          check(await bar.getAttribute('data-workflow-readonly') === 'true', 'read statusbar advertised as writable');
          const select = bar.locator('[data-semantic-component="ScSelect"]');
          if (await select.count()) {
            check(await select.getAttribute('aria-readonly') === 'true', 'readonly status control missing real readonly semantics');
            await select.click();
            check(await page.locator('[role="option"]:visible').count() === 0, 'readonly status control opened writable options');
          }
        }
        if (wants(authKey)) {
          const trigger = host.locator('[data-field-help-trigger]:visible').first();
          check(await trigger.count() === 1, 'native help sample missing');
          const helpId = await trigger.getAttribute('aria-controls');
          check(Boolean(helpId), 'field help trigger has no declared content identity');
          const help = page.locator(`[id=${JSON.stringify(helpId)}]`);
          check(!await help.isVisible(), 'native field help rendered before interaction');
          await trigger.click();
          await help.waitFor({ state: 'visible' });
          check(Boolean((await help.innerText()).trim()), 'native field help content empty');
          await trigger.click();
          await help.waitFor({ state: 'hidden' });
          observations.push({ nativeHelp: 'click_open_close', helpId, observedSpan: null });
        }
        const key = `${surface}:auth_occurrence:${width}`;
        if (wants(key)) { report.rows.push({ key, candidates, observations, contract_response_index: exchanges.indexOf(exchange), binding });
        report.executed_keys.push(key); report.unit_results[key] = 'passed'; }
        const applicable = observations.some(item => item.observedSpan !== null);
        if (wants(spanKey)) report.rows.push({ key: spanKey, status: applicable ? 'passed' : 'not_applicable_to_sample', observations });
        if (wants(spanKey) && applicable && surface === 'edit') { report.executed_keys.push(spanKey); report.unit_results[spanKey] = 'passed'; }
      }
    }
  };
  try {
    await page.goto(`${base}/login`);
    const inputs = page.locator('input'); await inputs.nth(0).fill(target.user.login); await inputs.nth(1).fill(password);
    if (await inputs.nth(2).count() && !await inputs.nth(2).isDisabled()) await inputs.nth(2).fill(database);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 45000 });
    const init = await wait(item => item.intent === 'system.init' && item.response?.data?.navigation?.nav, 'released navigation missing');
    check(init.response.data.user?.id === target.user.id && init.response.data.user?.company_id === target.user.company_id, 'bootstrap actor/company mismatch');
    if (scope === 'project_create') {
      report.approval_scope = { project_create: 'live_create_contract_only; no_positive_record_seal' };
      for (const entry of target.project_create_entries || []) {
        const keys = [1440,390].filter(width => wants(`project_create:${entry.kind}:${width}`));
        if (!keys.length) continue;
        const released = findReleasedNavigationTargetById(init.response.data.navigation.nav, entry.action_id, entry.menu_id);
        check(released, 'project create entry absent from released navigation');
        const start = exchanges.length;
        await page.goto(`${base}/a/${entry.action_id}?menu_id=${entry.menu_id}`);
        const exchange = await wait(item => exchanges.indexOf(item) >= start && item.intent === 'ui.contract.v2'
          && item.response?.ok === true && item.response.data?.pageInfo?.model === entry.model
          && item.response.data.statusContract?.globalStatus?.effectiveRenderProfile === 'create', 'project create contract missing');
        const contract = decodeContractV2Snapshot(exchange.response.data);
        check(Number(exchange.params.action_id) === entry.action_id && Number(exchange.params.menu_id) === entry.menu_id, 'project create request entry mismatch');
        const declaration = projectCreateDeclaration(contract, entry, exchange.params);
        const root = page.locator('[data-product-page-mode="form"][data-form-model="project.project"]');
        await root.locator(declaration.pattern).waitFor({timeout:45000});
        const host = root.locator('[data-contract-form-driver]');
        check(await host.getAttribute('data-source-contract-sha') === declaration.seal, 'project driver seal mismatch');
        for (const width of keys) {
          await page.setViewportSize({width,height:width===390?844:960});
          check(await host.locator('[data-field-name="intake_next_action_display"], [data-field-name="intake_blocking_reason_display"]').count()===0,'retired project guidance rendered');
          const required=[];
          for(const field of declaration.required) {
            const node=host.locator(`[data-field-key=${JSON.stringify(field.widgetId)}]:visible`);
            check(await node.count()===1,'project required occurrence missing',field);
            check(await node.locator('[required], [aria-required="true"], .field-state--required').count()>0,'project required semantic missing',field);
            required.push(field);
          }
          const observedOrder=await host.locator('[data-field-key]:visible').evaluateAll((nodes,ids)=>nodes.map(node=>node.getAttribute('data-field-key')).filter(id=>ids.includes(id)),required.map(field=>field.widgetId));
          check(isDeepStrictEqual(observedOrder,required.map(field=>field.widgetId)),'project required field order diverged');
          const key=`project_create:${entry.kind}:${width}`, screenshot=`${report.observationRunId}-${key.replaceAll(':','-')}.png`;
          await page.screenshot({path:path.join(output,screenshot),fullPage:true});
          report.rows.push({key,entry,declaration,required,screenshot,contract_response_index:exchanges.indexOf(exchange)});
          report.executed_keys.push(key);report.unit_results[key]='passed';
        }
      }
    } else {
    const nav = findReleasedNavigationTargetById(init.response.data.navigation.nav, target.action.id, target.menu.id);
    check(nav, 'approved list is not in released navigation');
    const listUrl = `${base}/a/${target.action.id}?menu_id=${target.menu.id}`;
    const start = exchanges.length; await page.goto(listUrl);
    const list = await wait(item => exchanges.indexOf(item) >= start && item.intent === 'ui.contract.v2'
      && item.response?.ok === true && item.response.data?.pageInfo?.model === approved.edit.approved.model
      && ['list', 'tree'].includes(item.response.data.pageInfo.viewType), 'list contract missing');
    const surface = page.locator('[data-product-page-mode="list"]:visible').first(); await surface.waitFor({ timeout: 45000 });
    const rows = await wait(item => exchanges.indexOf(item) >= start && item.intent === 'api.data' && item.params.model === approved.edit.approved.model
      && item.params.op === 'list' && item.response?.ok === true, 'list data missing');
    report.list_data = rows; report.navigation = nav;
    const records = rows.response.data?.records;
    check(Array.isArray(records) && records.length > 0, 'list supplied no record sample');
    const firstRecord = records[0];
    const visibleRecord = surface.locator(`[data-record-key="${firstRecord.id}"]:visible`).first();
    await visibleRecord.waitFor({ timeout: 45000 });
    const primaryLabel = (await visibleRecord.locator('[data-semantic-cell-kind="primary"]').innerText()).trim();
    check(primaryLabel && Object.values(firstRecord).some(value => typeof value === 'string' && value.trim() === primaryLabel),
      'list primary label differs from data response');
    if (scope === 'base') for (const width of [1440, 390]) await snapshot('list', width, { contract_response_index: exchanges.indexOf(list) });
    // Use the production row navigation consumer with the captured list contract.
    let rowTarget;
    const runtime = useActionViewNavigationRuntime({ routeQueryMap: { value: { view_mode: 'list' } }, showHud: { value: false },
      menuId: { value: target.menu.id }, actionId: { value: target.action.id },
      actionContract: { value: { snapshot: list.response.data, widgetsByFieldCode: new Map() } },
      canEditRecord: { value: list.response.data.statusContract?.globalStatus?.modelRights?.write === true },
      resolvedModelRef: { value: approved.edit.approved.model }, modelRef: { value: approved.edit.approved.model },
      routerPush: destination => { rowTarget = destination; } });
    runtime.handleRowClick({ id: target.record.id, model: approved.edit.approved.model });
    check(rowTarget, 'list declares no record navigation'); report.declared_row_target = rowTarget;
    await page.setViewportSize({ width: 1440, height: 960 });
    if (scope === 'consumption' && wants('entry_click')) {
      const search = surface.locator('[data-list-query-action-bar] .collection-search-control input[type="search"]:visible, [data-list-query-action-bar] form.product-list-header__search input[type="search"]:visible');
      const submit = surface.locator('[data-list-query-action-bar] .collection-search-control button.toolbar-search-submit:visible, [data-list-query-action-bar] form.product-list-header__search button[type="submit"]:visible');
      check(typeof target.record.name === 'string' && target.record.name.trim(), 'resolved record has no search label');
      const index = exchanges.length;
      await search.fill(target.record.name); await submit.click();
      await wait(item => exchanges.indexOf(item) >= index && item.intent === 'api.data' && item.params.op === 'list'
        && item.params.model === approved.edit.approved.model && item.response?.data?.records?.some(record => record.id === target.record.id), 'declared search did not return approved record');
    }
    const actualRow = surface.locator(`[data-record-key="${target.record.id}"]:visible`).first();
    const canClickRow = await actualRow.isVisible().catch(() => false);
    if (scope === 'consumption' && wants('entry_click')) check(canClickRow, 'approved record is not visible after declared search');
    if (!canClickRow) report.not_run.push('row_click:approved_record_not_on_current_page');
    for (const mode of ['edit', 'readonly']) {
      if (![...affected].some(key => key.startsWith(`${mode}:`)) && !(mode === 'edit' && wants('entry_click'))) continue;
      const gate = approved[mode];
      const index = exchanges.length;
      const pathname = mode === 'edit' ? rowTarget.path : `/r/${gate.approved.model}/${gate.approved.record_id}`;
      const query = new URLSearchParams(mode === 'edit' ? rowTarget.query : { action_id: String(gate.approved.action_id), menu_id: String(gate.approved.menu_id) });
      if (mode === 'edit' && canClickRow && (scope === 'base' || wants('entry_click'))) {
        await actualRow.click();
        await page.waitForURL(url => url.pathname === pathname && url.searchParams.get('action_id') === String(gate.approved.action_id)
          && url.searchParams.get('menu_id') === String(gate.approved.menu_id), { timeout: 45000 });
        report.row_click = 'passed';
        if (scope === 'consumption') { report.rows.push({ key: 'entry_click', declared: rowTarget, observed: page.url() }); report.executed_keys.push('entry_click'); report.unit_results.entry_click = 'passed'; }
      } else await page.goto(`${base}${pathname}?${query}`);
      if ([...affected].some(key => key.startsWith(`${mode}:`))) await observeForm(mode, mode, gate.approved.record_id, index);
    }
    if (scope === 'base' && [...affected].some(key => key.startsWith('create:'))) {
    await page.goto(listUrl); await surface.waitFor({ timeout: 45000 });
    const create = surface.locator('[data-action-key="create"], [data-action-ref="record.create"]');
    const declaredCreate = list.response.data.statusContract?.globalStatus?.modelRights?.create;
    check(typeof declaredCreate === 'boolean', 'list create authority missing');
    if (!declaredCreate) { report.not_run.push('create:declared_denied'); }
    else {
      // Button label comes from the actual element; no translated business state is assumed.
      const createLabel = list.response.data.searchContract?.custom?.ui_labels?.create || list.response.data.searchContract?.ui_labels?.create;
      check(typeof createLabel === 'string' && createLabel.trim(), 'create label declaration missing');
      const button = surface.locator('.product-list-header__leading').getByRole('button', { name: createLabel, exact: true });
      report.create_control_candidates = await create.count();
      check(await button.isEnabled(), 'declared create control not enabled');
      const index = exchanges.length; await button.click();
      await observeForm('create', 'create', 'new', index);
    }
    }
    }
    check(errors.length === 0, 'browser errors', errors); check(mutations.length === 0, 'business writes attempted', mutations);
    check(report.executed_keys.length === affected.size && report.executed_keys.every(key => affected.has(key)), 'affected scope was not fully executed');
    report.pass = true;
  } catch (error) {
    report.failure = error.message; await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
    throw error;
  } finally {
    report.errors = errors; report.mutations = mutations; report.exchanges = exchanges;
    fs.writeFileSync(path.join(output, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
    await context.close(); await browser.close();
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) await main();

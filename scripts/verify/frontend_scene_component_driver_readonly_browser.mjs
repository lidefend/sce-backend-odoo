#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5175';
const ODOO_URL = process.env.ODOO_URL || 'http://127.0.0.1:18082';
const DB_NAME = process.env.DB_NAME || 'sc_frontend_acceptance';
const PASSWORD = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const TARGET = JSON.parse(process.env.SCENE_COMPONENT_DRIVER_TARGETS_JSON || '{}');
const OUTPUT = process.env.SCENE_COMPONENT_DRIVER_ARTIFACTS || 'artifacts/frontend-scene-component-driver';

function check(value, message) {
  if (!value) throw new Error(message);
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function requestIntent(request) {
  if (request.method() !== 'POST') return '';
  try {
    const body = request.postDataJSON();
    return String(body?.intent || body?.params?.intent || '');
  } catch {
    return '';
  }
}

function requestBody(request) {
  try {
    return request.postDataJSON() || {};
  } catch {
    return {};
  }
}

function requestOperation(request) {
  const body = requestBody(request);
  return String(body?.params?.op || body?.params?.payload?.op || '');
}

function isBusinessMutation(request) {
  const intent = requestIntent(request);
  if (['execute_button', 'api.data.create', 'api.data.write', 'api.data.unlink'].includes(intent)) return true;
  if (intent !== 'api.data') return false;
  try {
    const body = request.postDataJSON();
    return ['create', 'write', 'unlink'].includes(String(body?.params?.op || body?.params?.payload?.op || ''));
  } catch {
    return true;
  }
}

const canonicalDomSnapshot = () => ({
  nodes: [...document.querySelectorAll('[data-native-contract-structure] [data-canonical-node-id]')].map((node) => ({
    id: node.getAttribute('data-canonical-node-id') || '',
    kind: node.getAttribute('data-canonical-node-kind') || '',
    zone: node.closest('[data-canonical-zone]')?.getAttribute('data-canonical-zone') || '',
    path: [...node.parentElement?.closest('[data-native-contract-structure]')?.querySelectorAll('[data-canonical-node-id]') || []]
      .filter((candidate) => candidate === node || candidate.contains(node))
      .map((candidate) => candidate.getAttribute('data-canonical-node-id') || '')
      .filter(Boolean),
    nativeClass: node.getAttribute('data-native-class') || '',
    nativeWidget: node.querySelector(':scope > [data-native-widget]')?.getAttribute('data-native-widget') || '',
  })),
  fields: [...document.querySelectorAll('[data-native-contract-structure] [data-field-key]')].map((node) => ({
    widgetId: node.getAttribute('data-field-key') || '',
    fieldCode: node.getAttribute('data-field-name') || '',
    state: node.getAttribute('data-field-state') || '',
    type: node.getAttribute('data-field-type') || '',
    visible: node.getClientRects().length > 0
      && getComputedStyle(node).display !== 'none'
      && getComputedStyle(node).visibility !== 'hidden',
  })),
  actions: [...document.querySelectorAll('[data-contract-form-driver] [data-action-ref]')].map((node) => ({
    actionId: node.getAttribute('data-action-ref') || '',
    backendIdentity: node.getAttribute('data-backend-identity') || '',
    tier: node.getAttribute('data-action-tier') || '',
    enabled: node.getAttribute('data-action-enabled') || '',
    disabled: node.hasAttribute('disabled'),
  })),
  nativeWidgets: [...document.querySelectorAll('[data-native-contract-structure] [data-canonical-node-kind="widget"] > [data-native-widget]')].map((node) => ({
    name: node.getAttribute('data-native-widget') || '',
    state: node.getAttribute('data-native-widget-state') || 'unresolved',
    text: String(node.textContent || '').trim(),
  })),
});

function assertCanonicalSnapshot(snapshot, label) {
  check(snapshot.nodes.length > 0, `${label} canonical nodes missing`);
  check(snapshot.fields.length > 0, `${label} canonical fields missing`);
  check(new Set(snapshot.nodes.map((node) => node.id)).size === snapshot.nodes.length, `${label} canonical nodes duplicated`);
  check(new Set(snapshot.fields.map((field) => field.widgetId)).size === snapshot.fields.length, `${label} widget identities duplicated`);
  check(snapshot.fields.every((field) => field.widgetId && field.fieldCode), `${label} field identity missing`);
  check(snapshot.actions.every((action) => action.actionId && action.backendIdentity), `${label} action reference missing`);
}

async function captureNativeOdooSnapshot(context) {
  const nativePage = await context.newPage();
  const runtimeErrors = { console: [], pageerror: [], failed: [] };
  nativePage.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) runtimeErrors.console.push(message.text());
  });
  nativePage.on('pageerror', (error) => runtimeErrors.pageerror.push(error.message));
  nativePage.on('response', (response) => {
    if (response.status() >= 400 && !/favicon/i.test(response.url())) runtimeErrors.failed.push({ status: response.status(), url: response.url() });
  });
  await nativePage.goto(`${ODOO_URL}/web/login?db=${encodeURIComponent(DB_NAME)}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await nativePage.locator('input[name="login"]').fill(TARGET.login);
  await nativePage.locator('input[name="password"]').fill(PASSWORD);
  await nativePage.locator('button[type="submit"]').click();
  await nativePage.waitForURL((url) => !url.pathname.includes('/web/login'), { timeout: 45000 });
  const nativeRoute = `${ODOO_URL}/web#id=${TARGET.record_id}&model=${encodeURIComponent(TARGET.model)}&view_type=form&action=${TARGET.action_id}&view_id=${TARGET.view_id}&menu_id=${TARGET.menu_id}`;
  await nativePage.goto(nativeRoute, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await nativePage.locator('.o_form_view').waitFor({ state: 'visible', timeout: 60000 });
  await nativePage.waitForTimeout(1200);
  const sourceView = await nativePage.evaluate(async ({ model, viewId, actionId }) => {
    const response = await fetch(`/web/dataset/call_kw/${encodeURIComponent(model)}/get_views`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0', method: 'call', id: Date.now(),
        params: {
          model, method: 'get_views', args: [],
          kwargs: { views: [[viewId, 'form']], options: { action_id: actionId, load_filters: false, toolbar: true } },
        },
      }),
    });
    const payload = await response.json();
    const arch = String(payload?.result?.views?.form?.arch || '');
    if (!response.ok || !arch) return { ok: false, status: response.status, error: payload?.error || null, atoms: [] };
    const root = new DOMParser().parseFromString(arch, 'application/xml').documentElement;
    const atomTags = new Set(['form', 'sheet', 'group', 'div', 'alert', 'header', 'footer', 'notebook', 'page', 'field', 'button', 'widget', 'chatter']);
    const walk = (node, parentPath = []) => {
      if (!(node instanceof Element)) return [];
      const tag = node.tagName.toLowerCase();
      const siblings = [...(node.parentElement?.children || [])].filter((item) => item.tagName === node.tagName);
      const index = Math.max(0, siblings.indexOf(node));
      const segment = `${tag}[${index}]`;
      const path = [...parentPath, segment];
      const attrs = Object.fromEntries([...node.attributes].map((item) => [item.name, item.value]).sort(([a], [b]) => a.localeCompare(b)));
      const own = atomTags.has(tag) ? [{
        tag, path, name: attrs.name || '', label: attrs.string || '', nolabel: attrs.nolabel || '',
        widget: attrs.widget || '', options: attrs.options || '', domain: attrs.domain || '',
        invisible: attrs.invisible || '', readonly: attrs.readonly || '', required: attrs.required || '', modifiers: attrs.modifiers || '',
        className: attrs.class || '', childTags: [...node.children].map((item) => item.tagName.toLowerCase()),
      }] : [];
      return [...own, ...[...node.children].flatMap((child) => walk(child, path))];
    };
    const accessRights = {};
    for (const operation of ['read', 'write', 'create', 'unlink']) {
      const accessResponse = await fetch(`/web/dataset/call_kw/${encodeURIComponent(model)}/check_access_rights`, {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0', method: 'call', id: `${Date.now()}-${operation}`,
          params: { model, method: 'check_access_rights', args: [operation], kwargs: { raise_exception: false } },
        }),
      });
      const accessPayload = await accessResponse.json();
      accessRights[operation] = accessPayload?.result === true;
    }
    return {
      ok: true,
      status: response.status,
      rootAttributes: Object.fromEntries([...root.attributes].map((item) => [item.name, item.value]).sort(([a], [b]) => a.localeCompare(b))),
      accessRights,
      atoms: walk(root),
    };
  }, { model: TARGET.model, viewId: TARGET.view_id, actionId: TARGET.action_id });
  check(sourceView.ok, `native get_views failed: ${JSON.stringify(sourceView)}`);
  const snapshot = await nativePage.evaluate(() => {
    const visible = (node) => node.getClientRects().length > 0 && getComputedStyle(node).visibility !== 'hidden';
    const fields = [...document.querySelectorAll('.o_form_view .o_field_widget[name]')]
      .filter(visible)
      .map((node) => ({
        fieldCode: node.getAttribute('name') || '',
        widget: [...node.classList].find((item) => item.startsWith('o_field_') && item !== 'o_field_widget') || '',
        readonly: node.matches('[readonly], [disabled], .o_readonly_modifier')
          || node.querySelector('input, textarea, select')?.matches('[readonly], [disabled]') === true,
      }));
    const actions = [...document.querySelectorAll('.o_form_view button[name]')]
      .filter(visible)
      .map((node) => ({
        method: node.getAttribute('name') || '',
        buttonType: node.getAttribute('data-type') || node.getAttribute('type') || '',
        label: String(node.textContent || '').trim(),
        disabled: node.matches('[disabled], .disabled') || node.getAttribute('aria-disabled') === 'true',
      }));
    const capabilityCount = (selector) => [...document.querySelectorAll(`.o_form_view ${selector}`)].filter(visible).length;
    return {
      url: location.href,
      title: document.title,
      fields,
      actions,
      capabilities: {
        canEdit: [...document.querySelectorAll('.o_form_button_edit')].some(visible),
        canCreate: [...document.querySelectorAll('.o_form_button_create')].some(visible),
        sheet: capabilityCount('.o_form_sheet'),
        group: capabilityCount('.o_group'),
        div: capabilityCount('div'),
        alert: capabilityCount('.alert'),
        notebook: capabilityCount('.o_notebook'),
        page: capabilityCount('.o_notebook .tab-pane'),
        x2many: capabilityCount('.o_field_x2many, .o_field_one2many, .o_field_many2many'),
        statusbar: capabilityCount('.o_statusbar_status'),
        buttonBox: capabilityCount('.oe_button_box'),
        chatter: capabilityCount('.o-mail-Chatter, .o_ChatterContainer'),
      },
      horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
    };
  });
  snapshot.sourceView = sourceView;
  const rootFlagAllows = (name) => !['0', 'false'].includes(String(sourceView.rootAttributes?.[name] ?? '1').toLowerCase());
  snapshot.pageCapabilities = {
    authority: 'native_form_root_then_model_acl',
    view: {
      edit: rootFlagAllows('edit'),
      create: rootFlagAllows('create'),
      delete: rootFlagAllows('delete'),
      duplicate: rootFlagAllows('duplicate'),
    },
    modelAcl: sourceView.accessRights,
    effective: {
      edit: rootFlagAllows('edit') && sourceView.accessRights.write === true,
      create: rootFlagAllows('create') && sourceView.accessRights.create === true,
      delete: rootFlagAllows('delete') && sourceView.accessRights.unlink === true,
    },
  };
  check(snapshot.capabilities.canEdit === snapshot.pageCapabilities.effective.edit, 'native edit capability disagrees with form-root/ACL authority');
  check(snapshot.capabilities.canCreate === snapshot.pageCapabilities.effective.create, 'native create capability disagrees with form-root/ACL authority');
  snapshot.fieldCount = snapshot.fields.length;
  snapshot.uniqueFieldCount = new Set(snapshot.fields.map((field) => field.fieldCode)).size;
  snapshot.actionCount = snapshot.actions.length;
  snapshot.uniqueActionCount = new Set(snapshot.actions.map((action) => action.method)).size;
  const screenshot = path.join(OUTPUT, 'odoo-native-readonly-project.png');
  await nativePage.screenshot({ path: screenshot, fullPage: true });
  snapshot.screenshot = { path: screenshot, sha256: sha256(screenshot) };
  await nativePage.setViewportSize({ width: 390, height: 844 });
  await nativePage.waitForTimeout(300);
  snapshot.mobile = await nativePage.evaluate(() => ({
    fieldOrder: [...document.querySelectorAll('.o_form_view .o_field_widget[name]')]
      .filter((node) => node.getClientRects().length > 0 && getComputedStyle(node).visibility !== 'hidden')
      .map((node) => node.getAttribute('name') || ''),
    horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
  }));
  const mobileScreenshot = path.join(OUTPUT, 'odoo-native-readonly-project-mobile-390.png');
  await nativePage.screenshot({ path: mobileScreenshot, fullPage: true });
  snapshot.mobile.screenshot = { path: mobileScreenshot, sha256: sha256(mobileScreenshot) };
  snapshot.runtimeErrors = runtimeErrors;
  await nativePage.close();
  return snapshot;
}

async function main() {
  check(PASSWORD, 'SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
  check(TARGET.model && !String(TARGET.model).includes('payment') && TARGET.record_id > 0 && TARGET.action_id > 0 && TARGET.view_id > 0 && TARGET.menu_id > 0, 'invalid non-payment target');
  fs.mkdirSync(OUTPUT, { recursive: true });
  const browser = await launchChromium();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const nativeOdoo = await captureNativeOdooSnapshot(context);
  const page = await context.newPage();
  const evidence = {
    console: [], pageerror: [], failed: [], mutations: [], systemInitPolicy: null,
    contractLayoutShape: null, contractStatusDiagnostics: null,
    contractSha256: '', contractRequests: [], contractResponses: [],
  };
  await page.route('**/*', async (route) => {
    const request = route.request();
    if (isBusinessMutation(request)) {
      const body = requestBody(request);
      evidence.mutations.push({
        intent: requestIntent(request),
        op: requestOperation(request),
        model: String(body?.params?.model || body?.params?.payload?.model || ''),
        valueKeys: Object.keys(body?.params?.vals || body?.params?.payload?.vals || {}).sort(),
        url: request.url(),
        blocked: true,
      });
      await route.abort('blockedbyclient');
      return;
    }
    await route.continue();
  });
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) evidence.console.push(message.text());
  });
  page.on('pageerror', (error) => evidence.pageerror.push(error.message));
  page.on('request', (request) => {
    if (requestIntent(request) === 'ui.contract.v2') {
      const params = requestBody(request)?.params || {};
      evidence.contractRequests.push({
        op: String(params.op || ''),
        model: String(params.model || ''),
        actionId: Number(params.action_id || 0),
        menuId: Number(params.menu_id || 0),
        viewId: Number(params.view_id || 0),
        viewType: String(params.view_type || ''),
        recordId: Number(params.record_id || 0),
        renderProfile: String(params.render_profile || ''),
      });
    }
  });
  page.on('response', async (response) => {
    const failedResponse = response.status() >= 400 && !/favicon/i.test(response.url())
      ? { status: response.status(), url: response.url() }
      : null;
    if (failedResponse) evidence.failed.push(failedResponse);
    const request = response.request();
    const intent = requestIntent(request);
    if (request.method() === 'POST' && /json/i.test(response.headers()['content-type'] || '')) {
      try {
        const body = await response.json();
        if (failedResponse) {
          const error = body?.error || body?.result?.error || {};
          const data = error?.data && typeof error.data === 'object' ? error.data : {};
          Object.assign(failedResponse, {
            code: String(error?.code || body?.code || ''),
            name: String(data?.name || error?.name || ''),
            message: String(data?.message || error?.message || body?.message || '').slice(0, 500),
          });
        }
        const findContract = (value, depth = 0) => {
          if (!value || typeof value !== 'object' || depth > 5) return null;
          if (value.layoutContract?.containerTree) return value;
          for (const nested of Object.values(value)) {
            const found = findContract(nested, depth + 1);
            if (found) return found;
          }
          return null;
        };
        const contract = findContract(body);
        const summarize = (nodes, parentPath = []) => (Array.isArray(nodes) ? nodes : []).map((node, index) => {
          const kind = String(node?.type || node?.containerType || 'container');
          const identity = String(node?.containerId || node?.widgetId || node?.name || `${kind}.${index}`);
          const currentPath = [...parentPath, identity];
          const fieldInfo = node?.fieldInfo || node?.field_info || {};
          const attributes = node?.attributes || {};
          return {
          keys: node && typeof node === 'object' ? Object.keys(node).sort() : [],
          containerId: String(node?.containerId || ''),
          containerType: String(node?.containerType || ''),
          type: String(node?.type || ''),
          name: String(node?.name || ''),
          nolabel: node?.nolabel === true,
          path: currentPath,
          widget: String(node?.widget || fieldInfo?.widget || attributes?.widget || ''),
          options: node?.options ?? fieldInfo?.options ?? attributes?.options ?? null,
          domain: node?.domain ?? fieldInfo?.domain ?? attributes?.domain ?? null,
          modifiers: node?.modifiers ?? fieldInfo?.modifiers ?? attributes?.modifiers ?? null,
          invisible: node?.invisible ?? fieldInfo?.invisible ?? attributes?.invisible ?? null,
          readonly: node?.readonly ?? fieldInfo?.readonly ?? attributes?.readonly ?? null,
          required: node?.required ?? fieldInfo?.required ?? attributes?.required ?? null,
          actionBackendIdentity: String(node?.action?.backendIdentity || ''),
          attributes,
          children: summarize(node?.children, currentPath),
          };
        });
        if (contract) {
          evidence.contractLayoutShape = { intent, nodes: summarize(contract.layoutContract.containerTree) };
          const status = contract.statusContract || {};
          evidence.contractStatusDiagnostics = {
            hiddenContainers: (status.containerStatus || [])
              .filter((row) => row?.visible === false)
              .map((row) => ({ containerId: String(row.containerId || ''), disabled: row.disabled === true, reasonCode: String(row.reasonCode || '') })),
            hiddenWidgets: (status.widgetStatus || [])
              .filter((row) => row?.visible === false)
              .map((row) => ({ widgetId: String(row.widgetId || ''), disabled: row.disabled === true, reasonCode: String(row.reasonCode || '') })),
            mainDataKeys: Object.keys(contract.dataContract?.mainData || {}).sort(),
            actions: (contract.actionContract?.actionRuleList || []).map((row) => ({
              backendIdentity: String(row?.backendIdentity || ''),
              actionId: String(row?.actionId || ''),
              allowed: row?.allowed,
              enabled: row?.enabled,
              disabled: row?.disabled,
              reasonCode: String(row?.reasonCode || row?.reason_code || ''),
              permissionConstraints: row?.permissionConstraints || null,
              sourceChannels: (row?.sourceTrace || []).map((trace) => String(trace?.sourceChannel || '')).filter(Boolean),
              sourceTrace: row?.sourceTrace || [],
              invisible: row?.visible?.attrs?.invisible ?? row?.invisible ?? null,
            })),
            buttonStatus: (status.buttonStatus || []).map((row) => ({
              backendIdentity: String(row?.backendIdentity || ''),
              btnId: String(row?.btnId || ''),
              visible: row?.visible !== false,
              disabled: row?.disabled === true,
              reasonCode: String(row?.reasonCode || ''),
            })),
          };
          evidence.contractSha256 = String(contract?.meta?.lifecycle?.integrity?.contractSha256 || '');
          evidence.contractResponses.push({ intent, sha256: evidence.contractSha256 });
        }
      } catch { /* shape evidence remains unavailable */ }
    }
    if (intent !== 'system.init') return;
    try {
      const body = await response.json();
      const data = body?.data || body?.result?.data || body?.result || {};
      evidence.systemInitPolicy = data?.feature_flags?.scene_component_drivers_v1 || null;
    } catch { /* evidence remains fail-closed below */ }
  });
  try {
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.locator('#login-username, input[autocomplete="username"]').first().fill(TARGET.login);
    await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
    const database = page.locator('input').nth(2);
    if (await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
    await page.locator('.layout-shell').waitFor({ timeout: 45000 });

    const route = `/r/${encodeURIComponent(TARGET.model)}/${TARGET.record_id}?action_id=${TARGET.action_id}&view_id=${TARGET.view_id}&menu_id=${TARGET.menu_id}`;
    await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const anyHost = page.locator('[data-contract-form-driver]').first();
    try {
      await anyHost.waitFor({ state: 'visible', timeout: 8000 });
    } catch (error) {
      const failureScreenshot = path.join(OUTPUT, 'failure-before-driver-host.png');
      await page.screenshot({ path: failureScreenshot, fullPage: true });
      const diagnostic = await page.evaluate(() => ({
        url: location.href,
        title: document.title,
        text: String(document.body?.innerText || '').slice(0, 1200),
        pageMode: document.querySelector('[data-product-page-mode]')?.getAttribute('data-product-page-mode') || '',
        contractError: document.querySelector('[data-contract-form-driver-error]')?.textContent || '',
      }));
      const failureReport = path.join(OUTPUT, 'failure-before-driver-host.json');
      const runtimeEvidence = {
        console: evidence.console,
        pageerror: evidence.pageerror,
        failed: evidence.failed,
        mutations: evidence.mutations,
        contractRequests: evidence.contractRequests,
      };
      fs.writeFileSync(failureReport, `${JSON.stringify({ ...diagnostic, systemInitPolicy: evidence.systemInitPolicy, contractLayoutShape: evidence.contractLayoutShape, runtimeEvidence, screenshot: failureScreenshot }, null, 2)}\n`);
      throw new Error(`ContractForm driver host missing: ${JSON.stringify({ ...diagnostic, systemInitPolicy: evidence.systemInitPolicy, contractLayoutShape: evidence.contractLayoutShape, runtimeEvidence, screenshot: failureScreenshot, report: failureReport })}`, { cause: error });
    }
    const hostDiagnostic = {
      activeKit: await anyHost.getAttribute('data-contract-form-driver'),
      source: await anyHost.getAttribute('data-contract-form-driver-source'),
      reason: await anyHost.getAttribute('data-contract-form-driver-reason'),
      systemInitPolicy: evidence.systemInitPolicy,
      route,
    };
    check(hostDiagnostic.activeKit === 'tdesign-modern', `TDesign policy was not selected: ${JSON.stringify(hostDiagnostic)}`);
    const host = page.locator('[data-contract-form-driver="tdesign-modern"]');
    await page.locator('[data-scene-ui-kit="tdesign-modern"]').waitFor({ state: 'visible', timeout: 45000 });
    await page.locator('[data-control-driver="tdesign-modern"] [data-scene-driver-control]').first().waitFor({ state: 'visible', timeout: 45000 });
    await page.waitForTimeout(500);

    const result = await page.evaluate(() => {
      const host = document.querySelector('[data-contract-form-driver="tdesign-modern"]');
      const driverFields = [...document.querySelectorAll('[data-control-driver="tdesign-modern"]')];
      const editableDriverControls = driverFields.filter((node) => {
        const control = node.querySelector('input, textarea, select, [contenteditable="true"]');
        return control && !control.hasAttribute('readonly') && !control.hasAttribute('disabled');
      });
      return {
        sourceContractSha256: host?.getAttribute('data-source-contract-sha') || '',
        renderModelFields: Number(host?.getAttribute('data-render-model-fields') || 0),
        renderModelActions: Number(host?.getAttribute('data-render-model-actions') || 0),
        driverFieldCount: driverFields.length,
        editableDriverControlCount: editableDriverControls.length,
        horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
        fallback: document.querySelector('[data-scene-driver-fallback="true"]') !== null,
        capabilities: {
          alert: document.querySelectorAll('[data-canonical-node-kind="alert"]').length,
          notebook: document.querySelectorAll('[data-canonical-node-kind="notebook"]').length,
          page: document.querySelectorAll('[data-canonical-node-kind="page"]').length,
          x2many: document.querySelectorAll('[data-field-type="one2many"], [data-field-type="many2many"]').length,
          statusbar: document.querySelectorAll('.native-statusbar, [data-canonical-node-kind="statusbar"]').length,
          buttonBox: document.querySelectorAll('[data-canonical-node-kind="button_box"]').length,
          chatter: document.querySelectorAll('[data-canonical-node-kind="chatter"], [data-canonical-node-kind="activity"]').length,
        },
      };
    });
    result.canonical = await page.evaluate(canonicalDomSnapshot);
    result.fieldCount = result.canonical.fields.length;
    result.uniqueFieldCount = new Set(result.canonical.fields.map((field) => field.widgetId)).size;
    const readonlyPrecheckScreenshot = path.join(OUTPUT, 'readonly-precheck.png');
    await page.screenshot({ path: readonlyPrecheckScreenshot, fullPage: true });
    fs.writeFileSync(path.join(OUTPUT, 'readonly-precheck.json'), `${JSON.stringify({
      result,
      contractLayoutShape: evidence.contractLayoutShape,
      screenshot: { path: readonlyPrecheckScreenshot, sha256: sha256(readonlyPrecheckScreenshot) },
    }, null, 2)}\n`);
    check(evidence.systemInitPolicy?.system_default_kit === 'tdesign-modern', 'system.init entitlement default was not authoritative');
    check(evidence.systemInitPolicy?.allow_user_override === true, 'system.init entitlement did not allow governed driver switching');
    check(
      JSON.stringify(evidence.systemInitPolicy?.form_modes || []) === JSON.stringify(['create', 'edit', 'readonly']),
      'system.init entitlement did not preserve explicit form modes',
    );
    check(result.sourceContractSha256, 'normalized source contract identity missing');
    check(evidence.contractSha256 === result.sourceContractSha256, 'network and canvas contract identities differ');
    check(result.fieldCount > 0 && result.fieldCount === result.uniqueFieldCount, 'readonly fields are missing or duplicated');
    check(result.renderModelFields === result.uniqueFieldCount, 'render model and DOM field sets differ');
    check(result.driverFieldCount > 0, 'TDesign did not render any supported readonly field');
    check(result.editableDriverControlCount === 0, 'readonly driver exposed an editable control');
    check(result.horizontalOverflow === 0, 'readonly driver caused horizontal overflow');
    check(result.fallback === false, 'TDesign load unexpectedly fell back to Native');
    for (const capability of ['alert', 'notebook', 'page', 'x2many', 'statusbar', 'buttonBox', 'chatter']) {
      check(
        Number(result.capabilities[capability] || 0) === Number(nativeOdoo.capabilities[capability] || 0),
        `native/custom ${capability} capability count differs: ${JSON.stringify({ native: nativeOdoo.capabilities[capability], custom: result.capabilities[capability] })}`,
      );
    }
    assertCanonicalSnapshot(result.canonical, 'readonly TDesign');
    const nativeFieldSet = [...new Set(nativeOdoo.fields.map((field) => field.fieldCode))].sort();
    const customFieldSet = [...new Set(result.canonical.fields.filter((field) => field.visible).map((field) => field.fieldCode))].sort();
    const nativeActionSet = [...new Set(nativeOdoo.actions.map((action) => (
      /^\d+$/.test(String(action.method || ''))
        ? `window_action:${action.method}`
        : `button:object:${action.method}`
    )))].sort();
    const customActionSet = [...new Set(result.canonical.actions
      .map((action) => String(action.backendIdentity || ''))
      .filter(Boolean))].sort();
    const flattenContractNodes = (nodes) => (Array.isArray(nodes) ? nodes : []).flatMap((node) => [
      node,
      ...flattenContractNodes(node.children),
    ]);
    const contractNodes = flattenContractNodes(evidence.contractLayoutShape?.nodes || []);
    const contractFields = contractNodes.filter((node) => node.type === 'field' && node.name);
    const nativeSourceFields = nativeOdoo.sourceView.atoms.filter((atom) => atom.tag === 'field' && atom.name);
    const metadataGaps = [];
    const metadataPairs = [];
    for (const nativeField of nativeSourceFields) {
      const normalizedField = contractFields.find((field) => field.name === nativeField.name);
      if (!normalizedField) {
        metadataGaps.push({ field: nativeField.name, property: 'node', native: true, normalized: false });
        continue;
      }
      for (const property of ['label', 'nolabel', 'widget', 'options', 'domain', 'modifiers', 'invisible', 'readonly', 'required']) {
        const nativeValue = nativeField[property];
        const normalizedAttribute = property === 'label'
          ? normalizedField.label
          : property === 'nolabel'
            ? normalizedField.nolabel
            : normalizedField.attributes?.[property];
        const normalizedValue = normalizedAttribute ?? normalizedField[property];
        metadataPairs.push({ field: nativeField.name, property, native: nativeValue, normalized: normalizedValue });
        const normalizedComparable = property === 'nolabel'
          ? (normalizedValue === true ? '1' : normalizedValue === false ? '' : normalizedValue)
          : normalizedValue;
        if (nativeValue !== '' && nativeValue !== null && nativeValue !== undefined
          && (normalizedComparable === '' || normalizedComparable === null || normalizedComparable === undefined)) {
          metadataGaps.push({ field: nativeField.name, property, native: nativeValue, normalized: normalizedValue });
        }
      }
    }
    const nativeStructureCounts = nativeOdoo.sourceView.atoms.reduce((acc, atom) => {
      const kind = atom.tag === 'div' && /(?:^|\s)alert(?:\s|$)/.test(atom.className) ? 'alert' : atom.tag;
      acc[kind] = (acc[kind] || 0) + 1;
      return acc;
    }, {});
    const normalizedStructureCounts = contractNodes.reduce((acc, node) => {
      const kind = String(node.type || node.containerType || 'container').toLowerCase();
      acc[kind] = (acc[kind] || 0) + 1;
      return acc;
    }, {});
    const requiredCapabilities = ['sheet', 'notebook', 'page', 'alert', 'widget', 'chatter'];
    const structureGaps = requiredCapabilities
      .filter((kind) => (nativeStructureCounts[kind] || 0) > 0 && (normalizedStructureCounts[kind] || 0) === 0)
      .map((kind) => ({ kind, native: nativeStructureCounts[kind], normalized: normalizedStructureCounts[kind] || 0 }));
    const nativeStructureSignature = nativeOdoo.sourceView.atoms
      .filter((atom) => atom.tag !== 'form')
      .map((atom) => ({
        kind: atom.tag === 'div' ? 'container' : atom.tag,
        identity: ['field', 'button', 'widget', 'page'].includes(atom.tag) ? atom.name : '',
        depth: Math.max(0, atom.path.length - 1),
      }));
    const normalizedStructureSignature = contractNodes
      .filter((node) => node.type !== 'text')
      .map((node) => ({
        kind: node.type || node.containerType || 'container',
        identity: ['field', 'button', 'widget', 'page'].includes(node.type) ? node.name : '',
        depth: node.path.length,
      }));
    const nativeActionOrder = nativeOdoo.actions.map((action) => (
      /^\d+$/.test(String(action.method || '')) ? `window_action:${action.method}` : `button:object:${action.method}`
    ));
    const customActionOrder = result.canonical.actions.map((action) => action.backendIdentity);
    const nativeParity = {
      fields: {
        native: nativeFieldSet,
        custom: customFieldSet,
        customStructural: [...new Set(result.canonical.fields.map((field) => field.fieldCode))].sort(),
        missingInCustom: nativeFieldSet.filter((field) => !customFieldSet.includes(field)),
        extraInCustom: customFieldSet.filter((field) => !nativeFieldSet.includes(field)),
        nativeOrder: nativeOdoo.fields.map((field) => field.fieldCode),
        customOrder: result.canonical.fields.filter((field) => field.visible).map((field) => field.fieldCode),
      },
      actions: {
        native: nativeActionSet,
        custom: customActionSet,
        missingInCustom: nativeActionSet.filter((action) => !customActionSet.includes(action)),
        extraInCustom: customActionSet.filter((action) => !nativeActionSet.includes(action)),
        nativeOrder: nativeActionOrder,
        customOrder: customActionOrder,
      },
      structure: {
        nativeCounts: nativeStructureCounts,
        normalizedCounts: normalizedStructureCounts,
        gaps: structureGaps,
        normalizedHierarchy: contractNodes.map((node) => ({ path: node.path, type: node.type, name: node.name })),
        canonicalHierarchy: result.canonical.nodes.map((node) => ({ path: node.path, kind: node.kind, id: node.id })),
        nativeSignature: nativeStructureSignature,
        normalizedSignature: normalizedStructureSignature,
      },
      fieldMetadata: { gaps: metadataGaps, pairs: metadataPairs },
      nativeWidgets: {
        declared: nativeOdoo.sourceView.atoms.filter((atom) => atom.tag === 'widget').map((atom) => atom.name),
        custom: result.canonical.nativeWidgets,
      },
    };
    fs.writeFileSync(path.join(OUTPUT, 'native-custom-parity.json'), `${JSON.stringify({
      nativeOdoo,
      contractRequests: evidence.contractRequests,
      contractStatusDiagnostics: evidence.contractStatusDiagnostics,
      nativeParity,
    }, null, 2)}\n`);
    check(nativeParity.fields.missingInCustom.length === 0 && nativeParity.fields.extraInCustom.length === 0, `native/custom field parity failed: ${JSON.stringify(nativeParity.fields)}`);
    check(JSON.stringify(nativeParity.fields.nativeOrder) === JSON.stringify(nativeParity.fields.customOrder), `native/custom field order parity failed: ${JSON.stringify(nativeParity.fields)}`);
    check(nativeParity.actions.missingInCustom.length === 0 && nativeParity.actions.extraInCustom.length === 0, `native/custom action parity failed: ${JSON.stringify(nativeParity.actions)}`);
    check(JSON.stringify(nativeActionOrder) === JSON.stringify(customActionOrder), `native/custom action occurrence order parity failed: ${JSON.stringify(nativeParity.actions)}`);
    check(structureGaps.length === 0, `native/normalized structural capability parity failed: ${JSON.stringify(structureGaps)}`);
    check(
      JSON.stringify(nativeStructureSignature) === JSON.stringify(normalizedStructureSignature),
      'native/normalized container hierarchy signature differs',
    );
    check(metadataGaps.length === 0, `native/normalized field metadata parity failed: ${JSON.stringify(metadataGaps)}`);
    check(
      nativeParity.nativeWidgets.declared.length === nativeParity.nativeWidgets.custom.length
        && nativeParity.nativeWidgets.custom.every((widget) => widget.state === 'resolved'),
      `native widget behavior is not resolved by the custom renderer: ${JSON.stringify(nativeParity.nativeWidgets)}`,
    );
    check(evidence.mutations.length === 0, 'readonly journey issued a business mutation');
    check(evidence.console.length === 0 && evidence.pageerror.length === 0 && evidence.failed.length === 0, 'runtime errors detected');

    const screenshot = path.join(OUTPUT, 'tdesign-readonly-project.png');
    await page.screenshot({ path: screenshot, fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(300);
    const mobile = {
      canonical: await page.evaluate(canonicalDomSnapshot),
      horizontalOverflow: await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)),
    };
    assertCanonicalSnapshot(mobile.canonical, 'readonly custom mobile');
    check(mobile.horizontalOverflow === 0, 'readonly custom mobile caused horizontal overflow');
    check(
      JSON.stringify(nativeOdoo.mobile.fieldOrder) === JSON.stringify(mobile.canonical.fields.filter((field) => field.visible).map((field) => field.fieldCode)),
      'readonly mobile native/custom field order parity failed',
    );
    const mobileScreenshot = path.join(OUTPUT, 'tdesign-readonly-project-mobile-390.png');
    await page.screenshot({ path: mobileScreenshot, fullPage: true });
    check(evidence.mutations.length === 0, `readonly parity issued a business mutation: ${JSON.stringify(evidence.mutations)}`);
    check(
      evidence.console.length === 0 && evidence.pageerror.length === 0 && evidence.failed.length === 0,
      `readonly parity runtime errors detected: ${JSON.stringify({ console: evidence.console, pageerror: evidence.pageerror, failed: evidence.failed })}`,
    );
    const report = {
      schema_version: 'native_same_page_readonly_parity.v1',
      result: 'PASS',
      phase: 'readonly_only',
      database_write_policy: 'browser_business_mutations_forbidden',
      git_sha: process.env.GIT_SHA || '',
      database: DB_NAME,
      target: { ...TARGET, login: TARGET.login },
      nativeOdoo,
      nativeParity,
      customDriver: hostDiagnostic.activeKit,
      ...result,
      mobile: {
        ...mobile,
        screenshot: { path: mobileScreenshot, sha256: sha256(mobileScreenshot) },
      },
      runtime_errors: {
        console: evidence.console,
        pageerror: evidence.pageerror,
        failed: evidence.failed,
        mutations: evidence.mutations,
        systemInitPolicy: evidence.systemInitPolicy,
      },
      screenshot: { path: screenshot, sha256: sha256(screenshot) },
    };
    const reportPath = path.join(OUTPUT, 'report.json');
    fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
    console.log(`[frontend_scene_component_driver_readonly_browser] PASS report=${reportPath}`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`[frontend_scene_component_driver_readonly_browser] FAIL ${error.stack || error.message}`);
  process.exit(2);
});

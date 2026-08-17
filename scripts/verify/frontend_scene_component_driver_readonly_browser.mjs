#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5175';
const DB_NAME = process.env.DB_NAME || 'sc_frontend_acceptance';
const PASSWORD = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const TARGET = JSON.parse(process.env.SCENE_COMPONENT_DRIVER_TARGETS_JSON || '{}');
const OUTPUT = process.env.SCENE_COMPONENT_DRIVER_ARTIFACTS || 'artifacts/frontend-scene-component-driver';
const FIELD_MATRIX = JSON.parse(fs.readFileSync('config/p1_payment_request_field_completeness_v1.json', 'utf8'));

function requiredPaymentPrimaryFields(profile, state) {
  const mapping = FIELD_MATRIX.form_surface_profile_mapping || {};
  return (FIELD_MATRIX.field_rules || [])
    .filter((rule) => rule.model === 'payment.request')
    .filter((rule) => (rule.surfaces || []).some((surface) => (mapping[surface] || []).includes(profile)))
    .filter((rule) => rule.zone !== 'subordinate')
    .filter((rule) => rule.applicability !== 'state_rejected' || state === 'rejected')
    .map((rule) => String(rule.field || ''))
    .filter(Boolean);
}

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

async function login(page, loginName) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(loginName);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('input').nth(2);
  if (await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
}

async function logout(page) {
  const logoutButton = page.getByRole('button', { name: '退出登录' });
  if (!(await logoutButton.isVisible().catch(() => false))) {
    const menuButton = page.getByRole('button', { name: '菜单', exact: true });
    if (await menuButton.isVisible().catch(() => false)) await menuButton.click();
  }
  await logoutButton.click();
  await page.waitForURL((url) => url.pathname.includes('/login'), { timeout: 30000 });
}

const canonicalDomSnapshot = () => ({
  nodes: [...document.querySelectorAll('[data-canonical-form-zones] [data-canonical-node-id]')].map((node) => ({
    id: node.getAttribute('data-canonical-node-id') || '',
    kind: node.getAttribute('data-canonical-node-kind') || '',
    zone: node.closest('[data-canonical-zone]')?.getAttribute('data-canonical-zone') || '',
  })),
  fields: [...document.querySelectorAll('[data-canonical-form-zones] [data-field-key]')].map((node) => ({
    widgetId: node.getAttribute('data-field-key') || '',
    fieldCode: node.getAttribute('data-field-name') || '',
    state: node.getAttribute('data-field-state') || '',
    type: node.getAttribute('data-field-type') || '',
  })),
  actions: [...document.querySelectorAll('[data-canonical-action-bar] [data-action-ref]')].map((node) => ({
    actionId: node.getAttribute('data-action-ref') || '',
    backendIdentity: node.getAttribute('data-backend-identity') || '',
    tier: node.getAttribute('data-action-tier') || '',
    enabled: node.getAttribute('data-action-enabled') || '',
    disabled: node.hasAttribute('disabled'),
  })),
});

function assertCanonicalSnapshot(snapshot, label) {
  check(snapshot.nodes.length > 0, `${label} canonical nodes missing`);
  check(snapshot.fields.length > 0, `${label} canonical fields missing`);
  check(new Set(snapshot.nodes.map((node) => node.id)).size === snapshot.nodes.length, `${label} canonical nodes duplicated`);
  check(new Set(snapshot.fields.map((field) => field.widgetId)).size === snapshot.fields.length, `${label} widget identities duplicated`);
  check(snapshot.fields.every((field) => field.widgetId && field.fieldCode), `${label} field identity missing`);
  check(new Set(snapshot.actions.map((action) => `${action.actionId}\u0000${action.backendIdentity}`)).size === snapshot.actions.length, `${label} action references duplicated`);
  check(snapshot.actions.every((action) => action.actionId && action.backendIdentity), `${label} action reference missing`);
}

async function main() {
  check(PASSWORD, 'SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
  check(TARGET.model && !String(TARGET.model).includes('payment') && TARGET.record_id > 0 && TARGET.action_id > 0 && TARGET.menu_id > 0, 'invalid non-payment target');
  const paymentTarget = TARGET.payment_target || {};
  check(
    paymentTarget.model === 'payment.request'
      && paymentTarget.record_id > 0
      && paymentTarget.draft_record_id > 0
      && paymentTarget.action_id > 0
      && paymentTarget.menu_id > 0
      && paymentTarget.login,
    'invalid governed payment qualification target',
  );
  fs.mkdirSync(OUTPUT, { recursive: true });
  const browser = await launchChromium();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const evidence = {
    console: [], pageerror: [], failed: [], mutations: [], systemInitPolicy: null,
    contractLayoutShape: null, contractActionSummary: null, contractSha256: '', contractResponses: [],
  };
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) evidence.console.push(message.text());
  });
  page.on('pageerror', (error) => evidence.pageerror.push(error.message));
  page.on('request', (request) => {
    if (isBusinessMutation(request)) {
      const body = requestBody(request);
      evidence.mutations.push({
        intent: requestIntent(request),
        op: requestOperation(request),
        model: String(body?.params?.model || body?.params?.payload?.model || ''),
        valueKeys: Object.keys(body?.params?.vals || body?.params?.payload?.vals || {}).sort(),
        url: request.url(),
      });
    }
  });
  page.on('response', async (response) => {
    if (response.status() >= 400 && !/favicon/i.test(response.url())) evidence.failed.push({ status: response.status(), url: response.url() });
    const request = response.request();
    const intent = requestIntent(request);
    if (request.method() === 'POST' && /json/i.test(response.headers()['content-type'] || '')) {
      try {
        const body = await response.json();
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
        const summarize = (nodes) => (Array.isArray(nodes) ? nodes : []).map((node) => ({
          keys: node && typeof node === 'object' ? Object.keys(node).sort() : [],
          containerId: String(node?.containerId || ''),
          containerType: String(node?.containerType || ''),
          type: String(node?.type || ''),
          name: String(node?.name || ''),
          children: summarize(node?.children),
        }));
        if (contract) {
          evidence.contractLayoutShape = { intent, nodes: summarize(contract.layoutContract.containerTree) };
          const buttonStatus = new Map((contract?.statusContract?.buttonStatus || []).map((row) => [String(row?.btnId || ''), row]));
          evidence.contractActionSummary = (contract?.actionContract?.actionRuleList || []).map((row) => ({
            actionId: String(row?.actionId || ''),
            actionKey: String(row?.actionKey || ''),
            backendIdentity: String(row?.backendIdentity || ''),
            sourceWidgetId: String(row?.sourceWidgetId || ''),
            targetScope: String(row?.targetScope || ''),
            triggerType: String(row?.triggerType || ''),
            tier: String(row?.presentation?.tier || ''),
            visibleProfiles: Array.isArray(row?.visibleProfiles) ? row.visibleProfiles : [],
            allowed: row?.allowed,
            enabled: row?.enabled,
            disabled: row?.disabled,
            status: buttonStatus.get(String(row?.actionId || '')) || null,
          }));
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
    await login(page, TARGET.login);

    const route = `/r/${encodeURIComponent(TARGET.model)}/${TARGET.record_id}?action_id=${TARGET.action_id}&menu_id=${TARGET.menu_id}`;
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
      fs.writeFileSync(failureReport, `${JSON.stringify({ ...diagnostic, systemInitPolicy: evidence.systemInitPolicy, contractLayoutShape: evidence.contractLayoutShape, screenshot: failureScreenshot }, null, 2)}\n`);
      throw new Error(`ContractForm driver host missing: ${JSON.stringify({ ...diagnostic, systemInitPolicy: evidence.systemInitPolicy, contractLayoutShape: evidence.contractLayoutShape, screenshot: failureScreenshot, report: failureReport })}`, { cause: error });
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
      };
    });
    result.canonical = await page.evaluate(canonicalDomSnapshot);
    result.fieldCount = result.canonical.fields.length;
    result.uniqueFieldCount = new Set(result.canonical.fields.map((field) => field.widgetId)).size;
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
    assertCanonicalSnapshot(result.canonical, 'readonly TDesign');
    check(evidence.mutations.length === 0, 'readonly journey issued a business mutation');
    check(evidence.console.length === 0 && evidence.pageerror.length === 0 && evidence.failed.length === 0, 'runtime errors detected');

    const screenshot = path.join(OUTPUT, 'tdesign-readonly-project.png');
    await page.screenshot({ path: screenshot, fullPage: true });
    const readonlyState = result.canonical;
    const readonlyResponsesBeforeSwitch = evidence.contractResponses.length;
    await page.locator('[data-contract-form-driver-chooser]').selectOption('ui5-horizon');
    const ui5ReadonlyHost = page.locator('[data-contract-form-driver="ui5-horizon"]');
    await ui5ReadonlyHost.waitFor({ state: 'visible', timeout: 45000 });
    await page.locator('[data-scene-ui-kit="ui5-horizon"]').waitFor({ state: 'visible', timeout: 45000 });
    await page.locator('[data-control-driver="ui5-horizon"] ui5-input, [data-control-driver="ui5-horizon"] ui5-date-picker, [data-control-driver="ui5-horizon"] ui5-select, [data-control-driver="ui5-horizon"] ui5-textarea').first().waitFor({ state: 'visible', timeout: 45000 });
    const ui5ReadonlyState = await page.evaluate(() => ({
      sha: document.querySelector('[data-contract-form-driver="ui5-horizon"]')?.getAttribute('data-source-contract-sha') || '',
      editableControls: [...document.querySelectorAll('[data-control-driver="ui5-horizon"] ui5-input, [data-control-driver="ui5-horizon"] ui5-date-picker, [data-control-driver="ui5-horizon"] ui5-select, [data-control-driver="ui5-horizon"] ui5-textarea')]
        .filter((node) => !node.hasAttribute('disabled')).length,
      horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
    }));
    ui5ReadonlyState.canonical = await page.evaluate(canonicalDomSnapshot);
    assertCanonicalSnapshot(ui5ReadonlyState.canonical, 'readonly UI5');
    check(ui5ReadonlyState.sha === result.sourceContractSha256, 'readonly contract identity changed during TDesign to UI5 switch');
    check(JSON.stringify(ui5ReadonlyState.canonical) === JSON.stringify(readonlyState), 'readonly canonical DOM changed during TDesign to UI5 switch');
    check(ui5ReadonlyState.editableControls === 0, 'UI5 readonly driver exposed an editable control');
    check(ui5ReadonlyState.horizontalOverflow === 0, 'UI5 readonly driver caused horizontal overflow');
    check(evidence.contractResponses.length === readonlyResponsesBeforeSwitch, 'readonly UI5 switch refetched business contract');
    const ui5ReadonlyScreenshot = path.join(OUTPUT, 'ui5-readonly-project.png');
    await page.screenshot({ path: ui5ReadonlyScreenshot, fullPage: true });
    await page.locator('[data-contract-form-driver-chooser]').selectOption('sc-native');
    await page.locator('[data-contract-form-driver="sc-native"]').waitFor({ state: 'visible', timeout: 15000 });
    const nativeReadonlyState = await page.evaluate(() => ({
      sha: document.querySelector('[data-contract-form-driver="sc-native"]')?.getAttribute('data-source-contract-sha') || '',
    }));
    nativeReadonlyState.canonical = await page.evaluate(canonicalDomSnapshot);
    assertCanonicalSnapshot(nativeReadonlyState.canonical, 'readonly Native');
    check(nativeReadonlyState.sha === result.sourceContractSha256, 'readonly contract identity changed during UI5 to Native switch');
    check(JSON.stringify(nativeReadonlyState.canonical) === JSON.stringify(readonlyState), 'readonly canonical DOM changed during UI5 to Native switch');
    check(evidence.contractResponses.length === readonlyResponsesBeforeSwitch, 'readonly Native switch refetched business contract');
    await page.locator('[data-contract-form-driver-chooser]').selectOption('tdesign-modern');
    await page.locator('[data-contract-form-driver="tdesign-modern"]').waitFor({ state: 'visible', timeout: 15000 });

    async function exerciseEditableMode(mode, editableRoute, updatedValueOverride = '') {
      const contractResponsesBeforeRoute = evidence.contractResponses.length;
      await page.goto(`${BASE_URL}${editableRoute}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
      const tdesignHost = page.locator('[data-contract-form-driver="tdesign-modern"]');
      await tdesignHost.waitFor({ state: 'visible', timeout: 45000 });
      await page.locator('[data-scene-ui-kit="tdesign-modern"]').waitFor({ state: 'visible', timeout: 45000 });
      await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 45000 });
      await page.locator('[data-control-driver="tdesign-modern"] [data-scene-driver-control]').first().waitFor({ state: 'visible', timeout: 45000 });
      await page.waitForTimeout(300);

      const contractSha = await tdesignHost.getAttribute('data-source-contract-sha');
      check(contractSha, `${mode} source contract identity missing`);
      check(evidence.contractResponses.length > contractResponsesBeforeRoute, `${mode} normalized contract response missing`);
      check(evidence.contractSha256 === contractSha, `${mode} network and canvas contract identities differ`);

      const before = await page.evaluate(() => ({
        horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
      }));
      before.canonical = await page.evaluate(canonicalDomSnapshot);
      assertCanonicalSnapshot(before.canonical, `${mode} TDesign`);
      check(before.horizontalOverflow === 0, `${mode} driver caused horizontal overflow`);

      const editable = page.locator(
        '[data-field-type="char"] [data-control-driver="tdesign-modern"] input:not([disabled]):not([readonly]), '
        + '[data-field-type="text"] [data-control-driver="tdesign-modern"] textarea:not([disabled]):not([readonly])',
      ).first();
      await editable.waitFor({ state: 'visible', timeout: 45000 });
      const fieldName = await editable.evaluate((node) => node.closest('[data-field-name]')?.getAttribute('data-field-name') || '');
      check(fieldName, `${mode} editable field identity missing`);
      const originalValue = await editable.inputValue();
      const updatedValue = updatedValueOverride || `${originalValue || mode}-${mode}-driver`;
      await editable.fill(updatedValue);
      await editable.blur();

      const contractResponsesBeforeSwitch = evidence.contractResponses.length;
      const chooser = page.locator('[data-contract-form-driver-chooser]');
      await chooser.selectOption('sc-native');
      const nativeHost = page.locator('[data-contract-form-driver="sc-native"]');
      await nativeHost.waitFor({ state: 'visible', timeout: 15000 });
      const nativeInput = page.locator(`[data-field-name="${fieldName}"] input, [data-field-name="${fieldName}"] textarea`).first();
      await nativeInput.waitFor({ state: 'visible', timeout: 15000 });
      check(await nativeInput.inputValue() === updatedValue, `${mode} draft value changed during TDesign to Native switch`);
      const nativeState = await page.evaluate(() => ({
        sha: document.querySelector('[data-contract-form-driver="sc-native"]')?.getAttribute('data-source-contract-sha') || '',
      }));
      nativeState.canonical = await page.evaluate(canonicalDomSnapshot);
      assertCanonicalSnapshot(nativeState.canonical, `${mode} Native`);
      check(nativeState.sha === contractSha, `${mode} contract identity changed during driver switch`);
      check(JSON.stringify(nativeState.canonical) === JSON.stringify(before.canonical), `${mode} canonical DOM changed during driver switch`);
      check(evidence.contractResponses.length === contractResponsesBeforeSwitch, `${mode} driver switch refetched business contract`);

      await page.locator('[data-contract-form-driver-chooser]').selectOption('ui5-horizon');
      const ui5Host = page.locator('[data-contract-form-driver="ui5-horizon"]');
      await ui5Host.waitFor({ state: 'visible', timeout: 45000 });
      await page.locator('[data-scene-ui-kit="ui5-horizon"]').waitFor({ state: 'visible', timeout: 45000 });
      const ui5Input = page.locator(
        `[data-field-name="${fieldName}"] [data-control-driver="ui5-horizon"] ui5-input, `
        + `[data-field-name="${fieldName}"] [data-control-driver="ui5-horizon"] ui5-textarea`,
      ).first();
      await ui5Input.waitFor({ state: 'visible', timeout: 45000 });
      check(
        await ui5Input.evaluate((node) => String(node.value || '')) === updatedValue,
        `${mode} draft value changed during Native to UI5 switch`,
      );
      const ui5State = await page.evaluate(() => ({
        sha: document.querySelector('[data-contract-form-driver="ui5-horizon"]')?.getAttribute('data-source-contract-sha') || '',
        horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
      }));
      ui5State.canonical = await page.evaluate(canonicalDomSnapshot);
      assertCanonicalSnapshot(ui5State.canonical, `${mode} UI5`);
      check(ui5State.sha === contractSha, `${mode} contract identity changed during UI5 switch`);
      check(JSON.stringify(ui5State.canonical) === JSON.stringify(before.canonical), `${mode} canonical DOM changed during UI5 switch`);
      check(ui5State.horizontalOverflow === 0, `${mode} UI5 driver caused horizontal overflow`);
      check(evidence.contractResponses.length === contractResponsesBeforeSwitch, `${mode} UI5 switch refetched business contract`);
      const ui5ModeScreenshot = path.join(OUTPUT, `ui5-${mode}-project.png`);
      await page.screenshot({ path: ui5ModeScreenshot, fullPage: true });

      await page.locator('[data-contract-form-driver-chooser]').selectOption('tdesign-modern');
      await page.locator('[data-contract-form-driver="tdesign-modern"]').waitFor({ state: 'visible', timeout: 15000 });
      const restoredInput = page.locator(
        `[data-field-name="${fieldName}"] [data-control-driver="tdesign-modern"] input, `
        + `[data-field-name="${fieldName}"] [data-control-driver="tdesign-modern"] textarea`,
      ).first();
      await restoredInput.waitFor({ state: 'visible', timeout: 15000 });
      check(await restoredInput.inputValue() === updatedValue, `${mode} draft value changed during Native to TDesign switch`);
      const modeScreenshot = path.join(OUTPUT, `tdesign-${mode}-project.png`);
      await page.screenshot({ path: modeScreenshot, fullPage: true });
      return {
        mode, route: editableRoute, sourceContractSha256: contractSha, fieldCount: before.canonical.fields.length,
        actionCount: before.canonical.actions.length, canonical: before.canonical, editedField: fieldName, originalValue, updatedValue,
        contractResponsesDuringSwitch: evidence.contractResponses.length - contractResponsesBeforeSwitch,
        screenshot: { path: modeScreenshot, sha256: sha256(modeScreenshot) },
        ui5Screenshot: { path: ui5ModeScreenshot, sha256: sha256(ui5ModeScreenshot) },
      };
    }

    const editResult = await exerciseEditableMode(
      'edit',
      `/f/${encodeURIComponent(TARGET.model)}/${TARGET.record_id}?action_id=${TARGET.action_id}&menu_id=${TARGET.menu_id}`,
    );
    const createResult = await exerciseEditableMode(
      'create',
      `/f/${encodeURIComponent(TARGET.model)}/new?action_id=${TARGET.action_id}&menu_id=${TARGET.menu_id}`,
      String(TARGET.create_probe_name || ''),
    );

    async function executeCreateProbe() {
      check(TARGET.create_probe_name, 'create probe identity missing from governed fixture');
      await page.locator('[data-contract-form-driver-chooser]').selectOption('ui5-horizon');
      await page.locator('[data-contract-form-driver="ui5-horizon"]').waitFor({ state: 'visible', timeout: 45000 });
      const probeInput = page.locator('[data-field-name="name"] [data-control-driver="ui5-horizon"] ui5-input').first();
      await probeInput.waitFor({ state: 'visible', timeout: 45000 });
      check(
        await probeInput.evaluate((node) => String(node.value || '')) === TARGET.create_probe_name,
        'create probe value changed before unified save execution',
      );
      const createPreflight = await page.evaluate(canonicalDomSnapshot);
      fs.writeFileSync(path.join(OUTPUT, 'create-action-preflight.json'), `${JSON.stringify(createPreflight, null, 2)}\n`);
      console.log(`[frontend_scene_component_driver_readonly_browser] CREATE_PREFLIGHT ${JSON.stringify(createPreflight.actions)}`);
      const canonicalSave = page.locator('[data-canonical-action-bar] [data-action-ref="form.save"]').first();
      await canonicalSave.waitFor({ state: 'visible', timeout: 45000 });
      check(await canonicalSave.getAttribute('data-backend-identity'), 'canonical form.save backend identity missing');
      check(await canonicalSave.isEnabled(), 'canonical form.save action is disabled');
      const createResponsePromise = page.waitForResponse((response) => {
        const request = response.request();
        const body = requestBody(request);
        return requestIntent(request) === 'api.data'
          && requestOperation(request) === 'create'
          && String(body?.params?.model || '') === TARGET.model;
      }, { timeout: Number(process.env.SCENE_COMPONENT_DRIVER_CREATE_TIMEOUT_MS || 45000) });
      await canonicalSave.click();
      let createResponse;
      try {
        createResponse = await createResponsePromise;
      } catch (error) {
        const failure = await page.evaluate(() => ({
          url: location.href,
          contractError: document.querySelector('[data-contract-form-driver-error]')?.textContent || '',
          validationErrors: [...document.querySelectorAll('.validation-error, .field-error-text')].map((node) => String(node.textContent || '').trim()).filter(Boolean),
          visibleButtons: [...document.querySelectorAll('button')].filter((node) => node.getClientRects().length > 0).map((node) => ({
            text: String(node.textContent || '').trim(),
            actionId: node.getAttribute('data-action-ref') || '',
            backendIdentity: node.getAttribute('data-backend-identity') || '',
            disabled: node.hasAttribute('disabled'),
          })),
        }));
        const failureScreenshot = path.join(OUTPUT, 'failure-canonical-save.png');
        await page.screenshot({ path: failureScreenshot, fullPage: true });
        fs.writeFileSync(path.join(OUTPUT, 'failure-canonical-save.json'), `${JSON.stringify({ ...failure, mutations: evidence.mutations, screenshot: { path: failureScreenshot, sha256: sha256(failureScreenshot) } }, null, 2)}\n`);
        throw error;
      }
      check(createResponse.ok(), `create probe request failed with ${createResponse.status()}`);
      const request = createResponse.request();
      const requestPayload = requestBody(request);
      check(requestPayload?.params?.vals?.name === TARGET.create_probe_name, 'unified create request lost the driver-neutral field value');
      const responsePayload = await createResponse.json();
      const findCreatedId = (value, depth = 0) => {
        if (!value || typeof value !== 'object' || depth > 6) return 0;
        if (Number(value.id || 0) > 0) return Number(value.id);
        for (const nested of Object.values(value)) {
          const found = findCreatedId(nested, depth + 1);
          if (found > 0) return found;
        }
        return 0;
      };
      const createdId = findCreatedId(responsePayload);
      check(createdId > 0, 'unified create response did not return a record identity');
      await page.waitForURL((url) => !url.pathname.endsWith('/new') && url.pathname.includes(`/${createdId}`), { timeout: 45000 });
      await page.locator('[data-contract-form-driver]').first().waitFor({ state: 'visible', timeout: 45000 });
      const persistedName = await page.locator('[data-field-name="name"] input, [data-field-name="name"] ui5-input').first()
        .evaluate((node) => String(node.value || node.getAttribute('value') || ''));
      check(persistedName === TARGET.create_probe_name, 'created record did not reopen with the persisted driver-neutral value');
      return {
        intent: requestIntent(request),
        op: requestOperation(request),
        model: String(requestPayload?.params?.model || ''),
        valueKeys: Object.keys(requestPayload?.params?.vals || {}).sort(),
        createdId,
        activeDriver: await page.locator('[data-contract-form-driver]').first().getAttribute('data-contract-form-driver'),
      };
    }

    const createExecution = await executeCreateProbe();

    async function exerciseUi5MobileMode(mode, mobileRoute) {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto(`${BASE_URL}${mobileRoute}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.locator('[data-contract-form-driver]').first().waitFor({ state: 'visible', timeout: 45000 });
      await page.locator('[data-contract-form-driver-chooser]').selectOption('ui5-horizon');
      const ui5Host = page.locator('[data-contract-form-driver="ui5-horizon"]');
      await ui5Host.waitFor({ state: 'visible', timeout: 45000 });
      await page.locator('[data-scene-ui-kit="ui5-horizon"]').waitFor({ state: 'visible', timeout: 45000 });
      await page.locator('[data-control-driver="ui5-horizon"]').first().waitFor({ state: 'visible', timeout: 45000 });
      await page.waitForTimeout(300);
      const mobileState = await page.evaluate(() => ({
          sha: document.querySelector('[data-contract-form-driver="ui5-horizon"]')?.getAttribute('data-source-contract-sha') || '',
          horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
      }));
      mobileState.canonical = await page.evaluate(canonicalDomSnapshot);
      mobileState.fieldCount = mobileState.canonical.fields.length;
      mobileState.uniqueFieldCount = new Set(mobileState.canonical.fields.map((field) => field.widgetId)).size;
      mobileState.actionCount = mobileState.canonical.actions.length;
      mobileState.uniqueActionCount = new Set(mobileState.canonical.actions.map((action) => `${action.actionId}\u0000${action.backendIdentity}`)).size;
      assertCanonicalSnapshot(mobileState.canonical, `${mode} UI5 mobile`);
      check(mobileState.sha, `${mode} UI5 mobile source contract identity missing`);
      check(mobileState.fieldCount > 0 && mobileState.fieldCount === mobileState.uniqueFieldCount, `${mode} UI5 mobile fields are missing or duplicated`);
      check(mobileState.actionCount === mobileState.uniqueActionCount, `${mode} UI5 mobile actions are duplicated`);
      check(mobileState.horizontalOverflow === 0, `${mode} UI5 mobile caused horizontal overflow`);
      const mobileScreenshot = path.join(OUTPUT, `ui5-${mode}-mobile-390.png`);
      await page.screenshot({ path: mobileScreenshot, fullPage: true });
      return {
        mode,
        route: mobileRoute,
        ...mobileState,
        screenshot: { path: mobileScreenshot, sha256: sha256(mobileScreenshot) },
      };
    }

    const mobileModes = [];
    for (const [mode, mobileRoute] of [
      ['readonly', route],
      ['edit', `/f/${encodeURIComponent(TARGET.model)}/${TARGET.record_id}?action_id=${TARGET.action_id}&menu_id=${TARGET.menu_id}`],
      ['create', `/f/${encodeURIComponent(TARGET.model)}/new?action_id=${TARGET.action_id}&menu_id=${TARGET.menu_id}`],
    ]) {
      mobileModes.push(await exerciseUi5MobileMode(mode, mobileRoute));
    }
    check(
      evidence.mutations.length === 1
        && evidence.mutations[0]?.intent === 'api.data'
        && evidence.mutations[0]?.op === 'create'
        && evidence.mutations[0]?.model === TARGET.model,
      `driver parity journey issued an unexpected business mutation: ${JSON.stringify(evidence.mutations)}`,
    );

    await page.setViewportSize({ width: 1440, height: 900 });
    await logout(page);
    await login(page, paymentTarget.login);

    async function paymentDriverState(driverKit) {
      return page.evaluate(({ driverKit }) => {
        const canonical = {
          nodes: [...document.querySelectorAll('[data-canonical-form-zones] [data-canonical-node-id]')].map((node) => ({
            id: node.getAttribute('data-canonical-node-id') || '',
            kind: node.getAttribute('data-canonical-node-kind') || '',
            zone: node.closest('[data-canonical-zone]')?.getAttribute('data-canonical-zone') || '',
          })),
          fields: [...document.querySelectorAll('[data-canonical-form-zones] [data-field-key]')].map((node) => ({
            widgetId: node.getAttribute('data-field-key') || '',
            fieldCode: node.getAttribute('data-field-name') || '',
            state: node.getAttribute('data-field-state') || '',
            type: node.getAttribute('data-field-type') || '',
            zone: node.closest('[data-canonical-zone]')?.getAttribute('data-canonical-zone') || '',
          })),
          actions: [...document.querySelectorAll('[data-canonical-action-bar] [data-action-ref]')].map((node) => ({
            actionId: node.getAttribute('data-action-ref') || '',
            backendIdentity: node.getAttribute('data-backend-identity') || '',
            tier: node.getAttribute('data-action-tier') || '',
            enabled: node.getAttribute('data-action-enabled') || '',
            disabled: node.hasAttribute('disabled'),
          })),
        };
        const primaryZone = document.querySelector('[data-canonical-zone="primary"]');
        return {
          driverKit,
          sha: document.querySelector(`[data-contract-form-driver="${driverKit}"]`)?.getAttribute('data-source-contract-sha') || '',
          canonical,
          primarySectionIds: [...(primaryZone?.children || [])]
            .map((node) => node.getAttribute('data-canonical-node-id') || '')
            .filter(Boolean),
          horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
        };
      }, { driverKit });
    }

    async function qualifyPaymentMode(mode, paymentRoute, paymentState) {
      await page.goto(`${BASE_URL}${paymentRoute}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
      try {
        await page.locator('[data-contract-form-driver]').first().waitFor({ state: 'visible', timeout: 12000 });
        const chooser = page.locator('[data-contract-form-driver-chooser]');
        await chooser.waitFor({ state: 'visible', timeout: 12000 });
        if (await chooser.inputValue() !== 'tdesign-modern') await chooser.selectOption('tdesign-modern');
        await page.locator('[data-contract-form-driver="tdesign-modern"]').waitFor({ state: 'visible', timeout: 12000 });
      } catch (error) {
        const screenshotPath = path.join(OUTPUT, `failure-payment-${mode}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });
        const diagnostic = await page.evaluate(() => ({
          url: location.href,
          text: String(document.body?.innerText || '').slice(0, 1800),
          contractError: document.querySelector('[data-contract-form-driver-error]')?.textContent || '',
          activeDriver: document.querySelector('[data-contract-form-driver]')?.getAttribute('data-contract-form-driver') || '',
        }));
        const reportPath = path.join(OUTPUT, `failure-payment-${mode}.json`);
        fs.writeFileSync(reportPath, `${JSON.stringify({
          ...diagnostic,
          contractLayoutShape: evidence.contractLayoutShape,
          contractActionSummary: evidence.contractActionSummary,
          runtimeErrors: { console: evidence.console, pageerror: evidence.pageerror, failed: evidence.failed },
          screenshot: { path: screenshotPath, sha256: sha256(screenshotPath) },
        }, null, 2)}\n`);
        throw new Error(`payment ${mode} canonical host unavailable: ${JSON.stringify({ ...diagnostic, report: reportPath })}`, { cause: error });
      }
      await page.locator('[data-control-driver="tdesign-modern"]').first().waitFor({ state: 'visible', timeout: 45000 });
      await page.waitForTimeout(300);
      const responsesBeforeSwitch = evidence.contractResponses.length;
      const baseline = await paymentDriverState('tdesign-modern');
      const requiredPrimaryFields = requiredPaymentPrimaryFields(mode, paymentState);
      const primaryFields = baseline.canonical.fields.filter((field) => field.zone === 'primary');
      const subordinateFields = baseline.canonical.fields.filter((field) => field.zone === 'subordinate');
      const diagnosticPath = path.join(OUTPUT, `diagnostic-payment-${mode}.json`);
      fs.writeFileSync(diagnosticPath, `${JSON.stringify({
        mode,
        route: paymentRoute,
        paymentState,
        requiredPrimaryFields,
        primaryFields,
        subordinateFields,
        canonical: baseline.canonical,
        primarySectionIds: baseline.primarySectionIds,
        contractLayoutShape: evidence.contractLayoutShape,
        contractActionSummary: evidence.contractActionSummary,
      }, null, 2)}\n`);
      assertCanonicalSnapshot(baseline.canonical, `payment ${mode} TDesign`);
      const primaryCodes = new Set(primaryFields.map((field) => field.fieldCode));
      const missingRequired = requiredPrimaryFields.filter((field) => !primaryCodes.has(field));
      check(missingRequired.length === 0, `payment ${mode} missing required P1 fields: ${JSON.stringify(missingRequired)}`);
      check(primaryFields.length === primaryCodes.size, `payment ${mode} primary fields duplicated`);
      check(subordinateFields.length > 0, `payment ${mode} subordinate field capabilities missing`);
      const expectedPrimarySections = Number(paymentTarget.expected_primary_sections?.[mode] || 0);
      check(expectedPrimarySections > 0, `payment ${mode} expected primary-section authority is missing`);
      check(baseline.primarySectionIds.length === expectedPrimarySections, `payment ${mode} expected ${expectedPrimarySections} primary sections, got ${baseline.primarySectionIds.length}`);
      check(new Set(baseline.primarySectionIds).size === baseline.primarySectionIds.length, `payment ${mode} primary sections duplicated`);
      check(baseline.canonical.nodes.some((node) => node.zone === 'subordinate'), `payment ${mode} subordinate zones missing`);
      check(baseline.canonical.actions.filter((action) => action.tier === 'primary' && action.enabled === 'true').length === 1, `payment ${mode} must expose one enabled primary action`);
      check(baseline.horizontalOverflow === 0, `payment ${mode} TDesign overflow`);
      const drivers = [baseline];
      for (const driverKit of ['sc-native', 'ui5-horizon']) {
        await page.locator('[data-contract-form-driver-chooser]').selectOption(driverKit);
        await page.locator(`[data-contract-form-driver="${driverKit}"]`).waitFor({ state: 'visible', timeout: 45000 });
        await page.locator(`[data-scene-ui-kit="${driverKit}"]`).waitFor({ state: 'visible', timeout: 45000 });
        await page.waitForTimeout(250);
        const state = await paymentDriverState(driverKit);
        check(state.sha === baseline.sha, `payment ${mode} contract identity changed in ${driverKit}`);
        check(JSON.stringify(state.canonical) === JSON.stringify(baseline.canonical), `payment ${mode} canonical DOM changed in ${driverKit}`);
        check(JSON.stringify(state.primarySectionIds) === JSON.stringify(baseline.primarySectionIds), `payment ${mode} sections changed in ${driverKit}`);
        check(state.horizontalOverflow === 0, `payment ${mode} ${driverKit} overflow`);
        drivers.push(state);
      }
      check(evidence.contractResponses.length === responsesBeforeSwitch, `payment ${mode} driver switch refetched contract`);
      const screenshotPath = path.join(OUTPUT, `ui5-payment-${mode}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      return {
        mode,
        route: paymentRoute,
        sourceContractSha256: baseline.sha,
        primaryFieldCount: primaryFields.length,
        subordinateFieldCount: subordinateFields.length,
        requiredPrimaryFields,
        primarySectionIds: baseline.primarySectionIds,
        actionIdentities: baseline.canonical.actions.map((action) => action.backendIdentity),
        drivers: drivers.map((state) => state.driverKit),
        screenshot: { path: screenshotPath, sha256: sha256(screenshotPath) },
      };
    }

    const paymentQualification = [
      await qualifyPaymentMode(
        'readonly',
        `/r/${encodeURIComponent(paymentTarget.model)}/${paymentTarget.record_id}?action_id=${paymentTarget.action_id}&menu_id=${paymentTarget.menu_id}`,
        'approved',
      ),
      await qualifyPaymentMode(
        'edit',
        `/f/${encodeURIComponent(paymentTarget.model)}/${paymentTarget.draft_record_id}?action_id=${paymentTarget.action_id}&menu_id=${paymentTarget.menu_id}`,
        'draft',
      ),
    ];
    check(evidence.mutations.length === 1, `payment qualification issued a business mutation: ${JSON.stringify(evidence.mutations)}`);
    check(
      evidence.console.length === 0 && evidence.pageerror.length === 0 && evidence.failed.length === 0,
      `driver parity runtime errors detected: ${JSON.stringify({ console: evidence.console, pageerror: evidence.pageerror, failed: evidence.failed })}`,
    );
    const report = {
      schema_version: 'frontend_scene_component_driver_form.v4',
      result: 'PASS',
      git_sha: process.env.GIT_SHA || '',
      database: DB_NAME,
      target: { ...TARGET, login: TARGET.login },
      driver: 'tdesign-modern',
      ...result,
      editableModes: [editResult, createResult],
      createExecution,
      mobileModes,
      paymentQualification,
      runtime_errors: {
        console: evidence.console,
        pageerror: evidence.pageerror,
        failed: evidence.failed,
        mutations: evidence.mutations,
        systemInitPolicy: evidence.systemInitPolicy,
      },
      screenshot: { path: screenshot, sha256: sha256(screenshot) },
      ui5Screenshot: { path: ui5ReadonlyScreenshot, sha256: sha256(ui5ReadonlyScreenshot) },
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

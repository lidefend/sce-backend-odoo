#!/usr/bin/env node
'use strict';

import fs from 'node:fs';
import path from 'node:path';
import { successfulIntentData } from './frontend_authenticated_intent.mjs';

const BASE_URL = String(process.env.SC_CLOSE_03_BASE_URL || 'http://127.0.0.1:18081/t/demo').replace(/\/+$/, '');
const LOGIN = String(process.env.SC_CLOSE_03_LOGIN || 'wutao').trim();
const PASSWORD = String(process.env.SC_CLOSE_03_PASSWORD || '').trim();
const EXPECTED_SHA = String(process.env.SC_CLOSE_03_EXPECTED_SHA || '').trim();
const OUTPUT_DIR = path.resolve(String(
  process.env.SC_CLOSE_03_OUTPUT
    || '.runtime/agent-runs/CLOSE-03-PROJECT-INTAKE-DRAFT-RESTORE-20261119/intake_autosave_samples',
));

const ENTRIES = {
  intake: {
    key: 'project_intake',
    module: 'smart_construction_core',
    menu: 'menu_sc_project_initiation',
    action: 'action_project_initiation',
    model: 'project.project',
    sceneKey: 'projects.intake',
    intakeMode: 'standard',
  },
  record: {
    key: 'project_record',
    module: 'smart_construction_core',
    menu: 'menu_sc_project_project',
    action: 'action_sc_project_list',
    model: 'project.project',
  },
  payment: {
    key: 'payment_create',
    module: 'smart_construction_core',
    menu: 'menu_sc_user_payment_apply',
    action: 'action_payment_request_user_payment_apply',
    model: 'payment.request',
  },
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function writeJson(relativePath, value) {
  const target = path.join(OUTPUT_DIR, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, JSON.stringify(value, null, 2), 'utf8');
  return path.relative(OUTPUT_DIR, target).split(path.sep).join('/');
}

function acceptanceEntryHeaders() {
  const identityPath = path.resolve('config/acceptance/isolated_entry_identity.v1.env');
  const values = {};
  for (const line of fs.readFileSync(identityPath, 'utf8').split(/\r?\n/)) {
    const clean = line.trim();
    if (!clean || clean.startsWith('#') || !clean.includes('=')) continue;
    const [key, ...rest] = clean.split('=');
    values[key.trim()] = rest.join('=').trim();
  }
  return {
    'X-SC-Namespace': values.SC_ENTRY_NAMESPACE || '',
    'X-SC-Audience': values.SC_ENTRY_AUDIENCE || '',
    'X-SC-Entry-Secret': values.SC_ENTRY_SHARED_SECRET || '',
    'X-SC-Route-Version': values.SC_ENTRY_ROUTE_VERSION || '',
  };
}

async function createDirectTransport() {
  const entryHeaders = acceptanceEntryHeaders();
  assert(Object.values(entryHeaders).every(Boolean), 'acceptance entry identity is incomplete');
  let token = '';

  const post = async (payload, anonymous = false) => {
    const response = await fetch(`${BASE_URL}/api/v1/intent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...entryHeaders,
        ...(anonymous ? { 'X-Anonymous-Intent': 'true' } : {}),
        ...(!anonymous && token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });
    return { status: response.status, body: await response.json() };
  };

  const login = await post({
    intent: 'login',
    params: { login: LOGIN, password: PASSWORD, contract_mode: 'default' },
  }, true);
  const loginData = success(login, 'login');
  token = String(loginData?.session?.token || loginData?.token || '').trim();
  assert(token, 'login did not issue a token');

  const replayIntent = async (_context, intent, params) => post({
    intent,
    params,
    context: { lang: 'zh_CN', tz: 'Asia/Shanghai' },
  });
  const getRuntime = async () => {
    const response = await fetch(`${BASE_URL}/api/runtime-version`, { headers: entryHeaders });
    assert(response.ok, `runtime-version rejected (HTTP ${response.status})`);
    return response.json();
  };
  return { replayIntent, getRuntime };
}

function unwrap(body) {
  return body?.data || body?.result || body;
}

function success(result, label) {
  return successfulIntentData(result.status, result.body, label);
}

async function stage(label, promise) {
  try {
    return await promise;
  } catch (error) {
    throw new Error(`${label}: ${error?.message || error}`);
  }
}

function walkNav(nodes, rows = []) {
  if (!Array.isArray(nodes)) return rows;
  for (const node of nodes) {
    if (!node || typeof node !== 'object') continue;
    const meta = node.meta && typeof node.meta === 'object' ? node.meta : {};
    rows.push({
      menuId: Number(node.menu_id || node.id || meta.menu_id || 0),
      actionId: Number(node.action_id || meta.action_id || node.action?.id || 0),
      xmlid: String(node.xmlid || node.menu_xmlid || meta.xmlid || meta.menu_xmlid || ''),
      model: String(node.model || meta.model || node.res_model || ''),
    });
    walkNav(node.children, rows);
  }
  return rows;
}

function findEntryIdentities(value, menuXmlid) {
  const rows = [];
  const visit = (candidate) => {
    if (Array.isArray(candidate)) {
      candidate.forEach(visit);
      return;
    }
    if (!candidate || typeof candidate !== 'object') return;
    const compatibility = candidate.entry_target?.compatibility_refs || {};
    const declaredMenu = String(candidate.menu_xmlid || candidate.menu_key || '').trim();
    if (declaredMenu === menuXmlid) {
      rows.push({
        menuId: Number(candidate.menu_id || candidate.config_menu_id || compatibility.menu_id || 0),
        actionId: Number(candidate.action_id || compatibility.action_id || 0),
        menuXmlid: declaredMenu,
        actionXmlid: String(candidate.action_xmlid || compatibility.action_xmlid || '').trim(),
        model: String(candidate.model || candidate.res_model || '').trim(),
      });
    }
    Object.values(candidate).forEach(visit);
  };
  visit(value);
  return rows;
}

function policyOf(contract) {
  return contract?.runtimeContract?.intakeAutosave || {};
}

function assertPolicy(policy, key) {
  assert(policy.enabled === true, `${key}: intake autosave is not enabled`);
  assert(policy.schemaVersion === 'intake_autosave_policy.v1', `${key}: schema version missing`);
  assert(policy.policyVersion === 1, `${key}: policy version mismatch`);
  assert(Array.isArray(policy.appliesTo) && policy.appliesTo.length === 1 && policy.appliesTo[0] === 'create', `${key}: appliesTo is not create-only`);
  assert(policy.scope === 'project_intake_standard', `${key}: unexpected scope ${policy.scope}`);
  assert(policy.storage?.kind === 'browser_local_storage', `${key}: storage kind missing`);
  assert(Number(policy.storage?.payloadVersion || 0) > 0, `${key}: payload version missing`);
  assert(policy.retention?.seconds === 86400, `${key}: retention must be 24 hours`);
  assert(policy.retention?.basis === 'last_valid_input', `${key}: retention basis mismatch`);
  assert(policy.recovery?.strategy === 'prompt_restore_or_discard', `${key}: recovery strategy mismatch`);
  assert(Array.isArray(policy.fields) && policy.fields.length > 0, `${key}: allowed fields missing`);
  assert(policy.fields.every((field) => (
    field.name
    && field.type
    && field.inputKind
    && field.readonly === false
    && field.allowEmpty === true
    && field.source === 'effective_create_form'
    && field.constraints
    && typeof field.constraints === 'object'
  )), `${key}: allowed field declaration incomplete`);
  assert(policy.coverage?.fields === true, `${key}: field coverage missing`);
  for (const excluded of ['attachments', 'binary', 'unsavedChildRecords', 'workflowState', 'serverDefaults']) {
    assert(policy.coverage?.[excluded] === false, `${key}: unsupported ${excluded} is included`);
  }
  assert(
    policy.fields.some((field) => field.name === 'name' && field.inputKind === 'text'),
    `${key}: required text input is absent`,
  );
  assert(
    policy.fields.some((field) => field.inputKind === 'relation' && field.relation),
    `${key}: relation input is absent`,
  );
}

function assertNoPolicy(contract, key) {
  const policy = policyOf(contract);
  assert(!policy?.enabled, `${key}: unexpectedly enables intake autosave`);
}

function createParams(entry, identity) {
  return {
    op: 'model',
    model: entry.model,
    view_type: 'form',
    render_profile: 'create',
    scene_key: entry.sceneKey || undefined,
    action_id: identity.actionId,
    menu_id: identity.menuId,
    client_type: 'web_pc',
    delivery_profile: 'full',
    contract_surface: 'user',
    source_mode: 'governance_pipeline',
    context: entry.intakeMode ? { intake_mode: entry.intakeMode } : undefined,
  };
}

function minimalCreateValues(policy, actorId) {
  const values = {};
  for (const field of policy.fields || []) {
    if (field.inputKind === 'relation' && field.relation === 'res.users' && actorId > 0) {
      values[field.name] = actorId;
      continue;
    }
    if (!field.required) continue;
    if (field.inputKind === 'text') values[field.name] = field.name === 'name' ? 'CLOSE-03 project intake' : '';
    else if (field.inputKind === 'date') values[field.name] = new Date().toISOString().slice(0, 10);
    else if (field.inputKind === 'datetime') values[field.name] = new Date().toISOString().slice(0, 19);
    else if (field.inputKind === 'selection') values[field.name] = field.constraints?.allowedValues?.[0] || '';
    else if (field.inputKind === 'integer') values[field.name] = 0;
    else if (field.inputKind === 'decimal') values[field.name] = 0;
    else if (field.inputKind === 'boolean') values[field.name] = false;
  }
  return values;
}

async function main() {
  assert(PASSWORD, 'SC_CLOSE_03_PASSWORD is required');
  fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const assertions = [];
  const check = (name, condition, detail = '') => {
    assertions.push({ name, status: condition ? 'passed' : 'failed', detail: String(detail || '') });
    assert(condition, `${name}${detail ? `: ${detail}` : ''}`);
  };

  {
    const { replayIntent, getRuntime } = await createDirectTransport();
    const context = null;
    const { status: systemStatus, body: systemBody } = await replayIntent(context, 'system.init', {
      scene: 'web',
      with_preload: false,
      scene_ready_mode: 'registry',
      with: ['workspace_home'],
    });
    const systemData = success({ status: systemStatus, body: systemBody }, 'system.init');
    const runtime = await getRuntime();
    const servedSha = String(runtime.git_sha || runtime.source_revision || '').trim();
    if (servedSha && EXPECTED_SHA) check('runtime_source_sha', servedSha === EXPECTED_SHA, `${servedSha} != ${EXPECTED_SHA}`);
    const actor = systemData?.user || {};
    const recordContext = systemData?.record_context || {};
    const navRows = walkNav(systemData?.navigation?.nav || []);
    writeJson('system.init.json', systemData);

    async function resolve(entry) {
      const menuXmlid = `${entry.module}.${entry.menu}`;
      const actionXmlid = `${entry.module}.${entry.action}`;
      const nav = navRows.find((row) => row.xmlid === menuXmlid) || {};
      const declared = findEntryIdentities(systemData, menuXmlid)
        .find((row) => row.menuId > 0 && row.actionId > 0) || {};
      const menuId = Number(nav.menuId || declared.menuId || 0);
      const actionId = Number(nav.actionId || declared.actionId || 0);
      check(`${entry.key}.menu_resolved`, menuId > 0, menuId);
      check(`${entry.key}.action_resolved`, actionId > 0, actionId);
      check(
        `${entry.key}.action_identity`,
        !declared.actionXmlid || declared.actionXmlid === actionXmlid,
        declared.actionXmlid,
      );
      return { menuId, actionId, menuXmlid, actionXmlid };
    }

    const intakeIdentity = await resolve(ENTRIES.intake);
    writeJson('project_intake/identity.json', intakeIdentity);
    const intakeParams = createParams(ENTRIES.intake, intakeIdentity);
    const { status: intakeStatus, body: intakeBody } = await stage(
      'project_intake.contract',
      replayIntent(context, 'ui.contract.v2', intakeParams),
    );
    const intakeContract = success({ status: intakeStatus, body: intakeBody }, 'project_intake.ui.contract.v2');
    const intakePolicy = policyOf(intakeContract);
    assertPolicy(intakePolicy, 'project_intake');
    check('project_intake.model', intakeContract?.pageInfo?.model === 'project.project', intakeContract?.pageInfo?.model || '');
    check('project_intake.render_profile', intakeContract?.statusContract?.globalStatus?.effectiveRenderProfile === 'create');
    const minimalValues = minimalCreateValues(intakePolicy, Number(actor.id || 0));
    check('project_intake.minimal_name', Boolean(minimalValues.name), JSON.stringify(minimalValues));
    check('project_intake.minimal_relation', Object.values(minimalValues).some((value) => Number(value) > 0), JSON.stringify(minimalValues));

    const { status: projectStatus, body: projectBody } = await replayIntent(context, 'api.data', {
      op: 'list',
      model: 'project.project',
      fields: ['id', 'name'],
      domain: [],
      limit: 1,
      order: 'id asc',
    });
    const projectData = success({ status: projectStatus, body: projectBody }, 'project.list');
    const projectId = Number(projectData?.records?.[0]?.id || 0);
    check('project_record.id_resolved', projectId > 0, projectId);
    const recordIdentity = await resolve(ENTRIES.record);
    writeJson('project_record/identity.json', recordIdentity);
    const { status: recordStatus, body: recordBody } = await stage('project_record.contract', replayIntent(context, 'ui.contract.v2', {
      op: 'action_open',
      action_id: recordIdentity.actionId,
      menu_id: recordIdentity.menuId,
      record_id: projectId,
      view_type: 'form',
      render_profile: 'edit',
      client_type: 'web_pc',
      delivery_profile: 'full',
      contract_surface: 'user',
      source_mode: 'governance_pipeline',
    }));
    const recordContract = success({ status: recordStatus, body: recordBody }, 'project_record.ui.contract.v2');
    assertNoPolicy(recordContract, 'project_record');

    const paymentIdentity = await resolve(ENTRIES.payment);
    writeJson('payment_create/identity.json', paymentIdentity);
    const paymentParams = createParams(ENTRIES.payment, paymentIdentity);
    const { status: paymentStatus, body: paymentBody } = await stage(
      'payment_create.contract',
      replayIntent(context, 'ui.contract.v2', paymentParams),
    );
    const paymentContract = success({ status: paymentStatus, body: paymentBody }, 'payment_create.ui.contract.v2');
    assertNoPolicy(paymentContract, 'payment_create');

    const contracts = {
      project_intake: writeJson('project_intake/contract.envelope.json', intakeBody),
      project_record: writeJson('project_record/contract.envelope.json', recordBody),
      payment_create: writeJson('payment_create/contract.envelope.json', paymentBody),
    };
    writeJson('project_intake/create.request.json', { intent: 'ui.contract.v2', params: intakeParams });
    writeJson('project_intake/minimal_create_values.json', minimalValues);
    writeJson('project_record/identity.json', { projectId });
    writeJson('system.init.json', systemData);

    const summary = {
      schema: 'close_03.intake_autosave_samples.v1',
      generated_at: new Date().toISOString(),
      base_url: BASE_URL,
      expected_source_sha: EXPECTED_SHA || null,
      served_sha: servedSha || null,
      runtime,
      actor: {
        id: Number(actor.id || 0),
        login: String(actor.login || LOGIN),
        company_id: Number(recordContext.company_id || 0),
        company_name: String(recordContext.company_name || ''),
      },
      entries: {
        project_intake: {
          menu_xmlid: `${ENTRIES.intake.module}.${ENTRIES.intake.menu}`,
          action_xmlid: `${ENTRIES.intake.module}.${ENTRIES.intake.action}`,
          menu_id: intakeIdentity.menuId,
          action_id: intakeIdentity.actionId,
          model: ENTRIES.intake.model,
          policy: intakePolicy,
          minimal_create_values: minimalValues,
          contract_path: contracts.project_intake,
        },
        project_record: {
          menu_xmlid: `${ENTRIES.record.module}.${ENTRIES.record.menu}`,
          action_xmlid: `${ENTRIES.record.module}.${ENTRIES.record.action}`,
          menu_id: recordIdentity.menuId,
          action_id: recordIdentity.actionId,
          model: ENTRIES.record.model,
          record_id: projectId,
          intake_autosave: policyOf(recordContract),
          contract_path: contracts.project_record,
        },
        payment_create: {
          menu_xmlid: `${ENTRIES.payment.module}.${ENTRIES.payment.menu}`,
          action_xmlid: `${ENTRIES.payment.module}.${ENTRIES.payment.action}`,
          menu_id: paymentIdentity.menuId,
          action_id: paymentIdentity.actionId,
          model: ENTRIES.payment.model,
          intake_autosave: policyOf(paymentContract),
          contract_path: contracts.payment_create,
        },
      },
      assertions,
      summary: { status: 'PASS', assertion_count: assertions.length },
    };
    const summaryPath = writeJson('summary.json', summary);
    process.stdout.write(`[close-03-intake-samples] PASS assertions=${assertions.length} summary=${summaryPath}\n`);
  }
}

main().catch((error) => {
  process.stderr.write(`[close-03-intake-samples] FAIL ${error?.message || error}\n`);
  process.exitCode = 1;
});

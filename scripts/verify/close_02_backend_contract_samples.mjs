#!/usr/bin/env node
'use strict';

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import {
  authenticateBrowserProbe,
  fillLoginCredentials,
  successfulIntentData,
} from './frontend_authenticated_intent.mjs';

const requireBase = fs.existsSync(path.join(process.cwd(), 'frontend/apps/web/package.json'))
  ? path.join(process.cwd(), 'frontend/apps/web/package.json')
  : path.join(process.cwd(), 'package.json');
const { chromium } = createRequire(requireBase)('playwright');

const BASE_URL = String(process.env.SC_CLOSE_02_BASE_URL || 'http://127.0.0.1:18081/t/demo').replace(/\/+$/, '');
const LOGIN = String(process.env.SC_CLOSE_02_LOGIN || 'wutao').trim();
const PASSWORD = String(process.env.SC_CLOSE_02_PASSWORD || '').trim();
const EXPECTED_SHA = String(process.env.SC_CLOSE_02_EXPECTED_SHA || '').trim();
const ENTRY_FILTER = String(process.env.SC_CLOSE_02_ENTRY || '').trim();
const TRANSPORT = String(process.env.SC_CLOSE_02_TRANSPORT || 'browser').trim().toLowerCase();
const OUTPUT_DIR = path.resolve(String(
  process.env.SC_CLOSE_02_OUTPUT
    || '.runtime/agent-runs/CLOSE-02-FIELD-QUERY-SORT-DETAIL-20261118/search_contract_samples',
));

const ENTRIES = [
  {
    key: 'project_ledger',
    label: '项目台账',
    module: 'smart_construction_core',
    menu: 'menu_sc_project_project',
    action: 'action_sc_project_list',
    model: 'project.project',
    resolutionKey: 'project',
  },
  {
    key: 'payment_request',
    label: '付款申请',
    module: 'smart_construction_core',
    menu: 'menu_sc_user_payment_apply',
    action: 'action_payment_request_user_payment_apply',
    model: 'payment.request',
    resolutionKey: 'payment_request',
  },
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function writeJson(relativePath, value) {
  const target = path.join(OUTPUT_DIR, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, JSON.stringify(value, null, 2), 'utf8');
  return path.relative(OUTPUT_DIR, target).split(path.sep).join('/');
}

function unwrap(body) {
  return body?.data || body?.result || body;
}

function intentData(result, label) {
  try {
    return successfulIntentData(result.status, result.body, label);
  } catch {
    const error = result.body?.error && typeof result.body.error === 'object' ? result.body.error : {};
    throw new Error(
      `${label}: rejected status=${result.status} code=${String(error.code || result.body?.code || '').trim()} `
      + `reason=${String(error.reason_code || '').trim()}`,
    );
  }
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
      id: Number(node.id || node.menu_id || meta.menu_id || 0),
      menu_id: Number(node.menu_id || node.id || meta.menu_id || 0),
      action_id: Number(node.action_id || meta.action_id || node.action?.id || 0),
      xmlid: String(node.xmlid || node.menu_xmlid || meta.xmlid || meta.menu_xmlid || ''),
      model: String(node.model || meta.model || node.res_model || ''),
    });
    walkNav(node.children, rows);
  }
  return rows;
}

function findEntryIdentities(value, menuXmlid, rows = []) {
  if (Array.isArray(value)) {
    for (const item of value) findEntryIdentities(item, menuXmlid, rows);
    return rows;
  }
  if (!value || typeof value !== 'object') return rows;
  const compatibility = value.entry_target?.compatibility_refs || {};
  if (value.menu_xmlid === menuXmlid || value.menu_key === menuXmlid) {
    rows.push({
      menu_id: Number(value.menu_id || value.config_menu_id || compatibility.menu_id || 0),
      action_id: Number(value.action_id || compatibility.action_id || 0),
      menu_xmlid: String(value.menu_xmlid || value.menu_key || ''),
      action_xmlid: String(value.action_xmlid || compatibility.action_xmlid || ''),
      state: String(value.route_kind || value.state || value.authority?.state || ''),
      route: String(value.route || value.entry_target?.route || ''),
      source: String(value.source || ''),
    });
  }
  for (const child of Object.values(value)) findEntryIdentities(child, menuXmlid, rows);
  return rows;
}

function readResolutionHint(entry) {
  const resolutionPath = path.resolve('artifacts/backend/acceptance_record_identity.json');
  if (!fs.existsSync(resolutionPath)) return null;
  const body = JSON.parse(fs.readFileSync(resolutionPath, 'utf8'));
  const target = body?.targets?.[entry.resolutionKey];
  if (!target || target.menu_xmlid !== entry.xmlids.menu || target.action_xmlid !== entry.xmlids.action) {
    return null;
  }
  return {
    path: path.relative(process.cwd(), resolutionPath).split(path.sep).join('/'),
    schema: String(body.schema || ''),
    producer: String(body.producer || ''),
    hint_expected_sha: String(body.expected_sha || ''),
    menu_id: Number(target.menu_id || 0),
    action_id: Number(target.action_id || 0),
    menu_xmlid: String(target.menu_xmlid || ''),
    action_xmlid: String(target.action_xmlid || ''),
    model: String(target.model || ''),
  };
}

function recordValueId(value) {
  if (Array.isArray(value)) return Number(value[0] || 0);
  if (value && typeof value === 'object') return Number(value.id || value.res_id || 0);
  return Number(value || 0);
}

function recordValueText(value) {
  if (Array.isArray(value)) return String(value[1] || value[0] || '').trim();
  if (value && typeof value === 'object') return String(value.display_name || value.name || value.label || value.id || '').trim();
  return String(value ?? '').trim();
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function acceptanceEntryHeaders() {
  const values = {};
  const identityPath = path.resolve('config/acceptance/isolated_entry_identity.v1.env');
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
  let startupPayload = null;

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
  const loginData = intentData(login, 'login');
  token = String(loginData?.session?.token || loginData?.token || '').trim();
  assert(token, 'login did not issue a token');

  startupPayload = {
    intent: 'system.init',
    params: { scene: 'web', with_preload: false, scene_ready_mode: 'registry', with: ['workspace_home'] },
    context: { lang: 'zh_CN', tz: 'Asia/Shanghai' },
  };
  const system = await post(startupPayload);
  intentData(system, 'system.init');

  const replayIntent = async (_context, intent, params) => {
    const result = await post({ ...startupPayload, intent, params });
    intentData(result, intent);
    return [result.status, result.body];
  };
  replayIntent.startupData = startupPayload;
  return {
    replayIntent,
    systemResult: system,
    async runtimeVersion() {
      const response = await fetch(`${BASE_URL}/api/runtime-version`, { headers: entryHeaders });
      assert(response.ok, `runtime-version status=${response.status}`);
      return await response.json();
    },
    async close() {},
  };
}

function flattenDomain(value) {
  return Array.isArray(value) ? value : [];
}

function pageFields(primary, conditionFields = []) {
  const base = Array.isArray(primary?.params?.fields) ? primary.params.fields.map(String) : [];
  return unique(['id', ...base, ...conditionFields]).slice(0, 80);
}

function requestParams(entry, primary, domain, { offset = 0, limit = 20, fields = [], order = '' } = {}) {
  const params = {
    ...(primary?.params && typeof primary.params === 'object' ? primary.params : {}),
    op: 'list',
    model: entry.model,
    action_id: entry.action_id,
    menu_id: entry.menu_id,
    fields: unique(['id', ...fields]).slice(0, 80),
    domain: flattenDomain(domain),
    limit,
    offset,
    need_total: true,
  };
  if (order) params.order = order;
  if (!primary?.params?.domain_raw) delete params.domain_raw;
  return params;
}

async function main() {
  assert(PASSWORD, 'SC_CLOSE_02_PASSWORD is required');
  fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  let browser = null;
  let context = null;
  let direct = null;
  const assertions = [];
  const check = (name, condition, detail = '') => {
    assertions.push({ name, status: condition ? 'passed' : 'failed', detail });
    assert(condition, `${name}${detail ? `: ${detail}` : ''}`);
  };

  try {
    let replayIntent;
    let systemResult;
    let runtimeResponse;
    if (TRANSPORT === 'http') {
      direct = await createDirectTransport();
      replayIntent = direct.replayIntent;
      systemResult = direct.systemResult;
      runtimeResponse = await direct.runtimeVersion();
    } else {
      browser = await chromium.launch({ headless: true });
      context = await browser.newContext({ baseURL: BASE_URL });
      const page = await context.newPage();
      await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
      replayIntent = await authenticateBrowserProbe(
        page,
        LOGIN,
        async () => fillLoginCredentials(page, LOGIN, PASSWORD).then(
          () => page.locator('button[type="submit"]').first().click(),
        ),
      );
      systemResult = await stage(
        'system.init',
        replayIntent(context, 'system.init', replayIntent.startupData?.params || {}),
      );
      runtimeResponse = await context.request.get(`${BASE_URL}/api/runtime-version`);
      runtimeResponse = await runtimeResponse.json();
    }
    const systemData = intentData(systemResult, 'system.init');

    const runtimeBody = runtimeResponse;
    const servedSha = String(runtimeBody.git_sha || runtimeBody.source_revision || '').trim();
    if (servedSha && servedSha !== 'unknown' && EXPECTED_SHA) {
      check('runtime_source_sha', servedSha === EXPECTED_SHA, `${servedSha} != ${EXPECTED_SHA}`);
    } else {
      assertions.push({
        name: 'runtime_source_sha',
        status: 'observed_unknown',
        detail: 'served runtime does not expose a SHA; source mount identity is recorded from the worktree',
      });
    }

    const navRows = walkNav(systemData?.navigation?.nav || []);
    const recordContext = systemData?.record_context || {};
    const actor = systemData?.user || {};
    writeJson('system.init.json', systemData);

    const summary = {
      schema: 'close_02.backend_search_contract_samples.v1',
      generated_at: new Date().toISOString(),
      base_url: BASE_URL,
      expected_source_sha: EXPECTED_SHA || null,
      served_sha: servedSha || null,
      runtime: runtimeBody,
      database: String(runtimeBody.database || ''),
      actor: {
        id: Number(actor.id || 0),
        login: String(actor.login || LOGIN),
        company_id: Number(recordContext.company_id || 0),
        company_name: String(recordContext.company_name || ''),
        role_codes: recordContext.role_codes || recordContext.roles || [],
      },
      record_context: recordContext,
      entries: [],
      assertions,
    };

    for (const declaration of ENTRIES.filter((entry) => !ENTRY_FILTER || entry.key === ENTRY_FILTER)) {
      const entry = {
        ...declaration,
        xmlids: {
          menu: `${declaration.module}.${declaration.menu}`,
          action: `${declaration.module}.${declaration.action}`,
        },
      };
      const nav = navRows.find((row) => row.xmlid === entry.xmlids.menu) || {};
      const identity = findEntryIdentities(systemData, entry.xmlids.menu)
        .find((row) => row.menu_id > 0 && row.action_id > 0) || {};
      const resolutionHint = readResolutionHint(entry);
      let actionId = Number(nav.action_id || identity.action_id || resolutionHint?.action_id || 0);
      let menuId = Number(nav.menu_id || identity.menu_id || resolutionHint?.menu_id || 0);

      if (!actionId || !menuId) {
        const lookup = await stage(`${entry.key}.xmlid_lookup`, replayIntent(context, 'api.data', {
          op: 'list',
          model: 'ir.model.data',
          fields: ['module', 'name', 'res_id'],
          domain: [
            ['module', '=', declaration.module],
            ['name', 'in', [declaration.menu, declaration.action]],
          ],
          limit: 10,
        }));
        const rows = intentData(lookup, 'ir.model.data').records || [];
        const byName = new Map(rows.map((row) => [String(row.name), Number(row.res_id || 0)]));
        menuId = menuId || Number(byName.get(declaration.menu) || 0);
        actionId = actionId || Number(byName.get(declaration.action) || 0);
      }
      check(`${entry.key}.menu_resolved`, menuId > 0, String(menuId));
      check(`${entry.key}.action_resolved`, actionId > 0, String(actionId));
      check(
        `${entry.key}.declared_entry_identity`,
        (
          identity.menu_xmlid === entry.xmlids.menu
          && identity.action_xmlid === entry.xmlids.action
        ) || (
          resolutionHint?.menu_xmlid === entry.xmlids.menu
          && resolutionHint?.action_xmlid === entry.xmlids.action
          && resolutionHint?.model === entry.model
        ),
        JSON.stringify(identity.menu_xmlid ? identity : resolutionHint),
      );
      entry.menu_id = menuId;
      entry.action_id = actionId;
      entry.navigation = nav;
      entry.declared_route = identity;
      entry.resolution_hint = resolutionHint;

      const [contractStatus, contractBody] = await stage(`${entry.key}.contract`, replayIntent(context, 'ui.contract.v2', {
        op: 'action_open',
        action_id: actionId,
        menu_id: menuId,
        client_type: 'web_pc',
        delivery_profile: 'full',
      }));
      check(`${entry.key}.contract_http`, contractStatus === 200);
      const contract = intentData({ status: contractStatus, body: contractBody }, 'ui.contract.v2');
      const primary = contract?.dataContract?.dataSource?.primary || {};
      const primaryOrder = String(primary?.params?.order || '').trim();
      const pageSize = Math.max(1, Math.min(200, Number(primary?.params?.limit || 20)));
      const baseDomain = flattenDomain(primary?.params?.domain);
      const contractFields = Array.isArray(contract?.searchContract?.fields) ? contract.searchContract.fields : [];
      const filters = Array.isArray(contract?.searchContract?.filters) ? contract.searchContract.filters : [];

      check(`${entry.key}.primary_order`, Boolean(primaryOrder), primaryOrder);
      check(
        `${entry.key}.search_defaults_order`,
        String(contract?.searchContract?.defaults?.order || '').trim() === primaryOrder,
        String(contract?.searchContract?.defaults?.order || ''),
      );
      check(`${entry.key}.native_fields`, contractFields.length > 0, String(contractFields.length));
      check(
        `${entry.key}.field_semantics`,
        contractFields.every((row) => row?.field && row?.type && row?.operator && Array.isArray(row?.operators)),
        JSON.stringify(contractFields.map((row) => row?.field || '')),
      );
      check(
        `${entry.key}.field_occurrences`,
        contractFields.every((row) => row?.occurrence_key && row?.native_locator),
      );
      if (declaration.model === 'payment.request') {
        check(`${entry.key}.entry_scope`, baseDomain.length > 0, JSON.stringify(baseDomain));
      }

      const textFields = contractFields
        .filter((row) => ['char', 'text', 'html'].includes(String(row.type)))
        .slice(0, 6);
      const relationFields = contractFields
        .filter((row) => String(row.type) === 'many2one')
        .slice(0, 6);
      check(`${entry.key}.text_field_declared`, textFields.length > 0);
      check(`${entry.key}.relation_field_declared`, relationFields.length > 0);

      const baseFields = pageFields(primary, [
        ...textFields.map((row) => String(row.field)),
        ...relationFields.map((row) => String(row.field)),
      ]);
      const baseRequest = requestParams(entry, primary, baseDomain, {
        fields: baseFields,
        limit: Math.min(200, Math.max(40, pageSize * 4)),
        order: primaryOrder,
      });
      const [baseStatus, baseBody] = await stage(
        `${entry.key}.base_list`,
        replayIntent(context, 'api.data', baseRequest),
      );
      const baseResult = { status: baseStatus, body: baseBody };
      const baseData = intentData(baseResult, `api.data:base:${entry.key}`);
      const baseRows = Array.isArray(baseData.records) ? baseData.records : [];
      const baseTotal = Number(baseData.total || 0);
      check(`${entry.key}.base_records`, baseRows.length > 0, String(baseRows.length));
      check(`${entry.key}.base_total`, baseTotal > pageSize, `${baseTotal} <= ${pageSize}`);

      const textCandidates = [];
      for (const row of baseRows.slice(0, 80)) {
        for (const field of textFields) {
          const value = recordValueText(row[field.field]);
          if (!value) continue;
          for (const token of value.split(/[\s/|,，;；()（）_-]+/).filter(Boolean)) {
            for (let size = 1; size <= Math.min(6, token.length); size += 1) {
              textCandidates.push({ row: field, value: token.slice(0, size) });
            }
          }
        }
      }

      const relationCounts = new Map();
      for (const field of relationFields) {
        for (const row of baseRows) {
          const value = recordValueId(row[field.field]);
          if (!value) continue;
          const key = `${field.field}:${value}`;
          const current = relationCounts.get(key) || { row: field, value, count: 0 };
          current.count += 1;
          relationCounts.set(key, current);
        }
      }
      const relationCandidates = [...relationCounts.values()].sort((a, b) => b.count - a.count).slice(0, 20);

      async function bestCandidate(candidates, field) {
        let best = null;
        const seen = new Set();
        for (const candidate of candidates) {
          const key = `${candidate.row.field}:${String(candidate.value)}`;
          if (seen.has(key)) continue;
          seen.add(key);
          const conditionDomain = [[candidate.row.field, candidate.row.operator || field.operator || '=', candidate.value]];
          const params = requestParams(entry, primary, [...baseDomain, ...conditionDomain], {
            fields: pageFields(primary, [candidate.row.field]),
            limit: 1,
            order: primaryOrder,
          });
          const [status, body] = await stage(
            `${entry.key}.candidate.${candidate.row.field}`,
            replayIntent(context, 'api.data', params),
          );
          const result = { status, body };
          const data = intentData(result, `api.data:candidate:${entry.key}:${candidate.row.field}`);
          const total = Number(data.total || 0);
          if (!best || total > best.total) best = { ...candidate, params, total };
          if (total > pageSize) break;
        }
        return best;
      }

      const textHit = await bestCandidate(textCandidates, textFields[0]);
      check(`${entry.key}.text_hit_over_page`, Boolean(textHit && textHit.total > pageSize), JSON.stringify(textHit && {
        field: textHit.row.field,
        value: textHit.value,
        total: textHit.total,
      }));

      const relationHit = await bestCandidate(relationCandidates, relationFields[0]);
      check(`${entry.key}.relation_hit_over_page`, Boolean(relationHit && relationHit.total > pageSize), JSON.stringify(relationHit && {
        field: relationHit.row.field,
        value: relationHit.value,
        total: relationHit.total,
      }));

      const filterConditions = filters.slice(0, 12).map((row) => ({
        row,
        domain: flattenDomain(row.domain),
        raw: String(row.domain_raw || '').trim(),
      })).filter((row) => row.domain.length || row.raw);
      let filterHit = null;
      for (const candidate of filterConditions) {
        const condition = candidate.domain.length ? candidate.domain : [];
        if (!condition.length && candidate.raw) {
          // Filter raw is kept as evidence below, but the normalized domain is the
          // declared executable form. A parser-free consumer must not guess it.
          continue;
        }
        const params = requestParams(entry, primary, [...baseDomain, ...condition], {
          fields: pageFields(primary),
          limit: 1,
          order: primaryOrder,
        });
        const [status, body] = await stage(
          `${entry.key}.filter.${candidate.row.key}`,
          replayIntent(context, 'api.data', params),
        );
        const result = { status, body };
        const data = intentData(result, `api.data:filter:${entry.key}:${candidate.row.key}`);
        const total = Number(data.total || 0);
        if (!filterHit || total > filterHit.total) filterHit = { ...candidate, params, total };
        if (total > pageSize) break;
      }
      check(`${entry.key}.existing_filter_over_page`, Boolean(filterHit && filterHit.total > pageSize), JSON.stringify(filterHit && {
        key: filterHit.row.key,
        total: filterHit.total,
      }));

      async function executeQuery(sampleKey, conditionDomain, { offset = 0, limit = pageSize } = {}) {
        const params = requestParams(entry, primary, [...baseDomain, ...conditionDomain], {
          fields: pageFields(primary, conditionDomain.map((leaf) => String(leaf?.[0] || '')).filter(Boolean)),
          offset,
          limit,
          order: primaryOrder,
        });
        const [status, body] = await stage(
          `${entry.key}.${sampleKey}`,
          replayIntent(context, 'api.data', params),
        );
        const result = { status, body };
        const data = intentData(result, `api.data:${sampleKey}:${entry.key}`);
        const requestPath = writeJson(`${entry.key}/${sampleKey}.request.json`, params);
        const responsePath = writeJson(`${entry.key}/${sampleKey}.response.json`, result.body);
        return { params, result, data, requestPath, responsePath };
      }

      const textHitPage = await executeQuery('text_hit_page_1', [[textHit.row.field, textHit.row.operator, textHit.value]]);
      const textSecondPage = await executeQuery('text_hit_page_2', [[textHit.row.field, textHit.row.operator, textHit.value]], { offset: pageSize });
      const relationPage = await executeQuery('relation_hit_page_1', [[relationHit.row.field, relationHit.row.operator, relationHit.value]]);
      const filterPage = await executeQuery('existing_filter_page_1', flattenDomain(filterHit.row.domain));
      const zeroValue = textHit.row.operator === 'ilike' ? '__close02_no_match__' : 'CLOSE02-NO-MATCH';
      const zeroPage = await executeQuery('valid_zero_result', [[textHit.row.field, textHit.row.operator, zeroValue]]);

      const firstIds = (textHitPage.data.records || []).map((row) => Number(row.id || 0));
      const secondIds = (textSecondPage.data.records || []).map((row) => Number(row.id || 0));
      check(`${entry.key}.second_page`, secondIds.length > 0, String(secondIds.length));
      check(`${entry.key}.page_identity`, firstIds.every((id) => !secondIds.includes(id)));
      check(`${entry.key}.zero_result`, Number(zeroPage.data.total || 0) === 0, String(zeroPage.data.total || 0));
      check(`${entry.key}.hit_total`, Number(textHitPage.data.total || 0) >= Number(textHit.total || 0));
      check(`${entry.key}.relation_total`, (relationPage.data.total || 0) > pageSize);
      check(`${entry.key}.filter_total`, (filterPage.data.total || 0) > pageSize);
      check(`${entry.key}.request_order`, textHitPage.result.body?.meta?.order === primaryOrder, String(textHitPage.result.body?.meta?.order || ''));
      check(
        `${entry.key}.scope_not_expanded`,
        Number(textHitPage.data.total || 0) <= baseTotal
          && Number(relationPage.data.total || 0) <= baseTotal
          && Number(filterPage.data.total || 0) <= baseTotal,
      );
      const queryIds = new Set([...firstIds, ...secondIds, ...(relationPage.data.records || []).map((row) => Number(row.id || 0))]);
      const baseIds = new Set(baseRows.map((row) => Number(row.id || 0)));
      check(`${entry.key}.returned_ids_in_scope`, [...queryIds].every((id) => baseIds.has(id)));

      entry.contract_path = writeJson(`${entry.key}/contract.envelope.json`, contractBody);
      entry.base_request_path = writeJson(`${entry.key}/base.request.json`, baseRequest);
      entry.base_response_path = writeJson(`${entry.key}/base.response.json`, baseResult.body);
      entry.effective = {
        menu_xmlid: entry.xmlids.menu,
        action_xmlid: entry.xmlids.action,
        menu_id: menuId,
        action_id: actionId,
        model: declaration.model,
        view_id: contract?.searchContract?.nativeIdentity?.viewId || null,
        view_xmlid: contract?.searchContract?.nativeIdentity?.viewXmlId || '',
        search_authority: contract?.searchContract?.nativeIdentity?.authority || '',
        collection_order: primaryOrder,
        page_size: pageSize,
      };
      entry.search_fields = contractFields.map((row) => ({
        field: row.field,
        key: row.key,
        label: row.label,
        type: row.type,
        relation: row.relation || '',
        operator: row.operator,
        operators: row.operators,
        choices: row.choices || [],
        query_mode: row.query_mode,
        occurrence_key: row.occurrence_key,
        native_locator: row.native_locator,
        occurrence_index: row.occurrence_index,
        filter_domain_raw: row.filter_domain_raw || '',
        domain_raw: row.domain_raw || '',
        context_raw: row.context_raw || '',
        filter_domain_requires_input: row.filter_domain_requires_input === true,
        context_requires_input: row.context_requires_input === true,
      }));
      entry.samples = {
        base: {
          total: baseTotal,
          returned: baseRows.length,
          request: entry.base_request_path,
          response: entry.base_response_path,
        },
        text_hit: {
          field: textHit.row.field,
          operator: textHit.row.operator,
          value: textHit.value,
          total: Number(textHitPage.data.total || 0),
          page_1_ids: firstIds,
          page_2_ids: secondIds,
          page_1_request: textHitPage.requestPath,
          page_1_response: textHitPage.responsePath,
          page_2_request: textSecondPage.requestPath,
          page_2_response: textSecondPage.responsePath,
        },
        relation_hit: {
          field: relationHit.row.field,
          operator: relationHit.row.operator,
          value: relationHit.value,
          total: Number(relationPage.data.total || 0),
          ids: (relationPage.data.records || []).map((row) => Number(row.id || 0)),
          request: relationPage.requestPath,
          response: relationPage.responsePath,
        },
        existing_filter: {
          key: filterHit.row.key,
          label: filterHit.row.label,
          total: Number(filterPage.data.total || 0),
          ids: (filterPage.data.records || []).map((row) => Number(row.id || 0)),
          request: filterPage.requestPath,
          response: filterPage.responsePath,
        },
        zero_result: {
          field: textHit.row.field,
          operator: textHit.row.operator,
          value: zeroValue,
          total: Number(zeroPage.data.total || 0),
          request: zeroPage.requestPath,
          response: zeroPage.responsePath,
        },
      };
      summary.entries.push(entry);
    }

    summary.summary = {
      status: assertions.every((row) => row.status !== 'failed') ? 'PASS' : 'FAIL',
      assertion_count: assertions.length,
      entries: summary.entries.map((entry) => ({
        key: entry.key,
        menu_xmlid: entry.xmlids.menu,
        action_xmlid: entry.xmlids.action,
        model: entry.model,
        menu_id: entry.menu_id,
        action_id: entry.action_id,
        order: entry.effective.collection_order,
        field_count: entry.search_fields.length,
        text_hit_total: entry.samples.text_hit.total,
        relation_hit_total: entry.samples.relation_hit.total,
        filter_total: entry.samples.existing_filter.total,
      })),
    };
    const summaryPath = writeJson('summary.json', summary);
    process.stdout.write(`[close-02-backend-samples] PASS entries=${summary.entries.length} assertions=${assertions.length} summary=${summaryPath}\n`);
  } finally {
    if (direct) await direct.close();
    if (context) await context.close();
    if (browser) await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`[close-02-backend-samples] FAIL ${error?.message || error}\n`);
  process.exitCode = 1;
});

// FE-PERF-01-R0.1B measurement collector (P4, independent of product code).
//
// Purpose: capture the complete page-initialization request set for the four
// governed form scenarios, with per-request start/TTFB/end timing, the five
// cache layers, backend stage timing and raw sample retention. It never writes
// product code, business data, ACLs or cache policy; it only drives the
// registered local.dev browser and records observations under artifacts/.
//
// Scenarios:
//   A_new_payment       create payment.request  (action 880 / menu 559)
//   B_edit_payment      edit   payment.request  (record 1141)
//   C_project_readonly  role-home project detail (record 24, readonly)
//   D_project_edit      project edit form        (record 24, edit)
//
// Cache layers recorded independently per request:
//   browser_http / frontend_create_map / backend_process_source /
//   backend_assembled / runtime_source_asset / warmup

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { launchChromium } from './playwright_runtime.mjs';

const ENTRY = process.env.FE_PERF_ENTRY || 'http://127.0.0.1:18081/t/demo';
const PASS = process.env.SC_DEMO_USER_PASSWORD;
const N = Number(process.env.FE_PERF_N || 20);
const OUT = path.resolve(process.env.FE_PERF_OUT || 'artifacts/fe_perf_r01b');
const ROOT = process.cwd();
const sha = v => crypto.createHash('sha256').update(v).digest('hex');

const safeToken = v => (typeof v === 'string' && /^[a-zA-Z0-9_.:-]{1,120}$/.test(v)) ? v : null;
function requestIdentity(params) {
  const out = {};
  for (const k of ['op','model','view_type','viewType','render_profile','renderProfile','action_id','menu_id','view_id','record_id','scene_key','sceneKey','source_mode','sourceMode','surface','contract_surface'])
    if (params[k] !== undefined && params[k] !== null) out[k] = params[k];
  out.params_sha256 = sha(JSON.stringify(params || {}));
  out.client_type = safeToken(params.client_type);
  out.delivery_profile = safeToken(params.delivery_profile);
  out.client_contract_capabilities = Array.isArray(params.client_contract_capabilities)
    ? params.client_contract_capabilities.map(String).filter(safeToken).sort() : null;
  out.accepted_contract_versions = Array.isArray(params.accepted_contract_versions)
    ? params.accepted_contract_versions.map(String).filter(safeToken).sort() : null;
  return out;
}

async function login(page) {
  await page.goto(`${ENTRY}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill('demo_role_finance');
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASS);
  const lr = page.waitForResponse(r => r.url().includes('/api/v1/intent') && (() => { try { return r.request().postDataJSON()?.intent === 'login'; } catch { return false; } })(), { timeout: 30000 }).catch(() => null);
  const ir = page.waitForResponse(r => r.url().includes('/api/v1/intent') && (() => { try { return r.request().postDataJSON()?.intent === 'system.init'; } catch { return false; } })(), { timeout: 30000 }).catch(() => null);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await lr; await ir;
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.locator('[data-role-home][data-state="ready"]').waitFor({ state: 'visible', timeout: 30000 });
}

async function goHome(page) {
  await page.goto(`${ENTRY}/s/workspace.home`, { waitUntil: 'domcontentloaded' });
  await page.locator('[data-role-home][data-state="ready"]').waitFor({ state: 'visible', timeout: 30000 });
}

async function openMenu(page, label) {
  await page.getByRole('searchbox', { name: '搜索业务入口', exact: true }).fill(label);
  await page.waitForTimeout(700);
  await page.locator('button.t-button').filter({ hasText: label }).first().click();
  await page.locator('[data-semantic-component="ListPage"][data-list-status="ok"]:visible').waitFor({ timeout: 30000 });
}

async function clickFirstRecord(page) {
  const row = page.locator('[data-semantic-component="ListPage"] [data-record-key]:visible').first();
  await row.click();
  await page.locator('[data-product-page-mode="form"][data-state="ok"]:visible').first().waitFor({ timeout: 30000 });
}

async function waitFormReady(page) {
  await page.locator('[data-product-page-mode="form"][data-state="ok"]:visible').first().waitFor({ timeout: 30000 });
}

async function listReady(page) {
  await page.locator('[data-semantic-component="ListPage"][data-list-status="ok"]:visible').waitFor({ timeout: 30000 });
}

async function homeReady(page) {
  await page.locator('[data-role-home][data-state="ready"]').waitFor({ state: 'visible', timeout: 30000 });
}

async function homeWithCardsReady(page) {
  await homeReady(page);
  await page.locator('[data-object-route^="/r/project.project/"]').first().waitFor({ state: 'visible', timeout: 20000 });
}

async function clickProjectCard(page) {
  const card = page.locator('[data-object-route^="/r/project.project/"]').first();
  await card.waitFor({ state: 'visible', timeout: 15000 });
  await card.getByRole('button', { name: '打开' }).first().click();
  await waitFormReady(page);
}

async function clickEdit(page) {
  const edit = page.getByRole('button', { name: '编辑', exact: true });
  if (await edit.count() && await edit.isEnabled()) {
    await edit.click();
    await page.getByRole('button', { name: '保存修改', exact: true }).waitFor({ timeout: 15000 });
  }
}

async function capture(page, run, navStart, label) {
  const items = [];
  const onReq = req => {
    if (!req.url().includes('/api/v1/intent')) return;
    let p; try { p = req.postDataJSON(); } catch { return; }
    if (!['ui.contract.v2', 'api.data'].includes(p?.intent)) return;
    items.push({ request: req, intent: p.intent, params: p.params || {}, start_ms: Math.round(performance.now() - navStart) });
  };
  page.on('request', onReq);
  let runError = null;
  try { await run(); } catch (e) { runError = String(e?.message || e).slice(0, 220); }
  const formReadyMs = Math.round(performance.now() - navStart);
  await new Promise(r => setTimeout(r, 700));
  page.off('request', onReq);
  const rows = [];
  for (const item of items) {
    const row = { label, intent: item.intent, run_error: runError, start_ms: item.start_ms,
      response_start_ms: null, response_end_ms: null, ttfb_ms: null, status: null, bytes: null,
      body_sha256: null, ok: null, server_elapsed_ms: null, projection_cache: null,
      page_model: null, page_view_type: null, main_data_field_count: null, request_identity: requestIdentity(item.params),
      sql_count: 'GAP', error: null };
    try {
      const resp = await item.request.response();
      if (!resp) { row.error = 'no_response'; rows.push(row); continue; }
      row.status = resp.status();
      row.response_start_ms = Math.round(performance.now() - navStart);
      await resp.finished();
      const body = await resp.body();
      row.response_end_ms = Math.round(performance.now() - navStart);
      row.ttfb_ms = Math.max(0, (row.response_start_ms || 0) - item.start_ms);
      row.bytes = body.length;
      row.body_sha256 = sha(body);
      const env = JSON.parse(body.toString());
      row.ok = env?.ok === true;
      row.server_elapsed_ms = typeof env?.meta?.elapsed_ms === 'number' ? env.meta.elapsed_ms : null;
      const pc = env?.meta?.projection_cache;
      row.projection_cache = pc ? { status: pc.status, reason: pc.reason, asset_write_succeeded: pc.asset_write_succeeded, stages_ms: pc.stages_ms } : null;
      const gen = env?.data?.meta?.lifecycle?.generation || {};
      row.contract_sha256 = gen.contractSha256 || gen.contract_sha256 || null;
      row.source_sha256 = gen.sourceSha256 || gen.source_sha256 || null;
      row.page_model = env?.data?.pageInfo?.model || null;
      row.page_view_type = env?.data?.pageInfo?.viewType || null;
      row.main_data_field_count = env?.data?.dataContract?.mainData ? Object.keys(env.data.dataContract.mainData).length : null;
    } catch (e) { row.error = String(e?.message || e).slice(0, 160); }
    rows.push(row);
  }
  return { rows, form_ready_ms: formReadyMs };
}

const SCENARIOS = [
  {
    id: 'A_new_payment', name: '新建付款申请', model: 'payment.request',
    run: async page => { await openMenu(page, '付款申请'); const btn = page.getByRole('button', { name: /新建|创建|新增/ }).first(); if (await btn.count()) { await btn.click(); } await waitFormReady(page); },
  },
  {
    id: 'B_edit_payment', name: '编辑付款申请', model: 'payment.request',
    run: async page => { await openMenu(page, '付款申请'); await clickFirstRecord(page); },
  },
  {
    id: 'C_project_readonly', name: '项目只读', model: 'project.project',
    run: async page => { await clickProjectCard(page); },
  },
  {
    id: 'D_project_edit', name: '项目编辑', model: 'project.project',
    run: async page => { await clickProjectCard(page); await clickEdit(page); },
  },
];

async function warmRun(page, sc, i) {
  if (sc.id === 'A_new_payment') {
    if (i === 0) await openMenu(page, '付款申请'); else { await page.goBack(); await listReady(page); }
    const btn = page.getByRole('button', { name: /新建|创建|新增/ }).first();
    if (await btn.count()) await btn.click();
    await waitFormReady(page);
  } else if (sc.id === 'B_edit_payment') {
    if (i === 0) await openMenu(page, '付款申请'); else { await page.goBack(); await listReady(page); }
    await clickFirstRecord(page);
  } else if (sc.id === 'C_project_readonly') {
    if (i > 0) { await page.goBack(); await homeWithCardsReady(page); }
    await clickProjectCard(page);
  } else { // D_project_edit
    if (i === 0) {
      await clickProjectCard(page);
    } else {
      await page.goBack(); await page.waitForTimeout(300);
      await page.goBack().catch(() => {}); await page.waitForTimeout(300);
      await homeWithCardsReady(page);
      await clickProjectCard(page);
    }
    await clickEdit(page);
  }
}

function pct(values, p) {
  if (!values.length) return null;
  const s = [...values].sort((a, b) => a - b);
  const idx = Math.min(s.length - 1, Math.ceil((p / 100) * s.length) - 1);
  return s[Math.max(0, idx)];
}
function agg(values) {
  if (!values.length) return { n: 0, min: null, median: null, p90: null, max: null, mean: null };
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  return { n: values.length, min: Math.min(...values), median: pct(values, 50), p90: pct(values, 90), max: Math.max(...values), mean: Math.round(mean * 10) / 10 };
}

async function main() {
  if (!PASS) throw new Error('SC_DEMO_USER_PASSWORD missing');
  fs.mkdirSync(path.join(OUT, 'raw'), { recursive: true });
  const runId = new Date().toISOString().replace(/[:.]/g, '-');
  const raw = [];
  const head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  const servedIndex = sha(Buffer.from(await (await fetch(`${ENTRY}/login`)).arrayBuffer()));
  const browser = await launchChromium({ headless: true });

  async function newContext() {
    const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    page.__documentLoads = 0;
    page.on('load', () => { page.__documentLoads += 1; });
    return { context, page };
  }

  const meta = { entry: ENTRY, head, served_index_sha256: servedIndex, n_per_cell: N, started_at: new Date().toISOString(), run_id: runId };

  try {
    for (const sc of SCENARIOS) {
      // browser-cold: fresh context + login each sample
      for (let i = 0; i < N; i += 1) {
        const { context, page } = await newContext();
        await login(page);
        const loadsBefore = page.__documentLoads;
        const navStart = performance.now();
        const cap = await capture(page, () => sc.run(page), navStart, sc.id);
        const sample = { scenario: sc.id, state: 'browser_cold', index: i, form_ready_ms: cap.form_ready_ms, document_reload_count: page.__documentLoads - loadsBefore,
          contract_request_count: cap.rows.filter(r => r.intent === 'ui.contract.v2').length, frontend_store_hit: false, rows: cap.rows };
        raw.push(sample);
        fs.writeFileSync(path.join(OUT, 'raw', `${sc.id}.cold.${i}.json`), JSON.stringify(sample) + '\n');
        await context.close().catch(() => {});
      }
      // browser-warm: one context, one login, then repeat
      {
        const { context, page } = await newContext();
        await login(page);
        for (let i = 0; i < N; i += 1) {
          const loadsBefore = page.__documentLoads;
          const navStart = performance.now();
          const cap = await capture(page, () => warmRun(page, sc, i), navStart, sc.id);
          const reloadCount = page.__documentLoads - loadsBefore;
          const contractCount = cap.rows.filter(r => r.intent === 'ui.contract.v2').length;
          const sample = { scenario: sc.id, state: 'browser_warm', index: i, form_ready_ms: cap.form_ready_ms, document_reload_count: reloadCount,
            contract_request_count: contractCount, frontend_store_hit: reloadCount === 0 && contractCount === 0, rows: cap.rows };
          raw.push(sample);
          fs.writeFileSync(path.join(OUT, 'raw', `${sc.id}.warm.${i}.json`), JSON.stringify(sample) + '\n');
        }
        await context.close().catch(() => {});
      }
    }
  } catch (e) {
    fs.writeFileSync(path.join(OUT, 'run-error.json'), JSON.stringify({ error: String(e?.message || e).replaceAll(PASS, '[redacted]') }) + '\n');
    console.error('FE_PERF_B2_ERROR=' + String(e?.message || e).replaceAll(PASS, '[redacted]'));
    process.exitCode = 1;
  } finally {
    await browser.close().catch(() => {});
  }

  // ---- deliverables ----
  const allRows = [];
  for (const s of raw) for (const r of s.rows) allRows.push({ scenario: s.scenario, state: s.state, index: s.index, ...r });
  fs.writeFileSync(path.join(OUT, 'request-timeline.json'), JSON.stringify({ meta, samples: raw }, null, 2) + '\n');

  const cacheMatrix = raw.map(s => ({
    scenario: s.scenario, state: s.state, index: s.index, form_ready_ms: s.form_ready_ms,
    requests: s.rows.map(r => ({
      intent: r.intent, model: r.request_identity.model || null, op: r.request_identity.op || null,
      render_profile: r.request_identity.render_profile || null,
      status: r.projection_cache?.status || null, reason: r.projection_cache?.reason || null,
      asset_write_succeeded: r.projection_cache?.asset_write_succeeded ?? null,
      backend_assembled_hit: r.projection_cache?.reason === 'assembled_v2_hot_cache_hit',
      backend_source_hit: r.projection_cache?.status === 'hot' && r.projection_cache?.reason === 'hot_cache_hit',
      runtime_asset_hit: r.projection_cache?.reason === 'runtime_source_asset_hit',
      frontend_create_map: null,
      server_elapsed_ms: r.server_elapsed_ms,
    })),
  }));
  fs.writeFileSync(path.join(OUT, 'cache-state-matrix.json'), JSON.stringify({ meta, matrix: cacheMatrix }, null, 2) + '\n');

  const stageProfile = {};
  for (const sc of SCENARIOS) stageProfile[sc.id] = { name: sc.name, requests: {} };
  for (const r of allRows) {
    const key = r.intent + ':' + (r.request_identity.model || '?') + ':' + (r.request_identity.op || '?') + ':' + (r.request_identity.render_profile || '?');
    const bucket = stageProfile[r.scenario].requests[key] ||= { rows: [] };
    bucket.rows.push(r);
  }
  for (const sc of SCENARIOS) {
    for (const key of Object.keys(stageProfile[sc.id].requests)) {
      const rs = stageProfile[sc.id].requests[key].rows;
      const stageSums = {};
      for (const r of rs) {
        const st = r.projection_cache?.stages_ms || {};
        for (const [k, v] of Object.entries(st)) stageSums[k] = [...(stageSums[k] || []), v];
      }
      stageProfile[sc.id].requests[key] = {
        n: rs.length,
        server_elapsed_ms: agg(rs.map(r => r.server_elapsed_ms).filter(v => typeof v === 'number')),
        bytes: agg(rs.map(r => r.bytes).filter(v => typeof v === 'number')),
        ttfb_ms: agg(rs.map(r => r.ttfb_ms).filter(v => typeof v === 'number')),
        stages_ms: Object.fromEntries(Object.entries(stageSums).map(([k, v]) => [k, agg(v)])),
      };
    }
  }
  fs.writeFileSync(path.join(OUT, 'contract-stage-profile.json'), JSON.stringify({ meta, stages: stageProfile }, null, 2) + '\n');

  const browserPerf = raw.map(s => {
    const ends = s.rows.map(r => r.response_end_ms).filter(v => typeof v === 'number');
    const starts = s.rows.map(r => r.start_ms).filter(v => typeof v === 'number');
    return {
      scenario: s.scenario, state: s.state, index: s.index,
      nav_start_ms: 0,
      first_request_start_ms: starts.length ? Math.min(...starts) : null,
      last_response_end_ms: ends.length ? Math.max(...ends) : null,
      form_ready_ms: s.form_ready_ms,
      request_count: s.rows.length,
      overlap_window_ms: ends.length && starts.length ? Math.max(...ends) - Math.min(...starts) : null,
      frontend_after_last_response_ms: ends.length ? Math.max(0, s.form_ready_ms - Math.max(...ends)) : null,
    };
  });
  fs.writeFileSync(path.join(OUT, 'browser-performance.json'), JSON.stringify({ meta, samples: browserPerf }, null, 2) + '\n');

  const byScenario = {};
  for (const s of raw) (byScenario[s.scenario] ||= []).push(s);
  const md = [`# R0.1B 性能归因报告（首次采集）`, '',
    `- 运行身份：${meta.entry} / HEAD ${meta.head.slice(0, 12)} / served index ${meta.served_index_sha256.slice(0, 12)}`,
    `- 每格样本：N=${N}（浏览器冷/暖各 N），四场景共 ${raw.length} 样本；原始样本见 raw/`,
    `- 说明：本表为真实单次采集，非 120/160 完整基线；P50/P90 按现有样本用 nearest-rank 计算。`, ''];
  for (const sc of SCENARIOS) {
    const rows = byScenario[sc.id] || [];
    md.push(`## ${sc.name} (${sc.id})`, '');
    for (const state of ['browser_cold', 'browser_warm']) {
      const rs = rows.filter(r => r.state === state);
      const ready = rs.map(r => r.form_ready_ms);
      const lastEnd = rs.map(r => Math.max(0, ...r.rows.map(x => x.response_end_ms || 0)));
      md.push(`- ${state === 'browser_cold' ? '浏览器冷态' : '浏览器暖态'}: form_ready ${JSON.stringify(agg(ready))}, last_request_end ${JSON.stringify(agg(lastEnd))}, 每样本请求数均值 ${(rs.reduce((a, b) => a + b.rows.length, 0) / (rs.length || 1)).toFixed(1)}`);
    }
    md.push('');
  }
  md.push('## 主契约与关系子契约阶段耗时（见 contract-stage-profile.json）', '');
  md.push('SQL 数量无法从 HTTP 元数据获得，需由 `local_dev_runtime_performance.py` 进程内关系归因补齐（R0.1B 缺口）。', '');
  fs.writeFileSync(path.join(OUT, 'r0.1b-performance-analysis.md'), md.join('\n') + '\n');

  console.log(JSON.stringify({ status: 'observed', meta, samples: raw.length, output_dir: OUT }));
}

await main();

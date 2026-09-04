#!/usr/bin/env node
/**
 * BOQ 真实闭环 G3.3-B 双角色五视口浏览器验收（dual-role × five-viewport）。
 *
 * 矩阵：2 角色（cost_manager / cost_user） × 5 视口（1440 / 1280 / 1024 / 768 / 390）
 *      × 2 数据集（boq_1k / boq_10k） = 20 cell。
 *
 * 每个 cell 采集 11 个必填浏览器证据字段（见 README 第 12 节 /
 * config/frontend/acceptance_evidence_contract_v1.schema.json），并把
 * 整包聚合成 frontend_acceptance_evidence_contract.v1 证据包：
 *   - schema / baseline / environment_assets / toolchain / collected_at
 *   - browser_evidence_contract.{required_fields, cross_env_reuse_forbidden=true}
 *
 * v0.3.0：每 cell 额外采集 role_session_digest（登录后 sessionStorage
 * sc_auth_token 的 sha256——只落摘要、绝不落原始 token）。只读场景两成本
 * 角色对同 dataset × 视口渲染字节级一致是 G3.3-B 的验收目标本身，因此
 * screenshot_digest 允许跨角色相同；独立采集由 role_session_digest 证明
 * （每次登录产生独立会话 token，20 cell 两两不同）。
 *
 * 产物目录结构：
 *   artifacts/boq-dual-role-five-viewport/
 *     evidence.json                — v1 证据包
 *     report.json                  — 矩阵执行结果（每 cell PASS/FAIL + 断言）
 *     index.html                   — 矩阵可视化（视口 × 数据集 × 角色）
 *     screenshots/<cell_id>.png    — 每 cell 截图
 *     <cell_id>/probe.json         — 每 cell 的契约/错误探针
 *
 * 证据合规：boq_dual_role_five_viewport_evidence_guard.py 验证。
 *
 * 环境前置：
 *   - dev nginx + Odoo 已就绪；1k/10k BOQ 导入批次的 project_id 必须已
 *     在 G3.1 既有 import wizard 中落地；
 *   - 角色 sc_cost_mgr 与 sc_cost_user_cap 必须存在并具备
 *     project.management 场景的只读权限。
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { launchChromium } from './playwright_runtime.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..', '..');

// sc-local-dev 栈实际映射：dev nginx = 127.0.0.1:18081（18083 是 clean 栈），
// demo 数据库 = sc_dev_demo（G3.1 fixture 用户与 12210/12211 项目所在库）。
const BASE_URL = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18081').replace(/\/$/, '');
const DB_NAME = process.env.DB_NAME || 'sc_dev_demo';
const PASSWORD = process.env.E2E_PASSWORD || '';
const OUT_DIR = process.env.ARTIFACTS_DIR
  || path.join(REPO_ROOT, 'artifacts', 'boq-dual-role-five-viewport');

const ENVIRONMENT_ID = process.env.BOQ_ACCEPTANCE_ENV_ID || 'local';
const PRODUCT_SERVICE_STATIC_SHAS = {
  frontend_sha: String(process.env.FRONTEND_SHA || ''),
  backend_sha: String(process.env.BACKEND_SHA || ''),
  contract_schema_sha: String(process.env.CONTRACT_SCHEMA_SHA || ''),
};
const TOOL_VERSION = `boq-dual-role-five-viewport-browser-acceptance.mjs@${String(
  process.env.HARNESS_VERSION || '0.3.0'
)}`;

// demo fixture 实际登录名（demo_addons sc_demo_users.xml：user_sc_cost_manager_cap
// → sc_cost_mgr，user_sc_cost_user_cap → sc_cost_user_cap；sc_fx_* 不存在）。
const ROLES = [
  { id: 'cost_manager', login: process.env.BOQ_COST_MANAGER_LOGIN || 'sc_cost_mgr' },
  { id: 'cost_user', login: process.env.BOQ_COST_USER_LOGIN || 'sc_cost_user_cap' },
];
const VIEWPORTS = [
  { id: '1440x900', width: 1440, height: 900, bucket: 'desktop_l' },
  { id: '1280x800', width: 1280, height: 800, bucket: 'desktop_m' },
  { id: '1024x768', width: 1024, height: 768, bucket: 'desktop_s' },
  { id: '768x1024', width: 768, height: 1024, bucket: 'tablet' },
  { id: '390x844', width: 390, height: 844, bucket: 'mobile' },
];
const DATASETS = [
  {
    id: 'boq_1k',
    projectId: Number(process.env.BOQ_1K_PROJECT_ID || 0),
    label: '1k 行 BOQ（小型项目）',
  },
  {
    id: 'boq_10k',
    projectId: Number(process.env.BOQ_10K_PROJECT_ID || 0),
    label: '10k 行 BOQ（大型项目）',
  },
];

const CAPTURE_MODE = 'readonly';
const NORMALIZED_ROUTE_TEMPLATE = (projectId) => `/s/project.management?project_id=${projectId}`;
const SCENE_BLOCK_SELECTOR = '[data-block-key="block.project.boq_preview"], [data-block-type="boq_import_preview"]';

function check(value, reason) {
  if (!value) throw new Error(reason);
}

function sha256File(filePath) {
  const digest = crypto.createHash('sha256');
  digest.update(fs.readFileSync(filePath));
  return digest.digest('hex');
}

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function cellId(roleId, datasetId, viewportId) {
  return `${roleId}__${datasetId}__${viewportId}`;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function capturePageState(page) {
  const state = {
    pageErrors: [],
    httpErrors: [],
    consoleErrors: [],
    contractProbes: [],
  };
  page.on('pageerror', (err) => state.pageErrors.push(String(err && err.message ? err.message : err)));
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = String(msg.text() || '');
      // 忽略 favicon 与 ResizeObserver 噪音（与既有 collection_view_semantics 一致）
      if (/favicon|ResizeObserver/i.test(text)) return;
      state.consoleErrors.push(text);
    }
  });
  page.on('response', async (response) => {
    if (response.status() >= 400) {
      state.httpErrors.push({ status: response.status(), url: response.url() });
    }
    const req = response.request();
    if (!req.url().includes('/api/v1/intent')) return;
    let payload = null;
    try { payload = req.postDataJSON(); } catch { payload = null; }
    if (!payload || payload.intent !== 'project.dashboard.enter') return;
    let body = null;
    try { body = await response.json(); } catch { body = null; }
    // BOQ preview 是 runtime surface 块：场景静态契约（system.init /
    // ui.contract.v2 scene_contract 源）不含它；真实渲染链路的契约载体是
    // project.dashboard.enter 的 data.blocks（stub 块）+ runtime_fetch_hints
    // （指向 project.dashboard.block.fetch 的 boq 块运行时拉取）。
    const data = body && typeof body.data === 'object' && body.data ? body.data : null;
    const blocks = data && Array.isArray(data.blocks) ? data.blocks : [];
    const fetchHints = data && data.runtime_fetch_hints
      && typeof data.runtime_fetch_hints === 'object'
      && data.runtime_fetch_hints.blocks
      && typeof data.runtime_fetch_hints.blocks === 'object'
      ? data.runtime_fetch_hints.blocks
      : null;
    state.contractProbes.push({
      params: payload.params || {},
      status: response.status(),
      body_has_blocks: blocks.length > 0,
      body_has_boq_preview: blocks.some((b) => b && (
        b.key === 'boq'
        || b.block_key === 'block.project.boq_preview'
        || b.block_type === 'boq_import_preview'
      )) || Boolean(fetchHints && fetchHints.boq),
    });
  });
  return state;
}

async function login(page, loginName) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(loginName);
  await inputs.nth(1).fill(PASSWORD);
  if (await inputs.nth(2).isEnabled().catch(() => false)) {
    await inputs.nth(2).fill(DB_NAME);
  } else {
    check(await inputs.nth(2).inputValue() === DB_NAME, 'LOGIN_DATABASE_MISMATCH');
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  try {
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
  } catch (error) {
    const failShot = path.join(OUT_DIR, 'screenshots', 'login-failed.png');
    ensureDir(path.dirname(failShot));
    await page.screenshot({ path: failShot, fullPage: true });
    const body = (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 800);
    throw new Error(`LOGIN_FAILED:${loginName}:${body}; ${error.message}`);
  }
  await page.locator('.layout-shell').waitFor({ timeout: 45_000 });
}

/**
 * 提取当前登录会话的 role_session_digest：登录后前端把 intent API 的
 * Bearer token 存在 sessionStorage（sc_auth_token:<db>）。这里只取其
 * sha256 摘要（证据包绝不落原始 token）。每次登录生成独立会话 token，
 * 因此 20 个 cell 的 role_session_digest 两两不同 —— 这是「每 cell 独立
 * 采集」的硬证据（只读场景下两角色截图字节级一致时仍可区分独立会话）。
 */
async function captureRoleSessionDigest(page) {
  const token = await page.evaluate((db) => {
    const direct = sessionStorage.getItem(`sc_auth_token:${db}`);
    if (direct) return direct;
    const keys = Object.keys(sessionStorage).filter((k) => k.startsWith('sc_auth_token'));
    return keys.length ? sessionStorage.getItem(keys[0]) : null;
  }, DB_NAME);
  check(typeof token === 'string' && token.length > 0, 'ROLE_SESSION_TOKEN_MISSING');
  return crypto.createHash('sha256').update(token).digest('hex');
}

async function openProjectManagement(page, projectId) {
  const route = NORMALIZED_ROUTE_TEMPLATE(projectId);
  await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  // 等场景 orchestrator 与 BOQ preview block 出现（G3.3-A 挂接的 block）
  try {
    await page.locator(SCENE_BLOCK_SELECTOR).first().waitFor({ timeout: 45_000 });
  } catch (error) {
    const failShot = path.join(OUT_DIR, 'screenshots', `project-management-failed-${projectId}.png`);
    ensureDir(path.dirname(failShot));
    await page.screenshot({ path: failShot, fullPage: true });
    const body = (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 1200);
    throw new Error(`PROJECT_MANAGEMENT_BLOCK_MISSING:project=${projectId}:url=${page.url()}:body=${body}; ${error.message}`);
  }
  // 等加载态结束
  await page.waitForFunction(() => !/加载中|正在载入|正在加载/.test(document.body.innerText || ''), undefined, { timeout: 45_000 });
}

async function captureNoOverflow(page, label) {
  const geometry = await page.evaluate(() => ({
    doc: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
    docHeight: document.documentElement.scrollHeight,
  }));
  if (geometry.doc > geometry.viewport + 2) {
    throw new Error(`${label}:HORIZONTAL_OVERFLOW:doc=${geometry.doc}>viewport=${geometry.viewport}`);
  }
  return geometry;
}

async function captureCell({ browser, role, dataset, viewport, cellOutDir }) {
  const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, locale: 'zh-CN' });
  const page = await context.newPage();
  const state = capturePageState(page);
  const collectedAt = isoNow();
  let browserVersion = 'unknown';
  try {
    browserVersion = String(page.context().browser().version() || 'unknown');
  } catch { /* version probe best-effort */ }

  const browserUrlBeforeNav = `${BASE_URL}${NORMALIZED_ROUTE_TEMPLATE(dataset.projectId)}`;
  await login(page, role.login);
  const roleSessionDigest = await captureRoleSessionDigest(page);
  await openProjectManagement(page, dataset.projectId);
  // 再稳定 1.5s 等待 BOQ preview 内部拉取完成
  await page.waitForTimeout(1500);
  const geometry = await captureNoOverflow(page, `${role.id}@${viewport.id}@${dataset.id}`);

  const screenshotPath = path.join(OUT_DIR, 'screenshots', `${cellId(role.id, dataset.id, viewport.id)}.png`);
  ensureDir(path.dirname(screenshotPath));
  await page.screenshot({ path: screenshotPath, fullPage: true, animations: 'disabled' });
  const screenshotDigest = sha256File(screenshotPath);
  const browserUrl = page.url();
  const normalizedRoute = NORMALIZED_ROUTE_TEMPLATE(dataset.projectId);

  const probe = {
    pageErrors: state.pageErrors.slice(),
    httpErrors: state.httpErrors.slice(),
    consoleErrors: state.consoleErrors.slice(),
    contractProbes: state.contractProbes.slice(),
    geometry,
    browserUrl,
    roleSessionDigest,
  };
  ensureDir(cellOutDir);
  fs.writeFileSync(path.join(cellOutDir, 'probe.json'), `${JSON.stringify(probe, null, 2)}\n`);

  if (state.pageErrors.length > 0) {
    throw new Error(`PAGE_ERRORS:${JSON.stringify(state.pageErrors)}`);
  }
  if (state.httpErrors.length > 0) {
    throw new Error(`HTTP_ERRORS:${JSON.stringify(state.httpErrors)}`);
  }
  if (state.consoleErrors.length > 0) {
    throw new Error(`CONSOLE_ERRORS:${JSON.stringify(state.consoleErrors)}`);
  }
  if (state.contractProbes.length === 0) {
    throw new Error('CONTRACT_PROBE_MISSING:no project.dashboard.enter POST observed');
  }
  if (!state.contractProbes.some((p) => p.body_has_boq_preview)) {
    throw new Error('BOQ_PREVIEW_BLOCK_NOT_IN_CONTRACT_RESPONSE');
  }

  await context.close();

  return {
    environment_id: ENVIRONMENT_ID,
    dataset_id: dataset.id,
    role: role.id,
    normalized_route: normalizedRoute,
    browser_url: browserUrl,
    viewport: viewport.id,
    capture_mode: CAPTURE_MODE,
    browser_full_version: browserVersion,
    screenshot_digest: screenshotDigest,
    role_session_digest: roleSessionDigest,
    product_service_static_shas: { ...PRODUCT_SERVICE_STATIC_SHAS },
    collected_at_and_tool_version: `${collectedAt}|${TOOL_VERSION}`,
  };
}

function buildEvidencePackage(cells, baselineSha) {
  const requiredFields = [
    'environment_id', 'dataset_id', 'role', 'normalized_route', 'browser_url',
    'viewport', 'capture_mode', 'browser_full_version', 'screenshot_digest',
    'product_service_static_shas', 'collected_at_and_tool_version',
  ];

  const envAssets = [
    {
      path: 'config/frontend/acceptance_environments_v1.json',
      sha256: sha256File(path.join(REPO_ROOT, 'config', 'frontend', 'acceptance_environments_v1.json')),
    },
    {
      path: 'config/frontend/acceptance_tool_matrix_v1.json',
      sha256: sha256File(path.join(REPO_ROOT, 'config', 'frontend', 'acceptance_tool_matrix_v1.json')),
    },
    {
      path: 'config/frontend/acceptance_evidence_contract_v1.schema.json',
      sha256: sha256File(path.join(REPO_ROOT, 'config', 'frontend', 'acceptance_evidence_contract_v1.schema.json')),
    },
    {
      path: 'scripts/verify/boq_dual_role_five_viewport_browser_acceptance.mjs',
      sha256: sha256File(path.join(REPO_ROOT, 'scripts', 'verify', 'boq_dual_role_five_viewport_browser_acceptance.mjs')),
    },
  ];

  const toolchain = {
    node: String(process.version || 'unknown'),
    playwright: 'playwright-runtime (see scripts/verify/playwright_runtime.mjs)',
  };

  return {
    schema: 'frontend_acceptance_evidence_contract.v1',
    baseline: {
      baseline_sha: baselineSha,
      baseline_sha_source: 'G3.3-B acceptance run baseline (origin/main HEAD at capture time)',
      capability_inventory_path: 'docs/planning/custom-frontend-integration/G1_CAPABILITY_INVENTORY.md',
    },
    environment_assets: {
      profiles_present: ['daily', 'local', 'production', 'test'],
      assets: envAssets,
    },
    toolchain,
    collected_at: isoNow(),
    browser_evidence_contract: {
      required_fields: requiredFields,
      cross_env_reuse_forbidden: true,
    },
    matrix_spec: {
      roles: ROLES.map((r) => r.id),
      viewports: VIEWPORTS.map((v) => v.id),
      datasets: DATASETS.map((d) => d.id),
      cell_count: ROLES.length * VIEWPORTS.length * DATASETS.length,
    },
    cells,
  };
}

function buildReport(cells, results) {
  return {
    schema_version: 'boq-dual-role-five-viewport-acceptance.v1',
    collected_at: isoNow(),
    base_url: BASE_URL,
    database: DB_NAME,
    matrix: {
      roles: ROLES.map((r) => r.id),
      viewports: VIEWPORTS.map((v) => v.id),
      datasets: DATASETS.map((d) => d.id),
    },
    cells: results.map((r) => ({
      cell_id: cellId(r.role.id, r.dataset.id, r.viewport.id),
      role: r.role.id,
      viewport: r.viewport.id,
      dataset: r.dataset.id,
      status: r.status,
      error: r.error || null,
      screenshot_digest: r.evidence ? r.evidence.screenshot_digest : null,
      cell_dir: r.cellDir,
    })),
    totals: {
      cells: cells.length,
      pass: results.filter((r) => r.status === 'pass').length,
      fail: results.filter((r) => r.status === 'fail').length,
    },
  };
}

function renderIndexHtml(report) {
  const headerCells = VIEWPORTS.map((v) => `<th>${v.id}</th>`).join('');
  const rows = ROLES.flatMap((role) =>
    DATASETS.map((dataset) => {
      const cells = VIEWPORTS.map((viewport) => {
        const cid = cellId(role.id, dataset.id, viewport.id);
        const r = report.cells.find((c) => c.cell_id === cid);
        const status = r ? r.status : 'missing';
        const color = status === 'pass' ? '#2e7d32' : status === 'fail' ? '#c62828' : '#9e9e9e';
        const detail = r && r.error ? `<br><small>${String(r.error).slice(0, 200)}</small>` : '';
        return `<td style="background:${color};color:#fff;padding:6px;">${status}${detail}</td>`;
      }).join('');
      return `<tr><th>${role.id} / ${dataset.id}</th>${cells}</tr>`;
    }),
  ).join('');
  return `<!doctype html>
<meta charset="utf-8">
<title>BOQ dual-role five-viewport acceptance</title>
<style>body{font-family:system-ui,sans-serif;margin:24px;}table{border-collapse:collapse;}th,td{border:1px solid #ccc;padding:6px 10px;text-align:center;}th{background:#f4f4f4;}h1{margin:0 0 8px;}small{color:#eee;}</style>
<h1>BOQ G3.3-B 双角色五视口验收矩阵</h1>
<p>采集时间：${report.collected_at} ｜ 基础 URL：${report.base_url} ｜ DB：${report.database}</p>
<p>汇总：${report.totals.pass}/${report.totals.cells} 通过</p>
<table>
<thead><tr><th>role / dataset</th>${headerCells}</tr></thead>
<tbody>${rows}</tbody>
</table>
<p>每 cell 详情：<code>artifacts/boq-dual-role-five-viewport/&lt;cell_id&gt;/probe.json</code></p>
<p>截图：<code>artifacts/boq-dual-role-five-viewport/screenshots/&lt;cell_id&gt;.png</code></p>
<p>证据包：<code>evidence.json</code> （v1 schema：<code>config/frontend/acceptance_evidence_contract_v1.schema.json</code>）</p>
`;
}

function gitHead(args) {
  return execFileSync('git', args, { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
}

async function main() {
  check(PASSWORD, 'E2E_PASSWORD_REQUIRED');
  for (const dataset of DATASETS) {
    check(dataset.projectId > 0, `BOQ_${dataset.id.toUpperCase()}_PROJECT_ID_REQUIRED`);
  }
  ensureDir(OUT_DIR);
  ensureDir(path.join(OUT_DIR, 'screenshots'));

  const baselineSha = (() => {
    try { return gitHead(['rev-parse', 'origin/main']); }
    catch { return gitHead(['rev-parse', 'HEAD']); }
  })();
  check(/^[0-9a-f]{40}$/.test(baselineSha), `BASELINE_SHA_INVALID:${baselineSha}`);

  const browser = await launchChromium({ headless: true });
  const results = [];
  const cells = [];
  try {
    for (const role of ROLES) {
      for (const dataset of DATASETS) {
        for (const viewport of VIEWPORTS) {
          const cid = cellId(role.id, dataset.id, viewport.id);
          const cellDir = path.join(OUT_DIR, cid);
          ensureDir(cellDir);
          try {
            const evidence = await captureCell({ browser, role, dataset, viewport, cellOutDir: cellDir });
            cells.push(evidence);
            results.push({ role, dataset, viewport, status: 'pass', error: null, evidence, cellDir: cid });
            console.log(`[boq-dual-role-five-viewport] PASS ${cid}`);
          } catch (error) {
            const message = error instanceof Error ? error.stack || error.message : String(error);
            results.push({ role, dataset, viewport, status: 'fail', error: message, evidence: null, cellDir: cid });
            console.error(`[boq-dual-role-five-viewport] FAIL ${cid}: ${message}`);
          }
        }
      }
    }
  } finally {
    await browser.close();
  }

  const evidencePkg = buildEvidencePackage(cells, baselineSha);
  fs.writeFileSync(path.join(OUT_DIR, 'evidence.json'), `${JSON.stringify(evidencePkg, null, 2)}\n`);

  const report = buildReport(cells, results);
  fs.writeFileSync(path.join(OUT_DIR, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
  fs.writeFileSync(path.join(OUT_DIR, 'index.html'), renderIndexHtml(report));

  console.log(JSON.stringify({ ok: report.totals.fail === 0, ...report.totals, evidence: path.join(OUT_DIR, 'evidence.json') }));
  if (report.totals.fail > 0) process.exitCode = 2;
}

main().catch((error) => {
  console.error(`BOQ_DUAL_ROLE_FIVE_VIEWPORT=FAIL ${error.stack || error.message}`);
  process.exitCode = 3;
});

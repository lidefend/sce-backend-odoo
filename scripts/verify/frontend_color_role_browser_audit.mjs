#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { launchChromium } from './playwright_runtime.mjs';
import { captureReleasedNavigation } from './released_navigation_target.mjs';
import { resolveAcceptanceEnvironment, verifyServedIdentity } from './lib/frontend_acceptance_environment.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'color-role-audit' });
const BASE_URL = acceptance.baseUrl;
const DATABASE = acceptance.database;
const LOGIN = process.env.E2E_LOGIN || acceptance.login || acceptance.roleBindings.contract_operator || acceptance.roleBindings.project_manager || '';
const PASSWORD = process.env.E2E_PASSWORD || acceptance.password || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const OUTPUT = path.resolve(process.env.COLOR_ROLE_AUDIT_OUTPUT || '.runtime/final-acceptance/color-role-audit');
const REPORT = path.resolve(process.env.COLOR_ROLE_AUDIT_REPORT || path.join(OUTPUT, 'report.json'));
const VIEWPORTS = [{ key: '1440', width: 1440, height: 900 }, { key: '390', width: 390, height: 844 }];
const THEMES = ['light', 'dark'];
const AUDIT_STARTED_AT = new Date().toISOString();
let navigationSequence = 0;
let activeAuditNavigation = null;

if (!LOGIN || !PASSWORD) throw new Error('acceptance login and password are required');
await fs.mkdir(OUTPUT, { recursive: true });

async function auditedGoto(page, url, options) {
  const parsed = new URL(url, BASE_URL);
  const navigation = { id: ++navigationSequence, target_path: parsed.pathname, started_at: new Date().toISOString() };
  activeAuditNavigation = navigation;
  try {
    return await page.goto(url, options);
  } finally {
    navigation.completed_at = new Date().toISOString();
    activeAuditNavigation = null;
  }
}

function routeFor(node) {
  const meta = node?.meta && typeof node.meta === 'object' ? node.meta : {};
  const route = String(node?.route || meta.route || '');
  const actionId = Number(node?.action_id || node?.actionId || node?.action || meta.action_id || 0);
  const menuId = Number(node?.menu_id || node?.menuId || meta.menu_id || 0);
  if (route) return actionId > 0 && menuId > 0 && !/[?&]menu_id=/.test(route)
    ? `${route}${route.includes('?') ? '&' : '?'}menu_id=${menuId}` : route;
  return actionId > 0 ? `/a/${actionId}${menuId > 0 ? `?menu_id=${menuId}` : ''}` : '';
}

function actionable(nodes, parents = []) {
  const rows = [];
  for (const node of Array.isArray(nodes) ? nodes : []) {
    const label = String(node?.title || node?.label || node?.name || '').trim();
    const labels = [...parents, label].filter(Boolean);
    const route = routeFor(node);
    if (route) rows.push({ label: labels.join(' / '), route });
    rows.push(...actionable(node?.children, labels));
  }
  return rows;
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function gitText(args) {
  return execFileSync('git', args, { cwd: acceptance.root, encoding: 'utf8' });
}

async function sourceEvidence(observedAssetPaths = []) {
  const head = gitText(['rev-parse', 'HEAD']).trim();
  const status = gitText(['status', '--porcelain']);
  const trackedDiff = gitText(['diff', '--binary', 'HEAD']);
  const untracked = [];
  for (const row of status.split('\n').filter((line) => line.startsWith('?? '))) {
    const relative = row.slice(3);
    const absolute = path.join(acceptance.root, relative);
    const content = await fs.readFile(absolute).catch(() => Buffer.from(''));
    untracked.push({ path: relative, sha256: sha256(content) });
  }
  const indexResponse = await fetch(`${BASE_URL}/`, { redirect: 'error' });
  if (!indexResponse.ok) throw new Error(`served index probe failed: HTTP ${indexResponse.status}`);
  const servedIndex = await indexResponse.text();
  const assetPaths = Array.from(new Set([
    ...Array.from(servedIndex.matchAll(/(?:src|href)=["']([^"']+\.(?:js|css))["']/g), (match) => match[1]),
    ...observedAssetPaths,
  ])).sort();
  const assets = [];
  for (const assetPath of assetPaths) {
    const response = await fetch(new URL(assetPath, BASE_URL), { redirect: 'error' });
    if (!response.ok) throw new Error(`served asset probe failed: HTTP ${response.status}`);
    const served = Buffer.from(await response.arrayBuffer());
    const localPath = path.join(acceptance.root, 'frontend/apps/web/dist-release', assetPath.replace(/^\//, ''));
    const local = await fs.readFile(localPath);
    assets.push({ path: assetPath, served_sha256: sha256(served), local_sha256: sha256(local), matches: served.equals(local) });
  }
  const localIndex = await fs.readFile(path.join(acceptance.root, 'frontend/apps/web/dist-release/index.html'));
  const localIndexStat = await fs.stat(path.join(acceptance.root, 'frontend/apps/web/dist-release/index.html'));
  const servedIdentity = await verifyServedIdentity(acceptance, acceptance.provenance.expectedSha || '', fetch);
  return {
    head,
    dirty: Boolean(status.trim()),
    dirty_fingerprint_sha256: sha256(`${trackedDiff}\n${JSON.stringify(untracked)}`),
    audit_script_sha256: sha256(await fs.readFile(new URL(import.meta.url))),
    token_generator_sha256: sha256(await fs.readFile(path.join(acceptance.root, 'frontend/packages/design-tokens/scripts/build_tokens.py'))),
    served_index_sha256: sha256(servedIndex),
    local_index_sha256: sha256(localIndex),
    release_built_at: localIndexStat.mtime.toISOString(),
    served_bundle_matches_local_release: sha256(servedIndex) === sha256(localIndex) && assets.every((row) => row.matches),
    assets,
    runtime_identity: servedIdentity,
  };
}

function evaluateColorContract(measurement, requiredRoles) {
  const counts = Object.fromEntries(requiredRoles.map((role) => [role, measurement.samples.filter((row) => row.role === role).length]));
  const focusSamples = measurement.samples.filter((row) => row.role === 'focus');
  const distinctStateFamily = measurement.samples.some((active) => active.role === 'active' && measurement.samples.some((hover) => hover.role === 'hover' && hover.family === active.family && hover.fingerprint !== active.fingerprint));
  const saturatedArea = measurement.saturatedRects && measurement.viewport
    ? rectangleUnionRatio(measurement.saturatedRects, measurement.viewport)
    : measurement.saturatedArea;
  return {
    required_role_samples_present: Object.values(counts).every((count) => count > 0),
    keyboard_focus_reached: !requiredRoles.includes('focus') || measurement.keyboard_focus?.reached === true,
    semantic_color_role_coverage: measurement.samples.length > 0 && measurement.samples.every((row) => ['ordinary', 'primary', 'active', 'hover', 'focus', 'danger'].includes(row.role)),
    semantic_color_role_binding_pass: measurement.samples.every((row) => !row.infoMisbound && row.roleBindingPass !== false),
    normal_text_contrast_pass: measurement.samples.filter((row) => row.textContrast !== null).every((row) => row.textContrast >= 4.5),
    focus_contrast_pass: !requiredRoles.includes('focus') || focusSamples.length > 0 && focusSamples.every((row) => resolvedFocusContrast(row) >= 3),
    navigation_state_distinct: !(requiredRoles.includes('active') && requiredRoles.includes('hover')) || distinctStateFamily,
    selected_state_distinct: Boolean(measurement.variables.selectedBg) && measurement.variables.selectedBg !== measurement.variables.hoverBg,
    large_saturated_surface_budget_pass: saturatedArea <= 0.08,
  };
}

function evaluateDialogLifecycle(lifecycle) {
  return {
    dialog_escape_closes: lifecycle.escapeClosed === true,
    dialog_focus_restored: lifecycle.focusRestored === true,
    dialog_focus_trapped: lifecycle.focusTrapped === true,
    dialog_body_lock_restored: lifecycle.bodyLockRestored === true,
    dialog_no_write_request: lifecycle.writeRequests === 0,
  };
}

function compositeColor(foreground, background) {
  const alpha = foreground.a + background.a * (1 - foreground.a);
  return {
    r: (foreground.r * foreground.a + background.r * background.a * (1 - foreground.a)) / alpha,
    g: (foreground.g * foreground.a + background.g * background.a * (1 - foreground.a)) / alpha,
    b: (foreground.b * foreground.a + background.b * background.a * (1 - foreground.a)) / alpha,
    a: alpha,
  };
}

function contrastRatio(left, right) {
  const channel = (value) => { const x = value / 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; };
  const luminance = (color) => 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b);
  const a = luminance(left); const b = luminance(right);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

function resolvedFocusContrast(sample) {
  if (sample.focusForeground && sample.focusAdjacent && Number(sample.focusWidth) >= 2) {
    return contrastRatio(compositeColor(sample.focusForeground, sample.focusAdjacent), sample.focusAdjacent);
  }
  return Number(sample.focusContrast || 0);
}

function rectangleUnionRatio(rectangles, viewport) {
  const clipped = rectangles.map((rect) => ({
    left: Math.max(0, rect.left), top: Math.max(0, rect.top),
    right: Math.min(viewport.width, rect.right), bottom: Math.min(viewport.height, rect.bottom),
  })).filter((rect) => rect.right > rect.left && rect.bottom > rect.top);
  const xs = Array.from(new Set(clipped.flatMap((rect) => [rect.left, rect.right]))).sort((a, b) => a - b);
  let area = 0;
  for (let index = 0; index < xs.length - 1; index += 1) {
    const left = xs[index]; const right = xs[index + 1];
    const spans = clipped.filter((rect) => rect.left < right && rect.right > left).map((rect) => [rect.top, rect.bottom]).sort((a, b) => a[0] - b[0]);
    let start = null; let end = null; let height = 0;
    for (const [top, bottom] of spans) {
      if (start === null) { start = top; end = bottom; continue; }
      if (top > end) { height += end - start; start = top; end = bottom; } else end = Math.max(end, bottom);
    }
    if (start !== null) height += end - start;
    area += (right - left) * height;
  }
  return area / (viewport.width * viewport.height);
}

function sanitizeRuntimeText(value) {
  let result = String(value || '');
  for (const secret of [BASE_URL, LOGIN, DATABASE, PASSWORD].filter(Boolean)) result = result.split(secret).join('<redacted>');
  result = result.replace(/\b(?:bearer\s+)?[A-Za-z0-9_-]{24,}(?:\.[A-Za-z0-9_-]{12,}){0,2}\b/gi, '<credential-redacted>');
  result = result.replace(/\b(password|passwd|token|cookie|session|authorization)\s*[:=]\s*[^\s,;]+/gi, '$1=<redacted>');
  return result.replace(/https?:\/\/[^\s/?#]+(?:[/?#][^\s]*)?/g, (raw) => {
    try { return `<origin>${new URL(raw).pathname}`; } catch { return '<url-redacted>'; }
  }).slice(0, 1000);
}

function safeRequestPath(value) {
  try { return new URL(value).pathname; } catch { return '<invalid-url>'; }
}

async function login(page, navigation) {
  await auditedGoto(page, `${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(LOGIN);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('input').nth(2);
  if (await database.isEnabled().catch(() => false)) await database.fill(DATABASE);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => !/正在初始化|正在加载导航/.test(document.body.innerText || ''), null, { timeout: 45_000 });
  if (!navigation.nav().length) throw new Error('authenticated navigation was not captured');
}

async function findList(page, navigation) {
  const candidates = actionable(navigation.nav());
  const ordered = [
    ...candidates.filter((row) => /项目台账|一般合同|施工合同/.test(row.label)),
    ...candidates.filter((row) => !/项目台账|一般合同|施工合同/.test(row.label)),
  ];
  for (const target of ordered) {
    await auditedGoto(page, `${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    if (!await page.locator('[data-list-query-action-bar]').waitFor({ state: 'visible', timeout: 6_000 }).then(() => true).catch(() => false)) continue;
    await page.locator('.product-loading-shell').waitFor({ state: 'detached', timeout: 30_000 }).catch(() => {});
    return target;
  }
  throw new Error('no list route discovered');
}

async function findExtendedTargets(page, navigation, fallbackList) {
  const candidates = actionable(navigation.nav());
  const contractCandidates = [
    ...candidates.filter((row) => /施工合同/.test(row.label)),
    ...candidates.filter((row) => /一般合同/.test(row.label)),
    ...candidates.filter((row) => /合同/.test(row.label)),
    ...candidates.filter((row) => !/合同/.test(row.label)),
  ].filter((row, index, rows) => rows.findIndex((candidate) => candidate.route === row.route) === index);
  let contractList = null;
  let recordRoute = '';
  let dialogRoute = '';
  for (const target of contractCandidates) {
    await auditedGoto(page, `${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    if (!await page.locator('[data-list-query-action-bar]').waitFor({ state: 'visible', timeout: 6_000 }).then(() => true).catch(() => false)) continue;
    await page.locator('.product-loading-shell').waitFor({ state: 'detached', timeout: 30_000 }).catch(() => {});
    const recordRow = page.locator('.cell-primary-link:visible, .mobile-record-card:visible').first();
    if (!await recordRow.count()) continue;
    await recordRow.click();
    if (!await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 10_000 }).then(() => true).catch(() => false)) continue;
    if (!await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 10_000 }).then(() => true).catch(() => false)) continue;
    await page.locator('.product-form-loading-skeleton').waitFor({ state: 'detached', timeout: 30_000 }).catch(() => {});
    const current = new URL(page.url());
    const candidateRecordRoute = `${current.pathname}${current.search}`;
    let candidateEditRoute = '';
    const editAction = page.getByRole('button', { name: /^编辑$/ }).first();
    if (await editAction.count() && await editAction.isEnabled().catch(() => false)) {
      await editAction.click();
      await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 10_000 });
      await page.locator('.product-form-loading-skeleton').waitFor({ state: 'detached', timeout: 30_000 }).catch(() => {});
      const editUrl = new URL(page.url());
      candidateEditRoute = `${editUrl.pathname}${editUrl.search}`;
    }
    await auditedGoto(page, `${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    await page.locator('[data-list-query-action-bar]').waitFor({ state: 'visible', timeout: 45_000 });
    const create = page.getByRole('button', { name: /新建/ }).last();
    if (await create.count() && await create.isEnabled().catch(() => false)) {
      await create.click();
      const category = page.locator('.business-category-picker-option:visible').first();
      if (await category.count()) await category.click();
      if (await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 10_000 }).then(() => true).catch(() => false)) {
        await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 10_000 });
        await page.locator('.product-form-loading-skeleton').waitFor({ state: 'detached', timeout: 30_000 }).catch(() => {});
        if (await page.locator('.many2one-widget-shell input:visible, .many2one-combobox:visible').count()) {
          const createUrl = new URL(page.url());
          dialogRoute = `${createUrl.pathname}${createUrl.search}`;
        }
      }
    }
    if (!dialogRoute && candidateEditRoute) {
      await auditedGoto(page, `${BASE_URL}${candidateEditRoute}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});
      await page.locator('.product-form-loading-skeleton').waitFor({ state: 'detached', timeout: 30_000 }).catch(() => {});
      if (await page.locator('.many2one-widget-shell input:visible, .many2one-combobox:visible').count()) dialogRoute = candidateEditRoute;
    }
    if (!dialogRoute) continue;
    contractList = target;
    recordRoute = candidateRecordRoute;
    break;
  }
  if (!contractList || !recordRoute) throw new Error('no runtime-discovered contract list with an openable record');
  return [
    { kind: 'form', label: `${contractList.label} / 记录表单`, route: dialogRoute },
    { kind: 'dialog', label: `${contractList.label} / 关系选择弹窗`, route: dialogRoute || recordRoute.replace(/^\/r\//, '/f/') },
    { kind: 'empty', label: `${fallbackList.label} / 空列表`, route: fallbackList.route },
    { kind: 'error', label: '无权访问状态', route: '/access-denied' },
  ];
}

function publicTarget(target) {
  return {
    kind: target.kind,
    label: target.kind === 'home' ? '首页' : `${target.kind}-production-surface`,
    route_class: target.kind === 'form' || target.kind === 'dialog' ? 'runtime-discovered-record' : target.kind === 'error' ? 'access-denied' : 'runtime-discovered-list',
  };
}

function requestLooksLikeWrite(request) {
  if (request.method() === 'GET' || request.method() === 'HEAD') return false;
  const body = String(request.postData() || '');
  if (!body) return true;
  let payload;
  try { payload = JSON.parse(body); } catch { return true; }
  const operations = [];
  const walk = (value) => {
    if (!value || typeof value !== 'object') return;
    for (const [key, child] of Object.entries(value)) {
      if (['op', 'method', 'operation', 'intent'].includes(key) && typeof child === 'string') operations.push(child.toLowerCase());
      walk(child);
    }
  };
  walk(payload);
  if (operations.some((operation) => /(?:^|\.)(?:create|write|unlink|save|delete|upload)$/.test(operation))) return true;
  const dataOps = [];
  const collectDataOps = (value) => {
    if (!value || typeof value !== 'object') return;
    for (const [key, child] of Object.entries(value)) {
      if (key === 'op' && typeof child === 'string') dataOps.push(child.toLowerCase());
      collectDataOps(child);
    }
  };
  collectDataOps(payload);
  const allowedReadOps = new Set(['action_open', 'default_get', 'fields_get', 'list', 'load_views', 'name_search', 'onchange', 'read', 'read_group', 'search', 'search_read']);
  if (!dataOps.length) return true;
  return dataOps.some((operation) => !allowedReadOps.has(operation));
}

async function prepareTargetState(page, target) {
  if (target.kind === 'home') {
    await page.locator('[data-role-home]').waitFor({ state: 'visible', timeout: 45_000 });
    return {};
  }
  if (target.kind === 'list') {
    await page.locator('[data-list-query-action-bar]').waitFor({ state: 'visible', timeout: 45_000 });
    return {};
  }
  if (target.kind === 'form') {
    await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 45_000 });
    await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 45_000 });
    return {};
  }
  if (target.kind === 'empty') {
    await page.locator('[data-list-query-action-bar]').waitFor({ state: 'visible', timeout: 45_000 });
    const input = page.locator('[data-list-query-action-bar] input[type="search"]:visible, [data-list-query-action-bar] input:visible').first();
    await input.fill('__SC_COLOR_EMPTY__');
    await input.press('Enter');
    await page.locator('[data-list-status="empty"] .sc-empty').waitFor({ state: 'visible', timeout: 45_000 });
    return {};
  }
  if (target.kind === 'error') {
    await page.locator('.sc-alert-danger[role="alert"]').waitFor({ state: 'visible', timeout: 45_000 });
    return {};
  }
  if (target.kind !== 'dialog') throw new Error(`unsupported audit target kind: ${target.kind}`);
  await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 45_000 });
  await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 45_000 });
  const bodyBefore = await page.evaluate(() => ({ overflow: document.body.style.overflow, paddingRight: document.body.style.paddingRight }));
  let writeRequests = 0;
  let searchMoreCount = 0;
  let openedDialogCount = 0;
  const countWrite = (request) => { if (requestLooksLikeWrite(request)) writeRequests += 1; };
  page.on('request', countWrite);
  const comboboxes = page.locator('.many2one-combobox:visible');
  for (let index = 0; index < await comboboxes.count(); index += 1) {
    const combobox = comboboxes.nth(index);
    const opener = combobox.locator('input:visible').first();
    await opener.focus();
    await page.waitForTimeout(50);
    const searchMore = combobox.getByRole('button', { name: /搜索更多/ });
    if (!await searchMore.count()) continue;
    searchMoreCount += 1;
    await searchMore.click();
    const dialog = page.locator('[role="dialog"].relation-dialog:visible');
    await dialog.waitFor({ state: 'visible', timeout: 10_000 });
    openedDialogCount += 1;
    const result = dialog.locator('.relation-dialog-result-card:visible, .relation-dialog-table tbody tr:visible').first();
    if (!await result.waitFor({ state: 'visible', timeout: 10_000 }).then(() => true).catch(() => false)) {
      await page.keyboard.press('Escape');
      await dialog.waitFor({ state: 'hidden', timeout: 5_000 });
      continue;
    }
    const initialFocusInside = await dialog.evaluate((element) => element.contains(document.activeElement));
    await result.click();
    return { bodyBefore, countWrite, dialog, initialFocusInside, opener, writeRequests: () => writeRequests };
  }
  page.off('request', countWrite);
  throw new Error(`runtime form has no populated relation search dialog (comboboxes=${await comboboxes.count()}, search_more=${searchMoreCount}, opened=${openedDialogCount})`);
}

async function focusWithKeyboard(page, selector) {
  const setup = await page.evaluate((allowedSelector) => {
    const candidates = Array.from(document.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')).filter((element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return rect.width > 1 && rect.height > 1 && style.display !== 'none' && style.visibility !== 'hidden';
    });
    const targetIndex = candidates.findIndex((element) => element.matches(allowedSelector));
    if (targetIndex < 0) return { prepared: false, candidateCount: candidates.length, targetIndex };
    const previousIndex = targetIndex > 0 ? targetIndex - 1 : candidates.length - 1;
    const previous = candidates[previousIndex];
    if (!(previous instanceof HTMLElement)) return { prepared: false, candidateCount: candidates.length, targetIndex };
    previous.focus();
    return { prepared: true, candidateCount: candidates.length, targetIndex, previousIndex };
  }, selector);
  if (!setup.prepared) return { reached: false, tabCount: 0, ...setup };
  await page.keyboard.press('Tab');
  await page.waitForTimeout(180);
  const reached = await page.evaluate((allowedSelector) => {
    const active = document.activeElement;
    return active instanceof Element && active.matches(allowedSelector) && active.matches(':focus-visible');
  }, selector);
  return { reached, tabCount: 1, ...setup };
}

async function inspect(page, target, viewport, theme) {
  await page.setViewportSize(viewport);
  await auditedGoto(page, `${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  await page.evaluate((nextTheme) => { document.documentElement.dataset.scTheme = nextTheme; }, theme);
  await page.waitForTimeout(100);
  const targetState = await prepareTargetState(page, target);

  let openedMobileNavigation = false;
  if (target.kind !== 'dialog' && viewport.width <= 760 && !await page.locator('.workspace-activity-rail button.active:visible').count()) {
    const toggle = page.locator('.sidebar-toggle:visible').first();
    if (await toggle.count()) {
      await toggle.click();
      await page.locator('#primary-sidebar').waitFor({ state: 'visible', timeout: 5_000 });
      openedMobileNavigation = true;
    }
  }
  if (target.kind !== 'dialog') {
    for (const [activeSelector, hoverSelector] of [
      ['.activity-tab.active:visible', '.activity-tab:not(.active):visible'],
      ['.node.active.leaf:visible', '.node.leaf:not(.active):visible'],
      ['.workspace-activity-rail button.active:visible', '.workspace-activity-rail button:not(.active):visible'],
    ]) {
      if (await page.locator(activeSelector).count() && await page.locator(hoverSelector).count()) {
        await page.locator(hoverSelector).first().hover();
        break;
      }
    }
  }
  const transientStateSamples = openedMobileNavigation ? await page.evaluate(() => {
    function parseColor(raw) {
      const match = String(raw || '').match(/^rgba?\(\s*([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)(?:\s*[,/]\s*([\d.]+))?\s*\)$/i);
      return match ? { r: +match[1], g: +match[2], b: +match[3], a: match[4] === undefined ? 1 : +match[4] } : null;
    }
    function composite(foreground, background) {
      const alpha = foreground.a + background.a * (1 - foreground.a);
      return { r: (foreground.r * foreground.a + background.r * background.a * (1 - foreground.a)) / alpha, g: (foreground.g * foreground.a + background.g * background.a * (1 - foreground.a)) / alpha, b: (foreground.b * foreground.a + background.b * background.a * (1 - foreground.a)) / alpha, a: alpha };
    }
    function effectiveBackground(element) {
      const layers = []; let node = element;
      while (node instanceof Element) { const color = parseColor(getComputedStyle(node).backgroundColor); if (color && color.a > 0) layers.push(color); node = node.parentElement; }
      let result = { r: 255, g: 255, b: 255, a: 1 };
      for (const layer of layers.reverse()) result = composite(layer, result);
      return result;
    }
    function channel(value) { const x = value / 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }
    function luminance(color) { return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b); }
    function contrast(left, right) { const a = luminance(left); const b = luminance(right); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); }
    const specs = [
      ['active', '.node.active.leaf', 'nav-node'], ['hover', '.node.leaf:not(.active):hover', 'nav-node'],
      ['active', '.workspace-activity-rail button.active', 'activity-rail'], ['hover', '.workspace-activity-rail button:not(.active):hover', 'activity-rail'],
    ];
    const rows = [];
    for (const [role, selector, family] of specs) for (const element of document.querySelectorAll(selector)) {
      const style = getComputedStyle(element); const rect = element.getBoundingClientRect();
      if (rect.width <= 1 || rect.height <= 1 || style.visibility === 'hidden' || style.display === 'none') continue;
      const background = effectiveBackground(element); const text = parseColor(style.color);
      rows.push({
        role, selector, family, rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
        color: style.color, backgroundColor: style.backgroundColor, borderColor: style.borderLeftColor,
        outlineColor: style.outlineColor, outlineWidth: style.outlineWidth, boxShadow: style.boxShadow,
        textContrast: text ? contrast(composite(text, background), background) : null, borderContrast: null, focusContrast: null, saturation: 0, chroma: 0,
        viewportAreaRatio: rect.width * rect.height / (innerWidth * innerHeight), infoMisbound: false, roleBindingPass: true,
        fingerprint: [style.backgroundColor, style.color, style.borderTopColor, style.borderRightColor, style.borderBottomColor, style.borderLeftColor, style.outlineColor, style.outlineWidth, style.boxShadow, getComputedStyle(element, '::before').backgroundColor, getComputedStyle(element, '::after').backgroundColor].join('|'),
      });
    }
    return rows;
  }) : [];
  if (openedMobileNavigation) {
    await page.keyboard.press('Escape');
    await page.locator('#primary-sidebar').waitFor({ state: 'detached', timeout: 5_000 });
  }
  const targetHoverSelector = {
    form: '.form-section-nav button:not(.is-active):visible',
    dialog: '.relation-dialog-table tbody tr:not(.relation-dialog-row--active):visible',
  }[target.kind];
  if (targetHoverSelector && await page.locator(targetHoverSelector).count()) await page.locator(targetHoverSelector).first().hover();
  const focusSelector = {
    home: '.role-home-surface button',
    list: '.list-surface-column-button',
    form: '.template-page-header-actions .sc-btn-primary, [data-form-canvas] input',
    dialog: '[role="dialog"].relation-dialog button, [role="dialog"].relation-dialog input, [role="dialog"].relation-dialog [tabindex]:not([tabindex="-1"])',
    empty: '[data-list-status="empty"] .sc-empty button',
    error: '.sc-alert-danger[role="alert"] button',
  }[target.kind];
  const keyboardFocus = await focusWithKeyboard(page, focusSelector);

  const measurement = await page.evaluate(({ kind }) => {
    function parseColor(raw) {
      const value = String(raw || '').trim();
      let match = value.match(/^rgba?\(\s*([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)(?:\s*[,/]\s*([\d.]+))?\s*\)$/i);
      if (match) return { r: +match[1], g: +match[2], b: +match[3], a: match[4] === undefined ? 1 : +match[4] };
      match = value.match(/^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?\)$/i);
      if (match) return { r: +match[1] * 255, g: +match[2] * 255, b: +match[3] * 255, a: match[4] === undefined ? 1 : +match[4] };
      return null;
    }
    function composite(foreground, background) {
      const alpha = foreground.a + background.a * (1 - foreground.a);
      if (!alpha) return { r: 0, g: 0, b: 0, a: 0 };
      return {
        r: (foreground.r * foreground.a + background.r * background.a * (1 - foreground.a)) / alpha,
        g: (foreground.g * foreground.a + background.g * background.a * (1 - foreground.a)) / alpha,
        b: (foreground.b * foreground.a + background.b * background.a * (1 - foreground.a)) / alpha,
        a: alpha,
      };
    }
    function effectiveBackground(element) {
      const layers = [];
      let node = element;
      while (node instanceof Element) {
        const color = parseColor(getComputedStyle(node).backgroundColor);
        if (color && color.a > 0) layers.push(color);
        node = node.parentElement;
      }
      let result = { r: 255, g: 255, b: 255, a: 1 };
      for (const layer of layers.reverse()) result = composite(layer, result);
      return result;
    }
    function channel(value) {
      const normalized = value / 255;
      return normalized <= 0.03928 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
    }
    function luminance(color) { return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b); }
    function contrast(left, right) {
      const a = luminance(left); const b = luminance(right);
      return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    }
    function saturation(color) {
      const values = [color.r, color.g, color.b].map((value) => value / 255);
      const max = Math.max(...values); const min = Math.min(...values); const lightness = (max + min) / 2;
      return max === min ? 0 : (max - min) / (1 - Math.abs(2 * lightness - 1));
    }
    function chroma(color) { return (Math.max(color.r, color.g, color.b) - Math.min(color.r, color.g, color.b)) / 255; }
    function unionArea(rectangles) {
      const clipped = rectangles.map((rect) => ({
        left: Math.max(0, rect.left), top: Math.max(0, rect.top),
        right: Math.min(innerWidth, rect.right), bottom: Math.min(innerHeight, rect.bottom),
      })).filter((rect) => rect.right > rect.left && rect.bottom > rect.top);
      const xs = Array.from(new Set(clipped.flatMap((rect) => [rect.left, rect.right]))).sort((a, b) => a - b);
      let area = 0;
      for (let index = 0; index < xs.length - 1; index += 1) {
        const left = xs[index]; const right = xs[index + 1];
        const spans = clipped.filter((rect) => rect.left < right && rect.right > left).map((rect) => [rect.top, rect.bottom]).sort((a, b) => a[0] - b[0]);
        let height = 0; let start = -1; let end = -1;
        for (const [top, bottom] of spans) {
          if (start < 0) { start = top; end = bottom; continue; }
          if (top > end) { height += end - start; start = top; end = bottom; } else end = Math.max(end, bottom);
        }
        if (start >= 0) height += end - start;
        area += (right - left) * height;
      }
      return area;
    }
    function cssVariable(name) {
      const probe = document.createElement('span');
      probe.style.color = `var(${name})`; document.body.append(probe);
      const value = getComputedStyle(probe).color; probe.remove(); return value;
    }
    const variables = {
      infoBg: cssVariable('--sc-app-info-bg'), infoBorder: cssVariable('--sc-app-info-border'), infoText: cssVariable('--sc-app-info-text'),
      dangerBg: cssVariable('--sc-app-danger-bg'), dangerBorder: cssVariable('--sc-app-danger-border'), dangerText: cssVariable('--sc-app-danger-text'),
      focusRing: cssVariable('--sc-app-focus-ring'),
      interactive: cssVariable('--sc-semantic-surface-interactive'),
      hoverBg: cssVariable('--sc-app-hover-bg'), selectedBg: cssVariable('--sc-app-selected-bg'), selectedBorder: cssVariable('--sc-app-selected-border'), selectedText: cssVariable('--sc-app-selected-text'), navigationActiveBg: cssVariable('--sc-navigation-active-bg'),
    };
    const shared = [
      ['active', '.node.active.leaf', 'nav-node'], ['hover', '.node.leaf:not(.active):hover', 'nav-node'],
      ['active', '.activity-tab.active', 'activity-tab'], ['hover', '.activity-tab:not(.active):hover', 'activity-tab'],
      ['active', '.workspace-activity-rail button.active', 'activity-rail'], ['hover', '.workspace-activity-rail button:not(.active):hover', 'activity-rail'],
    ];
    const specsByKind = {
      home: [
      ['ordinary', '.layout-shell'], ['ordinary', '.layout-main'], ['ordinary', '.workspace-sidebar-panel'],
      ['ordinary', '.role-home-surface__tasks'], ['ordinary', '.role-home-surface__overview'], ['ordinary', '.role-home-surface__access'],
      ['ordinary', '.role-home-surface__summary-list article'], ['ordinary', '.role-home-surface__link-list--quick button'],
      ...shared, ['focus', '.role-home-surface button:focus-visible'],
      ],
      list: [
      ['ordinary', '.layout-shell'], ['ordinary', '.layout-main'], ['ordinary', '.workspace-sidebar-panel'],
      ['ordinary', '[data-list-query-action-bar]'], ['ordinary', '.list-surface-column-button'], ['ordinary', '.table thead th'], ['ordinary', '.pagination-footer'],
      ['primary', '.toolbar-search-submit'], ...shared, ['focus', '.list-surface-column-button:focus-visible'],
      ],
      form: [
        ['ordinary', '.layout-shell'], ['ordinary', '.layout-main'], ['ordinary', '[data-form-canvas]'], ['ordinary', '[data-form-canvas] .field'],
        ['primary', '.template-page-header-actions .sc-btn-primary'],
        ['active', '.form-section-nav button.is-active', 'form-section-nav'], ['hover', '.form-section-nav button:not(.is-active):hover', 'form-section-nav'],
        ['focus', '.template-page-header-actions .sc-btn-primary:focus-visible, [data-form-canvas] input:focus-visible'],
      ],
      dialog: [
        ['ordinary', '[role="dialog"].relation-dialog'], ['ordinary', '.relation-dialog-search'], ['ordinary', '.relation-dialog-footer'],
        ['primary', '.relation-dialog-footer .sc-btn-primary'],
        ['active', '.relation-dialog-row--active, .relation-dialog-result-card--active', 'relation-result'],
        ['hover', '.relation-dialog-table tbody tr:not(.relation-dialog-row--active):hover', 'relation-result'],
        ['focus', '[role="dialog"].relation-dialog :focus-visible'],
      ],
      empty: [
        ['ordinary', '.layout-shell'], ['ordinary', '.layout-main'], ['ordinary', '[data-list-status="empty"] .sc-empty'],
        ['primary', '[data-list-status="empty"] .sc-empty .sc-btn-primary'], ['focus', '[data-list-status="empty"] .sc-empty button:focus-visible'],
      ],
      error: [
        ['ordinary', '.layout-shell'], ['ordinary', '.layout-main'], ['danger', '.sc-alert-danger[role="alert"]'], ['focus', '.sc-alert-danger[role="alert"] button:focus-visible'],
      ],
    };
    const specs = specsByKind[kind] || [];
    const samples = [];
    for (const [role, selector, family = selector] of specs) {
      for (const element of Array.from(document.querySelectorAll(selector)).slice(0, 8)) {
        const rect = element.getBoundingClientRect(); const style = getComputedStyle(element);
        if (rect.width <= 1 || rect.height <= 1 || style.display === 'none' || style.visibility === 'hidden') continue;
        const background = effectiveBackground(element);
        const text = parseColor(style.color);
        const outline = parseColor(style.outlineColor);
        const border = parseColor(style.borderLeftColor);
        const adjacent = effectiveBackground(element.parentElement || element);
        const textComposite = text ? composite(text, background) : null;
        const focusVisible = element.matches(':focus-visible');
        const shadowFocus = focusVisible && style.boxShadow.includes(variables.focusRing) ? parseColor(variables.focusRing) : null;
        const outlineWidth = parseFloat(style.outlineWidth);
        const productOutline = focusVisible && outlineWidth >= 2 && [variables.focusRing, variables.interactive].includes(style.outlineColor) ? outline : null;
        const focusForeground = shadowFocus || productOutline;
        const focusWidth = shadowFocus ? 3 : productOutline ? outlineWidth : 0;
        const focusComposite = focusForeground ? composite(focusForeground, adjacent) : null;
        const fingerprint = [style.backgroundColor, style.color, style.borderTopColor, style.borderRightColor, style.borderBottomColor, style.borderLeftColor, style.outlineColor, style.outlineWidth, style.boxShadow, getComputedStyle(element, '::before').backgroundColor, getComputedStyle(element, '::after').backgroundColor].join('|');
        samples.push({
          role, selector, family, rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
          element: { tag: element.tagName.toLowerCase(), className: String(element.className || '').slice(0, 160) },
          color: style.color, backgroundColor: style.backgroundColor, borderColor: style.borderLeftColor,
          outlineColor: style.outlineColor, outlineWidth: style.outlineWidth, boxShadow: style.boxShadow,
          textContrast: textComposite ? contrast(textComposite, background) : null,
          borderContrast: border ? contrast(composite(border, adjacent), adjacent) : null,
          focusContrast: focusForeground && focusWidth >= 2 ? contrast(focusComposite, adjacent) : null,
          focusForeground,
          focusAdjacent: adjacent,
          focusWidth,
          focusVisible,
          fingerprint,
          saturation: saturation(background),
          chroma: chroma(background),
          viewportAreaRatio: rect.width * rect.height / (innerWidth * innerHeight),
          infoMisbound: role === 'ordinary' && [variables.infoBg, variables.infoBorder, variables.infoText].includes(style.backgroundColor)
            || role === 'ordinary' && [variables.infoBg, variables.infoBorder, variables.infoText].includes(style.borderLeftColor)
            || role === 'ordinary' && [variables.infoBg, variables.infoBorder, variables.infoText].includes(style.color),
          roleBindingPass: role === 'danger'
            ? style.backgroundColor === variables.dangerBg && style.borderLeftColor === variables.dangerBorder && style.color === variables.dangerText
            : family === 'form-section-nav' && role === 'active'
              ? style.backgroundColor === variables.navigationActiveBg && style.color === variables.selectedText
            : family === 'relation-result' && role === 'active'
              ? style.backgroundColor === variables.selectedBg && style.backgroundColor !== variables.hoverBg
            : role !== 'ordinary' || ![variables.dangerBg, variables.dangerBorder, variables.dangerText].includes(style.backgroundColor)
              && ![variables.dangerBg, variables.dangerBorder, variables.dangerText].includes(style.borderLeftColor)
              && ![variables.dangerBg, variables.dangerBorder, variables.dangerText].includes(style.color),
        });
      }
    }
    const saturatedRects = samples.filter((row) => row.role === 'ordinary' && row.saturation >= 0.45 && row.chroma >= 0.25).map((row) => ({ left: row.rect.x, top: row.rect.y, right: row.rect.x + row.rect.width, bottom: row.rect.y + row.rect.height }));
    const saturatedArea = unionArea(saturatedRects) / (innerWidth * innerHeight);
    return { variables, samples, saturatedRects, saturatedArea };
  }, { kind: target.kind });
  measurement.keyboard_focus = keyboardFocus;
  measurement.samples.push(...transientStateSamples);
  measurement.viewport = { width: viewport.width, height: viewport.height };
  const mobileHomeStateNotApplicable = viewport.width <= 760 && target.kind === 'home' && !measurement.samples.some((row) => row.role === 'active');
  const requiredRolesByKind = {
    home: mobileHomeStateNotApplicable ? ['ordinary', 'focus'] : ['ordinary', 'active', 'hover', 'focus'],
    list: ['ordinary', 'primary', 'active', 'hover', 'focus'],
    form: ['ordinary', 'primary', 'active', 'hover', 'focus'],
    dialog: viewport.width > 760 ? ['ordinary', 'primary', 'active', 'hover', 'focus'] : ['ordinary', 'primary', 'active', 'focus'],
    empty: ['ordinary', 'primary', 'focus'],
    error: ['ordinary', 'danger', 'focus'],
  };
  const requiredRoles = requiredRolesByKind[target.kind] || [];
  measurement.state_role_na = mobileHomeStateNotApplicable ? {
    roles: ['active', 'hover'],
    reason_code: 'MOBILE_ROLE_HOME_HAS_NO_PERSISTENT_SELECTED_NAVIGATION',
    covered_by: 'same target at 1440 light/dark',
  } : null;
  measurement.required_roles = requiredRoles;
  measurement.role_counts = Object.fromEntries(requiredRoles.map((role) => [role, measurement.samples.filter((row) => row.role === role).length]));
  measurement.checks = evaluateColorContract(measurement, requiredRoles);
  if (target.kind === 'dialog') {
    const relationLabels = (await page.locator('.relation-dialog-result-facts small:visible, .relation-dialog-table th:visible').allTextContents())
      .map((value) => String(value || '').trim()).filter(Boolean);
    measurement.relation_business_labels = relationLabels;
    measurement.checks.visible_relation_labels_chinese = relationLabels.length > 0
      && relationLabels.every((label) => /[\u3400-\u9fff]/u.test(label));
  }
  const screenshot = path.join(OUTPUT, `${target.kind}-${viewport.key}-${theme}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  if (target.kind === 'dialog') {
    const dialog = targetState.dialog;
    const focusables = dialog.locator('a[href]:visible, button:not([disabled]):visible, input:not([disabled]):visible, select:not([disabled]):visible, textarea:not([disabled]):visible, [tabindex]:not([tabindex="-1"]):visible');
    const focusableCount = await focusables.count();
    let forwardWrapped = false;
    let backwardWrapped = false;
    if (focusableCount > 1) {
      const first = focusables.first();
      const last = focusables.last();
      await last.focus();
      await page.keyboard.press('Tab');
      forwardWrapped = await first.evaluate((element) => document.activeElement === element);
      await first.focus();
      await page.keyboard.press('Shift+Tab');
      backwardWrapped = await last.evaluate((element) => document.activeElement === element);
    }
    await page.keyboard.press('Escape');
    const escapeClosed = await dialog.waitFor({ state: 'hidden', timeout: 5_000 }).then(() => true).catch(() => false);
    await page.waitForFunction((element) => document.activeElement === element, await targetState.opener.elementHandle(), { timeout: 2_000 }).catch(() => {});
    const focusRestored = await targetState.opener.evaluate((element) => document.activeElement === element);
    const bodyAfter = await page.evaluate(() => ({ overflow: document.body.style.overflow, paddingRight: document.body.style.paddingRight }));
    const lifecycle = {
      escapeClosed,
      focusRestored,
      focusTrapped: targetState.initialFocusInside && focusableCount > 1 && forwardWrapped && backwardWrapped,
      bodyLockRestored: JSON.stringify(bodyAfter) === JSON.stringify(targetState.bodyBefore),
      writeRequests: targetState.writeRequests(),
    };
    page.off('request', targetState.countWrite);
    measurement.dialog_lifecycle = lifecycle;
    Object.assign(measurement.checks, evaluateDialogLifecycle(lifecycle));
  }
  return { target: publicTarget(target), viewport, theme, measurement, screenshot: path.relative(acceptance.root, screenshot) };
}

async function negativeFixtures(page) {
  const raw = await page.evaluate(() => {
    function rgb(raw) { const row = String(raw || '').match(/rgba?\((\d+)[, ]+(\d+)[, ]+(\d+)(?:\s*[,/]\s*([\d.]+))?/); return row ? { r: +row[1], g: +row[2], b: +row[3], a: row[4] === undefined ? 1 : +row[4] } : null; }
    function channel(value) { const x = value / 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }
    function lum(c) { return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b); }
    function ratio(a, b) { const x = lum(a); const y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
    const host = document.createElement('div'); host.id = 'color-negative-fixtures'; document.body.append(host);
    const info = document.createElement('div'); info.style.background = 'var(--sc-app-info-bg)'; host.append(info);
    const infoProbe = document.createElement('div'); infoProbe.style.color = 'var(--sc-app-info-bg)'; host.append(infoProbe);
    const infoDetected = getComputedStyle(info).backgroundColor === getComputedStyle(infoProbe).color;
    const weak = document.createElement('button'); weak.style.cssText = 'outline:3px solid rgba(0,182,254,.18);background:#fff'; host.append(weak);
    const weakColor = rgb(getComputedStyle(weak).outlineColor); const white = { r: 255, g: 255, b: 255, a: 1 };
    const weakComposite = weakColor ? { r: weakColor.r * weakColor.a + 255 * (1 - weakColor.a), g: weakColor.g * weakColor.a + 255 * (1 - weakColor.a), b: weakColor.b * weakColor.a + 255 * (1 - weakColor.a), a: 1 } : white;
    const weakDetected = ratio(weakComposite, white) < 3;
    const hover = document.createElement('div'); const active = document.createElement('div'); hover.style.background = '#eff6ff'; active.style.background = '#eff6ff'; host.append(hover, active);
    const indistinguishableDetected = getComputedStyle(hover).backgroundColor === getComputedStyle(active).backgroundColor;
    const saturated = document.createElement('div'); saturated.style.cssText = 'position:fixed;inset:0 20% 40% 0;background:#2563eb'; host.append(saturated);
    const rect = saturated.getBoundingClientRect(); const saturatedDetected = rect.width * rect.height / (innerWidth * innerHeight) > 0.25;
    host.remove();
    return { infoDetected, weakDetected, weakColor, white, weakContrast: ratio(weakComposite, white), indistinguishableDetected, saturatedDetected, saturatedArea: rect.width * rect.height / (innerWidth * innerHeight) };
  });
  const base = { variables: { selectedBg: 'selected', hoverBg: 'hover' }, keyboard_focus: { reached: true }, saturatedArea: 0, samples: [] };
  const fixtures = [
    {
      fixture: 'ordinary_surface_uses_info', reason_code: 'COLOR_ROLE_MISBOUND', target_check: 'semantic_color_role_binding_pass',
      measurement: { ...base, samples: [{ role: 'ordinary', infoMisbound: raw.infoDetected, textContrast: 21, fingerprint: 'ordinary' }] }, required: ['ordinary'],
    },
    {
      fixture: 'weak_transparent_focus', reason_code: 'FOCUS_CONTRAST_LT_3', target_check: 'focus_contrast_pass',
      measurement: { ...base, samples: [{ role: 'focus', infoMisbound: false, textContrast: 21, focusContrast: raw.weakContrast, focusForeground: raw.weakColor, focusAdjacent: raw.white, focusWidth: 3, fingerprint: 'focus' }] }, required: ['focus'],
    },
    {
      fixture: 'active_equals_hover', reason_code: 'ACTIVE_HOVER_INDISTINGUISHABLE', target_check: 'navigation_state_distinct',
      measurement: { ...base, samples: [{ role: 'active', family: 'fixture-state', infoMisbound: false, textContrast: 21, fingerprint: 'same' }, { role: 'hover', family: 'fixture-state', infoMisbound: false, textContrast: 21, fingerprint: 'same' }] }, required: ['active', 'hover'],
    },
    {
      fixture: 'large_saturated_panel', reason_code: 'SATURATED_AREA_BUDGET_EXCEEDED', target_check: 'large_saturated_surface_budget_pass',
      measurement: {
        ...base,
        viewport: { width: 100, height: 100 },
        saturatedRects: [{ left: -10, top: 0, right: 60, bottom: 60 }, { left: 40, top: 0, right: 110, bottom: 60 }],
        samples: [{ role: 'ordinary', infoMisbound: false, textContrast: 21, fingerprint: 'saturated' }],
      },
      required: ['ordinary'],
    },
  ];
  const colorFixtures = fixtures.map((fixture) => {
    const checks = evaluateColorContract(fixture.measurement, fixture.required);
    const failedChecks = Object.entries(checks).filter(([key, passed]) => key !== 'role_sample_counts' && !passed).map(([key]) => key);
    return {
      fixture: fixture.fixture,
      reason_code: fixture.reason_code,
      target_check: fixture.target_check,
      detected: failedChecks.length === 1 && failedChecks[0] === fixture.target_check,
      failed_checks: failedChecks,
    };
  });
  const dangerChecks = evaluateColorContract({
    ...base,
    samples: [{ role: 'danger', infoMisbound: false, roleBindingPass: false, textContrast: 7, fingerprint: 'danger-info' }],
  }, ['danger']);
  colorFixtures.push({
    fixture: 'danger_surface_uses_info',
    reason_code: 'DANGER_ROLE_MISBOUND',
    target_check: 'semantic_color_role_binding_pass',
    detected: Object.entries(dangerChecks).filter(([, passed]) => !passed).map(([key]) => key).join(',') === 'semantic_color_role_binding_pass',
    failed_checks: Object.entries(dangerChecks).filter(([, passed]) => !passed).map(([key]) => key),
  });
  for (const [fixture, reasonCode, targetCheck, lifecycle] of [
    ['dialog_escape_ignored', 'DIALOG_ESCAPE_IGNORED', 'dialog_escape_closes', { escapeClosed: false, focusRestored: true, focusTrapped: true, bodyLockRestored: true, writeRequests: 0 }],
    ['dialog_focus_not_restored', 'DIALOG_FOCUS_NOT_RESTORED', 'dialog_focus_restored', { escapeClosed: true, focusRestored: false, focusTrapped: true, bodyLockRestored: true, writeRequests: 0 }],
  ]) {
    const checks = evaluateDialogLifecycle(lifecycle);
    const failedChecks = Object.entries(checks).filter(([, passed]) => !passed).map(([key]) => key);
    colorFixtures.push({ fixture, reason_code: reasonCode, target_check: targetCheck, detected: failedChecks.length === 1 && failedChecks[0] === targetCheck, failed_checks: failedChecks });
  }
  return colorFixtures;
}

const candidateStart = await sourceEvidence();
const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: VIEWPORTS[0] });
const page = await context.newPage();
const navigation = captureReleasedNavigation(page);
const runtime = { console_errors: [], page_errors: [], failed_responses: [], request_failures: [], expected_navigation_aborts: [] };
const observedAssetPaths = new Set();
page.on('console', (message) => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) runtime.console_errors.push(sanitizeRuntimeText(message.text())); });
page.on('pageerror', (error) => runtime.page_errors.push(sanitizeRuntimeText(error.message)));
page.on('response', (response) => {
  const url = new URL(response.url());
  if (url.pathname.startsWith('/assets/') && /\.(?:js|css)$/.test(url.pathname)) observedAssetPaths.add(url.pathname);
  if (response.status() >= 400) runtime.failed_responses.push({ status: response.status(), path: url.pathname });
});
page.on('requestfailed', (request) => {
  const failure = sanitizeRuntimeText(request.failure()?.errorText || 'request failed');
  const row = { path: safeRequestPath(request.url()), error: failure };
  if (/ERR_ABORTED/i.test(failure) && activeAuditNavigation && row.path === '/api/v1/intent' && ['fetch', 'xhr'].includes(request.resourceType())) {
    runtime.expected_navigation_aborts.push({ ...row, navigation_id: activeAuditNavigation.id, navigation_target_path: activeAuditNavigation.target_path, observed_at: new Date().toISOString() });
  }
  else runtime.request_failures.push(row);
});

try {
  await login(page, navigation);
  const listTarget = await findList(page, navigation);
  const extendedTargets = await findExtendedTargets(page, navigation, listTarget);
  const targets = [{ kind: 'home', label: '首页', route: '/' }, { kind: 'list', ...listTarget }, ...extendedTargets];
  const rows = [];
  for (const viewport of VIEWPORTS) for (const theme of THEMES) for (const target of targets) rows.push(await inspect(page, target, viewport, theme));
  await auditedGoto(page, `${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  const fixtures = await negativeFixtures(page);
  const writeDetectorSelfTest = {
    params_op_write_detected: requestLooksLikeWrite({ method: () => 'POST', postData: () => JSON.stringify({ intent: 'api.data', params: { op: 'write' } }) }),
    unknown_post_json_failed_closed: requestLooksLikeWrite({ method: () => 'POST', postData: () => JSON.stringify({ intent: 'unknown.readonly' }) }),
    params_op_read_allowed: !requestLooksLikeWrite({ method: () => 'POST', postData: () => JSON.stringify({ intent: 'api.data', params: { op: 'read' } }) }),
  };
  const provenance = await sourceEvidence([...observedAssetPaths]);
  provenance.candidate_stable_during_audit = provenance.head === candidateStart.head && provenance.dirty_fingerprint_sha256 === candidateStart.dirty_fingerprint_sha256;
  provenance.release_built_before_audit = Date.parse(provenance.release_built_at) <= Date.parse(AUDIT_STARTED_AT);
  const failures = rows.flatMap((row) => Object.entries(row.measurement.checks).filter(([, passed]) => !passed)
    .map(([check]) => ({ target: row.target, viewport: row.viewport, theme: row.theme, check })));
  if (!fixtures.every((fixture) => fixture.detected)) failures.push({ check: 'negative_fixture_detection_incomplete', fixtures });
  if (!Object.values(writeDetectorSelfTest).every(Boolean)) failures.push({ check: 'write_detector_self_test_failed' });
  if (!provenance.served_bundle_matches_local_release) failures.push({ check: 'served_bundle_does_not_match_local_release' });
  if (!provenance.candidate_stable_during_audit) failures.push({ check: 'candidate_changed_during_audit' });
  if (!provenance.release_built_before_audit) failures.push({ check: 'release_build_not_older_than_audit' });
  const passed = failures.length === 0 && !runtime.console_errors.length && !runtime.page_errors.length && !runtime.failed_responses.length && !runtime.request_failures.length;
  const report = {
    schema: 'frontend_color_role_browser_audit.v3',
    source: { profile: acceptance.profile, operation: acceptance.operation, expected_sha: acceptance.provenance.expectedSha || null, provenance },
    evidence_classification: 'isolated acceptance fixture; relative artifact paths; credentials and request query strings omitted',
    audit_started_at: AUDIT_STARTED_AT,
    audit_completed_at: new Date().toISOString(),
    targets: targets.map(publicTarget),
    rows,
    negative_fixtures: fixtures,
    write_detector_self_test: writeDetectorSelfTest,
    runtime,
    failures,
    summary: { rows: rows.length, negative_detected: fixtures.filter((row) => row.detected).length, negative_total: fixtures.length, failures: failures.length, runtime_errors: runtime.console_errors.length + runtime.page_errors.length + runtime.failed_responses.length + runtime.request_failures.length },
    passed,
  };
  let serialized = JSON.stringify(report, null, 2);
  const sensitiveValues = [PASSWORD, LOGIN, DATABASE, acceptance.root].filter((value) => String(value || '').length >= 4);
  const leaked = sensitiveValues.filter((value) => serialized.includes(value));
  if (leaked.length) {
    report.failures.push({ check: 'sensitive_evidence_detected', count: leaked.length });
    report.summary.failures = report.failures.length;
    report.passed = false;
    serialized = JSON.stringify(report, null, 2);
    for (const value of leaked) serialized = serialized.split(value).join('<redacted>');
  }
  await fs.writeFile(REPORT, `${serialized}\n`, 'utf8');
  process.stdout.write(`[frontend_color_role_browser_audit] ${report.passed ? 'PASS' : 'FAIL'} rows=${rows.length} failures=${report.failures.length} negative=${report.summary.negative_detected}/${report.summary.negative_total}\n`);
  if (!report.passed) process.exitCode = 1;
} finally {
  await context.close(); await browser.close();
}

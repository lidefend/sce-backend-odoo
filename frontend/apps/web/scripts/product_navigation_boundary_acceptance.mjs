import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';
import process from 'node:process';

const BASE_URL = String(process.env.BASE_URL || 'http://127.0.0.1:18081').replace(/\/$/, '');
const LOGIN = process.env.LOGIN || 'admin';
const PASSWORD = process.env.PASSWORD || 'admin';
const DB_NAME = process.env.DB_NAME || '';

function check(condition, message, details = {}) {
  if (condition) return;
  const error = new Error(message);
  error.details = details;
  throw error;
}

function observe(page, evidence) {
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon')) evidence.errors.push(`console:${message.text()}`);
  });
  page.on('pageerror', (error) => evidence.errors.push(`page:${error.message}`));
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) evidence.errors.push(`http:${response.status()}:${response.url()}`);
  });
  page.on('request', (request) => {
    if (request.method() !== 'POST') return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch { body = {}; }
    const intent = String(body.intent || '');
    const method = String(body?.params?.method || body.method || '');
    if (/(^|\.)(create|write|unlink|execute_button|upload)(\.|$)/.test(intent) || /^(create|write|unlink|web_save|action_)/.test(method)) evidence.mutations += 1;
  });
}

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input.sc-input');
  await inputs.nth(0).fill(LOGIN);
  await inputs.nth(1).fill(PASSWORD);
  if (DB_NAME && await inputs.nth(2).isEditable()) await inputs.nth(2).fill(DB_NAME);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('[data-semantic-component="ProductAppShell"]').waitFor({ state: 'visible', timeout: 45000 });
}

function canonicalNode(page, menuId, actionId) {
  return page.locator(`[data-navigation-node="canonical"][data-navigation-menu-id="${menuId}"][data-navigation-action-id="${actionId}"]`);
}

function nodeByLabel(page, label) {
  return page.locator('[data-navigation-node="canonical"]').filter({ hasText: label }).first();
}

async function expandNode(page, label) {
  const node = nodeByLabel(page, label);
  check(await node.count() === 1, `${label} canonical navigation node must be unique`, { count: await node.count() });
  const toggle = node.locator(':scope > .t-submenu__title');
  if (await toggle.getAttribute('aria-expanded') !== 'true') await toggle.click();
  return node;
}

async function desktopJourney(browser, report) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const page = await context.newPage();
  observe(page, report);
  await login(page);
  await page.locator('[data-navigation-state="ready"] [data-semantic-component="ProductSideNavigation"]')
    .waitFor({ state: 'visible', timeout: 45000 });

  const projectGroup = await expandNode(page, '项目中心');
  await expandNode(page, '项目创建');
  const target = canonicalNode(page, 679, 859);
  check(await target.count() === 1, '项目完整工作区必须拥有唯一 canonical menu/action 身份', { count: await target.count() });
  const targetButton = target;
  check((await targetButton.textContent() || '').trim() === '项目信息编辑', '项目工作区菜单标签漂移');
  const depth = Number(await target.getAttribute('data-navigation-depth'));
  check(depth >= 2, '正式项目入口必须保留三级父子层级', { depth });

  const sourceUrl = page.url();
  await targetButton.click();
  await page.waitForURL((url) => url.pathname === '/a/859' && url.searchParams.get('menu_id') === '679', { timeout: 45000 });
  const firstTarget = page.url();
  check(await page.locator('[data-navigation-node="canonical"][aria-current="page"]').count() === 1, '当前叶子菜单必须恰好一个');

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-navigation-state="ready"]').waitFor({ timeout: 45000 });
  check(page.url() === firstTarget, '刷新必须恢复相同 action/menu 深链', { firstTarget, afterReload: page.url() });
  check(await page.locator('[data-navigation-node="canonical"][aria-current="page"]').count() === 1, '刷新后当前叶子菜单必须保持唯一');

  const collapsibleGroup = await expandNode(page, '合同中心');
  const collapsibleToggle = collapsibleGroup.locator(':scope > .t-submenu__title');
  const beforeCollapse = await collapsibleToggle.getAttribute('aria-expanded');
  await collapsibleToggle.click();
  const afterCollapse = await collapsibleToggle.getAttribute('aria-expanded');
  check(beforeCollapse !== afterCollapse, '桌面导航折叠状态必须可切换');
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-navigation-state="ready"]').waitFor({ timeout: 45000 });
  const reloadedCollapsibleGroup = nodeByLabel(page, '合同中心');
  check(await reloadedCollapsibleGroup.locator(':scope > .t-submenu__title').getAttribute('aria-expanded') === afterCollapse, '桌面导航折叠偏好必须在刷新后保持');

  await page.goBack({ waitUntil: 'domcontentloaded' });
  await page.goForward({ waitUntil: 'domcontentloaded' });
  await page.locator('[data-navigation-state="ready"]').waitFor({ timeout: 45000 });
  check(new URL(page.url()).searchParams.get('menu_id') === '679', '浏览器前进后退不得丢失 menu identity');

  report.desktop = { sourceUrl, firstTarget, depth, activeLeafCount: 1, collapsePersisted: true };
  await context.close();
}

async function mobileJourney(browser, report) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'zh-CN' });
  const page = await context.newPage();
  observe(page, report);
  await login(page);
  const menuButton = page.getByRole('button', { name: '菜单', exact: true });
  await menuButton.click();
  const drawer = page.locator('[data-semantic-component="ProductMobileNavigationDrawer"][role="dialog"]');
  await drawer.waitFor({ state: 'visible', timeout: 15000 });
  check(await drawer.getAttribute('aria-modal') === 'true', '移动导航必须使用 modal Drawer 语义');
  await page.keyboard.press('Escape');
  await drawer.waitFor({ state: 'hidden', timeout: 15000 });
  check(await menuButton.evaluate((element) => element === document.activeElement), '关闭 Drawer 后必须恢复菜单按钮焦点');
  const overflow = await page.evaluate(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth);
  check(overflow <= 0, '390px 导航外壳不得产生横向溢出', { overflow });
  report.mobile = { drawerRole: 'dialog', escapeClosed: true, focusRestored: true, overflow };
  await context.close();
}

async function main() {
  const browser = await launchChromium({ headless: true });
  const report = { baseUrl: BASE_URL, login: LOGIN, errors: [], mutations: 0 };
  try {
    await desktopJourney(browser, report);
    await mobileJourney(browser, report);
    check(report.errors.length === 0, '导航旅程存在浏览器错误', { errors: report.errors });
    check(report.mutations === 0, '只读导航旅程不得产生业务 mutation', { mutations: report.mutations });
    report.pass = true;
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error('[product_navigation_boundary_acceptance] FAIL', error.message);
  if (error.details) console.error(JSON.stringify(error.details, null, 2));
  process.exit(1);
});

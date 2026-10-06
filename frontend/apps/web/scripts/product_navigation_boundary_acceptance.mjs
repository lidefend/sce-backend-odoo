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
  const usernameInput = page.getByPlaceholder('请输入账号');
  const passwordInput = page.getByPlaceholder('请输入密码');
  await usernameInput.waitFor({ state: 'visible', timeout: 45000 });
  await usernameInput.fill(LOGIN);
  await passwordInput.fill(PASSWORD);
  if (DB_NAME) {
    const databaseInput = page.getByPlaceholder('请输入数据库名（如 sc_minimal）');
    if (await databaseInput.count()) await databaseInput.fill(DB_NAME);
  }
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('[data-semantic-component="ProductAppShell"]').waitFor({ state: 'visible', timeout: 45000 });
}

function nodeByLabel(page, label) {
  return page.locator(`[data-navigation-node="canonical"][data-navigation-label="${label}"]`);
}

async function submenuToggle(node, label) {
  const toggle = node.locator('[data-navigation-toggle="submenu"]').first();
  await toggle.waitFor({ state: 'visible', timeout: 15000 });
  const toggleLabel = String(await toggle.textContent() || '').trim();
  check(toggleLabel === label, `${label} 分组标题必须与其业务标签一致`, { toggleLabel });
  return toggle;
}

async function expandNode(page, label) {
  const node = nodeByLabel(page, label);
  check(await node.count() === 1, `${label} canonical navigation node must be unique`, { count: await node.count() });
  const children = node.locator('[data-navigation-node="canonical"]');
  check(await children.count() > 0, `${label} 必须是可展开的分组节点`, { childCount: await children.count() });
  if (!(await children.first().isVisible())) {
    await (await submenuToggle(node, label)).click();
    await children.first().waitFor({ state: 'visible', timeout: 15000 });
  }
  return node;
}

async function navigationLabels(page) {
  return page.locator('[data-navigation-node="canonical"]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-navigation-label')));
}

async function desktopJourney(browser, report) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const page = await context.newPage();
  observe(page, report);
  await login(page);
  await page.locator('[data-navigation-state="ready"] [data-semantic-component="ProductSideNavigation"]')
    .waitFor({ state: 'visible', timeout: 45000 });

  await expandNode(page, '项目中心');
  await expandNode(page, '项目台账');
  const target = page.locator(
    '[data-navigation-node="canonical"][data-navigation-label="项目中心"] '
    + '[data-navigation-node="canonical"][data-navigation-label="项目台账"] '
    + '[data-navigation-node="canonical"][data-navigation-label="项目台账"]',
  );
  check(await target.count() === 1, '项目完整工作区必须拥有唯一 canonical menu/action 身份', { count: await target.count() });
  check((await target.textContent() || '').trim() === '项目台账', '项目工作区菜单标签漂移');
  const depth = Number(await target.getAttribute('data-navigation-depth'));
  check(depth >= 2, '正式项目入口必须保留三级父子层级', { depth });
  const targetMenuId = String(await target.getAttribute('data-navigation-menu-id') || '');
  const targetActionId = String(await target.getAttribute('data-navigation-action-id') || '');
  check(/^\d+$/.test(targetMenuId) && /^\d+$/.test(targetActionId), '项目工作区入口必须绑定真实 menu/action 身份', { targetMenuId, targetActionId });

  const sourceUrl = page.url();
  await target.click();
  await page.waitForURL((url) => url.pathname === `/a/${targetActionId}` && url.searchParams.get('menu_id') === targetMenuId, { timeout: 45000 });
  const firstTarget = page.url();
  check(await page.locator('[data-navigation-node="canonical"][aria-current="page"]').count() === 1, '当前叶子菜单必须恰好一个');

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-navigation-state="ready"]').waitFor({ timeout: 45000 });
  check(page.url() === firstTarget, '刷新必须恢复相同 action/menu 深链', { firstTarget, afterReload: page.url() });
  check(await page.locator('[data-navigation-node="canonical"][aria-current="page"]').count() === 1, '刷新后当前叶子菜单必须保持唯一');

  const collapsibleGroup = await expandNode(page, '合同中心');
  const collapsibleChildren = collapsibleGroup.locator('[data-navigation-node="canonical"]');
  await (await submenuToggle(collapsibleGroup, '合同中心')).click();
  await collapsibleChildren.first().waitFor({ state: 'hidden', timeout: 15000 });
  check(!(await collapsibleChildren.first().isVisible()), '桌面导航折叠状态必须可切换');
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-navigation-state="ready"]').waitFor({ timeout: 45000 });
  const reloadedCollapsibleGroup = nodeByLabel(page, '合同中心');
  check(await reloadedCollapsibleGroup.count() === 1, '刷新后合同中心节点必须仍唯一', { count: await reloadedCollapsibleGroup.count() });
  check(!(await reloadedCollapsibleGroup.locator('[data-navigation-node="canonical"]').first().isVisible()), '桌面导航折叠偏好必须在刷新后保持');

  await page.goBack({ waitUntil: 'domcontentloaded' });
  await page.goForward({ waitUntil: 'domcontentloaded' });
  await page.locator('[data-navigation-state="ready"]').waitFor({ timeout: 45000 });
  check(new URL(page.url()).searchParams.get('menu_id') === targetMenuId, '浏览器前进后退不得丢失 menu identity');

  const canonicalLabels = await navigationLabels(page);
  const product_configuration_entry_count = canonicalLabels.filter((label) => label === '产品配置').length;
  const legacy_configuration_entry_count = canonicalLabels.filter((label) => label === '配置中心').length;
  check(product_configuration_entry_count === 1, '产品配置入口必须唯一', { product_configuration_entry_count, canonicalLabels });
  check(legacy_configuration_entry_count === 0, '旧配置中心入口必须被拒绝', { legacy_configuration_entry_count, canonicalLabels });

  await expandNode(page, '产品配置');
  const formConfigurationEntry = nodeByLabel(page, '表单配置');
  check(await formConfigurationEntry.count() === 1, '产品配置必须发布唯一表单配置入口', { count: await formConfigurationEntry.count() });
  check((await formConfigurationEntry.textContent() || '').trim() === '表单配置', '产品配置子入口业务标签漂移');
  await formConfigurationEntry.click();
  await page.waitForURL((url) => url.pathname.startsWith('/admin/business-config'), { timeout: 45000 });
  const workbench = page.locator('.business-config-page');
  await workbench.waitFor({ state: 'visible', timeout: 45000 });
  check(await workbench.getAttribute('data-page-sections-ready') === 'true', '配置工作台页面契约区块必须就绪');

  // The workbench publishes its configuration tasks only after a business page is
  // selected from the governed catalog. Walk that real path instead of asserting a
  // menu-config entry the current published menu tree does not contain.
  const pagePicker = page.getByRole('button', { name: '选择业务页面', exact: true }).first();
  await pagePicker.waitFor({ state: 'visible', timeout: 60000 });
  const firstPageChoice = page.getByRole('button', { name: '选择', exact: true }).first();
  await firstPageChoice.waitFor({ state: 'visible', timeout: 60000 });
  await firstPageChoice.click();
  await page.waitForURL(
    (url) => url.searchParams.has('model') && url.searchParams.has('action_id'),
    { timeout: 45000 },
  );
  const configuredPage = new URL(page.url());
  const configuredModel = String(configuredPage.searchParams.get('model') || '');
  const configuredActionId = String(configuredPage.searchParams.get('action_id') || '');
  check(configuredModel.length > 0, '配置工作台必须绑定真实业务模型身份', { configuredModel });
  check(/^\d+$/.test(configuredActionId), '配置工作台必须绑定真实业务动作身份', { configuredActionId });

  const menuConfigurationAction = page.getByRole('button', { name: '配置菜单', exact: true });
  await menuConfigurationAction.first().waitFor({ state: 'visible', timeout: 45000 });
  await menuConfigurationAction.first().click();
  await page.waitForURL((url) => url.pathname === '/admin/menu-config', { timeout: 45000 });
  const menuConfigurationHeading = page.getByRole("heading", { name: "菜单配置", exact: true });
  await menuConfigurationHeading.waitFor({ state: 'visible', timeout: 45000 });
  const menuConfigurationHeadingText = String(await menuConfigurationHeading.textContent() || '').trim();
  check(menuConfigurationHeadingText === '菜单配置', '菜单配置页标题漂移', { menuConfigurationHeadingText });

  report.desktop = { sourceUrl, firstTarget, targetMenuId, targetActionId, depth, activeLeafCount: 1, collapsePersisted: true, product_configuration_entry_count, legacy_configuration_entry_count, configuredModel, configuredActionId, menuConfigurationHeadingText };
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

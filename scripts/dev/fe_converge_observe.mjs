// FE-CONVERGE-01 page observation: login, measure real rendered layout, dump
// navigation, detect overflow/console errors. Read-only; not a delivery receipt.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const requireWeb = createRequire(path.join(root, 'frontend/apps/web/package.json'));
const { resolveChromiumExecutablePath } = await import(path.join(root, 'scripts/verify/playwright_runtime.mjs'));
const { chromium } = requireWeb('playwright');

const BASE = process.env.FRONTEND_URL || 'http://127.0.0.1:5176';
const LOGIN = process.env.E2E_LOGIN || 'sc_test_admin';
const PASSWORD = process.env.E2E_PASSWORD || '123456';
const DATABASE = process.env.DB_NAME || 'sc_dev_demo';
const OUT = path.resolve(process.env.CANDIDATE_VISUAL_OUTPUT_DIR || path.join(root, 'artifacts/fe-converge-01/observe'));
fs.mkdirSync(OUT, { recursive: true });

const executablePath = resolveChromiumExecutablePath();
if (!executablePath) throw new Error('chromium not found');

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.first().waitFor({ state: 'visible', timeout: 45000 });
  const count = await inputs.count();
  if (count >= 1) await inputs.nth(0).fill(LOGIN);
  if (count >= 2) await inputs.nth(1).fill(PASSWORD);
  if (count >= 3 && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(DATABASE);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 }).catch(() => {});
  await page.locator('.layout-shell, .shell').waitFor({ timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(2500);
}

async function measureShell(page) {
  return page.evaluate(() => {
    const rect = (el) => (el ? { w: Math.round(el.getBoundingClientRect().width), h: Math.round(el.getBoundingClientRect().height) } : null);
    const menuItem = document.querySelector('.sc-navigation-menu .t-menu__item, [data-navigation-menu-id]');
    const topbar = document.querySelector('.topbar, [class*="topbar"]');
    const nav = [...document.querySelectorAll('[data-navigation-menu-id], [data-navigation-action-id]')]
      .map((n) => ({
        label: n.getAttribute('data-navigation-label') || (n.textContent || '').trim().slice(0, 30),
        menuId: n.getAttribute('data-navigation-menu-id'),
        actionId: n.getAttribute('data-navigation-action-id'),
        state: n.getAttribute('data-navigation-state'),
        h: Math.round(n.getBoundingClientRect().height),
      }))
      .filter((x) => x.menuId || x.actionId)
      .slice(0, 120);
    const doc = document.documentElement;
    return {
      url: location.href,
      viewport: { w: window.innerWidth, h: window.innerHeight },
      overflowX: doc.scrollWidth > doc.clientWidth ? doc.scrollWidth - doc.clientWidth : 0,
      topbar: rect(topbar),
      firstMenuItem: rect(menuItem),
      nav,
    };
  });
}

const browser = await chromium.launch({ executablePath, headless: true, args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
const consoleErrors = [];
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${String(e).slice(0, 200)}`));

await login(page);
const report = { base: BASE, login: LOGIN, database: DATABASE, url: page.url(), pages: [], consoleErrors };

for (const [name, route] of [
  ['home', '/'],
  ['my-work', '/my-work'],
  ['menu-config', '/admin/menu-config'],
]) {
  try {
    await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1800);
    const m = await measureShell(page);
    await page.screenshot({ path: path.join(OUT, `${name}-desktop.png`), fullPage: false });
    report.pages.push({ name, route, ...m });
  } catch (err) {
    report.pages.push({ name, route, error: String(err).slice(0, 200) });
  }
}

await browser.close();
fs.writeFileSync(path.join(OUT, 'measure.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ out: OUT, url: report.url, pages: report.pages.map((p) => ({ name: p.name, url: p.url, overflowX: p.overflowX, firstMenuItem: p.firstMenuItem, navCount: p.nav?.length })) }, null, 2));

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const baseUrl = String(process.env.FRONTEND_URL || '').replace(/\/$/, '');
const database = String(process.env.DB_NAME || '');
const login = String(process.env.E2E_LOGIN || '');
const password = String(process.env.E2E_PASSWORD || '');
const head = String(process.env.CANDIDATE_GIT_HEAD || '');
const outputDir = path.resolve(
  process.env.FE_POLISH_B1_OUTPUT_DIR || '.runtime/fe-polish-b1-browser',
);

if (!baseUrl || !database || !login || !password || !/^[0-9a-f]{40}$/.test(head)) {
  throw new Error('FE-POLISH-B1 browser identity is incomplete');
}

fs.mkdirSync(outputDir, { recursive: true });
const browser = await launchChromium({ headless: true });
const report = {
  head,
  baseUrl,
  database,
  login,
  mutationCount: 0,
  viewports: [],
  consoleErrors: [],
  httpErrors: [],
};
const failures = [];

function check(condition, name, evidence) {
  if (!condition) failures.push({ name, evidence });
}

async function loginAndOpen(viewport, route, readySelector) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    locale: 'zh-CN',
    colorScheme: 'light',
  });
  const page = await context.newPage();
  page.on('console', (message) => {
    if (message.type() === 'error') {
      report.consoleErrors.push({
        viewport: viewport.name,
        route,
        text: message.text(),
      });
    }
  });
  page.on('response', (response) => {
    if (response.status() >= 400) {
      report.httpErrors.push({
        viewport: viewport.name,
        route,
        status: response.status(),
        url: response.url(),
      });
    }
  });
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.first().waitFor({ state: 'visible', timeout: 45000 });
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) {
    await inputs.nth(2).fill(database);
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator(readySelector).waitFor({ state: 'visible', timeout: 45000 });
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  return { context, page };
}

for (const viewport of [
  { name: 'desktop', width: 1440, height: 960 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  const evidence = { viewport };
  {
    const { context, page } = await loginAndOpen(
      viewport,
      '/my-work',
      '[data-semantic-component="MyWorkApprovalWorkspace"][data-state="ready"]',
    );
    await page.locator('.work-card').first().waitFor({ state: 'visible', timeout: 45000 });
    const cards = await page.locator('.work-card').evaluateAll((nodes) => nodes.map((node) => {
      const title = node.querySelector('h3');
      const amountNode = node.querySelector('.work-card__summary dd');
      const style = title ? getComputedStyle(title) : null;
      const rawLabel = title?.getAttribute('title') || '';
      const visibleTitle = String(title?.textContent || '').trim();
      const amountText = String(amountNode?.textContent || '').trim();
      const amount = amountText.replace(/^.*[：:]/, '').trim();
      return {
        recordId: node.getAttribute('data-record-id'),
        rawLabel,
        visibleTitle,
        amount,
        titleContainsAmount: Boolean(amount && visibleTitle.includes(amount)),
        summaryContainsAmount: Boolean(amount && amountText.includes(amount)),
        rawLabelContainsAmount: Boolean(amount && rawLabel.includes(amount)),
        whiteSpace: style?.whiteSpace || '',
        lineClamp: style?.webkitLineClamp || '',
        clientHeight: title?.clientHeight || 0,
        scrollHeight: title?.scrollHeight || 0,
        fullyVisible: Boolean(title && title.scrollHeight <= title.clientHeight + 1),
      };
    }));
    check(cards.length > 0, `${viewport.name}: my-work cards present`, cards.length);
    check(
      cards.every((card) => card.amount && !card.titleContainsAmount && card.summaryContainsAmount),
      `${viewport.name}: My Work amount is presented once`,
      cards.slice(0, 3),
    );
    check(
      cards.every((card) => card.rawLabelContainsAmount && card.whiteSpace === 'normal' && card.lineClamp),
      `${viewport.name}: My Work keeps the authoritative identity and wrapping`,
      cards.slice(0, 3),
    );
    check(
      cards.every((card) => card.fullyVisible),
      `${viewport.name}: My Work record identity is not clipped`,
      cards.filter((card) => !card.fullyVisible).slice(0, 3),
    );
    await page.locator('.work-card').first().screenshot({
      path: path.join(outputDir, `${viewport.name}-my-work-card.png`),
    });

    await page.locator('.router-host').evaluate((node) => {
      node.scrollTo({ top: node.scrollHeight, behavior: 'auto' });
    });
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const footer = await page.evaluate(() => {
      const node = document.querySelector('.shell-content-footer');
      const router = document.querySelector('.router-host');
      const frame = router?.querySelector(':scope > :not(.shell-content-footer)');
      const footerRect = node?.getBoundingClientRect();
      const frameRect = frame?.getBoundingClientRect();
      const routerRect = router?.getBoundingClientRect();
      return {
        order: node ? getComputedStyle(node).order : '',
        footerRect: footerRect
          ? { top: footerRect.top, bottom: footerRect.bottom, height: footerRect.height }
          : null,
        frameRect: frameRect
          ? { top: frameRect.top, bottom: frameRect.bottom, height: frameRect.height }
          : null,
        routerRect: routerRect
          ? { top: routerRect.top, bottom: routerRect.bottom, height: routerRect.height }
          : null,
      };
    });
    check(footer.order === '3', `${viewport.name}: footer owns final flex order`, footer);
    check(
      Boolean(
        footer.footerRect
        && footer.frameRect
        && footer.routerRect
        && footer.footerRect.top >= footer.frameRect.bottom - 1
        && footer.footerRect.bottom <= footer.routerRect.bottom + 1,
      ),
      `${viewport.name}: footer renders after the routed frame`,
      footer,
    );
    await page.screenshot({
      path: path.join(outputDir, `${viewport.name}-footer.png`),
      fullPage: false,
    });
    Object.assign(evidence, { myWork: { cards: cards.slice(0, 3), footer } });
    await context.close();
  }

  {
    const { context, page } = await loginAndOpen(
      viewport,
      '/s/workspace.home',
      '[data-semantic-component="WorkspaceHome"][data-state="ready"]',
    );
    const tasks = await page.locator('[data-login-home-block="today_actions"] article').evaluateAll((nodes) => nodes.map((node) => {
      const chip = node.querySelector('.role-home-surface__task-amount');
      const label = node.querySelector('.role-home-surface__task-record');
      const amount = String(chip?.textContent || '').replace(/^.*[：:]/, '').trim();
      const visibleLabel = String(label?.textContent || '').trim();
      return {
        recordId: node.getAttribute('data-record-id'),
        amount,
        visibleLabel,
        labelContainsAmount: Boolean(amount && visibleLabel.includes(amount)),
      };
    }));
    check(tasks.length > 0, `${viewport.name}: role-home tasks present`, tasks.length);
    check(
      tasks.every((task) => task.amount && !task.labelContainsAmount),
      `${viewport.name}: role-home amount chip owns the money expression`,
      tasks.slice(0, 3),
    );
    await page.screenshot({
      path: path.join(outputDir, `${viewport.name}-workspace-home.png`),
      fullPage: false,
    });

    const theme = await page.locator('.scene-style-trigger:visible').first().evaluate((node) => {
      const label = node.querySelector('.scene-style-trigger__label');
      const caret = node.querySelector('.scene-style-picker__caret');
      const rect = node.getBoundingClientRect();
      const caretRect = caret?.getBoundingClientRect();
      return {
        ariaLabel: node.getAttribute('aria-label') || '',
        labelDisplay: label ? getComputedStyle(label).display : '',
        labelText: String(label?.textContent || '').trim(),
        caretVisible: Boolean(
          caretRect && caretRect.width > 0 && caretRect.height > 0,
        ),
        withinViewport: rect.left >= 0 && rect.right <= window.innerWidth,
      };
    });
    if (viewport.name === 'mobile') {
      check(theme.labelDisplay === 'none', 'mobile: style label is not clipped', theme);
      check(theme.caretVisible, 'mobile: style-picker caret remains visible', theme);
      check(
        theme.withinViewport && /^切换界面风格，当前.+/.test(theme.ariaLabel),
        'mobile: style-picker keeps its accessible name inside the viewport',
        theme,
      );
    }
    Object.assign(evidence, { workspaceHome: { tasks: tasks.slice(0, 3), theme } });
    await context.close();
  }

  report.viewports.push(evidence);
}

await browser.close();
report.pass = failures.length === 0
  && report.consoleErrors.length === 0
  && report.httpErrors.length === 0
  && report.mutationCount === 0;
report.failures = failures;
fs.writeFileSync(
  path.join(outputDir, 'summary.json'),
  `${JSON.stringify(report, null, 2)}\n`,
);
console.log(JSON.stringify({
  pass: report.pass,
  failures,
  consoleErrors: report.consoleErrors,
  httpErrors: report.httpErrors,
}, null, 2));
if (!report.pass) process.exitCode = 1;

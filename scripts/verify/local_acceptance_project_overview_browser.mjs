import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { launchChromium } from './playwright_runtime.mjs';

const base = process.env.ACCEPTANCE_FRONTEND_URL || 'http://127.0.0.1:5179';
const login = process.env.E2E_LOGIN || 'fixture_role_pm';
const password = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD;
const output = path.resolve(process.env.ACCEPTANCE_EVIDENCE_DIR || '.runtime/acceptance/project-overview');
assert(password, 'SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
fs.mkdirSync(output, { recursive: true });

const report = { status: 'failed', head: process.env.CANDIDATE_HEAD, base, login, cases: [], errors: [] };
const browser = await launchChromium();

async function openCase(key, route, { expectNotice, expectOverviewText } = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.on('pageerror', (error) => report.errors.push(error.message));
  try {
    await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
    await page.locator('#login-username').fill(login);
    await page.locator('#login-password').fill(password);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
    await page.goto(`${base}/${route}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-form-model]', { timeout: 30000 });
    if (expectOverviewText) {
      await page.waitForFunction(
        (expected) => document.body.innerText.replace(/\s+/g, ' ').includes(expected),
        expectOverviewText,
        { timeout: 30000 },
      );
    }
    if (expectNotice === true) {
      await page.waitForSelector('[data-submission-readiness]', { timeout: 30000 });
    }
    if (expectNotice === false) {
      await page.waitForFunction(() => document.querySelector('[data-field-name]') !== null, { timeout: 30000 });
    }
    const noticeCount = await page.locator('[data-submission-readiness]').count();
    const bodyCount = await page.locator('[data-field-name="submission_readiness_display"]').count();
    const text = expectOverviewText ? (await page.locator('body').innerText()).replace(/\s+/g, ' ') : null;
    assert.ok(!expectOverviewText || text.includes(expectOverviewText), `${key}: overview text missing`);
    assert.equal(noticeCount, expectNotice === true ? 1 : 0, `${key}: notice count`);
    assert.equal(bodyCount, 0, `${key}: native body readiness field must not render`);
    await page.screenshot({ path: path.join(output, `${key}.png`), fullPage: true });
    report.cases.push({ key, status: 'passed', noticeCount, bodyCount, overviewText: expectOverviewText || null });
  } catch (error) {
    await page.screenshot({ path: path.join(output, `${key}-failed.png`), fullPage: true });
    fs.writeFileSync(path.join(output, `${key}-body.txt`), await page.locator('body').innerText());
    throw new Error(`${key}: ${error.message}`);
  } finally {
    await context.close();
  }
}

try {
  // 立项完成度 + 办理前检查（项目可提交）：草稿 FE Project A
  await openCase('project-draft-overview', 'r/project.project/1?action_id=590&menu_id=382', {
    expectNotice: true,
    expectOverviewText: '立项完成度：1 / 3',
  });
  // 新建项目（no_data）
  await openCase('project-new', 'f/project.project/new?action_id=795&menu_id=379', {
    expectNotice: true,
  });
  report.status = 'passed';
} catch (error) {
  report.failure = error.message;
  process.exitCode = 1;
} finally {
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
}

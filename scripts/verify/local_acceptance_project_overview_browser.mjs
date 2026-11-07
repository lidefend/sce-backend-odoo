import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { launchChromium } from './playwright_runtime.mjs';

const base = process.env.ACCEPTANCE_FRONTEND_URL || 'http://127.0.0.1:5179';
const login = process.env.E2E_LOGIN || 'fixture_role_pm';
const password = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD;
const output = path.resolve(process.env.ACCEPTANCE_EVIDENCE_DIR || '.runtime/acceptance/project-overview');
const nonDraftProjectId = process.env.ACCEPTANCE_NON_DRAFT_PROJECT_ID;
assert(password, 'SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
fs.mkdirSync(output, { recursive: true });

const report = { status: 'failed', head: process.env.CANDIDATE_HEAD, base, login, cases: [], errors: [] };
const browser = await launchChromium();

function squashed(text) {
  return String(text || '').replace(/\s+/g, '');
}

async function openCase(key, route, { expectNotice, expectOverviewText, expectOverviewTextAbsent, actor, expectForbiddenLabel } = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const caseLogin = actor || login;
  page.on('pageerror', (error) => report.errors.push(error.message));
  try {
    await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
    await page.locator('#login-username').fill(caseLogin);
    await page.locator('#login-password').fill(password);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
    await page.goto(`${base}/${route}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-form-model]', { timeout: 30000 });
    if (expectOverviewText) {
      const expected = squashed(expectOverviewText);
      await page.waitForFunction(
        (expected) => document.body.innerText.replace(/\s+/g, '').includes(expected),
        expected,
        { timeout: 30000 },
      );
    }
    if (expectNotice === true) {
      await page.waitForSelector('[data-submission-readiness]', { timeout: 30000 });
    }
    if (expectNotice === false || expectOverviewTextAbsent) {
      await page.waitForFunction(() => document.querySelector('[data-field-name]') !== null, { timeout: 30000 });
    }
    const noticeCount = await page.locator('[data-submission-readiness]').count();
    const bodyCount = await page.locator('[data-field-name="submission_readiness_display"]').count();
    const bodyText = squashed(await page.locator('body').innerText());
    if (expectOverviewText) {
      assert.ok(bodyText.includes(squashed(expectOverviewText)), `${key}: overview text missing`);
    }
    if (expectOverviewTextAbsent) {
      assert.ok(!bodyText.includes(squashed(expectOverviewTextAbsent)), `${key}: overview text must be hidden`);
    }
    if (expectNotice === true) {
      assert.equal(noticeCount, 1, `${key}: page-header readiness notice count`);
      if (expectForbiddenLabel) {
        const noticeText = squashed(await page.locator('[data-submission-readiness]').first().innerText());
        assert.ok(noticeText.includes('无权限'), `${key}: forbidden notice must show the desensitized 无权限 label`);
      }
    } else {
      assert.equal(noticeCount, 0, `${key}: no page-header readiness notice expected`);
    }
    assert.equal(bodyCount, 0, `${key}: native body readiness field must not render`);
    await page.screenshot({ path: path.join(output, `${key}.png`), fullPage: true });
    report.cases.push({
      key,
      status: 'passed',
      login: caseLogin,
      noticeCount,
      bodyCount,
      overviewText: expectOverviewText || null,
      overviewTextAbsent: expectOverviewTextAbsent || null,
    });
  } catch (error) {
    await page.screenshot({ path: path.join(output, `${key}-failed.png`), fullPage: true });
    fs.writeFileSync(path.join(output, `${key}-body.txt`), await page.locator('body').innerText());
    throw new Error(`${key}: ${error.message}`);
  } finally {
    await context.close();
  }
}

try {
  await openCase('project-draft-overview', 'r/project.project/1?action_id=590&menu_id=382', {
    expectNotice: true,
    expectOverviewText: '立项完成度：1 / 3',
  });
  await openCase('project-new', 'f/project.project/new?action_id=795&menu_id=379', {
    expectNotice: true,
  });
  if (nonDraftProjectId) {
    await openCase('project-non-draft', `r/project.project/${nonDraftProjectId}?action_id=590&menu_id=382`, {
      expectNotice: false,
      expectOverviewTextAbsent: '立项完成度：',
    });
  }
  await openCase('project-forbidden', 'r/project.project/1?action_id=590&menu_id=382', {
    expectNotice: true,
    expectForbiddenLabel: true,
    actor: 'fixture_role_project_a_member',
  });
  report.status = 'passed';
} catch (error) {
  report.failure = error.message;
  process.exitCode = 1;
} finally {
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
}

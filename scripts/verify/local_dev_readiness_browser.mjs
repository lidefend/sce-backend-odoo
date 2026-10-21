import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { launchChromium } from './playwright_runtime.mjs';
const target = JSON.parse(process.env.LOCAL_DEV_READINESS_JSON || '{}');
const output = path.resolve('.runtime/agent-runs/PRODUCT-ITERATION-V2-20261020/readiness-browser');
const report = { status: 'failed', head: process.env.CANDIDATE_HEAD, stage: 'head_plus_dirty_scope', cases: [], errors: [], mutations: [] };
fs.mkdirSync(output, { recursive: true });
assert.equal(target.database, 'sc_dev_demo');
assert.deepEqual(target.missing, [], 'existing records must cover declared cases');
assert.equal(target.cases.length, 5);
const browser = await launchChromium();
try {
  const selected = process.env.READINESS_CASE_KEYS?.split(',').filter(Boolean);
  if (selected) assert.ok(selected.every(key => target.cases.some(item => item.key === key)));
  for (const item of target.cases.filter(item => !selected || selected.includes(item.key))) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    const responses = [];
    page.on('pageerror', error => report.errors.push(error.message));
    await page.route('**/*', async route => {
      let body; try { body = route.request().postDataJSON(); } catch { body = {}; }
      const intent = body?.intent || '';
      const operation = body?.params?.operation || body?.params?.op || '';
      if (/execute|create|write|unlink|publish|rollback/.test(intent) || (intent === 'api.data' && ['create', 'write', 'unlink'].includes(operation))) {
        report.mutations.push({ intent, operation });
        return route.abort();
      }
      return route.continue();
    });
    page.on('response', async response => {
      if (response.request().method() !== 'POST') return;
      try { const body = await response.json(); responses.push(body); } catch {}
    });
    try {
      const base = process.env.FRONTEND_URL;
      await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
      await page.locator('#login-username').fill(item.actor.login);
      await page.locator('#login-password').fill(process.env.E2E_PASSWORD);
      const db = page.getByLabel(/数据库/);
      if (await db.count() === 1 && await db.isVisible() && await db.isEnabled()) await db.fill(target.database);
      await page.getByRole('button', { name: /^登录$/ }).click();
      await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 45000 });
      responses.length = 0;
      const route = item.record_id ? `r/${item.model}/${item.record_id}` : `f/${item.model}/new`;
      await page.goto(`${base}/${route}?action_id=${item.action_id}&menu_id=${item.menu_id}`, { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(expected => document.body.innerText.includes(expected), item.expected.split('\n')[0], { timeout: 30000 });
      const field = page.locator('[data-field-name="submission_readiness_display"]');
      assert.equal(await field.count(), 1, 'one native readiness field');
      await field.scrollIntoViewIfNeeded();
      assert.equal(await field.isVisible(), true, 'readiness field visible');
      const body = await field.innerText();
      for (const line of item.expected.split('\n')) assert.ok(body.includes(line), `${item.key}: expected native readiness text`);
      assert.ok(JSON.stringify(responses).includes('submission_readiness_display'), 'field supplied by runtime contract/data');
      assert.equal(report.mutations.length, 0);
      assert.equal(report.errors.length, 0);
      await page.screenshot({ path: path.join(output, `${item.key}.png`), fullPage: true });
      await field.screenshot({ path: path.join(output, `${item.key}-field.png`) });
      report.cases.push({ key: item.key, status: 'passed', actor_id: item.actor.id, record_id: item.record_id, readiness: item.status });
    } catch (error) {
      await page.screenshot({ path: path.join(output, `${item.key}-failed.png`), fullPage: true });
      fs.writeFileSync(path.join(output, `${item.key}-responses.json`), JSON.stringify(responses, null, 2));
      fs.writeFileSync(path.join(output, `${item.key}-body.txt`), await page.locator('body').innerText());
      throw new Error(`${item.key}: ${error.message}`);
    } finally { await context.close(); }
  }
  report.status = 'passed';
} catch (error) { report.failure = error.message; process.exitCode = 1; }
finally {
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
}

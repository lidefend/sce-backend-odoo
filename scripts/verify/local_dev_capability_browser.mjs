import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { launchChromium } from './playwright_runtime.mjs';
const target = JSON.parse(process.env.LOCAL_DEV_CAPABILITY_JSON || '{}');
const output = path.resolve('.runtime/agent-runs/PRODUCT-ITERATION-V2-20261020/capability-browser');
const report = { status: 'failed', head: process.env.CANDIDATE_HEAD, stage: 'head_plus_dirty_scope', cases: [], errors: [], mutations: [] };
assert.equal(target.database, 'sc_dev_demo');
assert.equal(target.cases.length, 2);
fs.mkdirSync(output, { recursive: true });
const browser = await launchChromium();
try {
  const selectedKeys = process.env.CAPABILITY_CASE_KEYS?.split(',').map(key => key.trim()).filter(Boolean);
  const selected = selectedKeys?.length ? selectedKeys : undefined;
  if (selected) assert.ok(selected.every(key => target.cases.some(item => item.key === key)));
  for (const item of target.cases.filter(item => !selected || selected.includes(item.key))) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
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
    try {
      const base = process.env.FRONTEND_URL;
      await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
      await page.locator('#login-username').fill(item.actor.login);
      await page.locator('#login-password').fill(process.env.E2E_PASSWORD);
      const db = page.getByLabel(/数据库/);
      if (await db.count() === 1 && await db.isVisible() && await db.isEnabled()) await db.fill(target.database);
      await page.getByRole('button', { name: /^登录$/ }).click();
      await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 45000 });
      const responsePromise = page.waitForResponse(response => {
        try { return response.request().postDataJSON()?.intent === 'product.configuration.capability.catalog'; }
        catch { return false; }
      });
      await page.goto(`${base}/my-capabilities`, { waitUntil: 'domcontentloaded' });
      const envelope = await (await responsePromise).json();
      const data = envelope.data || envelope.result?.data || envelope.result;
      assert.deepEqual(data.user_capabilities, item.expected, 'HTTP contract equals principal-scoped authority');
      const cards = page.locator('.capability-card');
      if (item.expected.items.length) {
        await page.waitForFunction(count => document.querySelectorAll('.capability-card').length === count, item.expected.items.length);
      } else {
        await page.getByText(item.expected.empty_message, { exact: true }).waitFor();
      }
      assert.equal(await cards.count(), item.expected.items.length);
      for (const row of item.expected.items) {
        const exact = cards.locator(`xpath=self::*[@data-capability-key=${JSON.stringify(row.key)}]`);
        assert.equal(await exact.count(), 1);
        assert.equal(await exact.getAttribute('data-capability-status'), row.status);
        assert.equal(await exact.getAttribute('data-capability-available'), String(row.available));
        assert.equal(await exact.locator('strong').innerText(), row.label);
        assert.equal(await exact.locator('.capability-status-badge').innerText(), row.status_label);
        if (!row.available) assert.equal(await exact.locator('.capability-reason').innerText(), row.reason);
      }
      assert.equal(report.errors.length, 0);
      assert.equal(report.mutations.length, 0);
      await page.screenshot({ path: path.join(output, `${item.key}.png`), fullPage: true });
      const navigationResults = [];
      const navigationKeys = process.env.CAPABILITY_NAVIGATION_KEYS?.split(',').map(key => key.trim()).filter(Boolean);
      if (navigationKeys?.length) assert.ok(navigationKeys.every(key => item.navigation.some(entry => entry.key === key)), 'selected navigation must resolve for actor');
      for (const entry of (item.navigation || []).filter(entry => !navigationKeys?.length || navigationKeys.includes(entry.key))) {
        const requests = [];
        const capture = request => {
          try { requests.push(request.postDataJSON()); } catch {}
        };
        page.on('request', capture);
        const contractResponsePromise = page.waitForResponse(response => {
          try {
            const body = response.request().postDataJSON();
            return body?.intent === 'ui.contract.v2' && Number(body.params?.action_id) === entry.action_id;
          } catch { return false; }
        }, { timeout: 45000 });
        contractResponsePromise.catch(() => {});
        const listResponsePromise = page.waitForResponse(response => {
          try {
            const body = response.request().postDataJSON();
            return body?.intent === 'api.data' && body.params?.model === entry.model && body.params?.op === 'list';
          } catch { return false; }
        }, { timeout: 45000 });
        // Attach rejection handling before navigation, which can fail independently.
        listResponsePromise.catch(() => {});
        await page.goto(`${base}${entry.route}`, { waitUntil: 'domcontentloaded' });
        const listResponse = await listResponsePromise;
        assert.ok(listResponse.ok(), 'list transport must succeed');
        const listRequest = listResponse.request().postDataJSON().params;
        const listEnvelope = await listResponse.json();
        const listData = listEnvelope.data || listEnvelope.result?.data || listEnvelope.result;
        assert.ok(Array.isArray(listData?.records), 'list response must declare records');
        assert.ok(Array.isArray(listRequest.fields) && listRequest.fields.length > 0, 'frontend must request explicit fields');
        assert.ok(Array.isArray(listRequest.domain), 'frontend domain must match list contract');
        assert.ok(Number.isInteger(listRequest.offset) && listRequest.offset >= 0);
        assert.ok(Number.isInteger(listRequest.limit) && listRequest.limit > 0);
        for (const record of listData.records) {
          for (const field of listRequest.fields) assert.ok(Object.hasOwn(record, field), `response missing requested field ${field}`);
        }
        if (listData.total !== undefined) assert.ok(Number.isInteger(listData.total) && listData.total >= listData.records.length);
        await page.waitForFunction(() => {
          const root = document.querySelector('[data-semantic-component="ActionView"]');
          return root && ['ok', 'empty'].includes(root.getAttribute('data-collection-state'));
        }, null, { timeout: 45000 });
        const collectionState = await page.locator('[data-semantic-component="ActionView"]').getAttribute('data-collection-state');
        assert.equal(collectionState, listData.records.length ? 'ok' : 'empty', 'rendered collection state must match response');
        const contractResponse = await contractResponsePromise;
        assert.ok(contractResponse.ok());
        const contractEnvelope = await contractResponse.json();
        const contract = contractEnvelope.data || contractEnvelope.result?.data || contractEnvelope.result;
        const globalStatus = contract.statusContract?.globalStatus;
        assert.equal(typeof globalStatus?.modelRights?.write, 'boolean', 'model write authority must be declared');
        assert.equal(typeof globalStatus?.effectiveRecordCapabilities?.create, 'boolean', 'create authority must be declared');
        const root = page.locator('[data-semantic-component="ActionView"]');
        assert.equal(await root.getAttribute('data-can-create'), String(globalStatus.effectiveRecordCapabilities.create));
        assert.equal(await root.getAttribute('data-can-edit'), String(globalStatus.modelRights.write));
        const actionAuthority = { create: globalStatus.effectiveRecordCapabilities.create, edit: globalStatus.modelRights.write };
        const listProfile = contract.layoutContract?.listProfile;
        assert.ok(Array.isArray(listProfile?.columns) && listProfile.columns.length > 0, 'list columns must be declared');
        const headers = root.locator('[data-semantic-component="CollectionColumnHeaderControl"]');
        assert.ok(await headers.count() > 0, 'declared collection must render field headers');
        const renderedColumns = [];
        for (const header of await headers.all()) {
          const field = await header.getAttribute('data-column');
          assert.ok(listProfile.columns.includes(field), `rendered column ${field} is not declared`);
          assert.ok(listRequest.fields.includes(field), `rendered column ${field} was not queried`);
          assert.equal((await header.locator('.column-sort-btn').innerText()).trim(), listProfile.column_labels[field]);
          renderedColumns.push(field);
        }
        page.off('request', capture);
        assert.ok(requests.some(body => body?.params?.model === entry.model), `native action must query ${entry.model}`);
        assert.equal(report.errors.length, 0);
        assert.equal(report.mutations.length, 0);
        await page.screenshot({ path: path.join(output, `${item.key}-${entry.key}.png`), fullPage: true });
        const searchToken = 'contractprobe_no_project_' + Date.now();
        const emptyResponsePromise = page.waitForResponse(response => {
          try {
            const body = response.request().postDataJSON();
            return body?.intent === 'api.data' && body.params?.model === entry.model
              && body.params?.op === 'list' && JSON.stringify(body.params).includes(searchToken);
          } catch { return false; }
        }, { timeout: 45000 });
        emptyResponsePromise.catch(() => {});
        const search = root.locator('[data-semantic-component="CollectionActionToolbar"] input[type="search"]:visible');
        assert.equal(await search.count(), 1, 'exactly one active collection search required');
        await search.fill(searchToken);
        assert.equal(await search.inputValue(), searchToken);
        await root.locator('[data-semantic-component="CollectionActionToolbar"] .toolbar-search-submit:visible').click();
        const emptyResponse = await emptyResponsePromise;
        assert.ok(emptyResponse.ok());
        const emptyEnvelope = await emptyResponse.json();
        const emptyData = emptyEnvelope.data || emptyEnvelope.result?.data || emptyEnvelope.result;
        assert.deepEqual(emptyData.records, [], 'real search must return zero records');
        await page.waitForFunction(() => document.querySelector('[data-semantic-component="ActionView"]')?.getAttribute('data-collection-state') === 'empty');
        assert.equal(report.errors.length, 0);
        assert.equal(report.mutations.length, 0);
        await page.screenshot({ path: path.join(output, `${item.key}-${entry.key}-empty.png`), fullPage: true });
        navigationResults.push({ key: entry.key, model: entry.model, action_id: entry.action_id, route: entry.route, status: 'passed',
          action_authority: actionAuthority, empty_search: { real_response: true, records: 0, rendered_state: 'empty' },
          columns: { rendered: renderedColumns, declared_and_queried: true, labels_match_declaration: true },
          transport: { operation: 'list', requested_fields: listRequest.fields, returned_record_count: listData.records.length,
            collection_state: collectionState, requested_fields_present: true, request_response_schema_aligned: true } });
      }
      report.cases.push({ key: item.key, actor_id: item.actor.id, status: 'passed', count: item.expected.items.length,
        navigation: navigationResults, states: [...new Set(item.expected.items.map(row => row.status))], empty: !item.expected.items.length });
    } catch (error) {
      await page.screenshot({ path: path.join(output, `${item.key}-failed.png`), fullPage: true });
      fs.writeFileSync(path.join(output, `${item.key}-body.txt`), await page.locator('body').innerText());
      throw new Error(`${item.key}: ${error.message}`);
    } finally { await context.close(); }
  }
  assert.ok(report.cases.length > 0, 'zero browser cases is a failure');
  assert.equal(report.cases.length, selected?.length || target.cases.length);
  report.status = 'passed';
} catch (error) { report.failure = error.message; process.exitCode = 1; }
finally { fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2)); await browser.close(); }

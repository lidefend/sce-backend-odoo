#!/usr/bin/env node
'use strict';

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const FRONTEND_URL = String(process.env.SC_CLOSE_03_FRONTEND_URL || 'http://127.0.0.1:5175').replace(/\/+$/, '');
const DATABASE = String(process.env.SC_CLOSE_03_DB || 'sc_frontend_acceptance');
const LOGIN = String(process.env.SC_CLOSE_03_LOGIN || 'fixture_role_config_admin');
const PASSWORD = String(process.env.SC_CLOSE_03_PASSWORD || '');
const OUTPUT_DIR = path.resolve(String(
  process.env.SC_CLOSE_03_BROWSER_OUTPUT
    || '.runtime/agent-runs/CLOSE-03-PROJECT-INTAKE-DRAFT-RESTORE-20261119/browser_journey',
));
const SAMPLE_SUMMARY = path.resolve(String(
  process.env.SC_CLOSE_03_SAMPLE_SUMMARY
    || '.runtime/agent-runs/CLOSE-03-PROJECT-INTAKE-DRAFT-RESTORE-20261119/intake_autosave_samples/summary.json',
));

function check(condition, message, detail = undefined) {
  if (condition) return;
  throw new Error(`${message}${detail === undefined ? '' : ` ${JSON.stringify(detail)}`}`);
}

async function stage(label, promise) {
  try {
    return await promise;
  } catch (error) {
    throw new Error(`${label}: ${error?.message || error}`);
  }
}

function writeJson(name, value) {
  const target = path.join(OUTPUT_DIR, name);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function readEntries() {
  const body = JSON.parse(fs.readFileSync(SAMPLE_SUMMARY, 'utf8'));
  check(body?.summary?.status === 'PASS', 'backend contract samples did not pass');
  return body.entries || {};
}

function requestPayload(request) {
  try {
    return JSON.parse(request.postData() || '{}');
  } catch {
    return {};
  }
}

function isMutation(payload) {
  return payload?.intent === 'api.data'
    && ['create', 'write', 'unlink'].includes(String(payload?.params?.op || ''));
}

async function login(page) {
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(LOGIN);
  await inputs.nth(1).fill(PASSWORD);
  if (await inputs.nth(2).count()) {
    if (!(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(DATABASE);
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
}

async function browserIntent(page, intent, params) {
  const result = await page.evaluate(async ({ intentName, requestParams }) => {
    const tokenKey = Object.keys(sessionStorage).find((key) => key.startsWith('sc_auth_token:'));
    const token = tokenKey ? sessionStorage.getItem(tokenKey) : '';
    const response = await fetch('/api/v1/intent', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ intent: intentName, params: requestParams }),
    });
    return { status: response.status, body: await response.json() };
  }, { intentName: intent, requestParams: params });
  check(result.status >= 200 && result.status < 300, `${intent} failed`, {
    status: result.status,
    code: result.body?.error?.code || '',
    reason: result.body?.error?.reason_code || '',
  });
  return result.body?.data || result.body?.result || result.body;
}

async function waitForDraftSaved(page, draftKey) {
  await page.locator('[data-intake-autosave][data-intake-autosave-state="success"]').first()
    .waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForFunction(
    (key) => Boolean(localStorage.getItem(key)),
    draftKey,
    { timeout: 15000 },
  );
}

async function chooseManager(page, label) {
  const manager = page.locator('input[id*="field-field-manager_id-occ-"]').first();
  await manager.click();
  const option = page.getByText(label, { exact: true }).last();
  await option.waitFor({ state: 'visible', timeout: 15000 });
  await option.click();
  await page.waitForFunction(
    ({ selector, expected }) => document.querySelector(selector)?.value === expected,
    { selector: 'input[id*="field-field-manager_id-occ-"]', expected: label },
    { timeout: 15000 },
  );
  return manager;
}

async function main() {
  check(PASSWORD, 'SC_CLOSE_03_PASSWORD is required');
  fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
  fs.mkdirSync(path.join(OUTPUT_DIR, 'screenshots'), { recursive: true });
  const entries = readEntries();
  const intake = entries.project_intake;
  const payment = entries.payment_create;
  check(intake?.menu_id && intake?.action_id, 'project-intake identity missing');
  check(payment?.menu_id && payment?.action_id, 'payment-create identity missing');

  const browser = await launchChromium({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    locale: 'zh-CN',
  });
  const page = await context.newPage();
  const errors = [];
  const failedIntents = [];
  const ignoredOptionalIntents = [];
  const mutations = [];
  let createdId = 0;
  let draftKey = '';

  page.on('pageerror', (error) => errors.push(String(error?.message || error)));
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon')) {
      errors.push(String(message.text()));
    }
  });
  page.on('request', (request) => {
    if (!request.url().includes('/api/v1/intent')) return;
    const payload = requestPayload(request);
    if (isMutation(payload)) mutations.push(payload);
  });
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent') || response.status() < 400) return;
    const payload = requestPayload(response.request());
    let body = {};
    try { body = await response.json(); } catch { /* status is still evidence */ }
    const failure = {
      status: response.status(),
      intent: String(payload.intent || ''),
      op: String(payload?.params?.op || ''),
      code: String(body?.error?.code || ''),
      reason: String(body?.error?.reason_code || ''),
    };
    if (
      failure.intent === 'chatter.followers.list'
      && failure.code === 'INTENT_NOT_FOUND'
      && failure.status === 404
    ) {
      ignoredOptionalIntents.push(failure);
    } else {
      failedIntents.push(failure);
    }
  });

  try {
    await login(page);
    const createUrl = `${FRONTEND_URL}/a/${intake.action_id}?menu_id=${intake.menu_id}`;
    await page.goto(createUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const name = page.locator('input[id*="field-field-name-occ-"]').first();
    await stage('project-intake form ready', name.waitFor({ state: 'visible', timeout: 45000 }));

    const projectName = `CLOSE-03 intake ${Date.now()}`;
    await name.fill(projectName);
    const manager = await chooseManager(page, 'Acceptance Fixture Finance Reviewer');

    await stage('draft key created', page.waitForFunction(
      () => Object.keys(localStorage).some((key) => key.startsWith('sc:intake:autosave:')),
      null,
      { timeout: 15000 },
    ));
    draftKey = await page.evaluate(() => (
      Object.keys(localStorage).find((key) => key.startsWith('sc:intake:autosave:')) || ''
    ));
    check(draftKey, 'draft key was not created');
    await stage('draft saved', waitForDraftSaved(page, draftKey));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'screenshots', '01-saved-input.png') });

    const beforeRestoreMutations = mutations.length;
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
    const recoverable = page.locator('[data-intake-autosave][data-intake-autosave-state="recoverable"]').first();
    await stage('restore prompt visible', recoverable.waitFor({ state: 'visible', timeout: 45000 }));
    check(mutations.length === beforeRestoreMutations, 'reload created a record before restore consent', mutations);
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'screenshots', '02-restore-prompt.png') });

    await page.getByRole('button', { name: '恢复', exact: true }).click();
    await stage('restore completed', page.waitForFunction(
      ({ selector, expected }) => document.querySelector(selector)?.value === expected,
      { selector: 'input[id*="field-field-name-occ-"]', expected: projectName },
      { timeout: 15000 },
    ));
    await stage('restored relation', page.waitForFunction(
      ({ selector, expected }) => document.querySelector(selector)?.value === expected,
      {
        selector: 'input[id*="field-field-manager_id-occ-"]',
        expected: 'Acceptance Fixture Finance Reviewer',
      },
      { timeout: 15000 },
    ));
    check(await manager.inputValue() === 'Acceptance Fixture Finance Reviewer', 'relation value was not restored');
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'screenshots', '03-restored.png') });

    await name.fill('');
    const beforeValidationMutations = mutations.length;
    await page.getByRole('button', { name: /^创建项目$/ }).click();
    await stage(
      'validation failure visible',
      page.getByText('名称不能为空', { exact: true }).first().waitFor({ state: 'visible', timeout: 15000 }),
    );
    check(mutations.length === beforeValidationMutations, 'local validation failure attempted a create', mutations);
    check(Boolean(await page.evaluate((key) => localStorage.getItem(key), draftKey)), 'failed validation deleted the draft');

    await name.fill(projectName);
    const createResponse = page.waitForResponse((response) => {
      if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
      const payload = requestPayload(response.request());
      return payload.intent === 'api.data' && payload?.params?.op === 'create'
        && payload?.params?.model === 'project.project';
    }, { timeout: 45000 });
    await page.getByRole('button', { name: /^创建项目$/ }).click();
    const response = await createResponse;
    const createdBody = await response.json();
    createdId = Number(createdBody?.data?.id || createdBody?.result?.id || 0);
    check(createdId > 0, 'create response did not return a record identity', createdBody);
    await stage(
      'created detail navigation',
      page.waitForURL((url) => url.pathname === `/f/project.project/${createdId}`, { timeout: 45000 }),
    );
    await stage('draft cleanup', page.waitForFunction(
      (key) => localStorage.getItem(key) === null,
      draftKey,
      { timeout: 15000 },
    ));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'screenshots', '04-created-record.png') });

    const readback = await browserIntent(page, 'api.data', {
      op: 'list',
      model: 'project.project',
      fields: ['id', 'name', 'manager_id'],
      domain: [['id', '=', createdId]],
      limit: 1,
    });
    check(readback?.records?.length === 1, 'created project readback is empty', readback);
    check(readback.records[0].name === projectName, 'created project readback name mismatch', readback.records[0]);
    check(
      Number(Array.isArray(readback.records[0].manager_id)
        ? readback.records[0].manager_id[0]
        : readback.records[0].manager_id?.id || readback.records[0].manager_id || 0) > 0,
      'created project readback lost the restored relation',
      readback.records[0],
    );
    check(
      await page.locator('[data-intake-autosave]').count() === 0,
      'existing project detail exposed new-input recovery',
    );

    await page.goto(createUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.locator('input[id*="field-field-name-occ-"]').first()
      .waitFor({ state: 'visible', timeout: 45000 });
    check(await page.locator('[data-intake-autosave]').count() === 0, 'a new form reopened the created draft');
    check(
      await page.evaluate(() => !Object.keys(localStorage).some((key) => key.startsWith('sc:intake:autosave:'))),
      'created draft remains in local storage',
    );

    await page.goto(`${FRONTEND_URL}/a/${payment.action_id}?menu_id=${payment.menu_id}`, {
      waitUntil: 'domcontentloaded',
      timeout: 45000,
    });
    await page.waitForTimeout(3000);
    check(await page.locator('[data-intake-autosave]').count() === 0, 'payment create inherited project intake recovery');

    await page.goto(`${FRONTEND_URL}/f/project.project/${createdId}?menu_id=${intake.menu_id}`, {
      waitUntil: 'domcontentloaded',
      timeout: 45000,
    });
    await page.waitForTimeout(2000);
    check(await page.locator('[data-intake-autosave]').count() === 0, 'project detail exposed intake recovery');

    const cleanup = await browserIntent(page, 'api.data.unlink', {
      model: 'project.project',
      ids: [createdId],
    });
    check(Number(cleanup?.deleted_count || 0) === 1, 'created project cleanup did not delete one record', cleanup);
    const afterCleanup = await browserIntent(page, 'api.data', {
      op: 'list',
      model: 'project.project',
      fields: ['id'],
      domain: [['id', '=', createdId]],
      limit: 1,
    });
    check(Number(afterCleanup?.count || afterCleanup?.records?.length || 0) === 0, 'created project cleanup readback is not empty');
    check(failedIntents.length === 0, 'browser journey observed failed intents', failedIntents);
    check(errors.length === 0, 'browser journey observed page errors', errors);

    const evidence = {
      schema: 'close_03.project_intake_browser.v1',
      status: 'PASS',
      frontend_url: FRONTEND_URL,
      database: DATABASE,
      login: LOGIN,
      entry: {
        menu_id: intake.menu_id,
        action_id: intake.action_id,
        model: intake.model,
      },
      draft_key: draftKey,
      recovered_name: projectName,
      recovered_relation: 'Acceptance Fixture Finance Reviewer',
      validation_failure_preserved_draft: true,
      created_record_id: createdId,
      created_record_readback: readback.records[0],
      draft_absent_after_create: true,
      new_form_had_no_draft: true,
      payment_create_had_no_draft: true,
      project_detail_had_no_draft: true,
      cleanup,
      failed_intents: failedIntents,
      ignored_optional_intents: ignoredOptionalIntents,
      errors,
    };
    writeJson('summary.json', evidence);
    process.stdout.write(`[close-03-browser] PASS created=${createdId} cleaned=1\n`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`[close-03-browser] FAIL ${error?.message || error}\n`);
  process.exitCode = 1;
});

#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5175';
const DB_NAME = process.env.DB_NAME || 'sc_frontend_acceptance';
const PASSWORD = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const TARGETS = JSON.parse(process.env.FRONTEND_FINANCIAL_WORKSPACE_TARGETS_JSON || '{}');
const OUTPUT = path.resolve(process.env.FORM_INFORMATION_ARCHITECTURE_OUTPUT || 'artifacts/frontend-form-information-architecture/browser');
const ALL_CASES = [
  { key: 'contract', role: 'fixture_role_contract_operator', expected: 'CONOUT2600001' },
  { key: 'settlement', role: 'fixture_role_finance', expected: 'FE-A-SET-001' },
  { key: 'payment_request', role: 'fixture_role_finance', expected: 'FE-A-PR-001' },
];
const CASE_FILTER = String(process.env.FORM_INFORMATION_ARCHITECTURE_CASE || '').trim();
const CASES = CASE_FILTER ? ALL_CASES.filter((entry) => entry.key === CASE_FILTER) : ALL_CASES;
const VIEWPORTS = [{ width: 1440, height: 900 }, { width: 390, height: 844 }];

function check(value, message) {
  if (!value) throw new Error(message);
}

async function login(page, username) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(username);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('input').nth(2);
  if (await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45_000 });
}

function recordRoute(target) {
  check(target?.record_id > 0 && target?.action_id > 0 && target?.menu_id > 0, 'missing runtime target');
  return `/r/${encodeURIComponent(target.model)}/${target.record_id}?action_id=${target.action_id}&menu_id=${target.menu_id}`;
}

async function inspectCase(browser, entry) {
  const context = await browser.newContext({ viewport: VIEWPORTS[0], locale: 'zh-CN' });
  const page = await context.newPage();
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('pageerror', (error) => errors.push(error.message));
  await login(page, entry.role);
  await page.goto(`${BASE_URL}${recordRoute(TARGETS[entry.key])}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  const surface = page.locator('[data-product-page-mode="form"]:visible').first();
  await surface.waitFor({ timeout: 45_000 });
  await page.waitForFunction((identity) => document.querySelector('[data-product-page-mode="form"]')?.textContent?.includes(identity), entry.expected, { timeout: 45_000 });
  const rows = [];
  for (const viewport of VIEWPORTS) {
    await page.setViewportSize(viewport);
    await page.waitForTimeout(250);
    const metrics = await surface.evaluate((node) => {
      const visible = (element) => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
      };
      const sectionTitles = [...node.querySelectorAll('[data-group-title]')]
        .filter(visible).map((element) => String(element.getAttribute('data-group-title') || '').trim()).filter(Boolean);
      const fieldKeys = [...node.querySelectorAll('[data-field-key]')]
        .filter(visible).map((element) => String(element.getAttribute('data-field-key') || '').trim()).filter(Boolean);
      const text = node.textContent || '';
      return {
        section_titles: [...new Set(sectionTitles)],
        field_keys: fieldKeys,
        summary_count: [...node.querySelectorAll('.form-readonly-summary')].filter(visible).length,
        internal_section_text: (text.match(/来源追溯|系统办理信息|历史核对信息|录入与归档/g) || []),
        empty_value_count: (text.match(/未填写/g) || []).length,
        horizontal_overflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
      };
    });
    const duplicateFields = metrics.field_keys.filter((name, index, values) => values.indexOf(name) !== index);
    const technicalFields = metrics.field_keys.filter((name) => /^(?:legacy_source_|carrier_|migration_|replay_|technical_|audit_|source_created_)|^(?:create_uid|create_date|write_uid|write_date|entry_user_id|entry_time|creator_name|created_time|archived|active)$/.test(name));
    const screenshot = path.join(OUTPUT, `${entry.key}-${viewport.width}x${viewport.height}.png`);
    await page.screenshot({ path: screenshot, fullPage: true });
    check(metrics.summary_count === 1, `${entry.key} ${viewport.width}: missing readonly business summary`);
    check(metrics.internal_section_text.length === 0, `${entry.key} ${viewport.width}: internal section leaked`);
    check(technicalFields.length === 0, `${entry.key} ${viewport.width}: technical fields leaked ${technicalFields}`);
    check(duplicateFields.length === 0, `${entry.key} ${viewport.width}: duplicate fields ${duplicateFields}`);
    check(metrics.section_titles.length > 0 && metrics.section_titles.length <= 7, `${entry.key} ${viewport.width}: section count ${metrics.section_titles.length} ${metrics.section_titles.join(' / ')}`);
    check(metrics.horizontal_overflow <= 1, `${entry.key} ${viewport.width}: horizontal overflow ${metrics.horizontal_overflow}`);
    rows.push({ case: entry.key, viewport: `${viewport.width}x${viewport.height}`, ...metrics, screenshot });
  }
  check(errors.length === 0, `${entry.key}: runtime errors ${errors.join(' | ')}`);
  await context.close();
  return rows;
}

fs.mkdirSync(OUTPUT, { recursive: true });
check(PASSWORD, 'SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
const browser = await launchChromium({ headless: true });
try {
  const rows = [];
  for (const entry of CASES) rows.push(...await inspectCase(browser, entry));
  const report = { schema_version: 'frontend_form_information_architecture_browser.v1', database: DB_NAME, rows };
  fs.writeFileSync(path.join(OUTPUT, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(`[frontend_form_information_architecture_browser] PASS cases=${CASES.length} viewports=${VIEWPORTS.length}`);
} finally {
  await browser.close();
}

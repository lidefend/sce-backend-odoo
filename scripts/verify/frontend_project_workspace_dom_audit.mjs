#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';
import { resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'project-workspace-dom-audit', operation: 'readonly' });
const target = JSON.parse(process.env.PROJECT_WORKSPACE_TARGET || '{}');
const output = path.resolve(process.env.PROJECT_WORKSPACE_OUTPUT || 'artifacts/frontend-project-workspace-dom-audit/summary.json');

function check(value, message) { if (!value) throw new Error(message); }

check(target && typeof target.route === 'string' && target.route.startsWith('/'), 'target route is required');
check(target.model === 'project.project', 'target model must be project.project');
check(acceptance.login && acceptance.password, 'governed acceptance credentials are required');
fs.mkdirSync(path.dirname(output), { recursive: true });

const identity = {
  title: 'name',
  fields: ['name', 'project_code', 'owner_id', 'manager_id', 'user_id', 'cost_manager_id', 'doc_manager_id'],
  status: ['lifecycle_state', 'sc_approval_state', 'last_update_status'],
};
const viewports = [
  { key: '1440', width: 1440, height: 900 },
  { key: '1024', width: 1024, height: 800 },
  { key: '768', width: 768, height: 900 },
  { key: '390', width: 390, height: 844 },
];

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const evidence = {
  schema: 'frontend_project_workspace_dom_audit.v1',
  passed: false,
  provenance: {
    profile: acceptance.profile,
    base_url: acceptance.baseUrl,
    database: acceptance.database,
    login: acceptance.login,
    expected_sha: acceptance.provenance.expectedSha,
    route: target.route,
    model: target.model,
  },
  console: [],
  pageerror: [],
  http: [],
  identity: {},
  status: {},
  collaboration: {},
  deep: {},
  viewports: [],
};

page.on('console', (message) => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) evidence.console.push(message.text()); });
page.on('pageerror', (error) => evidence.pageerror.push(error.message));
page.on('response', (response) => { if (response.status() >= 500) evidence.http.push({ status: response.status(), url: response.url() }); });

await page.goto(`${acceptance.baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
await page.locator('#login-username, input[autocomplete="username"]').first().fill(acceptance.login);
await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(acceptance.password);
const database = page.locator('input').nth(2);
if (await database.isEnabled().catch(() => false)) await database.fill(acceptance.database);
await page.getByRole('button', { name: /^登录$/ }).click();
await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });

await page.goto(`${acceptance.baseUrl}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
await page.waitForFunction(() => !/正在载入|正在加载|正在初始化/.test(document.body.innerText || ''), null, { timeout: 45_000 });
await page.locator(`[data-field-name="${identity.title}"]`).first().waitFor({ state: 'visible', timeout: 45_000 });

for (const field of identity.fields) {
  evidence.identity[field] = await page.locator(`[data-field-name="${field}"]`).count();
}
for (const field of identity.status) {
  evidence.status[field] = await page.locator(`[data-field-name="${field}"]`).count();
}

const collab = await page.evaluate(() => {
  const count = (selector) => document.querySelectorAll(selector).length;
  const rect = (selector) => {
    const node = document.querySelector(selector);
    if (!node) return null;
    const box = node.getBoundingClientRect();
    return { x: Math.round(box.x), width: Math.round(box.width), height: Math.round(box.height) };
  };
  return {
    followerNodes: count('[data-field-name="message_follower_ids"], [data-component="follower-manager"], .sc-follower'),
    attachmentNodes: count('[data-field-name="message_attachment_ids"], [data-component="attachment-manager"]'),
    timelineNodes: count('[data-component="collaboration-timeline"], .sc-collaboration-timeline'),
    helpTriggers: count('[data-field-help-trigger]'),
    helpTriggerTexts: [...document.querySelectorAll('[data-field-help-trigger]')].slice(0, 12).map((node) => (node.textContent || '').trim()),
    emptyActionRegions: count('[data-action-area-empty], .sc-empty-action-area'),
    attachmentRect: rect('[data-component="attachment-manager"]'),
    timelineRect: rect('[data-component="collaboration-timeline"]'),
  };
});
evidence.collaboration = collab;

const deep = await page.evaluate(() => {
  const q = (selector) => [...document.querySelectorAll(selector)];
  const text = (node) => (node.textContent || '').replace(/\s+/g, ' ').trim();
  const attrs = (node) => {
    const out = {};
    for (const name of ['data-widget-type', 'data-component-renderer', 'data-semantic-status', 'data-status', 'data-field-name', 'data-sc-anchor', 'data-component', 'aria-label']) {
      if (node.getAttribute(name)) out[name] = node.getAttribute(name);
    }
    return out;
  };
  const closestAnchor = (node) => {
    let cur = node;
    while (cur && cur !== document.body) {
      if (cur.getAttribute && cur.getAttribute('data-sc-anchor')) return cur.getAttribute('data-sc-anchor');
      cur = cur.parentElement;
    }
    return null;
  };
  return {
    statusCards: q('[data-widget-type="status_with_color"], .sc-status-badge, [data-semantic-component="ScStatusBadge"]')
      .slice(0, 8).map((node) => ({ text: text(node), ...attrs(node), anchor: closestAnchor(node) })),
    identityOccurrences: ['project_code', 'user_id', 'manager_id'].map((field) => ({
      field,
      nodes: q(`[data-field-name="${field}"]`).slice(0, 4).map((node) => ({
        anchor: closestAnchor(node),
        text: text(node),
      })),
    })),
    helpTriggers: q('[data-field-help-trigger]').slice(0, 8).map((node) => ({
      text: text(node),
      ariaLabel: node.getAttribute('aria-label') || null,
      anchor: closestAnchor(node),
      parentField: (node.closest('[data-field-name]') || {}).getAttribute ? node.closest('[data-field-name]')?.getAttribute('data-field-name') : null,
    })),
    mailCollaboration: ['message_follower_ids', 'message_attachment_ids'].map((field) => ({
      field,
      nodes: q(`[data-field-name="${field}"]`).slice(0, 2).map((node) => {
        const box = node.getBoundingClientRect();
        return { anchor: closestAnchor(node), text: text(node).slice(0, 160), rect: { x: Math.round(box.x), width: Math.round(box.width), height: Math.round(box.height) } };
      }),
    })),
    chatterNodes: q('[data-component*="chatter"], [data-component*="Chatter"], .o-mail-Chatter, [data-field-name*="message_"]')
      .slice(0, 12).map((node) => ({ tag: node.tagName, ...attrs(node), text: text(node).slice(0, 120) })),
  };
});
evidence.deep = deep;

for (const vp of viewports) {
  await page.setViewportSize({ width: vp.width, height: vp.height });
  await page.waitForTimeout(250);
  const geometry = await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    return {
      scrollWidth: Math.max(doc.scrollWidth, body ? body.scrollWidth : 0),
      clientWidth: doc.clientWidth,
      horizontalOverflow: Math.max(doc.scrollWidth, body ? body.scrollWidth : 0) > doc.clientWidth + 1,
    };
  });
  evidence.viewports.push({ key: vp.key, width: vp.width, ...geometry });
  const shot = path.join(path.dirname(output), `viewport-${vp.key}.png`);
  await page.screenshot({ path: shot, fullPage: true });
}

evidence.passed = (
  evidence.identity[identity.title] >= 1
  && evidence.console.length === 0
  && evidence.pageerror.length === 0
  && evidence.http.length === 0
  && evidence.viewports.every((vp) => !vp.horizontalOverflow)
);
fs.writeFileSync(output, JSON.stringify(evidence, null, 2) + '\n');
await browser.close();

if (!evidence.passed) {
  console.error('[project-workspace-dom-audit] FAIL', JSON.stringify({ console: evidence.console.length, pageerror: evidence.pageerror.length, http: evidence.http.length, viewports: evidence.viewports.map((v) => v.key) }));
  process.exit(1);
}
console.log(`[project-workspace-dom-audit] PASS route=${target.route} viewports=${evidence.viewports.length} overflow=0 errors=0`);

#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { resolveAcceptanceEnvironment, assertNoHardcodedNumericRouteFallback } from './lib/frontend_acceptance_environment.mjs';
import { acquireAcceptanceLease } from './lib/frontend_acceptance_lease.mjs';

const local = resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: { SC_ACCEPTANCE_PROFILE: 'local' } });
assert.equal(local.database, 'sc_frontend_acceptance');
const daily = resolveAcceptanceEnvironment({ tool: 'daily-release-probe', env: { SC_ACCEPTANCE_PROFILE: 'daily' } });
assert.equal(daily.baseUrl, 'http://1.95.85.92:18081');
assert.equal(daily.database, 'sc_demo');
assert.throws(() => resolveAcceptanceEnvironment({ tool: 'missing', env: { SC_ACCEPTANCE_PROFILE: 'local' } }), /unknown acceptance tool/);
assert.throws(() => resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', operation: 'fixture', env: { SC_ACCEPTANCE_PROFILE: 'daily' } }), /forbidden/);
assert.throws(() => resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: { SC_ACCEPTANCE_PROFILE: 'daily', DB_NAME: 'wrong' } }), /database override conflicts/);
assert.throws(() => assertNoHardcodedNumericRouteFallback("page.goto('/a/786')"), /hardcoded numeric route/);

const formalSources = [
  'scripts/verify/frontend_delivery_hardening_browser.mjs',
  'scripts/verify/frontend_full_product_audit.mjs',
  'scripts/verify/frontend_form_system_audit.mjs',
  'scripts/verify/frontend_geometry_scroll_audit.mjs',
];
for (const relative of formalSources) {
  const source = await fs.readFile(new URL(`../../${relative}`, import.meta.url), 'utf8');
  assertNoHardcodedNumericRouteFallback(source, relative);
  assert.doesNotMatch(source, /http:\/\/1\.95\.85\.92|\bsc_demo\b/, `${relative} must resolve environment data from governed config`);
}
const deliveryAuditSource = await fs.readFile(new URL('../../scripts/verify/frontend_delivery_hardening_browser.mjs', import.meta.url), 'utf8');
assert.match(deliveryAuditSource, /waitForSurfaceReady/, 'delivery audit must wait for route-specific rendered content');
assert.match(deliveryAuditSource, /assertMeaningfulScreenshot/, 'delivery audit must reject blank or duplicate screenshots');
const formAuditSource = await fs.readFile(new URL('../../scripts/verify/frontend_form_system_audit.mjs', import.meta.url), 'utf8');
assert.doesNotMatch(formAuditSource, /\.contract-form-inspector/, 'form audit must not use the retired form inspector selector');
assert.match(formAuditSource, /\.record-form-inspector/, 'form audit must target the shared record form inspector');
assert.match(formAuditSource, /many2oneComboboxes[\s\S]*candidate.*focus\(\)[\s\S]*搜索更多/, 'form audit must discover a relation dialog by interacting with each eligible field');
const myWorkSource = await fs.readFile(new URL('../../frontend/apps/web/src/components/business/MyWorkApprovalWorkspace.vue', import.meta.url), 'utf8');
assert.match(myWorkSource, /\.product-work\s*\{[^}]*align-content:\s*start/s, 'empty my-work grids must not stretch summary cards');
const actionViewSource = await fs.readFile(new URL('../../frontend/apps/web/src/views/ActionView.vue', import.meta.url), 'utf8');
assert.match(actionViewSource, /\.page\s*\{[^}]*align-content:\s*start/s, 'empty list grids must not create artificial vertical gaps');
const makeSource = await fs.readFile(new URL('../../make/dev.mk', import.meta.url), 'utf8');
assert.doesNotMatch(makeSource, /REQUIRED_ACTIONS\s*:=\s*[^\n]*=>\d+/, 'formal daily target must not pin numeric action ids');

const root = await fs.mkdtemp(path.join(os.tmpdir(), 'sc-acceptance-lease-'));
await fs.mkdir(path.join(root, '.leases'), { recursive: true });
await fs.writeFile(path.join(root, '.leases', 'shared-read-stale.json'), `${JSON.stringify({ pid: 999_999_999 })}\n`);
const shared = await acquireAcceptanceLease({ root, mode: 'shared-read' });
await assert.rejects(() => fs.access(path.join(root, '.leases', 'shared-read-stale.json')));
await assert.rejects(() => acquireAcceptanceLease({ root, mode: 'exclusive-write' }), /lease conflict/);
await shared.release();
const exclusive = await acquireAcceptanceLease({ root, mode: 'exclusive-service' });
await exclusive.release();
await fs.rm(root, { recursive: true, force: true });
console.log('[frontend_acceptance_environment_test] PASS');

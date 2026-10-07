#!/usr/bin/env node
// Bounded read-only diagnostic: log in as each declared denied-role candidate on
// the registered acceptance runtime and record its capability closure plus the
// number of released navigation targets it actually received.
//
// This exists so the incremental scope planner can derive the affected entry set
// offline, without re-walking the product surfaces. It produces no delivery
// evidence, asserts no product behaviour, and never replaces the owning layer's
// check: it only observes identity and navigation delivery.
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';
import { countReleasedNavigationTargets, loadOverlay } from './business_entry_matrix_model.mjs';

const BASE = (process.env.SC_ACCEPTANCE_FRONTEND_URL || '').replace(/\/$/, '');
const DB = process.env.SC_ACCEPTANCE_DATABASE || process.env.DB_NAME || 'sc_demo';
const PASSWORD = process.env.ACCEPTANCE_PASSWORD || '';
const OVERLAY_PATH = process.env.SC_ENTRY_MATRIX_OVERLAY || 'scripts/verify/business_entry_matrix_overlay.json';
const OUT = process.env.SC_ENTRY_MATRIX_CLOSURES_OUT
  || path.join('artifacts', 'frontend-business-entry-matrix', 'negative_closures.json');

if (!BASE) throw new Error('SC_ACCEPTANCE_FRONTEND_URL is required');
if (!PASSWORD) throw new Error('ACCEPTANCE_PASSWORD is required');

function servedRevisionOf(payload) {
  const data = payload?.data || payload?.result || payload || {};
  return String(data.git_sha || data.source_revision || '');
}

async function observe(browser, role, served) {
  const context = await browser.newContext({ locale: 'zh-CN' });
  const page = await context.newPage();
  const state = { roleXmlids: [], nav: null, company: null, error: null };
  page.on('response', async (response) => {
    const request = response.request();
    let payload = {};
    try { payload = JSON.parse(request.postData() || '{}'); } catch { return; }
    const intent = String(payload.intent || '');
    if (response.status() >= 400) return;
    try {
      const body = await response.json();
      const data = body.data || (body.result && (body.result.data || body.result)) || {};
      if (intent === 'login') {
        const principal = data.principal;
        if (principal && Array.isArray(principal.role_xmlids)) {
          state.roleXmlids = principal.role_xmlids.map(String);
        }
        const revision = servedRevisionOf(body);
        if (revision) served.value = revision;
      } else if (intent === 'system.init' || intent === 'app.init') {
        const user = data.user;
        if (user && Number(user.company_id) > 0) state.company = Number(user.company_id);
        const nav = data.navigation && data.navigation.nav;
        if (Array.isArray(nav)) state.nav = nav;
      }
    } catch { /* identity stays null and the snapshot fails closed downstream */ }
  });
  try {
    await page.goto(`${BASE}/login?db=${DB}`, { waitUntil: 'networkidle' });
    const inputs = page.locator('input');
    await inputs.nth(0).fill(role);
    await inputs.nth(1).fill(PASSWORD);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
    await page.waitForTimeout(3000);
  } catch (error) {
    state.error = String((error && error.message) || error);
  }
  await context.close().catch(() => {});
  return state;
}

// Reuse-first input: an already-recorded observation of the same runtime must
// be adopted instead of re-walking the ten principal logins.  The snapshot is
// accepted either as a prior ``business_entry_negative_closures.v1`` artifact or
// as the flat ``{role: {...}}`` map the bounded probe emits.
const SNAPSHOT = (process.env.SC_ENTRY_MATRIX_CLOSURES_FROM || '').trim();

function adoptSnapshot() {
  const document = JSON.parse(fs.readFileSync(SNAPSHOT, 'utf8'));
  const raw = document.schema === 'business_entry_negative_closures.v1'
    ? document.candidates
    : document;
  const candidates = {};
  for (const [role, value] of Object.entries(raw || {})) {
    if (!value || typeof value !== 'object') continue;
    const roleXmlids = Array.isArray(value.role_xmlids) ? value.role_xmlids.map(String) : [];
    candidates[role] = {
      closure_size: Number(value.closure_size ?? roleXmlids.length),
      role_xmlids: roleXmlids,
      nav_targets: Number(value.nav_targets || 0),
      company: value.company === undefined ? null : value.company,
      error: value.error || null,
      adopted_from: SNAPSHOT,
    };
  }
  return { candidates, served: String(document.served_revision || '') };
}

const overlay = loadOverlay(OVERLAY_PATH);
const order = overlay.deniedRoleCandidates;
if (!order.length) throw new Error(`${OVERLAY_PATH} declares no denied_role_candidates`);

const served = { value: '' };
let candidates;
if (SNAPSHOT) {
  const adopted = adoptSnapshot();
  candidates = adopted.candidates;
  served.value = adopted.served;
  const missing = order.filter((role) => !Object.prototype.hasOwnProperty.call(candidates, role));
  if (missing.length) {
    throw new Error(`${SNAPSHOT} does not observe the declared candidates: ${missing.join(', ')}`);
  }
} else {
  const browser = await launchChromium({ headless: true });
  candidates = {};
  try {
    for (const role of order) {
      if (Object.prototype.hasOwnProperty.call(candidates, role)) continue;
      const observed = await observe(browser, role, served);
      candidates[role] = {
        closure_size: observed.roleXmlids.length,
        role_xmlids: observed.roleXmlids,
        nav_targets: observed.nav ? countReleasedNavigationTargets(observed.nav) : 0,
        company: observed.company,
        error: observed.error,
      };
    }
  } finally {
    await browser.close();
  }
}

const failed = Object.entries(candidates).filter(([, value]) => value.error);
const payload = {
  schema: 'business_entry_negative_closures.v1',
  generated_at: new Date().toISOString(),
  base_url: BASE,
  database: DB,
  served_revision: served.value,
  reused_observation: SNAPSHOT || null,
  candidates,
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
const ineligible = Object.entries(candidates)
  .filter(([, value]) => value.nav_targets === 0)
  .map(([role]) => role);
console.log(`[business-entry-negatives] candidates=${order.length} ineligible=${ineligible.length} closure=${OUT}`);
if (failed.length) {
  console.log(`[business-entry-negatives] FAILED ${failed.map(([role, value]) => `${role}:${value.error}`).join('; ')}`);
  process.exit(2);
}

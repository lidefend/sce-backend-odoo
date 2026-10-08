// Pure model for the declaration-driven business-entry acceptance matrix.
//
// Both the browser probe (scripts/verify/business_entry_matrix_browser.mjs) and
// the incremental scope planner (scripts/verify/business_entry_matrix_scope.mjs)
// import this module, so the declaration consumption, the negative-authority
// candidate resolution and the key fingerprint cannot drift between execution
// and planning. Nothing here touches the network, the filesystem or the DOM.

import fs from 'node:fs';
import crypto from 'node:crypto';

export const SCOPE_SCHEMA = 'business_entry_matrix_scope.v1';

// Count the released navigation targets a principal actually received. A node
// only carries a route when the runtime published a positive action_id/menu_id
// pair; a candidate that received none cannot support a denial, because
// "the entry is absent" would be vacuously true rather than exercised.
export function countReleasedNavigationTargets(nav) {
  const pending = Array.isArray(nav) ? [...nav] : [];
  let count = 0;
  while (pending.length) {
    const node = pending.shift();
    if (!node || typeof node !== 'object') continue;
    const meta = node.meta && typeof node.meta === 'object' ? node.meta : {};
    const actionId = Number(node.action_id || meta.action_id || 0);
    const menuId = Number(node.menu_id || meta.menu_id || 0);
    if (actionId > 0 && menuId > 0) count += 1;
    if (Array.isArray(node.children)) pending.push(...node.children);
  }
  return count;
}

export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const ch = text[index];
    if (quoted) {
      if (ch === '"') {
        if (text[index + 1] === '"') { field += '"'; index += 1; } else { quoted = false; }
      } else { field += ch; }
      continue;
    }
    if (ch === '"') { quoted = true; continue; }
    if (ch === ',') { row.push(field); field = ''; continue; }
    if (ch === '\n') { row.push(field); field = ''; rows.push(row); row = []; continue; }
    if (ch === '\r') continue;
    field += ch;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

export function loadMatrix(csvPath) {
  const table = parseCsv(fs.readFileSync(csvPath, 'utf8'));
  const header = table.shift();
  return table
    .filter((cols) => cols.some((value) => String(value).trim() !== ''))
    .map((cols) => Object.fromEntries(header.map((name, index) => [name, cols[index] === undefined ? '' : cols[index]])));
}

export function loadOverlay(overlayPath) {
  const body = JSON.parse(fs.readFileSync(overlayPath, 'utf8'));
  return {
    defaults: body.defaults && typeof body.defaults === 'object' ? body.defaults : {},
    entries: body.entries && typeof body.entries === 'object' ? body.entries : {},
    deniedRoleCandidates: Array.isArray(body.denied_role_candidates)
      ? body.denied_role_candidates.map(String)
      : [],
  };
}

export function overlayFor(overlay, menuXmlid) {
  const merged = { ...overlay.defaults, ...(overlay.entries[menuXmlid] || {}) };
  if (!('detail' in merged)) merged.detail = true;
  if (!('expect_write' in merged)) merged.expect_write = null;
  return merged;
}

export function declaredEntryGroups(row) {
  try {
    const parsed = JSON.parse(String(row.role_authority || '{}'));
    if (Array.isArray(parsed.action_groups) && parsed.action_groups.length) {
      return parsed.action_groups.map(String);
    }
    if (Array.isArray(parsed.menu_chain)) {
      return [...new Set(parsed.menu_chain
        .flatMap((node) => (node && Array.isArray(node.groups) ? node.groups : []))
        .map(String))];
    }
    return [];
  } catch {
    return [];
  }
}

export function selectEntries(matrix, overlay, filters = {}) {
  const { skipPassed = false, keys = [], domain = '' } = filters;
  let selected = matrix.filter((row) => skipPassed || row.acceptance_status !== 'passed');
  if (keys.length) selected = selected.filter((row) => keys.includes(row.menu_xmlid));
  if (domain) selected = selected.filter((row) => row.domain === domain);
  return selected
    .map((row) => ({ row, behaviour: overlayFor(overlay, row.menu_xmlid) }))
    .filter((entry) => entry.row.menu_xmlid && entry.row.action_xmlid);
}

// Build the eligibility map from the principal closures observed on the runtime.
// A candidate is eligible only when the runtime released it at least one
// navigation target; an empty navigation tree makes "the entry is absent"
// vacuously true, which would fabricate a denial that was never exercised.
export function candidateStates(candidateOrder, closures) {
  const states = new Map();
  for (const role of candidateOrder) {
    const observed = closures && closures[role];
    if (!observed) {
      states.set(role, { role, eligible: false, missing: true, roleXmlids: [], releasedTargets: 0 });
      continue;
    }
    const roleXmlids = Array.isArray(observed.role_xmlids) ? observed.role_xmlids.map(String) : [];
    const releasedTargets = Number(observed.nav_targets || 0);
    states.set(role, {
      role,
      eligible: roleXmlids.length > 0 && releasedTargets > 0,
      missing: false,
      roleXmlids,
      releasedTargets,
    });
  }
  return states;
}

export function ineligibleCandidates(candidateOrder, states) {
  return candidateOrder
    .map((role) => states.get(role))
    .filter((candidate) => candidate && !candidate.eligible && !candidate.missing)
    .map((candidate) => ({ role: candidate.role, released_targets: candidate.releasedTargets, capability_closure_size: candidate.roleXmlids.length }));
}

// Resolve which eligible candidate owns the denial for one entry. The probe
// picks the first eligible candidate whose capability closure is disjoint from
// the entry's declared groups; this function is the single implementation of
// that rule.
export function resolveNegativeCandidate(declared, candidateOrder, states, pinned = null) {
  if (!declared.length) {
    return { chosen: null, reason: 'entry role_authority declares no group to deny' };
  }
  for (const role of candidateOrder) {
    if (pinned && role !== pinned) continue;
    const candidate = states.get(role);
    if (!candidate || !candidate.eligible) continue;
    if (!candidate.roleXmlids.length) continue;
    if (!candidate.roleXmlids.some((cap) => declared.includes(cap))) {
      return { chosen: role, reason: 'disjoint eligible candidate' };
    }
  }
  return {
    chosen: null,
    reason: pinned
      ? 'pinned denied_role is not an eligible candidate disjoint from the entry declared groups'
      : 'no eligible denied-role candidate declares a capability closure disjoint from the entry declared groups',
  };
}

// Group the derived denial per candidate, exactly as the probe asserts it.
export function negativePlanByCandidate(entries, candidateOrder, states) {
  const byCandidate = new Map();
  const undecidable = [];
  for (const { row, behaviour } of entries) {
    const declared = declaredEntryGroups(row);
    const pinned = behaviour.denied_role ? String(behaviour.denied_role) : null;
    const resolved = resolveNegativeCandidate(declared, candidateOrder, states, pinned);
    if (!resolved.chosen) {
      undecidable.push({ entry: row.menu_xmlid, declared_groups: declared, reason: resolved.reason });
      continue;
    }
    if (!byCandidate.has(resolved.chosen)) byCandidate.set(resolved.chosen, []);
    byCandidate.get(resolved.chosen).push({ action: row.action_xmlid, menu: row.menu_xmlid });
  }
  return { byCandidate, undecidable };
}

export function universalCapabilities(candidateOrder, states) {
  const closures = candidateOrder
    .map((role) => states.get(role))
    .filter((candidate) => candidate && candidate.eligible)
    .map((candidate) => candidate.roleXmlids)
    .filter((caps) => Array.isArray(caps) && caps.length);
  if (!closures.length) return [];
  return closures.reduce((acc, caps) => acc.filter((cap) => caps.includes(cap)));
}

// Row fields the probe actually consumes. A change to any of them can change
// this entry's outcome, so they are bound into the key fingerprint.
const CONSUMED_ROW_FIELDS = [
  'menu_xmlid', 'action_xmlid', 'label', 'domain', 'model', 'scope_disposition',
  'batch', 'role_authority', 'rendering_path',
];

// Row fields that record an outcome rather than declare an input. They must
// never enter the fingerprint: a declaration-driven check exists so that
// recording a result cannot invalidate the observation that produced it.
// `acceptance_status` is written when a batch is closed, so binding it made the
// closing commit re-open every row it had just closed (observed as three
// consecutive 89-key re-walks on the same governance runtime with no changed
// input). The status still travels as provenance, so a change stays visible.
export const ROW_OUTCOME_FIELDS = ['acceptance_status'];

export function canonicalJson(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value === undefined ? null : value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
}

export function sha256(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

export function fileRevision(repoRoot, relativePaths) {
  const parts = [];
  for (const relative of relativePaths) {
    const absolute = `${repoRoot.replace(/\/$/, '')}/${relative}`;
    parts.push(`${relative}:${sha256(fs.readFileSync(absolute, 'utf8'))}`);
  }
  return sha256(parts.join('\n'));
}

// Model revision governs the derivation only (declaration consumption,
// candidate eligibility and denial ownership). A change here affects exactly
// the entries whose derived denial changed, which the planner can compute
// offline; the browser file revision is tracked separately and does affect
// every key because it carries the entry assertions themselves.
export const MODEL_INPUTS = [
  'scripts/verify/business_entry_matrix_model.mjs',
  'scripts/verify/released_navigation_target.mjs',
];
export const PROBE_INPUTS = ['scripts/verify/business_entry_matrix_browser.mjs'];

export function entryFingerprint({ row, behaviour, environment, derived, modelRevision, probeRevision }) {
  const consumed = {};
  for (const field of CONSUMED_ROW_FIELDS) consumed[field] = row[field] === undefined ? '' : String(row[field]);
  return sha256(canonicalJson({
    row: consumed,
    behaviour,
    environment,
    derived: derived || null,
    model_revision: modelRevision,
    // The browser probe carries the entry assertions themselves, so an edit to
    // it re-opens every key unless the executor explicitly declares the change
    // assertion-neutral by pinning the reviewed revision.
    probe_revision: probeRevision === undefined ? null : probeRevision,
  }));
}

// Identity that governs reuse. Every browser assertion here runs against the
// bundle the target serves, so the served *bundle* is part of the identity: a
// candidate built from another bundle may render another surface, and reusing
// the older observation would report coverage the run never produced.
//
// The bundle identity is the served frontend artifact fingerprint the runtime
// publishes as `frontend_build_sha256`, not the deployed commit. The commit
// changes on every mainline merge, including merges that never rebuild the
// frontend, so binding the commit re-walked every entry on every deployment and
// destroyed the incremental lane. The artifact fingerprint changes exactly when
// the served bundle changed, which is the input the assertions depend on. The
// probe still binds the *deployment* revision, so an observation is only taken
// on the declared deployment; that revision is recorded as provenance.
//
// Fail-closed: when the runtime declares no bundle fingerprint, reuse degrades
// to the deployed revision (never silently across bundles), and the caller
// records `reuse_identity_key=served_revision` so the degradation is visible.
export const BUNDLE_IDENTITY_KEY = 'frontend_build_sha256';
export const FALLBACK_IDENTITY_KEY = 'served_revision';
const BUNDLE_FINGERPRINT = /^[0-9a-f]{64}$/;

export function reuseIdentityKey({ bundleFingerprint } = {}) {
  return BUNDLE_FINGERPRINT.test(String(bundleFingerprint || '').trim().toLowerCase())
    ? BUNDLE_IDENTITY_KEY
    : FALLBACK_IDENTITY_KEY;
}

export function environmentIdentity({ baseUrl, database, login, candidateOrder, servedRevision, bundleFingerprint }) {
  const revision = String(servedRevision || '').trim();
  if (!revision) {
    throw new Error('environmentIdentity: the served revision is required to bind reuse');
  }
  const environment = {
    base_url: String(baseUrl || ''),
    database: String(database || ''),
    login: String(login || ''),
    denied_role_candidates: candidateOrder.map(String),
  };
  const bundle = String(bundleFingerprint || '').trim().toLowerCase();
  if (BUNDLE_FINGERPRINT.test(bundle)) {
    return { ...environment, [BUNDLE_IDENTITY_KEY]: bundle };
  }
  return { ...environment, [FALLBACK_IDENTITY_KEY]: revision };
}

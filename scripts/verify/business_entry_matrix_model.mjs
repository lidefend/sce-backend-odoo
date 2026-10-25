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
      states.set(role, { role, eligible: false, missing: true, roleXmlids: [], releasedTargets: 0, company: null });
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
      // The company the candidate's closure was observed in. It is part of the
      // permission fact: the same capability closure grants a different record
      // set in another company, so a change here must re-open the units bound to
      // this candidate and nothing else.
      company: observed.company === undefined || observed.company === null ? null : Number(observed.company),
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

export function entryFingerprint({
  row, behaviour, environment, surfaceInputs, derived, permissionContext, modelRevision, probeRevision,
}) {
  const consumed = {};
  for (const field of CONSUMED_ROW_FIELDS) consumed[field] = row[field] === undefined ? '' : String(row[field]);
  return sha256(canonicalJson({
    row: consumed,
    behaviour,
    environment,
    // What the assertions were measured against, bound per unit so a change to
    // one entry's declared surface re-opens exactly that entry.
    surface_inputs: surfaceInputs || null,
    derived: derived || null,
    // The permission fact this one entry's denial observation depends on,
    // bound per unit so a change to one candidate's closure re-opens exactly
    // the entries bound to that candidate instead of every declared entry.
    permission_context: permissionContext || null,
    model_revision: modelRevision,
    // The browser probe carries the entry assertions themselves, so an edit to
    // it re-opens every key unless the executor explicitly declares the change
    // assertion-neutral by pinning the reviewed revision.
    probe_revision: probeRevision === undefined ? null : probeRevision,
  }));
}

export const BUNDLE_IDENTITY_KEY = 'frontend_build_sha256';
export const FALLBACK_IDENTITY_KEY = 'served_revision';
export const ACTING_COMPANY_KEY = 'acting_company_id';
export const ACTING_CLOSURE_KEY = 'acting_role_closure_sha256';
export const SURFACE_SCOPE_WHOLE = 'whole_artifact';
export const SURFACE_SCOPE_DECLARED = 'declared_surfaces';
export const SURFACE_SCOPE_REVISION = 'served_revision_degraded';
const SHA256_HEX = /^[0-9a-f]{64}$/;

// Deployment provenance is recorded, never bound as a validity input.
//
// The deploying commit (served revision) changes on every mainline merge,
// including merges that never rebuild the frontend, so binding it re-walked
// every entry on every deployment and destroyed the incremental lane. It is
// still recorded so an observation stays traceable to the deployment that
// produced it, but the validity basis is the served surface (below).
export function deploymentProvenance({ servedRevision, bundleFingerprint } = {}) {
  const revision = String(servedRevision || '').trim();
  if (!revision) {
    throw new Error(
      'deploymentProvenance: the served revision is required so an observation is traceable to a deployment',
    );
  }
  const bundle = String(bundleFingerprint || '').trim().toLowerCase();
  return {
    served_revision: revision,
    [BUNDLE_IDENTITY_KEY]: SHA256_HEX.test(bundle) ? bundle : null,
  };
}

export function reuseIdentityKey({ bundleFingerprint } = {}) {
  return SHA256_HEX.test(String(bundleFingerprint || '').trim().toLowerCase())
    ? BUNDLE_IDENTITY_KEY
    : FALLBACK_IDENTITY_KEY;
}

// The per-unit surface dependency: what this one entry's assertions were
// measured against.
//
// It is bound per unit, not folded into the shared environment identity, so a
// change to the served surface re-opens exactly the entries whose declared
// surface moved. When the build publishes a per-surface hash map
// (`surfaceScopes`) and the entry declares the surfaces it renders, only those
// hashes bind, so an unrelated frontend change does not re-open this entry.
// When no per-surface declaration is available the binding degrades, fail-closed,
// to the whole served artifact and records `scope=whole_artifact`.
export function surfaceInputs({
  bundleFingerprint, servedRevision, surfaces = [], surfaceScopes = {},
} = {}) {
  const declared = (Array.isArray(surfaces) ? surfaces : [])
    .map((surface) => String(surface || '').trim())
    .filter(Boolean);
  const unique = [...new Set(declared)].sort();
  const scopes = surfaceScopes && typeof surfaceScopes === 'object' ? surfaceScopes : {};
  const hashes = unique
    .map((surface) => ({ surface, sha: String(scopes[surface] || '').trim().toLowerCase() }))
    .filter((item) => SHA256_HEX.test(item.sha));
  if (unique.length && hashes.length === unique.length) {
    return {
      scope: SURFACE_SCOPE_DECLARED,
      surfaces: unique,
      sha256: sha256(hashes.map((item) => `${item.surface}:${item.sha}`).join('\n')),
    };
  }
  const whole = String(bundleFingerprint || '').trim().toLowerCase();
  if (SHA256_HEX.test(whole)) {
    return { scope: SURFACE_SCOPE_WHOLE, surfaces: [], sha256: whole };
  }
  // Last-resort degradation: a runtime that publishes no artifact fingerprint
  // cannot narrow the binding, so reuse degrades to the serving deployment
  // (never across deployments) and records the degradation. Fail-closed.
  const revision = String(servedRevision || '').trim();
  if (revision) {
    return { scope: SURFACE_SCOPE_REVISION, surfaces: [], sha256: sha256(revision) };
  }
  throw new Error(
    'surfaceInputs: this entry declares no fully hashed surface scope and the runtime published no '
    + 'artifact fingerprint or serving deployment, so its assertions cannot be bound to the surface '
    + 'they were measured on',
  );
}

// The authoritative acting-principal readback the denial plan is bound to.
//
// The negative-closure diagnostic logs in as the acting principal as well as
// the denied-role candidates, so both the company and the acting account's own
// role closure are observed facts rather than assumptions. A snapshot that
// observes another login, carries no company, or carries no closure cannot bind
// reuse: the same login in another company sees another record set, and a role
// change on the same account in the same company changes what it can reach, so
// reuse across either would report coverage the run never produced. Fail-closed.
export function actingContext(closures = {}, { login } = {}) {
  const acting = (closures && closures.acting) || {};
  const observedLogin = String(acting.login || '').trim();
  const expectedLogin = String(login || '').trim();
  if (!observedLogin || !expectedLogin || observedLogin !== expectedLogin) {
    throw new Error(
      `actingContext: the closure snapshot observed login ${observedLogin || '(none)'} but reuse is bound `
      + `to ${expectedLogin || '(none)'}; refresh the snapshot before planning reuse`,
    );
  }
  const company = Number(acting.company_id);
  if (!Number.isInteger(company) || company <= 0) {
    throw new Error(
      'actingContext: the closure snapshot carries no authoritative acting-company readback '
      + '(closures.acting.company_id); refresh the snapshot before planning reuse',
    );
  }
  const roleXmlids = Array.isArray(acting.role_xmlids) ? acting.role_xmlids.map(String).filter(Boolean) : [];
  if (!roleXmlids.length) {
    throw new Error(
      'actingContext: the closure snapshot carries no authoritative acting-principal role closure '
      + "(closures.acting.role_xmlids); the acting account's own permissions must invalidate reuse, "
      + 'so the closure is required -- refresh the snapshot before planning reuse',
    );
  }
  return {
    login: observedLogin,
    company_id: company,
    role_closure_sha256: sha256([...new Set(roleXmlids)].sort().join('\n')),
  };
}

// The permission fact a single entry's denial observation depends on.
//
// It is deliberately *not* part of the shared environment identity: the shared
// identity would invalidate every declared entry whenever any candidate's
// permissions moved, and it never carried the readback at all, so a change to
// one candidate's closure was invisible and its units were wrongly reused.
export function permissionContext({ candidate, state } = {}) {
  const role = candidate === undefined || candidate === null ? '' : String(candidate);
  if (!role) {
    // The declaration assigned this entry no denial candidate, so it has no
    // permission fact to bind; the undecidable set is reported separately.
    return {
      denied_candidate: null,
      eligible: false,
      released_targets: 0,
      capability_closure_sha256: null,
      company_id: null,
    };
  }
  if (!state || state.missing === true) {
    throw new Error(
      `permissionContext: no authoritative closure readback for the denied candidate ${role}`,
    );
  }
  const roleXmlids = Array.isArray(state.roleXmlids) ? state.roleXmlids.map(String).sort() : [];
  return {
    denied_candidate: role,
    eligible: state.eligible === true,
    released_targets: Number(state.releasedTargets || 0),
    capability_closure_sha256: sha256(roleXmlids.join('\n')),
    company_id: state.company === undefined || state.company === null ? null : Number(state.company),
  };
}

// Who/where the observation was taken as: the runtime and the acting principal's
// own permission context. These are shared by every declared entry, so a change
// invalidates all of them, which is correct: they define what the run could see
// at all. The served surface is *not* here; it binds per unit (surfaceInputs).
export function environmentIdentity({
  baseUrl, database, login, actingCompanyId, actingRoleClosureSha256,
}) {
  const company = Number(actingCompanyId);
  if (!Number.isInteger(company) || company <= 0) {
    throw new Error('environmentIdentity: the authoritative acting-company readback is required to bind reuse');
  }
  const closure = String(actingRoleClosureSha256 || '').trim().toLowerCase();
  if (!SHA256_HEX.test(closure)) {
    throw new Error(
      "environmentIdentity: the acting principal's authoritative role closure "
      + '(actingRoleClosureSha256) is required to bind reuse',
    );
  }
  return {
    base_url: String(baseUrl || ''),
    database: String(database || ''),
    login: String(login || ''),
    [ACTING_COMPANY_KEY]: company,
    [ACTING_CLOSURE_KEY]: closure,
  };
}

// Observation import binds the original execution inputs, never current labels
// pasted onto an old outcome. Deployment revisions remain provenance only.
export function observationBinding(document) {
  return { identity: document.identity, units: document.units.map(({ id, fingerprint }) => ({ id, fingerprint })) };
}

export function validateClosureEnvironment(document, { baseUrl, database }) {
  if (!baseUrl || !database || document.base_url !== baseUrl || document.database !== database) {
    throw new Error('closure snapshot runtime URL/database mismatch; refresh the snapshot');
  }
}

export function validateObservationBinding(summary, plan, current) {
  const observed = summary.observation_binding;
  const planned = plan.observation_binding;
  if (!observed?.identity || !Array.isArray(observed.units) || !planned?.identity || !Array.isArray(planned.units)) {
    throw new Error('observation/plan missing original execution input binding');
  }
  const actor = actingContext({ acting: summary.acting }, { login: summary.login });
  const actual = environmentIdentity({ baseUrl: summary.base_url, database: summary.database,
    login: actor.login, actingCompanyId: actor.company_id, actingRoleClosureSha256: actor.role_closure_sha256 });
  for (const identity of [observed.identity, planned.identity, current.identity]) {
    if (canonicalJson(identity) !== canonicalJson(actual)) throw new Error('observation runtime/actor identity mismatch');
  }
  if (summary.session_company_id !== actor.company_id) throw new Error('observation acting company mismatch');
  const plannedKeys = new Set(plan.execute || plan.affected || []);
  const selected = summary.selection?.keys;
  if (!Array.isArray(selected) || !selected.length || selected.some(key => !plannedKeys.has(key))) {
    throw new Error('observation selection is not bound to original plan');
  }
  const maps = [observed, planned, current].map(doc => {
    const result = new Map();
    for (const unit of doc.units) {
      if (!unit.id || !/^[a-f0-9]{64}$/.test(unit.fingerprint || '') || result.has(unit.id)) {
        throw new Error('invalid or duplicate execution input fingerprint');
      }
      result.set(unit.id, unit.fingerprint);
    }
    return result;
  });
  for (const entry of summary.entries || []) {
    const key = entry.entry;
    if (!selected.includes(key) || !maps[0].has(key)
      || maps[0].get(key) !== maps[1].get(key) || maps[0].get(key) !== maps[2].get(key)) {
      throw new Error(`observation input fingerprint/selection mismatch: ${key}`);
    }
  }
  return observed;
}

// A namespace path owns database selection; never add client database hints.
export function matrixLoginUrl(baseUrl) {
  const url = new URL(baseUrl);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('matrix base URL must have only an HTTP origin and optional namespace path');
  }
  url.pathname = url.pathname.replace(/\/+$/, '') + '/login';
  return url.toString();
}

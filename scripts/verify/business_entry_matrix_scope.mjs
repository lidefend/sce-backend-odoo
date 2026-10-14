#!/usr/bin/env node
// Adapter that declares the business-entry matrix surface as evidence units for
// the systemic evidence-scope engine (scripts/ops/evidence_scope.py).
//
// It computes, offline, one unit per declared entry: the declared row, the
// overlay behaviour, the negative-authority candidate that entry resolves to,
// the registered environment identity, and the tool revisions. The engine then
// decides what may be reused and what must actually be executed; this adapter
// never walks a product surface.
//
//   --emit-units   <out.json>   the declared surface with per-unit fingerprints
//   --emit-results <out.json> --summary <probe summary.json> --plan <plan.json>
//                               the units this run actually executed, for recording
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import {
  ACTING_COMPANY_KEY,
  validateClosureEnvironment,
  validateObservationBinding,
  MODEL_INPUTS,
  PROBE_INPUTS,
  actingContext,
  candidateStates,
  declaredEntryGroups,
  deploymentProvenance,
  entryFingerprint,
  environmentIdentity,
  fileRevision,
  permissionContext,
  reuseIdentityKey,
  surfaceInputs,
  loadMatrix,
  loadOverlay,
  overlayFor,
  resolveNegativeCandidate,
  sha256,
} from './business_entry_matrix_model.mjs';

const CHECK = 'verify.frontend.business_entry.matrix.browser';
const UNITS_SCHEMA = 'evidence_scope.units.v1';
const RESULTS_SCHEMA = 'evidence_scope.results.v1';
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');

const CSV_PATH = process.env.SC_ENTRY_MATRIX_CSV || 'docs/product/frontend_business_entry_acceptance_v1.csv';
const OVERLAY_PATH = process.env.SC_ENTRY_MATRIX_OVERLAY || 'scripts/verify/business_entry_matrix_overlay.json';
const CLOSURES_PATH = process.env.SC_ENTRY_MATRIX_CLOSURES
  || path.join('artifacts', 'frontend-business-entry-matrix', 'negative_closures.json');
const BASE = (process.env.SC_ACCEPTANCE_FRONTEND_URL || '').replace(/\/$/, '');
const DATABASE = process.env.SC_ACCEPTANCE_DATABASE || process.env.DB_NAME || 'sc_demo';
const SERVED_REVISION = process.env.SC_ACCEPTANCE_TARGET_SHA || '';
// The served frontend artifact fingerprint the runtime publishes as
// `frontend_build_sha256` (declared by the governed frontend build entry). It is
// the reuse input that changes exactly when the served bundle changed, which is
// what the entry assertions actually depend on.
const BUNDLE_FINGERPRINT = (process.env.SC_ACCEPTANCE_FRONTEND_BUILD_SHA || '').trim().toLowerCase();
const LOGIN = process.env.ACCEPTANCE_LOGIN || '';
const NEUTRAL_REVISION = (process.env.SC_ENTRY_MATRIX_PROBE_ASSERTION_NEUTRAL || '').trim();
// Optional per-entry surface dependency declaration published by the build:
// ``{"entries": {"<menu_xmlid>": ["surface.a", ...]}, "hashes": {"surface.a": "<sha256>"}}``.
// When an entry declares every one of its surfaces with a hash, only those
// hashes bind it, so an unrelated frontend change does not re-open it. Absent,
// or partially covered, the binding degrades to the whole served artifact.
const SURFACE_SCOPES_PATH = (process.env.SC_ENTRY_MATRIX_SURFACE_SCOPES || '').trim();

function argsOf(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = argv[index + 1];
    if (next === undefined || next.startsWith('--')) { parsed[key] = '1'; continue; }
    parsed[key] = next; index += 1;
  }
  return parsed;
}

function writeJson(target, payload) {
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

function loadClosures() {
  if (!fs.existsSync(CLOSURES_PATH)) {
    throw new Error(`${CLOSURES_PATH} is missing: run the read-only closure diagnostic before planning`);
  }
  const document = JSON.parse(fs.readFileSync(CLOSURES_PATH, 'utf8'));
  if (document.schema !== 'business_entry_negative_closures.v1') {
    throw new Error(`${CLOSURES_PATH}: unexpected schema ${document.schema}`);
  }
  validateClosureEnvironment(document, { baseUrl: BASE, database: DATABASE });
  return document;
}

function loadSurfaceScopes() {
  if (!SURFACE_SCOPES_PATH) return { entries: {}, hashes: {} };
  const body = JSON.parse(fs.readFileSync(SURFACE_SCOPES_PATH, 'utf8'));
  return {
    entries: body && typeof body.entries === 'object' ? body.entries : {},
    hashes: body && typeof body.hashes === 'object' ? body.hashes : {},
  };
}

export function surface() {
  if (!SERVED_REVISION) throw new Error('SC_ACCEPTANCE_TARGET_SHA is required so the observation is traceable to a deployment');
  const matrix = loadMatrix(CSV_PATH);
  const overlay = loadOverlay(OVERLAY_PATH);
  const closures = loadClosures();
  const order = overlay.deniedRoleCandidates;
  const states = candidateStates(order, closures.candidates);
  const surfaceScopes = loadSurfaceScopes();
  // The acting principal's company and own role closure are authoritative
  // readbacks, not caller assumptions: the same login in another company sees
  // another record set, and a role change on the same account changes what it
  // can reach, so both must invalidate reuse.
  const acting = actingContext(closures, { login: LOGIN });
  const identity = environmentIdentity({
    baseUrl: BASE, database: DATABASE, login: LOGIN, actingCompanyId: acting.company_id,
    actingRoleClosureSha256: acting.role_closure_sha256,
  });
  // The deploying commit is provenance, not a validity input.
  const provenance = deploymentProvenance({
    servedRevision: SERVED_REVISION, bundleFingerprint: BUNDLE_FINGERPRINT,
  });
  const modelRevision = fileRevision(ROOT, MODEL_INPUTS);
  const probeHash = fileRevision(ROOT, PROBE_INPUTS);
  const probeRevision = NEUTRAL_REVISION || probeHash;
  const units = [];
  const derived = {};
  for (const row of matrix) {
    if (!row.menu_xmlid || !row.action_xmlid) continue;
    const behaviour = overlayFor(overlay, row.menu_xmlid);
    const declared = declaredEntryGroups(row);
    const pinned = behaviour.denied_role ? String(behaviour.denied_role) : null;
    const resolved = resolveNegativeCandidate(declared, order, states, pinned);
    const plan = {
      candidate: resolved.chosen,
      reason: resolved.reason,
      declared_groups: declared,
      pinned,
    };
    derived[row.menu_xmlid] = plan;
    units.push({
      id: row.menu_xmlid,
      fingerprint: entryFingerprint({
        row,
        behaviour,
        environment: identity,
        // What these assertions were measured against, bound per unit: the
        // declared surfaces when the build published their hashes, otherwise
        // the whole served artifact (fail-closed, recorded).
        surfaceInputs: surfaceInputs({
          bundleFingerprint: BUNDLE_FINGERPRINT,
          servedRevision: SERVED_REVISION,
          surfaces: surfaceScopes.entries[row.menu_xmlid] || [],
          surfaceScopes: surfaceScopes.hashes,
        }),
        derived: plan,
        // Bound per unit, so a change to one candidate's authoritative closure
        // re-opens exactly the entries bound to that candidate.
        permissionContext: permissionContext({
          candidate: resolved.chosen,
          state: resolved.chosen ? states.get(resolved.chosen) : null,
        }),
        modelRevision,
        probeRevision,
      }),
      required: true,
    });
  }
  return {
    schema: UNITS_SCHEMA,
    check: CHECK,
    identity,
    provenance: {
      ...provenance,
      reuse_identity_key: reuseIdentityKey({ bundleFingerprint: BUNDLE_FINGERPRINT }),
      surface_scopes_declared: Boolean(SURFACE_SCOPES_PATH),
      acting_company_id: acting.company_id,
      acting_login: acting.login,
      acting_role_closure_sha256: acting.role_closure_sha256,
      denied_role_candidates: order,
      observed_at: new Date().toISOString(),
    },
    tool_revision: {
      model: modelRevision,
      probe: probeHash,
      probe_used: probeRevision,
      probe_assertion_neutral: Boolean(NEUTRAL_REVISION) && NEUTRAL_REVISION !== probeHash,
    },
    derived,
    units,
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
const args = argsOf(process.argv.slice(2));
if (args['emit-units']) {
  const document = surface();
  writeJson(args['emit-units'], document);
  const ineligible = Object.entries(loadClosures().candidates)
    .filter(([, value]) => Number(value.nav_targets || 0) === 0)
    .map(([role]) => role);
  const undecidable = Object.entries(document.derived).filter(([, value]) => !value.candidate).map(([key]) => key);
  console.log(`[business-entry-scope] units=${document.units.length} ineligible_candidates=${ineligible.length} undecidable=${undecidable.length} reuse_identity_key=${document.provenance.reuse_identity_key}=${document.provenance[document.provenance.reuse_identity_key] || 'absent'}`);
  if (undecidable.length) {
    console.log(`[business-entry-scope] undecidable: ${undecidable.slice(0, 10).join(', ')}`);
  }
} else if (args['emit-results']) {
  const summaryPath = args.summary;
  const planPath = args.plan;
  if (!summaryPath || !planPath) throw new Error('--summary and --plan are required with --emit-results');
  const document = surface();
  const fingerprints = new Map(document.units.map((unit) => [unit.id, unit.fingerprint]));
  const summary = JSON.parse(fs.readFileSync(summaryPath, 'utf8'));
  const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
  // The observation must have been taken in the company the reuse identity
  // binds; otherwise the recorded status would claim coverage from another
  // permission context. Fail-closed on a missing or mismatched readback.
  const boundCompany = Number(document.identity[ACTING_COMPANY_KEY]);
  const observedCompany = Number(summary.session_company_id);
  if (!Number.isInteger(observedCompany) || observedCompany <= 0) {
    throw new Error(
      `${summaryPath}: the observation carries no acting-company readback (session_company_id), `
      + 'so it cannot be bound to the reuse identity',
    );
  }
  if (observedCompany !== boundCompany) {
    throw new Error(
      `${summaryPath}: the observation was taken in company ${observedCompany} but reuse is bound to `
      + `company ${boundCompany}`,
    );
  }
  validateObservationBinding(summary, plan, document);
  // Per-unit status is read from the probe's own per-entry record and nothing
  // else. The probe aggregates a surface verdict (summary.ok / summary.fatal)
  // for its process exit code; that aggregate must never rewrite a sibling's
  // outcome. Folding the surface verdict into every unit made one failing entry
  // stamp every correctly checked sibling as `checked=failed`, which poisons the
  // reuse ledger and forces a justified re-walk of entries that never regressed.
  const recorded = new Map();
  for (const entry of summary.entries || []) {
    if (entry && entry.entry) recorded.set(String(entry.entry), String(entry.status || 'checked'));
  }
  // An interrupted run declares `completeness:partial` and carries only the
  // entries it actually concluded. Those unreached units are not recorded — not
  // as a pass and not as a failure — so the next incremental pass still sees
  // them as never-recorded and resumes from them. A document that does not
  // declare partiality (an older probe, or a fatal exit with no observation at
  // all) keeps the fail-closed behaviour: a selected key with no per-entry
  // observation carries no proof whatsoever and stays non-reusable.
  const partial = String(summary.completeness || '') === 'partial';
  for (const key of (summary.selection && summary.selection.keys) || []) {
    if (recorded.has(String(key))) continue;
    if (partial) continue;
    recorded.set(String(key), 'failed');
  }
  const executed = [...recorded.keys()].filter((key) => fingerprints.has(key));
  const statuses = {};
  for (const key of executed) statuses[key] = recorded.get(key);
  // A partial observation did not finish the plan it was given. Narrow the
  // declared plan to the units this run actually reached so the recorder never
  // claims the unreached ones; they stay unrecorded and are picked up next pass.
  const plannedAll = (plan.affected || []).map(String);
  const plannedAffected = partial ? plannedAll.filter((key) => executed.includes(key)) : plannedAll;
  const results = {
    schema: RESULTS_SCHEMA,
    check: CHECK,
    planned_affected: plannedAffected,
    executed_units: executed.map((key) => ({ id: key, fingerprint: fingerprints.get(key) })),
    results: statuses,
    partial,
    surface_ok: summary.ok === true,
    surface_fatal: summary.fatal === true,
    source: summaryPath,
  };
  writeJson(args['emit-results'], results);
  console.log(`[business-entry-scope] executed=${executed.length} planned_affected=${results.planned_affected.length} ok=${summary.ok}`);
} else {
  throw new Error('one of --emit-units or --emit-results is required');
}

}

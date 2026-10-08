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
import {
  MODEL_INPUTS,
  PROBE_INPUTS,
  candidateStates,
  declaredEntryGroups,
  entryFingerprint,
  environmentIdentity,
  fileRevision,
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
const LOGIN = process.env.ACCEPTANCE_LOGIN || '';
const NEUTRAL_REVISION = (process.env.SC_ENTRY_MATRIX_PROBE_ASSERTION_NEUTRAL || '').trim();

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
  return document;
}

function surface() {
  if (!SERVED_REVISION) throw new Error('SC_ACCEPTANCE_TARGET_SHA is required to bind the environment identity');
  const matrix = loadMatrix(CSV_PATH);
  const overlay = loadOverlay(OVERLAY_PATH);
  const closures = loadClosures();
  const order = overlay.deniedRoleCandidates;
  const states = candidateStates(order, closures.candidates);
  const identity = environmentIdentity({
    baseUrl: BASE, database: DATABASE, login: LOGIN, candidateOrder: order,
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
        row, behaviour, environment: identity, derived: plan, modelRevision, probeRevision,
      }),
      required: true,
    });
  }
  return {
    schema: UNITS_SCHEMA,
    check: CHECK,
    identity,
    provenance: { served_revision: SERVED_REVISION, observed_at: new Date().toISOString() },
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

const args = argsOf(process.argv.slice(2));
if (args['emit-units']) {
  const document = surface();
  writeJson(args['emit-units'], document);
  const ineligible = Object.entries(loadClosures().candidates)
    .filter(([, value]) => Number(value.nav_targets || 0) === 0)
    .map(([role]) => role);
  const undecidable = Object.entries(document.derived).filter(([, value]) => !value.candidate).map(([key]) => key);
  console.log(`[business-entry-scope] units=${document.units.length} ineligible_candidates=${ineligible.length} undecidable=${undecidable.length}`);
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
  // A selected key that produced no per-entry observation carries no proof
  // whatsoever. That covers a probe that died before the entry loop (fatal) as
  // well as an interrupted run; either way the unit stays non-reusable instead
  // of being claimed as checked on the strength of the surface verdict alone.
  for (const key of (summary.selection && summary.selection.keys) || []) {
    if (!recorded.has(String(key))) recorded.set(String(key), 'failed');
  }
  const executed = [...recorded.keys()].filter((key) => fingerprints.has(key));
  const statuses = {};
  for (const key of executed) statuses[key] = recorded.get(key);
  const results = {
    schema: RESULTS_SCHEMA,
    check: CHECK,
    planned_affected: (plan.affected || []).map(String),
    executed_units: executed.map((key) => ({ id: key, fingerprint: fingerprints.get(key) })),
    results: statuses,
    surface_ok: summary.ok === true,
    surface_fatal: summary.fatal === true,
    source: summaryPath,
  };
  writeJson(args['emit-results'], results);
  console.log(`[business-entry-scope] executed=${executed.length} planned_affected=${results.planned_affected.length} ok=${summary.ok}`);
} else {
  throw new Error('one of --emit-units or --emit-results is required');
}

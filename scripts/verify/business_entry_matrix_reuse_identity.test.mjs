#!/usr/bin/env node
// Behavioural lock for the business-entry matrix reuse identity and per-unit
// declaration fingerprint.
//
// Two defects are covered here, both of them observed on the governed runtime.
//
// 1. Reuse identity. Browser evidence was once reused across a candidate the
//    target served from a different revision, because the identity bound only
//    the base url, database, acting login and candidate order; a pristine
//    108/108 reading survived a frontend rebuild that had changed every list
//    surface. Binding the deployed commit fixed that, but the commit changes on
//    every mainline merge, including merges that never rebuild the frontend, so
//    the incremental lane degenerated into a full re-walk of all 89 declared
//    entries on every deployment (observed three times in a row on an unchanged
//    governance runtime). The identity therefore binds the served frontend
//    artifact fingerprint the runtime publishes (`frontend_build_sha256`), which
//    changes exactly when the served bundle changed.
//
// 2. Declaration fingerprint. `acceptance_status` records an outcome, and it is
//    written when a batch is closed. Binding it into the fingerprint made the
//    closing commit re-open every row it had just closed.
//
// Every negative case is asserted from a working baseline first, so a broken
// harness cannot look like the expected stop.
import assert from 'node:assert/strict';

import { environmentIdentity, entryFingerprint, reuseIdentityKey } from './business_entry_matrix_model.mjs';

let cases = 0;
const check = (actual, expected, label) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

const BASE = 'http://example.invalid:18081';
const DATABASE = 'sc_demo';
const LOGIN = 'wutao';
const CANDIDATES = ['fixture_role_read'];
const BUNDLE_A = 'a'.repeat(64);
const BUNDLE_B = 'b'.repeat(64);

const row = { menu_xmlid: 'menu.a', action_xmlid: 'action.a', model: 'res.partner', rendering_path: 'list' };
const behaviour = { denied_role: null };
const derived = { candidate: 'fixture_role_read', reason: 'declared', declared_groups: [], pinned: null };
const fingerprint = (environment, overrides = {}) => entryFingerprint({
  row: { ...row, ...(overrides.row || {}) },
  behaviour,
  environment,
  derived,
  modelRevision: 'model',
  probeRevision: 'probe',
});

const identity = (servedRevision, bundleFingerprint) => environmentIdentity({
  baseUrl: BASE, database: DATABASE, login: LOGIN, candidateOrder: CANDIDATES,
  servedRevision, bundleFingerprint,
});

// 1. Baseline: a complete governed runtime identity binds, and the reuse input
//    is the served artifact fingerprint, not the deploying commit.
const baseline = identity('1'.repeat(40), BUNDLE_A);
check(reuseIdentityKey({ bundleFingerprint: BUNDLE_A }), 'frontend_build_sha256',
  'a declared artifact fingerprint is the reuse identity key');
check(baseline.frontend_build_sha256, BUNDLE_A, 'the identity carries the served artifact fingerprint');
check(baseline.served_revision, undefined, 'the deploying commit is not a reuse input');
check(baseline.base_url, BASE, 'the identity still carries the base url');
check(baseline.database, DATABASE, 'the identity still carries the database');
check(baseline.login, LOGIN, 'the identity still carries the acting login');
check(baseline.denied_role_candidates, CANDIDATES, 'the identity still carries the candidate order');
check(fingerprint(baseline), fingerprint(identity('1'.repeat(40), BUNDLE_A)),
  'an unchanged governed runtime keeps the unit fingerprint reusable');

// 2. Deterministic: unchanged inputs keep a unit reusable.
check(identity('1'.repeat(40), BUNDLE_A), baseline, 'an unchanged runtime identity is byte-identical');

// 3. The efficiency contract: the same served bundle on another deploying commit
//    keeps every unit reusable. This is the case the naive commit binding broke.
check(fingerprint(identity('2'.repeat(40), BUNDLE_A)), fingerprint(baseline),
  'a deployment that served the same bundle keeps the unit reusable');
check(identity('2'.repeat(40), BUNDLE_A), baseline,
  'a deployment that served the same bundle keeps the identity reusable');

// 4. The protection survives: another served bundle invalidates the unit, so a
//    frontend rebuild can never inherit the older observation.
assert.notEqual(fingerprint(identity('1'.repeat(40), BUNDLE_B)), fingerprint(baseline),
  'a unit measured on another served bundle must not stay reusable');
assert.notEqual(identity('1'.repeat(40), BUNDLE_B), baseline,
  'another served bundle must not keep the identity reusable');
cases += 2;

// 5. Fail-closed degradation: a runtime that publishes no artifact fingerprint
//    binds the deployed revision instead, so reuse never crosses bundles, and
//    the degraded key is visible to the caller.
check(reuseIdentityKey({ bundleFingerprint: '' }), 'served_revision',
  'an absent artifact fingerprint reports the degraded reuse key');
const degraded = identity('1'.repeat(40), '');
check(degraded.served_revision, '1'.repeat(40), 'the degraded identity binds the deployed revision');
check(degraded.frontend_build_sha256, undefined, 'the degraded identity declares no artifact fingerprint');
assert.notEqual(fingerprint(identity('2'.repeat(40), '')), fingerprint(degraded),
  'degraded reuse must still not cross deployments');
cases += 1;

// 6. A serving surface whose reason for exclusion is the outcome, not an input:
//    recording a batch outcome must not re-open the entry it recorded.
const reported = fingerprint(baseline);
check(fingerprint(baseline, { row: { acceptance_status: 'passed' } }), reported,
  'recording the acceptance outcome does not change the declaration fingerprint');
check(fingerprint(baseline, { row: { acceptance_status: 'pending' } }), reported,
  'clearing the acceptance outcome does not change the declaration fingerprint');
assert.notEqual(fingerprint(baseline, { row: { rendering_path: 'kanban' } }), reported,
  'a changed consumed declaration still re-opens the entry');
assert.notEqual(fingerprint(baseline, { row: { model: 'res.company' } }), reported,
  'a changed declared model still re-opens the entry');
cases += 2;

// 7. Fail-closed: with the baseline proven above, a missing deployment revision
//    is the removed input and not a broken harness.
const expectStop = (run, label) => {
  try {
    run();
  } catch (error) {
    assert.match(String(error.message || ''), /served revision is required/, `${label}: refusal message`);
    cases += 1;
    return;
  }
  throw new Error(`${label}: expected a refusal, got an identity`);
};

expectStop(() => identity('', BUNDLE_A), 'a blank served revision is refused');
expectStop(() => environmentIdentity({
  baseUrl: BASE, database: DATABASE, login: LOGIN, candidateOrder: [],
}), 'an absent served revision is refused');

console.log(`[business_entry_matrix_reuse_identity_test] PASS cases=${cases}`);

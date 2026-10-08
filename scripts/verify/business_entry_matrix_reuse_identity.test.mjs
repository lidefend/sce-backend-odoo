#!/usr/bin/env node
// Behavioural lock for the business-entry matrix reuse identity.
//
// Defect this covers: browser evidence was reused across a candidate the target
// served from a different revision, because the reuse identity bound only the
// base url, database, acting login and candidate order. A pristine 108/108
// reading therefore survived a frontend rebuild that had changed every list
// surface, and the regression it carried was reported as a scoped re-check
// rather than as invalidated evidence.
//
// The negative case is asserted from a working baseline first: the same helper
// binds a complete identity, and only then is the missing-revision refusal
// proven, so a broken harness cannot look like the expected stop.
import assert from 'node:assert/strict';

import { entryFingerprint, environmentIdentity } from './business_entry_matrix_model.mjs';

let cases = 0;
const check = (actual, expected, label) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

const row = { menu_xmlid: 'menu.a', action_xmlid: 'action.a', model: 'res.partner', rendering_path: 'list' };
const behaviour = { denied_role: null };
const derived = { candidate: 'fixture_role_read', reason: 'declared', declared_groups: [], pinned: null };

const baseline = environmentIdentity({
  baseUrl: 'http://example.invalid:18081',
  database: 'sc_demo',
  login: 'wutao',
  candidateOrder: ['fixture_role_read'],
  servedRevision: 'a'.repeat(40),
});

// 1. Baseline: a complete governed runtime identity binds, and it carries the
//    served revision as a first-class reuse input.
check(baseline.served_revision, 'a'.repeat(40), 'the identity carries the served revision');
check(baseline.base_url, 'http://example.invalid:18081', 'the identity still carries the base url');
check(baseline.database, 'sc_demo', 'the identity still carries the database');
check(baseline.login, 'wutao', 'the identity still carries the acting login');
check(baseline.denied_role_candidates, ['fixture_role_read'], 'the identity still carries the candidate order');

// 2. Deterministic: unchanged inputs keep a unit reusable.
const atSameRevision = environmentIdentity({
  baseUrl: 'http://example.invalid:18081',
  database: 'sc_demo',
  login: 'wutao',
  candidateOrder: ['fixture_role_read'],
  servedRevision: 'a'.repeat(40),
});
check(atSameRevision, baseline, 'an unchanged runtime identity is byte-identical');

const fingerprint = (environment) => entryFingerprint({
  row, behaviour, environment, derived, modelRevision: 'model', probeRevision: 'probe',
});
check(
  fingerprint(atSameRevision),
  fingerprint(baseline),
  'an unchanged runtime identity keeps the unit fingerprint reusable',
);

// 3. A different served revision invalidates the unit: the observation was made
//    against another bundle, so it cannot be reused.
const otherRevision = environmentIdentity({
  baseUrl: 'http://example.invalid:18081',
  database: 'sc_demo',
  login: 'wutao',
  candidateOrder: ['fixture_role_read'],
  servedRevision: 'b'.repeat(40),
});
assert.notEqual(
  fingerprint(otherRevision),
  fingerprint(baseline),
  'a unit measured on another served revision must not stay reusable',
);
cases += 1;

// 4. Fail-closed: with the baseline proven above, a missing revision is the
//    removed input and not a broken harness.
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

expectStop(
  () => environmentIdentity({
    baseUrl: 'http://example.invalid:18081', database: 'sc_demo', login: 'wutao', candidateOrder: [], servedRevision: '',
  }),
  'a blank served revision is refused',
);
expectStop(
  () => environmentIdentity({
    baseUrl: 'http://example.invalid:18081', database: 'sc_demo', login: 'wutao', candidateOrder: [],
  }),
  'an absent served revision is refused',
);

console.log(`[business_entry_matrix_reuse_identity_test] PASS cases=${cases}`);

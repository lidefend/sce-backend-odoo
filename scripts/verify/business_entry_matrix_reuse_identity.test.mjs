#!/usr/bin/env node
// Behavioural lock for the business-entry matrix reuse identity.
//
// Three defects are covered here, all of them observed on the governed runtime.
//
// 1. Reuse identity. Browser evidence was once reused across a candidate the
//    target served from a different revision, because the identity bound only
//    the base url, database, acting login and candidate order; a pristine
//    108/108 reading survived a frontend rebuild that had changed every list
//    surface. Binding the deployed commit fixed that, but the commit changes on
//    every mainline merge, including merges that never rebuild the frontend, so
//    the incremental lane degenerated into a full re-walk of all 89 declared
//    entries on every deployment. The deploying commit is therefore *provenance*
//    only, and the validity basis is the served surface.
//
// 2. Acting-principal permission context. The company the evidence was taken in
//    was an authoritative readback, but the acting account's own role closure
//    was not: a role change on the same login in the same company changes the
//    record set it reaches, so it must invalidate reuse too.
//
// 3. Per-unit surface dependency. Folding the whole served artifact into a
//    shared identity re-opened every entry on any frontend change. The served
//    surface binds per unit, narrowed by the entry's declared surfaces when the
//    build publishes their hashes.
//
// 4. Declaration fingerprint. `acceptance_status` records an outcome, and it is
//    written when a batch is closed. Binding it into the fingerprint made the
//    closing commit re-open every row it had just closed.
//
// Every negative case is asserted from a working baseline first, so a broken
// harness cannot look like the expected stop.
import assert from 'node:assert/strict';

import {
  matrixLoginUrl,
  ACTING_CLOSURE_KEY,
  SURFACE_SCOPE_DECLARED,
  SURFACE_SCOPE_WHOLE,
  actingContext,
  deploymentProvenance,
  environmentIdentity,
  entryFingerprint,
  permissionContext,
  reuseIdentityKey,
  surfaceInputs,
} from './business_entry_matrix_model.mjs';

let cases = 0;
const check = (actual, expected, label) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

const BASE = 'http://example.invalid:18081';
const DATABASE = 'sc_demo';
const LOGIN = 'wutao';
const COMPANY = 1;
const CANDIDATES = ['fixture_role_read'];
const BUNDLE_A = 'a'.repeat(64);
const BUNDLE_B = 'b'.repeat(64);
const SURFACE_A = 'c'.repeat(64);
const SURFACE_B = 'd'.repeat(64);
const SURFACE_A_MOVED = 'e'.repeat(64);
const REVISION_1 = '1'.repeat(40);
const REVISION_2 = '2'.repeat(40);

// The acting principal's authoritative role-closure readback.
const ACTING_CLOSURE = actingContext(
  { acting: { login: LOGIN, company_id: COMPANY, role_xmlids: ['base.group_user', 'base.group_partner_manager'] } },
  { login: LOGIN },
).role_closure_sha256;
const OTHER_CLOSURE = actingContext(
  { acting: { login: LOGIN, company_id: COMPANY, role_xmlids: ['base.group_user'] } },
  { login: LOGIN },
).role_closure_sha256;

const row = { menu_xmlid: 'menu.a', action_xmlid: 'action.a', model: 'res.partner', rendering_path: 'list' };
const behaviour = { denied_role: null };
const derived = { candidate: 'fixture_role_read', reason: 'declared', declared_groups: [], pinned: null };
const readState = { role: 'fixture_role_read', eligible: true, missing: false, roleXmlids: ['base.group_user'], releasedTargets: 12, company: COMPANY };
const readContext = permissionContext({ candidate: 'fixture_role_read', state: readState });
const wholeArtifact = surfaceInputs({ bundleFingerprint: BUNDLE_A });
const fingerprint = (environment, overrides = {}) => entryFingerprint({
  row: { ...row, ...(overrides.row || {}) },
  behaviour: overrides.behaviour === undefined ? behaviour : overrides.behaviour,
  environment,
  surfaceInputs: overrides.surfaceInputs === undefined ? wholeArtifact : overrides.surfaceInputs,
  derived: overrides.derived === undefined ? derived : overrides.derived,
  permissionContext: overrides.permissionContext === undefined ? readContext : overrides.permissionContext,
  modelRevision: 'model',
  probeRevision: 'probe',
});

const identity = (company = COMPANY, closure = ACTING_CLOSURE) => environmentIdentity({
  baseUrl: BASE, database: DATABASE, login: LOGIN, actingCompanyId: company,
  actingRoleClosureSha256: closure,
});

// 1. Baseline: the shared identity is the runtime + the acting principal's own
//    permission context, and the deploying commit is not a validity input.
const baseline = identity();
check(reuseIdentityKey({ bundleFingerprint: BUNDLE_A }), 'frontend_build_sha256',
  'a declared artifact fingerprint is the reuse identity key');
check(baseline.base_url, BASE, 'the identity carries the base url');
check(baseline.database, DATABASE, 'the identity carries the database');
check(baseline.login, LOGIN, 'the identity carries the acting login');
check(baseline.acting_company_id, COMPANY,
  'the identity binds the authoritative acting-company readback');
check(baseline[ACTING_CLOSURE_KEY], ACTING_CLOSURE,
  "the identity binds the acting principal's own role closure");
check(baseline.served_revision, undefined, 'the deploying commit is not a shared identity input');
check(baseline.frontend_build_sha256, undefined, 'the served artifact is not a shared identity input');
check(baseline.denied_role_candidates, undefined,
  'the candidate order is not a shared identity input: it is bound per unit through the resolved candidate');
check(fingerprint(baseline), fingerprint(identity()), 'an unchanged governed runtime keeps the unit fingerprint reusable');

// 2. Deterministic: unchanged inputs keep a unit reusable.
check(identity(), baseline, 'an unchanged runtime identity is byte-identical');

// 3. Provenance. The deploying commit is recorded so an observation is
//    traceable to a deployment, but it must never invalidate reuse.
const provenance = deploymentProvenance({ servedRevision: REVISION_1, bundleFingerprint: BUNDLE_A });
check(provenance.served_revision, REVISION_1, 'the provenance records the serving deployment');
check(provenance.frontend_build_sha256, BUNDLE_A, 'the provenance records the served artifact');
check(deploymentProvenance({ servedRevision: REVISION_2, bundleFingerprint: BUNDLE_B }).served_revision, REVISION_2,
  'the provenance follows the serving deployment');
check(fingerprint(baseline), fingerprint(baseline),
  'the deploying commit is not part of the unit fingerprint');

// 4. The efficiency contract: another deploying commit keeps every unit
//    reusable, because the artifact the assertions were measured on is unchanged.
check(fingerprint(baseline), fingerprint(identity()),
  'a deployment that served the same bundle keeps the unit reusable');

// 5. The protection survives: another served artifact re-opens the unit.
assert.notEqual(
  fingerprint(baseline, { surfaceInputs: surfaceInputs({ bundleFingerprint: BUNDLE_B }) }),
  fingerprint(baseline),
  'a unit measured on another served artifact must not stay reusable',
);
cases += 1;

// 6. Acting-principal role closure. The same login in the same company with a
//    changed role closure reaches another record set, so it must re-open.
assert.notEqual(identity(COMPANY, OTHER_CLOSURE), baseline,
  "another acting closure must not keep the identity reusable");
assert.notEqual(fingerprint(identity(COMPANY, OTHER_CLOSURE)), fingerprint(baseline),
  "another acting closure must not keep a unit reusable");
cases += 2;

// 7. Company context. The same login in another company sees another record set.
assert.notEqual(identity(2), baseline, 'another acting company must not keep the identity reusable');
assert.notEqual(fingerprint(identity(2)), fingerprint(baseline),
  'another acting company must not keep a unit reusable');
cases += 2;

// 8. Per-unit surface dependency. Two entries that declare disjoint surfaces
//    must invalidate independently: moving one surface re-opens exactly the
//    entry that renders it.
const scopes = { 'surface.a': SURFACE_A, 'surface.b': SURFACE_B };
const movedScopes = { 'surface.a': SURFACE_A_MOVED, 'surface.b': SURFACE_B };
const declared = (surface, map) => surfaceInputs({ surfaces: [surface], surfaceScopes: map });
check(declared('surface.a', scopes).scope, SURFACE_SCOPE_DECLARED,
  'a fully hashed declared surface narrows the binding');
check(declared('surface.a', scopes).sha256, declared('surface.a', { ...scopes }).sha256,
  'an unchanged declared surface keeps its binding byte-identical');
const unitA = fingerprint(baseline, { surfaceInputs: declared('surface.a', scopes) });
const unitB = fingerprint(baseline, { surfaceInputs: declared('surface.b', scopes) });
assert.notEqual(unitA, unitB, 'two entries bound to different surfaces are distinct units');
assert.notEqual(fingerprint(baseline, { surfaceInputs: declared('surface.a', movedScopes) }), unitA,
  'a moved surface re-opens the entry that declares it');
check(fingerprint(baseline, { surfaceInputs: declared('surface.b', movedScopes) }), unitB,
  'the sibling entry that does not declare the moved surface stays byte-identical');
cases += 4;

// 9. Fail-closed degradation. A partially covered or absent declaration binds
//    the whole served artifact, and a missing artifact stops reuse planning.
check(surfaceInputs({ bundleFingerprint: BUNDLE_A, surfaces: ['surface.a'], surfaceScopes: {} }).scope,
  SURFACE_SCOPE_WHOLE,
  'an uncovered declared surface degrades to the whole artifact');
check(surfaceInputs({ bundleFingerprint: BUNDLE_A, surfaces: [], surfaceScopes: scopes }).scope,
  SURFACE_SCOPE_WHOLE,
  'an entry that declares no surface binds the whole artifact');
const expectStop = (run, pattern, label) => {
  try {
    run();
  } catch (error) {
    assert.match(String(error.message || ''), pattern, `${label}: refusal message`);
    cases += 1;
    return;
  }
  throw new Error(`${label}: expected a refusal`);
};
expectStop(() => surfaceInputs({}), /cannot be bound to the surface/,
  'no declared surface and no artifact fingerprint is refused');
expectStop(() => deploymentProvenance({ servedRevision: '' }), /served revision is required/,
  'a blank serving deployment is refused');

// 10. Per-unit permission dependency. Each entry is bound to the denied-role
//     candidate the declaration resolved for *that* entry. Moving one candidate's
//     capability closure must re-open exactly the entries bound to it, and must
//     not invalidate an entry bound to another candidate; and a closure that
//     moved must never leave its own entry wrongly reusable.
const stateA = { role: 'fixture_role_read', eligible: true, missing: false, roleXmlids: ['base.group_user'], releasedTargets: 12, company: COMPANY };
const stateB = { role: 'fixture_role_write', eligible: true, missing: false, roleXmlids: ['base.group_system'], releasedTargets: 40, company: COMPANY };
const contextA = permissionContext({ candidate: 'fixture_role_read', state: stateA });
const contextB = permissionContext({ candidate: 'fixture_role_write', state: stateB });
const movedA = permissionContext({ candidate: 'fixture_role_read', state: { ...stateA, roleXmlids: ['base.group_user', 'base.group_erp_manager'] } });
const releasedA = permissionContext({ candidate: 'fixture_role_read', state: { ...stateA, releasedTargets: 9 } });
const movedCompanyA = permissionContext({ candidate: 'fixture_role_read', state: { ...stateA, company: 2 } });

const unitPermA = fingerprint(baseline, { permissionContext: contextA });
const unitPermB = fingerprint(baseline, { permissionContext: contextB });
check(unitPermA === fingerprint(baseline, { permissionContext: contextA }), true,
  'an unchanged candidate closure keeps its own entry reusable');
assert.notEqual(unitPermA, unitPermB, 'two entries bound to different candidates are distinct units');
assert.notEqual(fingerprint(baseline, { permissionContext: movedA }), unitPermA,
  'a moved capability closure re-opens the entry bound to that candidate');
assert.notEqual(fingerprint(baseline, { permissionContext: releasedA }), unitPermA,
  'a changed released navigation count re-opens the entry bound to that candidate');
assert.notEqual(fingerprint(baseline, { permissionContext: movedCompanyA }), unitPermA,
  'a candidate observed in another company re-opens the entry bound to it');
check(fingerprint(baseline, { permissionContext: contextB }), unitPermB,
  'the sibling entry bound to the other candidate stays byte-identical when one candidate moves');
cases += 6;

// 11. The authoritative acting-principal readback. The closure snapshot must
//     observe the same login reuse is bound to and must carry a company and a
//     role closure; anything else refuses rather than binding silently.
const closures = {
  acting: { login: LOGIN, company_id: COMPANY, role_xmlids: ['base.group_user'] },
  candidates: { [CANDIDATES[0]]: {} },
};
check(actingContext(closures, { login: LOGIN }).company_id, COMPANY,
  'the acting company is read from the authoritative snapshot');
check(actingContext(closures, { login: LOGIN }).role_closure_sha256,
  actingContext({ acting: { login: LOGIN, company_id: COMPANY, role_xmlids: ['base.group_user'] } }, { login: LOGIN }).role_closure_sha256,
  'the acting closure is read from the authoritative snapshot');
expectStop(() => actingContext({}, { login: LOGIN }), /refresh the snapshot/,
  'a snapshot with no acting readback is refused');
expectStop(() => actingContext({ acting: { login: 'other', company_id: 1, role_xmlids: ['g'] } }, { login: LOGIN }),
  /observed login other/, 'a snapshot observing another login is refused');
expectStop(() => actingContext({ acting: { login: LOGIN, company_id: 0, role_xmlids: ['g'] } }, { login: LOGIN }),
  /acting-company readback/, 'a snapshot with no company is refused');
expectStop(() => actingContext({ acting: { login: LOGIN, company_id: COMPANY } }, { login: LOGIN }),
  /acting-principal role closure/, 'a snapshot with no acting closure is refused');
expectStop(() => permissionContext({ candidate: 'fixture_role_absent', state: { missing: true, eligible: false } }),
  /no authoritative closure readback/, 'a candidate with no closure readback is refused');
check(permissionContext({ candidate: null, state: null }).denied_candidate, null,
  'an entry with no denial candidate binds no permission fact');
cases += 1;

// 12. Fail-closed environment identity: the acting company and the acting role
//     closure are required inputs and a non-hash closure is refused.
expectStop(() => identity(0), /acting-company readback/, 'a non-positive acting company is refused');
expectStop(() => identity(1.5), /acting-company readback/, 'a non-integer acting company is refused');
expectStop(() => identity(COMPANY, ''), /role closure/, 'an absent acting closure is refused');
expectStop(() => identity(COMPANY, 'not-a-hash'), /role closure/, 'a non-hash acting closure is refused');

// 13. A serving surface whose reason for exclusion is the outcome, not an input:
//     recording a batch outcome must not re-open the entry it recorded.
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

console.log(`[business_entry_matrix_reuse_identity_test] PASS cases=${cases}`);

// Import must prove original execution identity and per-unit input, not relabel
// an old outcome with the current unit fingerprint.
const { observationBinding, validateObservationBinding, validateClosureEnvironment } = await import('./business_entry_matrix_model.mjs');
const importDocument = { identity: baseline, units: [{ id: 'menu.a', fingerprint: 'a'.repeat(64) }, { id: 'menu.b', fingerprint: 'b'.repeat(64) }] };
const binding = observationBinding(importDocument);
const importPlan = { execute: ['menu.a', 'menu.b'], observation_binding: binding };
const observation = { base_url: BASE, database: DATABASE, login: LOGIN, session_company_id: COMPANY,
  acting: { login: LOGIN, company_id: COMPANY, role_xmlids: ['base.group_user', 'base.group_partner_manager'] },
  selection: { keys: ['menu.a', 'menu.b'] }, entries: [{ entry: 'menu.a', status: 'passed' }],
  completeness: 'partial', observation_binding: binding };
let importCases = 0;
function rejectsImport(value, plan = importPlan, current = importDocument) {
  assert.throws(() => validateObservationBinding(value, plan, current)); importCases += 1;
}
validateObservationBinding(observation, importPlan, importDocument); importCases += 1;
for (const patch of [{ login: 'other' }, { database: 'other' }, { base_url: 'http://other.invalid' },
  { acting: { ...observation.acting, role_xmlids: ['base.group_user'] } },
  { acting: { ...observation.acting, login: 'other' }, login: 'other' },
  { observation_binding: undefined }, { acting: undefined }]) rejectsImport({ ...observation, ...patch });
rejectsImport(observation, { execute: ['menu.a'] });
rejectsImport(observation, importPlan, { ...importDocument, units: [{ id: 'menu.a', fingerprint: 'c'.repeat(64) }] });
rejectsImport({ ...observation, entries: [{ entry: 'menu.c', status: 'passed' }] });
// Unexecuted sibling changes do not invalidate the actual partial outcome.
validateObservationBinding(observation, importPlan, { ...importDocument, units: [importDocument.units[0], { id: 'menu.b', fingerprint: 'c'.repeat(64) }] }); importCases += 1;
validateObservationBinding({ ...observation, target_sha: 'new-deploy', frontend_build_sha256: 'new-bundle' }, importPlan, importDocument); importCases += 1;
for (const patch of [{ database: 'other' }, { base_url: 'http://other.invalid' }, { database: undefined }]) {
  assert.throws(() => validateClosureEnvironment({ base_url: BASE, database: DATABASE, ...patch }, { baseUrl: BASE, database: DATABASE })); importCases += 1;
}
console.log(`[business-entry-observation-binding] PASS ${importCases} cases`);

check(matrixLoginUrl('http://example.invalid:18081/t/demo/'), 'http://example.invalid:18081/t/demo/login', 'namespace retained without database query');
check(matrixLoginUrl('http://example.invalid:18081'), 'http://example.invalid:18081/login', 'isolated root entry supported');
for (const base of ['http://example.invalid/t/demo?db=sc_demo', 'http://user:secret@example.invalid', 'http://example.invalid/#x', 'file:///tmp/demo']) {
  assert.throws(() => matrixLoginUrl(base), /base URL/);
}
console.log('matrix namespace cases: 6 passed');

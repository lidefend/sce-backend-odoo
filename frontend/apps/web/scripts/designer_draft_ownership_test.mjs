// Behavioural counter-examples for the designer draft protection boundary.
//
// These are the facts the runner must honour, expressed as observable decisions rather
// than as string checks on the implementation: which draft is considered authored by
// this run, which pre-existing draft may be written, which operations an authorization
// releases, and what happens when the run exits abnormally.
import assert from 'node:assert/strict';
import {
  isDraftOperationAllowed,
  parseDraftAuthorization,
  resolveChangeSetOpenResponse,
  resolveCleanupRelease,
  resolveDesignerDraftOwnership,
  resolveDesignerDraftPolicy,
  resolvePreexistingDraftProbe,
  resolvePreWriteDraftGate,
  resolveResumedDraftDecision,
} from './designer_draft_ownership.mjs';

let cases = 0;

// 1. `open` answers with the serialized draft when it resumes or creates one and with
//    `{change_set: null}` only on a read-only miss. Reading only `change_set` turned a
//    found draft into "no draft", so every recognised shape must be read correctly and
//    anything else must be an error rather than an empty result.
{
  const serialized = resolveChangeSetOpenResponse({ body: { ok: true, data: { id: 163, token: 't', state: 'draft' } } });
  assert.equal(serialized.error, null);
  assert.equal(serialized.shape, 'serialized_change_set');
  assert.equal(serialized.draft.id, 163);
  const nested = resolveChangeSetOpenResponse({ body: { ok: true, data: { change_set: { id: 192, token: 't' } } } });
  assert.equal(nested.error, null);
  assert.equal(nested.draft.id, 192);
  const miss = resolveChangeSetOpenResponse({ body: { ok: true, data: { change_set: null, created: false } } });
  assert.equal(miss.error, null);
  assert.equal(miss.draft, null);
  assert.equal(miss.shape, 'resume_only_miss');
  for (const body of [{ ok: true, data: {} }, { ok: true, data: { created: true } }, { ok: true }, {}]) {
    const unknown = resolveChangeSetOpenResponse({ body, intent: 'open:save' });
    assert.equal(unknown.draft, null);
    assert.equal(unknown.error, 'unrecognised_change_set_open_shape:open:save', JSON.stringify(body));
  }
  cases++;
}

// 2. Ownership needs the product's own creation credential. A draft the run merely
//    resumed is never released, and being absent from the inventory is not the proof.
{
  const resumed = resolveDesignerDraftOwnership({ changeSetId: 163, inventoryIds: [], created: false, freshRequested: false });
  assert.equal(resumed.release, false);
  assert.equal(resumed.reason, 'creation_not_proven_by_this_run');
  const freshButResumed = resolveDesignerDraftOwnership({ changeSetId: 163, inventoryIds: [], created: false, freshRequested: true });
  assert.equal(freshButResumed.release, false);
  assert.equal(freshButResumed.reason, 'creation_not_proven_by_this_run');
  const createdButNotFresh = resolveDesignerDraftOwnership({ changeSetId: 163, inventoryIds: [], created: true, freshRequested: false });
  assert.equal(createdButNotFresh.release, false);
  assert.equal(createdButNotFresh.reason, 'creation_not_proven_by_this_run');
  const contradictory = resolveDesignerDraftOwnership({ changeSetId: 163, inventoryIds: [163], created: true, freshRequested: true });
  assert.equal(contradictory.release, false);
  assert.equal(contradictory.reason, 'preexisting_designer_draft_not_authored_by_run');
  const authored = resolveDesignerDraftOwnership({ changeSetId: 231, inventoryIds: [163], created: true, freshRequested: true });
  assert.equal(authored.release, true);
  assert.equal(authored.reason, 'created_by_this_run');
  const unidentified = resolveDesignerDraftOwnership({ changeSetId: null, inventoryIds: [], created: true, freshRequested: true });
  assert.equal(unidentified.release, false);
  assert.equal(unidentified.reason, 'unidentified_change_set');
  cases++;
}

// 3. The save stages into whatever draft the product already holds, so the operation
//    must be authorized before the click. A draft authorized only for `discard` must be
//    refused with no write at all.
{
  const onlyDiscard = resolveDesignerDraftPolicy({ inventory: [{ id: 163 }], authorization: '163:discard' });
  assert.equal(onlyDiscard.decision, 'proceed');
  const blocked = resolvePreWriteDraftGate({ probedIds: [163], policy: onlyDiscard });
  assert.equal(blocked.decision, 'fail_closed');
  assert.equal(blocked.reason, 'probed_designer_draft_stage_not_authorized:163');
  assert.deepEqual(blocked.ids, [163]);

  const stageOnly = resolveDesignerDraftPolicy({ inventory: [{ id: 163 }], authorization: '163:stage' });
  const allowed = resolvePreWriteDraftGate({ probedIds: [163], policy: stageOnly });
  assert.equal(allowed.decision, 'proceed');
  assert.deepEqual(allowed.ids, [163]);
  const nothingProbed = resolvePreWriteDraftGate({ probedIds: [], policy: resolveDesignerDraftPolicy({ inventory: [], authorization: '' }) });
  assert.equal(nothingProbed.decision, 'proceed');
  cases++;
}

// 4. A resumed draft must have been seen by the probe before the save, and every
//    operation the journey performs on it must be authorized.
{
  const full = resolveDesignerDraftPolicy({ inventory: [{ id: 163 }], authorization: '163:stage,preview,publish,rollback' });
  const unprobed = resolveResumedDraftDecision({ changeSetId: 195, probedIds: [163], policy: full });
  assert.equal(unprobed.decision, 'fail_closed');
  assert.equal(unprobed.reason, 'resumed_designer_draft_not_probed:195');
  const partial = resolveDesignerDraftPolicy({ inventory: [{ id: 163 }], authorization: '163:stage' });
  const missingOp = resolveResumedDraftDecision({ changeSetId: 163, probedIds: [163], policy: partial });
  assert.equal(missingOp.decision, 'fail_closed');
  assert.equal(missingOp.reason, 'resumed_designer_draft_preview_not_authorized:163');
  const ok = resolveResumedDraftDecision({ changeSetId: 163, probedIds: [163], policy: full });
  assert.equal(ok.decision, 'proceed');
  cases++;
}

// 5. The withdrawn global switch must not be resurrectable: a bare truthy token names no
//    draft and no operation, so it is a refusal rather than "allow every resumed draft".
for (const raw of ['1', 'true', 'yes', '163', '163:', 'abc:stage', '163:frobnicate', '163:stage,', ' :stage']) {
  const parsed = parseDraftAuthorization(raw);
  assert(parsed.error, `authorization ${JSON.stringify(raw)} must be refused, not interpreted`);
  assert.equal(parsed.entries.size, 0);
}
assert.equal(parseDraftAuthorization('').error, null);
assert.equal(parseDraftAuthorization(undefined).error, null);
{
  const { entries, error } = parseDraftAuthorization('163:stage,publish; 192:discard');
  assert.equal(error, null);
  assert.deepEqual([...entries.get(163)].sort(), ['publish', 'stage']);
  assert.deepEqual([...entries.get(192)], ['discard']);
  cases++;
}

// 6. A run writes configuration only when every draft the product could resume is either
//    authorized by id or absent. Unknown ownership is a refusal, never an assumption.
{
  const missing = resolveDesignerDraftPolicy({ inventory: undefined, authorization: '' });
  assert.equal(missing.decision, 'fail_closed');
  assert.equal(missing.reason, 'designer_draft_inventory_missing');

  const unauthorized = resolveDesignerDraftPolicy({ inventory: [{ id: 163 }, { id: 192 }], authorization: '' });
  assert.equal(unauthorized.decision, 'fail_closed');
  assert.equal(unauthorized.reason, 'preexisting_designer_draft:163,192');
  assert.deepEqual(unauthorized.blocking, [163, 192]);

  const authorized = resolveDesignerDraftPolicy({ inventory: [{ id: 163 }, { id: 192 }], authorization: '163:stage,publish;192:discard' });
  assert.equal(authorized.decision, 'proceed');
  assert.deepEqual(authorized.inventoryIds, [163, 192]);
  assert.deepEqual(authorized.allowed, { 163: ['stage', 'publish'], 192: ['discard'] });
  assert.equal(isDraftOperationAllowed({ policy: authorized, changeSetId: 163, operation: 'stage' }), true);
  assert.equal(isDraftOperationAllowed({ policy: authorized, changeSetId: 163, operation: 'rollback' }), false);
  assert.equal(isDraftOperationAllowed({ policy: authorized, changeSetId: 192, operation: 'stage' }), false);
  assert.equal(isDraftOperationAllowed({ policy: authorized, changeSetId: 999, operation: 'stage' }), false);

  // Authorizing an id that is not actually present would hide a stale operator intent.
  const phantom = resolveDesignerDraftPolicy({ inventory: [{ id: 163 }], authorization: '163:stage;192:discard' });
  assert.equal(phantom.decision, 'fail_closed');
  assert.equal(phantom.reason, 'authorized_draft_not_in_inventory:192');

  // One authorized draft does not open the door for the others.
  const partial = resolveDesignerDraftPolicy({ inventory: [{ id: 163 }, { id: 192 }], authorization: '163:stage' });
  assert.equal(partial.decision, 'fail_closed');
  assert.equal(partial.reason, 'preexisting_designer_draft:192');
  cases++;
}

// 7. A draft that appears between the inventory and the first write is somebody else's:
//    the read-only probe must refuse before the run stages anything.
{
  const appeared = resolvePreexistingDraftProbe({ existingIds: [163, 195], inventoryIds: [163] });
  assert.equal(appeared.decision, 'fail_closed');
  assert.equal(appeared.reason, 'preexisting_designer_draft_appeared:195');
  assert.deepEqual(appeared.ids, [195]);
  const stable = resolvePreexistingDraftProbe({ existingIds: [163], inventoryIds: [163] });
  assert.equal(stable.decision, 'proceed');
  const none = resolvePreexistingDraftProbe({ existingIds: [], inventoryIds: [] });
  assert.equal(none.decision, 'proceed');
  cases++;
}

// 8. Abnormal exit: cleanup releases only ids this run authored. If a foreign id reached
//    the cleanup set, the guard refuses and releases nothing, so the exit path cannot
//    delete a draft the run did not create.
{
  const own = resolveCleanupRelease({ heldIds: [190, 191], inventoryIds: [] });
  assert.equal(own.decision, 'proceed');
  assert.deepEqual(own.release, [190, 191]);
  assert.deepEqual(own.foreign, []);

  const mixed = resolveCleanupRelease({ heldIds: [190, 163], inventoryIds: [163] });
  assert.equal(mixed.decision, 'fail_closed');
  assert.equal(mixed.reason, 'foreign_draft_in_cleanup_set:163');
  assert.deepEqual(mixed.release, []);
  assert.deepEqual(mixed.foreign, [163]);

  const empty = resolveCleanupRelease({ heldIds: [], inventoryIds: [163] });
  assert.equal(empty.decision, 'proceed');
  assert.deepEqual(empty.release, []);
  cases++;
}

// 9. Runner import contract: a named import that this module does not export is *not* a
//    syntax error, so `node --check` passes and the defect only appears at runtime as a
//    browser run that dies after login. Assert the exports the runners depend on instead.
{
  const fs = await import('node:fs/promises');
  const namespace = await import('./designer_draft_ownership.mjs');
  for (const file of ['formal_form_lowcode_loop.mjs', 'formal_form_designer_journey.mjs']) {
    const source = await fs.readFile(new URL(`./${file}`, import.meta.url), 'utf8');
    const clause = source.match(/import\s*\{([^}]*)\}\s*from\s*'\.\/designer_draft_ownership\.mjs'/);
    assert(clause, `${file} no longer imports this module`);
    const names = clause[1].split(',').map((entry) => entry.trim()).filter(Boolean);
    assert(names.length > 0, `${file} imports nothing from this module`);
    for (const name of names) assert.equal(typeof namespace[name], 'function', `${file} imports missing export ${name}`);
  }
  cases++;
}

console.log(`[designer_draft_ownership] PASS cases=${cases}`);

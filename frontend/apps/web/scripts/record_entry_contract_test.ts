import assert from 'node:assert/strict';
import {
  adaptLegacyRecordEntry,
  decodeFormalRecordEntry,
  normalizeModelWriteAuthority,
  normalizeRecordOpenIntent,
  recordEntryFromModelRights,
  resolveRecordOpenTarget,
} from '../src/app/runtime/recordEntryContract';
import { buildEntryTargetRouteTarget } from '../src/app/routeQuery';
import { buildActionViewRowClickTarget } from '../src/app/runtime/actionViewInteractionRuntime';

function resolvedPath(entry: Parameters<typeof resolveRecordOpenTarget>[0]) {
  return resolveRecordOpenTarget(entry)?.path;
}

// The complete authority matrix lives here once.  Adapters only translate
// their carrier into RecordEntryContract and must not duplicate these rules.
assert.equal(resolvedPath({ model: 'x.model', recordId: 7, entryIntent: 'open', modelWriteAuthority: true }), '/f/x.model/7');
assert.equal(resolvedPath({ model: 'x.model', recordId: 7, entryIntent: 'handling', modelWriteAuthority: true }), '/f/x.model/7');
assert.equal(resolvedPath({ model: 'x.model', recordId: 7, entryIntent: 'explicit_edit', modelWriteAuthority: true }), '/f/x.model/7');
assert.equal(resolvedPath({ model: 'x.model', recordId: 7, entryIntent: 'explicit_readonly', modelWriteAuthority: true }), '/r/x.model/7');
for (const intent of ['open', 'handling', 'explicit_edit'] as const) {
  assert.equal(resolvedPath({ model: 'x.model', recordId: 7, entryIntent: intent, modelWriteAuthority: false }), '/r/x.model/7');
  assert.equal(resolvedPath({ model: 'x.model', recordId: 7, entryIntent: intent, modelWriteAuthority: null }), '/r/x.model/7');
}

assert.equal(normalizeModelWriteAuthority(true), true);
assert.equal(normalizeModelWriteAuthority(false), false);
assert.equal(normalizeModelWriteAuthority('true'), null);
assert.equal(normalizeModelWriteAuthority('edit'), null);
assert.equal(normalizeRecordOpenIntent('handling'), 'handling');
assert.equal(normalizeRecordOpenIntent('process'), null);

const formalHandling = decodeFormalRecordEntry({
  model: 'x.model', record_id: 7, entry_intent: 'handling', model_write_authority: true, action_id: 4, menu_id: 3,
});
assert.deepEqual(formalHandling, {
  model: 'x.model', recordId: 7, entryIntent: 'handling', modelWriteAuthority: true, actionId: 4, menuId: 3,
});
assert.equal(resolvedPath(formalHandling!), '/f/x.model/7');
assert.equal(
  resolvedPath(decodeFormalRecordEntry({ model: 'x.model', record_id: 7, entry_intent: 'handling', model_write_authority: 'true' })!),
  '/r/x.model/7',
);
assert.equal(
  resolvedPath(decodeFormalRecordEntry({ model: 'x.model', record_id: 7, entry_intent: 'process', model_write_authority: true })!),
  '/r/x.model/7',
);

assert.equal(
  resolvedPath(adaptLegacyRecordEntry({ model: 'x.model', record_id: 7, entry_intent: 'process', model_write_authority: true })!),
  '/f/x.model/7',
);
assert.equal(
  resolvedPath(adaptLegacyRecordEntry({ model: 'x.model', record_id: 7 }, { legacyRoute: '/r/x.model/7' })!),
  '/r/x.model/7',
);
assert.equal(decodeFormalRecordEntry({ model: 'x.model', record_id: 7 }), null);
assert.equal(
  resolvedPath(recordEntryFromModelRights({ model: 'x.model', recordId: 7, modelRights: { write: true } })),
  '/f/x.model/7',
);
assert.equal(
  resolvedPath(recordEntryFromModelRights({ model: 'x.model', recordId: 7, modelRights: { write: 'true' } })),
  '/r/x.model/7',
);
assert.equal(
  buildActionViewRowClickTarget({ targetModel: 'x.model', rawId: 7, actionId: 4, menuId: 3, carryQuery: {}, editable: true })?.path,
  '/f/x.model/7',
);
assert.equal(
  buildActionViewRowClickTarget({ targetModel: 'x.model', rawId: 7, actionId: 4, menuId: 3, carryQuery: {}, editable: false })?.path,
  '/r/x.model/7',
);

// The compatibility carrier may preserve a legacy route, but a formal record
// envelope has higher authority and remains fail-closed when write is absent.
assert.equal(buildEntryTargetRouteTarget({
  type: 'compatibility',
  route: '/r/x.model/7',
  record_entry: { model: 'x.model', record_id: 7, entry_intent: 'handling', model_write_authority: true },
}, { actionId: 4, menuId: 3 }).path, '/f/x.model/7');
assert.equal(buildEntryTargetRouteTarget({
  type: 'compatibility',
  route: '/r/x.model/7',
  record_entry: { model: 'x.model', record_id: 7, entry_intent: 'handling' },
}, { actionId: 4, menuId: 3 }).path, '/r/x.model/7');

console.log('record_entry_contract_test: ok');

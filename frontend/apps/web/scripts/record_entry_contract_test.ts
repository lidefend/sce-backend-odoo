import assert from 'node:assert/strict';
import {
  adaptLegacyRecordEntry,
  decodeFormalRecordEntry,
  normalizeModelWriteAuthority,
  normalizeRecordOpenIntent,
  recordEntryFromModelRights,
  resolveRecordOpenTarget,
} from '../src/app/runtime/recordEntryContract';
import { isContractGapError } from '../src/app/contract/contractGap';
import {
  contractAuthLevelDeniesAccess,
  contractAuthLevelGrantsEdit,
  contractAuthLevelGrantsRead,
  normalizeContractAuthLevel,
  requireContractAuthLevel,
} from '../src/app/contract/contractAuthLevel';
import { buildEntryTargetRouteTarget } from '../src/app/routeQuery';
import { buildActionViewRowClickTarget } from '../src/app/runtime/actionViewInteractionRuntime';

function resolvedPath(entry: Parameters<typeof resolveRecordOpenTarget>[0]) {
  return resolveRecordOpenTarget(entry)?.path;
}

// A declared-but-illegal formal carrier must stop with a contract gap instead
// of being downgraded (T5).  assertGap proves the negative path is a real stop.
function assertGap(label: string, run: () => unknown) {
  let stopped = false;
  try {
    run();
  } catch (error) {
    stopped = isContractGapError(error);
  }
  assert.equal(stopped, true, `${label}: expected a ContractGapError stop`);
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
// T5: an illegal declaration stops; it is never downgraded to read-only.
assertGap('formal non-boolean write authority', () => decodeFormalRecordEntry({
  model: 'x.model', record_id: 7, entry_intent: 'handling', model_write_authority: 'true',
}));
assertGap('formal illegal entry intent', () => decodeFormalRecordEntry({
  model: 'x.model', record_id: 7, entry_intent: 'process', model_write_authority: true,
}));
// T5: a write-implying intent without a declared write authority is a gap.
assertGap('formal missing write authority', () => decodeFormalRecordEntry({
  model: 'x.model', record_id: 7, entry_intent: 'handling',
}));
assertGap('formal missing write authority (open)', () => decodeFormalRecordEntry({
  model: 'x.model', record_id: 7, entry_intent: 'open',
}));
// T5: an explicit deny stays read-only and an explicit grant stays editable.
assert.equal(
  resolvedPath(decodeFormalRecordEntry({ model: 'x.model', record_id: 7, entry_intent: 'handling', model_write_authority: false })!),
  '/r/x.model/7',
);
assert.equal(
  resolvedPath(decodeFormalRecordEntry({ model: 'x.model', record_id: 7, entry_intent: 'handling', model_write_authority: true })!),
  '/f/x.model/7',
);
// T5: a readonly intent does not require a write authority fact.
assert.equal(
  resolvedPath(decodeFormalRecordEntry({ model: 'x.model', record_id: 7, entry_intent: 'explicit_readonly' })!),
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
assertGap('entry target missing write authority', () => buildEntryTargetRouteTarget({
  type: 'compatibility',
  route: '/r/x.model/7',
  record_entry: { model: 'x.model', record_id: 7, entry_intent: 'handling' },
}, { actionId: 4, menuId: 3 }));
assert.equal(buildEntryTargetRouteTarget({
  type: 'compatibility',
  route: '/r/x.model/7',
  record_entry: { model: 'x.model', record_id: 7, entry_intent: 'handling', model_write_authority: false },
}, { actionId: 4, menuId: 3 }).path, '/r/x.model/7');

// T5: the auth-level enum is declared once; none is an explicit deny and an
// undeclared/invalid level is a declaration gap, never merged into read/edit.
assert.equal(normalizeContractAuthLevel('ADMIN'), 'admin');
assert.equal(normalizeContractAuthLevel('read'), 'read');
assert.equal(normalizeContractAuthLevel('owner'), null);
assert.equal(normalizeContractAuthLevel(undefined), null);
assert.equal(contractAuthLevelGrantsRead('read'), true);
assert.equal(contractAuthLevelGrantsRead('edit'), true);
assert.equal(contractAuthLevelGrantsRead('admin'), true);
assert.equal(contractAuthLevelGrantsRead('none'), false);
assert.equal(contractAuthLevelGrantsRead(null), false);
assert.equal(contractAuthLevelGrantsEdit('edit'), true);
assert.equal(contractAuthLevelGrantsEdit('admin'), true);
assert.equal(contractAuthLevelGrantsEdit('read'), false);
assert.equal(contractAuthLevelDeniesAccess('none'), true);
assert.equal(contractAuthLevelDeniesAccess(null), false);
assert.equal(requireContractAuthLevel('edit', { missing: 'x', requiredDeclarationLayer: 'y' }), 'edit');
assertGap('requireContractAuthLevel invalid', () => requireContractAuthLevel('owner', {
  missing: 'statusContract.globalStatus.pageAuth', requiredDeclarationLayer: 'P0:smart_core',
}));

console.log('record_entry_contract_test: ok');

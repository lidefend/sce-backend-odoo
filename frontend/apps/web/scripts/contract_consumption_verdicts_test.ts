/**
 * Behavioural locks for two T5 consumption verdicts that used to be decided by
 * the frontend instead of the declaration:
 *
 * 1. the occurrence auth enum (none < read < edit < admin); and
 * 2. the native statusbar field suppression in the form body.
 *
 * Both must consume the declaration.  `admin` implies edit, a missing/illegal
 * auth level is a contract gap (fail closed, never a silent readonly), and a
 * body occurrence of the statusbar field is only suppressed when it is the same
 * declared occurrence -- a different occurrence of the same field stays visible.
 */
import assert from 'node:assert/strict';

import { resolveOccurrenceAuthVerdict } from '../src/app/contract/contractAuthLevel';
import { resolveStatusFieldSuppression } from '../src/pages/contractForm/nativeLayoutUtils';

let cases = 0;

function verdict(auth: unknown, extra: Partial<Parameters<typeof resolveOccurrenceAuthVerdict>[0]> = {}, label = '') {
  cases += 1;
  return resolveOccurrenceAuthVerdict({ hasWidgetVerdict: true, auth, ...extra });
}

// --- 1. occurrence auth enum -----------------------------------------------
assert.equal(verdict(null, {}, 'missing').gap, true, `${'auth missing'}: a field verdict without a level is a gap`);
assert.deepEqual(
  { readonly: verdict(null).readonly, blocked: verdict(null).blocked },
  { readonly: true, blocked: true },
  'auth missing: the occurrence fails closed (readonly + blocked), never a normal widget',
);
assert.equal(verdict('owner').gap, true, 'auth illegal: an unrecognised level is a gap, not a readonly fallback');
assert.equal(verdict('none').readonly, true, 'auth none: explicit denial is readonly');
assert.equal(verdict('none').gap, false, 'auth none: explicit denial is not a gap');
assert.equal(verdict('read').readonly, true, 'auth read: readonly');
assert.equal(verdict('read').gap, false, 'auth read: declared, not a gap');
assert.equal(verdict('edit').readonly, false, 'auth edit: writable');
assert.equal(verdict('edit').gap, false, 'auth edit: declared, not a gap');
assert.equal(verdict('admin').readonly, false, 'auth admin: admin explicitly implies edit, so writable');
assert.equal(verdict('admin').gap, false, 'auth admin: declared, not a gap');
assert.equal(verdict(' ADMIN ').readonly, false, 'auth admin: trimmed/lowercased enum still grants edit');
assert.equal(verdict('edit', { unresolved: true }).readonly, true, 'an unresolved occurrence stays readonly');
assert.equal(verdict('edit', { unresolved: true }).blocked, true, 'an unresolved occurrence stays blocked');

// A button/container verdict carries no field authority and must not be read as one.
cases += 1;
const buttonVerdict = resolveOccurrenceAuthVerdict({ hasWidgetVerdict: false, auth: undefined });
assert.deepEqual(buttonVerdict, { level: null, gap: false, readonly: false, blocked: false },
  'a non-field verdict must not become readonly or a gap');

// --- 2. statusbar suppression ----------------------------------------------
cases += 1;
assert.equal(
  resolveStatusFieldSuppression({ hasNode: true, nodeIdentity: 'n.state.1', statusbarNodeIdentity: 'n.state.1', statusbarField: 'state' }),
  'state',
  'the statusbar occurrence itself is suppressed in the body',
);
cases += 1;
assert.equal(
  resolveStatusFieldSuppression({ hasNode: true, nodeIdentity: 'n.state.2', statusbarNodeIdentity: 'n.state.1', statusbarField: 'state' }),
  '',
  'a different body occurrence of the same field name stays visible',
);
cases += 1;
assert.equal(
  resolveStatusFieldSuppression({ hasNode: true, nodeIdentity: 'n.state.2', statusbarField: 'state' }),
  '',
  'without a statusbar claim a body occurrence is never suppressed by field name alone',
);
cases += 1;
assert.equal(
  resolveStatusFieldSuppression({ hasNode: false, statusbarField: 'state' }),
  'state',
  'a legacy field-level lookup still suppresses the statusbar field by name',
);
cases += 1;
assert.equal(
  resolveStatusFieldSuppression({ hasNode: true, nodeIdentity: 'n.other', statusbarNodeIdentity: 'n.state', statusbarField: '' }),
  '',
  'an absent statusbar field suppresses nothing',
);

console.log(`[contract_consumption_verdicts_test] PASS cases=${cases}`);
